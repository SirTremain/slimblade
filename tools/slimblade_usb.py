#!/usr/bin/env python3
"""Inspect a SlimBlade Pro HID interface and flash hash-locked images.

The default ``identify`` command opens hidraw read-only. Commands that transmit
require an explicit confirmation or exact hash. Firmware commands accept only
recorded, exact-hash images.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import sys
import time
from typing import Any
import zlib

from hid_bridge import get_identity, get_report_descriptor


KENSINGTON_VENDOR_ID = 0x047D
SLIMBLADE_PRO_WIRED_PRODUCT_ID = 0x80D7
BOOT_IDENTITIES = {(0x25A7, 0xFABE), (0x3554, 0xF600), (0x3554, 0xF800)}
OFFICIAL_V449_SIZE = 128_112
OFFICIAL_V449_SHA256 = (
    "e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7"
)
OFFICIAL_V449_PAYLOAD_OFFSET = 0x2000
OFFICIAL_V449_PAYLOAD_SIZE = 119_920
OFFICIAL_V449_PAYLOAD_SHA256 = (
    "3b7849cafa2a8d4a0c2694c9771d70563563dc1c6cdbf84ede9b8648071604bf"
)
OFFICIAL_V449_PAYLOAD_CRC = 0xDD0FE246
V449_PROBE_SIZE = 128_112
V449_PROBE_SHA256 = (
    "990079b8a71668f0e19963c71a70f8efac3f36e69a21133d60f9951cd8519081"
)
V449_PROBE_PAYLOAD_SIZE = 119_920
V449_PROBE_PAYLOAD_SHA256 = (
    "46520d851e5c908500e89f48fc05880c60fc43fb17367aeb6c109b3f0ce3ee88"
)
V449_PROBE_PAYLOAD_CRC = 0xBE3FEDCE
RECOVERY_CARRIER_SIZE = 128_112
RECOVERY_CARRIER_SHA256 = (
    "e555d5e17edc84cb8799d035d6193f6f664c1df9116bcba3c49faef1609221e8"
)
RECOVERY_CARRIER_PAYLOAD_SIZE = 119_920
RECOVERY_CARRIER_PAYLOAD_SHA256 = (
    "aac81065cc171f263d54c4bb64019bd2fa250d032640fcd7415fbb4caf8b2899"
)
RECOVERY_CARRIER_PAYLOAD_CRC = 0xCBD4F74B
RECOVERY_CARRIER_BCD_DEVICE = "0451"
RESET_TRAMPOLINE_SIZE = 128_112
RESET_TRAMPOLINE_SHA256 = (
    "bad4a3a7bdf3610e8b6cf0d9b1bb27f4d147ffa0efb242f24c0257bb454c6905"
)
RESET_TRAMPOLINE_PAYLOAD_SIZE = 119_920
RESET_TRAMPOLINE_PAYLOAD_SHA256 = (
    "0bae1c229db988c03f6eb55b78a726d69fdf1f42048694a404335f00b950028a"
)
RESET_TRAMPOLINE_PAYLOAD_CRC = 0xDB034CD6
RESET_TRAMPOLINE_BCD_DEVICE = "0452"
RECOVERY_STUB_SIZE = 128_112
RECOVERY_STUB_SHA256 = (
    "34daf13778a79034cc3a35917fbe6cfacc0b2f93db650e50f1f4df98ecf7e618"
)
RECOVERY_STUB_PAYLOAD_SIZE = 119_920
RECOVERY_STUB_PAYLOAD_SHA256 = (
    "67415f19bf43ea3f91fe1ec223bad5c69d3e6975cf42aba60219a8bfd1457ea6"
)
RECOVERY_STUB_PAYLOAD_CRC = 0x6E473ED7
STARTUP_TRAMPOLINE_SIZE = 128_112
STARTUP_TRAMPOLINE_SHA256 = (
    "dccea5665710e9aebe039a83d49d07a1a0b32efc3826c7367814f5512ececa7b"
)
STARTUP_TRAMPOLINE_PAYLOAD_SIZE = 119_920
STARTUP_TRAMPOLINE_PAYLOAD_SHA256 = (
    "da04628aa7e05ee253b63a4984b2ceb138d91029f239f11efd6914b0da9afc8a"
)
STARTUP_TRAMPOLINE_PAYLOAD_CRC = 0x4E9C5E53
STARTUP_TRAMPOLINE_BCD_DEVICE = "0453"
BOOT_REPORT_LENGTH = 49
BOOT_REPORT_ID = 0x06
NORMAL_REPORT_LENGTH = 17
NORMAL_REPORT_ID = 0x08


def checksum(packet: bytes | bytearray) -> int:
    """Return the updater's one-byte checksum for a zeroed checksum slot."""
    return (0x55 - sum(packet)) & 0xFF


def normal_command_packet(command: int) -> bytes:
    if not 0 <= command <= 0xFF:
        raise ValueError("normal command must fit in one byte")
    packet = bytearray(NORMAL_REPORT_LENGTH)
    packet[0] = NORMAL_REPORT_ID
    packet[1] = command
    packet[-1] = checksum(packet)
    return bytes(packet)


def normal_reset_packet() -> bytes:
    return normal_command_packet(0x0D)


def boot_reset_packet() -> bytes:
    packet = bytearray(49)
    packet[0] = 0x06  # Bootloader vendor report ID.
    packet[1] = 0x0D  # Reset command.
    packet[-1] = checksum(packet)
    return bytes(packet)


