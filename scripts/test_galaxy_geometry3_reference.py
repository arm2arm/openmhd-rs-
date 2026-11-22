"""Independent-reference arithmetic controls; execute each method only on REANA.

No candidate geometry is imported or evaluated. The exact constants below come
from integer rounding rules and the manually reviewed analytic fixture formulas.
These written assertions have not been executed by creating this file.
"""
from fractions import Fraction as Q
from pathlib import Path
import unittest

import galaxy_geometry3_reference as reference


DESIGN = Path(__file__).resolve().parents[1] / 'docs/galaxy/fixtures/geometry3_analytic_v1.json'


class GeometryReferenceArithmeticTests(unittest.TestCase):
    def test_exact_binary64_words_and_finite_decoding(self):
        controls = ((Q(0), 0), (Q(1), 0x3ff0000000000000),
                    (Q(-1), 0xbff0000000000000), (Q(2), 0x4000000000000000),
                    (Q(1, 2), 0x3fe0000000000000),
                    (Q(1, 1 << 1022), 0x0010000000000000))
        for value, bits in controls:
            with self.subTest(bits=f'{bits:016x}'):
                self.assertEqual(reference.binary64_bits(value), bits)
                self.assertEqual(reference.exact_binary64(bits), value)
        self.assertEqual(reference.binary64_bits(Q(1, 10)), 0x3fb999999999999a)
        self.assertEqual(reference.exact_binary64(0x8000000000000000), 0)

    def test_midpoint_ties_choose_even_significand_and_carry(self):
        controls = ((Q(1) + Q(1, 1 << 53), 0x3ff0000000000000),
                    (Q(1) + Q(3, 1 << 53), 0x3ff0000000000002),
                    (Q(2) - Q(1, 1 << 53), 0x4000000000000000))
        for value, bits in controls:
            self.assertEqual(reference.binary64_bits(value), bits)
            self.assertEqual(reference.binary64_bits(-value), bits | (1 << 63))

    def test_gradual_underflow_and_minimum_normal_midpoint(self):
        self.assertEqual(reference.binary64_bits(Q(1, 1 << 1074)), 1)
        self.assertEqual(reference.binary64_bits(Q(1, 1 << 1075)), 0)
        self.assertEqual(reference.binary64_bits(Q(-1, 1 << 1075)), 1 << 63)
        self.assertEqual(reference.binary64_bits(Q(3, 1 << 1075)), 2)
        self.assertEqual(reference.binary64_bits(Q((1 << 52) - 1, 1 << 1074)), (1 << 52) - 1)
        midpoint = Q(1, 1 << 1022) - Q(1, 1 << 1075)
        self.assertEqual(reference.binary64_bits(midpoint), 1 << 52)

    def test_largest_finite_and_infinite_rounding_boundary(self):
        largest = Q(((1 << 53) - 1) << 971)
        self.assertEqual(reference.binary64_bits(largest), 0x7fefffffffffffff)
        self.assertEqual(reference.exact_binary64(0x7fefffffffffffff), largest)
        for value in (largest + (1 << 970), -(largest + (1 << 970))):
            with self.assertRaisesRegex(ValueError, 'not finite'):
                reference.binary64_bits(value)
        for bits in (0x7ff0000000000000, 0xfff0000000000000, 0x7ff8000000000001):
            with self.assertRaisesRegex(ValueError, 'Nonfinite'):
                reference.exact_binary64(bits)

    def test_radical_enclosures_and_rational_roots(self):
        self.assertEqual(reference.radical_record(Q(3, 2), Q(4, 9)),
                         {'kind': 'rational', 'value': '1', 'nearest_binary64': '3ff0000000000000'})
        for factor in (Q(3, 4), Q(-3, 4)):
            result = reference.radical_record(factor, Q(3))
            lo, hi = map(Q, result['enclosure'])
            self.assertLess(lo, hi)
            target_squared = Q(27, 16)
            if factor > 0:
                self.assertLess(lo * lo, target_squared)
                self.assertGreater(hi * hi, target_squared)
            else:
                self.assertGreater(lo * lo, target_squared)
                self.assertLess(hi * hi, target_squared)
            self.assertEqual(f'{reference.binary64_bits(lo):016x}', result['nearest_binary64'])
            self.assertEqual(reference.binary64_bits(lo), reference.binary64_bits(hi))
        self.assertEqual(reference.radical_record(0, 3)['value'], '0')

    def test_oblique_volume_centroid_and_all_central_moments(self):
        volume, centroid, central = reference.moments([Q(1)] * 3, [Q(1)] * 3, Q(3, 2))
        self.assertEqual(volume, Q(1, 2))
        self.assertEqual(centroid, [Q(35, 96)] * 3)
        for a in range(3):
            for b in range(3):
                self.assertEqual(central[a][b], Q(599 if a == b else -169, 18432))

    def test_complement_oblique_moments_and_full_box_limit(self):
        widths = [Q(1)] * 3
        volume, centroid, central = reference.moments(widths, [Q(1)] * 3, Q(3, 2), complement=True)
        self.assertEqual(volume, Q(1, 2))
        self.assertEqual(centroid, [Q(61, 96)] * 3)
        self.assertEqual(central[0], [Q(599, 18432), Q(-169, 18432), Q(-169, 18432)])
        # General unequal positive coefficients with a level beyond the box.
        coefficients, widths = [Q(2), Q(3), Q(5)], [Q(2), Q(3), Q(4)]
        volume, centroid, central = reference.moments(widths, coefficients, Q(40))
        self.assertEqual(volume, 24)
        self.assertEqual(centroid, [Q(1), Q(3, 2), Q(2)])
        self.assertEqual(central, [[Q(8), Q(0), Q(0)], [Q(0), Q(18), Q(0)], [Q(0), Q(0), Q(32)]])

    def test_general_diagonal_simplex_before_first_upper_bound(self):
        coefficients = [Q(2), Q(3), Q(5)]
        level = Q(1, 2)
        widths = [Q(1)] * 3
        # All upper limits are inactive. Map to a tetrahedron of axis
        # intercepts h/c_i: V=h^3/(6*prod c), c_i-coordinate mean=h/(4*c_i).
        volume, centroid, central = reference.moments(widths, coefficients, level)
        self.assertEqual(volume, level ** 3 / 180)
        self.assertEqual(centroid, [level / (4 * c) for c in coefficients])
        for a in range(3):
            for b in range(3):
                factor = Q(3, 80) if a == b else Q(-1, 80)
                self.assertEqual(central[a][b], volume * factor * level ** 2 /
                                 (coefficients[a] * coefficients[b]))

    def test_coarea_hexagon_centroid_and_covariance(self):
        weight, centroid, central_weight = reference.moments(
            [Q(1)] * 3, [Q(1)] * 3, Q(3, 2), derivative=True)
        self.assertEqual(weight, Q(3, 4))
        self.assertEqual(centroid, [Q(1, 2)] * 3)
        # Six centre-to-edge triangles: E[r^2]=5/24. Symmetry and fixed
        # x+y+z give diagonal covariance5/72 and cross covariance-5/144.
        for a in range(3):
            for b in range(3):
                self.assertEqual(central_weight[a][b] / weight,
                                 Q(5, 72) if a == b else Q(-5, 144))

    def test_oblique_wall_square_triangle_and_complements(self):
        controls = ((Q(3, 2), False, Q(7, 8), Q(19, 42)),
                    (Q(1, 2), False, Q(1, 8), Q(1, 6)),
                    (Q(3, 2), True, Q(1, 8), Q(5, 6)),
                    (Q(1, 2), True, Q(7, 8), Q(23, 42)))
        for level, complement, expected_area, expected_centroid in controls:
            area, centroid, _ = reference.moments([Q(1)] * 2, [Q(1)] * 2, level,
                                                  complement=complement)
            self.assertEqual(area, expected_area)
            self.assertEqual(centroid, [expected_centroid] * 2)

    def test_registered_catalog_has_all252_unique_transformations(self):
        catalog = reference.case_catalog()
        self.assertEqual(len(catalog), 252)
        self.assertEqual(len({case['name'] for case in catalog}), 252)
        for fixture in reference.FIXTURES:
            entries = [case for case in catalog if case['fixture'] == fixture]
            self.assertEqual(len(entries), 36)
            self.assertEqual({(case['scale_index'], case['permutation'], case['translation_index'])
                              for case in entries},
                             {(s, p, t) for s in range(3) for p in reference.PERMUTATIONS for t in range(2)})

    def test_permutation_preserves_original_id_and_changes_all_domain_axes(self):
        import json
        design = json.loads(DESIGN.read_bytes())
        fixture = next(f for f in design['fixtures'] if f['name'] == 'bounded_one_cell_2x3x4')
        selection = {'scale_index': 1, 'permutation': 'yzx', 'translation_index': 0}
        actual = reference.transform(fixture, selection)
        self.assertEqual(actual['anchor'], [Q(-2), Q(-3), Q(-1)])
        self.assertEqual(actual['width'], [Q(3), Q(4), Q(2)])
        self.assertEqual(actual['generators'][0]['position'], [Q(-1), Q(0), Q(1, 4)])
        self.assertEqual(actual['generators'][0]['id'], '00000000000000060000000000000001')

    def test_complete_base_oblique_reference_has_independent_face_covariance(self):
        inputs, result = reference.evaluate_case(
            DESIGN.read_bytes(), 'bounded_oblique_bisector__s1__pxyz__t0')
        self.assertFalse(result['candidate_invoked'])
        self.assertFalse(result['component_accepted'])
        self.assertEqual(len(inputs['generators']), 2)
        self.assertEqual(len(result['faces']), 13)
        self.assertEqual([len(c['incidences']) for c in result['cells']], [7, 7])
        for cell, offset in zip(result['cells'], (Q(11, 96), Q(-11, 96))):
            self.assertEqual(Q(cell['volume']['value']), Q(1, 2))
            self.assertEqual([Q(v['value']) for v in cell['centroid_offset']], [offset] * 3)
        face = result['faces'][0]
        self.assertEqual(len(face['polygon_offset']), 6)
        self.assertEqual(Q(face['covariance'][0][0]['value']), Q(5, 72))
        self.assertEqual(Q(face['covariance'][0][1]['value']), Q(-5, 144))
        vertices = [[Q(component['value']) for component in vertex] for vertex in face['polygon_offset']]
        for index in range(1, len(vertices) - 1):
            u = [vertices[index][a] - vertices[0][a] for a in range(3)]
            v = [vertices[index + 1][a] - vertices[0][a] for a in range(3)]
            cross = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2],
                     u[0] * v[1] - u[1] * v[0]]
            self.assertGreater(sum(cross), 0)

    def test_complete_periodic_self_face_keys_retain_two_incidences(self):
        _, result = reference.evaluate_case(
            DESIGN.read_bytes(), 'periodic_one_cell_self_images__s1__pxyz__t0')
        self.assertEqual(len(result['cells']), 1)
        self.assertEqual(len(result['faces']), 3)
        self.assertEqual([face['key']['hi_image'] for face in result['faces']],
                         [[0, 0, 1], [0, 1, 0], [1, 0, 0]])
        incidences = result['cells'][0]['incidences']
        self.assertEqual(len(incidences), 6)
        for index, face in enumerate(result['faces']):
            self.assertEqual([entry['key'] for entry in incidences[2 * index:2 * index + 2]],
                             [face['key'], face['key']])
            self.assertEqual([entry['sign'] for entry in incidences[2 * index:2 * index + 2]], [1, -1])

    def test_changed_design_is_rejected_before_reference_evaluation(self):
        with self.assertRaisesRegex(ValueError, 'Changed registered geometry design'):
            reference.evaluate_case(DESIGN.read_bytes() + b' ',
                                    'bounded_oblique_bisector__s1__pxyz__t0')
        for value in ('1/0', ' 1', '+1', '1e-6', '1+1'):
            with self.assertRaises(ValueError):
                reference.rational(value)


if __name__ == '__main__':
    unittest.main()
