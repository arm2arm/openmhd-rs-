#!/usr/bin/env python3
"""Reduce one fan-out campaign to the registered phase checks (no execution).

The historical run_m1_campaign.py batches every case inside one workflow.
Under the per-case policy the same phases are separate REANA workflows: one
short bounded-gate workflow and one plan of independent cases per phase
(scripts/reana_cases.py). This script applies the unchanged checks of
run_m1_bounded.py and run_m1_campaign.py to those outputs for one explicit
configuration. Pair, ladder and family gates are the frozen production
evaluation stored in each plan checkpoint; nothing is re-measured and no
threshold is defined here. A passing verdict is evidence for review, never
M1 acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import run_m1_bounded as bounded
import run_m1_campaign as campaign
from run_m1_physics import configurations as physics_configurations
from run_m1_wave_loop import configurations as wave_configurations, limiter_arguments, limiter_matches
from run_m1_wave_loop import step_arguments, step_matches, projection_matches

PROFILE = bounded.CANDIDATE
STUDY = 'm1-limiter-bounded'
# Short-stage study of each configuration: (iterative projection, trial step fraction).
BOUNDED_STUDIES = {(False, None): 'm1-limiter-bounded', (True, None): 'm1-iterative-bounded',
                   (True, .95): 'm1-iterative-step-bounded'}
PHASES = ('bounded_short', 'bounded_medium', 'mean', 'calibration_wave', 'calibration_vortex', 'physics', 'waves')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def registered(riemann):
    """The unchanged registered case matrices of each fan-out phase."""
    def waves(**changes):
        arguments = dict(suite='physical', candidate_mean=True, profile=PROFILE, quick=False,
                         temporal=False, calibration=False, riemann=riemann)
        return wave_configurations(SimpleNamespace(**dict(arguments, **changes)))[0]
    return dict(medium=waves(quick=True), mean=waves(suite='mean'), waves=waves(temporal=True),
                physics=physics_configurations(False, PROFILE, riemann))


def bounded_checks(directory, snapshot_sha256, riemann, limiter, iterative=False, step=None):
    """The four short stages, run by the legacy gate inside one workflow of the same snapshot."""
    study = BOUNDED_STUDIES[iterative, step]
    execution = load(directory/'execution.json')
    artifacts = load(directory/'artifacts.sha256.json')
    gate_file = directory/study/'gate.json'
    gate = load(gate_file)
    provenance = gate['provenance']
    names = [stage[0] for stage in bounded.stages(PROFILE, 1., False)]
    return dict(
        workflow_completed=execution['status'] == 'completed' and execution['study'] == study,
        same_snapshot=execution['snapshot_sha256'] == snapshot_sha256,
        gate_file_unchanged=sha(gate_file) == artifacts[f'outputs/{study}/gate.json'],
        four_short_stages_passed=([s['name'] for s in gate['stages']] == names
                                  and all(s['status'] == 'pass' for s in gate['stages'])),
        blockers_closed=gate['bounded_blockers_closed'] is True and gate['source_and_binary_unchanged'] is True,
        configuration=(provenance['profile'] == PROFILE and provenance['projection_screening'] == 1.
                       and provenance.get('riemann_solver', 'hlld') == riemann
                       and provenance.get('potential_limiter') == limiter
                       and gate.get('potential_limiter') == limiter
                       and provenance.get('accelerated_projection') is (not iterative)
                       and gate.get('iterative_projection', False) is iterative
                       and provenance.get('trial_step_fraction') == step
                       and gate.get('trial_step_fraction') == step))


def plan_checks(directory, snapshot_sha256, binary_sha256, cases, riemann, limiter, iterative=False, step=None):
    """Identity, completeness and configuration of one plan; returns (checks, runs, checkpoint).

    The names differ from those of the campaign checks merged with them, so neither replaces the other.
    """
    plan = load(directory/'plan.json')
    runs = load(directory/'runs.json')
    checkpoint = load(directory/'checkpoint.json')
    entries = {e['specification']['config']['name']: e for e in plan['cases']}
    options = dict(accelerated_projection=not iterative, projection_screening=1.)
    if limiter is not None:
        options['potential_limiter'] = limiter
    if step is not None:
        options['trial_step_fraction'] = step

    def binary(entry):
        record = directory/'download'/entry['directory']/'outputs/execution.json'
        return record.exists() and load(record).get('binary_sha256') == binary_sha256

    checks = dict(
        same_snapshot=plan['snapshot_sha256'] == snapshot_sha256,
        registered_cases={n: e['specification']['config'] for n, e in entries.items()} == cases,
        registered_options=all(e['specification']['options'] == options for e in entries.values()),
        terminal_without_errors=(checkpoint.get('all_terminal') is True and not checkpoint['observation_errors']
                                 and not checkpoint['execution_failures']),
        every_planned_case_completed=(set(runs) == set(entries)
                                      and all(r['status'] == 'completed' for r in runs.values())),
        same_binary=bool(entries) and all(binary(e) for e in entries.values()),
        candidate_and_limiter_metadata=bool(runs) and all(
            campaign.candidate_matches(r, riemann) and limiter_matches(r.get('summary', {}), limiter)
            and projection_matches(r.get('summary', {}), not iterative)
            and step_matches(r.get('summary', {}), step)
            for r in runs.values()))
    return checks, runs, checkpoint


def phase(function):
    """Missing or malformed evidence fails its phase; it never raises past the verdict."""
    try:
        checks = function()
        return dict(checks=checks, passed=bool(checks) and all(v is True for v in checks.values()))
    except (OSError, KeyError, ValueError, TypeError) as error:
        return dict(checks={}, passed=False, error=f'{type(error).__name__}: {error}')


def verdict(snapshot, preflight, directories, riemann, limiter, iterative=False, step=None):
    limiter_arguments(limiter)
    step_arguments(step)
    if (iterative, step) not in BOUNDED_STUDIES:
        raise ValueError('No registered short-stage study for this configuration')
    snapshot_sha256 = sha(snapshot)
    receipt = load(preflight/'preflight.json')
    if receipt['snapshot_sha256'] != snapshot_sha256:
        raise ValueError('Preflight receipt belongs to a different snapshot')
    binary_sha256 = receipt['binary_sha256']
    cases = registered(riemann)
    loaded = {}

    def plan(name):
        if name not in loaded:
            loaded[name] = plan_checks(directories[name], snapshot_sha256, binary_sha256, cases[name], riemann, limiter,
                                       iterative, step)
        return loaded[name]

    def merged(checks, registered_checks):
        if set(checks) & set(registered_checks):
            raise ValueError('Plan and registered check names collide')
        return dict(checks, **registered_checks)

    def medium():
        checks, runs, checkpoint = plan('medium')
        summary = dict(checkpoint['summaries']['wave'], runs=runs)
        return merged(checks, bounded.verdict('waves_medium', summary, 1.))

    def mean():
        checks, runs, checkpoint = plan('mean')
        return merged(checks, campaign.mean_checks(dict(checkpoint['summaries']['wave'], runs=runs), riemann))

    def calibration_wave():
        # The historical N128 calibration sized a shared worker pool, which the per-case policy
        # removed. Its accuracy/state/boost checks are applied to the same two registered cases.
        _, runs, checkpoint = plan('waves')
        names = [n for n, c in cases['waves'].items() if c['case'] == 'alfven' and c['n'] == 128 and c['jitter'] == .15
                 and c['parallel'] == 0. and c['motion_family'] == 'fixed' and c['dt'] is None]
        chosen = {n: runs[n] for n in names}
        pairs = [p for p in checkpoint['summaries']['wave']['pairs'] if set(p['names']) == set(names)]
        checks = campaign.wave_checks(dict(runs=chosen, pairs=pairs), 2, 1, riemann=riemann)
        checks['amplitude_error'] = all(r['errors']['final']['B']['L1']/.1 <= .02 for r in chosen.values())
        return checks

    def calibration_vortex():
        _, runs, _ = plan('physics')
        names = [n for n, c in cases['physics'].items() if c['case'] == 'orszag-tang' and c['n'] == 128
                 and c['jitter'] == .15 and not any(c['boost'])]
        chosen = {n: runs[n] for n in names}
        return dict(complete=len(chosen) == 1 and all(r['status'] == 'completed' for r in chosen.values()),
                    diagnostics=bool(chosen) and all(r.get('state_and_diagnostic_gates') is True for r in chosen.values()),
                    execution_configuration=bool(chosen) and all(campaign.candidate_matches(r, riemann)
                                                                 for r in chosen.values()))

    def physics():
        checks, runs, checkpoint = plan('physics')
        summary = checkpoint['summaries']['physics']
        return merged(checks, dict(physics_gates=summary['all_registered_physics_gates'] is True,
                                   complete_ladder=summary['completed_evolutions'] == 30))

    def waves():
        checks, runs, checkpoint = plan('waves')
        return merged(checks, campaign.wave_checks(dict(checkpoint['summaries']['wave'], runs=runs),
                                                   112, 48, full=True, riemann=riemann))

    functions = dict(bounded_short=lambda: bounded_checks(directories['bounded'], snapshot_sha256, riemann, limiter,
                                                          iterative, step),
                     bounded_medium=medium, mean=mean, calibration_wave=calibration_wave,
                     calibration_vortex=calibration_vortex, physics=physics, waves=waves)
    phases = {name: phase(functions[name]) for name in PHASES}
    return dict(
        scope='Registered phase checks of one explicit configuration from independent REANA workflows. '
              'Evidence for review only; independent review and the owner decide milestone acceptance.',
        configuration=dict(profile=PROFILE, accelerated_projection=not iterative, projection_screening=1.,
                           riemann_solver=riemann, potential_limiter=limiter, trial_step_fraction=step),
        snapshot_sha256=snapshot_sha256, binary_sha256=binary_sha256, phases=phases,
        all_registered_phase_checks_passed=all(p['passed'] for p in phases.values()),
        full_m1_accepted=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True, help='snapshot.json of the frozen source')
    parser.add_argument('--preflight', type=Path, required=True, help='downloaded m1-fanout-preflight outputs')
    parser.add_argument('--bounded', type=Path, required=True, help='downloaded outputs of the short-stage study')
    for name in ('medium', 'mean', 'physics', 'waves'):
        parser.add_argument('--'+name, type=Path, required=True, help=f'fan-out plan directory of the {name} phase')
    parser.add_argument('--riemann', choices=campaign.RIEMANN_SOLVERS, default='hlld-pressure')
    parser.add_argument('--potential-limiter', default='smooth-extrema')
    parser.add_argument('--iterative-projection', action='store_true',
                        help='the configuration solves the projection without the cached factorization')
    parser.add_argument('--trial-step-fraction', type=float, help='the configuration\'s first-trial fraction')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output file')
    directories = {name: getattr(args, name).resolve() for name in ('bounded', 'medium', 'mean', 'physics', 'waves')}
    result = verdict(args.snapshot.resolve(), args.preflight.resolve(), directories, args.riemann, args.potential_limiter,
                     args.iterative_projection, args.trial_step_fraction)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    for name, item in result['phases'].items():
        failed = [k for k, v in item['checks'].items() if v is not True]
        print(f'{name:18} {"pass" if item["passed"] else "FAIL"} {item.get("error", "")} {failed or ""}')
    print('All registered phase checks passed:', result['all_registered_phase_checks_passed'],
          '| Full M1 acceptance: not evaluated.')
    return 0 if result['all_registered_phase_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
