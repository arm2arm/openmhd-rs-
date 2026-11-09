#!/usr/bin/env python3
"""Explain archived shock errors using existing measurements; no solver runs."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from check_shock_curl_audit import fit


def read(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('audit', type=Path)
    parser.add_argument('trace', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    paths = [args.audit/'cells/n256_j0.15_brio_worst.csv',
             args.audit/'cells/n256_j0.15_brio_cells.csv', args.trace]
    rows, cells, trace = map(read, paths)
    cell_id = int(rows[0]['cell_id'])
    cell = next(r for r in cells if int(r['id']) == cell_id)
    x, y = float(cell['x']), float(cell['y'])
    if not 1 < x < 2:
        raise ValueError('This explanation requires the archived right-branch stencil.')
    a, gx, gy = map(float, fit(rows))
    total_weight = sum(float(r['area']) for r in rows)
    mean = [sum(float(r['area'])*float(r[k]) for r in rows)/total_weight
            for k in ('dx', 'dy', 'az')]
    sxx = sxy = syy = tx = ty = 0.
    contributions = []
    for r in rows:
        xx, yy, aa = [float(r[k])-mean[i] for i, k in enumerate(('dx', 'dy', 'az'))]
        w = float(r['area'])/total_weight
        sxx += w*xx*xx
        sxy += w*xx*yy
        syy += w*yy*yy
        tx += w*xx*aa
        ty += w*yy*aa
        residual = float(r['az'])-(x-2)-float(r['dx'])
        contributions.append(dict(neighbour=int(r['neighbour']), residual=residual,
                                  transverse_contribution=float(r['weight_y'])*residual))
    determinant = sxx*syy-sxy*sxy
    covariance_gy = (sxx*ty-sxy*tx)/determinant
    trace_condition = (sxx+syy)**2/determinant
    eigen_condition = (trace_condition-2+math.sqrt(trace_condition*(trace_condition-4)))/2
    gx_restricted = tx/sxx
    a_restricted = mean[2]-gx_restricted*mean[0]

    def mse(intercept, dx, dy):
        return sum(float(r['area'])*(float(r['az'])-intercept-dx*float(r['dx'])
                                    -dy*float(r['dy']))**2 for r in rows)/total_weight

    free_mse, restricted_mse = mse(a, gx, gy), mse(a_restricted, gx_restricted, 0.)
    explained = sum(r['transverse_contribution'] for r in contributions)
    if max(abs(explained-gy), abs(covariance_gy-gy), abs(gy-float(cell['bx_error']))) > 1e-12:
        raise ValueError('Independent decompositions disagree with the archived derivative.')
    # Reproduce the implementation's sample-baseline subtraction separately.
    baseline = contributions[0]['residual']
    stable_sum = sum(float(r['weight_y'])*(c['residual']-baseline)
                     for r, c in zip(rows, contributions))
    if abs(stable_sum-gy) > 1e-12:
        raise ValueError('Sample-baseline subtraction disagrees with the fit.')
    failing = [r for r in trace if int(r['id']) == 253]
    if not failing or float(failing[0]['time']) != 0.:
        raise ValueError('Expected the complete archived cell-253 trace.')
    for r in failing:
        closure = float(r['total_rate'])-float(r['kinetic_rate'])-float(r['magnetic_rate'])
        if abs(closure-float(r['pressure_rate'])) > 1e-10:
            raise ValueError('Gamma=2 pressure-rate identity failed.')
    fig, axes = plt.subplots(1, 3, figsize=(13.6, 4.6), layout='constrained')
    residuals = [r['residual'] for r in contributions]
    points = axes[0].scatter([100*float(r['dx']) for r in rows],
                            [100*float(r['dy']) for r in rows], c=residuals,
                            s=[500*float(r['area'])/total_weight+40 for r in rows],
                            cmap='YlOrRd', vmin=0, vmax=max(residuals), edgecolor='#333')
    for r in rows:
        axes[0].annotate(r['neighbour'], (100*float(r['dx']), 100*float(r['dy'])),
                         xytext=(5, 6), textcoords='offset points', fontsize=9)
    axes[0].scatter([0], [0], marker='*', s=120, color='#243b53', label=f'Cell {cell_id}')
    axes[0].axvline(100*(1-x), color='#777', ls='--', label='Az slope change')
    axes[0].set(title='A. Five samples across a kink', xlabel='100 × centroid offset in x',
                ylabel='100 × centroid offset in y', xlim=(-2.1, 1.6), ylim=(-2.1, 2.2))
    axes[0].set_aspect('equal')
    axes[0].legend(loc='upper right', fontsize=8)
    fig.colorbar(points, ax=axes[0], shrink=.7, label='Residual from local x-linear field')
    terms = [r['transverse_contribution'] for r in contributions]
    axes[1].bar([str(r['neighbour']) for r in contributions], terms,
                color=['#bf4940' if v < 0 else '#357ca5' for v in terms])
    axes[1].axhline(0, color='#555', lw=.8)
    axes[1].set(title='B. Kink leaks into transverse slope', xlabel='Neighbour cell ID',
                ylabel='Contribution to spurious Bx', ylim=(-.35, .27))
    axes[1].text(.04, .94, f'Sum = {explained:.6f}\nBx = {0.75+gy:.6f}; expected 0.75',
                 va='top', transform=axes[1].transAxes, fontsize=10)
    axes[2].plot([float(r['time']) for r in failing], [float(r['thermal']) for r in failing],
                 color='#bf4940', lw=2)
    axes[2].axhline(0, color='#555', lw=.8)
    axes[2].set(title='C. Another cell loses pressure', xlabel='Simulation time',
                ylabel='Thermal energy density = pressure (γ = 2)', ylim=(-.005, .115))
    axes[2].text(.04, .94, 'Cell 253: initial B is correct\np falls from 0.1 to 6.2 × 10⁻⁸',
                 va='top', transform=axes[2].transAxes, fontsize=10)
    axes[2].ticklabel_format(axis='x', style='sci', scilimits=(0, 0))
    for ax in axes[1:]:
        ax.grid(axis='y', alpha=.2)
        ax.set_axisbelow(True)
    fig.suptitle('Jittered Brio–Wu, 256 × 4: reconstruction error and energy-coupling failure',
                 fontsize=13)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=180)
    plt.close(fig)
    report = dict(scope='Explanation of archived measurements; no new evolution or acceptance gate.',
                  initial_cell=cell_id, centroid=[x, y], fit=[a, gx, gy],
                  covariance=[[sxx, sxy], [sxy, syy]], covariance_rhs=[tx, ty],
                  spectral_condition=eigen_condition, trace_squared_over_det=trace_condition,
                  free_fit_rms=math.sqrt(free_mse), zero_gy_fit_rms=math.sqrt(restricted_mse),
                  fitting_objective_reduction=1-free_mse/restricted_mse,
                  contributions=contributions, transverse_sum=explained,
                  sample_baseline_sum=stable_sum, failing_cell_first=failing[0],
                  failing_cell_last=failing[-1],
                  input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in [*paths, Path(__file__),
                                          Path(__file__).with_name('check_shock_curl_audit.py')]})
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n')
    print(f'Cell {cell_id}: gy={gy:.9f}, matrix condition={eigen_condition:.6f}, '
          f'fit-objective reduction={1-free_mse/restricted_mse:.2%}; all identity checks pass.')


if __name__ == '__main__':
    main()
