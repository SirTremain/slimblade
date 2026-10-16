"""Offline synthetic controls; no vendor bytes, downloads or tool execution."""
import importlib.util
from pathlib import Path
import struct
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "decomp/results/preparation" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sdk = load("inspect_sdk")
probe = load("gcc_sdk_probe")


def synthetic_elf():
    data = bytearray(0x200)
    data[:7] = b"\x7fELF\x01\x01\x01"
    struct.pack_into("<HHIIIIIHHHHHH", data, 16,
                     2, 40, 1, 0x1001, 0, 0x40, 0, 52, 0, 0, 40, 4, 0)
    sections = [(0,) * 10,
                (0, 1, 6, 0x1000, 0x100, 8, 0, 0, 2, 0),
                (0, 3, 0, 0, 0x110, 6, 0, 0, 1, 0),
                (0, 2, 0, 0, 0x120, 32, 2, 0, 4, 16)]
    for i, row in enumerate(sections):
        struct.pack_into("<IIIIIIIIII", data, 0x40 + i * 40, *row)
    data[0x100:0x108] = b"abcdefgh"
    data[0x110:0x116] = b"\0test\0"
    struct.pack_into("<IIIBBH", data, 0x130, 1, 0x1001, 8, 0x12, 0, 1)
    return data


class OccurrenceTests(unittest.TestCase):
    def test_overlapping_and_alignment(self):
        self.assertEqual(sdk.occurrences(b"aaaaa", b"aaa", 1), [0, 1, 2])
        self.assertEqual(sdk.occurrences(b"aaaaa", b"aaa", 2), [0, 2])
        self.assertEqual(sdk.occurrences(b"abcd", b"xyz"), [])

    def test_reject_invalid_pattern_and_alignment(self):
        for pattern, alignment in [(b"", 2), (b"x", 0), (b"x", -1)]:
            with self.subTest(pattern=pattern, alignment=alignment):
                with self.assertRaises(ValueError):
                    sdk.occurrences(b"x", pattern, alignment)


class ElfTests(unittest.TestCase):
    def test_thumb_symbol_and_arm_symbol(self):
        data = synthetic_elf()
        self.assertEqual(sdk.elf_functions(data), [("test", 0x1000, "thumb", b"abcdefgh")])
        struct.pack_into("<I", data, 0x134, 0x1000)
        self.assertEqual(sdk.elf_functions(data)[0][2], "arm")

    def test_reject_truncation_and_wrong_architecture(self):
        with self.assertRaises(ValueError):
            sdk.elf_functions(synthetic_elf()[:0x138])
        data = synthetic_elf()
        struct.pack_into("<H", data, 18, 3)
        with self.assertRaises(ValueError):
            sdk.elf_functions(data)

    def test_reject_function_outside_section(self):
        data = synthetic_elf()
        struct.pack_into("<I", data, 0x138, 9)
        with self.assertRaises(ValueError):
            sdk.elf_functions(data)

    def test_reject_bad_names_or_non_executable_code(self):
        for offset, value in [(0x130, 100), (0x40 + 40 + 8, 2),
                              (0x40 + 80 + 4, 1)]:
            data = synthetic_elf()
            struct.pack_into("<I", data, offset, value)
            with self.subTest(offset=offset):
                with self.assertRaises(ValueError):
                    sdk.elf_functions(data)

    def test_ignore_unsized_and_undefined_symbols(self):
        for offset, fmt, value in [(0x138, "<I", 0), (0x13e, "<H", 0)]:
            data = synthetic_elf()
            struct.pack_into(fmt, data, offset, value)
            self.assertEqual(sdk.elf_functions(data), [])


class MapTests(unittest.TestCase):
    HEADER = "Load Region SECTIONS (Base: 0x00001000, Size: 0x00000010, Max: 0xffffffff)\n"

    def test_ranges_modes_and_duplicate_rows(self):
        rows = "    sample 0x00001001 Thumb Code 8 test.o\n" * 2
        rows += "    tail 0x00001008 ARM Code 8 test.o\n"
        rows += "    unsized 0x00001000 Thumb Code 0 test.o\n"
        self.assertEqual(sdk.map_functions(b"abcdefghijklmnop", self.HEADER + rows),
                         [("sample", 0x1000, "thumb", b"abcdefgh"),
                          ("tail", 0x1008, "arm", b"ijklmnop")])

    def test_reject_bad_region_missing_rows_and_overflow(self):
        for text in [self.HEADER.replace("0x00000010", "0x00000011"),
                     self.HEADER,
                     self.HEADER + "    outside 0x0000100c ARM Code 8 test.o\n"]:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    sdk.map_functions(b"abcdefghijklmnop", text)


class SourceTests(unittest.TestCase):
    HEADER = ("// synthetic test fixture, not SDK content\n"
              "__INLINE uint16_t co_read16p(void const *p) { return 7; }\n"
              "__INLINE uint32_t co_read32p(void const *p) { return co_read16p(p); }\n")

    def test_extract_preserves_body_and_line(self):
        body, line = probe.extract(self.HEADER, "co_read16p")
        self.assertEqual(line, 2)
        self.assertEqual(body, "__INLINE uint16_t co_read16p(void const *p) { return 7; }")

    def test_reject_missing_duplicate_and_nested_definitions(self):
        for header in ["", self.HEADER * 2,
                       "__INLINE uint16_t co_read16p(void *p) { if (p) { return 7; } }"]:
            with self.subTest(header=header):
                with self.assertRaises(ValueError):
                    probe.extract(header, "co_read16p")

    def test_helper_inline_and_external_name_only(self):
        source, origin = probe.source_for((0xe4fc, 0xe512, None, None, None), self.HEADER)
        self.assertIn("static __attribute__((__always_inline__)) inline uint16_t co_read16p", source)
        self.assertIn("uint32_t fn_0000e4fc(void const *p) { return co_read16p(p); }", source)
        self.assertEqual(origin["function"], "co_read32p")

    def test_clock_hypothesis_unchanged(self):
        row = (0x3bb4, 0x3bbe, "unsigned", "unsigned x", "return x + 7;")
        source, origin = probe.source_for(row, "")
        self.assertEqual(source, "unsigned fn_00003bb4(unsigned x) { return x + 7; }\n")
        self.assertEqual(origin["kind"], "unchanged initial clock hypothesis")


if __name__ == "__main__":
    unittest.main()
