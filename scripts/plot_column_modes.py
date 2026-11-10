#!/usr/bin/env python3
"""Plot hash-verified accepted-state row modes from the bounded #24 investigation."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    report_path = args.input/'report.json'
    report = json.loads(report_path.read_text())
    if report['status'] != 'completed' or report['scientific_acceptance'] is not False:
        raise ValueError('Expected completed diagnostic, not scientific acceptance')
    series = []
    verified = {}
    for mesh, color in [('0.0', '#426b93'), ('0.15c', '#ae3970')]:
        for frame, style in [('base', '-'), ('boost', '--')]:
            name = f'brio-wu_n1024_j{mesh}_{frame}'
            record = report['runs'][name]
            if not all(record['scientific_file_parity'].values()):
                raise ValueError('Scientific parity failed')
            path = args.input/name/'row_modes.json'
            if sha(path) != record['sha256']['row_modes.json']:
                raise ValueError('Changed row-mode report')
            data = json.loads(path.read_text())
            for row in data:
                if row['sha256'] != record['sha256'][row['file']]:
                    raise ValueError('Snapshot provenance differs')
                if 'frozen_rates' in row:
                    rate = row['frozen_rates']
                    if rate['sha256'] != record['sha256'][rate['file']]:
                        raise ValueError('Rate provenance differs')
            verified[str(path)] = sha(path)
            label = ('Regular' if mesh == '0.0' else 'Column jitter')+' / '+frame
            series.append((label, color, style, data))
    args.output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
    for axis, field in zip(axes, ('vx', 'by', 'reduced_az')):
        for label, color, style, data in series:
            axis.semilogy([r['time'] for r in data],
                          [max(r['alternating'][field]['max_abs'], 1e-18) for r in data],
                          style, color=color, label=label, linewidth=1.7)
        axis.set_ylabel(f'Max row mode: {field}')
        axis.grid(alpha=.2, which='both')
    axes[0].legend(ncol=2, loc='upper left', fontsize=10)
    axes[-1].set_xlabel('Simulation time')
    fig.suptitle('Finest Brio shock: transverse alternating mode', fontsize=16)
    fig.text(.5, .025, 'Nx1024 × Ny4 • κ=1 screened quadratic candidate • original scientific files preserved\n'
             'Coefficient = (row 0 − row 1 + row 2 − row 3)/4; values below 10⁻¹⁸ shown at 10⁻¹⁸.\n'
             'These are mode diagnostics, not the registered boost-error norm. M1 remains unaccepted.',
             ha='center', fontsize=10)
    fig.tight_layout(rect=(0, .10, 1, .96))
    fig.savefig(args.output/'column_mode_growth.png', dpi=160)
    plt.close(fig)
    if all('frozen_rates' in r for *_, data in series for r in data):
        fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
        for axis, (label, _, _, data) in zip(axes.flat, series):
            for key, color, text in [('fluid', '#222222', 'Total'),
                                     ('fluid_x', '#bd4c3d', 'x-normal faces'),
                                     ('fluid_y', '#397ba5', 'y-normal faces')]:
                selected = [(r['time'], r['frozen_rates']['growth']['vx']) for r in data
                            if r['alternating']['vx']['max_abs'] >= 1e-10]
                axis.plot([t for t, _ in selected],
                          [g['rates'][key]['logarithmic_growth'] for _, g in selected],
                          color=color, label=text)
            axis.axhline(0., color='#888888', linewidth=.7)
            axis.set_title(label)
            axis.grid(alpha=.2)
            axis.set_xlabel('Simulation time')
            axis.set_ylabel('Instantaneous mode growth / time⁻¹')
        axes[0, 0].legend(fontsize=9)
        fig.suptitle('Fluid-face contributions to the transverse vx mode', fontsize=16)
        fig.text(.5, .025, 'Volume-weighted (mode · rate) / (mode · mode); sampled on the evolving nonlinear state.\n'
                 'Shown only above mode amplitude 10⁻¹⁰. These are instantaneous rates, not eigenvalues.',
                 ha='center', fontsize=10)
        fig.tight_layout(rect=(0, .08, 1, .95))
        fig.savefig(args.output/'column_mode_rate_groups.png', dpi=160)
        plt.close(fig)
    record = dict(source_sha256=sha(Path(__file__)), report_sha256=sha(report_path),
                  inputs=verified, scientific_acceptance=False,
                  matplotlib=matplotlib.__version__,
                  outputs={p.name: sha(p) for p in sorted(args.output.glob('column_mode_*.png'))})
    (args.output/'column_mode_plot_provenance.json').write_text(json.dumps(record, indent=2)+'\n')


if __name__ == '__main__':
    main()
