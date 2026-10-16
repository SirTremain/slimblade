"""Offline policy/lock/ELF tests. No private license read and no Wine execution."""
import copy
import fcntl
import json
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import armcc_compare as ac


def task(entry=0x1000):
    row = {'id': f'fn_{entry:08x}', 'entry': hex(entry), 'end_exclusive': hex(entry + 8),
           'mode': 'thumb', 'signature': 'unsigned int (unsigned int)',
           'abi_status': 'hypothesis_requires_review'}
    return {**row, 'layout': ac.layout(row)}


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_manifest_rejects_unreviewed_shapes(self):
        row = task()
        self.assertEqual(ac.validate_task(row, 0x2000), (0x1000, 0x1008))
        for delta in ({'entry': '0x1001'}, {'end_exclusive': '0x1000'}, {'mode': 'arm'},
                      {'id': 'wrong'}, {'signature': 'int (...)'}, {'abi_status': 'certified'},
                      {'signature': 'int (struct X *)'}):
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                ac.validate_task({**row, **delta}, 0x2000)

    def test_tree_pin_detects_content_addition_and_removal(self):
        file = self.root / 'tool'
        file.write_bytes(b'first')
        first = ac.tree_pin(self.root)
        file.write_bytes(b'other')
        self.assertNotEqual(first, ac.tree_pin(self.root))
        file.write_bytes(b'first')
        extra = self.root / 'extra'
        extra.write_bytes(b'x')
        self.assertNotEqual(first, ac.tree_pin(self.root))
        extra.unlink()
        self.assertEqual(first, ac.tree_pin(self.root))

    def test_tree_pin_rejects_dangling_and_directory_links(self):
        link = self.root / 'link'
        link.symlink_to(self.root / 'missing')
        with self.assertRaises(ValueError):
            ac.tree_pin(self.root)
        link.unlink()
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            ac.tree_pin(self.root)

    def test_runner_mounts_no_reference_or_device(self):
        (self.root / '.decomp/armcc-wine-work').mkdir(parents=True)
        cmd = ac.runner.command(self.root, self.root / 'build')
        self.assertIn('--clearenv', cmd)
        self.assertNotIn('--dev-bind', cmd)
        self.assertNotIn('/dev/bus/usb', str(cmd))
        self.assertNotIn('stock-v4.49.bin', str(cmd))
        self.assertNotIn('keil-license.txt', str(cmd))
        pos = cmd.index(str(self.root / '.decomp/keil-mdk-5.43a'))
        self.assertEqual(cmd[pos - 1], '--ro-bind')
        self.assertEqual(cmd.count('--chdir'), 1)
        self.assertEqual(cmd[cmd.index('--chdir') + 1], '/build')

    def test_runner_redacts_license_shapes(self):
        self.assertEqual(ac.runner.scrub('LIC: AAAAA-BBBBB-CCCCC-DDDDD-EEEEE-FFFFF'),
                         'LIC: [REDACTED]')

    def test_runner_serializes_private_prefix(self):
        state = self.root / '.decomp/armcc-wine-work'
        state.mkdir(parents=True)
        with (state / 'compiler.lock').open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with mock.patch.object(ac.runner.subprocess, 'run') as execute:
                with self.assertRaisesRegex(RuntimeError, 'compiler busy'):
                    ac.runner.build_batch(self.root, self.root)
                execute.assert_not_called()

    def test_object_alignment_and_runtime_relocations(self):
        # Synthetic ELF object headers, not firmware or compiler output.
        data = bytearray(208)
        data[:7] = b'\x7fELF\x01\x01\x01'
        struct.pack_into('<HHIIIIIHHHHHH', data, 16,
                         1, 40, 1, 0, 0, 52, 0x05000000, 52, 0, 0, 40, 3, 2)
        struct.pack_into('<10I', data, 92, 1, 1, 6, 0, 200, 4, 0, 0, 2, 0)
        struct.pack_into('<10I', data, 132, 0, 3, 0, 0, 172, 7, 0, 0, 1, 0)
        data[172:179] = b'\0.text\0'
        ac.object_check(bytes(data), 0x1002)
        struct.pack_into('<I', data, 92+32, 4)
        ac.object_check(bytes(data), 0x1000)
        with self.assertRaisesRegex(ValueError, 'alignment'):
            ac.object_check(bytes(data), 0x1002)
        # Turn the string-table header into an allocated-data relocation target.
        struct.pack_into('<10I', data, 52, 0, 9, 0, 0, 0, 8, 0, 1, 4, 8)
        with self.assertRaisesRegex(ValueError, 'relocations'):
            ac.object_check(bytes(data), 0x1000)
        with self.assertRaises(ValueError):
            ac.object_check(bytes(data[:90]), 0x1000)

    @unittest.skipUnless(shutil.which('clang'), 'requires local AST analyzer')
    def test_source_signature_and_policy_before_compile(self):
        lock = {'tools': {'analyzer': {'path': '/usr/bin/clang'}}}
        source = 'unsigned int fn_00001000(unsigned int a) { return a + 17u; }'
        self.assertEqual(ac.source_check(source, self.root, lock, task()), task()['signature'])
        cases = [source.replace('unsigned int fn_', 'int fn_'),
                 'unsigned int fn_00001000(unsigned int a) { __asm__("nop"); return a; }',
                 'unsigned int fn_00001000(unsigned int a) { return *(unsigned int *)a; }',
                 'unsigned int x; unsigned int fn_00001000(unsigned int a) { return x+a; }',
                 'unsigned int f(void); unsigned int fn_00001000(unsigned int a) { return f()+a; }',
                 'unsigned int fn_00001000(unsigned int a) { static unsigned int x; return x+a; }',
                 'typedef unsigned int U; U fn_00001000(U a) { return a; }',
                 '#define A 1\n' + source]
        for candidate in cases:
            with self.subTest(source=candidate), self.assertRaises(ValueError):
                ac.source_check(candidate, self.root, lock, task())


