#!/usr/bin/env python3
"""Rendering: tool lists, recent calls, and the 3-line statusline assembly.

build_statusline(input_data, stats_dict) assembles the full three-line output
that statusline.py's main() previously built inline. Keeping it here keeps
the entry point a thin orchestrator and groups all presentation logic.
"""

import json
import os
import re

from formatting import (
    BLUE,
    CYAN,
    DIM,
    GREEN,
    NC,
    PURPLE,
    RED,
    YELLOW,
    format_duration,
    format_tokens,
    _visible_len,
    get_statusline_width_from_input,
    make_progress_bar,
    truncate_to_width,
)
from gitinfo import format_git_info, get_git_info
import stats


# A CodeBuddy worktree lives at <project>/.codebuddy/worktrees/<name>; the leaf
# is a generated name ("worktree") that is meaningless to the user.
_CODEBUDDY_WORKTREE_RE = re.compile(r'^(?P<root>.+)/\.codebuddy/worktrees/[^/]+/?$')
# A git-linked worktree's .git is a *file* containing
# "gitdir: <mainrepo>/.git/worktrees/<name>".
_GIT_WORKTREE_GITDIR_RE = re.compile(r'^(?P<root>.+?)/\.git/worktrees/[^/]+/?$')


def _display_dir_name(cwd):
    """Directory name to show for *cwd*.

    Worktrees obscure the real project name. Resolve back to the main project
    directory in either common case:
      * CodeBuddy worktrees: <project>/.codebuddy/worktrees/<name>
      * git-linked worktrees: a .git *file* pointing at
        <mainrepo>/.git/worktrees/<name>
    Otherwise fall back to the plain directory name.
    """
    if not cwd:
        return ""
    cwd = cwd.rstrip('/')
    m = _CODEBUDDY_WORKTREE_RE.match(cwd)
    if m:
        return os.path.basename(m.group('root')) or ""
    git_path = os.path.join(cwd, '.git')
    if os.path.isfile(git_path):
        try:
            with open(git_path, 'r') as f:
                content = f.read()
        except OSError:
            pass
        else:
            gm = re.search(r'gitdir:\s*(\S+)', content)
            if gm:
                gd = gm.group(1)
                if not os.path.isabs(gd):
                    gd = os.path.normpath(os.path.join(cwd, gd))
                wm = _GIT_WORKTREE_GITDIR_RE.match(gd)
                if wm:
                    return os.path.basename(wm.group('root')) or ""
    return os.path.basename(cwd) or ""


# Tool display order and short names
TOOL_ORDER = ["Bash", "Read", "Edit", "Write", "Glob", "Grep", "Agent", "WebFetch", "WebSearch"]
TOOL_SHORT = {
    "Bash": "Bash", "Read": "Read", "Edit": "Edit", "Write": "Write",
    "Glob": "Glob", "Grep": "Grep", "Agent": "Agent",
    "WebFetch": "Fetch", "WebSearch": "Search",
}

# One entry is "Tool summary..."; the cap covers the whole entry so the width
# budget stays predictable (the tool-name prefix is part of it).
RECENT_CALLS_ENTRY_MAX = 68
RECENT_CALLS_ENTRY_MIN = 16


# ---------------------------------------------------------------------------
# Configurable layout
#
# The three-line statusline is assembled from discrete "blocks". A statusline-owned
# config file (<config-dir>/plugins/data/statusline/config.json, where
# config-dir = CODEBUDDY_CONFIG_DIR or ~/.codebuddy) decides which blocks are
# shown, their order on line 1, and whether the Tools line and the Recent
# block are enabled.
# With no config file, BLOCKS_LINE1 is the default layout and the output is
# identical to the pre-config build.
# ---------------------------------------------------------------------------

def _config_path():
    """Location of the layout config, reusing the data dir (stats._PLUGIN_DATA)."""
    return os.path.join(stats._PLUGIN_DATA, "config.json")


