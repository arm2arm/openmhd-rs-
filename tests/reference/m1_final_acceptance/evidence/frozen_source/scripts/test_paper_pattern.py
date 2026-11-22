import unittest

from analyze_paper_pattern import coefficients


class PatternCoefficients(unittest.TestCase):
    def test_duplicate_periodic_images_cancel_against_shared_baseline(self):
        # Distinct images of cell 5 carry the same periodic scalar. The two
        # sample-to-baseline differences therefore vanish exactly for them.
        rows = [dict(neighbor_base=str(j), baseline_neighbor='1029',
                     weight_x=str(x), weight_y=str(y))
                for j, x, y in [(5, 1, .5), (6, -2, 1), (5, 3, -1.5)]]
        result = coefficients(rows)
        self.assertEqual(dict(result), {5: [2., -1.], 6: [-2., 1.]})
        values = {5: .3, 6: -.4}
        self.assertAlmostEqual(sum(result[j][0]*values[j] for j in result), 1.4)
        self.assertAlmostEqual(sum(result[j][1]*values[j] for j in result), -.7)
        self.assertEqual([sum(w[k] for w in result.values()) for k in range(2)], [0., 0.])


if __name__ == '__main__':
    unittest.main()
