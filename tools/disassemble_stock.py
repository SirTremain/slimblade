#!/usr/bin/env python3
"""Disassemble a range from the exact official SlimBlade Pro v4.49 image."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


STOCK_SIZE = 128_112
STOCK_SHA256 = "e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7"


def number(value: str) -> int:
    return int(value, 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("firmware", type=Path)
    parser.add_argument("--start", type=number, required=True)
    parser.add_argument("--stop", type=number, required=True)
    parser.add_argument("--state", choices=("arm", "thumb"), required=True)
    args = parser.parse_args()

    image = args.firmware.read_bytes()
    digest = hashlib.sha256(image).hexdigest()
    if len(image) != STOCK_SIZE or digest != STOCK_SHA256:
        print("refusing image other than exact official v4.49", file=sys.stderr)
        return 2
    if not 0 <= args.start < args.stop <= len(image):
        print("invalid disassembly range", file=sys.stderr)
        return 2

    objcopy = shutil.which("llvm-objcopy")
    objdump = shutil.which("llvm-objdump")
    if objcopy is None or objdump is None:
        print("llvm-objcopy and llvm-objdump are required", file=sys.stderr)
        return 2

    triple = "armv5te-none-eabi" if args.state == "arm" else "thumbv5te-none-eabi"
    with tempfile.TemporaryDirectory(prefix="slimblade-disasm-") as directory:
        elf = Path(directory) / "v449.elf"
        subprocess.run(
            [objcopy, "-I", "binary", "-O", "elf32-littlearm", "-B", "arm", str(args.firmware), str(elf)],
            check=True,
        )
        return subprocess.run(
            [
                objdump,
                "-D",
                f"--triple={triple}",
                f"--start-address={args.start:#x}",
                f"--stop-address={args.stop:#x}",
                str(elf),
            ],
            check=False,
        ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
