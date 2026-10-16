"""Synthetic boundary and dependency controls; no stock bytes needed."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import prepare_pilot as p


class PilotBoundaryTests(unittest.TestCase):
    def setUp(self):
        # Synthetic two-instruction leaf, not extracted firmware.
        self.raw = b"\x01\x30\x70\x47"
        self.fn = {"entry": "0x0", "end_exclusive": "0x4", "instructions": [
            {"address": "0x0", "bytes": "0130", "text": "add r0,#1", "tmode": 1,
             "flow_type": "FALL_THROUGH", "flows": [], "fallthrough": "0x2"},
            {"address": "0x2", "bytes": "7047", "text": "bx lr", "tmode": 1,
             "flow_type": "COMPUTED_JUMP", "flows": []}]}
        self.refs = [{"from": "00000010", "to": "00000000", "type": "UNCONDITIONAL_CALL"}]

    def test_contiguous_leaf(self):
        self.assertEqual(len(p.check_leaf(self.fn, 0, 4, self.raw, self.refs)[0]), 1)

    def test_wrong_mode_bytes_and_flow(self):
        for key, value in (("tmode", 0), ("bytes", "0230"), ("flow_type", "UNCONDITIONAL_CALL"),
                           ("flows", ["0x10"]), ("fallthrough", "0x10")):
            fn = copy.deepcopy(self.fn)
            fn["instructions"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                p.check_leaf(fn, 0, 4, self.raw, self.refs)

    def test_offcut_and_outgoing_dependencies(self):
        for ref in ({"from": "00000010", "to": "00000002", "type": "UNCONDITIONAL_CALL"},
                    {"from": "00000000", "to": "00800000", "type": "READ"}):
            with self.assertRaises(ValueError):
                p.check_leaf(self.fn, 0, 4, self.raw, self.refs + [ref])

    def test_no_external_entry_evidence(self):
        with self.assertRaises(ValueError):
            p.check_leaf(self.fn, 0, 4, self.raw, [])


if __name__ == "__main__":
    unittest.main()
