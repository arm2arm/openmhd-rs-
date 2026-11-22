"""Prospective metadata controls for canonical scripts/ location; REANA only.

Synthetic envelopes below contain no evaluated geometry or passing physics.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('geometry_reference_job',
    ROOT / 'reana/galaxy_geometry3_reference_case.py')
job = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(job)


def buffers():
    paths = {'reference.py': 'scripts/galaxy_geometry3_reference.py',
             'design.json': 'docs/galaxy/fixtures/geometry3_analytic_v1.json',
             'launcher.py': 'reana/galaxy_test_case.py',
             'supervisor.py': 'tools/m1_evidence/reana_metadata_job.py',
             'runner.py': 'reana/galaxy_geometry3_reference_case.py'}
    value = {name:(ROOT / path).read_bytes() for name,path in paths.items()}
    case = dict(schema='openmhd.geometry3-reference-case.v1', selection=job.catalog()[0],
                resources=dict(job.RESOURCES), source_revision='1'*40,
                prerequisite_receipts={name:'2'*64 for name in
                    ('m1_acceptance','reference_source_review','reference_arithmetic_output_review',
                     'job_source_review','job_method_output_review')},
                candidate_invoked=False, component_accepted=False)
    # This is a nonphysical schema control, never an executed reference packet.
    value['case.json'] = job.encode(case)
    return value


def payload(value):
    return job.encode(dict(schema='openmhd.geometry3-reference-job-inputs.v1',
                           input_sha256={name:job.sha(raw) for name,raw in value.items()}))


def changed_case(value, change):
    result = dict(value)
    case = job.parse(value['case.json'])
    change(case)
    result['case.json'] = job.encode(case)
    return result


def stage(work, value):
    for name,raw in value.items():
        (work / name).write_bytes(raw)
    (work / 'payload.json').write_bytes(payload(value))


class GeometryReferenceJobMetadataTests(unittest.TestCase):
    def test_catalog_has252_unique_literal_names_and_transform_metadata(self):
        rows = job.catalog()
        self.assertEqual(len(rows),252)
        self.assertEqual(len({row['name'] for row in rows}),252)
        self.assertEqual({name:sum(row['fixture']==name for row in rows) for name in job.FIXTURES},
                         {name:36 for name in job.FIXTURES})
        self.assertEqual(rows[0]['name'],'periodic_one_cell_self_images__s0__pxyz__t0')
        self.assertEqual(rows[-1]['name'],'bounded_oblique_bisector__s2__pzyx__t1')

    def test_schema_positive_uses_real_pinned_sources_without_reference_evaluation(self):
        value = buffers()
        case = job.validate_inputs(value,payload(value))
        self.assertEqual(case['selection'],job.catalog()[0])
        self.assertFalse(case['candidate_invoked'])
        self.assertFalse(case['component_accepted'])

    def test_resealed_altered_reference_or_supervisor_source_is_rejected(self):
        original = buffers()
        for name in job.PINS:
            value = dict(original)
            value[name] += b'\n'
            with self.assertRaisesRegex(ValueError,'Pinned reference/design/launcher/supervisor source'):
                job.validate_inputs(value,payload(value))

    def test_exact_payload_and_input_inventory_reject_missing_extra_and_changed_bytes(self):
        original = buffers()
        missing = dict(original)
        del missing['design.json']
        with self.assertRaisesRegex(ValueError,'Exact reference-job input inventory'):
            job.validate_inputs(missing,payload(missing))
        extra = dict(original, unrelated=b'fixture')
        with self.assertRaisesRegex(ValueError,'Exact reference-job input inventory'):
            job.validate_inputs(extra,payload(extra))
        changed = dict(original)
        changed['case.json'] += b'\n'
        with self.assertRaisesRegex(ValueError,'Exact input digests'):
            job.validate_inputs(changed,payload(original))

    def test_bool_indices_and_resource_values_cannot_equal_integer_controls(self):
        original = buffers()
        changes = (
            lambda c:c['selection'].update(scale_index=False),
            lambda c:c['resources'].update(threads=True),
            lambda c:c['resources'].update(timeout_seconds=True),
        )
        for change in changes:
            value = changed_case(original,change)
            with self.assertRaisesRegex(ValueError,'Integer selection indices|Exact declared reference resources'):
                job.validate_inputs(value,payload(value))

    def test_changed_case_label_or_unregistered_transform_is_rejected(self):
        original = buffers()
        for change in (lambda c:c['selection'].update(name='wrong'),
                       lambda c:c['selection'].update(permutation='xxx'),
                       lambda c:c['selection'].update(scale_index=3)):
            value = changed_case(original,change)
            with self.assertRaisesRegex(ValueError,'Exact registered reference selection'):
                job.validate_inputs(value,payload(value))

    def test_scope_and_declared_receipts_cannot_turn_into_acceptance(self):
        original = buffers()
        for change,expected in (
                (lambda c:c.update(component_accepted=True),'Reference-only nonaccepting scope'),
                (lambda c:c.update(candidate_invoked=True),'Reference-only nonaccepting scope'),
                (lambda c:c['prerequisite_receipts'].update(job_source_review='bad'),'Declared prerequisite digest encoding')):
            value = changed_case(original,change)
            with self.assertRaisesRegex(ValueError,expected):
                job.validate_inputs(value,payload(value))

    def test_duplicate_keys_and_nonfinite_json_are_rejected(self):
        for raw,expected in ((b'{"x":1,"x":2}','Repeated JSON key'),
                             (b'{"x":NaN}','Nonfinite JSON')):
            with self.assertRaisesRegex(ValueError,expected):
                job.parse(raw)

    def test_regular_input_reader_rejects_links_and_parent_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            (work/'real').write_bytes(b'fixture')
            (work/'link').symlink_to(work/'real')
            with self.assertRaisesRegex(ValueError,'Linked path rejected'):
                job.regular_bytes(work,'link')
            with self.assertRaisesRegex(ValueError,'Safe relative path'):
                job.regular_bytes(work,'../real')

    def test_reference_transport_has_exact_ten_paths_and_retains_readonly_boundary(self):
        spec = importlib.util.spec_from_file_location('geometry_reference_adapter_control',
            ROOT/'tools/galaxy_evidence/geometry_reference_readonly_adapter.py')
        adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adapter)
        self.assertEqual(len(adapter.ARTIFACTS),10)
        for name in adapter.ARTIFACTS:
            self.assertEqual(adapter.artifact_path(name),name)
        for name in ('../case.json','outputs/reference/../reference.json','source.tar.gz',
                     'outputs/galaxy-preflight/preflight.json','outputs/reference/new.json'):
            with self.assertRaises(adapter.native.base.AdapterError):
                adapter.artifact_path(name)
        self.assertIs(adapter.native.artifact_path,adapter.artifact_path)

    def test_prelaunch_input_failure_has_typed_failed_nonaccepting_envelope(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            (work/'payload.json').write_bytes(b'{}\n')
            self.assertEqual(job.run(work),1)
            result = job.parse((work/'outputs/result.json').read_bytes())
            command = job.parse((work/'outputs/command.json').read_bytes())
            self.assertEqual(result['status'],'failed')
            self.assertFalse(result['component_accepted'])
            self.assertEqual(command,{'status':'not_launched'})
            self.assertTrue((work/'outputs/artifacts.sha256.json').is_file())

    def test_escaping_launch_retains_unknown_command_and_partial_output(self):
        calls = []
        class FakeLauncher:
            @staticmethod
            def persist(path,value):
                path.write_bytes(job.encode(value))
            @staticmethod
            def launch_native(supervisor,argv,work,environment,output,timeout,links):
                calls.append((argv,timeout,links))
                FakeLauncher.persist(output/'command.json',dict(status='unknown_closure',outcome='unknown',
                    cleanup={'writers_settled':False},external_terminal_evidence_required=True))
                (output/'stdout.txt').write_bytes(b'nonphysical partial launch marker\n')
                raise RuntimeError('fixture-launch-unknown')
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            stage(work,buffers())
            with patch.object(job,'load_module',side_effect=[FakeLauncher,object()]):
                code = job.run(work)
            self.assertEqual(code,1)
            self.assertEqual(len(calls),1)
            self.assertEqual(calls[0][1],300)
            self.assertEqual(calls[0][0][1:], [str(work/'reference.py'),'--design',str(work/'design.json'),
                '--case',job.catalog()[0]['name'],'--output',str(work/'outputs/reference')])
            result = job.parse((work/'outputs/result.json').read_bytes())
            self.assertEqual(result['error'],'fixture-launch-unknown')
            self.assertTrue(result['external_terminal_evidence_required'])
            self.assertEqual((work/'outputs/stdout.txt').read_bytes(),b'nonphysical partial launch marker\n')

    def test_successful_fake_command_without_actual_reference_cannot_complete(self):
        class FakeLauncher:
            @staticmethod
            def persist(path,value):
                path.write_bytes(job.encode(value))
            @staticmethod
            def launch_native(supervisor,argv,work,environment,output,timeout,links):
                row = dict(status='complete',outcome='success',returncode=0,cleanup=dict(
                    direct_child_reaped=True,writers_settled=True,leader_held_until_group_close=True,
                    group_authority_lost=False))
                FakeLauncher.persist(output/'command.json',row)
                return row
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            stage(work,buffers())
            with patch.object(job,'load_module',side_effect=[FakeLauncher,object()]):
                code = job.run(work)
            self.assertEqual(code,1)
            result = job.parse((work/'outputs/result.json').read_bytes())
            self.assertEqual(result['error'],'Exact complete reference output inventory')
            self.assertFalse(result['component_accepted'])
            self.assertNotIn('reference_case_evaluated',result)

    def test_failed_reference_status_and_wrong_body_digest_reach_distinct_rejections(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            reference = output/'reference'
            reference.mkdir()
            raw = {'status.json':job.encode(dict(schema='openmhd.geometry3.reference-execution.v1',
                        status='failed',case=job.catalog()[0]['name'],source_sha256=job.PINS['reference.py'],
                        candidate_invoked=False,component_accepted=False)),
                   'input.json':b'{}\n','reference.json':b'{}\n'}
            manifest = {name:{'sha256':job.sha(data),'bytes':len(data)} for name,data in raw.items()}
            for name,data in raw.items():
                (reference/name).write_bytes(data)
            (reference/'sha256.json').write_bytes(job.encode(manifest))
            case = job.parse(buffers()['case.json'])
            with self.assertRaisesRegex(ValueError,'Actual successful reference status/source'):
                job.validate_reference(output,case)
            manifest['input.json']['sha256'] = '0'*64
            (reference/'sha256.json').write_bytes(job.encode(manifest))
            with self.assertRaisesRegex(ValueError,'Actual reference body digest and size'):
                job.validate_reference(output,case)


if __name__ == '__main__':
    unittest.main()
