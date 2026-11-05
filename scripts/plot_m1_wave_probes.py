#!/usr/bin/env python3
"""Compare registered irregular-wave experiments; incomplete cases stay explicit.

This is a diagnostic figure, not a replacement for the full acceptance packet.
Every included snapshot must match its completed run's immutable file digest.
"""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from run_m1_wave_loop import physical_errors, read_cells


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--linear-dir', type=Path, required=True)
    parser.add_argument('--quadratic-dir', type=Path, required=True)
    parser.add_argument('--consistent-dir', type=Path, required=True)
    parser.add_argument('--matched-dir', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    inputs, measurements, snapshots = {}, {}, {}
    studies = [('linear HLL', args.linear_dir),
               ('quadratic only', args.quadratic_dir),
               ('consistent rate', args.consistent_dir)]
    if args.matched_dir is not None:
        studies.append(('matched cleaning', args.matched_dir))
    for label, directory in studies:
        ledger = directory / 'runs.json'
        # Capture one ledger version, since an unfinished study may still append.
        raw = ledger.read_bytes()
        inputs[str(ledger)] = hashlib.sha256(raw).hexdigest()
        runs = json.loads(raw)
        measurements[label] = {}
        for n in (32, 64, 128, 256):
            name = (f'alfven_bulk-frame-hll-v1_v0.0_j0.15_fixed_n{n}_base'
                    if label == 'linear HLL' else f'n{n}')
            r = runs.get(name)
            if r is None or r['status'] != 'completed':
                measurements[label][n] = {'status': 'pending' if r is None else r['status']}
                continue
            if r['summary']['time'] != 1. or not r['summary']['completed']:
                raise ValueError('completed record lacks target state')
            hashes = r.get('artifacts_sha256', r.get('sha256'))
            row = {'status': 'completed'}
            for stage, time in [('initial', 0.), ('final', 1.)]:
                path = directory / name / (stage + '.csv')
                digest = sha(path)
                if digest != hashes[path.name]:
                    raise ValueError(f'changed snapshot: {path}')
                inputs[str(path)] = digest
                cells = read_cells(path)
                if len(cells) != n*n or any(c['time'] != time for c in cells):
                    raise ValueError('snapshot count/time mismatch')
                row[stage] = physical_errors(cells, time, 'alfven', 0., [0., 0., 0.])
                if n == 128 and stage == 'final':
                    snapshots[label] = cells
            measurements[label][n] = row

    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False,
                         'axes.spines.right': False, 'savefig.dpi': 160})
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.7), layout='constrained')
    for label, _ in studies:
        rows = [(n, r) for n, r in measurements[label].items() if r['status'] == 'completed']
        for ax, stage in zip(axes, ('initial', 'final')):
            ax.loglog([n for n, _ in rows], [r[stage]['B']['L1']/.1 for _, r in rows],
                      'o-', label=label)
    axes[1].axhline(.02, color='grey', ls=':', label='finest-grid amplitude limit')
    for ax, title in zip(axes, ('Initial curl representation', 'Evolved physical error at t=1')):
        ax.set(title=title, xlabel='N in each direction', ylabel='Vector B L1 / amplitude .1')
        ax.grid(alpha=.2)
        ax.legend(fontsize=8)
    pending = [f'{label}: '+','.join(str(n) for n, r in measurements[label].items()
                                    if r['status'] != 'completed') for label, _ in studies]
    fig.suptitle('Irregular travelling wave · jitter .15 · fixed mesh\n'
                 'Missing completed results — ' + '; '.join(pending), fontsize=11)
    fig.savefig(out/'irregular_wave_experiments.png')
    plt.close(fig)

    fig, axes = plt.subplots(1, len(studies), figsize=(4.3*len(studies), 4.4), layout='constrained')
    fields = {}
    for label, cells in snapshots.items():
        x = np.array([c['x'] for c in cells])
        exact = np.column_stack((np.ones(len(x)), .1*np.sin(2*np.pi*x), .1*np.cos(2*np.pi*x)))
        b = np.array([[c[k] for k in ('bx', 'by', 'bz')] for c in cells])
        fields[label] = np.linalg.norm(b-exact, axis=1)/.1
    largest = max((float(v.max()) for v in fields.values()), default=1.)
    for ax, (label, _) in zip(axes, studies):
        if label in fields:
            cells = snapshots[label]
            im = ax.scatter([c['x'] for c in cells], [c['y'] for c in cells],
                            c=fields[label], s=2, vmin=0, vmax=largest, cmap='magma', rasterized=True)
        else:
            ax.text(.5, .5, 'N128 final state pending', ha='center', transform=ax.transAxes)
        ax.set(title=label, xlabel='x', ylabel='y', xlim=(0, 1), ylim=(0, 1), aspect='equal')
    if fields:
        fig.colorbar(im, ax=axes, label='Pointwise |B − Bexact| / .1', shrink=.8)
    fig.suptitle('N128 irregular wave at t=1 · same color scale\nCell-centroid samples; no smoothing', fontsize=11)
    fig.savefig(out/'irregular_wave_error_maps.png')
    plt.close(fig)
    record = {'scope': 'diagnostic comparison, not full M1 acceptance',
              'script_sha256': sha(Path(__file__)), 'matplotlib': matplotlib.__version__,
              'numpy': np.__version__, 'inputs_sha256': inputs, 'measurements': measurements,
              'outputs_sha256': {p.name: sha(p) for p in out.glob('*.png')}}
    (out/'provenance.json').write_text(json.dumps(record, indent=2, allow_nan=False)+'\n')


if __name__ == '__main__':
    main()
