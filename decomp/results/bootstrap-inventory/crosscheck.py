#!/usr/bin/env python3
"""Independent LLVM decode of reviewed anchors; no code generation for firmware."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("baseline", type=Path)
p.add_argument("firmware", type=Path)
p.add_argument("output", type=Path)
args = p.parse_args()
data = args.firmware.read_bytes()
baseline = json.loads(args.baseline.read_text())
if len(data) != baseline["bytes"] or hashlib.sha256(data).hexdigest() != baseline["sha256"]:
    raise ValueError("wrong firmware")
args.output.mkdir(parents=True, exist_ok=False)
elf = args.output / "disassembly-only.elf"
objcopy, objdump = shutil.which("llvm-objcopy"), shutil.which("llvm-objdump")
subprocess.run([objcopy, "-I", "binary", "-O", "elf32-littlearm", "--rename-section",
                ".data=.text,alloc,load,readonly,code", str(args.firmware), str(elf)], check=True)
records = []
for name, triple, start, end in (
    ("vectors", "armv5te-none-eabi", "0x2020", "0x2040"),
    ("startup", "armv5te-none-eabi", "0x2060", "0x2170"),
    ("exception-wrappers", "armv5te-none-eabi", "0x2300", "0x2330"),
    ("thumb-entry", "thumbv5te-none-eabi", "0x19878", "0x19890"),
):
    cmd = [objdump, "-D", "--triple=" + triple, "--start-address=" + start,
           "--stop-address=" + end, str(elf)]
    listing = subprocess.check_output(cmd)
    (args.output / (name + ".txt")).write_bytes(listing)
    records.append({"file": name + ".txt", "command": cmd, "sha256": hashlib.sha256(listing).hexdigest()})
tools = [{"path": path, "bytes": Path(path).stat().st_size,
          "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
          "version": subprocess.check_output([path, "--version"], text=True)}
         for path in (objcopy, objdump)]
(args.output / "manifest.json").write_text(json.dumps({"tools": tools, "records": records}, indent=2) + "\n")
print("Exported independent LLVM anchor disassembly to", args.output)
