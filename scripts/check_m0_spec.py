#!/usr/bin/env python3
"""Small M0 algebra fixtures; this script implements no mesh evolution or MHD solver.

Source and interpretation: docs/PAPER_IMPLEMENTATION_SPEC.md, arXiv:2609.35989v1.
Run with Python 3's standard library: python3 scripts/check_m0_spec.py
Assertions about printed inconsistencies are deliberate regression checks on the
review findings, not validations of the printed initial conditions.
"""

from fractions import Fraction as F
from math import cos, pi, sin, sqrt
from random import Random
import unittest


def add(*vectors):
    return [sum(values) for values in zip(*vectors)]


def scale(factor, vector):
    return [factor * value for value in vector]


def dot(left, right):
    return sum(a * b for a, b in zip(left, right))


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def matvec(matrix, vector):
    return [dot(row, vector) for row in matrix]


def transpose(matrix):
    return list(zip(*matrix))


def curl(jacobian):
    """Jacobian indices are [component][coordinate], P (52)/(61)."""
    return [jacobian[2][1] - jacobian[1][2],
            jacobian[0][2] - jacobian[2][0],
            jacobian[1][0] - jacobian[0][1]]


def solve_exact(matrix, rhs):
    """Tiny rational elimination for fixtures only; not a production LS solver."""
    rows = [[F(x) for x in row] + [F(value)]
            for row, value in zip(matrix, rhs)]
    size = len(rows)
    for column in range(size):
        pivot = next(i for i in range(column, size) if rows[i][column])
        rows[column], rows[pivot] = rows[pivot], rows[column]
        divisor = rows[column][column]
        rows[column] = [x / divisor for x in rows[column]]
        for i in range(size):
            if i != column:
                factor = rows[i][column]
                rows[i] = [x - factor * y
                           for x, y in zip(rows[i], rows[column])]
    return [row[-1] for row in rows]


