"""REANA-only arithmetic controls for the manufactured 3D operator inputs."""
import struct
import unittest

from geometry3_operator_fixtures import catalog, fixture


def value(word):
    return struct.unpack('>d', bytes.fromhex(word))[0]


def vector(words):
    return tuple(map(value, words))


class ManufacturedOperators(unittest.TestCase):
    def test_noncentral_product_all_curl_placements_and_chart_samples(self):
        for layout in ('local_image', 'bounded_interior'):
            for axis in 'xyz':
                packet = fixture(f'{layout}__quadratic__xy__{axis}')
                x, y, _ = centre = vector(packet['evaluation_position_bits'])
                ref = packet['expected']
                self.assertEqual(value(ref['value_bits']), x * y)
                self.assertEqual(vector(ref['gradient_bits']), (y, x, 0))
                self.assertEqual(tuple(map(vector, ref['hessian_bits'])), ((0, 1, 0), (1, 0, 0), (0, 0, 0)))
                curl = {'x': (0, 0, -x), 'y': (0, 0, y), 'z': (x, -y, 0)}
                self.assertEqual(vector(ref['curl_A_bits']), curl[axis])
                self.assertEqual(value(ref['div_A_bits']), {'x': y, 'y': x, 'z': 0}[axis])
                self.assertEqual(value(ref['div_B_same_fit_bits']), 0)
                if axis == 'z':
                    self.assertEqual(tuple(map(vector, ref['curl_jacobian_bits'])),
                                     ((1, 0, 0), (0, -1, 0), (0, 0, 0)))
                self.assertEqual(ref['exact_design_rank'], 10)
                self.assertTrue(all(s['id'] != packet['mesh']['owner_id'] for s in packet['samples']))
                width = vector(packet['mesh']['width_bits'])
                for sample in packet['samples']:
                    lifted = tuple(v + w * L for v, w, L in zip(vector(sample['position_bits']), sample['image'], width))
                    self.assertEqual(vector(sample['displacement_bits']), tuple(a-b for a, b in zip(lifted, centre)))
                    self.assertEqual(value(sample['scalar_bits']), lifted[0] * lifted[1])
                if layout == 'local_image':
                    self.assertTrue(any(any(s['image']) for s in packet['samples']))
                else:
                    self.assertEqual([s['adjacency_ring'] for s in packet['samples']].count(1), 6)
                    self.assertEqual([s['adjacency_ring'] for s in packet['samples']].count(2), 18)

    def test_basis_coverage_affine_weights_and_rank_deficiency(self):
        cases = catalog()
        self.assertEqual(len(cases), 87)
        for layout in ('bounded_interior', 'local_image'):
            for component in 'xyz':
                selected = {term for l, fit, term, axis in cases.values()
                            if l == layout and fit == 'quadratic' and axis == component}
                self.assertEqual(selected, {'constant', 'x', 'y', 'z', 'xx_half', 'yy_half', 'zz_half', 'xy', 'xz', 'yz'})
        linear = fixture('bounded_interior__linear__constant__y')
        self.assertEqual(linear['expected']['exact_design_rank'], 4)
        self.assertEqual(vector(linear['expected']['gradient_bits']), (0, 0, 0))
        self.assertEqual({value(s['face_area_weight_bits']) for s in linear['samples']}, {1/16})
        for name, rank in (('plane__linear__deficient', 3), ('plane__quadratic__deficient', 6),
                           ('shell__quadratic__deficient', 9)):
            packet = fixture(name)
            ref = packet['expected']
            self.assertGreater(ref['rows'], ref['columns'])
            self.assertEqual((ref['expected_fit'], ref['exact_design_rank']), ('reject_rank_deficient', rank))
            self.assertGreater(len({s['scalar_bits'] for s in packet['samples']}), 1)
            for sample in packet['samples']:
                d = vector(sample['displacement_bits'])
                if name.startswith('shell'):
                    self.assertEqual(sum(x*x for x in d), 1/32)
                else:
                    self.assertEqual(d[2], 0)


if __name__ == '__main__':
    unittest.main()
