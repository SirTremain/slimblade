#!/usr/bin/env python3
"""Offline, hash-locked checks for the stock reset-trampoline image."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

from firmware_image import (
    APPLICATION_HEADER_OFFSET,
    APPLICATION_PREFIX_OFFSET,
    OFFICIAL_V449_SIZE,
    STACK_HEADER_OFFSET,
    V449_BCD_DEVICE_OFFSET,
    parse_header,
)
from make_reset_trampoline import (
    BASE_CARRIER_SHA256,
    RESET_HANDLER,
    STOCK_RESET_CONTINUATION,
    TRAMPOLINE_ADDRESS,
    TRAMPOLINE_LIMIT,
    arm_b,
    make_reset_trampoline,
)


AUDITED_CODE_SIZE = 8
AUDITED_CODE_SHA256 = (
    "eb26dace22b23177e84b62225949e573cd2b2764add0a722411733f3cb2a57f2"
)
AUDITED_CONTAINER_SHA256 = (
    "bad4a3a7bdf3610e8b6cf0d9b1bb27f4d147ffa0efb242f24c0257bb454c6905"
)
AUDITED_PAYLOAD_SHA256 = (
    "0bae1c229db988c03f6eb55b78a726d69fdf1f42048694a404335f00b950028a"
)
AUDITED_PAYLOAD_CRC = 0xDB034CD6
STOCK_FIRST_RESET_INSTRUCTION = bytes.fromhex("0000a0e3")


class VerificationError(ValueError):
    """A trampoline artifact differs from the audited build."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _decode_arm_b(data: bytes, source: int) -> int:
    _require(len(data) == 4, "ARM branch instruction is not four bytes")
    instruction = struct.unpack("<I", data)[0]
    _require(instruction & 0xFF000000 == 0xEA000000, "instruction is not ARM B")
    delta = (instruction & 0x00FFFFFF) << 2
    if delta & (1 << 25):
        delta -= 1 << 26
    return source + 8 + delta


def _elf_text_contract(elf: bytes, code_size: int) -> None:
    _require(len(elf) >= 52, "ELF header is truncated")
    header = struct.unpack_from("<16sHHIIIIIHHHHHH", elf)
    _require(header[0][:7] == b"\x7fELF\x01\x01\x01", "ELF format is wrong")
    _require(header[1] == 2 and header[2] == 40, "ELF is not an ARM executable")
    _require(header[4] == TRAMPOLINE_ADDRESS, "ELF entry address changed")
    section_offset = header[6]
    section_size, section_count, names_index = header[11:14]
    _require(section_size == 40, "ELF section-header size changed")
    _require(0 < section_count and names_index < section_count, "bad ELF sections")
    _require(
        section_offset + section_size * section_count <= len(elf),
        "ELF section table is truncated",
    )
    sections = [
        struct.unpack_from("<IIIIIIIIII", elf, section_offset + index * 40)
        for index in range(section_count)
    ]
    name_section = sections[names_index]
    names = elf[name_section[4] : name_section[4] + name_section[5]]
    found_text = False
    for section in sections:
        end = names.find(b"\0", section[0])
        _require(end >= 0, "bad ELF section name")
        name = names[section[0] : end].decode("ascii")
        if name == ".text":
            found_text = True
            _require(section[3] == TRAMPOLINE_ADDRESS, "ELF text address changed")
            _require(section[5] == code_size, "ELF text size changed")
        _require(section[1] not in (4, 9), "ELF contains relocations")
        _require(not (section[2] & 1 and section[2] & 2), "writable alloc section")
    _require(found_text, "ELF has no text section")


