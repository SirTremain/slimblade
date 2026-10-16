#!/usr/bin/env python3
"""Structural review of exported discovery, never function boundary approval."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import struct


def check_functions(functions, byte_count):
    """Track row indexes, not IDs: duplicate IDs must not hide ownership."""
    ownership = [[] for _ in range(byte_count)]
    errors, blocked = [], set()
    ids, entries = defaultdict(list), defaultdict(list)
    for index, fn in enumerate(functions):
        entry = int(fn["entry"], 16)
        ids[fn["id"]].append(index)
        entries[entry].append(index)
        spans = [(int(s["start"], 16), int(s["end_exclusive"], 16)) for s in fn["ranges"]]
        problems = []
        if not any(start <= entry < end for start, end in spans):
            problems.append("entry outside body")
        alignment = 4 if fn["mode"] == "arm" else 2
        if fn["mode"] not in ("arm", "thumb") or entry % alignment:
            problems.append("unknown mode or misaligned entry")
        for start, end in spans:
            if not 0x2020 <= start < end <= 0x1ed60:
                problems.append("range outside mixed application block")
            for offset in range(max(0, start), min(byte_count, end)):
                ownership[offset].append(index)
        if problems:
            blocked.add(fn["id"])
            errors.extend([fn["id"], problem] for problem in problems)
    for label, groups in (("function ID", ids), ("function entry", entries)):
        for key, indexes in groups.items():
            if len(indexes) > 1:
                key = hex(key) if isinstance(key, int) else key
                errors.append([key, f"duplicate {label} in rows {indexes}"])
                blocked.update(functions[i]["id"] for i in indexes)

    # Include self-overlap within one body's ranges, not only shared tails.
    # Coalesce only adjacent bytes with exactly the same claiming rows.
    overlaps = []
    for offset, owners in enumerate(ownership):
        if len(owners) <= 1:
            continue
        if overlaps and overlaps[-1]["end_exclusive"] == offset and overlaps[-1]["rows"] == owners:
            overlaps[-1]["end_exclusive"] = offset + 1
        else:
            overlaps.append({"start": offset, "end_exclusive": offset + 1, "rows": owners})
        blocked.update(functions[i]["id"] for i in owners)
    for span in overlaps:
        span["function_ids"] = sorted({functions[i]["id"] for i in span["rows"]})
        span["start"], span["end_exclusive"] = hex(span["start"]), hex(span["end_exclusive"])
        errors.append([span["start"], f"overlapping body ranges ending at {span['end_exclusive']} in rows {span['rows']}"])
    return ownership, errors, blocked, overlaps


def check_diagnostics(meta, functions, ownership):
    """Fail closed for legacy evidence; no bookmarks is not boundary approval."""
    errors, blocked, diagnostics = [], set(), []
    if (meta.get("schema_version") != 2 or not isinstance(meta.get("analysis_diagnostics"), list)
            or not isinstance(meta.get("default_address_space"), str)):
        return [["evidence", "missing/version-mismatched analysis diagnostics; re-export with ExportEvidence.java"]], blocked, diagnostics

    def owners_at(address):
        return {functions[i]["id"] for i in ownership[address]} if 0 <= address < len(ownership) else set()

    for index, diagnostic in enumerate(meta["analysis_diagnostics"]):
        try:
            address = int(diagnostic["address"], 16)
            sources = [int(source, 16) for source in diagnostic["flow_sources"]]
            if (diagnostic["severity"] not in ("error", "warning")
                    or not isinstance(diagnostic["flow_sources"], list)
                    or any(not isinstance(diagnostic[key], str) for key in ("address_space", "category", "message"))):
                raise ValueError("invalid diagnostic fields")
        except (KeyError, TypeError, ValueError):
            errors.append([f"diagnostic {index}", "malformed analysis diagnostic; re-export evidence"])
            continue
        affected, attribution = set(), "unassigned"
        if diagnostic["address_space"] == meta["default_address_space"]:
            affected = owners_at(address)
            if affected:
                attribution = "body"
            else:
                affected = set().union(*(owners_at(source) for source in sources))
                if affected:
                    attribution = "incoming_flow"
        diagnostics.append({**diagnostic, "function_ids": sorted(affected), "attribution": attribution})
        if diagnostic["severity"] == "error":
            errors.append([diagnostic["address"], f"Ghidra error: {diagnostic['category']}: {diagnostic['message']}"])
            blocked.update(affected)
    return errors, blocked, diagnostics


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("baseline", type=Path)
    p.add_argument("firmware", type=Path)
    p.add_argument("inventory", type=Path)
    p.add_argument("evidence", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    baseline = json.loads(args.baseline.read_text())
    data = args.firmware.read_bytes()
    if len(data) != baseline["bytes"] or hashlib.sha256(data).hexdigest() != baseline["sha256"]:
        raise ValueError("input differs from baseline")
    if (args.evidence / "database-container.bin").read_bytes() != data:
        raise ValueError("Ghidra database byte comparison failed")
    inventory = json.loads(args.inventory.read_text())
    if inventory["baseline_sha256"].lower() != baseline["sha256"] or inventory["language"] != "ARM:LE:32:v5t":
        raise ValueError("wrong inventory identity or language")
    functions = inventory["functions"]
    ownership, errors, blocked, overlap_ranges = check_functions(functions, len(data))
    entries = {int(f["entry"], 16): f for f in functions}
    anchors = {0x2064: "arm", 0x2300: "arm", 0x2320: "arm", 0x19878: "thumb"}
    for entry, mode in anchors.items():
        if entry not in entries or entries[entry]["mode"] != mode:
            errors.append([hex(entry), "anchor entry/mode missing"])
    for address, value in {0x2040: 0x2064, 0x2170: 0x19879, 0x2194: 0x1ed60,
                           0x2198: 0x400020, 0x219c: 0x6f4, 0x21a0: 0x3940,
                           0x21a4: 0x400714}.items():
        if struct.unpack_from("<I", data, address)[0] != value:
            errors.append([hex(address), "anchor word changed"])
    meta = json.loads((args.evidence / "metadata.json").read_text())
    analysis_errors, analysis_blocked, diagnostics = check_diagnostics(meta, functions, ownership)
    errors.extend(analysis_errors)
    blocked.update(analysis_blocked)
    covered = sum(bool(x) for x in ownership)
    overlaps = sum(len(x) > 1 for x in ownership)
    size = lambda fn: sum(int(s["end_exclusive"], 16) - int(s["start"], 16) for s in fn["ranges"])
    report = {
        "status": "structural checks passed; boundaries NOT approved" if not errors else "structural checks FAILED; inventory review BLOCKED",
        "function_count": len(functions), "entry_modes": dict(Counter(f["mode"] for f in functions)),
        "container_denominator": len(data), "payload_denominator": baseline["payload_bytes"],
        "function_body_union_bytes": covered, "overlapping_function_body_bytes": overlaps,
        "overlapping_ranges": overlap_ranges,
        "bytes_outside_function_bodies": len(data) - covered,
        "instruction_count": meta["instruction_count"], "instruction_bytes": meta["instruction_bytes"],
        "defined_data_bytes": meta["defined_data_bytes"], "unclassified_bytes": meta["unclassified_bytes"],
        "computed_flow_instruction_count": meta["computed_flow_instruction_count"],
        "multi_range_functions": sum(len(f["ranges"]) > 1 for f in functions),
        "functions_at_most_four_bytes": sum(size(f) <= 4 for f in functions),
        "largest_functions": [{"entry": f["entry"], "bytes": size(f), "ranges": len(f["ranges"])}
                              for f in sorted(functions, key=size, reverse=True)[:10]],
        "prefix_is_all_ff": data[:0x2000] == b"\xff" * 0x2000,
        "errors": errors,
        "analysis_diagnostics": diagnostics,
        "analysis_error_count": sum(d["severity"] == "error" for d in diagnostics),
        "analysis_warning_count": sum(d["severity"] == "warning" for d in diagnostics),
        "unassigned_analysis_error_count": sum(d["severity"] == "error" and not d["function_ids"] for d in diagnostics),
        "blocked_function_ids": sorted(blocked),
        "matching_coverage": "unknown",
        "notes": ["Body-byte coverage is not recovered-code coverage.",
                  "Defined Ghidra data is not recovered source data.",
                  "Computed flows include returns; count is not an unresolved-call count.",
                  "Incoming-flow attribution identifies review candidates, not approved body ownership.",
                  "Functions absent from the blocked list are not automatically approved.",
                  "Warnings require review; analysis errors block even when outside all function bodies.",
                  "No function tasks or pseudocode were generated."]}
    if args.output.exists():
        raise ValueError("refusing to overwrite review")
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
