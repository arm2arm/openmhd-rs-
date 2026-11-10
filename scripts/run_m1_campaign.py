#!/usr/bin/env python3
"""REANA acceptance sequence: preflight, memory calibration, then full M1 matrices.

Stops at the first failed phase. A completed campaign is evidence for review,
not automatic milestone acceptance. Historical profiles and thresholds stay intact.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

from run_m1_bounded import CANDIDATE, ROOT, SCRIPTS, run_stage
from run_m1_wave_loop import dump, sha, validate_parallelism

EVOLUTION = ['--profile', CANDIDATE, '--accelerated-projection', '--projection-screening', '1']


def memory_bytes(path):
    record = json.loads(path.read_text())
    peak = record.get('peak_process_rss_bytes')
    if record.get('returncode') != 0 or not isinstance(peak, int) or peak <= 0:
        raise ValueError('Missing successful peak resident memory measurement: '+str(path))
    return peak


def worker_budget(peak_bytes, requested):
    # N128 -> N256: 4x cell count plus sparse-factor growth and safety allowance.
    # This is a scheduling estimate, not a measured N256 memory claim.
    estimate = 8*peak_bytes
    workers = min(requested, 24, int(56_000_000_000//estimate)) if estimate > 0 else 0
    if workers < 1:
        raise ValueError('Calibration cannot fit one estimated N256 case in 56 GB')
    threads=max(1,requested//workers)
    validate_parallelism(workers,threads)
    return dict(workers=workers, threads_per_case=threads, measured_peak_bytes=peak_bytes,
                estimated_n256_peak_bytes=estimate, memory_limit_bytes=64_000_000_000,
                reserved_bytes=8_000_000_000, estimate_multiplier=8)


def wave_checks(summary, expected, pairs, full=False):
    runs = summary['runs']
    checks = dict(all_completed=len(runs)==expected and all(r['status']=='completed' for r in runs.values()),
                  positive_and_conservative=bool(runs) and all(r.get('positive_and_conservative') for r in runs.values()),
                  boost_pairs=len(summary['pairs'])==pairs and all(
                      p['status'] in ('pass', 'pass under both reported normalizations') for p in summary['pairs']))
    if full:
        checks['spatial_gates'] = len(summary['alfven_convergence'])==8 and all(
            x['gate']=='pass' for x in summary['alfven_convergence'])
        temporal = summary['temporal']
        checks['temporal_measured'] = isinstance(temporal, list) and len(temporal)==12 and all(
            x['status']=='completed' and math.isfinite(x['errors']['B']['L1']) for x in temporal)
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=24)
    parser.add_argument('--calibration-timeout', type=float, default=7200.,
                        help='Prospective wall seconds per N128 evolution')
    parser.add_argument('--case-timeout', type=float, default=86400.,
                        help='Per full-matrix evolution wall seconds; physical targets stay unchanged')
    parser.add_argument('--calibration-only', action='store_true', help='Stop after preflight and N128 calibration')
    args = parser.parse_args()
    if not 1 <= args.jobs <= 24: parser.error('jobs must be 1..24')
    if any(not math.isfinite(t) or t <= 0 for t in (args.calibration_timeout,args.case_timeout)):
        parser.error('Timeouts must be finite and positive')
    if sys.platform != 'linux':
        parser.error('Run on the REANA Linux backend')
    os.environ['LC_ALL'] = 'C'
    out = args.output_dir.resolve()
    if out.exists(): parser.error('Use a fresh output directory')
    out.mkdir(parents=True)
    paths = sorted({*ROOT.glob('crates/**/*.rs'), *ROOT.glob('apps/**/*.rs'),
                    *ROOT.glob('crates/*/Cargo.toml'), *ROOT.glob('apps/*/Cargo.toml'),
                    *ROOT.glob('scripts/*.py'), *ROOT.glob('benchmarks/**/*.json'),
                    ROOT/'Cargo.toml', ROOT/'Cargo.lock', ROOT/'rust-toolchain.toml'})
    sources = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    report = dict(created_utc=datetime.now(timezone.utc).isoformat(), phases=[], status='running',
                  source_sha256=sources, binary_sha256=sha(ROOT/'target/release/vector-potential'),
                  revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  profile=CANDIDATE, projection_screening=1., jobs_requested=args.jobs,
                  calibration_timeout_seconds=args.calibration_timeout,
                  full_case_timeout_seconds=args.case_timeout,
                  full_m1_accepted=False, all_new_candidate_gates_passed=False)
    dump(out/'campaign.json', report)

    def run(name, script, options, cap, measure=False):
        dest = out/name
        command = [sys.executable, str(SCRIPTS/script), *options, '--output-dir', str(dest)]
        if measure: command = [sys.executable, str(SCRIPTS/'measure_process.py'),
                               '--output', str(out/(name+'.memory.json')), '--', *command]
        row = dict(name=name, command=command, status='failed', timeout_seconds=cap)
        started = time.monotonic()
        try:
            with (out/(name+'.log')).open('w') as log:
                row['returncode'] = run_stage(command, log, cap)
            row['status'] = 'completed' if row['returncode']==0 else 'failed'
            if measure: row['peak_memory_bytes'] = memory_bytes(out/(name+'.memory.json'))
        except subprocess.TimeoutExpired:
            row['status'] = 'timeout'
        except (OSError, ValueError) as error:
            row['error'] = str(error)
        row['seconds'] = time.monotonic()-started
        return row

    def record(row, checks=None):
        if checks is not None:
            row['checks'] = checks
            if not all(checks.values()): row['status']='failed'
        report['phases'].append(row)
        dump(out/'campaign.json', report)
        print(row['name'], row['status'], f'{row["seconds"]:.1f}s', row.get('checks', {}), flush=True)
        if row['status'] != 'completed': raise ValueError('Phase failed: '+row['name'])

    load = lambda name, file='summary.json': json.loads((out/name/file).read_text())
    try:
        row = run('bounded', 'run_m1_bounded.py', ['--medium', '--medium-jobs', str(args.jobs),
                                               '--case-timeout','120','--medium-timeout','1800'], 14400)
        checks = dict(precondition=load('bounded','gate.json').get('full_matrix_precondition_met') is True) if row['status']=='completed' else None
        record(row, checks)
        row = run('mean', 'run_m1_wave_loop.py', ['--suite','mean','--candidate-mean','--jobs',str(args.jobs),
                                               '--timeout','600',*EVOLUTION], 1800)
        record(row, wave_checks(load('mean'),24,12) if row['status']=='completed' else None)

        # At most three cases; distribute the requested core budget without nesting past it.
        calibration_threads=max(1,args.jobs//min(3,args.jobs))
        report['calibration_threads_per_case']=calibration_threads
        dump(out/'campaign.json',report)
        jobs = [('calibration_wave','run_m1_wave_loop.py', ['--suite','physical','--calibration','--jobs',str(min(2,args.jobs)),
                                                          '--threads',str(calibration_threads),'--timeout',str(args.calibration_timeout),*EVOLUTION]),
                ('calibration_vortex','run_m1_physics.py', ['--calibration','--jobs','1','--threads',str(calibration_threads),
                                                         '--timeout',str(args.calibration_timeout),*EVOLUTION])]
        with ThreadPoolExecutor(max_workers=2 if args.jobs>=3 else 1) as pool:
            futures = [pool.submit(run, name, script, options, 2*args.calibration_timeout+600, True) for name,script,options in jobs]
            rows = [f.result() for f in futures]
        for row in rows:
            checks = None
            if row['status']=='completed' and row['name']=='calibration_wave':
                summary = load(row['name'])
                checks = wave_checks(summary,2,1)
                checks['amplitude_error'] = all(r['errors']['final']['B']['L1']/.1 <= .02 for r in summary['runs'].values())
            elif row['status']=='completed':
                runs = load(row['name'],'runs.json')
                checks = dict(complete=len(runs)==1 and all(r['status']=='completed' for r in runs.values()),
                              diagnostics=bool(runs) and all(r.get('state_and_diagnostic_gates') for r in runs.values()))
            record(row, checks)
        report['resources'] = worker_budget(max(r['peak_memory_bytes'] for r in rows), args.jobs)
        dump(out/'campaign.json', report)
        if not args.calibration_only:
            workers = str(report['resources']['workers'])
            threaded=['--threads',str(report['resources']['threads_per_case'])]
            cap = lambda count: math.ceil(count/int(workers))*args.case_timeout+1800
            row = run('physics','run_m1_physics.py',['--jobs',workers,*threaded,'--timeout',str(args.case_timeout),*EVOLUTION],cap(30))
            checks = dict(physics_gates=load('physics')['all_registered_physics_gates'] is True,
                          complete_ladder=load('physics')['completed_evolutions']==30) if row['status']=='completed' else None
            record(row, checks)
            row = run('waves','run_m1_wave_loop.py',['--suite','physical','--temporal','--jobs',workers,*threaded,
                                                  '--timeout',str(args.case_timeout),*EVOLUTION],cap(112))
            record(row, wave_checks(load('waves'),112,48,full=True) if row['status']=='completed' else None)
            report['all_new_candidate_gates_passed'] = True
        report['status'] = 'completed'
    except (OSError, ValueError, KeyError, TypeError) as error:
        report.update(status='failed', error=f'{type(error).__name__}: {error}')
    finally:
        unchanged = (sources == {str(p.relative_to(ROOT)): sha(p) for p in paths}
                     and report['binary_sha256']==sha(ROOT/'target/release/vector-potential'))
        report['source_and_binary_unchanged'] = unchanged
        if not unchanged:
            report.update(status='failed', all_new_candidate_gates_passed=False, error='source/binary changed')
        report['ended_utc'] = datetime.now(timezone.utc).isoformat()
        dump(out/'campaign.json', report)
    return 0 if report['status']=='completed' else 1


if __name__ == '__main__': raise SystemExit(main())
