#!/usr/bin/env python3
"""Derive a marker-first experimental guard from the live recovery stub."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import struct
import sys

from firmware_image import (
    APPLICATION_CODE_OFFSET,
    APPLICATION_HEADER_OFFSET,
    OFFICIAL_V449_SIZE,
    refresh_header_crc,
)


LIVE_STUB_SHA256 = (
    "34daf13778a79034cc3a35917fbe6cfacc0b2f93db650e50f1f4df98ecf7e618"
)
LIVE_STUB_CODE_END = 0x21C4
FINAL_ACTION_CALL = 0x20B6
EXPERIMENT_ENTRY = LIVE_STUB_CODE_END
EXPERIMENT_CODE = bytes.fromhex("fee7")  # Thumb `b .`: deliberate hang probe.
GUARD_CODE_END = EXPERIMENT_ENTRY + len(EXPERIMENT_CODE)


def thumb_bl(source: int, target: int) -> bytes:
    """Encode an ARMv5 two-halfword Thumb BL."""
    if source & 1 or target & 1:
        raise ValueError("Thumb BL source and target must be halfword-aligned")
    delta = target - (source + 4)
    if delta & 1 or not -(1 << 22) <= delta < (1 << 22):
        raise ValueError("Thumb BL target is out of range")
    encoded = delta & 0x7FFFFF
    return struct.pack(
        "<HH", 0xF000 | (encoded >> 12), 0xF800 | ((encoded >> 1) & 0x7FF)
    )


def make_recovery_guard(stub: bytes) -> tuple[bytes, bytes]:
    digest = hashlib.sha256(stub).hexdigest()
    if len(stub) != OFFICIAL_V449_SIZE or digest != LIVE_STUB_SHA256:
        raise ValueError(
            "input is not the exact live-proven standalone recovery stub: "
            f"size={len(stub)}, sha256={digest}"
        )
    if stub[EXPERIMENT_ENTRY:GUARD_CODE_END] != b"\xff" * len(EXPERIMENT_CODE):
        raise ValueError("experimental entry is not erased padding")

    image = bytearray(stub)
    image[FINAL_ACTION_CALL : FINAL_ACTION_CALL + 4] = thumb_bl(
        FINAL_ACTION_CALL, EXPERIMENT_ENTRY
    )
    image[EXPERIMENT_ENTRY:GUARD_CODE_END] = EXPERIMENT_CODE
    refresh_header_crc(image, APPLICATION_HEADER_OFFSET)
    code = bytes(image[APPLICATION_CODE_OFFSET:GUARD_CODE_END])
    return bytes(image), code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stub", type=Path, help="exact live-proven recovery stub")
    parser.add_argument("container", type=Path)
    parser.add_argument("code", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        container, code = make_recovery_guard(args.stub.read_bytes())
        args.container.write_bytes(container)
        args.code.write_bytes(code)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(
        f"wrote {len(code)} code bytes; "
        f"container_sha256={hashlib.sha256(container).hexdigest()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

