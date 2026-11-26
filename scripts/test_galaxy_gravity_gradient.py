"""Direct controls for the G-GRAD reference, signs and finite-difference witnesses."""
from fractions import Fraction as Q
from types import SimpleNamespace
import unittest

import galaxy_gravity_bridge as bridge
import galaxy_gravity_gradient as gradient


def model(positions, masses, epsilon=1):
    return SimpleNamespace(g=Q(1), epsilon=Q(epsilon),
                           sources=tuple(SimpleNamespace(payload=str(i), position=tuple(map(Q, p)), mass=Q(m))
                                         for i, (p, m) in enumerate(zip(positions, masses))))


class GradientTests(unittest.TestCase):
    def test_registered_words_and_particle_ids(self):
        for name in gradient.CASE_NAMES:
            case = bridge.parse_input(gradient.fixture(name))
            self.assertEqual(case["case"], "G1-GRAD-"+name)
            self.assertEqual(case["input_order"], [r["id"] for r in case["particles"]])
            self.assertEqual(len(case["input_order"]), 3 if name == "three-body" else 2)
            if name in gradient.RATIOS:
                r = Q(gradient.RATIOS[name])
                position = [bridge.exact(x) for x in case["particles"][1]["position"]]
                for x, n in zip(position, (2, -1, 2)):
                    exact = r*n/3
                    self.assertEqual(gradient.word(x), gradient.word(exact))
                    self.assertLessEqual(abs(x-exact), abs(exact)*Q(1, 2**52))

    def test_all_unordered_pairs_contribute_once(self):
        m = model([(0,0,0)]*3, [2,3,5], epsilon=2)
        self.assertEqual(gradient.potential(m, "0", 0, 0), (Q(-31,2),)*3)
        lo, hi, _ = gradient.potential(m, "0", 0, Q(3,2))
        # The unshifted pair still contributes -15/2. The other distances are 5/2.
        self.assertEqual((lo, hi), (Q(-139,10),)*2)

    def test_axis_force_sign_and_central_difference_witnesses(self):
        m = model([(0,0,0),(3,0,0)], [2,3], epsilon=4)
        exact = Q(18,125)
        out = gradient.coordinate(m, "0", 0, Q(float(exact)), ((exact, exact), False), Q(4))
        self.assertTrue(out["passed"])
        w = out["witness"]
        self.assertLessEqual(w["truncation_start"]+2, w["plateau_start"])
        self.assertLessEqual(w["plateau_start"]+3, w["roundoff"])
        self.assertGreater(out["levels"][w["plateau_start"]]["force_fd"], 0)

    def test_reversed_force_rejects_despite_correct_scalar_energy(self):
        m = model([(0,0,0),(3,0,0)], [2,3], epsilon=4)
        exact = Q(18,125)
        out = gradient.coordinate(m, "0", 0, -Q(float(exact)), ((exact, exact), False), Q(4))
        self.assertFalse(out["passed"])
        self.assertGreater(out["algebra_relative"][0], 1)
        self.assertIsNone(out["witness"]["plateau_start"])

    def test_even_nonconstant_energy_and_exact_zero_force(self):
        m = model([(0,0,0)]*2, [2,3])
        zero = ((Q(0),Q(0)),True)
        result = gradient.coordinate(m, "1", 2, Q(0), zero, Q(1))
        self.assertTrue(result["passed"] and result["coarse_energy_changes"])
        self.assertTrue(all(r["U_plus"]==r["U_minus"] for r in result["levels"]))
        self.assertFalse(gradient.coordinate(m, "1", 2, Q(1,10**20), zero, Q(1))["passed"])

    def test_plateau_and_roundoff_require_ordered_independent_evidence(self):
        def row(error, secant=None):
            secant = error if secant is None else secant
            return dict(rounded_error=(error,error), rust_error=error, secant_error=(secant,secant))
        t = gradient.FD_LIMIT
        curve = [row(16*t),row(4*t),row(t),row(t/2),row(t/3),row(t/4),row(4*t,t/10)]
        self.assertEqual(gradient.witnesses(curve), dict(truncation_start=0, plateau_start=3, roundoff=6))
        self.assertIsNone(gradient.witnesses(curve[:-1])["roundoff"])
        self.assertIsNone(gradient.witnesses(curve[:5]+curve[6:])["plateau_start"])
        self.assertIsNone(gradient.witnesses(curve[:-1]+[row(4*t,2*t)])["roundoff"])
