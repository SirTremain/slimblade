import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "slimblade_usb.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("slimblade_usb", MODULE_PATH)
assert SPEC and SPEC.loader
slimblade_usb = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(slimblade_usb)


class PacketTests(unittest.TestCase):
    def test_normal_reset_packet(self) -> None:
        packet = slimblade_usb.normal_reset_packet()
        self.assertEqual(len(packet), 17)
        self.assertEqual(packet.hex(), "080d000000000000000000000000000040")
        self.assertEqual(sum(packet) & 0xFF, 0x55)

    def test_carrier_command_packets(self) -> None:
        expected = {
            0x0E: "080e00000000000000000000000000003f",
            0x0F: "080f00000000000000000000000000003e",
            0x10: "081000000000000000000000000000003d",
        }
        for command, encoded in expected.items():
            with self.subTest(command=command):
                packet = slimblade_usb.normal_command_packet(command)
                self.assertEqual(packet.hex(), encoded)
                self.assertEqual(sum(packet) & 0xFF, 0x55)

    def test_normal_command_rejects_out_of_range_byte(self) -> None:
        for command in (-1, 0x100):
            with self.subTest(command=command):
                with self.assertRaises(ValueError):
                    slimblade_usb.normal_command_packet(command)

    def test_boot_reset_packet(self) -> None:
        packet = slimblade_usb.boot_reset_packet()
        self.assertEqual(len(packet), 49)
        self.assertEqual(packet[:2], b"\x06\x0d")
        self.assertEqual(packet[-1], 0x42)
        self.assertEqual(sum(packet) & 0xFF, 0x55)

    def test_boot_query_packet(self) -> None:
        packet = slimblade_usb.boot_query_packet()
        self.assertEqual(len(packet), 49)
        self.assertEqual(packet[:2], b"\x06\xb2")
        self.assertEqual(packet[-1], 0x9D)
        self.assertEqual(sum(packet) & 0xFF, 0x55)

    def test_known_boot_identities(self) -> None:
        self.assertIn((0x25A7, 0xFABE), slimblade_usb.BOOT_IDENTITIES)
        self.assertIn((0x3554, 0xF600), slimblade_usb.BOOT_IDENTITIES)
        self.assertIn((0x3554, 0xF800), slimblade_usb.BOOT_IDENTITIES)

    def test_prepare_packet_matches_updater_layout(self) -> None:
        payload = bytes(range(255)) + b"\xff"
        packet = slimblade_usb.prepare_download_packet(payload)
        self.assertEqual(len(packet), 49)
        self.assertEqual(packet[:2], b"\x06\xb0")
        self.assertEqual(packet[5:9], b"\x00\x00\x01\x00")
        self.assertEqual(
            int.from_bytes(packet[9:13], "big"),
            slimblade_usb.updater_crc32(payload),
        )

    def test_nonfinal_download_packet_matches_updater_layout(self) -> None:
        payload = bytes(range(64))
        packet = slimblade_usb.download_packet(payload, 0)
        self.assertEqual(len(packet), 49)
        self.assertEqual(packet[:4], b"\x06\xb1\xc0\x20")
        self.assertEqual(packet[5:9], b"\x00\x00\x20\x00")
        self.assertEqual(packet[17:49], payload[:32])

    def test_short_final_download_packet_is_ff_padded(self) -> None:
        payload = bytes(range(35))
        packet = slimblade_usb.download_packet(payload, 32)
        self.assertEqual(packet[:4], b"\x06\xb1\xc1\x03")
        self.assertEqual(packet[5:9], b"\x00\x00\x20\x20")
        self.assertEqual(packet[17:20], payload[32:])
        self.assertEqual(packet[20:49], b"\xff" * 29)

    def test_official_payload_constants(self) -> None:
        image = Path("/tmp/slimblade-v449.bin")
        if not image.exists():
            self.skipTest("temporary official firmware extraction is absent")
        payload = slimblade_usb.load_official_v449(image)
        self.assertEqual(len(payload), slimblade_usb.OFFICIAL_V449_PAYLOAD_SIZE)
        self.assertEqual(
            slimblade_usb.updater_crc32(payload),
            slimblade_usb.OFFICIAL_V449_PAYLOAD_CRC,
        )

    def test_descriptor_probe_payload_constants(self) -> None:
        image = Path("/tmp/slimblade-v449-probe-bcd450.bin")
        if not image.exists():
            self.skipTest("temporary v4.50 descriptor probe is absent")
        payload = slimblade_usb.load_v449_descriptor_probe(image)
        self.assertEqual(len(payload), slimblade_usb.V449_PROBE_PAYLOAD_SIZE)
        self.assertEqual(
            slimblade_usb.updater_crc32(payload),
            slimblade_usb.V449_PROBE_PAYLOAD_CRC,
        )

    def test_recovery_carrier_payload_constants(self) -> None:
        image = (
            MODULE_PATH.parents[1]
            / "firmware"
            / "recovery_carrier"
            / "build"
            / "DO_NOT_FLASH-stock-recovery-carrier.container.bin"
        )
        if not image.exists():
            self.skipTest("recovery carrier has not been built")
        payload = slimblade_usb.load_recovery_carrier(image)
        self.assertEqual(len(payload), slimblade_usb.RECOVERY_CARRIER_PAYLOAD_SIZE)
        self.assertEqual(
            slimblade_usb.updater_crc32(payload),
            slimblade_usb.RECOVERY_CARRIER_PAYLOAD_CRC,
        )

    def test_recovery_carrier_rejects_one_byte_corruption(self) -> None:
        image = (
            MODULE_PATH.parents[1]
            / "firmware"
            / "recovery_carrier"
            / "build"
            / "DO_NOT_FLASH-stock-recovery-carrier.container.bin"
        )
        if not image.exists():
            self.skipTest("recovery carrier has not been built")
        corrupted = bytearray(image.read_bytes())
        corrupted[0x21AC] ^= 1
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corrupted.bin"
            path.write_bytes(corrupted)
            with self.assertRaisesRegex(ValueError, "not the recorded"):
                slimblade_usb.load_recovery_carrier(path)

    def test_reset_trampoline_payload_constants(self) -> None:
        image = (
            MODULE_PATH.parents[1]
            / "firmware"
            / "reset_trampoline"
            / "build"
            / "DO_NOT_FLASH-stock-reset-trampoline.container.bin"
        )
        if not image.exists():
            self.skipTest("reset trampoline has not been built")
        payload = slimblade_usb.load_reset_trampoline(image)
        self.assertEqual(len(payload), slimblade_usb.RESET_TRAMPOLINE_PAYLOAD_SIZE)
        self.assertEqual(
            slimblade_usb.updater_crc32(payload),
            slimblade_usb.RESET_TRAMPOLINE_PAYLOAD_CRC,
        )

    def test_reset_trampoline_rejects_one_byte_corruption(self) -> None:
        image = (
            MODULE_PATH.parents[1]
            / "firmware"
            / "reset_trampoline"
            / "build"
            / "DO_NOT_FLASH-stock-reset-trampoline.container.bin"
        )
        if not image.exists():
            self.skipTest("reset trampoline has not been built")
        corrupted = bytearray(image.read_bytes())
        corrupted[0x2064] ^= 1
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corrupted.bin"
            path.write_bytes(corrupted)
            with self.assertRaisesRegex(ValueError, "not the recorded"):
                slimblade_usb.load_reset_trampoline(path)

    def test_recovery_stub_payload_constants(self) -> None:
        image = (
            MODULE_PATH.parents[1]
            / "firmware"
            / "recovery_stub"
            / "build"
            / "DO_NOT_FLASH-recovery-stub.container.bin"
        )
        if not image.exists():
            self.skipTest("recovery stub has not been built")
        payload = slimblade_usb.load_recovery_stub(image)
        self.assertEqual(len(payload), slimblade_usb.RECOVERY_STUB_PAYLOAD_SIZE)
        self.assertEqual(
            slimblade_usb.updater_crc32(payload),
            slimblade_usb.RECOVERY_STUB_PAYLOAD_CRC,
        )

    def test_recovery_stub_rejects_one_byte_corruption(self) -> None:
        image = (
            MODULE_PATH.parents[1]
            / "firmware"
            / "recovery_stub"
            / "build"
            / "DO_NOT_FLASH-recovery-stub.container.bin"
        )
        if not image.exists():
            self.skipTest("recovery stub has not been built")
        corrupted = bytearray(image.read_bytes())
        corrupted[0x2064] ^= 1
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corrupted.bin"
            path.write_bytes(corrupted)
            with self.assertRaisesRegex(ValueError, "not the recorded"):
                slimblade_usb.load_recovery_stub(path)

    def test_startup_trampoline_payload_constants(self) -> None:
        image = (
            MODULE_PATH.parents[1]
            / "firmware"
            / "startup_trampoline"
            / "build"
            / "DO_NOT_FLASH-stock-startup-trampoline.container.bin"
        )
        if not image.exists():
            self.skipTest("startup trampoline has not been built")
        payload = slimblade_usb.load_startup_trampoline(image)
        self.assertEqual(len(payload), slimblade_usb.STARTUP_TRAMPOLINE_PAYLOAD_SIZE)
        self.assertEqual(
            slimblade_usb.updater_crc32(payload),
            slimblade_usb.STARTUP_TRAMPOLINE_PAYLOAD_CRC,
        )

    def test_startup_trampoline_rejects_one_byte_corruption(self) -> None:
        image = (
            MODULE_PATH.parents[1]
            / "firmware"
            / "startup_trampoline"
            / "build"
            / "DO_NOT_FLASH-stock-startup-trampoline.container.bin"
        )
        if not image.exists():
            self.skipTest("startup trampoline has not been built")
        corrupted = bytearray(image.read_bytes())
        corrupted[0x22E4] ^= 1
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corrupted.bin"
            path.write_bytes(corrupted)
            with self.assertRaisesRegex(ValueError, "not the recorded"):
                slimblade_usb.load_startup_trampoline(path)


