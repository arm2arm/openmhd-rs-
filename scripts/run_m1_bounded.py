#!/usr/bin/env python3
"""One bounded M1 regression gate for a named candidate; never M1 acceptance.

Runs the existing bounded shock, mesh-symmetry, wave/boost and coarse
shock/vortex suites for one evolution configuration, each in a fresh
subdirectory with its own provenance, and reduces them to one verdict:
whether the short development blockers of issue #22 are closed for that
configuration. A timeout, crash or missing summary is a failure. Passing this
gate only permits planning the unchanged full M1 matrix; it submits no job.
"""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import time

from run_m1_wave_loop import ROOT, dump, sha, RIEMANN_SOLVERS, riemann_matches

CANDIDATE = 'bulk-frame-heun-quadratic-v1'
SCRIPTS = Path(__file__).resolve().parent


def stages(profile, kappa, medium, medium_jobs=3, case_timeout=30., medium_timeout=600., riemann='hlld'):
    """(name, command tail, summary file, wall cap in seconds, expectation)."""
    evolution = ['--profile', profile, '--accelerated-projection', '--projection-screening', str(kappa)]
    bounded = ['--jobs', '3', '--timeout', str(case_timeout)]
    short_scale = max(1., case_timeout/30.)
    result = [
        ('shock_short', ['run_shock_repro.py', *bounded, *evolution], 'summary.json', 300*short_scale,
         'four nx256 x ny4 t=.01 Brio cases: positive, conservative, seam isolated, boost pairs pass, regular Bx gated'),
        ('shock_symmetry', ['run_shock_symmetry.py', *bounded, '--projection-screening', str(kappa)], 'summary.json', 300*short_scale,
         'nx256 t=.1: column mesh passes every gate; planar candidate passes with Bx diagnostic; '
         'literal paper profile on planar jitter is the known failure #20 and is not this candidate'),
        ('waves_short', ['run_projection_screening.py', *bounded, '--kappa', str(kappa)], 'analysis.json', 600*short_scale,
         'N8/16/32 t=.02 Alfven orders >=1.8 regular and jittered, wave and shock boost pairs, regular Bx'),
        ('physics_quick', ['run_m1_physics.py', '--quick', *bounded, *evolution], 'summary.json', 600*short_scale,
         'Brio nx64/128 and Orszag-Tang N16/32 with boosts: all complete and boost-consistent; state and '
         'diagnostic gates at the finest quick grid of each family (coarser grids are below every registered grid)'),
    ]
    if medium:
        result.append(('waves_medium', ['run_m1_wave_loop.py', '--quick', '--suite', 'physical', '--jobs', str(medium_jobs), '--timeout', str(medium_timeout), *evolution],
                       'summary.json', max(3600, math.ceil(48/medium_jobs)*medium_timeout+180),
                       'Alfven and loop N32/64 t=1, fixed and comoving, regular and jittered: all complete, positive, '
                       'conservative; every boost pair passes'))
    if riemann not in RIEMANN_SOLVERS: raise ValueError('Unknown Riemann solver')
    if riemann != 'hlld':
        for _,tail,_,_,_ in result:tail.extend(['--riemann',riemann])
    return result


def verdict(name, summary, kappa):
    """Named boolean checks for one stage; every check must hold."""
    if name == 'shock_short':
        return {k: bool(summary[k]) for k in ('complete', 'stability_and_budget', 'boost_checks',
                                              'short_diagnostic_checks', 'short_screen_passed')}
    if name == 'shock_symmetry':
        return {k: bool(summary[k]) for k in ('symmetric_mesh_gates_passed', 'planar_candidate_gates_passed',
                                              'source_and_binary_unchanged')}
    if name == 'waves_short':
        mine = summary['by_kappa'].get(str(float(kappa)))
        checks = dict(configuration_covered=mine is not None,
                      all_runs_completed=summary['completed'] == summary['expected'],
                      source_and_binary_unchanged=bool(summary['source_and_binary_unchanged']))
        for key in ('all_completed_positive_and_conservative', 'wave_orders_passed',
                    'boost_pairs_passed', 'regular_bx_gate_passed'):
            checks[key] = (mine or {}).get(key) is True
        return checks
    if name == 'physics_quick':
        runs = summary['runs']
        finest = {}
        for n, r in runs.items():
            c = r['config']; key = (c['case'], c['jitter'], c['jitter_mode'])
            finest[key] = max(finest.get(key, 0), c['n'])
        gated = [r for r in runs.values()
                 if r['config']['n'] == finest[r['config']['case'], r['config']['jitter'], r['config']['jitter_mode']]]
        return dict(all_runs_completed=bool(summary['complete']) and summary['registered_configuration'],
                    boost_pairs_passed=bool(summary['boost_pairs']) and all(p['status'] == 'pass' for p in summary['boost_pairs']),
                    positive_and_conservative=all(r.get('positive_and_conservative') for r in runs.values()),
                    finest_quick_grid_gates=bool(gated) and all(r.get('state_and_diagnostic_gates') for r in gated))
    if name == 'waves_medium':
        runs = summary['runs']
        return dict(all_runs_completed=bool(runs) and all(r['status'] == 'completed' for r in runs.values()),
                    positive_and_conservative=all(r.get('positive_and_conservative') for r in runs.values()),
                    boost_pairs_passed=bool(summary['pairs']) and all(p.get('status', '').startswith('pass') for p in summary['pairs']))
    raise ValueError('unknown stage '+name)


