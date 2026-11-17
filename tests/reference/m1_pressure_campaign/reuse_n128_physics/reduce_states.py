"""Independent N128 final-state reductions of exported cells; no evolution."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw', type=Path)
    args = parser.parse_args()
    archive = Path(__file__).resolve().parent
    run_bytes = gzip.decompress((archive/'runs.json.gz').read_bytes())
    runs = json.loads(run_bytes)
    measured, inputs = {}, {}
    for name, run in runs.items():
        config = run['config']
        if config['case'] != 'orszag-tang' or config['n'] != 128:
            continue
        assert run['status'] == 'completed' and config['ny'] == 128 and config['time'] == .5
        data = []
        for filename, time in [('initial.csv', 0.), ('final.csv', .5)]:
            path = args.raw/name/filename
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            assert digest == run['sha256'][filename]
            inputs[name+'/'+filename] = digest
            cells = np.genfromtxt(path, names=True, delimiter=',')
            assert np.array_equal(cells['id'], np.arange(128**2)) and (cells['time'] == time).all()
            assert all(np.isfinite(cells[field]).all() for field in cells.dtype.names)
            assert all((cells[field] > 0).all() for field in ('volume', 'rho', 'p'))
            assert abs(math.fsum(cells['volume'])-1.) < 1e-10
            data.append(cells)
        initial, final = data

        def totals(cells):
            return np.array([math.fsum(cells['volume']*cells['rho']),
                             *[math.fsum(cells['volume']*cells['rho']*cells[field]) for field in ('vx', 'vy', 'vz')],
                             math.fsum(cells['volume']*cells['energy'])])

        def dot_totals(cells):
            return np.array([np.dot(cells['volume'], cells['rho']),
                             *[np.dot(cells['volume'], cells['rho']*cells[field]) for field in ('vx', 'vy', 'vz')],
                             np.dot(cells['volume'], cells['energy'])])

        def average(cells, values):
            return math.fsum(cells['volume']*values)/math.fsum(cells['volume'])

        summary = run['summary']
        budget = (totals(final)-totals(initial))/summary['initial']['budget_scales']
        dot_budget = (dot_totals(final)-dot_totals(initial))/summary['initial']['budget_scales']
        drift = np.array([average(final, final[field])-average(initial, initial[field]) for field in ('bx', 'by', 'bz')])
        bscale = 1/math.sqrt(4*math.pi)
        magnitude = np.sqrt(sum(final[field]**2 for field in ('bx', 'by', 'bz')))
        normalized = np.sqrt(final['volume']/math.pi)*final['div_b_limited']/(magnitude+1e-12*bscale)
        rms = math.sqrt(average(final, normalized**2))
        mean = float(np.linalg.norm(drift))/bscale
        assert max(abs(budget-np.array(summary['final']['normalized_budget']))) < 2e-13
        assert max(abs(drift-np.array(summary['final']['mean_B_drift']))) < 2e-13
        assert abs(rms-summary['final']['div_B_limited']['dimensionless']['rms']) < 2e-13
        checks = dict(positive=True, budget=float(max(abs(budget))) <= 1e-10,
                      normalized_mean_B_drift=mean <= .001, normalized_limited_divergence=rms <= .1)
        assert all(checks.values())
        measured[name] = dict(final_minimum_density=float(min(final['rho'])),
                              final_minimum_pressure=float(min(final['p'])),
                              final_normalized_budget=budget.tolist(), final_mean_B_drift=drift.tolist(),
                              alternative_dot_normalized_budget=dot_budget.tolist(),
                              compensated_budget_report_difference=float(max(abs(budget-np.array(summary['final']['normalized_budget'])))),
                              dot_budget_report_difference=float(max(abs(dot_budget-np.array(summary['final']['normalized_budget'])))),
                              final_normalized_mean_B_drift=mean, final_normalized_limited_divergence_RMS=rms,
                              stored_history_maxima=run['diagnostic_values'], final_checks=checks)
    assert len(measured) == 4
    report = dict(scope='Independent final-cell compensated-sum budgets, mean-field drift and normalized divergence reductions. The alternative NumPy dot-sum budget is retained to expose reduction-order differences. The limited-face divergence values and history maxima are exported solver data, not an independently rebuilt operator or evolution. No N256 or full M1 verdict.',
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  run_map_sha256=hashlib.sha256(run_bytes).hexdigest(), input_sha256=inputs,
                  numpy=np.__version__, measured=measured)
    (archive/'independent_states.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Independently verified all four N128 final-state reductions.')


if __name__ == '__main__':
    main()
