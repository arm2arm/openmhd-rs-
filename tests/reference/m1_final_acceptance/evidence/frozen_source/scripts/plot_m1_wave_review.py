#!/usr/bin/env python3
"""Plot the complete reviewed wave matrix before the containing loop packet finishes."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from matplotlib.colors import LogNorm
from matplotlib.patches import Rectangle
from plot_m1_completion import ROOT, matplotlib, plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', type=Path, default=ROOT/'tests/reference/m1_completion/ai_review')
    parser.add_argument('--output', type=Path, default=ROOT/'docs/images/m1_completion')
    args = parser.parse_args()
    hashes = json.loads((args.review/'archive_sha256.json').read_text())
    names = ['original_wave_matrix_report.json', 'signal_wave_matrix_report.json']
    reports = []
    for name in names:
        data = (args.review/name).read_bytes()
        if hashlib.sha256(data).hexdigest() != hashes[name]:
            raise ValueError(f'changed reviewed report: {name}')
        report = json.loads(data)
        if len(report['runs']) != 64 or len(report['pairs']) != 32 or len(report['ladders']) != 8:
            raise ValueError('requires a complete reviewed wave matrix')
        if any(s['n'] != [32, 64, 128, 256] for s in report['ladders']):
            raise ValueError('missing reviewed resolution')
        reports.append(report)
    args.output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'figure.dpi': 150, 'font.size': 10, 'savefig.bbox': 'tight'})
    labels = ['Original', 'Signal completion']
    colors = ['#ba483b', '#226aa1']
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharex=True, sharey=True, layout='constrained')
    for row, jitter in enumerate([0., .15]):
        for col, parallel in enumerate([0., 1.]):
            ax = axes[row, col]
            for report, label, color in zip(reports, labels, colors):
                for motion, style, marker in [('fixed', '-', 'o'), ('comoving', '--', '^')]:
                    s = next(s for s in report['ladders'] if (s['parallel'], s['jitter'], s['motion']) == (parallel, jitter, motion))
                    p = s['finest_three']['order']
                    verdict = 'PASS' if s['gate'] else 'FAIL'
                    ax.loglog(s['n'], np.array(s['B_L1'])/.1, linestyle=style, marker=marker,
                              color=color, label=f'{label}, {motion}: p={p:.2f}, {verdict}')
            ax.axhline(.02, color='black', linestyle=':', linewidth=1, label='Finest-error bound')
            ax.set_title(f'{"Travelling" if parallel == 0 else "Standing"} · {"regular" if jitter == 0 else "jitter 0.15"}')
            ax.set_xticks([32, 64, 128, 256], [32, 64, 128, 256])
            ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
            ax.set_xlabel('N per direction'); ax.set_ylabel('Magnetic vector L1 / wave amplitude')
            ax.grid(alpha=.25); ax.legend(fontsize=7)
    fig.suptitle('Complete Alfvén spatial matrix · t=1 · 2.5D periodic Voronoi\n'
                 'Gate: N64/128/256 fitted order ≥ 1.8 and N256 relative error ≤ 0.02\n'
                 'Each profile passes 3/8 ladders; residual-fit uncertainty is reported separately')
    fig.savefig(args.output/'reviewed_wave_convergence.png'); plt.close(fig)

    configs = [(v, j, m) for v in [0., 1.] for j in [0., .15] for m in ['fixed', 'comoving']]
    row_labels = [f'{"Travelling" if v == 0 else "Standing"}, {"regular" if j == 0 else "jittered"}, {m}' for v, j, m in configs]
    matrices = []
    for report in reports:
        values = np.array([[next(p for p in report['pairs'] if (p['parallel'], p['jitter'], p['motion'], p['n']) == (*c, n))['times']['final']['errors']['B']['L1']/.1
                            for n in [32, 64, 128, 256]] for c in configs])
        if not np.all(np.isfinite(values)) or np.any(values < 0):
            raise ValueError('invalid reviewed magnetic boost error')
        matrices.append(values)
    ceiling = max(1e-7, 10**np.ceil(np.log10(max(float(v.max()) for v in matrices))))
    fig, axes = plt.subplots(1, 2, figsize=(12, 6), sharey=True, layout='constrained')
    for ax, values, report, label in zip(axes, matrices, reports, labels):
        im = ax.imshow(np.maximum(values, 1e-16), norm=LogNorm(1e-16, ceiling), cmap='viridis', aspect='auto')
        for (i, j), value in np.ndenumerate(values):
            ax.text(j, i, f'{value:.1e}', ha='center', va='center', fontsize=8,
                    color='black' if value > 1e-5 else 'white')
            if value > 1e-8:
                ax.add_patch(Rectangle((j-.48, i-.48), .96, .96, fill=False, edgecolor='#f03b20', linewidth=2))
        ax.set_xticks(range(4), [32, 64, 128, 256]); ax.set_xlabel('N per direction')
        ax.set_yticks(range(8), row_labels)
        ax.set_title(f'{label}\n{report["review_summary"]["boost_pass_both"]}/32 full-field pairs pass both scales', fontsize=11)
    fig.colorbar(im, ax=axes, label='Magnetic boost L1 / 0.1', shrink=.9)
    fig.suptitle('Complete Alfvén boost matrix · joint boost (2, −1, 0), t=1\n'
                 'Red boxes exceed the magnetic relative-L1 gate 1e−8; colour floor 1e−16\n'
                 'Full-field classifications include density, pressure, velocity and energy; wave matrix only')
    fig.savefig(args.output/'reviewed_wave_boost.png'); plt.close(fig)
    figures = ['reviewed_wave_convergence.png', 'reviewed_wave_boost.png']
    provenance = {'scope': 'Complete 128-run wave matrix only; no claim that loop/temporal packet is finished',
                  'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  'input_report_sha256': {name: hashes[name] for name in names},
                  'figure_sha256': {name: hashlib.sha256((args.output/name).read_bytes()).hexdigest() for name in figures}}
    (args.output/'wave_review_plot_provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')


if __name__ == '__main__':
    main()
