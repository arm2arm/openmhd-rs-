#!/usr/bin/env python3
"""Read-only reduction of the issue #26 limiter-control ladders.

Inputs are fan-out plan directories written by scripts/reana_cases.py
(plan.json, runs.json, raw/<case>/final.csv) and, for the baseline, the
retained 104-case run map of the stopped pressure campaign. No evolution is
launched and no production error routine is imported.
"""
import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN_MAP = HERE.parent/'m1_pressure_campaign/standing_diagnosis/runs.json.gz'
WINDOW = 1/16
PROFILE = 'bulk-frame-heun-quadratic-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def distance(x, centres):
    return min(abs((x-c+.5) % 1-.5) for c in centres)


def measure(path, record, n, jitter, frame):
    """Independent norms and distortion localisation of one standing fixed snapshot."""
    c = record['config']
    assert record['status'] == 'completed' and record['positive_and_conservative']
    assert c['profile'] == PROFILE and c['riemann_solver'] == 'hlld-pressure' and c['case'] == 'alfven'
    assert c['n'] == n and c['jitter'] == jitter and c['target'] == 1. and c['parallel'] == 1.
    assert c['motion_family'] == 'fixed' and record['summary']['projection_screening'] == 1.
    boost = c['boost']
    assert boost == ([2., -1., 0.] if frame == 'boost' else [0., 0., 0.])
    digest = sha(path)
    assert digest == record['sha256']['final.csv'], path
    with path.open() as stream:
        cells = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(stream)]
    assert len(cells) == n*n
    assert all(q['id'] == i and q['time'] == 1. and q['volume'] > 0 and q['rho'] > 0 and q['p'] > 0
               and all(math.isfinite(v) for v in q.values()) for i, q in enumerate(cells))
    assert abs(math.fsum(q['volume'] for q in cells)-1.) < 1e-10
    # Standing wave: analytic phase 2 pi (x - boost_x t) at t=1; integer boost_x leaves 2 pi x.
    assert boost[0] == round(boost[0])
    error = math.fsum(q['volume']*math.sqrt((q['bx']-1.)**2 + (q['by']-.1*math.sin(math.tau*q['x']))**2
                                           + (q['bz']-.1*math.cos(math.tau*q['x']))**2) for q in cells)
    assert abs(error-record['errors']['final']['B']['L1']) < 2e-13, (error, record['errors']['final']['B']['L1'])
    fields = {}
    for field, exact, own_extrema, potential_extrema in (
            ('by', (.1, 0.), (.25, .75), (0., .5)), ('bz', (0., .1), (0., .5), (.25, .75))):
        sine = 2*math.fsum(q['volume']*q[field]*math.sin(math.tau*q['x']) for q in cells)
        cosine = 2*math.fsum(q['volume']*q[field]*math.cos(math.tau*q['x']) for q in cells)
        mean = math.fsum(q['volume']*q[field] for q in cells)
        residual = [q[field]-mean-sine*math.sin(math.tau*q['x'])-cosine*math.cos(math.tau*q['x']) for q in cells]
        total = math.fsum(q['volume']*abs(r) for q, r in zip(cells, residual))
        fields[field] = dict(
            fundamental_error=math.hypot(sine-exact[0], cosine-exact[1]),
            residual_L1_without_mean_and_fundamental=total,
            residual_max=max(map(abs, residual)),
            residual_L1_fraction_within_one_sixteenth={
                key: math.fsum(q['volume']*abs(r) for q, r in zip(cells, residual)
                               if distance(q['x'], centres) <= WINDOW)/total
                for key, centres in (('field_extrema', own_extrema), ('potential_extrema', potential_extrema))})
    summary = record['summary']
    return dict(n=n, B_L1=error, v_L1=record['errors']['final']['v']['L1'], steps=summary['steps'],
                limited=summary['limited'], potential_limiter=summary.get('potential_limiter', 'default'),
                potential_limiter_active_cells=summary.get('potential_limiter_active_cells'),
                final_sha256=digest, fields=fields, seconds=record.get('seconds'))


