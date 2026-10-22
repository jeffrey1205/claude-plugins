#!/usr/bin/env python3
"""Incremental transcript parsing.

Parses main + sub-agent transcripts into the accumulated stats dict,
reusing an on-disk cache so each invocation only processes new lines.
The read loop and the delta-merge logic are shared between the main
transcript and sub-agent transcripts via `_read_transcript_delta` and
`_merge_delta` to avoid the two near-identical copies that previously
lived in parse_transcript_incremental.
"""

import json
import os
import re
import time

import stats as stats_mod

from stats import (
    AGENT_IDS_MAX,
    CACHE_VERSION,
    RECENT_CALLS_MAX,
    SEEN_MSG_IDS_MAX,
    TOOL_IDS_MAX,
    _LAST_KEYS,
    cleanup_old_caches,
    load_cache,
    new_stats,
    save_cache,
)


# Code-mode hosts report a REPL call's argumentsDisplayText as raw JS
# (const r = await Bash({ command: "..." })). The assignment prefix and the
# wrapper call are noise that would eat the whole per-call budget on line 3,
# so strip them and keep the payload. Plain-text hints (normal tools) match
# none of these patterns and pass through untouched.
_HINT_JS_ASSIGN_RE = re.compile(r'^\s*(?:const|let|var)\s+\w+\s*=\s*')
_HINT_AWAIT_RE = re.compile(r'^\s*(?:return\s+)?await\s+')
_HINT_CALL_RE = re.compile(r'^\s*(\w+)\s*\(\s*\{(.*)\}\s*\)\s*$')
# Key names worth surfacing, most specific first so file_path wins over a
# generic path in the same argument object.
_HINT_ARG_RE = re.compile(
    r'["\']?(command|file_path|pattern|query|url|description|path)["\']?'
    r'\s*[:=]\s*["\']((?:[^"\'\\]|\\.)*)["\']')
_HINT_STRING_RE = re.compile(r'^\s*["\'](.*)["\']\s*$')


def _clean_call_hint(hint):
    """Reduce a code-mode JS hint to the payload the user cares about.

    const r = await Bash({ command: "git status" }) becomes git status,
    return await Read({ file_path: "/x" }) becomes /x, and
    const P = '/x' becomes /x. Returns hint unchanged when nothing matches
    (plain command or path summaries from ordinary tools).
    """
    if not hint:
        return hint
    text = hint.strip()
    text = _HINT_JS_ASSIGN_RE.sub('', text)
    text = _HINT_AWAIT_RE.sub('', text)
    call = _HINT_CALL_RE.match(text)
    if call:
        arg = _HINT_ARG_RE.search(call.group(2))
        if arg:
            return arg.group(2).replace('\\"', '"').replace("\\'", "'")
        return text
    literal = _HINT_STRING_RE.match(text)
    if literal:
        return literal.group(1)
    return hint


# Tool name -> argument key used to build its one-line call summary.
_SUMMARY_ARG_KEY = {
    'Bash': 'command',
    'Read': 'file_path',
    'Edit': 'file_path',
    'Write': 'file_path',
    'Glob': 'pattern',
    'Agent': 'description',
    'WebFetch': 'url',
    'WebSearch': 'query',
}


def _extract_call_summary(name, args):
    """Extract a short summary from a function_call's parsed arguments.

    args should be a dict (already parsed from JSON).
    Truncation is handled by format_recent_calls, not here.
    """
    if not isinstance(args, dict) or not args:
        return name

    key = _SUMMARY_ARG_KEY.get(name)
    if key:
        return args.get(key, '') or name

    if name == 'Grep':
        pat = args.get('pattern', '')
        path = args.get('path', '')
        if pat or path:
            return f"{pat} {path}".strip()
        return name

    # Generic: first string value
    for v in args.values():
        if isinstance(v, str) and v:
            return v
    return name


# Tools that spawn a sub-agent: counted as running until their result lands.
AGENT_TOOL_NAMES = frozenset(('Agent', 'Task'))


