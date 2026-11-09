#!/usr/bin/env python3
"""Plot measured failures; requires Matplotlib only for this presentation step."""
import argparse
import json
import math
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('analysis', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    data = json.loads(args.analysis.read_text())
    runs = {(r['study'], r['name']): r for r in data['runs']}
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.2), layout='constrained')
    colors = ['#333333', '#167ca6', '#b34e29']
    studies = ['baseline', 'extended', 'quadratic_extended']
    labels = ['Original paper-state source', 'Successive LS, alpha=0.2', 'Quadratic trace, alpha=0.2']
    for ax, n in zip(axes[0], [256, 512]):
        for study, label, color in zip(studies, labels, colors):
            run = runs[study, f'n{n}_j0.15_base']
            h = run['history']
            ax.plot([r['time'] for r in h], [r['p_min'] for r in h], label=label, color=color)
            if not run['completed']:
                ax.plot(h[-1]['time'], h[-1]['p_min'], 'x', color=color, markersize=9)
        ax.set(title=f'Jittered shock: nx={n}, ny=4', xlabel='Simulation time',
               ylabel='Minimum accepted-state pressure', ylim=(-.005, .105))
        ax.axhline(0, color='.6', lw=.7)
        ax.grid(alpha=.2)
        ax.text(.03, .93, 'x = aborted evolution', transform=ax.transAxes, va='top', fontsize=9)
    axes[0, 0].legend(loc='upper right', fontsize=8)
    ax = axes[1, 0]
    for operator, color in [('successive', colors[1]), ('quadratic', colors[2])]:
        modes = [r for r in data['modes'] if r['jitter'] == 0 and r['ky'] == 0 and r['operator'] == operator]
        ax.plot([r['kx']/8 for r in modes], [r['potential_rayleigh']/256 for r in modes],
                'o', color=color, label=f'{operator}: Rust measurement')
    theta = [math.pi*i/200 for i in range(201)]
    ax.plot([t/math.pi for t in theta], [(2/3)*(math.cos(2*t)-math.cos(t)) for t in theta],
            color=colors[2], alpha=.6, label='Quadratic: independent symbol')
    ax.axhline(0, color='.4', lw=.8)
    ax.axvspan(2/3, 1, color=colors[2], alpha=.08)
    ax.text(.74, 1.1, 'Growth', color=colors[2])
    ax.set(title='Quadratic Laplacian can amplify modes', xlabel='Wavenumber / Nyquist wavenumber',
           ylabel='Growth rate times h² (eta=1)', xlim=(0, 1))
    ax.legend(loc='lower left', fontsize=8)
    ax.grid(alpha=.2)
    ax = axes[1, 1]
    for i, study in enumerate(studies):
        run = runs[study, 'n256_j0.15_base']
        ax.bar(i, run['bx_max_error'], color=colors[i])
        ax.text(i, run['bx_max_error']*1.12, f'{run["bx_max_error"]:.3g}', ha='center', fontsize=9)
    ax.axhline(1e-8, color='black', ls='--', label='Unchanged gate: 1e-8')
    ax.set(yscale='log', ylim=(1e-9, 1), ylabel='Maximum |Bx - 0.75|',
           title='Bx still fails at the last accepted state', xticks=range(3),
           xticklabels=['Original\n(aborted)', 'Successive\n(t=0.02)', 'Quadratic\n(t=0.02)'])
    ax.legend(loc='lower right', fontsize=8)
    ax.grid(axis='y', alpha=.2)
    fig.suptitle('Optional dissipation rejected as an M1 repair\n'
                 'Bounded local controls; no thresholds changed; both trial profiles removed', fontsize=15)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=180)


if __name__ == '__main__':
    main()
