#!/usr/bin/env python3
"""Explicit local LIC check with no screenshots, raw logs or key-bearing argv.

Uses the user's real adapters and persistent Wine prefix; no device access.
The native helper only interacts with ordinary Win32 dialog controls.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


# ARMCC 5.06u3 removed the ARM968E-S name. The bundled release notes,
# SDCOMP-45000, explicitly prescribe --cpu=5TE. This is a synthetic access
# check, not a change to any pinned stock calibration or worker build flags.
SMOKE_CPU = '5TE'


def scrub(value, key):
    value = re.sub(re.escape(key), '[REDACTED]', value, flags=re.I) if key else value
    return re.sub(r'(?i)\b[A-Z0-9]{5}(?:-[A-Z0-9]{5}){3,}\b', '[REDACTED]', value)


def run(argv, timeout=30, variant=None):
    env = dict(os.environ)
    if variant:
        env['ARM_TOOL_VARIANT'] = variant
    return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=timeout, check=False, env=env)


def public_status(result, key):
    value = scrub((result.stdout + result.stderr).decode(errors='replace'), key)
    return {'returncode': result.returncode,
            'error_codes': sorted(set(re.findall(r'\b(?:[ACLQ]\d{4}[EU]|R\d{3}(?:\(\d+\))?)\b', value))),
            'version': [line for line in value.splitlines()
                        if line.startswith(('Product:', 'Component:', 'Tool:'))],
            'diagnostic': [line for line in value.splitlines()
                           if 'error' in line.lower() or 'licen' in line.lower()]}


def ui(key):
    result = run(['wine', '/work/keil-gui/keil_ui_text.exe.so'])
    if result.returncode:
        raise RuntimeError('UI text helper failed')
    records = []
    for entry in result.stdout.decode(errors='replace').split('\x1e'):
        values = entry.split('\t', 2)
        if len(values) == 3:
            records.append((values[0], values[1], scrub(values[2], key)))
    return records


def compile_check(key, variant=None):
    suffix = variant or 'auto'
    obj = rf'Z:\scratch\probe-{suffix}.o'
    version = run(['wine', r'Z:\keil\ARM\ARMCC\bin\armcc.exe', '--vsn'], variant=variant)
    print(json.dumps({'variant': suffix, 'compiler_version': public_status(version, key)}), flush=True)
    build = run(['wine', r'Z:\keil\ARM\ARMCC\bin\armcc.exe', f'--cpu={SMOKE_CPU}',
                 '--thumb', '-O2', '-c', r'Z:\probe-source.c', '-o', obj], variant=variant)
    print(json.dumps({'variant': suffix, 'cpu': SMOKE_CPU, 'arm9_compile': public_status(build, key),
                      'object_created': Path(f'/scratch/probe-{suffix}.o').is_file()}), flush=True)
    if build.returncode == 0 and Path(f'/scratch/probe-{suffix}.o').is_file():
        link = run(['wine', r'Z:\keil\ARM\ARMCC\bin\armlink.exe',
                    '--entry=probe', '--ro-base=0x1000', '--no_scanlib', obj,
                    '-o', rf'Z:\scratch\probe-{suffix}.axf'], variant=variant)
        print(json.dumps({'variant': suffix, 'arm9_link': public_status(link, key),
                          'image_created': Path(f'/scratch/probe-{suffix}.axf').is_file()}), flush=True)


def inside(install, test_existing, headless_test=False):
    os.umask(0o077)
    key = Path('/license.txt').read_text().strip()
    if not re.fullmatch(r'[A-Za-z0-9]{5}(?:-[A-Za-z0-9]{5}){5}', key):
        raise ValueError('expected one six-group Keil LIC, without surrounding text')
    if headless_test:
        try:
            compile_check(key)
        finally:
            run(['wineserver', '-k'], timeout=10)
        return
    Path('/tmp/.X11-unix').mkdir(mode=0o1777, exist_ok=True)
    x = subprocess.Popen(['/opt/xvfb/usr/bin/Xvfb', ':99', '-screen', '0',
                          '1280x960x24', '-nolisten', 'tcp', '-ac', '-extension', 'GLX'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = None
    try:
        for _ in range(100):
            if Path('/tmp/.X11-unix/X99').exists():
                break
            if x.poll() is not None:
                raise RuntimeError('private display failed')
            time.sleep(0.1)
        else:
            raise RuntimeError('private display timeout')
        app = subprocess.Popen(['wine', r'Z:\keil\UV4\UV4.exe'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(4)
        for coordinates in (('20', '40'), ('88', '220')):
            result = run(['xdotool', 'mousemove', *coordinates, 'click', '1'])
            if result.returncode:
                raise RuntimeError('menu navigation failed')
            time.sleep(0.5)
        before = ui(key)
        if test_existing:
            print(json.dumps({'installed_products': [row[2] for row in before if row[0] == 'PRODUCT']}), flush=True)
            for variant in ('mdk_basic', 'mdk_std', 'mdk_pro'):
                compile_check(key, variant)
            return
        if not install:
            print(json.dumps({'installed_products': [row[2] for row in before if row[0] == 'PRODUCT'],
                              'visible_controls': [(row[0], row[1]) for row in before],
                              'cid_present': any(row[0] == '1192' and row[2] for row in before)}), flush=True)
            return
        # IDs are pinned from a pre-install inspection of this exact MDK dialog.
        edits = {row[0] for row in before if row[1].lower() == 'edit'}
        buttons = {row[0]: row[2].replace('&', '').strip() for row in before
                   if row[1].lower() == 'button'}
        if '1741' not in edits or buttons.get('1223') != 'Add LIC':
            raise RuntimeError('unexpected license dialog controls; installation not attempted')
        result = run(['wine', '/work/keil-gui/keil_ui_text.exe.so', 'install', '1741', '1223'])
        if result.returncode:
            raise RuntimeError('license UI input failed')
        time.sleep(2)
        after = ui(key)
        # UI text is scrubbed in memory; raw helper output is never logged.
        print(json.dumps({'license_dialog': [row for row in after
                                             if row[0] in ('1744', 'PRODUCT') or row[1] == 'Static']}), flush=True)
        compile_check(key)
    finally:
        run(['wineserver', '-k'], timeout=10)
        if app is not None:
            app.wait(timeout=10)
        x.terminate()
        x.wait(timeout=10)


def command(root, install=False, test_existing=False, headless_test=False):
    if sum((install, test_existing, headless_test)) > 1:
        raise ValueError('installation and existing-license checks are separate operations')
    import keil_gui_probe
    cmd = keil_gui_probe.command(root, allow_network=True, allow_installed_license=True)
    cmd[cmd.index('/probe.py') - 1] = str(Path(__file__).resolve())
    extra = ['--ro-bind', str(root / '.decomp/keil-license.txt'), '/license.txt',
             '--ro-bind', str(Path(__file__).with_name('keil_smoke.c').resolve()), '/probe-source.c',
             '--tmpfs', '/scratch']
    cmd = cmd[:-4] + extra + cmd[-4:]
    if install:
        cmd.append('--install-and-test')
    if test_existing:
        cmd.append('--test-existing')
    if headless_test:
        cmd.append('--headless-test')
    return cmd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--inside', action='store_true')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--install-and-test', action='store_true')
    mode.add_argument('--test-existing', action='store_true')
    mode.add_argument('--headless-test', action='store_true',
                      help='test the installed licence without starting uVision or Xvfb')
    args = parser.parse_args()
    if args.inside:
        inside(args.install_and_test, args.test_existing, args.headless_test)
    elif args.root:
        os.execv('/usr/bin/bwrap', command(args.root.resolve(), args.install_and_test,
                                          args.test_existing, args.headless_test))
    else:
        parser.error('--root required')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # No repr/traceback: failed subprocess output may contain the LIC.
        print(json.dumps({'check_failed': type(exc).__name__}), file=sys.stderr)
        raise SystemExit(1)
