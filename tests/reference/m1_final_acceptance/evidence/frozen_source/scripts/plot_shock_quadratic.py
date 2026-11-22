#!/usr/bin/env python3
"""Plot bounded quadratic-curl measurements; failed physical gates stay explicit."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def read_json(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study', type=Path)
    parser.add_argument('projected_short', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    with (args.study/'initial.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    extensions = read_json(args.study/'extension/runs.json')
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), layout='constrained')
    for stencil, color in [('affine', '#586575'), ('quadratic', '#147d92')]:
        selected = [r for r in rows if r['jitter'] == '0.15' and r['field'] == 'smooth-1d'
                    and r['stencil'] == stencil]
        axes[0].plot([int(r['nx']) for r in selected],
                     [float(r['transverse_max_error']) for r in selected],
                     'o-', color=color, label=stencil.title())
    axes[0].set(xlabel='nx (ny = 4)', ylabel='Maximum spurious transverse gradient',
                yscale='log', xticks=[256, 512, 1024], title='Initial smooth x-only field')
    configs = [('projected', 'affine', args.projected_short, '#586575', 'Previous projected'),
               ('quadratic', 'quadratic', args.study/'short', '#147d92', 'Retained quadratic'),
               ('hessian', 'quadratic', args.study/'hessian_short', '#b76c2c', 'Rejected Hessian')]
    for profile, stencil, short, color, label in configs:
        initial = next(r for r in rows if r['nx'] == '256' and r['jitter'] == '0.15'
                       and r['field'] == 'brio' and r['stencil'] == stencil)
        run = read_json(short/'runs.json')['j0.15_base']
        extended = extensions[f'bulk-frame-heun-{profile}-v1_base']
        bx = [float(initial['transverse_max_error']), run['diagnostic_values']['bx_max_error'],
              extended['bx_max_error']]
        pressures = [.1, read_json(short/'j0.15_base/history.json')[-1]['diagnostics']['p_min'],
                     extended['history'][-1]['diagnostics']['p_min']]
        axes[1].plot([0, .01, .02], bx, 'o--', color=color, label=label)
        axes[2].plot([0, .01, .02], pressures, 'o--', color=color, label=label)
    axes[1].set(xlabel='Simulation time', ylabel='Maximum |Bx − 0.75|', ylim=(0, .18),
                title='Jittered shock: field error')
    axes[1].text(.03, .96, 'Unchanged gate: 1e−8 (all fail)', va='top',
                 transform=axes[1].transAxes, fontsize=9)
    axes[2].set(xlabel='Simulation time', ylabel='Minimum gas pressure', ylim=(0, .115),
                title='Jittered shock: positive endpoints')
    axes[2].axhline(0, color='#a33', linewidth=1)
    for ax in axes:
        ax.grid(alpha=.2)
        ax.legend(fontsize=8)
    for ax in axes[1:]:
        ax.set_xticks([0, .01, .02])
    fig.suptitle('Measured improvement with tradeoffs; 256 × 4 shock, no M1 acceptance', fontsize=12)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=180)
    plt.close(fig)


if __name__ == '__main__':
    main()