def load_layout_config():
    """Read the layout config JSON, or None if missing/invalid.

    Any failure (missing file, bad JSON, wrong shape) returns None so the
    caller falls back to the default layout — a broken config must never
    blank the statusline.
    """
    try:
        with open(_config_path(), 'r') as f:
            data = json.load(f)
    except (IOError, ValueError):  # ValueError covers json.JSONDecodeError
        return None
    if not isinstance(data, dict):
        return None
    return data


def resolve_layout(cfg):
    """Resolve the effective layout from a raw config dict.

    Rules:
      - line1_order: shown blocks, in this order.
      - line1_hidden: explicitly hidden (takes precedence over order).
      - any known block in neither list (e.g. added in a future release) is
        auto-appended to the end and shown, so new blocks never silently
        vanish for users with a custom config.
      - unknown ids in line1_order are ignored.
      - missing/garbled config -> built-in defaults (all shown, both lines on).
    """
    layout = cfg.get("layout", {}) if isinstance(cfg, dict) else {}
    if not isinstance(layout, dict):
        layout = {}

    order = layout.get("line1_order", BLOCKS_LINE1)
    if not isinstance(order, list):
        order = BLOCKS_LINE1

    hidden = layout.get("line1_hidden", [])
    if not isinstance(hidden, list):
        hidden = []
    hidden = set(hidden)

    # Drop unknown ids (typos / removed blocks).
    order = [b for b in order if b in RENDERERS]

    # Auto-append known blocks neither ordered nor hidden (new-block safety).
    for b in BLOCKS_LINE1:
        if b not in order and b not in hidden:
            order.append(b)

    # Hidden wins: never render a hidden block.
    order = [b for b in order if b not in hidden]

    tools = layout.get("tools", True)
    recent = layout.get("recent", True)
    # The 'recent' toggle gates the recent block exactly like 'hidden' does,
    # so 'list' output and the render loop stay in sync with no special case.
    if not recent:
        order = [b for b in order if b != "recent"]
    return {
        "line1_order": order,
        "tools": bool(tools),
        "recent": bool(recent),
    }


# --- Block renderers (line 1) ----------------------------------------------
# Each returns the finished, colored string for its block, or "" when the
# block has nothing to show.

def _render_cwd_git(input_data, stats_dict):
    workspace = input_data.get('workspace') or {}
    git_cwd = workspace.get('current_dir') or os.getcwd()
    cwd_name = _display_dir_name(git_cwd)
    git_info = get_git_info(git_cwd)
    git_part = format_git_info(git_info) if git_info else ""
    parts = []
    if cwd_name:
        parts.append(f"{CYAN}{cwd_name}{NC}")
    if git_part:
        parts.append(git_part)
    # Session line changes ride with the git segment (space-joined, no "|"),
    # per the line-1 layout: "proj on  main* +26/-4 | model | ...".
    cost = input_data.get('cost') or {}
    added = cost.get('total_lines_added', 0) or 0
    removed = cost.get('total_lines_removed', 0) or 0
    if added > 0 or removed > 0:
        parts.append(f"{GREEN}+{added}{NC}/{RED}-{removed}{NC}")
    return " ".join(parts)


def _render_model(input_data, stats_dict):
    model = input_data.get('model') or {}
    model_name = model.get('display_name', '')
    return f"{BLUE}{model_name}{NC}" if model_name else ""


def _render_effort(input_data, stats_dict):
    """Reasoning effort level, when the host exposes one.

    Claude Code sends effort.level (low/medium/high/xhigh/max) and omits the
    key entirely for models without the parameter; CodeBuddy does not send it
    at all. Rendering nothing when it is absent keeps the line clean.
    """
    effort = input_data.get('effort')
    level = ''
    if isinstance(effort, dict):
        level = str(effort.get('level') or '').strip()[:12]
    return (PURPLE + 'Effort:' + NC + level) if level else ''


