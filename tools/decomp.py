#!/usr/bin/env python3
"""Offline task coordination. This is not a decompiler or matching verifier."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import sqlite3
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
IDENTIFIER = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
COMPARATORS = {"stock-leaf-pilot-feedback-v1": "stock_compare",
               "armcc5-leaf-feedback-v1": "armcc_compare",
               "armcc5-direct-call-experiment-v1": "armcc_calls"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def relative_path(value):
    path = PurePosixPath(value)
    require(value and not path.is_absolute() and ".." not in path.parts,
            f"unsafe relative path: {value}")
    return path


def packet_hash(path):
    require(path.is_dir() and not path.is_symlink(), "packet must be a directory")
    rows = []
    for item in sorted(path.rglob("*")):
        require(not item.is_symlink(), f"symlink in evidence packet: {item}")
        if item.is_file():
            rows.append([item.relative_to(path).as_posix(), digest(item.read_bytes())])
    require(rows, "empty evidence packet")
    return digest(canonical(rows))


def load_tasks(root):
    baseline = read_json(root / "decomp/baseline.json")
    inventory = read_json(root / "decomp/functions.json")
    queue = read_json(root / "decomp/tasks.json")
    require(queue["schema_version"] == inventory["schema_version"] == 1,
            "unsupported schema")
    require(inventory["baseline_id"] == baseline["id"], "inventory baseline mismatch")
    tasks = {}
    spans = []
    for task in queue["tasks"] + inventory["functions"]:
        ident = task["id"]
        require(IDENTIFIER.fullmatch(ident), "invalid task ID")
        require(ident not in tasks, f"duplicate task: {ident}")
        require(task["kind"] in ("bootstrap", "function"), "invalid task kind")
        for key in ("title", "instructions", "acceptance"):
            require(isinstance(task[key], str) and task[key].strip(), f"missing {key}")
        require(task["allowed_paths"], "task needs an allowed path")
        for path in task["allowed_paths"]:
            relative_path(path)
            expected = f"decomp/results/{ident}/"
            require(path.startswith(expected) or
                    (task["kind"] == "function" and path == f"decomp/src/{ident}.c"),
                    f"worker path outside task ownership: {path}")
        if task["kind"] == "function":
            entry = int(task["entry"], 16)
            require(ident == f"fn_{entry:08x}" and entry % 2 == 0,
                    "function ID must use the even entry address")
            require(task["mode"] in ("arm", "thumb"), "unknown instruction state")
            require(task["mode"] != "arm" or entry % 4 == 0, "unaligned ARM entry")
            require(SHA256.fullmatch(task["evidence_sha256"]), "missing packet hash")
            require(task["boundary_review"] and
                    "REPLACE" not in task["boundary_review"], "unreviewed boundary")
            if "comparison_scope" in task:
                require(task["comparison_scope"] in COMPARATORS,
                        "unknown comparison scope")
                comparison = task["comparison"]
                relative_path(comparison["lock_path"])
                require(comparison["lock_path"].startswith(".decomp/") and
                        SHA256.fullmatch(comparison["lock_sha256"]), "invalid comparison lock")
            relative_path(task["evidence_path"])
            require(task["evidence_path"].startswith(".decomp/evidence/"),
                    "evidence must stay in ignored local storage")
            require(task["ranges"], "missing body ranges")
            contains_entry = False
            for span in task["ranges"]:
                start, end = int(span["start"], 16), int(span["end_exclusive"], 16)
                require(0 <= start < end <= baseline["bytes"],
                        "range outside initial flat container model")
                contains_entry |= start <= entry < end
                spans.append((start, end, ident))
            require(contains_entry, "entry outside body")
            require(set(("bootstrap-inventory", "bootstrap-toolchain", "bootstrap-verifier"))
                    <= set(task["depends_on"]), "function missing bootstrap dependencies")
        tasks[ident] = task
    spans.sort()
    for left, right in zip(spans, spans[1:]):
        require(left[1] <= right[0], f"overlapping function ownership: {left[2]}, {right[2]}")
    visiting, visited = set(), set()

    def visit(ident):
        require(ident in tasks, f"unknown dependency: {ident}")
        require(ident not in visiting, "dependency cycle")
        if ident in visited:
            return
        visiting.add(ident)
        for dep in tasks[ident]["depends_on"]:
            visit(dep)
        visiting.remove(ident)
        visited.add(ident)

    for ident in tasks:
        visit(ident)
    return baseline, tasks


def evidence_check(root, baseline, task):
    if task["kind"] != "function":
        return
    path = root / task["evidence_path"]
    require(packet_hash(path) == task["evidence_sha256"], "evidence packet changed")
    meta = read_json(path / "metadata.json")
    require(meta["baseline_sha256"] == baseline["sha256"], "packet baseline mismatch")
    for key in ("entry", "mode", "ranges"):
        require(meta[key] == task[key], f"packet {key} mismatch")
    for name in ("listing.txt", "context.md"):
        require((path / name).is_file(), f"packet missing {name}")
    if "comparison_scope" in task:
        comparator = __import__(COMPARATORS[task["comparison_scope"]])
        comparison = task["comparison"]
        lock = comparator.load_lock(root / comparison["lock_path"], comparison["lock_sha256"])
        # Call locks extend an immutable leaf parent. Never treat a fixed
        # external address as a reconstructed callee or flatten away its pins.
        if task["comparison_scope"] == "armcc5-direct-call-experiment-v1":
            extension, parent = lock
            lock = {**parent, "tasks": extension["tasks"]}
        definition = {k: v for k, v in task.items() if k != "comparison"}
        require(lock["tasks"][task["id"]]["task_sha256"] ==
                digest((json.dumps(definition, sort_keys=True, indent=2) + "\n").encode()),
                "task differs from comparison lock")
        require(lock["baseline"]["sha256"] == baseline["sha256"] and
                lock["baseline_bytes"] == baseline["bytes"], "comparison baseline mismatch")
        if task["comparison_scope"] in ("armcc5-leaf-feedback-v1", "armcc5-direct-call-experiment-v1"):
            pinned = lock["tasks"][task["id"]]
            require(len(task["ranges"]) == 1 and
                    int(task["ranges"][0]["start"], 16) == int(pinned["entry"], 16) and
                    int(task["ranges"][0]["end_exclusive"], 16) == int(pinned["end_exclusive"], 16),
                    "comparison range mismatch")
            require(all(task[k] == pinned[k] for k in ("entry", "mode", "signature", "abi_status")),
                    "comparison ABI/entry mismatch")
            if task["comparison_scope"] == "armcc5-direct-call-experiment-v1":
                require(all(task[k] == pinned[k] for k in ("extern_functions", "calls")),
                        "comparison call contract mismatch")


def connect(state):
    state.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(state, timeout=15, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY, spec_hash TEXT NOT NULL, worker TEXT NOT NULL,
        state TEXT NOT NULL, updated TEXT NOT NULL, report TEXT,
        report_hash TEXT, reviewer TEXT, note TEXT)""")
    return db


