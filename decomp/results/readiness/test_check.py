"""Synthetic negative controls for the readiness delta checker."""
import copy
import unittest
import check


class ReadinessChecks(unittest.TestCase):
    def inventories(self):
        functions = [{"id": key, "entry": ranges[0]["start"], "mode": "thumb",
                      "ranges": [{"start": ranges[0]["start"], "end_exclusive": ranges[0]["start"]}]}
                     for key, ranges in check.CHANGED_BODIES.items()]
        functions.append({"id": "other", "entry": "0x2200", "mode": "arm", "ranges": []})
        before = {"language": "synthetic", "functions": functions}
        after = copy.deepcopy(before)
        for fn in after["functions"]:
            if fn["id"] in check.CHANGED_BODIES:
                fn["ranges"] = copy.deepcopy(check.CHANGED_BODIES[fn["id"]])
        return before, after

    def test_only_expected_delta_passes(self):
        check.check_inventory(*self.inventories())

    def test_unrelated_function_change_fails(self):
        before, after = self.inventories()
        after["functions"][-1]["mode"] = "thumb"
        with self.assertRaisesRegex(ValueError, "unexpected function change"):
            check.check_inventory(before, after)

    def test_wrong_repaired_boundary_fails(self):
        before, after = self.inventories()
        after["functions"][0]["ranges"][0]["end_exclusive"] = "0x4028"
        with self.assertRaisesRegex(ValueError, "unexpected function change"):
            check.check_inventory(before, after)

    def test_wrong_identity_fails(self):
        before, after = self.inventories()
        after["language"] = "other"
        with self.assertRaisesRegex(ValueError, "metadata changed"):
            check.check_inventory(before, after)

    def test_duplicate_function_fails(self):
        before, after = self.inventories()
        after["functions"].append(copy.deepcopy(after["functions"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate ID"):
            check.check_inventory(before, after)

    def test_removed_function_fails(self):
        before, after = self.inventories()
        after["functions"].pop()
        with self.assertRaisesRegex(ValueError, "function set changed"):
            check.check_inventory(before, after)

    def test_delta_address_limits(self):
        for address in (0x4000, 0x401d, 0xa1d4, 0xa1d7):
            self.assertTrue(check.changed_address(address))
        for address in (0x3ffe, 0x401e, 0xa1d2, 0xa1d8, 0x1e480):
            self.assertFalse(check.changed_address(address))

    def test_runtime_helper_anchor_gate(self):
        with self.assertRaisesRegex(ValueError, "runtime helper anchor changed"):
            check.runtime_dispatch(bytes(128112), [], [])


if __name__ == "__main__":
    unittest.main()
