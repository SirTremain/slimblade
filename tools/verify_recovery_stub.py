#!/usr/bin/env python3
"""Offline, hash-locked pre-flight checks for the BK3635 recovery stub."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

from firmware_image import (
    APPLICATION_CODE_OFFSET,
    APPLICATION_HEADER_OFFSET,
    APPLICATION_PREFIX_OFFSET,
    APPLICATION_UID,
    OFFICIAL_APPLICATION_END_OFFSET,
    OFFICIAL_V449_SHA256,
    OFFICIAL_V449_SIZE,
    beken_crc32,
    parse_header,
)


AUDITED_CODE_SHA256 = (
    "d88b2cd9211d9c46914062770e024f409dcee75ec826e70e80f6ff9a9e353bfe"
)
AUDITED_CONTAINER_SHA256 = (
    "34daf13778a79034cc3a35917fbe6cfacc0b2f93db650e50f1f4df98ecf7e618"
)
AUDITED_CODE_SIZE = 420
EXPECTED_PAYLOAD_SIZE = OFFICIAL_V449_SIZE - APPLICATION_PREFIX_OFFSET
EXPECTED_BLOCK_COUNT = (EXPECTED_PAYLOAD_SIZE + 31) // 32


class VerificationError(ValueError):
    """An artifact differs from the manually audited recovery-stub build."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def _u32(data: bytes, offset: int) -> int:
    _require(offset >= 0 and offset + 4 <= len(data), f"no word at {offset:#x}")
    return struct.unpack_from("<I", data, offset)[0]


def _elf_sections(elf: bytes) -> tuple[dict[str, int], list[dict[str, int | str]]]:
    _require(len(elf) >= 52, "ELF header is truncated")
    header = struct.unpack_from("<16sHHIIIIIHHHHHH", elf)
    ident = header[0]
    _require(ident[:7] == b"\x7fELF\x01\x01\x01", "ELF is not 32-bit little-endian")
    elf_type, machine, entry = header[1], header[2], header[4]
    section_offset = header[6]
    section_entry_size, section_count, names_index = header[11:14]
    _require(elf_type == 2, "ELF is not executable")
    _require(machine == 40, "ELF machine is not ARM")
    _require(entry == APPLICATION_CODE_OFFSET, "ELF entry is not 0x2020")
    _require(section_entry_size == 40, "unexpected ELF section-header size")
    _require(0 < section_count and names_index < section_count, "bad ELF section table")
    table_end = section_offset + section_entry_size * section_count
    _require(table_end <= len(elf), "ELF section table is truncated")

    raw_sections = [
        struct.unpack_from("<IIIIIIIIII", elf, section_offset + index * 40)
        for index in range(section_count)
    ]
    names = raw_sections[names_index]
    names_offset, names_size = names[4], names[5]
    _require(names_offset + names_size <= len(elf), "ELF section names are truncated")
    name_data = elf[names_offset : names_offset + names_size]

    sections: list[dict[str, int | str]] = []
    for section in raw_sections:
        name_offset = section[0]
        _require(name_offset < len(name_data) or name_offset == 0, "bad section name")
        name_end = name_data.find(b"\0", name_offset)
        _require(name_end >= 0, "unterminated section name")
        sections.append(
            {
                "name": name_data[name_offset:name_end].decode("ascii"),
                "type": section[1],
                "flags": section[2],
                "address": section[3],
                "offset": section[4],
                "size": section[5],
            }
        )
    return {"type": elf_type, "machine": machine, "entry": entry}, sections


