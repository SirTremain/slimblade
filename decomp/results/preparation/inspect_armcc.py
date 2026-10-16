#!/usr/bin/env python3
"""Fingerprint a user-supplied compiler and compare a runtime-library member.

Uses LLVM archive/ELF readers only; does not execute ARM tools, accept licenses,
or incorporate library bytes into reconstructed source. Outputs remain local.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('root',type=Path); p.add_argument('output',type=Path)
    a=p.parse_args(); root=a.root.resolve(); compiler=root/'ARMCC'
    a.output.mkdir(parents=True,exist_ok=False)
    files=[]
    for path in sorted(compiler.rglob('*')):
        if path.is_symlink(): raise ValueError('compiler contains symlink')
        if path.is_file():
            data=path.read_bytes()
            files.append({'path':path.relative_to(compiler).as_posix(),'bytes':len(data),'sha256':sha(data)})
    inventory=json.dumps(files,sort_keys=True,separators=(',',':')).encode()
    (a.output/'files.json').write_bytes(inventory+b'\n')
    library=compiler/'lib/armlib/fz_5s.l'; member='dnaninf.o'
    obj=subprocess.check_output(['/usr/bin/llvm-ar','p',str(library),member])
    view=json.loads(subprocess.check_output(['/usr/bin/llvm-readobj','--elf-output-style=JSON','--sections','--symbols','--relocations','-'],input=obj))[0]
    sections=[row['Section'] for row in view['Sections']]
    code=[s for s in sections if s['Flags']['Value'] & 2]
    if len(code)!=1 or code[0]['Name']['Name']!='x$fpl$dnaninf' or code[0]['Size']!=184:
        raise ValueError('unexpected runtime object layout')
    section=code[0]
    if any(s['Type']['Value'] in (4,9) and s['Info']==section['Index'] and s['Size'] for s in sections):
        raise ValueError('runtime code needs relocations; raw comparison inappropriate')
    original=(root/'.decomp/stock/stock-v4.49.bin').read_bytes()
    if sha(original)!='e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7':
        raise ValueError('wrong firmware')
    code_bytes=obj[section['Offset']:section['Offset']+section['Size']]
    if code_bytes!=original[0x1e4f0:0x1e5a8]: raise ValueError('runtime code does not match')
    symbols=[row['Symbol']['Name']['Name'] for row in view['Symbols'] if row['Symbol']['Section']['Value']==section['Index']]
    if '__fpl_dnaninf' not in symbols: raise ValueError('unexpected runtime symbol')
    (a.output/member).write_bytes(obj)
    (a.output/'object.json').write_text(json.dumps(view,indent=2)+'\n')
    result={'observed_at':datetime.now(timezone.utc).isoformat(),'source':'user supplied ARMCC folder',
            'source_url':None,'source_url_status':'requested from user; not independently authenticated',
            'file_count':len(files),'total_bytes':sum(row['bytes'] for row in files),'file_inventory_sha256':sha(inventory),
            'compiler':next(row for row in files if row['path']=='bin/armcc.exe'),
            'linker':next(row for row in files if row['path']=='bin/armlink.exe'),
            'library':next(row for row in files if row['path']=='lib/armlib/fz_5s.l'),
            'member':member,'member_sha256':sha(obj),'section':section['Name']['Name'],
            'section_sha256':sha(code_bytes),'stock_range':['0x0001e4f0','0x0001e5a8'],
            'equal_bytes':184,'code_relocations':0,'symbols':symbols,
            'conclusion':'exact runtime-library fingerprint; not proof of application compiler version or recovered C'}
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
