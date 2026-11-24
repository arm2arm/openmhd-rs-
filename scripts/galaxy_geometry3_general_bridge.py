"""Lossless transport for the separately registered general M2a geometry campaign.

No candidate/reference module is imported. No floating-point arithmetic is used.
All new tests and invocations must run on REANA after independent source review.
This module cannot establish a numerical gate or execution provenance by itself.
"""
from collections import Counter
import hashlib
import json
import re


DESIGN_SHA256 = 'd4c847974422e0d74a2a8cbbbfb65e6702540d9fb0c8f0d38b549a48873692d8'
METHOD = 'm2a-certified-dual-halfspace-v1'
MAX_INPUT_BYTES = 128 * 1024
MAX_JSON_BYTES = 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_CELLS = 512
MAX_FACES = 16384
MAX_INCIDENCES = 32768
MAX_FACE_VERTICES = 4096
FIXTURES = (
    'periodic_one_cell_self_images', 'periodic_cartesian_2x2x2',
    'periodic_nonuniform_3x2x2', 'periodic_cartesian_4x4x4',
    'periodic_nonuniform_4x4x4', 'bounded_one_cell_2x3x4',
    'bounded_oblique_bisector',
)


def require(value, message):
    if not value:
        raise ValueError(message)


def keys(value, expected, label):
    require(type(value) is dict and set(value) == set(expected), 'Exact fields: ' + label)


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'Duplicate JSON field')
        value[key] = item
    return value


def reject_constant(_value):
    raise ValueError('Nonfinite JSON constant')


def finite_word(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{16}', value) is not None,
            'Canonical finite binary64 word')
    require((int(value, 16) >> 52) & 0x7ff != 0x7ff, 'Nonfinite binary64 word')
    return value


def positive_word(value):
    finite_word(value)
    bits = int(value, 16)
    require(0 < bits < 1 << 63, 'Strictly positive binary64 word')
    return value


def zero_word(value):
    finite_word(value)
    return int(value, 16) & ((1 << 63) - 1) == 0


def persistent_id(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{32}', value) is not None,
            'Canonical persistent ID')
    return value


def integer_value(value, lower, upper):
    require(type(value) is int and lower <= value <= upper, 'Bounded integer value')
    return value


def integer_text(value, lower, upper):
    require(type(value) is str and len(value) <= 21
            and re.fullmatch(r'0|-?[1-9][0-9]*', value) is not None,
            'Canonical integer text')
    return integer_value(int(value), lower, upper)


def triple(value, validator):
    require(type(value) is list and len(value) == 3, 'Three-axis vector')
    return [validator(item) for item in value]


def image_value(value):
    return triple(value, lambda x: integer_value(x, -(1 << 63), (1 << 63) - 1))


def parse_input(raw):
    require(type(raw) is bytes and len(raw) <= MAX_JSON_BYTES, 'Bounded input JSON bytes')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object,
                       parse_constant=reject_constant)
    keys(value, ('schema', 'case', 'method', 'design_sha256', 'scalar_encoding',
                 'identity_encoding', 'domain', 'generators'), 'literal input')
    require(value['schema'] == 'openmhd.geometry3.general-input.v1'
            and value['method'] == METHOD and value['design_sha256'] == DESIGN_SHA256,
            'Registered input identity')
    require(value['scalar_encoding'] == '16 lowercase hexadecimal IEEE754 binary64 bits'
            and value['identity_encoding'] == '32 lowercase namespace-first EntityId hexadecimal digits',
            'Registered input encoding')
    case = value['case']
    keys(case, ('name',), 'general case')
    require(type(case['name']) is str and re.fullmatch('[a-z0-9_]{1,160}', case['name']),
            'Canonical general-case label')
    domain = value['domain']
    keys(domain, ('boundary', 'anchor_bits', 'width_bits'), 'domain')
    require(domain['boundary'] in ('periodic', 'bounded'), 'Boundary kind')
    triple(domain['anchor_bits'], finite_word)
    triple(domain['width_bits'], positive_word)
    generators = value['generators']
    require(type(generators) is list and 1 <= len(generators) <= MAX_CELLS, 'Bounded generator count')
    seen = set()
    for generator in generators:
        keys(generator, ('id', 'position_bits', 'winding'), 'generator')
        persistent_id(generator['id'])
        require(generator['id'] not in seen, 'Duplicate generator ID')
        seen.add(generator['id'])
        triple(generator['position_bits'], finite_word)
        image_value(generator['winding'])
    return value


def convert_input(raw):
    """Preserve every supplied word, identity, axis and generator order."""
    value = parse_input(raw)
    domain = value['domain']
    rows = ['openmhd-geometry3-input-v1', 'case ' + value['case']['name'],
            'boundary ' + domain['boundary'], 'anchor ' + ' '.join(domain['anchor_bits']),
            'width ' + ' '.join(domain['width_bits']), 'count ' + str(len(value['generators']))]
    for generator in value['generators']:
        rows.append('generator ' + ' '.join([generator['id'], *generator['position_bits'],
                                            *(str(x) for x in generator['winding'])]))
    rows.append('end')
    converted = ('\n'.join(rows) + '\n').encode('ascii')
    require(len(converted) <= MAX_INPUT_BYTES, 'Bounded converted input')
    return converted


