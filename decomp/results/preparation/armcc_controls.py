#!/usr/bin/env python3
"""Explicit real-tool synthetic controls; never a stock oracle or worker job."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
import armcc_compare as ac

FIXTURES = [
    (0x1000, 'unsigned int', 'unsigned int a', 'return a+17u;', 'return a+18u;',
     'unsigned int (unsigned int)', 'changed-constant'),
    (0x1020, 'int', 'const unsigned char *p', 'return *p;', 'return (signed char)*p;',
     'int (const unsigned char *)', 'changed-signedness'),
    (0x1040, 'void', 'volatile unsigned int *p', '*p=7u;', '(void)p;',
     'void (volatile unsigned int *)', 'missing-store'),
    (0x1060, 'unsigned int', 'unsigned int a', 'return a^0x12345678u;', 'return a^0x12345679u;',
     'unsigned int (unsigned int)', 'changed-literal'),
    (0x1082, 'unsigned int', 'unsigned int a', 'return a+17u;', 'return a+17u;',
     'unsigned int (unsigned int)', 'two-byte-entry-repeat'),
    (0x10a0, 'unsigned int', 'unsigned int a', 'return a+17u;', 'return a+17u;',
     'unsigned int (unsigned int)', 'repeat'),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    out.chmod(0o700)
    tools = ac.tool_lock(args.root)
    tasks, original, changed = {}, {}, {}
    for entry, ret, params, body, mutation, signature, label in FIXTURES:
        name = f'fn_{entry:08x}'
        task = {'id': name, 'entry': hex(entry), 'end_exclusive': hex(entry+64),
                'mode': 'thumb', 'abi_status': 'hypothesis_requires_review', 'signature': signature}
        tasks[name] = {**task, 'layout': ac.layout(task)}
        original[name] = f'{ret} {name}({params}) {{ {body} }}\n'
        changed[name] = f'{ret} {name}({params}) {{ {mutation} }}\n'
    lock = {**tools, 'tasks': tasks}
    runs = []
    for tag, sources in (('reference', original), ('changed', changed)):
        build = out / tag
        build.mkdir()
        runs.append(ac.build_sources(lock, sources, build))
    report = {'scope': 'synthetic ARMCC5/LLD controls only', 'tools': tools, 'checks': []}
    for entry, ret, params, body, mutation, signature, label in FIXTURES:
        name = f'fn_{entry:08x}'
        a, b = [ac.runtime_bytes(run[name]['elf'], entry) for run in runs]
        expected_equal = body == mutation
        ac.require((a == b) == expected_equal, 'unexpected synthetic comparison: ' + label)
        if label == 'changed-literal':
            ac.require(bytes.fromhex('78563412') in a and bytes.fromhex('79563412') in b,
                       'literal-pool control did not exercise literal bytes')
        report['checks'].append({'label': label, 'passed': True, 'equal': a == b,
                                 'reference_sha256': ac.sc.base.sha(a), 'actual_sha256': ac.sc.base.sha(b)})
    # Exact machine bytes are not enough: the same-byte signed return declaration
    # must fail source ABI policy before compilation is attempted.
    abi = out / 'abi'
    abi.mkdir()
    try:
        ac.source_check(original['fn_00001000'].replace('unsigned int fn_', 'int fn_'),
                        abi, lock, tasks['fn_00001000'])
    except ValueError:
        report['checks'].append({'label': 'wrong-signature', 'passed': True})
    else:
        raise ValueError('wrong signature accepted')
    (out / 'report.json').write_bytes(ac.sc.encode(report))
    print(json.dumps({'checks': report['checks'], 'stock_certified': False}, indent=2))


if __name__ == '__main__':
    main()
