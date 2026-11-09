import unittest
from physics_projection import area, clip, polygons, shock_errors, vortex_bins


class ConservativeProjection(unittest.TestCase):
    def test_diagonal_half_plane_and_periodic_area(self):
        square=[(0.,0.),(1.,0.),(1.,1.),(0.,1.)]
        self.assertAlmostEqual(area(clip(square,(1.,1.),1.)),.5)
        cell=dict(id=0,time=0.,x=.5,y=.5,volume=1.,rho=2.,p=3.,bx=4.,by=5.)
        geometry=dict(time=0.,lengths=[1.,1.],cells=[dict(id=0,volume=1.,centroid=[.5,.5],generator=[.5,.5],
            planes=[[-1.,0.,0.,0.],[1.,0.,1.,0.],[0.,-1.,0.,0.],[0.,1.,0.,1.]])])
        pieces=polygons(geometry,[cell],(.2,-.3))
        self.assertAlmostEqual(sum(map(area,pieces[0])),1.)
        values=vortex_bins([cell],pieces,4)
        for v in values:
            for f in ('rho','p','bx','by'):self.assertAlmostEqual(v[f],cell[f])
        with self.assertRaisesRegex(ValueError,'time'):
            polygons(geometry,[{**cell,'time':.5}])
        for key in ('volume','centroid','generator'):
            changed=dict(geometry['cells'][0])
            changed[key]=float('nan') if key=='volume' else [float('nan'),.5]
            with self.assertRaisesRegex(ValueError,'invalid geometry'):
                polygons({**geometry,'cells':[changed]},[cell])

    def test_bin_averages_sampled_primitives(self):
        cells=[dict(rho=1.,p=6.,bx=2.,by=-1.),dict(rho=3.,p=10.,bx=4.,by=1.)]
        pieces=[[[(0.,0.),(.25,0.),(.25,1.),(0.,1.)]],
                [[(.25,0.),(1.,0.),(1.,1.),(.25,1.)]]]
        values=vortex_bins(cells,pieces,2)
        for i in (0,2):
            self.assertAlmostEqual(values[i]['rho'],2.)
            self.assertAlmostEqual(values[i]['p'],8.)
            self.assertAlmostEqual(values[i]['by'],0.)
        for i in (1,3):self.assertAlmostEqual(values[i]['p'],10.)
        with self.assertRaisesRegex(ValueError,'coverage'):vortex_bins(cells[:1],pieces[:1],2)

    def test_shock_reference_average_precedes_absolute_error(self):
        reference=[dict(x=.75,rho=1.,p=1.,vx=0.,by=-1.),dict(x=1.25,rho=1.,p=1.,vx=0.,by=1.)]
        cells=[dict(rho=1.,p=1.,vx=0.,by=0.)]
        pieces=[[[(.5,0.),(1.5,0.),(1.5,.125),(.5,.125)]]]
        errors=shock_errors(cells,pieces,reference)
        self.assertEqual(errors['by']['L1'],0.)
        self.assertEqual(errors['by']['L2'],0.)


if __name__=='__main__':unittest.main()
