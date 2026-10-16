#!/usr/bin/env python3
"""Pinned ARMCC5/LLD leaf feedback; not a whole-image or source certificate.

The coordinator owns this code, immutable lock and reference image. Workers
supply C only. The licensed compiler runs headlessly in a separate build sandbox.
The same-UID coordinator environment is trusted, not a hostile-worker sandbox.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import struct
import sys
import tempfile

import armcc_runner as runner
import stock_compare as sc

SCOPE = 'armcc5-leaf-feedback-v1'
AST_FLAGS = ['--target=arm-none-eabi', '-mcpu=arm968e-s', '-mthumb',
             '-mfloat-abi=soft', '-mabi=aapcs', '-std=gnu99', '-funsigned-char',
             '-fshort-enums', '-fshort-wchar', '-ffreestanding', '-fno-builtin',
             '-nostdinc', '-Werror', '-fsyntax-only', '-Xclang', '-ast-dump=json']
TYPE_WORDS = {'void', 'unsigned', 'signed', 'int', 'short', 'long', 'char',
              'const', 'volatile', 'restrict', '_Bool'}
require = sc.require


def layout(task):
    return sc.layout(task).replace('.ARM.attributes)', '.ARM.attributes .arm_vfe_header)').replace(
        ' .symtab 0', ' .debug_frame 0 : { *(.debug_frame) }\n .symtab 0')


def tree_pin(path):
    """Pin tool files including symlink target bytes, never private license state."""
    require(path.is_dir(), 'missing tool directory: ' + str(path))
    rows = []
    for file in sorted(path.rglob('*')):
        if file.is_symlink():
            require(file.is_file(), 'directory/dangling tool symlink unsupported')
            rows.append([str(file.relative_to(path)), str(file.readlink()), sc.base.sha(file.read_bytes())])
        elif file.is_file():
            rows.append([str(file.relative_to(path)), sc.base.sha(file.read_bytes())])
    require(rows, 'empty tool tree')
    return {'path': str(path.resolve()), 'files': len(rows), 'sha256': sc.base.sha(sc.encode(rows))}


def code_files():
    return [Path(__file__), Path(runner.__file__), Path(sc.__file__), sc.PROTOTYPE,
            runner.PREP / 'keil_gui_probe.py', runner.PREP / 'offline_identity.py']


def tool_paths(root):
    return {
        'compiler': root / 'ARMCC/bin/armcc.exe', 'armlink': root / 'ARMCC/bin/armlink.exe',
        'linker': Path('/usr/bin/ld.lld'), 'analyzer': Path('/usr/bin/clang'),
        'python': Path(sys.executable), 'sandbox': Path('/usr/bin/bwrap')}


def tree_paths(root):
    return [root / path for path in (
        'ARMCC', '.decomp/tools/wine-11.19', '.decomp/keil-mdk-5.43a/ARM/sw')]


def host_dependencies(root):
    deps = set()
    paths = tool_paths(root)
    host_executables = [str(paths[n]) for n in ('linker', 'analyzer', 'python', 'sandbox')]
    host_executables += [str(root / '.decomp/tools/wine-11.19/usr/bin' / n)
                         for n in ('wine', 'wineserver')]
    for binary in host_executables:
        for line in sc.base.run(['/usr/bin/ldd', binary]).splitlines():
            deps.update(re.findall(r'(/[^\s()]+)', line))
    return sorted(deps)


def tool_lock(root):
    root = root.resolve()
    tools = {name: sc.base.pin(path) for name, path in tool_paths(root).items()}
    trees = [tree_pin(path) for path in tree_paths(root)]
    return {'root': str(root), 'tools': tools, 'tool_trees': trees,
            'host_libraries': [sc.base.pin(p) for p in host_dependencies(root)],
            'code': [sc.base.pin(p) for p in code_files()],
            'compile_flags': runner.FLAGS, 'link_flags': runner.LLD_FLAGS,
            'ast_flags': AST_FLAGS, 'python_version': sys.version,
            'analyzer_version': sc.base.run(['/usr/bin/clang', '--version']),
            'linker_version': sc.base.run(['/usr/bin/ld.lld', '--version']),
            'license_state': 'private and unpinned; runtime must report MDK Professional 5.43',
            'wine_state': 'persistent real-host prefix; not independently portable'}


def validate_task(task, size):
    require(task.get('mode') == 'thumb', 'only Thumb leaves supported')
    require(task.get('abi_status') == 'hypothesis_requires_review', 'unsupported ABI status')
    start, end = int(task['entry'], 16), int(task['end_exclusive'], 16)
    require(0 <= start < end <= size and start % 2 == end % 2 == 0, 'bad range')
    require(task['id'] == f'fn_{start:08x}', 'symbol/entry mismatch')
    signature = task['signature']
    require(isinstance(signature, str) and signature.count('(') == signature.count(')') == 1
            and '...' not in signature and
            set(re.findall(r'[A-Za-z_]\w*', signature)) <= TYPE_WORDS,
            'explicit integer/pointer signature required')
    return start, end


def initialize(root, baseline, manifest, destination):
    require(not destination.exists(), 'lock exists; never overwrite an oracle')
    raw, packet_data = baseline.read_bytes(), manifest.read_bytes()
    packet = json.loads(packet_data)
    require(packet['baseline_sha256'] == sc.base.sha(raw), 'baseline/manifest mismatch')
    tasks, spans = {}, []
    for task in packet['tasks']:
        start, end = validate_task(task, len(raw))
        require(re.fullmatch(r'[0-9a-f]{64}', task['task_sha256']), 'missing task definition pin')
        require(task['id'] not in tasks, 'duplicate task')
        require(not any(start < b and a < end for a, b in spans), 'overlapping tasks')
        spans.append((start, end))
        tasks[task['id']] = {**task, 'expected_sha256': sc.base.sha(raw[start:end]),
                            'layout': layout(task)}
    require(tasks, 'empty manifest')
    lock = {**tool_lock(root), 'schema_version': 1, 'scope': SCOPE,
            'compiler_qualification': 'candidate_only', 'certified_match': False,
            'baseline': sc.base.pin(baseline), 'baseline_bytes': len(raw),
            'manifest_sha256': sc.base.sha(packet_data), 'tasks': tasks}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(sc.encode(lock))
    destination.chmod(0o444)
    return sc.base.sha(destination.read_bytes())


def load_lock(path, expected_hash):
    data = path.read_bytes()
    require(sc.base.sha(data) == expected_hash, 'lock hash mismatch')
    lock = json.loads(data)
    require(lock.get('schema_version') == 1 and lock.get('scope') == SCOPE, 'unsupported lock')
    require(lock['certified_match'] is False and lock['compiler_qualification'] == 'candidate_only',
            'feedback cannot certify compiler or source')
    for name, value in (('compile_flags', runner.FLAGS), ('link_flags', runner.LLD_FLAGS),
                        ('ast_flags', AST_FLAGS), ('python_version', sys.version)):
        require(lock[name] == value, name + ' changed')
    require([p['path'] for p in lock['code']] == [str(p.resolve()) for p in code_files()],
            'coordinator code paths changed')
    root = Path(lock['root'])
    require(root.is_absolute() and root.resolve() == root, 'noncanonical coordinator root')
    require({name: p['path'] for name, p in lock['tools'].items()} ==
            {name: str(p) for name, p in tool_paths(root).items()}, 'tool paths changed')
    require([p['path'] for p in lock['tool_trees']] == [str(p.resolve()) for p in tree_paths(root)],
            'tool tree paths changed')
    require([p['path'] for p in lock['host_libraries']] == host_dependencies(root),
            'host library set changed')
    for record in [*lock['tools'].values(), *lock['host_libraries'], *lock['code'], lock['baseline']]:
        sc.base.check_pin(record)
    for tree in lock['tool_trees']:
        require(tree_pin(Path(tree['path'])) == tree, 'tool tree changed')
    require(Path(lock['baseline']['path']).stat().st_size == lock['baseline_bytes'], 'baseline size changed')
    require(lock['tasks'], 'empty lock')
    raw = Path(lock['baseline']['path']).read_bytes()
    spans = []
    for ident, task in lock['tasks'].items():
        start, end = validate_task(task, lock['baseline_bytes'])
        require(not any(start < b and a < end for a, b in spans), 'overlapping tasks')
        spans.append((start, end))
        require(ident == task['id'] and task['layout'] == layout(task), 'task layout changed')
        require(re.fullmatch(r'[0-9a-f]{64}', task['task_sha256']), 'missing task definition pin')
        require(sc.base.sha(raw[start:end]) == task['expected_sha256'], 'expected bytes changed')
    return lock


def object_check(data, entry):
    """Reject layout-forced misalignment, extra allocation and runtime relocations.

    SUBALIGN(2) must not silently lower the alignment of a literal-pool-bearing
    object. These leaf assignments have no external calls/data relocations.
    Debug relocations are allowed and must be resolved by the linker.
    """
    def take(offset, size):
        require(0 <= offset <= offset + size <= len(data), 'truncated object')
        return data[offset:offset + size]
    require(take(0, 7) == b'\x7fELF\x01\x01\x01', 'expected ELF32 LE object')
    h = struct.unpack('<HHIIIIIHHHHHH', take(16, 36))
    kind, machine, version, pc, phoff, shoff, flags, ehsize, phsize, phnum, shsize, shnum, shstr = h
    require((kind, machine, version, pc, flags, ehsize, phnum, shsize) ==
            (1, 40, 1, 0, 0x05000000, 52, 0, 40), 'unsupported object header')
    require(0 < shstr < shnum < 4096, 'bad object tables')
    sections = [struct.unpack('<10I', take(shoff + i * 40, 40)) for i in range(shnum)]
    allocated = [(i, s) for i, s in enumerate(sections) if s[2] & 2 and s[5]]
    require(len(allocated) == 1, 'extra object allocation')
    index, text = allocated[0]
    names = take(sections[shstr][4], sections[shstr][5])
    require(text[0] < len(names) and names[text[0]:].split(b'\0', 1)[0] == b'.text' and
            (text[1], text[2], text[3]) == (1, 6, 0), 'unexpected object text')
    require(text[8] in (2, 4) and entry % text[8] == 0, 'object alignment incompatible with entry')
    take(text[4], text[5])
    for s in sections:
        if s[1] in (4, 9) and s[5]:
            require(s[7] < shnum and not sections[s[7]][2] & 2,
                    'runtime relocations outside leaf scope')


def runtime_bytes(elf, entry):
    require(sc.base.elf_view(elf)['elf_flags'] == 0x05000200, 'changed ELF ABI flags')
    return sc.runtime_bytes(elf, entry)


def source_check(source, build, lock, task):
    sc.base.source_policy(source)
    # Exclude language constructs whose compiler defaults need broader ABI review.
    require(not re.search(r'\b(?:float|double|enum|struct|union|typedef)\b', source),
            'aggregate/float/typedef ABI outside leaf scope')
    (build / 'candidate.c').write_text(source)
    ast = json.loads(sc.base.run([lock['tools']['analyzer']['path'], *AST_FLAGS,
                                 'candidate.c'], build))
    sc.leaf_policy(ast, task['id'])
    function = next(n for n in ast['inner'] if n.get('kind') == 'FunctionDecl')
    signature = function['type']['qualType']
    require(signature == task['signature'], 'source signature differs from pinned hypothesis')
    return signature


def build_sources(lock, sources, out):
    """Fresh source builds only; out exists but must be empty."""
    require(not list(out.iterdir()), 'build directory must be empty')
    jobs, signatures = [], {}
    for ident, source in sources.items():
        require(ident in lock['tasks'], 'task absent from lock')
        task = lock['tasks'][ident]
        build = out / ident
        build.mkdir()
        signatures[ident] = source_check(source, build, lock, task)
        (build / 'layout.ld').write_text(task['layout'])
        jobs.append({'id': ident, 'entry': int(task['entry'], 16)})
    (out / 'jobs.json').write_bytes(sc.encode({'compile_flags': runner.FLAGS,
        'link_flags': runner.LLD_FLAGS, 'backend': 'lld', 'jobs': jobs}))
    report = runner.build_batch(Path(lock['root']), out)
    require(len(report['jobs']) == len(jobs), 'missing build results')
    for row, job in zip(report['jobs'], jobs, strict=True):
        require(row['id'] == job['id'] and row['compile_returncode'] == row['link_returncode'] == 0,
                'compiler/linker rejected source; inspect redacted build report')
        object_check((out / job['id'] / 'candidate.o').read_bytes(), job['entry'])
    for row, tool in zip(report['commands'][:2], ('armcc', 'armlink'), strict=True):
        require(row['returncode'] == 0 and 'Product: MDK Professional 5.43' in row['stdout'] and
                'Component: ARM Compiler 5.06 update 7 (build 960)' in row['stdout'] and
                'Tool: ' + tool in row['stdout'], 'compiler product/version changed')
    return {ident: {'elf': (out / ident / 'candidate.elf').read_bytes(), 'signature': signatures[ident]}
            for ident in sources}


def verify(lock_path, lock_hash, task_id, candidate, output):
    lock = load_lock(lock_path, lock_hash)
    require(task_id in lock['tasks'], 'task absent from lock')
    require(candidate.suffix == '.c' and candidate.is_file() and not candidate.is_symlink(),
            'regular C source required; no prebuilt candidate')
    require(not output.exists(), 'output already exists')
    task = lock['tasks'][task_id]
    start, end = validate_task(task, lock['baseline_bytes'])
    expected = Path(lock['baseline']['path']).read_bytes()[start:end]
    require(sc.base.sha(expected) == task['expected_sha256'], 'expected bytes changed')
    source = candidate.read_text()
    with tempfile.TemporaryDirectory(prefix='armcc-leaf-') as temp:
        build = Path(temp)
        try:
            built = build_sources(lock, {task_id: source}, build)[task_id]
            actual = runtime_bytes(built['elf'], start)
        except (OSError, ValueError, RuntimeError) as error:
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(build, output)
            (output / 'rejection.json').write_bytes(sc.encode({
                'result': 'rejected', 'reason': runner.scrub(str(error)),
                'certified_match': False, 'lock_sha256': lock_hash}))
            raise
        result = {**sc.compare(expected, actual, start), 'task': task_id, 'scope': SCOPE,
                  'certified_match': False, 'matching_coverage': 'unknown',
                  'compiler_qualification': 'candidate_only', 'abi_status': task['abi_status'],
                  'signature': built['signature'], 'source_sha256': sc.base.sha(source.encode()),
                  'elf_sha256': sc.base.sha(built['elf']), 'lock_sha256': lock_hash}
        load_lock(lock_path, lock_hash)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(build, output)
        (output / 'comparison.json').write_bytes(sc.encode(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    for name in ('root', 'baseline', 'manifest', 'output'):
        init.add_argument('--' + name, type=Path, required=True)
    for command in ('check', 'verify'):
        child = sub.add_parser(command)
        child.add_argument('--lock', type=Path, required=True)
        child.add_argument('--lock-sha256', required=True)
        if command == 'verify':
            child.add_argument('--task', required=True)
            for name in ('source', 'output'):
                child.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'init':
            print(initialize(args.root, args.baseline, args.manifest, args.output))
        elif args.command == 'check':
            lock = load_lock(args.lock, args.lock_sha256)
            print(f"Pinned ARMCC5/LLD feedback: {len(lock['tasks'])} leaves; not certification")
        else:
            result = verify(args.lock, args.lock_sha256, args.task, args.source, args.output)
            print(json.dumps(result, indent=2))
            return 0 if result['result'] == 'exact-range-bytes' else 2
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, StopIteration) as error:
        print('REJECTED: ' + runner.scrub(str(error)), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