def new_state():
    """Cross-invocation dedup state, persisted next to the stats cache.

    seen_msg_ids: Claude can write several lines for one assistant message
        (same message.id/usage); usage is counted once per id.
    tool_ids: tool_use ids already counted, so a repeated content block
        cannot inflate tool_counts.
    agent_ids: live Agent/Task call ids; Claude's tool_result carries only
        the id, so this is how a running agent gets closed.
    """
    return {"seen_msg_ids": [], "tool_ids": [], "agent_ids": []}


def normalize_state(state):
    """Return a usable state dict (cache from an older run may be partial)."""
    if not isinstance(state, dict):
        return new_state()
    for key in ('seen_msg_ids', 'tool_ids', 'agent_ids'):
        value = state.get(key)
        if not isinstance(value, list):
            value = []
        state[key] = [v for v in value if isinstance(v, str)]
    del state['seen_msg_ids'][:-SEEN_MSG_IDS_MAX]
    del state['tool_ids'][:-TOOL_IDS_MAX]
    del state['agent_ids'][:-AGENT_IDS_MAX]
    return state


def _remember(state, key, value, limit):
    """Append *value* to a bounded list, dropping the oldest entries."""
    if not value:
        return
    items = state[key]
    if value in items:
        return
    items.append(value)
    del items[:-limit]


