#!/usr/bin/env python3
"""Verify the marker-first hang guard as an exact live-stub derivation."""

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
    OFFICIAL_V449_SIZE,
    beken_crc32,
    parse_header,
)
from make_recovery_guard import (
    EXPERIMENT_CODE,
    EXPERIMENT_ENTRY,
    FINAL_ACTION_CALL,
    GUARD_CODE_END,
    LIVE_STUB_CODE_END,
    LIVE_STUB_SHA256,
    make_recovery_guard,
)


AUDITED_CODE_SHA256 = (
    "93eef0420d1a54e4ca7efbfa1ca6a30e79044ff91b4294584ab062b7c6e061c0"
)
AUDITED_CONTAINER_SHA256 = (
    "7bb3055bc1575bcb9ca4eab9ba2a83a3dbaba131e92cca78fffb18397cc2d19a"
)
AUDITED_PAYLOAD_SHA256 = (
    "3c11672dca070a246202b70b743456b4b5bb32b157d2e305e2f032499e36823c"
)
EXPECTED_DIFFERENCES = [
    0x2010,
    0x2011,
    0x2012,
    0x2013,
    0x20B8,
    0x21C4,
    0x21C5,
]
PERSISTENT_CONTROLLER_START = 0x00803000
PERSISTENT_CONTROLLER_END = 0x00803100
PERSISTENT_WORD_ADDRESSES = {0x00008000, 0x0000807C, 0x0000807D}


