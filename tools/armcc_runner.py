#!/usr/bin/env python3
"""Coordinator ARMCC5 batch runner using the installed, private Wine license.

Builds only supplied C in a fresh build directory. No hardware, activation,
uVision, display, reference-image mount, or raw licensing logs. Serializes the
persistent Wine prefix; callers must retain coordinator-owned pins and outputs.
"""
import argparse
import fcntl
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
PREP = ROOT / 'decomp/results/preparation'
sys.path.insert(0, str(PREP))
import keil_gui_probe

FLAGS = ['--cpu=5TE', '--thumb', '--apcs=/interwork', '--fpu=SoftVFP',
         '--littleend', '--c99', '--gnu', '-O2', '-Ospace']
LINK_FLAGS = ['--no_scanlib', '--no_remove', '--no_legacyalign']
LLD_FLAGS = ['-m', 'armelf', '--build-id=none', '--no-undefined',
             '--fatal-warnings', '--orphan-handling=error']


def scrub(text):
    # Includes every normal Keil LIC, including a previously installed key.
    return re.sub(r'(?i)\b[A-Z0-9]{5}(?:-[A-Z0-9]{5}){3,}\b', '[REDACTED]', text)


def command(root, build):
    cmd = keil_gui_probe.command(root, allow_network=True, allow_installed_license=True)
    cmd[cmd.index('/probe.py') - 1] = str(Path(__file__).resolve())
    # No GUI is used. Product files are read-only; Wine state remains writable.
    pos = cmd.index(str(root / '.decomp/keil-mdk-5.43a'))
    cmd[pos - 1] = '--ro-bind'
    cmd[cmd.index('--chdir') + 1] = '/build'
    extra = ['--bind', str(build), '/build',
             '--ro-bind', str(PREP / 'keil_gui_probe.py'), '/keil_gui_probe.py',
             '--setenv', 'LC_ALL', 'C', '--setenv', 'TZ', 'UTC']
    return cmd[:-4] + extra + cmd[-4:]


def invoke(argv, cwd):
    result = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=60, check=False)
    return {'argv': argv, 'returncode': result.returncode,
            'stdout': scrub(result.stdout.decode(errors='replace')),
            'stderr': scrub(result.stderr.decode(errors='replace'))}


def inside():
    manifest = json.loads(Path('/build/jobs.json').read_text())
    backend = manifest.get('backend', 'armlink')
    if backend not in ('armlink', 'lld'):
        raise ValueError('unsupported linker backend')
    link_flags = LINK_FLAGS if backend == 'armlink' else LLD_FLAGS
    if manifest['compile_flags'] != FLAGS or manifest['link_flags'] != link_flags:
        raise ValueError('unexpected fixed profile')
    report = {'commands': [], 'jobs': []}
    try:
        for tool in ('armcc', 'armlink'):
            row = invoke(['wine', rf'Z:\keil\ARM\ARMCC\bin\{tool}.exe', '--vsn'], '/build')
            report['commands'].append(row)
            if row['returncode']:
                raise RuntimeError('tool version failed')
        for job in manifest['jobs']:
            name, entry = job['id'], job['entry']
            if not re.fullmatch(r'fn_[0-9a-f]{8}', name) or name != f'fn_{entry:08x}' or entry % 2:
                raise ValueError('invalid build job')
            cwd = Path('/build') / name
            row = invoke(['wine', r'Z:\keil\ARM\ARMCC\bin\armcc.exe', *FLAGS,
                          '-c', 'candidate.c', '-o', 'candidate.o'], cwd)
            report['commands'].append(row)
            linked = None
            if row['returncode'] == 0:
                argv = (['wine', r'Z:\keil\ARM\ARMCC\bin\armlink.exe',
                         *LINK_FLAGS, '--entry=' + name, f'--ro-base=0x{entry:x}',
                         'candidate.o', '-o', 'candidate.elf'] if backend == 'armlink' else
                        ['/usr/bin/ld.lld', *LLD_FLAGS, '-T', 'layout.ld',
                         'candidate.o', '-o', 'candidate.elf'])
                linked = invoke(argv, cwd)
                report['commands'].append(linked)
            report['jobs'].append({'id': name, 'compile_returncode': row['returncode'],
                                   'link_returncode': None if linked is None else linked['returncode']})
    finally:
        subprocess.run(['wineserver', '-k'], capture_output=True, timeout=10, check=False)
        Path('/build/build-report.json').write_text(json.dumps(report, indent=2) + '\n')


def build_batch(root, build):
    root, build = root.resolve(), build.resolve()
    # Nonblocking lock: no concurrent jobs can alter the shared prefix or kill
    # another job's Wine server. Queuing/retries are a coordinator responsibility.
    with (root / '.decomp/armcc-wine-work/compiler.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('compiler busy; coordinator must serialize builds and retry') from error
        result = subprocess.run(command(root, build), capture_output=True, timeout=600)
        if result.returncode:
            raise RuntimeError('isolated ARMCC batch failed: ' + scrub(result.stderr.decode(errors='replace')))
    return json.loads((build / 'build-report.json').read_text())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inside', action='store_true')
    args = parser.parse_args()
    try:
        if not args.inside:
            parser.error('use the coordinator calibration/comparison wrapper')
        inside()
    except Exception as error:
        print('ARMCC runner failed: ' + type(error).__name__, file=sys.stderr)
        raise SystemExit(1)
