#!/usr/bin/env python3
"""Plot measured speedups; accept partial studies without inventing missing data."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('directory', type=Path)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
data = json.loads((args.directory/'summary.json').read_text())
rows = data['scaling']
if not rows:
    raise SystemExit('No measured scaling comparisons yet')
fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
for ax, key, label in zip(axes, ('mesh_speedup', 'evolution_speedup', 'wall_speedup'),
                         ('Mesh construction', 'Time evolution', 'Total runtime')):
    for n, jitter in sorted({(r['n'], r['jitter']) for r in rows}):
        selected = sorted([r for r in rows if (r['n'], r['jitter']) == (n, jitter)], key=lambda r: r['threads'])
        ax.plot([1]+[r['threads'] for r in selected], [1]+[r[key] for r in selected], 'o-', label=f'N{n}, jitter {jitter}')
    ax.axhline(1., color='grey', lw=1, linestyle='--')
    ax.set(xlabel='Threads per simulation', ylabel='Speedup over one thread', title=label, xticks=[1, 4, 12, 24])
    ax.grid(alpha=.2)
    ax.legend(fontsize=8)
fig.suptitle('Measured threading performance on shared REANA infrastructure')
fig.tight_layout()
args.output.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(args.output, dpi=160)