def boot_query_packet() -> bytes:
    packet = bytearray(49)
    packet[0] = 0x06  # Bootloader vendor report ID.
    packet[1] = 0xB2  # Query loader/device type.
    packet[-1] = checksum(packet)
    return bytes(packet)


def updater_crc32(payload: bytes) -> int:
    """Return the BK3635 updater CRC (initial all-ones, no final XOR)."""
    return zlib.crc32(payload) ^ 0xFFFFFFFF


def prepare_download_packet(payload: bytes) -> bytes:
    packet = bytearray(BOOT_REPORT_LENGTH)
    packet[0] = BOOT_REPORT_ID
    packet[1] = 0xB0
    packet[5:9] = len(payload).to_bytes(4, "big")
    packet[9:13] = updater_crc32(payload).to_bytes(4, "big")
    return bytes(packet)


def download_packet(payload: bytes, offset: int) -> bytes:
    if offset < 0 or offset >= len(payload):
        raise ValueError("payload offset is outside the image")
    data = payload[offset : offset + 32]
    final = offset + len(data) == len(payload)
    packet = bytearray(BOOT_REPORT_LENGTH)
    packet[0] = BOOT_REPORT_ID
    packet[1] = 0xB1
    packet[2] = 0xC1 if final else 0xC0
    packet[3] = len(data)
    address = OFFICIAL_V449_PAYLOAD_OFFSET + offset
    packet[5:9] = address.to_bytes(4, "big")
    packet[17:49] = b"\xff" * 32
    packet[17 : 17 + len(data)] = data
    return bytes(packet)


def load_official_v449(path: Path) -> bytes:
    image = path.read_bytes()
    digest = hashlib.sha256(image).hexdigest()
    if len(image) != OFFICIAL_V449_SIZE or digest != OFFICIAL_V449_SHA256:
        raise ValueError(
            "firmware is not the recorded official v4.49 image: "
            f"size={len(image)}, sha256={digest}"
        )
    payload = image[OFFICIAL_V449_PAYLOAD_OFFSET:]
    payload_digest = hashlib.sha256(payload).hexdigest()
    payload_crc = updater_crc32(payload)
    if (
        len(payload) != OFFICIAL_V449_PAYLOAD_SIZE
        or payload_digest != OFFICIAL_V449_PAYLOAD_SHA256
        or payload_crc != OFFICIAL_V449_PAYLOAD_CRC
    ):
        raise ValueError("official v4.49 application payload validation failed")
    return payload


def load_v449_descriptor_probe(path: Path) -> bytes:
    image = path.read_bytes()
    digest = hashlib.sha256(image).hexdigest()
    if len(image) != V449_PROBE_SIZE or digest != V449_PROBE_SHA256:
        raise ValueError(
            "firmware is not the recorded v4.50 descriptor probe: "
            f"size={len(image)}, sha256={digest}"
        )
    payload = image[OFFICIAL_V449_PAYLOAD_OFFSET:]
    payload_digest = hashlib.sha256(payload).hexdigest()
    payload_crc = updater_crc32(payload)
    if (
        len(payload) != V449_PROBE_PAYLOAD_SIZE
        or payload_digest != V449_PROBE_PAYLOAD_SHA256
        or payload_crc != V449_PROBE_PAYLOAD_CRC
    ):
        raise ValueError("v4.50 descriptor-probe payload validation failed")
    return payload


def load_recovery_carrier(path: Path) -> bytes:
    image = path.read_bytes()
    digest = hashlib.sha256(image).hexdigest()
    if len(image) != RECOVERY_CARRIER_SIZE or digest != RECOVERY_CARRIER_SHA256:
        raise ValueError(
            "firmware is not the recorded stock recovery carrier: "
            f"size={len(image)}, sha256={digest}"
        )
    payload = image[OFFICIAL_V449_PAYLOAD_OFFSET:]
    payload_digest = hashlib.sha256(payload).hexdigest()
    payload_crc = updater_crc32(payload)
    if (
        len(payload) != RECOVERY_CARRIER_PAYLOAD_SIZE
        or payload_digest != RECOVERY_CARRIER_PAYLOAD_SHA256
        or payload_crc != RECOVERY_CARRIER_PAYLOAD_CRC
    ):
        raise ValueError("stock recovery-carrier payload validation failed")
    return payload


def load_reset_trampoline(path: Path) -> bytes:
    image = path.read_bytes()
    digest = hashlib.sha256(image).hexdigest()
    if len(image) != RESET_TRAMPOLINE_SIZE or digest != RESET_TRAMPOLINE_SHA256:
        raise ValueError(
            "firmware is not the recorded stock reset trampoline: "
            f"size={len(image)}, sha256={digest}"
        )
    payload = image[OFFICIAL_V449_PAYLOAD_OFFSET:]
    payload_digest = hashlib.sha256(payload).hexdigest()
    payload_crc = updater_crc32(payload)
    if (
        len(payload) != RESET_TRAMPOLINE_PAYLOAD_SIZE
        or payload_digest != RESET_TRAMPOLINE_PAYLOAD_SHA256
        or payload_crc != RESET_TRAMPOLINE_PAYLOAD_CRC
    ):
        raise ValueError("stock reset-trampoline payload validation failed")
    return payload


