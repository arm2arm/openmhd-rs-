"""Execution provenance must distinguish HLL from historical HLLD results."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import run_m1_bounded as bounded
import run_m1_campaign as campaign
from run_m1_physics import configurations as physics
from run_m1_wave_loop import HLL_PROFILE, riemann_arguments, riemann_matches, with_riemann
from run_projection_screening import configurations as screening
from run_shock_repro import configurations as shocks
from run_shock_symmetry import configurations as symmetry


class FluxConfiguration(unittest.TestCase):
    def test_routing_changes_only_the_explicit_candidate_flux(self):
        families=[(shocks,(HLL_PROFILE,)),(screening,((1.,),())),(physics,(True,HLL_PROFILE))]
        for builder,args in families:
            original=builder(*args);selected=builder(*args,riemann='hll')
            self.assertEqual(set(original),set(selected))
            for name,c in original.items():
                self.assertNotIn('riemann_solver',c)
                self.assertEqual(riemann_arguments(c),[])
                self.assertEqual(selected[name],dict(c,riemann_solver='hll'))
                self.assertEqual(riemann_arguments(selected[name]),['--riemann','hll'])
        selected=symmetry('hll');original=symmetry()
        for name,c in selected.items():
            self.assertEqual(c,dict(original[name],riemann_solver='hll') if c['profile']==HLL_PROFILE else original[name])
        for _,tail,_,_,_ in bounded.stages(HLL_PROFILE,1.,True,riemann='hll'):
            self.assertEqual(tail[tail.index('--riemann')+1],'hll')
        for _,tail,_,_,_ in bounded.stages(HLL_PROFILE,1.,True):self.assertNotIn('--riemann',tail)
        self.assertEqual(campaign.evolution_options(),campaign.EVOLUTION)
        self.assertEqual(campaign.evolution_options('hll'),[*campaign.EVOLUTION,'--riemann','hll'])

    def test_missing_wrong_or_unsupported_flux_metadata_is_rejected(self):
        base=dict(profile=HLL_PROFILE);hll=dict(base,riemann_solver='hll')
        self.assertTrue(riemann_matches(base,{}))
        self.assertTrue(riemann_matches(hll,dict(riemann_solver='hll-comparator-v1')))
        for actual in ({},dict(riemann_solver='hlld'),dict(riemann_solver='unknown')):
            self.assertFalse(riemann_matches(hll,actual))
        self.assertFalse(riemann_matches(base,dict(riemann_solver='hll-comparator-v1')))
        for solver in ('bad',None):
            with self.assertRaises(ValueError):with_riemann({'a':base},solver)
        with self.assertRaises(ValueError):with_riemann({'a':dict(profile='paper-global-v2')},'hll')

    def test_parent_gate_rejects_mixed_manifest_or_binary_flux(self):
        configs=screening((1.,),(),riemann='hll')
        runs={n:dict(config=c,status='completed',summary=dict(profile=HLL_PROFILE,
              projection_screening=1.,riemann_solver='hll-comparator-v1')) for n,c in configs.items()}
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp)
            def save():
                (dest/'manifest.json').write_text(json.dumps(configs))
                (dest/'runs.json').write_text(json.dumps(runs))
            save()
            self.assertTrue(bounded.execution_matches('waves_short',dest,HLL_PROFILE,1.,'hll'))
            self.assertFalse(bounded.execution_matches('waves_short',dest,HLL_PROFILE,1.))
            n=next(iter(configs));configs[n].pop('riemann_solver');save()
            self.assertFalse(bounded.execution_matches('waves_short',dest,HLL_PROFILE,1.,'hll'))
            configs[n]['riemann_solver']='hll';runs[n]['summary'].pop('riemann_solver');save()
            self.assertFalse(bounded.execution_matches('waves_short',dest,HLL_PROFILE,1.,'hll'))

    def test_campaign_requires_matching_flux_profile_and_screening(self):
        r=dict(status='completed',positive_and_conservative=True,config=dict(profile=HLL_PROFILE,riemann_solver='hll'),
               summary=dict(profile=HLL_PROFILE,riemann_solver='hll-comparator-v1',projection_screening=1.))
        self.assertTrue(campaign.candidate_matches(r,'hll'))
        self.assertFalse(campaign.candidate_matches(r,'hlld'))
        summary=dict(runs={'a':r},pairs=[])
        self.assertTrue(campaign.wave_checks(summary,1,0,riemann='hll')['execution_configuration'])
        for section,key,value in [('config','riemann_solver','hlld'),('summary','riemann_solver','hlld'),
                                  ('summary','profile','paper-global-v2'),('summary','projection_screening',0.)]:
            bad=copy.deepcopy(r);bad[section][key]=value
            self.assertFalse(campaign.candidate_matches(bad,'hll'))
            summary['runs']['a']=bad
            self.assertFalse(campaign.wave_checks(summary,1,0,riemann='hll')['execution_configuration'])


if __name__=='__main__':unittest.main()
