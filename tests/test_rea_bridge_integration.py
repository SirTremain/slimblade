"""Opt-in local Ghidra controls. Never starts models, compiler or hardware.

SLIMBLADE_REA_INTEGRATION=1 python3 -m unittest discover -s tests -p test_rea_bridge_integration.py -v
"""
import json
import os
from pathlib import Path
import secrets
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import rea_bridge as rea


@unittest.skipUnless(os.environ.get('SLIMBLADE_REA_INTEGRATION') == '1',
                     'explicit opt-in and pinned local artifacts required')
class SavedProjectControls(unittest.TestCase):
    def setUp(self):
        self.output = '.decomp/rea/runs/control-' + self._testMethodName + '-' + secrets.token_hex(4)

    def test_positive_corrected_project(self):
        result = rea.analyze(ROOT, ['0xbe60', '0x112b0', '0x1e4f0', '0x1e150', '0x1e420'], self.output, 60)
        self.assertEqual(result['status'], 'observed')
        self.assertTrue(result['source_project_unchanged'])
        self.assertFalse(result['certified_match'])
        report = json.loads((ROOT / self.output / 'report.json').read_text())
        self.assertEqual(len(report['observations']), 15)
        self.assertEqual(report['admission']['functions_checked'], 776)
        view = rea.inspect(ROOT, self.output, '0xbe60', 'assembly')
        self.assertEqual(view['value'], ['0xbe60: push {r4,lr}', '0xbe62: bl 0x0000bd7c',
                                         '0xbe66: mov r0, #0x0', '0xbe68: pop {r4,pc}'])
        for address in ('0x1e150', '0x1e420'):
            value = rea.inspect(ROOT, self.output, address, 'pseudocode')['value']
            self.assertIn('slimblade_v449_runtime', value)
        print('\nREA retained positive control:', self.output, flush=True)

    def reject(self, field, replacement, diagnostic):
        original = rea.write_json
        def wrong_expectation(path, value):
            if path.name == 'admission.json':
                value = dict(value, **{field: replacement})
            original(path, value)
        # Alter ONLY this disposable run's expected admission, not pins or firmware.
        with patch.object(rea, 'write_json', side_effect=wrong_expectation):
            with self.assertRaises(ValueError):
                rea.analyze(ROOT, ['0xbe60'], self.output, 30)
        report = json.loads((ROOT / self.output / 'report.json').read_text())
        self.assertEqual(report['status'], 'failed')
        self.assertTrue(report['source_project_unchanged'])
        self.assertFalse(report['observations'])
        self.assertIn(diagnostic, (ROOT / self.output / 'ghidra.log').read_text())
        print('\nREA retained negative control:', self.output, flush=True)

    def test_wrong_baseline(self):
        self.reject('baseline_sha256', '0'*64, 'database bytes differ from baseline')

    def test_wrong_runtime_model(self):
        self.reject('runtime_xml', '<wrong-runtime-model/>', 'runtime model changed')
