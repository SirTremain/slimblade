"""Offline synthetic controls for the exact-range pilot feedback tool."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("stock_compare", ROOT / "tools/stock_compare.py")
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)


class ByteTests(unittest.TestCase):
    def test_exact(self):
        self.assertEqual(sc.compare(b"abc", b"abc", 0x1000)["result"], "exact-range-bytes")

    def test_size_and_byte_mismatch(self):
        for data in (b"ab", b"abcd", b"axc"):
            self.assertEqual(sc.compare(b"abc", data, 0x1000)["result"], "mismatch")

    def test_malformed_elf(self):
        with self.assertRaises(sc.Rejected):
            sc.runtime_bytes(b"not elf", 0x1000)


@unittest.skipUnless(shutil.which("clang") and shutil.which("ld.lld"), "requires local LLVM")
class CompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = sc.tool_lock()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pilot-test-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.task = {"id": "fn_00001000", "entry": "0x00001000"}

    def build(self, body, entry=None):
        task = self.task if entry is None else {"id": f"fn_{entry:08x}", "entry": hex(entry)}
        out = self.directory / str(len(list(self.directory.iterdir())))
        out.mkdir()
        source = body.replace("PROBE", task["id"])
        elf, _ = sc.compile_leaf(source, out, self.lock, task["id"], sc.layout(task))
        return sc.runtime_bytes(elf, int(task["entry"], 16))

    def test_repeatable_build(self):
        source = "unsigned int PROBE(unsigned int a) { return a + 17u; }"
        self.assertEqual(self.build(source), self.build(source))

    def test_two_byte_aligned_entry(self):
        self.assertTrue(self.build("unsigned int PROBE(unsigned int a) { return a + 17u; }", 0x1002))

    def test_changed_constant(self):
        a = self.build("unsigned int PROBE(unsigned int a) { return a + 17u; }")
        b = self.build("unsigned int PROBE(unsigned int a) { return a + 18u; }")
        self.assertNotEqual(a, b)

    def test_signed_load(self):
        a = self.build("int PROBE(const signed char *p) { return *p; }")
        b = self.build("int PROBE(const unsigned char *p) { return *p; }")
        self.assertNotEqual(a, b)

    def test_removed_store(self):
        a = self.build("void PROBE(volatile unsigned int *p) { *p = 7u; }")
        b = self.build("void PROBE(volatile unsigned int *p) { (void)p; }")
        self.assertNotEqual(a, b)

    def test_literal_pool_compared(self):
        a = self.build("unsigned int PROBE(unsigned int a) { return a ^ 0x12345678u; }")
        b = self.build("unsigned int PROBE(unsigned int a) { return a ^ 0x12345679u; }")
        self.assertIn(bytes.fromhex("78563412"), a)
        self.assertNotEqual(a, b)

    def test_policy_rejections(self):
        sources = [
            'void PROBE(void) { __asm__("nop"); }',
            "unsigned int PROBE(void) { return *(unsigned int *)0x800000u; }",
            "unsigned int PROBE(void) { static unsigned int x; return ++x; }",
            "unsigned int x; unsigned int PROBE(void) { return x; }",
            "extern unsigned int other(void); unsigned int PROBE(void) { return other(); }",
            "void wrong_name(void) {}",
            "unsigned int PROBE(void) { return ((unsigned int (*)(void))0x1001u)(); }",
            "#define X 1\nunsigned int PROBE(void) { return X; }",
        ]
        for source in sources:
            with self.subTest(source=source), self.assertRaises(sc.Rejected):
                self.build(source)

    def test_complete_locked_roundtrip_and_tamper(self):
        source = self.directory / "probe.c"
        source.write_text("unsigned int fn_00001000(unsigned int a) { return a + 17u; }")
        expected = self.build(source.read_text())
        baseline = self.directory / "fixture.bin"
        baseline.write_bytes(b"\xff" * 0x1000 + expected)
        # Synthetic oracle is explicitly constructed here, never from stock.
        lock = {**self.lock, "scope": sc.SCOPE, "baseline": sc.base.pin(baseline),
                "baseline_bytes": baseline.stat().st_size,
                "tasks": {self.task["id"]: {**self.task, "end_exclusive": hex(0x1000+len(expected)),
                          "expected_sha256": sc.base.sha(expected), "layout": sc.layout(self.task)}}}
        path = self.directory / "lock.json"
        path.write_bytes(sc.encode(lock))
        sha = sc.base.sha(path.read_bytes())
        result = sc.verify(path, sha, self.task["id"], source, self.directory / "valid")
        self.assertEqual(result["result"], "exact-range-bytes")
        self.assertFalse(result["certified_match"])
        source.write_text(source.read_text().replace("17u", "18u"))
        result = sc.verify(path, sha, self.task["id"], source, self.directory / "wrong")
        self.assertEqual(result["result"], "mismatch")
        for field in ("verifier_sha256", "prototype_sha256"):
            changed = {**lock, field: "0"*64}
            path.write_bytes(sc.encode(changed))
            with self.assertRaises(sc.Rejected):
                sc.load_lock(path, sc.base.sha(path.read_bytes()))
        path.write_bytes(sc.encode(lock))
        baseline.write_bytes(baseline.read_bytes()[:-1] + b"\x00")
        with self.assertRaises(sc.Rejected):
            sc.load_lock(path, sha)

    def test_pins_flags_and_scope_fail_closed(self):
        baseline = self.directory / "baseline.bin"
        baseline.write_bytes(b"synthetic")
        lock = {**self.lock, "scope": sc.SCOPE, "baseline": sc.base.pin(baseline),
                "baseline_bytes": 9, "tasks": {}}
        variants = []
        variants.append({**lock, "scope": "unknown"})
        variants.append({**lock, "compile_flags": ["-O0"]})
        variants.append({**lock, "link_flags": []})
        variants.append({**lock, "compiler": {**lock["compiler"], "sha256": "0"*64}})
        variants.append({**lock, "python_version": "changed"})
        for changed in variants:
            path = self.directory / "tampered.json"
            path.write_bytes(sc.encode(changed))
            with self.subTest(changed=changed.keys()), self.assertRaises(sc.Rejected):
                sc.load_lock(path, sc.base.sha(path.read_bytes()))
        with self.assertRaises(sc.Rejected):
            sc.load_lock(path, "0"*64)

    def test_prebuilt_and_symlink_candidates_rejected(self):
        baseline = self.directory / "baseline.bin"
        baseline.write_bytes(b"synthetic")
        lock = {**self.lock, "scope": sc.SCOPE, "baseline": sc.base.pin(baseline),
                "baseline_bytes": 9,
                "tasks": {self.task["id"]: {"entry": "0x0", "end_exclusive": "0x9",
                          "expected_sha256": sc.base.sha(b"synthetic"), "layout": sc.layout(self.task)}}}
        path = self.directory / "lock.json"
        path.write_bytes(sc.encode(lock))
        sha = sc.base.sha(path.read_bytes())
        candidate = self.directory / "candidate.elf"
        candidate.write_bytes(b"not accepted")
        link = self.directory / "candidate.c"
        link.symlink_to(candidate)
        for source in (candidate, link):
            with self.assertRaises(sc.Rejected):
                sc.verify(path, sha, self.task["id"], source, self.directory / "output")
        good = self.directory / "good.c"
        good.write_text("unsigned int fn_00001000(void) { return 0u; }")
        output = self.directory / "output"
        output.mkdir()
        marker = output / "candidate.elf"
        marker.write_bytes(b"preserve existing output")
        with self.assertRaises(sc.Rejected):
            sc.verify(path, sha, self.task["id"], good, output)
        self.assertEqual(marker.read_bytes(), b"preserve existing output")


if __name__ == "__main__":
    unittest.main()