def rows(db, tasks):
    result = {r["id"]: dict(r) for r in db.execute("SELECT * FROM tasks")}
    for ident, row in result.items():
        require(ident in tasks and row["spec_hash"] == digest(canonical(tasks[ident])),
                f"task spec changed after assignment: {ident}; reconcile state deliberately")
    return result


def ready(task, states, tasks):
    # Scheduling dependencies are not machine-code dependencies or certification.
    # Bootstrap review uses accepted; function drafts use reviewed, never matched.
    return all(states.get(dep, {}).get("state") ==
               ("accepted" if tasks[dep]["kind"] == "bootstrap" else "reviewed")
               for dep in task["depends_on"])


def preparation_ready(root, task=None):
    path = root / "decomp/preparation.json"
    if not path.exists():
        return False  # Fail closed: deleting the gate must not enable workers.
    gate = read_json(path)
    require(gate.get("schema_version") == 1 and isinstance(gate.get("ready"), bool),
            "invalid preparation gate")
    if gate["ready"]:
        ids = gate.get("allowed_function_ids")
        require(isinstance(ids, list) and all(isinstance(i, str) and IDENTIFIER.fullmatch(i) for i in ids)
                and len(set(ids)) == len(ids), "ready gate requires explicit function scope")
        if "batch" in gate:
            import reconstruction
            batch = reconstruction.load_batch(root, gate['batch'], local=True)
            require(set(ids) == set(batch['tasks']), "batch gate membership mismatch")
        if task is not None:
            return task["id"] in ids
    return gate["ready"]


