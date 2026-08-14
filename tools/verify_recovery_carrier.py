#!/usr/bin/env python3
"""Offline, hash-locked checks for the staged stock recovery carrier."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

from firmware_image import (
    APPLICATION_HEADER_OFFSET,
    APPLICATION_PREFIX_OFFSET,
    OFFICIAL_V449_SHA256,
    OFFICIAL_V449_SIZE,
    STACK_HEADER_OFFSET,
    V449_BCD_DEVICE_OFFSET,
    beken_crc32,
    parse_header,
)
from make_recovery_carrier import (
    CARRIER_ADDRESS,
    CARRIER_LIMIT,
    DISPATCH_BRANCHES,
    DISPATCH_CALL,
    make_recovery_carrier,
    thumb_bl,
)


AUDITED_CODE_SIZE = 264
AUDITED_CODE_SHA256 = (
    "6dfab1b623c6fbd8daa6be71bdb3bfad1e90808da90956dc671c0165544dbd2e"
)
AUDITED_CONTAINER_SHA256 = (
    "e555d5e17edc84cb8799d035d6193f6f664c1df9116bcba3c49faef1609221e8"
)
EXPECTED_PAYLOAD_SIZE = OFFICIAL_V449_SIZE - APPLICATION_PREFIX_OFFSET
EXPECTED_BLOCK_COUNT = (EXPECTED_PAYLOAD_SIZE + 31) // 32


class VerificationError(ValueError):
    """A carrier artifact differs from the manually audited build."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _u32(data: bytes, offset: int) -> int:
    _require(offset >= 0 and offset + 4 <= len(data), f"no word at {offset:#x}")
    return struct.unpack_from("<I", data, offset)[0]


def _decode_thumb_bl(image: bytes, source: int) -> int:
    high, low = struct.unpack_from("<HH", image, source)
    _require(high & 0xF800 == 0xF000, f"no Thumb BL first half at {source:#x}")
    _require(low & 0xF800 == 0xF800, f"no Thumb BL second half at {source:#x}")
    delta = ((high & 0x7FF) << 12) | ((low & 0x7FF) << 1)
    if delta & (1 << 22):
        delta -= 1 << 23
    return source + 4 + delta


def _elf_sections(elf: bytes) -> tuple[int, list[dict[str, int | str]]]:
    _require(len(elf) >= 52, "ELF header is truncated")
    header = struct.unpack_from("<16sHHIIIIIHHHHHH", elf)
    _require(
        header[0][:7] == b"\x7fELF\x01\x01\x01",
        "ELF is not 32-bit little-endian",
    )
    _require(header[1] == 2 and header[2] == 40, "ELF is not an ARM executable")
    entry = header[4]
    section_offset = header[6]
    section_size, section_count, names_index = header[11:14]
    _require(section_size == 40, "unexpected ELF section-header size")
    _require(0 < section_count and names_index < section_count, "bad section table")
    _require(
        section_offset + section_size * section_count <= len(elf),
        "ELF section table is truncated",
    )
    raw = [
        struct.unpack_from("<IIIIIIIIII", elf, section_offset + index * 40)
        for index in range(section_count)
    ]
    name_section = raw[names_index]
    names = elf[name_section[4] : name_section[4] + name_section[5]]
    sections: list[dict[str, int | str]] = []
    for section in raw:
        end = names.find(b"\0", section[0])
        _require(end >= 0, "bad ELF section name")
        sections.append(
            {
                "name": names[section[0] : end].decode("ascii"),
                "type": section[1],
                "flags": section[2],
                "address": section[3],
                "size": section[5],
            }
        )
    return entry, sections


