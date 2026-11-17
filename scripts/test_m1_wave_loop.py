#!/usr/bin/env python3
"""Independent analytic fixtures for the issue #7 measurement code."""
import math
import json
import tempfile
import hashlib
import unittest
from pathlib import Path
from run_m1_wave_loop import BOOST, boost_error, norms, physical_errors, evaluate, refinement_orders, reanalyze, read_snapshot, fitted_order, mean_refinement_series
from run_prescribed_loop import diagnostics, evaluate as evaluate_transport, pair_errors


class Measurements(unittest.TestCase):
    def test_mean_refinement_includes_new_candidate_and_keeps_historical_rows(self):
        profile='bulk-frame-heun-quadratic-v1'
        pairs=[]
        for jitter in (0.,.15):
            for n,dt in [*( (n,.00025) for n in (8,16,32,64) ),(16,.001),(16,.0005)]:
                pairs.append(dict(case='smooth',profile=profile,jitter=jitter,n=n,dt=dt,
                                  errors={'B':{'L1':(16/n)**2*(dt/.00025)**2}}))
        historical=mean_refinement_series([])
        rows=mean_refinement_series(pairs)
        self.assertEqual(rows[:len(historical)],historical)
        candidate=[r for r in rows if r['profile']==profile]
        self.assertEqual(len(candidate),4)
        for r in candidate:
            expected=[8,16,32,64] if r['variable']=='n' else [.001,.0005,.00025]
            self.assertEqual([x for x,_ in r['values']],expected)
            self.assertEqual(r['successive_B_L1_orders'],[2.]*(len(expected)-1))
        # An absent measurement remains absent, never a fabricated order.
        del pairs[2]['errors']
        row=next(r for r in mean_refinement_series(pairs)
                 if r['profile']==profile and r['jitter']==0. and r['variable']=='n')
        self.assertEqual(row['successive_B_L1_orders'],[2.,None,None])

    def test_order_fit_and_uncertainty_on_known_power_law(self):
        n=[64,128,256]
        slope,error=fitted_order(n,[3./x**2 for x in n])
        self.assertAlmostEqual(slope,2.)
        self.assertLess(error,1e-14)
        _,error=fitted_order(n,[3./64**2,4./128**2,3./256**2])
        self.assertGreater(error,0.)
    def test_snapshot_rejects_truncation_wrong_volume_and_wrong_time(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'cells.csv'
            path.write_text('id,time,volume\n0,1,0.0009765625\n')
            with self.assertRaisesRegex(ValueError,'cell count'): read_snapshot(path,32,1.)
            path.write_text('id,time,volume\n'+''.join(f'{i},1,0.2\n' for i in range(4)))
            with self.assertRaisesRegex(ValueError,'domain volume'): read_snapshot(path,2,1.)
            path.write_text('id,time,volume\n'+''.join(f'{i},0.5,0.25\n' for i in range(4)))
            with self.assertRaisesRegex(ValueError,'time'): read_snapshot(path,2,1.)
            self.assertEqual(len(read_snapshot(path,2,.5)),4)

    def test_prescribed_missing_finest_error_never_passes(self):
        runs={}
        for n,e in [(32,.08),(64,.04),(128,.02),(256,None)]:
            runs[f'n{n}_base']={'config':{'n':n,'jitter':0.,'motion':'fixed'},'status':'completed'}
            if e is not None: runs[f'n{n}_base']['errors']={'passive_A':{'L1':e}}
        result=evaluate_transport(Path('.'),runs,[])
        self.assertTrue(result['fixed_convergence'][0]['gate'].startswith('fail'))
        self.assertIsNone(result['fixed_convergence'][0]['rows'][-1]['A_L1_over_peak'])
    def test_norm_rejects_missing_values_and_nonpositive_volumes(self):
        for values,cells in [([],[]),([1.],[{'volume':0.}]),([1.,2.],[{'volume':1.}]),([math.nan],[{'volume':1.}])]:
            with self.assertRaises(ValueError): norms(values,cells)

    def test_prescribed_diagnostics_distinguish_signed_mean_and_rms(self):
        cells=[dict(volume=.5,az=2.,bx=3.,by=4.,bz=0.,div_b_ls=v,div_b_face=v,div_b_limited=v) for v in (-2.,2.)]
        result=diagnostics(cells)
        self.assertEqual(result['magnetic_energy'],12.5)
        self.assertEqual(result['div_b_ls']['signed_mean'],0.)
        self.assertEqual(result['div_b_ls']['dimensional']['L2'],2.)
        self.assertEqual(pair_errors(cells,cells)['B']['max'],0.)

    def test_prescribed_missing_and_failed_ladders_do_not_pass(self):
        c={'n':32,'jitter':0.,'motion':'fixed'}
        result=evaluate_transport(Path('.'),{'test_base':{'config':c,'status':'failed'}},[])
        self.assertEqual(result['fixed_convergence'][0]['gate'],'fail: evolution')
        result=evaluate_transport(Path('.'),{'test_base':{'config':c,'status':'completed','errors':{'passive_A':{'L1':1e-8}}}},[])
        self.assertTrue(result['fixed_convergence'][0]['gate'].startswith('unexecuted'))
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
