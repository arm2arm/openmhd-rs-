#!/usr/bin/env python3
"""Plot the initial curl-rate probe and short projected shock; no acceptance claim."""
import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt


def read(path):
    with path.open() as stream:
        return [{k: float(v) for k, v in row.items()} for row in csv.DictReader(stream)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe', type=Path, help='Initial compatibility output directory')
    parser.add_argument('short', type=Path, help='Four-case projected short-run directory')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rows = read(args.probe/'summary.csv')
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), layout='constrained')
    for jitter, color, label in [(0., '#303846', 'Regular'), (.15, '#2563a6', 'Jittered')]:
        family = sorted((r for r in rows if r['jitter'] == jitter), key=lambda r: r['nx'])
        for field, style, method in [('baseline_relative_mismatch', '--', 'baseline'),
                                     ('projected_relative_mismatch', '-', 'projected')]:
            axes[0].plot([r['nx'] for r in family], [r[field] for r in family],
                         style, marker='o', color=color, label=f'{label}, {method}')
    axes[0].set(xlabel='nx (ny = 4)', ylabel='Relative magnetic-rate mismatch',
                yscale='log', xticks=[64, 128, 256], title='Initial operator compatibility')
    axes[0].legend(fontsize=8, loc='center left')
    for folder, color, label in [('j0.0_base', '#303846', 'Regular'),
                                 ('j0.15_base', '#2563a6', 'Jittered')]:
        cells = sorted(read(args.short/folder/'final.csv'), key=lambda r: r['x'])
        axes[1].scatter([r['x'] for r in cells], [r['p'] for r in cells], s=5,
                        alpha=.5, color=color, label=label)
    axes[1].axhline(0, color='#b02e2e', lw=1, linestyle='--')
    axes[1].set(xlabel='x', ylabel='Gas pressure', xlim=(0, 2), ylim=(-.03, 1.1),
                title='Projected-rate shock at t = 0.01')
    axes[1].legend(fontsize=8)
    axes[1].text(.03, .06, 'Jittered minimum p = 0.06755', transform=axes[1].transAxes, fontsize=9)
    for ax in axes:
        ax.grid(alpha=.2)
    fig.suptitle('Short stability improvement; jittered Bx gate still fails (0.113 > 1e-8)', fontsize=11)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=180)
    plt.close(fig)


if __name__ == '__main__':
    main()
