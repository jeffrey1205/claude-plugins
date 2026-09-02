#!/usr/bin/env python3
"""Claude Code 状态行 - 显示模型、上下文、目录、分支、工具活动等信息"""

import json
import sys
import subprocess
import os
import time
from datetime import datetime, timezone

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
SPEED_CACHE_TTL = 2
SPEED_MIN_DELTA_MS = 500
PROMPT_CACHE_TTL_SECONDS = 300


# ---------------------------------------------------------------------------
# Context window helpers
# ---------------------------------------------------------------------------

def get_context_size(data):
    try:
        return data.get('context_window', {}).get('context_window_size', 200000) or 200000
    except Exception:
        return 200000


def get_context_percentage(data):
    try:
        return int(data.get('context_window', {}).get('used_percentage', 0) or 0)
    except Exception:
        return 0


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

    try:
        with open(cache_file, 'w') as f:
            json.dump(result, f)
    except OSError:
        pass
    return result


# ---------------------------------------------------------------------------
# Directory
# ---------------------------------------------------------------------------

def get_directory(data, max_levels=2):
    try:
        current_dir = data.get('workspace', {}).get('current_dir', '')
        if not current_dir:
            return ''
        parts = current_dir.rstrip('/').split('/')
        return '/'.join(parts[-max_levels:])
    except Exception:
        return ''


# ---------------------------------------------------------------------------
# Token display
# ---------------------------------------------------------------------------

def get_token_display(data, transcript):
    tokens = transcript.get('session_tokens', {})
    in_tokens = tokens.get('input', 0) + tokens.get('cache_read', 0) + tokens.get('cache_creation', 0)
    out_tokens = tokens.get('output', 0)

    if in_tokens == 0 and out_tokens == 0:
        try:
            ctx = data.get('context_window', {})
            in_tokens = ctx.get('total_input_tokens', 0) or 0
            out_tokens = ctx.get('total_output_tokens', 0) or 0
        except Exception:
            pass

    return f"In: {format_tokens(in_tokens)}, Out: {format_tokens(out_tokens)}"


# ---------------------------------------------------------------------------
# Sub-agent Token Tracking (Isolated & Incremental with Map-based Overwrite)
# ---------------------------------------------------------------------------

def get_subagent_tokens(data, transcript):
    transcript_path = data.get('transcript_path', '')
    if not transcript_path:
        return {'input': 0, 'output': 0}

    session_dir = os.path.dirname(transcript_path)
    subagents_dir = os.path.join(session_dir, 'subagents')
    if not os.path.isdir(subagents_dir):
        return {'input': 0, 'output': 0}

    session_id = data.get('session_id', 'default')
    total_sub_in = 0
    total_sub_out = 0

    try:
        files = os.listdir(subagents_dir)
    except OSError:
        return {'input': 0, 'output': 0}

    for filename in files:
        if not filename.endswith('.jsonl'):
            continue
        subagent_path = os.path.join(subagents_dir, filename)
        if not os.path.isfile(subagent_path):
            continue

        agent_id = filename[:-6]
        cache_file = f"/tmp/statusline-subagent-cache-{session_id}-{agent_id}"

        try:
            st = os.stat(subagent_path)
            curr_mtime = st.st_mtime
            curr_size = st.st_size
        except OSError:
            continue

        cached = None
        try:
            with open(cache_file, 'r') as f:
                cached = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass

        if cached and cached.get('mtime') == curr_mtime and cached.get('size') == curr_size:
            sub_tokens = cached.get('tokens', {'input': 0, 'output': 0})
            total_sub_in += sub_tokens.get('input', 0)
            total_sub_out += sub_tokens.get('output', 0)
            continue

        last_offset = 0
        message_usages = {}
        non_id_tokens = {'input': 0, 'output': 0}

        if cached and curr_size >= cached.get('size', 0) and cached.get('mtime', 0) <= curr_mtime:
            last_offset = cached.get('offset', 0)
            message_usages = cached.get('message_usages', {})
            non_id_tokens = cached.get('non_id_tokens', {'input': 0, 'output': 0})

        final_offset = last_offset
        try:
            with open(subagent_path, 'r', errors='replace') as f:
                if last_offset > 0:
                    f.seek(last_offset)
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if not isinstance(entry, dict):
                        continue

                    if entry.get('type') == 'assistant':
                        msg = entry.get('message', {})
                        if isinstance(msg, dict):
                            msg_id = msg.get('id')
                            usage = msg.get('usage')
                            if usage and isinstance(usage, dict):
                                inp = usage.get('input_tokens', 0) or 0
                                out = usage.get('output_tokens', 0) or 0
                                if msg_id:
                                    message_usages[msg_id] = {'input': inp, 'output': out}
                                else:
                                    non_id_tokens['input'] += inp
                                    non_id_tokens['output'] += out
                final_offset = f.tell()
        except Exception:
            pass

        sub_in = sum(u['input'] for u in message_usages.values()) + non_id_tokens['input']
        sub_out = sum(u['output'] for u in message_usages.values()) + non_id_tokens['output']
        sub_tokens = {'input': sub_in, 'output': sub_out}

        cache_payload = {
            'mtime': curr_mtime,
            'size': curr_size,
            'offset': final_offset,
            'tokens': sub_tokens,
            'message_usages': message_usages,
            'non_id_tokens': non_id_tokens
        }
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache_payload, f)
        except OSError:
            pass

        total_sub_in += sub_in
        total_sub_out += sub_out

    return {'input': total_sub_in, 'output': total_sub_out}