class SpecificationAlgebra(unittest.TestCase):
    def test_covector_and_mean_field_identity(self):
        """P (42)+(76) equals its Eulerian gauge equation at a local jet."""
        rng = Random(1)
        vec = lambda: [rng.randrange(-7, 8) for _ in range(3)]
        for _ in range(100):
            a, v, u, w, mean_b, grad_phi = [vec() for _ in range(6)]
            grad_a = [vec() for _ in range(3)]
            grad_u = [vec() for _ in range(3)]
            b = add(curl(grad_a), mean_b)
            grad_psi = add(matvec(transpose(grad_u), a),
                           matvec(transpose(grad_a), u))
            eulerian_plus_motion = add(cross(v, b), scale(-1, grad_psi),
                                       grad_phi, matvec(grad_a, w))
            material = add(cross(add(v, scale(-1, u)), b),
                           scale(-1, matvec(transpose(grad_u), a)),
                           matvec(grad_a, add(w, scale(-1, u))),
                           grad_phi, cross(u, mean_b))
            self.assertEqual(material, eulerian_plus_motion)

    def test_free_intercept_affine_fit(self):
        """P (54)-(60), dimensionally reduced, reproduces all affine moments."""
        points = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1)]
        weights = [1, 2, 3, 4, 5]
        basis = [[1, x, y] for x, y in points]
        matrix = [[sum(w * x[a] * x[b] for w, x in zip(weights, basis))
                   for b in range(3)] for a in range(3)]
        q = [scale(w, solve_exact(matrix, x))
             for w, x in zip(weights, basis)]
        for a in range(3):
            for b in range(3):
                self.assertEqual(sum(row[a] * x[b] for row, x in zip(q, basis)),
                                 int(a == b))
        affine = [[1, 2, 3], [4, -5, 6], [7, 8, -9]]
        fitted = []
        for coefficients in affine:
            samples = [dot(coefficients, x) for x in basis]
            fitted.append([sum(row[k] * value for row, value in zip(q, samples))
                           for k in range(3)])
        self.assertEqual(fitted, affine)
        grad_a = [[row[1], row[2], 0] for row in fitted]
        self.assertEqual(curl(grad_a), [-9, -8, -8])

    def test_positive_derivative_has_negative_transport_velocity(self):
        """P (71): dot(A)=b*d_x(A) transports at speed -b."""
        # Piecewise-constant states; face displacements are -1 and +1.
        left, centre, right = F(2), F(5), F(11)
        for b in (F(-3), F(3)):
            minus_face = centre if b * (-1) < 0 else left
            plus_face = centre if b < 0 else right
            # Two-face affine derivative has weights (-1/2,+1/2).
            rate = b * (plus_face - minus_face) / 2
            expected = (b * (right - centre) / 2 if b > 0
                        else b * (centre - left) / 2)
            self.assertEqual(rate, expected)

    def test_centroid_velocity_correction(self):
        """P (89), including a crossing requiring unwrapped coordinates."""
        dt, c0, c1 = F(1, 5), F(9, 10), F(13, 10)
        actual = (c1 - c0) / dt
        generator = F(3, 2)
        corrected = 2 * actual - generator
        self.assertEqual((generator + corrected) / 2, actual)
        wrapped_velocity = ((c1 % 1) - c0) / dt
        self.assertNotEqual(wrapped_velocity, actual)

    def test_cleaning_mode_sign(self):
        """P (41)-(42) imply a damped, not exponentially driven, wave."""
        # A_x=a*cos(k*x), phi=p*sin(k*x): a'=k*p, p'=-alpha*cs²*k*a-d*p.
        alpha, cs2, k, damping = F(1), F(4), F(3), F(2, 5)
        a, p = F(2, 7), F(-3, 11)
        a_dot = k * p
        p_dot = -alpha * cs2 * k * a - damping * p
        p_ddot = -alpha * cs2 * k * a_dot - damping * p_dot
        self.assertEqual(p_ddot + damping * p_dot + alpha * cs2 * k * k * p, 0)

    def test_printed_cleaning_dimensions_flag_R2(self):
        """Exponent vectors represent dimensions in independent units B,L,T."""
        phi = (1, 2, -1)
        phi_dot = (1, 2, -2)
        phi_ddot = (1, 2, -3)
        rate = (0, 0, -1)             # beta*cs/r
        printed_inertia = (0, -1, 2)  # r/(beta*cs²)
        derived_inertia = (0, 0, 1)   # r/(beta*cs)
        self.assertNotEqual(phi_dot, rate)
        self.assertEqual(phi_dot, tuple(add(phi, rate)))
        self.assertNotEqual(phi_dot, tuple(add(printed_inertia, phi_ddot)))
        self.assertEqual(phi_dot, tuple(add(derived_inertia, phi_ddot)))

    def test_alfven_printed_potential_flags_R1(self):
        """Analytic derivatives of printed (99)-(101), no finite differences."""
        for x in (0.0, 0.173, 0.25):
            s, c = sin(2 * pi * x), cos(2 * pi * x)
            # Ay=0.1*cos(kx)/k+y/2; Az=0.1*sin(kx)/k-z/2.
            printed_grad = [[0, 0, 0], [-0.1 * s, 0.5, 0],
                            [0.1 * c, 0, -0.5]]
            actual = curl(printed_grad)
            target = [1, 0.1 * s, 0.1 * c]
            self.assertEqual(actual[0], 0)
            self.assertNotEqual(actual, target)

    def test_alfven_derived_periodic_potential(self):
        """D fixture: Ay=0.1*sin(kx)/k, Az=0.1*cos(kx)/k, mean Bx=1."""
        for x in (0.0, 0.173, 0.25):
            s, c = sin(2 * pi * x), cos(2 * pi * x)
            corrected_grad = [[0, 0, 0], [0.1 * c, 0, 0], [-0.1 * s, 0, 0]]
            actual = add(curl(corrected_grad), [1, 0, 0])
            for value, expected in zip(actual, [1, 0.1 * s, 0.1 * c]):
                self.assertAlmostEqual(value, expected, places=14)

    def test_orszag_tang_normalization(self):
        """Printed Az normalization reproduces the stated magnetic amplitude."""
        printed_curl_amplitude = 4 * pi / (4 * pi) ** 1.5
        stated_b_amplitude = 1 / sqrt(4 * pi)
        self.assertAlmostEqual(printed_curl_amplitude, stated_b_amplitude)


if __name__ == "__main__":
    unittest.main(verbosity=2)
