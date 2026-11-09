#!/usr/bin/env python3
"""Independent 70-digit normal-equation check of exported worst-cell affine fits."""
import argparse
import csv
from decimal import Decimal, localcontext
import json
import math
from pathlib import Path


def solve(matrix, rhs):
    """Small pivoted elimination; deliberately separate from production covariance algebra."""
    a = [list(row) + [b] for row, b in zip(matrix, rhs)]
    for k in range(len(rhs)):
        pivot = max(range(k, len(rhs)), key=lambda i: abs(a[i][k]))
        a[k], a[pivot] = a[pivot], a[k]
        if not a[k][k]:
            raise ValueError('Singular independent fit')
        divisor = a[k][k]
        a[k] = [v/divisor for v in a[k]]
        for i in range(len(rhs)):
            if i != k:
                factor = a[i][k]
                a[i] = [x-factor*y for x, y in zip(a[i], a[k])]
    return [row[-1] for row in a]


def fit(rows):
    with localcontext() as context:
        context.prec = 70
        convert = lambda value: Decimal.from_float(float(value))
        matrix = [[Decimal(0) for _ in range(3)] for _ in range(3)]
        rhs = [Decimal(0) for _ in range(3)]
        for row in rows:
            x = [Decimal(1), convert(row['dx']), convert(row['dy'])]
            weight, value = convert(row['area']), convert(row['az'])
            if not weight.is_finite() or weight <= 0 or not all(v.is_finite() for v in [*x, value]):
                raise ValueError('Invalid independent fit samples')
            for j in range(3):
                rhs[j] += weight*x[j]*value
                for k in range(3):
                    matrix[j][k] += weight*x[j]*x[k]
        return solve(matrix, rhs)


def check(directory):
    with (directory/'summary.csv').open() as stream:
        summary = list(csv.DictReader(stream))
    expected = {(n, j, f) for n in (256, 512, 1024) for j in (0., .15) for f in ('brio', 'smooth')}
    actual = [(int(r['nx']), float(r['jitter']), r['field']) for r in summary]
    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError('Incomplete or duplicate reconstruction audit')
    results = []
    for row in summary:
        for field, tolerance in [('decomposition_max_error', 2e-10),
                                 ('affine_max_error', 2e-10), ('constant_max_error', 1e-14)]:
            value = float(row[field])
            if not math.isfinite(value) or not 0 <= value <= tolerance:
                raise ValueError(f'Invalid reconstruction control: {field}={value}')
        stem = f'n{row["nx"]}_j{row["jitter"]}_{row["field"]}'
        with (directory/'cells'/f'{stem}_worst.csv').open() as stream:
            samples = list(csv.DictReader(stream))
        intercept, gx, gy = fit(samples)
        errors = [abs(float(gx)-float(row['worst_gx'])), abs(float(gy)-float(row['worst_gy']))]
        passed = all(e <= 1e-10*(1+abs(float(row[f'worst_g{k}']))) for e, k in zip(errors, ('x', 'y')))
        results.append(dict(nx=int(row['nx']), jitter=float(row['jitter']), field=row['field'],
                            cell=int(row['worst_cell']), high_precision_fit=list(map(str, (intercept, gx, gy))),
                            absolute_gradient_difference=errors, passed=passed))
    if not all(r['passed'] for r in results):
        raise ValueError('Production and independent fits disagree')
    return dict(decimal_precision=70, checks=results, all_fits_agree=True,
                scope='Initial reconstruction agreement only; does not certify physical accuracy or M1 acceptance.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    result = check(args.directory)
    (args.directory/'independent_fits.json').write_text(json.dumps(result, indent=2)+'\n')
    print(f'All {len(result["checks"])} independent 70-digit fits agree with the implemented derivatives.')


if __name__ == '__main__':
    main()
