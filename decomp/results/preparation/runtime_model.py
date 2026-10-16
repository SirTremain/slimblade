#!/usr/bin/env python3
"""Instruction-derived helper model, NOT recovered C or a firmware build input.

Compare against TraceRuntime.java's execution of unmodified original ARM bytes.
All arithmetic is explicitly 32-bit. The model preserves NZCV and both exits.
"""
import argparse
import collections
import json
from pathlib import Path

MASK = 0xffffffff
WORDS = {0x1e360: 0x3efc7e09, 0x1e47c: 0x80492492}
BASELINE = 'e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7'


def model(call, inputs, saved_return):
    r = dict(zip(('r0','r1','r2','r3','r4','r5','r6'), inputs))
    r.update(NG=0, ZR=0, CY=0, OV=0, TMode=0, sp=0x400800, lr=call+8)

    def add(a, b, carry=0):
        full = a+b+carry
        value = full & MASK
        r.update(NG=value >> 31, ZR=int(value == 0), CY=int(full > MASK),
                 OV=int(bool((~(a^b) & (a^value)) & 0x80000000)))
        return value

    def sub(a, b):
        return add(a, (~b)&MASK, 1)

    def hi():
        return r['CY'] and not r['ZR']

    r['r6'] = WORDS[call]
    r.update(NG=r['r6'] >> 31, ZR=int(r['r6'] == 0))
    unordered = False
    if not r['NG']:
        sub(r['r2'], 1)
        r['r5'] = (2*r['r3']+r['CY']) & MASK
        add(r['r5'], 0x200000)
        unordered = hi()
    if unordered:
        index = 8
    else:
        sub(r['r0'], 1)
        r['r12'] = (2*r['r1']+r['CY']) & MASK
        add(r['r12'], 0x200000)
        if hi():
            index = 8
        elif not r['ZR']:
            index = r['r3'] >> 31
        else:
            sign = r['r1'] >> 31
            add(r['r5'], 0x200000)
            index = 3*sign+2
            if r['ZR']:
                index += (r['r3'] >> 31)+r['CY']
    r['r5'] = 3*index
    selector = (r['r6'] >> r['r5']) & 7
    r['r6'] = selector
    r['r12'] = sub(selector, 4)
    if not r['CY']:
        r['r12'] = r['lr']+4*selector
        r['pc'] = r['r12']
        r['lr'] = saved_return
    else:
        if selector in (6, 7):
            r['r0'], r['r1'] = 0, 0x7ff80000
        else:
            if selector == 4:
                r['r0'], r['r1'] = r['r2'], r['r3']
            sub(r['r0'], 1)
            r['r4'] = add(r['r1'], r['r1'], r['CY'])
            if not r['ZR']:
                r['r4'] = sub(0x200000, r['r4'])
            if hi():
                r['r0'] = 0
                r['r1'] &= 0x80000000
        r['pc'] = saved_return & ~1
        r['TMode'] = saved_return & 1
    r.update(r4=0x14141414, r5=0x15151515, r6=0x16161616, sp=r['sp']+16)
    return index, selector, r


def verify(report, injected=None):
    if report['baseline_sha256'] != BASELINE:
        raise ValueError('wrong original image')
    coverage = collections.defaultdict(lambda: {'indices': set(), 'selectors': set(), 'exits': set()})
    if report.get('injected_analysis_model', False):
        raise ValueError('original instruction traces required')
    if injected is not None:
        if (not injected.get('injected_analysis_model') or injected.get('baseline_sha256') != BASELINE
                or len(injected['cases']) != len(report['cases'])):
            raise ValueError('invalid injected comparison report')
    for n, row in enumerate(report['cases']):
        index, selector, result = model(row['call'], row['inputs'], row['saved_return'])
        if (index, selector, result) != (row['index'], row['selector'], row['result']):
            delta = {key: [result.get(key), value] for key,value in row['result'].items() if result.get(key) != value}
            raise ValueError(f'case {n}: expected model/actual trace mismatch {delta}; index {index}/{row["index"]}; selector {selector}/{row["selector"]}')
        if injected is not None:
            trial = injected['cases'][n]
            for key in ('call', 'inputs', 'saved_return', 'result'):
                if trial[key] != row[key]:
                    raise ValueError(f'injected case {n} disagrees: {key}: {trial[key]} != {row[key]}')
        c = coverage[hex(row['call'])]
        c['indices'].add(index); c['selectors'].add(selector); c['exits'].add(hex(result['pc']))
    return {'cases': len(report['cases']), 'injected_model_compared': injected is not None,
            'coverage': {k: {n: sorted(v) for n,v in c.items()} for k,c in coverage.items()},
            'scope': 'model agrees on tested original-instruction cases; not exhaustive equivalence or C reconstruction'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('traces', type=Path)
    p.add_argument('--injected', type=Path)
    a = p.parse_args()
    print(json.dumps(verify(json.loads(a.traces.read_text()),
                           json.loads(a.injected.read_text()) if a.injected else None), indent=2))


if __name__ == '__main__':
    main()
