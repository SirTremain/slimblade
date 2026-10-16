#!/usr/bin/env python3
"""Freeze reviewed direct-call experiment inputs without creating runnable tasks."""
import argparse
import json
from pathlib import Path
import shutil

import armcc_calls as cc
import decomp
import prepare_next_batch as nb
import prepare_pilot as pp


def prepare(root, export, output):
    root, output = root.resolve(), output.resolve()
    cc.require(output.is_relative_to(root / '.decomp') and not output.exists(), 'fresh ignored output required')
    path = root / 'decomp/proposals/direct-call-candidates.json'
    proposal = json.loads(path.read_text())
    exported = json.loads(export.read_text())
    parent_path = root / '.decomp/pilot-armcc5-v1/lock.json'
    parent_hash = '2c2e3416849c68cade707434e9589c8c2806721fef9f02bd7b68c5286abc0c4a'
    parent = cc.ac.load_lock(parent_path, parent_hash)
    raw = Path(parent['baseline']['path']).read_bytes()
    cc.require(exported['baseline_sha256'] == proposal['baseline_sha256'] == cc.ac.sc.base.sha(raw)
               and exported['language'] == 'ARM:LE:32:v5t', 'export identity changed')
    inventory = root / '.decomp/inventory-runtime-v4.json'
    cc.require(cc.ac.sc.base.sha(inventory.read_bytes()) ==
               '468be36c1cc8af5f9201bc20f1207127ddd55a1b392645183bba4d43d3eb7fd2', 'inventory changed')
    discovery = json.loads(inventory.read_text())['functions']
    packet = root / '.decomp/evidence/runtime-v4'
    cc.require(decomp.packet_hash(packet) ==
               'd497d1947359eac5ea340c88e6206b10843cddd586f1f761a1c71222a66f0916', 'upstream evidence changed')
    refs = json.loads((packet / 'references.json').read_text())
    listing = (packet / 'listing.txt').read_text().splitlines()
    wrapper = root / '.decomp/evidence/llvm-crosscheck/disassembly-only.elf'
    cc.require(cc.ac.sc.base.sha(wrapper.read_bytes()) == pp.INPUTS['.decomp/evidence/llvm-crosscheck/disassembly-only.elf'],
               'independent wrapper changed')
    llvm = shutil.which('llvm-objdump')
    cc.require(llvm, 'LLVM disassembler required')
    output.mkdir(mode=0o700)
    reports = []
    for task in proposal['tasks']:
        start, end = cc.validate_task(task, raw)
        known = [f for f in discovery if f['id'] == task['id']]
        ranges = [{'start': f'0x{start:08x}', 'end_exclusive': f'0x{end:08x}'}]
        cc.require(len(known) == 1 and known[0]['mode'] == 'thumb' and known[0]['ranges'] == ranges, 'boundary changed')
        owners = [f['id'] for f in discovery for r in f['ranges']
                  if start < int(r['end_exclusive'], 16) and int(r['start'], 16) < end]
        cc.require(owners == [task['id']], 'overlapping ownership')
        fn = next(f for f in exported['functions'] if int(f['entry'], 16) == start)
        cc.require(int(fn['end_exclusive'], 16) == end, 'export boundary changed')
        sites = {int(s['address'], 16): int(task['extern_functions'][s['callee']]['entry'], 16) for s in task['calls']}
        cursor = start
        for row in fn['instructions']:
            address, data = int(row['address'], 16), bytes.fromhex(row['bytes'])
            cc.require(address == cursor and row['tmode'] == 1 and data == raw[address:address+len(data)], 'byte/state mismatch')
            cc.require(row.get('fallthrough') is None or start <= int(row['fallthrough'], 16) < end, 'escaping fallthrough')
            if address in sites:
                cc.require(row['flow_type'] == 'UNCONDITIONAL_CALL' and len(data) == 4 and
                           [int(f, 16) for f in row['flows']] == [sites[address]], 'call export mismatch')
            else:
                cc.require('CALL' not in row['flow_type'] and len(data) == 2 and not row['flows'] and
                           '[0x' not in row['text'], 'unsupported wrapper instruction')
            cursor += len(data)
        cc.require(cursor == end and fn['instructions'][-1]['text'] == 'pop {r4,pc}', 'incomplete wrapper')
        incoming = [r for r in refs if pp.address(r['to']) is not None and start <= int(r['to'], 16) < end
                    and not (pp.address(r['from']) is not None and start <= int(r['from'], 16) < end)]
        cc.require(incoming and all(int(r['to'], 16) == start and r['type'] == 'UNCONDITIONAL_CALL' for r in incoming),
                   'offcut/data entry requires review')
        outgoing = [r for r in refs if pp.address(r['from']) is not None and start <= int(r['from'], 16) < end]
        cc.require(len(outgoing) == len(sites) and all(r['type'] == 'UNCONDITIONAL_CALL' and
                   sites.get(int(r['from'], 16)) == pp.address(r['to']) for r in outgoing), 'unreviewed dependency')
        folder = output / task['id']; folder.mkdir()
        decoded = cc.ac.sc.base.run([llvm, '-D', '--triple=thumbv5te-none-eabi', f'--start-address={start}',
                                    f'--stop-address={end}', str(wrapper)])
        nb.independent_decode(decoded, raw, start, end)
        (folder / 'llvm.txt').write_text(decoded)
        pp.write_json(folder / 'instructions.json', fn)
        pp.write_json(folder / 'references.json', {'incoming': incoming, 'outgoing': outgoing})
        relevant = [(start, end)] + [(int(r['from'], 16)-20, int(r['from'], 16)+16) for r in incoming]
        for name, callee in task['extern_functions'].items():
            found = [f for f in discovery if f['id'] == name]
            cc.require(len(found) == 1 and found[0]['mode'] == 'thumb' and len(found[0]['ranges']) == 1, 'callee entry/state unknown')
            r = found[0]['ranges'][0]
            relevant.append((int(r['start'], 16), int(r['end_exclusive'], 16)+8))
        (folder / 'context-listing.txt').write_text('\n'.join(l for l in listing
            if any(a <= int(l.split()[0], 16) < b for a, b in relevant))+'\n')
        task['task_sha256'] = cc.ac.sc.base.sha(cc.ac.sc.encode(task))
        reports.append({'task': task['id'], 'owned_bytes': end-start, 'range_sha256': cc.ac.sc.base.sha(raw[start:end]),
                        'evidence_sha256': decomp.packet_hash(folder), 'callers': len(incoming)})
    pp.write_json(output / 'manifest.json', proposal)
    digest = cc.initialize(parent_path, parent_hash, output / 'manifest.json', output / 'lock.json')
    report = {'status': 'experimental_not_swarm_ready', 'lock_sha256': digest, 'tasks': reports,
              'proposal': cc.ac.sc.base.pin(path), 'export': cc.ac.sc.base.pin(export.resolve()),
              'llvm': cc.ac.sc.base.pin(llvm), 'baseline': parent['baseline'],
              'active_gate_changed': False, 'stock_candidates_compiled': False}
    pp.write_json(output / 'report.json', report)
    for file in output.rglob('*'):
        if file.is_file():
            file.chmod(0o444)
    cc.load_lock(output / 'lock.json', digest)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--export', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(prepare(args.root, args.export, args.output), indent=2))