def load_recovery_stub(path: Path) -> bytes:
    image = path.read_bytes()
    digest = hashlib.sha256(image).hexdigest()
    if len(image) != RECOVERY_STUB_SIZE or digest != RECOVERY_STUB_SHA256:
        raise ValueError(
            "firmware is not the recorded standalone recovery stub: "
            f"size={len(image)}, sha256={digest}"
        )
    payload = image[OFFICIAL_V449_PAYLOAD_OFFSET:]
    payload_digest = hashlib.sha256(payload).hexdigest()
    payload_crc = updater_crc32(payload)
    if (
        len(payload) != RECOVERY_STUB_PAYLOAD_SIZE
        or payload_digest != RECOVERY_STUB_PAYLOAD_SHA256
        or payload_crc != RECOVERY_STUB_PAYLOAD_CRC
    ):
        raise ValueError("standalone recovery-stub payload validation failed")
    return payload


def load_startup_trampoline(path: Path) -> bytes:
    image = path.read_bytes()
    digest = hashlib.sha256(image).hexdigest()
    if len(image) != STARTUP_TRAMPOLINE_SIZE or digest != STARTUP_TRAMPOLINE_SHA256:
        raise ValueError(
            "firmware is not the recorded stock startup trampoline: "
            f"size={len(image)}, sha256={digest}"
        )
    payload = image[OFFICIAL_V449_PAYLOAD_OFFSET:]
    payload_digest = hashlib.sha256(payload).hexdigest()
    payload_crc = updater_crc32(payload)
    if (
        len(payload) != STARTUP_TRAMPOLINE_PAYLOAD_SIZE
        or payload_digest != STARTUP_TRAMPOLINE_PAYLOAD_SHA256
        or payload_crc != STARTUP_TRAMPOLINE_PAYLOAD_CRC
    ):
        raise ValueError("stock startup-trampoline payload validation failed")
    return payload


def identity_dict(device: Path) -> dict[str, Any]:
    fd = os.open(device, os.O_RDONLY | os.O_NONBLOCK)
    try:
        identity = get_identity(fd)
        descriptor = get_report_descriptor(fd)
    finally:
        os.close(fd)
    return {
        "device": str(device),
        "identity": identity,
        "report_descriptor_length": len(descriptor),
        "report_descriptor_hex": descriptor.hex(),
    }


def usb_identity_from_directory(directory: Path) -> dict[str, str | int] | None:
    vendor_path = directory / "idVendor"
    product_path = directory / "idProduct"
    if not vendor_path.is_file() or not product_path.is_file():
        return None
    try:
        vendor = int(vendor_path.read_text().strip(), 16)
        product = int(product_path.read_text().strip(), 16)
    except (OSError, ValueError):
        return None

    values: dict[str, str | int] = {
        "sysfs": str(directory.resolve()),
        "vendor": vendor,
        "product": product,
    }
    for key, filename in (
        ("name", "product"),
        ("bcd_device", "bcdDevice"),
        ("devnum", "devnum"),
    ):
        try:
            values[key] = (directory / filename).read_text().strip()
        except OSError:
            values[key] = ""
    return values


def sysfs_usb_identities() -> list[dict[str, str | int]]:
    devices: list[dict[str, str | int]] = []
    for directory in Path("/sys/bus/usb/devices").glob("*"):
        identity = usb_identity_from_directory(directory)
        if identity is not None:
            devices.append(identity)
    return devices


def usb_identity_for_hidraw(device: Path) -> dict[str, str | int] | None:
    """Return the USB parent identity for this exact hidraw node."""
    try:
        actual_device = device.resolve(strict=True)
        hidraw_device = Path("/sys/class/hidraw") / actual_device.name / "device"
        resolved = hidraw_device.resolve(strict=True)
    except OSError:
        return None
    for directory in (resolved, *resolved.parents):
        identity = usb_identity_from_directory(directory)
        if identity is not None:
            return identity
    return None


def loader_candidate_paths(preferred: Path) -> list[Path]:
    """Return current hidraw nodes, preferring the requested/stable loader path."""
    requested = [preferred, Path("/dev/slimblade-loader")]
    requested.extend(sorted(Path("/dev").glob("hidraw*")))
    candidates: list[Path] = []
    seen: set[str] = set()
    for path in requested:
        try:
            resolved = path.resolve(strict=True)
        except OSError:
            continue
        if not resolved.name.startswith("hidraw"):
            continue
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(resolved)
    return candidates


def open_queried_loader_candidate(
    device: Path, query_timeout: float
) -> tuple[
    Path,
    tuple[int, int],
    dict[str, str | int],
    int,
    selectors.BaseSelector,
] | None:
    """Open a loader and prove BK3635 type d2 without issuing an erase."""
    details = identity_dict(device)
    identity = details["identity"]
    actual = (int(identity["vendor"]), int(identity["product"]))
    if actual not in BOOT_IDENTITIES:
        return None
    boot_usb_identity = usb_identity_for_hidraw(device)
    if boot_usb_identity is None:
        raise OSError(f"could not resolve the USB parent of {device}")
    parent_actual = (
        int(boot_usb_identity["vendor"]),
        int(boot_usb_identity["product"]),
    )
    if parent_actual != actual:
        raise ValueError("hidraw loader identity and USB parent disagree")

    fd = os.open(device, os.O_RDWR)
    selector = selectors.DefaultSelector()
    try:
        selector.register(fd, selectors.EVENT_READ)
        write_report(fd, boot_query_packet())
        response = read_boot_report(fd, selector, query_timeout)
        if response is None:
            raise TimeoutError("loader disappeared or did not answer B2")
        if response[1] != 0xB2 or response[2] != 0xD2:
            raise ValueError("loader returned an unexpected B2 device type")
    except BaseException:
        selector.close()
        os.close(fd)
        raise
    return device, actual, boot_usb_identity, fd, selector


