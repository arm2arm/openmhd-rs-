#!/usr/bin/env python3
"""Independent analytic fixtures for the issue #7 measurement code."""
import math
import unittest
from run_m1_wave_loop import BOOST, boost_error, norms, physical_errors


class Measurements(unittest.TestCase):
    def test_nonuniform_volume_norms(self):
        result = norms([-2., 4.], [{'volume': 1.}, {'volume': 3.}])
        self.assertEqual(result['L1'], 3.5)
        self.assertEqual(result['L2'], math.sqrt(13.))
        self.assertEqual(result['max'], 4.)

    def test_energy_and_coordinates_transform_with_fluid_boost(self):
        base = dict(id=0., volume=1., x=.9, y=.1, rho=2., p=1., vx=.3, vy=-.2, vz=.7,
                    bx=.4, by=.2, bz=.1, energy=4.)
        boosted = dict(base)
        time = .3
        for k, b in zip(('x', 'y'), BOOST):
            boosted[k] = (base[k]+b*time) % 1
        for k, b in zip(('vx', 'vy', 'vz'), BOOST):
            boosted[k] += b
        boosted['energy'] += base['rho']*sum(base[k]*b for k,b in zip(('vx','vy','vz'),BOOST))+.5*base['rho']*sum(b*b for b in BOOST)
        result = boost_error([base], [boosted], time)
        for value in result.values():
            self.assertLess(value['max'] if isinstance(value,dict) else value, 2e-15)
        boosted['energy'] += .125
        self.assertAlmostEqual(boost_error([base], [boosted], time)['energy']['L1'], .125)

    def test_exact_alfven_and_known_magnetic_error(self):
        # v_parallel=1 stationary wave, observed after boost at x=x0+b_x*t.
        x0, time = .125, .25
        by, bz = .1/math.sqrt(2), .1/math.sqrt(2)
        cell = dict(volume=1., x=x0+BOOST[0]*time, y=.1, bx=1., by=by, bz=bz,
                    vx=1.+BOOST[0], vy=by+BOOST[1], vz=bz+BOOST[2])
        result = physical_errors([cell],time,'alfven',1.,BOOST)
        self.assertLess(result['B']['max'],1e-16)
        cell['bx'] += .125
        self.assertAlmostEqual(physical_errors([cell],time,'alfven',1.,BOOST)['B']['L2'],.125)

    def test_loop_cusp_and_edge_are_excluded_from_magnetic_norm(self):
        amplitude = .001/math.sqrt(4*math.pi)
        cells = [dict(volume=1.,x=x,y=.5,az=amplitude*max(0.,.3-abs(x-.5)),bx=0.,by=by,bz=0.)
                 for x,by in ((.5,123.),(.8,456.),(.6,amplitude))]
        result = physical_errors(cells,0.,'loop',0.,(0.,0.,0.))
        self.assertEqual(result['passive_B_excluded_cells'],2)
        self.assertEqual(result['passive_B']['max'],0.)
        self.assertEqual(result['passive_A']['max'],0.)


if __name__ == '__main__':
    unittest.main()
