#!/usr/bin/env python3
"""Coordinator-only export of six reviewed leaf packets; no recovered C."""
import argparse
import json
from pathlib import Path
import re
import shutil
import struct
import sys

import decomp
import stock_compare as sc

SPANS = [(0x3b48, 0x3b64), (0x3bb4, 0x3bbe), (0xe4ee, 0xe4fc),
         (0xe4fc, 0xe512), (0xe540, 0xe548), (0xe548, 0xe558)]
INPUTS = {
    ".decomp/inventory-readiness-v2.json": "e6467b624c95023e9c5e6fa0c5babfdb27b8b35318b2277ab800aab47fe7d488",
    ".decomp/pilot-leaves.json": "4ca31f47f191060e6d2b89f4ff3c50da8b4930aa80d6bb7625188044f9e56ed6",
    ".decomp/evidence/llvm-crosscheck/disassembly-only.elf": "33760455b2b3c6259d6d8f67e188f46102b959fb63185112f8c0e5574fbe2ded",
}
CONTEXT = {
    0x3b48: "Register-only leaf. r0/r1 are inputs; r0 is returned. Conditional branches stay inside the body. Preserve 32-bit wraparound, logical shifts and unsigned condition codes; source typedefs and purpose are unknown.",
    0x3bb4: "Register-only leaf. r0/r1 are inputs and r0 is returned. Caller at 0xd51c stores r0. Preserve 32-bit arithmetic and truncation; semantic names are not recovered.",
    0xe4ee: "Input r0 addresses two readable bytes, including potentially unaligned input. Two LDRB reads, no writes or calls. Return in r0 is explicitly narrowed to 16 bits. Declared return type, const/volatile qualifiers and complete pointer domain require worker evidence; do not replace byte loads with an aligned halfword load.",
    0xe4fc: "Input r0 addresses four readable bytes; four LDRB accesses, no writes or calls. Preserve read widths/order and unsigned shifts. Caller at 0xc70c uses r0. Return declaration and pointer qualifiers remain source-level hypotheses.",
    0xe540: "Input r0 is a writable byte address and r1 supplies bits; two STRB writes, no reads/calls. r0 is unchanged. Reviewed callers do not consume a return value, suggesting void, not proving the original declaration. Preserve byte accesses and do not invent alignment guarantees.",
    0xe548: "Input r0 is a writable byte address and r1 supplies bits; four STRB writes, no reads/calls. r0 is unchanged. Callers at 0xbd5c and 0xc89a do not consume a return value. Preserve widths, ordering and shifts; declaration/qualifiers remain hypotheses.",
}


def write_json(path, value):
    path.write_bytes(sc.encode(value))


def address(value):
    return int(value, 16) if re.fullmatch(r"[0-9a-f]{8}", value) else None


def check_leaf(fn, start, end, raw, refs):
    sc.require(int(fn["entry"], 16) == start and int(fn["end_exclusive"], 16) == end, "wrong leaf")
    cursor = start
    for i in fn["instructions"]:
        a = int(i["address"], 16)
        b = bytes.fromhex(i["bytes"])
        sc.require(a == cursor and len(b) == 2 and i["tmode"] == 1 and b == raw[a:a+2], "instruction bytes/state changed")
        sc.require("CALL" not in i["flow_type"] and "[0x" not in i["text"], "non-leaf/literal reference")
        sc.require(all(start <= int(x, 16) < end for x in i["flows"]), "escaping branch")
        sc.require(i.get("fallthrough") is None or start <= int(i["fallthrough"], 16) < end, "escaping fallthrough")
        cursor += 2
    sc.require(cursor == end and fn["instructions"][-1]["text"] == "bx lr", "incomplete body")
    incoming = [r for r in refs if address(r["to"]) is not None and start <= address(r["to"]) < end
                and not (address(r["from"]) is not None and start <= address(r["from"]) < end)]
    sc.require(incoming and all(address(r["to"]) == start and r["type"] == "UNCONDITIONAL_CALL"
                               for r in incoming), "offcut/data entry requires review")
    outgoing = [r for r in refs if address(r["from"]) is not None and start <= address(r["from"]) < end]
    sc.require(all(address(r["to"]) is not None and start <= address(r["to"]) < end
                   and r["type"] == "CONDITIONAL_JUMP" for r in outgoing), "external dependency")
    return incoming, outgoing


