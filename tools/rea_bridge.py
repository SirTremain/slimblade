#!/usr/bin/env python3
"""Coordinator-only adapter for the pinned, unmodified REA Ghidra bridge.

No MCP registration, model calls, compiler, queue mutations or hardware access.
Uses a checked disposable copy of the corrected project, NOT REA's raw importer.
Outputs are local bridge observations, NOT canonical upstream Evidence records.
"""
import argparse
import base64
from contextlib import contextmanager
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import signal
import socket
import stat
import subprocess
import tarfile
import tempfile
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CONFIG = 'decomp/rea/config.json'
METHODS = ('read_function_instructions', 'analyze_function', 'procedure_references')
MEMBERS = ('bridge/ghidra/ReaGhidraBridge.java',
           'bridge/ghidra/ReaGhidraExtensions.java', 'LICENSE')
MAX_REPLY = 8 * 1024 * 1024
FACETS = ('summary', 'pseudocode', 'assembly', 'callers', 'callees',
          'incoming_references', 'outgoing_references', 'basic_blocks',
          'native_value_flow', 'unresolved_calls')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def safe_path(root, relative):
    part = PurePosixPath(relative)
    require(not part.is_absolute() and part.parts and '..' not in part.parts,
            'unsafe relative path')
    path = root.joinpath(*part.parts)
    require(all(not p.is_symlink() for p in (path, *path.parents)
                if p == root or root in p.parents), 'symlink in selected path')
    require(path.resolve().is_relative_to(root.resolve()), 'path escapes root')
    return path


def tree_digest(root):
    """Hash regular contents, executable bits, and internal file symlinks."""
    require(root.is_dir() and not root.is_symlink(), 'expected regular directory')
    rows = []
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root).as_posix()
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            target = path.resolve(strict=True)
            require(target.is_relative_to(root.resolve()) and target.is_file(),
                    'external or directory symlink in tree')
            rows.append([relative, 'link', os.readlink(path), digest(target.read_bytes())])
        elif stat.S_ISREG(mode):
            rows.append([relative, 'file', bool(mode & 0o111), digest(path.read_bytes())])
        else:
            require(stat.S_ISDIR(mode), 'special file in tree')
    require(rows, 'empty tree')
    return digest(canonical(rows))


def archive_members(data, pin):
    require(len(data) == pin['bytes'] and digest(data) == pin['sha256'],
            'REA archive identity mismatch')
    require('sha512-' + base64.b64encode(hashlib.sha512(data).digest()).decode()
            == pin['integrity'], 'REA archive npm integrity mismatch')
    found = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        for member in archive:
            # No arbitrary tar extraction, traversal, links or lifecycle scripts.
            if member.name not in {'package/' + p for p in MEMBERS}:
                continue
            name = member.name.removeprefix('package/')
            require(name not in found and member.isfile() and member.size <= MAX_REPLY,
                    'invalid or duplicate bridge archive member')
            found[name] = archive.extractfile(member).read(MAX_REPLY + 1)
            require(len(found[name]) == member.size, 'short bridge archive member')
    require(set(found) == set(MEMBERS), 'missing bridge archive members')
    return found


def load_config(root):
    config = json.loads(safe_path(root, CONFIG).read_text())
    require(config['schema_version'] == 1 and config['adapter'] == 'saved-project-bridge-v1',
            'unsupported REA adapter profile')
    return config


def install(root, fetch=False):
    config = load_config(root)
    archive = safe_path(root, config['archive']['path'])
    if not archive.exists():
        require(fetch, 'pinned archive missing; use install --fetch for explicit download')
        archive.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(config['archive']['url'], timeout=60) as response:
            data = response.read(config['archive']['bytes'] + 1)
        archive_members(data, config['archive'])
        with archive.open('xb') as stream:
            stream.write(data)
    members = archive_members(archive.read_bytes(), config['archive'])
    destination = safe_path(root, config['bridge_directory'])
    if destination.exists():
        verify_bridge(root, config)
        return {'status': 'already-installed', 'version': config['archive']['version']}
    destination.mkdir(parents=True)
    for relative, data in members.items():
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(data)
    return {'status': 'installed-bridge-only', 'version': config['archive']['version'],
            'npm_lifecycle_scripts_run': False, 'global_configuration_changed': False}


