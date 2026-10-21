#!/usr/bin/env python3
"""Remove the statusLine entry written by setup-statusline.py.

Leaves the runtime cache and the layout config in place: both are harmless
once the statusline no longer runs.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hostinfo


def main(argv=None):
    parser = argparse.ArgumentParser(description='Remove the statusLine entry')
    parser.add_argument('--host', default='auto',
                        choices=['auto'] + list(hostinfo.HOSTS))
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args(argv)

    host = args.host if args.host != 'auto' else hostinfo.detect({})
    path = hostinfo.settings_path(host)
    settings = hostinfo.load_settings(path)
    current = settings.get('statusLine')
    command = current.get('command', '') if isinstance(current, dict) else ''

    if not command:
        print('statusline: %s has no statusLine entry' % path)
        return 0
    if 'statusline' not in command.lower() and not args.force:
        print('statusline: %s points at another command, leaving it alone:' % path,
              file=sys.stderr)
        print('  %s' % command, file=sys.stderr)
        print('Re-run with --force to remove it anyway.', file=sys.stderr)
        return 2

    del settings['statusLine']
    hostinfo.write_settings(path, settings)
    print('statusline: removed from %s' % path)
    print('  was: %s' % command)
    print('Layout config and cache were left untouched.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