class VerificationError(ValueError):
    """The guard differs from its audited marker-first construction."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _thumb_bl_target(image: bytes, address: int) -> int:
    _require(0 <= address <= len(image) - 4, f"no Thumb BL at {address:#x}")
    high, low = struct.unpack_from("<HH", image, address)
    _require(high & 0xF800 == 0xF000, f"bad Thumb BL first half at {address:#x}")
    _require(low & 0xF800 == 0xF800, f"bad Thumb BL second half at {address:#x}")
    delta = ((high & 0x7FF) << 12) | ((low & 0x7FF) << 1)
    if delta & (1 << 22):
        delta -= 1 << 23
    return address + 4 + delta


def verify_experiment_storage_isolation(
    image: bytes, start: int, end: int
) -> dict[str, object]:
    """Apply conservative static checks to the post-marker experiment."""
    _require(0 <= start < end <= len(image), "experimental range is invalid")
    experiment = image[start:end]

    forbidden_literals: list[tuple[int, int]] = []
    for offset in range(0, max(0, len(experiment) - 3)):
        value = struct.unpack_from("<I", experiment, offset)[0]
        if (
            PERSISTENT_CONTROLLER_START <= value < PERSISTENT_CONTROLLER_END
            or value in PERSISTENT_WORD_ADDRESSES
        ):
            forbidden_literals.append((start + offset, value))
    _require(
        not forbidden_literals,
        "experiment contains a persistent-storage controller/word address",
    )

    direct_targets: list[int] = []
    for address in range(start, end - 3, 2):
        high, low = struct.unpack_from("<HH", image, address)
        if high & 0xF800 == 0xF000 and low & 0xF800 == 0xF800:
            target = _thumb_bl_target(image, address)
            direct_targets.append(target)
            _require(
                start <= target < end,
                f"experiment calls outside its isolated range: {target:#x}",
            )

    halfwords = [
        struct.unpack_from("<H", experiment, offset)[0]
        for offset in range(0, len(experiment) - 1, 2)
    ]
    _require(
        not any(opcode & 0xFF87 == 0x4780 for opcode in halfwords),
        "experiment contains an indirect Thumb BLX",
    )
    _require(
        not any(opcode & 0xFF00 == 0xDF00 for opcode in halfwords),
        "experiment contains a Thumb software interrupt",
    )
    return {
        "range": f"0x{start:x}-0x{end:x}",
        "bytes": len(experiment),
        "persistent_address_literals": 0,
        "out_of_range_direct_calls": 0,
        "indirect_blx": 0,
        "software_interrupts": 0,
        "direct_call_targets": [f"0x{target:x}" for target in direct_targets],
    }


def verify_recovery_guard_data(
    stub: bytes, guard: bytes, code: bytes
) -> dict[str, object]:
    _require(len(stub) == OFFICIAL_V449_SIZE, "live stub size changed")
    _require(_sha256(stub) == LIVE_STUB_SHA256, "base is not the live-proven stub")
    expected_guard, expected_code = make_recovery_guard(stub)
    _require(guard == expected_guard, "guard is not the exact audited derivation")
    _require(code == expected_code, "raw guard code differs from derivation")
    _require(
        guard[APPLICATION_CODE_OFFSET:GUARD_CODE_END] == code,
        "container does not contain the supplied guard code",
    )

    differences = [
        offset for offset, pair in enumerate(zip(stub, guard)) if pair[0] != pair[1]
    ]
    _require(differences == EXPECTED_DIFFERENCES, "stub-to-guard difference set changed")
    _require(
        guard[APPLICATION_CODE_OFFSET:FINAL_ACTION_CALL]
        == stub[APPLICATION_CODE_OFFSET:FINAL_ACTION_CALL],
        "marker-first executed prefix differs from live stub",
    )
    _require(
        guard[FINAL_ACTION_CALL + 4 : LIVE_STUB_CODE_END]
        == stub[FINAL_ACTION_CALL + 4 : LIVE_STUB_CODE_END],
        "recovery support routines differ from live stub",
    )
    _require(
        _thumb_bl_target(stub, FINAL_ACTION_CALL) == 0x20FC,
        "live stub final call no longer targets watchdog reset",
    )
    _require(
        _thumb_bl_target(guard, FINAL_ACTION_CALL) == EXPERIMENT_ENTRY,
        "guard does not enter experiment after marker completion",
    )
    _require(
        guard[EXPERIMENT_ENTRY:GUARD_CODE_END] == EXPERIMENT_CODE,
        "experimental hang instruction changed",
    )
    experiment_isolation = verify_experiment_storage_isolation(
        guard, EXPERIMENT_ENTRY, GUARD_CODE_END
    )
    _require(
        guard[GUARD_CODE_END:] == b"\xff" * (len(guard) - GUARD_CODE_END),
        "bytes after guard code are not erased padding",
    )

    header = parse_header(guard, APPLICATION_HEADER_OFFSET)
    _require(header.calculate_crc(guard) == header.crc, "guard application CRC is invalid")
    code_sha = _sha256(code)
    container_sha = _sha256(guard)
    _require(code_sha == AUDITED_CODE_SHA256, "guard code differs from audited build")
    _require(
        container_sha == AUDITED_CONTAINER_SHA256,
        "guard container differs from audited build",
    )
    payload = guard[APPLICATION_PREFIX_OFFSET:]
    payload_sha = _sha256(payload)
    _require(payload_sha == AUDITED_PAYLOAD_SHA256, "guard payload hash changed")
    return {
        "result": "PASS",
        "base_stub_sha256": _sha256(stub),
        "code_bytes": len(code),
        "code_sha256": code_sha,
        "container_bytes": len(guard),
        "container_sha256": container_sha,
        "application_crc": f"{header.crc:08x}",
        "payload_bytes": len(payload),
        "payload_sha256": payload_sha,
        "payload_crc": f"{beken_crc32(payload):08x}",
        "changed_offsets": [f"0x{offset:x}" for offset in differences],
        "live_stub_final_target": "0x20fc",
        "guard_experiment_entry": f"0x{EXPERIMENT_ENTRY:x}",
        "fallback_invariant": "loader marker completes before experimental entry",
        "experiment_storage_isolation": experiment_isolation,
        "experiment": "deliberate Thumb self-loop; power cycle should enter loader",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stub", type=Path)
    parser.add_argument("guard", type=Path)
    parser.add_argument("code", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        report = verify_recovery_guard_data(
            args.stub.read_bytes(), args.guard.read_bytes(), args.code.read_bytes()
        )
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