def verify_bridge(root, config):
    archive = safe_path(root, config['archive']['path'])
    members = archive_members(archive.read_bytes(), config['archive'])
    directory = safe_path(root, config['bridge_directory'])
    actual = set()
    for path in directory.rglob('*'):
        require(not path.is_symlink(), 'symlink in installed bridge')
        if not path.is_dir():
            require(path.is_file(), 'special file in installed bridge')
            actual.add(path.relative_to(directory).as_posix())
    require(actual == set(members), 'unexpected installed bridge files')
    for relative, data in members.items():
        require(safe_path(directory, relative).read_bytes() == data, 'installed bridge changed')
    return directory


def check(root):
    config = load_config(root)
    verify_bridge(root, config)
    for pin in config['files'].values():
        path = safe_path(root, pin['path'])
        require(path.is_file() and digest(path.read_bytes()) == pin['sha256'],
                'pinned file changed: ' + pin['path'])
    for pin in config['trees'].values():
        require(tree_digest(safe_path(root, pin['path'])) == pin['sha256'],
                'pinned tree changed: ' + pin['path'])
    bwrap = subprocess.run(['/usr/bin/bwrap', '--version'], capture_output=True,
                           text=True, check=True, timeout=10)
    require(bwrap.stdout.strip() == config['bubblewrap_version'], 'bubblewrap version changed')
    return config


def selected_entries(values, inventory):
    require(1 <= len(values) <= 8, 'select one to eight exact function entries')
    result = []
    known = {int(f['entry'], 16) for f in inventory['functions']}
    for value in values:
        require(re.fullmatch(r'0x[0-9a-fA-F]{1,8}', value) is not None,
                'entry must be an explicit hexadecimal address')
        address = int(value, 16)
        require(address in known, 'entry absent from pinned analysis inventory')
        require(address not in result, 'duplicate entry')
        result.append(address)
    return result


def query_params(method, program, address):
    require(method in METHODS, 'query operation not allowlisted')
    params = {'procedure': hex(address)}
    if method != 'analyze_function':
        params['document'] = program
    if method == 'procedure_references':
        params['direction'] = 'outgoing'
    return params


def sandbox_command(root, config, work, endpoint):
    require(re.fullmatch(r'[A-Za-z0-9_.-]+', config['project_owner']) is not None,
            'invalid pinned project owner')
    ghidra = safe_path(root, config['trees']['ghidra']['path'])
    java = safe_path(root, config['trees']['java']['path'])
    bridge = safe_path(root, config['bridge_directory'])
    checker = safe_path(root, config['files']['checker']['path'])
    hosts = safe_path(root, config['files']['hosts']['path'])
    # The original database, firmware tree, queue, home, licence and hardware are absent.
    command = ['/usr/bin/bwrap', '--unshare-all', '--die-with-parent', '--new-session',
               '--cap-drop', 'ALL', '--hostname', 'slimblade-rea',
               '--ro-bind', str(hosts), '/etc/hosts', '--ro-bind', '/usr', '/usr',
               '--symlink', 'usr/bin', '/bin', '--symlink', 'usr/lib', '/lib',
               '--symlink', 'usr/lib', '/lib64', '--proc', '/proc', '--dev', '/dev',
               '--tmpfs', '/tmp', '--ro-bind', str(ghidra), '/opt/ghidra',
               '--ro-bind', str(java), '/opt/jdk', '--ro-bind', str(bridge), '/rea',
               '--ro-bind', str(checker), '/adapter/CheckReaProject.java',
               '--bind', str(work), '/work', '--bind', str(endpoint), str(endpoint),
               '--clearenv', '--setenv', 'PATH', '/opt/jdk/bin:/usr/bin:/bin',
               '--setenv', 'JAVA_HOME', '/opt/jdk', '--setenv', 'LANG', 'C.UTF-8',
               '--setenv', 'XDG_CONFIG_HOME', '/work/config',
               '--setenv', 'XDG_CACHE_HOME', '/work/cache',
               '--setenv', 'JAVA_TOOL_OPTIONS',
               '-Duser.name=' + config['project_owner'] + ' -Duser.home=/work/home -Dapplication.settingsdir=/work/config '
               '-Dapplication.cachedir=/work/cache -Dapplication.tempdir=/work/temp',
               '--chdir', '/work', '/opt/ghidra/support/analyzeHeadless',
               '/work/project', 'SlimBlade-rea-copy', '-process', config['program'],
               '-readOnly', '-noanalysis', '-scriptPath', '/adapter;/rea/bridge/ghidra',
               '-preScript', 'CheckReaProject.java', '/work/admission.json',
               '/work/admission-result.json', '-postScript', 'ReaGhidraBridge.java',
               str(endpoint / 'descriptor.json'), '-postScript', 'CheckReaProject.java',
               '/work/admission.json', '/work/final-admission-result.json']
    return command