def _current_context_tokens(ctx):
    """Live context length from the latest request (non-overlapping parts)."""
    usage = ctx.get('current_usage')
    if not isinstance(usage, dict):
        return 0
    return ((usage.get('input_tokens', 0) or 0)
            + (usage.get('cache_creation_input_tokens', 0) or 0)
            + (usage.get('cache_read_input_tokens', 0) or 0))


def _render_context_bar(input_data, stats_dict):
    """Bar + percentage + window ceiling, e.g. `██░░ 27% 1.0M`.

    The used-token count is intentionally NOT repeated here: the Tokens block
    already carries it, and showing `265.1K/1.0M` as well pushed line 1 past
    the terminal width. used_percentage is 0-100 (host rounds to 2 dp), so it
    is converted to a 0-1 ratio for the bar.
    """
    ctx = input_data.get('context_window') or {}
    used_pct = ctx.get('used_percentage')
    ctx_size = ctx.get('context_window_size', 0) or 0

    ratio = None
    if used_pct is not None:
        try:
            # Clamp so a >100 value (possible mid-compaction) cannot overflow.
            ratio = min(used_pct / 100.0, 1.0)
        except (TypeError, ValueError):
            ratio = None

    if ratio is not None:
        bar, _ = make_progress_bar(ratio, width=10)
        part = f"{bar} {DIM}{round(ratio * 100)}%{NC}"
        if ctx_size > 0:
            part += f" {DIM}{format_tokens(ctx_size)}{NC}"
        return part

    if ctx_size > 0:
        return f"{DIM}Max:{format_tokens(ctx_size)}{NC}"

    # No ratio and no ceiling (some models omit the metadata): the raw current
    # usage is still useful, so show it rather than dropping the block.
    current = _current_context_tokens(ctx)
    return f"{DIM}{format_tokens(current)}{NC}" if current > 0 else ""


def _render_compact_periodic(input_data, stats_dict):
    # Compact/Periodic counts: always show when present, even if
    # used_percentage is null (e.g. first call right after compact).
    # Rendered as its own " | "-separated block (no leading space), so the
    # parts join cleanly whether only Compact, only Periodic, or both show.
    parts = []
    if stats_dict.get('compact_count', 0) > 0:
        parts.append(f"{YELLOW}Compact×{stats_dict['compact_count']}{NC}")
    if stats_dict.get('periodic_count', 0) > 0:
        parts.append(f"{DIM}Periodic×{stats_dict['periodic_count']}{NC}")
    return " ".join(parts)


def _render_tokens(input_data, stats_dict):
    """Session In/Out plus the cache hit ratio.

    Cache is shown as a percentage only: the token count duplicates `In`
    (cache reads are a subset of it) and made the line too wide. Reasoning
    tokens (Think) are not rendered.
    """
    ctx = input_data.get('context_window') or {}
    display_in = stats_dict.get('total_input', 0) or ctx.get('total_input_tokens') or 0
    display_out = stats_dict.get('total_output', 0) or ctx.get('total_output_tokens') or 0
    display_cache = stats_dict.get('total_cache_read', 0) or 0

    parts = [
        f"{GREEN}In:{NC}{format_tokens(display_in)}",
        f"{GREEN}Out:{NC}{format_tokens(display_out)}",
    ]
    if display_cache > 0 and display_in > 0:
        cache_pct = int(display_cache / display_in * 100)
        parts.append(f"{DIM}Cache:{NC}{cache_pct}%")
    return " ".join(parts)


def _render_requests(input_data, stats_dict):
    n = stats_dict.get('request_count', 0) or 0
    return f"{CYAN}Req:{NC}{n}" if n > 0 else ""


def _render_credits(input_data, stats_dict):
    c = stats_dict.get('total_credits', 0) or 0
    return f"{YELLOW}Credits:{NC}{c:.2f}" if c > 0 else ""


