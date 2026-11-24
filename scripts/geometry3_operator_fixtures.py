"""Exact manufactured inputs and analytic expectations for the 3D O01 gate.

Generate individual packets on REANA. No candidate, rank estimator or
least-squares implementation is imported.
"""
import argparse
from fractions import Fraction as Q
from itertools import product
from pathlib import Path

from galaxy_geometry3_reference import encode, word

# Published basis order. Each term gives its exponent triple and denominator.
TERMS = {
    'constant': ((0, 0, 0), 1),
    'x': ((1, 0, 0), 1), 'y': ((0, 1, 0), 1), 'z': ((0, 0, 1), 1),
    'xx_half': ((2, 0, 0), 2), 'yy_half': ((0, 2, 0), 2), 'zz_half': ((0, 0, 2), 2),
    'xy': ((1, 1, 0), 1), 'xz': ((1, 0, 1), 1), 'yz': ((0, 1, 1), 1),
}
AXES = 'xyz'
DESIGN_SHA256 = '32e5ed2af3097c8106896fcb262a751ee37fe06dbf927f510e03952b5826b4ac'


def derivative(term, position, axes=()):
    powers, denominator = TERMS[term]
    remaining = list(powers)
    coefficient = Q(1, denominator)
    for axis in axes:
        if not remaining[axis]:
            return Q(0)
        coefficient *= remaining[axis]
        remaining[axis] -= 1
    for value, exponent in zip(position, remaining):
        coefficient *= value**exponent
    return coefficient


def cross(a, b):
    return tuple(a[(i + 1) % 3] * b[(i + 2) % 3] - a[(i + 2) % 3] * b[(i + 1) % 3]
                 for i in range(3))


def words(values):
    return [word(v) for v in values]


