#!/usr/bin/env python3
"""Verify the source-built BK3635 startup against stock SlimBlade v4.49."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

from firmware_image import OFFICIAL_V449_SHA256, OFFICIAL_V449_SIZE


STARTUP_ADDRESS = 0x2020
STARTUP_END = 0x21AC
STARTUP_SIZE = STARTUP_END - STARTUP_ADDRESS
AUDITED_STARTUP_SHA256 = (
    "60d7616f48e2e457787e28748aec0b8afd404af35094cc8ef6b74c660c9248d8"
)
WRAPPERS_ADDRESS = 0x2300
WRAPPERS_END = 0x2330
WRAPPERS_SIZE = WRAPPERS_END - WRAPPERS_ADDRESS
AUDITED_WRAPPERS_SHA256 = (
    "02e811fe3f434dd0fc697621bfbdc9cd74eee2d1e5d16df93f94f15fe7e5df9d"
)


class VerificationError(ValueError):
    """The rebuilt startup or its reference input is not the audited version."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _u32(data: bytes, offset: int) -> int:
    _require(0 <= offset <= len(data) - 4, f"no word at {offset:#x}")
    return struct.unpack_from("<I", data, offset)[0]


def _arm_branch_target(code: bytes, address: int) -> int:
    instruction = _u32(code, address - STARTUP_ADDRESS)
    _require(instruction >> 24 in (0xEA, 0xEB), f"no ARM branch at {address:#x}")
    delta = (instruction & 0xFFFFFF) << 2
    if delta & (1 << 25):
        delta -= 1 << 26
    return address + 8 + delta


def _arm_blx_target(code: bytes, address: int) -> int:
    instruction = _u32(code, address - WRAPPERS_ADDRESS)
    _require(instruction & 0xFE000000 == 0xFA000000, f"no ARM BLX at {address:#x}")
    delta = ((instruction & 0xFFFFFF) << 2) | ((instruction >> 23) & 2)
    if delta & (1 << 25):
        delta -= 1 << 26
    return address + 8 + delta


def _elf_sections(elf: bytes) -> tuple[int, list[dict[str, int | str]]]:
    _require(len(elf) >= 52, "ELF header is truncated")
    header = struct.unpack_from("<16sHHIIIIIHHHHHH", elf)
    _require(header[0][:7] == b"\x7fELF\x01\x01\x01", "ELF is not 32-bit little-endian")
    _require(header[1] == 2 and header[2] == 40, "ELF is not an ARM executable")
    entry = header[4]
    table_offset = header[6]
    entry_size, count, names_index = header[11:14]
    _require(entry_size == 40, "unexpected ELF section-header size")
    _require(0 < count and names_index < count, "bad ELF section table")
    _require(table_offset + entry_size * count <= len(elf), "ELF section table is truncated")
    raw = [
        struct.unpack_from("<IIIIIIIIII", elf, table_offset + index * entry_size)
        for index in range(count)
    ]
    names_header = raw[names_index]
    names = elf[names_header[4] : names_header[4] + names_header[5]]
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


