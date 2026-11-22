#!/usr/bin/env python3
"""Plot the bounded Heun time study; errors are against a finite dt reference."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    data = json.loads((args.directory/'summary.json').read_text())
    manifest = json.loads((args.directory/'manifest.json').read_text())
    config = next(iter(manifest['configs'].values()))
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True)
    for row in data['temporal']:
        ax = axes[int(row['parallel'])][int(row['jitter'] > 0)]
        y = [e['B']['L1'] for e in row['errors']]
        if manifest.get('auxiliary_study'):
            spline = 'spline' in row['profile']
            label = ('Cubic projection' if spline else 'Bin projection')
            label += ', limited' if row['limited'] else ', unlimited'
            ax.loglog(row['caps'][:-1], y, 'o-' if row['limited'] else 's--',
                      color='tab:orange' if spline else 'tab:blue', label=label)
        else:
            label = 'Reevaluated Heun' if 'heun' in row['profile'] else 'Historical endpoint'
            ax.loglog(row['caps'][:-1], y, 'o-', label=label)
        ax.set_title(('Travelling' if row['parallel'] == 0 else 'Standing')+f", jitter={row['jitter']}")
        ax.set_ylabel('Magnetic L1 time error')
        ax.set_xlabel('Timestep cap')
        ax.grid(True, which='both', alpha=.25)
        ax.legend(fontsize=8)
    fig.suptitle(f"Alfvén time comparison: N={config['n']}, t={config['target']}; reference dt=0.000025"
                 + (' (execution check)' if manifest['quick'] else ''))
    fig.tight_layout()
    fig.savefig(args.directory/'temporal.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
