"""Secret-handling/command tests: never load an actual LIC or execute Wine."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


DIRECTORY = Path(__file__).resolve().parents[1] / 'decomp/results/preparation'
SPEC = importlib.util.spec_from_file_location('keil_license_check', DIRECTORY / 'keil_license_check.py')
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class LicenseCheckTests(unittest.TestCase):
    def test_scrubs_exact_secret_and_other_full_license_shapes(self):
        key = 'AAAAA-BBBBB-CCCCC-DDDDD-EEEEE-FFFFF'
        value = f'LIC0={key.lower()} other=11111-22222-33333-44444-55555-66666'
        result = CHECK.scrub(value, key)
        self.assertEqual(result, 'LIC0=[REDACTED] other=[REDACTED]')

    def test_public_error_preserves_code_not_key(self):
        key = 'AAAAA-BBBBB-CCCCC-DDDDD-EEEEE-FFFFF'
        proc = subprocess.CompletedProcess([], 1, b'',
            f'Error: C9555E: license LIC0={key} denied\nLICENSE ERROR R203\n'.encode())
        result = CHECK.public_status(proc, key)
        self.assertEqual(result['returncode'], 1)
        self.assertEqual(result['error_codes'], ['C9555E', 'R203'])
        self.assertNotIn(key, str(result))
        self.assertIn('[REDACTED]', str(result))

    def test_cpu_error_is_reported(self):
        proc = subprocess.CompletedProcess([], 1, b'', b'Fatal error: C3903U: cpu not permitted')
        self.assertEqual(CHECK.public_status(proc, '')['error_codes'], ['C3903U'])

    def test_smoke_uses_documented_architecture_replacement_and_links(self):
        success = subprocess.CompletedProcess([], 0, b'', b'')
        with mock.patch.object(CHECK, 'run', return_value=success) as run, \
                mock.patch.object(CHECK.Path, 'is_file', return_value=True), \
                mock.patch('builtins.print'):
            CHECK.compile_check('')
        self.assertEqual(run.call_count, 3)
        compile_argv = run.call_args_list[1].args[0]
        self.assertIn('--cpu=5TE', compile_argv)
        self.assertNotIn('--cpu=ARM968E-S', compile_argv)
        self.assertIn('--thumb', compile_argv)
        self.assertIn('--no_scanlib', run.call_args_list[2].args[0])

    def test_failed_compile_does_not_link_even_if_object_exists(self):
        failure = subprocess.CompletedProcess([], 1, b'', b'Fatal error: C3903U')
        with mock.patch.object(CHECK, 'run', return_value=failure) as run, \
                mock.patch.object(CHECK.Path, 'is_file', return_value=True), \
                mock.patch('builtins.print'):
            CHECK.compile_check('')
        self.assertEqual(run.call_count, 2)

    def test_command_uses_secret_file_not_secret_argument(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / '.decomp/armcc-wine-work').mkdir(parents=True)
            sys.path.insert(0, str(DIRECTORY))
            try:
                cmd = CHECK.command(root)
                active = CHECK.command(root, install=True)
                headless = CHECK.command(root, headless_test=True)
            finally:
                sys.path.pop(0)
            self.assertNotIn('--install-and-test', cmd)
            self.assertEqual(active, cmd + ['--install-and-test'])
            self.assertEqual(headless, cmd + ['--headless-test'])
            self.assertIn('--share-net', cmd)
            self.assertNotIn('--dev-bind', cmd)
            pos = cmd.index(str(root / '.decomp/keil-license.txt'))
            self.assertEqual(cmd[pos - 1:pos + 2],
                             ['--ro-bind', str(root / '.decomp/keil-license.txt'), '/license.txt'])
            pos = cmd.index('/probe.py')
            self.assertEqual(cmd[pos - 1], str(DIRECTORY / 'keil_license_check.py'))
            self.assertIn('/scratch', cmd)

    def test_conflicting_operations_rejected(self):
        with self.assertRaises(ValueError):
            CHECK.command(Path('/unused'), install=True, test_existing=True)
        with self.assertRaises(ValueError):
            CHECK.command(Path('/unused'), install=True, headless_test=True)
        with self.assertRaises(ValueError):
            CHECK.command(Path('/unused'), test_existing=True, headless_test=True)

    def test_headless_mode_does_not_start_gui(self):
        key = 'AAAAA-BBBBB-CCCCC-DDDDD-EEEEE-FFFFF'
        with mock.patch.object(CHECK.Path, 'read_text', return_value=key), \
                mock.patch.object(CHECK.os, 'umask'), \
                mock.patch.object(CHECK, 'compile_check') as compile_check, \
                mock.patch.object(CHECK, 'run') as run, \
                mock.patch.object(CHECK.subprocess, 'Popen') as popen:
            CHECK.inside(False, False, headless_test=True)
        compile_check.assert_called_once_with(key)
        popen.assert_not_called()
        run.assert_called_once_with(['wineserver', '-k'], timeout=10)


if __name__ == '__main__':
    unittest.main()