def assess(records, medium, unchanged=True):
    expected = [s[0] for s in stages(CANDIDATE, 1., medium)]
    complete = [r['name'] for r in records] == expected
    passed = complete and unchanged and all(r['status'] == 'pass' for r in records)
    return dict(stages_expected=expected, bounded_blockers_closed=passed, medium_stage_included=medium,
                source_and_binary_unchanged=unchanged,
                full_matrix_precondition_met=passed and medium,
                full_m1_accepted=False,
                scope='Bounded development gate for one named configuration. The unchanged full shock/reference, '
                      'wave/loop/vortex, spatial/temporal and boost matrix is not evaluated here and remains '
                      'required before any M1 acceptance.')


def run_stage(command, log, cap, cancel=None):
    """Kill the whole stage process group on timeout/interruption, including workers."""
    if cancel is not None and cancel.is_set():
        raise InterruptedError('Sibling phase failed; stage cancelled')
    with subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                          start_new_session=True) as process:
        try:
            if cancel is None:
                return process.wait(timeout=cap)
            deadline = time.monotonic()+cap
            while True:
                if cancel.is_set():
                    raise InterruptedError('Sibling phase failed; stage cancelled')
                remaining = deadline-time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, cap)
                try:
                    return process.wait(timeout=min(.2, remaining))
                except subprocess.TimeoutExpired:
                    pass
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            raise


