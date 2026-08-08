#!/usr/bin/env python3
"""Claude Code 状态行 - 显示模型、上下文、目录、分支、工具活动等信息"""

import json
import sys
import subprocess
import os
import time

RESET = '\033[0m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
RED = '\033[31m'
BLUE = '\033[34m'
MAGENTA = '\033[35m'
CYAN = '\033[36m'
BRIGHT_MAGENTA = '\033[95m'
DIM = '\033[2m'

PROGRESS_BAR_WIDTH = 10
TRANSCRIPT_CACHE_TTL = 5
SPEED_CACHE_TTL = 2
SPEED_MIN_DELTA_MS = 500
PROMPT_CACHE_TTL_SECONDS = 300


# ---------------------------------------------------------------------------
# Context window helpers
# ---------------------------------------------------------------------------

def get_context_size(data):
    return data.get('context_window', {}).get('context_window_size', 200000) or 200000


def get_context_percentage(data):
    return int(data.get('context_window', {}).get('used_percentage', 0) or 0)


def format_context_size(size):
    if size >= 1000000:
        return f"{size // 1000000}M"
    elif size >= 1000:
        return f"{size // 1000}K"
    return str(size)


def format_tokens(n):
    if n >= 1000000:
        return f"{n / 1000000:.1f}M"
    elif n >= 1000:
        return f"{n / 1000:.1f}K"
    return str(n)


def build_progress_bar(pct, ctx_size=None):
    filled = pct * PROGRESS_BAR_WIDTH // 100
    bar = '\u2593' * filled + '\u2591' * (PROGRESS_BAR_WIDTH - filled)
    pct_display = f"{pct}%/{format_context_size(ctx_size)}" if ctx_size else f"{pct}%"

    if pct >= 80:
        return f"{RED}{bar} {pct_display}{RESET}"
    elif pct >= 50:
        return f"{YELLOW}{bar} {pct_display}{RESET}"
    return f"{GREEN}{bar} {pct_display}{RESET}"


# ---------------------------------------------------------------------------
# Git info
# ---------------------------------------------------------------------------

def get_git_info(session_id, cache_max_age=5):
    cache_file = f"/tmp/statusline-git-cache-{session_id}"

    try:
        mtime = os.path.getmtime(cache_file)
        if time.time() - mtime <= cache_max_age:
            with open(cache_file) as f:
                return json.load(f)
    except (OSError, json.JSONDecodeError):
        pass

    result = {'branch': '', 'staged': 0, 'modified': 0}

    try:
        output = subprocess.check_output(
            ['git', 'status', '--porcelain', '-b'],
            text=True, stderr=subprocess.DEVNULL
        ).strip().split('\n')

        for line in output:
            if line.startswith('## '):
                result['branch'] = line[3:].split('...')[0]
            elif line:
                code = line[:2]
                if code[0] != ' ' and code[0] != '?':
                    result['staged'] += 1
                if code[1] != ' ':
                    result['modified'] += 1
    except Exception:
        pass

    with open(cache_file, 'w') as f:
        json.dump(result, f)
    return result


# ---------------------------------------------------------------------------
# Directory
# ---------------------------------------------------------------------------

def get_directory(data, max_levels=2):
    current_dir = data.get('workspace', {}).get('current_dir', '')
    if not current_dir:
        return ''
    parts = current_dir.rstrip('/').split('/')
    return '/'.join(parts[-max_levels:])


# ---------------------------------------------------------------------------
# Token display
# ---------------------------------------------------------------------------

def get_token_display(data):
    ctx = data.get('context_window', {})
    in_tokens = ctx.get('total_input_tokens', 0) or 0
    out_tokens = ctx.get('total_output_tokens', 0) or 0
    return f"In: {format_tokens(in_tokens)}, Out: {format_tokens(out_tokens)}"


# ---------------------------------------------------------------------------
# Duration
# ---------------------------------------------------------------------------

