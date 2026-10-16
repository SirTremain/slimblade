#!/usr/bin/env python3
"""Static SDK/stock byte correspondence only; never certifies recovered code."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

HISTORY = "ea2ee1dd6f47ab414180b1b4e6ea375caef489d7"
UPSTREAM = "0a461f8ed4a4f17ff6889d6f9d34e521b92b8243"
STOCK = "e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7"
PILOT = [(0x3b48, 0x3b64), (0x3bb4, 0x3bbe), (0xe4ee, 0xe4fc),
         (0xe4fc, 0xe512), (0xe540, 0xe548), (0xe548, 0xe558)]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def occurrences(haystack, needle, alignment=2):
    if not needle:
        raise ValueError("empty pattern")
    if alignment not in (1, 2, 4):
        raise ValueError("unsupported alignment")
    result = []
    offset = 0
    while True:
        offset = haystack.find(needle, offset)
        if offset < 0:
            return result
        if offset % alignment == 0:
            result.append(offset)
        offset += 1


def elf_functions(data):
    """Read ELF32 LE ARM function symbols with explicit, bounded code sections."""
    def take(offset, size):
        if offset < 0 or size < 0 or offset + size > len(data):
            raise ValueError("truncated ELF")
        return data[offset:offset + size]

    if take(0, 7) != b"\x7fELF\x01\x01\x01":
        raise ValueError("expected ELF32 LE")
    header = struct.unpack("<HHIIIIIHHHHHH", take(16, 36))
    kind, machine, _, _, _, shoff, _, _, _, _, shsize, shnum, _ = header
    if kind != 2 or machine != 40 or shsize != 40 or not 0 < shnum < 4096:
        raise ValueError("unsupported ELF")
    sections = [struct.unpack("<IIIIIIIIII", take(shoff + i * 40, 40)) for i in range(shnum)]
    results = []
    for section in sections:
        if section[1] != 2:
            continue
        if section[9] != 16 or section[5] % 16 or section[6] >= shnum:
            raise ValueError("bad symbol table")
        strings_section = sections[section[6]]
        if strings_section[1] != 3:
            raise ValueError("symbol names not in string table")
        strings = take(strings_section[4], strings_section[5])
        take(section[4], section[5])
        for offset in range(section[4], section[4] + section[5], 16):
            name, value, size, info, _, index = struct.unpack("<IIIBBH", take(offset, 16))
            if info & 15 != 2 or size < 8 or index == 0 or index >= shnum:
                continue
            code = sections[index]
            start = value & ~1
            if code[1] != 1 or code[2] & 6 != 6 or not code[3] <= start < start + size <= code[3] + code[5]:
                raise ValueError("function outside executable section")
            if name >= len(strings) or b"\0" not in strings[name:]:
                raise ValueError("bad symbol name")
            symbol = strings[name:].split(b"\0", 1)[0].decode("ascii")
            contents = take(code[4] + start - code[3], size)
            results.append((symbol, start, "thumb" if value & 1 else "arm", contents))
    return results


def map_functions(data, text):
    region = re.search(r"Load Region SECTIONS \(Base: (0x[0-9a-f]+), Size: (0x[0-9a-f]+),", text)
    if not region or int(region[2], 16) != len(data):
        raise ValueError("map load region does not match flat SDK app")
    base = int(region[1], 16)
    rows = []
    seen = set()
    for match in re.finditer(r"^\s+(\S+)\s+(0x[0-9a-f]+)\s+(Thumb|ARM) Code\s+(\d+)\s+(.+)$", text, re.M):
        name, value, mode, size, origin = match.groups()
        start, size = int(value, 16) & ~1, int(size)
        if size < 8 or (name, start) in seen:
            continue
        if not base <= start < start + size <= base + len(data):
            raise ValueError("mapped function outside app load region")
        seen.add((name, start))
        rows.append((name, start, mode.lower(), data[start-base:start-base+size]))
    if not rows:
        raise ValueError("no sized map functions")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.output.resolve()
    raw = (root / ".decomp/stock/stock-v4.49.bin").read_bytes()
    if sha(raw) != STOCK:
        raise ValueError("wrong stock")
    out.mkdir(parents=True, exist_ok=False)
    downloads = root / ".decomp/downloads"
    tree_data = (downloads / "sdk-tree-preparation.json").read_bytes()
    tree = json.loads(tree_data)
    if tree.get("truncated") or tree.get("sha") != UPSTREAM:
        raise ValueError("unexpected upstream tree")
    tree_by_path = {row["path"]: row for row in tree["tree"]}
    artifacts = [("bk3633_stack_gcc.elf", "SDK/src/system/bk3633_stack_gcc.elf"),
                 ("bk3633_stack.bin", "SDK/projects/app_mouse/output/stack/bk3633_stack.bin"),
                 ("bk3633_app_sdk.bin", "SDK/projects/app_mouse/output/app/bk3633_app.bin"),
                 ("bk3633_app_sdk.map", "SDK/projects/app_mouse/Listings/bk3633_app.map")]
    report = {"scope": "prebuilt SDK static correspondence, not reconstructed C or compiler proof",
              "date_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "baseline_sha256": STOCK, "script_sha256": sha(Path(__file__).read_bytes()),
              "tree": {"bytes": len(tree_data), "sha256": sha(tree_data),
                  "source_url": f"https://gitee.com/api/v5/repos/beken-corp/bk3633_ble_sdk/git/trees/{UPSTREAM}?recursive=1"},
              "artifacts": [], "pilot_patterns": [], "whole_symbol_matches": []}
    blobs = {}
    for name, rel in artifacts:
        data = (downloads / name).read_bytes()
        blob_id = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        meta = tree_by_path[rel]
        if meta["sha"] != blob_id or meta["size"] != len(data):
            raise ValueError("SDK download differs from upstream tree")
        report["artifacts"].append({"file": name, "bytes": len(data), "sha256": sha(data),
            "git_blob_sha1": blob_id, "source_url": f"https://gitee.com/beken-corp/bk3633_ble_sdk/raw/{UPSTREAM}/{rel}"})
        blobs[name] = data
        if name.endswith(".map"):
            continue
        for start, end in PILOT:
            report["pilot_patterns"].append({"entry": hex(start), "bytes": end-start,
                "artifact": name, "file_offsets": [hex(x) for x in occurrences(data, raw[start:end])]})
    elf_path = downloads / "bk3633_stack_gcc.elf"
    for label, command in {"comment": ["llvm-readelf", "-p", ".comment", str(elf_path)],
                           "attributes": ["llvm-readelf", "-A", str(elf_path)]}.items():
        output = subprocess.check_output(command, text=True)
        (out / (label + ".txt")).write_text(output)
        report[label] = output
    inventory_data = (root / ".decomp/inventory-runtime-v4.json").read_bytes()
    inventory = json.loads(inventory_data)
    if inventory["baseline_sha256"] != STOCK:
        raise ValueError("inventory baseline mismatch")
    report["inventory_sha256"] = sha(inventory_data)
    functions = {int(f["entry"], 16): f for f in inventory["functions"]}
    gcc_candidates = elf_functions(blobs["bk3633_stack_gcc.elf"])
    arm_candidates = map_functions(blobs["bk3633_app_sdk.bin"], blobs["bk3633_app_sdk.map"].decode())
    report["sdk_sized_functions_checked"] = {"gcc_stack": len(gcc_candidates), "arm_app": len(arm_candidates)}
    report["arm_app_map_header"] = blobs["bk3633_app_sdk.map"].decode().splitlines()[0]
    candidates = [("gcc_stack", *row) for row in gcc_candidates] + [("arm_app", *row) for row in arm_candidates]
    for artifact, name, start, mode, code in candidates:
        for offset in occurrences(raw, code, 2 if mode == "thumb" else 4):
            discovered = functions.get(offset)
            if not discovered or discovered["mode"] != mode:
                continue
            same_range = [(int(r["start"], 16), int(r["end_exclusive"], 16)) for r in discovered["ranges"]] == [(offset, offset+len(code))]
            report["whole_symbol_matches"].append({"sdk_symbol": name, "sdk_entry": hex(start),
                "artifact": artifact,
                "stock_entry": hex(offset), "bytes": len(code), "sha256": sha(code),
                "mode": mode, "same_discovered_body_range": same_range,
                "qualification": "exact prebuilt bytes only; coincidental small matches possible"})
    symbols_rel = "SDK/src/system/peripheral_stack_symbol.txt"
    symbols = subprocess.check_output(["git", "show", f"{HISTORY}:vendor/bk3633_sdk/{symbols_rel}"], cwd=root)
    (out / "peripheral_stack_symbol.txt").write_bytes(symbols)
    report["arm_linker_lead"] = {"header": symbols.decode().splitlines()[0],
        "sha256": sha(symbols), "bytes": len(symbols), "historical_commit": HISTORY,
        "source_url": f"https://gitee.com/beken-corp/bk3633_ble_sdk/raw/{UPSTREAM}/{symbols_rel}",
        "qualification": "symbol-file metadata; not proof of compiler for every binary function"}
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"sized_sdk_functions": len(candidates),
                      "exact_prebuilt_correspondences": len(report["whole_symbol_matches"]),
                      "pilot_patterns": report["pilot_patterns"]}, indent=2))


if __name__ == "__main__":
    main()