def execution_matches(name, dest, profile, kappa, riemann='hlld'):
    """Do not accept a partial manifest, mismatched binary, or a different candidate."""
    configs = json.loads((dest/'manifest.json').read_text())
    runs = json.loads((dest/'runs.json').read_text())
    expected = dict(shock_short=4, shock_symmetry=8, waves_short=21, physics_quick=20, waves_medium=48)
    if len(configs) != expected[name] or set(runs) != set(configs):
        return False
    for n, c in configs.items():
        literal = name == 'shock_symmetry' and c['profile'] == 'paper-global-v2'
        if not literal and c['profile'] != profile:
            return False
        if c.get('riemann_solver','hlld') != ('hlld' if literal else riemann):
            return False
        r = runs[n]
        if r.get('config') != c:
            return False
        if 'summary' in r and not riemann_matches(c,r['summary']):
            return False
        if literal and c.get('jitter_mode') == 'planar':
            # Only the documented pressure failure is an expected control outcome.
            # A timeout, crash, or unrelated error cannot stand in for that evidence.
            if (r['status'] != 'failed' or 'conservative/curl closure' not in r.get('error', '')
                    or 'positive density and pressure' not in r.get('error', '')):
                return False
        if r['status'] == 'completed':
            s = r['summary']
            if (s['profile'] != c['profile'] or s.get('projection_screening', 0.) != (0. if literal else kappa)
                    or not riemann_matches(c,s)):
                return False
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--profile', choices=(CANDIDATE,), default=CANDIDATE)
    parser.add_argument('--projection-screening', type=float, default=1.)
    parser.add_argument('--medium', action='store_true',
                        help='Also run the N32/64 t=1 wave/loop pairs (about 25 minutes on three workers)')
    parser.add_argument('--medium-jobs', type=int, default=3,
                        help='Concurrent medium cases, 1..24; short stages remain at three workers')
    parser.add_argument('--case-timeout', type=float, default=30., help='Short-case wall seconds, at most 120; local default 30')
    parser.add_argument('--medium-timeout', type=float, default=600., help='Medium-case wall seconds; REANA campaign uses 1800')
    parser.add_argument('--riemann',choices=RIEMANN_SOLVERS,default='hlld')
    args = parser.parse_args()
    if not math.isfinite(args.projection_screening) or args.projection_screening < 0:
        parser.error('projection screening must be >= 0')
    if not 1 <= args.medium_jobs <= 24:
        parser.error('medium jobs must be 1..24')
    if not math.isfinite(args.case_timeout) or not 0 < args.case_timeout <= 120:
        parser.error('case timeout must be in (0,120] seconds')
    if not math.isfinite(args.medium_timeout) or not 0 < args.medium_timeout <= 1800:
        parser.error('medium timeout must be in (0,1800] seconds')
    out = args.output_dir.resolve()
    if out.exists(): parser.error('Use a fresh output directory')
    out.mkdir(parents=True)
    paths = sorted({*ROOT.glob('crates/**/*.rs'), *ROOT.glob('apps/**/*.rs'),
                    *ROOT.glob('crates/*/Cargo.toml'), *ROOT.glob('apps/*/Cargo.toml'),
                    *ROOT.glob('scripts/*.py'), *ROOT.glob('benchmarks/**/*.json'),
                    ROOT/'Cargo.toml', ROOT/'Cargo.lock', ROOT/'rust-toolchain.toml'})
    sources = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    with tarfile.open(out/'source.tar.gz', 'w:gz') as archive:
        for p in paths: archive.add(p, arcname=str(p.relative_to(ROOT)))
    provenance = dict(created_utc=datetime.now(timezone.utc).isoformat(), profile=args.profile,
                      source_sha256=sources, source_archive_sha256=sha(out/'source.tar.gz'),
                      projection_screening=args.projection_screening, accelerated_projection=True,
                      revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                      dirty_status=subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).strip(),
                      gate_source_sha256=sha(Path(__file__).resolve()), short_workers=3,
                      medium_workers=args.medium_jobs if args.medium else 0, threads_per_case=1)
    if args.riemann != 'hlld':provenance['riemann_solver']=args.riemann
    provenance.update(case_timeout_seconds=args.case_timeout, medium_timeout_seconds=args.medium_timeout)
    records = []
    for name, tail, summary_name, cap, expectation in stages(args.profile, args.projection_screening, args.medium, args.medium_jobs,
                                                           args.case_timeout, args.medium_timeout,args.riemann):
        dest = out/name
        command = [sys.executable, str(SCRIPTS/tail[0]), *tail[1:], '--output-dir', str(dest)]
        record = dict(name=name, command=command, expectation=expectation, timeout_seconds=cap, status='fail')
        started = time.monotonic()
        try:
            with (out/(name+'.log')).open('w') as log:
                returncode = run_stage(command, log, cap)
            record['returncode'] = returncode
            summary = json.loads((dest/summary_name).read_text())
            if name in ('physics_quick', 'waves_medium') and 'runs' not in summary:
                summary['runs'] = json.loads((dest/'runs.json').read_text())
            record['summary_sha256'] = sha(dest/summary_name)
            record['checks'] = verdict(name, summary, args.projection_screening)
            record['checks']['execution_matches'] = execution_matches(name, dest, args.profile, args.projection_screening,args.riemann)
            stage_provenance = json.loads((dest/'provenance.json').read_text())
            binary_hash = stage_provenance['binary_sha256']
            provenance.setdefault('binary_sha256', binary_hash)
            record['checks']['same_binary'] = binary_hash == provenance['binary_sha256']
            record['runs_sha256'] = sha(dest/'runs.json')
            # The symmetry screen exits 1 for the literal profile's known planar failure.
            exit_ok = returncode == 0 or (name == 'shock_symmetry' and returncode == 1)
            record['status'] = 'pass' if exit_ok and record['checks'] and all(record['checks'].values()) else 'fail'
        except subprocess.TimeoutExpired:
            record.update(status='timeout', error='Stage wall-time cap reached; incomplete execution')
        except (OSError, ValueError, KeyError, TypeError) as error:
            record['error'] = f'{type(error).__name__}: {error}'
        record['seconds'] = time.monotonic()-started
        records.append(record)
        dump(out/'gate.json', dict(provenance=provenance, stages=records))
        print(f'{name:15} {record["status"]:8} {record["seconds"]:7.1f}s  '
              f'{ {k: v for k, v in record.get("checks", {}).items() if not v} or ""}', flush=True)
        if record['status'] != 'pass':
            break
    unchanged = (sources == {str(p.relative_to(ROOT)): sha(p) for p in paths}
                 and provenance.get('binary_sha256') == sha(ROOT/'target/release/vector-potential'))
    result = assess(records, args.medium, unchanged)
    if args.riemann != 'hlld':result['riemann_solver']=args.riemann
    dump(out/'gate.json', dict(provenance=provenance, stages=records, **result))
    print(f'Bounded blockers closed for {args.profile}, kappa={args.projection_screening}'
          f'{", flux="+args.riemann if args.riemann != "hlld" else ""}: '
          f'{"YES" if result["bounded_blockers_closed"] else "NO"}. Full M1 acceptance: not evaluated.')
    return 0 if result['bounded_blockers_closed'] else 1


if __name__ == '__main__': raise SystemExit(main())
