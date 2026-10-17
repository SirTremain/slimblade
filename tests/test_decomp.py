"""Synthetic coordination tests; no firmware, network or device access."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "tools/decomp.py"
sys.path.insert(0, str(REPO / 'tools'))
import decomp as coordinator
import armcc_compare
import armcc_calls


class CoordinationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="slimblade-scaffold-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(REPO / "decomp", self.root / "decomp")
        # Unit fixtures must not inherit live stock assignments or local data.
        inventory = self.root / "decomp/functions.json"
        data = json.loads(inventory.read_text())
        data["functions"] = []
        inventory.write_text(json.dumps(data))
        (self.root / "decomp/preparation.json").write_text(json.dumps(
            {"schema_version": 1, "ready": True, "allowed_function_ids": []}))

    def cli(self, *args, success=True):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root), *args],
            text=True, capture_output=True, timeout=25,
        )
        if success is not None:
            self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def report(self, task="bootstrap-toolchain", worker="worker-a", status="draft"):
        path = self.root / f"{task}-result.json"
        path.write_text(json.dumps({
            "task": task, "worker": worker, "status": status,
            "observations": [], "inferences": [], "open_questions": [],
            "validation": ["Synthetic fixture only"],
        }))
        return path

    def accept_bootstraps(self):
        for task in ("bootstrap-inventory", "bootstrap-toolchain", "bootstrap-verifier"):
            self.cli("claim", task, "--worker", "worker-a")
            report = self.report(task)
            self.cli("submit", task, "--worker", "worker-a", "--report", str(report))
            self.cli("review", task, "--reviewer", "reviewer", "--decision", "accept",
                     "--note", "Synthetic review")

    def function(self):
        path = self.root / "decomp/templates/function.json"
        task = json.loads(path.read_text())
        task["boundary_review"] = "Synthetic fixture, not real firmware"
        evidence = self.root / task["evidence_path"]
        evidence.mkdir(parents=True)
        baseline = json.loads((self.root / "decomp/baseline.json").read_text())
        meta = {key: task[key] for key in ("entry", "mode", "ranges")}
        meta["baseline_sha256"] = baseline["sha256"]
        (evidence / "metadata.json").write_text(json.dumps(meta))
        (evidence / "listing.txt").write_text("Synthetic data; not firmware")
        (evidence / "context.md").write_text("Synthetic context")
        task["evidence_sha256"] = self.cli("hash-packet", str(evidence)).stdout.strip()
        inventory = self.root / "decomp/functions.json"
        data = json.loads(inventory.read_text())
        data["functions"] = [task]
        inventory.write_text(json.dumps(data))
        (self.root / "decomp/preparation.json").write_text(json.dumps(
            {"schema_version": 1, "ready": True, "allowed_function_ids": [task["id"]]}))
        return task, evidence

    def test_status_does_not_create_database(self):
        self.assertIn("matching coverage: unknown", self.cli("status").stdout)
        self.assertFalse((self.root / ".decomp/queue.sqlite3").exists())
        self.cli("check")

    def test_competing_claims_only_one_wins(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda i: self.cli(
                "claim", "bootstrap-toolchain", "--worker", f"worker-{i}", success=None),
                range(8)))
        self.assertEqual(sum(result.returncode == 0 for result in results), 1)

    def test_claim_owner_and_self_review(self):
        self.cli("claim", "bootstrap-toolchain", "--worker", "worker-a")
        report = self.report()
        self.cli("release", "bootstrap-toolchain", "--worker", "worker-b",
                 "--note", "wrong owner", success=False)
        self.cli("submit", "bootstrap-toolchain", "--worker", "worker-a", "--report", str(report))
        self.cli("review", "bootstrap-toolchain", "--reviewer", "worker-a",
                 "--decision", "accept", "--note", "self review", success=False)

    def test_worker_cannot_submit_matched(self):
        self.cli("claim", "bootstrap-toolchain", "--worker", "worker-a")
        self.cli("submit", "bootstrap-toolchain", "--worker", "worker-a",
                 "--report", str(self.report(status="matched")), success=False)

    def test_changed_report_rejected_but_requeue_available(self):
        self.cli("claim", "bootstrap-toolchain", "--worker", "worker-a")
        report = self.report()
        self.cli("submit", "bootstrap-toolchain", "--worker", "worker-a", "--report", str(report))
        report.write_text(report.read_text() + "\n")
        self.cli("review", "bootstrap-toolchain", "--reviewer", "reviewer",
                 "--decision", "accept", "--note", "changed", success=False)
        self.cli("review", "bootstrap-toolchain", "--reviewer", "reviewer",
                 "--decision", "requeue", "--note", "resubmit changed report")
        self.cli("claim", "bootstrap-toolchain", "--worker", "worker-b")

    def test_dependencies_and_packet_tampering(self):
        task, evidence = self.function()
        self.cli("claim", task["id"], "--worker", "worker-a", success=False)
        self.accept_bootstraps()
        (evidence / "listing.txt").write_text("changed evidence")
        self.cli("claim", task["id"], "--worker", "worker-a", success=False)

    def test_reviewed_function_is_not_matched(self):
        task, _ = self.function()
        self.accept_bootstraps()
        self.cli("claim", task["id"], "--worker", "worker-a")
        self.cli("submit", task["id"], "--worker", "worker-a",
                 "--report", str(self.report(task["id"])))
        result = self.cli("review", task["id"], "--reviewer", "reviewer",
                          "--decision", "accept", "--note", "Draft review only")
        self.assertIn("reviewed; this does not certify a binary match", result.stdout)
        self.assertIn("matching coverage: unknown", self.cli("status").stdout)

    def test_blocked_report_cannot_be_accepted(self):
        self.cli("claim", "bootstrap-toolchain", "--worker", "worker-a")
        self.cli("submit", "bootstrap-toolchain", "--worker", "worker-a",
                 "--report", str(self.report(status="blocked")))
        self.cli("review", "bootstrap-toolchain", "--reviewer", "reviewer",
                 "--decision", "accept", "--note", "blocked", success=False)

    def test_block_is_terminal_and_does_not_silently_reset_budget(self):
        self.cli('claim', 'bootstrap-toolchain', '--worker', 'worker-a')
        report = self.report(status='blocked')
        self.cli('submit', 'bootstrap-toolchain', '--worker', 'worker-a', '--report', str(report))
        self.cli('review', 'bootstrap-toolchain', '--reviewer', 'reviewer', '--decision', 'block',
                 '--note', 'Synthetic evidence-backed blocker')
        self.assertIn('blocked', self.cli('status').stdout)
        self.cli('claim', 'bootstrap-toolchain', '--worker', 'worker-b', success=False)
        self.cli('release', 'bootstrap-toolchain', '--worker', 'worker-a', '--note', 'reset', success=False)

    def test_dependency_states_distinguish_bootstraps_and_reviewed_functions(self):
        tasks = {'boot': {'kind': 'bootstrap'}, 'leaf': {'kind': 'function'}}
        task = {'depends_on': ['boot', 'leaf']}
        states = {'boot': {'state': 'accepted'}, 'leaf': {'state': 'reviewed'}}
        self.assertTrue(coordinator.ready(task, states, tasks))
        for state in ('accepted', 'submitted', 'blocked', 'claimed', 'queued', 'matched'):
            states['leaf']['state'] = state
            self.assertFalse(coordinator.ready(task, states, tasks))

    def test_invalid_paths_and_cycles(self):
        queue = self.root / "decomp/tasks.json"
        original = json.loads(queue.read_text())
        data = json.loads(queue.read_text())
        data["tasks"][0]["allowed_paths"] = ["../../escape"]
        queue.write_text(json.dumps(data))
        self.cli("check", success=False)
        original["tasks"][0]["depends_on"] = ["bootstrap-inventory"]
        queue.write_text(json.dumps(original))
        self.cli("check", success=False)

    def test_packet_rejects_symlinks(self):
        packet = self.root / "packet"
        packet.mkdir()
        (packet / "link").symlink_to(self.root / "decomp/baseline.json")
        self.cli("hash-packet", str(packet), success=False)

    def test_local_check_rejects_missing_packet(self):
        task, evidence = self.function()
        self.cli("check", "--local")
        (evidence / "listing.txt").unlink()
        self.cli("check", "--local", success=False)

    def test_pilot_claim_requires_local_lock(self):
        task, _ = self.function()
        task["comparison_scope"] = "stock-leaf-pilot-feedback-v1"
        task["comparison"] = {"lock_path": ".decomp/missing.json", "lock_sha256": "0"*64}
        inventory = self.root / "decomp/functions.json"
        data = json.loads(inventory.read_text())
        data["functions"] = [task]
        inventory.write_text(json.dumps(data))
        self.accept_bootstraps()
        self.cli("claim", task["id"], "--worker", "worker-a", success=False)

    def test_preparation_gate_blocks_function_claim(self):
        task, _ = self.function()
        self.accept_bootstraps()
        gate = self.root / "decomp/preparation.json"
        gate.write_text(json.dumps({"schema_version": 1, "ready": False}))
        self.assertIn("blocked", self.cli("status").stdout)
        self.cli("claim", task["id"], "--worker", "worker-a", success=False)

    def test_missing_preparation_gate_fails_closed(self):
        task, _ = self.function()
        self.accept_bootstraps()
        (self.root / "decomp/preparation.json").unlink()
        self.assertIn("blocked", self.cli("status").stdout)
        self.cli("claim", task["id"], "--worker", "worker-a", success=False)

    def test_invalid_preparation_gate_rejected(self):
        (self.root / "decomp/preparation.json").write_text('{"schema_version":1,"ready":"true"}')
        self.cli("check", success=False)

    def test_ready_gate_does_not_expand_to_unreviewed_tasks(self):
        task, _ = self.function()
        self.accept_bootstraps()
        gate = self.root / "decomp/preparation.json"
        gate.write_text(json.dumps({"schema_version": 1, "ready": True, "allowed_function_ids": []}))
        self.assertIn("blocked", self.cli("status").stdout)
        self.cli("claim", task["id"], "--worker", "worker-a", success=False)
        gate.write_text(json.dumps({"schema_version": 1, "ready": True}))
        self.cli("check", success=False)

    def test_armcc_scope_requires_new_local_lock(self):
        task, _ = self.function()
        task["comparison_scope"] = "armcc5-leaf-feedback-v1"
        task["comparison"] = {"lock_path": ".decomp/missing.json", "lock_sha256": "0"*64}
        path = self.root / "decomp/functions.json"
        data = json.loads(path.read_text())
        data["functions"] = [task]
        path.write_text(json.dumps(data))
        self.cli("check")
        self.cli("check", "--local", success=False)

    def test_armcc_task_binding_and_coordinator_build_prompt(self):
        task, _ = self.function()
        task.update(comparison_scope=armcc_compare.SCOPE, signature='unsigned int (unsigned int)',
                    abi_status='hypothesis_requires_review',
                    comparison={'lock_path': '.decomp/test-lock.json', 'lock_sha256': '0'*64})
        baseline = coordinator.read_json(self.root / 'decomp/baseline.json')
        definition = {k: v for k, v in task.items() if k != 'comparison'}
        pinned = {**task, 'end_exclusive': task['ranges'][0]['end_exclusive'],
                  'task_sha256': coordinator.digest(armcc_compare.sc.encode(definition))}
        lock = {'baseline': {'sha256': baseline['sha256']}, 'baseline_bytes': baseline['bytes'],
                'tasks': {task['id']: pinned}}
        with mock.patch.object(armcc_compare, 'load_lock', return_value=lock):
            prompt = coordinator.prompt(self.root, baseline, task, 'fixture')
            self.assertIn('tools/armcc_compare.py', prompt)
            self.assertIn('coordinator build service', prompt)
            self.assertNotIn('tools/stock_compare.py', prompt)
            pinned['signature'] = 'int (unsigned int)'
            with self.assertRaisesRegex(ValueError, 'ABI/entry'):
                coordinator.evidence_check(self.root, baseline, task)

    def test_input_hash_gate_with_synthetic_bytes(self):
        image = self.root / "synthetic.bin"
        data = b"header-payload"
        image.write_bytes(data)
        path = self.root / "decomp/baseline.json"
        baseline = json.loads(path.read_text())
        baseline.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                        payload_offset=7, payload_bytes=len(data[7:]),
                        payload_sha256=hashlib.sha256(data[7:]).hexdigest())
        path.write_text(json.dumps(baseline))
        self.cli("verify-input", str(image))
        image.write_bytes(b"Header-payload")
        self.cli("verify-input", str(image), success=False)

    def test_call_lock_retains_parent_and_full_task_contract(self):
        task, _ = self.function()
        task.update(comparison_scope=armcc_calls.SCOPE, signature='unsigned int (void)',
                    abi_status='hypothesis_requires_review',
                    extern_functions={'fn_00002000': {'entry':'0x2000','mode':'thumb','signature':'void (void)'}},
                    calls=[{'address':'0x1002','callee':'fn_00002000'}],
                    comparison={'lock_path':'.decomp/calls.json','lock_sha256':'0'*64})
        baseline = coordinator.read_json(self.root/'decomp/baseline.json')
        definition = {k:v for k,v in task.items() if k != 'comparison'}
        pinned = {**task, 'end_exclusive':task['ranges'][0]['end_exclusive'],
                  'task_sha256':coordinator.digest(armcc_compare.sc.encode(definition))}
        parent = {'baseline':{'sha256':baseline['sha256']},'baseline_bytes':baseline['bytes']}
        extension = {'tasks':{task['id']:pinned}}
        with mock.patch.object(armcc_calls,'load_lock',return_value=(extension,parent)):
            self.assertIn('tools/armcc_calls.py',coordinator.prompt(self.root,baseline,task,'fixture'))
            pinned['calls'] = []
            with self.assertRaisesRegex(ValueError,'call contract'):
                coordinator.evidence_check(self.root,baseline,task)
            pinned['calls'] = task['calls']
            parent['baseline']['sha256'] = 'f'*64
            with self.assertRaisesRegex(ValueError,'baseline mismatch'):
                coordinator.evidence_check(self.root,baseline,task)


if __name__ == "__main__":
    unittest.main()
