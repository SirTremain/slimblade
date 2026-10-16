#!/usr/bin/env python3
"""Fresh pinned rebuild of unchanged calibration hypotheses, not worker drafts."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
import armcc_compare as ac
from calibrate import PROBES


def replay(lock_path, digest, output):
    lock = ac.load_lock(lock_path, digest)
    ac.require(not output.exists(), 'use a fresh output directory')
    sources = {}
    for start, end, ret, params, body in PROBES:
        name = f'fn_{start:08x}'
        ac.require(ac.validate_task(lock['tasks'][name], lock['baseline_bytes']) == (start, end),
                   'fixed calibration range differs')
        sources[name] = f'{ret} {name}({params}) {{ {body} }}\n'
    ac.require(set(sources) == set(lock['tasks']), 'different calibration task set')
    output.mkdir(parents=True, mode=0o700)
    built = ac.build_sources(lock, sources, output)
    raw = Path(lock['baseline']['path']).read_bytes()
    results = []
    for start, end, *_ in PROBES:
        name = f'fn_{start:08x}'
        actual = ac.runtime_bytes(built[name]['elf'], start)
        result = {**ac.sc.compare(raw[start:end], actual, start), 'task': name,
                  'source_sha256': ac.sc.base.sha(sources[name].encode()),
                  'elf_sha256': ac.sc.base.sha(built[name]['elf']),
                  'actual_sha256': ac.sc.base.sha(actual), 'signature': built[name]['signature']}
        results.append(result)
        print(name, result['result'], result['actual_bytes'], result['expected_bytes'], flush=True)
    ac.load_lock(lock_path, digest)
    report = {'scope': 'fixed calibration replay only', 'certified_match': False,
              'matching_coverage': 'unknown', 'lock_sha256': digest,
              'date': datetime.now(timezone.utc).isoformat(), 'results': results,
              'script_sha256': ac.sc.base.sha(Path(__file__).read_bytes()),
              'hypotheses_sha256': ac.sc.base.sha((Path(__file__).parent / 'calibrate.py').read_bytes())}
    (output / 'report.json').write_bytes(ac.sc.encode(report))
    ac.require(all(r['result'] == 'exact-range-bytes' for r in results), 'calibration replay mismatch')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', type=Path, required=True)
    parser.add_argument('--lock-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    replay(args.lock, args.lock_sha256, args.output)