def _parse_arguments(raw):
    """Return a tool-call argument dict from a dict or a JSON string."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw:
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _norm_usage(input_tokens, output_tokens, cache_read, cache_write,
                reasoning, credits, model, message_id):
    """Normalize one usage record; `input` is INCLUSIVE of cache tokens."""
    return {
        "input": int(input_tokens or 0),
        "output": int(output_tokens or 0),
        "cache_read": int(cache_read or 0),
        "cache_write": int(cache_write or 0),
        "reasoning": int(reasoning or 0),
        "credits": float(credits or 0),
        "model": model or "",
        "message_id": message_id or "",
    }


def extract_usage(entry):
    """Return normalized token/credit usage for *entry*, or None.

    Branching is by line shape, not by host: CodeBuddy writes
    providerData.usage/rawUsage on function_call and reasoning entries, Claude
    Code writes message.usage on assistant entries. A wrong host guess can
    therefore never lose tokens.

    Invariant: `input` INCLUDES cache reads/writes on both hosts. CodeBuddy's
    usage.inputTokens already includes them; Claude Code reports plain input,
    cache writes and cache reads separately, so those are summed here.
    """
    if not isinstance(entry, dict):
        return None

    if entry.get('type') == 'assistant':
        message = entry.get('message')
        if not isinstance(message, dict):
            return None
        usage = message.get('usage')
        if not isinstance(usage, dict):
            return None
        cache_write = usage.get('cache_creation_input_tokens', 0) or 0
        cache_read = usage.get('cache_read_input_tokens', 0) or 0
        plain = usage.get('input_tokens', 0) or 0
        return _norm_usage(
            input_tokens=plain + cache_write + cache_read,
            output_tokens=usage.get('output_tokens', 0) or 0,
            cache_read=cache_read,
            cache_write=cache_write,
            reasoning=0,
            credits=0,
            model=message.get('model') or '',
            message_id=message.get('id') or '',
        )

    provider = entry.get('providerData')
    if not isinstance(provider, dict):
        return None
    usage = provider.get('usage') or {}
    raw_usage = provider.get('rawUsage') or {}
    if not isinstance(usage, dict) or not isinstance(raw_usage, dict):
        return None
    if not usage and not raw_usage:
        return None

    input_tokens = usage.get('inputTokens', 0) or 0   # already cache-inclusive
    output_tokens = usage.get('outputTokens', 0) or 0
    cache_read = sum(
        detail.get('cached_tokens', 0) or 0
        for detail in (usage.get('inputTokensDetails') or [])
        if isinstance(detail, dict)
    )
    reasoning = sum(
        detail.get('reasoning_tokens', 0) or 0
        for detail in (usage.get('outputTokensDetails') or [])
        if isinstance(detail, dict)
    )
    cache_write = 0
    credits = 0.0
    if raw_usage:
        if 'prompt_cache_hit_tokens' in raw_usage:
            cache_read = raw_usage.get('prompt_cache_hit_tokens') or 0
        cache_write = raw_usage.get('cache_creation_input_tokens', 0) or 0
        credits = raw_usage.get('credit', 0) or 0

    return _norm_usage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read=cache_read,
        cache_write=cache_write,
        reasoning=reasoning,
        credits=credits,
        model=provider.get('requestModelName') or provider.get('requestModelId') or '',
        message_id='',
    )


def iter_calls(entry):
    """Return [(call_id, name, args, summary_hint)] for tool calls in *entry*."""
    calls = []
    if not isinstance(entry, dict):
        return calls
    if entry.get('type') == 'function_call':
        name = entry.get('name') or ''
        if name:
            provider = entry.get('providerData')
            hint = entry.get('argumentsDisplayText') or ''
            if not hint and isinstance(provider, dict):
                hint = provider.get('argumentsDisplayText') or ''
            calls.append((entry.get('callId') or entry.get('id') or '', name,
                          _parse_arguments(entry.get('arguments')), hint))
        return calls
    if entry.get('type') == 'assistant':
        message = entry.get('message')
        content = message.get('content') if isinstance(message, dict) else None
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict) or block.get('type') != 'tool_use':
                    continue
                name = block.get('name') or ''
                if name:
                    calls.append((block.get('id') or '', name,
                                  _parse_arguments(block.get('input')), ''))
    return calls


def iter_results(entry):
    """Return [(call_id, name)] for tool results in *entry*."""
    results = []
    if not isinstance(entry, dict):
        return results
    if entry.get('type') == 'function_call_result':
        results.append((entry.get('callId') or '', entry.get('name') or ''))
        return results
    if entry.get('type') == 'user':
        message = entry.get('message')
        content = message.get('content') if isinstance(message, dict) else None
        if isinstance(content, list):
            for block in content:
                if (isinstance(block, dict) and block.get('type') == 'tool_result'
                        and block.get('tool_use_id')):
                    results.append((block['tool_use_id'], ''))
    return results


def _add_compact_periodic(stats, entry):
    """Count context compaction and periodic summaries (per host dialect)."""
    entry_type = entry.get('type')
    if entry_type == 'system':
        # Claude Code: one boundary marker per /compact. Its summary message
        # is also marked isCompactSummary, which we ignore to avoid counting
        # the same compaction twice.
        if entry.get('subtype') == 'compact_boundary':
            stats["compact_count"] += 1
        return
    if entry_type == 'message':
        # CodeBuddy: the summary line carries both flags; the follow-up
        # "Please continue" line does not.
        provider = entry.get('providerData')
        if (isinstance(provider, dict) and provider.get('isCompactInternal')
                and provider.get('isSummary')):
            stats["compact_count"] += 1
        return
    if entry_type == 'summary':
        provider = entry.get('providerData')
        if isinstance(provider, dict):
            if provider.get('source') not in ('initial-user-message', None):
                stats["periodic_count"] += 1


def add_line_to_stats(stats, data, state=None, is_main=True):
    """Parse a single JSONL entry and accumulate into stats.

    *state* carries the bounded dedup sets across invocations; pass None for
    a one-off parse (tests), which is equivalent to a fresh
    session. *is_main* is False for sub-agent transcripts: those lines are
    all sidechain traffic, so the isSidechain skip must not apply.
    """
    if not isinstance(data, dict):
        return
    if state is None:
        state = new_state()
    if is_main and data.get('isSidechain') is True:
        # Sub-agent traffic is counted from <session-dir>/subagents/*.jsonl.
        return

    for call_id, name, args, hint in iter_calls(data):
        if call_id and call_id in state['tool_ids']:
            continue
        _remember(state, 'tool_ids', call_id, TOOL_IDS_MAX)
        stats["tool_counts"][name] = stats["tool_counts"].get(name, 0) + 1
        if name in AGENT_TOOL_NAMES:
            stats["running_agents"] += 1
            _remember(state, 'agent_ids', call_id, AGENT_IDS_MAX)
        recent = stats["recent_calls"]
        recent.append({"name": name,
                       "summary": _clean_call_hint(hint)
                       or _extract_call_summary(name, args)})
        if len(recent) > RECENT_CALLS_MAX:
            del recent[:-RECENT_CALLS_MAX]

    for call_id, name in iter_results(data):
        if name in AGENT_TOOL_NAMES or (call_id and call_id in state['agent_ids']):
            stats["running_agents"] -= 1
            if call_id in state['agent_ids']:
                state['agent_ids'].remove(call_id)
    _add_compact_periodic(stats, data)

    usage = extract_usage(data)
    if usage is None:
        return
    if usage['message_id']:
        if usage['message_id'] in state['seen_msg_ids']:
            return  # repeated line for an already-counted assistant message
        _remember(state, 'seen_msg_ids', usage['message_id'], SEEN_MSG_IDS_MAX)
    if usage['input'] <= 0 and usage['output'] <= 0:
        return

    stats["total_input"] += usage['input']
    stats["total_output"] += usage['output']
    stats["total_cache_read"] += usage['cache_read']
    stats["total_cache_write"] += usage['cache_write']
    stats["total_reasoning"] += usage['reasoning']
    stats["total_credits"] += usage['credits']
    stats["request_count"] += 1
    stats["last_input"] = usage['input']
    stats["last_output"] = usage['output']
    stats["last_cache_read"] = usage['cache_read']
    stats["last_credits"] = usage['credits']


# Substrings that mark a line as possibly contributing to the stats. A fast
# pre-filter only: a false positive costs one json.loads, a false negative
# would silently drop data, so keep it broad and cover both host dialects.
_PREFILTER_TOKENS = (
    'providerData', 'function_call', '"assistant"', 'tool_use', 'tool_result',
    'compact_boundary', '"summary"',
)


def _line_may_contribute(line):
    """True when *line* may affect the stats (cheap substring test)."""
    for token in _PREFILTER_TOKENS:
        if token in line:
            return True
    return False


def _read_transcript_delta(path, offset, state=None, is_main=True):
    """Read a transcript from *offset*; return (delta, new_offset, has_new, truncated).

    Shared read loop for both the main transcript and sub-agent transcripts:
      - truncation: an offset past EOF means the file shrank (rewritten), so
        report it and let the caller re-parse everything from 0.
      - fast path: if offset is at EOF (and > 0), nothing to read.
      - partial last line (mid-write): stop before it and report the offset
        of the incomplete line so the next cycle re-reads it.
      - pre-filter skips lines that cannot contribute to stats.

    Returns an empty delta (new_stats()) when there is nothing new or the
    file is unavailable, so callers can treat it as a no-op.
    """
    try:
        file_size = os.path.getsize(path)
    except (IOError, OSError):
        return new_stats(), offset, False, False
    if offset > file_size:
        # Cached offset is past EOF. The caller cannot subtract the removed
        # lines' per-transcript contributions, so it must discard the cached
        # stats and re-read this transcript from 0.
        return new_stats(), offset, False, True
    if offset == file_size and offset > 0:
        return new_stats(), offset, False, False

    delta = new_stats()
    has_new_data = False
    failed_line_offset = None
    try:
        with open(path, 'rb') as f:
            if offset > 0:
                f.seek(offset)
            while True:
                line_start = f.tell()
                raw_line = f.readline()
                if not raw_line:
                    break
                has_new_data = True
                try:
                    line = raw_line.decode('utf-8')
                except UnicodeDecodeError:
                    continue
                # If line has no trailing newline, the writer is likely
                # mid-write. Stop reading here so we don't advance the
                # offset past this partial line. On the next cycle, we'll
                # re-read from this offset and hopefully get the full line.
                if not line.endswith('\n'):
                    failed_line_offset = line_start
                    break
                if not _line_may_contribute(line):
                    continue
                try:
                    data = json.loads(line)
                    add_line_to_stats(delta, data, state, is_main)
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
            new_offset = failed_line_offset if failed_line_offset is not None else f.tell()
    except (IOError, OSError):
        return new_stats(), offset, False, False

    if not has_new_data:
        return new_stats(), offset, False, False
    return delta, new_offset, True, False


def _merge_delta(stats, delta, is_main, previous_running_agents=0):
    """Merge a transcript *delta* into the accumulated *stats*.

    Shared by the main transcript and sub-agent transcripts. Sub-agent
    transcripts (is_main=False) contribute tokens/credits/tools but NOT
    running_agents/compact_count/periodic_count, because those counters are
    main-transcript-only.

    last_* fields are "last value" not cumulative; they are overwritten only
    when the delta carries a non-zero value (i.e. a new API response).
    """
    # Sub-agent transcripts contribute tokens/credits/tools only; these three
    # counters are main-transcript-only. running_agents is merged after the
    # loop because it needs the previous cached value.
    skip_keys = {"running_agents"} if is_main else {"running_agents", "compact_count", "periodic_count"}

    for key in delta:
        if key in skip_keys:
            continue
        if key in _LAST_KEYS:
            if delta[key]:
                stats[key] = delta[key]
            continue
        if isinstance(delta[key], (int, float)):
            stats[key] = stats.get(key, 0) + delta[key]
        elif isinstance(delta[key], dict):
            if not isinstance(stats.get(key), dict):
                stats[key] = {}
            for k, v in delta[key].items():
                stats[key][k] = stats[key].get(k, 0) + v
        elif isinstance(delta[key], list):
            stats[key] = (stats.get(key) or []) + delta[key]
            stats[key] = stats[key][-RECENT_CALLS_MAX:]

    if is_main:
        stats["running_agents"] = max(0, delta["running_agents"] + previous_running_agents)


def _sub_agent_transcripts(subagents_dir, sub_offsets):
    """Return [(agent_key, path, offset)] for each sub-agent transcript.

    Materialized as a list (not a generator) because the caller needs the
    same set twice — once for the offsets bookkeeping, once for the read
    loop — and a generator would list the directory twice. Cached offsets
    are validated here so a corrupted cache value falls back to 0.
    """
    entries = []
    if not os.path.isdir(subagents_dir):
        return entries
    try:
        for fname in os.listdir(subagents_dir):
            if not fname.endswith('.jsonl'):
                continue
            agent_key = fname[:-6]
            offset = sub_offsets.get(agent_key, 0)
            if not isinstance(offset, (int, float)):
                offset = 0
            entries.append((agent_key, os.path.join(subagents_dir, fname), offset))
    except OSError:
        pass
    return entries


def _collect_deltas(transcript_path, subs, main_offset, stats, previous_running_agents, state=None):
    """Read main + sub-agent transcripts from their offsets and merge into *stats*.

    *subs* is the materialized list from _sub_agent_transcripts.

    Returns (any_new, truncated, main_offset, sub_offsets). When *truncated*
    is True nothing has been merged, so the caller discards *stats* and
    calls this again with every offset at 0 — the first pass is then free of
    double-counting by construction.
    """
    main_delta, main_new_offset, main_has_new, truncated = _read_transcript_delta(
        transcript_path, main_offset, state, is_main=True)
    if truncated:
        return False, True, main_offset, {}
    any_new = main_has_new
    _merge_delta(stats, main_delta, is_main=True,
                 previous_running_agents=previous_running_agents)

    sub_offsets = {}
    for agent_key, sub_path, sub_offset in subs:
        sub_delta, sub_new_offset, sub_has_new, sub_truncated = _read_transcript_delta(
            sub_path, sub_offset, state, is_main=False)
        if sub_truncated:
            return False, True, main_offset, {}
        sub_offsets[agent_key] = sub_new_offset
        if sub_has_new:
            any_new = True
        # Sub-agents contribute tokens/credits/tools but NOT
        # running_agents/compact_count/periodic_count.
        _merge_delta(stats, sub_delta, is_main=False)

    return any_new, False, main_new_offset, sub_offsets


def parse_transcript_incremental(transcript_path, session_id):
    """Parse main + sub-agent transcripts incrementally.

    Extracts In/Out/Cache/Think/Credits/Req/Tools/Compact/Periodic from all transcripts.
    Sub-agents contribute to token/credit/tool counts but NOT to
    running_agents, compact_count, or periodic_count (those are main-transcript-only).

    Skip-write: if no new data was found, skip writing the cache entirely.
    Truncation handling: truncation is detected while reading (a cached offset
    past EOF), which is also the only getsize each transcript needs. If any
    transcript was truncated, discard all cached stats and re-parse everything
    from scratch. This avoids double-counting when we can't subtract old
    per-sub-agent contributions.
    """
    stats = new_stats()

    if not transcript_path:
        return stats, False

    # Determine sub-agent directory
    session_dir = transcript_path[:-6] if transcript_path.endswith('.jsonl') else transcript_path
    subagents_dir = os.path.join(session_dir, "subagents")

    # Load cache
    cache = load_cache(session_id)
    if cache and (cache.get("cache_version") != CACHE_VERSION
                  or (cache.get("host") and cache.get("host") != stats_mod.HOST)):
        # A cache from another host (or an older schema) cannot be merged:
        # offsets and counters refer to different transcripts.
        cache = None
    state = normalize_state(cache.get("state") if cache else None)
    previous_running_agents = 0
    main_offset = 0
    sub_offsets = {}
    if cache:
        if "stats" in cache and isinstance(cache["stats"], dict):
            stats = cache["stats"]
            # Backfill new fields and remove obsolete keys for same-version caches
            defaults = new_stats()
            valid_keys = set(defaults)
            for key, default in defaults.items():
                if key not in stats:
                    if isinstance(default, list):
                        stats[key] = list(default)
                    elif isinstance(default, dict):
                        stats[key] = dict(default)
                    else:
                        stats[key] = default
            for obsolete in list(stats.keys()):
                if obsolete not in valid_keys:
                    del stats[obsolete]
            previous_running_agents = stats.get("running_agents", 0)
        if "main_offset" in cache and isinstance(cache["main_offset"], (int, float)):
            main_offset = cache["main_offset"]
        if "sub_offsets" in cache and isinstance(cache["sub_offsets"], dict):
            sub_offsets = cache["sub_offsets"]

    # Materialize the sub-agent list once; it drives both passes below.
    subs = _sub_agent_transcripts(subagents_dir, sub_offsets)

    any_new_data, any_truncated, main_offset, sub_offsets = _collect_deltas(
        transcript_path, subs, main_offset, stats, previous_running_agents, state)

    # --- Full re-parse: discard cache, parse everything from offset 0 ---
    if any_truncated:
        stats = new_stats()
        state = new_state()
        subs = [(agent_key, path, 0) for agent_key, path, _ in subs]
        any_new_data, _, main_offset, sub_offsets = _collect_deltas(
            transcript_path, subs, 0, stats, 0, state)

    # Skip cache write when nothing changed and no truncation occurred.
    if any_new_data or any_truncated or cache is None:
        save_cache(session_id, stats, main_offset, sub_offsets, state)

    # Cleanup old caches ~1% of the time to avoid O(n) scan every 300ms.
    if int(time.time() * 1000) % 97 < 1:
        cleanup_old_caches(session_id)

    return stats, any_truncated
