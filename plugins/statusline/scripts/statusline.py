#!/usr/bin/env python3
"""Claude Code 状态行 - 显示模型、上下文、目录、分支等信息"""

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

PROGRESS_BAR_WIDTH = 10


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


def build_progress_bar(pct, ctx_size=None):
    filled = pct * PROGRESS_BAR_WIDTH // 100
    bar = '▓' * filled + '░' * (PROGRESS_BAR_WIDTH - filled)
    pct_display = f"{pct}%/{format_context_size(ctx_size)}" if ctx_size else f"{pct}%"

    if pct >= 80:
        return f"{RED}{bar} {pct_display}{RESET}"
    elif pct >= 50:
        return f"{YELLOW}{bar} {pct_display}{RESET}"
    return f"{GREEN}{bar} {pct_display}{RESET}"


def get_git_branch(session_id, cache_max_age=5):
    cache_file = f"/tmp/statusline-git-cache-{session_id}"

    # 检查缓存是否有效
    try:
        mtime = os.path.getmtime(cache_file)
        if time.time() - mtime <= cache_max_age:
            with open(cache_file) as f:
                return f.read().strip()
    except OSError:
        pass

    # 单次 git 命令获取分支
    try:
        branch = subprocess.check_output(
            ['git', 'symbolic-ref', '--short', 'HEAD'],
            text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        branch = ''

    with open(cache_file, 'w') as f:
        f.write(branch)
    return branch


def get_directory(data, max_levels=2):
    current_dir = data.get('workspace', {}).get('current_dir', '')
    if not current_dir:
        return ''
    parts = current_dir.rstrip('/').split('/')
    return '/'.join(parts[-max_levels:])


def get_token_display(data):
    ctx = data.get('context_window', {})
    in_tokens = ctx.get('total_input_tokens', 0) or 0
    out_tokens = ctx.get('total_output_tokens', 0) or 0
    return f"{CYAN}In: {in_tokens}, Out: {out_tokens}{RESET}"


def get_duration(data):
    duration_ms = data.get('cost', {}).get('total_duration_ms', 0) or 0
    duration_sec = duration_ms // 1000
    mins, secs = duration_sec // 60, duration_sec % 60
    return f"{MAGENTA}{mins}m{secs}s{RESET}"


def get_model_short(data):
    display_name = data.get('model', {}).get('display_name', '')
    return f"{BRIGHT_MAGENTA}{display_name}{RESET}" if display_name else ''


def build_statusline(data):
    session_id = data.get('session_id', 'default')
    ctx_pct = get_context_percentage(data)
    ctx_size = get_context_size(data)
    ctx_bar = build_progress_bar(ctx_pct, ctx_size=ctx_size)
    model = get_model_short(data)
    directory = get_directory(data)
    branch = get_git_branch(session_id)
    effort = data.get('effort', {}).get('level', '')
    tokens = get_token_display(data)
    duration = get_duration(data)

    parts = []
    if model:
        parts.append(model)
    parts.append(ctx_bar)
    if directory:
        parts.append(f"{BLUE}{directory}{RESET}")
    if branch:
        parts.append(f"{CYAN}{branch}{RESET}")
    if effort:
        parts.append(f"{YELLOW}{effort}{RESET}")
    parts.append(tokens)
    parts.append(duration)

    return ' | '.join(parts)


def main():
    try:
        data = json.load(sys.stdin)
        print(build_statusline(data))
    except Exception as e:
        print(f"statusline error: {e}")


if __name__ == '__main__':
    main()