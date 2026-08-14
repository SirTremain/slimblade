import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "firmware_image.py"
SPEC = importlib.util.spec_from_file_location("firmware_image", MODULE_PATH)
assert SPEC and SPEC.loader
firmware_image = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = firmware_image
SPEC.loader.exec_module(firmware_image)


class FirmwareImageTests(unittest.TestCase):
    def test_application_container_round_trip(self) -> None:
        code = bytes(range(37))
        image = firmware_image.make_application_container(code)
        header = firmware_image.parse_header(
            image, firmware_image.APPLICATION_HEADER_OFFSET
        )
        self.assertEqual(header.uid, firmware_image.APPLICATION_UID)
        self.assertEqual(header.end_offset, len(image))
        self.assertEqual(header.calculate_crc(image), header.crc)
        self.assertEqual(
            image[firmware_image.APPLICATION_CODE_OFFSET :][: len(code)], code
        )
        self.assertEqual(len(image) % 16, 0)

    def test_empty_application_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            firmware_image.make_application_container(b"")

    def test_application_can_be_padded_to_official_geometry(self) -> None:
        code = bytes(range(37))
        image = firmware_image.make_application_container(
            code, end_offset=firmware_image.OFFICIAL_APPLICATION_END_OFFSET
        )
        header = firmware_image.parse_header(
            image, firmware_image.APPLICATION_HEADER_OFFSET
        )
        self.assertEqual(len(image), firmware_image.OFFICIAL_V449_SIZE)
        self.assertEqual(
            header.end_offset, firmware_image.OFFICIAL_APPLICATION_END_OFFSET
        )
        self.assertEqual(header.length_words, 0x7518)
        self.assertEqual(header.calculate_crc(image), header.crc)
        self.assertEqual(
            image[firmware_image.APPLICATION_CODE_OFFSET :][: len(code)], code
        )
        self.assertEqual(
            image[
                firmware_image.APPLICATION_CODE_OFFSET + len(code) :
            ],
            b"\xff"
            * (
                firmware_image.OFFICIAL_APPLICATION_END_OFFSET
                - firmware_image.APPLICATION_CODE_OFFSET
                - len(code)
            ),
        )

    def test_official_images_have_valid_known_headers(self) -> None:
        for version in ("448", "449"):
            image_path = Path(f"/tmp/slimblade-v{version}.bin")
            if not image_path.exists():
                self.skipTest("temporary official firmware extractions are absent")
            result = firmware_image.inspect_image(image_path)
            headers = result["headers"]
            self.assertEqual(len(headers), 2)
            self.assertTrue(all(header["crc_valid"] for header in headers))

    def test_v449_descriptor_probe_only_changes_metadata_and_bcd_device(self) -> None:
        image_path = Path("/tmp/slimblade-v449.bin")
        if not image_path.exists():
            self.skipTest("temporary official v4.49 extraction is absent")
        official = image_path.read_bytes()
        probe = firmware_image.make_v449_descriptor_probe(official)
        self.assertEqual(len(probe), len(official))
        self.assertEqual(probe[firmware_image.V449_BCD_DEVICE_OFFSET], 0x50)
        headers = [
            firmware_image.parse_header(probe, offset)
            for offset in (
                firmware_image.STACK_HEADER_OFFSET,
                firmware_image.APPLICATION_HEADER_OFFSET,
            )
        ]
        self.assertTrue(
            all(header.calculate_crc(probe) == header.crc for header in headers)
        )
        allowed = {
            *range(firmware_image.STACK_HEADER_OFFSET, firmware_image.STACK_HEADER_OFFSET + 4),
            *range(
                firmware_image.APPLICATION_HEADER_OFFSET,
                firmware_image.APPLICATION_HEADER_OFFSET + 4,
            ),
            firmware_image.V449_BCD_DEVICE_OFFSET,
        }
        changed = {
            index
            for index, pair in enumerate(zip(official, probe))
            if pair[0] != pair[1]
        }
        self.assertIn(firmware_image.V449_BCD_DEVICE_OFFSET, changed)
        self.assertTrue(changed <= allowed)


if __name__ == "__main__":
    unittest.main()
