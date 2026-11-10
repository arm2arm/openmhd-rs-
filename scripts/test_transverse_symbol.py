"""Independent known linear ODE and completeness checks for the response reducer."""
import unittest
import numpy as np
from run_transverse_symbol import FIELDS, INPUTS, matrices


def fixture():
    matrix=-np.eye(10)
    matrix[:2,:2]=[[-2.,-3.],[3.,-2.]]
    rows=[]
    for j,field in enumerate(INPUTS):
        for phase in (0,1):
            for k,output in enumerate(FIELDS):
                for out_phase in (0,1):
                    rows.append(dict(input=field,input_phase=phase,output=output,output_phase=out_phase,
                                     derivative=matrix[2*k+out_phase,2*j+phase] if k<5 else 0.,leakage_l2=0.))
    return rows


class UniformResponseTests(unittest.TestCase):
    def test_known_damped_rotation_and_modal_leakage(self):
        measured=matrices(fixture())['projected']
        eigenvalues=[complex(*v) for v in measured['eigenvalues']]
        self.assertAlmostEqual(measured['max_real_eigenvalue'],-1.)
        self.assertTrue(any(abs(v-complex(-2.,3.))<1e-12 for v in eigenvalues))
        self.assertTrue(any(abs(v-complex(-2.,-3.))<1e-12 for v in eigenvalues))
        self.assertEqual(measured['leakage_relative'],0.)

    def test_incomplete_duplicate_or_nonfinite_operator_is_rejected(self):
        rows=fixture()
        for invalid in (rows[:-1],rows+[rows[0]], [dict(r,derivative=float('nan')) for r in rows]):
            with self.assertRaises(ValueError):matrices(invalid)
