"""Command-construction checks; these tests never execute Wine or ARMCC."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'decomp/results/preparation/wine_probe.py'
SPEC = importlib.util.spec_from_file_location('wine_probe', SCRIPT)
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


class WineProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / '.decomp/armcc-wine-work').mkdir(parents=True)

    def test_default_remains_standalone_and_isolated(self):
        cmd = PROBE.command(self.root)
        self.assertNotIn('ARM_TOOL_VARIANT', cmd)
        self.assertIn('--unshare-all', cmd)
        self.assertIn('--clearenv', cmd)
        self.assertIn('--dev', cmd)
        self.assertNotIn('--dev-bind', cmd)
        self.assertEqual(cmd[-2:], ['Z:\\compiler\\bin\\armcc.exe', '--vsn'])
        self.assertNotIn('ARMLMD_LICENSE_FILE', cmd)
        self.assertNotIn('LM_LICENSE_FILE', cmd)

    def test_explicit_product_selection_only_adds_selector(self):
        default = PROBE.command(self.root)
        for variant in PROBE.TOOL_VARIANTS:
            with self.subTest(variant=variant):
                cmd = PROBE.command(self.root, variant)
                expected = default[:-3] + ['--setenv', 'ARM_TOOL_VARIANT', variant] + default[-3:]
                self.assertEqual(cmd, expected)

    def test_unknown_selector_rejected(self):
        with self.assertRaises(ValueError):
            PROBE.command(self.root, 'arbitrary-value')


if __name__ == '__main__':
    unittest.main()
