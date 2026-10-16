#!/usr/bin/env python3
"""Read live ChatGPT quota through Codex's documented account RPC; no inference.

No auth file contents, account identifiers, credits or raw RPC errors are logged.
Only initialize, account/read and account/rateLimits/read requests are supported.
"""
import argparse
from contextlib import contextmanager
import json
import queue
import subprocess
import threading

from swarm_runtime import quota_snapshot, stop_process, guarded_quota, latch_pause


class Account:
    def __init__(self, timeout=15, command=None):
        self.timeout = timeout
        self.messages = queue.Queue()
        self.next_id = 0
        self.process = None
        self.command = command or ['/usr/bin/codex', '-c', 'features.apps=false',
                                  '-c', 'features.plugins=false', 'app-server', '--stdio']

    def __enter__(self):
        self.process = subprocess.Popen(
            self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, start_new_session=True)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        try:
            self.request('initialize', {'clientInfo': {'name': 'slimblade_quota_guard',
                         'version': '1', 'title': 'SlimBlade quota guard'}})
            self.process.stdin.write(json.dumps({'method': 'initialized', 'params': {}}) + '\n')
            self.process.stdin.flush()
            account = self.request('account/read', {'refreshToken': False})
            if (account.get('account') or {}).get('type') != 'chatgpt':
                raise RuntimeError('ChatGPT sign-in required; API billing is not allowed')
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def _read(self):
        try:
            for line in self.process.stdout:
                try:
                    message = json.loads(line)
                except ValueError:
                    self.messages.put(None)
                    break
                if 'id' in message:
                    self.messages.put(message)
        finally:
            self.messages.put(None)

    def request(self, method, params=None):
        if method not in ('initialize', 'account/read', 'account/rateLimits/read'):
            raise ValueError('account client cannot launch jobs or mutate account state')
        self.next_id += 1
        request = {'id': self.next_id, 'method': method}
        if params is not None:
            request['params'] = params
        self.process.stdin.write(json.dumps(request) + '\n')
        self.process.stdin.flush()
        try:
            reply = self.messages.get(timeout=self.timeout)
        except queue.Empty as error:
            raise RuntimeError('live quota RPC timed out') from error
        if reply is None or reply.get('id') != self.next_id or 'error' in reply:
            raise RuntimeError('live quota RPC failed; no workers should start')
        return reply['result']

    def snapshot(self):
        return quota_snapshot(self.request('account/rateLimits/read'))

    def __exit__(self, *_):
        if self.process:
            stop_process(self.process)
            for stream in (self.process.stdin, self.process.stdout):
                stream.close()


@contextmanager
def monitored_account(state, reset):
    account = Account()
    try:
        account.__enter__()
    except Exception as error:
        latch_pause(state, error)
        raise
    try:
        yield lambda: guarded_quota(account.snapshot, state, reset)
    finally:
        account.__exit__(None, None, None)


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    with Account() as account:
        print(json.dumps(account.snapshot(), indent=2))
