#!/usr/bin/env python3
"""Build the stock-derived ARM reset-trampoline acceptance image."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import struct
import sys

from firmware_image import (
    APPLICATION_HEADER_OFFSET,
    OFFICIAL_V449_SIZE,
    STACK_HEADER_OFFSET,
    V449_BCD_DEVICE_OFFSET,
    refresh_header_crc,
)


BASE_CARRIER_SHA256 = (
    "e555d5e17edc84cb8799d035d6193f6f664c1df9116bcba3c49faef1609221e8"
)
RESET_HANDLER = 0x2064
STOCK_RESET_CONTINUATION = 0x2068
TRAMPOLINE_ADDRESS = 0x22B4
TRAMPOLINE_LIMIT = 0x2300


def arm_b(source: int, target: int) -> bytes:
    """Encode an unconditional ARM-state B instruction."""
    if source & 3 or target & 3:
        raise ValueError("ARM branch source and target must be word-aligned")
    delta = target - (source + 8)
    if delta & 3 or not -(1 << 25) <= delta < (1 << 25):
        raise ValueError("ARM branch target is out of range")
    instruction = 0xEA000000 | ((delta >> 2) & 0x00FFFFFF)
    return struct.pack("<I", instruction)


def make_reset_trampoline(base: bytes, code: bytes) -> bytes:
    digest = hashlib.sha256(base).hexdigest()
    if len(base) != OFFICIAL_V449_SIZE or digest != BASE_CARRIER_SHA256:
        raise ValueError(
            "input is not the exact audited v4.51 recovery carrier: "
            f"size={len(base)}, sha256={digest}"
        )
    if not code:
        raise ValueError("trampoline code is empty")
    if TRAMPOLINE_ADDRESS + len(code) > TRAMPOLINE_LIMIT:
        raise ValueError("trampoline overlaps the stock IRQ handler")
    if base[TRAMPOLINE_ADDRESS:TRAMPOLINE_LIMIT] != b"\0" * (
        TRAMPOLINE_LIMIT - TRAMPOLINE_ADDRESS
    ):
        raise ValueError("carrier trampoline region is not zero-filled")

    image = bytearray(base)
    image[RESET_HANDLER : RESET_HANDLER + 4] = arm_b(
        RESET_HANDLER, TRAMPOLINE_ADDRESS
    )
    image[TRAMPOLINE_ADDRESS : TRAMPOLINE_ADDRESS + len(code)] = code
    image[V449_BCD_DEVICE_OFFSET] = 0x52
    refresh_header_crc(image, APPLICATION_HEADER_OFFSET)
    refresh_header_crc(image, STACK_HEADER_OFFSET)
    return bytes(image)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path)
    parser.add_argument("code", type=Path)
    parser.add_argument("output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        image = make_reset_trampoline(
            args.base.read_bytes(), args.code.read_bytes()
        )
        args.output.write_bytes(image)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(f"wrote {len(image)} bytes; sha256={hashlib.sha256(image).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
