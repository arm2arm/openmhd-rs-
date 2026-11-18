"""Check rectangular periodic boosts and the magnetic/energy comparison gate."""
import unittest
import tempfile
import json
from pathlib import Path
from run_ct_controls import pair_error, analyze


class BoostComparison(unittest.TestCase):
    def test_wrong_executed_profile_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory);(path/'case').mkdir()
            (path/'case'/'summary.json').write_text(json.dumps(dict(profile='voronoi-ct-heun-v1')))
            with self.assertRaisesRegex(ValueError,'profile provenance mismatch'):
                analyze(path,{'case':dict(profile='voronoi-ct-admissible-v1')},{'case':dict(status='completed')})

    def test_rectangular_seam_and_conservative_energy_transform(self):
        a=dict(id=0,x=1.99,y=.001,volume=.25,rho=2.,p=.1,vx=.2,vy=.3,vz=-.1,bx=.75,by=-1.,bz=.2,energy=3.)
        b=dict(a,x=.03,y=.106,vx=2.2,vy=-.7,energy=8.2)
        c=dict(case='brio-wu',time=.02)
        self.assertTrue(pair_error([a],[b],c)['passed'])
        b['energy']+=1e-5
        self.assertFalse(pair_error([a],[b],c)['passed'])
        b['energy']-=1e-5;b['bx']+=1e-5
        self.assertFalse(pair_error([a],[b],c)['passed'])


if __name__=='__main__':
    unittest.main()
