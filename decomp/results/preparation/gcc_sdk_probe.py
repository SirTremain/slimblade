#!/usr/bin/env python3
"""Bounded, source-backed GCC experiment; never changes worker locks or oracles.

Extract four utility bodies from the previously recorded SDK Git revision. Keep
the two existing clock hypotheses. Compile with one of two predeclared SDK-led
configurations. This is calibration evidence, not recovered-source submission.
"""
import argparse
import datetime
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import stock_compare as sc

spec = importlib.util.spec_from_file_location("initial_calibration", Path(__file__).with_name("calibrate.py"))
initial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(initial)

HISTORY = "ea2ee1dd6f47ab414180b1b4e6ea375caef489d7"
UPSTREAM = "0a461f8ed4a4f17ff6889d6f9d34e521b92b8243"
HEADER = "SDK/src/modules/common/api/co_utils.h"
INPUTS = [HEADER, "SDK/projects/app_mouse/Makefile",
          "SDK/src/plf/refip/src/arch/compiler/armgcc_4_8/compiler.h",
          "SDK/src/system/peripheral_stack_symbol.txt"]
NAMES = {0xe4ee: "co_read16p", 0xe4fc: "co_read32p",
         0xe540: "co_write16p", 0xe548: "co_write32p"}
# The first 12 options come directly from the SDK mouse Makefile. The remaining
# options make the standalone, header-free experiment explicit and reproducible.
SDK_FLAGS = ["-Os", "-mcpu=arm968e-s", "-march=armv5te", "-mthumb",
             "-mthumb-interwork", "-ffunction-sections", "-fdata-sections",
             "-fno-strict-aliasing", "-fgnu89-inline", "-ffast-math",
             "-fmessage-length=0", "-Wall", "-std=gnu99", "-mfloat-abi=soft",
             "-mabi=aapcs", "-ffreestanding", "-fno-builtin", "-nostdinc",
             "-fno-unwind-tables", "-fno-asynchronous-unwind-tables"]
TYPES = "typedef unsigned char uint8_t;\ntypedef unsigned short uint16_t;\ntypedef unsigned int uint32_t;\n"


def extract(header, name):
    matches = list(re.finditer(r"__INLINE\s+(?:uint16_t|uint32_t|void)\s+" + re.escape(name)
                              + r"\s*\([^)]*\)\s*\{[^{}]*\}", header))
    if len(matches) != 1:
        raise ValueError("expected exactly one simple SDK definition: " + name)
    match = matches[0]
    return match.group(), header[:match.start()].count("\n") + 1


def source_for(probe, header):
    start, _, ret, params, body = probe
    symbol = f"fn_{start:08x}"
    if start not in NAMES:
        return f"{ret} {symbol}({params}) {{ {body} }}\n", {"kind": "unchanged initial clock hypothesis"}
    name = NAMES[start]
    body, line = extract(header, name)
    # Preserve the extracted function body and parameter types. Only its name
    # and external linkage change so its standalone bytes can be measured.
    definition = re.sub(r"\b" + name + r"\b", symbol, body, count=1).replace("__INLINE ", "", 1)
    helper = ""
    if name == "co_read32p":
        helper, _ = extract(header, "co_read16p")
        helper = helper.replace("__INLINE ", "static __attribute__((__always_inline__)) inline ", 1) + "\n"
    source = ("/* Calibration-only SDK extraction; linkage/name adapted, body unchanged.\n"
              " * Original copyright: RivieraWaves 2009-2015; see retained SDK source. */\n"
              + TYPES + helper + definition + "\n")
    return source, {"kind": "SDK source correspondence hypothesis", "function": name,
                    "path": HEADER, "line": line, "body_sha256": sc.base.sha(body.encode())}


