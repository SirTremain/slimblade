import copy
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1]/'decomp/results/preparation/runtime_model.py'
SPEC = importlib.util.spec_from_file_location('runtime_model', PATH)
MODEL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODEL)


class RuntimeModelTests(unittest.TestCase):
    def test_local_continuation_restores_outer_lr(self):
        index, selector, r = MODEL.model(0x1e360,[0,0,0,0,0,0,0],0x2101)
        self.assertEqual((index,selector,r['pc'],r['lr'],r['sp'],r['TMode']),
                         (0,1,0x1e36c,0x2101,0x400810,0))

    def test_nan_returns_through_stack_not_inline_word(self):
        index, selector, r = MODEL.model(0x1e360,[0,0x7ff80000,0,0,0,0,0],0x2101)
        self.assertEqual((index,selector,r['pc'],r['lr'],r['r0'],r['r1'],r['TMode']),
                         (8,6,0x2100,0x1e368,0,0x7ff80000,1))

    def test_second_caller_uses_distinct_dispatch(self):
        index, selector, r = MODEL.model(0x1e47c,[0,0x7ff80000,0,0,0,0,0],0x2101)
        self.assertEqual((index,selector,r['pc'],r['lr'],r['TMode']), (8,0,0x1e484,0x2101,0))

    def fixture(self):
        inputs = [0]*7
        index, selector, result = MODEL.model(0x1e360,inputs,0x2100)
        row = dict(call=0x1e360,inputs=inputs,saved_return=0x2100,index=index,selector=selector,result=result)
        return dict(baseline_sha256=MODEL.BASELINE,cases=[row],injected_analysis_model=False)

    def test_changed_register_flag_stack_and_exit_are_rejected(self):
        for key in ('r0','r1','r4','r5','r6','r12','sp','lr','pc','CY','OV','NG','ZR','TMode'):
            with self.subTest(key=key):
                report = self.fixture()
                report['cases'][0]['result'][key] ^= 1
                with self.assertRaises(ValueError): MODEL.verify(report)

    def test_injected_does_not_substitute_for_original(self):
        report = self.fixture(); injected = copy.deepcopy(report)
        injected['injected_analysis_model'] = True
        self.assertTrue(MODEL.verify(report,injected)['injected_model_compared'])
        with self.assertRaises(ValueError): MODEL.verify(injected)
        injected['cases'][0]['result']['sp'] += 4
        with self.assertRaises(ValueError): MODEL.verify(report,injected)

    def test_wrong_baseline_rejected(self):
        report = self.fixture(); report['baseline_sha256'] = '0'*64
        with self.assertRaises(ValueError): MODEL.verify(report)


if __name__ == '__main__': unittest.main()
