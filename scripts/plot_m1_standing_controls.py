#!/usr/bin/env python3
"""Plot archived fixed-cap controls; this replays measurements, not solver validation."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(gzip.decompress(args.input.read_bytes()))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
    for ax, n, dt in zip(axes, (32, 64), ('.0002', '.0001')):
        for profile, label, color in [('compact', 'Common-factor limiter', '#ba4c29'),
                                      ('projected', 'Projected limiter', '#1768a0')]:
            rows = sorted([p for p in data['pairs'] if p['profile'] == profile and p['n'] == n], key=lambda p: p['time'])
            if [p['time'] for p in rows] != [0., .25, 1.]:
                raise ValueError('complete initial/quarter/final measurements required')
            ax.semilogy([p['time'] for p in rows], [p['max_normalized_L1'] for p in rows], 'o-', color=color, label=label)
        ax.axhline(data['gate'], linestyle='--', color='#555555', label='Registered boost limit')
        ax.set(title=f'N = {n} × {n}; dt cap = {dt}', xlabel='Time', xticks=[0., .25, 1.], ylim=(1e-15, 3e-5))
        ax.grid(True, which='major', alpha=.17)
    axes[0].set_ylabel('Maximum normalized boost L1 error')
    fig.suptitle('Standing Alfvén wave: fixed-cap boost controls', fontsize=14)
    fig.legend(*axes[0].get_legend_handles_labels(), loc='lower center', ncol=3, frameon=False, bbox_to_anchor=(.5, .06))
    fig.text(.5, .025, 'Regular fixed-family mesh; joint boost (2, −1, 0). Bounded controls, not full M1 acceptance.', ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .15, 1, .94))
    figure = args.output_dir / 'standing_boost_controls.png'
    fig.savefig(figure, dpi=170)
    plt.close(fig)
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    (args.output_dir / 'provenance.json').write_text(json.dumps({
        'scope': 'Figure replay of archived measured fixed-cap controls, not a new acceptance run',
        'input_sha256': sha(args.input), 'script_sha256': sha(Path(__file__)),
        'figure_sha256': sha(figure), 'matplotlib': matplotlib.__version__,
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
