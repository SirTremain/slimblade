#!/usr/bin/env python3
"""Audit the bounded runtime repair and independently executed helper model."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import helper_fixup
import runtime_model

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'tools'))
import decomp

CHANGED_BODIES = {
    'fn_0001e150': [(0x1e150,0x1e364),(0x1e368,0x1e398),(0x1e5a8,0x1e5b8)],
    'fn_0001e420': [(0x1e420,0x1e480),(0x1e484,0x1e490)],
    'fn_0001e4f0': [(0x1e4f0,0x1e568),(0x1e56c,0x1e5a8)],
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def changed(address):
    return any(a <= address < b for a,b in ((0x1e364,0x1e37c),(0x1e480,0x1e490),(0x1e56c,0x1e5a8)))


def check_inventory(before, after):
    require({k:v for k,v in before.items() if k != 'functions'} ==
            {k:v for k,v in after.items() if k != 'functions'}, 'inventory metadata changed')
    old = {f['id']:f for f in before['functions']}
    new = {f['id']:f for f in after['functions']}
    require(len(old) == len(before['functions']) and len(new) == len(after['functions']) and old.keys() == new.keys(), 'function set changed')
    for ident, previous in old.items():
        expected = dict(previous)
        if ident in CHANGED_BODIES:
            expected['ranges'] = [{'start':f'0x{a:08x}', 'end_exclusive':f'0x{b:08x}'} for a,b in CHANGED_BODIES[ident]]
        require(new[ident] == expected, f'unexpected body change: {ident}')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--tag', default='runtime-v4', choices=['runtime-v4','runtime-replay'])
    a = p.parse_args(); state = a.root.resolve()/'.decomp'
    require(not a.output.exists(), 'output exists')
    load = lambda path: json.loads(path.read_text())
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    original = load(state/'runtime-original-v4.json')
    injected = load(state/'runtime-injected-v2.json')
    execution = runtime_model.verify(original, injected)
    require(execution['cases'] == 10368, 'test matrix changed')
    require(execution['coverage'] == {
        '0x1e360': {'indices':list(range(9)), 'selectors':[0,1,6,7], 'exits':['0x1e368','0x1e36c','0x2100']},
        '0x1e47c': {'indices':list(range(9)), 'selectors':[0,2], 'exits':['0x1e484','0x1e48c']}}, 'missing case coverage')
    code = (state/'runtime-fixup-v2/runtime.sleigh').read_text()
    require(code == helper_fixup.body(), 'tested model differs from generator')
    xml = (state/'runtime-fixup-v2/runtime.xml').read_text()
    require(xml == '<callfixup name="slimblade_v449_runtime"><pcode><body><![CDATA[\n'+code+']]></body></pcode></callfixup>\n', 'XML/model mismatch')
    before = load(state/'inventory-readiness-v2.json')
    require(sha(state/'inventory-readiness-v2.json') == 'e6467b624c95023e9c5e6fa0c5babfdb27b8b35318b2277ab800aab47fe7d488', 'prior inventory changed')
    after = load(state/f'inventory-{a.tag}.json')
    check_inventory(before, after)
    old_packet = state/'evidence/readiness-v2'; packet = state/'evidence'/a.tag
    require(decomp.packet_hash(old_packet) == '8918a09bb12f34ed1071c4cb4add900ee129c1120b8026d3876d0b2e48b54a9b', 'prior evidence changed')
    require(sha(packet/'database-container.bin') == runtime_model.BASELINE, 'firmware mutated')
    audit = load(state/a.tag.replace('runtime-', 'runtime-repair-')/'audit.json')
    require(audit['container_sha256'] == runtime_model.BASELINE and audit['firmware_bytes_changed'] is False, 'wrong repair baseline')
    require(audit['model_xml_sha256'] == sha(state/'runtime-fixup-v2/runtime.xml'), 'installed model differs')
    report = load(state/f'inventory-{a.tag}-review.json')
    require(report['analysis_error_count'] == 0 and report['overlapping_function_body_bytes'] == 0 and report['errors'] == [], 'structural errors remain')
    require(report['matching_coverage'] == 'unknown', 'invalid certification claim')
    listings = [{int(line.split()[0],16):line for line in (path/'listing.txt').read_text().splitlines()}
                for path in (old_packet, packet)]
    for address in listings[0].keys() | listings[1].keys():
        if not changed(address):
            require(listings[0].get(address) == listings[1].get(address), f'unrelated listing changed at {address:x}')
    old_refs, refs = (load(path/'references.json') for path in (old_packet, packet))
    refset = lambda rows: {tuple(sorted(row.items())) for row in rows}
    for diff in refset(old_refs) ^ refset(refs):
        source = int(dict(diff)['from'],16)
        require(changed(source) or source in (0x1e360,0x1e47c,0x1e564), f'unrelated reference changed {source:x}')
    required = {(0x1e360,0x1e368),(0x1e360,0x1e36c),(0x1e47c,0x1e484),(0x1e47c,0x1e48c)}
    edges = {(int(r['from'],16),int(r['to'],16)) for r in refs if r['type'] == 'COMPUTED_JUMP' and r['to'].isalnum()}
    require(required <= edges, 'missing computed continuation')
    result = {'status':'bounded runtime analysis repaired; compiler preparation still blocked',
              'baseline_sha256':runtime_model.BASELINE, 'execution':execution,
              'inventory_sha256':sha(state/f'inventory-{a.tag}.json'), 'evidence_sha256':decomp.packet_hash(packet),
              'model_sha256':sha(state/'runtime-fixup-v2/runtime.sleigh'), 'model_xml_sha256':audit['model_xml_sha256'],
              'original_traces_sha256':sha(state/'runtime-original-v4.json'), 'injected_traces_sha256':sha(state/'runtime-injected-v2.json'),
              'analysis_errors':0, 'matching_coverage':'unknown'}
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
