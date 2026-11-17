#!/usr/bin/env python3
"""Run a pinned baseline binary and the current build back to back on one node.

For performance work that must not change results. Every case is run with
both binaries, one after the other, and their physical outputs must be
byte-identical before a timing ratio means anything. Timings are single
observations on a shared cluster. No acceptance gate is evaluated and no
registered case is replaced: the runs are short excerpts of registered setups.

A baseline that takes long can come from a record of an earlier run of the
same binary, arguments and configuration: its hashes are as binding, its
timings are from another day and are labelled so.

The new build is also run in other configurations (VARIANTS), and its final
state is compared number by number with its own run of the same case. A
variant in IDENTITY_VARIANTS is an existing configuration: the baseline runs
it too and the outputs must be byte-identical. The others are measurements
for a decision, never requirements; a failed measurement stops nothing.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
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
# `--suite historical`: short cases of the other profiles with their complete
# arguments, the historical default paper-global-v2 among them (also with
# fluid mesh motion, which rebuilds the mesh at every trial). No campaign
# options are added, there are no variants, and every output must be
# byte-identical between the binaries.
HISTORICAL = {
    'paper_global_alfven32_fluid': (['--profile', 'paper-global-v2', '--case', 'alfven', '--n', '32', '--jitter', '0.15',
                                     '--motion', 'fluid', '--time', '0.02'], 1800),
    'paper_global_loop64_fixed': (['--profile', 'paper-global-v2', '--case', 'loop', '--n', '64', '--jitter', '0.15',
                                   '--time', '0.02'], 1800),
    'bulk_frame_alfven64_rigid_boost': (['--profile', 'bulk-frame-v1', '--case', 'alfven', '--n', '64', '--jitter', '0.15',
                                         '--motion', 'rigid', *BOOST, '--time', '0.02'], 1800),
    'heun_alfven64_rigid_boost': (['--profile', 'bulk-frame-heun-v1', '--case', 'alfven', '--n', '64', '--jitter', '0.15',
                                   '--motion', 'rigid', *BOOST, '--time', '0.02'], 1800),
    'spline_loop64_fixed': (['--profile', 'bulk-frame-heun-spline-v1', '--case', 'loop', '--n', '64', '--jitter', '0.15',
                             '--time', '0.02'], 1800),
    'projected_alfven64_fixed': (['--profile', 'bulk-frame-heun-projected-v1', '--case', 'alfven', '--n', '64',
                                  '--jitter', '0.15', '--time', '0.02'], 1800),
    'quadratic_defaults_alfven64': (['--profile', PROFILE, '--case', 'alfven', '--n', '64', '--jitter', '0.15',
                                     '--time', '0.02'], 1800),
}
SUITES = {'campaign': CASES, 'historical': HISTORICAL}
TIMING = 'timing.json'
# Baselines taken from the record when it matches: the N256 one runs 15 minutes.
RECORD = ROOT/'tests/reference/perf_identity/baseline.json'
RECORDED_CASES = ('alfven256_standing',)
# name -> (options removed from CONFIGURATION, options added). Both projection
# solvers iterate on the same equations to the same residual tolerances;
# without the cached factorization the preconditioner is the Jacobi diagonal.
# The trial step fraction is an opt-in controller option of the new build.
VARIANTS = {
    'iterative_projection': (('--accelerated-projection',), ()),
    'step_fraction_0.95': ((), ('--trial-step-fraction', '0.95')),
    'iterative_step_fraction_0.95': (('--accelerated-projection',), ('--trial-step-fraction', '0.95')),
}
IDENTITY_VARIANTS = ('iterative_projection',)
PHYSICAL = ('rho', 'p', 'vx', 'vy', 'vz', 'bx', 'by', 'bz')
POTENTIAL = ('ax', 'ay', 'az', 'phi')
COUNTERS = ('steps', 'rejected_cfl', 'rejected_state', 'rejected_geometry', 'hll_fallbacks')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def configuration(variant=None):
    removed, added = VARIANTS[variant] if variant else ((), ())
    if not set(removed) <= set(CONFIGURATION) or {a for a in added if a.startswith('--')} & set(CONFIGURATION):
        raise ValueError('Variant removes an option the configuration lacks or adds one it has')
    return [option for option in CONFIGURATION if option not in removed]+list(added)


def command(binary, arguments, threads, destination, variant=None, campaign=True):
    options = configuration(variant) if campaign else []
    return [str(binary), *arguments, *options, '--threads', str(threads), '--output', str(destination)]


def expected_profile(arguments, campaign=True):
    return PROFILE if campaign else arguments[arguments.index('--profile')+1]


def record_of(report):
    """The baseline rows of a completed report, without commands or paths."""
    if report.get('status') != 'completed' or report.get('configuration') != CONFIGURATION:
        raise ValueError('Record needs a completed report of this configuration')
    cases = {}
    for name, (arguments, _) in CASES.items():
        row = report['runs'].get(name+'_baseline')
        if row is None:
            continue
        if row['status'] != 'completed' or row['command'][1:1+len(arguments)] != arguments:
            raise ValueError('Baseline run does not match its case: '+name)
        cases[name] = dict(arguments=arguments, steps=row['steps'], rejected_cfl=row['rejected_cfl'],
                           physical_sha256=row['physical_sha256'], wall_seconds=row['wall_seconds'],
                           timing={k: v for k, v in row['timing'].items() if k != 'phases'})
    return dict(baseline_binary_sha256=report['baseline_binary_sha256'], configuration=CONFIGURATION,
                threads=report['threads'], recorded_utc=report['created_utc'], cases=cases)


def recorded(record, name, arguments, baseline_sha256):
    """The recorded baseline row of one case, or None when it does not apply."""
    if (record is None or name not in RECORDED_CASES or record.get('configuration') != CONFIGURATION or
            record.get('baseline_binary_sha256') != baseline_sha256):
        return None
    row = record.get('cases', {}).get(name)
    if row is None or row['arguments'] != arguments:
        return None
    return dict(status='recorded', recorded_utc=record['recorded_utc'], recorded_threads=record['threads'],
                **{k: row[k] for k in ('steps', 'rejected_cfl', 'physical_sha256', 'wall_seconds', 'timing')})


def table(path):
    with path.open(newline='') as stream:
        rows = list(csv.reader(stream))
    return rows[0], [[float(x) for x in row] for row in rows[1:]]


def measure(reference, other):
    """Column by column, how far two final states of one case are apart."""
    (header, a), (other_header, b) = table(reference/'final.csv'), table(other/'final.csv')
    if header != other_header or len(a) != len(b) or not a:
        raise ValueError('Final states of different shape')
    columns = {}
    for k, name in enumerate(header):
        columns[name] = dict(max_abs_difference=max(abs(x[k]-y[k]) for x, y in zip(a, b)),
                             max_abs_value=max(abs(x[k]) for x in a))
    largest = lambda names: max(columns[n]['max_abs_difference'] for n in names)
    summaries = [json.loads((d/'summary.json').read_text()) for d in (reference, other)]
    return dict(columns=columns, largest_physical_difference=largest(PHYSICAL),
                largest_potential_difference=largest(POTENTIAL),
                counters={k: [s[k] for s in summaries] for k in COUNTERS})


def phase(row, name):
    """[seconds, calls] of one profiled phase; zeros when it never ran."""
    return row['timing'].get('phases', {}).get(name, [0., 0])


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


def execute(arguments, log, cap):
    """Exit code and resource usage of this one child; killed at the cap."""
    process = subprocess.Popen(arguments, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    expired = threading.Event()

    def stop():
        expired.set()
        process.kill()
    timer = threading.Timer(cap, stop)
    timer.start()
    try:
        # wait4 reports the usage of this child alone, not the largest so far.
        _, status, usage = os.wait4(process.pid, 0)
    finally:
        timer.cancel()
    process.returncode = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -os.WTERMSIG(status)
    if expired.is_set():
        raise subprocess.TimeoutExpired(arguments, cap)
    return process.returncode, usage


def run(label, binary, arguments, threads, cap, output, variant=None, campaign=True):
    destination = output/label
    destination.mkdir()
    row = dict(command=command(binary, arguments, threads, destination, variant, campaign), status='failed')
    start = time.monotonic()
    try:
        with (destination/'run.log').open('w') as log:
            row['returncode'], usage = execute(row['command'], log, cap)
        # Linux reports the peak resident set in KiB.
        row.update(cpu_seconds=usage.ru_utime+usage.ru_stime, peak_child_rss_kib=usage.ru_maxrss)
        if row['returncode']:
            raise ValueError('Failed evolution: '+label)
        summary = json.loads((destination/'summary.json').read_text())
        if not summary['completed'] or summary['profile'] != expected_profile(arguments, campaign):
            raise ValueError('Incomplete or mismatched output: '+label)
        row.update(status='completed', steps=summary['steps'], rejected_cfl=summary['rejected_cfl'],
                   physical_sha256=physical_hashes(destination),
                   timing=json.loads((destination/TIMING).read_text()))
    except subprocess.TimeoutExpired:
        row['status'] = 'timeout'
        raise
    finally:
        row['wall_seconds'] = time.monotonic()-start
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, help='pinned vector-potential binary')
    parser.add_argument('--baseline-sha256', help='refuse another baseline than this one')
    parser.add_argument('--candidate', type=Path, default=ROOT/'target/release/vector-potential')
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--quick', action='store_true', help='only the three shortest campaign cases')
    parser.add_argument('--suite', choices=sorted(SUITES), default='campaign')
    parser.add_argument('--record', type=Path, default=RECORD, help='recorded baselines of RECORDED_CASES')
    parser.add_argument('--run-every-baseline', action='store_true', help='ignore the record')
    parser.add_argument('--no-variants', action='store_true', help='skip the VARIANTS measurements')
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--extract-record', type=Path, metavar='REPORT',
                        help='print the baseline record of a completed report and exit')
    args = parser.parse_args()
    if args.extract_record:
        print(json.dumps(record_of(json.loads(args.extract_record.read_text())), indent=1, allow_nan=False))
        return 0
    if args.baseline is None or args.output_dir is None:
        parser.error('--baseline and --output-dir are required')
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
    record = None
    if not args.run_every_baseline and args.record.is_file():
        record = json.loads(args.record.read_text())
    report = dict(created_utc=datetime.now(timezone.utc).isoformat(), status='running',
                  scope='Byte identity of physical outputs and single shared-cluster timings; not acceptance.',
                  baseline_binary_sha256=sha(baseline), candidate_binary_sha256=sha(candidate),
                  threads=args.threads, visible_cpus=os.cpu_count(), suite=args.suite,
                  configuration=CONFIGURATION if args.suite == 'campaign' else None,
                  runs={}, comparisons={}, variants={})
    campaign = args.suite == 'campaign'
    cases = SUITES[args.suite]
    dump = lambda: (output/'report.json').write_text(json.dumps(report, indent=1, allow_nan=False)+'\n')
    dump()
    try:
        for name, (arguments, cap) in cases.items():
            if args.quick and campaign and name not in QUICK:
                continue
            for variant in (None, *(() if args.no_variants or not campaign else VARIANTS)):
                key = name if variant is None else f'{name}_{variant}'
                identity = variant is None or variant in IDENTITY_VARIANTS
                try:
                    rows = {}
                    for label, binary in (('baseline', baseline), ('candidate', candidate)):
                        if label == 'baseline' and not identity:
                            continue
                        row = recorded(record, name, arguments, report['baseline_binary_sha256']) \
                            if label == 'baseline' and variant is None and campaign else None
                        if row is None:
                            print(f'Starting {key} {label}', flush=True)
                            row = run(f'{key}_{label}', binary, arguments, args.threads, cap, output, variant,
                                      campaign)
                        rows[label] = report['runs'][f'{key}_{label}'] = row
                        dump()
                    if identity:
                        report['comparisons'][key] = dict(compare(rows['baseline'], rows['candidate']),
                                                          baseline_timing=rows['baseline']['status'])
                        print(key, json.dumps(report['comparisons'][key]), flush=True)
                    if variant is not None:
                        main, row = report['runs'][f'{name}_candidate'], rows['candidate']
                        report['variants'].setdefault(variant, {})[name] = dict(
                            measure(output/f'{name}_candidate', output/f'{key}_candidate'), status='completed',
                            evolution_seconds=[r['timing']['evolution_seconds'] for r in (main, row)],
                            total_seconds=[r['timing']['total_seconds'] for r in (main, row)],
                            peak_child_rss_kib=[r['peak_child_rss_kib'] for r in (main, row)],
                            projections=phase(row, 'stage/projection'),
                            iterations=phase(row, 'projection/iterations')[1])
                        print(key, json.dumps({k: v for k, v in report['variants'][variant][name].items()
                                               if k != 'columns'}), flush=True)
                except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
                    # A measurement fails alone; an identity requirement fails the report.
                    if identity:
                        raise
                    report['variants'].setdefault(variant, {})[name] = dict(
                        status='failed', error=f'{type(error).__name__}: {error}')
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
