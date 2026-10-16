"""Construction tests only: no Wine, GUI, network or device operations."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


DIRECTORY = Path(__file__).resolve().parents[1] / 'decomp/results/preparation'
SPEC = importlib.util.spec_from_file_location('keil_gui_probe', DIRECTORY / 'keil_gui_probe.py')
PROBE = importlib.util.module_from_spec(SPEC)
sys.path.insert(0, str(DIRECTORY))
try:
    SPEC.loader.exec_module(PROBE)
finally:
    sys.path.pop(0)


class KeilGuiProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / '.decomp/armcc-wine-work').mkdir(parents=True)

    def test_default_has_private_network_and_display(self):
        cmd = PROBE.command(self.root)
        self.assertIn('--unshare-all', cmd)
        self.assertNotIn('--share-net', cmd)
        self.assertIn('--clearenv', cmd)
        self.assertIn('--dev', cmd)
        self.assertNotIn('--dev-bind', cmd)
        self.assertIn(':99', cmd)
        self.assertNotIn('/tmp/.X11-unix', cmd)
        self.assertNotIn('ARMLMD_LICENSE_FILE', cmd)
        self.assertNotIn('LM_LICENSE_FILE', cmd)
        self.assertEqual(cmd[-4:], ['/usr/bin/python3', '-u', '/probe.py', '--inside'])

    def test_readonly_compiler_and_persistent_private_prefix(self):
        cmd = PROBE.command(self.root)
        pos = cmd.index(str(self.root / 'ARMCC'))
        self.assertEqual(cmd[pos - 1:pos + 2],
                         ['--ro-bind', str(self.root / 'ARMCC'), '/keil/ARM/ARMCC'])
        pos = cmd.index('WINEPREFIX')
        self.assertEqual(cmd[pos - 1:pos + 2], ['--setenv', 'WINEPREFIX', '/work/prefix-v2'])
        self.assertIn('winemenubuilder.exe,mscoree,mshtml,winebus=d', cmd)

    def test_adapter_probe_requires_filter_fd(self):
        cmd = PROBE.command(self.root, 42)
        self.assertIn('--share-net', cmd)
        pos = cmd.index('--seccomp')
        self.assertEqual(cmd[pos + 1], '42')
        pos = cmd.index('/sys/class/net')
        self.assertEqual(cmd[pos - 1:pos + 2],
                         ['--ro-bind', '/sys/class/net', '/sys/class/net'])
        self.assertNotIn('/sys', cmd)

    def test_network_access_is_explicit_and_does_not_expose_host_devices(self):
        cmd = PROBE.command(self.root, allow_network=True)
        self.assertIn('--share-net', cmd)
        self.assertNotIn('--seccomp', cmd)
        self.assertNotIn('KEIL_REAL_ADAPTERS', cmd)
        self.assertNotIn('--dev-bind', cmd)
        self.assertNotIn('/sys', cmd)

    def test_conflicting_network_options_rejected(self):
        with self.assertRaises(ValueError):
            PROBE.command(self.root, 42, allow_network=True)

    def test_generic_screenshot_probe_rejects_installed_license(self):
        config = self.root / '.decomp/keil-mdk-5.43a/TOOLS.INI'
        config.parent.mkdir()
        config.write_text('[ARM]\nLIC0=SYNTHETIC-TEST-ONLY\n')
        with self.assertRaisesRegex(ValueError, 'no-screenshot'):
            PROBE.command(self.root)
        self.assertIn('--clearenv', PROBE.command(self.root, allow_installed_license=True))


if __name__ == '__main__':
    unittest.main()
