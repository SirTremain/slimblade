#!/usr/bin/env python3
"""Check all pilot packets/locks and reject six deliberately wrong C probes.

Probes are negative fixtures, not reconstruction attempts or recovered source.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import decomp
import stock_compare as sc


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    root = args.root.resolve()
    baseline, tasks = decomp.load_tasks(root)
    args.output.mkdir(parents=True, exist_ok=False)
    results = []
    for task in tasks.values():
        if task.get("comparison_scope") != sc.SCOPE:
            continue
        decomp.evidence_check(root, baseline, task)
        candidate = args.output / (task["id"] + "-negative.c")
        candidate.write_text(f"unsigned int {task['id']}(void) {{ return 0u; }}\n")
        c = task["comparison"]
        result = sc.verify(root / c["lock_path"], c["lock_sha256"], task["id"], candidate,
                           args.output / task["id"])
        sc.require(result["result"] == "mismatch" and not result["certified_match"], "wrong probe accepted")
        results.append({"task": task["id"], "packet_verified": True, "wrong_candidate_rejected": True,
                        "comparison": result})
    sc.require(len(results) == 6, "expected six reviewed pilot leaves")
    report = {"scope": "pilot-readiness-controls", "passed": True, "checks": results,
              "stock_c_reconstructed": 0, "matching_coverage": "unknown"}
    (args.output / "checks.json").write_bytes(sc.encode(report))
    print("Six packets and locks verified; six wrong real-stock candidates rejected; no stock C recovered.")


if __name__ == "__main__":
    main()
