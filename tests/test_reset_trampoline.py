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


maker = load_module("make_reset_trampoline", TOOLS / "make_reset_trampoline.py")
verifier = load_module(
    "verify_reset_trampoline", TOOLS / "verify_reset_trampoline.py"
)


class ResetTrampolineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        build = ROOT / "firmware" / "reset_trampoline" / "build"
        cls.base_path = (
            ROOT
            / "firmware"
            / "recovery_carrier"
            / "build"
            / "DO_NOT_FLASH-stock-recovery-carrier.container.bin"
        )
        cls.image_path = build / "DO_NOT_FLASH-stock-reset-trampoline.container.bin"
        cls.code_path = build / "DO_NOT_FLASH-stock-reset-trampoline.code.bin"
        cls.elf_path = build / "DO_NOT_FLASH-stock-reset-trampoline.elf"

    def require_build(self) -> None:
        paths = (self.base_path, self.image_path, self.code_path, self.elf_path)
        if not all(path.exists() for path in paths):
            self.skipTest("reset-trampoline build artifacts are absent")

    def test_arm_branch_encodings(self) -> None:
        self.assertEqual(
            maker.arm_b(0x2064, 0x22B4), bytes.fromhex("920000ea")
        )
        self.assertEqual(
            maker.arm_b(0x22B8, 0x2068), bytes.fromhex("6affffea")
        )

    def test_arm_branch_rejects_unaligned_address(self) -> None:
        with self.assertRaises(ValueError):
            maker.arm_b(0x2065, 0x22B4)

    def test_exact_build_passes(self) -> None:
        self.require_build()
        report = verifier.verify_reset_trampoline_data(
            self.base_path.read_bytes(),
            self.image_path.read_bytes(),
            self.code_path.read_bytes(),
            self.elf_path.read_bytes(),
        )
        self.assertEqual(report["result"], "PASS")

    def test_wrong_base_is_rejected(self) -> None:
        self.require_build()
        base = bytearray(self.base_path.read_bytes())
        base[0] ^= 1
        with self.assertRaisesRegex(ValueError, "exact audited"):
            maker.make_reset_trampoline(bytes(base), self.code_path.read_bytes())

    def test_corrupt_reset_branch_is_rejected(self) -> None:
        self.require_build()
        image = bytearray(self.image_path.read_bytes())
        image[maker.RESET_HANDLER] ^= 1
        with self.assertRaises(verifier.VerificationError):
            verifier.verify_reset_trampoline_data(
                self.base_path.read_bytes(),
                bytes(image),
                self.code_path.read_bytes(),
                self.elf_path.read_bytes(),
            )

    def test_corrupt_return_branch_is_rejected(self) -> None:
        self.require_build()
        code = bytearray(self.code_path.read_bytes())
        code[4] ^= 1
        with self.assertRaises(verifier.VerificationError):
            verifier.verify_reset_trampoline_data(
                self.base_path.read_bytes(),
                self.image_path.read_bytes(),
                bytes(code),
                self.elf_path.read_bytes(),
            )

    def test_oversized_trampoline_is_rejected(self) -> None:
        self.require_build()
        size = maker.TRAMPOLINE_LIMIT - maker.TRAMPOLINE_ADDRESS + 1
        with self.assertRaisesRegex(ValueError, "overlaps"):
            maker.make_reset_trampoline(self.base_path.read_bytes(), b"\0" * size)


if __name__ == "__main__":
    unittest.main()
