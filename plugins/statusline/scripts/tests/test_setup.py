#!/usr/bin/env python3
"""setup-statusline.py behaviour."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SETUP = os.path.join(PLUGIN_ROOT, 'scripts', 'setup-statusline.py')


class SetupTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._cb = os.path.join(self._tmp, 'codebuddy')
        self._claude = os.path.join(self._tmp, 'claude')
        self._env = dict(os.environ,
                         CODEBUDDY_CONFIG_DIR=self._cb,
                         CLAUDE_CONFIG_DIR=self._claude,
                         STATUSLINE_TMPDIR=os.path.join(self._tmp, 'tmp'))
        self._env.pop('CODEBUDDY_PLUGIN_ROOT', None)
        self._env.pop('CLAUDE_PLUGIN_ROOT', None)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _run(self, args):
        return subprocess.run([sys.executable, SETUP] + args, env=self._env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=10)

    def _settings(self, host='codebuddy'):
        root = self._cb if host == 'codebuddy' else self._claude
        with open(os.path.join(root, 'settings.json'), 'r', encoding='utf-8') as handle:
            return json.load(handle)

    def _write_settings(self, payload, host='codebuddy'):
        root = self._cb if host == 'codebuddy' else self._claude
        os.makedirs(root, exist_ok=True)
        with open(os.path.join(root, 'settings.json'), 'w', encoding='utf-8') as handle:
            json.dump(payload, handle)

    def _old_root(self):
        root = os.path.join(self._tmp, 'old')
        os.makedirs(os.path.join(root, 'scripts'))
        open(os.path.join(root, 'scripts', 'statusline.py'), 'w').close()
        return root

    def test_creates_codebuddy_settings(self):
        result = self._run(['--host', 'codebuddy', '--plugin-root', PLUGIN_ROOT])
        self.assertEqual(result.returncode, 0, result.stderr)
        entry = self._settings()['statusLine']
        self.assertEqual(entry['type'], 'command')
        self.assertEqual(entry['padding'], 0)
        self.assertIn(os.path.join(PLUGIN_ROOT, 'scripts', 'statusline.py'),
                      entry['command'])
        self.assertIn('restart', result.stdout.lower())

    def test_idempotent(self):
        args = ['--host', 'codebuddy', '--plugin-root', PLUGIN_ROOT]
        self._run(args)
        second = self._run(args)
        self.assertEqual(second.returncode, 0)
        self.assertIn('already configured', second.stdout)

    def test_preserves_other_keys(self):
        self._write_settings({'model': 'x', 'statusLine': {'padding': 2}})
        self._run(['--host', 'codebuddy', '--plugin-root', PLUGIN_ROOT])
        payload = self._settings()
        self.assertEqual(payload['model'], 'x')
        self.assertEqual(payload['statusLine']['padding'], 2)

    def test_rewrites_stale_path(self):
        old = self._old_root()
        first = self._run(['--host', 'codebuddy', '--plugin-root', old])
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn(old, self._settings()['statusLine']['command'])
        second = self._run(['--host', 'codebuddy', '--plugin-root', PLUGIN_ROOT])
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn(PLUGIN_ROOT, self._settings()['statusLine']['command'])

    def test_refuses_foreign_command(self):
        self._write_settings({'statusLine': {'type': 'command', 'command': 'my-own.sh'}})
        result = self._run(['--host', 'codebuddy', '--plugin-root', PLUGIN_ROOT])
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._settings()['statusLine']['command'], 'my-own.sh')

    def test_force_replaces_foreign_command(self):
        self._write_settings({'statusLine': {'type': 'command', 'command': 'my-own.sh'}})
        result = self._run(['--host', 'codebuddy', '--plugin-root', PLUGIN_ROOT, '--force'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotEqual(self._settings()['statusLine']['command'], 'my-own.sh')

    def test_claude_target(self):
        result = self._run(['--host', 'claude', '--plugin-root', PLUGIN_ROOT])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self._claude, 'settings.json')))
        self.assertFalse(os.path.exists(os.path.join(self._cb, 'settings.json')))

    def test_check_reports_state(self):
        unchecked = self._run(['--host', 'codebuddy', '--plugin-root', PLUGIN_ROOT,
                               '--check', '--json'])
        self.assertEqual(unchecked.returncode, 1)
        payload = json.loads(unchecked.stdout)
        self.assertFalse(payload['configured'])
        self._run(['--host', 'codebuddy', '--plugin-root', PLUGIN_ROOT])
        checked = self._run(['--host', 'codebuddy', '--plugin-root', PLUGIN_ROOT,
                             '--check', '--json'])
        self.assertEqual(checked.returncode, 0)
        self.assertTrue(json.loads(checked.stdout)['configured'])

    def test_missing_script_reports_error(self):
        result = self._run(['--host', 'codebuddy', '--plugin-root', self._tmp])
        self.assertEqual(result.returncode, 2)
        self.assertIn('cannot find', result.stderr)


if __name__ == '__main__':
    unittest.main()
