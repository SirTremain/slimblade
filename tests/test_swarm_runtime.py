"""Synthetic orchestration checks: no model, firmware, licensing or hardware."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import swarm_runtime as sr
from swarm_build import attempt_budget


def snapshot(remaining=81, now=None):
    now = time.time() if now is None else now
    return {'remaining_percent': remaining, 'observed_at': now,
            'resets_at': 1999999999, 'window_minutes': 10080}


class QuotaTests(unittest.TestCase):
    def test_weekly_can_be_primary_or_secondary(self):
        weekly = {'usedPercent': 19, 'windowDurationMins': 10080, 'resetsAt': 2000}
        for key in ('primary', 'secondary'):
            limits = {'limitId': 'codex', key: weekly}
            self.assertEqual(sr.quota_snapshot({'rateLimits': limits}, now=1000),
                {'observed_at': 1000, 'remaining_percent': 81, 'resets_at': 2000,
                 'window_minutes': 10080})

    def test_reject_missing_malformed_ambiguous_or_exhausted_quota(self):
        weekly = {'usedPercent': 19, 'windowDurationMins': 10080, 'resetsAt': 2000}
        bad = [{}, {'rateLimits': {'limitId': 'other', 'primary': weekly}},
               {'rateLimits': {'limitId': 'codex', 'primary': weekly, 'secondary': weekly}}]
        for change in ({'usedPercent': True}, {'usedPercent': float('nan')},
                       {'usedPercent': -1}, {'usedPercent': 100}, {'resetsAt': 999},
                       {'resetsAt': float('inf')}, {'windowDurationMins': 300}):
            bad.append({'rateLimits': {'limitId': 'codex', 'primary': {**weekly, **change}}})
        for response in bad:
            with self.subTest(response=response), self.assertRaises(ValueError):
                sr.quota_snapshot(response, now=1000)

    def test_threshold_staleness_and_reset_do_not_resume(self):
        sr.check_budget(snapshot(45.01, 1000), now=1000)
        for value in (snapshot(45, 1000), snapshot(40, 1000), snapshot(81, 900),
                      snapshot(81, 1001), snapshot(float('nan'), 1000)):
            with self.assertRaises(ValueError):
                sr.check_budget(value, now=1000)
        with self.assertRaisesRegex(ValueError, 'window changed'):
            sr.check_budget(snapshot(81, 1000), now=1000, reset=3000)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='slimblade-swarm-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_slots_bound_concurrency(self):
        with sr.worker_slot(self.root), sr.worker_slot(self.root):
            with self.assertRaisesRegex(ValueError, 'slots full'):
                with sr.worker_slot(self.root):
                    self.fail('third worker entered')
        with sr.worker_slot(self.root):
            pass

    def test_task_lock_prevents_duplicate_workers_and_concurrent_build(self):
        with sr.task_lock(self.root, 'fn_00001000'):
            with self.assertRaisesRegex(ValueError, 'active worker/build'):
                with sr.task_lock(self.root, 'fn_00001000'):
                    self.fail('duplicate task owner')

    def test_attempt_budget_and_non_improvement(self):
        attempt_budget([{'differing_bytes': n} for n in (20, 19, 18, 17, 16, 15, 14)])
        with self.assertRaisesRegex(ValueError, 'eight'):
            attempt_budget([{'differing_bytes': n} for n in range(8, 0, -1)])
        for history in ([{'differing_bytes': n} for n in (10, 10, 11, 10)],
                        [{'result': 'rejected'}] * 3):
            with self.assertRaisesRegex(ValueError, 'without improvement'):
                attempt_budget(history)
        attempt_budget([{'result': 'compiler-busy'}] * 20)

    def test_quota_stop_latches_across_new_jobs_and_reset(self):
        with self.assertRaises(ValueError):
            sr.guarded_quota(lambda: snapshot(45), self.root, 1999999999)
        self.assertTrue((self.root / 'PAUSED.json').exists())
        with self.assertRaisesRegex(ValueError, 'paused'):
            sr.guarded_quota(snapshot, self.root, 1999999999)

    def test_successful_worker_checkpoints(self):
        output = self.root / 'run'
        result = sr.supervise([sys.executable, '-c', 'print(input())'], 'synthetic\n',
                              output, snapshot, seconds=2, poll_seconds=0.02)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual((output / 'events.jsonl').read_text().strip(), 'synthetic')
        self.assertGreaterEqual(len(result['usage']), 2)

    def test_initial_low_quota_launches_nothing(self):
        marker, output = self.root / 'started', self.root / 'run'
        with self.assertRaises(ValueError):
            sr.supervise([sys.executable, '-c', f'open({str(marker)!r},"w").close()'], '',
                         output, lambda: snapshot(45))
        self.assertFalse(marker.exists())
        state = json.loads((output / 'checkpoint.json').read_text())
        self.assertEqual(state['status'], 'stopped')
        self.assertNotIn('pid', state)

    def test_running_worker_stops_on_quota_or_missing_reading_or_timeout(self):
        for cause in ('low', 'missing', 'time'):
            count = 0
            def read():
                nonlocal count
                count += 1
                if count > 1 and cause == 'missing':
                    raise RuntimeError('quota unavailable')
                return snapshot(45 if count > 1 and cause == 'low' else 81)
            output = self.root / cause
            start = time.monotonic()
            with self.assertRaises((ValueError, RuntimeError)):
                sr.supervise([sys.executable, '-c', 'import time;time.sleep(60)'], '',
                             output, read, seconds=0.15, poll_seconds=0.02)
            self.assertLess(time.monotonic()-start, 5)
            state = json.loads((output / 'checkpoint.json').read_text())
            self.assertEqual(state['status'], 'stopped')
            with self.assertRaises(ProcessLookupError):
                os.kill(state['pid'], 0)

    def test_path_traversal_and_symlink_rejected(self):
        for path in ('/tmp/x', '../x', 'a/../../x'):
            with self.assertRaises(ValueError):
                sr.safe_path(self.root, path)
        (self.root / 'link').symlink_to('/tmp')
        with self.assertRaises(ValueError):
            sr.safe_path(self.root, 'link/child')

    def test_config_denies_auth_network_self_spawn_and_external_tools(self):
        cmd = sr.codex_command('gpt-6-luna', ['decomp/src/fn_00001000.c'])
        value = ' '.join(cmd)
        for expected in ('agents.enabled=false', 'network.enabled=false',
                         'features.apps=false', 'features.plugins=false',
                         'approval_policy="never"', '"deny"'):
            self.assertIn(expected, value)
        self.assertNotIn('--dangerously-bypass', value)
        with self.assertRaises(ValueError):
            sr.codex_command('unreviewed-model', [])

    def test_batch_policy_excludes_old_tasks_and_call_experiments(self):
        (self.root / 'decomp').mkdir()
        file = self.root / 'decomp/swarm-policy.json'
        value = json.loads((ROOT / 'decomp/swarm-policy.json').read_text())
        value['quota_window_resets_at'] = int(time.time()) + 1000
        file.write_text(json.dumps(value))
        for ident in sr.BATCHES['four-reviewed-leaf-batch-2-only']:
            self.assertEqual(sr.policy(self.root, ident)['scope'], 'four-reviewed-leaf-batch-2-only')
        for ident in ('fn_00003b48', 'fn_00006464', 'fn_00006500', 'fn_00001000'):
            with self.assertRaisesRegex(ValueError, 'outside selected batch'):
                sr.policy(self.root, ident)
        for change in ({'scope': 'all-functions'}, {'maximum_concurrent_workers': 3},
                       {'stop_remaining_percent': 40}, {'quota_window_resets_at': 1}):
            file.write_text(json.dumps({**value, **change}))
            with self.subTest(change=change), self.assertRaises(ValueError):
                sr.policy(self.root)
        value['scope'] = 'six-reviewed-leaf-pilot-only'
        file.write_text(json.dumps(value))
        sr.policy(self.root, 'fn_00003b48')
        with self.assertRaises(ValueError):
            sr.policy(self.root, 'fn_00013f58')

    def test_real_mount_isolation(self):
        # Only synthetic files; tests don't attempt to open a physical device.
        work, evidence, runtime = [self.root / p for p in ('work', 'evidence', 'runtime')]
        for directory in (work, evidence, runtime):
            directory.mkdir()
        for path in sr.WORKER_READS:
            file = work / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text('read-only instructions')
        source = work / 'decomp/src/fn_00001000.c'
        source.parent.mkdir(parents=True)
        source.write_text('')
        results = work / 'decomp/results/fn_00001000'
        results.mkdir(parents=True)
        (evidence / 'listing.txt').write_text('synthetic evidence')
        (self.root / 'private-secret').write_text('not for worker')
        check = '''from pathlib import Path
assert not Path(%r).exists()
assert not Path('/dev/bus/usb').exists()
assert list(Path('/workspace/.git').iterdir()) == []
assert not Path('/workspace/decomp/results/preparation').exists()
assert Path('/evidence/listing.txt').read_text() == 'synthetic evidence'
for name in ('/workspace/AGENTS.md', '/evidence/listing.txt', '/usr/forbidden',
             '/workspace/unassigned-file'):
    try: Path(name).write_text('changed')
    except OSError: pass
    else: raise AssertionError('read-only mount was writable')
Path('/workspace/decomp/src/fn_00001000.c').write_text('synthetic result')
Path('/workspace/decomp/results/fn_00001000/result.json').write_text('{}')
print('isolation passed')
''' % str(self.root / 'private-secret')
        cmd = sr.sandbox_command(work, evidence, runtime,
                                ['decomp/src/fn_00001000.c', 'decomp/results/fn_00001000/'],
                                ['/usr/bin/python3', '-c', check])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(source.read_text(), 'synthetic result')
        self.assertEqual((work / 'AGENTS.md').read_text(), 'read-only instructions')
        fake_auth = self.root / 'auth-fixture.json'
        fake_auth.write_text('{"fixture":"not-an-actual-token"}')
        settings = sr.codex_command('gpt-6-luna', ['decomp/src/fn_00001000.c'])
        config = []
        for index, value in enumerate(settings):
            if value == '-c':
                config += settings[index:index+2]
        inner_check = '''from pathlib import Path
try: Path(%r).read_text()
except OSError: pass
else: raise AssertionError('harness auth readable by a worker command')
Path('/workspace/decomp/src/fn_00001000.c').write_text('inner sandbox passed')
''' % str(Path.home() / '.codex/auth.json')
        argv = ['/usr/bin/codex', *config, 'sandbox', '--',
                '/usr/bin/python3', '-c', inner_check]
        result = subprocess.run(sr.sandbox_command(work, evidence, runtime,
            ['decomp/src/fn_00001000.c', 'decomp/results/fn_00001000/'], argv, auth=fake_auth),
            capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(source.read_text(), 'inner sandbox passed')


if __name__ == '__main__':
    unittest.main()
