#!/usr/bin/env python3
"""Per-model token and credit report for a session transcript.

Reads the main transcript plus <session-dir>/subagents/*.jsonl and groups
usage by model with parsing.extract_usage, so the report matches what the
statusline accumulates. No monetary amount is printed.
"""

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hostinfo
import parsing


def format_tokens(value):
    if value >= 1000000:
        return '%d (%.1fM)' % (value, value / 1000000.0)
    if value >= 1000:
        return '%d (%.1fK)' % (value, value / 1000.0)
    return '%d' % value


def find_latest_transcript(host):
    base = os.path.join(hostinfo.config_root(host), 'projects')
    latest = ''
    latest_mtime = 0
    try:
        projects = os.listdir(base)
    except OSError:
        return ''
    for project in projects:
        project_dir = os.path.join(base, project)
        if not os.path.isdir(project_dir):
            continue
        for path in glob.glob(os.path.join(project_dir, '*.jsonl')):
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            if mtime > latest_mtime:
                latest_mtime = mtime
                latest = path
    return latest


def transcript_group(transcript_path):
    paths = [transcript_path]
    session_dir = (transcript_path[:-6] if transcript_path.endswith('.jsonl')
                   else transcript_path)
    sub_dir = os.path.join(session_dir, 'subagents')
    try:
        names = sorted(os.listdir(sub_dir))
    except OSError:
        names = []
    for name in names:
        if name.endswith('.jsonl'):
            paths.append(os.path.join(sub_dir, name))
    return paths


def collect(paths):
    totals = {}
    seen = set()
    for path in paths:
        try:
            handle = open(path, 'r', encoding='utf-8', errors='replace')
        except IOError:
            continue
        with handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                usage = parsing.extract_usage(entry)
                if usage is None:
                    continue
                if usage['input'] <= 0 and usage['output'] <= 0:
                    continue
                message_id = usage['message_id']
                if message_id:
                    if message_id in seen:
                        continue
                    seen.add(message_id)
                model = usage['model'] or 'unknown'
                acc = totals.get(model)
                if acc is None:
                    acc = totals[model] = {
                        'requests': 0, 'input': 0, 'output': 0,
                        'cache_read': 0, 'cache_write': 0,
                        'reasoning': 0, 'credits': 0.0,
                    }
                acc['requests'] += 1
                acc['input'] += usage['input']
                acc['output'] += usage['output']
                acc['cache_read'] += usage['cache_read']
                acc['cache_write'] += usage['cache_write']
                acc['reasoning'] += usage['reasoning']
                acc['credits'] += usage['credits']
    return totals


def print_report(totals, transcript_path):
    print('=' * 78)
    print('  Statusline - Token & Credit Report')
    print('  transcript: %s' % transcript_path)
    print('=' * 78)
    if not totals:
        print('  (no usage records found)')
        return

    total = {'requests': 0, 'input': 0, 'output': 0, 'cache_read': 0,
             'cache_write': 0, 'reasoning': 0, 'credits': 0.0}
    for model in sorted(totals):
        acc = totals[model]
        print('')
        print('  %s:' % model)
        print('    Requests:     %d' % acc['requests'])
        print('    Input:        %s' % format_tokens(acc['input']))
        print('    Output:       %s' % format_tokens(acc['output']))
        print('    Cache Read:   %s' % format_tokens(acc['cache_read']))
        if acc['cache_write']:
            print('    Cache Write:  %s' % format_tokens(acc['cache_write']))
        if acc['reasoning']:
            print('    Reasoning:    %s' % format_tokens(acc['reasoning']))
        if acc['credits']:
            print('    Credits:      %.2f' % acc['credits'])
        for key in total:
            total[key] += acc[key]

    print('')
    print('-' * 78)
    print('  TOTALS:')
    print('    Requests:     %d' % total['requests'])
    print('    Input:        %s' % format_tokens(total['input']))
    print('    Output:       %s' % format_tokens(total['output']))
    print('    Cache Read:   %s' % format_tokens(total['cache_read']))
    if total['cache_write']:
        print('    Cache Write:  %s' % format_tokens(total['cache_write']))
    if total['reasoning']:
        print('    Reasoning:    %s' % format_tokens(total['reasoning']))
    if total['credits']:
        print('    Credits:      %.2f' % total['credits'])
        print('    (transcript only: image/video generation and team_member')
        print('     credits are not recorded here, so this can be lower than')
        print('     the host WebUI per-turn total.)')
    print('=' * 78)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Token and credit report')
    parser.add_argument('--host', default='auto',
                        choices=['auto'] + list(hostinfo.HOSTS))
    parser.add_argument('--transcript', default='')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)

    host = args.host if args.host != 'auto' else hostinfo.detect({})
    transcript_path = args.transcript
    if not transcript_path and not sys.stdin.isatty():
        try:
            data = json.load(sys.stdin)
        except ValueError:
            data = {}
        if isinstance(data, dict):
            transcript_path = data.get('transcript_path', '') or ''
    if not transcript_path or not os.path.isfile(transcript_path):
        transcript_path = find_latest_transcript(host)
    if not transcript_path:
        print('statusline: no transcript found for host %s' % host,
              file=sys.stderr)
        return 2

    totals = collect(transcript_group(transcript_path))
    if args.json:
        print(json.dumps({'transcript': transcript_path, 'models': totals},
                         indent=2, ensure_ascii=False))
    else:
        print_report(totals, transcript_path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
