"""Unadopted G01 comparison arithmetic; run only on REANA after review.

Compare exact binary64 candidate values to retained rational/algebraic bounds.
No float/libm or candidate geometry algorithm is used. This is an arithmetic
result for supplied bytes, never execution-provenance or component acceptance.
"""
from collections import Counter
from fractions import Fraction as Q
import hashlib
import json
import re

import galaxy_geometry3_bridge as bridge


MAX_REFERENCE_BYTES = 16 * 1024 * 1024
MAX_RATIONAL_CHARS = 4096
GATE = '1/10000000000'
NUMERIC_GATES = (
    'cell_volume_relative_max', 'cell_centroid_max_over_Lref',
    'positive_face_area_relative_max', 'face_centroid_max_over_Lref',
    'unit_normal_max_component_error',
    'central_moment_max_over_expected_V_Lref_squared',
    'normal_closure_norm_over_cell_surface', 'volume_closure_relative',
)
require = bridge.require


def rational(value):
    require(type(value) is str and len(value) <= MAX_RATIONAL_CHARS
            and re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?', value) is not None,
            'Canonical bounded reference rational')
    result = Q(value)
    require(value == text(result), 'Reduced canonical reference rational')
    return result


def text(value):
    return (str(value.numerator) if value.denominator == 1
            else str(value.numerator) + '/' + str(value.denominator))


def candidate_word(word):
    """Exact IEEE binary64 interpretation; no rounded host float conversion."""
    bridge.finite_word(word)
    bits = int(word, 16)
    exponent = (bits >> 52) & 0x7ff
    significand = bits & ((1 << 52) - 1)
    if exponent:
        significand |= 1 << 52
    power = exponent - 1075 if exponent else -1074
    value = (Q(significand << power) if power >= 0
             else Q(significand, 1 << -power))
    return -value if bits >> 63 else value


def interval(record):
    require(type(record) is dict, 'Reference scalar record')
    if record.get('kind') == 'rational':
        bridge.keys(record, ('kind', 'value', 'nearest_binary64'), 'rational record')
        bridge.finite_word(record['nearest_binary64'])
        value = rational(record['value'])
        return value, value
    bridge.keys(record, ('kind', 'factor', 'radicand', 'enclosure',
                         'sqrt_fraction_bits', 'nearest_binary64'), 'radical record')
    require(record['kind'] == 'rational_times_sqrt', 'Reference scalar kind')
    bridge.finite_word(record['nearest_binary64'])
    factor, radicand = rational(record['factor']), rational(record['radicand'])
    bridge.integer_value(record['sqrt_fraction_bits'], 1, 4096)
    require(type(record['enclosure']) is list and len(record['enclosure']) == 2,
            'Two radical enclosure endpoints')
    lower, upper = map(rational, record['enclosure'])
    square = factor * factor * radicand
    require(factor != 0 and radicand > 0 and lower <= upper, 'Signed positive-radicand enclosure')
    if factor > 0:
        require(0 <= lower <= upper and lower * lower <= square <= upper * upper,
                'Positive radical enclosure proof')
    else:
        require(lower <= upper <= 0 and upper * upper <= square <= lower * lower,
                'Negative radical enclosure proof')
    return lower, upper


def exact(record):
    lower, upper = interval(record)
    require(lower == upper, 'Exact rational reference required')
    return lower


def absolute_error(actual, target):
    lower, upper = target
    require(lower <= upper, 'Ordered reference enclosure')
    return max(lower - actual, actual - upper, Q(0)), max(abs(actual - lower), abs(actual - upper))


def divide_positive(bounds, denominator):
    lower, upper = bounds
    dlo, dhi = denominator
    require(0 <= lower <= upper and 0 < dlo <= dhi, 'Independently positive normalization')
    return lower / dhi, upper / dlo


def verdict(bounds, limit):
    lower, upper = bounds
    require(0 <= lower <= upper and limit >= 0, 'Nonnegative error bounds and gate')
    return 'pass' if upper <= limit else 'fail' if lower > limit else 'unresolved'


def vector_error_squared(actual, reference):
    require(len(actual) == len(reference) == 3, 'Three-axis error vector')
    bounds = [absolute_error(a, interval(r)) for a, r in zip(actual, reference)]
    return sum((lo * lo for lo, _ in bounds), Q(0)), sum((hi * hi for _, hi in bounds), Q(0))


def scalar_vector(records):
    require(type(records) is list and len(records) == 3, 'Three-axis reference vector')
    return [interval(record) for record in records]


