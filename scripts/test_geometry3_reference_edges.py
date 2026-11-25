"""Exact reference controls for a clipped cube and non-simple vertices."""
from fractions import Fraction
import unittest

import galaxy_geometry3_general_reference as reference


def box():
    return [dict(n=tuple(sign if i == axis else 0 for i in range(3)), h=1)
            for axis in range(3) for sign in (-1, 1)]


class ExactEdgeTests(unittest.TestCase):
    def test_sub_ulp_corner_cut_volume_and_area(self):
        scale = 1 << 70
        planes = box() + [dict(n=(scale, scale, scale), h=3 * scale - 1)]
        vertices, faces, cert = reference.certify_cell(planes, 1)
        volume, _, _, measures = reference.integrate(vertices, faces)
        self.assertEqual((cert['vertices'], cert['edges'], cert['faces']), (10, 15, 7))
        self.assertEqual(volume, 8 - Fraction(1, 6 * scale**3))
        cut, = [r for r in measures if r['plane'] is planes[-1]]
        self.assertEqual(cut['area_squared'], Fraction(3, 4 * scale**4))
        self.assertNotIn((1, 1, 1), vertices)

    def test_infeasible_proposal_uses_exact_edge_walk(self):
        from unittest.mock import patch
        scale = 1 << 70
        planes = box() + [dict(n=(scale, scale, scale), h=3 * scale - 1)]
        infeasible = (((1, 1, 1), 1), (1, 3, 5))
        with patch.object(reference, 'proposed_vertices', return_value=[infeasible]):
            vertices, _, cert = reference.certify_cell(planes, 1)
        self.assertEqual(cert['vertex_enumeration'], 'exact-edge-walk')
        self.assertEqual(cert['proposal_rejection'], 'ValueError')
        step = Fraction(1, scale)
        self.assertTrue({(1 - step, 1, 1), (1, 1 - step, 1), (1, 1, 1 - step)} <= set(vertices))

    def test_non_simple_pyramid_with_point_and_edge_contacts(self):
        # Apex z=1 has four incident faces and a redundant point support.
        # The last inequality also touches an entire base edge.
        planes = [dict(n=n, h=1) for n in (
            (0, 0, -1), (1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (0, 0, 1))]
        planes.append(dict(n=(1, 0, 0), h=2))
        vertices, faces, cert = reference.certified_surface(planes, 1, reference.exact_vertices(planes))
        self.assertEqual(set(vertices), {(0, 0, 1)} | {(x, y, -1) for x in (-2, 2) for y in (-2, 2)})
        self.assertEqual((cert['vertices'], cert['edges'], cert['faces']), (5, 8, 5))
        self.assertEqual(reference.integrate(vertices, faces)[0], Fraction(32, 3))

    def test_unbounded_direction_rejects(self):
        planes = [p for p in box() if p['n'] != (1, 0, 0)]
        with self.assertRaisesRegex(ValueError, 'Bounded reference cell has a forward endpoint'):
            list(reference.exact_vertices(planes))


if __name__ == '__main__':
    unittest.main()
