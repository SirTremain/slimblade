#!/usr/bin/env python3
"""Inspect and construct BK3635 application images without accessing hardware."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib


HEADER_SIZE = 16
STACK_HEADER_OFFSET = 0x1F70
APPLICATION_PREFIX_OFFSET = 0x2000
APPLICATION_HEADER_OFFSET = 0x2010
APPLICATION_CODE_OFFSET = 0x2020
OFFICIAL_APPLICATION_END_OFFSET = 0x1F470
APPLICATION_UID = 0x42424242
STACK_UID = 0x53535353
CRC_UNCHECKED = 0xFF
SECTION_UNKNOWN = 0xFF
ROM_VERSION = 1
HEADER_STRUCT = struct.Struct("<IHHIBBH")
OFFICIAL_V449_SIZE = 128_112
OFFICIAL_V449_SHA256 = (
    "e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7"
)
V449_USB_DESCRIPTOR_OFFSET = 0x1E7D1
V449_BCD_DEVICE_OFFSET = V449_USB_DESCRIPTOR_OFFSET + 12
V449_USB_DESCRIPTOR = bytes.fromhex("12010002000000407d04d780490401020001")


def beken_crc32(data: bytes) -> int:
    """Return reflected CRC-32 with initial all-ones and no final XOR."""
    return zlib.crc32(data) ^ 0xFFFFFFFF


@dataclass(frozen=True)
class ImageHeader:
    offset: int
    crc: int
    version: int
    length_words: int
    uid: int
    crc_status: int
    section_status: int
    rom_version: int

    @property
    def end_offset(self) -> int:
        return self.offset + self.length_words * 4

    @property
    def payload_offset(self) -> int:
        return self.offset + HEADER_SIZE

    def calculate_crc(self, image: bytes) -> int:
        if self.end_offset > len(image):
            raise ValueError(
                f"header at {self.offset:#x} ends beyond file at {self.end_offset:#x}"
            )
        return beken_crc32(image[self.payload_offset : self.end_offset])

    def describe(self, image: bytes) -> dict[str, int | str | bool]:
        calculated = self.calculate_crc(image)
        result = asdict(self)
        result.update(
            {
                "offset": f"0x{self.offset:x}",
                "crc": f"{self.crc:08x}",
                "calculated_crc": f"{calculated:08x}",
                "crc_valid": calculated == self.crc,
                "uid": f"{self.uid:08x}",
                "end_offset": f"0x{self.end_offset:x}",
            }
        )
        return result


def parse_header(image: bytes, offset: int) -> ImageHeader:
    if offset < 0 or offset + HEADER_SIZE > len(image):
        raise ValueError(f"no complete image header at {offset:#x}")
    fields = HEADER_STRUCT.unpack_from(image, offset)
    return ImageHeader(offset, *fields)


def inspect_image(path: Path) -> dict[str, object]:
    image = path.read_bytes()
    headers = []
    for offset, expected_uid in (
        (STACK_HEADER_OFFSET, STACK_UID),
        (APPLICATION_HEADER_OFFSET, APPLICATION_UID),
    ):
        if offset + HEADER_SIZE > len(image):
            continue
        header = parse_header(image, offset)
        if header.uid != expected_uid:
            continue
        headers.append(header.describe(image))
    return {"path": str(path), "bytes": len(image), "headers": headers}


def make_application_container(
    code: bytes, version: int = 3, end_offset: int | None = None
) -> bytes:
    """Wrap code linked for 0x2020 in an updater-compatible application image."""
    if not code:
        raise ValueError("application code is empty")
    padded_length = (len(code) + 15) & ~15
    padded_code = code + b"\xff" * (padded_length - len(code))
    natural_end = APPLICATION_CODE_OFFSET + len(padded_code)
    if end_offset is not None:
        if end_offset < natural_end:
            raise ValueError(
                f"requested end {end_offset:#x} is before code end {natural_end:#x}"
            )
        if end_offset % 16:
            raise ValueError("requested application end must be 16-byte aligned")
        padded_code += b"\xff" * (end_offset - natural_end)
    total_region_length = HEADER_SIZE + len(padded_code)
    header = HEADER_STRUCT.pack(
        beken_crc32(padded_code),
        version,
        total_region_length // 4,
        APPLICATION_UID,
        CRC_UNCHECKED,
        SECTION_UNKNOWN,
        ROM_VERSION,
    )
    return b"\xff" * APPLICATION_HEADER_OFFSET + header + padded_code


def refresh_header_crc(image: bytearray, offset: int) -> None:
    header = parse_header(image, offset)
    crc = header.calculate_crc(image)
    struct.pack_into("<I", image, offset, crc)


def make_v449_descriptor_probe(image: bytes) -> bytes:
    """Make a stock-derived v4.50-descriptor probe without changing code flow."""
    digest = hashlib.sha256(image).hexdigest()
    if len(image) != OFFICIAL_V449_SIZE or digest != OFFICIAL_V449_SHA256:
        raise ValueError(
            "input is not the recorded official v4.49 image: "
            f"size={len(image)}, sha256={digest}"
        )
    descriptor = image[
        V449_USB_DESCRIPTOR_OFFSET : V449_USB_DESCRIPTOR_OFFSET
        + len(V449_USB_DESCRIPTOR)
    ]
    if descriptor != V449_USB_DESCRIPTOR:
        raise ValueError("official v4.49 USB descriptor does not match expectation")

    probe = bytearray(image)
    probe[V449_BCD_DEVICE_OFFSET] = 0x50
    refresh_header_crc(probe, APPLICATION_HEADER_OFFSET)
    refresh_header_crc(probe, STACK_HEADER_OFFSET)
    return bytes(probe)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("image", type=Path)
    pack = subparsers.add_parser("pack-application")
    pack.add_argument("code", type=Path, help="raw binary linked for address 0x2020")
    pack.add_argument("output", type=Path)
    pack.add_argument("--version", type=int, default=3)
    pack.add_argument(
        "--end-offset",
        type=lambda value: int(value, 0),
        help="pad the application container to this absolute file/flash offset",
    )
    probe = subparsers.add_parser(
        "make-v449-descriptor-probe",
        help="make a stock-derived, non-flashed bcdDevice 4.50 acceptance probe",
    )
    probe.add_argument("official_image", type=Path)
    probe.add_argument("output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "inspect":
            print(json.dumps(inspect_image(args.image), indent=2, sort_keys=True))
            return 0
        if args.command == "pack-application":
            container = make_application_container(
                args.code.read_bytes(),
                version=args.version,
                end_offset=args.end_offset,
            )
            args.output.write_bytes(container)
            result = inspect_image(args.output)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if args.command == "make-v449-descriptor-probe":
            probe = make_v449_descriptor_probe(args.official_image.read_bytes())
            args.output.write_bytes(probe)
            payload = probe[APPLICATION_PREFIX_OFFSET:]
            result = inspect_image(args.output)
            result.update(
                {
                    "sha256": hashlib.sha256(probe).hexdigest(),
                    "payload_bytes": len(payload),
                    "payload_sha256": hashlib.sha256(payload).hexdigest(),
                    "payload_crc": f"{beken_crc32(payload):08x}",
                    "usb_bcd_device": "4.50",
                }
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