def prompt(root, baseline, task, worker):
    evidence_check(root, baseline, task)
    output = (root / "decomp/prompts/worker.md").read_text() + (
        f"\n## Assignment\n\nWorker: `{worker}`\n\n"
        f"Baseline: `{baseline['id']}` / `{baseline['sha256']}`\n\n"
        "```json\n" + json.dumps(task, indent=2) + "\n```\n"
    )
    if "comparison" in task:
        c = task["comparison"]
        script = COMPARATORS[task["comparison_scope"]] + ".py"
        command = ["python3", str(root / "tools" / script), "verify", "--lock",
                   str(root / c["lock_path"]), "--lock-sha256", c["lock_sha256"], "--task", task["id"],
                   "--source", f"decomp/src/{task['id']}.c", "--output", f"decomp/results/{task['id']}/attempt-01"]
        output += (f"\nMain coordinator root (not a worker mount): {root}\n\n"
                   f"Evidence directory: {root / task['evidence_path']}\n\n"
                   "Working directory for this command: the assigned worker worktree. Change only the attempt output suffix for each build; "
                   "never reuse an output directory. Exit 0 means exact range bytes, 2 means a byte/size mismatch, "
                   "1 means rejected source/build or changed trusted inputs. None certifies a recovered function.\n\n"
                   "For ARMCC tasks, send the command and source path to the coordinator build service; "
                   "workers must not receive access to the private licensed Wine prefix. The coordinator "
                   "runs one compiler job at a time and returns the redacted attempt outputs. A busy-lock "
                   "rejection is a scheduling retry, not a source attempt.\n\n"
                   "```sh\n" + shlex.join(command) + "\n```\n")
    return output


