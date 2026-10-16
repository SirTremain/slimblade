"""Coordinator handoff fixtures; no firmware, model jobs or actual queue edits."""
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import decomp
import swarm_runtime as sr
import swarm_worker as sw
import swarm_build as sb


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='slimblade-handoff-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root / '.worktrees/fixture'
        self.work.mkdir(parents=True)
        self.task_id = 'fn_00001000'
        self.task = {'id': self.task_id, 'kind': 'function',
            'allowed_paths': [f'decomp/src/{self.task_id}.c', f'decomp/results/{self.task_id}/'],
            'comparison': {'lock_path': 'fixture-lock.json', 'lock_sha256': 'fixture-only'}}

    def test_queue_identity_and_cumulative_claim_time(self):
        (self.root / '.decomp').mkdir()
        queue = self.root / '.decomp/queue.sqlite3'
        now = datetime.now(timezone.utc)
        with sqlite3.connect(queue) as db:
            db.execute('create table tasks (id text,worker text,state text,spec_hash text,updated text)')
            db.execute('insert into tasks values (?,?,?,?,?)',
                (self.task_id, 'fixture', 'claimed', decomp.digest(decomp.canonical(self.task)), now.isoformat()))
        def git(worktree, *args):
            return str(self.work) if args[-1] == '--show-toplevel' else 'fixture-commit'
        with patch.object(decomp, '__file__', str(self.root / 'tools/decomp.py')), \
             patch.object(decomp, 'load_tasks', return_value=({}, {self.task_id: self.task})), \
             patch.object(decomp, 'preparation_ready', return_value=True), \
             patch.object(decomp, 'evidence_check'), patch.object(decomp, 'prompt', return_value='fixture'), \
             patch.object(sw, 'git', side_effect=git), patch.object(sw, 'check_worker_diff'):
            _, _, seconds = sw.assignment(self.root, self.work, self.task_id, 'fixture')
            self.assertTrue(1190 < seconds <= 1200)
            with self.assertRaisesRegex(ValueError, 'claimed'):
                sw.assignment(self.root, self.work, self.task_id, 'other')
            with sqlite3.connect(queue) as db:
                db.execute('update tasks set updated=?', ((now-timedelta(minutes=21)).isoformat(),))
            with self.assertRaisesRegex(ValueError, 'elapsed-time'):
                sw.assignment(self.root, self.work, self.task_id, 'fixture')
            # Independent review is not another worker iteration and gets its
            # own bounded rebuild, but still requires the exact queue owner.
            self.assertEqual(sw.assignment(self.root, self.work, self.task_id,
                                           'fixture', review=True)[2], 600)

    def test_diff_rejects_untracked_outside_assignment_and_symlink(self):
        result = MagicMock(stdout=b'?? outside.txt\0')
        with patch.object(sw.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(ValueError, 'out-of-assignment'):
                sw.check_worker_diff(self.work, self.task['allowed_paths'])
        sw.prepare_outputs(self.work, self.task['allowed_paths'])
        name = f'decomp/results/{self.task_id}/link'
        (self.work / name).symlink_to('/tmp')
        result.stdout = ('?? ' + name + '\0').encode()
        with patch.object(sw.subprocess, 'run', return_value=result):
            with self.assertRaises(ValueError):
                sw.check_worker_diff(self.work, self.task['allowed_paths'])

    def test_build_ledger_and_independent_rebuild_reject_changed_source(self):
        sw.prepare_outputs(self.work, self.task['allowed_paths'])
        source = self.work / self.task['allowed_paths'][0]
        source.write_text('synthetic source, never compiled')
        args = SimpleNamespace(root=self.root, worktree=self.work, task=self.task_id,
                               worker='fixture', review=False)
        fake_ac = SimpleNamespace(__file__=str(self.root / 'tools/armcc_compare.py'),
            sc=SimpleNamespace(base=SimpleNamespace(sha=lambda data: hashlib.sha256(data).hexdigest())),
            runner=SimpleNamespace(scrub=lambda message: message))
        called = []
        def compare(command, prompt, process_output, quota, **kwargs):
            called.append(command)
            output = Path(command[-1])
            output.mkdir()
            sr.write_json(output / 'comparison.json',
                          {'result': 'exact-range-bytes', 'differing_bytes': 0})
            return {'returncode': 0}
        with patch.dict(sys.modules, {'armcc_compare': fake_ac}), \
             patch.object(sb, 'assignment', return_value=(self.task, 'fixture', 100)), \
             patch.object(sr, 'policy', return_value={'quota_window_resets_at': 1999999999}), \
             patch.object(sb, 'monitored_account'), patch.object(sr, 'supervise', side_effect=compare):
            sb.build(args)
            folder = self.root / '.decomp/swarm/builds' / self.task_id
            self.assertEqual(len(json.loads((folder / 'attempts.json').read_text())), 1)
            args.review = True
            source.write_text('changed synthetic source')
            with self.assertRaisesRegex(ValueError, 'unchanged exact draft'):
                sb.build(args)
            source.write_text('synthetic source, never compiled')
            sb.build(args)
            self.assertEqual(len(called), 2)
            self.assertNotEqual(called[0][-1], called[1][-1])
            self.assertEqual(json.loads((folder / 'review-status.json').read_text())['result'],
                             'exact-range-bytes')

    def test_global_compiler_slot_rejects_overlapping_task_builds(self):
        with sr.compiler_slot(self.root):
            with self.assertRaisesRegex(ValueError, 'compiler busy'):
                with sr.compiler_slot(self.root):
                    self.fail('concurrent compiler')


if __name__ == '__main__':
    unittest.main()
