"""Independently reduce existing 24-case candidate mean-field snapshots; no evolution."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output file')
    directory = args.directory
    runs = json.loads((directory/'runs.json').read_text())
    summary = json.loads((directory/'checkpoint.json').read_text())['summaries']['wave']
    assert len(runs) == 24 and len(summary['pairs']) == 12
    records = []
    for pair in summary['pairs']:
        names = pair['names']
        arrays = []
        inputs = {}
        for name in names:
            run = runs[name]
            config = run['config']
            assert run['status'] == 'completed' and config['case'] == 'smooth'
            assert config['profile'] == 'bulk-frame-heun-quadratic-v1'
            assert run['summary']['projection_screening'] == 1.
            path = directory/'raw'/name/'final.csv'
            inputs[name] = sha(path)
            assert inputs[name] == run['sha256']['final.csv']
            data = np.genfromtxt(path, names=True, delimiter=',')
            assert np.array_equal(data['id'], np.arange(config['n']**2))
            assert all(np.isfinite(data[field]).all() for field in data.dtype.names)
            assert (data['time'] == .02).all()
            assert all((data[field] > 0).all() for field in ('volume', 'rho', 'p'))
            assert abs(math.fsum(data['volume'])-1.) < 1e-10
            arrays.append(data)
        x, y = arrays
        assert len(x) == len(y)
        assert runs[names[0]]['config']['boost'] == [0., 0., 0.]
        boost = np.array(runs[names[1]]['config']['boost'])
        assert list(boost) == [2., -1., 0.]
        values = {field: y[field].copy() for field in
                  ('rho', 'p', 'vx', 'vy', 'vz', 'bx', 'by', 'bz', 'energy')}
        for field, speed in zip(('vx', 'vy', 'vz'), boost):
            values[field] -= speed
        values['energy'] = (y['energy']-y['rho']*sum(y[field]*speed for field, speed in
                            zip(('vx', 'vy', 'vz'), boost))+.5*y['rho']*sum(boost**2))
        errors = {field: float(max(abs(value-x[field]))) for field, value in values.items()}
        disagreement = max(abs(errors[field]-pair['errors'][field]['max']) for field in errors)
        assert disagreement < 1e-13
        position = max(float(max(abs((y[field]-x[field]-speed*.02+.5) % 1-.5)))
                       for field, speed in zip(('x', 'y'), boost))
        volume = float(max(abs(y['volume']/x['volume']-1.)))
        roots_match = (runs[names[0]]['summary']['auxiliary_roots'] ==
                       runs[names[1]]['summary']['auxiliary_roots'])
        budgets = [row['diagnostics'] for name in names for row in runs[name]['history']]
        budget = max(abs(value) for row in budgets for value in row['normalized_budget'])
        positive = all(row['rho_min'] > 0 and row['p_min'] > 0 for row in budgets)
        passed = (max(errors.values()) <= 1e-9 and position <= 1e-11 and volume <= 1e-11
                  and roots_match and positive and budget <= 1e-10)
        records.append(dict(names=names, input_sha256=inputs, maximum_errors=errors,
                            position_max=position, volume_relative_max=volume,
                            matching_auxiliary_roots=roots_match, maximum_recorded_budget=budget,
                            maximum_production_disagreement=disagreement, passed=passed))
    result = dict(scope='Independent transformed-snapshot mean-field boost reduction; recorded histories checked, no new evolution, no general invariance or M1 acceptance.',
                  run_map_sha256=sha(directory/'runs.json'), analysis_source_sha256=sha(Path(__file__)),
                  numpy=np.__version__, pairs=records, all_passed=all(row['passed'] for row in records),
                  full_m1_accepted=False)
    args.output.write_text(json.dumps(result, indent=1, allow_nan=False)+'\n')
    print('Mean-field pairs:', len(records), 'all passed:', result['all_passed'])
    return 0 if result['all_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