def execute(args):
    root = args.root.resolve()
    baseline, tasks = load_tasks(root)
    state = (args.state or root / ".decomp/queue.sqlite3").resolve()
    if args.command == "check":
        if args.local:
            for task in tasks.values():
                evidence_check(root, baseline, task)
        print(f"Valid scaffold: {len(tasks)} tasks; " +
              ("local evidence/tool locks verified; " if args.local else "") +
              "whole-image verifier not implemented; matching coverage unknown")
        if not preparation_ready(root):
            print("Preparation BLOCKED: function claims disabled; see decomp/preparation.json")
        else:
            print("Preparation READY for the reviewed scope only; user-assigned run/budget still required")
        return
    if args.command == "verify-input":
        data = args.image.read_bytes()
        require(len(data) == baseline["bytes"] and digest(data) == baseline["sha256"],
                "firmware resource identity mismatch")
        payload = data[baseline["payload_offset"]:]
        require(len(payload) == baseline["payload_bytes"] and
                digest(payload) == baseline["payload_sha256"], "payload identity mismatch")
        print("Input identity verified only; no analysis or device access")
        return
    if args.command == "hash-packet":
        print(packet_hash(args.directory))
        return
    if args.command == "status" and not state.exists():
        states = {}
    else:
        db = connect(state)
        try:
            db.execute("BEGIN IMMEDIATE")
            states = rows(db, tasks)
            if args.command != "status":
                require(args.task in tasks, f"unknown task: {args.task}")
                task = tasks[args.task]
                row = states.get(args.task)
                now = datetime.now(timezone.utc).isoformat()
                if args.command == "claim":
                    require(IDENTIFIER.fullmatch(args.worker), "invalid worker ID")
                    require(row is None or row["state"] == "queued", "task already owned")
                    require(ready(task, states, tasks), "scheduling dependencies not reviewed/accepted")
                    require(task["kind"] != "function" or preparation_ready(root, task),
                            "preparation blockers unresolved; function claims disabled")
                    packet = prompt(root, baseline, task, args.worker)
                    db.execute("INSERT OR REPLACE INTO tasks VALUES (?,?,?,?,?,NULL,NULL,NULL,NULL)",
                               (args.task, digest(canonical(task)), args.worker, "claimed", now))
                    print(packet)
                elif args.command == "packet":
                    require(row and row["state"] == "claimed", "task not claimed")
                    print(prompt(root, baseline, task, row["worker"]))
                elif args.command in ("release", "submit"):
                    require(row and row["state"] == "claimed" and row["worker"] == args.worker,
                            "claim owner mismatch or task not claimed")
                    if args.command == "release":
                        db.execute("UPDATE tasks SET state='queued', updated=?, note=? WHERE id=?",
                                   (now, args.note, args.task))
                    else:
                        report = args.report.resolve()
                        data = read_json(report)
                        require(data["task"] == args.task and data["worker"] == args.worker,
                                "result identity mismatch")
                        require(data["status"] in ("draft", "blocked"),
                                "workers submit drafts/blockers, never self-certified matches")
                        for key in ("observations", "inferences", "open_questions", "validation"):
                            require(isinstance(data[key], list), f"result {key} must be a list")
                        require(data["validation"], "record validation performed or unavailable")
                        evidence_check(root, baseline, task)
                        db.execute("UPDATE tasks SET state='submitted', updated=?, report=?, "
                                   "report_hash=? WHERE id=?",
                                   (now, str(report), digest(report.read_bytes()), args.task))
                elif args.command == "review":
                    require(row and row["state"] == "submitted", "task not submitted")
                    require(IDENTIFIER.fullmatch(args.reviewer) and args.reviewer != row["worker"],
                            "independent reviewer ID required")
                    report = Path(row["report"])
                    if args.decision in ("accept", "block"):
                        require(digest(report.read_bytes()) == row["report_hash"],
                                "submitted report changed; requeue before resubmitting")
                        evidence_check(root, baseline, task)
                    if args.decision == "accept":
                        require(read_json(report)["status"] == "draft", "blocked result cannot pass")
                        next_state = "accepted" if task["kind"] == "bootstrap" else "reviewed"
                    elif args.decision == "block":
                        require(read_json(report)["status"] == "blocked", "block requires evidence-backed blocked report")
                        require(args.note.strip(), "block requires reviewer explanation")
                        next_state = "blocked"
                    else:
                        next_state = "queued"
                    db.execute("UPDATE tasks SET state=?, updated=?, reviewer=?, note=? WHERE id=?",
                               (next_state, now, args.reviewer, args.note, args.task))
                    print(f"{args.task}: {next_state}; this does not certify a binary match")
            db.execute("COMMIT")
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()
    if args.command == "status":
        for ident, task in tasks.items():
            row = states.get(ident, {})
            status = row.get("state", "queued")
            if status == "queued" and not ready(task, states, tasks):
                status = "waiting"
            if status == "queued" and task["kind"] == "function" and not preparation_ready(root, task):
                status = "blocked"
            print(f"{ident:28} {status:10} {row.get('worker', '-')}")
        count = sum(task["kind"] == "function" for task in tasks.values())
        print(f"\nFunction tasks: {count}; complete inventory: unknown; matching coverage: unknown")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--state", type=Path, help="coordinator's shared local SQLite file")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("check").add_argument("--local", action="store_true",
                                         help="also verify local function packets and compiler locks")
    sub.add_parser("verify-input").add_argument("image", type=Path)
    sub.add_parser("hash-packet").add_argument("directory", type=Path)
    for name in ("claim", "packet", "release", "submit", "review"):
        child = sub.add_parser(name)
        child.add_argument("task")
        if name in ("claim", "release", "submit"):
            child.add_argument("--worker", required=True)
        if name == "submit":
            child.add_argument("--report", type=Path, required=True)
        if name == "review":
            child.add_argument("--reviewer", required=True)
            child.add_argument("--decision", choices=("accept", "requeue", "block"), required=True)
        if name in ("release", "review"):
            child.add_argument("--note", required=True)
    try:
        execute(parser.parse_args())
    except (ValueError, KeyError, TypeError, OSError, sqlite3.Error) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
