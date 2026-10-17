#!/usr/bin/env python3
"""Freeze the reviewed batch-4 leaf intake with retained Rea context; no C/model jobs.

Does not activate a batch, edit existing assignments, alter a verifier or claim work.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

import armcc_compare as ac
import decomp
import prepare_next_batch as nb
import prepare_pilot as pp
import rea_bridge as rea

SELECTION = 'decomp/proposals/batch-4-selection.json'
ENTRIES = {0x9fe2, 0x11e38, 0x15e0c}
UPSTREAM_HASH = 'd497d1947359eac5ea340c88e6206b10843cddd586f1f761a1c71222a66f0916'


def validate_leaf(fn, start, end, raw, refs):
    """Narrow reviewed shape; internal unconditional branches are not calls."""
    rea.require(int(fn['entry'], 16) == start and int(fn['end_exclusive'], 16) == end, 'wrong boundary')
    cursor = start
    for row in fn['instructions']:
        address = int(row['address'], 16)
        rea.require(address == cursor and row['tmode'] == 1 and
                    bytes.fromhex(row['bytes']) == raw[address:address+2], 'instruction bytes/mode changed')
        rea.require(row['flow_type'] in ('FALL_THROUGH', 'CONDITIONAL_JUMP', 'UNCONDITIONAL_JUMP', 'TERMINATOR'),
                    'unsupported instruction flow')
        rea.require(all(start <= int(t, 16) < end for t in row['flows']), 'escaping branch')
        rea.require(row.get('fallthrough') is None or start <= int(row['fallthrough'], 16) < end,
                    'escaping fallthrough')
        text = row['text']
        rea.require(not any(t in text for t in ('[0x', 'push', 'pop', 'sp', 'pc')), 'stack/literal/global shape')
        # Only the selected pointer store helper may access memory. Its address
        # register must stay incoming r0, preventing constructed MMIO addresses.
        if start == 0x11e38:
            rea.require(re.fullmatch(r'(lsr r[12],r1,#0x(8|10|18)|strb r[12],\[r0,#0x[0-3]\]|bx lr)', text),
                        'unreviewed byte-store shape')
        else:
            rea.require(not any(t in text for t in ('ldr', 'str', '[', ']')), 'unexpected memory access')
        cursor += 2
    rea.require(cursor == end and fn['instructions'][-1]['text'] == 'bx lr', 'incomplete leaf')
    incoming = [r for r in refs if pp.address(r['to']) is not None and start <= int(r['to'],16) < end
                and not (pp.address(r['from']) is not None and start <= int(r['from'],16) < end)]
    outgoing = [r for r in refs if pp.address(r['from']) is not None and start <= int(r['from'],16) < end]
    rea.require(incoming and all(int(r['to'],16) == start and r['type'] == 'UNCONDITIONAL_CALL'
                                for r in incoming), 'offcut/data/unknown entry')
    rea.require(all(pp.address(r['to']) is not None and start <= int(r['to'],16) < end and
                    r['type'] in ('CONDITIONAL_JUMP', 'UNCONDITIONAL_JUMP') for r in outgoing),
                'external dependency')
    return incoming, outgoing


def export_instructions(root, config, selection, output):
    work = output / 'work'
    for name in ('project', 'home', 'config', 'cache', 'temp'):
        (work / name).mkdir(parents=True)
    source = rea.safe_path(root, config['trees']['project']['path'])
    shutil.copyfile(rea.safe_path(root, config['files']['project']['path']), work/'project/SlimBlade-rea-copy.gpr')
    shutil.copytree(source, work/'project/SlimBlade-rea-copy.rep', symlinks=True)
    rea.require(rea.tree_digest(work/'project/SlimBlade-rea-copy.rep') == config['trees']['project']['sha256'],
                'project changed while copying')
    rea.write_json(work/'selection.json', selection)
    rea.write_json(work/'admission.json', {'baseline_sha256': config['baseline_sha256'],
        'baseline_bytes': config['baseline_bytes'],
        'inventory': json.loads(rea.safe_path(root, config['files']['inventory']['path']).read_text()),
        'runtime_xml': rea.safe_path(root, config['files']['runtime_xml']['path']).read_text()})
    process = guard = None
    try:
        with rea.endpoint_directory(lambda: rea.stop(process)) as endpoint:
            command = rea.sandbox_command(root, config, work, endpoint)
            index = command.index('--clearenv')
            command[index:index] = ['--ro-bind', str(root/'ghidra/ExportReaIntake.java'), '/adapter/ExportReaIntake.java']
            index = command.index('-postScript')
            command[index:] = ['-postScript', 'ExportReaIntake.java', '/work/selection.json', '/work/export.json',
                              '-postScript', 'CheckReaProject.java', '/work/admission.json', '/work/final-admission-result.json']
            with (output/'export.log').open('xb') as log:
                process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                guard = rea.RunGuard(process, output/'export.log', time.monotonic()+60)
                process.wait(timeout=60)
            rea.require(process.returncode == 0 and 'ERROR ' not in (output/'export.log').read_text(),
                        'instruction export failed; inspect export.log')
            rea.require((work/'admission-result.json').read_bytes() == (work/'final-admission-result.json').read_bytes(),
                        'project admission changed')
    finally:
        rea.stop(process)
        if guard:
            guard.close()
        rea.require(rea.tree_digest(source) == config['trees']['project']['sha256'], 'original project changed')
    rea.require(not guard.violation, guard.violation)
    return json.loads((work/'export.json').read_text())


def retained(root, run, config):
    directory = rea.safe_path(root, run)
    rea.require(directory.is_relative_to(root/'.decomp/rea/runs'), 'expected retained Rea run')
    path = rea.safe_path(directory, 'report.json')
    report = json.loads(path.read_text())
    rea.require(report['status'] == 'observed' and report['source_project_unchanged'] is True and
                report['certified_match'] is False and report['configuration'] == config and
                report['profile']['config_sha256'] == rea.digest(rea.canonical(config)) and
                report['profile_sha256'] == rea.digest(rea.canonical(report['profile'])) and
                report['profile']['runner_sha256'] == rea.digest((root/'tools/rea_bridge.py').read_bytes()) and
                report['admission']['sha256'] == config['baseline_sha256'], 'retained Rea identity changed')
    seen = set()
    for row in report['observations']:
        key = (row['entry'], row['method'])
        rea.require(key not in seen, 'duplicate retained observation')
        seen.add(key)
        rea.require(row['method'] in rea.METHODS and row['path'] == f"{int(row['entry'],16):08x}-{row['method']}.json",
                    'unexpected retained observation path/method')
        rea.require(rea.digest(rea.safe_path(directory,row['path']).read_bytes()) == row['sha256'],
                    'retained Rea observation changed')
    rea.require(seen == {(entry, method) for entry in report['profile']['entry_selection'] for method in rea.METHODS},
                'incomplete retained observation set')
    return directory, report, rea.digest(path.read_bytes())


def prepare(root, run, name):
    rea.require(re.fullmatch(r'rea-batch4-[a-z0-9-]+', name), 'fresh batch-4 output name required')
    output = rea.safe_path(root, '.decomp/'+name)
    packets = rea.safe_path(root, '.decomp/evidence/'+name)
    rea.require(not output.exists() and not packets.exists(), 'never overwrite packets or locks')
    config = rea.check(root)
    directory, report, report_hash = retained(root, run, config)
    selection_path = root/SELECTION
    selection = json.loads(selection_path.read_text())
    rea.require({int(t['entry'],16) for t in selection['tasks']} == ENTRIES and len(selection['tasks']) == 3,
                'batch-4 membership changed')
    baseline, active = decomp.load_tasks(root)
    raw_path = root/'.decomp/stock/stock-v4.49.bin'
    raw = raw_path.read_bytes()
    rea.require(rea.digest(raw) == baseline['sha256'] == config['baseline_sha256'], 'baseline changed')
    upstream = root/'.decomp/evidence/runtime-v4'
    rea.require(decomp.packet_hash(upstream) == UPSTREAM_HASH, 'original evidence changed')
    inventory = json.loads(rea.safe_path(root,config['files']['inventory']['path']).read_text())['functions']
    refs = json.loads((upstream/'references.json').read_text())
    listing = (upstream/'listing.txt').read_text().splitlines()
    wrapper = root/'.decomp/evidence/llvm-crosscheck/disassembly-only.elf'
    rea.require(rea.digest(wrapper.read_bytes()) == pp.INPUTS['.decomp/evidence/llvm-crosscheck/disassembly-only.elf'],
                'independent decoder input changed')
    llvm = shutil.which('llvm-objdump'); rea.require(llvm, 'LLVM required')
    for task in selection['tasks']:
        rea.require(task['id'] not in active, 'would replace an existing task')
    output.mkdir(mode=0o700)
    exported = export_instructions(root, config, selection, output)
    tasks = []
    for selected in selection['tasks']:
        a,b = ac.validate_task(selected,len(raw))
        ident = selected['id']
        ranges = [{'start': selected['entry'], 'end_exclusive': selected['end_exclusive']}]
        owners = [f['id'] for f in inventory for r in f['ranges']
                  if a<int(r['end_exclusive'],16) and int(r['start'],16)<b]
        known = next(f for f in inventory if f['id']==ident)
        rea.require(owners == [ident] and known['ranges']==ranges and known['mode']=='thumb', 'ownership/mode changed')
        fn = next(f for f in exported['functions'] if int(f['entry'],16)==a)
        incoming,outgoing = validate_leaf(fn,a,b,raw,refs)
        dossier = rea.inspect(root,run,hex(a),'assembly')
        body = json.loads((directory/f'{a:08x}-analyze_function.json').read_text())['value']['procedure']['body']
        rea.require(body['ranges'] == [{'start':hex(a),'end':hex(b-1)}] and body['total_bytes']==b-a,
                    'Rea body disagrees with original ownership')
        actual = [(int(line.partition(':')[0],16), ''.join(line.partition(':')[2].split())) for line in dossier['value']]
        expected = [(int(row['address'],16), ''.join(row['text'].split())) for row in fn['instructions']]
        rea.require(actual == expected, 'Rea assembly disagrees with fresh export')
        decoded = ac.sc.base.run([llvm,'-D','--triple=thumbv5te-none-eabi',f'--start-address={a}',
                                 f'--stop-address={b}',str(wrapper)])
        nb.independent_decode(decoded,raw,a,b)
        packet = packets/ident; packet.mkdir(parents=True)
        (packet/'llvm.txt').write_text(decoded)
        (packet/'listing.txt').write_text('\n'.join(l for l in listing if a<=int(l.split()[0],16)<b)+'\n')
        caller_spans = [(int(r['from'],16)-24,int(r['from'],16)+24) for r in incoming]
        (packet/'callers.txt').write_text('\n'.join(l for l in listing if any(x<=int(l.split()[0],16)<y for x,y in caller_spans))+'\n')
        pp.write_json(packet/'instructions.json',fn)
        pp.write_json(packet/'references.json',{'incoming':incoming,'outgoing':outgoing})
        for method in rea.METHODS:
            shutil.copyfile(directory/f'{a:08x}-{method}.json',packet/f'rea-{method}.json')
        pp.write_json(packet/'rea-provenance.json',{'source_report':run+'/report.json','source_report_sha256':report_hash,
            'profile':report['profile'],'profile_sha256':report['profile_sha256'],'configuration':config,
            'admission':report['admission'],'limitations':report['limitations'],
            'observations':[r for r in report['observations'] if int(r['entry'],16)==a],
            'record_kind':report['record_kind'],'certified_match':False})
        (packet/'context.md').write_text(selected['review']+'\n\nRea pseudocode is unverified, not recovered C. Preserve all Rea limitations, facet availability and relationship coverage. Original bytes, LLVM and register effects take precedence over inferred types. Body ranges in Rea have inclusive ends. Hidden callers remain unknown. No adjacent data/padding is owned. No compiler/pin changes, asm, intrinsics or literal instruction blobs.\n')
        pp.write_json(packet/'metadata.json',{'baseline_sha256':baseline['sha256'],'baseline_bytes':len(raw),
            'source_url':baseline['source_url'],'retrieved_at':baseline['retrieved_at'],
            'entry':selected['entry'],'mode':'thumb','ranges':ranges,'range_sha256':rea.digest(raw[a:b]),
            'inspection_date':'2026-10-17','ghidra_version':'12.1.4','language':'ARM:LE:32:v5t',
            'export_settings':'validated disposable copy; readOnly/noanalysis',
            'export_sha256':rea.digest((output/'work/export.json').read_bytes()),
            'export_script':ac.sc.base.pin(root/'ghidra/ExportReaIntake.java'),
            'selection_sha256':rea.digest(selection_path.read_bytes()),'llvm':ac.sc.base.pin(llvm),
            'llvm_version':ac.sc.base.run([llvm,'--version']),
            'data_and_literal_ranges':[],'outgoing_dependencies':[],'full_inventory_approved':False})
        task = {'id':ident,'kind':'function','title':'Batch 4 Rea-assisted leaf '+selected['entry'],
            **{k:selected[k] for k in ('entry','mode','signature','abi_status')},'ranges':ranges,
            'depends_on':['bootstrap-inventory','bootstrap-toolchain','bootstrap-verifier'],
            'allowed_paths':[f'decomp/src/{ident}.c',f'decomp/results/{ident}/'],
            'boundary_review':'2026-10-17 coordinator: original bytes, fresh Ghidra per-instruction mode/flow, unique ownership, LLVM, Rea and addressed caller review; docs/batch-4.md.',
            'comparison_scope':ac.SCOPE,'evidence_path':str(packet.relative_to(root)),
            'evidence_sha256':decomp.packet_hash(packet),
            'instructions':'Read the packet, docs/batch-4.md and docs/rea.md. Recover only this leaf using the unchanged ARMCC5 profile. Treat Rea pseudocode as a hypothesis; preserve widths, unsigned conditions, byte ordering, aliasing and actual scratch-register effects. No calls, absolute globals, asm, intrinsics, raw instruction data or pin changes. Coordinator guarded builds only. Stop at 20 minutes/8 attempts/3 non-improving attempts. Submit draft or blocked, never matched.',
            'acceptance':'Independent full-diff/source/ABI/clobber review and fresh unchanged-source exact-range rebuild; not certification.'}
        tasks.append(task)
    pp.write_json(output/'manifest.json',{'baseline_sha256':baseline['sha256'],'tasks':[
        {**{k:t[k] for k in ('id','entry','mode','signature','abi_status')},
         'end_exclusive':t['ranges'][0]['end_exclusive'],'task_sha256':rea.digest(ac.sc.encode(t))} for t in tasks]})
    lock_hash = ac.initialize(root,raw_path,output/'manifest.json',output/'lock.json')
    for task in tasks:
        task['comparison']={'lock_path':str((output/'lock.json').relative_to(root)),'lock_sha256':lock_hash}
        decomp.evidence_check(root,baseline,task)
    pp.write_json(output/'functions.json',{'schema_version':1,'baseline_id':baseline['id'],'functions':tasks})
    for folder in (packets,):
        for path in folder.rglob('*'):
            if path.is_file():path.chmod(0o444)
    return {'tasks':[t['id'] for t in tasks],'owned_bytes':94,'lock_sha256':lock_hash,
            'proposal':str(output/'functions.json'),'active_gate_changed':False,'model_jobs_started':0}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=rea.ROOT)
    parser.add_argument('--rea-run',required=True)
    parser.add_argument('--name',required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(args.root.resolve(),args.rea_run,args.name),indent=2))