def verify_sdk_startup_data(
    stock: bytes, code: bytes, wrappers: bytes, elf: bytes
) -> dict[str, object]:
    stock_sha = _sha256(stock)
    _require(len(stock) == OFFICIAL_V449_SIZE, "stock image size is wrong")
    _require(stock_sha == OFFICIAL_V449_SHA256, "stock image is not official v4.49")
    _require(len(code) == STARTUP_SIZE, "rebuilt startup size changed")

    stock_startup = stock[STARTUP_ADDRESS:STARTUP_END]
    first_difference = next(
        (index for index, pair in enumerate(zip(code, stock_startup)) if pair[0] != pair[1]),
        None,
    )
    _require(
        code == stock_startup,
        "rebuilt startup differs from stock"
        + (f" at {STARTUP_ADDRESS + first_difference:#x}" if first_difference is not None else ""),
    )
    code_sha = _sha256(code)
    _require(code_sha == AUDITED_STARTUP_SHA256, "startup differs from audited build")

    vector_literals = [_u32(code, offset) for offset in range(0x20, 0x40, 4)]
    _require(
        vector_literals == [0x2064, 0x2060, 0x2060, 0x2060, 0x2060, 0, 0x2320, 0x2300],
        "vector targets changed",
    )
    call_targets = {
        "stack_init": _arm_branch_target(code, 0x2098),
        "zero_bss": _arm_branch_target(code, 0x209C),
        "copy_data": _arm_branch_target(code, 0x20A0),
    }
    _require(
        call_targets == {"stack_init": 0x20B4, "zero_bss": 0x2140, "copy_data": 0x2114},
        "reset call targets changed",
    )
    _require(_u32(code, 0x2170 - STARTUP_ADDRESS) == 0x19879, "Thumb entry changed")

    _require(len(wrappers) == WRAPPERS_SIZE, "interrupt-wrapper span size changed")
    stock_wrappers = stock[WRAPPERS_ADDRESS:WRAPPERS_END]
    _require(wrappers == stock_wrappers, "rebuilt interrupt wrappers differ from stock")
    wrappers_sha = _sha256(wrappers)
    _require(wrappers_sha == AUDITED_WRAPPERS_SHA256, "wrappers differ from audited build")
    _require(wrappers[0x10:0x20] == b"\0" * 16, "reserved IRQ/FIQ gap is not zero")
    _require(
        [_u32(wrappers, offset) for offset in (0, 8, 12, 0x20, 0x28, 0x2C)]
        == [0xE92D500F, 0xE8BD500F, 0xE25EF004] * 2,
        "interrupt save, restore, or exception return changed",
    )
    interrupt_targets = {
        "irq_thumb_dispatch": _arm_blx_target(wrappers, 0x2304),
        "fiq_thumb_dispatch": _arm_blx_target(wrappers, 0x2324),
    }
    _require(
        interrupt_targets == {"irq_thumb_dispatch": 0x3E78, "fiq_thumb_dispatch": 0x60E0},
        "interrupt dispatcher target changed",
    )

    entry, sections = _elf_sections(elf)
    _require(entry == STARTUP_ADDRESS, "ELF entry is not the ARM vector table")
    by_name = {str(section["name"]): section for section in sections}
    startup = by_name.get(".startup", {})
    _require(startup.get("address") == STARTUP_ADDRESS, "ELF startup address changed")
    _require(startup.get("size") == STARTUP_SIZE, "ELF startup size changed")
    _require(int(startup.get("flags", 0)) & 0x6 == 0x6, "ELF startup is not allocated executable code")
    _require(by_name.get(".irq_wrapper", {}).get("address") == 0x2300, "ELF IRQ address changed")
    _require(by_name.get(".irq_wrapper", {}).get("size") == 0x10, "ELF IRQ size changed")
    _require(by_name.get(".fiq_wrapper", {}).get("address") == 0x2320, "ELF FIQ address changed")
    _require(by_name.get(".fiq_wrapper", {}).get("size") == 0x10, "ELF FIQ size changed")
    for section in sections:
        flags = int(section["flags"])
        _require(int(section["type"]) not in (4, 9), "ELF contains relocations")
        _require(not (flags & 1 and flags & 2), "ELF contains writable allocated data")

    return {
        "result": "PASS",
        "stock_sha256": stock_sha,
        "startup_region": "0x2020-0x21ab",
        "startup_bytes": len(code),
        "startup_sha256": code_sha,
        "byte_exact": True,
        "elf_entry": f"0x{entry:x}",
        "reset_target": "0x2064",
        "thumb_application_entry": "0x19879",
        "reset_calls": {name: f"0x{target:x}" for name, target in call_targets.items()},
        "interrupt_wrapper_region": "0x2300-0x232f",
        "interrupt_wrapper_bytes": len(wrappers),
        "interrupt_wrapper_sha256": wrappers_sha,
        "interrupt_dispatch": {
            name: f"0x{target:x}" for name, target in interrupt_targets.items()
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stock", type=Path, help="official Kensington v4.49 image")
    parser.add_argument("code", type=Path, help="raw source-built startup region")
    parser.add_argument("wrappers", type=Path, help="raw IRQ/FIQ span")
    parser.add_argument("elf", type=Path, help="linked source-built ELF")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        report = verify_sdk_startup_data(
            args.stock.read_bytes(),
            args.code.read_bytes(),
            args.wrappers.read_bytes(),
            args.elf.read_bytes(),
        )
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
