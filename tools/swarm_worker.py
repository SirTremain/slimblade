#!/usr/bin/env python3
"""Run one explicitly assigned worker turn, never an autonomous firmware swarm.

The Goal coordinator owns claims, compiler calls, review and subsequent turns.
Each invocation has real OS isolation, a wall-clock bound and live quota guard.
"""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

import swarm_runtime as sr
from swarm_account import monitored_account


def prepare_outputs(worktree, allowed):
    for relative in allowed:
        path = sr.safe_path(worktree, relative)
        if relative.endswith('/'):
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.touch()


def git(worktree, *args):
    return subprocess.run(['git', '-C', str(worktree), *args], capture_output=True,
                          check=True, text=True, timeout=15).stdout.strip()


def check_worker_diff(worktree, allowed):
    changed = subprocess.run(['git', '-C', str(worktree), 'status', '--porcelain=v1',
                              '-z', '--untracked-files=all'], capture_output=True,
                             check=True, timeout=15).stdout.decode().split('\0')
    for item in filter(None, changed):
        sr.require(len(item) > 3 and 'R' not in item[:2] and 'C' not in item[:2],
                   'unexpected rename/copy in worker worktree')
        name = item[3:]
        sr.require(any(name.startswith(p) if p.endswith('/') else name == p for p in allowed),
                   'out-of-assignment worker change: ' + name)
        file = sr.safe_path(worktree, name)
        sr.require(not file.exists() or file.is_file(), 'nonregular worker result')


def assignment(root, worktree, task_id, worker, *, review=False):
    # Use the actual coordinator's pinned verifier modules, not worktree copies.
    sys.path.insert(0, str(root / 'tools'))
    import decomp
    sr.require(Path(decomp.__file__).resolve() == root / 'tools/decomp.py',
               'use the coordinator queue tools, not a worker copy')
    baseline, tasks = decomp.load_tasks(root)
    task = tasks[task_id]
    sr.require(task['kind'] == 'function' and decomp.preparation_ready(root, task),
               'task outside reviewed pilot gate')
    decomp.evidence_check(root, baseline, task)
    sr.require(worktree.is_relative_to(root / '.worktrees') and worktree != root,
               'worker must use a separate repository worktree')
    sr.require(Path(git(worktree, 'rev-parse', '--show-toplevel')).resolve() == worktree,
               'not a worktree root')
    sr.require(git(worktree, 'rev-parse', 'HEAD') == git(root, 'rev-parse', 'HEAD'),
               'worker base differs from coordinator commit')
    queue = root / '.decomp/queue.sqlite3'
    with sqlite3.connect(queue.as_uri() + '?mode=ro', uri=True) as db:
        row = db.execute('select worker,state,spec_hash,updated from tasks where id=?', (task_id,)).fetchone()
    sr.require(row is not None and row[:3] == (worker, 'claimed', decomp.digest(decomp.canonical(task))),
               'task must already be claimed by this worker with the unchanged definition')
    elapsed = datetime.now().timestamp() - datetime.fromisoformat(row[3]).timestamp()
    sr.require(elapsed >= 0 and (review or elapsed < 1200),
               'assigned task elapsed-time budget exhausted')
    check_worker_diff(worktree, task['allowed_paths'])
    return task, decomp.prompt(root, baseline, task, worker), 600 if review else 1200-elapsed


def run(args):
    sr.check_runtime()
    root, worktree = args.root.resolve(), args.worktree.resolve()
    policy = sr.policy(root)
    output = args.output.resolve()
    sr.require(output.is_relative_to(root / '.decomp/swarm') and not output.exists(),
               'use a fresh ignored coordinator run directory')
    state_dir = root / '.decomp/swarm'
    sr.require(not (state_dir / 'PAUSED.json').exists(), 'run paused; explicit user resume required')
    with sr.worker_slot(state_dir / 'slots'), sr.task_lock(state_dir / 'locks', args.task):
        task, prompt, remaining_seconds = assignment(root, worktree, args.task, args.worker)
        deadline = time.monotonic() + remaining_seconds
        ledger = state_dir / 'builds' / args.task / 'attempts.json'
        sr.attempt_budget(json.loads(ledger.read_text()) if ledger.exists() else [])
        allowed = task['allowed_paths']
        prepare_outputs(worktree, allowed)
        evidence = root / task['evidence_path']
        prompt += '\nSource commit for your report: ' + git(worktree, 'rev-parse', 'HEAD') + '\n'
        if args.feedback:
            feedback = args.feedback.read_text()
            sr.require(len(feedback.encode()) <= 64_000, 'feedback too large')
            prompt += '\n## Coordinator feedback for this bounded turn\n' + feedback
        prompt += '''\n## Enforced runner handoff
Your worktree is mounted as /workspace; your immutable evidence is /evidence.
Those replace host evidence/worktree paths printed earlier. The rest of the host,
compiler, credentials, queue and calibration source are not worker inputs.
Do not run the compiler, spawn agents or claim another task. Implement the next
source candidate and notes, then end this turn with a request for compilation.
The coordinator will compile, review and return feedback in a subsequent turn.
Compiler attempts and elapsed time are shared across turns, not reset by launch.
Do not claim a verified match before independent coordinator review.
'''
        with monitored_account(state_dir, policy['quota_window_resets_at']) as quota:
            quota()
            with tempfile.TemporaryDirectory(prefix='slimblade-worker-runtime-') as temp:
                runtime = Path(temp)
                cmd = sr.sandbox_command(worktree, evidence, runtime, allowed,
                    sr.codex_command(args.model, allowed), auth=Path.home() / '.codex/auth.json')
                state = sr.supervise(cmd, prompt, output, quota,
                                     seconds=min(args.seconds, deadline-time.monotonic()))
    check_worker_diff(worktree, allowed)
    sr.write_json(output / 'assignment.json', {'task': args.task, 'worker': args.worker,
        'model': args.model, 'worktree': str(worktree), 'source_commit': git(worktree, 'rev-parse', 'HEAD'),
        'allowed_paths': allowed, 'evidence_sha256': task['evidence_sha256'],
        'coordinator_review_required': True, 'certified_match': False})
    return state


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--worktree', type=Path, required=True)
    parser.add_argument('--task', required=True)
    parser.add_argument('--worker', required=True)
    parser.add_argument('--model', choices=sr.MODELS, default='gpt-6-luna')
    parser.add_argument('--seconds', type=int, default=1200)
    parser.add_argument('--feedback', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2))


if __name__ == '__main__':
    main()
