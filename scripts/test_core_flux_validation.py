#!/usr/bin/env python3
"""Independent small fixtures for the profile comparison/boost diagnostics."""
import io
import unittest

from run_core_flux_validation import FIELDS, boost_errors, profile_errors, read_cells


class ComparisonTests(unittest.TestCase):
    def test_interval_averages_and_norms(self):
        # Candidate central cells [0.5,1], [1,1.5] average reference pairs.
        cells = [dict(x_comoving=(i + .5) / 2, **{k: 2 for k in FIELDS}) for i in range(4)]
        reference = [dict(x=.5 + (i + .5) / 4, **{k: v for k in FIELDS})
                     for i, v in enumerate((1, 3, 3, 7))]
        errors = profile_errors(cells, reference)
        for k in FIELDS:
            self.assertEqual(errors[f"{k}_l1"], 1.5)  # differences 0, -3
            self.assertAlmostEqual(errors[f"{k}_l2"], 4.5**.5)
        reference[0]["x"] += .1
        with self.assertRaises(ValueError):
            profile_errors(cells, reference)

    def test_boost_energy_and_periodic_coordinate_transform(self):
        a = dict(x=1.9, x_comoving=1.9, rho=2., p=1., bx=.75, by=-1., vx=3., vy=-2., energy=12.)
        b = dict(a, x=.1, vx=5., energy=28.)  # E+boost*rho*vx+rho*boost²/2
        errors = boost_errors([a], [b], 2, .1)
        self.assertLess(max(errors.values()), 1e-14)
        b["energy"] += .25
        self.assertEqual(boost_errors([a], [b], 2, .1)["energy"], .25)

    def test_reject_nonfinite_or_nonpositive_profiles(self):
        for values in ("nan,1", "1,inf", "0,1", "1,-1"):
            with self.assertRaises(ValueError):
                read_cells(io.StringIO("rho,p\n" + values + "\n"))


if __name__ == "__main__":
    unittest.main()