def _render_time(input_data, stats_dict):
    cost = input_data.get('cost') or {}
    duration_str = format_duration(cost.get('total_duration_ms', 0) or 0)
    return f"{DIM}Time:{NC}{duration_str}" if duration_str else ""


def _render_speed(input_data, stats_dict):
    """Session-average output throughput, in tokens per second.

    Numerator is total output tokens (main + sub-agent transcripts).
    Denominator is cost.total_api_duration_ms — the *pure model* time the
    host tracks — NOT cost.total_duration_ms, which is wall-clock and
    includes tool execution and idle waiting; dividing by it would badly
    understate the rate. Labelled "Avg" because it averages the whole
    session; the line-3 "Speed" item is the recent delta instead.

    Caveat: total_api_duration_ms is host-side and may not include
    sub-agent API time, while total_output does. So a sub-agent-heavy run
    can read slightly high. It is still the closest available denominator.
    """
    cost = input_data.get('cost') or {}
    api_ms = cost.get('total_api_duration_ms', 0) or 0
    out = stats_dict.get('total_output', 0) or 0
    if api_ms <= 0 or out <= 0:
        return ""
    rate = out / (api_ms / 1000.0)
    return f"{PURPLE}Avg:{NC}{rate:.1f}t/s"


def _render_recent(input_data, stats_dict):
    """Line-2 'Recent:' block: tokens, cache ratio and speed of the last turn.

    Credits are deliberately omitted: the cumulative Credits block already
    shows them on line 1, and repeating them was pure duplication.

    recent_rate (tokens/s or None) is injected into *stats_dict* by
    build_statusline from the entry-point delta measurement; None (not yet
    measurable) omits the Speed item.
    """
    last_in = stats_dict.get('last_input', 0) or 0
    last_out = stats_dict.get('last_output', 0) or 0
    last_cache = stats_dict.get('last_cache_read', 0) or 0
    if last_in <= 0 and last_out <= 0:
        return ""
    parts = [
        f"{GREEN}In:{NC}{format_tokens(last_in)}",
        f"{GREEN}Out:{NC}{format_tokens(last_out)}",
    ]
    if last_cache > 0 and last_in > 0:
        parts.append(f"{DIM}Cache:{NC}{int(last_cache / last_in * 100)}%")
    recent_rate = stats_dict.get('recent_rate')
    if recent_rate is not None:
        parts.append(f"{PURPLE}Speed:{NC}{recent_rate:.1f}t/s")
    return f"{DIM}Recent:{NC} " + " ".join(parts)


RENDERERS = {
    "cwd_git": _render_cwd_git,
    "model": _render_model,
    "effort": _render_effort,
    "context_bar": _render_context_bar,
    "compact_periodic": _render_compact_periodic,
    "time": _render_time,
    "credits": _render_credits,
    "requests": _render_requests,
    "tokens": _render_tokens,
    "recent": _render_recent,
    "speed": _render_speed,
}

# Canonical block order = default layout, and the auto-append order for new blocks.
BLOCKS_LINE1 = list(RENDERERS.keys())


def _format_tool_entry(prefix, color, name, count=None):
    """Format a single tool entry like '✓ Bash×3' or '↑ Agent'.

    Count is shown only when > 1.
    """
    entry = f"{color}{prefix}{NC} {name}"
    if count is not None and count > 1:
        entry += f"{DIM}×{count}{NC}"
    return entry