def verify_carrier_data(
    stock: bytes, carrier: bytes, code: bytes, elf: bytes
) -> dict[str, object]:
    stock_sha = _sha256(stock)
    _require(len(stock) == OFFICIAL_V449_SIZE, "stock image size is wrong")
    _require(stock_sha == OFFICIAL_V449_SHA256, "stock image is not official v4.49")
    _require(len(code) == AUDITED_CODE_SIZE, "carrier code size changed")
    _require(CARRIER_ADDRESS + len(code) < CARRIER_LIMIT, "carrier safety margin vanished")
    _require(
        stock[CARRIER_ADDRESS:CARRIER_LIMIT] == b"\0" * (CARRIER_LIMIT - CARRIER_ADDRESS),
        "stock carrier gap is not zero-filled",
    )
    _require(len(carrier) == len(stock), "carrier size differs from stock")
    _require(carrier == make_recovery_carrier(stock, code), "carrier is not a clean stock-derived build")
    _require(
        carrier[CARRIER_ADDRESS : CARRIER_ADDRESS + len(code)] == code,
        "injected bytes differ from linked code",
    )
    _require(
        carrier[CARRIER_ADDRESS + len(code) : CARRIER_LIMIT]
        == b"\0" * (CARRIER_LIMIT - CARRIER_ADDRESS - len(code)),
        "unused carrier safety margin changed",
    )
    _require(carrier[0x2300:0x2330] == stock[0x2300:0x2330], "stock IRQ/FIQ handlers changed")

    for offset, expected in DISPATCH_BRANCHES.items():
        _require(carrier[offset : offset + 2] == expected, f"dispatcher patch at {offset:#x} changed")
    _require(
        carrier[DISPATCH_CALL : DISPATCH_CALL + 4]
        == thumb_bl(DISPATCH_CALL, CARRIER_ADDRESS),
        "dispatcher call encoding changed",
    )
    _require(_decode_thumb_bl(carrier, DISPATCH_CALL) == CARRIER_ADDRESS, "dispatcher does not call carrier")
    _require(_decode_thumb_bl(stock, DISPATCH_CALL) == 0x1895C, "recorded stock command 0x0d target changed")

    _require(
        carrier[0x21AC:0x21BE]
        == bytes.fromhex("0d2804d00e2804d00f280ad00ae02f4b1847"),
        "carrier dispatch or stock-recovery tail call changed",
    )
    _require(
        carrier[0x21BE:0x21CE]
        == bytes.fromhex("10b52e482f498860202000f03bf810bd"),
        "read-only storage probe changed",
    )
    _require(
        carrier[0x21CE:0x21D0] == bytes.fromhex("28e0"),
        "reset-only probe changed",
    )

    literals = {
        0x2278: 0x0001895D,
        0x227C: 0x0000807C,
        0x2280: 0x00803000,
        0x2284: 0x78563412,
        0x2288: 0x0000807D,
        0x228C: 0x19D2BC9A,
        0x2290: 0x000178EB,
        0x2294: 0x0080001C,
        0x2298: 0x00806000,
        0x229C: 0x008000C0,
        0x22A0: 0x00AA5AAA,
        0x22A4: 0x005A0050,
        0x22A8: 0x00A50050,
        0x22AC: 0x000058A9,
        0x22B0: 0x0000A958,
    }
    for offset, expected in literals.items():
        _require(_u32(carrier, offset) == expected, f"critical literal at {offset:#x} changed")
    _require(
        [_u32(stock, offset) for offset in (0x177E4, 0x177EC)]
        == [_u32(carrier, 0x22AC), _u32(carrier, 0x22B0)]
        == [0x58A9, 0xA958],
        "storage unlock order differs from stock",
    )
    _require(
        carrier[0x2242:0x2276]
        == bytes.fromhex(
            "0f49194a0a60194a0a60a5220a61c3224a614a687c239a4302434a60"
            "0120104348604868c007fcd1002008600860086148617047"
        ),
        "storage-controller instruction sequence changed",
    )

    for offset in (STACK_HEADER_OFFSET, APPLICATION_HEADER_OFFSET):
        header = parse_header(carrier, offset)
        _require(header.calculate_crc(carrier) == header.crc, f"header CRC at {offset:#x} is invalid")
    _require(carrier[V449_BCD_DEVICE_OFFSET] == 0x51, "carrier bcdDevice is not 4.51")

    entry, sections = _elf_sections(elf)
    _require(entry == CARRIER_ADDRESS + 1, "carrier ELF entry is not Thumb 0x21ad")
    by_name = {str(section["name"]): section for section in sections}
    _require(by_name.get(".text", {}).get("address") == CARRIER_ADDRESS, "ELF text address changed")
    _require(by_name.get(".text", {}).get("size") == len(code), "ELF text size differs from raw code")
    for section in sections:
        flags = int(section["flags"])
        _require(int(section["type"]) not in (4, 9), "ELF contains relocations")
        _require(not (flags & 1 and flags & 2), "ELF contains writable allocated data")

    code_sha = _sha256(code)
    carrier_sha = _sha256(carrier)
    _require(code_sha == AUDITED_CODE_SHA256, "carrier code differs from audited build")
    _require(carrier_sha == AUDITED_CONTAINER_SHA256, "carrier image differs from audited build")
    payload = carrier[APPLICATION_PREFIX_OFFSET:]
    _require(len(payload) == EXPECTED_PAYLOAD_SIZE, "wire payload size changed")
    return {
        "result": "PASS",
        "stock_sha256": stock_sha,
        "code_bytes": len(code),
        "code_sha256": code_sha,
        "carrier_bytes": len(carrier),
        "carrier_sha256": carrier_sha,
        "carrier_region": "0x21ac-0x22b3",
        "unused_gap_bytes": CARRIER_LIMIT - CARRIER_ADDRESS - len(code),
        "payload_bytes": len(payload),
        "payload_sha256": _sha256(payload),
        "payload_crc": f"{beken_crc32(payload):08x}",
        "b1_blocks": EXPECTED_BLOCK_COUNT,
        "usb_bcd_device": "4.51",
        "commands": {
            "0x0d": "original stock recovery",
            "0x0e": "non-writing storage read probe",
            "0x0f": "direct watchdog reset probe",
            "0x10": "direct marker and reset probe",
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stock", type=Path)
    parser.add_argument("carrier", type=Path)
    parser.add_argument("code", type=Path)
    parser.add_argument("elf", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        report = verify_carrier_data(
            args.stock.read_bytes(),
            args.carrier.read_bytes(),
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
