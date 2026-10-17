#!/usr/bin/env python3
"""Read-only byte/dependency accounting and reviewed-batch admission (stdlib).

No model jobs, compiler invocation, queue writes, implicit inventory approval,
match certification, image construction or hardware operations.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

import decomp

SCOPES = {'armcc5-leaf-feedback-v1', 'armcc5-direct-call-experiment-v1'}
require = decomp.require


def reviewed_text(value):
    return isinstance(value, str) and bool(value.strip()) and 'REPLACE' not in value


def pinned_file(root, pin):
    require(isinstance(pin, dict) and set(pin) == {'path', 'sha256'}, 'invalid file pin')
    name = pin['path']
    decomp.relative_path(name)
    path = root / name
    require(path.resolve().is_relative_to(root.resolve()) and
            not any(p.is_symlink() for p in (path, *path.parents) if p == root or root in p.parents),
            'symlink or escaping file pin')
    require(path.is_file() and decomp.SHA256.fullmatch(pin['sha256']) and
            hashlib.sha256(path.read_bytes()).hexdigest() == pin['sha256'], 'changed/missing pinned file: '+name)
    return path


def validate_ledger(ledger, baseline):
    require(ledger['schema_version'] == 1 and ledger['baseline_sha256'] == baseline['sha256'] and
            ledger['baseline_bytes'] == baseline['bytes'], 'ledger baseline/schema mismatch')
    cursor, names = 0, set()
    for region in ledger['regions']:
        require(decomp.IDENTIFIER.fullmatch(region['id']) and region['id'] not in names, 'duplicate/invalid region')
        names.add(region['id'])
        start, end = int(region['start'], 16), int(region['end_exclusive'], 16)
        require(start == cursor and start < end <= baseline['bytes'], 'region gap, overlap, order or bounds')
        require(region['treatment'] == 'unresolved' and region['evidence'].strip(),
                'region reconstruction is not certified by this planning ledger')
        cursor = end
    require(cursor == baseline['bytes'], 'ledger must account for complete selected image')
    dependencies = {}
    for row in ledger['dependencies']:
        ident = row['id']
        require(decomp.IDENTIFIER.fullmatch(ident) and ident not in dependencies, 'duplicate/invalid dependency')
        require(row['state'] in ('unresolved', 'observed_not_reconstructed'), 'unsupported dependency claim')
        require(row['address_space'] in ('container', 'ram', 'external_unknown'), 'explicit address space required')
        require(isinstance(row['required_for_hardware'], bool) and row['evidence'].strip() and
                row['next_action'].strip(), 'dependency evidence and action required')
        for address in row.get('addresses', []):
            value = int(address, 16)
            require(0 <= value < 2**32 and row['address_space'] != 'external_unknown', 'invalid located dependency')
            if row['address_space'] == 'container':
                require(value < baseline['bytes'], 'container dependency outside baseline')
        dependencies[ident] = row
    return dependencies


def read_states(root, tasks):
    path = root / '.decomp/queue.sqlite3'
    if not path.exists():
        return {}
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        return decomp.rows(db, tasks)


def report(root):
    baseline, tasks = decomp.load_tasks(root)
    ledger = decomp.read_json(root / 'decomp/reconstruction.json')
    dependencies = validate_ledger(ledger, baseline)
    states = read_states(root, tasks)
    declared, reviewed, stale = 0, 0, []
    for ident, task in tasks.items():
        if task['kind'] != 'function':
            continue
        size = sum(int(r['end_exclusive'], 16)-int(r['start'], 16) for r in task['ranges'])
        declared += size
        row = states.get(ident, {})
        if row.get('state') != 'reviewed':
            continue
        source = root / f'decomp/src/{ident}.c'
        result = root / f'decomp/results/{ident}/result.json'
        # Both integration and the exact submitted report must still agree.
        if (not source.is_file() or not result.is_file() or source.is_symlink() or result.is_symlink() or
                decomp.digest(result.read_bytes()) != row['report_hash'] or
                decomp.read_json(result).get('coordinator_review', {}).get('source_sha256') !=
                decomp.digest(source.read_bytes())):
            stale.append(ident)
        else:
            reviewed += size
    return {'baseline_bytes': baseline['bytes'], 'accounted_container_bytes': baseline['bytes'],
            'declared_function_bytes': declared, 'unassigned_container_bytes': baseline['bytes']-declared,
            'reviewed_source_bytes': reviewed, 'stale_review_integrations': stale,
            'matching_coverage': 'unknown', 'whole_image_verified': False,
            'hardware_gate': 'closed', 'dependencies': dependencies,
            'note': 'Accounting and reviewed-source bytes are not certified matching coverage.'}


def load_batch(root, pin, *, local=False):
    """Validate a frozen intake manifest. This neither activates it nor claims work."""
    path = pinned_file(root, pin)
    require(pin['path'].startswith('decomp/batches/'), 'batch must be coordinator-owned')
    batch = decomp.read_json(path)
    baseline, tasks = decomp.load_tasks(root)
    require(batch['schema_version'] == 1 and batch['status'] == 'prepared' and
            batch['baseline_sha256'] == baseline['sha256'], 'unprepared batch or wrong baseline')
    require(decomp.IDENTIFIER.fullmatch(batch['id']) and reviewed_text(batch['reviewer']) and
            reviewed_text(batch['review_note']), 'batch review identity required')
    ledger_path = pinned_file(root, batch['ledger'])
    ledger = decomp.read_json(ledger_path)
    dependencies = validate_ledger(ledger, baseline)
    require(isinstance(batch['tasks'], dict) and batch['tasks'], 'explicit nonempty batch membership required')
    for ident, digest in batch['tasks'].items():
        require(ident in tasks and tasks[ident]['kind'] == 'function', 'unknown/nonfunction batch member')
        task = tasks[ident]
        require(decomp.digest(decomp.canonical(task)) == digest, 'batch task definition changed')
        require(task.get('comparison_scope') in SCOPES, 'unsupported batch comparator')
        # The selected task lock already pins signature, ranges and all calls.
        if local:
            decomp.evidence_check(root, baseline, task)
    contracts = batch['call_contracts']
    expected = {(ident, callee) for ident in batch['tasks']
                for callee in tasks[ident].get('extern_functions', {})}
    actual = set()
    for contract in contracts:
        key = (contract['caller'], contract['callee'])
        require(key in expected and key not in actual, 'unexpected/duplicate callee contract')
        actual.add(key)
        require(contract['treatment'] == 'fixed_address_not_reconstructed', 'fixed symbol is not recovered code')
        require(contract['dependency'] in dependencies and
                dependencies[contract['dependency']]['address_space'] == 'container', 'missing callee dependency')
        target = tasks[key[0]]['extern_functions'][key[1]]['entry']
        require(int(target, 16) in [int(a, 16) for a in dependencies[contract['dependency']].get('addresses', [])],
                'callee dependency address mismatch')
        for field in ('arguments', 'return_value', 'register_clobbers', 'memory_effects', 'evidence'):
            require(reviewed_text(contract[field]), 'incomplete callee ABI/effects review')
    require(actual == expected, 'missing callee contract')
    require(set(batch['qualification']) == {tasks[t]['comparison_scope'] for t in batch['tasks']},
            'missing/extra comparator qualification')
    require(set(batch['profile_locks']) == set(batch['qualification']), 'qualification profile locks required')
    for scope, proof in batch['qualification'].items():
        evidence = decomp.read_json(pinned_file(root, proof))
        profile_pin = batch['profile_locks'][scope]
        profile_path = pinned_file(root, profile_pin)
        require(evidence.get('certified_match') is False and evidence.get('results') and
                all(r.get('passed') is True for r in evidence['results']), 'invalid qualification report')
        # Qualification is reviewed evidence, not a checkbox or a model score.
        # Call profiles require both stock samples and a fresh unchanged rebuild.
        if scope == 'armcc5-direct-call-experiment-v1':
            require(evidence.get('scope') == 'bounded-stock-thumb-call-qualification' and
                    evidence.get('call_lock_sha256') == profile_pin['sha256'] and
                    any(r.get('control', '').endswith('/candidate') and r.get('result') == 'exact-range-bytes'
                        for r in evidence['results']) and
                    any(r.get('control', '').endswith('/independent-rebuild') and r.get('result') == 'exact-range-bytes'
                        for r in evidence['results']) and
                    any(r.get('result') in ('mismatch', 'rejected') for r in evidence['results']),
                    'stock call qualification/rebuild/negative controls required')
            if local:
                import armcc_calls
                qualified, parent = armcc_calls.load_lock(profile_path, profile_pin['sha256'])
                for ident in batch['tasks']:
                    task = tasks[ident]
                    if task['comparison_scope'] != scope:
                        continue
                    candidate, candidate_parent = armcc_calls.load_lock(root / task['comparison']['lock_path'],
                                                                       task['comparison']['lock_sha256'])
                    require(candidate['extension'] == qualified['extension'] and candidate_parent == parent,
                            'call profile differs from qualified verifier/parent')
        elif local:
            import armcc_compare
            qualified = armcc_compare.load_lock(profile_path, profile_pin['sha256'])
            fields = ('code','compile_flags','link_flags','ast_flags','tools','tool_trees',
                      'host_libraries','baseline','baseline_bytes')
            for ident in batch['tasks']:
                task = tasks[ident]
                if task['comparison_scope'] == scope:
                    selected = armcc_compare.load_lock(root / task['comparison']['lock_path'],
                                                       task['comparison']['lock_sha256'])
                    require(all(selected[k] == qualified[k] for k in fields), 'leaf profile differs from qualification')
    return batch


def batch_plan(root, pin, *, local=False):
    batch = load_batch(root, pin, local=local)
    _, tasks = decomp.load_tasks(root)
    states = read_states(root, tasks)
    plan = {}
    for ident in batch['tasks']:
        state = states.get(ident, {}).get('state', 'queued')
        if state != 'queued':
            plan[ident] = state  # Never propose reclaiming reviewed/blocked work.
        elif not decomp.ready(tasks[ident], states, tasks):
            plan[ident] = 'waiting_for_scheduling_dependencies'
        else:
            plan[ident] = 'eligible_after_run_preflight'
    return {'batch': batch['id'], 'tasks': plan, 'activated': False,
            'model_jobs_started': 0, 'note': 'Still requires committed preparation, selected gate/policy, explicit run and live quota.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--batch', help='validate a frozen coordinator batch relative path')
    parser.add_argument('--sha256')
    parser.add_argument('--local', action='store_true')
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        if args.batch:
            print(json.dumps(batch_plan(root, {'path': args.batch, 'sha256': args.sha256}, local=args.local), indent=2))
        else:
            print(json.dumps(report(root), indent=2))
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as error:
        parser.exit(1, 'REJECTED: '+str(error)+'\n')


if __name__ == '__main__':
    main()
