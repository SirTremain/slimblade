#!/usr/bin/env python3
"""Collect public toolchain evidence without running any SDK or device tools."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.error
import urllib.request

SDK_REV = "0a461f8ed4a4f17ff6889d6f9d34e521b92b8243"
HISTORY = "ea2ee1dd6f47ab414180b1b4e6ea375caef489d7"
BASE = f"https://gitee.com/beken-corp/bk3633_ble_sdk/raw/{SDK_REV}/"
FILES = ["SDK/projects/app_mouse/Makefile", "SDK/projects/app_mouse/prj3633.uvproj",
         "SDK/projects/app_2.4g/boot_usb/bk3435.uvproj",
         "SDK/src/system/peripheral_app_link.txt", "SDK/src/system/link_app.lds",
         "SDK/src/system/startup_boot.S"]
URLS = {
    "bk3633_boot.map": BASE + "SDK/projects/app_2.4g/boot_usb/lst/bk3633_boot.map",
    "clang-cross-compilation.html": "https://clang.llvm.org/docs/CrossCompilation.html",
    "arm-compiler-download-index.html": "https://support.arm.com/documentation/ka005198/1-0/?lang=en",
    "keil-legacy.html": "https://www.keil.com/download/legacy/",
    "ghidra-getting-started.md": "https://raw.githubusercontent.com/NationalSecurityAgency/ghidra/Ghidra_12.1.4_build/GhidraDocs/GettingStarted.md",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    rows = []

    def record(name, data, **metadata):
        (args.output / name).write_bytes(data)
        rows.append({"file": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                     "retrieved_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), **metadata})

    for rel in FILES:
        data = subprocess.check_output(["git", "show", f"{HISTORY}:vendor/bk3633_sdk/{rel}"], cwd=args.repo)
        record(rel.replace("/", "__"), data, source_url=BASE + rel,
               acquisition="local Git history; upstream provenance recorded in historical UPSTREAM.md",
               historical_commit=HISTORY, upstream_commit=SDK_REV)
    for name, url in URLS.items():
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                data = response.read()
            record(name, data, source_url=url, acquisition="HTTPS")
        except (urllib.error.URLError, TimeoutError) as exc:
            rows.append({"file": name, "source_url": url, "error": str(exc),
                         "attempted_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    (args.output / "sources.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
