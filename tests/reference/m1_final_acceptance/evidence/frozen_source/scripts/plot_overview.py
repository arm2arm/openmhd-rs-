#!/usr/bin/env python3
"""Figures of docs/OVERVIEW.md from existing results (read-only plotting, no evolution).

All three figures show the current opt-in M1 candidate as run by campaign A
(tests/reference/m1_iterative_step_campaigns): the Alfvén ladders from the
archived phase summary, and the finest Brio-Wu and Orszag-Tang states from the
local raw snapshots of that campaign next to the pinned Athena++ references.
Writes PNGs and provenance.json with every input's and output's SHA256.

  "$HOME/.venvs/openmhd-plot/bin/python" scripts/plot_overview.py
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT/'tests/reference/m1_iterative_step_campaigns/iter/plans/iter-waves_checkpoint.json.gz'
RAW = ROOT/'results/followup_iter-physics_20261117/raw'
REFERENCE = ROOT/'tests/reference/external_mhd'
CANDIDATE = ('bulk-frame-heun-quadratic-v1, projection screening 1, hlld-pressure flux, '
             'smooth-extrema A limiter, iterative projection')
# Reference palette of the data-viz method: surface, text and categorical slots 1-3.
SURFACE, INK, MUTED, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
BLUE, ORANGE, AQUA = '#2a78d6', '#eb6834', '#1baf7a'
SEQUENTIAL = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']
AMPLITUDE = 0.1   # Alfvén-wave amplitude: relative B L1 = B L1 / 0.1


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def style():
    plt.rcParams.update({
        'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE, 'savefig.facecolor': SURFACE,
        'axes.edgecolor': MUTED, 'axes.labelcolor': INK, 'text.color': INK,
        'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.grid': True, 'grid.color': GRID,
        'grid.linewidth': 0.8, 'axes.spines.top': False, 'axes.spines.right': False,
        'font.size': 10.5, 'axes.titlesize': 11.5, 'axes.titleweight': 'bold', 'legend.frameon': False})


def ladders(output):
    rows = json.loads(gzip.decompress(CAMPAIGN.read_bytes()))['summaries']['wave']['alfven_convergence']
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True, constrained_layout=True)
    for ax, jitter, title in zip(axes, (0.0, 0.15), ('Regular mesh', 'Jittered mesh (jitter .15)')):
        mine = {(r['parallel'], r['motion']): r for r in rows if r['jitter'] == jitter}
        same, standing = mine[(0.0, 'fixed')], mine[(1.0, 'fixed')]
        n = np.array([x['n'] for x in same['rows']], float)
        for row, color, marker, label in ((standing, ORANGE, 's', 'standing wave, fixed mesh'),
                                          (same, BLUE, 'o', 'other three ladders (identical)')):
            error = np.array([x['B_L1'] for x in row['rows']])/AMPLITUDE
            ax.plot(n, error, color=color, marker=marker, lw=2, ms=6.5, label=label,
                    markeredgecolor=SURFACE, markeredgewidth=1.2, zorder=3)
            ax.annotate(f"order {row['finest_three_order']:.3f}", (n[-1], error[-1]), xytext=(8, 0),
                        textcoords='offset points', va='center', color=INK, fontsize=9.5)
        guide = 0.55*(np.array([x['B_L1'] for x in same['rows']])[0]/AMPLITUDE)*(n/n[0])**-2
        ax.plot(n, guide, color=MUTED, lw=1.2, ls=':', label=r'$N^{-2}$ slope guide', zorder=2)
        ax.set(xscale='log', yscale='log', title=title, xlabel=r'cells per side $N$')
        ax.set_xticks(n, [f'{int(v)}' for v in n])
        ax.minorticks_off()
        ax.set_xlim(26, 420)
    axes[0].set_ylabel('B L1 error relative to the wave amplitude')
    axes[0].legend(loc='lower left', fontsize=9.5)
    fig.suptitle('Alfvén waves, t = 1: every ladder converges at second order (registered gate: order at least 1.8)',
                 color=INK, fontsize=12)
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return [CAMPAIGN]


def read_cells(path):
    with open(path) as stream:
        rows = list(csv.DictReader(stream))
    return {k: np.array([float(r[k]) for r in rows]) for k in ('x', 'y', 'rho', 'p', 'vx', 'by')}


def read_reference(path):
    rows = list(csv.DictReader(io.StringIO(gzip.decompress(Path(path).read_bytes()).decode())))
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0]}


def brio(output):
    mine_path = RAW/'brio-wu_n1024_j0.0_base/final.csv'
    ref_path = REFERENCE/'brio_8192.csv.gz'
    mine, ref = read_cells(mine_path), read_reference(ref_path)
    window = (mine['x'] >= 0.5) & (mine['x'] <= 1.5)
    xs = np.unique(np.round(mine['x'][window], 12))
    column = lambda field: np.array([mine[field][window][np.isclose(mine['x'][window], x)].mean() for x in xs])
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 6.2), sharex=True, constrained_layout=True)
    for ax, (field, label) in zip(axes.flat, (('rho', r'density $\rho$'), ('p', r'pressure $p$'),
                                              ('vx', r'velocity $v_x$'), ('by', r'field $B_y$'))):
        ax.plot(ref['x'], ref[field], color=ORANGE, lw=2, ls='--', label='Athena++, 8192 cells', zorder=2)
        ax.plot(xs, column(field), color=BLUE, lw=1.6, label='OpenMHD-RS, 1024 x 4 Voronoi cells', zorder=3)
        ax.set_title(label)
    for ax in axes[1]:
        ax.set_xlabel('x')
    axes[0, 0].legend(loc='lower left', fontsize=9.5)
    fig.suptitle('Brio–Wu shock tube, t = 0.1, regular mesh, against the pinned Athena++ reference', color=INK, fontsize=12)
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return [mine_path, ref_path]


def orszag_tang(output):
    mine_path = RAW/'orszag-tang_n256_j0.0_base/final.csv'
    ref_path = REFERENCE/'vortex_512.csv.gz'
    mine, ref = read_cells(mine_path), read_reference(ref_path)

    def image(cells, n):
        order = np.lexsort((np.round(cells['x'], 12), np.round(cells['y'], 12)))
        if len(order) != n*n:
            raise ValueError('not a regular square lattice')
        return cells['rho'][order].reshape(n, n)

    left, right = image(mine, 256), image(ref, 64)
    lo, hi = min(left.min(), right.min()), max(left.max(), right.max())
    cmap = LinearSegmentedColormap.from_list('blue', SEQUENTIAL)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.9), constrained_layout=True)
    for ax, data, title in ((axes[0], left, 'OpenMHD-RS, 256 x 256 Voronoi cells'), (axes[1], right, 'Athena++ 512 x 512, archived as 64 x 64 bin averages')):
        shown = ax.imshow(data, origin='lower', extent=(0, 1, 0, 1), cmap=cmap, vmin=lo, vmax=hi, interpolation='nearest')
        ax.set(title=title, xlabel='x', ylabel='y')
        ax.grid(False)
    bar = fig.colorbar(shown, ax=axes, shrink=0.85, pad=0.02)
    bar.set_label(r'density $\rho$')
    fig.suptitle('Orszag–Tang vortex, t = 0.5, regular mesh', color=INK, fontsize=12)
    fig.savefig(output, dpi=160)
    plt.close(fig)
    return [mine_path, ref_path]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'docs/images/overview')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    style()
    inputs, outputs = {}, {}
    for name, make in (('alfven_ladders.png', ladders), ('brio_wu.png', brio), ('orszag_tang.png', orszag_tang)):
        path = args.output_dir/name
        for source in make(path):
            inputs[str(Path(source).resolve().relative_to(ROOT))] = sha(source)
        outputs[name] = sha(path)
    provenance = dict(scope='Read-only figures of existing results; no evolution.', configuration=CANDIDATE,
                      campaign='tests/reference/m1_iterative_step_campaigns (campaign A, 2026-11-17/18)',
                      script_sha256=sha(__file__), matplotlib=matplotlib.__version__, numpy=np.__version__,
                      input_sha256=inputs, output_sha256=outputs)
    (args.output_dir/'provenance.json').write_text(json.dumps(provenance, indent=1)+'\n')
    for name, digest in outputs.items():
        print(name, digest[:16])


if __name__ == '__main__':
    raise SystemExit(main())
