#!/usr/bin/env python3
"""Write the statusLine command into the host settings.json.

Runs from /statusline:setup. Works for both hosts: the target file is
~/.codebuddy/settings.json or ~/.claude/settings.json, chosen from --host,
the plugin-root environment variables, or where this script is installed.
Idempotent: the same target changes nothing; after a plugin upgrade the
versioned path changes and the command is rewritten.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hostinfo


def resolve_root(host, explicit=''):
    """Plugin root: explicit > env > newest cached version > dev checkout."""
    if explicit:
        return os.path.abspath(explicit)
    env_key = 'CLAUDE_PLUGIN_ROOT' if host == hostinfo.CLAUDE else 'CODEBUDDY_PLUGIN_ROOT'
    env_root = os.environ.get(env_key) or ''
    if env_root:
        return os.path.abspath(env_root)
    cached = hostinfo.newest_plugin_root(host)
    if cached:
        return cached
    here = os.path.dirname(os.path.abspath(__file__))
    dev = os.path.dirname(here)
    if os.path.isfile(os.path.join(dev, 'scripts', 'statusline.py')):
        return dev
    if os.path.isfile(os.path.join(here, 'statusline.py')):
        return os.path.dirname(here)
    return ''


def main(argv=None):
    parser = argparse.ArgumentParser(description='Configure the statusline command')
    parser.add_argument('--host', default='auto',
                        choices=['auto'] + list(hostinfo.HOSTS))
    parser.add_argument('--plugin-root', default='')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)

    host = args.host if args.host != 'auto' else hostinfo.detect({})
    root = resolve_root(host, args.plugin_root)
    script = os.path.join(root, 'scripts', 'statusline.py') if root else ''
    settings_path = hostinfo.settings_path(host)

    if not script or not os.path.isfile(script):
        print('statusline: cannot find scripts/statusline.py (root=%r).' % root,
              file=sys.stderr)
        print('Reinstall the plugin, or pass --plugin-root <plugin dir>.',
              file=sys.stderr)
        return 2

    settings = hostinfo.load_settings(settings_path)
    current = settings.get('statusLine')
    if not isinstance(current, dict):
        current = {}
    current_command = current.get('command', '')
    configured = hostinfo.same_target(current_command, script)

    if args.check:
        payload = {
            'host': host,
            'plugin_root': root,
            'script': script,
            'settings': settings_path,
            'command': current_command,
            'configured': configured,
            'stale': bool(current_command) and not configured,
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False))
        else:
            print('host:       %s' % host)
            print('plugin:     %s' % root)
            print('settings:   %s' % settings_path)
            print('configured: %s' % ('yes' if configured else 'no'))
            if payload['stale']:
                print('stale:      yes (statusLine points elsewhere; re-run setup)')
        return 0 if configured else 1

    if configured:
        if args.json:
            print(json.dumps({'host': host, 'changed': False, 'script': script,
                              'settings': settings_path}, ensure_ascii=False))
        else:
            print('statusline: already configured -> %s' % script)
        return 0

    if current_command and 'statusline' not in current_command.lower() and not args.force:
        print('statusline: %s already defines a different statusLine command:'
              % settings_path, file=sys.stderr)
        print('  %s' % current_command, file=sys.stderr)
        print('Refusing to overwrite it. Re-run with --force to replace.',
              file=sys.stderr)
        return 2

    command = hostinfo.build_command(sys.executable or 'python3', script)
    padding = current.get('padding')
    if not isinstance(padding, int):
        padding = 0
    settings['statusLine'] = {'type': 'command', 'command': command, 'padding': padding}
    hostinfo.write_settings(settings_path, settings)

    if args.json:
        print(json.dumps({'host': host, 'changed': True, 'script': script,
                          'settings': settings_path, 'command': command},
                         ensure_ascii=False))
    else:
        print('statusline: configured %s' % settings_path)
        print('  command: %s' % command)
        print('Restart the session to see the new statusline.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
