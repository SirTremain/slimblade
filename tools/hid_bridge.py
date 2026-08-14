#!/usr/bin/env python3
"""Read-only hidraw bridge for the SlimBlade research environment.

The device node is visible in the user's host shell but not in the agent's
mount namespace. This process opens hidraw read-only and exposes a deliberately
small JSON-over-UNIX-socket interface. There is no HID write or SET_FEATURE
operation in this program.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import selectors
import socket
import struct
import sys
import time
from typing import Any


REPORT_DESCRIPTOR_MAX = 4096
DEFAULT_SOCKET = Path(__file__).resolve().parent.parent / ".slimblade-hid.sock"


def _ior(type_char: str, number: int, size: int) -> int:
    return (2 << 30) | (size << 16) | (ord(type_char) << 8) | number


HIDIOCGRDESCSIZE = _ior("H", 0x01, 4)
HIDIOCGRDESC = _ior("H", 0x02, 4 + REPORT_DESCRIPTOR_MAX)
HIDIOCGRAWINFO = _ior("H", 0x03, 8)


def _hidiocgrawname(size: int) -> int:
    return _ior("H", 0x04, size)


def get_identity(fd: int) -> dict[str, Any]:
    raw_info = bytearray(8)
    fcntl.ioctl(fd, HIDIOCGRAWINFO, raw_info, True)
    bus, vendor, product = struct.unpack("IHH", raw_info)

    raw_name = bytearray(256)
    fcntl.ioctl(fd, _hidiocgrawname(len(raw_name)), raw_name, True)
    name = raw_name.split(b"\0", 1)[0].decode("utf-8", errors="replace")
    return {"bus": bus, "vendor": vendor, "product": product, "name": name}


def get_report_descriptor(fd: int) -> bytes:
    size_buffer = bytearray(4)
    fcntl.ioctl(fd, HIDIOCGRDESCSIZE, size_buffer, True)
    (size,) = struct.unpack("I", size_buffer)
    if not 0 <= size <= REPORT_DESCRIPTOR_MAX:
        raise RuntimeError(f"kernel returned invalid report descriptor size {size}")

    descriptor_buffer = bytearray(4 + REPORT_DESCRIPTOR_MAX)
    struct.pack_into("I", descriptor_buffer, 0, size)
    fcntl.ioctl(fd, HIDIOCGRDESC, descriptor_buffer, True)
    (returned_size,) = struct.unpack_from("I", descriptor_buffer, 0)
    if returned_size > REPORT_DESCRIPTOR_MAX:
        raise RuntimeError(
            f"kernel returned invalid report descriptor size {returned_size}"
        )
    return bytes(descriptor_buffer[4 : 4 + returned_size])


def read_reports(fd: int, timeout: float, limit: int) -> list[dict[str, Any]]:
    selector = selectors.DefaultSelector()
    selector.register(fd, selectors.EVENT_READ)
    deadline = time.monotonic() + timeout
    reports: list[dict[str, Any]] = []
    try:
        while len(reports) < limit:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            if not selector.select(remaining):
                break
            try:
                report = os.read(fd, REPORT_DESCRIPTOR_MAX)
            except BlockingIOError:
                continue
            if not report:
                break
            reports.append(
                {
                    "monotonic_ns": time.monotonic_ns(),
                    "length": len(report),
                    "hex": report.hex(),
                }
            )
    finally:
        selector.close()
    return reports


def handle_request(fd: int, request: dict[str, Any]) -> dict[str, Any]:
    operation = request.get("operation")
    if operation == "info":
        return {"ok": True, "identity": get_identity(fd)}
    if operation == "descriptor":
        descriptor = get_report_descriptor(fd)
        return {"ok": True, "length": len(descriptor), "hex": descriptor.hex()}
    if operation == "read":
        timeout = min(max(float(request.get("timeout", 1.0)), 0.0), 10.0)
        limit = min(max(int(request.get("limit", 32)), 1), 1024)
        return {"ok": True, "reports": read_reports(fd, timeout, limit)}
    return {"ok": False, "error": f"unsupported operation: {operation!r}"}


def serve(device: Path, socket_path: Path) -> int:
    if socket_path.exists() or socket_path.is_socket():
        print(f"refusing to replace existing socket: {socket_path}", file=sys.stderr)
        return 2

    try:
        fd = os.open(device, os.O_RDONLY | os.O_NONBLOCK)
    except OSError as error:
        print(f"cannot open {device} read-only: {error}", file=sys.stderr)
        return 1

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        server.bind(str(socket_path))
        os.chmod(socket_path, 0o600)
        server.listen(4)
        identity = get_identity(fd)
        print(
            f"ready: {identity['vendor']:04x}:{identity['product']:04x} "
            f"{identity['name']} via {socket_path}",
            flush=True,
        )
        while True:
            connection, _ = server.accept()
            with connection, connection.makefile("rwb") as stream:
                line = stream.readline(65537)
                if not line or len(line) > 65536:
                    continue
                try:
                    request = json.loads(line)
                    response = handle_request(fd, request)
                except Exception as error:  # Return diagnostics to the local client.
                    response = {"ok": False, "error": str(error)}
                stream.write(json.dumps(response, sort_keys=True).encode() + b"\n")
                stream.flush()
    except KeyboardInterrupt:
        return 0
    finally:
        server.close()
        os.close(fd)
        try:
            socket_path.unlink()
        except FileNotFoundError:
            pass


def request(socket_path: Path, payload: dict[str, Any]) -> int:
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.connect(str(socket_path))
        with client.makefile("rwb") as stream:
            stream.write(json.dumps(payload).encode() + b"\n")
            stream.flush()
            response = json.loads(stream.readline(1_000_000))
    finally:
        client.close()
    print(json.dumps(response, indent=2, sort_keys=True))
    return 0 if response.get("ok") else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", type=Path, default=DEFAULT_SOCKET)
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve_parser = subparsers.add_parser("serve", help="start the read-only bridge")
    serve_parser.add_argument("--device", type=Path, default=Path("/dev/hidraw4"))

    subparsers.add_parser("info", help="read the hidraw identity")
    subparsers.add_parser("descriptor", help="read the HID report descriptor")
    read_parser = subparsers.add_parser("read", help="read queued input reports")
    read_parser.add_argument("--timeout", type=float, default=1.0)
    read_parser.add_argument("--limit", type=int, default=32)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "serve":
        return serve(args.device, args.socket)
    payload: dict[str, Any] = {"operation": args.command}
    if args.command == "read":
        payload.update(timeout=args.timeout, limit=args.limit)
    return request(args.socket, payload)


if __name__ == "__main__":
    raise SystemExit(main())