class CarrierGuardTests(unittest.TestCase):
    def test_read_probe_accepts_only_valid_checksummed_command_reply(self) -> None:
        packet = slimblade_usb.normal_command_packet(0x0E)
        read_fd, write_fd = os.pipe()
        selector = slimblade_usb.selectors.DefaultSelector()
        try:
            selector.register(read_fd, slimblade_usb.selectors.EVENT_READ)
            os.write(write_fd, packet)
            self.assertEqual(
                slimblade_usb.read_normal_command_response(
                    read_fd, selector, 0x0E, 0.1
                ),
                packet,
            )
        finally:
            selector.close()
            os.close(read_fd)
            os.close(write_fd)

    def test_read_probe_rejects_bad_checksum(self) -> None:
        packet = bytearray(slimblade_usb.normal_command_packet(0x0E))
        packet[-1] ^= 1
        read_fd, write_fd = os.pipe()
        selector = slimblade_usb.selectors.DefaultSelector()
        try:
            selector.register(read_fd, slimblade_usb.selectors.EVENT_READ)
            os.write(write_fd, packet)
            self.assertIsNone(
                slimblade_usb.read_normal_command_response(
                    read_fd, selector, 0x0E, 0.01
                )
            )
        finally:
            selector.close()
            os.close(read_fd)
            os.close(write_fd)

    def test_carrier_identity_requires_bcd_451(self) -> None:
        hid = {"identity": {"vendor": 0x047D, "product": 0x80D7}}
        usb = {
            "sysfs": "/sys/devices/fake",
            "vendor": 0x047D,
            "product": 0x80D7,
            "bcd_device": "0450",
        }
        with mock.patch.object(slimblade_usb, "identity_dict", return_value=hid):
            with mock.patch.object(
                slimblade_usb, "usb_identity_for_hidraw", return_value=usb
            ):
                with self.assertRaisesRegex(ValueError, "expected recovery carrier"):
                    slimblade_usb.require_recovery_carrier(Path("/dev/hidraw4"))

    def test_carrier_identity_accepts_bcd_451(self) -> None:
        hid = {"identity": {"vendor": 0x047D, "product": 0x80D7}}
        usb = {
            "sysfs": "/sys/devices/fake",
            "vendor": 0x047D,
            "product": 0x80D7,
            "bcd_device": "0451",
        }
        with mock.patch.object(slimblade_usb, "identity_dict", return_value=hid):
            with mock.patch.object(
                slimblade_usb, "usb_identity_for_hidraw", return_value=usb
            ):
                self.assertIs(
                    slimblade_usb.require_recovery_carrier(Path("/dev/hidraw4")), usb
                )

    def test_carrier_flash_needs_exact_hash_confirmation(self) -> None:
        argv = [
            "slimblade_usb.py",
            "flash-recovery-carrier",
            "--firmware",
            "carrier.bin",
            "--confirm-sha256",
            "wrong",
        ]
        with mock.patch.object(sys, "argv", argv):
            with mock.patch.object(slimblade_usb, "flash_recovery_carrier") as flash:
                with mock.patch("sys.stderr", new=io.StringIO()):
                    self.assertEqual(slimblade_usb.main(), 2)
                flash.assert_not_called()

    def test_reset_trampoline_needs_exact_hash_confirmation(self) -> None:
        argv = [
            "slimblade_usb.py",
            "flash-reset-trampoline",
            "--firmware",
            "trampoline.bin",
            "--confirm-sha256",
            "wrong",
        ]
        with mock.patch.object(sys, "argv", argv):
            with mock.patch.object(slimblade_usb, "flash_reset_trampoline") as flash:
                with mock.patch("sys.stderr", new=io.StringIO()):
                    self.assertEqual(slimblade_usb.main(), 2)
                flash.assert_not_called()

    def test_recovery_stub_needs_exact_hash_confirmation(self) -> None:
        argv = [
            "slimblade_usb.py",
            "flash-recovery-stub",
            "--firmware",
            "stub.bin",
            "--confirm-sha256",
            "wrong",
        ]
        with mock.patch.object(sys, "argv", argv):
            with mock.patch.object(slimblade_usb, "flash_recovery_stub") as flash:
                with mock.patch("sys.stderr", new=io.StringIO()):
                    self.assertEqual(slimblade_usb.main(), 2)
                flash.assert_not_called()

    def test_startup_trampoline_needs_exact_hash_confirmation(self) -> None:
        argv = [
            "slimblade_usb.py",
            "flash-startup-trampoline",
            "--firmware",
            "startup.bin",
            "--confirm-sha256",
            "wrong",
        ]
        with mock.patch.object(sys, "argv", argv):
            with mock.patch.object(slimblade_usb, "flash_startup_trampoline") as flash:
                with mock.patch("sys.stderr", new=io.StringIO()):
                    self.assertEqual(slimblade_usb.main(), 2)
                flash.assert_not_called()

    def test_full_recovery_needs_exact_action_confirmation(self) -> None:
        argv = [
            "slimblade_usb.py",
            "carrier-full-recovery",
            "--confirm-action",
            "wrong",
        ]
        with mock.patch.object(sys, "argv", argv):
            with mock.patch.object(slimblade_usb, "carrier_full_recovery") as action:
                with mock.patch("sys.stderr", new=io.StringIO()):
                    self.assertEqual(slimblade_usb.main(), 2)
                action.assert_not_called()