# ---------------------------------------------------------------------------
# Duration
# ---------------------------------------------------------------------------

def get_duration(data):
    try:
        duration_ms = data.get('cost', {}).get('total_duration_ms', 0) or 0
        duration_sec = duration_ms // 1000
        mins, secs = duration_sec // 60, duration_sec % 60
        return f"{mins}m {secs}s"
    except Exception:
        return "0m 0s"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def get_model_short(data):
    try:
        display_name = data.get('model', {}).get('display_name', '')
        return display_name if display_name else ''
    except Exception:
        return ''


# ---------------------------------------------------------------------------
# Transcript Incremental JSONL parsing (Map-based Overwrite Dedup)
# ---------------------------------------------------------------------------

def parse_transcript(transcript_path, session_id):
    empty_result = {
        'tools': [], 'agents': 0, 'todos': [],
        'session_tokens': {'input': 0, 'output': 0, 'cache_creation': 0, 'cache_read': 0},
        'last_assistant_at': None, 'tool_counts': {}
    }

    if not transcript_path or not os.path.isfile(transcript_path):
        return empty_result

    try:
        st = os.stat(transcript_path)
        curr_mtime = st.st_mtime
        curr_size = st.st_size
    except OSError:
        return empty_result

    cache_file = f"/tmp/statusline-transcript-cache-{session_id}"

    cached = None
    try:
        with open(cache_file, 'r') as f:
            cached = json.load(f)
    except (OSError, json.JSONDecodeError):
        pass

    if cached and cached.get('mtime') == curr_mtime and cached.get('size') == curr_size:
        return cached.get('result', empty_result)

    last_offset = 0
    running_tools = {}
    tool_counts = {}
    agent_ids = set()
    message_usages = {}
    non_id_tokens = {'input': 0, 'output': 0, 'cache_creation': 0, 'cache_read': 0}
    latest_todos = []
    result = {
        'tools': [],
        'agents': 0,
        'todos': [],
        'session_tokens': {'input': 0, 'output': 0, 'cache_creation': 0, 'cache_read': 0},
        'last_assistant_at': None,
    }

    if cached and curr_size >= cached.get('size', 0) and cached.get('mtime', 0) <= curr_mtime:
        last_offset = cached.get('offset', 0)
        running_tools = cached.get('running_tools', {})
        tool_counts = cached.get('tool_counts', {})
        agent_ids = set(cached.get('agent_ids', []))
        message_usages = cached.get('message_usages', {})
        non_id_tokens = cached.get('non_id_tokens', {'input': 0, 'output': 0, 'cache_creation': 0, 'cache_read': 0})
        latest_todos = cached.get('todos', [])
        result['last_assistant_at'] = cached.get('last_assistant_at')

    final_offset = last_offset
    try:
        with open(transcript_path, 'r', errors='replace') as f:
            if last_offset > 0:
                f.seek(last_offset)

            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if not isinstance(entry, dict):
                    continue

                if entry.get('type') == 'assistant' and entry.get('timestamp'):
                    result['last_assistant_at'] = entry.get('timestamp')

                if entry.get('type') == 'assistant':
                    msg = entry.get('message', {})
                    if isinstance(msg, dict):
                        msg_id = msg.get('id')
                        usage = msg.get('usage')

                        if usage and isinstance(usage, dict):
                            inp = usage.get('input_tokens', 0) or 0
                            out = usage.get('output_tokens', 0) or 0
                            cc = usage.get('cache_creation_input_tokens', 0) or 0
                            cr = usage.get('cache_read_input_tokens', 0) or 0

                            if msg_id:
                                message_usages[msg_id] = {
                                    'input': inp,
                                    'output': out,
                                    'cache_creation': cc,
                                    'cache_read': cr
                                }
                            else:
                                non_id_tokens['input'] += inp
                                non_id_tokens['output'] += out
                                non_id_tokens['cache_creation'] += cc
                                non_id_tokens['cache_read'] += cr

                content = entry.get('message', {}).get('content')
                if not content or not isinstance(content, list):
                    continue

                for block in content:
                    if not isinstance(block, dict):
                        continue

                    block_type = block.get('type')
                    if block_type == 'tool_use' and block.get('id') and block.get('name'):
                        name = block['name']
                        tool_input = block.get('input') or {}

                        if name in ('Agent', 'Task'):
                            agent_ids.add(block['id'])
                            continue
                        if name in ('TodoWrite', 'TaskCreate', 'TaskUpdate'):
                            continue

                        target = _extract_target(name, tool_input)
                        running_tools[block['id']] = {
                            'name': name,
                            'target': target,
                        }

                    if block_type == 'tool_result' and block.get('tool_use_id'):
                        tool_id = block['tool_use_id']
                        if tool_id in running_tools:
                            tool_info = running_tools.pop(tool_id)
                            name = tool_info['name']
                            tool_counts[name] = tool_counts.get(name, 0) + 1
                        if tool_id in agent_ids:
                            agent_ids.discard(tool_id)

                    if block_type == 'tool_use' and block.get('name') == 'TodoWrite':
                        todos = (block.get('input') or {}).get('todos')
                        if isinstance(todos, list):
                            latest_todos = [
                                {'content': t.get('content', ''), 'status': t.get('status', 'pending')}
                                for t in todos if isinstance(t, dict)
                            ]

            final_offset = f.tell()
    except Exception:
        final_offset = last_offset

    total_session_tokens = {'input': 0, 'output': 0, 'cache_creation': 0, 'cache_read': 0}
    for u in message_usages.values():
        total_session_tokens['input'] += u['input']
        total_session_tokens['output'] += u['output']
        total_session_tokens['cache_creation'] += u['cache_creation']
        total_session_tokens['cache_read'] += u['cache_read']
    total_session_tokens['input'] += non_id_tokens['input']
    total_session_tokens['output'] += non_id_tokens['output']
    total_session_tokens['cache_creation'] += non_id_tokens['cache_creation']
    total_session_tokens['cache_read'] += non_id_tokens['cache_read']

    result['session_tokens'] = total_session_tokens
    result['tools'] = list(running_tools.values())[-3:]
    result['tool_counts'] = dict(sorted(tool_counts.items(), key=lambda x: -x[1])[:5])
    result['agents'] = len(agent_ids)
    result['todos'] = latest_todos

    cache_payload = {
        'mtime': curr_mtime,
        'size': curr_size,
        'offset': final_offset,
        'session_tokens': total_session_tokens,
        'running_tools': running_tools,
        'tool_counts': tool_counts,
        'agent_ids': list(agent_ids),
        'message_usages': message_usages,
        'non_id_tokens': non_id_tokens,
        'todos': latest_todos,
        'last_assistant_at': result['last_assistant_at'],
        'result': result
    }

    try:
        with open(cache_file, 'w') as f:
            json.dump(cache_payload, f)
    except OSError:
        pass

    return result


