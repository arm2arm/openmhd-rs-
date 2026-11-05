"""Tampered provenance, configuration and missing-evidence regression fixtures."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import run_m1_completion as study
from m1_mesh_cache import reuse_runs

class MeasurementTests(unittest.TestCase):
    def test_configuration_and_snapshot_time_must_match(self):
        c=dict(case='passive',n=4,jitter=0.,comoving=True)
        s=dict(case='passive_loop',operator='voronoi-face-ls-heun-v1',n=4,jitter=0.,comoving=True,time=1.,gas_evolved=False,velocity=[2,1])
        a=[dict(time=0.) for _ in range(16)];b=[dict(time=1.) for _ in range(16)]
        study.validate_run(c,s,a,b)
        for bad in [{**s,'n':8},{**s,'time':.5},{**s,'comoving':False}]:
            with self.assertRaises(ValueError):study.validate_run(c,bad,a,b)
        with self.assertRaises(ValueError):study.validate_run(c,s,a,b[:-1])
        b[3]['time']=.9
        with self.assertRaises(ValueError):study.validate_run(c,s,a,b)

    def test_missing_ladders_are_unexecuted(self):
        with patch.object(study,'reference',return_value=[]):
            result=study.measure(Path('/unused'),{})
        self.assertTrue(all(g['status'].startswith('unexecuted') for g in result['gates']))
        self.assertTrue(all(g['status'].startswith('unexecuted') for g in result['vortex_boost_pairs']))

    def test_failed_member_is_not_hidden_by_missing_resolutions(self):
        rows=[{'config':{'n':256},'status':'failed evolution'}]
        status=study.ladder_status(rows,[256,512,1024],False)
        self.assertTrue(status.startswith('fail'))
        self.assertIn('512',status)

    def fixture(self,p):
        (p/'x').mkdir();(p/'x/raw.csv').write_text('raw\n')
        r=dict(config={'case':'passive'},status='completed',artifacts_sha256={'raw.csv':study.sha(p/'x/raw.csv')})
        for name,value in [('manifest.json',{'x':r['config']}),('runs.json',{'x':r}),('summary.json',{'old':'summary'})]:study.dump(p/name,value)
        provenance=dict(revision='fixture',binary_sha256='fixture',external_reference_hashes={},result_sha256={n:study.sha(p/n) for n in ('manifest.json','runs.json','summary.json')})
        study.dump(p/'provenance.json',provenance)
        return r

    def test_reanalysis_preserves_original_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.fixture(p)
            with patch.object(study,'measure',return_value={'corrected':True}): study.reanalyze(p)
            self.assertEqual(json.loads((p/'execution_summary.json').read_text()),{'old':'summary'})
            for file in ['x/raw.csv','runs.json','execution_summary.json']:
                before=(p/file).read_bytes();(p/file).write_bytes(before+b' ')
                with self.assertRaises(ValueError):study.reanalyze(p)
                (p/file).write_bytes(before)

    def test_reuse_checks_configuration_and_raw_hashes(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);src=p/'source';src.mkdir();r=self.fixture(src);out=p/'out';out.mkdir()
            copied=reuse_runs(src,out,{'x':r['config']});self.assertIn('execution_origin',copied['x'])
            bad=p/'bad';bad.mkdir();(src/'x/raw.csv').write_text('changed')
            with self.assertRaises(ValueError):reuse_runs(src,bad,{'x':r['config']})

if __name__=='__main__':unittest.main()
