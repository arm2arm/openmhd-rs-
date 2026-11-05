import unittest
from m1_overlap import area, overlap, project, FIELDS

class OverlapTests(unittest.TestCase):
    def test_triangle_and_clipped_sliver(self):
        p=[(0.,0.),(2.,0.),(0.,2.)]
        self.assertEqual(area(p),2.)
        self.assertEqual(overlap(p,((0.,1.),(0.,1.))),1.)
        self.assertAlmostEqual(overlap(p,((1.,2.),(0.,1.))),.5)
        self.assertEqual(overlap(p,((3.,4.),(0.,1.))),0.)

    def test_periodic_image_split_preserves_integrals(self):
        polys={0:[(-.25,0),(.25,0),(.25,1),(-.25,1)],1:[(.25,0),(.75,0),(.75,1),(.25,1)]}
        cells=[dict(volume=.5,**{k:float(i+1) for k in FIELDS}) for i in range(2)]
        p,d=project(cells,polys,[1.,1.],[4,3])
        for row,want in zip(p[:4],[1.,2.,2.,1.]): self.assertAlmostEqual(row['rho'],want)
        self.assertLess(d['coverage_relative_max'],1e-14)
        self.assertLess(max(map(abs,d['integral_residual'].values())),1e-14)
        shifted={i:[(x+7,y-3) for x,y in poly] for i,poly in polys.items()}
        q,_=project(cells,shifted,[1.,1.],[4,3]); self.assertEqual(p,q)

    def test_overlap_and_missing_cell_are_rejected(self):
        p={0:[(0,0),(1,0),(1,1),(0,1)]}
        cells=[dict(volume=1.,**{k:1. for k in FIELDS})]
        with self.assertRaises(ValueError): project(cells,{0:p[0],1:p[0]},[1.,1.],[2,2])
        with self.assertRaises(ValueError): project(cells,{0:[(0,0),(.5,0),(.5,1),(0,1)]},[1.,1.],[2,2])

if __name__=='__main__': unittest.main()
