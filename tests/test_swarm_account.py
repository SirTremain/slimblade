"""Fake account RPC tests; no account access, inference or credentials."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import swarm_account as sa


def command(account_type='chatgpt'):
    program = '''import json,sys
for line in sys.stdin:
    msg=json.loads(line)
    if 'id' not in msg: continue
    results={'initialize':{}, 'account/read':{'account':{'type':%r}},
             'account/rateLimits/read':{'rateLimits':{'limitId':'codex','primary':
                 {'usedPercent':20,'windowDurationMins':10080,'resetsAt':1999999999}}}}
    print(json.dumps({'id':msg['id'],'result':results[msg['method']]}),flush=True)
''' % account_type
    return [sys.executable, '-c', program]


class AccountTests(unittest.TestCase):
    def test_chatgpt_quota_and_request_allowlist(self):
        with sa.Account(command=command()) as account:
            self.assertEqual(account.snapshot()['remaining_percent'], 80)
            with self.assertRaises(ValueError):
                account.request('turn/start', {})

    def test_api_key_account_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'API billing'):
            with sa.Account(command=command('apiKey')):
                self.fail('API account accepted')

    def test_rpc_timeout_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, 'timed out'):
            with sa.Account(timeout=0.1, command=[sys.executable, '-c',
                                                 'import time;time.sleep(60)']):
                self.fail('missing RPC accepted')

    def test_startup_failure_latches_pause(self):
        with tempfile.TemporaryDirectory(prefix='slimblade-account-test-') as temp:
            state = Path(temp)
            with patch.object(sa.Account, '__enter__', side_effect=RuntimeError('unavailable')):
                with self.assertRaises(RuntimeError):
                    with sa.monitored_account(state, 1999999999):
                        self.fail('account failure launched work')
            self.assertTrue(json.loads((state / 'PAUSED.json').read_text())[
                            'explicit_user_resume_required'])


if __name__ == '__main__':
    unittest.main()
