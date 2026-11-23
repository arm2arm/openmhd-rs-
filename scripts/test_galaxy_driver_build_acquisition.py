"""UNEXECUTED metadata controls; each method needs its own REANA workflow.

All positive fixtures are explicitly NONPHYSICAL isolated schema/receipt
fragments. None has source archives, compiler output, binaries or sufficient
inputs to pass the complete public acquisition/records verifier. No live API.
"""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('driver_acquisition_under_test',
    ROOT / 'tools/galaxy_evidence/driver_build_acquisition.py')
a = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(a)


class DriverBuildAcquisitionTests(unittest.TestCase):
    def auth(self):
        marker = a.descriptor(b'NONPHYSICAL metadata fragment, not an executed build\n')
        return dict(schema=a.AUTH_SCHEMA, workflow='nonphysical-driver-build.1',
            uuid='12345678-1234-4234-8234-123456789abc', source_revision='1' * 40,
            snapshot=dict(marker), submission=dict(marker), build_release=dict(marker),
            host_source_sha256={**a.PINS, a.SELF: a.sha(b'NONPHYSICAL self-source marker')},
            origins={'fixture': {'manifest_path': 'files.sha256.json', 'manifest': dict(marker)}},
            receipts={role: {'origin': 'fixture', 'path': role, 'descriptor': dict(marker)}
                      for role in ('preflight_review', 'coordinator_release', 'source_preparation_command',
                                   'submission_command')},
            prerequisite_outputs='fixture', coordinator_authorized=True,
            external_prerequisite_truth_verified=False, component_accepted=False)

    def origin_fragment(self, root):
        origin, packet = root / 'origin', root / 'packet'
        origin.mkdir()
        packet.mkdir()
        auth = self.auth()
        for role in auth['receipts']:
            raw = ('NONPHYSICAL ' + role + '; no prerequisite attested\n').encode()
            a.put(origin, role, raw)
            auth['receipts'][role]['descriptor'] = a.descriptor(raw)
        a.put(origin, 'files.sha256.json', a.encode(a.inventory(origin)))
        auth['origins']['fixture']['manifest'] = a.descriptor(a.read(origin, 'files.sha256.json'))
        return packet, origin, auth

    def staged_fragment(self, root):
        # Only validate_inputs' metadata boundary is positive. Missing archives
        # and required Rust/helper source bodies prohibit any full record pass.
        packet = root / 'packet'
        packet.mkdir()
        auth = self.auth()
        preparer_raw = (ROOT / a.PREPARER).read_bytes()
        self.assertEqual(a.sha(preparer_raw), a.PINS[a.PREPARER])
        preparer = a.load_module(preparer_raw, ROOT / a.PREPARER, 'nonphysical_metadata_preparer')
        reviews = {role: ('NONPHYSICAL ' + role + '\n').encode() for role in auth['receipts']}
        for role, raw in reviews.items():
            a.put(packet, 'prerequisites/' + role, raw)
        mapping = {a.PREPARER: a.PINS[a.PREPARER], 'reana/remote.py': a.sha(b'NONPHYSICAL remote\n')}
        release_raw = a.encode(dict(schema='openmhd.galaxy-driver-build-release.v1', source_revision='1' * 40,
            source_sha256=mapping, preflight_review_sha256=a.sha(reviews['preflight_review']),
            coordinator_release_sha256=a.sha(reviews['coordinator_release'])))
        snapshot = dict(dirty_status='', source_revision='1' * 40, source_sha256=mapping,
            upload_sha256={'remote.py': mapping['reana/remote.py'], 'build_release.json': a.sha(release_raw)},
            compact_history=True, revision='2' * 40, revision_scope='private one-commit export fixture',
            workflow_derivation=dict(schema='openmhd.galaxy-driver-build-workflow.v1',
                base_workflow_sha256=a.sha(b'NONPHYSICAL original spec'), release_sha256=a.sha(release_raw),
                job_source_sha256=preparer.PINS[preparer.JOB], declared_build_jobs=4, declared_memory='8Gi',
                test_methods_to_execute=0, numerical_cases_to_execute=0,
                external_prerequisite_truth_verified=False, component_accepted=False))
        spec_raw = a.encode(preparer.specification(snapshot))
        snapshot['workflow_sha256'] = a.sha(spec_raw)
        snapshot_raw = a.encode(snapshot)
        submission_raw = a.encode({auth['workflow']: {'status': 'submission uncertain'}})
        for name, raw in (('snapshot.json', snapshot_raw), ('reana.yaml', spec_raw),
                          ('remote.py', b'NONPHYSICAL remote\n'), ('build_release.json', release_raw)):
            a.put(packet / 'source', name, raw)
        a.put(packet, 'submission_original.json', submission_raw)
        auth.update(snapshot=a.descriptor(snapshot_raw), submission=a.descriptor(submission_raw),
                    build_release=a.descriptor(release_raw))
        return packet, auth, preparer

    def journal_fragment(self, packet, auth, number='000000', success=True, raw=b'NONPHYSICAL opaque bytes\n'):
        folder = 'attempts/' + number
        remote = a.PREFIX + 'parts/geometry.part0000'
        argv = ['/usr/bin/python3', '-B', str(packet / 'host' / a.ADAPTER), 'download',
                '--workflow', auth['workflow'], '--output', str(packet / folder / 'body'), '--path', remote]
        row = dict(schema=a.TRANSPORT_SCHEMA, argv=argv, cwd=str(packet), workflow=auth['workflow'], uuid=auth['uuid'],
            action='download', remote_path=remote, phase='parts', timeout_seconds=300,
            started_utc='2026-11-22T00:00:00+00:00', finished_utc='2026-11-22T00:00:01+00:00',
            outcome='success' if success else 'nonzero', returncode=0 if success else 1,
            pid=123, child_reaped=True, seconds=1.0, host_source_sha256=auth['host_source_sha256'],
            interpreter=dict(executable='/usr/bin/python3', python='NONPHYSICAL interpreter declaration',
                             implementation='cpython', optimized=0))
        intent = dict(row, finished_utc=None, outcome='intent', pid=None, returncode=None, child_reaped=False)
        a.put(packet, folder + '/intent.json', a.encode(intent))
        row['intent_sha256'] = a.sha(a.encode(intent))
        a.put(packet, folder + '/launch.json', a.encode(dict(pid=123, argv=argv,
              launched_utc='2026-11-22T00:00:00.5+00:00')))
        diagnostic = a.encode(dict(schema='openmhd.galaxy-get-diagnostic.v1', action='download',
            workflow=auth['workflow'], requested_path=remote, outcome='success' if success else 'failure',
            code='completed' if success else 'network_error', workflow_ids=[auth['uuid']] if success else [],
            started_utc='2026-11-22T00:00:00.5+00:00', finished_utc='2026-11-22T00:00:00.9+00:00',
            page_count=2, received_bytes=len(raw), retained_bytes=len(raw),
            partial_file=None if success else 'body.partial'))
        unavailable = a.retain_log(b'')
        for channel, data in (('stdout', diagnostic if success else unavailable), ('stderr', unavailable if success else diagnostic)):
            row[channel] = folder + '/' + channel + '.json'
            a.put(packet, row[channel], data)
            row[channel + '_sha256'] = a.sha(data)
        a.put(packet, folder + ('/body' if success else '/body.partial'), raw)
        row['body_identity' if success else 'partial_identity'] = a.descriptor(raw)
        a.put(packet, folder + '/result.json', a.encode(row))
        return row, a.audit_attempt(packet, number, auth)

    def interval_fragments(self, packet, auth):
        raw = a.encode(dict(schema='openmhd.galaxy-server-observation.v1', origin='server',
            observed_utc='2026-11-22T00:00:02+00:00', matches=[dict(id=auth['uuid'], name=auth['workflow'][:-2],
                workflow=auth['workflow'], version=1, status='finished')]))
        a.put(packet, 'NONPHYSICAL-observation', raw)
        def entry(number, action, phase, start, finish, remote=None, success=True):
            return dict(number=number, action=action, phase=phase, remote_path=remote, success=success,
                body='NONPHYSICAL-observation', identity=a.descriptor(raw),
                started_utc='2026-11-22T00:00:' + start + '+00:00',
                finished_utc='2026-11-22T00:00:' + finish + '+00:00')
        failed = entry('000000', 'observe', 'before', '00', '01', success=False)
        before = entry('000001', 'observe', 'before', '01', '02')
        after = entry('000002', 'observe', 'after', '05', '06')
        entries = [failed, before, after]
        record = dict(before=before['number'], after=after['number'], metadata_before={}, metadata_after={})
        for phase, start, finish in (('before', '02', '03'), ('after', '03', '04')):
            for remote in a.FIXED:
                row = entry(str(len(entries)).zfill(6), 'download', 'metadata_' + phase, start, finish, remote)
                entries.append(row)
                record['metadata_' + phase][remote] = row['number']
        return record, entries

    def test_coordinator_release_is_explicit_and_nonaccepting(self):
        value = self.auth()
        self.assertIs(a.authorization(value), value)
        for field in ('coordinator_authorized', 'external_prerequisite_truth_verified', 'component_accepted'):
            changed = copy.deepcopy(value)
            changed[field] = not changed[field]
            with self.assertRaisesRegex(a.Invalid, '^coordinator_release_required$'):
                a.authorization(changed)

    def test_identity_host_pin_and_boolean_count_alias_rejections(self):
        value = self.auth()
        for changed, code in ((dict(value, workflow='nonphysical-driver-build.2'), 'original_version_one'),
                              (dict(value, uuid=value['uuid'].upper()), 'canonical_uuid'),
                              (dict(value, snapshot=dict(bytes=True, sha256=value['snapshot']['sha256'])), 'descriptor_size')):
            with self.assertRaisesRegex(a.Invalid, '^' + code + '$'):
                a.authorization(changed)
        changed = copy.deepcopy(value)
        changed['host_source_sha256'][a.ADAPTER] = '0' * 64
        with self.assertRaisesRegex(a.Invalid, '^host_source_pin$'):
            a.authorization(changed)

    def test_origin_resolution_requires_explicit_roots_and_survives_relocation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            packet, origin, auth = self.origin_fragment(root)
            a.check_origins(packet, auth, {'fixture': origin}, capture=True)
            moved = root / 'relocated-origin'
            origin.rename(moved)
            a.check_origins(packet, auth, {'fixture': moved})
            with self.assertRaisesRegex(a.Invalid, '^exact_explicit_origins$'):
                a.check_origins(packet, auth, {})

    def test_changed_origin_body_and_resealed_manifest_reject_old_release(self):
        with tempfile.TemporaryDirectory() as directory:
            packet, origin, auth = self.origin_fragment(Path(directory).resolve())
            a.check_origins(packet, auth, {'fixture': origin}, capture=True)
            (origin / 'preflight_review').write_bytes(b'CHANGED NONPHYSICAL receipt\n')
            with self.assertRaisesRegex(a.Invalid, '^origin_exact_closure$'):
                a.check_origins(packet, auth, {'fixture': origin})
            (origin / 'files.sha256.json').write_bytes(a.encode(a.inventory(origin, 'files.sha256.json')))
            with self.assertRaisesRegex(a.Invalid, '^origin_manifest_identity$'):
                a.check_origins(packet, auth, {'fixture': origin})

    def test_original_uncertain_submission_is_retained_not_relabelled(self):
        with tempfile.TemporaryDirectory() as directory:
            packet, auth, preparer = self.staged_fragment(Path(directory).resolve())
            raw = a.read(packet, 'submission_original.json')
            a.validate_inputs(packet, auth, preparer)
            self.assertEqual(a.read(packet, 'submission_original.json'), raw)
            self.assertEqual(a.parse(raw)[auth['workflow']]['status'], 'submission uncertain')
            self.assertNotIn('archives', a.parse(a.read(packet / 'source', 'snapshot.json')))

    def test_original_release_receipts_are_bound_to_retained_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            packet, auth, preparer = self.staged_fragment(Path(directory).resolve())
            a.validate_inputs(packet, auth, preparer)
            (packet / 'prerequisites/preflight_review').write_bytes(b'CHANGED NONPHYSICAL review')
            with self.assertRaisesRegex(a.Invalid, '^original_release_receipt_preflight_review$'):
                a.validate_inputs(packet, auth, preparer)

    def test_staged_spec_upload_and_snapshot_generation_guards(self):
        with tempfile.TemporaryDirectory() as directory:
            packet, auth, preparer = self.staged_fragment(Path(directory).resolve())
            a.validate_inputs(packet, auth, preparer)
            spec = packet / 'source/reana.yaml'
            original = spec.read_bytes()
            spec.write_bytes(b'{}\n')
            with self.assertRaisesRegex(a.Invalid, '^original_build_specification$'):
                a.validate_inputs(packet, auth, preparer)
            spec.write_bytes(original)
            (packet / 'source/remote.py').write_bytes(b'CHANGED NONPHYSICAL bootstrap')
            with self.assertRaisesRegex(a.Invalid, '^original_upload_identity$'):
                a.validate_inputs(packet, auth, preparer)
            (packet / 'source/snapshot.json').write_bytes(b'{}\n')
            with self.assertRaisesRegex(a.Invalid, '^authorized_input_snapshot$'):
                a.validate_inputs(packet, auth, preparer)

    def test_invalid_authorization_prevents_any_get_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            a.put(root, 'invalid-authorization.json', b'{}\n')
            with mock.patch.object(a.subprocess, 'Popen') as launch:
                with self.assertRaisesRegex(a.Invalid, '^authorization_fields$'):
                    a.acquire(root, root / 'unused-submission', root / 'invalid-authorization.json', root, {}, root / 'new')
                launch.assert_not_called()
            self.assertFalse((root / 'new').exists())

    def test_successful_journal_fragment_selects_original_body_only(self):
        with tempfile.TemporaryDirectory() as directory:
            packet = Path(directory).resolve()
            _, item = self.journal_fragment(packet, self.auth())
            self.assertEqual(a.choose([item], item['remote_path'])['number'], '000000')
            self.assertEqual(a.read(packet, item['body']), b'NONPHYSICAL opaque bytes\n')

    def test_matching_partial_is_failure_and_never_promoted(self):
        with tempfile.TemporaryDirectory() as directory:
            packet = Path(directory).resolve()
            _, item = self.journal_fragment(packet, self.auth(), success=False)
            self.assertFalse(item['success'])
            self.assertTrue((packet / 'attempts/000000/body.partial').is_file())
            with self.assertRaisesRegex(a.Invalid, '^missing_successful_body$'):
                a.choose([item], item['remote_path'])
            self.assertFalse((packet / 'attempts/000000/body').exists())
            (packet / 'attempts/000000/body').write_bytes(a.read(packet, 'attempts/000000/body.partial'))
            with self.assertRaisesRegex(a.Invalid, '^failed_body_cannot_be_promoted$'):
                a.audit_attempt(packet, '000000', self.auth())
            (packet / 'attempts/000000/body').unlink()
            (packet / 'attempts/000000/body.partial').unlink()
            with self.assertRaisesRegex(a.Invalid, '^missing_retained_partial$'):
                a.audit_attempt(packet, '000000', self.auth())

    def test_duplicate_and_conflicting_success_receipts_are_not_voted_away(self):
        with tempfile.TemporaryDirectory() as directory:
            packet, auth = Path(directory).resolve(), self.auth()
            _, first = self.journal_fragment(packet, auth)
            with self.assertRaisesRegex(a.Invalid, '^duplicate_receipt$'):
                a.choose([first, first], first['remote_path'])
            _, second = self.journal_fragment(packet, auth, number='000001', raw=b'CHANGED NONPHYSICAL body')
            with self.assertRaisesRegex(a.Invalid, '^changed_successful_body$'):
                a.choose([first, second], first['remote_path'])

    def test_wrong_uuid_or_changed_body_cannot_use_success_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            packet, auth = Path(directory).resolve(), self.auth()
            row, _ = self.journal_fragment(packet, auth)
            path = packet / row['stdout']
            original = path.read_bytes()
            diag = a.parse(original)
            diag['workflow_ids'] = ['00000000-0000-4000-8000-000000000000']
            path.write_bytes(a.encode(diag))
            row['stdout_sha256'] = a.sha(path.read_bytes())
            result = packet / 'attempts/000000/result.json'
            result.write_bytes(a.encode(row))
            with self.assertRaisesRegex(a.Invalid, '^successful_body_uuid_identity$'):
                a.audit_attempt(packet, '000000', auth)
            path.write_bytes(original)
            row['stdout_sha256'] = a.sha(original)
            result.write_bytes(a.encode(row))
            bad_count = a.parse(original)
            bad_count['received_bytes'] = True
            path.write_bytes(a.encode(bad_count))
            row['stdout_sha256'] = a.sha(path.read_bytes())
            result.write_bytes(a.encode(row))
            with self.assertRaisesRegex(a.Invalid, '^successful_diagnostic_bytes$'):
                a.audit_attempt(packet, '000000', auth)
            path.write_bytes(original)
            row['stdout_sha256'] = a.sha(original)
            result.write_bytes(a.encode(row))
            (packet / 'attempts/000000/body').write_bytes(b'CHANGED')
            with self.assertRaisesRegex(a.Invalid, '^successful_body_uuid_identity$'):
                a.audit_attempt(packet, '000000', auth)

    def test_intent_launch_and_reaped_identity_must_agree(self):
        with tempfile.TemporaryDirectory() as directory:
            packet, auth = Path(directory).resolve(), self.auth()
            row, _ = self.journal_fragment(packet, auth)
            result = packet / 'attempts/000000/result.json'
            result.write_bytes(a.encode(dict(row, child_reaped=False)))
            with self.assertRaisesRegex(a.Invalid, '^settled_launch_and_reaping$'):
                a.audit_attempt(packet, '000000', auth)
            result.write_bytes(a.encode(row))
            launch = packet / 'attempts/000000/launch.json'
            value = a.parse(launch.read_bytes())
            launch.write_bytes(a.encode(dict(value, pid=124)))
            with self.assertRaisesRegex(a.Invalid, '^settled_launch_and_reaping$'):
                a.audit_attempt(packet, '000000', auth)

    def test_retry_categories_exclude_semantic_and_unknown_outcomes(self):
        for code in ('network_error', 'adapter_deadline', 'incomplete_body'):
            self.assertTrue(a.retryable(dict(outcome='nonzero'), dict(code=code)))
        for code in ('http_error', 'download_workflow_changed', 'size_limit', 'invalid_json'):
            self.assertFalse(a.retryable(dict(outcome='nonzero'), dict(code=code)))
        for row, code in ((dict(outcome='unknown_lifecycle'), 'unknown_lifecycle'),
                          (dict(outcome='intent'), 'unknown_lifecycle'),
                          (dict(outcome='timeout', child_reaped=False), 'timeout_not_reaped')):
            with self.assertRaisesRegex(a.Invalid, '^' + code + '$'):
                a.retryable(row, None)

    def test_retry_bound_is_shared_and_cannot_restart_in_invocation(self):
        with tempfile.TemporaryDirectory() as directory:
            packet, auth = Path(directory).resolve(), self.auth()
            fetcher = a.Fetcher(packet, auth)
            success = dict(success=True)
            failure = dict(success=False)
            with mock.patch.object(a, 'attempt', side_effect=[success, success, failure]) as transport:
                fetcher.fresh('observe', None, 'before')
                fetcher.fresh('observe', None, 'after')
                with self.assertRaisesRegex(a.Invalid, '^transport_attempt_bound$'):
                    fetcher.fresh('observe', None, 'after')
                self.assertEqual(transport.call_count, 3)
                with self.assertRaisesRegex(a.Invalid, '^transport_attempt_bound$'):
                    fetcher.fresh('observe', None, 'after')
                self.assertEqual(transport.call_count, 3)

    def test_semantic_attempt_exception_stops_without_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            fetcher = a.Fetcher(Path(directory).resolve(), self.auth())
            sentinel = a.Invalid('NONPHYSICAL_semantic_sentinel')
            with mock.patch.object(a, 'attempt', side_effect=sentinel) as transport:
                with self.assertRaises(a.Invalid) as caught:
                    fetcher.fresh('download', a.FIXED[0], 'metadata_before')
                self.assertIs(caught.exception, sentinel)
                self.assertEqual(transport.call_count, 1)

    def test_requested_finished_version_one_observation_is_required(self):
        auth = self.auth()
        row = dict(id=auth['uuid'], name=auth['workflow'][:-2], workflow=auth['workflow'], version=1, status='finished')
        def buffer(matches):
            return a.encode(dict(schema='openmhd.galaxy-server-observation.v1', origin='server',
                                 observed_utc='2026-11-22T00:00:00+00:00', matches=matches))
        self.assertEqual(a.observation(buffer([row]), auth), row)
        for matches, code in (([], 'unique_requested_workflow'), ([row, row], 'unique_requested_workflow'),
                              ([dict(row, version=True)], 'requested_uuid_version'),
                              ([dict(row, id='00000000-0000-4000-8000-000000000000')], 'requested_uuid_version'),
                              ([dict(row, status='failed')], 'finished_build_required')):
            with self.assertRaisesRegex(a.Invalid, '^' + code + '$'):
                a.observation(buffer(matches), auth)

    def test_observation_interval_retains_retry_but_surrounds_downloads(self):
        with tempfile.TemporaryDirectory() as directory:
            packet, auth = Path(directory).resolve(), self.auth()
            record, entries = self.interval_fragments(packet, auth)
            a.fences(packet, auth, record, entries)
            entries[-1]['started_utc'] = '2026-11-22T00:00:00+00:00'
            with self.assertRaisesRegex(a.Invalid, '^download_before_baseline$'):
                a.fences(packet, auth, record, entries)

    def test_only_declared_success_paths_and_bounded_parts_are_requested(self):
        for name in (*a.FIXED, a.PREFIX + 'parts/geometry.part0000', a.PREFIX + 'parts/gravity.part0511'):
            self.assertEqual(a.remote_path(name), name)
        for name in (a.PREFIX + 'binaries/geometry3-case', a.PREFIX + 'export.failed.json',
                     a.PREFIX + 'parts/geometry.part512', a.PREFIX + '../secret'):
            with self.assertRaisesRegex(a.Invalid, '^download_path$'):
                a.remote_path(name)
        with self.assertRaisesRegex(a.Invalid, '^part_range$'):
            a.remote_path(a.PREFIX + 'parts/gravity.part0512')

    def test_two_example_discovery_requires_exact_order_and_typed_parts(self):
        # Discovery-only schema control: other fixed buffers are deliberately
        # non-JSON, so this cannot pass verify_records or become build evidence.
        metadata = {name: b'NONPHYSICAL discovery-only placeholder' for name in a.FIXED}
        build = dict(schema='openmhd.galaxy-driver-build.v1', status='complete', component_accepted=False,
            external_terminal_evidence_required=False, binaries=[
                dict(kind=kind, parts=[dict(path='parts/' + kind + '.part0000',
                     **a.descriptor(b'NONPHYSICAL opaque part'))]) for kind in ('geometry', 'gravity')])
        metadata[a.PREFIX + 'build.json'] = a.encode(build)
        self.assertEqual(a.discovered_paths(metadata), set(a.FIXED) | {
            a.PREFIX + 'parts/geometry.part0000', a.PREFIX + 'parts/gravity.part0000'})
        changed = copy.deepcopy(build)
        changed['binaries'][0]['parts'][0]['path'] = 'parts/geometry.part0001'
        metadata[a.PREFIX + 'build.json'] = a.encode(changed)
        with self.assertRaisesRegex(a.Invalid, '^part_descriptor_order$'):
            a.discovered_paths(metadata)
        changed = copy.deepcopy(build)
        changed['binaries'][0]['parts'][0]['bytes'] = True
        metadata[a.PREFIX + 'build.json'] = a.encode(changed)
        with self.assertRaisesRegex(a.Invalid, '^descriptor_size$'):
            a.discovered_paths(metadata)
        metadata[a.PREFIX + 'build.json'] = a.encode(dict(build, status='failed'))
        with self.assertRaisesRegex(a.Invalid, '^complete_build_before_part_discovery$'):
            a.discovered_paths(metadata)

    def test_regular_buffers_and_no_hidden_nested_manifest_extras(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            a.put(root, 'ordinary', b'NONPHYSICAL')
            self.assertEqual(a.read(root, 'ordinary'), b'NONPHYSICAL')
            (root / 'linked').symlink_to(root / 'ordinary')
            with self.assertRaisesRegex(a.Invalid, '^linked_path$'):
                a.read(root, 'linked')
            (root / 'linked').unlink()
            a.put(root, 'export/files.sha256.json', b'NONPHYSICAL extra')
            self.assertIn('files.sha256.json', a.inventory(root / 'export'))
            with self.assertRaisesRegex(a.Invalid, '^regular_bounded_file$'):
                a.read(root, 'ordinary', maximum=1)

    def test_duplicate_nonfinite_and_boolean_descriptor_inputs_rejected(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e400}', b'{"nested":[-1e400]}'):
            with self.assertRaises(a.Invalid):
                a.parse(raw)
        self.assertEqual(a.parse(b'{"n":1,"x":1.5}'), dict(n=1, x=1.5))
        with self.assertRaisesRegex(a.Invalid, '^descriptor_size$'):
            a.described(dict(bytes=True, sha256='0' * 64))
