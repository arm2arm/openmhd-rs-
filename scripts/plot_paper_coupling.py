#!/usr/bin/env python3
"""Plot preserved pressure histories and cell-253 face contributions."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('faces', type=Path)
    parser.add_argument('geometry', type=Path)
    parser.add_argument('hessian', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), constrained_layout=True)
    for ny, color in [(4, '#bd3434'), (8, '#3578b5'), (16, '#24835a')]:
        data = rows(args.geometry/f'n256_ny{ny}_j0.15_t0.01/history.csv')
        axes[0].plot([float(r['time']) for r in data], [float(r['p_min']) for r in data],
                     color=color, label=f'Paper source, {ny} rows')
        if ny == 4:
            axes[0].plot(float(data[-1]['time']), float(data[-1]['p_min']), 'x', color=color, ms=9)
    history = json.loads((args.hessian/'j0.15_base/history.json').read_text())
    axes[0].plot([r['time'] for r in history], [r['diagnostics']['p_min'] for r in history],
                 color='#9351aa', ls='--', label='Mixed Hessian trial, 4 rows (rejected)')
    axes[0].plot(history[-1]['time'], history[-1]['diagnostics']['p_min'], 'x', color='#9351aa', ms=9)
    axes[0].set(xlabel='Simulation time', ylabel='Minimum gas pressure',
                title='Pressure stability changes with transverse resolution', ylim=(-.004, .108), xlim=(0, .0102))
    axes[0].legend(fontsize=8, loc='upper right')
    axes[0].grid(alpha=.2)
    data = rows(args.faces/'j0.15_old_faces.csv')
    columns = ['target_energy_rate', 'target_magnetic_rate', 'target_fv_magnetic_rate']
    groups = [('1050', 'Face 1050: cells 253/254', '#d99232'),
              ('1051', 'Face 1051: cells 253/255', '#6e9bc2'),
              ('other', 'Other contributing faces', '#8c8793')]
    bottom = [0., 0., 0.]
    for face, label, color in groups:
        selected = [r for r in data if (r['face'] not in ['1050', '1051'] if face == 'other' else r['face'] == face)]
        values = [-sum(float(r[c]) for r in selected) for c in columns]
        axes[1].bar(range(3), values, bottom=bottom, color=color, label=label, width=.6)
        bottom = [a+b for a,b in zip(bottom,values)]
    for i, value in enumerate(bottom):
        axes[1].text(i, value+.6, f'{value:.2f}', ha='center', fontsize=10)
    axes[1].set_xticks(range(3), ['Conservative\nenergy', 'Curl-derived\nmagnetic energy', 'FV magnetic\n(diagnostic only)'])
    axes[1].set(ylabel='Initial local energy-density loss rate', title='Cell 253: total energy decreases much faster than curl B', ylim=(0, 54))
    axes[1].legend(fontsize=8, loc='upper right')
    axes[1].grid(axis='y', alpha=.2)
    fig.suptitle('Bounded paper-formalism audit — jittered Brio–Wu, nx=256\nStability controls only; the registered Bx gate and full M1 remain unresolved', fontsize=12)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=170)
    plt.close(fig)


if __name__ == '__main__':
    main()