def run(command, cwd, commands):
    result = subprocess.run(command, cwd=cwd, env=sc.base.ENV, capture_output=True,
                            text=True, timeout=60)
    commands.append({"argv": command, "cwd": str(cwd), "exit_code": result.returncode,
                     "stdout": result.stdout, "stderr": result.stderr})
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {command[0]}\n{result.stderr}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--toolchain", type=Path, required=True)
    parser.add_argument("--mode", choices=["sdk-nolto", "sdk-lto"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, toolchain, out = args.root.resolve(), args.toolchain.resolve(), args.output.resolve()
    raw = (root / ".decomp/stock/stock-v4.49.bin").read_bytes()
    if sc.base.sha(raw) != "e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7":
        raise ValueError("stock identity changed")
    out.mkdir(parents=True, exist_ok=False)
    commands = []
    flags = SDK_FLAGS + (["-flto"] if args.mode == "sdk-lto" else ["-fno-lto"])
    report = {"scope": "bounded SDK-led GCC calibration; no certification", "mode": args.mode,
              "date_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "flags": flags, "baseline_sha256": sc.base.sha(raw), "commands": commands,
              "script_sha256": sc.base.sha(Path(__file__).read_bytes()),
              "comparator_sha256": sc.base.sha((ROOT / "tools/stock_compare.py").read_bytes()),
              "prototype_sha256": sc.base.sha(sc.PROTOTYPE.read_bytes()),
              "initial_calibration_sha256": sc.base.sha(Path(initial.__file__).read_bytes()),
              "inputs": [], "probes": [], "certified_match": False}
    try:
        header = ""
        for rel in INPUTS:
            data = subprocess.check_output(["git", "show", f"{HISTORY}:vendor/bk3633_sdk/{rel}"], cwd=root)
            name = rel.replace("/", "__")
            (out / name).write_bytes(data)
            report["inputs"].append({"file": name, "bytes": len(data), "sha256": sc.base.sha(data),
                "source_url": f"https://gitee.com/beken-corp/bk3633_ble_sdk/raw/{UPSTREAM}/{rel}",
                "acquisition": "local Git history; historical upstream provenance, not a new upstream verification",
                "historical_commit": HISTORY, "upstream_commit": UPSTREAM})
            if rel == HEADER:
                header = data.decode()
        cc = str(toolchain / "bin/arm-none-eabi-gcc")
        ld = str(toolchain / "bin/arm-none-eabi-ld")
        report["compiler"] = sc.base.pin(cc)
        report["linker"] = sc.base.pin(ld)
        report["version"] = run([cc, "--version"], out, commands)
        report["compiler_subtools"] = []
        for subtool in ("cc1", "as", "collect2", "lto1", "lto-wrapper"):
            path = run([cc, f"-print-prog-name={subtool}"], out, commands).strip()
            report["compiler_subtools"].append({"name": subtool, **sc.base.pin(path)})
        for probe in initial.PROBES:
            start, end = probe[:2]
            name = f"fn_{start:08x}"
            build = out / name
            build.mkdir()
            source, origin = source_for(probe, header)
            (build / "probe.c").write_text(source)
            script = sc.layout({"entry": hex(start), "id": name})
            (build / "layout.ld").write_text(script)
            run([cc, *flags, "-c", "probe.c", "-o", "probe.o"], build, commands)
            if args.mode == "sdk-lto":
                link = [cc, *flags, "-nostdlib", "-nostartfiles", "-nodefaultlibs",
                        "-Wl,--build-id=none,--no-undefined,-T,layout.ld", "probe.o", "-o", "probe.elf"]
            else:
                link = [ld, "-m", "armelf", "--build-id=none", "--no-undefined",
                        "-T", "layout.ld", "probe.o", "-o", "probe.elf"]
            run(link, build, commands)
            elf = (build / "probe.elf").read_bytes()
            actual = sc.runtime_bytes(elf, start)
            row = {**sc.compare(raw[start:end], actual, start), "entry": hex(start), "origin": origin,
                   "source_sha256": sc.base.sha(source.encode()), "elf_sha256": sc.base.sha(elf),
                   "actual_sha256": sc.base.sha(actual), "expected_sha256": sc.base.sha(raw[start:end])}
            report["probes"].append(row)
            (build / "llvm.txt").write_text(run(["/usr/bin/llvm-objdump", "-d",
                "--triple=thumbv5te-none-eabi", "probe.elf"], build, commands))
            print(name, row["result"], row["differing_bytes"], "different bytes", flush=True)
        report["complete"] = True
    except Exception as error:
        report["complete"] = False
        report["error"] = str(error)
        raise
    finally:
        (out / "report.json").write_bytes(sc.encode(report))


if __name__ == "__main__":
    main()