class LoaderReopenTests(unittest.TestCase):
    def test_stub_result_requires_changed_loader_device_number(self) -> None:
        previous = {
            "sysfs": "/sys/devices/fake",
            "vendor": 0x25A7,
            "product": 0xFABE,
            "devnum": "30",
        }
        old = dict(previous)
        new = dict(previous, devnum="31")
        with mock.patch.object(
            slimblade_usb, "sysfs_usb_identities", side_effect=[[old], [new]]
        ):
            with mock.patch.object(slimblade_usb.time, "sleep"):
                result = slimblade_usb.wait_for_boot_reenumeration(previous, 1.0)
        self.assertEqual(result, new)

    def test_pre_erase_wait_retries_disappearing_loader(self) -> None:
        candidate = Path("/dev/hidraw3")
        selector = mock.Mock()
        session = (
            candidate,
            (0x25A7, 0xFABE),
            {"sysfs": "/sys/devices/fake"},
            12,
            selector,
        )
        with mock.patch.object(
            slimblade_usb, "loader_candidate_paths", return_value=[candidate]
        ):
            with mock.patch.object(
                slimblade_usb,
                "open_queried_loader_candidate",
                side_effect=[FileNotFoundError(candidate), session],
            ) as probe:
                with mock.patch.object(slimblade_usb.time, "sleep"):
                    result = slimblade_usb.wait_for_queried_loader(candidate, 1.0)
        self.assertIs(result, session)
        self.assertEqual(probe.call_count, 2)

    def test_unexpected_loader_protocol_is_not_retried(self) -> None:
        candidate = Path("/dev/hidraw3")
        with mock.patch.object(
            slimblade_usb, "loader_candidate_paths", return_value=[candidate]
        ):
            with mock.patch.object(
                slimblade_usb,
                "open_queried_loader_candidate",
                side_effect=ValueError("unexpected B2 device type"),
            ) as probe:
                with self.assertRaisesRegex(ValueError, "unexpected B2"):
                    slimblade_usb.wait_for_queried_loader(candidate, 1.0)
        probe.assert_called_once()

    def test_no_erase_when_loader_never_opens(self) -> None:
        with mock.patch.object(
            slimblade_usb,
            "wait_for_queried_loader",
            side_effect=RuntimeError("loader absent"),
        ):
            with mock.patch.object(slimblade_usb, "write_report") as write:
                with mock.patch("sys.stderr", new=io.StringIO()):
                    result = slimblade_usb.flash_application_payload(
                        Path("/dev/slimblade-loader"),
                        b"\0" * 32,
                        0.1,
                        "hash",
                        "test flash",
                        "0000",
                    )
        self.assertEqual(result, 3)
        write.assert_not_called()

    def test_b0_failure_is_not_automatically_retried(self) -> None:
        selector = mock.Mock()
        session = (
            Path("/dev/hidraw3"),
            (0x25A7, 0xFABE),
            {"sysfs": "/sys/devices/fake"},
            12,
            selector,
        )
        with mock.patch.object(
            slimblade_usb, "wait_for_queried_loader", return_value=session
        ) as wait:
            with mock.patch.object(
                slimblade_usb, "write_report", side_effect=OSError("B0 failed")
            ) as write:
                with mock.patch.object(slimblade_usb.os, "close"):
                    with mock.patch("sys.stderr", new=io.StringIO()):
                        with mock.patch("sys.stdout", new=io.StringIO()):
                            result = slimblade_usb.flash_application_payload(
                                Path("/dev/slimblade-loader"),
                                b"\0" * 32,
                                0.1,
                                "hash",
                                "test flash",
                                "0000",
                            )
        self.assertEqual(result, 3)
        wait.assert_called_once()
        write.assert_called_once()
        selector.close.assert_called_once()


class UdevRuleTests(unittest.TestCase):
    def test_stable_symlinks_are_scoped_to_correct_interfaces(self) -> None:
        rules = (
            MODULE_PATH.parents[1] / "udev" / "70-slimblade-research.rules"
        ).read_text()
        self.assertIn('ENV{ID_USB_INTERFACE_NUM}=="01"', rules)
        self.assertIn('SYMLINK+="slimblade-vendor"', rules)
        self.assertEqual(rules.count('SYMLINK+="slimblade-loader"'), 3)


if __name__ == "__main__":
    unittest.main()
