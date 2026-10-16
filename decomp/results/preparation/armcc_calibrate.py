#!/usr/bin/env python3
"""One fixed ARMCC5 run over unchanged stock calibration hypotheses."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
import armcc_runner as runner
import stock_compare as sc
import calibrate
import armcc_compare

STOCK = 'e91502e8021e61c97a77fb12324e99ee4acb23bee55a5a67d18e26521ef856f7'


def runtime_bytes(elf, entry):
    view = sc.base.elf_view(elf)
    sc.require(view['entry'] == entry | 1, 'wrong Thumb entry')
    sections = [s for s in view['sections'] if s['size']]
    sc.require(len(sections) == 1, 'extra allocated sections')
    section = sections[0]
    sc.require(section['type'] == 1 and section['flags'] == 6 and
               section['address'] == entry, 'unexpected code section')
    data = bytes.fromhex(section['bytes'])
    segments = [s for s in view['segments'] if s['memsz'] or s['filesz']]
    sc.require(len(segments) == 1, 'extra load segments')
    segment = segments[0]
    sc.require(segment['vaddr'] == entry and segment['paddr'] == entry and
               segment['filesz'] == len(data) and segment['memsz'] == len(data) and
               segment['flags'] == 0x80000005 and segment['bytes'] == data.hex(), 'unexpected load mapping')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--backend', choices=['armlink', 'lld'], default='armlink')
    args = parser.parse_args()
    root, out = args.root.resolve(), args.output.resolve()
    raw = (root / '.decomp/stock/stock-v4.49.bin').read_bytes()
    sc.require(sc.base.sha(raw) == STOCK, 'stock identity mismatch')
    out.mkdir(parents=True, exist_ok=False)
    out.chmod(0o700)
    jobs = []
    for start, end, ret, params, body in calibrate.PROBES:
        name = f'fn_{start:08x}'
        build = out / name
        build.mkdir()
        (build / 'candidate.c').write_text(f'{ret} {name}({params}) {{ {body} }}\n')
        (build / 'layout.ld').write_text(armcc_compare.layout({'entry': hex(start), 'id': name}))
        jobs.append({'id': name, 'entry': start, 'end': end})
    link_flags = runner.LINK_FLAGS if args.backend == 'armlink' else runner.LLD_FLAGS
    (out / 'jobs.json').write_bytes(sc.encode({'compile_flags': runner.FLAGS,
        'link_flags': link_flags, 'backend': args.backend, 'jobs': jobs}))
    report = {'date_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'scope': 'fixed ARMCC5 calibration; not certification', 'baseline_sha256': STOCK,
              'compile_flags': runner.FLAGS, 'link_flags': link_flags, 'backend': args.backend,
              'lld': sc.base.pin('/usr/bin/ld.lld') if args.backend == 'lld' else None,
              'armcc': sc.base.pin(root / 'ARMCC/bin/armcc.exe'),
              'armlink': sc.base.pin(root / 'ARMCC/bin/armlink.exe'),
              'runner_sha256': sc.base.sha(Path(runner.__file__).read_bytes()),
              'calibration_script_sha256': sc.base.sha(Path(__file__).read_bytes()),
              'initial_hypotheses_sha256': sc.base.sha(Path(calibrate.__file__).read_bytes()),
              'probes': [], 'certified_match': False}
    report['build'] = runner.build_batch(root, out)
    for job, status in zip(jobs, report['build']['jobs'], strict=True):
        build = out / job['id']
        row = {**status, 'source_sha256': sc.base.sha((build / 'candidate.c').read_bytes())}
        elf_path = build / 'candidate.elf'
        if status['compile_returncode'] == status['link_returncode'] == 0:
            elf = elf_path.read_bytes()
            row['elf_sha256'] = sc.base.sha(elf)
            try:
                reader = runtime_bytes if args.backend == 'armlink' else sc.runtime_bytes
                actual = reader(elf, job['entry'])
                row.update(sc.compare(raw[job['entry']:job['end']], actual, job['entry']))
                row['actual_sha256'] = sc.base.sha(actual)
                row['expected_sha256'] = sc.base.sha(raw[job['entry']:job['end']])
            except sc.Rejected as error:
                row['result'] = 'elf-rejected'
                row['reason'] = str(error)
                row['view'] = sc.base.elf_view(elf)
            for name, argv in (('llvm.txt', ['llvm-objdump', '-d', '--triple=thumbv5te-none-eabi']),
                               ('attributes.txt', ['llvm-readelf', '-A', '-h', '-l', '-S'])):
                (build / name).write_text(sc.base.run([*argv, str(elf_path)]))
        else:
            row['result'] = 'build-failed'
        report['probes'].append(row)
        print(job['id'], row['result'], row.get('actual_bytes'), row.get('expected_bytes'), flush=True)
    (out / 'report.json').write_bytes(sc.encode(report))


if __name__ == '__main__':
    main()
