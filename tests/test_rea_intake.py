"""Synthetic intake regressions; no Ghidra, firmware, compiler or model jobs."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import prepare_rea_batch as intake
import decomp
import rea_bridge as rea


class LeafAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.raw = b'\x00'*0x20
        self.fn = {'entry':'0x10','end_exclusive':'0x14','instructions':[
            {'address':'0x10','bytes':'0000','text':'b 0x00000012','tmode':1,
             'flow_type':'UNCONDITIONAL_JUMP','flows':['0x12'],'fallthrough':None},
            {'address':'0x12','bytes':'0000','text':'bx lr','tmode':1,
             'flow_type':'TERMINATOR','flows':[]}]}
        self.refs = [{'from':'00000000','to':'00000010','type':'UNCONDITIONAL_CALL'},
                     {'from':'00000010','to':'00000012','type':'UNCONDITIONAL_JUMP'}]

    def check(self, fn=None, refs=None):
        return intake.validate_leaf(fn or self.fn,0x10,0x14,self.raw,refs or self.refs)

    def test_internal_branch_and_omitted_null_fallthrough_are_supported(self):
        incoming,outgoing=self.check()
        self.assertEqual(len(incoming),1)
        self.assertEqual(len(outgoing),1)

    def test_escaping_control_calls_bad_mode_bytes_and_incomplete_body_fail(self):
        for change in ({'flows':['0x14']},{'fallthrough':'0x14'},
                       {'flow_type':'UNCONDITIONAL_CALL'},{'tmode':0},{'bytes':'0100'},
                       {'text':'ldr r0,[r1]'}, {'text':'mov r0,pc'}, {'address':'0x11'}):
            fn=copy.deepcopy(self.fn);fn['instructions'][0].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):self.check(fn)
        fn=copy.deepcopy(self.fn);fn['instructions'].pop()
        with self.assertRaises(ValueError):self.check(fn)

    def test_offcut_and_data_references_fail(self):
        for change in ({'to':'00000012'},{'type':'DATA'}):
            refs=copy.deepcopy(self.refs);refs[0].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):self.check(refs=refs)
        refs=copy.deepcopy(self.refs);refs[1]['to']='00000018'
        with self.assertRaises(ValueError):self.check(refs=refs)

    def test_pointer_store_shape_cannot_construct_absolute_address(self):
        fn={'entry':'0x11e38','end_exclusive':'0x11e3c','instructions':[
            {'address':'0x11e38','bytes':'0000','text':'strb r1,[r0,#0x0]','tmode':1,
             'flow_type':'FALL_THROUGH','flows':[],'fallthrough':'0x11e3a'},
            {'address':'0x11e3a','bytes':'0000','text':'bx lr','tmode':1,
             'flow_type':'TERMINATOR','flows':[]}]}
        raw=b'\x00'*0x11e3c
        refs=[{'from':'00000000','to':'00011e38','type':'UNCONDITIONAL_CALL'}]
        intake.validate_leaf(fn,0x11e38,0x11e3c,raw,refs)
        for text in ('lsl r0,r0,#0x17','mov r0,#0x1','str r1,[r0,#0x0]','strb r1,[r3,#0x0]'):
            fn['instructions'][0]['text']=text
            with self.subTest(text=text),self.assertRaises(ValueError):
                intake.validate_leaf(fn,0x11e38,0x11e3c,raw,refs)


class BatchContractTests(unittest.TestCase):
    def test_selected_tasks_are_exactly_new_leaf_assignments(self):
        _,tasks=decomp.load_tasks(ROOT)
        proposal=json.loads((ROOT/'decomp/proposals/batch-4-leaves.json').read_text())
        selected={int(t['entry'],16) for t in proposal['functions']}
        self.assertEqual(selected,intake.ENTRIES)
        self.assertEqual(sum(int(t['ranges'][0]['end_exclusive'],16)-int(t['entry'],16)
                             for t in proposal['functions']),94)
        for task in proposal['functions']:
            self.assertEqual(task,tasks[task['id']])
            self.assertEqual(task['comparison_scope'],'armcc5-leaf-feedback-v1')
            self.assertFalse(task.get('calls'))
            self.assertNotIn(task['id'],('fn_000112b0','fn_0000be60','fn_00006464','fn_00006500'))
        # Independent flags and quota values remain the original user policy.
        policy=json.loads((ROOT/'decomp/swarm-policy.json').read_text())
        self.assertEqual([policy[k] for k in ('stop_remaining_percent','work_reserve_percent',
            'maximum_concurrent_workers','maximum_task_seconds','maximum_compile_attempts',
            'maximum_non_improving_attempts')],[45,40,2,1200,8,3])

    def test_frozen_batch_and_qualification_identity(self):
        policy=json.loads((ROOT/'decomp/swarm-policy.json').read_text())
        data=(ROOT/policy['batch']['path']).read_bytes()
        self.assertEqual(rea.digest(data),policy['batch']['sha256'])
        batch=json.loads(data)
        for pin in batch['qualification'].values():
            proof=(ROOT/pin['path']).read_bytes()
            self.assertEqual(rea.digest(proof),pin['sha256'])
            evidence=json.loads(proof)
            self.assertFalse(evidence['certified_match'])
            self.assertTrue(all(r['passed'] for r in evidence['results']))
        self.assertFalse(batch['call_contracts'])


class RetainedEvidenceTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='rea-intake-test-')
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        (self.root/'tools').mkdir()
        (self.root/'tools/rea_bridge.py').write_text('synthetic runner')
        self.run='.decomp/rea/runs/fixture'
        self.directory=self.root/self.run;self.directory.mkdir(parents=True)
        self.config={'baseline_sha256':'a'*64}
        profile={'config_sha256':rea.digest(rea.canonical(self.config)),
                 'runner_sha256':rea.digest(b'synthetic runner'),'entry_selection':['0x10']}
        self.report={'status':'observed','source_project_unchanged':True,'certified_match':False,
                     'configuration':self.config,'profile':profile,'profile_sha256':rea.digest(rea.canonical(profile)),
                     'admission':{'sha256':'a'*64},'observations':[]}
        for method in rea.METHODS:
            name='00000010-'+method+'.json'
            (self.directory/name).write_text('{}')
            self.report['observations'].append({'entry':'0x10','method':method,'path':name,'sha256':rea.digest(b'{}')})
        self.save()

    def save(self):
        (self.directory/'report.json').write_text(json.dumps(self.report))

    def test_complete_bound_observations_admitted(self):
        directory,report,digest=intake.retained(self.root,self.run,self.config)
        self.assertEqual(directory,self.directory)
        self.assertEqual(report,self.report)
        self.assertEqual(len(digest),64)

    def test_missing_duplicate_changed_observations_and_profile_fail(self):
        original=copy.deepcopy(self.report)
        self.report['observations'].pop();self.save()
        with self.assertRaises(ValueError):intake.retained(self.root,self.run,self.config)
        self.report=copy.deepcopy(original)
        self.report['observations'].append(self.report['observations'][0]);self.save()
        with self.assertRaises(ValueError):intake.retained(self.root,self.run,self.config)
        self.report=copy.deepcopy(original);self.report['profile_sha256']='0'*64;self.save()
        with self.assertRaises(ValueError):intake.retained(self.root,self.run,self.config)
        self.report=copy.deepcopy(original);self.save()
        (self.directory/self.report['observations'][0]['path']).write_text('{"changed":true}')
        with self.assertRaises(ValueError):intake.retained(self.root,self.run,self.config)


if __name__=='__main__':unittest.main()
