#!/usr/bin/env python3
"""Fixed small calibration probes; no iterative per-function tuning or claims.

Sources encode reviewed instruction-level hypotheses. Results are calibration
evidence, not integrated recovered firmware. All outputs stay ignored/local.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT / "tools"))
import stock_compare as sc

PROBES = [
 (0x3b48,0x3b64,"unsigned int","unsigned int a, unsigned int b",
  "if (a == 0xf0000000u) return 0; return ((a-b)&0x0fffffffu) >= 0x08000000u;"),
 (0x3bb4,0x3bbe,"unsigned int","unsigned int a, unsigned int b",
  "return (a+2u*b)&0x0fffffffu;"),
 (0xe4ee,0xe4fc,"unsigned short","const unsigned char *p",
  "return p[0] + (p[1]<<8);"),
 (0xe4fc,0xe512,"unsigned int","const unsigned char *p",
  "unsigned int a=p[0]+((unsigned int)p[1]<<8); unsigned int b=((unsigned int)p[2]<<16)+((unsigned int)p[3]<<24); return a+b;"),
 (0xe540,0xe548,"void","unsigned char *p, unsigned short v",
  "p[0]=v; p[1]=v>>8;"),
 (0xe548,0xe558,"void","unsigned char *p, unsigned int v",
  "p[0]=v; p[1]=v>>8; p[2]=v>>16; p[3]=v>>24;")]


def run(cmd,cwd):
    p=subprocess.run(cmd,cwd=cwd,env=sc.base.ENV,capture_output=True,text=True,timeout=60)
    if p.returncode: raise RuntimeError(f"command {cmd} failed ({p.returncode}): {p.stdout}{p.stderr}")
    return p.stdout


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--compiler',choices=['gcc49','clang'],required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); root=a.root.resolve(); out=a.output.resolve()
    out.mkdir(parents=True,exist_ok=False)
    raw=(root/'.decomp/stock/stock-v4.49.bin').read_bytes()
    assert sc.base.sha(raw)=='e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7'
    if a.compiler=='gcc49':
        prefix=root/'.decomp/tools/gcc-arm-none-eabi-4_9-2015q3/bin'
        cc=str(prefix/'arm-none-eabi-gcc'); ld=str(prefix/'arm-none-eabi-ld')
        flags=['-mcpu=arm968e-s','-march=armv5te','-mthumb','-mthumb-interwork','-mfloat-abi=soft',
               '-mabi=aapcs','-std=c99','-Os','-ffreestanding','-fno-builtin','-fno-lto',
               '-fno-strict-aliasing','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-nostdinc']
    else:
        cc='/usr/bin/clang'; ld='/usr/bin/ld.lld'; flags=sc.FLAGS
    report={'compiler':sc.base.pin(cc),'version':run([cc,'--version'],out),'linker':sc.base.pin(ld),
            'flags':flags,'script_sha256':sc.base.sha(Path(__file__).read_bytes()),
            'purpose':'fixed calibration; original toolchain unknown; no certification','probes':[]}
    for start,end,ret,params,body in PROBES:
        name=f'fn_{start:08x}'; build=out/name; build.mkdir()
        source=f'{ret} {name}({params}) {{ {body} }}\n'
        (build/'probe.c').write_text(source)
        task={'entry':hex(start),'id':name}
        script=sc.layout(task)
        (build/'layout.ld').write_text(script)
        run([cc,*flags,'-c','probe.c','-o','probe.o'],build)
        run([ld,'-m','armelf','--build-id=none','--no-undefined','-T','layout.ld','probe.o','-o','probe.elf'],build)
        data=sc.runtime_bytes((build/'probe.elf').read_bytes(),start)
        result={**sc.compare(raw[start:end],data,start),'entry':hex(start),'source_sha256':sc.base.sha(source.encode())}
        (build/'llvm.txt').write_text(run(['/usr/bin/llvm-objdump','-d','--triple=thumbv5te-none-eabi','probe.elf'],build))
        report['probes'].append(result)
        print(name,result['result'],result['actual_bytes'],result['expected_bytes'],flush=True)
    (out/'report.json').write_bytes(sc.encode(report))


if __name__=='__main__': main()