class Bridge:
    def __init__(self, connection, token, deadline):
        self.connection = connection
        self.reader = connection.makefile('rb')
        self.token, self.deadline, self.counter = token, deadline, 0

    def call(self, method, params):
        require(method in (*METHODS, 'ping', 'shutdown'), 'bridge operation not allowlisted')
        self.counter += 1
        remaining = self.deadline - time.monotonic()
        require(remaining > 0, 'REA run deadline exceeded')
        self.connection.settimeout(remaining)
        self.connection.sendall(canonical({'id': self.counter, 'token': self.token,
                                          'method': method, 'params': params}) + b'\n')
        line = self.reader.readline(MAX_REPLY + 1)
        require(len(line) <= MAX_REPLY and line.endswith(b'\n'), 'oversized or incomplete bridge reply')
        response = json.loads(line)
        require(response.get('id') == self.counter, 'bridge reply ID mismatch')
        require(response.get('ok') is True, 'bridge rejected operation: ' + method + ': ' +
                json.dumps(response.get('error', {}))[:2000].replace(self.token, '[redacted]'))
        return response['result']

    def close(self):
        self.reader.close()
        self.connection.close()


def write_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def stop(process):
    if process is not None and process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)


@contextmanager
def endpoint_directory(cleanup):
    # Kill the child before removing its endpoint, including on exceptions.
    with tempfile.TemporaryDirectory(prefix='slimblade-rea-') as temp:
        try:
            yield Path(temp)
        finally:
            cleanup()


class RunGuard:
    """Bound the whole child lifetime, including partial/slow socket replies."""
    def __init__(self, process, log, deadline):
        self.process, self.log, self.deadline = process, log, deadline
        self.done = threading.Event()
        self.violation = None
        self.thread = threading.Thread(target=self.watch, daemon=True)
        self.thread.start()

    def watch(self):
        while not self.done.wait(0.1):
            if time.monotonic() >= self.deadline:
                self.violation = 'REA run deadline exceeded'
            elif self.log.stat().st_size > MAX_REPLY:
                self.violation = 'Ghidra log limit exceeded'
            if self.violation:
                stop(self.process)
                return

    def close(self):
        self.done.set()
        self.thread.join(timeout=11)


def analyze(root, values, output, seconds=300):
    require(1 <= seconds <= 600, 'REA run limit must be 1..600 seconds')
    config = check(root)
    inventory = json.loads(safe_path(root, config['files']['inventory']['path']).read_text())
    entries = selected_entries(values, inventory)
    output = safe_path(root, output)
    require(output.is_relative_to(root / '.decomp/rea/runs') and
            output != root / '.decomp/rea/runs', 'output must be a new ignored REA run directory')
    require(not output.exists(), 'never overwrite REA evidence')
    lock_path = safe_path(root, '.decomp/rea/coordinator.lock')
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        output.mkdir(parents=True, mode=0o700)
        return run_locked(root, config, entries, output, seconds)