def verify_reset_trampoline_data(
    base: bytes, image: bytes, code: bytes, elf: bytes
) -> dict[str, object]:
    _require(len(base) == OFFICIAL_V449_SIZE, "base carrier size changed")
    _require(_sha256(base) == BASE_CARRIER_SHA256, "base is not audited carrier")
    _require(len(code) == AUDITED_CODE_SIZE, "trampoline code size changed")
    _require(_sha256(code) == AUDITED_CODE_SHA256, "trampoline code hash changed")
    _require(
        image == make_reset_trampoline(base, code),
        "image is not an exact derivation of the carrier",
    )
    _require(_sha256(image) == AUDITED_CONTAINER_SHA256, "container hash changed")

    _require(
        base[0x2020:RESET_HANDLER] == image[0x2020:RESET_HANDLER],
        "reset vector or literal table changed",
    )
    _require(
        struct.unpack_from("<I", image, 0x2040)[0] == RESET_HANDLER,
        "reset vector does not still target 0x2064",
    )
    _require(
        base[RESET_HANDLER : RESET_HANDLER + 4] == STOCK_FIRST_RESET_INSTRUCTION,
        "recorded stock first reset instruction changed",
    )
    reset_branch = image[RESET_HANDLER : RESET_HANDLER + 4]
    _require(
        reset_branch == arm_b(RESET_HANDLER, TRAMPOLINE_ADDRESS),
        "reset branch encoding changed",
    )
    _require(
        _decode_arm_b(reset_branch, RESET_HANDLER) == TRAMPOLINE_ADDRESS,
        "reset branch target is wrong",
    )
    _require(
        code[:4] == STOCK_FIRST_RESET_INSTRUCTION,
        "trampoline does not replay displaced stock instruction",
    )
    _require(
        _decode_arm_b(code[4:8], TRAMPOLINE_ADDRESS + 4)
        == STOCK_RESET_CONTINUATION,
        "trampoline does not return to stock 0x2068",
    )
    _require(
        image[TRAMPOLINE_ADDRESS : TRAMPOLINE_ADDRESS + len(code)] == code,
        "injected trampoline differs from linked code",
    )
    _require(
        image[TRAMPOLINE_ADDRESS + len(code) : TRAMPOLINE_LIMIT]
        == b"\0" * (TRAMPOLINE_LIMIT - TRAMPOLINE_ADDRESS - len(code)),
        "unused pre-IRQ gap changed",
    )
    _require(image[0x2300:0x2330] == base[0x2300:0x2330], "stock IRQ changed")
    _require(image[V449_BCD_DEVICE_OFFSET] == 0x52, "bcdDevice is not 4.52")

    for offset in (STACK_HEADER_OFFSET, APPLICATION_HEADER_OFFSET):
        header = parse_header(image, offset)
        _require(
            header.calculate_crc(image) == header.crc,
            f"header CRC at {offset:#x} is invalid",
        )

    _elf_text_contract(elf, len(code))
    payload = image[APPLICATION_PREFIX_OFFSET:]
    payload_sha = _sha256(payload)
    payload_crc = zlib.crc32(payload) ^ 0xFFFFFFFF
    _require(len(payload) == 119_920, "wire payload size changed")
    _require(payload_sha == AUDITED_PAYLOAD_SHA256, "wire payload hash changed")
    _require(payload_crc == AUDITED_PAYLOAD_CRC, "wire payload CRC changed")
    return {
        "result": "PASS",
        "base_carrier_sha256": _sha256(base),
        "code_bytes": len(code),
        "code_sha256": _sha256(code),
        "container_bytes": len(image),
        "container_sha256": _sha256(image),
        "payload_bytes": len(payload),
        "payload_sha256": payload_sha,
        "payload_crc": f"{payload_crc:08x}",
        "reset_branch": "0x2064 -> 0x22b4",
        "stock_return": "0x22b8 -> 0x2068",
        "usb_bcd_device": "4.52",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path)
    parser.add_argument("image", type=Path)
    parser.add_argument("code", type=Path)
    parser.add_argument("elf", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        report = verify_reset_trampoline_data(
            args.base.read_bytes(),
            args.image.read_bytes(),
            args.code.read_bytes(),
            args.elf.read_bytes(),
        )
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
