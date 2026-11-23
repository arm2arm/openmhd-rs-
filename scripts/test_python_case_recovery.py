"""UNEXECUTED NONPHYSICAL metadata controls, one future REANA leaf per method.

Fragments below are NOT workflow observations, certificates, source archives or
complete passing campaigns. No fixture or target module is evaluated on import.
The complete positive verifier path must consume authentic future outputs.
"""
from datetime import datetime
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_provider():
    path = ROOT / 'tools/galaxy_python_evidence/python_case_recovery.py'
    spec = importlib.util.spec_from_file_location('nonphysical_python_case_recovery_controls', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PythonCompleteCaseRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.m = load_provider()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def release(self):
        m = self.m
        return dict(schema=m.RELEASE, invocation_path=str(self.root / 'out'), provider_sha256=m.sha(Path(m.__file__).read_bytes()),
            catalog=dict(source_revision='a' * 40, **{n: 'a' * 64 for n in
                ('snapshot_sha256', 'archive_sha256', 'job_sha256', 'certificate_sha256',
                 'plan_sha256', 'submission_sha256', 'identities_sha256')}),
            helpers={n: 'b' * 64 for n in m.TOOLS}, uuid_map_sha256='c' * 64,
            origins=[dict(manifest_sha256='d' * 64, summary_sha256='e' * 64)],
            root_review_sha256='f' * 64, get_acquisition_authorized=False, **m.SCOPE)

    def diagnostic(self, code='network_error'):
        m = self.m
        value = dict(schema='openmhd.metadata-readonly-adapter-diagnostic.v1', outcome='failure', code=code,
            started_utc='2026-11-23T00:00:01+00:00', finished_utc='2026-11-23T00:00:02+00:00',
            action='download', workflow='nonphysical-0000.1', requested_path='outputs/stdout.txt',
            http_status=None, workflow_ids=[], page_count=0, received_bytes=3, retained_bytes=3,
            partial_file='stdout.txt.partial')
        attempt = dict(outcome='nonzero', action=value['action'], workflow=value['workflow'],
            requested_path=value['requested_path'], started_utc='2026-11-23T00:00:00+00:00',
            finished_utc='2026-11-23T00:00:03+00:00', output='artifacts/stdout.txt',
            stdout=dict(path='stdout'), stderr=dict(path='stderr'))
        buffers = {'stdout': b'', 'stderr': m.encode(value), 'artifacts/stdout.txt.partial': b'abc'}
        old = SimpleNamespace(job=SimpleNamespace(utc=datetime.fromisoformat))
        return old, buffers, attempt, value

    def compact_fragment(self):
        # ONLY the compact job-side hash/coverage boundary, not a full packet.
        m = self.m
        release = self.release()
        identities = {s: dict(selector=s, source_path='NONPHYSICAL.py') for s in ('A.a', 'B.b')}
        snapshot = dict(source_revision='a' * 40, job_sha256='a' * 64,
            tests=list(identities), test_identities=identities, test_files=['NONPHYSICAL.py'])
        sr, certificate = m.encode(snapshot), b'NONPHYSICAL: not an import certificate\n'
        release['catalog'].update(snapshot_sha256=m.sha(sr), certificate_sha256=m.sha(certificate),
                                  identities_sha256=m.sha(m.encode(identities)))
        rr = m.encode(release)
        rows = [dict(directory=f'{i:04d}', selector=s, row=dict(status='passed', identity=identities[s]))
                for i, s in enumerate(identities)]
        summary = dict(schema=m.SUMMARY, release_sha256=m.sha(rr), provider_sha256=release['provider_sha256'],
            snapshot_sha256=m.sha(sr), preflight_certificate_sha256=m.sha(certificate), source_revision='a' * 40,
            catalog=dict(selectors=list(identities), test_identities=identities), expected_cases=2,
            counts=dict(passed=2, failed=0, pending=0, incomplete=0), whole_catalog_passed=True, cases=rows, **m.SCOPE)
        return sr, certificate, rr, summary

    def compact_call(self, fragment):
        m = self.m
        sr, certificate, rr, summary = fragment
        raw = m.encode(summary)
        files = {n: m.pin(v) for n, v in (('summary.json', raw), ('release.json', rr),
            ('context/shared/snapshot.json', sr), ('context/shared/preflight_certificate.json', certificate))}
        manifest = m.encode(dict(schema=m.FILES, tree=dict(files=files, directories=[]), **m.SCOPE))
        return m.compact(sr, certificate, raw, manifest, rr, m.sha(rr))

    def test_external_release_digest_precedes_any_helper_import_or_output(self):
        m = self.m
        raw = m.encode(self.release())
        m.put(self.root, 'release.json', raw)
        reached = []
        def forbidden(*args):
            reached.append(args)
            raise RuntimeError('NONPHYSICAL helper reached')
        with patch.object(m, 'helpers', side_effect=forbidden):
            with self.assertRaisesRegex(m.Rejected, '^external_root_release_digest$'):
                m.recover(self.root / 'release.json', '0' * 64, self.root / 'uuids.json', [], self.root, self.root / 'out')
        self.assertEqual(reached, [])
        self.assertFalse((self.root / 'out').exists())

    def test_release_has_literal_scope_and_boolean_live_authorization(self):
        m = self.m
        raw = m.encode(self.release())
        self.assertFalse(m.authenticate(raw, m.sha(raw))['get_acquisition_authorized'])
        for change in (dict(component_accepted=0), dict(physical_evolutions_run=0),
                       dict(get_acquisition_authorized=1)):
            value = dict(self.release(), **change)
            raw = m.encode(value)
            with self.subTest(change=change), self.assertRaisesRegex(m.Rejected, '^release_scope$'):
                m.authenticate(raw, m.sha(raw))

    def test_release_duplicate_origins_and_foreign_helper_inventory_rejected(self):
        m = self.m
        for change, error in ((dict(origins=self.release()['origins'] * 2), 'duplicate_or_invalid_origin'),
                (dict(helpers=dict(self.release()['helpers'], extra='0' * 64)), 'exact_keys')):
            raw = m.encode(dict(self.release(), **change))
            with self.subTest(error=error), self.assertRaisesRegex(m.Rejected, '^' + error + '$'):
                m.authenticate(raw, m.sha(raw))

    def test_duplicate_keys_nonfinite_constants_and_exponent_overflow_rejected(self):
        for raw, error in ((b'{"a":1,"a":2}', 'duplicate_json_key'), (b'[NaN]', 'nonfinite_json'),
                           (b'[1e9999]', 'nonfinite_json')):
            with self.subTest(raw=raw), self.assertRaisesRegex(self.m.Rejected, '^' + error + '$'):
                self.m.parse(raw)

    def test_existing_destination_is_preserved_before_helpers_or_get(self):
        m = self.m
        raw = m.encode(self.release())
        m.put(self.root, 'release.json', raw)
        out = self.root / 'out'
        m.put(out, 'prior', b'NONPHYSICAL prior owner\n')
        with patch.object(m, 'helpers') as imported:
            with self.assertRaisesRegex(m.Rejected, '^fresh_exclusive_destination$'):
                m.recover(self.root / 'release.json', m.sha(raw), self.root / 'uuids', [], self.root, out)
        imported.assert_not_called()
        self.assertEqual(m.read(out, 'prior'), b'NONPHYSICAL prior owner\n')
        self.assertEqual({p.name for p in out.iterdir()}, {'prior'})

    def test_release_cannot_reset_attempt_budget_by_choosing_another_destination(self):
        m = self.m
        raw = m.encode(self.release())
        m.put(self.root, 'release.json', raw)
        with patch.object(m, 'helpers') as imported:
            with self.assertRaisesRegex(m.Rejected, '^root_released_invocation_path$'):
                m.recover(self.root / 'release.json', m.sha(raw), self.root / 'uuids', [], self.root, self.root / 'another')
        imported.assert_not_called()
        self.assertFalse((self.root / 'another').exists())

    def test_link_special_path_and_hardlink_are_not_closed_inputs(self):
        m = self.m
        m.put(self.root, 'body', b'NONPHYSICAL')
        (self.root / 'alias').symlink_to(self.root / 'body')
        with self.assertRaisesRegex(m.Rejected, '^linked_path$'):
            m.read(self.root, 'alias')
        import os
        os.link(self.root / 'body', self.root / 'hard')
        with self.assertRaisesRegex(m.Rejected, '^bounded_regular_unlinked_file$'):
            m.read(self.root, 'hard')
        with self.assertRaisesRegex(m.Rejected, '^relative_path$'):
            m.at(self.root, '../outside')

    def test_fresh_helpers_reject_cache_without_replacing_existing_module(self):
        m = self.m
        release = self.release()
        for name in m.TOOLS:
            raw = b'# NONPHYSICAL inert module fragment\n'
            m.put(self.root, name, raw)
            release['helpers'][name] = m.sha(raw)
        prior = SimpleNamespace(__file__='/NONPHYSICAL/unrelated.py')
        with patch.dict(sys.modules, {'reana_metadata_job': prior}), patch.object(m.importlib, 'import_module') as imported:
            with self.assertRaisesRegex(m.Rejected, '^fresh_process_not_conflicting_cache$'):
                m.helpers(self.root, release)
            self.assertIs(sys.modules['reana_metadata_job'], prior)
        imported.assert_not_called()

    def test_helper_source_pin_precedes_import(self):
        with patch.object(self.m.importlib, 'import_module') as imported:
            for name in self.m.TOOLS:
                self.m.put(self.root, name, b'# NONPHYSICAL wrong source\n')
            with self.assertRaisesRegex(self.m.Rejected, '^helper_source_before_import$'):
                self.m.helpers(self.root, self.release())
        imported.assert_not_called()

    def test_original_uuid_map_requires_exact_order_unique_uuid_and_int_version(self):
        m = self.m
        plan = dict(cases=[dict(directory=f'{i:04d}', workflow=f'nonphysical-{i:04d}.1') for i in range(2)])
        value = dict(schema='openmhd.python-original-uuid-map.v1', cases=[dict(e,
            uuid=f'00000000-0000-4000-8000-{i + 1:012d}', version=1) for i, e in enumerate(plan['cases'])])
        release = self.release()
        def checked(v):
            raw = m.encode(v)
            return m.ids(raw, dict(release, uuid_map_sha256=m.sha(raw)), plan)
        self.assertEqual(len(checked(value)), 2)
        variants = []
        for field, new in (('version', True), ('uuid', value['cases'][1]['uuid']), ('workflow', 'wrong.1')):
            v = copy.deepcopy(value)
            v['cases'][0][field] = new
            variants.append(v)
        variants.append(dict(value, cases=list(reversed(value['cases']))))
        for v in variants:
            with self.subTest(value=v), self.assertRaisesRegex(m.Rejected, '^unique_original_version1_uuid$'):
                checked(v)

    def test_multi_origin_selection_uses_one_whole_capture_without_mutating_failures(self):
        m = self.m
        candidates = [dict(disposition='loss', origin='first whole case'),
                      dict(disposition='passed', origin='second whole case')]
        saved = copy.deepcopy(candidates)
        self.assertEqual(m.select_complete(candidates), 1)
        self.assertEqual(candidates, saved)
        self.assertIsNone(m.select_complete([candidates[0]]))

    def test_complete_actual_method_failure_is_not_a_retry_or_a_vote(self):
        for losses in (False, True):
            with self.subTest(losses=losses), self.assertRaisesRegex(self.m.Rejected, '^actual_complete_method_failure_not_retryable$'):
                self.m.disposition(dict(status='failed'), losses)
        with self.assertRaisesRegex(self.m.Rejected, '^candidate_disposition$'):
            self.m.select_complete([dict(disposition='passed'), dict(disposition='failed')])

    def test_complete_semantic_invalid_capture_stops_without_transport_retry(self):
        with self.assertRaisesRegex(self.m.Rejected, '^semantic_invalid_complete_capture$'):
            self.m.disposition(dict(status='incomplete', classification='invalid_or_job_failure_envelope'), False)

    def test_successful_remote_body_change_is_rejected_even_in_loss_capture(self):
        m = self.m
        def fragment(raw):
            return {'transport.json': m.encode(dict(attempts=[dict(outcome='success', output='artifacts/stdout.txt')])),
                    'artifacts/stdout.txt': raw}
        m.consistent([fragment(b'NONPHYSICAL A'), fragment(b'NONPHYSICAL A')])
        with self.assertRaisesRegex(m.Rejected, '^changed_remote_body_between_origins$'):
            m.consistent([fragment(b'NONPHYSICAL A'), fragment(b'NONPHYSICAL B')])

    def test_matching_failed_partial_is_never_promoted_or_merged(self):
        m = self.m
        data = {'transport.json': m.encode(dict(attempts=[dict(outcome='nonzero', output='artifacts/stdout.txt')])),
                'artifacts/stdout.txt.partial': b'NONPHYSICAL matches expected bytes'}
        self.assertEqual(m.visible(None, data, {}, {}, b'', 'unused'), {})
        data['artifacts/stdout.txt'] = data['artifacts/stdout.txt.partial']
        with self.assertRaisesRegex(m.Rejected, '^failed_matching_partial_never_canonical$'):
            m.visible(None, data, {}, {}, b'', 'unused')

    def test_network_diagnostic_requires_retained_partial_and_exact_clock(self):
        m = self.m
        old, buffers, attempt, value = self.diagnostic()
        self.assertTrue(m.diagnostic(old, buffers, attempt, 'unused'))
        del buffers['artifacts/stdout.txt.partial']
        with self.assertRaisesRegex(m.Rejected, '^typed_transport_loss_and_retained_partial$'):
            m.diagnostic(old, buffers, attempt, 'unused')
        old, buffers, attempt, value = self.diagnostic()
        value['started_utc'] = '2026-11-22T23:59:00+00:00'
        buffers['stderr'] = m.encode(value)
        with self.assertRaisesRegex(m.Rejected, '^diagnostic_clock$'):
            m.diagnostic(old, buffers, attempt, 'unused')

    def test_authentication_protocol_or_bool_http_errors_are_not_retryable(self):
        m = self.m
        for code, status in (('local_or_protocol_error', None), ('http_error', 401), ('http_error', True)):
            old, buffers, attempt, value = self.diagnostic(code)
            value['http_status'] = status
            buffers['stderr'] = m.encode(value)
            with self.subTest(code=code, status=status), self.assertRaisesRegex(m.Rejected, '^typed_transport_loss_and_retained_partial$'):
                m.diagnostic(old, buffers, attempt, 'unused')

    def test_pending_and_start_failed_authority_stop_without_retry(self):
        old, buffers, attempt, _ = self.diagnostic()
        for outcome in ('pending_launch', 'start_failed'):
            with self.subTest(outcome=outcome), self.assertRaisesRegex(self.m.Unknown, '^unsettled_or_unstarted_adapter_not_transport_retry$'):
                self.m.diagnostic(old, buffers, dict(attempt, outcome=outcome), 'unused')

    def test_settled_direct_adapter_timeout_has_no_inferred_download_success(self):
        m = self.m
        value = dict(outcome='timeout', returncode=None, download_sha256=None)
        self.assertTrue(m.diagnostic(None, {}, value, 'unused'))
        with self.assertRaisesRegex(m.Rejected, '^timeout_receipt$'):
            m.diagnostic(None, {}, dict(value, download_sha256='a' * 64), 'unused')

    def test_uuid_version_and_nonterminal_observations_stop(self):
        m = self.m
        old = SimpleNamespace(job=SimpleNamespace(server_status=lambda value, workflow: value['matches'][0]['status']))
        good = dict(matches=[dict(id='original', version=1, status='finished')])
        m.observation(old, m.encode(good), 'nonphysical.1', 'original')
        for changes, error in ((dict(id='other'), 'observed_original_uuid_version'),
                (dict(version=True), 'observed_original_uuid_version'),
                (dict(status='running'), 'original_nonterminal_requires_external_evidence'),
                (dict(status='failed'), 'original_terminal_failure_not_retryable')):
            with self.subTest(changes=changes), self.assertRaisesRegex(m.Rejected, '^' + error + '$'):
                m.observation(old, m.encode(dict(matches=[dict(good['matches'][0], **changes)])), 'nonphysical.1', 'original')

    def test_visible_source_drift_precedes_missing_artifact_retry(self):
        m = self.m
        entry = dict(specification=dict(selector='NONPHYSICAL'), payload_sha256='a' * 64)
        snapshot = dict(source_revision='a' * 40, source_sha256={})
        result = dict(case=entry['specification'], source_revision='b' * 40,
                      snapshot_sha256=m.sha(b'snapshot'), source_sha256={}, payload_sha256='a' * 64)
        data = {'transport.json': m.encode(dict(attempts=[dict(outcome='success', output='artifacts/result.json')])),
                'artifacts/result.json': m.encode(result)}
        with self.assertRaisesRegex(m.Rejected, '^visible_source_drift$'):
            m.visible(None, data, entry, snapshot, b'snapshot', 'unused')

    def test_visible_runtime_uuid_drift_cannot_be_hidden_by_get_loss(self):
        m = self.m
        data = {'transport.json': m.encode(dict(attempts=[dict(outcome='success', output='artifacts/runtime.json')])),
                'artifacts/runtime.json': m.encode(dict(job_path='/NONPHYSICAL/other/job.py', optimized=0))}
        with self.assertRaisesRegex(m.Rejected, '^visible_runtime_uuid_drift$'):
            m.visible(None, data, {}, {}, b'', 'original')

    def test_retry_budget_is_three_whole_attempts_and_stops_after_success(self):
        calls = []
        def perform(index):
            calls.append(index)
            return dict(disposition='passed' if index == 2 else 'loss')
        self.assertEqual(self.m.bounded(perform)['disposition'], 'passed')
        self.assertEqual(calls, [1, 2])
        calls.clear()
        def losses(index):
            calls.append(index)
            return dict(disposition='loss')
        with self.assertRaisesRegex(self.m.Rejected, '^three_settled_transport_losses_exhausted$'):
            self.m.bounded(losses)
        self.assertEqual(calls, [1, 2, 3])

    def test_unknown_sentinel_stops_first_attempt_without_swallowed_callback(self):
        calls = []
        sentinel = self.m.Unknown('NONPHYSICAL unsettled sentinel')
        def perform(index):
            calls.append(index)
            raise sentinel
        with self.assertRaises(self.m.Unknown) as caught:
            self.m.bounded(perform)
        self.assertIs(caught.exception, sentinel)
        self.assertEqual(calls, [1])

    def test_post_launch_exception_retains_running_intent_and_unknown_state(self):
        m = self.m
        out = self.root / 'attempt'
        observed = []
        sentinel = RuntimeError('NONPHYSICAL escaping transport sentinel')
        def escape(*args, **kwargs):
            observed.append((m.parse(m.read(out, 'state.json')), args[2:4]))
            raise sentinel
        old = SimpleNamespace(prepare=SimpleNamespace(adapter_attempt=escape))
        entry = dict(directory='0000', workflow='nonphysical.1')
        with self.assertRaises(RuntimeError) as caught:
            m.attempt(old, out, entry, {}, b'', {}, ['/NONPHYSICAL/python', '/NONPHYSICAL/adapter'], 'original')
        self.assertIs(caught.exception, sentinel)
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0][0]['status'], 'running')
        self.assertIs(observed[0][0]['external_evidence_required'], True)
        state = m.parse(m.read(out, 'state.json'))
        self.assertEqual((state['status'], state['error_type']), ('unknown', 'RuntimeError'))
        self.assertIsNone(state['finished_utc'])
        self.assertIs(state['external_evidence_required'], True)
        self.assertFalse((out / 'capture.json').exists())

    def test_sequence_counters_cannot_restart_or_skip(self):
        root = self.root / 'sequence'
        root.mkdir()
        (root / '01').mkdir()
        self.assertEqual([p.name for p in self.m.sequence_paths(root)], ['01'])
        (root / '03').mkdir()
        with self.assertRaisesRegex(self.m.Rejected, '^bounded_no_counter_reset_sequence$'):
            self.m.sequence_paths(root)

    def test_corrupt_or_resealed_unadmitted_origin_stops_before_original_validator(self):
        m = self.m
        origin = self.root / 'origin'
        m.put(origin, 'files.sha256.json', b'{"NONPHYSICAL": "resealed foreign origin"}\n')
        m.put(origin, 'summary.json', b'{"NONPHYSICAL": true}\n')
        old = SimpleNamespace(verify_packet=unittest.mock.Mock())
        with self.assertRaisesRegex(m.Rejected, '^root_admitted_origin$'):
            m.origin_graph(old, [origin], self.release())
        old.verify_packet.assert_not_called()

    def test_own_inventory_relocation_uses_bytes_not_historical_absolute_paths(self):
        m = self.m
        source = self.root / 'fragment'
        m.put(source, 'command-fragment.json', m.encode(['/NONPHYSICAL/deleted/python', '/NONPHYSICAL/deleted/adapter.py']))
        m.seal(source)
        before = m.closed(source)
        relocated = self.root / 'relocated'
        shutil.copytree(source, relocated)
        self.assertEqual(m.closed(relocated), before)
        (relocated / 'extra').write_bytes(b'NONPHYSICAL')
        with self.assertRaisesRegex(m.Rejected, '^closed_recovered_inventory$'):
            m.closed(relocated)

    def test_summary_retains_each_original_nonpassing_outcome(self):
        m = self.m
        rows = [dict(row=dict(status='passed'))] * 2
        graph = {'a' * 64: dict(summary=dict(counts=dict(passed=1, incomplete=1), whole_suite_passed=False)),
                 'b' * 64: dict(summary=dict(counts=dict(passed=1, incomplete=1), whole_suite_passed=False))}
        snapshot = dict(source_revision='a' * 40, tests=['A', 'B'], test_identities={}, test_files=[])
        value = m.summary_value(self.release(), '0' * 64, snapshot, dict(cases=[{}, {}]), rows, graph)
        self.assertTrue(value['whole_catalog_passed'])
        self.assertTrue(all(v['whole_suite_passed'] is False for v in value['original_outcomes'].values()))
        self.assertIs(value['authenticated_external_prerequisite'], False)
        with self.assertRaisesRegex(m.Rejected, '^full_catalog_strict_selection$'):
            m.summary_value(self.release(), '0' * 64, snapshot, dict(cases=[{}, {}]), rows[:1], graph)

    def test_new_schema_compact_fragment_requires_full_ordered_catalog_not_count_flags(self):
        fragment = self.compact_fragment()
        self.assertEqual(self.compact_call(fragment)['expected_cases'], 2)
        for rows in (fragment[3]['cases'][:1], list(reversed(fragment[3]['cases'])), fragment[3]['cases'][:1] * 2):
            changed = (*fragment[:3], dict(fragment[3], cases=rows))
            with self.subTest(rows=rows), self.assertRaises(self.m.Rejected):
                self.compact_call(changed)

    def test_compact_resealed_bool_scope_count_or_identity_does_not_pass(self):
        fragment = self.compact_fragment()
        for change, error in ((dict(component_accepted=0), 'proof_nonacceptance'),
                (dict(expected_cases=True), 'compact_exact_whole_catalog'),
                (dict(counts=dict(passed=2, failed=False, pending=0, incomplete=0)), 'compact_exact_whole_catalog')):
            with self.subTest(change=change), self.assertRaisesRegex(self.m.Rejected, '^' + error + '$'):
                self.compact_call((*fragment[:3], dict(fragment[3], **change)))

    def test_invocation_retains_actual_adapter_source_and_input_witness_validator(self):
        m = self.m
        release = self.release()
        release['invocation_path'] = '/NONPHYSICAL/original'
        seen = []
        def validate(value, *args):
            seen.append((value, args))
        old = SimpleNamespace(CAPTURE_SCHEMA='NONPHYSICAL capture fragment',
            job=SimpleNamespace(credential_free_argv=lambda value: None), validate_witnesses=validate)
        value = dict(schema='openmhd.python-complete-case-invocation.v1', output_path='/NONPHYSICAL/original',
            provider_sha256=release['provider_sha256'], adapter_sha256=release['helpers']['reana_metadata_readonly_adapter.py'],
            adapter_interpreter=dict(bytes=1, sha256='0' * 64), input_sources={},
            host_interpreter=dict(executable='/NONPHYSICAL/python', python='NONPHYSICAL version', optimized=0), **m.SCOPE)
        command = ['/NONPHYSICAL/python', '/NONPHYSICAL/original/tools/reana_metadata_readonly_adapter.py']
        m.invocation_check(old, value, command, release, ({}, {}, {}, {}))
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][0]['adapter_argv'], command)
        with self.assertRaisesRegex(m.Rejected, '^retained_actual_adapter_source_path_link$'):
            m.invocation_check(old, value, ['/NONPHYSICAL/python', '/NONPHYSICAL/replaced/adapter.py'], release, ({}, {}, {}, {}))
        self.assertEqual(len(seen), 1)
