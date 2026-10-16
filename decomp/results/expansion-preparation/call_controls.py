#!/usr/bin/env python3
"""Bounded coordinator-only synthetic ARMCC call controls; no firmware workers."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
import armcc_calls as cc
import swarm_runtime as sr
from swarm_account import monitored_account

LOCK = ROOT / '.decomp/pilot-armcc5-v1/lock.json'
DIGEST = '2c2e3416849c68cade707434e9589c8c2806721fef9f02bd7b68c5286abc0c4a'
SOURCE = '''extern unsigned int fn_00002000(unsigned int);
extern unsigned int fn_00003000(unsigned int);
unsigned int fn_00001000(unsigned int a) {
    return fn_00002000(a) + fn_00003000(a + 1u);
}
'''


def inside(output):
    cc.require(not output.exists(), 'never overwrite controls')
    parent = cc.ac.load_lock(LOCK, DIGEST)
    output.mkdir(parents=True, mode=0o700)
    task = {'id': 'fn_00001000', 'entry': '0x1000', 'end_exclusive': '0x1040',
            'mode': 'thumb', 'signature': 'unsigned int (unsigned int)',
            'abi_status': 'hypothesis_requires_review',
            'extern_functions': {f'fn_{n:08x}': {'entry': hex(n), 'mode': 'thumb',
                                  'signature': 'unsigned int (unsigned int)'} for n in (0x2000, 0x3000)}}
    task['layout'] = cc.layout(task)
    results = []
    original = None
    for name, source in [('positive', SOURCE), ('unchanged-rebuild', SOURCE),
                         ('wrong-callee', SOURCE.replace('fn_00002000(a)', 'fn_00003000(a)')),
                         ('wrong-argument', SOURCE.replace('a + 1u', 'a + 2u')),
                         ('missing-call', SOURCE.replace('fn_00002000(a) + ', ''))]:
        out = output / name; out.mkdir()
        built = cc.build_sources(parent, {task['id']: task}, {task['id']: source}, out)[task['id']]
        data = built['bytes']
        if original is None:
            original = data
        result = cc.ac.sc.compare(original, data, 0x1000)
        exact = name in ('positive', 'unchanged-rebuild')
        cc.require((result['result'] == 'exact-range-bytes') == exact, 'synthetic control failed: '+name)
        results.append({'control': name, 'passed': True, **result, 'source_sha256': cc.ac.sc.base.sha(source.encode()),
                        'elf_sha256': built['elf_sha256'], 'relocations': built['relocations']})
    # All previous reviewed sources rebuilt unchanged through the original path.
    prior = output / 'prior-six'; prior.mkdir()
    sources = {name: (ROOT / f'decomp/src/{name}.c').read_text() for name in parent['tasks']}
    rebuilt = cc.ac.build_sources(parent, sources, prior)
    raw = Path(parent['baseline']['path']).read_bytes()
    for ident, built in rebuilt.items():
        task = parent['tasks'][ident]; start, end = cc.ac.validate_task(task, len(raw))
        result = cc.ac.sc.compare(raw[start:end], cc.ac.runtime_bytes(built['elf'], start), start)
        cc.require(result['result'] == 'exact-range-bytes', 'prior reviewed source regressed: '+ident)
        results.append({'control': 'prior-six/'+ident, 'passed': True, **result,
                        'source_sha256': cc.ac.sc.base.sha(sources[ident].encode())})
    cc.ac.load_lock(LOCK, DIGEST)
    report = {'scope': 'synthetic direct-call controls plus unchanged six-source regression',
              'certified_match': False, 'matching_coverage': 'unknown',
              'parent_lock_sha256': DIGEST, 'extension_sha256': cc.ac.sc.base.sha(Path(cc.__file__).read_bytes()),
              'control_script_sha256': cc.ac.sc.base.sha(Path(__file__).read_bytes()), 'results': results}
    (output / 'report.json').write_bytes(cc.ac.sc.encode(report))
    print(json.dumps({'passed': len(results), 'report': str(output / 'report.json')}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--inside', action='store_true')
    args = p.parse_args()
    output = args.output.resolve()
    cc.require(output.is_relative_to(ROOT / '.decomp'), 'ignored output required')
    if args.inside:
        inside(output)
    else:
        state = ROOT / '.decomp/swarm'
        policy = sr.policy(ROOT)
        sr.require(not (state / 'PAUSED.json').exists(), 'paused; explicit resume required')
        with sr.compiler_slot(state / 'locks'), monitored_account(state, policy['quota_window_resets_at']) as quota:
            result = sr.supervise([sys.executable, str(Path(__file__).resolve()), '--inside', '--output', str(output)],
                '', output.with_name(output.name+'-process'), quota, seconds=600)
        sr.require(result.get('returncode') == 0, 'control subprocess failed; inspect retained evidence')
        print(json.dumps(result, indent=2))
