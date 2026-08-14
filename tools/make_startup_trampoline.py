#!/usr/bin/env python3
"""Build the stock-derived CPU/stack/interworking trampoline image."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

from firmware_image import (
    APPLICATION_HEADER_OFFSET,
    OFFICIAL_V449_SIZE,
    STACK_HEADER_OFFSET,
    V449_BCD_DEVICE_OFFSET,
    refresh_header_crc,
)


BASE_RESET_TRAMPOLINE_SHA256 = (
    "bad4a3a7bdf3610e8b6cf0d9b1bb27f4d147ffa0efb242f24c0257bb454c6905"
)
TRAMPOLINE_ADDRESS = 0x22B4
TRAMPOLINE_LIMIT = 0x2300
BASE_CODE = bytes.fromhex("0000a0e36affffea")


def make_startup_trampoline(base: bytes, code: bytes) -> bytes:
    digest = hashlib.sha256(base).hexdigest()
    if len(base) != OFFICIAL_V449_SIZE or digest != BASE_RESET_TRAMPOLINE_SHA256:
        raise ValueError(
            "input is not the exact audited v4.52 reset trampoline: "
            f"size={len(base)}, sha256={digest}"
        )
    if not code:
        raise ValueError("startup trampoline code is empty")
    if TRAMPOLINE_ADDRESS + len(code) > TRAMPOLINE_LIMIT:
        raise ValueError("startup trampoline overlaps the stock IRQ handler")
    if base[TRAMPOLINE_ADDRESS : TRAMPOLINE_ADDRESS + len(BASE_CODE)] != BASE_CODE:
        raise ValueError("v4.52 two-instruction trampoline changed")
    if base[TRAMPOLINE_ADDRESS + len(BASE_CODE) : TRAMPOLINE_LIMIT] != b"\0" * (
        TRAMPOLINE_LIMIT - TRAMPOLINE_ADDRESS - len(BASE_CODE)
    ):
        raise ValueError("v4.52 unused trampoline region is not zero-filled")

    image = bytearray(base)
    image[TRAMPOLINE_ADDRESS:TRAMPOLINE_LIMIT] = b"\0" * (
        TRAMPOLINE_LIMIT - TRAMPOLINE_ADDRESS
    )
    image[TRAMPOLINE_ADDRESS : TRAMPOLINE_ADDRESS + len(code)] = code
    image[V449_BCD_DEVICE_OFFSET] = 0x53
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
        image = make_startup_trampoline(
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
