#!/usr/bin/env python3
"""Bounded coordinator build/rebuild around explicitly pinned comparators.

Run outside the outer Codex sandbox with approval; the existing compiler
sandbox remains enabled. No worker-supplied command is executed.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time

import swarm_runtime as sr
from swarm_account import monitored_account
from swarm_worker import assignment
from swarm_runtime import attempt_budget
import decomp


def comparator_script(root, task):
    """Trusted dispatch only; task data cannot supply a command or module path."""
    scope = task.get('comparison_scope')
    sr.require(scope in ('armcc5-leaf-feedback-v1', 'armcc5-direct-call-experiment-v1'),
               'unsupported guarded build scope')
    return root / 'tools' / (decomp.COMPARATORS[scope] + '.py')


def build(args):
    root, worktree = args.root.resolve(), args.worktree.resolve()
    state = root / '.decomp/swarm'
    policy = sr.policy(root, args.task)
    sr.require(not (state / 'PAUSED.json').exists(), 'run paused; explicit user resume required')
    with sr.compiler_slot(state / 'locks'), sr.task_lock(state / 'locks', args.task):
        task, _, remaining_seconds = assignment(root, worktree, args.task, args.worker,
                                               review=args.review)
        deadline = time.monotonic() + min(600, remaining_seconds)
        sys.path.insert(0, str(root / 'tools'))
        import armcc_compare as ac
        # Explicitly audit that the actual module is the main coordinator copy.
        sr.require(Path(ac.__file__).resolve() == root / 'tools/armcc_compare.py',
                   'use the coordinator verifier, not a worker copy')
        folder = state / 'builds' / args.task
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        ledger = folder / 'attempts.json'
        history = json.loads(ledger.read_text()) if ledger.exists() else []
        source = sr.safe_path(worktree, f'decomp/src/{args.task}.c')
        source_hash = ac.sc.base.sha(source.read_bytes())
        if args.review:
            sr.require(history and history[-1].get('differing_bytes') == 0 and
                       history[-1]['source_sha256'] == source_hash,
                       'independent rebuild requires an unchanged exact draft')
            output = folder / 'independent-review'
        else:
            attempt_budget(history)
            output = folder / f'attempt-{len(history)+1:02d}'
        sr.require(not output.exists(), 'never overwrite build evidence')
        entry = {'source_sha256': source_hash, 'result': 'started', 'differing_bytes': None,
                 'output': str(output.relative_to(root))}
        if not args.review:
            # Count interruptions/rejections; never make a crashed attempt free.
            history.append(entry)
            sr.write_json(ledger, history)
        try:
            cmd = [sys.executable, str(comparator_script(root, task)), 'verify',
                '--lock', str(root / task['comparison']['lock_path']),
                '--lock-sha256', task['comparison']['lock_sha256'],
                '--task', args.task, '--source', str(source), '--output', str(output)]
            with monitored_account(state, policy['quota_window_resets_at']) as quota:
                run = sr.supervise(cmd, '', output.with_name(output.name + '-process'),
                                   quota, seconds=deadline-time.monotonic())
            if run.get('returncode') not in (0, 2):
                rejection = output / 'rejection.json'
                reason = (json.loads(rejection.read_text())['reason'] if rejection.exists()
                          else 'compiler process failed before comparison')
                raise RuntimeError(reason)
            result = json.loads((output / 'comparison.json').read_text())
        except Exception as error:
            entry.update(result='rejected', error=ac.runner.scrub(str(error)))
            # The prefix lock may be busy with a different task. This is a
            # scheduling collision, not a source attempt; preserve its report.
            if 'compiler busy; coordinator must serialize builds and retry' in str(error):
                entry['result'] = 'compiler-busy'
            raise
        else:
            entry.update(result=result['result'], differing_bytes=result['differing_bytes'])
            return result
        finally:
            if not args.review:
                sr.write_json(ledger, history)
            else:
                sr.write_json(folder / 'review-status.json', entry)


if __name__ == '__main__':
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--worktree', type=Path, required=True)
    parser.add_argument('--task', required=True)
    parser.add_argument('--worker', required=True)
    parser.add_argument('--review', action='store_true')
    args = parser.parse_args()
    print(json.dumps(build(args), indent=2))
