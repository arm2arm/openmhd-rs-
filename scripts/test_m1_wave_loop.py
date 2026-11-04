#!/usr/bin/env python3
"""Independent analytic fixtures for the issue #7 measurement code."""
import math
import json
import tempfile
import hashlib
import unittest
from pathlib import Path
from run_m1_wave_loop import BOOST, boost_error, norms, physical_errors, evaluate, refinement_orders, reanalyze


class Measurements(unittest.TestCase):
    def test_reanalysis_ignores_mutable_report_and_rejects_immutable_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)
            (out/'manifest.json').write_text('{}')
            (out/'runs.json').write_text('{}')
            (out/'summary.json').write_text('{"pairs":[]}')
            hashes={name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in ('manifest.json','runs.json','summary.json')}
            (out/'provenance.json').write_text(json.dumps({'revision':'test-fixture','result_sha256':hashes}))
            reanalyze(out)
            (out/'summary.json').write_text('{"pairs":[{"injected":"mutable metadata"}]}')
            reanalyze(out)
            self.assertEqual(json.loads((out/'summary.json').read_text())['pairs'],[])
            (out/'execution_summary.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'Changed immutable'):
                reanalyze(out)

    def test_refinement_gaps_and_missing_runs_do_not_invent_orders(self):
        self.assertEqual(refinement_orders([8,32],[.1,.025],True),[1.])
        self.assertEqual(refinement_orders([8,16,32],[.1,None,.025],True),[None,None])
        self.assertEqual(refinement_orders([.001,.00025],[.1,.025],False),[1.])

    def test_failed_evolution_is_not_labelled_unexecuted(self):
        run={'config':{'jitter':0.,'parallel':0.,'motion_family':'fixed','n':32},'status':'failed'}
        result=evaluate(Path('.'),{'alfven_test_base':run},[],'paper-global-v2',False)
        self.assertTrue(result['alfven_convergence'][0]['gate'].startswith('fail: evolution failed'))

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
