"""Written bridge controls, each to be executed separately on REANA.

The synthetic transcripts below contain deliberately degenerate zero polygons
and zero central moments. They are NONPHYSICAL grammar controls, never valid
geometry reference data or passing numerical-gate packets.
"""
import copy
import json
import unittest

import galaxy_geometry3_bridge as bridge


ZERO = '0000000000000000'
NEGZERO = '8000000000000000'
ONE = '3ff0000000000000'
NEGONE = 'bff0000000000000'
HALF = '3fe0000000000000'
ID = '00000000000000010000000000000001'


def inputs(periodic=False):
    fixture = 'periodic_one_cell_self_images' if periodic else 'bounded_one_cell_2x3x4'
    return {'schema': 'openmhd.geometry3.literal-input.v1', 'method': bridge.METHOD,
            'design_sha256': bridge.DESIGN_SHA256,
            'scalar_encoding': '16 lowercase hexadecimal IEEE754 binary64 bits',
            'identity_encoding': '32 lowercase namespace-first EntityId hexadecimal digits',
            'case': {'name': fixture + '__s1__pxyz__t0', 'fixture': fixture,
                     'scale_index': 1, 'permutation': 'xyz', 'translation_index': 0},
            'domain': {'boundary': 'periodic' if periodic else 'bounded',
                       'anchor_bits': [ZERO] * 3, 'width_bits': [ONE] * 3},
            'generators': [{'id': ID, 'position_bits': [HALF] * 3, 'winding': [0] * 3}]}


def encoded(value):
    return (json.dumps(value, indent=2) + '\n').encode()


def synthetic_transcript(periodic=False):
    """A complete, explicitly NONPHYSICAL structure-only control."""
    value = inputs(periodic)
    count = 3 if periodic else 6
    rows = ['openmhd-geometry3-candidate-v1', 'component_accepted false', 'status complete',
            'case ' + value['case']['name'], 'epoch 1',
            'domain ' + value['domain']['boundary'] + ' ' + ' '.join([ZERO] * 3 + [ONE] * 3),
            'counts 1 ' + str(count), 'input_generator ' + ID + ' ' + ' '.join([HALF] * 3 + ['0'] * 3),
            'cell ' + ' '.join([ID, ONE, *([ZERO] * 12), ONE, ONE, HALF, '6'])]
    if periodic:
        # Full self-image keys are in canonical lexicographic image order.
        for index, axis in enumerate((2, 1, 0)):
            for sign in (1, -1):
                image = [sign if a == axis else 0 for a in range(3)]
                translation = [NEGONE if a == axis and sign == -1 else ZERO for a in range(3)]
                rows.append('incidence ' + ' '.join([ID, str(index), str(sign), 'some', ID,
                                                    *(str(x) for x in image), *translation]))
    else:
        for index in range(6):
            rows.append('incidence ' + ' '.join([ID, str(index), '1', 'none', *([ZERO] * 3)]))
    for index in range(count):
        axis = (2, 1, 0)[index] if periodic else index // 2
        sign = 1 if periodic or index % 2 else -1
        image = [1 if periodic and a == axis else 0 for a in range(3)]
        key = (['some', '0', 'interior', ID, ID, *(str(x) for x in image)] if periodic
               else ['none', 'boundary', ID, str(index)])
        # Keep normal construction explicit; the synthetic polygons stay zero.
        normal = [(ONE if sign == 1 else NEGONE) if a == axis else ZERO for a in range(3)]
        metrics = [ONE, *normal, *([ZERO] * 3), HALF, *([ZERO] * 9)]
        rows.append('face ' + ' '.join([str(index), '0', *key, *(str(x) for x in image), *metrics, '4']))
        for ordinal in range(4):
            rows.append('vertex ' + ' '.join([str(index), str(ordinal), *([ZERO] * 3)]))
    rows.extend(['quality ' + ' '.join([ZERO] * 4 + ['0', '6', '1']), 'end'])
    return ('\n'.join(rows) + '\n').encode()


