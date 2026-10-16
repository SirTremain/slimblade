#!/usr/bin/env python3
"""Explicit, tiny synthetic worker exercise; no firmware task or queue claim.

Default only checks CLI startup/authentication in the actual worker namespace.
--model-smoke explicitly requests one bounded Luna turn with synthetic inputs.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

TOOLS = Path(__file__).resolve().parents[3] / 'tools'
sys.path.insert(0, str(TOOLS))
import swarm_runtime as sr
from swarm_account import Account


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model-smoke', action='store_true')
    args = parser.parse_args()
    sr.require(not args.output.exists(), 'fresh smoke output required')
    args.output.mkdir(parents=True, mode=0o700)
    with tempfile.TemporaryDirectory(prefix='slimblade-smoke-') as temp:
        base = Path(temp)
        work, evidence, runtime = [base / p for p in ('work', 'evidence', 'runtime')]
        for directory in (work, evidence, runtime):
            directory.mkdir()
        for relative in sr.WORKER_READS:
            file = work / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text('Synthetic runner test only. Do not access hardware or other agents.\n')
        (evidence / 'input.txt').write_text('Synthetic inputs: 4 and 7.\n')
        source = work / 'decomp/src/fn_00001000.c'
        source.parent.mkdir(parents=True)
        source.write_text('')
        result_dir = work / 'decomp/results/fn_00001000'
        result_dir.mkdir(parents=True)
        allowed = ['decomp/src/fn_00001000.c', 'decomp/results/fn_00001000/']
        auth = Path.home() / '.codex/auth.json'
        for label, argv in [('version', ['/usr/bin/codex', '--version']),
                            ('auth', ['/usr/bin/codex', 'login', 'status'])]:
            result = subprocess.run(sr.sandbox_command(work, evidence, runtime, allowed,
                                    argv, auth=auth), capture_output=True, text=True, timeout=20)
            sr.require(result.returncode == 0, 'isolated CLI ' + label + ' failed')
            lines = [line for line in (result.stdout + result.stderr).splitlines()
                     if line.startswith(('codex-cli ', 'Logged in using '))]
            print(json.dumps({'check': label, 'public_status': lines}), flush=True)
            if label == 'auth':
                sr.require(lines == ['Logged in using ChatGPT'], 'ChatGPT sign-in required')
        account_cmd = sr.sandbox_command(work, evidence, runtime, allowed,
                         ['/usr/bin/codex', 'app-server', '--stdio'], auth=auth)
        with Account(command=account_cmd) as account:
            print(json.dumps({'check': 'isolated-live-quota', **account.snapshot()}), flush=True)
        if args.model_smoke:
            prompt = '''This is a synthetic worker isolation smoke test, not firmware work.
Read /evidence/input.txt. Write only /workspace/decomp/results/fn_00001000/result.json
containing {"sum":11,"status":"synthetic-only"}. Do not modify other files, run a
compiler, use the network, read credentials, or launch agents. End with SYNTHETIC_OK.
'''
            with Account() as account:
                result = sr.supervise(sr.sandbox_command(work, evidence, runtime, allowed,
                    sr.codex_command('gpt-6-luna', allowed), auth=auth), prompt,
                    args.output / 'model-run', account.snapshot, seconds=90, poll_seconds=10)
            sr.require(result['status'] == 'completed', 'synthetic worker did not complete')
            report = json.loads((result_dir / 'result.json').read_text())
            sr.require(report == {'sum': 11, 'status': 'synthetic-only'}, 'wrong synthetic output')
            sr.require(source.read_text() == '', 'synthetic worker changed unrelated source')
            sr.write_json(args.output / 'result.json', {'model': 'gpt-6-luna',
                'synthetic_only': True, 'passed': True, 'usage': result['usage']})
            print('Synthetic model round-trip passed; no firmware task claimed.')


if __name__ == '__main__':
    main()
