#!/usr/bin/env python3
"""Read-only ARMCC version probe in a device/network-isolated local Wine sandbox.

Not a compiler-license workaround or production build runner. Installs nothing
system-wide, exposes no home directory and does not supply a license.
"""
import argparse
import json
from pathlib import Path
import subprocess


TOOL_VARIANTS = ('product', 'mdk_pro', 'mdk_pro_flex', 'mdk_lite')


def command(root, tool_variant=None):
    if tool_variant is not None and tool_variant not in TOOL_VARIANTS:
        raise ValueError('unsupported diagnostic tool variant')
    state = root/'.decomp'
    work = state/'armcc-wine-work'
    for name in ('cache','runtime'):
        (work/name).mkdir(exist_ok=True,mode=0o700)
    args = ['/usr/bin/bwrap','--unshare-all','--die-with-parent','--new-session',
            '--ro-bind','/usr','/usr','--symlink','usr/lib','/lib','--symlink','usr/lib','/lib64']
    for path in ('/etc/ld.so.cache','/etc/passwd','/etc/group','/etc/fonts'):
        args += ['--ro-bind',path,path]
    args += ['--ro-bind',str(state/'tools/wine-11.19'),'/opt/wine',
             '--ro-bind',str(root/'ARMCC'),'/compiler','--bind',str(work),'/work',
             '--proc','/proc','--dev','/dev','--tmpfs','/tmp','--chdir','/work','--clearenv']
    for key,value in {'PATH':'/opt/wine/usr/bin:/usr/bin','WINEPREFIX':'/work/prefix-v2',
                      'WINEARCH':'win64','WINEDEBUG':'-all','XDG_CACHE_HOME':'/work/cache',
                      'XDG_RUNTIME_DIR':'/work/runtime',
                      'WINEDLLOVERRIDES':'winemenubuilder.exe,mscoree,mshtml,winebus=d'}.items():
        args += ['--setenv',key,value]
    if tool_variant is not None:
        args += ['--setenv', 'ARM_TOOL_VARIANT', tool_variant]
    return args+['/opt/wine/usr/bin/wine','Z:\\compiler\\bin\\armcc.exe','--vsn']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('root',type=Path); p.add_argument('output',type=Path)
    p.add_argument('--tool-variant', choices=TOOL_VARIANTS,
                   help='diagnose product-map selection; supplies no license')
    a=p.parse_args(); a.output.mkdir(parents=True,exist_ok=False)
    cmd=command(a.root.resolve(), a.tool_variant)
    result=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=60)
    (a.output/'output.txt').write_text(result.stdout)
    (a.output/'command.json').write_text(json.dumps({'command':cmd,'returncode':result.returncode},indent=2)+'\n')
    print('returncode',result.returncode)
    print(result.stdout[-4000:])


if __name__=='__main__': main()
