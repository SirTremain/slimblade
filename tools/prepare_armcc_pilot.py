#!/usr/bin/env python3
"""Coordinator-only, one-time versioned ARMCC lock proposal; never opens a gate."""
import argparse
import json
from pathlib import Path
import sqlite3

import armcc_compare as ac
import decomp

SIGNATURES = {
    'fn_00003b48': 'unsigned int (unsigned int, unsigned int)',
    'fn_00003bb4': 'unsigned int (unsigned int, unsigned int)',
    'fn_0000e4ee': 'unsigned short (const unsigned char *)',
    'fn_0000e4fc': 'unsigned int (const unsigned char *)',
    'fn_0000e540': 'void (unsigned char *, unsigned short)',
    'fn_0000e548': 'void (unsigned char *, unsigned int)',
}


def prepare(root, output):
    root, output = root.resolve(), output.resolve()
    ac.require(not decomp.preparation_ready(root), 'close gate before a deliberate profile migration')
    ac.require(not output.exists() and output.is_relative_to(root / '.decomp'),
               'new ignored output directory required')
    baseline, tasks = decomp.load_tasks(root)
    functions = [t for t in tasks.values() if t['kind'] == 'function']
    ac.require({t['id'] for t in functions} == set(SIGNATURES), 'unexpected pilot assignment set')
    queue = root / '.decomp/queue.sqlite3'
    if queue.exists():
        with sqlite3.connect(queue.as_uri() + '?mode=ro', uri=True) as db:
            assigned = {row[0] for row in db.execute('select id from tasks')}
        ac.require(not assigned.intersection(SIGNATURES), 'assigned functions require manual state reconciliation')
    for task in functions:
        ac.require(task['comparison_scope'] == ac.sc.SCOPE, 'expected preserved original pilot profile')
        decomp.evidence_check(root, baseline, task)
    original = (root / 'decomp/functions.json').read_bytes()
    proposal = json.loads(original)
    manifest = {'baseline_sha256': baseline['sha256'], 'tasks': []}
    for task in proposal['functions']:
        task.update(comparison_scope=ac.SCOPE, signature=SIGNATURES[task['id']],
                    abi_status='hypothesis_requires_review')
        task['instructions'] = (
            'Read the immutable packet and docs/pilot.md. Recover this leaf only; no calls or absolute '
            'globals are supported. Name the C function exactly as the task ID. Review the pinned '
            'signature hypothesis against callers and document ambiguities; propose any ABI correction '
            'to the coordinator instead of changing the lock. Use the calibrated ARMCC5 profile through '
            'the coordinator build service. Never change flags, ranges or reference bytes. Stop at '
            '20 minutes/8 builds/3 non-improving attempts. Submit draft or blocked; never matched.')
        definition = {k: v for k, v in task.items() if k != 'comparison'}
        manifest['tasks'].append({k: task[k] for k in ('id', 'entry', 'mode', 'signature', 'abi_status')})
        manifest['tasks'][-1].update(end_exclusive=task['ranges'][0]['end_exclusive'],
                                    task_sha256=ac.sc.base.sha(ac.sc.encode(definition)))
    output.mkdir(parents=True, mode=0o700)
    (output / 'prior-functions.json').write_bytes(original)
    packet = output / 'manifest.json'
    packet.write_bytes(ac.sc.encode(manifest))
    lock = output / 'lock.json'
    digest = ac.initialize(root, root / '.decomp/stock/stock-v4.49.bin', packet, lock)
    for task in proposal['functions']:
        task['comparison'] = {'lock_path': str(lock.relative_to(root)), 'lock_sha256': digest}
    (output / 'functions.json').write_bytes(ac.sc.encode(proposal))
    for name in ('prior-functions.json', 'manifest.json', 'functions.json'):
        (output / name).chmod(0o444)
    return {'lock_sha256': digest, 'proposal': str(output / 'functions.json'), 'gate_changed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.root, args.output), indent=2))
