import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = str(ROOT / "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)


def load_module(name: str):
    path = ROOT / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


make_recovery_carrier = load_module("make_recovery_carrier")
verify_recovery_carrier = load_module("verify_recovery_carrier")


class RecoveryCarrierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        build = ROOT / "firmware" / "recovery_carrier" / "build"
        cls.paths = {
            "stock": Path("/tmp/slimblade-v449.bin"),
            "carrier": build / "DO_NOT_FLASH-stock-recovery-carrier.container.bin",
            "code": build / "DO_NOT_FLASH-stock-recovery-carrier.code.bin",
            "elf": build / "DO_NOT_FLASH-stock-recovery-carrier.elf",
        }
        missing = [str(path) for path in cls.paths.values() if not path.exists()]
        if missing:
            raise unittest.SkipTest("carrier artifacts absent: " + ", ".join(missing))
        cls.data = {name: path.read_bytes() for name, path in cls.paths.items()}

    def verify(self, **changes: bytes) -> dict[str, object]:
        data = self.data | changes
        return verify_recovery_carrier.verify_carrier_data(
            data["stock"], data["carrier"], data["code"], data["elf"]
        )

    def test_audited_carrier_passes(self) -> None:
        report = self.verify()
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["b1_blocks"], 3748)
        self.assertEqual(report["unused_gap_bytes"], 76)

    def test_generator_reproduces_build(self) -> None:
        generated = make_recovery_carrier.make_recovery_carrier(
            self.data["stock"], self.data["code"]
        )
        self.assertEqual(generated, self.data["carrier"])

    def test_thumb_bl_encoder_reproduces_stock_call(self) -> None:
        encoded = make_recovery_carrier.thumb_bl(0x18FBA, 0x1895C)
        self.assertEqual(encoded, self.data["stock"][0x18FBA:0x18FBE])

    def test_wrong_stock_is_rejected(self) -> None:
        stock = bytearray(self.data["stock"])
        stock[-1] ^= 1
        with self.assertRaises(ValueError):
            make_recovery_carrier.make_recovery_carrier(bytes(stock), self.data["code"])

    def test_oversized_injection_is_rejected(self) -> None:
        code = b"\0" * (
            make_recovery_carrier.CARRIER_LIMIT
            - make_recovery_carrier.CARRIER_ADDRESS
            + 1
        )
        with self.assertRaises(ValueError):
            make_recovery_carrier.make_recovery_carrier(self.data["stock"], code)

    def test_changed_stock_fallback_pointer_is_rejected(self) -> None:
        carrier = bytearray(self.data["carrier"])
        carrier[0x2278] ^= 1
        with self.assertRaises(verify_recovery_carrier.VerificationError):
            self.verify(carrier=bytes(carrier))

    def test_reversed_unlock_order_is_rejected(self) -> None:
        carrier = bytearray(self.data["carrier"])
        carrier[0x22AC:0x22B0], carrier[0x22B0:0x22B4] = (
            carrier[0x22B0:0x22B4],
            carrier[0x22AC:0x22B0],
        )
        with self.assertRaises(verify_recovery_carrier.VerificationError):
            self.verify(carrier=bytes(carrier))


if __name__ == "__main__":
    unittest.main()
