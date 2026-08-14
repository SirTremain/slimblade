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


maker = load_module("make_startup_trampoline", TOOLS / "make_startup_trampoline.py")
verifier = load_module(
    "verify_startup_trampoline", TOOLS / "verify_startup_trampoline.py"
)


class StartupTrampolineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        build = ROOT / "firmware" / "startup_trampoline" / "build"
        cls.paths = {
            "base": (
                ROOT
                / "firmware"
                / "reset_trampoline"
                / "build"
                / "DO_NOT_FLASH-stock-reset-trampoline.container.bin"
            ),
            "image": build / "DO_NOT_FLASH-stock-startup-trampoline.container.bin",
            "code": build / "DO_NOT_FLASH-stock-startup-trampoline.code.bin",
            "elf": build / "DO_NOT_FLASH-stock-startup-trampoline.elf",
            "stub": (
                ROOT
                / "firmware"
                / "recovery_stub"
                / "build"
                / "DO_NOT_FLASH-recovery-stub.container.bin"
            ),
        }
        missing = [str(path) for path in cls.paths.values() if not path.exists()]
        if missing:
            raise unittest.SkipTest("startup artifacts absent: " + ", ".join(missing))
        cls.data = {name: path.read_bytes() for name, path in cls.paths.items()}

    def verify(self, **changes: bytes) -> dict[str, object]:
        data = self.data | changes
        return verifier.verify_startup_trampoline_data(
            data["base"], data["image"], data["code"], data["elf"], data["stub"]
        )

    def test_exact_build_passes(self) -> None:
        report = self.verify()
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["arm_to_thumb"], "0x22cc -> 0x22e9")

    def test_even_thumb_pointer_is_rejected(self) -> None:
        code = bytearray(self.data["code"])
        code[0x30] &= 0xFE
        with self.assertRaises(verifier.VerificationError):
            self.verify(code=bytes(code))

    def test_changed_mode_setup_is_rejected(self) -> None:
        code = bytearray(self.data["code"])
        code[0x08] ^= 1
        with self.assertRaises(verifier.VerificationError):
            self.verify(code=bytes(code))

    def test_changed_base_is_rejected(self) -> None:
        base = bytearray(self.data["base"])
        base[0] ^= 1
        with self.assertRaises(verifier.VerificationError):
            self.verify(base=bytes(base))

    def test_changed_standalone_reference_is_rejected(self) -> None:
        stub = bytearray(self.data["stub"])
        stub[0x2064] ^= 1
        with self.assertRaises(verifier.VerificationError):
            self.verify(stub=bytes(stub))

    def test_oversized_code_is_rejected(self) -> None:
        size = maker.TRAMPOLINE_LIMIT - maker.TRAMPOLINE_ADDRESS + 1
        with self.assertRaisesRegex(ValueError, "overlaps"):
            maker.make_startup_trampoline(self.data["base"], b"\0" * size)


if __name__ == "__main__":
    unittest.main()
