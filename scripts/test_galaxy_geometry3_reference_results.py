"""NONPHYSICAL metadata controls; no numerical-reference or workflow evidence.

Import loads only the future canonical metadata modules. All fixtures/mocks run
only inside separately selected future REANA methods. Empty illustrative tables
exercise one-case schema joins, never compute geometry or supply a passing252
packet, real runtime/certificate, scientific result or external provenance.
"""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('geometry_reference_results_control',
    ROOT / 'tools/galaxy_evidence/geometry_reference_results.py')
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)

UUID = '00000000-0000-4000-8000-000000000001'
OTHER_UUID = '00000000-0000-4000-8000-000000000002'
WORKFLOW = 'nonphysical-schema-control-0000.1'


class GeometryReferenceResultsTests(unittest.TestCase):
    def job(self):
        return r.c.load_module('geometry_reference_unit_job', ROOT / r.JOB)

    def change(self, values, name, modify):
        value = r.c.parse(values[name])
        modify(value)
        values[name] = r.c.encode(value)

    def seal(self, values):
        # Reseal metadata hashes so negative controls reach the named inner guard.
        prefix = 'outputs/reference/'
        values[prefix + 'sha256.json'] = r.c.encode({n[len(prefix):]: r.descriptor(raw)
            for n, raw in values.items() if n.startswith(prefix) and not n.endswith('/sha256.json')})
        result = r.c.parse(values['outputs/result.json'])
        result['reference_outputs'] = {n[len(prefix):]: r.descriptor(raw)
            for n, raw in values.items() if n.startswith(prefix)}
        result['runtime_sha256'] = r.p.sha(values['outputs/runtime.json'])
        command = r.c.parse(values['outputs/command.json'])
        command['links']['runtime'] = result['runtime_sha256']
        values['outputs/command.json'] = r.c.encode(command)
        values['outputs/result.json'] = r.c.encode(result)
        values['outputs/artifacts.sha256.json'] = r.c.encode({n: r.descriptor(raw)
            for n, raw in values.items() if n != 'outputs/artifacts.sha256.json'})
        return values

    def artifact_fixture(self, work):
        """Private one-case metadata boundary: all geometry tables deliberately empty."""
        work.mkdir(parents=True)
        j = self.job()
        case = dict(schema='openmhd.geometry3-reference-case.v1', selection=r.p.catalog()[0],
            resources=dict(j.RESOURCES), source_revision='a' * 40,
            prerequisite_receipts={n: 'b' * 64 for n in r.p.RECEIPTS[:5]},
            candidate_invoked=False, component_accepted=False)
        buffers = {n: (ROOT / path).read_bytes() for n, path in r.p.SOURCE_PATHS.items()
                   if n != 'preparer.py'}
        buffers['case.json'] = r.p.encode(case)
        payload = r.p.encode(dict(schema='openmhd.geometry3-reference-job-inputs.v1',
                                 input_sha256={n: r.p.sha(raw) for n, raw in buffers.items()}))
        for name, raw in {**buffers, 'payload.json': payload}.items():
            r.p.put(work, name, raw)
        runtime = dict(schema='openmhd.geometry3-reference-runtime.v1', optimized=0,
            executable=sys.executable, python='NONPHYSICAL metadata schema control',
            system='Linux', machine='NONPHYSICAL', release='NONPHYSICAL', image=r.p.IMAGE,
            image_and_resources_are_declared_labels=True, declared_resources=dict(j.RESOURCES),
            visible_cpus=1, thread_environment={n: '1' for n in r.THREADS},
            prerequisite_receipts_declared_only=True, source_revision=case['source_revision'],
            payload_sha256=r.p.sha(payload), input_sha256={n: r.p.sha(raw) for n, raw in buffers.items()},
            job_path=str(work / 'runner.py'), **{'cpu.max': None, 'memory.max': None})
        runtime_raw = r.c.encode(runtime)
        command = dict(schema='openmhd.metadata-command.v1', outcome='success', returncode=0,
            external_terminal_evidence_required=False, pid=7, process_group=7,
            cwd=str(work), command=[sys.executable, str(work / 'reference.py'), '--design',
                str(work / 'design.json'), '--case', case['selection']['name'], '--output',
                str(work / 'outputs/reference')], timeout_seconds=300, timeout_scope='direct-child-wait',
            started_utc='2026-01-01T00:00:01+00:00', finished_utc='2026-01-01T00:00:02+00:00',
            duration_seconds=1, links=dict(runtime=r.p.sha(runtime_raw), payload=r.p.sha(payload),
                **{n: r.p.sha(raw) for n, raw in buffers.items()}),
            cleanup=dict(writers_settled=True, direct_child_reaped=True,
                leader_held_until_group_close=True, group_authority_lost=False, remaining_live_pids=[],
                leader_identity=dict(pid=7, process_group=7, session=7, starttime='123')))
        inputs = dict(schema='openmhd.geometry3.literal-input.v1', case=case['selection'],
                      design_sha256=j.PINS['design.json'])
        input_raw = r.c.encode(inputs)
        target = dict(schema='openmhd.geometry3.exact-reference.v1', case=case['selection'],
            design_sha256=j.PINS['design.json'], input_sha256=r.p.sha(input_raw),
            candidate_invoked=False, component_accepted=False, cells=[], faces=[])
        status = dict(schema='openmhd.geometry3.reference-execution.v1', status='complete',
            case=case['selection']['name'], source_sha256=j.PINS['reference.py'], cells=0, faces=0,
            candidate_invoked=False, component_accepted=False)
        result = dict(schema='openmhd.geometry3-reference-job-result.v1', status='complete', case=case,
            reference_case_evaluated=True, candidate_invoked=False, component_accepted=False,
            external_execution_provenance_verified=False, payload_sha256=r.p.sha(payload),
            runtime_sha256=r.p.sha(runtime_raw), reference_outputs={},
            started_utc='2026-01-01T00:00:00+00:00', finished_utc='2026-01-01T00:00:03+00:00')
        values = {'outputs/runtime.json': runtime_raw, 'outputs/command.json': r.c.encode(command),
            'outputs/result.json': r.c.encode(result), 'outputs/stdout.txt': b'NONPHYSICAL schema input\n',
            'outputs/stderr.txt': b'', 'outputs/reference/input.json': input_raw,
            'outputs/reference/reference.json': r.c.encode(target),
            'outputs/reference/status.json': r.c.encode(status)}
        return self.seal(values), j, case

    def transport_fixture(self, root, sources, number=0, action='observe', path=None, raw=None):
        root.mkdir(parents=True, exist_ok=True)
        start = datetime(2026, 2, 1, tzinfo=timezone.utc) + timedelta(seconds=number * 5)
        if raw is None:
            raw = r.c.encode(dict(schema='openmhd.galaxy-server-observation.v1', origin='server',
                observed_utc=(start + timedelta(seconds=2)).isoformat(), matches=[dict(id=UUID,
                name=WORKFLOW.removesuffix('.1'), version=1, workflow=WORKFLOW, status='finished')]))
        label = 'transport/' + str(number).zfill(4) + '.json'
        output = 'downloads/' + str(number).zfill(4) + '.body'
        argv = [sys.executable, '-B', str((ROOT / r.ADAPTER).resolve()), action,
                '--workflow', WORKFLOW, '--output', str(root / output)]
        if path is not None:
            argv += ['--path', path]
        diagnostic = dict(schema='openmhd.galaxy-get-diagnostic.v1', outcome='success', code='completed',
            action=action, workflow=WORKFLOW, requested_path=path, workflow_ids=[UUID], http_status=None,
            page_count=1, received_bytes=len(raw), retained_bytes=len(raw), partial_file=None,
            started_utc=(start + timedelta(seconds=1)).isoformat(),
            finished_utc=(start + timedelta(seconds=3)).isoformat())
        row = dict(schema='openmhd.geometry3-reference-transport.v1', action=action, workflow=WORKFLOW,
            remote_path=path, output=output, argv=argv, cwd=str(root),
            source_sha256={n: r.p.sha(v) for n, v in sources.items()}, timeout_seconds=300,
            started_utc=start.isoformat(), finished_utc=(start + timedelta(seconds=4)).isoformat(),
            outcome='success', returncode=0, direct_process_settled=True, captured_streams_closed=True,
            external_terminal_evidence_required=False,
            interpreter=dict(executable=sys.executable, python=sys.version, optimized=0),
            stdout=label.removesuffix('.json') + '.stdout',
            stderr=label.removesuffix('.json') + '.stderr', output_sha256=r.p.sha(raw))
        for name, body in ((output, raw), (row['stdout'], r.c.encode(diagnostic)),
                           (row['stderr'], r.c.encode(dict(schema='openmhd.galaxy-unavailable-diagnostic.v1',
                               unretained_bytes=0, sha256=r.p.sha(b''))))):
            r.p.put(root, name, body)
            if name in (row['stdout'], row['stderr']):
                row[('stdout' if name == row['stdout'] else 'stderr') + '_sha256'] = r.p.sha(body)
        r.p.put(root, label, r.c.encode(row))
        return label, row

    def capture_fixture(self, root):
        values, job, case = self.artifact_fixture(root / 'input')
        directory = root / 'capture/case_0000'
        sources = r.host_sources()
        labels = []
        for n in range(12):
            name = None if n in (0, 11) else r.p.ARTIFACTS[n - 1]
            label, _ = self.transport_fixture(directory, sources, n,
                'observe' if name is None else 'download', name, None if name is None else values[name])
            labels.append(label)
        row = dict(workflow=WORKFLOW, directory='case_0000', selection=case['selection'], status='passed',
            files=dict(zip(r.p.ARTIFACTS, labels[1:-1])), uuid=UUID, before=labels[0], after=labels[-1])
        expected = dict(workflow=WORKFLOW, directory='case_0000', selection=case['selection'])
        return directory, row, expected, sources, job, root / 'input'

    def boundary(self, root):
        # Private incomplete one-case boundary ONLY for public failure handling;
        # mocked plan validation cannot yield a passing whole252 packet.
        cases = root / 'cases'
        _, _, case = self.artifact_fixture(cases / 'case_0000')
        sources = r.host_sources()
        for name, source in (('runner.py', r.JOB), ('preparer.py', 'tools/galaxy_evidence/prepare_geometry3_reference.py')):
            r.p.put(cases, 'context/source/' + name, sources[source])
        submission = cases / 'submission.json'
        r.p.put(cases, 'submission.json', r.c.encode({WORKFLOW: dict(status='submission uncertain',
            error='NONPHYSICAL original journal control')}))
        plan = dict(cases=[dict(workflow=WORKFLOW, directory='case_0000', selection=case['selection'])])
        return cases, submission, plan, sources

    def pending(self, root, action, workflow, remote_path, sources):
        return r.c.encode(dict(schema='openmhd.galaxy-server-observation.v1', origin='server', matches=[
            dict(id=UUID, name=workflow.removesuffix('.1'), version=1, workflow=workflow, status='queued')])), \
            'transport/0000.json', UUID

    def test_one_case_schema_positive_is_explicitly_nonphysical(self):
        with tempfile.TemporaryDirectory() as temporary:
            values, job, _ = self.artifact_fixture(Path(temporary) / 'input')
            r.validate_artifacts(values, Path(temporary) / 'input', job)
            self.assertEqual(r.c.parse(values['outputs/reference/reference.json'])['cells'], [])
            self.assertFalse(r.c.parse(values['outputs/result.json'])['component_accepted'])

    def test_ten_artifacts_require_exact_inventory_and_actual_body_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            values, job, _ = self.artifact_fixture(Path(temporary) / 'input')
            r.validate_artifacts(values, Path(temporary) / 'input', job)
            for name in ('outputs/stdout.txt', 'outputs/reference/status.json'):
                changed = dict(values)
                changed[name] += b'changed'
                with self.assertRaisesRegex(ValueError, 'Every original reference artifact'):
                    r.validate_artifacts(changed, Path(temporary) / 'input', job)
            for mode in ('missing', 'extra'):
                changed = dict(values)
                if mode == 'missing':
                    changed.pop('outputs/stderr.txt')
                else:
                    changed['outputs/unlisted'] = b'x'
                with self.assertRaisesRegex(ValueError, 'Exact ten raw'):
                    r.validate_artifacts(changed, Path(temporary) / 'input', job)

    def test_reference_manifest_and_boolean_counts_are_not_equivalent(self):
        with tempfile.TemporaryDirectory() as temporary:
            values, job, _ = self.artifact_fixture(Path(temporary) / 'input')
            r.validate_artifacts(values, Path(temporary) / 'input', job)
            bad = dict(values)
            self.change(bad, 'outputs/reference/status.json', lambda x: x.update(cells=False))
            self.seal(bad)
            with self.assertRaisesRegex(ValueError, 'Reference counts'):
                r.validate_artifacts(bad, Path(temporary) / 'input', job)
            bad = dict(values)
            self.change(bad, 'outputs/reference/sha256.json', lambda x: x.pop('status.json'))
            result = r.c.parse(bad['outputs/result.json'])
            result['reference_outputs']['sha256.json'] = r.descriptor(bad['outputs/reference/sha256.json'])
            bad['outputs/result.json'] = r.c.encode(result)
            bad['outputs/artifacts.sha256.json'] = r.c.encode({n: r.descriptor(v) for n, v in bad.items()
                if n != 'outputs/artifacts.sha256.json'})
            with self.assertRaisesRegex(ValueError, 'Exact independent reference body closure'):
                r.validate_artifacts(bad, Path(temporary) / 'input', job)
            closed = Path(temporary) / 'empty_inventory'
            r.p.put(closed, 'empty', b'')
            r.c.close(closed)
            r.closed_inventory(closed)
            manifest = r.c.parse((closed / 'files.sha256.json').read_bytes())
            manifest['empty']['bytes'] = False
            (closed / 'files.sha256.json').write_bytes(r.c.encode(manifest))
            with self.assertRaisesRegex(ValueError, 'Closed inventory byte counts exclude Boolean'):
                r.closed_inventory(closed)

    def test_source_case_payload_and_result_links_reject_resealed_mutations(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / 'input'
            values, job, _ = self.artifact_fixture(work)
            r.validate_artifacts(values, work, job)
            for field, value in (('payload_sha256', '0' * 64), ('reference_case_evaluated', False),
                                 ('external_execution_provenance_verified', True)):
                bad = dict(values)
                self.change(bad, 'outputs/result.json', lambda x: x.update({field: value}))
                self.seal(bad)
                message = 'Result payload/runtime' if field == 'payload_sha256' else 'Actual complete reference-only'
                with self.assertRaisesRegex(ValueError, message):
                    r.validate_artifacts(bad, work, job)
            original = (work / 'reference.py').read_bytes()
            (work / 'reference.py').write_bytes(original + b'changed')
            with self.assertRaisesRegex(ValueError, 'Exact input digests'):
                r.validate_artifacts(values, work, job)

    def test_runtime_resources_threads_source_and_bool_types_are_exact(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / 'input'
            values, job, _ = self.artifact_fixture(work)
            r.validate_artifacts(values, work, job)
            for mutate in (lambda x: x.update(source_revision='0' * 40),
                           lambda x: x['declared_resources'].update(threads=True),
                           lambda x: x['thread_environment'].update(OMP_NUM_THREADS='2'),
                           lambda x: x.update(optimized=False)):
                bad = dict(values)
                self.change(bad, 'outputs/runtime.json', mutate)
                self.seal(bad)
                with self.assertRaisesRegex(ValueError, 'Actual unoptimized Linux reference runtime'):
                    r.validate_artifacts(bad, work, job)

    def test_command_argv_cwd_timeout_and_source_links_are_exact(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / 'input'
            values, job, _ = self.artifact_fixture(work)
            r.validate_artifacts(values, work, job)
            for mutate, message in ((lambda x: x['command'].append('--extra'), 'Actual one-case reference argv'),
                (lambda x: x.update(cwd='relative'), 'Actual one-case reference argv'),
                (lambda x: x.update(timeout_seconds=True), 'Actual one-case reference argv'),
                (lambda x: x['links'].update(payload='0' * 64), 'Original reference command/runtime/source')):
                bad = dict(values)
                self.change(bad, 'outputs/command.json', mutate)
                self.seal(bad)
                with self.assertRaisesRegex(ValueError, message):
                    r.validate_artifacts(bad, work, job)

    def test_unknown_closure_authority_loss_and_pid_aliases_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / 'input'
            values, job, _ = self.artifact_fixture(work)
            r.validate_artifacts(values, work, job)
            for mutate, message in ((lambda x: x['cleanup'].update(group_authority_lost=True), 'closed log writers'),
                (lambda x: x['cleanup'].update(writers_settled=None), 'closed log writers'),
                (lambda x: x.update(external_terminal_evidence_required=True), 'closed log writers'),
                (lambda x: x.update(pid=True), 'Held reference PID'),
                (lambda x: x['cleanup']['leader_identity'].update(starttime='0'), 'Held reference PID')):
                bad = dict(values)
                self.change(bad, 'outputs/command.json', mutate)
                self.seal(bad)
                with self.assertRaisesRegex(ValueError, message):
                    r.validate_artifacts(bad, work, job)

    def test_reference_status_design_selection_and_input_identity_are_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / 'input'
            values, job, _ = self.artifact_fixture(work)
            r.validate_artifacts(values, work, job)
            for name, mutate, message in (
                ('status.json', lambda x: x.update(status='failed'), 'Actual independent reference status/source'),
                ('reference.json', lambda x: x.update(design_sha256='0' * 64), 'Original rounded-input'),
                ('reference.json', lambda x: x.update(input_sha256='0' * 64), 'Original rounded-input'),
                ('input.json', lambda x: x['case'].update(scale_index=False), 'Original rounded-input')):
                bad = dict(values)
                self.change(bad, 'outputs/reference/' + name, mutate)
                if name == 'input.json':
                    self.change(bad, 'outputs/reference/reference.json',
                        lambda x: x.update(input_sha256=r.p.sha(bad['outputs/reference/input.json'])))
                self.seal(bad)
                with self.assertRaisesRegex(ValueError, message):
                    r.validate_artifacts(bad, work, job)

    def test_single_capture_positive_has_exact_twelve_ordered_receipts(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = self.capture_fixture(Path(temporary))
            r.validate_capture(*args)
            directory, row, expected, sources, job, inputs = args
            changed = copy.deepcopy(row)
            changed['files'].pop('outputs/runtime.json')
            with self.assertRaisesRegex(ValueError, 'Exact observe/ten-download/observe'):
                r.validate_capture(directory, changed, expected, sources, job, inputs)

    def test_capture_rejects_changed_uuid_version_and_nonfinished_observations(self):
        for mode in ('uuid', 'version', 'status'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                args = self.capture_fixture(Path(temporary))
                r.validate_capture(*args)
                directory, row, expected, sources, job, inputs = args
                record = r.c.parse(r.p.read(directory, row['before']))
                body = r.c.parse(r.p.read(directory, record['output']))
                body['matches'][0].update({'uuid': {'id': OTHER_UUID}, 'version': {'version': 2},
                                           'status': {'status': 'failed'}}[mode])
                raw = r.c.encode(body)
                (directory / record['output']).write_bytes(raw)
                record['output_sha256'] = r.p.sha(raw)
                diag = r.c.parse(r.p.read(directory, record['stdout']))
                diag.update(received_bytes=len(raw), retained_bytes=len(raw))
                diag_raw = r.c.encode(diag)
                (directory / record['stdout']).write_bytes(diag_raw)
                record['stdout_sha256'] = r.p.sha(diag_raw)
                (directory / row['before']).write_bytes(r.c.encode(record))
                message = {'uuid': 'Workflow UUID changed', 'version': 'Original workflow/version/UUID',
                           'status': 'Workflow must actually finish'}[mode]
                with self.assertRaisesRegex(ValueError, message):
                    r.validate_capture(directory, row, expected, sources, job, inputs)

    def test_transport_rejects_resealed_diagnostic_uuid_path_and_bool_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            sources = r.host_sources()
            root = Path(temporary) / 'case_0000'
            label, row = self.transport_fixture(root, sources)
            r.transport_body(root, label, WORKFLOW, UUID, 'observe', None, sources)
            original = r.p.read(root, row['stdout'])
            for mutate, message in ((lambda x: x.update(workflow_ids=[OTHER_UUID]), 'Exact reference transport UUID'),
                (lambda x: x.update(requested_path='outputs/result.json'), 'Typed credential-free adapter'),
                (lambda x: x.update(received_bytes=True), 'Diagnostic time/count/partial')):
                value = r.c.parse(original)
                mutate(value)
                raw = r.c.encode(value)
                (root / row['stdout']).write_bytes(raw)
                changed = copy.deepcopy(row)
                changed['stdout_sha256'] = r.p.sha(raw)
                (root / label).write_bytes(r.c.encode(changed))
                with self.assertRaisesRegex(ValueError, message):
                    r.transport_body(root, label, WORKFLOW, UUID, 'observe', None, sources)

    def test_transport_rejects_source_argv_time_and_noncanonical_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            sources = r.host_sources()
            root = Path(temporary) / 'case_0000'
            label, row = self.transport_fixture(root, sources)
            r.transport_body(root, label, WORKFLOW, UUID, 'observe', None, sources)
            for mutate, message in ((lambda x: x['source_sha256'].update({r.SELF: '0' * 64}), 'argv/source/time'),
                (lambda x: x['argv'].append('--extra'), 'argv/source/time'),
                (lambda x: x.update(finished_utc='2025-01-01T00:00:00+00:00'), 'argv/source/time'),
                (lambda x: x.update(output='downloads/other.body'), 'Canonical reference receipt/body/log')):
                changed = copy.deepcopy(row)
                mutate(changed)
                (root / label).write_bytes(r.c.encode(changed))
                with self.assertRaisesRegex(ValueError, message):
                    r.transport_body(root, label, WORKFLOW, UUID, 'observe', None, sources)

    def test_successful_capture_rejects_extra_receipt_body_and_partial(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = self.capture_fixture(Path(temporary))
            r.validate_capture(*args)
            for name in ('transport/9999.json', 'downloads/extra.body', 'downloads/0000.body.partial'):
                path = args[0] / name
                path.write_bytes(b'NONPHYSICAL extra receipt/body')
                with self.assertRaisesRegex(ValueError, 'unreferenced transport|Exact transport/log/download'):
                    r.validate_capture(*args)
                path.unlink()

    def test_timeout_retains_snapshot_partial_intent_and_no_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources, observations = r.host_sources(), []
            def timeout(argv, **kwargs):
                observations.append((list(argv), kwargs, r.c.parse((root / 'transport/0000.json').read_bytes())))
                (root / 'downloads/0000.body.partial').write_bytes(b'NONPHYSICAL partial')
                raise subprocess.TimeoutExpired(argv, 300, output=b'latest cumulative output', stderr=b'partial error')
            with mock.patch.object(r.subprocess, 'run', side_effect=timeout) as call:
                with self.assertRaisesRegex(ValueError, 'Unsuccessful reference transport'):
                    r.invoke(root, 'observe', WORKFLOW, None, sources)
            self.assertEqual(call.call_count, 1)
            self.assertEqual(observations[0][1]['timeout'], 300)
            self.assertEqual(observations[0][2]['outcome'], 'pending_launch')
            row = r.c.parse((root / 'transport/0000.json').read_bytes())
            self.assertEqual((row['outcome'], row['error_type']), ('timeout', 'TimeoutExpired'))
            self.assertIsNone(row['finished_utc'])
            self.assertFalse(row['captured_streams_closed'])
            self.assertTrue(row['external_terminal_evidence_required'])
            self.assertEqual((root / 'downloads/0000.body.partial').read_bytes(), b'NONPHYSICAL partial')
            retained = r.c.parse((root / row['stdout']).read_bytes())
            self.assertEqual(retained['sha256'], r.p.sha(b'latest cumulative output'))
            self.assertFalse((root / 'downloads/0000.body').exists())

    def test_nonzero_and_unstructured_output_are_retained_without_raw_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = r.host_sources()
            raw = b'NONPHYSICAL unstructured credential-shaped text https://invalid/?token=fixture'
            with mock.patch.object(r.subprocess, 'run', return_value=subprocess.CompletedProcess([], 7, raw, raw)) as call:
                with self.assertRaisesRegex(ValueError, 'Unsuccessful reference transport'):
                    r.invoke(root, 'observe', WORKFLOW, None, sources)
            self.assertEqual(call.call_count, 1)
            row = r.c.parse((root / 'transport/0000.json').read_bytes())
            self.assertEqual(row['returncode'], 7)
            self.assertEqual(row['outcome'], 'nonzero')
            for name in (row['stdout'], row['stderr']):
                stored = (root / name).read_bytes()
                self.assertNotIn(raw, stored)
                self.assertEqual(r.c.parse(stored), dict(schema='openmhd.galaxy-unavailable-diagnostic.v1',
                    unretained_bytes=len(raw), sha256=r.p.sha(raw)))

    def test_escaping_call_preserves_exact_sentinel_and_unknown_closure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, observed = Path(temporary), []
            sources = r.host_sources()
            sentinel = RuntimeError('NONPHYSICAL escaping transport sentinel')
            def escape(argv, **kwargs):
                observed.append((list(argv), kwargs, r.c.parse((root / 'transport/0000.json').read_bytes())))
                raise sentinel
            with mock.patch.object(r.subprocess, 'run', side_effect=escape) as call:
                with self.assertRaises(RuntimeError) as caught:
                    r.invoke(root, 'observe', WORKFLOW, None, sources)
            self.assertIs(caught.exception, sentinel)
            self.assertEqual(call.call_count, 1)
            self.assertEqual(len(observed), 1)
            self.assertEqual(observed[0][0], [sys.executable, '-B', str((ROOT / r.ADAPTER).resolve()),
                'observe', '--workflow', WORKFLOW, '--output', str(root / 'downloads/0000.body')])
            self.assertEqual(observed[0][1], dict(cwd=root, capture_output=True, timeout=300, check=False))
            self.assertEqual(observed[0][2]['argv'], observed[0][0])
            self.assertEqual(observed[0][2]['source_sha256'], {n: r.p.sha(v) for n, v in sources.items()})
            self.assertEqual(observed[0][2]['outcome'], 'pending_launch')
            self.assertTrue(observed[0][2]['external_terminal_evidence_required'])
            row = r.c.parse((root / 'transport/0000.json').read_bytes())
            self.assertEqual((row['outcome'], row['error_type']), ('unknown_closure', 'RuntimeError'))
            self.assertIsNone(row['finished_utc'])
            self.assertIsNone(row['direct_process_settled'])
            self.assertFalse(row['captured_streams_closed'])
            self.assertTrue(row['external_terminal_evidence_required'])

    def test_start_failure_is_typed_unknown_and_never_retried(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sentinel = FileNotFoundError('NONPHYSICAL no adapter launch')
            with mock.patch.object(r.subprocess, 'run', side_effect=sentinel) as call:
                with self.assertRaises(FileNotFoundError) as caught:
                    r.invoke(root, 'observe', WORKFLOW, None, r.host_sources())
            self.assertIs(caught.exception, sentinel)
            self.assertEqual(call.call_count, 1)
            row = r.c.parse((root / 'transport/0000.json').read_bytes())
            self.assertEqual(row['error_type'], 'FileNotFoundError')
            self.assertIsNone(row['finished_utc'])
            self.assertTrue(row['external_terminal_evidence_required'])
            self.assertNotIn('pid', row)

    def test_preexisting_destination_is_never_owned_or_modified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cases, submission, plan, _ = self.boundary(root)
            output = root / 'existing'
            output.mkdir()
            (output / 'summary.json').write_bytes(b'preexisting user bytes')
            with mock.patch.object(r.p, 'validate_plan', return_value=plan):
                with self.assertRaises(FileExistsError):
                    r.collect(cases, submission, output)
            self.assertEqual({p.name for p in output.iterdir()}, {'summary.json'})
            self.assertEqual((output / 'summary.json').read_bytes(), b'preexisting user bytes')

    def test_post_mkdir_capture_failure_retains_original_journal_and_typed_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cases, submission, plan, _ = self.boundary(root)
            output = root / 'packet'
            sentinel = RuntimeError('NONPHYSICAL copy sentinel')
            with mock.patch.object(r.p, 'validate_plan', return_value=plan), \
                 mock.patch.object(r, 'tools_capture', side_effect=sentinel):
                with self.assertRaises(RuntimeError) as caught:
                    r.collect(cases, submission, output)
            self.assertIs(caught.exception, sentinel)
            result = r.c.parse((output / 'summary.json').read_bytes())
            self.assertEqual((result['status'], result['error_type']), ('failed', 'RuntimeError'))
            self.assertEqual(result['submission_sha256'], r.p.sha(submission.read_bytes()))
            self.assertEqual((output / 'submission_original.json').read_bytes(), submission.read_bytes())
            self.assertFalse(result['whole_catalog_passed'])
            self.assertTrue(result['external_terminal_evidence_required'])
            r.c.verify_closed(output)

    def test_final_publication_failure_invalidates_prior_manifest_without_fake_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cases, submission, plan, _ = self.boundary(root)
            output, observed = root / 'packet', []
            sentinel, original_close = RuntimeError('NONPHYSICAL final publication sentinel'), r.c.close
            def fail_after_close(path):
                observed.append(r.c.parse((path / 'summary.json').read_bytes()))
                original_close(path)
                if len(observed) == 1:
                    raise sentinel
            with mock.patch.object(r.p, 'validate_plan', return_value=plan), \
                 mock.patch.object(r, 'invoke', side_effect=self.pending), \
                 mock.patch.object(r.c, 'close', side_effect=fail_after_close):
                with self.assertRaises(RuntimeError) as caught:
                    r.collect(cases, submission, output)
            self.assertIs(caught.exception, sentinel)
            self.assertEqual(observed[0]['cases'][0]['status'], 'pending')
            self.assertFalse(observed[0]['whole_catalog_passed'])
            self.assertEqual(observed[-1]['status'], 'failed')
            self.assertTrue((output / 'files.failed.sha256.json').is_file())
            r.c.verify_closed(output)
            with self.assertRaisesRegex(ValueError, 'Complete reference-only metadata scope'):
                r.verify_results(output)

    def test_catalog_missing_duplicate_reorder_and_bool_selection_are_nonpassing(self):
        expected = [dict(workflow=f'nonphysical-{n:04d}.1', directory=f'case_{n:04d}', selection=s)
                    for n, s in enumerate(r.p.catalog())]
        rows = [dict(e, status='incomplete') for e in expected]
        r.catalog_rows(rows, expected)  # Metadata only; zero reference files or passing rows.
        for mode in ('missing', 'duplicate', 'reorder', 'bool', 'duplicate_uuid'):
            changed = copy.deepcopy(rows)
            if mode == 'missing':
                changed.pop()
            elif mode == 'duplicate':
                changed[1] = copy.deepcopy(changed[0])
            elif mode == 'reorder':
                changed[0], changed[1] = changed[1], changed[0]
            elif mode == 'bool':
                changed[0]['selection']['scale_index'] = False
            else:
                changed[0]['uuid'] = changed[1]['uuid'] = UUID
            with self.assertRaisesRegex(ValueError, 'Complete ordered252|Exact ordered reference case|Unique original reference workflow UUID'):
                r.catalog_rows(changed, expected)

    def test_scope_requires_literal_false_without_external_or_numerical_acceptance(self):
        # Scope-only envelope has no cases, files, runtime/certificate or whole-pass claim.
        value = dict(schema='openmhd.geometry3-reference-results.v1', status='complete',
            candidate_invoked=False, component_accepted=False, numerical_output_review_passed=False,
            external_prerequisite_truth_verified=False, external_terminal_evidence_required=False)
        r.summary_scope(value)
        for key in ('candidate_invoked', 'component_accepted', 'numerical_output_review_passed',
                    'external_prerequisite_truth_verified', 'external_terminal_evidence_required'):
            changed = dict(value, **{key: 0})
            with self.assertRaisesRegex(ValueError, 'Complete reference-only metadata scope'):
                r.summary_scope(changed)

    def test_input_or_helper_generation_changes_invalidate_owned_collection(self):
        for mode in ('input', 'helper'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                cases, submission, plan, sources = self.boundary(root)
                output, observed = root / 'packet', []
                changed_sources = dict(sources, **{r.SELF: sources[r.SELF] + b'changed'})
                def pending_and_change(*args):
                    observed.append(args[2])
                    if mode == 'input':
                        (cases / 'case_0000/payload.json').write_bytes(b'NONPHYSICAL changed generation')
                    return self.pending(*args)
                with mock.patch.object(r.p, 'validate_plan', return_value=plan), \
                     mock.patch.object(r, 'host_sources', side_effect=[sources,
                         changed_sources if mode == 'helper' else sources]), \
                     mock.patch.object(r, 'invoke', side_effect=pending_and_change):
                    with self.assertRaisesRegex(ValueError, 'Complete original input/submission/host-source generation fence'):
                        r.collect(cases, submission, output)
                self.assertEqual(observed, [WORKFLOW])
                self.assertEqual(r.c.parse((output / 'summary.json').read_bytes())['status'], 'failed')
                self.assertFalse(r.c.parse((output / 'summary.json').read_bytes())['whole_catalog_passed'])

    def test_offline_helper_generation_must_equal_retained_original_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = r.host_sources()
            expected = r.tools_capture(root, sources)
            self.assertEqual(r.tools_verify(root, expected), sources)
            changed = dict(sources, **{r.SELF: sources[r.SELF] + b'changed'})
            with mock.patch.object(r, 'host_sources', return_value=changed):
                with self.assertRaisesRegex(ValueError, 'exact original helper generation'):
                    r.tools_verify(root, expected)


if __name__ == '__main__':
    unittest.main()
