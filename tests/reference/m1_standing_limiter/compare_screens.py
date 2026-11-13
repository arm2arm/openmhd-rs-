#!/usr/bin/env python3
"""Read-only comparison of the smooth-extrema candidate screens with the baseline.

Inputs are fan-out plan directories written by scripts/reana_cases.py
(plan.json, runs.json, checkpoint.json, raw/<case>/final.csv), the retained
104-case wave run map of the stopped pressure campaign and its local
shock/vortex run map. Pair and gate statuses are the frozen production
evaluation stored in each plan's checkpoint.json; everything else is copied
from run records or recomputed from hash-checked snapshots. No evolution is
launched. A passing screen is not acceptance of the registered matrix.
"""
import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
WAVE_BASELINE = HERE.parent/'m1_pressure_campaign/standing_diagnosis/runs.json.gz'
PROFILE = 'bulk-frame-heun-quadratic-v1'
LOOP_SCALE = .001/math.sqrt(4*math.pi)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_plan(directory, limiter='smooth-extrema'):
    plan = json.loads((directory/'plan.json').read_text())
    runs = json.loads((directory/'runs.json').read_text())
    checkpoint = json.loads((directory/'checkpoint.json').read_text())
    names = [e['specification']['config']['name'] for e in plan['cases']]
    assert all(e['specification']['options'].get('potential_limiter') == limiter for e in plan['cases'])
    assert set(runs) == set(names) and checkpoint['all_terminal'] and not checkpoint['observation_errors']
    assert checkpoint['completed_cases'] == checkpoint['expected_cases'] == len(names)
    for name, record in runs.items():
        assert record['status'] == 'completed' and record['summary']['potential_limiter'] == 'smooth-extrema-v1', name
        assert sha(directory/'raw'/name/'final.csv') == record['sha256']['final.csv'], name
    identity = dict(plan_sha256=sha(directory/'plan.json'), snapshot_sha256=plan['snapshot_sha256'],
                    cases=len(names), workflow_prefix=plan['cases'][0]['workflow'].rsplit('-', 1)[0],
                    verified_required_failure=checkpoint['verified_required_failure'],
                    execution_failures=checkpoint['execution_failures'])
    return runs, checkpoint, identity


def cells(path):
    with path.open() as stream:
        return [{k: float(v) for k, v in row.items()} for row in csv.DictReader(stream)]


def loop_extrema(path):
    """Potential range and peak planar field of one loop snapshot, in units of the initial field."""
    rows = cells(path)
    return dict(az_min=min(q['az'] for q in rows)/LOOP_SCALE, az_max=max(q['az'] for q in rows)/LOOP_SCALE,
                B_max=max(math.hypot(q['bx'], q['by']) for q in rows)/LOOP_SCALE,
                exact_az_range=[0., .3], exact_B=1.)


def waves(directory, baseline, baseline_raw):
    runs, checkpoint, identity = load_plan(directory)
    pairs = checkpoint['summaries']['wave']['pairs']
    result = dict(identity, pairs=[], alfven=[], loop=[])
    for pair in pairs:
        row = dict(names=pair['names'], status=pair['status'])
        if pair['case'] == 'loop':
            row['B_relative_L1'] = pair['B_relative_L1']
        else:
            row['max_relative_L1'] = max(max(v.values()) for v in pair['relative_L1'].values())
        result['pairs'].append(row)
    result['all_pairs_pass'] = len(pairs) == 24 and all(p['status'].startswith('pass') for p in pairs)
    for name in sorted(n for n in runs if n.endswith('_base')):
        c, b = runs[name], baseline[name]
        assert b['status'] == 'completed' and b['config'] == c['config'], name
        row = dict(name=name, steps=[c['summary']['steps'], b['summary']['steps']],
                   limiter_active_cells_initial_final=c['summary']['potential_limiter_active_cells'])
        if c['config']['case'] == 'alfven':
            mine, theirs = (r['errors']['final']['B']['L1'] for r in (c, b))
            row.update(B_L1=mine, baseline_B_L1=theirs, ratio=mine/theirs)
            result['alfven'].append(row)
        else:
            for key in ('passive_B', 'passive_A'):
                mine, theirs = (r['errors']['final'][key]['L1'] for r in (c, b))
                row[key+'_L1'] = dict(candidate=mine, baseline=theirs, ratio=mine/theirs)
            row['magnetic_energy_retained'] = {
                label: r['summary']['final']['magnetic_energy']/r['summary']['initial']['magnetic_energy']
                for label, r in (('candidate', c), ('baseline', b))}
            if c['config']['motion_family'] == 'fixed' and baseline_raw is not None:
                path = baseline_raw/name/'final.csv'
                assert sha(path) == b['sha256']['final.csv'], name
                row['extrema'] = dict(candidate=loop_extrema(directory/'raw'/name/'final.csv'),
                                      baseline=loop_extrema(path))
            result['loop'].append(row)
    return result


def mean(directory):
    runs, checkpoint, identity = load_plan(directory)
    pairs = checkpoint['summaries']['wave']['pairs']
    fields = ('rho', 'p', 'energy', 'B', 'v')
    return dict(identity, pairs=len(pairs), all_pairs_pass=len(pairs) == 12 and all(p['status'] == 'pass' for p in pairs),
                max_boost_error=max(p['errors'][f]['max'] for p in pairs for f in fields if f in p['errors']),
                boost_error_limit=1e-9,
                limiter_active_cells_initial_final=sorted({tuple(r['summary']['potential_limiter_active_cells'])
                                                           for r in runs.values()}))


