"""Inventory review controls using fabricated bytes only; no Ghidra required."""

import copy
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "decomp/results/bootstrap-inventory/review.py"


def function(entry, mode="arm", length=4):
    return {"id": f"fn_{entry:08x}", "entry": hex(entry), "mode": mode,
            "ranges": [{"start": hex(entry), "end_exclusive": hex(entry + length)}]}


def diagnostic(address=0x2064, severity="error", sources=(), space="ram"):
    return {"address": hex(address), "address_space": space, "severity": severity,
            "category": "Bad Instruction", "message": "Synthetic instruction conflict",
            "flow_sources": [hex(source) for source in sources]}


class InventoryReviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="slimblade-inventory-test-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        # Only documented anchor words are populated; this is not firmware.
        data = bytearray(128112)
        for address, value in {0x2040: 0x2064, 0x2170: 0x19879, 0x2194: 0x1ed60,
                               0x2198: 0x400020, 0x219c: 0x6f4, 0x21a0: 0x3940,
                               0x21a4: 0x400714}.items():
            struct.pack_into("<I", data, address, value)
        digest = hashlib.sha256(data).hexdigest()
        (self.root / "firmware.bin").write_bytes(data)
        (self.root / "database-container.bin").write_bytes(data)
        (self.root / "baseline.json").write_text(json.dumps(
            {"bytes": len(data), "sha256": digest, "payload_bytes": len(data) - 8192}))
        self.inventory = {"baseline_sha256": digest, "language": "ARM:LE:32:v5t",
                          "functions": [function(0x2064), function(0x2300), function(0x2320),
                                        function(0x19878, "thumb", 2)]}
        self.meta = {"schema_version": 2, "default_address_space": "ram", "analysis_diagnostics": [],
                     "instruction_count": 0, "instruction_bytes": 0, "defined_data_bytes": 0,
                     "unclassified_bytes": len(data), "computed_flow_instruction_count": 0}

    def review(self, success):
        (self.root / "inventory.json").write_text(json.dumps(self.inventory))
        (self.root / "metadata.json").write_text(json.dumps(self.meta))
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.root / "baseline.json"),
             str(self.root / "firmware.bin"), str(self.root / "inventory.json"),
             str(self.root), str(self.root / "report.json")],
            capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0 if success else 1, result.stdout + result.stderr)
        report = json.loads((self.root / "report.json").read_text())
        self.assertEqual(bool(report["errors"]), not success)
        self.assertEqual(report["matching_coverage"], "unknown")
        return report

    def test_clean_inventory_is_not_boundary_approval(self):
        report = self.review(True)
        self.assertIn("boundaries NOT approved", report["status"])
        self.assertEqual(report["blocked_function_ids"], [])
        self.assertEqual(report["analysis_error_count"], 0)

    def test_duplicate_entire_row_fails(self):
        self.inventory["functions"].append(copy.deepcopy(self.inventory["functions"][0]))
        report = self.review(False)
        self.assertEqual(report["overlapping_function_body_bytes"], 4)
        self.assertIn("duplicate function ID", str(report["errors"]))
        self.assertIn("duplicate function entry", str(report["errors"]))

    def test_duplicate_id_with_disjoint_bodies_fails(self):
        self.inventory["functions"][1]["id"] = "fn_00002064"
        report = self.review(False)
        self.assertEqual(report["overlapping_function_body_bytes"], 0)
        self.assertIn("duplicate function ID", str(report["errors"]))

    def test_duplicate_entry_is_numeric_not_string_comparison(self):
        extra = copy.deepcopy(self.inventory["functions"][0])
        extra.update(id="different_id", entry="0x00002064")
        self.inventory["functions"].append(extra)
        report = self.review(False)
        self.assertIn("duplicate function entry", str(report["errors"]))
        self.assertEqual(report["blocked_function_ids"], ["different_id", "fn_00002064"])

    def test_partial_overlap_fails_with_addresses_and_both_owners(self):
        self.inventory["functions"].append(function(0x2066, "thumb"))
        report = self.review(False)
        self.assertEqual(report["overlapping_function_body_bytes"], 2)
        self.assertEqual(report["overlapping_ranges"], [
            {"start": "0x2066", "end_exclusive": "0x2068", "rows": [0, 4],
             "function_ids": ["fn_00002064", "fn_00002066"]}])

    def test_overlapping_ranges_within_one_function_fail(self):
        self.inventory["functions"][0]["ranges"].append(
            {"start": "0x2066", "end_exclusive": "0x2068"})
        report = self.review(False)
        self.assertEqual(report["overlapping_function_body_bytes"], 2)
        self.assertEqual(report["blocked_function_ids"], ["fn_00002064"])

    def test_adjacent_ranges_do_not_overlap(self):
        self.inventory["functions"][0]["ranges"].append(
            {"start": "0x2068", "end_exclusive": "0x206c"})
        self.inventory["functions"].append(function(0x206c))
        self.assertEqual(self.review(True)["overlapping_ranges"], [])

    def test_conflict_inside_body_blocks_function(self):
        self.meta["analysis_diagnostics"] = [diagnostic(0x2066)]
        report = self.review(False)
        self.assertEqual(report["analysis_error_count"], 1)
        self.assertEqual(report["blocked_function_ids"], ["fn_00002064"])
        self.assertEqual(report["analysis_diagnostics"][0]["attribution"], "body")

    def test_error_at_exclusive_end_uses_incoming_flow(self):
        self.meta["analysis_diagnostics"] = [diagnostic(0x2068, sources=[0x2064])]
        report = self.review(False)
        self.assertEqual(report["blocked_function_ids"], ["fn_00002064"])
        self.assertEqual(report["analysis_diagnostics"][0]["attribution"], "incoming_flow")
        self.assertEqual(report["unassigned_analysis_error_count"], 0)

    def test_unassigned_error_still_fails_global_review(self):
        self.meta["analysis_diagnostics"] = [diagnostic(0x2068)]
        report = self.review(False)
        self.assertEqual(report["unassigned_analysis_error_count"], 1)
        self.assertEqual(report["blocked_function_ids"], [])

    def test_other_address_space_does_not_alias_function(self):
        self.meta["analysis_diagnostics"] = [diagnostic(space="other")]
        report = self.review(False)
        self.assertEqual(report["unassigned_analysis_error_count"], 1)
        self.assertEqual(report["blocked_function_ids"], [])

    def test_warning_is_visible_but_not_error(self):
        self.meta["analysis_diagnostics"] = [diagnostic(severity="warning")]
        report = self.review(True)
        self.assertEqual(report["analysis_warning_count"], 1)
        self.assertEqual(report["analysis_diagnostics"][0]["function_ids"], ["fn_00002064"])
        self.assertEqual(report["blocked_function_ids"], [])

    def test_legacy_evidence_fails_closed(self):
        del self.meta["schema_version"]
        del self.meta["analysis_diagnostics"]
        self.assertIn("re-export", str(self.review(False)["errors"]))

    def test_missing_diagnostics_fails_closed(self):
        del self.meta["analysis_diagnostics"]
        self.assertIn("re-export", str(self.review(False)["errors"]))

    def test_unknown_schema_fails_closed(self):
        self.meta["schema_version"] = 3
        self.assertIn("version-mismatched", str(self.review(False)["errors"]))

    def test_malformed_diagnostic_fails_closed(self):
        self.meta["analysis_diagnostics"] = [None]
        self.assertIn("malformed", str(self.review(False)["errors"]))

    def test_missing_flow_evidence_fails_closed(self):
        item = diagnostic()
        del item["flow_sources"]
        self.meta["analysis_diagnostics"] = [item]
        self.assertIn("malformed", str(self.review(False)["errors"]))

    def test_unknown_severity_cannot_hide_error(self):
        self.meta["analysis_diagnostics"] = [diagnostic(severity="ignored")]
        self.assertIn("malformed", str(self.review(False)["errors"]))


if __name__ == "__main__":
    unittest.main()
