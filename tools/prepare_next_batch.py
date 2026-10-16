#!/usr/bin/env python3
"""Export a NEW four-leaf proposal; never edit active tasks, pins, gates or queue."""
import argparse
import json
from pathlib import Path
import re
import shutil
import struct

import armcc_compare as ac
import decomp
import prepare_pilot as pp

SPANS = [(0x13f58, 0x13f72), (0x13f72, 0x13f7a),
         (0x154d4, 0x154ea), (0x18100, 0x18114)]
SIGNATURES = ['void (unsigned char *, const unsigned char *)',
              'void (unsigned char *, unsigned short)',
              'unsigned int (const unsigned char *)',
              'unsigned int (unsigned int, unsigned int)']
CONTEXT = [
    'Six alternating byte loads from r1 and byte stores to r0, offsets 0..5 in order. '
    'Do not assume non-overlap or use restrict: overlapping ranges may propagate bytes. '
    'Callers 0x4ff2 and 0x55e6 do not consume the result; void is a hypothesis. '
    'No wider aligned copies or library memcpy substitution.',
    'Two STRB writes at offsets 0 and 1; logical right shift of r1 by eight. '
    'Known callers supply immediate constants or LDRH values. They do not consume r0 '
    'as a result. unsigned short and void are hypotheses, not recovered declarations.',
    'Four LDRB reads at offsets 1,0,2,3; OR composition and unsigned shifts. '
    'Callers 0x17c36..0x17c7e store the full r0 result. Some retain r3 across calls: '
    'the original body preserves r3, even though AAPCS permits clobbering it. '
    'Exact output and caller-clobber review matter; generic ABI compatibility is insufficient. '
    'Do not infer pointer alignment, volatile qualifiers, or semantic purpose.',
    'Register-only predicate; r0 equality test and unsigned r1 comparison against 0x800. '
    'Returns zero or one; callers 0x175d4 and 0x177fe compare r0 with zero. '
    'Signedness of the first input and semantic names remain unknown.',
]


def independent_decode(text, raw, start, end):
    rows = re.findall(r'^\s*([0-9a-f]+):\s+([0-9a-f]{4})(?:\s+([0-9a-f]{4}))?\s+(.+)$', text, re.M)
    cursor = start
    for address, first, second, instruction in rows:
        data = struct.pack('<H', int(first, 16))
        if second:
            data += struct.pack('<H', int(second, 16))
        ac.require(int(address, 16) == cursor and data == raw[cursor:cursor+len(data)]
                   and '<unknown>' not in instruction, 'independent decode mismatch')
        cursor += len(data)
    ac.require(cursor == end, 'incomplete independent decode')


