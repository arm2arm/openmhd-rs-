"""Check the observational transverse mode and physical acceleration conversion."""
import unittest

from run_column_boost_repro import alternating, growth_measurement


class TransverseModeTests(unittest.TestCase):
    def test_constant_smooth_and_alternating_row_components(self):
        self.assertEqual(alternating([7.]*8, 2), [0., 0.])
        self.assertEqual(alternating([1., 0., -1., 0.], 1), [0.])
        self.assertEqual(alternating([9., 5., 9., 5.], 1), [2.])
        with self.assertRaises(ValueError):
            alternating([1.]*3, 1)

    def test_known_growth_and_mass_transport_cancellation(self):
        state, rates = [], []
        for sign in (1., -1., 1., -1.):
            state.append(dict(volume=0.25, rho=2., vx=7.+2.*sign,
                              by=0.5*sign, reduced_az=0.25*sign))
            # d(rho*v)=rho*dv + v*d(rho), with dv=3*(v-7).
            rates.append(dict(fluid_rho=1., fluid_x_rho=1., fluid_y_rho=0.,
                              fluid_mx=12.*sign+state[-1]['vx'],
                              fluid_x_mx=state[-1]['vx'], fluid_y_mx=12.*sign,
                              curl_y=1.5*sign, fv_y=-0.5*sign, unprojected_y=0.,
                              potential_z=0.75*sign, potential_unprojected_z=0.))
        measured = growth_measurement(state, rates, 1)
        self.assertEqual(measured['vx']['volume_weighted_mode_square'], 4.)
        self.assertEqual(measured['vx']['rates']['fluid']['logarithmic_growth'], 3.)
        self.assertEqual(measured['vx']['rates']['fluid_x']['logarithmic_growth'], 0.)
        self.assertEqual(measured['vx']['rates']['fluid_y']['logarithmic_growth'], 3.)
        self.assertEqual(measured['by']['rates']['fv_y']['logarithmic_growth'], -1.)
        self.assertIsNone(measured['rho']['rates']['fluid_rho']['logarithmic_growth'])
