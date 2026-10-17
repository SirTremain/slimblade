#!/usr/bin/env python3
"""Coordinator-owned isolation and bounded process supervision (stdlib/Linux).

Does not launch a model by import, alter compiler pins, or certify firmware.
The outer mount namespace hides the host, oracle, licences and other worktrees.
Codex's inner permissions additionally deny shell network and auth/state reads.
"""
from contextlib import contextmanager
import fcntl
import json
import math
import os
import re
from pathlib import Path, PurePosixPath
import signal
import subprocess
import time

MODELS = ('gpt-6-luna', 'gpt-6.1-sol')
STOP_REMAINING = 45.0
WORKER_READS = ('AGENTS.md', 'docs/project-plan.md', 'docs/workflow.md',
                'docs/pilot.md', 'docs/expansion.md', 'docs/broader-workflow.md', 'decomp/templates/result.json')
BATCHES = {
    'six-reviewed-leaf-pilot-only': ('fn_00003b48', 'fn_00003bb4', 'fn_0000e4ee',
                                   'fn_0000e4fc', 'fn_0000e540', 'fn_0000e548'),
    'four-reviewed-leaf-batch-2-only': ('fn_00013f58', 'fn_00013f72',
                                     'fn_000154d4', 'fn_00018100'),
}


def check_runtime():
    for command, expected in ((['/usr/bin/codex', '--version'], 'codex-cli 0.162.1'),
                              (['/usr/bin/bwrap', '--version'], 'bubblewrap 0.13.1')):
        actual = subprocess.run(command, capture_output=True, text=True, timeout=15)
        require(actual.returncode == 0 and actual.stdout.strip() == expected,
                'runner version changed; repeat isolation and synthetic smoke review')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def write_json(path, value):
    """Atomic coordinator checkpoint; not a firmware comparison artifact."""
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
    os.replace(temp, path)


def safe_path(root, relative):
    part = PurePosixPath(relative.rstrip('/'))
    require(not part.is_absolute() and part.parts and
            not any(p in ('', '.', '..') for p in part.parts), 'unsafe relative path')
    target = root.joinpath(*part.parts)
    require(target.resolve().is_relative_to(root.resolve()), 'path escapes root')
    require(not any(p.is_symlink() for p in (target, *target.parents)
                    if p == root or root in p.parents), 'symlinks are not worker mounts')
    return target


def sandbox_command(worktree, evidence, runtime, allowed, argv, *, auth=None):
    """The caller supplies reviewed paths; no home/repository-root/device binds."""
    worktree, evidence, runtime = [Path(p).resolve(strict=True)
                                  for p in (worktree, evidence, runtime)]
    require(worktree != Path('/') and runtime != Path('/'), 'unsafe mount root')
    require(not runtime.is_relative_to(worktree) and not evidence.is_relative_to(worktree),
            'runtime/evidence must be outside the mounted worktree')
    require(not (worktree / '.decomp').exists() and not (worktree / 'ARMCC').exists(),
            'private artifacts in worker worktree')
    # Private ephemeral harness state, not the actual home directory. The auth
    # file is mounted read-only; it is not copied into the repository or logs.
    user_home = Path.home()
    codex_state = user_home / '.codex'
    (runtime / 'codex').mkdir(exist_ok=True, mode=0o700)
    cmd = ['/usr/bin/bwrap', '--unshare-all', '--share-net', '--die-with-parent',
           '--new-session', '--cap-drop', 'ALL', '--ro-bind', '/usr', '/usr',
           '--symlink', 'usr/lib', '/lib', '--symlink', 'usr/lib', '/lib64',
           '--symlink', 'usr/bin', '/bin', '--proc', '/proc', '--dev', '/dev',
           '--tmpfs', '/tmp', '--dir', str(user_home),
           '--bind', str(runtime / 'codex'), str(codex_state), '--dir', '/workspace',
           '--dir', '/workspace/.git', '--dir', '/workspace/.codex',
           '--dir', '/workspace/.agents', '--dir', '/workspace/.aws',
           '--ro-bind', str(evidence), '/evidence']
    for relative in WORKER_READS:
        source = safe_path(worktree, relative)
        require(source.is_file(), 'missing worker instructions: ' + relative)
        cmd += ['--ro-bind', str(source), '/workspace/' + relative]
    for path in ('/etc/ld.so.cache', '/etc/passwd', '/etc/group', '/etc/nsswitch.conf',
                 '/etc/resolv.conf', '/etc/hosts', '/etc/ssl/certs',
                 '/etc/ssl/cert.pem', '/etc/ca-certificates/extracted'):
        if Path(path).exists():
            cmd += ['--ro-bind', path, path]
    for relative in allowed:
        target = safe_path(worktree, relative)
        require(target.exists(), 'worker writable paths must be prepared first')
        require(relative.startswith(('decomp/src/', 'decomp/results/')),
                'worker writes outside source/results')
        require(all(not p.is_symlink() and (p.is_dir() or p.is_file())
                    for p in target.rglob('*')) if target.is_dir()
                else target.is_file(), 'nonregular worker output')
        cmd += ['--bind', str(target), '/workspace/' + relative.rstrip('/')]
    if auth is not None:
        auth = Path(auth)
        require(auth.is_file() and not auth.is_symlink(), 'regular auth file required')
        cmd += ['--ro-bind', str(auth.resolve()), str(codex_state / 'auth.json')]
    cmd += ['--remount-ro', '/', '--clearenv', '--setenv', 'PATH', '/usr/bin:/bin',
            '--setenv', 'LANG', 'C.UTF-8', '--setenv', 'LC_ALL', 'C.UTF-8',
            '--setenv', 'TERM', 'dumb', '--chdir', '/workspace', *argv]
    return cmd


