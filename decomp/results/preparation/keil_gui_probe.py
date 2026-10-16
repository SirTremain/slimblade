#!/usr/bin/env python3
"""Private-screen Keil UI probe. No automatic activation or device access.

Uses the existing persistent Wine prefix. Interactive stdin accepts JSON arrays
for xdotool (inside the private display), 'screen', 'windows', 'compiler-version',
'adapter-check', or 'quit'. Never use this diagnostic to enter licenses: screenshots/logs are
not secret storage. This is a local diagnostic, not a qualified compiler runner.
Network is isolated unless explicitly requested. Do not use an isolated-network
CID for activation: the verified identity check used --allow-network.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from offline_identity import socket_filter, check_offline


def command(root, filter_fd=None, allow_network=False, allow_installed_license=False):
    if filter_fd is not None and allow_network:
        raise ValueError('choose the filtered diagnostic or normal network access, not both')
    state = root / '.decomp'
    config = state / 'keil-mdk-5.43a/TOOLS.INI'
    if (not allow_installed_license and config.is_file()
            and re.search(r'(?im)^\s*LIC\d+\s*=\s*\S', config.read_text(errors='replace'))):
        raise ValueError('Private licence installed: use the no-screenshot keil_license_check.py')
    work = state / 'armcc-wine-work'
    for name in ('cache', 'runtime', 'packs', 'keil-gui'):
        (work / name).mkdir(exist_ok=True, mode=0o700)
    args = ['/usr/bin/bwrap', '--unshare-all', '--die-with-parent', '--new-session',
            '--ro-bind', '/usr', '/usr', '--symlink', 'usr/lib', '/lib',
            '--symlink', 'usr/lib', '/lib64', '--symlink', 'usr/bin', '/bin']
    for path in ('/etc/ld.so.cache', '/etc/passwd', '/etc/group', '/etc/fonts',
                 '/etc/ImageMagick-7'):
        if Path(path).exists():
            args += ['--ro-bind', path, path]
    args += ['--ro-bind', str(state / 'tools/wine-11.19'), '/opt/wine',
             '--ro-bind', str(state / 'tools/xvfb-21.1.25-2'), '/opt/xvfb',
             '--bind', str(state / 'keil-mdk-5.43a'), '/keil',
             '--ro-bind', str(root / 'ARMCC'), '/keil/ARM/ARMCC',
             '--bind', str(work), '/work',
             '--ro-bind', str(Path(__file__).resolve()), '/probe.py',
             '--ro-bind', str(Path(__file__).with_name('offline_identity.py').resolve()), '/offline_identity.py',
             '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
             '--chdir', '/keil/UV4', '--clearenv']
    env = {'PATH': '/opt/wine/usr/bin:/usr/bin', 'WINEPREFIX': '/work/prefix-v2',
           'WINEARCH': 'win64', 'WINEDEBUG': '-all', 'DISPLAY': ':99',
           'XDG_CACHE_HOME': '/work/cache', 'XDG_RUNTIME_DIR': '/work/runtime',
           'WINEDLLOVERRIDES': 'winemenubuilder.exe,mscoree,mshtml,winebus=d'}
    for key, value in env.items():
        args += ['--setenv', key, value]
    if filter_fd is not None or allow_network:
        args += ['--share-net']
        if filter_fd is not None:
            args += ['--seccomp', str(filter_fd), '--setenv', 'KEIL_REAL_ADAPTERS', '1']
        args += ['--ro-bind', '/sys/class/net', '/sys/class/net']
        for adapter in sorted(Path('/sys/class/net').iterdir()):
            actual = str(adapter.resolve())
            args += ['--ro-bind', actual, actual]
    return args + ['/usr/bin/python3', '-u', '/probe.py', '--inside']


def inside():
    # No host display socket, USB node or home directory is mounted. Optional
    # adapter diagnostics share the network namespace; --allow-network removes
    # the experimental socket filter only after explicit caller opt-in.
    logs = Path('/work/keil-gui')
    if os.environ.get('KEIL_REAL_ADAPTERS') == '1':
        check_offline()
        print('IP/packet socket-denial checks passed; adapter discovery remains unverified', flush=True)
    Path('/tmp/.X11-unix').mkdir(mode=0o1777, exist_ok=True)
    with (logs / 'xvfb.log').open('a') as xlog, (logs / 'wine.log').open('a') as wlog:
        x = subprocess.Popen(['/opt/xvfb/usr/bin/Xvfb', ':99', '-screen', '0',
                              '1280x960x24', '-nolisten', 'tcp', '-ac',
                              '-extension', 'GLX'],
                             stdout=xlog, stderr=subprocess.STDOUT)
        app = None
        try:
            for _ in range(100):
                if Path('/tmp/.X11-unix/X99').exists():
                    break
                if x.poll() is not None:
                    raise RuntimeError('Xvfb failed; inspect local log')
                time.sleep(0.1)
            else:
                raise RuntimeError('private X server did not start')
            app = subprocess.Popen(['wine', r'Z:\keil\UV4\UV4.exe'],
                                   stdout=wlog, stderr=subprocess.STDOUT)
            print('Private Keil session started; commands: screen, windows, quit, JSON xdotool argv', flush=True)
            frame = 0
            for line in sys.stdin:
                line = line.strip()
                if line == 'quit':
                    break
                if line == 'screen':
                    frame += 1
                    path = logs / f'screen-{time.time_ns()}-{frame}.png'
                    result = subprocess.run(['import', '-display', ':99', '-window', 'root', str(path)],
                                            capture_output=True, text=True, timeout=20)
                    print(json.dumps({'screenshot': str(path), 'returncode': result.returncode,
                                      'stderr': result.stderr}), flush=True)
                elif line == 'windows':
                    result = subprocess.run(['xdotool', 'search', '--onlyvisible', '--name', '.*',
                                             'getwindowname', '%@'], capture_output=True,
                                            text=True, timeout=10)
                    print(result.stdout, result.stderr, flush=True)
                elif line == 'compiler-version':
                    result = subprocess.run(['wine', r'Z:\keil\ARM\ARMCC\bin\armcc.exe', '--vsn'],
                                            capture_output=True, text=True, timeout=30)
                    # Do not echo arbitrary licensing diagnostics or save keys.
                    public = [value for value in (result.stdout + result.stderr).splitlines()
                              if value.startswith(('Product:', 'Component:', 'Tool:',
                                                   'ARM Compiler', 'Error:', ' - Selected tool variant:'))]
                    print(json.dumps({'returncode': result.returncode, 'public_status': public}), flush=True)
                elif line == 'adapter-check':
                    result = subprocess.run(['wine', 'ipconfig', '/all'], capture_output=True,
                                            text=True, timeout=30)
                    # Adapter identities and IP addresses stay out of console output.
                    observed = set(re.findall(r'(?i)(?<![0-9a-f])(?:[0-9a-f]{2}-){5}[0-9a-f]{2}(?![0-9a-f])',
                                              result.stdout.lower())) - {'00-00-00-00-00-00'}
                    actual = {path.read_text().strip().replace(':', '-').lower()
                              for path in Path('/sys/class/net').glob('*/address')} - {'00-00-00-00-00-00'}
                    print(json.dumps({'returncode': result.returncode,
                                      'nonzero_macs_observed': len(observed),
                                      'matching_host_macs': len(observed & actual)}), flush=True)
                else:
                    values = json.loads(line)
                    if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
                        raise ValueError('expected xdotool argument array')
                    result = subprocess.run(['xdotool', *values], capture_output=True, text=True, timeout=15)
                    print(json.dumps({'returncode': result.returncode, 'stdout': result.stdout,
                                      'stderr': result.stderr}), flush=True)
        finally:
            subprocess.run(['wineserver', '-k'], timeout=10, check=False)
            if app is not None:
                app.wait(timeout=10)
            x.terminate()
            x.wait(timeout=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--inside', action='store_true')
    network = parser.add_mutually_exclusive_group()
    network.add_argument('--real-adapters', action='store_true',
                        help='experimental adapter visibility probe; blocks IP sockets, which also prevents Wine adapter queries; not for licence activation')
    network.add_argument('--allow-network', action='store_true',
                         help='explicit opt-in to normal host network access; no automatic activation')
    args = parser.parse_args()
    if args.inside:
        inside()
    elif args.root:
        if args.real_adapters:
            with socket_filter() as policy:
                result = subprocess.run(command(args.root.resolve(), policy.fileno()),
                                        pass_fds=(policy.fileno(),))
                raise SystemExit(result.returncode)
        else:
            os.execv('/usr/bin/bwrap', command(args.root.resolve(), allow_network=args.allow_network))
    else:
        parser.error('--root is required outside the sandbox')


if __name__ == '__main__':
    main()
