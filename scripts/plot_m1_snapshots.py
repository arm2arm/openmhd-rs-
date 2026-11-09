#!/usr/bin/env python3
"""Plot verified N64 archived field snapshots; these are not convergence gates."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from plot_m1_completion import ROOT, load, plt


def snapshot(directory, run, stage, time):
    path = directory / 'snapshots' / run / f'{stage}.csv.gz'
    hashes = json.loads((directory / 'archive_sha256.json').read_text())
    if hashlib.sha256(path.read_bytes()).hexdigest() != hashes[str(path.relative_to(directory))]:
        raise ValueError(f'unverified snapshot: {path}')
    with gzip.open(path, 'rt') as stream:
        cells = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(stream)]
    if len(cells) != 64**2 or len({c['id'] for c in cells}) != len(cells):
        raise ValueError('requires complete N64 snapshot')
    if any(c['time'] != time or c['volume'] <= 0 or not all(np.isfinite(list(c.values()))) for c in cells):
        raise ValueError('invalid time, volume or nonfinite snapshot')
    if abs(sum(c['volume'] for c in cells) - 1) > 1e-9:
        raise ValueError('snapshot volume is not unity')
    indices = [(round(64*c['x']-.5) % 64, round(64*c['y']-.5) % 64) for c in cells]
    if len(set(indices)) != len(cells) or any(
        max(abs((c[k]-(index+.5)/64+.5) % 1-.5) for k, index in zip(('x', 'y'), ij)) > 1e-10
        for c, ij in zip(cells, indices)
    ):
        raise ValueError('requires regular N64 centres at an integer displacement')
    arrays = {k: np.empty((64, 64)) for k in cells[0]}
    for c, (i, j) in zip(cells, indices):
        for k, v in c.items():
            arrays[k][j, i] = v
    return arrays


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default = ROOT / 'tests/reference/m1_completion'
    parser.add_argument('--candidate', type=Path, default=default/'signal_quick')
    parser.add_argument('--prescribed', type=Path, default=default/'prescribed')
    parser.add_argument('--output', type=Path, default=ROOT/'docs/images/m1_completion')
    args = parser.parse_args()
    for directory in (args.candidate, args.prescribed):
        load(directory)  # Verify complete compact archive before using its snapshots.
    args.output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'figure.dpi': 150, 'font.size': 10, 'savefig.bbox': 'tight'})

    fig, axes = plt.subplots(2, 3, figsize=(11, 7.5), sharex=True, sharey=True, layout='constrained')
    amplitude = .001/np.sqrt(4*np.pi)
    for row, (directory, prefix, label) in enumerate([
        (args.prescribed, 'loop_j0.0', 'Prescribed flow'),
        (args.candidate, 'loop_bulk-frame-signal-v1_v0.0_j0.0', 'Coupled MHD'),
    ]):
        for col, (motion, stage, time, title) in enumerate([
            ('fixed', 'initial', 0., 'Initial, t=0'),
            ('fixed', 'final', 1., 'Fixed mesh, t=1'),
            ('comoving', 'final', 1., 'Comoving mesh, t=1'),
        ]):
            data = snapshot(directory, f'{prefix}_{motion}_n64_base', stage, time)
            magnitude = np.sqrt(sum(data[k]**2 for k in ('bx', 'by', 'bz')))/amplitude
            im = axes[row, col].imshow(magnitude, origin='lower', extent=(0, 1, 0, 1),
                                      interpolation='nearest', cmap='magma', vmin=0, vmax=1.2)
            if magnitude.max() > 1.2:
                raise ValueError('magnetic snapshot exceeds the common displayed range')
            axes[row, col].set_title(title)
            axes[row, col].set_xlabel('x')
            axes[row, col].set_ylabel(f'{label}\ny' if col == 0 else 'y')
    fig.colorbar(im, ax=axes, label=r'$|B| / B_0$, $B_0=0.001/\sqrt{4\pi}$', shrink=.8)
    fig.suptitle('Field-loop snapshots · N64 regular periodic Voronoi mesh\n'
                 'Flow (2, 1); one integer-domain displacement at t=1 · coupled profile: bulk-frame-signal-v1')
    fig.savefig(args.output/'loop_snapshots.png')
    plt.close(fig)

    prefix = 'alfven_bulk-frame-signal-v1_v1.0_j0.0_fixed_n64'
    base = snapshot(args.candidate, prefix+'_base', 'final', 1.)
    boosted = snapshot(args.candidate, prefix+'_boost', 'final', 1.)
    x = (np.arange(64)+.5)/64
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout='constrained')
    for key, exact, color in [('by', .1*np.sin(2*np.pi*x), '#2166ac'),
                              ('bz', .1*np.cos(2*np.pi*x), '#b2182b')]:
        mean = np.mean(base[key], axis=0)
        axes[0].plot(x, exact, color=color, label=f'{key}: analytic')
        axes[0].plot(x, mean, '.', color=color, label=f'{key}: numerical y mean')
        axes[1].plot(x, mean-exact, color=color, label=f'{key}: y-mean error')
    difference = np.max(np.sqrt(sum((base[k]-boosted[k])**2 for k in ('bx', 'by', 'bz'))))
    axes[0].set_ylabel('Magnetic field')
    axes[1].set_ylabel('Numerical − analytic')
    for ax in axes:
        ax.set_xlabel('x'); ax.legend(fontsize=8); ax.grid(alpha=.25)
    axes[0].set_title('Wave shape at t=1')
    axes[1].set_title('Solution error (expanded vertical scale)')
    fig.suptitle('Standing Alfvén wave · N64 regular fixed mesh · bulk-frame-signal-v1\n'
                 f'Joint-boost comparison: max cellwise |ΔB| = {difference:.2e}')
    fig.savefig(args.output/'alfven_snapshot.png')
    plt.close(fig)
    files = ['loop_snapshots.png', 'alfven_snapshot.png']
    provenance = {
        'scope': 'N64 regular snapshots, not full spatial or temporal validation',
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'archive_manifest_sha256': {str(p): hashlib.sha256((p/'archive_sha256.json').read_bytes()).hexdigest()
                                    for p in (args.candidate, args.prescribed)},
        'figure_sha256': {p: hashlib.sha256((args.output/p).read_bytes()).hexdigest() for p in files},
    }
    (args.output/'snapshot_provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')


if __name__ == '__main__':
    main()
