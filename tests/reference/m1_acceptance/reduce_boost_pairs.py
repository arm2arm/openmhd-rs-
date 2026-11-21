"""Reduce existing medium/physics boost snapshots independently; no evolution."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

import reduce_waves


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def physics_pair(directory, pair, runs):
    names = pair['names']
    a, b = (runs[name] for name in names)
    config = a['config']
    assert config['boost'] == [0., 0., 0.] and b['config']['boost'] == [2., -1., 0.]
    assert {k: v for k, v in config.items() if k not in ('name', 'boost')} == {
        k: v for k, v in b['config'].items() if k not in ('name', 'boost')}
    arrays = []
    budgets = []
    for name, run in zip(names, (a, b)):
        path = directory/'raw'/name/'final.csv'
        assert sha(path) == run['sha256']['final.csv']
        assert run['status'] == 'completed' and run['returncode'] == 0
        summary = run['summary']
        assert config['profile'] == summary['profile'] == 'bulk-frame-heun-quadratic-v1'
        assert summary['completed'] and summary['projection_screening'] == 1.
        assert summary['potential_limiter'] == 'smooth-extrema-v1'
        assert config['riemann_solver'] == 'hlld-pressure'
        assert summary['riemann_solver'] == 'hlld-pressure-blend-v1'
        data = np.genfromtxt(path, names=True, delimiter=',')
        assert len(data) == config['n']*config['ny']
        assert np.array_equal(data['id'], np.arange(len(data)))
        assert all(np.isfinite(data[f]).all() for f in data.dtype.names)
        assert (data['time'] == config['time']).all()
        assert all((data[f] > 0).all() for f in ('volume', 'rho', 'p'))
        history = run['history']
        assert history[0]['time'] == 0 and history[-1]['time'] == config['time']
        assert all(x['time'] < y['time'] for x, y in zip(history, history[1:]))
        assert all(row['diagnostics']['rho_min'] > 0 and row['diagnostics']['p_min'] > 0
                   for row in history)
        budgets.append(max(abs(v) for row in history for v in row['diagnostics']['normalized_budget']))
        arrays.append(data)
    x, y = arrays
    volume = math.fsum(x['volume'])
    lengths = (2., .125) if config['case'] == 'brio-wu' else (1., 1.)
    assert abs(volume-math.prod(lengths)) < 1e-10
    # Rebuild the registered physical scales. Speed and total-energy scales
    # are recorded initial-budget metadata, not fitted from the boost errors.
    if config['case'] == 'brio-wu':
        scales = dict(rho=1., p=1., vx=1., bx=1., by=1., bz=1.)
    else:
        scales = dict(rho=25/(36*math.pi), p=5/(12*math.pi),
                      **{f: 1/math.sqrt(4*math.pi) for f in ('bx', 'by', 'bz')})
    initial = a['summary']['initial']['budget_scales']
    speed = initial[1]/initial[0]
    scales.update(vx=scales.get('vx', speed), vy=speed, vz=speed, energy=initial[4]/volume)
    assert scales == pair['scales']
    boost = b['config']['boost']
    expected = {f: x[f].copy() for f in scales}
    for f, v in zip(('vx', 'vy', 'vz'), boost):
        expected[f] += v
    expected['energy'] += x['rho']*(sum(x[f]*v for f, v in zip(('vx', 'vy', 'vz'), boost))
                                    + .5*sum(v*v for v in boost))
    errors = {f: math.fsum(x['volume']*abs(y[f]-v)/scales[f])/volume for f, v in expected.items()}
    disagreement = max(abs(errors[f]-pair['relative_L1'][f]) for f in errors)
    assert disagreement < 1e-13
    position = max(float(max(abs((y[f]-x[f]-v*config['time']+length/2) % length-length/2)))
                   for f, v, length in zip(('x', 'y'), boost, lengths))
    relative_volume = float(max(abs(y['volume']/x['volume']-1.)))
    passed = (max(errors.values()) <= 1e-8 and position <= 1e-9
              and relative_volume <= 1e-9 and max(budgets) <= 1e-10)
    assert passed == pair['passed']
    return dict(names=names, relative_L1=errors, scales=scales, position_max=position,
                volume_relative_max=relative_volume, maximum_recorded_budget=max(budgets),
                maximum_production_disagreement=disagreement, passed=passed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['medium', 'physics'])
    parser.add_argument('directory', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output')
    directory = args.directory
    runs = json.loads((directory/'runs.json').read_text())
    checkpoint = json.loads((directory/'checkpoint.json').read_text())
    if args.phase == 'medium':
        pairs = checkpoint['summaries']['wave']['pairs']
        assert len(runs) == 48 and len(pairs) == 24
        states = {name: reduce_waves.state_check(run) for name, run in runs.items()}
        rows = [reduce_waves.boost_pair(directory/'raw', row['names'], runs) for row in pairs]
        for row, original in zip(rows, pairs):
            assert row['passed']
            if row['case'] == 'loop':
                row['maximum_production_disagreement'] = abs(
                    row['relative_L1']['loop_amplitude']['B']-original['B_relative_L1'])
            else:
                row['maximum_production_disagreement'] = max(
                    abs(v-original['relative_L1'][convention][field])
                    for convention, values in row['relative_L1'].items() for field, v in values.items())
            assert row['maximum_production_disagreement'] < 1e-13
    else:
        pairs = checkpoint['summaries']['physics']['boost_pairs']
        assert len(runs) == 30 and len(pairs) == 15
        states = None
        rows = [physics_pair(directory, row, runs) for row in pairs]
    used = [name for row in rows for name in row['names']]
    assert len(set(used)) == len(used) == len(runs)
    report = dict(scope='Independent transformed-snapshot boost norms; checks recorded state/budget histories, not independent evolution or general invariance.',
                  phase=args.phase, analysis_source_sha256=sha(Path(__file__)),
                  wave_reducer_sha256=sha(Path(reduce_waves.__file__)), numpy=np.__version__,
                  run_map_sha256=sha(directory/'runs.json'),
                  checkpoint_sha256=sha(directory/'checkpoint.json'),
                  snapshot_sha256={name: sha(directory/'raw'/name/'final.csv') for name in used},
                  states=states, pairs=rows, all_passed=all(row['passed'] for row in rows),
                  full_m1_accepted=False)
    args.output.write_text(json.dumps(report, indent=1, allow_nan=False)+'\n')
    print(args.phase, 'pairs', len(rows), 'all passed', report['all_passed'])
    return 0 if report['all_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