class GeometryBridgeStructureTests(unittest.TestCase):
    def test_input_conversion_preserves_words_axes_ids_and_order(self):
        value = inputs()
        value['generators'][0]['position_bits'] = [NEGZERO, '0000000000000001', HALF]
        raw = encoded(value)
        converted = bridge.convert_input(raw)
        self.assertIn(('generator ' + ID + ' ' + NEGZERO + ' 0000000000000001 ' + HALF + ' 0 0 0\n').encode(), converted)
        self.assertTrue(converted.endswith(b'\nend\n'))
        self.assertEqual(bridge.parse_input(raw), value)

    def test_two_generators_are_never_sorted_by_the_converter(self):
        value = inputs()
        other = copy.deepcopy(value['generators'][0])
        other['id'] = '00000000000000000000000000000002'
        value['generators'].append(other)
        rows = bridge.convert_input(encoded(value)).decode().splitlines()
        generator_rows = [row for row in rows if row.startswith('generator ')]
        self.assertEqual([row.split()[1] for row in generator_rows], [ID, other['id']])

    def test_duplicate_json_fields_and_extra_schema_fields_are_rejected(self):
        raw = encoded(inputs()).replace(b'"method":', b'"method":"duplicate", "method":', 1)
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON field'):
            bridge.parse_input(raw)
        value = inputs()
        value['component_accepted'] = True
        with self.assertRaisesRegex(ValueError, 'Exact fields: literal input'):
            bridge.parse_input(encoded(value))

    def test_nonfinite_uppercase_and_wrong_width_words_are_rejected(self):
        for word in ('7ff0000000000000', 'fff0000000000000', '7ff8000000000001',
                     '3FF0000000000000', '0x3ff0000000000000', '0'):
            value = inputs()
            value['domain']['width_bits'][0] = word
            with self.subTest(word=word), self.assertRaises(ValueError):
                bridge.convert_input(encoded(value))
        for word in (ZERO, NEGZERO, NEGONE):
            value = inputs()
            value['domain']['width_bits'][0] = word
            with self.subTest(word=word), self.assertRaisesRegex(ValueError, 'Strictly positive'):
                bridge.convert_input(encoded(value))

    def test_duplicate_ids_bool_indices_and_wrong_windings_are_rejected(self):
        value = inputs()
        value['generators'].append(copy.deepcopy(value['generators'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate generator ID'):
            bridge.parse_input(encoded(value))
        for invalid in (True, 1.0, '1'):
            value = inputs()
            value['case']['scale_index'] = invalid
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, 'Bounded integer'):
                bridge.parse_input(encoded(value))
        for invalid in ([True, 0, 0], [1, 0, 0], [0, 0], [1 << 63, 0, 0]):
            value = inputs()
            value['generators'][0]['winding'] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                bridge.parse_input(encoded(value))

    def test_case_identity_and_input_resource_bounds_are_enforced(self):
        value = inputs()
        value['case']['name'] += '_changed'
        with self.assertRaisesRegex(ValueError, 'Exact registered case label'):
            bridge.parse_input(encoded(value))
        with self.assertRaisesRegex(ValueError, 'Bounded input JSON bytes'):
            bridge.parse_input(b' ' * (bridge.MAX_JSON_BYTES + 1))
        value = inputs()
        value['generators'] = []
        with self.assertRaisesRegex(ValueError, 'Bounded generator count'):
            bridge.parse_input(encoded(value))

    def test_complete_bounded_structure_retains_no_acceptance_or_gate_claim(self):
        result = bridge.parse_transcript(synthetic_transcript(), encoded(inputs()))
        self.assertEqual(len(result['cells']), 1)
        self.assertEqual(len(result['faces']), 6)
        self.assertEqual([face['key']['patch'] for face in result['faces']], list(range(6)))
        self.assertEqual(len(result['cells'][0]['incidences']), 6)
        self.assertIs(result['numeric_gates_evaluated'], False)
        self.assertIs(result['execution_provenance_verified'], False)
        self.assertIs(result['component_accepted'], False)

    def test_periodic_self_faces_retain_both_signed_image_incidences(self):
        result = bridge.parse_transcript(synthetic_transcript(True), encoded(inputs(True)))
        self.assertEqual(len(result['faces']), 3)
        self.assertEqual(len(result['cells'][0]['incidences']), 6)
        for index in range(3):
            used = [incidence for incidence in result['cells'][0]['incidences'] if incidence['face'] == index]
            self.assertEqual([entry['sign'] for entry in used], [1, -1])
            self.assertEqual(used[0]['neighbour']['image'], [-x for x in used[1]['neighbour']['image']])
            self.assertEqual(result['faces'][index]['left'], result['faces'][index]['right'])

    def test_partial_extra_and_noncanonical_transcript_rows_are_rejected(self):
        raw = synthetic_transcript()
        bad = (raw[:-1], raw.replace(b'\nend\n', b'\n'), raw + b'extra\n',
               raw.replace(b'epoch 1\n', b'epoch  1\n'), raw.replace(b'epoch 1\n', b'epoch\t1\n'),
               raw.replace(b'epoch 1\n', b'epoch 1\n\n'))
        for candidate in bad:
            with self.subTest(candidate=candidate[:80]), self.assertRaises(ValueError):
                bridge.parse_transcript(candidate, encoded(inputs()))

    def test_changed_actual_echo_is_rejected_without_coordinate_recomposition(self):
        raw = synthetic_transcript()
        changed = raw.replace(('input_generator ' + ID + ' ' + HALF).encode(),
                              ('input_generator ' + ID + ' ' + ONE).encode(), 1)
        with self.assertRaisesRegex(ValueError, 'Exact echoed input generator'):
            bridge.parse_transcript(changed, encoded(inputs()))
        changed = raw.replace(b'domain bounded ' + ZERO.encode(), b'domain bounded ' + NEGZERO.encode(), 1)
        with self.assertRaisesRegex(ValueError, 'Exact echoed domain words'):
            bridge.parse_transcript(changed, encoded(inputs()))

    def test_nonfinite_metric_and_negative_or_zero_positive_metric_are_rejected(self):
        raw = synthetic_transcript()
        for word in ('7ff8000000000001', ZERO, NEGZERO, NEGONE):
            changed = raw.replace(('cell ' + ID + ' ' + ONE).encode(),
                                  ('cell ' + ID + ' ' + word).encode(), 1)
            with self.subTest(word=word), self.assertRaises(ValueError):
                bridge.parse_transcript(changed, encoded(inputs()))

    def test_missing_duplicate_and_unknown_face_uses_cannot_close(self):
        raw = synthetic_transcript()
        duplicate = raw.replace(('incidence ' + ID + ' 1 1').encode(),
                                ('incidence ' + ID + ' 0 1').encode(), 1)
        with self.assertRaisesRegex(ValueError, 'Once-only face incidence closure'):
            bridge.parse_transcript(duplicate, encoded(inputs()))
        outside = raw.replace(('incidence ' + ID + ' 0 1').encode(),
                              ('incidence ' + ID + ' 6 1').encode(), 1)
        with self.assertRaisesRegex(ValueError, 'Bounded integer value'):
            bridge.parse_transcript(outside, encoded(inputs()))

    def test_wrong_reciprocal_neighbour_image_is_not_hidden_by_owner_id(self):
        raw = synthetic_transcript(True)
        old = 'incidence ' + ID + ' 0 -1 some ' + ID + ' 0 0 -1 '
        new = 'incidence ' + ID + ' 0 -1 some ' + ID + ' 0 0 1 '
        with self.assertRaisesRegex(ValueError, 'Reciprocal full-image incidence identity'):
            bridge.parse_transcript(raw.replace(old.encode(), new.encode(), 1), encoded(inputs(True)))

    def test_key_wrap_and_boundary_patch_invariants_are_enforced(self):
        raw = synthetic_transcript(True)
        old = 'interior ' + ID + ' ' + ID + ' 0 0 1 0 0 1 '
        new = 'interior ' + ID + ' ' + ID + ' 0 0 1 0 0 0 '
        with self.assertRaisesRegex(ValueError, 'Registered zero-winding face image'):
            bridge.parse_transcript(raw.replace(old.encode(), new.encode(), 1), encoded(inputs(True)))
        raw = synthetic_transcript()
        bad = raw.replace(('boundary ' + ID + ' 0 ').encode(), ('boundary ' + ID + ' 6 ').encode(), 1)
        with self.assertRaisesRegex(ValueError, 'Bounded integer value'):
            bridge.parse_transcript(bad, encoded(inputs()))

    def test_vertex_ordinal_and_declared_cell_count_are_exact(self):
        raw = synthetic_transcript()
        with self.assertRaisesRegex(ValueError, 'Exact vertex row inventory'):
            bridge.parse_transcript(raw.replace(b'vertex 0 1 ', b'vertex 0 0 ', 1), encoded(inputs()))
        with self.assertRaisesRegex(ValueError, 'Every input generator has one cell'):
            bridge.parse_transcript(raw.replace(b'counts 1 6\n', b'counts 2 6\n', 1), encoded(inputs()))

    def test_epoch_scope_and_output_byte_bound_are_fail_closed(self):
        raw = synthetic_transcript()
        for replacement in (b'epoch 0', b'epoch 01', b'epoch +1', b'epoch 18446744073709551616'):
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                bridge.parse_transcript(raw.replace(b'epoch 1', replacement, 1), encoded(inputs()))
        with self.assertRaisesRegex(ValueError, 'Nonaccepting transcript'):
            bridge.parse_transcript(raw.replace(b'component_accepted false', b'component_accepted true', 1), encoded(inputs()))
        with self.assertRaisesRegex(ValueError, 'Bounded transcript bytes'):
            bridge.parse_transcript(b'x' * (bridge.MAX_OUTPUT_BYTES + 1), encoded(inputs()))