def reference_key(value):
    require(type(value) is dict and value.get('kind') in ('interior', 'boundary'), 'Reference face key')
    if value['kind'] == 'interior':
        bridge.keys(value, ('kind', 'lo', 'hi', 'hi_image'), 'reference interior key')
        bridge.persistent_id(value['lo'])
        bridge.persistent_id(value['hi'])
        image = bridge.image_value(value['hi_image'])
        require(value['lo'] <= value['hi'] and (value['lo'] != value['hi']
                or any(image) and next(x for x in image if x) > 0), 'Reference canonical owners')
    else:
        bridge.keys(value, ('kind', 'cell', 'patch'), 'reference boundary key')
        bridge.persistent_id(value['cell'])
        bridge.integer_value(value['patch'], 0, 5)
    return bridge.key_tuple(value)


def compare(input_bytes, reference_bytes, transcript_bytes, design_bytes):
    require(type(design_bytes) is bytes and hashlib.sha256(design_bytes).hexdigest() == bridge.DESIGN_SHA256,
            'Exact registered design bytes')
    design = json.loads(design_bytes, object_pairs_hook=bridge.unique_object,
                        parse_constant=bridge.reject_constant)
    require(all(design['gates'].get(name) == GATE for name in NUMERIC_GATES), 'Unchanged eight numeric gates')
    inputs = bridge.parse_input(input_bytes)
    candidate = bridge.parse_transcript(transcript_bytes, input_bytes)
    require(type(reference_bytes) is bytes and len(reference_bytes) <= MAX_REFERENCE_BYTES,
            'Bounded reference bytes')
    reference = json.loads(reference_bytes, object_pairs_hook=bridge.unique_object,
                           parse_constant=bridge.reject_constant)
    bridge.keys(reference, ('schema', 'case', 'method', 'design_sha256', 'target',
                           'candidate_invoked', 'component_accepted', 'Lref', 'registered_gates',
                           'cells', 'faces', 'input_sha256'), 'reference packet')
    require(reference['schema'] == 'openmhd.geometry3.exact-reference.v1'
            and reference['method'] == bridge.METHOD and reference['case'] == inputs['case']
            and reference['design_sha256'] == bridge.DESIGN_SHA256
            and reference['input_sha256'] == hashlib.sha256(input_bytes).hexdigest()
            and reference['target'] == 'Exact geometry of actual once-rounded binary64 inputs'
            and reference['registered_gates'] == design['gates']
            and reference['candidate_invoked'] is False and reference['component_accepted'] is False,
            'Actual-input reference identity and unchanged gates')
    widths = [candidate_word(w) for w in inputs['domain']['width_bits']]
    length = exact(reference['Lref'])
    require(length == max(widths) and length > 0, 'Fixed independently positive Lref')
    volume_box = widths[0] * widths[1] * widths[2]
    require(type(reference['cells']) is list and len(reference['cells']) == len(candidate['cells'])
            and type(reference['faces']) is list and len(reference['faces']) == len(candidate['faces']),
            'Exact reference cell/positive-face counts')
    rcells, rfaces = {}, {}
    for cell in reference['cells']:
        bridge.keys(cell, ('id', 'volume', 'centroid_offset', 'central_second_moment', 'incidences'), 'reference cell')
        identity = bridge.persistent_id(cell['id'])
        require(identity not in rcells, 'Unique reference cell')
        rcells[identity] = cell
    for face in reference['faces']:
        bridge.keys(face, ('key', 'area', 'centroid_offset', 'normal', 'covariance', 'polygon_offset'), 'reference face')
        key = reference_key(face['key'])
        require(key not in rfaces, 'Unique reference face')
        rfaces[key] = face
    require(set(rcells) == {c['id'] for c in candidate['cells']}
            and set(rfaces) == {bridge.key_tuple(f['key']) for f in candidate['faces']},
            'Exact full persistent-cell/face-image reference inventory')
    require(sum((exact(c['volume']) for c in rcells.values()), Q(0)) == volume_box,
            'Independent reference volume covers actual rounded domain')
    observations = {name: [] for name in NUMERIC_GATES}
    tolerance = rational(GATE)

    def record(name, label, bounds, squared=False):
        limit = tolerance * tolerance if squared else tolerance
        observations[name].append({'item': label, 'lower': text(bounds[0]), 'upper': text(bounds[1]),
                                   'norm': 'squared normalized Euclidean' if squared else 'normalized absolute',
                                   'threshold': text(limit), 'verdict': verdict(bounds, limit)})

    generator_by_id = {g['id']: g for g in inputs['generators']}
    total_candidate_volume = Q(0)
    for cell in candidate['cells']:
        identity, ref = cell['id'], rcells[cell['id']]
        expected_volume = exact(ref['volume'])
        require(expected_volume > 0, 'Positive expected cell volume')
        actual_volume = candidate_word(cell['volume_bits'])
        total_candidate_volume += actual_volume
        record('cell_volume_relative_max', identity,
               divide_positive(absolute_error(actual_volume, (expected_volume, expected_volume)),
                               (expected_volume, expected_volume)))
        record('cell_centroid_max_over_Lref', identity,
               divide_positive(vector_error_squared([candidate_word(w) for w in cell['centroid_offset_bits']],
                                                    ref['centroid_offset']), (length * length, length * length)), True)
        require(type(ref['central_second_moment']) is list and len(ref['central_second_moment']) == 3,
                'Reference central tensor rows')
        for a in range(3):
            require(type(ref['central_second_moment'][a]) is list and len(ref['central_second_moment'][a]) == 3,
                    'Reference central tensor columns')
            for b in range(3):
                denominator = expected_volume * length * length
                bounds = absolute_error(candidate_word(cell['central_second_moment_bits'][a][b]),
                                        interval(ref['central_second_moment'][a][b]))
                record('central_moment_max_over_expected_V_Lref_squared', identity + ':' + str(a) + str(b),
                       divide_positive(bounds, (denominator, denominator)))
        incidences = {}
        for incidence in ref['incidences']:
            bridge.keys(incidence, ('key', 'sign', 'owner_chart_centroid'), 'reference incidence')
            key = reference_key(incidence['key'])
            require(type(incidence['sign']) is int and incidence['sign'] in (-1, 1), 'Reference incidence sign')
            compound = key, incidence['sign']
            require(compound not in incidences, 'No duplicate reference incidence')
            scalar_vector(incidence['owner_chart_centroid'])
            incidences[compound] = incidence
        actual_uses = [(bridge.key_tuple(candidate['faces'][i['face']]['key']), i['sign']) for i in cell['incidences']]
        require(Counter(actual_uses) == Counter(incidences.keys()), 'Exact signed reference incidence inventory')
        normal_sum = [Q(0), Q(0), Q(0)]
        surface_lower = surface_upper = Q(0)
        owner_position = [candidate_word(w) for w in generator_by_id[identity]['position_bits']]
        for incidence in cell['incidences']:
            face = candidate['faces'][incidence['face']]
            key = bridge.key_tuple(face['key'])
            ref_face = rfaces[key]
            lower, upper = interval(ref_face['area'])
            require(lower > 0, 'Independently positive face area enclosure')
            surface_lower += lower
            surface_upper += upper
            area = candidate_word(face['area_bits'])
            for axis in range(3):
                normal_sum[axis] += incidence['sign'] * area * candidate_word(face['normal_bits'][axis])
            centroid = [owner_position[a] + candidate_word(face['centroid_offset_bits'][a])
                        + candidate_word(incidence['chart_translation_bits'][a]) for a in range(3)]
            target = incidences[(key, incidence['sign'])]['owner_chart_centroid']
            record('face_centroid_max_over_Lref', identity + ':incidence:' + str(incidence['face']) + ':' + str(incidence['sign']),
                   divide_positive(vector_error_squared(centroid, target), (length * length, length * length)), True)
        squared = sum((x * x for x in normal_sum), Q(0))
        record('normal_closure_norm_over_cell_surface', identity,
               divide_positive((squared, squared), (surface_lower * surface_lower, surface_upper * surface_upper)), True)
    for index, face in enumerate(candidate['faces']):
        ref = rfaces[bridge.key_tuple(face['key'])]
        area = interval(ref['area'])
        record('positive_face_area_relative_max', str(index),
               divide_positive(absolute_error(candidate_word(face['area_bits']), area), area))
        record('face_centroid_max_over_Lref', 'canonical:' + str(index),
               divide_positive(vector_error_squared([candidate_word(w) for w in face['centroid_offset_bits']],
                                                    ref['centroid_offset']), (length * length, length * length)), True)
        scalar_vector(ref['normal'])
        for axis in range(3):
            record('unit_normal_max_component_error', str(index) + ':' + str(axis),
                   absolute_error(candidate_word(face['normal_bits'][axis]), interval(ref['normal'][axis])))
    residual = abs(total_candidate_volume - volume_box) / volume_box
    record('volume_closure_relative', 'all cells', (residual, residual))
    require(all(observations[name] for name in NUMERIC_GATES), 'Every named numeric gate has observations')
    gate_verdicts = {name: ('fail' if any(o['verdict'] == 'fail' for o in values)
                          else 'unresolved' if any(o['verdict'] == 'unresolved' for o in values) else 'pass')
                     for name, values in observations.items()}
    return {'schema': 'openmhd.geometry3.exact-error-comparison.proposal.v1', 'case': inputs['case'],
            'input_sha256': hashlib.sha256(input_bytes).hexdigest(),
            'reference_sha256': hashlib.sha256(reference_bytes).hexdigest(),
            'transcript_sha256': hashlib.sha256(transcript_bytes).hexdigest(),
            'gate_verdicts': gate_verdicts, 'observations': observations,
            'numeric_gates_evaluated': True, 'execution_provenance_verified': False,
            'component_accepted': False,
            'unregistered_metrics': ['face covariance', 'polygon metric and orientation', 'radius and plane distance'],
            'scope': 'Arithmetic on supplied bytes only; requires independent source/norm review, actual command/source/binary/reference provenance and per-case output review'}
