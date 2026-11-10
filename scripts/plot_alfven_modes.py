#!/usr/bin/env python3
"""Plot the measured N64 wave error decomposition; this is not an acceptance gate."""
import argparse
import gzip
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('measurements', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    raw = args.measurements.read_bytes()
    report = json.loads(gzip.decompress(raw) if args.measurements.suffix == '.gz' else raw)
    selected = [r for r in report['runs'].values()
                if r['config']['n'] == 64 and r['config']['motion_family'] == 'fixed'
                and r['config']['boost'] == [0., 0., 0.]]
    selected.sort(key=lambda r: (r['config']['jitter'], r['config']['parallel']))
    if [(r['config']['jitter'], r['config']['parallel']) for r in selected] != [
        (0., 0.), (0., 1.), (.15, 0.), (.15, 1.),
    ]:
        raise ValueError('Requires the four N64 fixed-mesh wave families')
    if any(r['stages']['final']['time'] != 1. for r in selected):
        raise ValueError('Requires completed t=1 snapshots')

    labels = ['Regular\ntravelling', 'Regular\nstanding',
              'Jittered\ntravelling', 'Jittered\nstanding']
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(1, 3, figsize=(14, 5), layout='constrained')
    positions = range(4)
    for stage, shift, color, label in [('initial', -.16, '#92c5bd', 'Initial discrete curl'),
                                      ('final', .16, '#1a8175', 'Final, t=1')]:
        values = [100*(1-r['stages'][stage]['amplitude_relative']) for r in selected]
        axes[0].bar([x+shift for x in positions], values, width=.3, color=color, label=label)
    axes[0].set(title='Wave-mode amplitude deficit', ylabel='100 × (1 − |c|), percent')
    axes[0].legend(fontsize=9, frameon=False)

    phases = [1000*r['stages']['final']['phase_radians'] for r in selected]
    axes[1].bar(positions, phases, width=.6, color='#7653a1')
    for i, phase in enumerate(phases):
        axes[1].text(i, phase+.4, f'{phase:.2f}', ha='center', va='bottom', color='white', fontsize=9)
    axes[1].set(title='Final wave-mode phase drift', ylabel='arg(c), milliradians')

    bottom = [0.]*4
    for key, label, color in [('phase', 'Phase', '#7653a1'),
                              ('amplitude', 'Amplitude', '#1a8175'),
                              ('shape', 'Orthogonal remainder', '#dc9d38'),
                              ('bx', 'Longitudinal Bx', '#bc5563')]:
        values = [100*r['stages']['final']['squared_error_fractions'][key] for r in selected]
        axes[2].bar(positions, values, bottom=bottom, width=.6, color=color, label=label)
        bottom = [b+v for b, v in zip(bottom, values)]
    axes[2].set(title='Shares of final squared B error', ylabel='Percent of volume-weighted B L2²', ylim=(0, 140))
    axes[2].set_yticks([0, 25, 50, 75, 100])
    axes[2].legend(fontsize=8, frameon=False, ncol=2, loc='upper left')
    for axis in axes:
        axis.set_xticks(positions, labels=labels)
        axis.tick_params(axis='x', labelsize=9)
        axis.grid(axis='y', alpha=.15)
        axis.set_axisbelow(True)
    fig.suptitle('Measured Alfvén error: N64, fixed meshes, screened quadratic candidate (κ=1)', fontsize=14)
    fig.supxlabel('32 medium waves × three snapshots checked. Mode decomposition is diagnostic; full N64/128/256 L1 convergence remains required.', fontsize=9)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
