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
            "carrier": (
                ROOT
                / "firmware"
                / "recovery_carrier"
                / "build"
                / "DO_NOT_FLASH-stock-recovery-carrier.container.bin"
            ),
            "startup_trampoline": (
                ROOT
                / "firmware"
                / "startup_trampoline"
                / "build"
                / "DO_NOT_FLASH-stock-startup-trampoline.container.bin"
            ),
        }
        missing = [str(path) for path in cls.paths.values() if not path.exists()]
        if missing:
            raise unittest.SkipTest("pre-flight artifacts absent: " + ", ".join(missing))
        cls.data = {name: path.read_bytes() for name, path in cls.paths.items()}

    def verify(self, **changes: bytes) -> dict[str, object]:
        data = self.data | changes
        return verify_recovery_stub.verify_artifacts_data(
            data["stock"],
            data["container"],
            data["code"],
            data["elf"],
            data["carrier"],
            data["startup_trampoline"],
        )

    def test_audited_build_passes(self) -> None:
        report = self.verify()
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["b1_blocks"], 3748)
        self.assertEqual(
            report["comparisons"]["startup_matches_live_trampoline"]["stack"],
            "0x00407f00",
        )

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

    def test_wrong_live_carrier_reference_is_rejected(self) -> None:
        carrier = bytearray(self.data["carrier"])
        carrier[0x224C] ^= 1
        with self.assertRaises(verify_recovery_stub.VerificationError):
            self.verify(carrier=bytes(carrier))

    def test_wrong_live_startup_reference_is_rejected(self) -> None:
        startup = bytearray(self.data["startup_trampoline"])
        startup[0x22BC] ^= 1
        with self.assertRaisesRegex(
            verify_recovery_stub.VerificationError, "live-tested v4.53"
        ):
            self.verify(startup_trampoline=bytes(startup))

    def test_changed_standalone_stack_load_is_rejected(self) -> None:
        stub = bytearray(self.data["container"])
        code = bytearray(self.data["code"])
        struct.pack_into("<I", stub, 0x206C, 0xE59FD008)
        struct.pack_into("<I", code, 0x206C - 0x2020, 0xE59FD008)
        header = verify_recovery_stub.parse_header(stub, 0x2010)
        struct.pack_into("<I", stub, 0x2010, header.calculate_crc(stub))
        with self.assertRaisesRegex(
            verify_recovery_stub.VerificationError, "minimal reset sequence"
        ):
            self.verify(container=bytes(stub), code=bytes(code))

    def test_changed_standalone_call_target_is_rejected(self) -> None:
        stub = bytearray(self.data["container"])
        code = bytearray(self.data["code"])
        stub[0x2098] ^= 1
        code[0x2098 - 0x2020] ^= 1
        header = verify_recovery_stub.parse_header(stub, 0x2010)
        struct.pack_into("<I", stub, 0x2010, header.calculate_crc(stub))
        with self.assertRaisesRegex(
            verify_recovery_stub.VerificationError, "call graph"
        ):
            self.verify(container=bytes(stub), code=bytes(code))


if __name__ == "__main__":
    unittest.main()