def codex_command(model, allowed):
    require(model in MODELS, 'model outside reviewed worker choices')
    # Config is fresh inside the mount namespace. No host MCP/plugins/hooks,
    # model self-delegation, API keys, or automatic approval escalation.
    # The outer namespace enforces the per-file mounts. Codex 0.162.1 incorrectly
    # treats a direct file-write rule as a workspace directory (.git/.aws below
    # the C file), so its inner rule names the directory; it cannot make an
    # outer read-only mount writable. Credential reads remain denied inside.
    filesystem = {':root': 'read', str(Path.home() / '.codex'): 'deny',
                  '/tmp': 'write', '/workspace': 'write'}
    table = '{' + ','.join(json.dumps(k) + '=' + json.dumps(v)
                           for k, v in filesystem.items()) + '}'
    config = ['approval_policy="never"', 'default_permissions="firmware-worker"',
              'permissions.firmware-worker.filesystem=' + table,
              'permissions.firmware-worker.network.enabled=false',
              'agents.enabled=false', 'features.apps=false', 'features.plugins=false',
              'features.memories=false', 'web_search="disabled"',
              'model_reasoning_effort="medium"']
    cmd = ['/usr/bin/codex', 'exec', '--ignore-user-config', '--ignore-rules',
           '--skip-git-repo-check', '--json', '--color', 'never', '--model', model]
    for value in config:
        cmd += ['-c', value]
    return cmd + ['-']


def quota_snapshot(response, *, now=None):
    """Validate live account/rateLimits/read response, not model token estimates."""
    now = time.time() if now is None else now
    limits = response.get('rateLimitsByLimitId', {}).get('codex') or response.get('rateLimits')
    require(isinstance(limits, dict) and limits.get('limitId') == 'codex',
            'missing Codex quota bucket')
    require(not limits.get('rateLimitReachedType') and not limits.get('spendControlReached'),
            'account reports a usage/spend limit')
    weekly = []
    for key in ('primary', 'secondary'):
        window = limits.get(key)
        if not window:
            continue
        used, duration, reset = (window.get(k) for k in
                                ('usedPercent', 'windowDurationMins', 'resetsAt'))
        require(type(used) in (int, float) and math.isfinite(used) and 0 <= used <= 100,
                'invalid quota percentage')
        require(type(reset) in (int, float) and math.isfinite(reset) and reset > now,
                'expired/invalid quota window')
        require(used < 100, 'included quota exhausted')
        if duration == 10080:
            weekly.append(window)
    require(len(weekly) == 1, 'weekly quota not unambiguously available')
    return {'observed_at': now, 'remaining_percent': 100-weekly[0]['usedPercent'],
            'resets_at': weekly[0]['resetsAt'], 'window_minutes': 10080}


def check_budget(snapshot, *, now=None, reset=None, max_age=60):
    now = time.time() if now is None else now
    observed, remaining = snapshot['observed_at'], snapshot['remaining_percent']
    require(type(observed) in (int, float) and math.isfinite(observed) and
            0 <= now-observed <= max_age, 'stale/future usage reading')
    require(type(remaining) in (int, float) and math.isfinite(remaining) and
            STOP_REMAINING < remaining <= 100, 'weekly reserve stop threshold')
    require(snapshot['resets_at'] > now, 'quota window expired')
    require(reset is None or snapshot['resets_at'] == reset,
            'quota window changed; explicit new run required')


def latch_pause(state_dir, error):
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    pause = state_dir / 'PAUSED.json'
    try:
        with pause.open('x') as stream:
            json.dump({'status': 'paused', 'time': time.time(),
                       'reason': type(error).__name__ + ': ' + str(error),
                       'explicit_user_resume_required': True}, stream)
    except FileExistsError:
        pass


def guarded_quota(read_quota, state_dir, expected_reset):
    """Latch a coordinator-owned stop. A later successful read cannot clear it."""
    pause = state_dir / 'PAUSED.json'
    require(not pause.exists(), 'run is paused; explicit user resume required')
    try:
        value = read_quota()
        check_budget(value, reset=expected_reset)
        return value
    except Exception as error:
        latch_pause(state_dir, error)
        raise