def format_tools(tool_counts, running_agents=0):
    """Format tool usage like: ✓ Bash×15 ✓ Read×2 ✓ Edit
    Agent shows running count: ↑ Agent×2 or just ✓ Agent×3"""
    if not tool_counts and running_agents == 0:
        return ""

    # Order: known tools first, then any others alphabetically
    ordered = []
    seen = set()
    for name in TOOL_ORDER:
        if name in tool_counts:
            ordered.append((name, tool_counts[name]))
            seen.add(name)
    for name in sorted(tool_counts.keys()):
        if name not in seen:
            ordered.append((name, tool_counts[name]))

    parts = []
    for name, count in ordered:
        short = TOOL_SHORT.get(name, name)
        if name == 'Agent' and running_agents > 0:
            parts.append(_format_tool_entry("↑", YELLOW, "Agent", running_agents))
            completed = count - running_agents
            if completed > 0:
                parts.append(_format_tool_entry("✓", GREEN, "Agent", completed))
        else:
            parts.append(_format_tool_entry("✓", GREEN, short, count))

    return " | ".join(parts)


def _merge_repeat_calls(calls):
    """Collapse runs of identical consecutive calls (newest-first list).

    Repeated polling (git status, ls) shows up as N identical entries that
    spend the whole per-call budget saying the same thing. Adjacent entries
    with the same name AND summary become one entry carrying its repeat
    count, rendered by format_recent_calls with a ×N suffix. Entries are
    copied so the cached stats dict is never mutated.
    """
    merged = []
    for call in calls:
        if merged:
            prev = merged[-1]
            if (prev.get('name') == call.get('name')
                    and prev.get('summary') == call.get('summary')):
                prev['count'] = prev.get('count', 1) + 1
                continue
        item = dict(call)
        item['count'] = 1
        merged.append(item)
    return merged


def format_recent_calls(recent_calls, max_entry_len=RECENT_CALLS_ENTRY_MAX):
    """Format the most recent function calls as line 3.

    Each call shows: ToolName summary_text(truncated). A call repeated
    back-to-back carries a ×N suffix (see _merge_repeat_calls).
    """
    if not recent_calls:
        return ""

    parts = []
    for call in reversed(recent_calls):
        name = call.get('name', '')
        summary = call.get('summary', '')
        short = TOOL_SHORT.get(name, name)
        count = call.get('count', 1)
        suffix = ' %s×%d%s' % (DIM, count, NC) if count > 1 else ''
        if summary and summary != name:
            # A multi-line command would inject extra rows into the statusline;
            # collapse all whitespace before truncating.
            summary = ' '.join(str(summary).split())
            # Truncate to max_summary visible columns (CJK-safe).
            # Previously used len() which miscounts wide characters and can
            # split ANSI escape sequences. The ×N suffix shares the budget.
            room = max(6, max_entry_len - _visible_len(short) - 1
                       - _visible_len(suffix))
            summary = truncate_to_width(summary, room)
            parts.append(f"{CYAN}{short}{NC} {DIM}{summary}{NC}{suffix}")
        else:
            parts.append(f"{CYAN}{short}{NC}{suffix}")
    return " | ".join(parts)


# Blocks grouped by what they describe. Line 1 answers "where am I / what am
# I talking to" plus the session clock (time, credits), line 2 is the session
# totals with the last turn, line 3 is activity. The layout config still holds
# ONE ordered block list; the group decides the row, so hide/show/move keep
# working without a second ordering knob.
LINE1_BLOCKS = frozenset(('cwd_git', 'model', 'effort', 'context_bar',
                          'compact_periodic', 'time', 'credits'))
LINE2_BLOCKS = frozenset(('requests', 'tokens', 'recent', 'speed'))



