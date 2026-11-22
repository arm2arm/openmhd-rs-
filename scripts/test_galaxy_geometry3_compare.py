"""Source-only exact-error controls, each requiring its own REANA workflow.

These scalar/vector arithmetic controls create no complete physical packet,
candidate execution, generated reference or geometry acceptance.
"""
from fractions import Fraction as Q
import unittest

import galaxy_geometry3_compare as comparison


def rational_record(value, word='0000000000000000'):
    return {'kind': 'rational', 'value': value, 'nearest_binary64': word}


def radical_record(factor='1', bounds=('1', '3/2')):
    return {'kind': 'rational_times_sqrt', 'factor': factor, 'radicand': '2',
            'enclosure': list(bounds), 'sqrt_fraction_bits': 256,
            'nearest_binary64': '3ff6a09e667f3bcd'}


class GeometryComparisonArithmeticTests(unittest.TestCase):
    def test_exact_candidate_words_include_both_zeros_and_gradual_underflow(self):
        pairs = (('0000000000000000', Q(0)), ('8000000000000000', Q(0)),
                 ('3ff0000000000000', Q(1)), ('bfe0000000000000', Q(-1, 2)),
                 ('0000000000000001', Q(1, 1 << 1074)),
                 ('0010000000000000', Q(1, 1 << 1022)),
                 ('7fefffffffffffff', Q(((1 << 53) - 1) << 971)))
        for word, expected in pairs:
            self.assertEqual(comparison.candidate_word(word), expected)

    def test_nonfinite_words_never_enter_error_arithmetic(self):
        for word in ('7ff0000000000000', 'fff0000000000000', '7ff8000000000001'):
            with self.subTest(word=word), self.assertRaisesRegex(ValueError, 'Nonfinite'):
                comparison.candidate_word(word)

    def test_rational_text_is_reduced_canonical_and_bounded(self):
        self.assertEqual(comparison.rational('-3/2'), Q(-3, 2))
        for value in ('2/2', '-0', '+1', '01', '0/2', '1/0', '1 /2', '1e-10'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                comparison.rational(value)
        with self.assertRaises(ValueError):
            comparison.rational('1' * (comparison.MAX_RATIONAL_CHARS + 1))

    def test_rounded_reference_word_never_replaces_the_exact_target(self):
        # Deliberately different observational nearest word is ignored by the
        # error calculation. Whole-reference source/provenance validation is
        # still a separate requirement, not attested by this scalar control.
        target = comparison.interval(rational_record('1/3'))
        self.assertEqual(target, (Q(1, 3), Q(1, 3)))
        self.assertEqual(comparison.absolute_error(Q(0), target), (Q(1, 3), Q(1, 3)))

    def test_positive_and_negative_radical_enclosures_are_proven_by_squares(self):
        self.assertEqual(comparison.interval(radical_record()), (Q(1), Q(3, 2)))
        negative = radical_record('-1', ('-3/2', '-1'))
        self.assertEqual(comparison.interval(negative), (Q(-3, 2), Q(-1)))
        for record in (radical_record('1', ('3/2', '2')), radical_record('1', ('1/2', '1')),
                       radical_record('-1', ('1', '3/2')), radical_record('1', ('3/2', '1'))):
            with self.subTest(record=record), self.assertRaises(ValueError):
                comparison.interval(record)

    def test_reference_scalar_schema_and_precision_are_strict(self):
        record = radical_record()
        record['sqrt_fraction_bits'] = True
        with self.assertRaisesRegex(ValueError, 'Bounded integer value'):
            comparison.interval(record)
        record = rational_record('1')
        record['extra'] = 'ignored would be unsafe'
        with self.assertRaisesRegex(ValueError, 'Exact fields'):
            comparison.interval(record)
        with self.assertRaisesRegex(ValueError, 'Exact rational reference required'):
            comparison.exact(radical_record())

    def test_error_bounds_cover_inside_and_outside_interval_without_midpoint_substitution(self):
        target = Q(1), Q(2)
        self.assertEqual(comparison.absolute_error(Q(3, 2), target), (Q(0), Q(1, 2)))
        self.assertEqual(comparison.absolute_error(Q(0), target), (Q(1), Q(2)))
        self.assertEqual(comparison.absolute_error(Q(3), target), (Q(1), Q(2)))

    def test_positive_interval_normalization_uses_lower_bound_for_upper_error(self):
        self.assertEqual(comparison.divide_positive((Q(1), Q(2)), (Q(3), Q(4))),
                         (Q(1, 4), Q(2, 3)))
        for denominator in ((Q(0), Q(1)), (Q(-1), Q(1)), (Q(2), Q(1))):
            with self.subTest(denominator=denominator), self.assertRaisesRegex(ValueError, 'Independently positive'):
                comparison.divide_positive((Q(0), Q(1)), denominator)

    def test_gate_boundary_is_inclusive_and_crossing_enclosures_remain_unresolved(self):
        limit = Q(1, 10)
        self.assertEqual(comparison.verdict((Q(0), limit), limit), 'pass')
        self.assertEqual(comparison.verdict((Q(11, 100), Q(1)), limit), 'fail')
        self.assertEqual(comparison.verdict((limit, Q(11, 100)), limit), 'unresolved')
        self.assertEqual(comparison.verdict((Q(9, 100), Q(11, 100)), limit), 'unresolved')

    def test_euclidean_centroid_gate_is_not_an_axiswise_maximum(self):
        zero = [rational_record('0')] * 3
        bounds = comparison.vector_error_squared([Q(1, 10), Q(1, 10), Q(0)], zero)
        self.assertEqual(bounds, (Q(1, 50), Q(1, 50)))
        self.assertEqual(comparison.verdict(bounds, Q(1, 100)), 'fail')

    def test_vector_bounds_preserve_radical_uncertainty_before_squaring(self):
        records = [radical_record(), rational_record('0'), rational_record('0')]
        bounds = comparison.vector_error_squared([Q(0), Q(0), Q(0)], records)
        self.assertEqual(bounds, (Q(1), Q(9, 4)))
        self.assertEqual(comparison.verdict(bounds, Q(2)), 'unresolved')

    def test_complete_face_keys_keep_image_direction_and_self_sign(self):
        identity = '00000000000000010000000000000001'
        positive = {'kind': 'interior', 'lo': identity, 'hi': identity, 'hi_image': [0, 0, 1]}
        self.assertEqual(comparison.reference_key(positive), (0, identity, identity, (0, 0, 1)))
        negative = dict(positive, hi_image=[0, 0, -1])
        with self.assertRaisesRegex(ValueError, 'Reference canonical owners'):
            comparison.reference_key(negative)
        for patch in (-1, 6, True):
            key = {'kind': 'boundary', 'cell': identity, 'patch': patch}
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                comparison.reference_key(key)
