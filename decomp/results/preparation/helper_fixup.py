#!/usr/bin/env python3
"""Generate analysis-only callfixup p-code. Never emits firmware instructions.

The same body is executed in the offline emulator before installation. Numeric
instruction addresses in comments identify the original operations represented.
"""
import argparse
from pathlib import Path


def body():
    lines = ['local a:4; local b:4; local v:4; local c:4; local inline_ptr:4;',
             'inline_ptr = inst_next; r6 = *:4 inline_ptr; lr = inline_ptr + 4;',
             'NG = r6 s< 0; ZR = r6 == 0;',
             'if (NG) goto <class_a>;']

    def flags(left, right, subtract=False, dest=None, carry=False):
        lines.extend([f'a = {left}; b = {right};', 'c = zext(CY);' if carry else 'c = 0;'])
        if subtract:
            lines.extend(['v = a - b;', 'CY = a >= b; OV = sborrow(a,b);'])
        else:
            lines.extend(['v = a + b;', 'OV = scarry(a,b) ^^ scarry(v,c);',
                          'CY = carry(a,b) || carry(v,c); v = v + c;'])
        lines.append('NG = v s< 0; ZR = v == 0;')
        if dest:
            lines.append(f'{dest} = v;')

    # 1e4fc..1e508: r2:r3 classification, skipped for negative inline words.
    flags('r2', '1', subtract=True)
    lines.append('r5 = r3 + r3 + zext(CY);')
    flags('r5', '0x200000')
    lines += ['if (CY && !ZR) goto <unordered>;', '<class_a>']
    # 1e50c..1e534: r0:r1 classification; preserve initial r5 on skipped path.
    flags('r0', '1', subtract=True)
    lines.append('r12 = r1 + r1 + zext(CY);')
    flags('r12', '0x200000')
    lines += ['if (CY && !ZR) goto <unordered>;', 'if (!ZR) goto <sign_b>;', 'r12 = r1 >> 31;']
    flags('r5', '0x200000')
    lines += ['r12 = r12 + (r12 << 1) + 2;', 'if (!ZR) goto <dispatch>;',
              'r12 = r12 + (r3 >> 31) + zext(CY);', 'goto <dispatch>;',
              '<unordered> r12 = 8; goto <dispatch>;', '<sign_b> r12 = r3 >> 31;',
              '<dispatch> r5 = r12 + (r12 << 1); r6 = (r6 >> r5) & 7;']
    flags('r6', '4', subtract=True, dest='r12')
    lines += ['if (CY) goto <outer>;',
              'r12 = lr + (r6 << 2);',
              'r4 = *:4 sp; r5 = *:4 (sp+4); r6 = *:4 (sp+8); lr = *:4 (sp+12); sp = sp+16;',
              'TB = (r12 & 1) != 0; setISAMode(TB); pc = r12 & 0xfffffffe; goto [pc];',
              '<outer> if (r6 >= 6) goto <nan>;',
              'if (r6 == 5) goto <normalize>;', 'r1 = r3; r0 = r2;', '<normalize>']
    flags('r0', '1', subtract=True)
    flags('r1', 'r1', carry=True, dest='r4')
    lines.append('if (ZR) goto <check_hi>;')
    flags('0x200000', 'r4', subtract=True, dest='r4')
    lines += ['<check_hi> if (!(CY && !ZR)) goto <return_outer>;',
              'r0 = 0; r1 = r1 & 0x80000000; goto <return_outer>;',
              '<nan> r0 = 0; r1 = 0x7ff80000;',
              '<return_outer> r4 = *:4 sp; r5 = *:4 (sp+4); r6 = *:4 (sp+8);',
              'a = *:4 (sp+12); sp = sp+16;',
              'TB = (a & 1) != 0; setISAMode(TB); pc = a & 0xfffffffe; return [pc];']
    return '\n'.join(lines)+'\n'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path, help='fresh ignored local output directory')
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    code = body()
    (a.output/'runtime.sleigh').write_text(code)
    (a.output/'runtime.xml').write_text('<callfixup name="slimblade_v449_runtime"><pcode><body><![CDATA[\n'+code+']]></body></pcode></callfixup>\n')


if __name__ == '__main__':
    main()