def verify_artifacts_data(
    stock: bytes, container: bytes, code: bytes, elf: bytes
) -> dict[str, object]:
    """Verify exact audited artifacts and return a compact comparison report."""
    stock_sha = _sha256(stock)
    _require(len(stock) == OFFICIAL_V449_SIZE, "stock v4.49 size is wrong")
    _require(stock_sha == OFFICIAL_V449_SHA256, "stock input is not official v4.49")

    stock_header = parse_header(stock, APPLICATION_HEADER_OFFSET)
    stub_header = parse_header(container, APPLICATION_HEADER_OFFSET)
    _require(len(container) == len(stock), "container size differs from stock")
    _require(stub_header.calculate_crc(container) == stub_header.crc, "application CRC is invalid")
    _require(stub_header.end_offset == OFFICIAL_APPLICATION_END_OFFSET, "application end differs from stock")
    for field in (
        "version",
        "length_words",
        "uid",
        "crc_status",
        "section_status",
        "rom_version",
    ):
        _require(
            getattr(stub_header, field) == getattr(stock_header, field),
            f"application header field {field} differs from stock",
        )
    _require(stub_header.uid == APPLICATION_UID, "application UID is wrong")
    _require(
        container[APPLICATION_PREFIX_OFFSET:APPLICATION_HEADER_OFFSET] == b"\xff" * 16,
        "non-transmitted application prefix is not erased padding",
    )

    _require(len(code) == AUDITED_CODE_SIZE, "raw recovery code size changed")
    _require(
        container[APPLICATION_CODE_OFFSET : APPLICATION_CODE_OFFSET + len(code)] == code,
        "container does not contain the supplied raw code",
    )
    _require(
        container[APPLICATION_CODE_OFFSET + len(code) :] ==
        b"\xff" * (len(container) - APPLICATION_CODE_OFFSET - len(code)),
        "bytes after recovery code are not erased padding",
    )

    # The eight vector opcodes and reset address retain the proven stock geometry.
    _require(
        container[0x2020:0x2040] == stock[0x2020:0x2040],
        "vector opcodes differ from stock v4.49",
    )
    _require(_u32(container, 0x2040) == _u32(stock, 0x2040) == 0x2064, "reset target differs from stock")
    _require(
        [_u32(container, offset) for offset in (0x2044, 0x2048, 0x204C, 0x2050)]
        == [0x2060] * 4,
        "exception vectors do not enter the safe hang loop",
    )
    _require(_u32(container, 0x2054) == 0, "reserved vector is nonzero")
    _require(
        [_u32(container, offset) for offset in (0x2058, 0x205C)] == [0x2060, 0x2060],
        "disabled IRQ/FIQ vectors do not enter the safe hang loop",
    )
    _require(_u32(container, 0x2060) == 0xEAFFFFFE, "safe hang loop changed")
    expected_reset = bytes.fromhex(
        "d300a0e300f021e104d09fe504009fe510ff2fe1007f400081200000"
    )
    _require(container[0x2064:0x2080] == expected_reset, "minimal reset sequence changed")

    # These are literal words consumed in order by the stock and stub instructions.
    stock_unlock = [_u32(stock, 0x177E4), _u32(stock, 0x177EC)]
    stub_unlock = [_u32(container, 0x2170), _u32(container, 0x2174)]
    _require(stock_unlock == [0x58A9, 0xA958], "recorded stock unlock order changed")
    _require(stub_unlock == stock_unlock, "stub storage unlock order differs from stock")
    _require(_u32(container, 0x216C) == 0x00803000, "storage controller base changed")
    _require(
        container[0x2138:0x216C]
        == bytes.fromhex(
            "0c490d4a0a600d4a0a60a5220a61c3224a614a687c239a4302434a60"
            "0120104348604868c007fcd1002008600860086148617047"
        ),
        "emitted storage-controller instruction sequence changed",
    )

    _require(
        [_u32(container, offset) for offset in (0x20C4, 0x20C8, 0x20CC)]
        == [0x807C, 0x78563412, 0x19D2BC9A],
        "loader marker address or bytes changed",
    )
    _require(_u32(container, 0x20E4) == _u32(container, 0x20F8) == 0x00803008, "storage address register changed")
    _require(
        container[0x20D0:0x20F8]
        == bytes.fromhex(
            "80b50120c00303490860282000f02cf880bdc04608308000"
            "80b5034a10605160242000f021f880bd"
        ),
        "erase/write command emission changed",
    )
    _require(
        container[0x2178:0x21C4]
        == bytes.fromhex(
            "70b50d0004000ce06a22012000f010f81000521e1206120e0028f6d1"
            "002d00d0c0462000641e2404240c0028ecd170bd05e00021491c0906"
            "090e1129fad30100401e0006000e0029f3d17047"
        ),
        "stock-equivalent assembly delay changed",
    )
    _require(
        container[0x21A8:0x21C4] == stock[0x178CE:0x178EA],
        "delay inner loop no longer matches stock instruction-for-instruction",
    )
    _require(
        container[0x2178:0x217E] == stock[0x178EA:0x178F0]
        and container[0x2180:0x2184] == stock[0x178F2:0x178F6]
        and container[0x2188:0x2196] == stock[0x178FA:0x17908]
        and container[0x219A:0x21A2] == stock[0x1790E:0x17916],
        "delay's executed outer/middle instructions differ from stock",
    )

    _require(
        [_u32(container, offset) for offset in (0x2128, 0x212C, 0x2130, 0x2134)]
        == [0x0080001C, 0x00806000, 0x008000C0, 0x00AA5AAA],
        "watchdog/reset MMIO literals changed",
    )
    _require(
        [_u32(stock, offset) for offset in (0x19CD0, 0x19CD4, 0x19CDC)]
        == [0x00AA5AAA, 0x008000C0, 0x00806000],
        "recorded stock watchdog/reset literals changed",
    )
    _require(
        container[0x20FC:0x2128]
        == bytes.fromhex(
            "0a49012008602d20420409480260a5231b040360074c084d25600024"
            "0c60502101605032026050330360fee7"
        ),
        "emitted watchdog/reset instruction sequence changed",
    )

    elf_header, sections = _elf_sections(elf)
    by_name = {str(section["name"]): section for section in sections}
    _require(by_name.get(".vectors", {}).get("address") == 0x2020, "ELF vector address changed")
    _require(by_name.get(".vectors", {}).get("size") == 0x60, "ELF vector size changed")
    _require(by_name.get(".text", {}).get("address") == 0x2080, "ELF text address changed")
    for section in sections:
        flags = int(section["flags"])
        _require(int(section["type"]) not in (4, 9), "ELF contains relocations")
        _require(not (flags & 1 and flags & 2), f"writable allocated section {section['name']} is unsupported")

    code_sha = _sha256(code)
    container_sha = _sha256(container)
    _require(code_sha == AUDITED_CODE_SHA256, "raw code differs from the audited build")
    _require(container_sha == AUDITED_CONTAINER_SHA256, "container differs from the audited build")

    payload = container[APPLICATION_PREFIX_OFFSET:]
    _require(len(payload) == EXPECTED_PAYLOAD_SIZE, "transmitted payload size changed")
    return {
        "result": "PASS",
        "stock_sha256": stock_sha,
        "code_bytes": len(code),
        "code_sha256": code_sha,
        "container_bytes": len(container),
        "container_sha256": container_sha,
        "application_crc": f"{stub_header.crc:08x}",
        "application_end": f"0x{stub_header.end_offset:x}",
        "payload_bytes": len(payload),
        "payload_sha256": _sha256(payload),
        "payload_crc": f"{beken_crc32(payload):08x}",
        "b1_blocks": EXPECTED_BLOCK_COUNT,
        "elf_entry": f"0x{elf_header['entry']:x}",
        "comparisons": {
            "header_geometry_matches_stock": True,
            "vector_opcodes_and_reset_target_match_stock": True,
            "storage_unlock_order_matches_stock": ["0x58a9", "0xa958"],
            "marker_and_watchdog_sequences_match_audited_disassembly": True,
            "wire_geometry_matches_successful_4.50_probe": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stock", type=Path, help="exact extracted official v4.49 image")
    parser.add_argument("container", type=Path)
    parser.add_argument("code", type=Path)
    parser.add_argument("elf", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        report = verify_artifacts_data(
            args.stock.read_bytes(),
            args.container.read_bytes(),
            args.code.read_bytes(),
            args.elf.read_bytes(),
        )
    except (OSError, VerificationError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