def generate(root, name):
    sc.require(re.fullmatch(r"pilot-[a-z0-9-]+", name), "invalid output name")
    destination = root / ".decomp" / name
    packets = root / ".decomp/evidence" / name
    sc.require(not destination.exists() and not packets.exists(), "refusing to overwrite pilot")
    for relative, sha in INPUTS.items():
        sc.require(sc.base.sha((root / relative).read_bytes()) == sha, f"changed input: {relative}")
    original_packet = root / ".decomp/evidence/readiness-v2"
    sc.require(decomp.packet_hash(original_packet) == "8918a09bb12f34ed1071c4cb4add900ee129c1120b8026d3876d0b2e48b54a9b", "inventory packet changed")
    baseline = decomp.read_json(root / "decomp/baseline.json")
    raw = (root / ".decomp/stock/stock-v4.49.bin").read_bytes()
    sc.require(sc.base.sha(raw) == baseline["sha256"] and len(raw) == baseline["bytes"], "baseline changed")
    sc.require((original_packet / "database-container.bin").read_bytes() == raw, "database bytes differ")
    wrapper = root / ".decomp/evidence/llvm-crosscheck/disassembly-only.elf"
    wrapped = wrapper.read_bytes()  # ET_REL wrapper, not a linked candidate ELF.
    sc.require(wrapped[:7] == b"\x7fELF\x01\x01\x01" and
               struct.unpack_from("<HH", wrapped, 16) == (1, 40), "wrong wrapper format")
    table = struct.unpack_from("<I", wrapped, 32)[0]
    size, count = struct.unpack_from("<HH", wrapped, 46)
    sc.require(size == 40 and count == 4, "wrapper table changed")
    sections = [struct.unpack_from("<IIIIIIIIII", wrapped, table + size*i) for i in range(count)]
    sc.require(any(s[1:4] == (1, 6, 0) and wrapped[s[4]:s[4]+s[5]] == raw for s in sections),
               "LLVM wrapper differs from baseline")
    discovery = decomp.read_json(root / ".decomp/inventory-readiness-v2.json")
    leaves = decomp.read_json(root / ".decomp/pilot-leaves.json")
    sc.require(leaves["language"] == "ARM:LE:32:v5t" and leaves["baseline_sha256"] == baseline["sha256"], "bad Ghidra identity")
    refs = decomp.read_json(original_packet / "references.json")
    listing = (original_packet / "listing.txt").read_text().splitlines()
    llvm = shutil.which("llvm-objdump")
    sc.require(llvm, "LLVM disassembler required")
    llvm_pin = sc.base.pin(llvm)
    llvm_version = sc.base.run([llvm, "--version"])
    destination.mkdir(parents=True)
    packets.mkdir(parents=True)
    tasks = []
    for (start, end), fn in zip(SPANS, leaves["functions"], strict=True):
        ident = f"fn_{start:08x}"
        known = [f for f in discovery["functions"] if f["id"] == ident]
        ranges = [{"start": f"0x{start:08x}", "end_exclusive": f"0x{end:08x}"}]
        sc.require(len(known) == 1 and known[0]["ranges"] == ranges and known[0]["mode"] == "thumb", "discovery boundary changed")
        incoming, outgoing = check_leaf(fn, start, end, raw, refs)
        packet = packets / ident
        packet.mkdir()
        local = [line for line in listing if start <= int(line.split()[0], 16) < end]
        sc.require([line.split()[1] for line in local] == [i["bytes"] for i in fn["instructions"]], "listing/export discrepancy")
        (packet / "listing.txt").write_text("\n".join(local) + "\n")
        command = [llvm, "-D", "--triple=thumbv5te-none-eabi", f"--start-address={start}",
                   f"--stop-address={end}", str(wrapper)]
        independent = sc.base.run(command)
        decoded = re.findall(r"^\s*([0-9a-f]+):\s+([0-9a-f]{4})\s+(.+)$", independent, re.M)
        sc.require(len(decoded) * 2 == end-start, "incomplete independent decode")
        for index, (a, word, text) in enumerate(decoded):
            offset = int(a, 16)
            sc.require(offset == start + index*2 and struct.pack("<H", int(word, 16)) == raw[offset:offset+2]
                       and '<unknown>' not in text, "independent decode mismatch")
        (packet / "llvm.txt").write_text(independent)
        write_json(packet / "references.json", {"incoming": incoming, "outgoing": outgoing})
        write_json(packet / "instructions.json", fn)
        caller_lines = []
        for ref in incoming:
            a = address(ref["from"])
            caller_lines.append(f"\nCaller reference: {ref}\n")
            caller_lines.extend(line for line in listing if a-16 <= int(line.split()[0], 16) < a+12)
        (packet / "callers.txt").write_text("\n".join(caller_lines) + "\n")
        (packet / "context.md").write_text(
            f"# {ident}: bounded leaf reconstruction\n\nObserved instruction-level evidence: {CONTEXT[start]}\n\n"
            "Complete body is contiguous Thumb code ending in BX LR. No outgoing calls, literal pools, absolute globals, "
            "stack use or MMIO constants are present. All discovered external references target the entry, not an offcut. "
            "See instructions.json, both disassemblies, references.json and callers.txt. Reference discovery is not proof "
            "that no hidden indirect caller exists. AAPCS is the candidate build convention, not an identified original compiler.\n\n"
            "Worker task: derive readable C and justify widths, signedness, pointer access and declaration from evidence. "
            "Do not paste instruction words, add inline assembly, stubs, intrinsics or tune flags. Byte-equality feedback is "
            "not a certified match. Record compiler or ABI blockers promptly. Preserve unknowns. No Ghidra pseudocode is provided.\n\n"
            "Only this body is owned. No adjacent padding, shared data or callee bytes may be absorbed to improve a score. "
            "The global inventory and runtime helper near 0x1e4f0 remain unapproved and outside this pilot. "
            "Return flags are not declared source outputs; report any caller evidence contradicting AAPCS.\n")
        write_json(packet / "metadata.json", {
            "baseline_sha256": baseline["sha256"], "entry": f"0x{start:08x}", "mode": "thumb", "ranges": ranges,
            "range_sha256": sc.base.sha(raw[start:end]), "ghidra_version": "12.1.4", "language": leaves["language"],
            "export_settings": "readOnly/noanalysis; ExportPilot.java; no pseudocode",
            "export_script_sha256": sc.base.sha((sc.ROOT / "decomp/results/pilot-readiness/ExportPilot.java").read_bytes()),
            "review": "2026-10-16 coordinator: bytes, per-instruction TMode, bounded flow, entry references, independent LLVM",
            "llvm": llvm_pin, "llvm_version": llvm_version, "llvm_command": command,
            "upstream_source_url": baseline["source_url"], "baseline_bytes": baseline["bytes"],
            "inspection_date": "2026-10-16", "data_and_literal_ranges": [], "outgoing_dependencies": [],
            "full_inventory_approved": False})
        tasks.append({"id": ident, "kind": "function", "title": f"Pilot: reconstruct Thumb leaf at 0x{start:08x}",
                      "depends_on": ["bootstrap-inventory", "bootstrap-toolchain", "bootstrap-verifier"],
                      "allowed_paths": [f"decomp/src/{ident}.c", f"decomp/results/{ident}/"],
                      "instructions": "Read the immutable packet and docs/pilot.md. Recover this leaf only; no calls or absolute globals are supported. Name the C function exactly as the task ID. Keep prototype hypotheses in notes. Use the frozen candidate compiler for byte feedback; do not alter flags or demand a match from an unidentified historical toolchain. Stop at 20 minutes/8 builds/3 non-improving attempts. Submit draft or blocked; never matched.",
                      "acceptance": "Evidence-backed C and recorded comparison, independently rebuilt/reviewed by coordinator. Exact bytes alone do not certify recovered source, ABI or whole-image equivalence.",
                      "entry": f"0x{start:08x}", "mode": "thumb", "ranges": ranges,
                      "evidence_path": packet.relative_to(root).as_posix(), "evidence_sha256": decomp.packet_hash(packet),
                      "boundary_review": "2026-10-16 coordinator limited leaf review; see decomp/results/pilot-readiness/notes.md and packet instructions.json/llvm.txt/references.json. Global inventory is NOT approved.",
                      "comparison_scope": sc.SCOPE})
    result = {"schema_version": 1, "baseline_id": baseline["id"],
              "inventory_status": "six_reviewed_pilot_leaves_only_global_inventory_unapproved", "functions": tasks}
    proposal = destination / "functions.json"
    write_json(proposal, result)
    lock_path = destination / "lock.json"
    lock_sha = sc.initialize(root, proposal, lock_path)
    for task in tasks:
        task["comparison"] = {"lock_path": lock_path.relative_to(root).as_posix(), "lock_sha256": lock_sha}
    write_json(proposal, result)
    for packet in packets.iterdir():
        for file in packet.iterdir():
            file.chmod(0o444)
        packet.chmod(0o555)
    print(f"Prepared {len(tasks)} leaf packets; proposal: {proposal}; lock SHA-256: {lock_sha}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=sc.ROOT)
    p.add_argument("--name", default="pilot-v1")
    args = p.parse_args()
    try:
        generate(args.root.resolve(), args.name)
    except (OSError, ValueError, KeyError) as error:
        sys.exit(f"error: {error}")
