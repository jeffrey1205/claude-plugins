#!/usr/bin/env python3
"""Cross-host parsing: CodeBuddy and Claude transcript dialects."""

import re
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hostinfo
import parsing
import stats

_ANSI = re.compile(r'\033\[[0-9;?]*[A-Za-z]')

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')


def _copy_fixture(name, target_dir):
    shutil.copy(os.path.join(FIXTURES, name), target_dir)
    source_side = os.path.join(FIXTURES, name[:-6], 'subagents')
    if os.path.isdir(source_side):
        dest_side = os.path.join(target_dir, name[:-6], 'subagents')
        shutil.copytree(source_side, dest_side)
    return os.path.join(target_dir, name)


class FixtureParse(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._orig_cache = stats.CACHE_DIR
        stats.CACHE_DIR = os.path.join(self._tmp, 'cache')

    def tearDown(self):
        stats.CACHE_DIR = self._orig_cache
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _parse(self, fixture, session_id):
        path = _copy_fixture(fixture, self._tmp)
        return parsing.parse_transcript_incremental(path, session_id)[0]

    def test_claude_totals(self):
        result = self._parse('claude_session.jsonl', 'cli-fixture')
        # In includes cache on both hosts: 100+200+300 for msg_1, 10 for msg_2,
        # 20 for msg_3, plus 7 from the sub-agent transcript.
        self.assertEqual(result['total_input'], 637)
        self.assertEqual(result['total_output'], 68)
        self.assertEqual(result['total_cache_read'], 300)
        self.assertEqual(result['total_cache_write'], 200)
        self.assertEqual(result['total_reasoning'], 0)
        self.assertEqual(result['total_credits'], 0)
        # msg_1 (duplicated line), msg_2, msg_3 + two sub-agent messages
        self.assertEqual(result['request_count'], 5)
        self.assertEqual(result['tool_counts'], {'Bash': 1, 'Agent': 1, 'Read': 1})
        # Both tool_use ids in the main transcript have a tool_result
        self.assertEqual(result['running_agents'], 0)
        # compact_boundary only: the isCompactSummary message must not add one
        self.assertEqual(result['compact_count'], 1)
        self.assertEqual(result['periodic_count'], 0)

    def test_claude_sidechain_not_double_counted(self):
        result = self._parse('claude_session.jsonl', 'cli-sidechain')
        # The isSidechain line carries 999 tokens; counting it would show 1636.
        self.assertLess(result['total_input'], 1000)

    def test_codebuddy_totals(self):
        result = self._parse('codebuddy_session.jsonl', 'cb-fixture')
        self.assertEqual(result['total_input'], 1250)
        self.assertEqual(result['total_output'], 125)
        self.assertEqual(result['total_cache_read'], 800)
        self.assertEqual(result['total_cache_write'], 100)
        self.assertAlmostEqual(result['total_credits'], 0.65)
        self.assertEqual(result['total_reasoning'], 40)
        self.assertEqual(result['request_count'], 3)
        self.assertEqual(result['tool_counts'], {'Bash': 1, 'Agent': 1, 'Read': 1})
        self.assertEqual(result['running_agents'], 1)
        self.assertEqual(result['compact_count'], 1)
        self.assertEqual(result['periodic_count'], 1)

    def test_incremental_matches_fresh_parse(self):
        path = _copy_fixture('claude_session.jsonl', self._tmp)
        first = parsing.parse_transcript_incremental(path, 'cli-inc')[0]
        second = parsing.parse_transcript_incremental(path, 'cli-inc')[0]
        self.assertEqual(first, second)

    def test_host_mismatch_invalidates_cache(self):
        path = _copy_fixture('claude_session.jsonl', self._tmp)
        first = parsing.parse_transcript_incremental(path, 'cli-host')[0]
        self.assertGreater(first['request_count'], 0)
        original = stats.HOST
        try:
            stats.HOST = 'codebuddy' if original == 'claude' else 'claude'
            second = parsing.parse_transcript_incremental(path, 'cli-host')[0]
        finally:
            stats.HOST = original
        # Full reparse on the other host: same numbers, not a doubled sum.
        self.assertEqual(first['request_count'], second['request_count'])


class ExtractUsage(unittest.TestCase):
    def test_claude_input_includes_cache(self):
        usage = parsing.extract_usage({'type': 'assistant', 'message': {
            'id': 'm1', 'model': 'opus',
            'usage': {'input_tokens': 1, 'output_tokens': 2,
                      'cache_creation_input_tokens': 3, 'cache_read_input_tokens': 4}}})
        self.assertEqual(usage['input'], 8)
        self.assertEqual(usage['cache_write'], 3)
        self.assertEqual(usage['cache_read'], 4)
        self.assertEqual(usage['message_id'], 'm1')

    def test_claude_without_usage(self):
        self.assertIsNone(parsing.extract_usage({'type': 'assistant', 'message': {'id': 'x'}}))

    def test_missing_message(self):
        self.assertIsNone(parsing.extract_usage({'type': 'assistant'}))

    def test_codebuddy_input_not_double_counted(self):
        usage = parsing.extract_usage({'type': 'function_call', 'providerData': {
            'usage': {'inputTokens': 100, 'outputTokens': 10,
                      'inputTokensDetails': [{'cached_tokens': 80}]},
            'rawUsage': {'prompt_cache_hit_tokens': 80, 'credit': 0.2}}})
        self.assertEqual(usage['input'], 100)   # already cache-inclusive
        self.assertEqual(usage['cache_read'], 80)
        self.assertAlmostEqual(usage['credits'], 0.2)

    def test_garbage_entry(self):
        self.assertIsNone(parsing.extract_usage('not-a-dict'))
        self.assertIsNone(parsing.extract_usage({'providerData': 'nope'}))


class DuplicateIds(unittest.TestCase):
    def test_seen_msg_ids_ring(self):
        state = parsing.new_state()
        entry = {'type': 'assistant', 'message': {'id': 'm1', 'usage': {
            'input_tokens': 10, 'output_tokens': 1}}}
        first = stats.new_stats()
        parsing.add_line_to_stats(first, entry, state)
        parsing.add_line_to_stats(first, entry, state)
        self.assertEqual(first['request_count'], 1)
        self.assertEqual(first['total_input'], 10)

    def test_ring_evicts_old_ids(self):
        state = parsing.new_state()
        for index in range(stats.SEEN_MSG_IDS_MAX + 1):
            parsing.add_line_to_stats(stats.new_stats(), {'type': 'assistant', 'message': {
                'id': 'm%d' % index, 'usage': {'input_tokens': 1}}}, state)
        self.assertEqual(len(state['seen_msg_ids']), stats.SEEN_MSG_IDS_MAX)
        self.assertEqual(state['seen_msg_ids'][-1], 'm%d' % stats.SEEN_MSG_IDS_MAX)

    def test_sidechain_ignored_only_in_main(self):
        entry = {'type': 'assistant', 'isSidechain': True, 'message': {
            'id': 'side', 'usage': {'input_tokens': 5}}}
        main = stats.new_stats()
        parsing.add_line_to_stats(main, entry, None, is_main=True)
        self.assertEqual(main['total_input'], 0)
        sub = stats.new_stats()
        parsing.add_line_to_stats(sub, entry, None, is_main=False)
        self.assertEqual(sub['total_input'], 5)


class Integration(unittest.TestCase):
    """Run the real script with both hosts' stdin fixtures (no TTY)."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _run(self, fixture):
        script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              'statusline.py')
        with open(os.path.join(FIXTURES, fixture), 'r', encoding='utf-8') as handle:
            payload = handle.read()
        env = dict(os.environ, STATUSLINE_TMPDIR=self._tmp, COLUMNS='200')
        env.pop('CODEBUDDY_CONFIG_DIR', None)
        env.pop('CLAUDE_CONFIG_DIR', None)
        return subprocess.run([sys.executable, script], input=payload, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=10)

    def _plain(self, text):
        return _ANSI.sub('', text)

    def test_claude_renders_effort_and_no_money(self):
        result = self._run('stdin_claude.json')
        self.assertEqual(result.returncode, 0, result.stderr)
        plain = self._plain(result.stdout)
        self.assertIn('Effort:high', plain)
        self.assertNotIn('Credits:', plain)
        self.assertNotIn('Periodic', plain)
        self.assertNotIn(chr(36), plain)
        self.assertNotIn(chr(0xa5), plain)

    def test_codebuddy_renders_no_effort(self):
        result = self._run('stdin_codebuddy.json')
        self.assertEqual(result.returncode, 0, result.stderr)
        plain = self._plain(result.stdout)
        self.assertNotIn('Effort:', plain)
        self.assertNotIn(chr(36), plain)
        self.assertNotIn(chr(0xa5), plain)

    def test_effort_block_registered_after_model(self):
        import render
        self.assertLess(render.BLOCKS_LINE1.index('model'),
                        render.BLOCKS_LINE1.index('effort'))
        self.assertNotIn('cost', render.BLOCKS_LINE1)