@unittest.skipUnless(shutil.which('clang') and shutil.which('ld.lld'), 'requires local LLVM')
class ElfControls(unittest.TestCase):
    def test_complete_load_bytes_mapping_and_metadata_are_checked(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            row = task(0x1002)
            lock = ac.sc.tool_lock()
            elf, _ = ac.sc.compile_leaf('unsigned int fn_00001002(unsigned int a) { return a+17u; }',
                                       out, lock, row['id'], row['layout'])
            self.assertTrue(ac.runtime_bytes(elf, 0x1002))
            phoff = struct.unpack_from('<I', elf, 28)[0]
            shoff = struct.unpack_from('<I', elf, 32)[0]
            # Entry state, executable/write permissions, load mapping, bytes
            # length/BSS, allocated section size, and unexpected extra flags.
            mutations = [(24, 0x1002), (36, 0), (phoff + 12, 0x1004), (phoff + 24, 7),
                         (phoff + 20, 100), (shoff + 40 + 20, 2)]
            for offset, value in mutations:
                damaged = bytearray(elf)
                struct.pack_into('<I', damaged, offset, value)
                with self.subTest(offset=offset), self.assertRaises(ValueError):
                    ac.runtime_bytes(bytes(damaged), 0x1002)


class LockControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        file = self.root / 'file'
        file.write_bytes(b'fixture')
        self.pin = ac.sc.base.pin(file)
        names = ('compiler', 'armlink', 'linker', 'analyzer', 'python', 'sandbox')
        for patcher in (mock.patch.object(ac, 'tool_paths', return_value={n: file for n in names}),
                        mock.patch.object(ac, 'tree_paths', return_value=[]),
                        mock.patch.object(ac, 'host_dependencies', return_value=[str(file)])):
            patcher.start()
            self.addCleanup(patcher.stop)
        row = {**task(0), 'end_exclusive': '0x6', 'task_sha256': '1'*64,
               'expected_sha256': ac.sc.base.sha(b'fixtur')}
        self.lock = {'schema_version': 1, 'scope': ac.SCOPE, 'certified_match': False,
                     'root': str(self.root),
                     'compiler_qualification': 'candidate_only', 'compile_flags': ac.runner.FLAGS,
                     'link_flags': ac.runner.LLD_FLAGS, 'ast_flags': ac.AST_FLAGS,
                     'python_version': sys.version, 'code': [ac.sc.base.pin(p) for p in ac.code_files()],
                     'tools': {name: self.pin for name in names},
                     'host_libraries': [self.pin], 'tool_trees': [], 'baseline': self.pin,
                     'baseline_bytes': 7, 'tasks': {row['id']: row}}
        self.path = self.root / 'lock.json'

    def write(self, lock):
        self.path.write_bytes(ac.sc.encode(lock))
        return ac.sc.base.sha(self.path.read_bytes())

    def test_tampered_flags_tools_verifier_reference_rejected(self):
        for change in ({'scope': 'certified'}, {'certified_match': True}, {'compile_flags': []},
                       {'link_flags': []}, {'ast_flags': []}, {'python_version': 'other'},
                       {'tools': {}}, {'code': []}, {'baseline_bytes': 8}, {'host_libraries': []},
                       {'tool_trees': [self.pin]}, {'tasks': {}}, {'root': 'relative'}):
            changed = {**self.lock, **change}
            digest = self.write(changed)
            with self.subTest(change=change), self.assertRaises(ValueError):
                ac.load_lock(self.path, digest)
        digest = self.write(self.lock)
        self.assertEqual(ac.load_lock(self.path, digest), self.lock)
        with self.assertRaises(ValueError):
            ac.load_lock(self.path, '0'*64)
        Path(self.pin['path']).write_bytes(b'changed')
        with self.assertRaises(ValueError):
            ac.load_lock(self.path, digest)

    def test_expected_bytes_and_layout_pins(self):
        for delta in ({'expected_sha256': '0'*64}, {'layout': 'ignored'}, {'task_sha256': 'bad'}):
            lock = copy.deepcopy(self.lock)
            lock['tasks']['fn_00000000'].update(delta)
            digest = self.write(lock)
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                ac.load_lock(self.path, digest)

    def test_no_prebuilt_symlink_or_output_overwrite(self):
        row = task()
        lock = {**self.lock, 'tasks': {row['id']: row}}
        candidate = self.root / 'candidate.c'
        candidate.write_text('unsigned int fn_00001000(unsigned int a) { return a; }')
        link = self.root / 'link.c'
        link.symlink_to(candidate)
        output = self.root / 'out'
        with mock.patch.object(ac, 'load_lock', return_value=lock):
            for source in (self.root / 'candidate.elf', link):
                with self.assertRaises(ValueError):
                    ac.verify(self.path, '', row['id'], source, output)
            output.mkdir()
            (output / 'keep').write_text('keep')
            with self.assertRaises(ValueError):
                ac.verify(self.path, '', row['id'], candidate, output)
        self.assertEqual((output / 'keep').read_text(), 'keep')


if __name__ == '__main__':
    unittest.main()
