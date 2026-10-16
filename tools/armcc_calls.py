#!/usr/bin/env python3
"""Experimental pinned Thumb direct-call feedback; NOT integrated swarm support.

Extends the unchanged leaf tools through a separate lock. Only ordinary Thumb
BL relocations to explicitly pinned extern functions are supported. No data
symbols, stubs, veneers, shared tails, ARM callees or whole-image certification.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import struct
import tempfile

import armcc_compare as ac

SCOPE = 'armcc5-direct-call-experiment-v1'
require = ac.require


def thumb_bl(data, offset, address):
    require(0 <= offset and offset % 2 == 0 and offset + 4 <= len(data), 'truncated/misaligned BL')
    hi, lo = struct.unpack_from('<HH', data, offset)
    require(hi & 0xf800 == 0xf000 and lo & 0xf800 == 0xf800, 'only ARMv5 Thumb BL supported')
    displacement = ((hi & 0x7ff) << 12) | ((lo & 0x7ff) << 1)
    if displacement & 0x400000:
        displacement -= 0x800000
    return address + 4 + displacement


def validate_task(task, raw):
    start, end = ac.validate_task(task, len(raw))
    externs = task['extern_functions']
    require(isinstance(externs, dict) and externs, 'explicit callees required')
    for name, callee in externs.items():
        entry = int(callee['entry'], 16)
        require(name == f'fn_{entry:08x}' and callee['mode'] == 'thumb' and
                0 <= entry < len(raw)-1 and entry % 2 == 0 and not start <= entry < end,
                'invalid external Thumb entry')
        ac.validate_task({'id': name, 'entry': hex(entry), 'end_exclusive': hex(entry+2),
                         'mode': 'thumb', 'signature': callee['signature'],
                         'abi_status': 'hypothesis_requires_review'}, len(raw))
    sites = task['calls']
    require(isinstance(sites, list) and sites, 'reviewed call sites required')
    seen = set()
    for site in sites:
        address = int(site['address'], 16)
        require(start <= address <= end-4 and address % 2 == 0 and
                not any(abs(address - other) < 4 for other in seen), 'overlapping/outside call')
        seen.add(address)
        name = site['callee']
        require(name in externs and thumb_bl(raw, address, address) == int(externs[name]['entry'], 16),
                'original call target differs from manifest')
    require({s['callee'] for s in sites} == set(externs), 'unused external declaration in contract')
    return start, end


def layout(task):
    # Bit zero marks the fixed target as Thumb. Never create a fake callee body.
    definitions = ''.join(f'{name} = 0x{int(row["entry"], 16)|1:x};\n'
                          for name, row in sorted(task['extern_functions'].items()))
    return definitions + ac.layout(task)


def source_check(source, build, parent, task):
    ac.sc.base.source_policy(source)
    require(not re.search(r'\b(?:float|double|enum|struct|union|typedef)\b', source),
            'aggregate/float/typedef ABI outside scope')
    (build / 'candidate.c').write_text(source)
    ast = json.loads(ac.sc.base.run([parent['tools']['analyzer']['path'], *ac.AST_FLAGS, 'candidate.c'], build))
    functions = [n for n in ast.get('inner', []) if n.get('kind') == 'FunctionDecl']
    expected = {task['id']: task['signature'], **{n: r['signature'] for n, r in task['extern_functions'].items()}}
    require(len(functions) == len(expected) and {n['name'] for n in functions} == set(expected),
            'exactly the assigned definition and pinned extern declarations required')
    for node in functions:
        name = node['name']
        body = any(n['kind'] == 'CompoundStmt' for n in node.get('inner', []))
        require(node['type']['qualType'] == expected[name], 'signature differs from pinned hypothesis')
        require(body == (name == task['id']), 'external definitions/stubs forbidden')
        require(not node.get('variadic') and not node.get('inline'), 'variadic/inline function forbidden')
        require(node.get('storageClass') == ('extern' if not body else None), 'unexpected function storage')
    require(not any(n.get('kind') == 'VarDecl' for n in ast.get('inner', [])), 'global data unsupported')
    allowed_refs = set()

    def calls(node):
        if node.get('kind') == 'CallExpr':
            target = node['inner'][0]
            require(target.get('kind') == 'ImplicitCastExpr' and
                    target.get('castKind') == 'FunctionToPointerDecay' and len(target['inner']) == 1,
                    'only direct external calls supported')
            ref = target['inner'][0]
            require(ref.get('kind') == 'DeclRefExpr' and ref['referencedDecl'].get('kind') == 'FunctionDecl'
                    and ref['referencedDecl']['name'] in task['extern_functions'], 'unapproved call')
            allowed_refs.add(ref['id'])
        for child in node.get('inner', []):
            calls(child)

    calls(ast)

    def walk(node):
        kind = node.get('kind', '')
        require('Asm' not in kind and not kind.endswith('Attr') and kind != 'StringLiteral',
                'assembly, attributes and strings forbidden')
        require(not (kind == 'VarDecl' and node.get('storageClass') in ('static', 'extern')), 'nonlocal data unsupported')
        require(node.get('castKind') not in ('IntegralToPointer', 'PointerToIntegral'), 'absolute address casts unsupported')
        if kind == 'DeclRefExpr' and node['referencedDecl'].get('kind') == 'FunctionDecl':
            require(node['id'] in allowed_refs, 'function addresses and indirect calls unsupported')
        for child in node.get('inner', []):
            walk(child)
    walk(ast)
    return expected


def object_calls(data, entry, externs):
    """Validate all allocated object bytes and every runtime relocation before use.

    AAELF32 relocation 10 is R_ARM_THM_CALL. No addend may select an offcut.
    Non-runtime debug relocations may remain for LLD; final ELF rejects all
    unresolved relocations and checks the entire load segment.
    """
    def take(offset, size):
        require(0 <= offset <= offset + size <= len(data), 'truncated object')
        return data[offset:offset+size]
    require(take(0, 7) == b'\x7fELF\x01\x01\x01', 'expected ELF32 LE object')
    h = struct.unpack('<HHIIIIIHHHHHH', take(16, 36))
    kind, machine, version, pc, phoff, shoff, flags, ehsize, phsize, phnum, shsize, shnum, shstr = h
    require((kind, machine, version, pc, flags, ehsize, phnum, shsize) ==
            (1, 40, 1, 0, 0x05000000, 52, 0, 40), 'unsupported object header')
    require(0 < shstr < shnum < 4096, 'bad object tables')
    sections = [struct.unpack('<10I', take(shoff+i*40, 40)) for i in range(shnum)]
    names = take(sections[shstr][4], sections[shstr][5])
    allocated = [(i, s) for i, s in enumerate(sections) if s[2] & 2 and s[5]]
    require(len(allocated) == 1, 'extra object allocation')
    index, text = allocated[0]
    require(text[0] < len(names) and names[text[0]:].split(b'\0', 1)[0] == b'.text'
            and (text[1], text[2], text[3]) == (1, 6, 0), 'unexpected object text')
    require(text[8] in (2, 4) and entry % text[8] == 0, 'object alignment incompatible with entry')
    code = take(text[4], text[5])
    calls, offsets = [], set()
    for rel in sections:
        if rel[1] not in (4, 9) or not rel[5]:
            continue
        require(rel[7] < shnum, 'invalid relocation target section')
        if not sections[rel[7]][2] & 2:
            continue
        require(rel[7] == index and rel[1] == 9 and rel[9] == 8 and rel[5] % 8 == 0,
                'only REL relocations on text supported')
        require(0 < rel[6] < shnum, 'missing symbol table')
        symbols = sections[rel[6]]
        require(symbols[1] == 2 and symbols[9] == 16 and symbols[5] % 16 == 0
                and 0 < symbols[6] < shnum, 'invalid symbol table')
        strings = sections[symbols[6]]
        require(strings[1] == 3, 'invalid symbol strings')
        strings = take(strings[4], strings[5])
        for pos in range(rel[4], rel[4]+rel[5], 8):
            offset, info = struct.unpack('<II', take(pos, 8))
            require(info & 255 == 10, 'only R_ARM_THM_CALL runtime relocations supported')
            sym = info >> 8
            require(0 < sym < symbols[5] // 16, 'invalid relocation symbol')
            name, value, size, binding, other, section = struct.unpack('<IIIBBH', take(symbols[4]+16*sym, 16))
            require(name < len(strings) and b'\0' in strings[name:], 'bad symbol name')
            name = strings[name:].split(b'\0', 1)[0].decode('ascii')
            # ARMCC emits STV_HIDDEN extern functions; LLVM fixtures use DEFAULT.
            # Neither changes the pinned target. Reject weak/protected/other bits.
            require(name in externs and section == value == size == 0 and other in (0, 2) and
                    binding in (0x10, 0x12), 'unapproved external symbol or binding')
            require(not any(abs(offset - previous) < 4 for previous in offsets), 'overlapping call relocations')
            offsets.add(offset)
            # For a zero symbol addend, the encoded displacement is -4 (PC bias).
            require(thumb_bl(code, offset, 0) == 0, 'nonzero/offcut call addend')
            calls.append({'offset': offset, 'callee': name})
    require(calls, 'missing direct-call relocations')
    return calls


def check_linked_calls(elf, entry, calls, externs):
    data = ac.runtime_bytes(elf, entry)
    for row in calls:
        require(thumb_bl(data, row['offset'], entry+row['offset']) == int(externs[row['callee']]['entry'], 16),
                'linked call target/state differs; veneers forbidden')
    return data


def initialize(parent_path, parent_hash, manifest_path, output):
    require(not output.exists(), 'lock exists; never overwrite pins')
    parent = ac.load_lock(parent_path, parent_hash)
    manifest = json.loads(manifest_path.read_text())
    raw = Path(parent['baseline']['path']).read_bytes()
    require(manifest['baseline_sha256'] == ac.sc.base.sha(raw), 'manifest baseline changed')
    tasks, spans = {}, []
    for task in manifest['tasks']:
        start, end = validate_task(task, raw)
        require(task['id'] not in tasks and not any(start < b and a < end for a, b in spans), 'duplicate/overlapping task')
        require(re.fullmatch(r'[0-9a-f]{64}', task['task_sha256']), 'task definition pin required')
        spans.append((start, end))
        tasks[task['id']] = {**task, 'expected_sha256': ac.sc.base.sha(raw[start:end]), 'layout': layout(task)}
    require(tasks, 'empty manifest')
    lock = {'schema_version': 1, 'scope': SCOPE, 'certified_match': False,
            'parent': {'path': str(parent_path.resolve()), 'sha256': parent_hash},
            'extension': ac.sc.base.pin(Path(__file__).resolve()),
            'manifest': ac.sc.base.pin(manifest_path.resolve()), 'tasks': tasks}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream:
        stream.write(ac.sc.encode(lock))
    output.chmod(0o444)
    return ac.sc.base.sha(output.read_bytes())


def load_lock(path, digest):
    raw = path.read_bytes()
    require(ac.sc.base.sha(raw) == digest, 'extension lock hash mismatch')
    lock = json.loads(raw)
    require(lock['schema_version'] == 1 and lock['scope'] == SCOPE and lock['certified_match'] is False, 'invalid experimental lock')
    require(lock['extension']['path'] == str(Path(__file__).resolve()), 'extension path changed')
    ac.sc.base.check_pin(lock['extension'])
    ac.sc.base.check_pin(lock['manifest'])
    parent = ac.load_lock(Path(lock['parent']['path']), lock['parent']['sha256'])
    baseline = Path(parent['baseline']['path']).read_bytes()
    manifest = json.loads(Path(lock['manifest']['path']).read_text())
    require(manifest['baseline_sha256'] == ac.sc.base.sha(baseline), 'manifest baseline mismatch')
    expected, spans = {}, []
    for task in manifest['tasks']:
        start, end = validate_task(task, baseline)
        require(task['id'] not in expected and not any(start < b and a < end for a, b in spans), 'duplicate/overlapping task')
        require(re.fullmatch(r'[0-9a-f]{64}', task['task_sha256']), 'task pin missing')
        spans.append((start, end))
        expected[task['id']] = {**task, 'expected_sha256': ac.sc.base.sha(baseline[start:end]), 'layout': layout(task)}
    require(expected and lock['tasks'] == expected, 'pinned task/layout changed')
    return lock, parent


def build_sources(parent, tasks, sources, out):
    require(not list(out.iterdir()), 'build directory must be empty')
    jobs = []
    for ident, source in sources.items():
        task = tasks[ident]
        folder = out / ident
        folder.mkdir()
        source_check(source, folder, parent, task)
        (folder / 'layout.ld').write_text(task['layout'])
        jobs.append({'id': ident, 'entry': int(task['entry'], 16)})
    (out / 'jobs.json').write_bytes(ac.sc.encode({'compile_flags': ac.runner.FLAGS,
        'link_flags': ac.runner.LLD_FLAGS, 'backend': 'lld', 'jobs': jobs}))
    report = ac.runner.build_batch(Path(parent['root']), out)
    require(len(report['jobs']) == len(jobs), 'missing build results')
    for row, tool in zip(report['commands'][:2], ('armcc', 'armlink'), strict=True):
        require(row['returncode'] == 0 and 'Product: MDK Professional 5.43' in row['stdout'] and
                'Component: ARM Compiler 5.06 update 7 (build 960)' in row['stdout'] and
                'Tool: '+tool in row['stdout'], 'compiler product/version changed')
    results = {}
    for row, job in zip(report['jobs'], jobs, strict=True):
        require(row['id'] == job['id'] and row['compile_returncode'] == row['link_returncode'] == 0,
                'compiler/linker rejected source; inspect redacted build report')
        folder, task = out / job['id'], tasks[job['id']]
        calls = object_calls((folder / 'candidate.o').read_bytes(), job['entry'], task['extern_functions'])
        elf = (folder / 'candidate.elf').read_bytes()
        actual = check_linked_calls(elf, job['entry'], calls, task['extern_functions'])
        results[job['id']] = {'bytes': actual, 'elf_sha256': ac.sc.base.sha(elf), 'relocations': calls}
    return results


def verify(path, digest, ident, candidate, output):
    lock, parent = load_lock(path, digest)
    require(ident in lock['tasks'], 'task absent from experimental lock')
    require(candidate.suffix == '.c' and candidate.is_file() and not candidate.is_symlink(), 'regular C required')
    require(not output.exists(), 'output exists')
    task, source = lock['tasks'][ident], candidate.read_text()
    start, end = validate_task(task, Path(parent['baseline']['path']).read_bytes())
    expected = Path(parent['baseline']['path']).read_bytes()[start:end]
    with tempfile.TemporaryDirectory(prefix='armcc-calls-') as temp:
        build = Path(temp)
        try:
            built = build_sources(parent, lock['tasks'], {ident: source}, build)[ident]
            result = {**ac.sc.compare(expected, built['bytes'], start), 'task': ident, 'scope': SCOPE,
                      'certified_match': False, 'matching_coverage': 'unknown',
                      'source_sha256': ac.sc.base.sha(source.encode()), 'lock_sha256': digest,
                      'elf_sha256': built['elf_sha256'], 'relocations': built['relocations'],
                      'external_callees_reconstructed': False, 'abi_status': task['abi_status']}
            load_lock(path, digest)
        except (OSError, ValueError, RuntimeError) as error:
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(build, output)
            (output / 'rejection.json').write_bytes(ac.sc.encode({'result': 'rejected', 'certified_match': False,
                'reason': ac.runner.scrub(str(error)), 'lock_sha256': digest}))
            raise
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(build, output)
        (output / 'comparison.json').write_bytes(ac.sc.encode(result))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    for name in ('parent-lock', 'manifest', 'output'):
        init.add_argument('--'+name, type=Path, required=True)
    init.add_argument('--parent-sha256', required=True)
    for name in ('check', 'verify'):
        child = sub.add_parser(name)
        child.add_argument('--lock', type=Path, required=True)
        child.add_argument('--lock-sha256', required=True)
        if name == 'verify':
            child.add_argument('--task', required=True)
            for field in ('source', 'output'):
                child.add_argument('--'+field, type=Path, required=True)
    args = p.parse_args()
    try:
        if args.command == 'init':
            print(initialize(args.parent_lock, args.parent_sha256, args.manifest, args.output))
        elif args.command == 'check':
            lock, _ = load_lock(args.lock, args.lock_sha256)
            print(f"Experimental call feedback: {len(lock['tasks'])} tasks; not swarm-ready or certification")
        else:
            result = verify(args.lock, args.lock_sha256, args.task, args.source, args.output)
            print(json.dumps(result, indent=2))
            return 0 if result['result'] == 'exact-range-bytes' else 2
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, StopIteration) as error:
        print('REJECTED: '+ac.runner.scrub(str(error)))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
