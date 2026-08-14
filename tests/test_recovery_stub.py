import importlib.util
from pathlib import Path
import struct
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "verify_recovery_stub.py"
TOOLS = str(ROOT / "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
SPEC = importlib.util.spec_from_file_location("verify_recovery_stub", MODULE_PATH)
assert SPEC and SPEC.loader
verify_recovery_stub = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verify_recovery_stub
SPEC.loader.exec_module(verify_recovery_stub)


class RecoveryStubTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        build = ROOT / "firmware" / "recovery_stub" / "build"
        cls.paths = {
            "stock": Path("/tmp/slimblade-v449.bin"),
            "container": build / "DO_NOT_FLASH-recovery-stub.container.bin",
            "code": build / "DO_NOT_FLASH-recovery-stub.code.bin",
            "elf": build / "DO_NOT_FLASH-recovery-stub.elf",
        }
        missing = [str(path) for path in cls.paths.values() if not path.exists()]
        if missing:
            raise unittest.SkipTest("pre-flight artifacts absent: " + ", ".join(missing))
        cls.data = {name: path.read_bytes() for name, path in cls.paths.items()}

    def verify(self, **changes: bytes) -> dict[str, object]:
        data = self.data | changes
        return verify_recovery_stub.verify_artifacts_data(
            data["stock"], data["container"], data["code"], data["elf"]
        )

    def test_audited_build_passes(self) -> None:
        report = self.verify()
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["b1_blocks"], 3748)

    def test_reversed_unlock_order_is_rejected_even_with_valid_crc(self) -> None:
        code = bytearray(self.data["code"])
        first = 0x2170 - 0x2020
        second = 0x2174 - 0x2020
        code[first : first + 4], code[second : second + 4] = (
            code[second : second + 4],
            code[first : first + 4],
        )
        container = bytearray(self.data["container"])
        container[0x2170:0x2174], container[0x2174:0x2178] = (
            container[0x2174:0x2178],
            container[0x2170:0x2174],
        )
        header = verify_recovery_stub.parse_header(container, 0x2010)
        struct.pack_into("<I", container, 0x2010, header.calculate_crc(container))
        with self.assertRaises(verify_recovery_stub.VerificationError):
            self.verify(code=bytes(code), container=bytes(container))

    def test_changed_container_padding_is_rejected(self) -> None:
        container = bytearray(self.data["container"])
        container[-1] = 0
        with self.assertRaises(verify_recovery_stub.VerificationError):
            self.verify(container=bytes(container))

    def test_changed_header_crc_is_rejected(self) -> None:
        container = bytearray(self.data["container"])
        container[0x2010] ^= 1
        with self.assertRaises(verify_recovery_stub.VerificationError):
            self.verify(container=bytes(container))

    def test_wrong_stock_reference_is_rejected(self) -> None:
        stock = bytearray(self.data["stock"])
        stock[-1] ^= 1
        with self.assertRaises(verify_recovery_stub.VerificationError):
            self.verify(stock=bytes(stock))


if __name__ == "__main__":
    unittest.main()