def _recent_calls_layout(width, head_parts, count, max_total=None):
    """Return (how many recent calls to show, per-call summary budget).

    Recent calls used to be a fixed 60 columns each, which pushed line 3 far
    past the terminal and truncated the last call anyway. Here the remaining
    width is shared: all calls shrink together, and only when even the floor
    does not fit do we drop the oldest ones (newest-first is more useful).

    *max_total* caps the whole row (the caller passes line 2's visible
    width) so line 3 stays roughly as wide as the row above instead of
    stretching with the terminal. A small floor keeps two calls visible
    when line 2 is narrower than the tools segment.
    """
    if width <= 0 or count <= 0:
        return count, RECENT_CALLS_ENTRY_MAX

    used = _visible_len(' | '.join(head_parts))
    avail = (width - 2) - used - (3 if used else 0)
    if avail <= 0:
        return 0, 0
    if max_total:
        cap = max_total - used - (3 if used else 0)
        avail = min(avail, max(cap, 2 * RECENT_CALLS_ENTRY_MIN + 3))

    per_call = (avail - 3 * (count - 1)) // count
    if per_call >= RECENT_CALLS_ENTRY_MIN:
        return count, min(RECENT_CALLS_ENTRY_MAX, per_call)

    fit = (avail + 3) // (RECENT_CALLS_ENTRY_MIN + 3)
    return max(1, min(count, fit)), RECENT_CALLS_ENTRY_MIN


def build_statusline(input_data, stats_dict, recent_rate=None):
    """Assemble the three-line statusline output from the parsed stats.

    Line 1: where/what + session clock — cwd+git (with line changes), model,
    effort, context bar, compact count, time, credits.
    Line 2: session totals + last turn — requests, tokens, recent, avg rate.
    Line 3: activity — tool counts, most recent calls.

    The block list comes from the layout config (resolve_layout); each block
    belongs to a fixed group, so custom order/hide still apply while the three
    rows stay balanced. Null-safe: model/cost/context_window may be missing.

    *recent_rate* (tokens/s or None) is the delta-based recent throughput
    shown inside the line-2 'recent' block; the entry point computes it from
    the previous invocation.
    """
    layout = resolve_layout(load_layout_config())
    width = get_statusline_width_from_input(input_data)

    # The recent block reads the entry-point-computed rate; inject it into a
    # shallow copy so every renderer keeps the (input_data, stats_dict)
    # signature and the caller's dict is never mutated.
    stats_dict = dict(stats_dict)
    stats_dict['recent_rate'] = recent_rate

    line1 = []
    line2 = []
    for block_id in layout['line1_order']:
        renderer = RENDERERS.get(block_id)
        if renderer is None:
            continue
        block = renderer(input_data, stats_dict)
        if not block:
            continue
        if block_id in LINE1_BLOCKS:
            line1.append(block)
        elif block_id in LINE2_BLOCKS:
            line2.append(block)

    # Line 3: tool counts and recent calls share one row (the Recent block
    # moved to line 2).
    activity = []
    if layout['tools']:
        tool_str = format_tools(stats_dict.get('tool_counts', {}),
                                stats_dict.get('running_agents', 0))
        if tool_str:
            activity.append(f"{DIM}Tools:{NC} {tool_str}")
    line2_str = ' | '.join(line2)
    if layout['recent']:
        calls = stats_dict.get('recent_calls') or []
        if calls:
            # Collapse back-to-back repeats first: fewer entries means
            # more budget each, and ×N says the same thing in less space.
            merged = _merge_repeat_calls(calls)
            # Cap the row at line 2's width so line 3 never stretches with
            # the terminal; the row above is the natural yardstick.
            shown, budget = _recent_calls_layout(
                width, activity, len(merged),
                max_total=_visible_len(line2_str))
            # Keep the newest calls when the terminal is too narrow for all.
            calls_str = format_recent_calls(
                merged[-shown:] if shown else [], budget)
            if calls_str:
                activity.append(calls_str)

    lines = [' | '.join(line1), line2_str, ' | '.join(activity)]
    output = '\n'.join(line for line in lines if line)

    # Truncate each line to the terminal width so the renderer never wraps a
    # line and squeezes the rows below out of view. Width comes from stdin
    # (`terminal_width`, no host sends it yet), COLUMNS (Claude Code), or
    # /dev/tty (CodeBuddy); 0 means no source, so skip truncation entirely.
    if width > 0:
        output = '\n'.join(
            truncate_to_width(line, max(20, width - 2))
            for line in output.split('\n')
        )

    return output
