#!/usr/bin/env python3
"""Offline, hash-locked checks for the CPU/stack/interworking trampoline."""

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
from make_startup_trampoline import (
    BASE_RESET_TRAMPOLINE_SHA256,
    TRAMPOLINE_ADDRESS,
    TRAMPOLINE_LIMIT,
    make_startup_trampoline,
)


AUDITED_STUB_SHA256 = (
    "34daf13778a79034cc3a35917fbe6cfacc0b2f93db650e50f1f4df98ecf7e618"
)
AUDITED_CODE_SIZE = 60
AUDITED_CODE_SHA256 = (
    "0e24e9ffbf218afabde39043b177f19e29761b3175b772351fb6f7a839a800f7"
)
AUDITED_CONTAINER_SHA256 = (
    "dccea5665710e9aebe039a83d49d07a1a0b32efc3826c7367814f5512ececa7b"
)
AUDITED_PAYLOAD_SHA256 = (
    "da04628aa7e05ee253b63a4984b2ceb138d91029f239f11efd6914b0da9afc8a"
)
AUDITED_PAYLOAD_CRC = 0x4E9C5E53


class VerificationError(ValueError):
    """A startup-trampoline artifact differs from the audited build."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _u32(data: bytes, offset: int) -> int:
    _require(offset >= 0 and offset + 4 <= len(data), f"no word at {offset:#x}")
    return struct.unpack_from("<I", data, offset)[0]


def _decode_arm_b(instruction: int, source: int) -> int:
    _require(instruction & 0xFF000000 == 0xEA000000, "instruction is not ARM B")
    delta = (instruction & 0x00FFFFFF) << 2
    if delta & (1 << 25):
        delta -= 1 << 26
    return source + 8 + delta


def _verify_elf(elf: bytes, code_size: int) -> None:
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


def verify_startup_trampoline_data(
    base: bytes, image: bytes, code: bytes, elf: bytes, stub: bytes
) -> dict[str, object]:
    _require(len(base) == OFFICIAL_V449_SIZE, "base image size changed")
    _require(
        _sha256(base) == BASE_RESET_TRAMPOLINE_SHA256,
        "base is not the live-proven v4.52 reset trampoline",
    )
    _require(_sha256(stub) == AUDITED_STUB_SHA256, "standalone stub hash changed")
    _require(len(code) == AUDITED_CODE_SIZE, "startup code size changed")
    _require(_sha256(code) == AUDITED_CODE_SHA256, "startup code hash changed")
    _require(
        image == make_startup_trampoline(base, code),
        "image is not an exact derivation of v4.52",
    )
    _require(_sha256(image) == AUDITED_CONTAINER_SHA256, "container hash changed")

    expected_words = {
        0x00: 0xE10FA000,  # mrs r10, cpsr
        0x04: 0xE1A0B00D,  # mov r11, sp
        0x08: 0xE3A000D3,  # mov r0, #0xd3
        0x0C: 0xE121F000,  # msr cpsr_c, r0
        0x10: 0xE59FD014,  # ldr sp, stack literal
        0x14: 0xE59F0014,  # ldr r0, Thumb pointer
        0x18: 0xE12FFF10,  # bx r0
        0x1C: 0xE121F00A,  # msr cpsr_c, r10
        0x20: 0xE1A0D00B,  # mov sp, r11
        0x24: 0xE3A00000,  # displaced stock mov r0, #0
        0x2C: 0x00407F00,  # standalone stack top
        0x30: 0x000022E9,  # odd Thumb entry pointer
        0x38: 0x000022D0,  # even ARM resume pointer
    }
    for offset, expected in expected_words.items():
        _require(_u32(code, offset) == expected, f"word at +{offset:#x} changed")
    _require(
        _decode_arm_b(_u32(code, 0x28), 0x22DC) == 0x2068,
        "final ARM branch does not resume stock 0x2068",
    )
    _require(code[0x34:0x38] == bytes.fromhex("00480047"), "Thumb ldr/bx changed")
    _require(_u32(code, 0x30) & 1 == 1, "ARM-to-Thumb target is not odd")
    _require(_u32(code, 0x38) & 1 == 0, "Thumb-to-ARM target is not even")

    # These are the standalone reset handler's exact mode/stack/interworking pieces.
    _require(code[0x08:0x10] == stub[0x2064:0x206C], "mode setup differs from stub")
    _require(code[0x18:0x1C] == stub[0x2074:0x2078], "ARM bx differs from stub")
    _require(_u32(code, 0x2C) == _u32(stub, 0x2078), "stack top differs from stub")
    _require(_u32(stub, 0x207C) == 0x2081, "stub Thumb entry pointer changed")

    _require(image[0x2064:0x2068] == base[0x2064:0x2068], "reset branch changed")
    _require(
        image[TRAMPOLINE_ADDRESS : TRAMPOLINE_ADDRESS + len(code)] == code,
        "container code differs from linked code",
    )
    _require(
        image[TRAMPOLINE_ADDRESS + len(code) : TRAMPOLINE_LIMIT]
        == b"\0" * (TRAMPOLINE_LIMIT - TRAMPOLINE_ADDRESS - len(code)),
        "unused pre-IRQ gap changed",
    )
    _require(image[0x2300:0x2330] == base[0x2300:0x2330], "stock IRQ changed")
    _require(image[V449_BCD_DEVICE_OFFSET] == 0x53, "bcdDevice is not 4.53")
    for offset in (STACK_HEADER_OFFSET, APPLICATION_HEADER_OFFSET):
        header = parse_header(image, offset)
        _require(header.calculate_crc(image) == header.crc, "image CRC is invalid")

    _verify_elf(elf, len(code))
    payload = image[APPLICATION_PREFIX_OFFSET:]
    payload_sha = _sha256(payload)
    payload_crc = zlib.crc32(payload) ^ 0xFFFFFFFF
    _require(len(payload) == 119_920, "wire payload size changed")
    _require(payload_sha == AUDITED_PAYLOAD_SHA256, "wire payload hash changed")
    _require(payload_crc == AUDITED_PAYLOAD_CRC, "wire payload CRC changed")
    return {
        "result": "PASS",
        "base_sha256": _sha256(base),
        "stub_sha256": _sha256(stub),
        "code_bytes": len(code),
        "code_sha256": _sha256(code),
        "container_bytes": len(image),
        "container_sha256": _sha256(image),
        "payload_bytes": len(payload),
        "payload_sha256": payload_sha,
        "payload_crc": f"{payload_crc:08x}",
        "arm_to_thumb": "0x22cc -> 0x22e9",
        "thumb_to_arm": "0x22ea -> 0x22d0",
        "stock_return": "0x22dc -> 0x2068",
        "usb_bcd_device": "4.53",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path)
    parser.add_argument("image", type=Path)
    parser.add_argument("code", type=Path)
    parser.add_argument("elf", type=Path)
    parser.add_argument("stub", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        report = verify_startup_trampoline_data(
            args.base.read_bytes(),
            args.image.read_bytes(),
            args.code.read_bytes(),
            args.elf.read_bytes(),
            args.stub.read_bytes(),
        )
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