def policy(root, task_id=None):
    value = json.loads((root / 'decomp/swarm-policy.json').read_text())
    require(isinstance(value.get('scope'), str) and value['scope'] in (*BATCHES, 'reviewed-batch-v1'),
            'unreviewed batch scope')
    if value['scope'] == 'reviewed-batch-v1':
        import reconstruction
        batch = reconstruction.load_batch(root, value['batch'], local=True)
        gate = json.loads((root / 'decomp/preparation.json').read_text())
        require(gate.get('schema_version') == 1 and gate.get('ready') is True and gate.get('batch') == value['batch'] and
                set(gate.get('allowed_function_ids', [])) == set(batch['tasks']),
                'batch gate/policy mismatch')
        ids = batch['tasks']
    else:
        ids = BATCHES[value['scope']]
    if task_id is not None:
        require(task_id in ids, 'task outside selected batch policy')
    expected = {'schema_version': 1,
                'worker_models': list(MODELS), 'maximum_concurrent_workers': 2,
                'stop_remaining_percent': 45, 'work_reserve_percent': 40,
                'maximum_task_seconds': 1200, 'maximum_compile_attempts': 8,
                'maximum_non_improving_attempts': 3,
                'new_quota_window_requires_user_resume': True,
                'launches_require_existing_queue_claim': True, 'hardware_access': False}
    require(all(type(value.get(k)) is type(v) and value[k] == v for k, v in expected.items()),
            'unreviewed swarm policy')
    require(type(value.get('quota_window_resets_at')) is int and
            value['quota_window_resets_at'] > time.time(), 'assigned quota window expired')
    return value


def attempt_budget(history):
    history = [row for row in history if row.get('result') != 'compiler-busy']
    require(len(history) < 8, 'eight compiler attempts exhausted')
    best, stagnant = None, 0
    for attempt in history:
        score = attempt.get('differing_bytes')
        if score is not None and (best is None or score < best):
            best, stagnant = score, 0
        else:
            stagnant += 1
    require(stagnant < 3, 'three attempts without improvement')


@contextmanager
def compiler_slot(state):
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (state / 'compiler.lock').open('a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError('compiler busy; wait for the current coordinator build') from error
        yield


@contextmanager
def task_lock(state, task):
    require(re.fullmatch(r'fn_[0-9a-f]{8}', task), 'invalid task lock name')
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (state / (task + '.lock')).open('a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError('task has an active worker/build') from error
        yield


@contextmanager
def worker_slot(state, maximum=2):
    require(maximum in (1, 2), 'at most two concurrent workers')
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    held = None
    try:
        for number in range(maximum):
            stream = (state / f'worker-{number}.lock').open('a')
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                stream.close()
                continue
            held = stream
            break
        require(held is not None, 'worker slots full')
        yield
    finally:
        if held:
            held.close()


def stop_process(process, grace=3):
    """Stop only the new child process group; never use broad pkill/killall."""
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        process.wait(timeout=grace)
        return
    try:
        process.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=grace)


def supervise(command, prompt, output, read_quota, *, seconds=1200, poll_seconds=10):
    require(0 < seconds <= 1200 and 0 < poll_seconds <= 15, 'unbounded worker run')
    deadline = time.monotonic() + seconds
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    state = {'status': 'preflight', 'started_at': time.time(), 'usage': []}
    checkpoint = output / 'checkpoint.json'
    process = None
    try:
        first = read_quota()
        check_budget(first)
        state['usage'].append(first)
        write_json(checkpoint, state)
        require(time.monotonic() < deadline, 'worker time limit during preflight')
        require(len(prompt.encode()) <= 256_000, 'worker prompt too large')
        (output / 'prompt.txt').write_text(prompt)
        with (output / 'prompt.txt').open('rb') as source, \
                (output / 'events.jsonl').open('xb') as events, \
                (output / 'stderr.txt').open('xb') as errors:
            process = subprocess.Popen(command, stdin=source, stdout=events,
                                       stderr=errors, start_new_session=True)
            state.update(status='running', pid=process.pid)
            write_json(checkpoint, state)
            while process.poll() is None:
                require(time.monotonic() < deadline, 'worker time limit')
                try:
                    process.wait(timeout=min(poll_seconds, max(0.01, deadline-time.monotonic())))
                except subprocess.TimeoutExpired:
                    pass
                current = read_quota()
                state['usage'].append(current)
                check_budget(current, reset=first['resets_at'])
                write_json(checkpoint, state)
            state.update(status='completed' if process.returncode == 0 else 'failed',
                         returncode=process.returncode)
    except BaseException as error:
        if process is not None:
            stop_process(process)
        state.update(status='stopped', reason=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        state['finished_at'] = time.time()
        write_json(checkpoint, state)
    return state
