"""Offline extension controls; synthetic objects/C only, no Wine or licence access."""
import copy
import json
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import armcc_calls as cc
import prepare_next_batch as nb


def task():
    row = {'id': 'fn_00001000', 'entry': '0x1000', 'end_exclusive': '0x100a',
           'mode': 'thumb', 'signature': 'unsigned int (unsigned int)',
           'abi_status': 'hypothesis_requires_review', 'task_sha256': '1'*64,
           'extern_functions': {'fn_00002000': {'entry': '0x2000', 'mode': 'thumb',
                                                'signature': 'unsigned int (unsigned int)'}},
           'calls': [{'address': '0x1002', 'callee': 'fn_00002000'}]}
    return {**row, 'layout': cc.layout(row)}


SOURCE = ('extern unsigned int fn_00002000(unsigned int);\n'
          'unsigned int fn_00001000(unsigned int x) { return fn_00002000(x) + 3u; }\n')


def bl(address, target):
    displacement = (target-address-4) & 0x7fffff
    return struct.pack('<HH', 0xf000 | (displacement >> 12), 0xf800 | ((displacement >> 1) & 0x7ff))


def object_fixture():
    # ELF32 ET_REL: null, .text, .rel.text, .symtab, .strtab, .shstrtab.
    data = bytearray(512)
    data[:7] = b'\x7fELF\x01\x01\x01'
    struct.pack_into('<HHIIIIIHHHHHH', data, 16, 1, 40, 1, 0, 0, 52,
                     0x05000000, 52, 0, 0, 40, 6, 5)
    names = b'\0.text\0.rel.text\0.symtab\0.strtab\0.shstrtab\0'
    code = b'\x10\xb5' + bl(0, 0) + b'\x10\xbd'
    symbols = b'\0fn_00002000\0'
    sections = [(0,)*10,
        (1, 1, 6, 0, 300, 8, 0, 0, 2, 0),
        (7, 9, 0, 0, 308, 8, 3, 1, 4, 8),
        (17, 2, 0, 0, 316, 32, 4, 1, 4, 16),
        (25, 3, 0, 0, 348, len(symbols), 0, 0, 1, 0),
        (33, 3, 0, 0, 380, len(names), 0, 0, 1, 0)]
    for i, section in enumerate(sections):
        struct.pack_into('<10I', data, 52+i*40, *section)
    data[300:308] = code
    struct.pack_into('<II', data, 308, 2, (1 << 8) | 10)
    struct.pack_into('<IIIBBH', data, 332, 1, 0, 0, 0x12, 0, 0)
    data[348:348+len(symbols)] = symbols
    data[380:380+len(names)] = names
    return data


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.raw = bytearray(0x3000)
        self.raw[0x1002:0x1006] = bl(0x1002, 0x2000)

    def test_decode_forward_backward_and_limits(self):
        for address, target in [(0x1002, 0x2000), (0x2002, 0x1000), (0x500000, 0x100004), (0, 0x400002)]:
            self.assertEqual(cc.thumb_bl(bl(address, target), 0, address), target)
        for data, off in [(b'\0'*4, 0), (bl(0, 8), 1), (bl(0, 8)[:3], 0), (b'\x00\xf0\x00\xe8', 0)]:
            with self.assertRaises(ValueError):
                cc.thumb_bl(data, off, 0)

    def test_stock_target_and_scope_restrictions(self):
        self.assertEqual(cc.validate_task(task(), self.raw), (0x1000, 0x100a))
        for change in ({'mode': 'arm'}, {'calls': []}, {'extern_functions': {}},
                       {'calls': [{'address': '0x1004', 'callee': 'fn_00002000'}]},
                       {'calls': task()['calls']*2}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                cc.validate_task({**task(), **change}, self.raw)
        broken = copy.deepcopy(task())
        broken['extern_functions']['fn_00002000']['mode'] = 'arm'
        with self.assertRaises(ValueError):
            cc.validate_task(broken, self.raw)
        self.raw[0x1002:0x1006] = bl(0x1002, 0x2002)
        with self.assertRaisesRegex(ValueError, 'original call target'):
            cc.validate_task(task(), self.raw)

    def test_layout_symbols_are_thumb_and_have_no_callee_body(self):
        script = cc.layout(task())
        self.assertIn('fn_00002000 = 0x2001;', script)
        self.assertEqual(script.count('PT_LOAD'), 1)

    def test_independent_disassembly_requires_full_original_bytes(self):
        raw = b'\x00\x20\x70\x47'
        nb.independent_decode('0: 2000 movs r0, #0\n2: 4770 bx lr\n', raw, 0, 4)
        for text in ('0: 2001 movs r0, #1\n2: 4770 bx lr\n', '0: 2000 movs r0, #0\n',
                     '0: 2000 <unknown>\n2: 4770 bx lr\n'):
            with self.assertRaises(ValueError):
                nb.independent_decode(text, raw, 0, 4)


class ObjectTests(unittest.TestCase):
    def test_accept_only_fixed_thumb_call(self):
        self.assertEqual(cc.object_calls(bytes(object_fixture()), 0x1000, task()['extern_functions']),
                         [{'offset': 2, 'callee': 'fn_00002000'}])
        hidden = object_fixture(); hidden[345] = 2
        self.assertEqual(cc.object_calls(bytes(hidden), 0x1000, task()['extern_functions']),
                         [{'offset': 2, 'callee': 'fn_00002000'}])

    def test_malformed_relocations_symbols_and_extra_data(self):
        changes = [(312, (1<<8)|2), (312, (1<<8)|30), (312, (8<<8)|10),
                   (308, 3), (308, 6), (336, 2), (340, 4),
                   (52+2*40+24, 99), (52+2*40+28, 99),
                   (52+2*40+4, 4), (52+3*40+4, 3),
                   (52+4*40+8, 2), (52+1*40+32, 8)]
        for offset, value in changes:
            data = object_fixture()
            struct.pack_into('<I', data, offset, value)
            with self.subTest(offset=offset, value=value), self.assertRaises(ValueError):
                cc.object_calls(bytes(data), 0x1000, task()['extern_functions'])
        for offset, value in [(344, 0x22), (345, 1), (345, 3), (345, 128), (346, 1), (349, ord('X'))]:
            data = object_fixture(); data[offset] = value
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                cc.object_calls(bytes(data), 0x1000, task()['extern_functions'])

    def test_offcut_addend_and_truncation(self):
        data = object_fixture()
        data[302:306] = bl(0, 2)
        with self.assertRaisesRegex(ValueError, 'addend'):
            cc.object_calls(bytes(data), 0x1000, task()['extern_functions'])
        for length in (0, 40, 150, 310, 350, 400):
            with self.subTest(length=length), self.assertRaises(ValueError):
                cc.object_calls(bytes(object_fixture()[:length]), 0x1000, task()['extern_functions'])


@unittest.skipUnless(shutil.which('clang'), 'requires local Clang AST analyzer')
class SourceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.out = Path(temp.name)
        self.parent = {'tools': {'analyzer': {'path': shutil.which('clang')}}}

    def check(self, source):
        return cc.source_check(source, self.out, self.parent, task())

    def test_pinned_prototype_and_ordinary_direct_call(self):
        self.assertEqual(self.check(SOURCE)['fn_00001000'], task()['signature'])

    def test_reject_extra_definitions_calls_state_and_abi(self):
        cases = [SOURCE.replace('extern unsigned int', 'extern int'),
            SOURCE.replace('fn_00002000', 'fn_00002002'),
            SOURCE.replace('extern unsigned int fn_00002000(unsigned int);',
                           'unsigned int fn_00002000(unsigned int a) { return a; }'),
            SOURCE.replace('return fn_', 'static unsigned int q; return q + fn_'),
            'unsigned int global;\n'+SOURCE,
            SOURCE.replace('return fn_', '__asm__("nop"); return fn_'),
            SOURCE.replace('return fn_', 'unsigned int *q = (unsigned int *)1234; return *q + fn_'),
            SOURCE.replace('return fn_00002000(x)', 'return fn_00001000(x)'),
            SOURCE.replace('return fn_00002000(x)', 'unsigned int (*f)(unsigned int) = fn_00002000; return f(x)'),
            SOURCE.replace('return fn_00002000(x)', 'return ((unsigned int (*)(unsigned int))42)(x)'),
            '#define X 1\n'+SOURCE]
        for source in cases:
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.check(source)


@unittest.skipUnless(shutil.which('clang') and shutil.which('ld.lld'), 'requires local LLVM')
class LinkedTests(unittest.TestCase):
    def test_real_link_calls_and_full_load_comparison(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            row = task()
            parent = {'tools': {'analyzer': {'path': shutil.which('clang')}}}
            cc.source_check(SOURCE, out, parent, row)
            (out / 'layout.ld').write_text(row['layout'])
            cc.ac.sc.base.run(['clang', *cc.ac.sc.FLAGS, '-c', 'candidate.c', '-o', 'candidate.o'], out)
            cc.ac.sc.base.run(['ld.lld', *cc.ac.runner.LLD_FLAGS, '-T', 'layout.ld', 'candidate.o', '-o', 'candidate.elf'], out)
            elf = (out / 'candidate.elf').read_bytes()
            data = cc.ac.runtime_bytes(elf, 0x1000)
            sites = [i for i in range(0, len(data)-3, 2)
                     if struct.unpack_from('<H', data, i)[0] & 0xf800 == 0xf000]
            self.assertEqual(len(sites), 1)
            calls = [{'offset': sites[0], 'callee': 'fn_00002000'}]
            self.assertEqual(cc.check_linked_calls(elf, 0x1000, calls, row['extern_functions']), data)
            changed = copy.deepcopy(row['extern_functions'])
            changed['fn_00002000']['entry'] = '0x2002'
            with self.assertRaisesRegex(ValueError, 'linked call target'):
                cc.check_linked_calls(elf, 0x1000, calls, changed)
            damaged = bytearray(elf)
            # Toggle a byte in the actual code segment at the call displacement.
            phoff = struct.unpack_from('<I', elf, 28)[0]
            offset = struct.unpack_from('<I', elf, phoff+4)[0]
            damaged[offset+sites[0]+2] ^= 1
            with self.assertRaises(ValueError):
                cc.check_linked_calls(bytes(damaged), 0x1000, calls, row['extern_functions'])


class LockTests(unittest.TestCase):
    def test_extension_manifest_parent_and_expected_bytes_pins(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            raw = bytearray(0x3000); raw[0x1002:0x1006] = bl(0x1002, 0x2000)
            baseline = folder / 'baseline.bin'; baseline.write_bytes(raw)
            parent = {'baseline': cc.ac.sc.base.pin(baseline)}
            manifest = folder / 'manifest.json'
            manifest.write_bytes(cc.ac.sc.encode({'baseline_sha256': cc.ac.sc.base.sha(raw), 'tasks': [task()]}))
            lock = folder / 'lock.json'
            with patch.object(cc.ac, 'load_lock', return_value=parent) as load:
                digest = cc.initialize(folder / 'parent.json', 'a'*64, manifest, lock)
                self.assertEqual(cc.load_lock(lock, digest)[1], parent)
                load.assert_called_with(folder / 'parent.json', 'a'*64)
                with self.assertRaises(ValueError):
                    cc.initialize(folder / 'parent.json', 'a'*64, manifest, lock)
                for field, value in [('scope', 'certified'), ('certified_match', True), ('tasks', {})]:
                    changed = json.loads(lock.read_text()); changed[field] = value
                    file = folder / 'changed.json'; file.write_bytes(cc.ac.sc.encode(changed))
                    with self.subTest(field=field), self.assertRaises(ValueError):
                        cc.load_lock(file, cc.ac.sc.base.sha(file.read_bytes()))
                with self.assertRaises(ValueError):
                    cc.load_lock(lock, '0'*64)
                manifest.write_text('{}')
                with self.assertRaises(ValueError):
                    cc.load_lock(lock, digest)


if __name__ == '__main__':
    unittest.main()
