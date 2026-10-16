#!/usr/bin/env python3
"""Check the bounded analysis delta and export independent disassembly evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess


BASELINE_SHA = "e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7"
CHANGED_BODIES = {
    "fn_00003f48": [{"start": "0x00003f48", "end_exclusive": "0x00004026"}],
    "fn_0000a14c": [{"start": "0x0000a14c", "end_exclusive": "0x0000a1d6"}],
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_inventory(before, after):
    require({k: v for k, v in before.items() if k != "functions"} ==
            {k: v for k, v in after.items() if k != "functions"}, "inventory metadata changed")
    old = {f["id"]: f for f in before["functions"]}
    new = {f["id"]: f for f in after["functions"]}
    require(len(old) == len(before["functions"]) and len(new) == len(after["functions"]), "duplicate ID")
    require(old.keys() == new.keys(), "function set changed")
    require(CHANGED_BODIES.keys() <= old.keys(), "repair target missing")
    for identifier, fn in old.items():
        expected = dict(fn)
        if identifier in CHANGED_BODIES:
            expected["ranges"] = CHANGED_BODIES[identifier]
        require(new[identifier] == expected, f"unexpected function change: {identifier}")


def runtime_dispatch(data, references, functions):
    word = lambda address: struct.unpack_from("<I", data, address)[0]
    # The load consumes the word at LR; dispatch and stack restoration are
    # nonstandard call semantics. This audit does not assert a Ghidra fixup.
    anchors = {0x1e4f0: 0xe49e6004, 0x1e544: 0xe08c508c,
               0x1e548: 0xe1a06536, 0x1e54c: 0xe2066007,
               0x1e558: 0xe08ec106, 0x1e55c: 0xe8bd4070, 0x1e560: 0xe12fff1c}
    require(all(word(a) == value for a, value in anchors.items()), "runtime helper anchor changed")
    calls = []
    for ref in references:
        if ref["to"] != "0001e4f0" or ref["type"] != "UNCONDITIONAL_CALL":
            continue
        address = int(ref["from"], 16)
        instruction = word(address)
        require(instruction & 0xff000000 == 0xeb000000, "reference is not an ARM BL")
        immediate = instruction & 0xffffff
        if immediate & 0x800000:
            immediate -= 1 << 24
        require(address + 8 + 4 * immediate == 0x1e4f0, "ARM call target mismatch")
        table = word(address + 4)
        selectors = [(table >> (3 * i)) & 7 for i in range(9)]
        owners = [f["id"] for f in functions if any(int(r["start"], 16) <= address <
                  int(r["end_exclusive"], 16) for r in f["ranges"])]
        calls.append({"call": hex(address), "function_ids": owners, "inline_data": hex(address + 4),
                      "word": hex(table), "selector_fields": selectors,
                      "possible_local_continuations": sorted({hex(address + 8 + 4 * s) for s in selectors if s < 4}),
                      "helper_dispatch_selectors": sorted({s for s in selectors if s >= 4})})
    return calls


def changed_address(address):
    return 0x4000 <= address < 0x401e or 0xa1d4 <= address < 0xa1d8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="main checkout with ignored local evidence")
    parser.add_argument("output", type=Path, help="new ignored evidence directory")
    parser.add_argument("--tag", default="readiness-v2", help="export/audit name suffix for a fresh replay")
    args = parser.parse_args()
    state = args.root.resolve() / ".decomp"
    load = lambda p: json.loads(p.read_text())
    old_packet = state / "evidence/bootstrap-review-v2"
    require(args.tag and all(c.isalnum() or c in "-_" for c in args.tag), "invalid tag")
    new_packet = state / "evidence" / args.tag
    data = (state / "stock/stock-v4.49.bin").read_bytes()
    require(len(data) == 128112 and hashlib.sha256(data).hexdigest() == BASELINE_SHA, "wrong baseline")
    for packet in (old_packet, new_packet):
        require((packet / "database-container.bin").read_bytes() == data, "database bytes differ")
    before = load(state / "inventory-review-v2.json")
    after = load(state / f"inventory-{args.tag}.json")
    check_inventory(before, after)
    audit = load(state / f"{args.tag}-repair.json")
    require(audit["container_sha256"] == BASELINE_SHA and audit["firmware_bytes_changed"] is False,
            "bad repair identity")
    require({int(e["address"], 16) for e in audit["resolved_errors"]} == {0x4000, 0x4004, 0xa1d4},
            "unexpected retired diagnostics")
    for row in audit["after"]:
        address = int(row["address"], 16)
        require(row["instruction"] and row["tmode"] == 1, "new instruction not Thumb")
        raw = bytes.fromhex(row["bytes"])
        require(raw == data[address:address + len(raw)], "instruction bytes changed")
    report = load(state / f"inventory-{args.tag}-review.json")
    require(report["analysis_error_count"] == 1 and len(report["errors"]) == 1 and
            report["errors"][0][0] == "0x0001e480", "remaining diagnostics changed")
    require(report["overlapping_function_body_bytes"] == 0, "overlapping function bodies")
    require(report["matching_coverage"] == "unknown", "invalid match claim")
    listings = []
    for packet in (old_packet, new_packet):
        listings.append({int(line.split()[0], 16): line for line in
                         (packet / "listing.txt").read_text().splitlines()})
    for address in listings[0].keys() | listings[1].keys():
        if not changed_address(address):
            require(listings[0].get(address) == listings[1].get(address),
                    f"unrelated listing changed at {hex(address)}")
    old_refs, new_refs = (load(p / "references.json") for p in (old_packet, new_packet))
    ref_set = lambda refs: {tuple(sorted(r.items())) for r in refs}
    for difference in ref_set(old_refs) ^ ref_set(new_refs):
        require(changed_address(int(dict(difference)["from"], 16)), "unrelated reference changed")
    calls = runtime_dispatch(data, old_refs, before["functions"])
    require({c["call"] for c in calls} == {"0x1e360", "0x1e47c"}, "runtime call sites changed")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    objcopy, objdump = shutil.which("llvm-objcopy"), shutil.which("llvm-objdump")
    require(objcopy and objdump, "LLVM disassembly tools missing")
    elf = output / "disassembly-only.elf"
    subprocess.run([objcopy, "-I", "binary", "-O", "elf32-littlearm", "--rename-section",
                    ".data=.text,alloc,load,readonly,code", str(state / "stock/stock-v4.49.bin"), str(elf)], check=True)
    records = []
    for name, triple, start, end in (
        ("thumb-continuation", "thumbv5te-none-eabi", "0x3fd0", "0x4026"),
        ("thumb-return", "thumbv5te-none-eabi", "0xa1ca", "0xa1d6"),
        ("runtime-caller-one", "armv5te-none-eabi", "0x1e35c", "0x1e398"),
        ("runtime-caller-two", "armv5te-none-eabi", "0x1e420", "0x1e490"),
        ("runtime-helper", "armv5te-none-eabi", "0x1e4f0", "0x1e5a8"),
    ):
        command = [objdump, "-D", "--triple=" + triple, "--start-address=" + start,
                   "--stop-address=" + end, str(elf)]
        listing = subprocess.check_output(command)
        (output / (name + ".txt")).write_bytes(listing)
        records.append({"file": name + ".txt", "command": command,
                        "sha256": hashlib.sha256(listing).hexdigest()})
    tools = [{"path": p, "bytes": Path(p).stat().st_size,
              "sha256": hashlib.sha256(Path(p).read_bytes()).hexdigest(),
              "version": subprocess.check_output([p, "--version"], text=True)} for p in (objcopy, objdump)]
    result = {"status": "bounded analysis delta verified; pilot still blocked",
              "baseline_sha256": BASELINE_SHA, "changed_bodies": sorted(CHANGED_BODIES),
              "resolved_diagnostics": 3, "remaining_diagnostics": 1,
              "runtime_calls": calls, "tools": tools, "disassembly": records,
              "matching_coverage": "unknown"}
    (output / "checks.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("status", "resolved_diagnostics", "remaining_diagnostics", "runtime_calls")}, indent=2))


if __name__ == "__main__":
    main()