def orders(rows):
    result = dict(successive_B_L1={}, successive_residual_L1={})
    for a, b in zip(rows, rows[1:]):
        if b['n'] != 2*a['n']:
            continue
        key = f"{a['n']}-{b['n']}"
        result['successive_B_L1'][key] = math.log(a['B_L1']/b['B_L1'])/math.log(2.)
        result['successive_residual_L1'][key] = {
            f: math.log(a['fields'][f]['residual_L1_without_mean_and_fundamental']
                        / b['fields'][f]['residual_L1_without_mean_and_fundamental'])/math.log(2.) for f in ('by', 'bz')}
    finest = [r for r in rows if r['n'] in (64, 128, 256)]
    if len(finest) == 3:
        # Same registered definition: least-squares log-log slope of the finest three B L1 errors.
        x = [math.log(1/r['n']) for r in finest]
        y = [math.log(r['B_L1']) for r in finest]
        xm, ym = sum(x)/3, sum(y)/3
        result['registered_finest_three_B_L1_order'] = sum((a-xm)*(b-ym) for a, b in zip(x, y))/sum((a-xm)**2 for a in x)
        result['finest_relative_B_L1'] = finest[-1]['B_L1']/.1
    else:
        result['registered_finest_three_B_L1_order'] = None
    return result


def ladder(runs, raw, jitter, frame):
    rows = []
    for n in (32, 64, 128, 256):
        name = f'alfven_{PROFILE}_v1.0_j{jitter}_fixed_n{n}_{frame}'
        if name not in runs or runs[name]['status'] != 'completed':
            continue
        rows.append(measure(raw/name/'final.csv', runs[name], n, jitter, frame))
    return dict(jitter=jitter, frame=frame, rows=rows, missing=[n for n in (32, 64, 128, 256)
                                                               if n not in [r['n'] for r in rows]], **orders(rows))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-raw', type=Path, required=True, help='waves directory of the stopped campaign')
    parser.add_argument('--plan', action='append', default=[], metavar='LABEL=DIRECTORY')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    baseline = json.loads(gzip.decompress(RUN_MAP.read_bytes()))
    result = dict(scope='Independent postprocessing; diagnostic controls are not acceptance and change no gate.',
                  script_sha256=sha(Path(__file__)), baseline_run_map_sha256=sha(RUN_MAP),
                  window_half_width=WINDOW, uniform_reference_fraction=4*WINDOW,
                  configurations={'baseline': dict(
                      source='openmhd-m1-pressure-reuse-20261110.1 (stopped campaign, default limiters)',
                      ladders=[ladder(baseline, args.baseline_raw, jitter, 'base') for jitter in (0., .15)])},
                  full_m1_accepted=False)
    for item in args.plan:
        label, directory = item.split('=', 1)
        directory = Path(directory)
        plan = json.loads((directory/'plan.json').read_text())
        runs = json.loads((directory/'runs.json').read_text())
        options = {json.dumps(e['specification']['options'], sort_keys=True) for e in plan['cases']}
        assert len(options) == 1, 'one limiter configuration per plan'
        frames = ['base'] + (['boost'] if any(n.endswith('_boost') for n in runs) else [])
        result['configurations'][label] = dict(
            options=json.loads(next(iter(options))), plan_sha256=sha(directory/'plan.json'),
            snapshot_sha256=plan['snapshot_sha256'], workflows=sorted(e['workflow'] for e in plan['cases']),
            ladders=[ladder(runs, directory/'raw', jitter, frame) for frame in frames for jitter in (0., .15)])
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    for label, configuration in result['configurations'].items():
        for item in configuration['ladders']:
            order = item['registered_finest_three_B_L1_order']
            print(label, 'jitter', item['jitter'], item['frame'],
                  'B L1', ' '.join(f"{r['B_L1']:.4e}" for r in item['rows']),
                  '| successive', ' '.join(f'{v:.3f}' for v in item['successive_B_L1'].values()),
                  '| finest-three', 'n/a' if order is None else f'{order:.4f}',
                  '| active', [r['potential_limiter_active_cells'] for r in item['rows']])


if __name__ == '__main__':
    main()