def exact_rank(matrix):
    # Exact elimination checks the algebraic fixture, independently of weighted numerical QR.
    rows = [list(map(Q, row)) for row in matrix]
    rank = 0
    for col in range(len(rows[0])):
        pivot = next((j for j in range(rank, len(rows)) if rows[j][col]), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for j in range(rank + 1, len(rows)):
            factor = rows[j][col] / rows[rank][col]
            rows[j] = [x - factor * y for x, y in zip(rows[j], rows[rank])]
        rank += 1
    return rank


def catalog():
    cases = {}
    for layout in ('local_image', 'bounded_interior'):
        for fit in ('linear', 'quadratic'):
            basis = tuple(TERMS)[:4] if fit == 'linear' else tuple(TERMS)
            for term, axis in product(basis, AXES):
                cases['__'.join((layout, fit, term, axis))] = layout, fit, term, axis
    for layout, fit in (('plane', 'linear'), ('plane', 'quadratic'), ('shell', 'quadratic')):
        cases['__'.join((layout, fit, 'deficient'))] = layout, fit, None, None
    return cases


def cell_id(counter):
    return f'{0x4f3031:016x}{counter:016x}'


def layout_rows(layout, fit):
    if layout == 'bounded_interior':
        h = Q(1, 4)
        centre = (5 * h / 2,) * 3
        rows = []
        for i, j, k in product(range(5), repeat=3):
            index = (i - 2, j - 2, k - 2)
            ring = sum(map(abs, index))
            if 1 <= ring <= (1 if fit == 'linear' else 2):
                rows.append((cell_id((i*5 + j)*5 + k), tuple(h * x for x in index), ring))
        axis_centres = words((Q(2*i + 1, 2) * h for i in range(5)))
        mesh = dict(kind='bounded_cartesian', anchor_bits=words((0, 0, 0)),
                    width_bits=words((5*h,) * 3), axis_centres_bits=axis_centres,
                    owner_id=cell_id(62), namespace_hex=f'{0x4f3031:016x}',
                    id_counter='(ix * 5 + iy) * 5 + iz', dimensions=[5, 5, 5])
        return h, centre, rows, mesh
    h = Q(1, 8)
    centre = (Q(7, 8), Q(3, 8), Q(5, 8))
    rows = []
    indices = (product(range(-2, 3), range(-2, 3), (0,)) if layout == 'plane'
               else product((-1, 0, 1), repeat=3))
    for counter, (i, j, k) in enumerate(indices):
        if not any((i, j, k)):
            continue
        if layout == 'shell' and i*i + j*j + k*k != 2:
            continue
        if layout == 'local_image':
            delta = (h * (i + Q(j, 4)), h * (j + Q(k, 8)), h * (k + Q(i, 8)))
        else:
            delta = tuple(h * t for t in (i, j, k))
        rows.append((cell_id(counter), delta, None))
    mesh = dict(kind='synthetic_local_chart', anchor_bits=words((0, 0, 0)), width_bits=words((1, 1, 1)),
                owner_id=cell_id(12 if layout == 'plane' else 13))
    return h, centre, rows, mesh


def fixture(name):
    layout, fit, term, component = catalog()[name]
    h, centre, rows, mesh = layout_rows(layout, fit)
    basis = tuple(TERMS)[:4] if fit == 'linear' else tuple(TERMS)
    rank = exact_rank([[derivative(t, [d/h for d in delta]) for t in basis] for _, delta, _ in rows])
    expected_rank = {'plane': 3 if fit == 'linear' else 6, 'shell': 9}.get(layout, len(basis))
    if rank != expected_rank or len(rows) <= len(basis):
        raise ValueError('Unexpected exact rank or row count for registered stencil')
    samples = []
    for key, delta, ring in rows:
        position = tuple(x + d for x, d in zip(centre, delta))
        image = [x // 1 for x in position] if mesh['kind'] == 'synthetic_local_chart' else [0] * 3
        wrapped = [x - k for x, k in zip(position, image)]
        sample = dict(id=key, image=image, position_bits=words(wrapped), displacement_bits=words(delta))
        if ring is not None:
            sample['adjacency_ring'] = ring
        if fit == 'linear':
            sample['face_area_weight_bits'] = word(h*h)
        else:
            sample['distance_squared_bits'] = word(sum(d*d for d in delta))
        value = (derivative(term, position) if term is not None
                 else position[0] + 2 * position[1] + 3 * position[2])
        sample['scalar_bits'] = word(value)
        samples.append(sample)
    reference = dict(exact_design_rank=rank, columns=len(basis), rows=len(samples),
                     expected_fit='reproduce' if term else 'reject_rank_deficient')
    if term is not None:
        gradient = [derivative(term, centre, (a,)) for a in range(3)]
        hessian = [[derivative(term, centre, (a, b)) for b in range(3)] for a in range(3)]
        k = AXES.index(component)
        unit = [int(a == k) for a in range(3)]
        reference.update(value_bits=word(derivative(term, centre)), gradient_bits=words(gradient),
                         curl_A_bits=words(cross(gradient, unit)), div_A_bits=word(gradient[k]))
        if fit == 'quadratic':
            dcurl = [cross([hessian[a][b] for a in range(3)], unit) for b in range(3)]
            reference.update(hessian_bits=[words(row) for row in hessian],
                             curl_jacobian_bits=[words(row) for row in zip(*dcurl)],
                             div_B_same_fit_bits=word(sum(dcurl[a][a] for a in range(3))))
    return dict(schema='openmhd.geometry3.o01-manufactured-input.v1', gate='O01', design_sha256=DESIGN_SHA256,
                name=name, layout=layout, fit=fit, units='dimensionless', precision='IEEE 754 binary64',
                scalar=term or 'x+2y+3z', A_component=component, mesh=mesh,
                evaluation_position_bits=words(centre),
                cell_volume_bits=word(h**3), mean_B_bits=words((0, 0, 0)), samples=samples, expected=reference,
                weighting='face_area' if fit == 'linear' else 'inverse_distance',
                candidate_executed=False, component_accepted=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('selection', choices=('catalog', *catalog()))
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    packet = list(catalog()) if args.selection == 'catalog' else fixture(args.selection)
    with args.output.open('xb') as stream:
        stream.write(encode(packet))
