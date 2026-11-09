#!/usr/bin/env python3
"""Numerical representability audit of exported derivatives; never alters gates."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def product(a, b):
    # Explicit contraction avoids the platform BLAS matmul path and lets this
    # audit independently check the exported rows with finite arithmetic.
    with np.errstate(all='raise'):
        result = np.einsum('ij,jk->ik', a, b, optimize=False)
    if not np.isfinite(result).all():
        raise ValueError('Nonfinite matrix product')
    return result


def audit(directory, nx, jitter, stencil, normal):
    start = time.monotonic()
    stem = f'n{nx}_j{jitter}'
    cells_path = directory/f'{stem}_cells.csv'
    matrix_path = directory/f'{stem}_{stencil}.csv'
    cells = rows(cells_path)
    count = len(cells)
    dx, dy = np.zeros((2, count, count))
    for r in rows(matrix_path):
        i, j = int(r['row']), int(r['column'])
        dx[i, j] += float(r['dx'])
        dy[i, j] += float(r['dy'])
    # Orthonormal Helmert basis: columns span the complement of constant A.
    gauge = np.zeros((count, count-1))
    for k in range(1, count):
        scale = math.sqrt(k*(k+1))
        gauge[:k, k-1] = 1/scale
        gauge[k, k-1] = -k/scale
    weight = np.sqrt([float(c['volume']) for c in cells])[:, None]
    normal = np.array(normal, dtype=float)
    normal /= np.linalg.norm(normal)
    perpendicular = weight * (normal[0]*dy-normal[1]*dx)
    parallel = weight * (normal[0]*dx+normal[1]*dy)
    a = product(perpendicular, gauge)
    b = product(parallel, gauge)
    u, singular, vt = np.linalg.svd(a, full_matrices=False)
    tolerance = 128*np.finfo(float).eps*max(a.shape)*singular[0]
    rank = int(np.count_nonzero(singular > tolerance))
    backward = float(np.linalg.norm(a-product(u*singular, vt)))
    orthogonal = float(np.linalg.norm(product(gauge.T, gauge)-np.eye(count-1)))
    constant = max(float(np.max(np.abs(dx.sum(axis=1)))), float(np.max(np.abs(dy.sum(axis=1)))))
    if backward > 1e-10*np.linalg.norm(a) or orthogonal > 1e-10 or constant > 1e-9:
        raise ValueError('Matrix/gauge/SVD consistency check failed')
    result = dict(nx=nx, ny=4, jitter=float(jitter), stencil=stencil, normal=normal.tolist(),
                  unknowns=count-1, rank=rank, singular_max=float(singular[0]),
                  singular_min=float(singular[-1]), rank_tolerance=float(tolerance),
                  backward_frobenius_residual=backward, gauge_orthogonality_error=orthogonal,
                  constant_annihilation_max=constant)
    if rank == count-1:
        # B A^+ = B V S^-1 U^T; U has orthonormal columns, preserving this norm.
        gain = product(b, vt.T) / singular
        bound = float(np.linalg.svd(gain, compute_uv=False)[0])
        result.update(parallel_over_perpendicular_bound=bound,
                      maximum_parallel_RMS_if_normal_max_1e_8=bound*1e-8)
    else:
        null_parallel = product(b, vt[rank:].T)
        result['parallel_response_on_numerical_normal_nullspace'] = float(np.linalg.norm(null_parallel))
    result['seconds'] = time.monotonic()-start
    result['input_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in [cells_path, matrix_path]}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh report path')
    report = dict(scope='Independent numerical rank/bound audit, not a rigorous interval proof or M1 acceptance.',
                  numpy_version=np.__version__, checks=[])
    for nx in [16, 32, 64, 256]:
        for jitter in ['0', '0.15']:
            for stencil in ['affine', 'quadratic']:
                for normal in ([[1, 0], [0, 1], [1, 1]] if nx == 32 else [[1, 0]]):
                    r = audit(args.directory, nx, jitter, stencil, normal)
                    report['checks'].append(r)
                    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
                    print(nx, jitter, stencil, normal, 'rank', r['rank'], '/', r['unknowns'],
                          'K', r.get('parallel_over_perpendicular_bound'), flush=True)


if __name__ == '__main__':
    main()