class Rows:
    def __init__(self, raw):
        require(type(raw) is bytes and len(raw) <= MAX_OUTPUT_BYTES, 'Bounded transcript bytes')
        require(raw.isascii() and raw.endswith(b'\n'), 'Complete ASCII transcript newline')
        self.rows = raw.decode('ascii').split('\n')[:-1]
        require(all(row and not any(c.isspace() and c != ' ' for c in row)
                    and all(row.split(' ')) for row in self.rows), 'Canonical transcript rows')
        self.index = 0

    def row(self, name, fields=None):
        require(self.index < len(self.rows), 'Truncated transcript')
        row = self.rows[self.index].split(' ')
        self.index += 1
        require(row[0] == name and (fields is None or len(row) == fields + 1),
                'Exact row: ' + name)
        return row[1:]


class Fields:
    def __init__(self, values):
        self.values = values
        self.index = 0

    def take(self):
        require(self.index < len(self.values), 'Truncated row fields')
        value = self.values[self.index]
        self.index += 1
        return value

    def number(self, lower, upper):
        return integer_text(self.take(), lower, upper)

    def identity(self):
        return persistent_id(self.take())

    def word(self):
        return finite_word(self.take())

    def words(self, count):
        return [self.word() for _ in range(count)]

    def image(self):
        return [self.number(-(1 << 63), (1 << 63) - 1) for _ in range(3)]

    def finish(self):
        require(self.index == len(self.values), 'Trailing row fields')


def face_key(fields):
    kind = fields.take()
    if kind == 'interior':
        lo, hi, image = fields.identity(), fields.identity(), fields.image()
        require(lo <= hi, 'Canonical face owner order')
        if lo == hi:
            require(any(image) and next(x for x in image if x) > 0, 'Positive canonical self image')
        return {'kind': kind, 'lo': lo, 'hi': hi, 'hi_image': image}
    require(kind == 'boundary', 'Face key kind')
    return {'kind': kind, 'cell': fields.identity(), 'patch': fields.number(0, 5)}


def key_tuple(key):
    if key['kind'] == 'interior':
        return 0, key['lo'], key['hi'], tuple(key['hi_image'])
    return 1, key['cell'], key['patch']


