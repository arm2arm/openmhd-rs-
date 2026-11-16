#!/usr/bin/env python3
"""Run a pinned baseline binary and the current build back to back on one node.

For performance work that must not change results. Every case is run with
both binaries, one after the other, and their physical outputs must be
byte-identical before a timing ratio means anything. Timings are single
observations on a shared cluster. No acceptance gate is evaluated and no
registered case is replaced: the runs are short excerpts of registered setups.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'bulk-frame-heun-quadratic-v1'
# The configuration of the 2026-11-13 fan-out campaign.
CONFIGURATION = ['--profile', PROFILE, '--motion', 'rigid', '--accelerated-projection',
                 '--projection-screening', '1', '--riemann', 'hlld-pressure',
                 '--potential-limiter', 'smooth-extrema']
BOOST = ['--mesh-x', '2', '--mesh-y', '-1', '--boost-x', '2', '--boost-y', '-1']
# name -> (arguments, wall cap in seconds). Physical times are short on purpose.
CASES = {
    'alfven128_standing': (['--case', 'alfven', '--n', '128', '--jitter', '0', '--parallel-velocity', '1',
                            '--time', '0.03'], 1800),
    'alfven128_jitter_boost': (['--case', 'alfven', '--n', '128', '--jitter', '0.15', '--parallel-velocity', '1',
                                '--time', '0.03', *BOOST], 1800),
    'loop128_jitter': (['--case', 'loop', '--n', '128', '--jitter', '0.15', '--time', '0.02'], 3600),
    'vortex128_jitter': (['--case', 'orszag-tang', '--n', '128', '--jitter', '0.15', '--time', '0.02'], 3600),
    'brio512_jitter': (['--case', 'brio-wu', '--n', '512', '--jitter', '0.15', '--time', '0.02'], 1800),
    'alfven256_standing': (['--case', 'alfven', '--n', '256', '--jitter', '0', '--parallel-velocity', '1',
                            '--time', '0.004'], 7200),
}
QUICK = ('alfven128_standing', 'alfven128_jitter_boost', 'brio512_jitter')
TIMING = 'timing.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(binary, arguments, threads, destination):
    return [str(binary), *arguments, *CONFIGURATION, '--threads', str(threads), '--output', str(destination)]


def physical_hashes(directory):
    """Every output except the wall-clock record and the console log."""
    files = {p.name: sha(p) for p in sorted(directory.iterdir())
             if p.is_file() and p.suffix in ('.json', '.csv') and p.name != TIMING}
    if not {'initial.csv', 'final.csv', 'summary.json', 'history.json'} <= files.keys():
        raise ValueError('Missing physical output in '+directory.name)
    return files


def compare(before, after):
    """Identity of the physical files and the measured ratios of one case."""
    names = sorted(set(before['physical_sha256']) | set(after['physical_sha256']))
    different = [n for n in names if before['physical_sha256'].get(n) != after['physical_sha256'].get(n)]
    ratio = lambda key: before['timing'][key]/after['timing'][key] if after['timing'][key] > 0 else None
    return dict(bit_identical=not different, different_files=different, files_compared=len(names),
                evolution_speedup=ratio('evolution_seconds'), initialization_speedup=ratio('initialization_seconds'),
                total_speedup=ratio('total_seconds'), wall_speedup=before['wall_seconds']/after['wall_seconds'])


def run(label, binary, arguments, threads, cap, output):
    destination = output/label
    destination.mkdir()
    row = dict(command=command(binary, arguments, threads, destination), status='failed')
    start = time.monotonic()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    try:
        with (destination/'run.log').open('w') as log:
            done = subprocess.run(row['command'], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=cap)
        row['returncode'] = done.returncode
        if done.returncode:
            raise ValueError('Failed evolution: '+label)
        summary = json.loads((destination/'summary.json').read_text())
        if not summary['completed'] or summary['profile'] != PROFILE:
            raise ValueError('Incomplete or mismatched output: '+label)
        row.update(status='completed', steps=summary['steps'], rejected_cfl=summary['rejected_cfl'],
                   physical_sha256=physical_hashes(destination),
                   timing=json.loads((destination/TIMING).read_text()))
    except subprocess.TimeoutExpired:
        row['status'] = 'timeout'
        raise
    finally:
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        row.update(wall_seconds=time.monotonic()-start,
                   cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
                   peak_child_rss_kib=after.ru_maxrss)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True, help='pinned vector-potential binary')
    parser.add_argument('--baseline-sha256', help='refuse another baseline than this one')
    parser.add_argument('--candidate', type=Path, default=ROOT/'target/release/vector-potential')
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--quick', action='store_true', help='only the three shortest cases')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.threads <= 24:
        parser.error('threads must be 1..24')
    output = args.output_dir.resolve()
    if output.exists():
        parser.error('Use a fresh output directory')
    baseline, candidate = args.baseline.resolve(), args.candidate.resolve()
    if args.baseline_sha256 and sha(baseline) != args.baseline_sha256:
        parser.error('Baseline binary checksum mismatch')
    output.mkdir(parents=True)
    baseline.chmod(0o755)
    report = dict(created_utc=datetime.now(timezone.utc).isoformat(), status='running',
                  scope='Byte identity of physical outputs and single shared-cluster timings; not acceptance.',
                  baseline_binary_sha256=sha(baseline), candidate_binary_sha256=sha(candidate),
                  threads=args.threads, visible_cpus=os.cpu_count(), configuration=CONFIGURATION,
                  runs={}, comparisons={})
    dump = lambda: (output/'report.json').write_text(json.dumps(report, indent=1, allow_nan=False)+'\n')
    dump()
    try:
        for name, (arguments, cap) in CASES.items():
            if args.quick and name not in QUICK:
                continue
            rows = {}
            for label, binary in (('baseline', baseline), ('candidate', candidate)):
                print(f'Starting {name} {label}', flush=True)
                try:
                    rows[label] = run(f'{name}_{label}', binary, arguments, args.threads, cap, output)
                finally:
                    dump()
                report['runs'][f'{name}_{label}'] = rows[label]
                dump()
            report['comparisons'][name] = compare(rows['baseline'], rows['candidate'])
            print(name, json.dumps(report['comparisons'][name]), flush=True)
            dump()
        if sha(baseline) != report['baseline_binary_sha256'] or sha(candidate) != report['candidate_binary_sha256']:
            raise ValueError('A binary changed during the comparison')
        identical = all(c['bit_identical'] for c in report['comparisons'].values())
        report.update(status='completed', all_bit_identical=identical)
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        report.update(status='failed', error=f'{type(error).__name__}: {error}')
    finally:
        report['ended_utc'] = datetime.now(timezone.utc).isoformat()
        dump()
    print('Comparison:', report['status'], '| all physical outputs byte-identical:',
          report.get('all_bit_identical'), flush=True)
    return 0 if report['status'] == 'completed' and report['all_bit_identical'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
