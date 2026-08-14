#!/usr/bin/env python3
"""Build the exact-hash stock-derived staged recovery carrier image."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import struct
import sys

from firmware_image import (
    APPLICATION_HEADER_OFFSET,
    OFFICIAL_V449_SHA256,
    OFFICIAL_V449_SIZE,
    STACK_HEADER_OFFSET,
    V449_BCD_DEVICE_OFFSET,
    refresh_header_crc,
)


CARRIER_ADDRESS = 0x21AC
CARRIER_LIMIT = 0x2300
DISPATCH_BRANCHES = {
    0x18F9A: bytes.fromhex("0ed0"),  # command 0x0e -> shared call site
    0x18FAE: bytes.fromhex("04d0"),  # command 0x0f -> shared call site
    0x18FB2: bytes.fromhex("02d0"),  # command 0x10 -> shared call site
}
DISPATCH_CALL = 0x18FBA


def thumb_bl(source: int, target: int) -> bytes:
    """Encode an ARMv5 Thumb BL from source to an even target address."""
    if source & 1 or target & 1:
        raise ValueError("Thumb BL source and target must be even")
    delta = target - (source + 4)
    if delta & 1 or not -(1 << 22) <= delta < (1 << 22):
        raise ValueError("Thumb BL target is out of range")
    high = 0xF000 | ((delta >> 12) & 0x7FF)
    low = 0xF800 | ((delta >> 1) & 0x7FF)
    return struct.pack("<HH", high, low)


def make_recovery_carrier(stock: bytes, code: bytes) -> bytes:
    digest = hashlib.sha256(stock).hexdigest()
    if len(stock) != OFFICIAL_V449_SIZE or digest != OFFICIAL_V449_SHA256:
        raise ValueError(
            "input is not the recorded official v4.49 image: "
            f"size={len(stock)}, sha256={digest}"
        )
    if not code:
        raise ValueError("carrier code is empty")
    if CARRIER_ADDRESS + len(code) > CARRIER_LIMIT:
        raise ValueError(
            f"carrier code ends at {CARRIER_ADDRESS + len(code):#x}, beyond {CARRIER_LIMIT:#x}"
        )
    stock_gap = stock[CARRIER_ADDRESS:CARRIER_LIMIT]
    if stock_gap != b"\0" * len(stock_gap):
        raise ValueError("recorded stock carrier region is not entirely zero-filled")

    image = bytearray(stock)
    image[CARRIER_ADDRESS : CARRIER_ADDRESS + len(code)] = code
    for offset, branch in DISPATCH_BRANCHES.items():
        image[offset : offset + len(branch)] = branch
    image[DISPATCH_CALL : DISPATCH_CALL + 4] = thumb_bl(
        DISPATCH_CALL, CARRIER_ADDRESS
    )
    image[V449_BCD_DEVICE_OFFSET] = 0x51
    refresh_header_crc(image, APPLICATION_HEADER_OFFSET)
    refresh_header_crc(image, STACK_HEADER_OFFSET)
    return bytes(image)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stock", type=Path)
    parser.add_argument("code", type=Path)
    parser.add_argument("output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        image = make_recovery_carrier(args.stock.read_bytes(), args.code.read_bytes())
        args.output.write_bytes(image)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(f"wrote {len(image)} bytes; sha256={hashlib.sha256(image).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