def physics(directory, baseline, packet):
    runs, checkpoint, identity = load_plan(directory)
    summary = checkpoint['summaries']['physics']
    result = dict(identity, runs=[], boost_pairs=[dict(names=p['names'], status=p['status'],
                                                       max_relative_L1=max(p['relative_L1'].values()))
                                                  for p in summary['boost_pairs']],
                  production_profile_gate='unexecuted: the screen omits the four N256 vortices, so the '
                                          'registered 30-case configuration is not evaluated')
    result['all_boost_pairs_pass'] = all(p['status'] == 'pass' for p in summary['boost_pairs'])
    for name in sorted(runs):
        c, b = runs[name], baseline[name]
        assert b['status'] == 'completed' and b['config'] == c['config'], name
        minimum = lambda record, key: min(h['diagnostics'][key] for h in record['history'])
        result['runs'].append(dict(
            name=name, state_and_diagnostic_gates=c['state_and_diagnostic_gates'],
            positive_and_conservative=c['positive_and_conservative'],
            limiter_active_cells_initial_final=c['summary']['potential_limiter_active_cells'],
            steps=[c['summary']['steps'], b['summary']['steps']],
            reference_L1={f: dict(candidate=e['L1'], baseline=b['reference_errors'][f]['L1'],
                                  ratio=e['L1']/b['reference_errors'][f]['L1'])
                          for f, e in c['reference_errors'].items()},
            diagnostics={k: dict(candidate=v, baseline=b['diagnostic_values'][k])
                         for k, v in c['diagnostic_values'].items() if isinstance(v, (int, float))},
            p_min=[minimum(c, 'p_min'), minimum(b, 'p_min')], rho_min=[minimum(c, 'rho_min'), minimum(b, 'rho_min')]))
    result['all_state_and_diagnostic_gates'] = all(r['state_and_diagnostic_gates'] and r['positive_and_conservative']
                                                   for r in result['runs'])
    ratios = [v['ratio'] for r in result['runs'] for v in r['reference_L1'].values()]
    result['reference_L1_ratio_range'] = [min(ratios), max(ratios)]
    # Informational only: the registered finest-grid Brio limits applied to the complete Brio ladders.
    limits = packet['cases']['brio-wu']['gate']['finest_scaled_L1_max']
    result['brio_finest_limits_informational'] = {
        name: {f: dict(L1=runs[name]['reference_errors'][f]['L1'], limit=limit,
                       below_limit=runs[name]['reference_errors'][f]['L1'] <= limit,
                       below_coarsest=runs[name]['reference_errors'][f]['L1']
                       < runs[name.replace('n1024', 'n256')]['reference_errors'][f]['L1'])
               for f, limit in limits.items()}
        for name in ('brio-wu_n1024_j0.0_base', 'brio-wu_n1024_j0.15c_base')}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--waves', type=Path, required=True)
    parser.add_argument('--mean', type=Path, required=True)
    parser.add_argument('--physics', type=Path, required=True)
    parser.add_argument('--baseline-physics', type=Path, required=True, help='runs.json of the stopped campaign physics phase')
    parser.add_argument('--baseline-raw', type=Path, help='waves directory of the stopped campaign, for loop extrema')
    parser.add_argument('--packet', type=Path, default=HERE.parents[2]/'benchmarks/m0/packet.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    wave_baseline = json.loads(gzip.decompress(WAVE_BASELINE.read_bytes()))
    physics_baseline = json.loads(args.baseline_physics.read_text())
    result = dict(
        scope='Bounded screens of one opt-in configuration; not the registered matrix and not acceptance.',
        configuration=f'{PROFILE} --accelerated-projection --projection-screening 1 --riemann hlld-pressure '
                      '--potential-limiter smooth-extrema',
        baseline='openmhd-m1-pressure-reuse-20261110.1 (same configuration, default A-transport limiter)',
        script_sha256=sha(Path(__file__)), baseline_wave_run_map_sha256=sha(WAVE_BASELINE),
        baseline_physics_run_map_sha256=sha(args.baseline_physics), packet_sha256=sha(args.packet),
        waves_medium=waves(args.waves, wave_baseline, args.baseline_raw),
        mean_field=mean(args.mean),
        shock_vortex_screen=physics(args.physics, physics_baseline, json.loads(args.packet.read_text())),
        full_m1_accepted=False)
    args.output.write_text(json.dumps(result, indent=1, allow_nan=False)+'\n')
    w, m, p = result['waves_medium'], result['mean_field'], result['shock_vortex_screen']
    print('waves-medium pairs pass:', w['all_pairs_pass'], '| mean pairs pass:', m['all_pairs_pass'],
          'max %.3e' % m['max_boost_error'], '| physics gates:', p['all_state_and_diagnostic_gates'],
          'boost:', p['all_boost_pairs_pass'], 'reference ratio range %.4f-%.4f' % tuple(p['reference_L1_ratio_range']))
    for row in w['loop']:
        if 'extrema' in row:
            e = row['extrema']
            print(row['name'].replace(PROFILE+'_', ''), 'passive_B ratio %.4f' % row['passive_B_L1']['ratio'],
                  'passive_A ratio %.4f' % row['passive_A_L1']['ratio'],
                  'az_min %.5f (base %.5f)' % (e['candidate']['az_min'], e['baseline']['az_min']),
                  'az_max %.5f (base %.5f)' % (e['candidate']['az_max'], e['baseline']['az_max']))


if __name__ == '__main__':
    main()
