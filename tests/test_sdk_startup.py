import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verifier = load_module("verify_sdk_startup", TOOLS / "verify_sdk_startup.py")


class SdkStartupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        build = (
            ROOT
            / "vendor"
            / "bk3633_sdk"
            / "SDK"
            / "projects"
            / "slimblade_wired"
            / "build"
        )
        cls.paths = {
            "stock": Path("/tmp/slimblade-v449.bin"),
            "code": build / "stock-startup-reference.bin",
            "wrappers": build / "stock-startup-reference.interrupt-wrappers.bin",
            "elf": build / "stock-startup-reference.elf",
        }
        missing = [str(path) for path in cls.paths.values() if not path.exists()]
        if missing:
            raise unittest.SkipTest("SDK startup artifacts absent: " + ", ".join(missing))
        cls.data = {name: path.read_bytes() for name, path in cls.paths.items()}

    def verify(self, **changes: bytes) -> dict[str, object]:
        data = self.data | changes
        return verifier.verify_sdk_startup_data(
            data["stock"], data["code"], data["wrappers"], data["elf"]
        )

    def test_exact_source_build_passes(self) -> None:
        report = self.verify()
        self.assertEqual(report["result"], "PASS")
        self.assertTrue(report["byte_exact"])
        self.assertEqual(report["reset_calls"]["zero_bss"], "0x2140")
        self.assertEqual(report["interrupt_dispatch"]["irq_thumb_dispatch"], "0x3e78")

    def test_single_instruction_byte_change_is_rejected(self) -> None:
        code = bytearray(self.data["code"])
        code[0x7C] ^= 1
        with self.assertRaisesRegex(verifier.VerificationError, "at 0x209c"):
            self.verify(code=bytes(code))

    def test_wrong_stock_reference_is_rejected(self) -> None:
        stock = bytearray(self.data["stock"])
        stock[0x100] ^= 1
        with self.assertRaisesRegex(verifier.VerificationError, "official v4.49"):
            self.verify(stock=bytes(stock))

    def test_single_wrapper_byte_change_is_rejected(self) -> None:
        wrappers = bytearray(self.data["wrappers"])
        wrappers[4] ^= 1
        with self.assertRaisesRegex(verifier.VerificationError, "differ from stock"):
            self.verify(wrappers=bytes(wrappers))

    def test_elf_entry_change_is_rejected(self) -> None:
        elf = bytearray(self.data["elf"])
        elf[24:28] = (0x2064).to_bytes(4, "little")
        with self.assertRaisesRegex(verifier.VerificationError, "ELF entry"):
            self.verify(elf=bytes(elf))


if __name__ == "__main__":
    unittest.main()