def parse_transcript(raw, input_bytes):
    """Decode complete structure; this does not prove a successful command or gate."""
    inputs = parse_input(input_bytes)
    generators = inputs['generators']
    ids = sorted(generator['id'] for generator in generators)
    winding = {g['id']: g['winding'] for g in generators}
    rows = Rows(raw)
    rows.row('openmhd-geometry3-candidate-v1', 0)
    require(rows.row('component_accepted', 1) == ['false'], 'Nonaccepting transcript')
    require(rows.row('status', 1) == ['complete'], 'Complete candidate status')
    require(rows.row('case', 1) == [inputs['case']['name']], 'Exact echoed case')
    epoch = integer_text(rows.row('epoch', 1)[0], 1, (1 << 64) - 1)
    domain = inputs['domain']
    require(rows.row('domain', 7) == [domain['boundary'], *domain['anchor_bits'], *domain['width_bits']],
            'Exact echoed domain words')
    counts = rows.row('counts', 2)
    ncells = integer_text(counts[0], 1, MAX_CELLS)
    nfaces = integer_text(counts[1], 1, MAX_FACES)
    require(ncells == len(generators), 'Every input generator has one cell')
    for generator in generators:
        require(rows.row('input_generator', 7) == [generator['id'], *generator['position_bits'],
                                                  *(str(x) for x in generator['winding'])],
                'Exact echoed input generator order and words')
    cells, total_incidences = [], 0
    for expected_id in ids:
        row = rows.row('cell', 18)
        require(row[0] == expected_id, 'Exact sorted persistent cell inventory')
        words = [finite_word(w) for w in row[1:17]]
        for index in (0, 13, 14, 15):
            positive_word(words[index])
        count = integer_text(row[17], 1, MAX_INCIDENCES)
        total_incidences += count
        require(total_incidences <= MAX_INCIDENCES, 'Bounded total incidences')
        incidences = []
        for _ in range(count):
            fields = Fields(rows.row('incidence'))
            require(fields.identity() == expected_id, 'Incidence owner row')
            index, sign = fields.number(0, nfaces - 1), fields.number(-1, 1)
            require(sign in (-1, 1), 'Nonzero incidence sign')
            kind = fields.take()
            neighbour = None
            if kind == 'some':
                neighbour = {'id': fields.identity(), 'image': fields.image()}
            else:
                require(kind == 'none', 'Incidence neighbour kind')
            translation = fields.words(3)
            fields.finish()
            incidences.append({'face': index, 'sign': sign, 'neighbour': neighbour,
                               'chart_translation_bits': translation})
        cells.append({'id': expected_id, 'volume_bits': words[0],
                      'centroid_offset_bits': words[1:4],
                      'central_second_moment_bits': [words[4 + 3*a:7 + 3*a] for a in range(3)],
                      'surface_area_bits': words[13], 'bounding_radius_bits': words[14],
                      'minimum_generator_face_distance_bits': words[15], 'incidences': incidences})
    faces = []
    for index in range(nfaces):
        fields = Fields(rows.row('face'))
        require(fields.number(0, nfaces - 1) == index, 'Sequential face index')
        left = fields.number(0, ncells - 1)
        kind = fields.take()
        right = None
        if kind == 'some':
            right = fields.number(0, ncells - 1)
        else:
            require(kind == 'none', 'Right cell kind')
        key = face_key(fields)
        wrapped = fields.image()
        values = fields.words(17)
        positive_word(values[0])
        positive_word(values[7])
        count = fields.number(3, MAX_FACE_VERTICES)
        fields.finish()
        vertices = []
        for ordinal in range(count):
            fields = Fields(rows.row('vertex', 5))
            require(fields.number(0, nfaces - 1) == index
                    and fields.number(0, MAX_FACE_VERTICES - 1) == ordinal, 'Exact vertex row inventory')
            vertices.append(fields.words(3))
            fields.finish()
        if key['kind'] == 'interior':
            require(right is not None and ids[left] == key['lo'] and ids[right] == key['hi'],
                    'Interior face persistent owners')
            require(all(-1 <= x <= 1 for x in wrapped) and
                    key['hi_image'] == [wrapped[a] + winding[key['lo']][a] - winding[key['hi']][a] for a in range(3)],
                    'Full trajectory image and local wrapped chart')
            if domain['boundary'] == 'bounded':
                require(wrapped == [0, 0, 0], 'Bounded interior image')
        else:
            require(domain['boundary'] == 'bounded' and right is None and ids[left] == key['cell']
                    and wrapped == [0, 0, 0], 'Physical boundary face owner and image')
        faces.append({'key': key, 'left': left, 'right': right, 'right_wrapped_image': wrapped,
                      'area_bits': values[0], 'normal_bits': values[1:4],
                      'centroid_offset_bits': values[4:7], 'plane_distance_bits': values[7],
                      'covariance_bits': [values[8 + 3*a:11 + 3*a] for a in range(3)],
                      'polygon_offset_bits': vertices})
    keys_in_order = [key_tuple(face['key']) for face in faces]
    require(keys_in_order == sorted(set(keys_in_order)), 'Unique sorted complete face/image keys')
    usages = [[] for _ in faces]
    for cell in cells:
        for incidence in cell['incidences']:
            index, sign = incidence['face'], incidence['sign']
            face, key = faces[index], faces[index]['key']
            neighbour = incidence['neighbour']
            if key['kind'] == 'boundary':
                require(sign == 1 and cell['id'] == key['cell'] and neighbour is None,
                        'Boundary incidence identity')
            else:
                owner = key['lo'] if sign == 1 else key['hi']
                other = key['hi'] if sign == 1 else key['lo']
                image = key['hi_image'] if sign == 1 else [-x for x in key['hi_image']]
                require(cell['id'] == owner and neighbour == {'id': other, 'image': image},
                        'Reciprocal full-image incidence identity')
            if sign == 1:
                require(all(zero_word(w) for w in incidence['chart_translation_bits']),
                        'Canonical left chart translation is zero')
            usages[index].append((cell['id'], sign))
    for face, used in zip(faces, usages):
        key = face['key']
        expected = ([(key['cell'], 1)] if key['kind'] == 'boundary'
                    else [(key['lo'], 1), (key['hi'], -1)])
        require(Counter(used) == Counter(expected), 'Once-only face incidence closure')
    quality = Fields(rows.row('quality', 7))
    quality_words = quality.words(4)
    for value in quality_words:
        require(int(value, 16) < 1 << 63 or zero_word(value), 'Nonnegative quality observation')
    counters = [quality.number(0, (1 << 64) - 1) for _ in range(3)]
    quality.finish()
    rows.row('end', 0)
    require(rows.index == len(rows.rows), 'No trailing transcript rows')
    return {'schema': 'openmhd.geometry3.decoded-candidate.v1', 'case': inputs['case'],
            'input_sha256': hashlib.sha256(input_bytes).hexdigest(),
            'protocol_sha256': hashlib.sha256(convert_input(input_bytes)).hexdigest(),
            'transcript_sha256': hashlib.sha256(raw).hexdigest(), 'epoch': epoch,
            'domain': domain, 'input_generators': generators, 'cells': cells, 'faces': faces,
            'quality_bits': quality_words, 'quality_counters': counters,
            'numeric_gates_evaluated': False, 'execution_provenance_verified': False,
            'component_accepted': False}