def wait_for_queried_loader(
    preferred: Path, timeout: float
) -> tuple[
    Path,
    tuple[int, int],
    dict[str, str | int],
    int,
    selectors.BaseSelector,
]:
    """Retry loader discovery/B2 only while no erase has been attempted."""
    deadline = time.monotonic() + timeout
    last_error = "no recognized loader hidraw node appeared"
    while time.monotonic() < deadline:
        for candidate in loader_candidate_paths(preferred):
            try:
                session = open_queried_loader_candidate(
                    candidate, min(1.0, max(0.05, deadline - time.monotonic()))
                )
            except OSError as error:
                last_error = str(error)
                continue
            if session is not None:
                return session
        time.sleep(0.05)
    raise RuntimeError(f"loader unavailable before erase: {last_error}")


def wait_for_boot_identity(timeout: float) -> dict[str, str | int] | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for device in sysfs_usb_identities():
            identity = (int(device["vendor"]), int(device["product"]))
            if identity in BOOT_IDENTITIES:
                return device
        time.sleep(0.05)
    return None


def wait_for_identity(
    expected: tuple[int, int], timeout: float
) -> dict[str, str | int] | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for device in sysfs_usb_identities():
            identity = (int(device["vendor"]), int(device["product"]))
            if identity == expected:
                return device
        time.sleep(0.05)
    return None


def wait_for_identity_at_path(
    sysfs_path: str | int, expected: tuple[int, int], timeout: float
) -> dict[str, str | int] | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for device in sysfs_usb_identities():
            identity = (int(device["vendor"]), int(device["product"]))
            if device["sysfs"] == sysfs_path and identity == expected:
                return device
        time.sleep(0.05)
    return None


def require_recovery_carrier(device: Path) -> dict[str, str | int]:
    details = identity_dict(device)
    hid_identity = details["identity"]
    actual = (hid_identity["vendor"], hid_identity["product"])
    expected = (KENSINGTON_VENDOR_ID, SLIMBLADE_PRO_WIRED_PRODUCT_ID)
    if actual != expected:
        raise ValueError(
            f"{device} is {actual[0]:04x}:{actual[1]:04x}, "
            f"expected {expected[0]:04x}:{expected[1]:04x}"
        )

    usb_identity = usb_identity_for_hidraw(device)
    if usb_identity is None:
        raise ValueError(f"could not resolve the USB parent of {device}")
    parent_actual = (
        int(usb_identity["vendor"]),
        int(usb_identity["product"]),
    )
    if parent_actual != expected:
        raise ValueError(
            "hidraw and USB-parent identities disagree: "
            f"{parent_actual[0]:04x}:{parent_actual[1]:04x}"
        )
    if usb_identity.get("bcd_device") != RECOVERY_CARRIER_BCD_DEVICE:
        raise ValueError(
            f"{device} has bcdDevice={usb_identity.get('bcd_device')!r}, "
            f"expected recovery carrier {RECOVERY_CARRIER_BCD_DEVICE}"
        )
    return usb_identity


def read_normal_command_response(
    fd: int,
    selector: selectors.BaseSelector,
    command: int,
    timeout: float,
) -> bytes | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        events = selector.select(max(0.0, deadline - time.monotonic()))
        if not events:
            return None
        report = os.read(fd, 4096)
        if (
            len(report) == NORMAL_REPORT_LENGTH
            and report[0] == NORMAL_REPORT_ID
            and report[1] == command
            and sum(report) & 0xFF == 0x55
        ):
            return report
    return None


def wait_for_carrier_reenumeration(
    previous: dict[str, str | int], timeout: float
) -> dict[str, str | int] | None:
    expected = (KENSINGTON_VENDOR_ID, SLIMBLADE_PRO_WIRED_PRODUCT_ID)
    previous_path = previous["sysfs"]
    previous_devnum = previous.get("devnum")
    saw_absence = False
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current = {
            item["sysfs"]: item
            for item in sysfs_usb_identities()
            if (int(item["vendor"]), int(item["product"])) == expected
            and item.get("bcd_device") == RECOVERY_CARRIER_BCD_DEVICE
        }
        same_port = current.get(previous_path)
        if same_port is None:
            saw_absence = True
        elif saw_absence or same_port.get("devnum") != previous_devnum:
            return same_port
        time.sleep(0.05)
    return None


def wait_for_boot_identity_at_path(
    sysfs_path: str | int, timeout: float
) -> dict[str, str | int] | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for device in sysfs_usb_identities():
            identity = (int(device["vendor"]), int(device["product"]))
            if device["sysfs"] == sysfs_path and identity in BOOT_IDENTITIES:
                return device
        time.sleep(0.05)
    return None


def wait_for_boot_reenumeration(
    previous: dict[str, str | int], timeout: float
) -> dict[str, str | int] | None:
    """Require a new loader enumeration, not the pre-flash loader instance."""
    previous_path = previous["sysfs"]
    previous_devnum = previous.get("devnum")
    saw_absence = False
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        same_path = None
        for device in sysfs_usb_identities():
            identity = (int(device["vendor"]), int(device["product"]))
            if device["sysfs"] == previous_path and identity in BOOT_IDENTITIES:
                same_path = device
                break
        if same_path is None:
            saw_absence = True
        elif saw_absence or same_path.get("devnum") != previous_devnum:
            return same_path
        time.sleep(0.05)
    return None


