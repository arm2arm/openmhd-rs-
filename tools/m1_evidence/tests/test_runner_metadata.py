"""REANA-only metadata controls; no physical M1 packet or acceptance is made.

All success-shaped server/result records below are explicitly synthetic UNIT
fixtures, not observations of REANA. Only observe-preflight's actual adapter
path can collect a real certificate. No import-time execution or credentials.
"""
import base64
import gzip
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS))
import prepare_metadata_reana as prepare
import reana_metadata_job as job

WHEN = '2026-11-22T00:00:00+00:00'
PLAIN = b'import unittest\nclass FixtureTests(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n'


class RunnerMetadataTests(unittest.TestCase):
    def source_fixture(self, root, unsafe=False, import_failure=False):
        """Small source-only UNIT package, never a scientific campaign."""
        sources = {name: PLAIN for name in job.TEST_FILES}
        if import_failure:
            sources[job.TEST_FILES[0]] += b'\nraise ImportError("UNIT import-failure control")\n'
        sources[job.JOB_NAME] = (TOOLS / 'reana_metadata_job.py').read_bytes()
        if unsafe:
            sources['../escape.txt'] = b'unsafe metadata fixture'
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w') as archive:
            for name, data in sources.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
        packed = gzip.compress(buffer.getvalue(), mtime=0)
        identities = job.identities_from_sources(sources)
        snapshot = dict(schema=job.SOURCE_SCHEMA, created_utc=WHEN, source_revision='0' * 40,
            source_sha256={n: job.digest(b) for n, b in sources.items()},
            archive_sha256=job.digest(packed), job_sha256=job.digest(sources[job.JOB_NAME]),
            image=job.IMAGE, tests=list(identities), test_identities=identities,
            test_files=list(job.TEST_FILES), resources=dict(job.RESOURCES),
            scientific_tests_or_evolutions_run=False, full_m1_accepted=False)
        snapshot_bytes = job.encode(snapshot)
        root.mkdir(parents=True, exist_ok=True)
        for name, data in (('snapshot.json', snapshot_bytes), ('source.tar.gz', packed),
                           ('job.py', sources[job.JOB_NAME])):
            (root / name).write_bytes(data)
        entry = prepare.create_case(root / 'preflight/0000', 'fixture-preflight', packed,
            snapshot_bytes, sources[job.JOB_NAME], dict(kind='preflight', resources=dict(job.RESOURCES)))
        job.dump(root / 'preflight/plan.json', dict(schema='openmhd.metadata-case-plan.v2',
            snapshot_sha256=job.digest(snapshot_bytes), cases=[entry], full_m1_accepted=False))
        job.dump(root / 'preflight/submission.json', {entry['workflow']: {'status': 'submitted'}})
        return snapshot, entry

    def output_fixture(self, snapshot, entry):
        """Synthetic successful metadata preflight; tests validator algebra only."""
        runtime = dict(schema=job.RUNTIME_SCHEMA, python='fixture-python', executable='/usr/bin/python3',
            implementation='CPython', platform='Linux fixture', optimized=0, image=job.IMAGE,
            visible_cpus=1, declared_resources=dict(job.RESOURCES),
            image_and_resources_are_declared_labels=True, job_path='/workspace/job.py',
            child_raw_path='/workspace/outputs/child_raw.bin', **{'cpu.max': 'fixture', 'memory.max': 'fixture'})
        command = dict(schema='openmhd.metadata-command.v1', command=job.expected_command(runtime, entry['specification']),
            cwd='/workspace/source', started_utc=WHEN, finished_utc=WHEN, duration_seconds=0.0,
            outcome='success', returncode=0, error_type=None, pid=123, process_group=123,
            timeout_seconds=180, timeout_scope='direct-child-wait',
            cleanup=dict(term_sent=False, kill_sent=False, direct_child_reaped=True,
                         writers_settled=True, remaining_live_pids=[]))
        child = dict(schema=job.CHILD_SCHEMA, kind='preflight', status='completed', passed=True,
            interpreter={k: runtime[k] for k in ('executable', 'python', 'optimized', 'implementation')},
            parsed_files=sorted(n for n in snapshot['source_sha256'] if n.endswith('.py')),
            test_selectors=snapshot['tests'], resolved_tests=len(snapshot['tests']),
            executed_identities=[snapshot['test_identities'][s] for s in snapshot['tests']],
            scientific_tests_or_evolutions_run=False, full_m1_accepted=False)
        result = dict(schema=job.RESULT_SCHEMA, status='completed', passed=True, started_utc=WHEN,
            finished_utc=WHEN, duration_seconds=0.0, case=entry['specification'], outcome='success',
            returncode=0, problem=None, command=command['command'], child_result=child,
            source_revision=snapshot['source_revision'], source_sha256=snapshot['source_sha256'],
            snapshot_sha256=job.digest(job.encode(snapshot)), payload_sha256=entry['payload_sha256'],
            runtime_sha256=job.digest(job.encode(runtime)), command_sha256=job.digest(job.encode(command)),
            scientific_tests_or_evolutions_run=False, full_m1_accepted=False)
        raw = job.encode(child)
        envelope = dict(schema='openmhd.metadata-child-envelope.v1', state='valid',
                        raw_sha256=job.digest(raw), raw_bytes=len(raw), problem=None, value=child)
        buffers = {'runtime.json': job.encode(runtime), 'command.json': job.encode(command),
            'result.json': job.encode(result), 'child_raw.bin': raw,
            'child_result.json': job.encode(envelope), 'stdout.txt': b'', 'stderr.txt': b''}
        buffers['artifacts.sha256.json'] = job.encode({'outputs/' + n: job.digest(b) for n, b in buffers.items()})
        return buffers

    def certificate_fixture(self, root):
        snapshot, entry = self.source_fixture(root)
        buffers = {n: (root / 'preflight' / n).read_bytes() for n in ('plan.json', 'submission.json')}
        buffers.update({n: (root / 'preflight/0000' / n).read_bytes()
                        for n in ('payload.json', 'reana.yaml', 'case.json')})
        buffers.update({'artifacts/' + n: b for n, b in self.output_fixture(snapshot, entry).items()})
        server = dict(schema=job.SERVER_SCHEMA, origin='server', observed_utc=WHEN,
            matches=[dict(workflow=entry['workflow'], name='fixture-preflight', version=1, status='finished')])
        buffers['server-before.json'] = buffers['server-after.json'] = job.encode(server)
        requests = [('observe', 'server-before.json')] + [('download', n) for n in job.OUTPUT_NAMES] + [
            ('observe', 'server-after.json')]
        transport = dict(schema='openmhd.metadata-transport.v1', client_argv=['/fixture/read-only-client'],
                         workflow=entry['workflow'], attempts=[], origin='server')
        for index, (action, name) in enumerate(requests):
            relative = name if action == 'observe' else 'artifacts/' + name
            requested = None if action == 'observe' else 'outputs/' + name
            argv = [*transport['client_argv'], action, '--workflow', entry['workflow']]
            if requested:
                argv += ['--path', requested]
            argv += ['--output', relative]
            receipt = dict(schema='openmhd.metadata-transport-attempt.v1', index=index, action=action,
                workflow=entry['workflow'], requested_path=requested, output=relative, command=argv,
                started_utc=WHEN, finished_utc=WHEN, duration_seconds=0.0, outcome='success', returncode=0,
                download_sha256=job.digest(buffers[relative]))
            for stream in ('stdout', 'stderr'):
                path = f'transport/{index:02d}.{stream}.txt'
                buffers[path] = b'UNIT fixture only; no server was contacted\n'
                receipt[stream] = dict(path=path, sha256=job.digest(buffers[path]))
            transport['attempts'].append(receipt)
        buffers['transport.json'] = job.encode(transport)
        return snapshot, entry, buffers

    def certificate_bytes(self, snapshot, buffers):
        return job.encode(dict(schema=job.CERT_SCHEMA, snapshot_sha256=job.digest(job.encode(snapshot)),
            capture_sha256={n: job.digest(b) for n, b in buffers.items()},
            buffers={n: base64.b64encode(b).decode('ascii') for n, b in buffers.items()},
            scientific_tests_or_evolutions_run=False, full_m1_accepted=False))

    def reclose(self, buffers):
        """Rehash a mutated UNIT fixture so semantic checks, not stale hashes, reject."""
        result = job.parse(buffers['artifacts/result.json'])
        runtime = buffers['artifacts/runtime.json']
        command = buffers['artifacts/command.json']
        child = job.parse(buffers['artifacts/child_raw.bin'])
        raw = buffers['artifacts/child_raw.bin']
        result.update(child_result=child, runtime_sha256=job.digest(runtime), command_sha256=job.digest(command))
        buffers['artifacts/result.json'] = job.encode(result)
        buffers['artifacts/child_result.json'] = job.encode(dict(schema='openmhd.metadata-child-envelope.v1',
            state='valid', raw_sha256=job.digest(raw), raw_bytes=len(raw), problem=None, value=child))
        buffers['artifacts/artifacts.sha256.json'] = job.encode({'outputs/' + n: job.digest(buffers['artifacts/' + n])
            for n in job.OUTPUT_NAMES if n != 'artifacts.sha256.json'})
        transport = job.parse(buffers['transport.json'])
        for attempt in transport['attempts']:
            attempt['download_sha256'] = job.digest(buffers[attempt['output']])
        buffers['transport.json'] = job.encode(transport)

    def assert_packet(self, work, outcome):
        output = work / 'outputs'
        self.assertEqual({p.name for p in output.iterdir()}, set(job.OUTPUT_NAMES))
        manifest = job.parse((output / 'artifacts.sha256.json').read_bytes())
        self.assertEqual(manifest, {'outputs/' + n: job.digest((output / n).read_bytes())
                                   for n in job.OUTPUT_NAMES if n != 'artifacts.sha256.json'})
        result = job.parse((output / 'result.json').read_bytes())
        self.assertIs(result['passed'], False)
        self.assertIs(result['full_m1_accepted'], False)
        self.assertEqual(result['outcome'], outcome)
        for name in ('runtime.json', 'command.json', 'child_result.json'):
            self.assertIsInstance(job.parse((output / name).read_bytes()), dict)
        return result

    def command_stub(self, raw=None, outcome='success', returncode=0):
        def execute(argv, cwd, environment, stdout, stderr, timeout):
            if raw is not None:
                Path(argv[argv.index('--result') + 1]).write_bytes(raw)
            return dict(schema='openmhd.metadata-command.v1', command=argv, cwd=str(cwd),
                started_utc=WHEN, finished_utc=WHEN, duration_seconds=0.0, outcome=outcome,
                returncode=returncode, error_type=None, pid=123, process_group=123,
                timeout_seconds=timeout, timeout_scope='direct-child-wait',
                cleanup=dict(term_sent=False, kill_sent=False, direct_child_reaped=True,
                             writers_settled=True, remaining_live_pids=[]))
        return execute

    def test_valid_certificate_host_release_includes_all_suites(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot, _, buffers = self.certificate_fixture(root / 'source')
            observation = root / 'observation'
            observation.mkdir()
            (observation / 'certificate.json').write_bytes(self.certificate_bytes(snapshot, buffers))
            prepare.prepare_cases(root / 'source', observation, root / 'cases', 'fixture')
            plan = job.parse((root / 'cases/plan.json').read_bytes())
            self.assertEqual(plan['coverage']['test_files'], list(job.TEST_FILES))
            self.assertEqual([e['specification']['selector'] for e in plan['cases']], snapshot['tests'])
            self.assertIs(plan['full_m1_accepted'], False)

    def test_normal_exact_leaf_has_actual_source_and_runtime_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'leaf.py'
            path.write_bytes(PLAIN)
            identity = next(iter(job.identities_from_sources({'leaf.py': PLAIN}, ('leaf.py',)).values()))
            prior = Path.cwd()
            try:
                os.chdir(tmp)
                suite, actual = job.load_one(identity['selector'], identity)
                leaf = list(suite)[0]
                self.assertEqual(leaf.id(), actual['runtime_id'])
                self.assertEqual(actual, identity)
                self.assertEqual(leaf._testMethodName, 'test_ok')
            finally:
                os.chdir(prior)

    def test_non_testcase_factory_is_rejected_before_import(self):
        source = b'import unittest\nclass Factory:\n    @staticmethod\n    def test_ok():\n        return unittest.FunctionTestCase(lambda: None)\n'
        with self.assertRaisesRegex(ValueError, 'plain unittest.TestCase'):
            job.identities_from_sources({'leaf.py': source}, ('leaf.py',))

    def test_inherited_discovery_is_rejected(self):
        source = PLAIN + b'\nclass Inherited(FixtureTests):\n    pass\n'
        with self.assertRaisesRegex(ValueError, 'inherited'):
            job.identities_from_sources({'leaf.py': source}, ('leaf.py',))

    def test_async_method_is_rejected(self):
        source = PLAIN.replace(b'def test_ok', b'async def test_ok')
        with self.assertRaisesRegex(ValueError, 'Unsupported unittest method'):
            job.identities_from_sources({'leaf.py': source}, ('leaf.py',))

    def test_decorated_method_is_rejected(self):
        source = PLAIN.replace(b'    def test_ok', b'    @staticmethod\n    def test_ok')
        with self.assertRaisesRegex(ValueError, 'Unsupported unittest method'):
            job.identities_from_sources({'leaf.py': source}, ('leaf.py',))

    def test_custom_testcase_dispatch_is_rejected(self):
        source = PLAIN + b'    def _callTestMethod(self, method):\n        pass\n'
        with self.assertRaisesRegex(ValueError, 'Custom TestCase dispatch'):
            job.identities_from_sources({'leaf.py': source}, ('leaf.py',))

    def test_duplicate_and_unresolved_selectors_are_rejected(self):
        duplicate = PLAIN + b'    def test_ok(self):\n        pass\n'
        with self.assertRaisesRegex(ValueError, 'Duplicate test method'):
            job.identities_from_sources({'leaf.py': duplicate}, ('leaf.py',))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'leaf.py'
            path.write_bytes(PLAIN)
            identity = next(iter(job.identities_from_sources({'leaf.py': PLAIN}, ('leaf.py',)).values()))
            prior = Path.cwd()
            try:
                os.chdir(tmp)
                with self.assertRaisesRegex(ValueError, 'Selector absent'):
                    job.load_one('leaf.FixtureTests.test_missing', identity)
            finally:
                os.chdir(prior)

    def test_dynamic_replacement_factory_is_rejected(self):
        source = PLAIN + b'\nFixtureTests.test_ok = staticmethod(lambda: unittest.FunctionTestCase(lambda: None))\n'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'dynamic.py'
            path.write_bytes(source)
            identity = next(iter(job.identities_from_sources({'dynamic.py': source}, ('dynamic.py',)).values()))
            prior = Path.cwd()
            try:
                os.chdir(tmp)
                with self.assertRaisesRegex(ValueError, 'Wrong test method/factory'):
                    job.load_one(identity['selector'], identity)
            finally:
                os.chdir(prior)

    def test_changed_input_keeps_complete_failure_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.source_fixture(root)
            work = root / 'preflight/0000'
            (work / 'source.tar.gz').write_bytes(b'changed')
            self.assertEqual(job.run(work, work / 'job.py'), 1)
            self.assert_packet(work, 'validation_failed')

    def test_actual_metadata_preflight_reports_resolved_leaf_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot, entry = self.source_fixture(root)
            work = root / 'preflight/0000'
            self.assertEqual(job.run(work, work / 'job.py'), 0)
            buffers = {n: (work / 'outputs' / n).read_bytes() for n in job.OUTPUT_NAMES}
            value = job.validate_preflight_outputs(buffers, job.encode(snapshot), entry)
            self.assertEqual(value['child_result']['executed_identities'],
                             [snapshot['test_identities'][s] for s in snapshot['tests']])

    def test_actual_child_import_failure_keeps_nonzero_envelope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.source_fixture(root, import_failure=True)
            work = root / 'preflight/0000'
            self.assertEqual(job.run(work, work / 'job.py'), 1)
            self.assert_packet(work, 'nonzero')
            self.assertIn(b'ImportError', (work / 'outputs/stderr.txt').read_bytes())

    def test_unsafe_member_keeps_extraction_failure_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.source_fixture(root, unsafe=True)
            work = root / 'preflight/0000'
            self.assertEqual(job.run(work, work / 'job.py'), 1)
            self.assert_packet(work, 'extraction_failed')
            self.assertFalse((root / 'escape.txt').exists())

    def test_launch_failure_has_finalized_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.source_fixture(root)
            work = root / 'preflight/0000'
            with mock.patch.object(job.subprocess, 'Popen', side_effect=OSError('UNIT fixture')):
                self.assertEqual(job.run(work, work / 'job.py'), 1)
            self.assert_packet(work, 'start_failed')
            command = job.parse((work / 'outputs/command.json').read_bytes())
            self.assertEqual(command['error_type'], 'OSError')
            self.assertTrue(command['cleanup']['writers_settled'])
            job.interval(command)

    def test_nonzero_child_without_result_keeps_failure_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.source_fixture(root)
            work = root / 'preflight/0000'
            with mock.patch.object(job, 'supervise', side_effect=self.command_stub(outcome='nonzero', returncode=1)):
                job.run(work, work / 'job.py')
            self.assert_packet(work, 'nonzero')

    def test_success_without_child_is_typed_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.source_fixture(root)
            work = root / 'preflight/0000'
            with mock.patch.object(job, 'supervise', side_effect=self.command_stub()):
                job.run(work, work / 'job.py')
            self.assert_packet(work, 'missing_child')
            envelope = job.parse((work / 'outputs/child_result.json').read_bytes())
            self.assertEqual(envelope['state'], 'absent')

    def test_removed_child_placeholder_is_typed_absent_and_restored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.source_fixture(root)
            work = root / 'preflight/0000'
            original = self.command_stub()
            def without_placeholder(*args):
                Path(args[0][args[0].index('--result') + 1]).unlink()
                return original(*args)
            with mock.patch.object(job, 'supervise', side_effect=without_placeholder):
                job.run(work, work / 'job.py')
            self.assert_packet(work, 'missing_child')
            self.assertEqual((work / 'outputs/child_raw.bin').read_bytes(), b'')

    def test_malformed_child_original_bytes_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.source_fixture(root)
            work = root / 'preflight/0000'
            raw = b'not JSON\x00\xff'
            with mock.patch.object(job, 'supervise', side_effect=self.command_stub(raw=raw)):
                job.run(work, work / 'job.py')
            self.assert_packet(work, 'invalid_child')
            self.assertEqual((work / 'outputs/child_raw.bin').read_bytes(), raw)
            envelope = job.parse((work / 'outputs/child_result.json').read_bytes())
            self.assertEqual(envelope['state'], 'invalid')
            self.assertEqual(envelope['raw_sha256'], job.digest(raw))

    def test_wrong_shape_child_keeps_raw_and_invalid_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.source_fixture(root)
            work = root / 'preflight/0000'
            with mock.patch.object(job, 'supervise', side_effect=self.command_stub(raw=b'[]')):
                job.run(work, work / 'job.py')
            self.assert_packet(work, 'invalid_child')
            self.assertEqual((work / 'outputs/child_raw.bin').read_bytes(), b'[]')

    def test_timeout_packet_is_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.source_fixture(root)
            work = root / 'preflight/0000'
            with mock.patch.object(job, 'supervise', side_effect=self.command_stub(outcome='timeout', returncode=-9)):
                job.run(work, work / 'job.py')
            self.assert_packet(work, 'timeout')

    def test_timeout_settles_descendant_writer_before_hashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Both parent and child are metadata-only Python processes. No solver.
            writer = 'import time\nwhile True:\n print("descendant",flush=True)\n time.sleep(.01)\n'
            parent = 'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",' + repr(writer) + ']); time.sleep(10)'
            with (root / 'stdout').open('wb') as stdout, (root / 'stderr').open('wb') as stderr:
                receipt = job.supervise([sys.executable, '-c', parent], root, dict(os.environ), stdout, stderr, 2)
            self.assertEqual(receipt['outcome'], 'timeout')
            self.assertTrue(receipt['cleanup']['direct_child_reaped'])
            self.assertTrue(receipt['cleanup']['writers_settled'])
            self.assertEqual(receipt['cleanup']['remaining_live_pids'], [])
            retained = (root / 'stdout').read_bytes()
            self.assertIn(b'descendant', retained)
            time.sleep(.15)
            self.assertEqual((root / 'stdout').read_bytes(), retained)

    def test_timeout_settles_detached_session_log_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            writer = 'import time\nwhile True:\n print("detached-writer",flush=True)\n time.sleep(.01)\n'
            parent = ('import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",'
                      + repr(writer) + '],start_new_session=True); time.sleep(10)')
            with (root / 'stdout').open('wb') as stdout, (root / 'stderr').open('wb') as stderr:
                receipt = job.supervise([sys.executable, '-c', parent], root, dict(os.environ), stdout, stderr, 2)
            self.assertEqual(receipt['outcome'], 'timeout')
            self.assertTrue(receipt['cleanup']['writers_settled'])
            self.assertEqual(receipt['cleanup']['remaining_live_pids'], [])
            retained = (root / 'stdout').read_bytes()
            self.assertIn(b'detached-writer', retained)
            time.sleep(.15)
            self.assertEqual((root / 'stdout').read_bytes(), retained)

    def test_optimized_invocation_rejects_with_failure_envelope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            completed = subprocess.run([sys.executable, '-O', str(TOOLS / 'reana_metadata_job.py')],
                                       cwd=root, capture_output=True, timeout=15)
            self.assertNotEqual(completed.returncode, 0)
            self.assert_packet(root, 'optimized_rejected')
            self.assertEqual(job.parse((root / 'outputs/runtime.json').read_bytes())['optimized'], 1)

    def test_pending_preflight_server_status_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, _, buffers = self.certificate_fixture(Path(tmp))
            value = job.parse(buffers['server-after.json'])
            value['matches'][0]['status'] = 'running'
            buffers['server-after.json'] = job.encode(value)
            with self.assertRaisesRegex(ValueError, 'terminal'):
                job.validate_certificate(self.certificate_bytes(snapshot, buffers), job.encode(snapshot))

    def test_stopped_preflight_server_status_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, _, buffers = self.certificate_fixture(Path(tmp))
            value = job.parse(buffers['server-after.json'])
            value['matches'][0]['status'] = 'stopped'
            buffers['server-after.json'] = job.encode(value)
            with self.assertRaisesRegex(ValueError, 'terminal'):
                job.validate_certificate(self.certificate_bytes(snapshot, buffers), job.encode(snapshot))

    def test_ambiguous_workflow_observation_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, _, buffers = self.certificate_fixture(Path(tmp))
            value = job.parse(buffers['server-before.json'])
            value['matches'].append(dict(value['matches'][0]))
            buffers['server-before.json'] = job.encode(value)
            with self.assertRaisesRegex(ValueError, 'Unique'):
                job.validate_certificate(self.certificate_bytes(snapshot, buffers), job.encode(snapshot))

    def test_mismatched_workflow_and_bool_version_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, _, buffers = self.certificate_fixture(Path(tmp))
            for change in ({'workflow': 'unrelated.1'}, {'version': True}, {'version': 2}):
                changed = dict(buffers)
                value = job.parse(changed['server-before.json'])
                value['matches'][0].update(change)
                changed['server-before.json'] = job.encode(value)
                with self.assertRaisesRegex(ValueError, 'terminal'):
                    job.validate_certificate(self.certificate_bytes(snapshot, changed), job.encode(snapshot))

    def test_fixture_origin_cannot_be_consumed_as_actual_server_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, _, buffers = self.certificate_fixture(Path(tmp))
            value = job.parse(buffers['server-before.json'])
            value['origin'] = 'fixture-negative'
            buffers['server-before.json'] = job.encode(value)
            with self.assertRaisesRegex(ValueError, 'Actual server'):
                job.validate_certificate(self.certificate_bytes(snapshot, buffers), job.encode(snapshot))

    def test_truthy_pass_and_wrong_result_schema_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, _, original = self.certificate_fixture(Path(tmp))
            for change in ({'passed': 1}, {'schema': 'unversioned'}, {'full_m1_accepted': 0}, {'returncode': False}):
                buffers = dict(original)
                result = job.parse(buffers['artifacts/result.json'])
                result.update(change)
                buffers['artifacts/result.json'] = job.encode(result)
                self.reclose(buffers)
                with self.assertRaises(ValueError):
                    job.validate_certificate(self.certificate_bytes(snapshot, buffers), job.encode(snapshot))

    def test_child_kind_scope_and_count_contradictions_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, _, original = self.certificate_fixture(Path(tmp))
            for change in ({'kind': 'unittest'}, {'passed': 1}, {'resolved_tests': True},
                           {'scientific_tests_or_evolutions_run': 0}, {'status': 'failed'}):
                buffers = dict(original)
                child = job.parse(buffers['artifacts/child_raw.bin'])
                child.update(change)
                buffers['artifacts/child_raw.bin'] = job.encode(child)
                self.reclose(buffers)
                with self.assertRaises(ValueError):
                    job.validate_certificate(self.certificate_bytes(snapshot, buffers), job.encode(snapshot))

    def test_missing_ast_selector_or_actual_identity_coverage_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, _, original = self.certificate_fixture(Path(tmp))
            for field in ('parsed_files', 'test_selectors', 'executed_identities'):
                buffers = dict(original)
                child = job.parse(buffers['artifacts/child_raw.bin'])
                child[field] = child[field][1:]
                buffers['artifacts/child_raw.bin'] = job.encode(child)
                self.reclose(buffers)
                with self.assertRaisesRegex(ValueError, 'coverage'):
                    job.validate_certificate(self.certificate_bytes(snapshot, buffers), job.encode(snapshot))

    def test_runtime_and_command_must_match_exact_preflight_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, _, original = self.certificate_fixture(Path(tmp))
            for name, change in (('runtime.json', {'optimized': False}),
                                 ('command.json', {'command': ['/usr/bin/python3', 'unrelated.py']}),
                                 ('command.json', {'timeout_seconds': True})):
                buffers = dict(original)
                value = job.parse(buffers['artifacts/' + name])
                value.update(change)
                buffers['artifacts/' + name] = job.encode(value)
                self.reclose(buffers)
                with self.assertRaises(ValueError):
                    job.validate_certificate(self.certificate_bytes(snapshot, buffers), job.encode(snapshot))

    def test_child_interpreter_must_match_parent_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, _, buffers = self.certificate_fixture(Path(tmp))
            value = job.parse(buffers['artifacts/child_raw.bin'])
            value['interpreter']['python'] = 'unrelated interpreter fixture'
            buffers['artifacts/child_raw.bin'] = job.encode(value)
            self.reclose(buffers)
            with self.assertRaisesRegex(ValueError, 'Child/runtime interpreter link'):
                job.validate_certificate(self.certificate_bytes(snapshot, buffers), job.encode(snapshot))

    def test_wrong_payload_snapshot_and_transport_download_links_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, _, original = self.certificate_fixture(Path(tmp))
            for field in ('snapshot_sha256', 'payload_sha256'):
                buffers = dict(original)
                result = job.parse(buffers['artifacts/result.json'])
                result[field] = 'f' * 64
                buffers['artifacts/result.json'] = job.encode(result)
                self.reclose(buffers)
                with self.assertRaisesRegex(ValueError, 'source/case'):
                    job.validate_certificate(self.certificate_bytes(snapshot, buffers), job.encode(snapshot))
            buffers = dict(original)
            transport = job.parse(buffers['transport.json'])
            transport['attempts'][1]['requested_path'] = 'outputs/unrelated.json'
            buffers['transport.json'] = job.encode(transport)
            with self.assertRaisesRegex(ValueError, 'Transport command/download'):
                job.validate_certificate(self.certificate_bytes(snapshot, buffers), job.encode(snapshot))

    def test_remote_case_revalidates_stopped_preflight_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot, _, buffers = self.certificate_fixture(root / 'source')
            server = job.parse(buffers['server-after.json'])
            server['matches'][0]['status'] = 'stopped'
            buffers['server-after.json'] = job.encode(server)
            certificate = self.certificate_bytes(snapshot, buffers)
            prepare.create_case(root / 'case', 'fixture-case', (root / 'source/source.tar.gz').read_bytes(),
                job.encode(snapshot), (root / 'source/job.py').read_bytes(),
                dict(kind='unittest', selector=snapshot['tests'][0], resources=dict(job.RESOURCES),
                     preflight_certificate_sha256=job.digest(certificate)), certificate)
            self.assertEqual(job.run(root / 'case', root / 'case/job.py'), 1)
            self.assert_packet(root / 'case', 'validation_failed')
            self.assertFalse((root / 'case/source').exists())

    def test_replaced_artifact_cannot_match_download_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, _, buffers = self.certificate_fixture(Path(tmp))
            buffers['artifacts/stdout.txt'] = b'replaced after download'
            with self.assertRaisesRegex(ValueError, 'Transport command/download'):
                job.validate_certificate(self.certificate_bytes(snapshot, buffers), job.encode(snapshot))

    def test_capture_retries_then_rejects_changed_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'metadata.json'
            path.write_bytes(b'{}')
            calls = []
            def replace_after_read(current):
                data = current.read_bytes()
                replacement = current.with_suffix('.next')
                replacement.write_bytes(data)
                replacement.replace(current)
                calls.append(current)
                return data
            with self.assertRaisesRegex(ValueError, 'Incoherent'):
                job.capture_files(root, ('metadata.json',), reader=replace_after_read)
            self.assertEqual(len(calls), 3)

    def test_capture_hash_parse_and_copy_share_one_immutable_buffer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'metadata.json'
            original = b'{"identity": "observed"}'
            path.write_bytes(original)
            calls = []
            def read(current):
                calls.append(current)
                return current.read_bytes()
            buffers = job.capture_files(root, ('metadata.json',), reader=read)
            path.write_bytes(b'{"identity": "later"}')
            self.assertEqual(len(calls), 1)
            self.assertEqual(job.parse(buffers['metadata.json'])['identity'], 'observed')
            self.assertEqual(job.digest(buffers['metadata.json']), job.digest(original))
            self.assertEqual(base64.b64decode(base64.b64encode(buffers['metadata.json'])), original)

    def test_incoherent_certificate_does_not_create_dependent_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.source_fixture(root / 'source')
            original = job.capture_files
            def capture(directory, names, **kwargs):
                if directory == root / 'observation':
                    raise ValueError('Incoherent UNIT fixture')
                return original(directory, names, **kwargs)
            with mock.patch.object(job, 'capture_files', side_effect=capture):
                with self.assertRaisesRegex(ValueError, 'Incoherent'):
                    prepare.prepare_cases(root / 'source', root / 'observation', root / 'cases', 'fixture')
            self.assertFalse((root / 'cases').exists())

    def test_readonly_observer_retains_start_failure_without_certificate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.source_fixture(root / 'source')
            with mock.patch.object(prepare.subprocess, 'run', side_effect=OSError('UNIT fixture')):
                with self.assertRaisesRegex(ValueError, 'adapter failed'):
                    prepare.observe_preflight(root / 'source', root / 'observation', ['/fixture/client'])
            self.assertFalse((root / 'observation/certificate.json').exists())
            transport = job.parse((root / 'observation/transport.json').read_bytes())
            self.assertEqual(transport['attempts'][0]['action'], 'observe')
            self.assertEqual(transport['attempts'][0]['outcome'], 'start_failed')
            self.assertTrue((root / 'observation/transport/00.stderr.txt').is_file())

    def test_readonly_observer_closes_labelled_synthetic_adapter_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot, entry = self.source_fixture(root / 'source')
            artifacts = self.output_fixture(snapshot, entry)
            commands = []
            def synthetic_adapter(argv, cwd, capture_output, timeout):
                # UNIT callback only: no live client, server or physical packet.
                commands.append(argv)
                action = argv[1]
                target = Path(cwd) / argv[argv.index('--output') + 1]
                if action == 'observe':
                    value = dict(schema=job.SERVER_SCHEMA, origin='server', observed_utc=WHEN,
                        matches=[dict(workflow=entry['workflow'], name='fixture-preflight',
                                      version=1, status='finished')])
                    target.write_bytes(job.encode(value))
                elif action == 'download':
                    name = Path(argv[argv.index('--path') + 1]).name
                    target.write_bytes(artifacts[name])
                else:
                    self.fail('Forbidden workflow mutation action: ' + action)
                return subprocess.CompletedProcess(argv, 0, b'UNIT synthetic adapter; no server contacted\n', b'')
            with mock.patch.object(prepare.subprocess, 'run', side_effect=synthetic_adapter):
                prepare.observe_preflight(root / 'source', root / 'observation', ['/fixture/client'])
            certificate = (root / 'observation/certificate.json').read_bytes()
            checked = job.validate_certificate(certificate, job.encode(snapshot))
            self.assertEqual(len(commands), len(job.OUTPUT_NAMES) + 2)
            self.assertEqual({a[1] for a in commands}, {'observe', 'download'})
            for name in job.OUTPUT_NAMES:
                self.assertEqual(base64.b64decode(checked['buffers']['artifacts/' + name]), artifacts[name])

    def test_credentials_are_not_allowed_in_adapter_argv(self):
        for argv in (['relative-client'], ['/client', '--token=secret'], ['/client', 'https://server/?token=value']):
            with self.assertRaises(ValueError):
                job.credential_free_argv(argv)

    def test_linked_download_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'actual').write_bytes(b'{}')
            (root / 'metadata.json').symlink_to(root / 'actual')
            with self.assertRaisesRegex(ValueError, 'Linked input'):
                job.capture_files(root, ('metadata.json',))

    def test_declared_outputs_include_original_child_and_command_evidence(self):
        spec = job.workflow_document({'source.tar.gz', 'snapshot.json', 'job.py', 'case.json'})
        self.assertEqual(set(spec['outputs']['files']), set(job.OUTPUTS))
        self.assertIn('outputs/child_raw.bin', spec['outputs']['files'])
        self.assertIn('outputs/command.json', spec['outputs']['files'])
        self.assertEqual(len(job.TEST_FILES), 3)
        self.assertIn('tools/m1_evidence/tests/test_runner_metadata.py', job.TEST_FILES)
