#!/usr/bin/env python3
"""Plot verified vortex calibration bins against the pinned M0 reference."""
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    provenance = json.loads((args.archive/'execution_provenance.json').read_text())
    raw_runs = gzip.decompress((args.archive/'runs.json.gz').read_bytes())
    if digest(raw_runs) != provenance['result_sha256']['runs.json']:
        raise ValueError('Execution runs hash differs')
    runs = json.loads(raw_runs)
    if len(runs) != 1:
        raise ValueError('Requires the single vortex calibration case')
    run = next(iter(runs.values()))
    config = run['config']
    if (config['case'] != 'orszag-tang' or config['n'] != 128 or config['jitter'] != .15
        or config['time'] != .5 or config['boost'] != [0., 0., 0.]
        or run['status'] != 'completed' or not run['state_and_diagnostic_gates']):
        raise ValueError('Requires the completed passing N128 jittered base calibration')
    raw_bins = gzip.decompress((args.archive/'projected_bins.json.gz').read_bytes())
    if digest(raw_bins) != run['sha256']['projected_bins.json']:
        raise ValueError('Projected bins differ from execution')
    candidate = json.loads(raw_bins)
    directory = ROOT/'tests/reference/external_mhd'
    reference_name = 'vortex_512.csv.gz'
    raw_reference = (directory/reference_name).read_bytes()
    pinned = json.loads((directory/'provenance.json').read_text())
    if digest(raw_reference) != pinned['result_sha256'][reference_name]:
        raise ValueError('Independent reference differs from pinned hash')
    reference = [{k: float(v) for k, v in row.items()} for row in
                 csv.DictReader(io.StringIO(gzip.decompress(raw_reference).decode()))]
    if len(candidate) != 4096 or len(reference) != 4096:
        raise ValueError('Requires complete 64 by 64 comparison bins')
    if any(abs(r['x']-(i % 64+.5)/64) > 1e-12 or abs(r['y']-(i // 64+.5)/64) > 1e-12
           for i, r in enumerate(reference)):
        raise ValueError('Reference bin ordering differs')
    if any(not math.isfinite(v) for r in candidate+reference for v in r.values()):
        raise ValueError('Nonfinite sample')

    scales = dict(rho=25/(36*math.pi), p=5/(12*math.pi),
                  bx=1/math.sqrt(4*math.pi), by=1/math.sqrt(4*math.pi))
    labels = dict(rho='Density ρ', p='Pressure p', bx='Magnetic Bx', by='Magnetic By')
    measured = {}
    args.output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.size': 10})
    outputs = []
    for family, fields in [('gas', ('rho', 'p')), ('magnetic', ('bx', 'by'))]:
        fig, axes = plt.subplots(2, 3, figsize=(11.8, 7.8), layout='constrained')
        for row, field in enumerate(fields):
            a = np.array([r[field] for r in candidate]).reshape(64, 64)
            b = np.array([r[field] for r in reference]).reshape(64, 64)
            error = (a-b)/scales[field]
            measured[field] = math.fsum(abs(x) for x in error.ravel())/4096
            if not math.isclose(measured[field], run['reference_errors'][field]['L1'],
                                rel_tol=1e-12, abs_tol=1e-15):
                raise ValueError('Plot error differs from registered comparison: '+field)
            vmin, vmax = min(a.min(), b.min()), max(a.max(), b.max())
            cmap = 'magma' if family == 'gas' else 'RdBu_r'
            if family == 'magnetic':
                vmax = max(abs(vmin), abs(vmax))
                vmin = -vmax
            for col, (values, title) in enumerate([(a, 'Candidate, N128'), (b, 'Athena++, N512')]):
                im = axes[row, col].imshow(values, origin='lower', extent=(0, 1, 0, 1),
                                           interpolation='nearest', cmap=cmap, vmin=vmin, vmax=vmax)
                axes[row, col].set_title(title, fontsize=10)
            fig.colorbar(im, ax=axes[row, :2], label=labels[field], shrink=.85)
            limit = max(abs(error.min()), abs(error.max()), 1e-16)
            im = axes[row, 2].imshow(error, origin='lower', extent=(0, 1, 0, 1),
                                     interpolation='nearest', cmap='RdBu_r', vmin=-limit, vmax=limit)
            axes[row, 2].set_title(f'Difference / M0 scale; L1={measured[field]:.5f}', fontsize=10)
            fig.colorbar(im, ax=axes[row, 2], label='Normalized difference', shrink=.85)
            for axis in axes[row]:
                axis.set(xlabel='x', ylabel='y', xticks=[0, .5, 1], yticks=[0, .5, 1])
        fig.suptitle('Orszag–Tang at t=0.5 · jitter 0.15 · screened quadratic candidate (κ=1)\n'
                     'Both solutions projected onto the registered 64 × 64 comparison bins', fontsize=13)
        fig.supxlabel('Jittered profile errors are diagnostics. Full regular-mesh refinement, boost and N256 gates remain required.', fontsize=9)
        name = f'vortex_calibration_{family}.png'
        fig.savefig(args.output/name, dpi=160)
        plt.close(fig)
        outputs.append(name)
    report = dict(scope=__doc__, script_sha256=digest(Path(__file__).read_bytes()),
                  execution_runs_sha256=digest(raw_runs), projected_bins_sha256=digest(raw_bins),
                  reference_gzip_sha256=digest(raw_reference), scaled_L1=measured,
                  matplotlib=matplotlib.__version__, numpy=np.__version__, backend='Agg',
                  figure_sha256={name: digest((args.output/name).read_bytes()) for name in outputs})
    (args.output/'vortex_calibration_plot_provenance.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
