#!/usr/bin/env python3
"""Independent closed-form G01 inputs/references; run each case only on REANA.

No candidate geometry module, generic clipping routine or candidate moments are
used. Exact rational Cartesian intervals and truncated-simplex inclusion/exclusion
give all moments. A coarea derivative gives the oblique shared-face moments.
The integer binary64 converter and rational radical enclosures are source for
independent review, not evidence of successful reference evaluation.
"""
import argparse
from functools import cmp_to_key
from fractions import Fraction
import hashlib
from itertools import product
import json
from math import comb, factorial, isqrt
from pathlib import Path
import re


DESIGN_SHA256 = '69fd92fc2009df207d076441527161825eb50ae911a2ec2a8e398d687306f288'
METHOD = 'exact-rounded-cartesian-and-box-cut-coarea-v1'
AXES = 'xyz'
PERMUTATIONS = ('xyz', 'xzy', 'yxz', 'yzx', 'zxy', 'zyx')
SCALES = ('1/1000000', '1', '1000000')
TRANSLATIONS = (('0', '0', '0'), ('371/1000', '-219/1000', '443/1000'))
FIXTURES = (
    'periodic_one_cell_self_images', 'periodic_cartesian_2x2x2',
    'periodic_nonuniform_3x2x2', 'periodic_cartesian_4x4x4',
    'periodic_nonuniform_4x4x4', 'bounded_one_cell_2x3x4',
    'bounded_oblique_bisector',
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def rational(text):
    require(type(text) is str and len(text) <= 4096
            and re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?', text),
            'Canonical rational input required')
    return Fraction(text)


def text(value):
    value = Fraction(value)
    return str(value.numerator) if value.denominator == 1 else str(value)


def nearest_integer(numerator, denominator):
    require(numerator >= 0 and denominator > 0, 'Positive rounding operands')
    integer, remainder = divmod(numerator, denominator)
    return integer + int(2 * remainder > denominator
                         or (2 * remainder == denominator and integer % 2 == 1))


def binary64_bits(value):
    """Round an exact rational once, nearest ties-to-even; reject infinity.

    This uses integer arithmetic, including gradual underflow and carry into
    the next exponent. It does not call float(), libm or the candidate decoder.
    Negative rationals that underflow retain the IEEE negative-zero sign.
    """
    value = Fraction(value)
    sign = (1 << 63) if value < 0 else 0
    numerator, denominator = abs(value.numerator), value.denominator
    if numerator == 0:
        return 0
    exponent = numerator.bit_length() - denominator.bit_length()
    if ((numerator < denominator << exponent) if exponent >= 0
            else (numerator << -exponent) < denominator):
        exponent -= 1
    if exponent < -1022:
        significand = nearest_integer(numerator << 1074, denominator)
        require(significand <= 1 << 52, 'Subnormal rounding range')
        return sign | significand
    shift = 52 - exponent
    significand = (nearest_integer(numerator << shift, denominator) if shift >= 0
                   else nearest_integer(numerator, denominator << -shift))
    if significand == 1 << 53:
        exponent += 1
        significand >>= 1
    require(-1022 <= exponent <= 1023 and (1 << 52) <= significand < (1 << 53),
            'Reference input/value is not finite binary64')
    return sign | ((exponent + 1023) << 52) | (significand - (1 << 52))


def exact_binary64(bits):
    """Decode finite bits to a rational; either zero decodes to exact zero."""
    require(type(bits) is int and 0 <= bits < 1 << 64, 'Binary64 word required')
    exponent, fraction = (bits >> 52) & 0x7ff, bits & ((1 << 52) - 1)
    require(exponent != 0x7ff, 'Nonfinite binary64 reference input')
    significand = fraction if exponent == 0 else (1 << 52) | fraction
    power = -1074 if exponent == 0 else exponent - 1023 - 52
    value = Fraction(significand << power) if power >= 0 else Fraction(significand, 1 << -power)
    return -value if bits >> 63 else value


def rounded(value):
    return exact_binary64(binary64_bits(value))


def word(value):
    return f'{binary64_bits(value):016x}'


def exact_record(value):
    value = Fraction(value)
    return {'kind': 'rational', 'value': text(value), 'nearest_binary64': word(value)}


def radical_record(factor, radicand):
    """Enclose factor*sqrt(radicand), and certify a unique rounded binary64.

    floor(sqrt(N/D)*2^k) = isqrt(floor(N*2^(2k)/D)). Rational roots are
    detected first, including exact rounding midpoints. For irrational roots
    both enclosing endpoints must round to the same finite word. The interval
    is independent evidence, not an error estimate inferred from two runs.
    """
    factor, radicand = Fraction(factor), Fraction(radicand)
    require(radicand >= 0, 'Nonnegative radical')
    nroot, droot = isqrt(radicand.numerator), isqrt(radicand.denominator)
    if factor == 0 or nroot * nroot == radicand.numerator and droot * droot == radicand.denominator:
        return exact_record(factor * Fraction(nroot, droot))
    for precision in (256, 512, 1024, 2048, 4096):
        shifted = radicand.numerator << (2 * precision)
        integer = isqrt(shifted // radicand.denominator)
        lower = factor * Fraction(integer, 1 << precision)
        upper = factor * Fraction(integer + 1, 1 << precision)
        if lower > upper:
            lower, upper = upper, lower
        lo_bits, hi_bits = binary64_bits(lower), binary64_bits(upper)
        if lo_bits == hi_bits:
            return {'kind': 'rational_times_sqrt', 'factor': text(factor),
                    'radicand': text(radicand), 'enclosure': [text(lower), text(upper)],
                    'sqrt_fraction_bits': precision, 'nearest_binary64': f'{lo_bits:016x}'}
    raise ValueError('Unresolved radical-to-binary64 rounding; no reference exported')


def vector_record(values):
    return [exact_record(value) for value in values]


def matrix_record(values):
    return [vector_record(row) for row in values]


def case_catalog():
    return [
        {'name': f'{fixture}__s{scale}__p{permutation}__t{translation}',
         'fixture': fixture, 'scale_index': scale, 'permutation': permutation,
         'translation_index': translation}
        for fixture in FIXTURES for scale in range(3)
        for permutation in PERMUTATIONS for translation in range(2)
    ]


def canonical_id(namespace, counter):
    require(0 <= namespace < 1 << 64 and 0 <= counter < 1 << 64, 'ID word range')
    return f'{namespace:016x}{counter:016x}'


def face_sort_key(key):
    if key['kind'] == 'interior':
        return (0, key['lo'], key['hi'], tuple(key['hi_image']))
    return (1, key['cell'], key['patch'])


def transform(fixture, selection):
    """Compose the registered transform exactly, then round each scalar once."""
    permutation = [AXES.index(axis) for axis in selection['permutation']]
    scale = rational(SCALES[selection['scale_index']])
    translation = [rational(t) for t in TRANSLATIONS[selection['translation_index']]]
    anchor = [rational(x) for x in fixture['domain']['anchor']]
    width = [rational(x) for x in fixture['domain']['width']]
    delta = [scale * width[permutation[a]] * translation[a] for a in range(3)]

    def point(values):
        return [rounded(scale * values[permutation[a]] + delta[a]) for a in range(3)]

    actual_anchor = point(anchor)
    actual_width = [rounded(scale * width[permutation[a]]) for a in range(3)]
    namespace = int(fixture['namespace_hex'], 16)
    generators = []
    original_indices = []
    if fixture.get('generator_rule') == 'tensor_product':
        axes = [[rational(x) for x in fixture['axes'][axis]['generators']] for axis in AXES]
        for iz in range(len(axes[2])):
            for iy in range(len(axes[1])):
                for ix in range(len(axes[0])):
                    position = point([axes[0][ix], axes[1][iy], axes[2][iz]])
                    generators.append({'id': canonical_id(namespace, len(generators) + 1),
                                       'position': position})
                    original_indices.append((ix, iy, iz))
        actual_axes = [
            [rounded(scale * value + delta[a]) for value in axes[permutation[a]]]
            for a in range(3)
        ]
        axis_indices = [tuple(index[p] for p in permutation) for index in original_indices]
    else:
        for generator in fixture['generators']:
            generators.append({'id': canonical_id(namespace, generator['counter']),
                               'position': point([rational(x) for x in generator['position']])})
        actual_axes, axis_indices = None, None
    for a in range(3):
        require(actual_width[a] > 0
                and rounded(actual_anchor[a] + actual_width[a]) > actual_anchor[a],
                'Rounded domain is not representable')
        for generator in generators:
            x = generator['position'][a]
            require(actual_anchor[a] < x < actual_anchor[a] + actual_width[a],
                    'Rounded fixture generator is not strictly inside its domain')
    return {'anchor': actual_anchor, 'width': actual_width,
            'periodic': fixture['domain']['kind'] == 'periodic_orthorhombic',
            'generators': generators, 'axes': actual_axes, 'axis_indices': axis_indices}


def box_monomial(widths, powers):
    value = Fraction(1)
    for width, power in zip(widths, powers):
        value *= width ** (power + 1) / (power + 1)
    return value


def cut_monomial(coefficients, widths, level, powers, derivative=False):
    """Integral t^powers over a box cut by sum(coeff_i*t_i)<=level.

    Shift u_i=coeff_i*t_i. Inclusion/exclusion shifts each violated upper
    bound by b_i=coeff_i*width_i, then expands only the low-degree monomial.
    Integral_simplex u^beta = prod(beta_i!)*H^(d+sum beta)/(d+sum beta)!.
    derivative=True differentiates in level, giving coarea-weighted moments.
    """
    dimension = len(widths)
    require(dimension in (2, 3) and len(coefficients) == len(powers) == dimension
            and all(c > 0 for c in coefficients) and all(w > 0 for w in widths)
            and sum(powers) <= 2 and all(type(p) is int and p >= 0 for p in powers),
            'Positive diagonal-cut moment domain')
    bounds = [c * w for c, w in zip(coefficients, widths)]
    integral = Fraction(0)
    for mask in product((0, 1), repeat=dimension):
        shifts = [bound * active for bound, active in zip(bounds, mask)]
        height = level - sum(shifts)
        if height <= 0:
            continue
        sign = -1 if sum(mask) % 2 else 1
        for beta in product(*(range(power + 1) for power in powers)):
            term = Fraction(sign)
            for alpha, degree, shift in zip(powers, beta, shifts):
                term *= comb(alpha, degree) * shift ** (alpha - degree) * factorial(degree)
            degree = dimension + sum(beta)
            term *= (height ** (degree - 1) / factorial(degree - 1) if derivative
                     else height ** degree / factorial(degree))
            integral += term
    jacobian = Fraction(1)
    for coefficient, power in zip(coefficients, powers):
        jacobian *= coefficient ** (power + 1)
    return integral / jacobian


def moments(widths, coefficients=None, level=None, derivative=False, complement=False):
    dimension = len(widths)

    def integral(powers):
        if coefficients is None:
            return box_monomial(widths, powers)
        value = cut_monomial(coefficients, widths, level, powers, derivative)
        require(not (derivative and complement), 'Complement derivative is not a positive surface measure')
        return box_monomial(widths, powers) - value if complement else value

    zero = (0,) * dimension
    volume = integral(zero)
    require(volume > 0, 'Required analytic cell/face must have positive measure')
    first = []
    second = [[Fraction(0) for _ in widths] for _ in widths]
    for a in range(dimension):
        powers = [0] * dimension
        powers[a] = 1
        first.append(integral(powers))
        for b in range(dimension):
            powers2 = [0] * dimension
            powers2[a] += 1
            powers2[b] += 1
            second[a][b] = integral(powers2)
    centroid = [value / volume for value in first]
    central = [[second[a][b] - first[a] * first[b] / volume
                for b in range(dimension)] for a in range(dimension)]
    return volume, centroid, central


def ordered_polygon(vertices, centroid, tangents, sign):
    """Order an analytically enumerated convex face by exact polar comparison.

    There is no clipping or hull construction. Projection tangent axes are
    cyclic, so sign fixes the outward normal and odd-permutation winding.
    """
    vertices = sorted(set(tuple(v) for v in vertices))
    require(len(vertices) >= 3, 'Required analytic face polygon is positive')
    a, b = tangents

    def compare(left, right):
        x, y = left[a] - centroid[a], left[b] - centroid[b]
        u, v = right[a] - centroid[a], right[b] - centroid[b]
        half_left = 0 if y > 0 or (y == 0 and x >= 0) else 1
        half_right = 0 if v > 0 or (v == 0 and u >= 0) else 1
        if half_left != half_right:
            return -1 if half_left < half_right else 1
        cross = x * v - y * u
        if cross != 0:
            return -1 if cross > 0 else 1
        return (left > right) - (left < right)

    vertices.sort(key=cmp_to_key(compare))
    if sign < 0:
        vertices.reverse()
    first = min(range(len(vertices)), key=vertices.__getitem__)
    return vertices[first:] + vertices[:first]


def plane_box_vertices(coefficients, widths, level):
    vertices = []
    for axis in range(3):
        other = [a for a in range(3) if a != axis]
        for sides in product((0, 1), repeat=2):
            point = [Fraction(0)] * 3
            for a, side in zip(other, sides):
                point[a] = widths[a] * side
            point[axis] = (level - sum(coefficients[a] * point[a] for a in other)) / coefficients[axis]
            if 0 <= point[axis] <= widths[axis]:
                vertices.append(point)
    return vertices


def wall_cut_vertices(coefficients, widths, level, complement):
    vertices = []
    for sides in product((0, 1), repeat=2):
        point = [w * side for w, side in zip(widths, sides)]
        value = sum(c * x for c, x in zip(coefficients, point))
        if (value >= level) if complement else (value <= level):
            vertices.append(point)
    for axis in range(2):
        other = 1 - axis
        for side in (0, 1):
            point = [Fraction(0)] * 2
            point[other] = widths[other] * side
            point[axis] = (level - coefficients[other] * point[other]) / coefficients[axis]
            if 0 <= point[axis] <= widths[axis]:
                vertices.append(point)
    return vertices


def cell_record(generator, volume, centroid, central, faces):
    return {'id': generator['id'], 'volume': exact_record(volume),
            'centroid_offset': vector_record([c - x for c, x in zip(centroid, generator['position'])]),
            'central_second_moment': matrix_record(central), 'incidences': faces}


def face_record(key, owner, area, centroid, normal, covariance, polygon):
    offset = [c - x for c, x in zip(centroid, owner['position'])]
    return {'key': key, 'area': area, 'centroid_offset': vector_record(offset),
            'normal': normal, 'covariance': matrix_record(covariance),
            'polygon_offset': [vector_record([x - g for x, g in zip(v, owner['position'])]) for v in polygon]}


def cartesian_reference(actual):
    generators, width, anchor = actual['generators'], actual['width'], actual['anchor']
    periodic = actual['periodic']
    if periodic:
        axes, indices = actual['axes'], actual['axis_indices']
        index_to_owner = {index: i for i, index in enumerate(indices)}
        intervals = []
        for axis, length in zip(axes, width):
            require(all(axis[i] < axis[i + 1] for i in range(len(axis) - 1)), 'Rounded axis collision/order')
            intervals.append([
                ((x + (axis[i - 1] if i else axis[-1] - length)) / 2,
                 (x + (axis[i + 1] if i + 1 < len(axis) else axis[0] + length)) / 2)
                for i, x in enumerate(axis)
            ])
    else:
        require(len(generators) == 1, 'Bounded Cartesian reference is one box')
        axes, indices, index_to_owner = None, [(0, 0, 0)], None
        intervals = [[(a, a + w)] for a, w in zip(anchor, width)]
    cells, faces = [], []
    for owner, (generator, index) in enumerate(zip(generators, indices)):
        bounds = [intervals[a][index[a]] for a in range(3)]
        widths = [high - low for low, high in bounds]
        volume, middle, central = moments(widths)
        centroid = [low + c for (low, _), c in zip(bounds, middle)]
        incidences = []
        for axis in range(3):
            b, c = (axis + 1) % 3, (axis + 2) % 3
            for side in (0, 1):
                sign = 2 * side - 1
                other, image = None, [0, 0, 0]
                if periodic:
                    neighbour = list(index)
                    neighbour[axis] += sign
                    count = len(axes[axis])
                    if neighbour[axis] < 0:
                        neighbour[axis], image[axis] = count - 1, -1
                    elif neighbour[axis] >= count:
                        neighbour[axis], image[axis] = 0, 1
                    other = index_to_owner[tuple(neighbour)]
                    neighbour_id = generators[other]['id']
                    forward = generator['id'] < neighbour_id or (other == owner and sign > 0)
                    key = {'kind': 'interior', 'lo': min(generator['id'], neighbour_id),
                           'hi': max(generator['id'], neighbour_id),
                           'hi_image': image if forward else [-x for x in image]}
                    incidence_sign = 1 if forward else -1
                else:
                    key = {'kind': 'boundary', 'cell': generator['id'], 'patch': 2 * axis + side}
                    incidence_sign, forward = 1, True
                incidences.append({'key': key, 'sign': incidence_sign,
                                   'owner_chart_centroid': vector_record([
                                       bounds[a][side] if a == axis else centroid[a] for a in range(3)])})
                if not forward:
                    continue
                face_centroid = list(centroid)
                face_centroid[axis] = bounds[axis][side]
                normal = [Fraction(sign if a == axis else 0) for a in range(3)]
                covariance = [[widths[a] ** 2 / 12 if a == d and a != axis else Fraction(0)
                               for d in range(3)] for a in range(3)]
                vertices = []
                for sb, sc in product((0, 1), repeat=2):
                    point = list(face_centroid)
                    point[b], point[c] = bounds[b][sb], bounds[c][sc]
                    vertices.append(point)
                polygon = ordered_polygon(vertices, face_centroid, (b, c), sign)
                faces.append(face_record(key, generator, exact_record(widths[b] * widths[c]),
                                         face_centroid, vector_record(normal), covariance, polygon))
        cells.append(cell_record(generator, volume, centroid, central, incidences))
    return cells, faces


def oblique_reference(actual):
    require(not actual['periodic'] and len(actual['generators']) == 2, 'Two bounded oblique sources')
    lower, upper = actual['generators']
    anchor, widths = actual['anchor'], actual['width']
    coefficients = [b - a for a, b in zip(lower['position'], upper['position'])]
    require(all(c > 0 for c in coefficients), 'Registered rounded oblique direction')
    level = sum((b * b - a * a) / 2 - c * origin
                for a, b, c, origin in zip(lower['position'], upper['position'], coefficients, anchor))
    n2 = sum(c * c for c in coefficients)
    shared = {'kind': 'interior', 'lo': lower['id'], 'hi': upper['id'], 'hi_image': [0, 0, 0]}
    surface_weight, middle, central_weight = moments(widths, coefficients, level, derivative=True)
    face_centroid = [a + c for a, c in zip(anchor, middle)]
    covariance = [[value / surface_weight for value in row] for row in central_weight]
    vertices = [[a + x for a, x in zip(anchor, vertex)]
                for vertex in plane_box_vertices(coefficients, widths, level)]
    polygon = ordered_polygon(vertices, face_centroid, (0, 1), 1)
    require(len(polygon) == 6, 'Registered oblique face must remain a hexagon')
    faces = [face_record(shared, lower, radical_record(surface_weight, n2), face_centroid,
                         [radical_record(c / n2, n2) for c in coefficients], covariance, polygon)]
    cells = []
    for complement, generator in enumerate((lower, upper)):
        volume, middle, central = moments(widths, coefficients, level, complement=bool(complement))
        centroid = [a + c for a, c in zip(anchor, middle)]
        incidences = [{'key': shared, 'sign': 1 if complement == 0 else -1,
                       'owner_chart_centroid': vector_record(face_centroid)}]
        for axis in range(3):
            tangents = ((axis + 1) % 3, (axis + 2) % 3)
            remaining_widths = [widths[a] for a in tangents]
            remaining_coefficients = [coefficients[a] for a in tangents]
            for side in (0, 1):
                fixed = widths[axis] * side
                face_level = level - coefficients[axis] * fixed
                area, cm, jc = moments(remaining_widths, remaining_coefficients, face_level,
                                       complement=bool(complement))
                cf = list(anchor)
                cf[axis] += fixed
                cov = [[Fraction(0) for _ in range(3)] for _ in range(3)]
                for i, a in enumerate(tangents):
                    cf[a] += cm[i]
                    for j, b in enumerate(tangents):
                        cov[a][b] = jc[i][j] / area
                wall_vertices = []
                for point2 in wall_cut_vertices(remaining_coefficients, remaining_widths,
                                                face_level, bool(complement)):
                    point3 = list(anchor)
                    point3[axis] += fixed
                    for a, coordinate in zip(tangents, point2):
                        point3[a] += coordinate
                    wall_vertices.append(point3)
                sign = 2 * side - 1
                polygon = ordered_polygon(wall_vertices, cf, tangents, sign)
                key = {'kind': 'boundary', 'cell': generator['id'], 'patch': 2 * axis + side}
                normal = [Fraction(sign if a == axis else 0) for a in range(3)]
                faces.append(face_record(key, generator, exact_record(area), cf,
                                         vector_record(normal), cov, polygon))
                incidences.append({'key': key, 'sign': 1, 'owner_chart_centroid': vector_record(cf)})
        cells.append(cell_record(generator, volume, centroid, central, incidences))
    return cells, faces


def evaluate_case(design_bytes, name):
    require(hashlib.sha256(design_bytes).hexdigest() == DESIGN_SHA256, 'Changed registered geometry design')
    design = json.loads(design_bytes)
    require(design['schema'] == 'openmhd.geometry3.analytic-design.v1', 'Design schema')
    families = design['transform_families']
    require(tuple(families['uniform_length_scales']) == SCALES
            and tuple(families['coordinate_permutations']) == PERMUTATIONS
            and tuple(tuple(t) for t in families['domain_and_points_translation_in_scaled_axis_lengths'])
            == TRANSLATIONS, 'Exact registered transformation family')
    selections = [case for case in case_catalog() if case['name'] == name]
    require(len(selections) == 1, 'One exact registered case name is required')
    selection = selections[0]
    fixtures = [fixture for fixture in design['fixtures'] if fixture['name'] == selection['fixture']]
    require(len(fixtures) == 1, 'Unique registered fixture')
    fixture = fixtures[0]
    actual = transform(fixture, selection)
    cells, faces = (oblique_reference(actual) if selection['fixture'] == 'bounded_oblique_bisector'
                    else cartesian_reference(actual))
    expected = fixture['expected']
    interior = sum(face['key']['kind'] == 'interior' for face in faces)
    require(len(cells) == expected['cells']
            and interior == expected['canonical_interior_faces']
            and len(faces) - interior == expected['boundary_face_fragments']
            and sum(len(cell['incidences']) for cell in cells) == expected['oriented_cell_incidences'],
            'Rounded problem changed the required registered positive topology')
    faces.sort(key=lambda face: face_sort_key(face['key']))
    for cell in cells:
        cell['incidences'].sort(key=lambda incidence: (face_sort_key(incidence['key']), -incidence['sign']))
    face_keys = [json.dumps(face['key'], sort_keys=True) for face in faces]
    require(len(face_keys) == len(set(face_keys)), 'Duplicate canonical reference face')
    inputs = {'schema': 'openmhd.geometry3.literal-input.v1', 'case': selection,
              'method': METHOD, 'design_sha256': DESIGN_SHA256,
              'scalar_encoding': '16 lowercase hexadecimal IEEE754 binary64 bits',
              'identity_encoding': '32 lowercase namespace-first EntityId hexadecimal digits',
              'domain': {'boundary': 'periodic' if actual['periodic'] else 'bounded',
                         'anchor_bits': [word(a) for a in actual['anchor']],
                         'width_bits': [word(w) for w in actual['width']]},
              'generators': [{'id': g['id'], 'position_bits': [word(x) for x in g['position']],
                              'winding': [0, 0, 0]} for g in actual['generators']]}
    reference = {'schema': 'openmhd.geometry3.exact-reference.v1', 'case': selection,
                 'method': METHOD, 'design_sha256': DESIGN_SHA256,
                 'target': 'Exact geometry of actual once-rounded binary64 inputs',
                 'candidate_invoked': False, 'component_accepted': False,
                 'Lref': exact_record(max(actual['width'])),
                 'registered_gates': design['gates'], 'cells': cells, 'faces': faces}
    return inputs, reference


def encode(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--design', type=Path, required=True)
    parser.add_argument('--case', required=True, choices=[case['name'] for case in case_catalog()])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    status = {'schema': 'openmhd.geometry3.reference-execution.v1', 'status': 'running',
              'case': args.case, 'candidate_invoked': False, 'component_accepted': False,
              'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (output / 'status.json').write_bytes(encode(status))
    try:
        raw = args.design.read_bytes()
        inputs, reference = evaluate_case(raw, args.case)
        input_bytes = encode(inputs)
        reference['input_sha256'] = hashlib.sha256(input_bytes).hexdigest()
        (output / 'input.json').write_bytes(input_bytes)
        (output / 'reference.json').write_bytes(encode(reference))
        require(args.design.read_bytes() == raw, 'Design changed during reference evaluation')
        status.update(status='complete', cells=len(reference['cells']), faces=len(reference['faces']))
    except BaseException as error:
        status.update(status='failed', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        (output / 'status.json').write_bytes(encode(status))
        (output / 'sha256.json').write_bytes(encode({
            path.name: {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}
            for path in sorted(output.iterdir()) if path.is_file() and path.name != 'sha256.json'
        }))


if __name__ == '__main__':
    main()