def get_duration(data):
    duration_ms = data.get('cost', {}).get('total_duration_ms', 0) or 0
    duration_sec = duration_ms // 1000
    mins, secs = duration_sec // 60, duration_sec % 60
    return f"{mins}m {secs}s"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def get_model_short(data):
    display_name = data.get('model', {}).get('display_name', '')
    return display_name if display_name else ''


# ---------------------------------------------------------------------------
# Transcript JSONL parsing
# ---------------------------------------------------------------------------

def _read_transcript_cache(session_id):
    cache_file = f"/tmp/statusline-transcript-cache-{session_id}"
    try:
        mtime = os.path.getmtime(cache_file)
        if time.time() - mtime <= TRANSCRIPT_CACHE_TTL:
            with open(cache_file) as f:
                return json.load(f)
    except (OSError, json.JSONDecodeError):
        pass
    return None


def _write_transcript_cache(session_id, data):
    cache_file = f"/tmp/statusline-transcript-cache-{session_id}"
    try:
        with open(cache_file, 'w') as f:
            json.dump(data, f)
    except OSError:
        pass


def parse_transcript(transcript_path, session_id):
    cached = _read_transcript_cache(session_id)
    if cached is not None:
        return cached

    result = {
        'tools': [],
        'agents': 0,
        'todos': [],
        'session_tokens': {'input': 0, 'cache_creation': 0, 'cache_read': 0},
        'last_assistant_at': None,
    }

    if not transcript_path or not os.path.isfile(transcript_path):
        _write_transcript_cache(session_id, result)
        return result

    tool_map = {}
    agent_ids = set()
    latest_todos = []
    seen_usage_keys = set()

    try:
        with open(transcript_path, 'r', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Track last assistant response time
                if entry.get('type') == 'assistant' and entry.get('timestamp'):
                    result['last_assistant_at'] = entry['timestamp']

                # Accumulate session tokens from assistant messages
                if entry.get('type') == 'assistant':
                    msg = entry.get('message', {})
                    usage = msg.get('usage')
                    if usage and isinstance(usage, dict):
                        usage_key = (
                            usage.get('input_tokens', 0),
                            usage.get('output_tokens', 0),
                            usage.get('cache_creation_input_tokens', 0),
                            usage.get('cache_read_input_tokens', 0),
                        )
                        if usage_key not in seen_usage_keys:
                            seen_usage_keys.add(usage_key)
                            result['session_tokens']['input'] += usage.get('input_tokens', 0) or 0
                            result['session_tokens']['cache_creation'] += usage.get('cache_creation_input_tokens', 0) or 0
                            result['session_tokens']['cache_read'] += usage.get('cache_read_input_tokens', 0) or 0

                content = entry.get('message', {}).get('content')
                if not content or not isinstance(content, list):
                    continue

                for block in content:
                    if not isinstance(block, dict):
                        continue

                    # Track tool_use
                    if block.get('type') == 'tool_use' and block.get('id') and block.get('name'):
                        name = block['name']
                        tool_input = block.get('input') or {}

                        # Skip Agent/Task/TodoWrite/TaskCreate/TaskUpdate
                        if name in ('Agent', 'Task'):
                            agent_ids.add(block['id'])
                            continue
                        if name in ('TodoWrite', 'TaskCreate', 'TaskUpdate'):
                            continue

                        target = _extract_target(name, tool_input)
                        tool_map[block['id']] = {
                            'name': name,
                            'target': target,
                            'status': 'running',
                        }

                    # Track tool_result (completion)
                    if block.get('type') == 'tool_result' and block.get('tool_use_id'):
                        tool_id = block['tool_use_id']
                        if tool_id in tool_map:
                            tool_map[tool_id]['status'] = 'completed' if not block.get('is_error') else 'error'
                        if tool_id in agent_ids:
                            agent_ids.discard(tool_id)

                    # Track todos
                    if block.get('type') == 'tool_use' and block.get('name') == 'TodoWrite':
                        todos = (block.get('input') or {}).get('todos')
                        if isinstance(todos, list):
                            latest_todos = [
                                {'content': t.get('content', ''), 'status': t.get('status', 'pending')}
                                for t in todos if isinstance(t, dict)
                            ]
    except Exception:
        pass

    # Build tools list (running first, then completed counts)
    running = [t for t in tool_map.values() if t['status'] == 'running']
    completed = [t for t in tool_map.values() if t['status'] in ('completed', 'error')]
    result['tools'] = running[-3:]  # last 3 running

    # Count completed by name
    tool_counts = {}
    for t in completed:
        tool_counts[t['name']] = tool_counts.get(t['name'], 0) + 1
    result['tool_counts'] = dict(sorted(tool_counts.items(), key=lambda x: -x[1])[:5])

    # Agent count (running = ids still in agent_ids)
    result['agents'] = len(agent_ids)

    # Todos
    result['todos'] = latest_todos

    _write_transcript_cache(session_id, result)
    return result


def _extract_target(tool_name, tool_input):
    if not isinstance(tool_input, dict):
        return None
    if tool_name in ('Read', 'Write', 'Edit'):
        path = tool_input.get('file_path') or tool_input.get('path')
        if path:
            return os.path.basename(path)
    elif tool_name == 'Glob':
        return tool_input.get('pattern')
    elif tool_name == 'Grep':
        return tool_input.get('pattern')
    elif tool_name == 'Bash':
        cmd = tool_input.get('command', '')
        if isinstance(cmd, str) and cmd.strip():
            cmd = cmd.strip().replace('\n', ' ')
            return cmd[:25] + '...' if len(cmd) > 25 else cmd
    return None


# ---------------------------------------------------------------------------
# Output speed tracking
# ---------------------------------------------------------------------------

def get_output_speed(data, session_id):
    output_tokens = (data.get('context_window', {}) or {}).get('current_usage', {}) or {}
    output_tokens = output_tokens.get('output_tokens')
    if not isinstance(output_tokens, (int, float)):
        return None

    cache_file = f"/tmp/statusline-speed-cache-{session_id}"
    now = time.time()

    try:
        with open(cache_file) as f:
            prev = json.load(f)
        prev_tokens = prev.get('tokens', 0)
        prev_time = prev.get('time', 0)
        delta_ms = (now - prev_time) * 1000

        if delta_ms > SPEED_CACHE_TTL * 1000 or delta_ms < SPEED_MIN_DELTA_MS:
            with open(cache_file, 'w') as f:
                json.dump({'tokens': output_tokens, 'time': now}, f)
            return None

        delta_tokens = output_tokens - prev_tokens
        if delta_tokens <= 0:
            with open(cache_file, 'w') as f:
                json.dump({'tokens': output_tokens, 'time': now}, f)
            return None

        speed = delta_tokens / (delta_ms / 1000)
        with open(cache_file, 'w') as f:
            json.dump({'tokens': output_tokens, 'time': now}, f)
        return speed
    except (OSError, json.JSONDecodeError):
        with open(cache_file, 'w') as f:
            json.dump({'tokens': output_tokens, 'time': now}, f)
        return None


# ---------------------------------------------------------------------------
# Prompt cache TTL
# ---------------------------------------------------------------------------

def get_prompt_cache_ttl(transcript_data):
    last_at = transcript_data.get('last_assistant_at')
    if not last_at:
        return None

    try:
        # Parse ISO timestamp
        from datetime import datetime, timezone
        ts = last_at.replace('Z', '+00:00')
        last_time = datetime.fromisoformat(ts).timestamp()
    except (ValueError, TypeError):
        return None

    now = time.time()
    remaining = (last_time + PROMPT_CACHE_TTL_SECONDS) - now
    if remaining <= 0:
        return "0m 0s"

    total_secs = int(remaining)
    mins, secs = total_secs // 60, total_secs % 60
    return f"{mins}m {secs}s"


# ---------------------------------------------------------------------------
# Cache hit rate
# ---------------------------------------------------------------------------

def get_cache_hit_rate(transcript_data):
    tokens = transcript_data.get('session_tokens', {})
    cache_read = tokens.get('cache_read', 0)
    cache_creation = tokens.get('cache_creation', 0)
    input_tokens = tokens.get('input', 0)

    total = cache_read + cache_creation + input_tokens
    if total <= 0:
        return None

    hit_rate = cache_read / total
    return f"{int(hit_rate * 100)}%"


# ---------------------------------------------------------------------------
# Build statusline
# ---------------------------------------------------------------------------

def build_statusline(data):
    session_id = data.get('session_id', 'default')
    transcript_path = data.get('transcript_path', '')

    # Parse transcript (cached)
    transcript = parse_transcript(transcript_path, session_id)

    # Existing fields
    ctx_pct = get_context_percentage(data)
    ctx_size = get_context_size(data)
    ctx_bar = build_progress_bar(ctx_pct, ctx_size=ctx_size)
    model = get_model_short(data)
    directory = get_directory(data)
    git_info = get_git_info(session_id)
    effort = data.get('effort', {}).get('level', '')
    tokens = get_token_display(data)
    duration = get_duration(data)

    # New fields
    speed = get_output_speed(data, session_id)
    cache_ttl = get_prompt_cache_ttl(transcript)
    cache_hit = get_cache_hit_rate(transcript)

    # Line 1: model | context bar | directory | git | effort
    line1_parts = []
    if model:
        line1_parts.append(f"{BRIGHT_MAGENTA}{model}{RESET}")
    line1_parts.append(ctx_bar)
    if directory:
        line1_parts.append(f"{BLUE}{directory}{RESET}")
    if git_info['branch']:
        git_str = f"{CYAN}{git_info['branch']}{RESET}"
        if git_info['staged'] > 0:
            git_str += f" {GREEN}+{git_info['staged']}{RESET}"
        if git_info['modified'] > 0:
            git_str += f" {YELLOW}~{git_info['modified']}{RESET}"
        line1_parts.append(git_str)
    if effort:
        line1_parts.append(f"{YELLOW}Effort: {effort}{RESET}")

    # Line 2: tokens | duration | cache ttl | cache hit | speed
    line2_parts = []
    line2_parts.append(f"{CYAN}{tokens}{RESET}")
    line2_parts.append(f"{MAGENTA}Duration: {duration}{RESET}")
    if cache_ttl is not None:
        ttl_color = GREEN if cache_ttl != "0m 0s" else DIM
        line2_parts.append(f"{ttl_color}TTL: {cache_ttl}{RESET}")
    if cache_hit is not None:
        line2_parts.append(f"{CYAN}Hit: {cache_hit}{RESET}")
    if speed is not None:
        line2_parts.append(f"{GREEN}Speed: {speed:.1f} tok/s{RESET}")

    # Line 3: tool activity | todos | agents
    line3_parts = []
    # Running tools
    for tool in transcript.get('tools', []):
        target = f": {tool['target']}" if tool.get('target') else ''
        line3_parts.append(f"{YELLOW}{tool['name']}{target}{RESET}")
    # Completed tool counts
    for name, count in transcript.get('tool_counts', {}).items():
        line3_parts.append(f"{GREEN}{name} x{count}{RESET}")
    # Todos
    in_progress = None
    completed_count = 0
    for t in transcript.get('todos', []):
        if t.get('status') == 'in_progress':
            in_progress = t
        if t.get('status') == 'completed':
            completed_count += 1
    if in_progress:
        total = len(transcript.get('todos', []))
        content = in_progress.get('content', '')
        if len(content) > 40:
            content = content[:37] + '...'
        line3_parts.append(f"Todo: {content} ({completed_count}/{total})")
    # Agent count
    agent_count = transcript.get('agents', 0)
    if agent_count > 0:
        line3_parts.append(f"Agents: {agent_count}")

    lines = []
    if line1_parts:
        lines.append(' | '.join(line1_parts))
    if line2_parts:
        lines.append(' | '.join(line2_parts))
    if line3_parts:
        lines.append(' | '.join(line3_parts))

    return '\n'.join(lines) if lines else ''


def main():
    try:
        data = json.load(sys.stdin)
        output = build_statusline(data)
        if output:
            print(output)
    except Exception as e:
        print(f"statusline error: {e}")


if __name__ == '__main__':
    main()
