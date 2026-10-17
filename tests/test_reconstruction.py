"""Synthetic broader-workflow contracts; no firmware/model/compiler/device use."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import decomp
import reconstruction as rc
import swarm_runtime as sr


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.base = {'sha256': 'a'*64, 'bytes': 32}
        self.ledger = {'schema_version': 1, 'baseline_sha256': 'a'*64, 'baseline_bytes': 32,
            'regions': [{'id': 'all', 'start': '0x0', 'end_exclusive': '0x20',
                         'treatment': 'unresolved', 'evidence': 'synthetic fixture'}],
            'dependencies': [{'id': 'callee', 'state': 'observed_not_reconstructed',
                'address_space': 'container', 'addresses': ['0x10'], 'required_for_hardware': True,
                'evidence': 'synthetic call', 'next_action': 'review callee'}]}

    def test_complete_denominator_and_no_certification(self):
        self.assertIn('callee', rc.validate_ledger(self.ledger, self.base))
        for field, value in [('start', '0x1'), ('end_exclusive', '0x1f'),
                             ('end_exclusive', '0x21'), ('treatment', 'reconstructed')]:
            bad = copy.deepcopy(self.ledger); bad['regions'][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                rc.validate_ledger(bad, self.base)
        self.ledger['regions'] *= 2
        with self.assertRaises(ValueError):
            rc.validate_ledger(self.ledger, self.base)

    def test_dependencies_keep_address_spaces_and_unknowns_explicit(self):
        for field, value in [('state', 'reconstructed'), ('address_space', 'guessed'),
                             ('addresses', ['0x400000']), ('next_action', '')]:
            bad = copy.deepcopy(self.ledger); bad['dependencies'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                rc.validate_ledger(bad, self.base)
        self.ledger['dependencies'][0].update(address_space='ram', addresses=['0x400000'])
        rc.validate_ledger(self.ledger, self.base)

    def test_real_ledger_covers_reference_without_private_artifacts(self):
        baseline = decomp.read_json(ROOT / 'decomp/baseline.json')
        rc.validate_ledger(decomp.read_json(ROOT / 'decomp/reconstruction.json'), baseline)


class BatchTests(LedgerTests):
    def setUp(self):
        super().setUp()
        temp = tempfile.TemporaryDirectory(prefix='slimblade-batch-contract-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        scope = 'armcc5-direct-call-experiment-v1'
        self.tasks = {'fn_00000000': {'id': 'fn_00000000', 'kind': 'function',
            'comparison_scope': scope, 'comparison': {'lock_path': '.decomp/profile.json', 'lock_sha256': 'f'*64}, 'extern_functions': {
                'fn_00000010': {'entry': '0x10', 'mode': 'thumb', 'signature': 'void (void)'}}}}
        profile = self.write('.decomp/profile.json', {'synthetic':True})
        self.batch = {'schema_version': 1, 'id': 'synthetic', 'status': 'prepared',
            'baseline_sha256': 'a'*64, 'reviewer': 'fixture', 'review_note': 'Synthetic contract only',
            'ledger': self.write('decomp/ledger.json', self.ledger),
            'tasks': {t: decomp.digest(decomp.canonical(v)) for t,v in self.tasks.items()},
            'profile_locks': {scope: profile},
            'qualification': {scope: self.write('.decomp/qualification.json', {
                'call_lock_sha256': profile['sha256'],
                'scope': 'bounded-stock-thumb-call-qualification', 'certified_match': False,
                'results': [dict(control='fixture/'+label, result=result, passed=True)
                    for label,result in [('candidate','exact-range-bytes'),
                                         ('independent-rebuild','exact-range-bytes'), ('negative','mismatch')]]})},
            'call_contracts': [{'caller': 'fn_00000000', 'callee': 'fn_00000010',
                'dependency': 'callee', 'treatment': 'fixed_address_not_reconstructed',
                **{f:'synthetic evidence' for f in ('arguments','return_value','register_clobbers','memory_effects','evidence')}}]}

    def write(self, name, value):
        path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        return {'path': name, 'sha256': decomp.digest(path.read_bytes())}

    def check(self, batch=None, local=False):
        pin = self.write('decomp/batches/fixture.json', self.batch if batch is None else batch)
        with patch.object(decomp, 'load_tasks', return_value=(self.base,self.tasks)), \
                patch('armcc_calls.load_lock', return_value=({'extension':'synthetic'}, {'parent':'synthetic'})), \
                patch.object(decomp, 'evidence_check') as evidence:
            result = rc.load_batch(self.root, pin, local=local)
            self.assertEqual(evidence.call_count, int(local))
            return result

    def test_validated_intake_does_not_create_queue_or_start_anything(self):
        self.check(local=True)
        self.assertFalse((self.root / '.decomp/queue.sqlite3').exists())
        self.assertFalse((self.root / '.decomp/swarm').exists())

    def test_missing_changed_or_extra_contracts_fail_closed(self):
        cases = []
        for change in ({'call_contracts': []}, {'tasks': {}}, {'status': 'draft'},
                       {'baseline_sha256': 'b'*64}, {'qualification': {}}):
            cases.append({**self.batch, **change})
        for field, value in [('register_clobbers',''), ('treatment','reconstructed'),
                             ('dependency','missing'), ('callee','fn_00000012')]:
            bad = copy.deepcopy(self.batch); bad['call_contracts'][0][field] = value; cases.append(bad)
        bad = copy.deepcopy(self.batch); bad['call_contracts'] *= 2; cases.append(bad)
        bad = copy.deepcopy(self.batch); bad['tasks']['fn_00000000']='0'*64; cases.append(bad)
        for batch in cases:
            with self.subTest(batch=batch), self.assertRaises(ValueError):
                self.check(batch)

    def test_qualification_requires_positive_rebuild_and_negative_evidence(self):
        scope = next(iter(self.batch['qualification']))
        for result in ({'certified_match':True,'results':[{'passed':True}]},
                       {'certified_match':False,'results':[{'passed':False}]},
                       {'certified_match':False,'results':[{'passed':True}]}):
            self.batch['qualification'][scope] = self.write('.decomp/bad.json', result)
            with self.assertRaises(ValueError):
                self.check()

    def test_pins_reject_mutation_traversal_and_symlinks(self):
        pin = self.write('data.json', {'x':1})
        (self.root/'data.json').write_text('{}')
        with self.assertRaises(ValueError): rc.pinned_file(self.root,pin)
        with self.assertRaises(ValueError): rc.pinned_file(self.root,{'path':'../escape','sha256':'0'*64})
        (self.root/'link').symlink_to(self.root/'data.json')
        with self.assertRaises(ValueError): rc.pinned_file(self.root,{'path':'link','sha256':'0'*64})

    def test_dynamic_batch_requires_gate_policy_agreement(self):
        pin = self.write('decomp/batches/fixture.json', self.batch)
        policy = decomp.read_json(ROOT/'decomp/swarm-policy.json')
        policy.update(scope='reviewed-batch-v1', batch=pin, quota_window_resets_at=1999999999)
        self.write('decomp/swarm-policy.json',policy)
        self.write('decomp/preparation.json',{'schema_version':1,'ready':True,'batch':pin,'allowed_function_ids':list(self.tasks)})
        with patch.object(rc,'load_batch',return_value=self.batch):
            sr.policy(self.root,'fn_00000000')
            with self.assertRaisesRegex(ValueError,'outside selected'):
                sr.policy(self.root,'fn_00000002')
            self.write('decomp/preparation.json',{'schema_version':1,'ready':False,'batch':pin,'allowed_function_ids':list(self.tasks)})
            with self.assertRaisesRegex(ValueError,'gate/policy'):
                sr.policy(self.root,'fn_00000000')

    def test_local_admission_rejects_changed_qualified_profile(self):
        pin = self.write('decomp/batches/fixture.json', self.batch)
        for changed in ({'extension':'changed'}, {'extension':'synthetic'}):
            parent = {'parent':'synthetic'} if changed['extension']=='changed' else {'parent':'changed'}
            with patch.object(decomp,'load_tasks',return_value=(self.base,self.tasks)), \
                    patch.object(decomp,'evidence_check'), \
                    patch('armcc_calls.load_lock',side_effect=[({'extension':'synthetic'},{'parent':'synthetic'}),(changed,parent)]):
                with self.assertRaisesRegex(ValueError,'profile differs'):
                    rc.load_batch(self.root,pin,local=True)

    def test_plan_never_reclaims_reviewed_or_blocked_tasks(self):
        pin = self.write('decomp/batches/fixture.json', self.batch)
        self.tasks['fn_00000000']['depends_on'] = []
        for state in ('reviewed','blocked','claimed','submitted'):
            with patch.object(rc,'load_batch',return_value=self.batch), \
                    patch.object(decomp,'load_tasks',return_value=(self.base,self.tasks)), \
                    patch.object(rc,'read_states',return_value={'fn_00000000':{'state':state}}):
                plan=rc.batch_plan(self.root,pin)
                self.assertEqual(plan['tasks']['fn_00000000'],state)
                self.assertEqual(plan['model_jobs_started'],0)


if __name__ == '__main__':
    unittest.main()
