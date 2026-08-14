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


maker = load_module("make_recovery_guard", TOOLS / "make_recovery_guard.py")
verifier = load_module("verify_recovery_guard", TOOLS / "verify_recovery_guard.py")


class RecoveryGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        build = ROOT / "firmware" / "recovery_guard" / "build"
        cls.paths = {
            "stub": (
                ROOT
                / "firmware"
                / "recovery_stub"
                / "build"
                / "DO_NOT_FLASH-recovery-stub.container.bin"
            ),
            "guard": build / "DO_NOT_FLASH-marker-first-guard-hang-probe.container.bin",
            "code": build / "DO_NOT_FLASH-marker-first-guard-hang-probe.code.bin",
        }
        missing = [str(path) for path in cls.paths.values() if not path.exists()]
        if missing:
            raise unittest.SkipTest("recovery-guard artifacts absent: " + ", ".join(missing))
        cls.data = {name: path.read_bytes() for name, path in cls.paths.items()}

    def verify(self, **changes: bytes) -> dict[str, object]:
        data = self.data | changes
        return verifier.verify_recovery_guard_data(
            data["stub"], data["guard"], data["code"]
        )

    def test_exact_guard_passes(self) -> None:
        report = self.verify()
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["guard_experiment_entry"], "0x21c4")
        self.assertEqual(len(report["changed_offsets"]), 7)

    def test_generator_reproduces_artifacts(self) -> None:
        guard, code = maker.make_recovery_guard(self.data["stub"])
        self.assertEqual(guard, self.data["guard"])
        self.assertEqual(code, self.data["code"])

    def test_wrong_live_stub_is_rejected(self) -> None:
        stub = bytearray(self.data["stub"])
        stub[0] ^= 1
        with self.assertRaisesRegex(ValueError, "live-proven"):
            maker.make_recovery_guard(bytes(stub))

    def test_changed_guard_branch_is_rejected(self) -> None:
        guard = bytearray(self.data["guard"])
        guard[maker.FINAL_ACTION_CALL] ^= 1
        with self.assertRaises(verifier.VerificationError):
            self.verify(guard=bytes(guard))

    def test_changed_experimental_instruction_is_rejected(self) -> None:
        code = bytearray(self.data["code"])
        code[maker.EXPERIMENT_ENTRY - maker.APPLICATION_CODE_OFFSET] ^= 1
        with self.assertRaisesRegex(verifier.VerificationError, "raw guard code"):
            self.verify(code=bytes(code))

    def test_thumb_bl_encoding_targets_experiment(self) -> None:
        self.assertEqual(
            maker.thumb_bl(maker.FINAL_ACTION_CALL, maker.EXPERIMENT_ENTRY),
            bytes.fromhex("00f085f8"),
        )

    def test_storage_isolation_rejects_controller_literal(self) -> None:
        image = b"\x00" * 8 + (0x00803000).to_bytes(4, "little")
        with self.assertRaisesRegex(
            verifier.VerificationError, "persistent-storage"
        ):
            verifier.verify_experiment_storage_isolation(image, 8, 12)

    def test_storage_isolation_rejects_marker_word_address(self) -> None:
        image = b"\x00" * 8 + (0x0000807C).to_bytes(4, "little")
        with self.assertRaisesRegex(
            verifier.VerificationError, "persistent-storage"
        ):
            verifier.verify_experiment_storage_isolation(image, 8, 12)

    def test_storage_isolation_rejects_call_into_guard_prefix(self) -> None:
        start = 0x100
        image = bytearray(b"\x00" * 0x108)
        image[start : start + 4] = maker.thumb_bl(start, 0x80)
        with self.assertRaisesRegex(verifier.VerificationError, "calls outside"):
            verifier.verify_experiment_storage_isolation(image, start, start + 4)

    def test_storage_isolation_accepts_current_self_loop(self) -> None:
        image = b"\x00" * maker.EXPERIMENT_ENTRY + maker.EXPERIMENT_CODE
        report = verifier.verify_experiment_storage_isolation(
            image, maker.EXPERIMENT_ENTRY, maker.GUARD_CODE_END
        )
        self.assertEqual(report["persistent_address_literals"], 0)
        self.assertEqual(report["out_of_range_direct_calls"], 0)


if __name__ == "__main__":
    unittest.main()
