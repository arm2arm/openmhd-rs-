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
import reana_metadata_readonly_adapter as adapter
import collect_metadata_reana_results as results

WHEN = '2026-11-22T00:00:00+00:00'
PLAIN = b'import unittest\nclass FixtureTests(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n'


class RunnerMetadataTests(unittest.TestCase):
    def adapter_http_fixture(self, rows=None, artifact=b'metadata bytes', headers=None, alter=None):
        """No network: source-supported REST envelope and byte stream only.

        The credential string and origin are public UNIT labels, never private
        configured-service values. Recorded request objects stay in this test.
        """
        rows = [dict(name='fixture-preflight.1', id='00000000-0000-4000-8000-000000000001',
                     status='finished')] if rows is None else rows
        calls = []
        class Response:
            def __init__(self, req, data, content_type, extra=None):
                self.status, self.url, self.data = 200, req.full_url, io.BytesIO(data)
                self.headers = adapter.Message()
                self.headers['Content-Type'] = content_type
                self.headers['Content-Length'] = str(len(data))
                for key, value in (extra or {}).items():
                    if key in self.headers:
                        del self.headers[key]
                    if value is not None:
                        self.headers[key] = value
                self.closed = False
            def geturl(self):
                return self.url
            def read(self, size):
                return self.data.read(size)
            def close(self):
                self.closed = True
                self.data.close()
        class Opener:
            def open(self, req, timeout):
                calls.append(req)
                self_test.assertEqual(req.get_method(), 'GET')
                self_test.assertGreater(timeout, 0)
                self_test.assertLessEqual(timeout, adapter.SOCKET_SECONDS)
                parsed = adapter.parse.urlsplit(req.full_url)
                params = adapter.parse.parse_qs(parsed.query)
                self_test.assertEqual(params['access_token'], ['public-UNIT-credential'])
                if parsed.path == '/api/workflows':
                    self_test.assertEqual(params['workflow_id_or_name'], ['fixture-preflight'])
                    self_test.assertNotIn('status', params)
                    page, size = int(params['page'][0]), int(params['size'][0])
                    value = dict(items=rows[(page-1)*size:page*size], total=len(rows),
                        page=page, size=size, has_prev=page > 1, has_next=page*size < len(rows))
                    response = Response(req, adapter.json_bytes(value), 'application/json')
                else:
                    self_test.assertEqual(parsed.path,
                        '/api/workflows/00000000-0000-4000-8000-000000000001/workspace/outputs/result.json')
                    response = Response(req, artifact, 'application/octet-stream', headers)
                if alter is not None:
                    replacement = alter(req, response, len(calls))
                    if replacement is not None:
                        response = replacement
                return response
        self_test = self
        opener = Opener()
        client = adapter.Client('https://unit.invalid', 'public-UNIT-credential', opener=opener)
        return client, calls, opener

    def adapter_main_fixture(self, root, opener, action='download', path='outputs/result.json'):
        stdout, stderr = io.StringIO(), io.StringIO()
        argv = [action, '--workflow', 'fixture-preflight.1', '--output', str(root / 'requested')]
        if path is not None:
            argv += ['--path', path]
        original = adapter.settings_from_private
        with mock.patch.object(adapter, 'settings_from_private') as settings:
            # The main lookup is mocked without changing Client's independent
            # validation of the synthetic supplied origin/token pair.
            settings.side_effect = lambda env=None: (('https://unit.invalid', 'public-UNIT-credential')
                                                     if env is None else original(env))
            with mock.patch.object(adapter, 'https_opener', return_value=opener), \
                 mock.patch.object(adapter.sys, 'stdout', stdout), \
                 mock.patch.object(adapter.sys, 'stderr', stderr):
                code = adapter.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def source_fixture(self, root, unsafe=False, import_failure=False, host_tools=False):
        """Small source-only UNIT package, never a scientific campaign."""
        sources = {name: PLAIN for name in job.TEST_FILES}
        if import_failure:
            sources[job.TEST_FILES[0]] += b'\nraise ImportError("UNIT import-failure control")\n'
        sources[job.JOB_NAME] = (TOOLS / 'reana_metadata_job.py').read_bytes()
        if host_tools:
            sources.update({'tools/m1_evidence/' + n: (TOOLS / n).read_bytes() for n in results.TOOLS})
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
                         writers_settled=True, remaining_live_pids=[],
                         leader_identity=dict(pid=123, process_group=123, session=123, starttime='1'),
                         leader_held_until_group_close=True, group_authority_lost=False))
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

    def certificate_fixture(self, root, host_tools=False):
        snapshot, entry = self.source_fixture(root, host_tools=host_tools)
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
                             writers_settled=True, remaining_live_pids=[],
                             leader_identity=dict(pid=123, process_group=123, session=123, starttime='1'),
                             leader_held_until_group_close=True, group_authority_lost=False))
        return execute

    def results_fixture(self, root):
        """Three tiny synthetic metadata leaves, not a physical campaign."""
        snapshot, _, preflight = self.certificate_fixture(root / 'source', host_tools=True)
        observation = root / 'observation'
        observation.mkdir()
        (observation / 'certificate.json').write_bytes(self.certificate_bytes(snapshot, preflight))
        prepare.prepare_cases(root / 'source', observation, root / 'prepared', 'fixture')
        plan = job.parse((root / 'prepared/plan.json').read_bytes())
        job.dump(root / 'prepared/submission.json', {e['workflow']: {'status': 'submitted'} for e in plan['cases']})
        context, witnesses = results.capture_context(root / 'source', observation, root / 'prepared')
        packet = root / 'packet'
        packet.mkdir()
        for name, data in context.items():
            target = packet / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        command = [sys.executable, str(TOOLS / 'reana_metadata_readonly_adapter.py')]
        job.dump(packet / 'context_capture.json', dict(schema=results.CAPTURE_SCHEMA, sources=witnesses,
            adapter_argv=command, adapter_source_sha256=snapshot['source_sha256'][
                'tools/m1_evidence/reana_metadata_readonly_adapter.py'],
            scientific_tests_or_evolutions_run=False, full_m1_accepted=False))
        job.dump(packet / 'collection_status.json', dict(schema=results.STATUS_SCHEMA, status='complete',
            started_utc=WHEN, finished_utc=WHEN, problem=None,
            scientific_tests_or_evolutions_run=False, full_m1_accepted=False))
        return snapshot, plan, context, packet, command

    def results_case_fixture(self, snapshot, entry, command, status='finished', failed=False):
        outputs = self.output_fixture(snapshot, entry)
        runtime, attempt = (job.parse(outputs[n]) for n in ('runtime.json', 'command.json'))
        child = dict(schema=job.CHILD_SCHEMA, kind='unittest', status='failed' if failed else 'completed',
            passed=not failed, selector=entry['specification']['selector'],
            executed_identity=snapshot['test_identities'][entry['specification']['selector']],
            interpreter={k: runtime[k] for k in ('executable', 'python', 'optimized', 'implementation')},
            tests_run=1, failures=1 if failed else 0, errors=0, skipped=0, expected_failures=0,
            unexpected_successes=0, scientific_tests_or_evolutions_run=False, full_m1_accepted=False)
        record = job.parse(outputs['result.json'])
        attempt.update(outcome='nonzero' if failed else 'success', returncode=1 if failed else 0)
        outputs['command.json'] = job.encode(attempt)
        record.update(child_result=child, status=child['status'], passed=not failed,
            outcome=attempt['outcome'], returncode=attempt['returncode'], command_sha256=job.digest(outputs['command.json']))
        outputs['result.json'], outputs['child_raw.bin'] = job.encode(record), job.encode(child)
        outputs['child_result.json'] = job.encode(dict(schema='openmhd.metadata-child-envelope.v1', state='valid',
            raw_sha256=job.digest(outputs['child_raw.bin']), raw_bytes=len(outputs['child_raw.bin']), problem=None, value=child))
        outputs['stderr.txt'] = b'UNIT synthetic metadata log; not an actual test workflow\n'
        outputs['artifacts.sha256.json'] = job.encode({'outputs/' + n: job.digest(b) for n, b in outputs.items()
                                                     if n != 'artifacts.sha256.json'})
        server = job.encode(dict(schema=job.SERVER_SCHEMA, origin='server', observed_utc=WHEN,
            matches=[dict(workflow=entry['workflow'], name=entry['workflow'].rsplit('.', 1)[0], version=1, status=status)]))
        buffers = {'server-before.json': server, 'server-after.json': server}
        if status in results.TERMINAL_DOWNLOAD:
            buffers.update({'artifacts/' + n: b for n, b in outputs.items()})
        transport = dict(schema='openmhd.metadata-transport.v1', client_argv=command, workflow=entry['workflow'],
                         attempts=[], origin='server')
        for index, (kind, name) in enumerate(results.expected_requests(status)):
            relative = name if kind == 'observe' else 'artifacts/' + name
            requested = None if kind == 'observe' else 'outputs/' + name
            argv = command + [kind, '--workflow', entry['workflow']] + (['--path', requested] if requested else [])
            row = dict(schema='openmhd.metadata-transport-attempt.v1', index=index, action=kind,
                workflow=entry['workflow'], requested_path=requested, output=relative, command=argv + ['--output', relative],
                started_utc=WHEN, finished_utc=WHEN, duration_seconds=0.0, outcome='success', returncode=0,
                download_sha256=job.digest(buffers[relative]))
            for stream in ('stdout', 'stderr'):
                path = f'transport/{index:02d}.{stream}.txt'
                buffers[path] = b'UNIT synthetic transport; no service contacted\n'
                row[stream] = dict(path=path, sha256=job.digest(buffers[path]))
            transport['attempts'].append(row)
        buffers['transport.json'] = job.encode(transport)
        return buffers

    def write_results_case(self, packet, entry, buffers):
        for name, raw in buffers.items():
            target = packet / 'cases' / entry['directory'] / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)

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

    def test_adapter_rest_name_maps_exact_integer_version_and_server_origin(self):
        client, calls, _ = self.adapter_http_fixture()
        receipt, ids = client.observe('fixture-preflight.1')
        self.assertEqual(receipt['schema'], job.SERVER_SCHEMA)
        self.assertEqual(receipt['origin'], 'server')
        self.assertEqual(receipt['matches'], [dict(workflow='fixture-preflight.1',
            name='fixture-preflight', version=1, status='finished')])
        self.assertEqual(ids, ['00000000-0000-4000-8000-000000000001'])
        self.assertEqual(len(calls), 2)
        job.validate_server(receipt, 'fixture-preflight.1')

    def test_adapter_pending_status_is_preserved_and_gate_rejects(self):
        rows = [dict(name='fixture-preflight.1', id='00000000-0000-4000-8000-000000000001', status='pending')]
        client, _, _ = self.adapter_http_fixture(rows=rows)
        receipt, _ = client.observe('fixture-preflight.1')
        self.assertEqual(receipt['matches'][0]['status'], 'pending')
        with self.assertRaisesRegex(ValueError, 'terminal'):
            job.validate_server(receipt, 'fixture-preflight.1')

    def test_adapter_stopped_status_is_preserved_and_gate_rejects(self):
        rows = [dict(name='fixture-preflight.1', id='00000000-0000-4000-8000-000000000001', status='stopped')]
        client, _, _ = self.adapter_http_fixture(rows=rows)
        receipt, _ = client.observe('fixture-preflight.1')
        self.assertEqual(receipt['matches'][0]['status'], 'stopped')
        with self.assertRaisesRegex(ValueError, 'terminal'):
            job.validate_server(receipt, 'fixture-preflight.1')

    def test_adapter_preserves_every_ambiguous_matching_row(self):
        rows = [dict(name='fixture-preflight.1', id=f'00000000-0000-4000-8000-{n:012x}', status=status)
                for n, status in ((1, 'finished'), (2, 'stopped'))]
        client, _, _ = self.adapter_http_fixture(rows=rows)
        receipt, ids = client.observe('fixture-preflight.1')
        self.assertEqual([r['status'] for r in receipt['matches']], ['finished', 'stopped'])
        self.assertEqual(len(ids), 2)
        with self.assertRaisesRegex(ValueError, 'Unique'):
            job.validate_server(receipt, 'fixture-preflight.1')

    def test_adapter_wrong_version_cannot_be_assumed_to_be_requested_one(self):
        rows = [dict(name='fixture-preflight.2', id='00000000-0000-4000-8000-000000000002', status='finished')]
        client, _, _ = self.adapter_http_fixture(rows=rows)
        receipt, ids = client.observe('fixture-preflight.1')
        self.assertEqual(receipt['matches'], [])
        self.assertEqual(ids, [])
        with self.assertRaisesRegex(ValueError, 'Unique'):
            job.validate_server(receipt, 'fixture-preflight.1')

    def test_adapter_cli_run_number_string_is_not_a_rest_version(self):
        rows = [dict(name='fixture-preflight', run_number='1',
                     id='00000000-0000-4000-8000-000000000001', status='finished')]
        client, _, _ = self.adapter_http_fixture(rows=rows)
        with self.assertRaisesRegex(adapter.AdapterError, 'invalid_workflow'):
            client.observe('fixture-preflight.1')

    def test_adapter_missing_uuid_is_not_invented(self):
        client, _, _ = self.adapter_http_fixture(rows=[dict(name='fixture-preflight.1', status='finished')])
        with self.assertRaisesRegex(adapter.AdapterError, 'invalid_rest_workflow_id'):
            client.observe('fixture-preflight.1')

    def test_adapter_nonunique_or_nonfinished_download_does_not_request_artifact(self):
        finished = dict(name='fixture-preflight.1', id='00000000-0000-4000-8000-000000000001',
                        status='finished')
        for rows, expected in (([], 'ambiguous_or_missing_workflow'),
                ([finished, dict(finished)], 'ambiguous_or_missing_workflow'),
                ([dict(finished, status='pending')], 'workflow_not_terminal'),
                ([dict(finished, status='running')], 'workflow_not_terminal')):
            _, calls, opener = self.adapter_http_fixture(rows=rows)
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                code, _, stderr = self.adapter_main_fixture(root, opener)
                self.assertEqual(code, 1)
                self.assertEqual(adapter.parse_json(stderr)['code'], expected)
                self.assertTrue(all(adapter.parse.urlsplit(req.full_url).path == '/api/workflows'
                                    for req in calls))
                self.assertEqual((root / 'requested.partial').read_bytes(), b'')
                self.assertFalse((root / 'requested').exists())

    def test_adapter_paginates_all_versions_and_selects_only_exact_requested_version(self):
        rows = [dict(name=f'fixture-preflight.{n}', id=f'00000000-0000-4000-8000-{n:012x}',
                     status='finished') for n in range(1, 102)]
        client, calls, _ = self.adapter_http_fixture(rows=rows)
        receipt, _ = client.observe('fixture-preflight.1')
        self.assertEqual(len(calls), 4)
        self.assertEqual([adapter.parse.parse_qs(adapter.parse.urlsplit(c.full_url).query)['page'][0]
                          for c in calls], ['1', '2', '1', '2'])
        self.assertEqual(len(receipt['matches']), 1)
        self.assertEqual(receipt['matches'][0]['version'], 1)

    def test_adapter_pagination_total_change_is_rejected(self):
        rows = [dict(name=f'fixture-preflight.{n}', id=f'00000000-0000-4000-8000-{n:012x}',
                     status='finished') for n in range(1, 102)]
        def alter(req, response, count):
            if count == 2:
                value = adapter.parse_json(response.data.getvalue())
                value['total'] = 102
                value['items'].append(dict(name='fixture-preflight.102',
                    id='00000000-0000-4000-8000-000000000066', status='finished'))
                data = adapter.json_bytes(value)
                response.data = io.BytesIO(data)
                response.headers.replace_header('Content-Length', str(len(data)))
        client, _, _ = self.adapter_http_fixture(rows=rows, alter=alter)
        with self.assertRaisesRegex(adapter.AdapterError, 'pagination_changed'):
            client.observe('fixture-preflight.1')

    def test_adapter_short_page_or_truthy_total_does_not_prove_complete_enumeration(self):
        for change, expected in (({'total': 2}, 'pagination_incomplete'), ({'total': True}, 'invalid_rest_page')):
            def alter(req, response, count):
                value = adapter.parse_json(response.data.getvalue())
                value.update(change)
                data = adapter.json_bytes(value)
                response.data = io.BytesIO(data)
                response.headers.replace_header('Content-Length', str(len(data)))
            client, _, _ = self.adapter_http_fixture(alter=alter)
            with self.assertRaisesRegex(adapter.AdapterError, expected):
                client.observe('fixture-preflight.1')

    def test_adapter_contradictory_pagination_flags_are_rejected(self):
        def alter(req, response, count):
            value = adapter.parse_json(response.data.getvalue())
            value['has_next'] = True
            data = adapter.json_bytes(value)
            response.data = io.BytesIO(data)
            response.headers.replace_header('Content-Length', str(len(data)))
        client, _, _ = self.adapter_http_fixture(alter=alter)
        with self.assertRaisesRegex(adapter.AdapterError, 'pagination_mismatch'):
            client.observe('fixture-preflight.1')

    def test_adapter_changed_second_scan_has_no_observation_publication(self):
        def alter(req, response, count):
            if count == 2:
                value = adapter.parse_json(response.data.getvalue())
                value['items'][0]['status'] = 'stopped'
                data = adapter.json_bytes(value)
                response.data = io.BytesIO(data)
                response.headers.replace_header('Content-Length', str(len(data)))
        _, _, opener = self.adapter_http_fixture(alter=alter)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, stdout, stderr = self.adapter_main_fixture(root, opener, 'observe', None)
            self.assertEqual(code, 1)
            self.assertEqual(stdout, '')
            self.assertEqual(adapter.parse_json(stderr)['code'], 'observation_changed')
            self.assertFalse((root / 'requested').exists())

    def test_adapter_http_auth_uses_primary_query_without_credential_emission(self):
        _, calls, opener = self.adapter_http_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, stdout, stderr = self.adapter_main_fixture(root, opener, 'observe', None)
            self.assertEqual(code, 0)
            self.assertEqual(stderr, '')
            self.assertTrue(calls)
            for req in calls:
                self.assertNotIn('Authorization', req.headers)
                self.assertEqual(req.get_method(), 'GET')
            receipt = (root / 'requested').read_bytes()
            for secret_label in ('public-UNIT-credential', 'https://unit.invalid'):
                self.assertNotIn(secret_label, stdout + stderr + receipt.decode())
            self.assertEqual(adapter.parse_json(stdout)['outcome'], 'success')
            self.assertEqual(adapter.parse_json(receipt)['origin'], 'server')

    def test_adapter_normal_tls_and_redirect_rejection_have_no_insecure_fallback(self):
        context = adapter.ssl.create_default_context()
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, adapter.ssl.CERT_REQUIRED)
        with mock.patch.object(adapter.ssl, 'create_default_context', return_value=context), \
             mock.patch.object(adapter.request, 'build_opener', return_value=object()) as build:
            adapter.https_opener()
        handlers = build.call_args.args
        self.assertTrue(any(isinstance(h, adapter.RejectRedirect) for h in handlers))
        with self.assertRaisesRegex(adapter.AdapterError, 'redirect_rejected'):
            adapter.RejectRedirect().redirect_request(None, None, 302, 'ignored', {}, 'https://other.invalid')

    def test_adapter_redirected_response_is_not_observed_or_published(self):
        def alter(req, response, count):
            response.url = 'https://other.invalid/redirected'
        _, calls, opener = self.adapter_http_fixture(alter=alter)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, _, stderr = self.adapter_main_fixture(root, opener, 'observe', None)
            self.assertEqual(code, 1)
            self.assertEqual(len(calls), 1)
            self.assertEqual(adapter.parse_json(stderr)['code'], 'redirect_rejected')
            self.assertFalse((root / 'requested').exists())

    def test_adapter_http_failure_does_not_read_or_emit_secret_error_body(self):
        class FailureOpener:
            def open(self, req, timeout):
                raise adapter.error.HTTPError(req.full_url, 403, 'public-UNIT-credential',
                    adapter.Message(), io.BytesIO(b'public-UNIT-credential in error body'))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, stdout, stderr = self.adapter_main_fixture(root, FailureOpener(), 'observe', None)
            self.assertEqual(code, 1)
            value = adapter.parse_json(stderr)
            self.assertEqual(value['code'], 'http_error')
            self.assertEqual(value['http_status'], 403)
            self.assertNotIn('public-UNIT-credential', stdout + stderr)
            self.assertEqual((root / 'requested.partial').read_bytes(), b'')
            self.assertFalse((root / 'requested').exists())

    def test_adapter_network_failure_has_static_diagnostic_and_no_observation(self):
        class FailureOpener:
            def open(self, req, timeout):
                raise adapter.error.URLError(req.full_url + ' public-UNIT-credential')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, stdout, stderr = self.adapter_main_fixture(root, FailureOpener(), 'observe', None)
            self.assertEqual(code, 1)
            self.assertEqual(adapter.parse_json(stderr)['code'], 'network_error')
            self.assertNotIn('public-UNIT-credential', stdout + stderr)
            self.assertNotIn('unit.invalid', stdout + stderr)
            self.assertFalse((root / 'requested').exists())

    def test_adapter_exact_download_bytes_use_unique_uuid_endpoint_and_atomic_publication(self):
        payload = b'\x00exact metadata\xff\n'
        _, calls, opener = self.adapter_http_fixture(artifact=payload,
            headers={'Content-Disposition': 'attachment; filename="outputs/result.json"'})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, stdout, stderr = self.adapter_main_fixture(root, opener)
            self.assertEqual(code, 0)
            self.assertEqual(stderr, '')
            self.assertEqual((root / 'requested').read_bytes(), payload)
            self.assertFalse((root / 'requested.partial').exists())
            self.assertEqual(adapter.parse_json(stdout)['received_bytes'], len(payload))
            self.assertEqual(len(calls), 5)  # two fenced list reads, GET, two post reads

    def test_adapter_unsafe_remote_paths_never_reach_http(self):
        for path in ('outputs/../case.json', '/outputs/result.json', 'outputs/*.json',
                     'outputs/%2e%2e/secret', 'outputs/result.json?access_token=x', 'job.py', 'outputs/archive.zip'):
            client, calls, _ = self.adapter_http_fixture()
            with tempfile.TemporaryDirectory() as tmp:
                target = adapter.Target(Path(tmp) / 'requested')
                try:
                    with self.assertRaisesRegex(adapter.AdapterError, 'unsafe_remote_path'):
                        client.download('fixture-preflight.1', path, target)
                finally:
                    target.close()
            self.assertEqual(calls, [])

    def test_adapter_content_length_mismatch_keeps_only_failed_partial(self):
        _, _, opener = self.adapter_http_fixture(artifact=b'short', headers={'Content-Length': '12'})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, _, stderr = self.adapter_main_fixture(root, opener)
            self.assertEqual(code, 1)
            self.assertEqual(adapter.parse_json(stderr)['code'], 'content_length_mismatch')
            self.assertEqual((root / 'requested.partial').read_bytes(), b'short')
            self.assertFalse((root / 'requested').exists())

    def test_adapter_incomplete_http_body_retains_exact_received_prefix(self):
        def alter(req, response, count):
            if '/workspace/' in req.full_url:
                reads = [b'first']
                def read(size):
                    if reads:
                        return reads.pop()
                    raise adapter.http.client.IncompleteRead(b'tail', 9)
                response.read = read
        _, _, opener = self.adapter_http_fixture(alter=alter)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, _, stderr = self.adapter_main_fixture(root, opener)
            value = adapter.parse_json(stderr)
            self.assertEqual(code, 1)
            self.assertEqual(value['code'], 'incomplete_body')
            self.assertEqual(value['received_bytes'], 9)
            self.assertEqual((root / 'requested.partial').read_bytes(), b'firsttail')
            self.assertFalse((root / 'requested').exists())

    def test_adapter_oversized_body_keeps_bounded_explicit_prefix(self):
        _, _, opener = self.adapter_http_fixture(artifact=b'x' * 65, headers={'Content-Length': None})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(adapter, 'MAX_BYTES', 64):
                # Bypass small-cap pagination in this focused stream/target case.
                client = adapter.Client('https://unit.invalid', 'public-UNIT-credential', opener=opener)
                target = adapter.Target(root / 'requested')
                try:
                    with self.assertRaisesRegex(adapter.AdapterError, 'size_limit'):
                        client.get('/api/workflows/00000000-0000-4000-8000-000000000001/workspace/outputs/result.json',
                            {}, lambda response, headers, length: client.stream(response, target.append, length))
                    self.assertEqual(target.received, 65)
                    self.assertEqual(target.written, 64)
                finally:
                    target.close()
            self.assertEqual((root / 'requested.partial').read_bytes(), b'x' * 64)
            self.assertFalse((root / 'requested').exists())

    def test_adapter_proxy_stream_without_content_length_is_supported(self):
        _, _, opener = self.adapter_http_fixture(artifact=b'exact eof-framed bytes', headers={'Content-Length': None})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, _, stderr = self.adapter_main_fixture(root, opener)
            self.assertEqual(code, 0)
            self.assertEqual(stderr, '')
            self.assertEqual((root / 'requested').read_bytes(), b'exact eof-framed bytes')

    def test_adapter_archives_encoded_bytes_and_wrong_filename_are_rejected(self):
        cases = [({'Content-Type': 'application/zip'}, 'invalid_artifact_content_type'),
                 ({'Content-Encoding': 'gzip'}, 'encoded_body'),
                 ({'Content-Disposition': 'attachment; filename="unrelated.json"'}, 'artifact_name_mismatch')]
        for headers, expected in cases:
            _, _, opener = self.adapter_http_fixture(headers=headers)
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                code, _, stderr = self.adapter_main_fixture(root, opener)
                self.assertEqual(code, 1)
                self.assertEqual(adapter.parse_json(stderr)['code'], expected)
                self.assertFalse((root / 'requested').exists())

    def test_adapter_output_overwrite_and_existing_partial_are_rejected_without_http(self):
        for name in ('requested', 'requested.partial'):
            _, calls, opener = self.adapter_http_fixture()
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / name).write_bytes(b'preserved')
                code, _, stderr = self.adapter_main_fixture(root, opener)
                self.assertEqual(code, 1)
                self.assertEqual(adapter.parse_json(stderr)['code'], 'output_exists')
                self.assertEqual((root / name).read_bytes(), b'preserved')
                self.assertEqual(calls, [])

    def test_adapter_output_links_and_linked_parent_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            actual = root / 'actual'
            actual.mkdir()
            (root / 'linked-parent').symlink_to(actual, target_is_directory=True)
            with self.assertRaises(OSError):
                adapter.Target(root / 'linked-parent/requested')
            (root / 'requested').symlink_to(root / 'absent')
            with self.assertRaisesRegex(adapter.AdapterError, 'output_exists'):
                adapter.Target(root / 'requested')
            self.assertFalse((root / 'absent').exists())

    def test_adapter_replaced_partial_is_not_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = adapter.Target(root / 'requested')
            try:
                target.append(b'received bytes')
                (root / 'requested.partial').unlink()
                (root / 'requested.partial').write_bytes(b'replaced')
                with self.assertRaisesRegex(adapter.AdapterError, 'changed_partial_file'):
                    target.publish()
            finally:
                target.close()
            self.assertEqual((root / 'requested.partial').read_bytes(), b'replaced')
            self.assertFalse((root / 'requested').exists())

    def test_adapter_post_download_status_change_retains_failure_bytes(self):
        def alter(req, response, count):
            if count in (4, 5):
                value = adapter.parse_json(response.data.getvalue())
                value['items'][0]['status'] = 'stopped'
                data = adapter.json_bytes(value)
                response.data = io.BytesIO(data)
                response.headers.replace_header('Content-Length', str(len(data)))
        _, _, opener = self.adapter_http_fixture(artifact=b'received before stop', alter=alter)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, _, stderr = self.adapter_main_fixture(root, opener)
            self.assertEqual(code, 1)
            self.assertEqual(adapter.parse_json(stderr)['code'], 'download_workflow_changed')
            self.assertEqual((root / 'requested.partial').read_bytes(), b'received before stop')
            self.assertFalse((root / 'requested').exists())

    def test_adapter_private_config_filename_and_environment_pair_are_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'private-unit-config.json'
            path.write_bytes(adapter.json_bytes(dict(server_url='https://unit.invalid',
                                                     access_token='public-UNIT-credential')))
            self.assertEqual(adapter.settings_from_private({'OPENMHD_REANA_CONFIG': str(path)}),
                             ('https://unit.invalid', 'public-UNIT-credential'))
            with self.assertRaisesRegex(adapter.AdapterError, 'incomplete_environment_connection'):
                adapter.settings_from_private({'REANA_SERVER_URL': 'https://unit.invalid'})
            with self.assertRaisesRegex(adapter.AdapterError, 'invalid_server_origin'):
                adapter.settings_from_private({'REANA_SERVER_URL': 'http://unit.invalid',
                                               'REANA_ACCESS_TOKEN': 'public-UNIT-credential'})

    def test_adapter_only_observe_and_download_actions_are_exposed(self):
        for action in ('run', 'start', 'stop', 'submit', 'upload', 'delete', 'restart'):
            with self.assertRaisesRegex(adapter.AdapterError, 'invalid_arguments'):
                adapter.parser().parse_args([action, '--workflow', 'fixture-preflight.1', '--output', 'unused'])

    def test_adapter_deadline_is_bounded_and_no_request_occurs_after_expiry(self):
        _, calls, opener = self.adapter_http_fixture()
        clock = mock.Mock(side_effect=[0.0, float(adapter.DEADLINE_SECONDS + 1)])
        client = adapter.Client('https://unit.invalid', 'public-UNIT-credential', opener=opener, clock=clock)
        with self.assertRaisesRegex(adapter.AdapterError, 'adapter_deadline'):
            client.observe('fixture-preflight.1')
        self.assertEqual(calls, [])

    def test_adapter_optimized_rejection_has_typed_diagnostic_without_private_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            completed = subprocess.run([sys.executable, '-O', str(TOOLS / 'reana_metadata_readonly_adapter.py')],
                                       cwd=tmp, capture_output=True, timeout=15)
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(adapter.parse_json(completed.stderr)['code'], 'optimized_rejected')
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_reaped_leader_never_authorizes_stale_group_signal(self):
        process = job.types.SimpleNamespace(pid=4242, returncode=0)
        identity = dict(pid=4242, process_group=4242, session=4242, starttime='1')
        with mock.patch.object(job.os, 'killpg') as kill, mock.patch.object(job.os, 'waitid') as wait:
            self.assertFalse(job.signal_owned_group(process, identity, job.signal.SIGKILL))
        kill.assert_not_called()
        wait.assert_not_called()

    def test_changed_leader_starttime_cannot_reacquire_numeric_group_authority(self):
        process = job.types.SimpleNamespace(pid=4242, returncode=None)
        identity = dict(pid=4242, process_group=4242, session=4242, starttime='1')
        fields = ['S', '1', '4242', '4242'] + ['0'] * 15 + ['2']
        text = '4242 (UNIT stale group control) ' + ' '.join(fields)
        with mock.patch.object(job.os, 'waitid', return_value=None), \
             mock.patch.object(Path, 'read_text', return_value=text), \
             mock.patch.object(job.os, 'killpg') as kill:
            self.assertFalse(job.signal_owned_group(process, identity, job.signal.SIGTERM))
        kill.assert_not_called()

    def test_primary_completion_uses_wnowait_without_reaping(self):
        process = job.types.SimpleNamespace(pid=4242, returncode=None, wait=mock.Mock())
        identity = dict(pid=4242, process_group=4242, session=4242, starttime='1')
        terminal = job.types.SimpleNamespace(si_code=job.os.CLD_EXITED, si_status=0)
        with mock.patch.object(job, 'leader_authority', return_value=True), \
             mock.patch.object(job.os, 'waitid', return_value=terminal) as wait:
            self.assertIs(job.wait_primary_held(process, identity, 1), terminal)
        process.wait.assert_not_called()
        self.assertTrue(wait.call_args.args[2] & job.os.WNOWAIT)
        self.assertIsNone(process.returncode)

    def test_group_scan_without_held_identity_does_not_match_reused_number(self):
        fields = ['S', '1', '4242', '4242'] + ['0'] * 15 + ['2']
        class UnrelatedEntry:
            name = '4243'
            def __truediv__(self, key):
                if key == 'stat':
                    return job.types.SimpleNamespace(read_text=lambda: '4243 (UNIT unrelated) ' + ' '.join(fields))
                raise AssertionError('Unrelated UID must not be inspected as an owned group')
            def stat(self):
                return job.types.SimpleNamespace(st_uid=job.os.getuid() + 1)
        with mock.patch.object(Path, 'iterdir', return_value=iter([UnrelatedEntry()])):
            live, errors = job.live_group_or_writers(None, set())
        self.assertEqual(live, {})
        self.assertEqual(errors, [])

    def test_certificate_requires_held_group_closure_and_no_lost_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, _, original = self.certificate_fixture(Path(tmp))
            for field, value in (('leader_held_until_group_close', False), ('group_authority_lost', True)):
                buffers = dict(original)
                command = job.parse(buffers['artifacts/command.json'])
                command['cleanup'][field] = value
                buffers['artifacts/command.json'] = job.encode(command)
                self.reclose(buffers)
                with self.assertRaisesRegex(ValueError, 'Held group authority/closure'):
                    job.validate_certificate(self.certificate_bytes(snapshot, buffers), job.encode(snapshot))

    def test_normal_primary_exit_holds_leader_until_descendant_writer_closes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            writer = 'import time\nwhile True:\n print("held-leader-writer",flush=True)\n time.sleep(.01)\n'
            parent = ('import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",'
                      + repr(writer) + ']); time.sleep(.5)')
            with (root / 'stdout').open('wb') as stdout, (root / 'stderr').open('wb') as stderr:
                receipt = job.supervise([sys.executable, '-c', parent], root, dict(os.environ), stdout, stderr, 3)
            self.assertEqual(receipt['outcome'], 'success')
            self.assertTrue(receipt['cleanup']['leader_held_until_group_close'])
            self.assertFalse(receipt['cleanup']['group_authority_lost'])
            self.assertTrue(receipt['cleanup']['direct_child_reaped'])
            self.assertTrue(receipt['cleanup']['writers_settled'])
            retained = (root / 'stdout').read_bytes()
            self.assertIn(b'held-leader-writer', retained)
            time.sleep(.15)
            self.assertEqual((root / 'stdout').read_bytes(), retained)

    def test_adapter_failed_and_stopped_downloads_are_forensic_not_preflight(self):
        for status in ('failed', 'stopped'):
            rows = [dict(name='fixture-preflight.1', id='00000000-0000-4000-8000-000000000001', status=status)]
            client, _, opener = self.adapter_http_fixture(rows=rows, artifact=b'UNIT failed-job bytes')
            receipt, _ = client.observe('fixture-preflight.1')
            with self.assertRaisesRegex(ValueError, 'terminal'):
                job.validate_server(receipt, 'fixture-preflight.1')
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                code, _, stderr = self.adapter_main_fixture(root, opener)
                self.assertEqual(code, 0)
                self.assertEqual(stderr, '')
                self.assertEqual((root / 'requested').read_bytes(), b'UNIT failed-job bytes')
                self.assertFalse((root / 'certificate.json').exists())

    def test_adapter_late_buffered_data_and_eof_reject_after_return_with_closed_fds(self):
        # Cooperative rejection once control returns, not interruption inside read().
        for boundary in ('data', 'eof'):
            clock, responses, targets = {'now': 0.0}, [], []
            class RecordedTarget(adapter.Target):
                def __init__(self, path):
                    super().__init__(path)
                    targets.append(self)
            def alter(req, response, count):
                responses.append(response)
                if '/workspace/' in req.full_url:
                    original = response.read
                    def read(size):
                        data = original(size)
                        if (boundary == 'data' and data) or (boundary == 'eof' and not data):
                            clock['now'] = adapter.DEADLINE_SECONDS + 1.0
                        return data
                    response.read = read
            _, _, opener = self.adapter_http_fixture(artifact=b'progressing buffered bytes', alter=alter)
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                with mock.patch.object(adapter.time, 'monotonic', side_effect=lambda: clock['now']), \
                     mock.patch.object(adapter, 'Target', RecordedTarget):
                    code, _, stderr = self.adapter_main_fixture(root, opener)
                self.assertEqual(code, 1)
                self.assertEqual(adapter.parse_json(stderr)['code'], 'adapter_deadline')
                self.assertEqual((root / 'requested.partial').read_bytes(), b'progressing buffered bytes')
                self.assertFalse((root / 'requested').exists())
                self.assertFalse((root / 'certificate.json').exists())
                self.assertTrue(all(r.closed for r in responses))
                self.assertIsNone(targets[0].fd)
                self.assertIsNone(targets[0].parent_fd)

    def test_adapter_final_observation_processing_rechecks_before_publication(self):
        clock = {'now': 0.0}
        _, _, opener = self.adapter_http_fixture()
        original = adapter.Client.observe
        def late(client, workflow):
            value = original(client, workflow)
            clock['now'] = adapter.DEADLINE_SECONDS + 1.0
            return value
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(adapter.time, 'monotonic', side_effect=lambda: clock['now']), \
                 mock.patch.object(adapter.Client, 'observe', late):
                code, _, stderr = self.adapter_main_fixture(root, opener, 'observe', None)
            self.assertEqual(code, 1)
            self.assertEqual(adapter.parse_json(stderr)['code'], 'adapter_deadline')
            self.assertFalse((root / 'requested').exists())
            self.assertTrue((root / 'requested.partial').is_file())

    def test_metadata_results_exact_catalog_is_offline_and_shared_bytes_are_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot, plan, _, packet, command = self.results_fixture(root)
            for entry in plan['cases']:
                self.write_results_case(packet, entry, self.results_case_fixture(snapshot, entry, command))
            summary = results.close_packet(packet)
            self.assertTrue(summary['whole_suite_passed'])
            self.assertEqual(summary['expected_cases'], len(snapshot['tests']))
            self.assertEqual(summary['catalog']['selectors'], snapshot['tests'])
            self.assertEqual(len(list(packet.rglob('source.tar.gz'))), 1)
            self.assertEqual(len(list(packet.rglob('preflight_certificate.json'))), 1)
            for name in ('source', 'observation', 'prepared'):
                (root / name).rename(root / ('unavailable-original-' + name))
            self.assertEqual(results.verify_packet(packet), summary)
            self.assertIs(summary['full_m1_accepted'], False)
            self.assertIs(summary['scientific_tests_or_evolutions_run'], False)

    def test_metadata_results_missing_extra_duplicate_or_swapped_catalog_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, _, context, _, _ = self.results_fixture(Path(tmp))
            for change in ('missing', 'duplicate', 'swap', 'coverage-extra', 'wrong-directory', 'wrong-workflow'):
                altered = dict(context)
                plan = job.parse(altered['inputs/cases/plan.json'])
                if change == 'missing':
                    plan['cases'].pop()
                elif change == 'duplicate':
                    plan['cases'][1] = plan['cases'][0]
                elif change == 'swap':
                    plan['cases'][0], plan['cases'][1] = plan['cases'][1], plan['cases'][0]
                elif change == 'coverage-extra':
                    plan['coverage']['selectors'].append('UNIT.extra.selector')
                elif change == 'wrong-directory':
                    plan['cases'][0]['directory'] = '../escape'
                else:
                    plan['cases'][0]['workflow'] = plan['cases'][1]['workflow']
                altered['inputs/cases/plan.json'] = job.encode(plan)
                with self.assertRaises((ValueError, KeyError)):
                    results.validate_context(altered)

    def test_metadata_results_swapped_source_payload_certificate_and_resource_pins_reject(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, plan, context, _, _ = self.results_fixture(Path(tmp))
            for change in ('archive', 'certificate', 'payload', 'resources'):
                altered = dict(context)
                directory = plan['cases'][0]['directory']
                if change == 'archive':
                    altered['shared/source.tar.gz'] += b'changed source bytes'
                elif change == 'certificate':
                    altered['shared/preflight_certificate.json'] = b'{}'
                elif change == 'payload':
                    name = 'inputs/cases/' + directory + '/payload.json'
                    value = job.parse(altered[name])
                    value['input_sha256']['source.tar.gz'] = '0' * 64
                    altered[name] = job.encode(value)
                else:
                    name = 'inputs/cases/' + directory + '/case.json'
                    value = job.parse(altered[name])
                    value['resources']['threads'] = True
                    altered[name] = job.encode(value)
                with self.assertRaises((ValueError, KeyError)):
                    results.validate_context(altered)

    def test_metadata_results_swapped_case_selector_runtime_child_log_and_manifest_links_reject(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, plan, _, _, command = self.results_fixture(Path(tmp))
            entry = plan['cases'][0]
            for change in ('source', 'case', 'selector', 'runtime', 'child', 'log', 'manifest'):
                buffers = self.results_case_fixture(snapshot, entry, command)
                if change in ('source', 'case'):
                    value = job.parse(buffers['artifacts/result.json'])
                    if change == 'source':
                        value['source_revision'] = '1' * 40
                    else:
                        value['case'] = plan['cases'][1]['specification']
                    buffers['artifacts/result.json'] = job.encode(value)
                elif change in ('selector', 'child'):
                    value = job.parse(buffers['artifacts/child_raw.bin'])
                    if change == 'selector':
                        value['selector'] = snapshot['tests'][1]
                        value['executed_identity'] = snapshot['test_identities'][snapshot['tests'][1]]
                    else:
                        value['skipped'] = 1
                    buffers['artifacts/child_raw.bin'] = job.encode(value)
                elif change == 'runtime':
                    value = job.parse(buffers['artifacts/runtime.json'])
                    value['python'] = 'unrelated UNIT interpreter'
                    buffers['artifacts/runtime.json'] = job.encode(value)
                self.reclose(buffers)
                if change == 'log':
                    buffers['artifacts/stderr.txt'] = b'swapped log without its original hash'
                elif change == 'manifest':
                    value = job.parse(buffers['artifacts/artifacts.sha256.json'])
                    value['outputs/stdout.txt'] = '0' * 64
                    buffers['artifacts/artifacts.sha256.json'] = job.encode(value)
                    transport = job.parse(buffers['transport.json'])
                    for attempt in transport['attempts']:
                        attempt['download_sha256'] = job.digest(buffers[attempt['output']])
                    buffers['transport.json'] = job.encode(transport)
                row = results.case_row(buffers, snapshot, job.encode(snapshot), entry, {'status': 'submitted'}, command)
                self.assertNotEqual(row['status'], 'passed', change)

    def test_metadata_results_failed_and_pending_cases_preserve_honest_whole_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, plan, _, packet, command = self.results_fixture(Path(tmp))
            for index, entry in enumerate(plan['cases']):
                status = ('failed', 'running', 'finished')[index]
                self.write_results_case(packet, entry, self.results_case_fixture(snapshot, entry, command,
                    status=status, failed=index == 0))
            summary = results.close_packet(packet)
            self.assertFalse(summary['whole_suite_passed'])
            self.assertEqual(summary['counts'], dict(passed=1, failed=1, pending=1, incomplete=0))
            self.assertEqual(summary['cases'][0]['classification'], 'validated_unittest_failure')
            self.assertFalse(summary['cases'][0]['external_evidence_required'])
            pending = summary['cases'][1]
            self.assertEqual(pending['status'], 'pending')
            self.assertTrue(all(a['path'] is None for a in pending['artifacts'].values()))
            self.assertTrue(pending['external_evidence_required'])
            entry = plan['cases'][1]
            raw = self.results_case_fixture(snapshot, entry, command, status='running')
            transport = job.parse(raw['transport.json'])
            transport['attempts'][0].update(outcome='nonzero', returncode=1, download_sha256=None)
            raw['transport.json'] = job.encode(transport)
            lost = results.case_row(raw, snapshot, job.encode(snapshot), entry, {'status': 'submitted'}, command)
            self.assertEqual(lost['status'], 'incomplete')

    def test_metadata_results_preflight_and_unittest_modes_cannot_substitute(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, plan, _, _, command = self.results_fixture(Path(tmp))
            entry = plan['cases'][0]
            valid = self.results_case_fixture(snapshot, entry, command)
            artifacts = {n: valid['artifacts/' + n] for n in job.OUTPUT_NAMES}
            job.validate_case_outputs(artifacts, job.encode(snapshot), entry)
            with self.assertRaisesRegex(ValueError, 'preflight mode'):
                job.validate_preflight_outputs(artifacts, job.encode(snapshot), entry)
            preflight_shaped = self.output_fixture(snapshot, entry)
            with self.assertRaises(ValueError):
                job.validate_case_outputs(preflight_shaped, job.encode(snapshot), entry)

    def test_metadata_results_partial_download_and_late_replacement_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, plan, _, packet, command = self.results_fixture(Path(tmp))
            for index, entry in enumerate(plan['cases']):
                buffers = self.results_case_fixture(snapshot, entry, command)
                if index == 0:
                    relative = 'artifacts/stdout.txt'
                    buffers.pop(relative)
                    buffers[relative + '.partial'] = b'UNIT interrupted artifact prefix'
                    transport = job.parse(buffers['transport.json'])
                    attempt = next(a for a in transport['attempts'] if a['output'] == relative)
                    attempt.update(outcome='timeout', returncode=None, download_sha256=None)
                    buffers['transport.json'] = job.encode(transport)
                self.write_results_case(packet, entry, buffers)
            summary = results.close_packet(packet)
            self.assertFalse(summary['whole_suite_passed'])
            self.assertEqual(summary['cases'][0]['status'], 'incomplete')
            artifact = summary['cases'][0]['artifacts']['stdout.txt']
            self.assertIsNone(artifact['path'])
            self.assertEqual(artifact['partial']['bytes'], len(b'UNIT interrupted artifact prefix'))
            path = packet / 'cases' / plan['cases'][1]['directory'] / 'artifacts/stderr.txt'
            path.write_bytes(b'replaced after closed capture')
            with self.assertRaises(ValueError):
                results.verify_packet(packet)

    def test_metadata_results_outer_adapter_timeout_is_300_and_keeps_partial_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, _, _, _, command = self.results_fixture(root)
            calls = []
            def timed_out(argv, cwd, capture_output, timeout):
                calls.append(argv)
                self.assertEqual(timeout, 300)
                self.assertTrue(capture_output)
                (Path(cwd) / (argv[argv.index('--output') + 1] + '.partial')).write_bytes(b'UNIT partial observation')
                raise subprocess.TimeoutExpired(argv, timeout, output=b'UNIT timeout', stderr=b'token=public-UNIT-redaction')
            with mock.patch.object(prepare.subprocess, 'run', side_effect=timed_out):
                summary = results.collect(root / 'source', root / 'observation', root / 'prepared', root / 'collected', command)
            self.assertFalse(summary['whole_suite_passed'])
            self.assertTrue(all(c[len(command)] == 'observe' for c in calls))
            self.assertEqual(len(calls), 2 * summary['expected_cases'])
            retained = (root / 'collected/cases/0000/transport/00.stderr.txt').read_bytes()
            self.assertNotIn(b'public-UNIT-redaction', retained)
            self.assertIn(b'[REDACTED]', retained)
            self.assertTrue((root / 'collected/cases/0000/server-before.json.partial').is_file())

    def test_metadata_results_changed_original_context_never_closes_a_passing_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot, _, context, _, command = self.results_fixture(root)
            captured = results.capture_context(root / 'source', root / 'observation', root / 'prepared')
            def acquire(output, actual_command, entry):
                self.assertEqual(actual_command, command)
                for name, data in self.results_case_fixture(snapshot, entry, command).items():
                    target = output / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
            with mock.patch.object(results, 'capture_context', side_effect=[captured, ValueError('UNIT changed inputs')]), \
                 mock.patch.object(results, 'observe_case', side_effect=acquire):
                summary = results.collect(root / 'source', root / 'observation', root / 'prepared', root / 'collected', command)
            self.assertEqual(context, captured[0])
            self.assertEqual(summary['collection_status'], 'failed')
            self.assertFalse(summary['whole_suite_passed'])

    def test_metadata_results_summary_types_and_unregistered_packet_files_reject(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, plan, _, packet, command = self.results_fixture(Path(tmp))
            for entry in plan['cases']:
                self.write_results_case(packet, entry, self.results_case_fixture(snapshot, entry, command))
            results.close_packet(packet)
            original = (packet / 'summary.json').read_bytes()
            value = job.parse(original)
            value['counts']['failed'] = False  # Python equality alone would equate False and 0.
            (packet / 'summary.json').write_bytes(job.encode(value))
            manifest = job.parse((packet / 'files.sha256.json').read_bytes())
            raw = (packet / 'summary.json').read_bytes()
            manifest['files']['summary.json'] = dict(sha256=job.digest(raw), bytes=len(raw))
            job.dump(packet / 'files.sha256.json', manifest)
            with self.assertRaisesRegex(ValueError, 'verdict mismatch'):
                results.verify_packet(packet)
            (packet / 'summary.json').write_bytes(original)
            (packet / 'unregistered.txt').write_bytes(b'UNIT unknown file')
            with self.assertRaisesRegex(ValueError, 'Unknown packet files'):
                results.verify_packet(packet)