def _extract_target(tool_name, tool_input):
    if not isinstance(tool_input, dict):
        return None
    try:
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
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Output speed tracking
# ---------------------------------------------------------------------------

def get_output_speed(data, session_id):
    try:
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
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Prompt cache TTL
# ---------------------------------------------------------------------------

def get_prompt_cache_ttl(transcript_data):
    last_at = transcript_data.get('last_assistant_at')
    if not last_at:
        return None

    try:
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
    try:
        tokens = transcript_data.get('session_tokens', {})
        input_tokens = tokens.get('input', 0)
        cache_read = tokens.get('cache_read', 0)
        cache_creation = tokens.get('cache_creation', 0)

        total_input = input_tokens + cache_read + cache_creation
        if total_input <= 0:
            return None

        hit_rate = cache_read / total_input
        return f"{int(hit_rate * 100)}%"
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Build statusline
# ---------------------------------------------------------------------------

def build_statusline(data):
    session_id = data.get('session_id', 'default')
    transcript_path = data.get('transcript_path', '')

    transcript = parse_transcript(transcript_path, session_id)
    sub_tokens = get_subagent_tokens(data, transcript)

    ctx_pct = get_context_percentage(data)
    ctx_size = get_context_size(data)
    ctx_bar = build_progress_bar(ctx_pct, ctx_size=ctx_size)
    model = get_model_short(data)
    directory = get_directory(data)
    git_info = get_git_info(session_id)

    try:
        effort = data.get('effort', {}).get('level', '')
    except Exception:
        effort = ''

    tokens = get_token_display(data, transcript)
    duration = get_duration(data)

    speed = get_output_speed(data, session_id)
    cache_ttl = get_prompt_cache_ttl(transcript)
    cache_hit = get_cache_hit_rate(transcript)

    # Line 1: model+effort | context bar | directory | git
    line1_parts = []
    if model:
        model_display = f"{BRIGHT_MAGENTA}{model}{RESET}"
        if effort:
            model_display += f" {BRIGHT_MAGENTA}{effort}{RESET}"
        line1_parts.append(model_display)
    line1_parts.append(ctx_bar)
    if directory:
        line1_parts.append(f"{BLUE}{directory}{RESET}")
    if git_info.get('branch'):
        git_str = f"{CYAN}{git_info['branch']}{RESET}"
        if git_info.get('staged', 0) > 0:
            git_str += f" {GREEN}+{git_info['staged']}{RESET}"
        if git_info.get('modified', 0) > 0:
            git_str += f" {YELLOW}~{git_info['modified']}{RESET}"
        line1_parts.append(git_str)

    # Line 2: tokens | subagent tokens (if active) | duration | cache ttl | cache hit | speed
    line2_parts = []
    line2_parts.append(f"{CYAN}{tokens}{RESET}")

    if sub_tokens['input'] > 0 or sub_tokens['output'] > 0:
        sub_str = f"Sub: In: {format_tokens(sub_tokens['input'])}, Out: {format_tokens(sub_tokens['output'])}"
        line2_parts.append(f"{MAGENTA}{sub_str}{RESET}")

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
    for tool in transcript.get('tools', []):
        target = f": {tool['target']}" if tool.get('target') else ''
        line3_parts.append(f"{YELLOW}{tool['name']}{target}{RESET}")
    for name, count in transcript.get('tool_counts', {}).items():
        line3_parts.append(f"{GREEN}{name} x{count}{RESET}")

    in_progress = None
    completed_count = 0
    todos = transcript.get('todos', [])
    for t in todos:
        if t.get('status') == 'in_progress':
            in_progress = t
        if t.get('status') == 'completed':
            completed_count += 1
    if in_progress:
        total = len(todos)
        content = in_progress.get('content', '')
        if len(content) > 40:
            content = content[:37] + '...'
        line3_parts.append(f"Todo: {content} ({completed_count}/{total})")

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
