#!/usr/bin/env python3
"""One SDK-only native GCC control; not a Kensington decompilation attempt."""
import argparse
import datetime
from pathlib import Path
import subprocess

import gcc_sdk_probe as probe
import inspect_sdk as sdk


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.output.resolve()
    data = (root / ".decomp/downloads/bk3633_stack_gcc.elf").read_bytes()
    if sdk.sha(data) != "9da4965e48c6bec0c3a08ab22ccd1de15b421d8e9a474f93db082b26b028dd58":
        raise ValueError("SDK identity changed")
    rows = [row for row in sdk.elf_functions(data) if row[0] == "co_list_init"]
    if len(rows) != 1 or rows[0][2] != "thumb":
        raise ValueError("unexpected SDK control symbol")
    _, entry, _, expected = rows[0]
    header_path = "SDK/src/modules/common/api/co_list.h"
    header = subprocess.check_output(["git", "show",
        f"{probe.HISTORY}:vendor/bk3633_sdk/{header_path}"], cwd=root)
    name = f"fn_{entry:08x}"
    source = ("/* SDK-only control; hypothesized initialization, profiling disabled. */\n"
              "struct co_list_hdr { struct co_list_hdr *next; };\n"
              "struct co_list { struct co_list_hdr *first; struct co_list_hdr *last; };\n"
              f"void {name}(struct co_list *list) {{ list->first = 0; list->last = 0; }}\n")
    cc_dir = root / ".decomp/tools/gcc-arm-none-eabi-9-2019-q4-major/bin"
    cc, ld = str(cc_dir / "arm-none-eabi-gcc"), str(cc_dir / "arm-none-eabi-ld")
    out.mkdir(parents=True, exist_ok=False)
    commands = []
    report = {"scope": "SDK-only control, not stock calibration or certification",
              "date_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "sdk_sha256": sdk.sha(data), "symbol": "co_list_init", "entry": hex(entry),
              "script_sha256": sdk.sha(Path(__file__).read_bytes()),
              "driver_sha256": sdk.sha(Path(probe.__file__).read_bytes()),
              "comparator_sha256": sdk.sha((probe.ROOT / "tools/stock_compare.py").read_bytes()),
              "header_sha256": sdk.sha(header), "header_bytes": len(header),
              "header_source_url": f"https://gitee.com/beken-corp/bk3633_ble_sdk/raw/{probe.UPSTREAM}/{header_path}",
              "historical_commit": probe.HISTORY,
              "source_sha256": sdk.sha(source.encode()), "commands": commands,
              "flags": probe.SDK_FLAGS + ["-fno-lto"], "certified_match": False}
    try:
        (out / "co_list.h").write_bytes(header)
        (out / "probe.c").write_text(source)
        (out / "layout.ld").write_text(probe.sc.layout({"entry": hex(entry), "id": name}))
        report["version"] = probe.run([cc, "--version"], out, commands)
        report["tools"] = [probe.sc.base.pin(cc), probe.sc.base.pin(ld)]
        for subtool in ("cc1", "as"):
            path = probe.run([cc, f"-print-prog-name={subtool}"], out, commands).strip()
            report["tools"].append(probe.sc.base.pin(path))
        probe.run([cc, *report["flags"], "-c", "probe.c", "-o", "probe.o"], out, commands)
        probe.run([ld, "-m", "armelf", "--build-id=none", "--no-undefined",
                   "-T", "layout.ld", "probe.o", "-o", "probe.elf"], out, commands)
        actual = probe.sc.runtime_bytes((out / "probe.elf").read_bytes(), entry)
        report["comparison"] = probe.sc.compare(expected, actual, entry)
        report["expected_sha256"] = sdk.sha(expected)
        report["actual_sha256"] = sdk.sha(actual)
        (out / "llvm.txt").write_text(probe.run(["llvm-objdump", "-d",
            "--triple=thumbv5te-none-eabi", "probe.elf"], out, commands))
        report["complete"] = True
        print(report["comparison"])
    except Exception as error:
        report["complete"] = False
        report["error"] = str(error)
        raise
    finally:
        (out / "report.json").write_bytes(probe.sc.encode(report))


if __name__ == "__main__":
    main()
