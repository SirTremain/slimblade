#!/usr/bin/env python3
"""Read-only startup diagnostics in the existing coordinator Wine sandbox.

No activation, license contents, GUI or device access. Retains only sanitized
diagnostics, using the existing runner's genuine-host prefix and serialization.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys


def inside():
    paths = ['/keil/ARM/ARMCC/bin/armcc.exe', '/work/prefix-v2/dosdevices/z:',
             '/work/prefix-v2/drive_c/windows/system32/ntdll.dll',
             '/work/prefix-v2/drive_c/windows/syswow64/ntdll.dll']
    print(json.dumps({'paths': {p: {'exists': Path(p).exists(),
          'symlink': str(Path(p).readlink()) if Path(p).is_symlink() else None}
          for p in paths}}), flush=True)
    commands = [
        ['wine', '--version'], ['winepath', '-w', '/keil/ARM/ARMCC/bin/armcc.exe'],
        ['wine', 'cmd', '/c', 'ver'],
        ['wine', r'Z:\keil\ARM\ARMCC\bin\armcc.exe', '--vsn'],
        ['wine', '/keil/ARM/ARMCC/bin/armcc.exe', '--vsn'],
    ]
    for cmd in commands:
        result = subprocess.run(cmd, capture_output=True, timeout=45)
        output = (result.stdout + result.stderr).decode(errors='replace')
        # Version/error text only; never output arbitrary activation diagnostics.
        lines = [line for line in output.splitlines() if line.startswith(
            ('wine-', 'Z:', 'Microsoft Windows', 'Product:', 'Component:', 'Tool:',
             'Application could', 'ShellExecuteEx', 'wine:', 'Error:'))]
        print(json.dumps({'argv': cmd, 'returncode': result.returncode,
                          'public_lines': lines}), flush=True)
    result = subprocess.run(['wine', r'Z:\keil\ARM\ARMCC\bin\armcc.exe', '--vsn'],
                            env={**os.environ, 'WINEDEBUG': '-all,+module'},
                            capture_output=True, timeout=45)
    debug = (result.stdout + result.stderr).decode(errors='replace')
    print(json.dumps({'module_errors': [line for line in debug.splitlines()
          if any(word in line.lower() for word in ('err:', 'failed', 'status c000', 'not found'))][-30:]}))
    subprocess.run(['wineserver', '-k'], capture_output=True, timeout=10)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--inside', action='store_true')
    args = parser.parse_args()
    if args.inside:
        inside()
    else:
        root = args.root.resolve()
        sys.path.insert(0, str(root / 'tools'))
        import armcc_runner as runner
        args.output.mkdir(parents=True, exist_ok=False)
        with (root / '.decomp/armcc-wine-work/compiler.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            cmd = runner.command(root, args.output.resolve())
            cmd[cmd.index('/probe.py') - 1] = str(Path(__file__).resolve())
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            output = runner.scrub((result.stdout + result.stderr).decode(errors='replace'))
            (args.output / 'startup-public.txt').write_text(output)
            print(output)
            raise SystemExit(result.returncode)