def generate(root, export, output):
    root, output = root.resolve(), output.resolve()
    ac.require(output.is_relative_to(root / '.decomp') and not output.exists(), 'fresh ignored output required')
    packets = root / '.decomp/evidence' / output.name
    ac.require(not packets.exists(), 'fresh evidence directory required')
    baseline, active = decomp.load_tasks(root)
    raw = (root / '.decomp/stock/stock-v4.49.bin').read_bytes()
    ac.require(len(raw) == baseline['bytes'] and ac.sc.base.sha(raw) == baseline['sha256'], 'baseline changed')
    discovery_path = root / '.decomp/inventory-runtime-v4.json'
    ac.require(ac.sc.base.sha(discovery_path.read_bytes()) ==
               '468be36c1cc8af5f9201bc20f1207127ddd55a1b392645183bba4d43d3eb7fd2', 'inventory changed')
    packet = root / '.decomp/evidence/runtime-v4'
    ac.require(decomp.packet_hash(packet) ==
               'd497d1947359eac5ea340c88e6206b10843cddd586f1f761a1c71222a66f0916', 'upstream evidence changed')
    exported = json.loads(export.read_text())
    ac.require(exported['baseline_sha256'] == baseline['sha256'] and
               exported['language'] == 'ARM:LE:32:v5t', 'export identity changed')
    discovery = json.loads(discovery_path.read_text())['functions']
    refs = json.loads((packet / 'references.json').read_text())
    listing = (packet / 'listing.txt').read_text().splitlines()
    wrapper = root / '.decomp/evidence/llvm-crosscheck/disassembly-only.elf'
    ac.require(ac.sc.base.sha(wrapper.read_bytes()) == pp.INPUTS['.decomp/evidence/llvm-crosscheck/disassembly-only.elf'],
               'independent disassembly wrapper changed')
    llvm = shutil.which('llvm-objdump')
    ac.require(llvm, 'LLVM disassembler required')
    output.mkdir(mode=0o700)
    tasks = []
    for (start, end), signature, context in zip(SPANS, SIGNATURES, CONTEXT, strict=True):
        ident = f'fn_{start:08x}'
        ac.require(ident not in active, 'proposal would replace an active task')
        ranges = [{'start': f'0x{start:08x}', 'end_exclusive': f'0x{end:08x}'}]
        known = [f for f in discovery if f['id'] == ident]
        ac.require(len(known) == 1 and known[0]['ranges'] == ranges and known[0]['mode'] == 'thumb', 'boundary changed')
        fn = next(f for f in exported['functions'] if int(f['entry'], 16) == start)
        incoming, outgoing = pp.check_leaf(fn, start, end, raw, refs)
        # Reject ownership overlaps, not only duplicate entry points.
        owners = [f['id'] for f in discovery for r in f['ranges']
                  if start < int(r['end_exclusive'], 16) and int(r['start'], 16) < end]
        ac.require(owners == [ident], 'overlapping discovery ownership')
        folder = packets / ident
        folder.mkdir(parents=True)
        local = [l for l in listing if start <= int(l.split()[0], 16) < end]
        ac.require([l.split()[1] for l in local] == [i['bytes'] for i in fn['instructions']], 'listing mismatch')
        (folder / 'listing.txt').write_text('\n'.join(local) + '\n')
        command = [llvm, '-D', '--triple=thumbv5te-none-eabi', f'--start-address={start}',
                   f'--stop-address={end}', str(wrapper)]
        decoded = ac.sc.base.run(command)
        independent_decode(decoded, raw, start, end)
        (folder / 'llvm.txt').write_text(decoded)
        pp.write_json(folder / 'instructions.json', fn)
        pp.write_json(folder / 'references.json', {'incoming': incoming, 'outgoing': outgoing})
        caller_lines = []
        for ref in incoming:
            a = int(ref['from'], 16)
            caller_lines.append(f'\nReference: {ref}')
            caller_lines.extend(l for l in listing if a-20 <= int(l.split()[0], 16) < a+16)
        (folder / 'callers.txt').write_text('\n'.join(caller_lines) + '\n')
        (folder / 'context.md').write_text(f'# {ident}\n\n{context}\n\n'
            'Observed: contiguous Thumb body ending in BX LR; no literal pool, external '
            'data reference, stack use or call. All discovered incoming references target '
            'the entry. Hidden indirect callers remain unknown. Source qualifiers and '
            'historical compiler are not proven. Check source/ABI and exact clobbers '
            'independently; exact-range bytes are not certification. No adjacent padding '
            'is owned. Derive C from evidence, not raw instruction words.\n')
        pp.write_json(folder / 'metadata.json', {
            'baseline_sha256': baseline['sha256'], 'baseline_bytes': len(raw),
            'entry': f'0x{start:08x}', 'mode': 'thumb', 'ranges': ranges,
            'range_sha256': ac.sc.base.sha(raw[start:end]), 'ghidra_version': '12.1.4',
            'language': exported['language'], 'export_settings': 'readOnly/noanalysis; ExportNextBatch.java',
            'export_sha256': ac.sc.base.sha(export.read_bytes()),
            'export_script_sha256': ac.sc.base.sha((root / 'decomp/results/expansion-preparation/ExportNextBatch.java').read_bytes()),
            'llvm': ac.sc.base.pin(llvm), 'llvm_version': ac.sc.base.run([llvm, '--version']),
            'upstream_source_url': baseline['source_url'], 'inspection_date': '2026-10-16',
            'data_and_literal_ranges': [], 'outgoing_dependencies': [], 'full_inventory_approved': False})
        tasks.append({
            'id': ident, 'kind': 'function', 'title': f'Batch 2 proposal: Thumb leaf at 0x{start:08x}',
            'entry': f'0x{start:08x}', 'mode': 'thumb', 'ranges': ranges,
            'depends_on': ['bootstrap-inventory', 'bootstrap-toolchain', 'bootstrap-verifier'],
            'allowed_paths': [f'decomp/src/{ident}.c', f'decomp/results/{ident}/'],
            'signature': signature, 'abi_status': 'hypothesis_requires_review',
            'instructions': 'Read the immutable packet and docs/expansion.md. Recover only this leaf with the pinned ARMCC5 profile. '
                'Review callers, aliasing, signedness and exact register clobbers. No calls, absolute globals, asm, intrinsics '
                'or raw instruction data. Coordinator builds only. Stop at 20 minutes/8 attempts/3 non-improving attempts. '
                'Report draft or blocked; never matched. Propose ABI corrections instead of changing pins.',
            'acceptance': 'Independent source/ABI review and fresh unchanged-source exact-range rebuild; not certification.',
            'evidence_path': folder.relative_to(root).as_posix(), 'evidence_sha256': decomp.packet_hash(folder),
            'boundary_review': '2026-10-16 coordinator: Ghidra TMode/flow/boundaries, original bytes, references, LLVM; see docs/expansion.md.',
            'comparison_scope': ac.SCOPE})
    manifest = {'baseline_sha256': baseline['sha256'], 'tasks': [
        {**{k: t[k] for k in ('id', 'entry', 'mode', 'signature', 'abi_status')},
         'end_exclusive': t['ranges'][0]['end_exclusive'], 'task_sha256': ac.sc.base.sha(ac.sc.encode(t))}
        for t in tasks]}
    pp.write_json(output / 'manifest.json', manifest)
    digest = ac.initialize(root, root / '.decomp/stock/stock-v4.49.bin', output / 'manifest.json', output / 'lock.json')
    for task in tasks:
        task['comparison'] = {'lock_path': (output / 'lock.json').relative_to(root).as_posix(), 'lock_sha256': digest}
        decomp.evidence_check(root, baseline, task)
    proposal = {'schema_version': 1, 'baseline_id': baseline['id'],
                'inventory_status': 'four_reviewed_leaf_proposals_not_active', 'functions': tasks}
    pp.write_json(output / 'functions.json', proposal)
    for directory in (output, packets):
        for file in directory.rglob('*'):
            if file.is_file():
                file.chmod(0o444)
    return {'proposal': str(output / 'functions.json'), 'tasks': len(tasks), 'owned_bytes': 76,
            'lock_sha256': digest, 'active_gate_changed': False, 'workers_started': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--export', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(generate(args.root, args.export, args.output), indent=2))