def run_locked(root, config, entries, output, seconds):
    start = time.time()
    process = client = guard = None
    profile = {'adapter': config['adapter'], 'config_sha256': digest(canonical(config)),
               'runner_sha256': digest(Path(__file__).read_bytes()),
               'language': 'ARM:LE:32:v5t', 'import': 'copied-corrected-project-noanalysis',
               'methods': list(METHODS), 'entry_selection': [hex(v) for v in entries]}
    profile_hash = digest(canonical(profile))
    result = {'schema_version': 1, 'status': 'started', 'profile': profile,
              'configuration': config,
              'profile_sha256': profile_hash, 'started_at': start,
              'record_kind': 'local-rea-bridge-observations-not-upstream-evidence',
              'certified_match': False, 'matching_coverage': 'unknown', 'observations': []}
    project_gpr = safe_path(root, config['files']['project']['path'])
    project_rep = safe_path(root, config['trees']['project']['path'])
    try:
        # The disposable project is retained on failure for diagnosis; never mutate the source.
        work = output / 'work'
        for name in ('project', 'home', 'config', 'cache', 'temp'):
            (work / name).mkdir(parents=True, mode=0o700)
        shutil.copyfile(project_gpr, work / 'project/SlimBlade-rea-copy.gpr')
        shutil.copytree(project_rep, work / 'project/SlimBlade-rea-copy.rep', symlinks=True)
        require(tree_digest(work / 'project/SlimBlade-rea-copy.rep') ==
                config['trees']['project']['sha256'], 'source project changed during copy')
        require(digest((work / 'project/SlimBlade-rea-copy.gpr').read_bytes()) ==
                config['files']['project']['sha256'], 'source project marker changed during copy')
        admission = {'baseline_sha256': config['baseline_sha256'], 'baseline_bytes': config['baseline_bytes'],
                     'inventory': json.loads(safe_path(root, config['files']['inventory']['path']).read_text()),
                     'runtime_xml': safe_path(root, config['files']['runtime_xml']['path']).read_text()}
        write_json(work / 'admission.json', admission)
        with endpoint_directory(lambda: stop(process)) as endpoint:
            token = secrets.token_hex(32)
            write_json(endpoint / 'descriptor.json', {
                'transport': 'unix-socket', 'endpoint_path': str(endpoint / 'bridge.sock'),
                'token': token, 'run_id': output.name, 'target_sha256': config['baseline_sha256'],
                'provider_version': '12.1.4', 'profile_digest': profile_hash})
            deadline = time.monotonic() + seconds
            with (output / 'ghidra.log').open('xb') as log:
                process = subprocess.Popen(sandbox_command(root, config, work, endpoint),
                                           stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                guard = RunGuard(process, output / 'ghidra.log', deadline)
                while not (endpoint / 'bridge.sock').exists():
                    require(process.poll() is None, 'Ghidra exited before bridge readiness; inspect ghidra.log')
                    require(time.monotonic() < deadline, 'REA startup deadline exceeded')
                    require((output / 'ghidra.log').stat().st_size <= MAX_REPLY, 'Ghidra log limit exceeded')
                    time.sleep(0.1)
                admission_result = json.loads((work / 'admission-result.json').read_text())
                require(admission_result.get('status') == 'admitted' and
                        admission_result.get('sha256') == config['baseline_sha256'], 'project admission failed')
                result['admission'] = admission_result
                connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                connection.connect(str(endpoint / 'bridge.sock'))
                client = Bridge(connection, token, deadline)
                handshake = client.call('ping', {})
                validate_handshake(handshake, config, profile_hash, output.name)
                write_json(output / 'handshake.json', handshake)
                # Upstream advertises mutation capabilities; this adapter NEVER forwards them.
                result['limitations'] = [
                    'Custom saved-project adapter, not the upstream raw-binary provider or canonical Evidence API.',
                    'Bridge capabilities include mutation; the coordinator RPC allowlist is read-only and no socket is exposed to workers.',
                    'No reanalysis ran. analysis_complete in the bridge handshake is not independent inventory completeness.',
                    'Pseudocode, boundaries, types and effects remain analysis hypotheses; all upstream limitations are retained.']
                for address in entries:
                    for method in METHODS:
                        observation = client.call(method, query_params(method, config['program'], address))
                        filename = f'{address:08x}-{method}.json'
                        write_json(output / filename, observation)
                        result['observations'].append({'entry': hex(address), 'method': method,
                            'path': filename, 'sha256': digest((output / filename).read_bytes())})
                client.call('shutdown', {})
                client.close()
                client = None
                process.wait(timeout=max(0.1, deadline-time.monotonic()))
                require(process.returncode == 0, 'Ghidra did not shut down successfully')
                log_text = (output / 'ghidra.log').read_text(errors='replace')
                require('REPORT SCRIPT ERROR' not in log_text and 'ERROR ' not in log_text,
                        'Ghidra logged an error despite exit status')
                require(json.loads((work / 'final-admission-result.json').read_text()) == admission_result,
                        'copied project changed during bridge queries')
                guard.close()
                require(not guard.violation, guard.violation)
        result['status'] = 'observed'
    except BaseException as error:
        result.update(status='failed', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        stop(process)
        if guard:
            guard.close()
            if guard.violation:
                result.update(status='failed', error=guard.violation)
        if client:
            client.close()
        unchanged = (digest(project_gpr.read_bytes()) == config['files']['project']['sha256'] and
                     tree_digest(project_rep) == config['trees']['project']['sha256'])
        result['source_project_unchanged'] = unchanged
        if not unchanged:
            result.update(status='failed', error='source project changed during observation')
        result['finished_at'] = time.time()
        result['elapsed_seconds'] = result['finished_at'] - start
        write_json(output / 'report.json', result)
    require(result['status'] == 'observed', result.get('error', 'REA observation failed'))
    return {key: result[key] for key in ('status', 'source_project_unchanged', 'elapsed_seconds', 'certified_match')}


def validate_handshake(value, config, profile_hash, run_id):
    require(value['target']['sha256'] == config['baseline_sha256'] and
            value['target']['language_id'] == 'ARM:LE:32:v5t' and
            value['target']['compiler_spec_id'] == 'default' and
            value['target']['name'] == config['program'] and
            value['provider'] == {'id': 'ghidra', 'version': '12.1.4'} and
            value['profile_digest'] == profile_hash and value['run_id'] == run_id and
            value['analysis_timed_out'] is False and set(METHODS) <= set(value['capabilities']),
            'bridge handshake identity mismatch')


def inspect(root, run, entry, facet='summary'):
    """Read retained observations without rerunning Ghidra or dropping caveats."""
    require(facet in FACETS, 'unknown observation facet')
    directory = safe_path(root, run)
    require(directory.is_relative_to(root / '.decomp/rea/runs') and
            directory != root / '.decomp/rea/runs', 'expected local REA run directory')
    report = json.loads(safe_path(directory, 'report.json').read_text())
    require(report['status'] == 'observed' and report['source_project_unchanged'] is True,
            'run did not finish successfully')
    require(re.fullmatch(r'0x[0-9a-fA-F]{1,8}', entry) is not None, 'explicit hexadecimal entry required')
    address = int(entry, 16)
    rows = [r for r in report['observations']
            if r['entry'] == hex(address) and r['method'] == 'analyze_function']
    require(len(rows) == 1, 'entry not uniquely observed in run')
    row = rows[0]
    require(row['path'] == f'{address:08x}-analyze_function.json', 'unexpected observation path')
    content = safe_path(directory, row['path']).read_bytes()
    require(digest(content) == row['sha256'], 'retained observation changed')
    observation = json.loads(content)
    value = observation['value']
    require(int(value['procedure']['address'], 16) == address, 'observation entry mismatch')
    selected = ({'procedure': value['procedure'],
                 'facets': sorted(value),
                 'callers': len(value.get('callers', [])),
                 'callees': len(value.get('callees', [])),
                 'unresolved_calls': value.get('unresolved_calls', [])}
                if facet == 'summary' else value[facet])
    # These are views, never new upstream Evidence IDs or reconstruction verdicts.
    return {'record_kind': report['record_kind'], 'source': run + '/' + row['path'],
            'sha256': row['sha256'], 'baseline_sha256': report['admission']['sha256'],
            'profile_sha256': report['profile_sha256'], 'facet': facet, 'value': selected,
            'adapter_limitations': report['limitations'],
            'upstream_limitations': observation.get('limitations', []),
            'dossier_limitations': value.get('limitations', []),
            'facet_availability': value.get('facet_availability', {}),
            'relationship_coverage': observation.get('relationship_coverage'),
            'certified_match': False}


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    commands = parser.add_subparsers(dest='command', required=True)
    installer = commands.add_parser('install', help='extract only pinned bridge sources/license; no npm scripts')
    installer.add_argument('--fetch', action='store_true')
    commands.add_parser('check', help='verify local dependencies without starting Ghidra')
    query = commands.add_parser('analyze', help='read selected entries from a disposable corrected-project copy')
    query.add_argument('--entry', action='append', required=True)
    query.add_argument('--output', required=True)
    query.add_argument('--seconds', type=int, default=300)
    view = commands.add_parser('inspect', help='read a hash-checked retained summary/facet without reanalysis')
    view.add_argument('--run', required=True)
    view.add_argument('--entry', required=True)
    view.add_argument('--facet', choices=FACETS, default='summary')
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == 'install':
        result = install(root, args.fetch)
    elif args.command == 'check':
        check(root)
        result = {'status': 'local-pins-verified', 'firmware_analysis_tested': False}
    elif args.command == 'analyze':
        result = analyze(root, args.entry, args.output, args.seconds)
    else:
        result = inspect(root, args.run, args.entry, args.facet)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
