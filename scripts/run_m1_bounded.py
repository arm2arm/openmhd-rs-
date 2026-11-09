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
from pathlib import Path
import subprocess
import sys
import time

from run_m1_wave_loop import ROOT, dump, sha

CANDIDATE = 'bulk-frame-heun-quadratic-v1'
SCRIPTS = Path(__file__).resolve().parent


def stages(profile, kappa, medium):
    """(name, command tail, summary file, wall cap in seconds, expectation)."""
    evolution = ['--profile', profile, '--accelerated-projection', '--projection-screening', str(kappa)]
    result = [
        ('shock_short', ['run_shock_repro.py', *evolution], 'summary.json', 300,
         'four nx256 x ny4 t=.01 Brio cases: positive, conservative, seam isolated, boost pairs pass, regular Bx gated'),
        ('shock_symmetry', ['run_shock_symmetry.py', '--projection-screening', str(kappa)], 'summary.json', 300,
         'nx256 t=.1: column mesh passes every gate; planar candidate passes with Bx diagnostic; '
         'literal paper profile on planar jitter is the known failure #20 and is not this candidate'),
        ('waves_short', ['run_projection_screening.py'], 'analysis.json', 600,
         'N8/16/32 t=.02 Alfven orders >=1.8 regular and jittered, wave and shock boost pairs, regular Bx'),
        ('physics_quick', ['run_m1_physics.py', '--quick', '--jobs', '3', *evolution], 'summary.json', 600,
         'Brio nx64/128 and Orszag-Tang N16/32 with boosts: all complete and boost-consistent; state and '
         'diagnostic gates at the finest quick grid of each family (coarser grids are below every registered grid)'),
    ]
    if medium:
        result.append(('waves_medium', ['run_m1_wave_loop.py', '--quick', '--suite', 'physical', '--jobs', '3', *evolution],
                       'summary.json', 3600,
                       'Alfven and loop N32/64 t=1, fixed and comoving, regular and jittered: all complete, positive, '
                       'conservative; every boost pair passes'))
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
        checks.update({k: bool(v) for k, v in (mine or {}).items()})
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
                    boost_pairs_passed=all(p['status'] == 'pass' for p in summary['boost_pairs']),
                    positive_and_conservative=all(r.get('positive_and_conservative') for r in runs.values()),
                    finest_quick_grid_gates=bool(gated) and all(r.get('state_and_diagnostic_gates') for r in gated))
    if name == 'waves_medium':
        runs = summary['runs']
        return dict(all_runs_completed=bool(runs) and all(r['status'] == 'completed' for r in runs.values()),
                    positive_and_conservative=all(r.get('positive_and_conservative') for r in runs.values()),
                    boost_pairs_passed=bool(summary['pairs']) and all(p.get('status', '').startswith('pass') for p in summary['pairs']))
    raise ValueError('unknown stage '+name)


def assess(records, medium):
    expected = [s[0] for s in stages(CANDIDATE, 1., medium)]
    complete = [r['name'] for r in records] == expected
    passed = complete and all(r['status'] == 'pass' for r in records)
    return dict(stages_expected=expected, bounded_blockers_closed=passed, medium_stage_included=medium,
                full_m1_accepted=False,
                scope='Bounded development gate for one named configuration. The unchanged full shock/reference, '
                      'wave/loop/vortex, spatial/temporal and boost matrix is not evaluated here and remains '
                      'required before any M1 acceptance.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--profile', default=CANDIDATE)
    parser.add_argument('--projection-screening', type=float, default=1.)
    parser.add_argument('--medium', action='store_true',
                        help='Also run the N32/64 t=1 wave/loop pairs (about 25 minutes on three workers)')
    args = parser.parse_args()
    if not math.isfinite(args.projection_screening) or args.projection_screening < 0:
        parser.error('projection screening must be >= 0')
    out = args.output_dir.resolve()
    if out.exists(): parser.error('Use a fresh output directory')
    out.mkdir(parents=True)
    provenance = dict(created_utc=datetime.now(timezone.utc).isoformat(), profile=args.profile,
                      projection_screening=args.projection_screening, accelerated_projection=True,
                      revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                      dirty_status=subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).strip(),
                      gate_source_sha256=sha(Path(__file__).resolve()), workers_per_stage=3, threads_per_case=1)
    records = []
    for name, tail, summary_name, cap, expectation in stages(args.profile, args.projection_screening, args.medium):
        dest = out/name
        command = [sys.executable, str(SCRIPTS/tail[0]), *tail[1:], '--output-dir', str(dest)]
        record = dict(name=name, command=command, expectation=expectation, timeout_seconds=cap, status='fail')
        started = time.monotonic()
        try:
            with (out/(name+'.log')).open('w') as log:
                done = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=cap)
            record['returncode'] = done.returncode
            summary = json.loads((dest/summary_name).read_text())
            if name in ('physics_quick', 'waves_medium') and 'runs' not in summary:
                summary['runs'] = json.loads((dest/'runs.json').read_text())
            record['summary_sha256'] = sha(dest/summary_name)
            record['checks'] = verdict(name, summary, args.projection_screening)
            # The symmetry screen exits 1 for the literal profile's known planar failure.
            exit_ok = done.returncode == 0 or name == 'shock_symmetry'
            record['status'] = 'pass' if exit_ok and record['checks'] and all(record['checks'].values()) else 'fail'
        except subprocess.TimeoutExpired:
            record.update(status='timeout', error='Stage wall-time cap reached; incomplete execution')
        except (OSError, ValueError, KeyError) as error:
            record['error'] = f'{type(error).__name__}: {error}'
        record['seconds'] = time.monotonic()-started
        records.append(record)
        dump(out/'gate.json', dict(provenance=provenance, stages=records))
        print(f'{name:15} {record["status"]:8} {record["seconds"]:7.1f}s  '
              f'{ {k: v for k, v in record.get("checks", {}).items() if not v} or ""}', flush=True)
    result = assess(records, args.medium)
    dump(out/'gate.json', dict(provenance=provenance, stages=records, **result))
    print(f'Bounded blockers closed for {args.profile}, kappa={args.projection_screening}: '
          f'{"YES" if result["bounded_blockers_closed"] else "NO"}. Full M1 acceptance: not evaluated.')
    return 0 if result['bounded_blockers_closed'] else 1


if __name__ == '__main__': raise SystemExit(main())
