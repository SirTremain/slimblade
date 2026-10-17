#!/usr/bin/env python3
"""Coordinator-only stock-call qualification and ten-leaf regression; no agents.

The two tiny wrappers are calibration specimens, not new worker assignments.
All generated source, compiler output and original bytes stay in ignored storage.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
import armcc_calls as cc
import swarm_runtime as sr
from swarm_account import monitored_account

LOCK = ROOT / '.decomp/direct-calls-v1/lock.json'
DIGEST = '973b9272d7345924e44b5084437b05557e18731afbcea257fee37b593ac1c3bc'
LEAF_LOCKS = (
    ('.decomp/pilot-armcc5-v1/lock.json', '2c2e3416849c68cade707434e9589c8c2806721fef9f02bd7b68c5286abc0c4a'),
    ('.decomp/next-leaves-v2/lock.json', '282c4bd898a44217d491dceef956452aee8f0eabba834b5c85f36ec87c92f76b'))


def inside(output):
    cc.require(not output.exists(), 'never overwrite qualification evidence')
    lock, parent = cc.load_lock(LOCK, DIGEST)
    output.mkdir(parents=True, mode=0o700)
    results = []
    for ident, task in lock['tasks'].items():
        callee, contract = next(iter(task['extern_functions'].items()))
        return_type = contract['signature'].split(' (')[0]
        source = (f'extern {return_type} {callee}(void);\n'
                  f'unsigned int {ident}(void) {{ {callee}(); return 0u; }}\n')
        candidate = output / f'{ident}.c'
        candidate.write_text(source)
        for label in ('candidate', 'independent-rebuild'):
            result = cc.verify(LOCK, DIGEST, ident, candidate, output / f'{ident}-{label}')
            cc.require(result['result'] == 'exact-range-bytes', 'stock calibration mismatch: '+ident)
            results.append({'control': ident+'/'+label, 'passed': True, **result})
        # A changed result and omitted side-effecting call must fail. A missing
        # relocation may be rejected earlier than the full byte comparison.
        for label, changed in [('wrong-result', source.replace('return 0u', 'return 1u')),
                               ('missing-call', source.replace(f'{callee}(); ', ''))]:
            candidate = output / f'{ident}-{label}.c'
            candidate.write_text(changed)
            out = output / f'{ident}-{label}'
            try:
                result = cc.verify(LOCK, DIGEST, ident, candidate, out)
                cc.require(result['result'] != 'exact-range-bytes', 'negative control unexpectedly exact')
            except ValueError as error:
                # Only an explicit comparator rejection is a passing negative;
                # missing tools or broken pins must not count as validation.
                rejection = out / 'rejection.json'
                cc.require(label == 'missing-call' and rejection.exists() and
                           'missing direct-call relocations' in str(error), 'unexpected control failure')
                result = json.loads(rejection.read_text())
            results.append({'control': ident+'/'+label, 'passed': True, **result})
    for path, digest in LEAF_LOCKS:
        leaf = cc.ac.load_lock(ROOT / path, digest)
        for ident in leaf['tasks']:
            result = cc.ac.verify(ROOT / path, digest, ident, ROOT / f'decomp/src/{ident}.c',
                                  output / ('regression-'+ident))
            cc.require(result['result'] == 'exact-range-bytes', 'existing leaf regressed: '+ident)
            results.append({'control': 'regression/'+ident, 'passed': True, **result})
    cc.load_lock(LOCK, DIGEST)
    report = {'schema_version': 1, 'scope': 'bounded-stock-thumb-call-qualification',
              'certified_match': False, 'matching_coverage': 'unknown',
              'external_callees_reconstructed': False, 'call_lock_sha256': DIGEST,
              'script': cc.ac.sc.base.pin(Path(__file__).resolve()), 'results': results}
    (output / 'report.json').write_bytes(cc.ac.sc.encode(report))
    print(json.dumps({'passed': len(results), 'report': str(output / 'report.json')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--inside', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    cc.require(out.is_relative_to(ROOT / '.decomp') and out != ROOT / '.decomp', 'fresh ignored output required')
    if args.inside:
        inside(out)
    else:
        state = ROOT / '.decomp/swarm'
        policy = sr.policy(ROOT)
        sr.require(not (state / 'PAUSED.json').exists(), 'paused; explicit resume required')
        with sr.compiler_slot(state / 'locks'), monitored_account(state, policy['quota_window_resets_at']) as quota:
            result = sr.supervise([sys.executable, str(Path(__file__).resolve()), '--inside', '--output', str(out)],
                                  '', out.with_name(out.name+'-process'), quota, seconds=600)
        sr.require(result.get('returncode') == 0, 'qualification failed; inspect retained evidence')
        print(json.dumps(result, indent=2))
