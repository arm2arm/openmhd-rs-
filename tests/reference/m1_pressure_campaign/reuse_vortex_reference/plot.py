"""Plot independently rebinned N64/N128 vortex data; N256 gate remains pending."""
import argparse
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


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    report = json.loads((args.archive/'independent_reference.json').read_text())
    values = json.loads(gzip.decompress((args.archive/'independent_bins.json.gz').read_bytes()))
    reference_path = Path('tests/reference/external_mhd/vortex_512.csv.gz')
    assert digest(reference_path) == report['reference_sha256']
    reference = np.genfromtxt(io.BytesIO(gzip.decompress(reference_path.read_bytes())), names=True, delimiter=',')
    scales = dict(rho=25/(36*math.pi), p=5/(12*math.pi),
                  bx=1/math.sqrt(4*math.pi), by=1/math.sqrt(4*math.pi))
    labels = dict(rho='Density ρ', p='Gas pressure p', bx='Magnetic Bx', by='Magnetic By')
    args.output.mkdir(parents=True, exist_ok=True)
    outputs = {}
    plt.rcParams.update({'font.size': 10})
    for family, fields in [('gas', ('rho', 'p')), ('magnetic', ('bx', 'by'))]:
        fig, axes = plt.subplots(2, 4, figsize=(15, 7.7), layout='constrained')
        for row, field in enumerate(fields):
            arrays = [np.array(values[f'orszag-tang_n{n}_j0.0_base'][field]).reshape(64, 64)
                      for n in (64, 128)]
            arrays.append(reference[field].reshape(64, 64))
            error = (arrays[1]-arrays[2])/scales[field]
            l1 = math.fsum(abs(x) for x in error.ravel())/4096
            assert abs(l1-report['measured']['orszag-tang_n128_j0.0_base']['reference_errors'][field]['L1']) < 2e-15
            lower, upper = min(a.min() for a in arrays), max(a.max() for a in arrays)
            cmap = 'magma' if family == 'gas' else 'RdBu_r'
            if family == 'magnetic':
                upper = max(abs(lower), abs(upper))
                lower = -upper
            for col, (array, title) in enumerate(zip(arrays, ('Candidate N64', 'Candidate N128', 'Athena++ N512'))):
                im = axes[row, col].imshow(array, origin='lower', extent=(0, 1, 0, 1),
                                           interpolation='nearest', cmap=cmap, vmin=lower, vmax=upper)
                axes[row, col].set_title(title)
            fig.colorbar(im, ax=axes[row, :3], label=labels[field], shrink=.85)
            limit = max(abs(error.min()), abs(error.max()), 1e-16)
            im = axes[row, 3].imshow(error, origin='lower', extent=(0, 1, 0, 1),
                                     interpolation='nearest', cmap='RdBu_r', vmin=-limit, vmax=limit)
            axes[row, 3].set_title(f'N128 − reference / scale\nL1 = {l1:.5f}', fontsize=10)
            fig.colorbar(im, ax=axes[row, 3], label='Normalized difference', shrink=.85)
            for axis in axes[row]:
                axis.set(xlabel='x', ylabel='y', xticks=[0, .5, 1], yticks=[0, .5, 1])
        fig.suptitle('Orszag–Tang at t=0.5 · regular mesh · hlld-pressure candidate\n'
                     'Independent raw-face rectangle integration into 64 × 64 comparison bins', fontsize=13)
        fig.supxlabel('Partial refinement evidence: N256, the complete boost ladder and full M1 acceptance remain pending.', fontsize=10)
        filename = f'pressure_vortex_refinement_{family}.png'
        fig.savefig(args.output/filename, dpi=150)
        plt.close(fig)
        outputs[filename] = digest(args.output/filename)
    provenance = dict(scope=__doc__, script_sha256=digest(Path(__file__)),
                      independent_reference_sha256=digest(args.archive/'independent_reference.json'),
                      independent_bins_sha256=digest(args.archive/'independent_bins.json.gz'),
                      reference_sha256=digest(reference_path),
                      matplotlib=matplotlib.__version__, numpy=np.__version__, backend='Agg',
                      figure_sha256=outputs)
    (args.archive/'plot_provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')


if __name__ == '__main__':
    main()
