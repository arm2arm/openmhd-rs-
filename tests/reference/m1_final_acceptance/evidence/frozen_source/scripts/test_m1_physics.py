"""Independent measurement checks for the registered shock/vortex packet."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run_m1_physics as study


class PhysicsMeasurements(unittest.TestCase):
    def test_galilean_energy_and_rectangular_periodic_pair(self):
        c=dict(case='brio-wu',time=.1)
        a=dict(id=0,time=.1,x=1.95,y=.02,volume=.25,rho=2.,p=3.,
               vx=.5,vy=-.25,vz=.1,bx=.75,by=1.,bz=0.,energy=8.)
        b=dict(a,x=.15,y=.045,vx=2.5,vy=-1.25,energy=15.5)
        summary=dict(initial=dict(budget_scales=[.5,1.,1.,1.,2.]))
        result=study.boost_comparison([a],[b],c,summary)
        self.assertTrue(result['passed'])
        self.assertEqual(result['relative_L1']['energy'],0.)
        b['energy']+=1e-4
        self.assertFalse(study.boost_comparison([a],[b],c,summary)['passed'])
        b['time']=.09
        with self.assertRaisesRegex(ValueError,'time'):study.boost_comparison([a],[b],c,summary)

    def test_absent_failed_or_unregistered_ladders_cannot_pass(self):
        packet=json.loads((study.ROOT/'benchmarks/m0/packet.json').read_text())
        configs=study.configurations()
        records={n:dict(status='failed') for n in configs}
        for config,runs,quick in ((configs,{},False),(configs,records,False),({}, {},False),
                                  (study.configurations(True),{},True)):
            result=study.evaluate(Path('/unused'),config,runs,quick,packet)
            self.assertFalse(result['all_registered_physics_gates'])
            self.assertTrue(all(f['status']=='unexecuted' for f in result['profile_families']))

    def test_every_boost_and_state_gate_is_required(self):
        packet=json.loads((study.ROOT/'benchmarks/m0/packet.json').read_text())
        configs=study.configurations()
        records={n:dict(status='completed',state_and_diagnostic_gates=True,
                       reference_errors={f:dict(L1=1/c['n']) for f in ('rho','p','vx','by','bx')},
                       summary={}) for n,c in configs.items()}
        with (patch.object(study,'read_cells',return_value=[]),
              patch.object(study,'boost_comparison',return_value=dict(passed=True))):
            self.assertTrue(study.evaluate(Path('/unused'),configs,records,False,packet)['all_registered_physics_gates'])
            broken=copy.deepcopy(records)
            broken[next(n for n in configs if n.endswith('_boost'))]['state_and_diagnostic_gates']=False
            self.assertFalse(study.evaluate(Path('/unused'),configs,broken,False,packet)['all_registered_physics_gates'])
            del broken[next(iter(broken))]
            self.assertFalse(study.evaluate(Path('/unused'),configs,broken,False,packet)['all_registered_physics_gates'])
        with (patch.object(study,'read_cells',return_value=[]),
              patch.object(study,'boost_comparison',return_value=dict(passed=False))):
            self.assertFalse(study.evaluate(Path('/unused'),configs,records,False,packet)['all_registered_physics_gates'])

    def test_nonfinite_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'diagnostics.json'
            for value in ('NaN','Infinity','-Infinity','1e999'):
                path.write_text('{"rho_min":'+value+'}')
                with self.assertRaisesRegex(ValueError,'nonfinite'):study.load_json(path)


if __name__=='__main__':unittest.main()
