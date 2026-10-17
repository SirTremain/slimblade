#!/usr/bin/env python3
"""Freeze reviewed call packets/task contracts; never edit the queue or generate C."""
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
    cc.require(output.parent == root / '.decomp' and not output.exists(), 'fresh ignored output required')
    packet_root = root / '.decomp/evidence' / output.name
    cc.require(not packet_root.exists(), 'never replace evidence packets')
    proposal_path = root / 'decomp/proposals/batch-3-selection.json'
    proposal = decomp.read_json(proposal_path)
    exported = decomp.read_json(export)
    parent_path = root / '.decomp/pilot-armcc5-v1/lock.json'
    parent_hash = '2c2e3416849c68cade707434e9589c8c2806721fef9f02bd7b68c5286abc0c4a'
    parent = cc.ac.load_lock(parent_path, parent_hash)
    raw = Path(parent['baseline']['path']).read_bytes()
    baseline = decomp.read_json(root / 'decomp/baseline.json')
    cc.require(exported['baseline_sha256'] == proposal['baseline_sha256'] == cc.ac.sc.base.sha(raw)
               and exported['language'] == 'ARM:LE:32:v5t', 'export identity changed')
    inventory = root / '.decomp/inventory-runtime-v4.json'
    cc.require(cc.ac.sc.base.sha(inventory.read_bytes()) ==
               '468be36c1cc8af5f9201bc20f1207127ddd55a1b392645183bba4d43d3eb7fd2', 'inventory changed')
    discovery = decomp.read_json(inventory)['functions']
    upstream = root / '.decomp/evidence/runtime-v4'
    cc.require(decomp.packet_hash(upstream) ==
               'd497d1947359eac5ea340c88e6206b10843cddd586f1f761a1c71222a66f0916', 'upstream evidence changed')
    refs = decomp.read_json(upstream / 'references.json')
    listing = (upstream / 'listing.txt').read_text().splitlines()
    wrapper = root / '.decomp/evidence/llvm-crosscheck/disassembly-only.elf'
    cc.require(cc.ac.sc.base.sha(wrapper.read_bytes()) == pp.INPUTS['.decomp/evidence/llvm-crosscheck/disassembly-only.elf'],
               'independent decode wrapper changed')
    llvm = shutil.which('llvm-objdump'); cc.require(llvm, 'LLVM required')
    output.mkdir(mode=0o700); packet_root.mkdir(parents=True, mode=0o700)
    # Cross-check every exported instruction, including the callee evidence.
    decodes = {}
    for fn in exported['functions']:
        a,b = int(fn['entry'],16),int(fn['end_exclusive'],16)
        cursor = a
        for row in fn['instructions']:
            address,data = int(row['address'],16),bytes.fromhex(row['bytes'])
            cc.require(address == cursor and row['tmode'] == 1 and len(data) in (2,4) and
                       data == raw[address:address+len(data)], 'export bytes/state changed')
            cursor += len(data)
        cc.require(cursor == b, 'incomplete instruction export')
        decoded = cc.ac.sc.base.run([llvm,'-D','--triple=thumbv5te-none-eabi',f'--start-address={a}',
                                    f'--stop-address={b}',str(wrapper)])
        nb.independent_decode(decoded,raw,a,b)
        decodes[a] = decoded
    tasks, manifest = [], []
    for selected in proposal['tasks']:
        a,b = cc.validate_task(selected,raw)
        ranges = [{'start':f'0x{a:08x}','end_exclusive':f'0x{b:08x}'}]
        owners = [f['id'] for f in discovery for r in f['ranges']
                  if a<int(r['end_exclusive'],16) and int(r['start'],16)<b]
        cc.require(owners == [selected['id']], 'ambiguous range ownership')
        known = next(f for f in discovery if f['id']==selected['id'])
        cc.require(known['ranges']==ranges and known['mode']=='thumb', 'unreviewed boundary')
        fn = next(f for f in exported['functions'] if int(f['entry'],16)==a)
        cc.require(int(fn['end_exclusive'],16)==b, 'export boundary mismatch')
        sites = {int(s['address'],16):int(selected['extern_functions'][s['callee']]['entry'],16)
                 for s in selected['calls']}
        for row in fn['instructions']:
            address = int(row['address'],16)
            cc.require(row.get('fallthrough') is None or a<=int(row['fallthrough'],16)<b, 'escaping fallthrough')
            if address in sites:
                cc.require(row['flow_type']=='UNCONDITIONAL_CALL' and
                           [int(f,16) for f in row['flows']]==[sites[address]], 'call mismatch')
            else:
                cc.require('CALL' not in row['flow_type'] and not row['flows'] and '[0x' not in row['text'],
                           'unsupported body control/data dependency')
        cc.require(fn['instructions'][-1]['text']=='pop {r4,pc}', 'return mismatch')
        incoming = [r for r in refs if pp.address(r['to']) is not None and a<=int(r['to'],16)<b
                    and not (pp.address(r['from']) is not None and a<=int(r['from'],16)<b)]
        outgoing = [r for r in refs if pp.address(r['from']) is not None and a<=int(r['from'],16)<b]
        cc.require(incoming and all(int(r['to'],16)==a and r['type']=='UNCONDITIONAL_CALL' for r in incoming),
                   'unreviewed incoming reference')
        cc.require(len(outgoing)==len(sites) and all(r['type']=='UNCONDITIONAL_CALL' and
                   sites.get(int(r['from'],16))==pp.address(r['to']) for r in outgoing), 'unreviewed outgoing reference')
        packet = packet_root / selected['id']; packet.mkdir()
        (packet/'llvm.txt').write_text(decodes[a])
        (packet/'listing.txt').write_text('\n'.join(l for l in listing if a<=int(l.split()[0],16)<b)+'\n')
        contexts = [(int(r['from'],16)-20,int(r['from'],16)+20) for r in incoming]
        contexts += [(int(f['entry'],16),int(f['end_exclusive'],16)+8) for f in exported['functions']
                     if int(f['entry'],16) not in {int(t['entry'],16) for t in proposal['tasks']}]
        (packet/'context-listing.txt').write_text('\n'.join(l for l in listing
            if any(x<=int(l.split()[0],16)<y for x,y in contexts))+'\n')
        (packet/'context.md').write_text(selected['review']+'\n\nNo C is precomputed. Fixed callees and their globals are not reconstructed. Hidden indirect callers and original declarations remain unknown.\n')
        pp.write_json(packet/'instructions.json',fn)
        pp.write_json(packet/'callee-instructions.json', [f for f in exported['functions'] if int(f['entry'],16) not in {int(t['entry'],16) for t in proposal['tasks']}])
        pp.write_json(packet/'references.json',{'incoming':incoming,'outgoing':outgoing})
        pp.write_json(packet/'metadata.json',{'baseline_sha256':baseline['sha256'],'baseline_bytes':len(raw),
            'source_url':baseline['source_url'],'retrieved_at':baseline['retrieved_at'],
            'entry':selected['entry'],'mode':'thumb','ranges':ranges,'data_and_literal_ranges':[],
            'inspection_date':'2026-10-17','ghidra_version':'12.1.4','language':exported['language'],
            'export_settings':'readOnly/noanalysis','export':cc.ac.sc.base.pin(export.resolve()),
            'export_script':cc.ac.sc.base.pin(root/'decomp/results/broader-preparation/ExportCallBatch.java'),
            'llvm':cc.ac.sc.base.pin(llvm),'full_inventory_approved':False})
        task = {'id':selected['id'],'kind':'function','title':'Batch 3 direct-call body '+selected['entry'],
            **{k:selected[k] for k in ('entry','mode','signature','abi_status','calls','extern_functions')},
            'ranges':ranges,'boundary_review':'2026-10-17 coordinator: original bytes, Ghidra TMode/flow, unique ownership, LLVM and addressed caller/callee review; docs/broader-workflow.md.',
            'depends_on':['bootstrap-inventory','bootstrap-toolchain','bootstrap-verifier'],
            'allowed_paths':[f'decomp/src/{selected["id"]}.c',f'decomp/results/{selected["id"]}/'],
            'evidence_path':str(packet.relative_to(root)),'evidence_sha256':decomp.packet_hash(packet),
            'comparison_scope':cc.SCOPE,
            'instructions':'Read the packet and docs/broader-workflow.md. Recover only the owned body with exact pinned extern declarations; preserve all argument, return, stack/register and side-effect behavior. Fixed callee bindings are not reconstructed dependencies. No asm, stubs, data globals, absolute casts or pin changes. Coordinator guarded builds only. Stop at 20 minutes/8 attempts/3 non-improving attempts.',
            'acceptance':'Independent full-diff/source/ABI/aliasing/clobber review and fresh unchanged-source exact-range rebuild; not certification.'}
        manifest.append({**{k:v for k,v in selected.items() if k!='review'},
                         'task_sha256':cc.ac.sc.base.sha(cc.ac.sc.encode(task))})
        tasks.append(task)
    pp.write_json(output/'manifest.json',{'baseline_sha256':baseline['sha256'],'tasks':manifest})
    digest = cc.initialize(parent_path,parent_hash,output/'manifest.json',output/'lock.json')
    for task in tasks:
        task['comparison']={'lock_path':str((output/'lock.json').relative_to(root)),'lock_sha256':digest}
        decomp.evidence_check(root,baseline,task)
    pp.write_json(output/'functions.json',{'schema_version':1,'baseline_id':baseline['id'],'functions':tasks})
    for folder in (packet_root,output):
        for path in folder.rglob('*'):
            if path.is_file(): path.chmod(0o444)
    return {'tasks':[t['id'] for t in tasks],'lock_sha256':digest,'worker_launched':False,'source_generated':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('root','export','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(prepare(a.root,a.export,a.output),indent=2))