def enter_loader(device: Path, timeout: float) -> int:
    details = identity_dict(device)
    identity = details["identity"]
    actual = (identity["vendor"], identity["product"])
    expected = (KENSINGTON_VENDOR_ID, SLIMBLADE_PRO_WIRED_PRODUCT_ID)
    if actual != expected:
        print(
            f"refusing write: {device} is {actual[0]:04x}:{actual[1]:04x}, "
            f"expected {expected[0]:04x}:{expected[1]:04x}",
            file=sys.stderr,
        )
        return 2

    packet = normal_reset_packet()
    fd = os.open(device, os.O_WRONLY | os.O_NONBLOCK)
    try:
        written = os.write(fd, packet)
    finally:
        os.close(fd)
    if written != len(packet):
        print(f"short HID write: {written} of {len(packet)} bytes", file=sys.stderr)
        return 3

    result = {
        "sent_hex": packet.hex(),
        "sent_length": len(packet),
        "boot_device": wait_for_boot_identity(timeout),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["boot_device"] else 4


def reset_loader(device: Path, timeout: float) -> int:
    details = identity_dict(device)
    identity = details["identity"]
    actual = (identity["vendor"], identity["product"])
    if actual not in BOOT_IDENTITIES:
        print(
            f"refusing write: {device} is {actual[0]:04x}:{actual[1]:04x}, "
            "not a recognized boot identity",
            file=sys.stderr,
        )
        return 2

    packet = boot_reset_packet()
    fd = os.open(device, os.O_WRONLY | os.O_NONBLOCK)
    try:
        written = os.write(fd, packet)
    finally:
        os.close(fd)
    if written != len(packet):
        print(f"short HID write: {written} of {len(packet)} bytes", file=sys.stderr)
        return 3

    expected = (KENSINGTON_VENDOR_ID, SLIMBLADE_PRO_WIRED_PRODUCT_ID)
    result = {
        "sent_hex": packet.hex(),
        "sent_length": len(packet),
        "application_device": wait_for_identity(expected, timeout),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["application_device"] else 4


def query_loader(device: Path, timeout: float) -> int:
    details = identity_dict(device)
    identity = details["identity"]
    actual = (identity["vendor"], identity["product"])
    if actual not in BOOT_IDENTITIES:
        print(
            f"refusing query: {device} is {actual[0]:04x}:{actual[1]:04x}, "
            "not a recognized boot identity",
            file=sys.stderr,
        )
        return 2

    packet = boot_query_packet()
    fd = os.open(device, os.O_RDWR | os.O_NONBLOCK)
    selector = selectors.DefaultSelector()
    try:
        selector.register(fd, selectors.EVENT_READ)
        written = os.write(fd, packet)
        if written != len(packet):
            print(f"short HID write: {written} of {len(packet)} bytes", file=sys.stderr)
            return 3
        events = selector.select(timeout)
        response = os.read(fd, 4096) if events else b""
    finally:
        selector.close()
        os.close(fd)

    result = {
        "sent_hex": packet.hex(),
        "sent_length": len(packet),
        "response_hex": response.hex(),
        "response_length": len(response),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if response else 4


def read_boot_report(
    fd: int, selector: selectors.BaseSelector, timeout: float
) -> bytes | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        events = selector.select(max(0.0, deadline - time.monotonic()))
        if not events:
            return None
        report = os.read(fd, 4096)
        if len(report) == BOOT_REPORT_LENGTH and report[0] == BOOT_REPORT_ID:
            return report
    return None


def write_report(fd: int, packet: bytes) -> None:
    written = os.write(fd, packet)
    if written != len(packet):
        raise OSError(f"short HID write: {written} of {len(packet)} bytes")


def flash_application_payload(
    device: Path,
    payload: bytes,
    timeout: float,
    image_sha256: str,
    operation: str,
    expected_bcd_device: str,
    expect_loader_after_flash: bool = False,
) -> int:
    try:
        (
            selected_device,
            actual,
            boot_usb_identity,
            fd,
            selector,
        ) = wait_for_queried_loader(device, max(timeout, 8.0))
    except ValueError as error:
        print(f"refusing {operation}: {error}", file=sys.stderr)
        return 2
    except (OSError, RuntimeError) as error:
        print(
            f"{operation} did not start; no erase was attempted: {error}",
            file=sys.stderr,
        )
        return 3

    print(
        json.dumps(
            {
                "device": str(selected_device),
                "requested_device": str(device),
                "boot_identity": f"{actual[0]:04x}:{actual[1]:04x}",
                "firmware_sha256": image_sha256,
                "operation": operation,
                "payload_bytes": len(payload),
                "payload_crc": f"{updater_crc32(payload):08x}",
                "start_address": f"0x{OFFICIAL_V449_PAYLOAD_OFFSET:04x}",
            },
            sort_keys=True,
        ),
        flush=True,
    )

    try:
        print("loader query: BK3635 device type d2", flush=True)

        # This is the erase boundary. Discovery and B2 retries stop here.
        prepare = prepare_download_packet(payload)
        write_report(fd, prepare)
        saw_prepare_echo = False
        prepare_deadline = time.monotonic() + max(timeout, 15.0)
        while time.monotonic() < prepare_deadline:
            response = read_boot_report(
                fd, selector, max(0.0, prepare_deadline - time.monotonic())
            )
            if response is None:
                break
            if response[1] == 0xB0:
                saw_prepare_echo = True
                continue
            if response[1:3] == b"\x5b\xb5" and response[3] == 0x02:
                if response[4] == 0x00:
                    print("prepare/erase: started", flush=True)
                    continue
                if response[4] == 0x01:
                    break
                raise RuntimeError(
                    f"loader returned unknown erase status {response[4]:02x}"
                )
        else:
            response = None
        if not saw_prepare_echo or response is None:
            raise RuntimeError("loader did not complete prepare/erase phase")
        print("prepare/erase: accepted", flush=True)

        packet_count = (len(payload) + 31) // 32
        next_progress = 5
        for index, offset in enumerate(range(0, len(payload), 32), 1):
            packet = download_packet(payload, offset)
            write_report(fd, packet)
            echoed = None
            packet_deadline = time.monotonic() + timeout
            while time.monotonic() < packet_deadline:
                candidate = read_boot_report(
                    fd, selector, max(0.0, packet_deadline - time.monotonic())
                )
                if candidate is None:
                    break
                if candidate[1] == 0xB1:
                    echoed = candidate
                    break
            if echoed != packet:
                raise RuntimeError(
                    f"block {index}/{packet_count} was not echoed correctly"
                )
            progress = index * 100 // packet_count
            if progress >= next_progress or index == packet_count:
                print(f"write/verify: {progress}% ({index}/{packet_count})", flush=True)
                next_progress = progress + 5

        # The loader validates the whole-image CRC after the final C1 packet and
        # then resets into the application. A final 5A/A5 status can arrive first.
        print("final block echoed; waiting for application USB identity", flush=True)
    except (OSError, RuntimeError) as error:
        print(f"{operation} failed: {error}", file=sys.stderr, flush=True)
        return 3
    finally:
        selector.close()
        os.close(fd)

    if expect_loader_after_flash:
        boot_device = wait_for_boot_reenumeration(boot_usb_identity, 20.0)
        if boot_device is None:
            print(
                "stub data completed, but a known resident-loader identity "
                "did not appear on the same USB path",
                file=sys.stderr,
            )
            return 4
        print(json.dumps({"boot_device": boot_device}, sort_keys=True), flush=True)
        return 0

    expected = (KENSINGTON_VENDOR_ID, SLIMBLADE_PRO_WIRED_PRODUCT_ID)
    application = wait_for_identity_at_path(
        boot_usb_identity["sysfs"], expected, 20.0
    )
    if application is None:
        print(
            "restore data completed, but the normal 047d:80d7 identity did not appear",
            file=sys.stderr,
        )
        return 4
    if application.get("bcd_device") != expected_bcd_device:
        print(
            f"application returned with bcdDevice={application.get('bcd_device')!r}, "
            f"expected {expected_bcd_device}",
            file=sys.stderr,
        )
        return 5
    print(json.dumps({"application_device": application}, sort_keys=True), flush=True)
    return 0


def restore_official_v449(device: Path, firmware: Path, timeout: float) -> int:
    try:
        payload = load_official_v449(firmware)
    except (OSError, ValueError) as error:
        print(f"refusing restore: {error}", file=sys.stderr)
        return 2
    return flash_application_payload(
        device,
        payload,
        timeout,
        OFFICIAL_V449_SHA256,
        "official-v4.49 restore",
        "0449",
    )


def flash_v449_descriptor_probe(device: Path, firmware: Path, timeout: float) -> int:
    try:
        payload = load_v449_descriptor_probe(firmware)
    except (OSError, ValueError) as error:
        print(f"refusing probe flash: {error}", file=sys.stderr)
        return 2
    return flash_application_payload(
        device,
        payload,
        timeout,
        V449_PROBE_SHA256,
        "v4.50 descriptor-probe flash",
        "0450",
    )


def flash_recovery_carrier(device: Path, firmware: Path, timeout: float) -> int:
    try:
        payload = load_recovery_carrier(firmware)
    except (OSError, ValueError) as error:
        print(f"refusing carrier flash: {error}", file=sys.stderr)
        return 2
    return flash_application_payload(
        device,
        payload,
        timeout,
        RECOVERY_CARRIER_SHA256,
        "stock recovery-carrier flash",
        RECOVERY_CARRIER_BCD_DEVICE,
    )


def flash_reset_trampoline(device: Path, firmware: Path, timeout: float) -> int:
    try:
        payload = load_reset_trampoline(firmware)
    except (OSError, ValueError) as error:
        print(f"refusing reset-trampoline flash: {error}", file=sys.stderr)
        return 2
    return flash_application_payload(
        device,
        payload,
        timeout,
        RESET_TRAMPOLINE_SHA256,
        "stock reset-trampoline flash",
        RESET_TRAMPOLINE_BCD_DEVICE,
    )


def flash_recovery_stub(device: Path, firmware: Path, timeout: float) -> int:
    try:
        payload = load_recovery_stub(firmware)
    except (OSError, ValueError) as error:
        print(f"refusing recovery-stub flash: {error}", file=sys.stderr)
        return 2
    return flash_application_payload(
        device,
        payload,
        timeout,
        RECOVERY_STUB_SHA256,
        "standalone recovery-stub flash",
        "",
        expect_loader_after_flash=True,
    )


def flash_startup_trampoline(device: Path, firmware: Path, timeout: float) -> int:
    try:
        payload = load_startup_trampoline(firmware)
    except (OSError, ValueError) as error:
        print(f"refusing startup-trampoline flash: {error}", file=sys.stderr)
        return 2
    return flash_application_payload(
        device,
        payload,
        timeout,
        STARTUP_TRAMPOLINE_SHA256,
        "stock startup-trampoline flash",
        STARTUP_TRAMPOLINE_BCD_DEVICE,
    )


def carrier_read_probe(device: Path, timeout: float) -> int:
    try:
        usb_identity = require_recovery_carrier(device)
        packet = normal_command_packet(0x0E)
        fd = os.open(device, os.O_RDWR | os.O_NONBLOCK)
        selector = selectors.DefaultSelector()
        try:
            selector.register(fd, selectors.EVENT_READ)
            write_report(fd, packet)
            response = read_normal_command_response(fd, selector, 0x0E, timeout)
        finally:
            selector.close()
            os.close(fd)
    except (OSError, ValueError) as error:
        print(f"refusing carrier read probe: {error}", file=sys.stderr)
        return 2

    result = {
        "carrier_device": usb_identity,
        "command": "0e-read-only-mmio",
        "sent_hex": packet.hex(),
        "response_hex": response.hex() if response else "",
        "response_valid": response is not None,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if response is not None else 4


def carrier_reset_probe(device: Path, timeout: float) -> int:
    try:
        previous = require_recovery_carrier(device)
        packet = normal_command_packet(0x0F)
        fd = os.open(device, os.O_WRONLY | os.O_NONBLOCK)
        try:
            write_report(fd, packet)
        finally:
            os.close(fd)
    except (OSError, ValueError) as error:
        print(f"refusing carrier reset probe: {error}", file=sys.stderr)
        return 2

    application = wait_for_carrier_reenumeration(previous, timeout)
    print(
        json.dumps(
            {
                "command": "0f-watchdog-reset",
                "sent_hex": packet.hex(),
                "application_device": application,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if application is not None else 4


def carrier_full_recovery(device: Path, timeout: float) -> int:
    try:
        previous = require_recovery_carrier(device)
        packet = normal_command_packet(0x10)
        fd = os.open(device, os.O_WRONLY | os.O_NONBLOCK)
        try:
            write_report(fd, packet)
        finally:
            os.close(fd)
    except (OSError, ValueError) as error:
        print(f"refusing carrier full recovery: {error}", file=sys.stderr)
        return 2

    boot_device = wait_for_boot_identity_at_path(previous["sysfs"], timeout)
    print(
        json.dumps(
            {
                "command": "10-erase-marker-reset",
                "sent_hex": packet.hex(),
                "boot_device": boot_device,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if boot_device is not None else 4


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--device",
        type=Path,
        default=Path("/dev/slimblade-vendor"),
        help="hidraw path (default: stable application vendor link)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("identify", help="query identity and descriptor read-only")
    subparsers.add_parser(
        "reset-packet", help="print both reset packets without sending them"
    )
    enter = subparsers.add_parser(
        "enter-loader", help="send only the reset-to-update packet"
    )
    enter.add_argument("--timeout", type=float, default=5.0)
    enter.add_argument(
        "--confirm",
        action="store_true",
        help="required acknowledgement that this temporarily resets the mouse",
    )
    reset_parser = subparsers.add_parser(
        "reset-loader", help="send command 0x0d to reset the bootloader"
    )
    reset_parser.add_argument("--timeout", type=float, default=5.0)
    reset_parser.add_argument(
        "--confirm",
        action="store_true",
        help="required acknowledgement that this resets the bootloader",
    )
    query = subparsers.add_parser(
        "query-loader", help="send the non-writing B2 identity query"
    )
    query.add_argument("--timeout", type=float, default=2.0)
    restore = subparsers.add_parser(
        "restore-official-v449",
        help="write only the recorded official v4.49 application image",
    )
    restore.add_argument("--firmware", type=Path, required=True)
    restore.add_argument("--timeout", type=float, default=3.0)
    restore.add_argument(
        "--confirm-sha256",
        metavar="SHA256",
        help="must exactly match the recorded official image hash",
    )
    probe = subparsers.add_parser(
        "flash-v449-descriptor-probe",
        help="write only the exact hash-locked stock-derived v4.50 probe",
    )
    probe.add_argument("--firmware", type=Path, required=True)
    probe.add_argument("--timeout", type=float, default=3.0)
    probe.add_argument(
        "--confirm-sha256",
        metavar="SHA256",
        help="must exactly match the recorded descriptor-probe image hash",
    )
    carrier = subparsers.add_parser(
        "flash-recovery-carrier",
        help="write only the exact hash-locked stock recovery carrier",
    )
    carrier.add_argument("--firmware", type=Path, required=True)
    carrier.add_argument("--timeout", type=float, default=3.0)
    carrier.add_argument(
        "--confirm-sha256",
        metavar="SHA256",
        help="must exactly match the recorded recovery-carrier image hash",
    )
    trampoline = subparsers.add_parser(
        "flash-reset-trampoline",
        help="write only the exact hash-locked stock reset trampoline",
    )
    trampoline.add_argument("--firmware", type=Path, required=True)
    trampoline.add_argument("--timeout", type=float, default=3.0)
    trampoline.add_argument(
        "--confirm-sha256",
        metavar="SHA256",
        help="must exactly match the recorded reset-trampoline image hash",
    )
    stub = subparsers.add_parser(
        "flash-recovery-stub",
        help="write the exact one-shot stub and require resident-loader return",
    )
    stub.add_argument("--firmware", type=Path, required=True)
    stub.add_argument("--timeout", type=float, default=3.0)
    stub.add_argument(
        "--confirm-sha256",
        metavar="SHA256",
        help="must exactly match the recorded standalone-stub image hash",
    )
    startup = subparsers.add_parser(
        "flash-startup-trampoline",
        help="write only the exact hash-locked CPU/stack/interworking trampoline",
    )
    startup.add_argument("--firmware", type=Path, required=True)
    startup.add_argument("--timeout", type=float, default=3.0)
    startup.add_argument(
        "--confirm-sha256",
        metavar="SHA256",
        help="must exactly match the recorded startup-trampoline image hash",
    )
    carrier_read = subparsers.add_parser(
        "carrier-read-probe",
        help="send carrier command 0x0e and require its checksummed reply",
    )
    carrier_read.add_argument("--timeout", type=float, default=2.0)
    carrier_read.add_argument("--confirm", action="store_true")
    carrier_reset = subparsers.add_parser(
        "carrier-reset-probe",
        help="send carrier command 0x0f and require USB re-enumeration",
    )
    carrier_reset.add_argument("--timeout", type=float, default=5.0)
    carrier_reset.add_argument("--confirm", action="store_true")
    carrier_full = subparsers.add_parser(
        "carrier-full-recovery",
        help="send carrier command 0x10: erase, write marker, and reset",
    )
    carrier_full.add_argument("--timeout", type=float, default=8.0)
    carrier_full.add_argument(
        "--confirm-action",
        metavar="ERASE-MARKER-RESET",
        help="must be the exact displayed phrase",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "identify":
        print(json.dumps(identity_dict(args.device), indent=2, sort_keys=True))
        return 0
    if args.command == "reset-packet":
        normal_packet = normal_reset_packet()
        boot_packet = boot_reset_packet()
        print(
            json.dumps(
                {
                    "normal": {
                        "hex": normal_packet.hex(),
                        "length": len(normal_packet),
                    },
                    "boot": {"hex": boot_packet.hex(), "length": len(boot_packet)},
                    "boot_query": {
                        "hex": boot_query_packet().hex(),
                        "length": len(boot_query_packet()),
                    },
                },
                indent=2,
            )
        )
        return 0
    if args.command == "enter-loader":
        if not args.confirm:
            print("refusing write without --confirm", file=sys.stderr)
            return 2
        return enter_loader(args.device, args.timeout)
    if args.command == "reset-loader":
        if not args.confirm:
            print("refusing write without --confirm", file=sys.stderr)
            return 2
        return reset_loader(args.device, args.timeout)
    if args.command == "query-loader":
        return query_loader(args.device, args.timeout)
    if args.command == "restore-official-v449":
        if args.confirm_sha256 != OFFICIAL_V449_SHA256:
            print(
                "refusing restore without the exact --confirm-sha256 value",
                file=sys.stderr,
            )
            return 2
        return restore_official_v449(args.device, args.firmware, args.timeout)
    if args.command == "flash-v449-descriptor-probe":
        if args.confirm_sha256 != V449_PROBE_SHA256:
            print(
                "refusing probe flash without the exact --confirm-sha256 value",
                file=sys.stderr,
            )
            return 2
        return flash_v449_descriptor_probe(args.device, args.firmware, args.timeout)
    if args.command == "flash-recovery-carrier":
        if args.confirm_sha256 != RECOVERY_CARRIER_SHA256:
            print(
                "refusing carrier flash without the exact --confirm-sha256 value",
                file=sys.stderr,
            )
            return 2
        return flash_recovery_carrier(args.device, args.firmware, args.timeout)
    if args.command == "flash-reset-trampoline":
        if args.confirm_sha256 != RESET_TRAMPOLINE_SHA256:
            print(
                "refusing reset-trampoline flash without the exact "
                "--confirm-sha256 value",
                file=sys.stderr,
            )
            return 2
        return flash_reset_trampoline(args.device, args.firmware, args.timeout)
    if args.command == "flash-recovery-stub":
        if args.confirm_sha256 != RECOVERY_STUB_SHA256:
            print(
                "refusing recovery-stub flash without the exact "
                "--confirm-sha256 value",
                file=sys.stderr,
            )
            return 2
        return flash_recovery_stub(args.device, args.firmware, args.timeout)
    if args.command == "flash-startup-trampoline":
        if args.confirm_sha256 != STARTUP_TRAMPOLINE_SHA256:
            print(
                "refusing startup-trampoline flash without the exact "
                "--confirm-sha256 value",
                file=sys.stderr,
            )
            return 2
        return flash_startup_trampoline(args.device, args.firmware, args.timeout)
    if args.command == "carrier-read-probe":
        if not args.confirm:
            print("refusing carrier read probe without --confirm", file=sys.stderr)
            return 2
        return carrier_read_probe(args.device, args.timeout)
    if args.command == "carrier-reset-probe":
        if not args.confirm:
            print("refusing carrier reset probe without --confirm", file=sys.stderr)
            return 2
        return carrier_reset_probe(args.device, args.timeout)
    if args.command == "carrier-full-recovery":
        if args.confirm_action != "ERASE-MARKER-RESET":
            print(
                "refusing full recovery without "
                "--confirm-action ERASE-MARKER-RESET",
                file=sys.stderr,
            )
            return 2
        return carrier_full_recovery(args.device, args.timeout)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
