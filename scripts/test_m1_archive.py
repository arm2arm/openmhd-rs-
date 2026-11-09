#!/usr/bin/env python3
"""Integrity fixtures for execution versus remeasurement archive layers."""
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from archive_m1_completion import archive
from run_m1_wave_loop import dump,sha


class ArchiveIntegrity(unittest.TestCase):
    def fixture(self,root):
        source=root/'raw';checkout=root/'checkout';source.mkdir();checkout.mkdir()
        (checkout/'fixture.rs').write_text('// exact execution source\n')
        for name in ('manifest.json','runs.json'): dump(source/name,{})
        dump(source/'summary.json',{'measurement':'original'})
        provenance={'revision':'fixture','source_sha256':{'fixture.rs':sha(checkout/'fixture.rs')},
                    'result_sha256':{n:sha(source/n) for n in ('manifest.json','runs.json','summary.json')}}
        dump(source/'provenance.json',provenance)
        return source,checkout

    def test_remeasurement_retains_both_layers(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source,checkout=self.fixture(root)
            (source/'execution_provenance.json').write_bytes((source/'provenance.json').read_bytes())
            (source/'execution_summary.json').write_bytes((source/'summary.json').read_bytes())
            dump(source/'summary.json',{'measurement':'corrected'})
            dump(source/'measurement_provenance.json',{'summary_sha256':sha(source/'summary.json'),
                 'execution_provenance_sha256':sha(source/'execution_provenance.json'),'execution_summary_sha256':sha(source/'execution_summary.json')})
            dest=root/'archive';archive(source,checkout,dest)
            self.assertEqual(json.loads(gzip.decompress((dest/'summary.json.gz').read_bytes()))['measurement'],'corrected')
            self.assertEqual(json.loads(gzip.decompress((dest/'execution_summary.json.gz').read_bytes()))['measurement'],'original')
            hashes=json.loads((dest/'archive_sha256.json').read_text())
            self.assertIn('measurement_provenance.json',hashes)
            self.assertIn('execution_sources.tar.gz',hashes)
            self.assertTrue(all(sha(dest/name)==digest for name,digest in hashes.items()))

    def test_changed_source_or_result_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source,checkout=self.fixture(root)
            (checkout/'fixture.rs').write_text('changed')
            with self.assertRaisesRegex(ValueError,'changed source'): archive(source,checkout,root/'archive')
            dump(source/'runs.json',{'unexpected':'run'})
            with self.assertRaisesRegex(ValueError,'changed execution result'): archive(source,checkout,root/'archive')


if __name__=='__main__': unittest.main()
