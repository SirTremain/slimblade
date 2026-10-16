#!/usr/bin/env python3
"""Offline analysis setup. Downloads archives; never executes the updater.

Only Python's standard library plus unzip/tar (to preserve tool permissions).
Existing files must match their pins; never replace a mismatched artifact.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import urllib.request
import zipfile


HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked(data, pin):
    if len(data) != pin["bytes"] or digest(data) != pin["sha256"]:
        raise ValueError("Artifact size/hash mismatch")
    return data


def save_new_or_identical(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"Refusing to overwrite {path}")
    else:
        path.write_bytes(data)


def extract_firmware(exe, baseline):
    # CLR embedded resources are length-prefixed. Locate the known size, then
    # require exactly one candidate matching the immutable full-resource hash.
    # This is a baseline-specific extractor, not a general .NET metadata parser.
    length = struct.pack("<I", baseline["bytes"])
    candidates = []
    pos = 0
    while (pos := exe.find(length, pos)) != -1:
        start = pos + 4
        candidate = exe[start:start + baseline["bytes"]]
        if digest(candidate) == baseline["sha256"]:
            candidates.append((start, checked(candidate, baseline)))
        pos += 1
    if len(candidates) != 1:
        raise ValueError(f"Expected one hash-verified resource, got {len(candidates)}")
    return candidates[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    args = parser.parse_args()
    state = args.state.resolve()
    pins = json.loads((HERE / "artifacts.json").read_text())
    baseline = json.loads(args.baseline.read_text())
    for name in ("downloads", "tools", "stock", "ghidra", "evidence", "research"):
        (state / name).mkdir(parents=True, exist_ok=True)
    records = []
    for name in ("ghidra", "java", "firmware_zip"):
        pin = pins[name]
        dest = state / "downloads" / pin["url"].rsplit("/", 1)[-1]
        if not dest.exists():
            # No execution until complete download and hash verification.
            with urllib.request.urlopen(pin["url"], timeout=120) as response:
                data = checked(response.read(), pin)
            dest.write_bytes(data)
        checked(dest.read_bytes(), pin)
        records.append({"artifact": name, "source_url": pin["url"],
                        "bytes": pin["bytes"], "sha256": pin["sha256"],
                        "local_file_mtime_utc": datetime.datetime.fromtimestamp(
                            dest.stat().st_mtime, datetime.timezone.utc).isoformat()})
        if "directory" in pin and not (state / "tools" / pin["directory"]).exists():
            cmd = (["unzip", "-q", str(dest), "-d", str(state / "tools")]
                   if name == "ghidra" else
                   ["tar", "-xzf", str(dest), "-C", str(state / "tools")])
            subprocess.run(cmd, check=True)
    with zipfile.ZipFile(state / "downloads" / pins["firmware_zip"]["url"].rsplit("/", 1)[-1]) as archive:
        exe = checked(archive.read(pins["updater"]["member"]), pins["updater"])
    offset, firmware = extract_firmware(exe, baseline)
    payload = firmware[baseline["payload_offset"]:]
    checked(payload, {"bytes": baseline["payload_bytes"], "sha256": baseline["payload_sha256"]})
    save_new_or_identical(state / "stock" / "updater.exe", exe)
    save_new_or_identical(state / "stock" / "stock-v4.49.bin", firmware)
    save_new_or_identical(state / "stock" / "payload-v4.49.bin", payload)
    for name, data, extra in (
        ("updater", exe, {"zip_member": pins["updater"]["member"]}),
        ("firmware", firmware, {"exe_offset": hex(offset)}),
        ("payload", payload, {"container_offset": hex(baseline["payload_offset"])}),
    ):
        records.append({"artifact": name, "source_url": baseline["source_url"],
                        "bytes": len(data), "sha256": digest(data), **extra})
    manifest = {"verified_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "records": records}
    # Keep the first acquisition record when rerunning setup.
    manifest_path = state / "acquisition.json"
    if not manifest_path.exists():
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
