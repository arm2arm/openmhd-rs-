"""Reject archives that hide incomplete runs or changed scientific figure inputs."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import archive_m1_completion as archive


def dump(path, value):
    path.write_text(json.dumps(value))


class ArchiveTests(unittest.TestCase):
    def fixture(self, root):
        (root/'run').mkdir()
        artifacts = ('run.log', 'initial.csv', 'final.csv', 'summary.json', 'polygons.csv')
        for name in artifacts:
            (root/'run'/name).write_text('fixture\n')
        dump(root/'run/projection.json', [{'rho': 1.}])
        run = {'config': {'case': 'vortex'}, 'status': 'completed', 'exit_code': 0,
               'sha256': {n: archive.sha(root/'run'/n) for n in artifacts}}
        dump(root/'manifest.json', {'run': run['config']})
        dump(root/'runs.json', {'run': run})
        measured = copy.deepcopy(run)
        measured['projection_sha256'] = archive.sha(root/'run/projection.json')
        dump(root/'summary.json', {'runs': {'run': measured}})
        self.seal(root)
        return run

    def seal(self, root):
        dump(root/'provenance.json', {'result_sha256': {
            n: archive.sha(root/n) for n in ('manifest.json', 'runs.json', 'summary.json')}})

    def test_valid_snapshot_keeps_verified_bytes_after_source_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.fixture(root)
            _, captured = archive.verify(root)
            before = captured['run/projection.json']
            dump(root/'run/projection.json', [{'rho': 999.}])
            self.assertEqual(captured['run/projection.json'], before)
            self.assertNotEqual(before, (root/'run/projection.json').read_bytes())
            with self.assertRaises(ValueError): archive.verify(root)

    def test_projection_must_exist_and_be_sealed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.fixture(root)
            p = root/'run/projection.json'; raw = p.read_bytes(); p.unlink()
            with self.assertRaises(ValueError): archive.verify(root)
            p.write_bytes(raw)
            s = archive.load(root/'summary.json')
            del s['runs']['run']['projection_sha256']
            dump(root/'summary.json', s); self.seal(root)
            with self.assertRaises(ValueError): archive.verify(root)

    def test_terminal_status_exit_code_and_artifacts_are_required(self):
        for status, code, remove in [('running', 0, None), ('completed', 1, None),
                                     ('failed evolution', 0, None), ('completed', 0, 'final.csv')]:
            with self.subTest(status=status, code=code, remove=remove), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); run = self.fixture(root)
                run.update(status=status, exit_code=code)
                if remove: del run['sha256'][remove]
                dump(root/'runs.json', {'run': run}); self.seal(root)
                with self.assertRaises(ValueError): archive.verify(root)

    def test_failed_evolution_is_retained_as_a_terminal_outcome(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); run = self.fixture(root)
            run.update(status='failed evolution', exit_code=1)
            run['sha256'] = {'run.log': run['sha256']['run.log']}
            dump(root/'runs.json', {'run': run})
            dump(root/'summary.json', {'runs': {'run': run}}); self.seal(root)
            records, _ = archive.verify(root)
            self.assertEqual(records['run']['status'], 'failed evolution')

    def test_wave_ledger_schema_and_conflicting_code_fields(self):
        for status, code in [('completed', 0), ('failed', 1)]:
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); run = self.fixture(root)
                run['config'] = {'case': 'alfven', 'dt': 0.0001}
                run.update(status=status, returncode=code)
                del run['exit_code']
                dump(root/'manifest.json', {'run': run['config']})
                dump(root/'runs.json', {'run': run})
                dump(root/'summary.json', {'runs': {'run': run}}); self.seal(root)
                archive.verify(root)
                run['exit_code'] = code+1
                dump(root/'runs.json', {'run': run}); self.seal(root)
                with self.assertRaises(ValueError): archive.verify(root)

    def test_measurement_input_digests_are_checked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.fixture(root)
            (root/'execution_provenance.json').write_bytes((root/'provenance.json').read_bytes())
            (root/'execution_summary.json').write_bytes((root/'summary.json').read_bytes())
            analysis = {key: archive.sha(root/name) for key, name in {
                'summary_sha256': 'summary.json', 'execution_provenance_sha256': 'execution_provenance.json',
                'execution_summary_sha256': 'execution_summary.json', 'raw_runs_sha256': 'runs.json'}.items()}
            dump(root/'measurement_provenance.json', analysis); archive.verify(root)
            for key in ('execution_summary_sha256', 'raw_runs_sha256'):
                dump(root/'measurement_provenance.json', {**analysis, key: '0'*64})
                with self.assertRaises(ValueError): archive.verify(root)

    def test_reuse_and_interruption_records_are_not_dropped(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.fixture(root)
            dump(root/'external_stop.json', {'reason': 'external diagnostic stop'})
            _, captured = archive.verify(root)
            self.assertIn('external_stop.json', captured)
            p = archive.load(root/'provenance.json')
            p['reuse_origin_sha256'] = '0'*64
            dump(root/'provenance.json', p)
            dump(root/'reuse_origin.json', {'origin': 'tampered'})
            with self.assertRaises(ValueError): archive.verify(root)


if __name__ == '__main__':
    unittest.main()
