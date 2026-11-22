"""UNEXECUTED metadata controls; fragments are NONPHYSICAL, not a175 packet.

Future test inputs must retain reading/frozen_tools with the exact four original
helper files. No workflow, source archive, child or successful method is faked.
Each ordinary method requires its own resource-declared REANA workflow.
"""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import recover_python_catalog as recovery


BUNDLE = Path(__file__).parent / 'reading/frozen_tools'
IDENTIFIER = '00000000-0000-4000-8000-000000000001'
OTHER = '00000000-0000-4000-8000-000000000002'


class RecoveryMetadataTests(unittest.TestCase):
    def entries(self):
        # Deliberately two policy rows, NOT the production175 original catalog.
        return [dict(directory=f'{i:04d}', workflow=f'NONPHYSICAL-{i:04d}.1',
                     specification=dict(selector=f'nonphysical.Suite.test_{i}')) for i in range(2)]

    def selected(self, entries):
        return [dict(directory=e['directory'], workflow=e['workflow'], selector=e['specification']['selector'])
                for e in entries]

    def fragment(self, *, outcome='success', code='completed', ids=None, action='observe'):
        # Diagnostic/prefix fragment only: never a full old strict case packet.
        stamp = '2026-11-22T00:00:00+00:00'
        value = dict(schema='openmhd.metadata-readonly-adapter-diagnostic.v1',
            outcome='success' if outcome == 'success' else 'failure', code=code,
            started_utc=stamp, finished_utc=stamp, action=action, workflow='NONPHYSICAL-0000.1',
            requested_path=None if action == 'observe' else 'outputs/result.json', http_status=None,
            workflow_ids=[IDENTIFIER] if ids is None else ids, page_count=1,
            received_bytes=0, retained_bytes=0, partial_file=None)
        a = dict(outcome=outcome, returncode=0 if outcome == 'success' else 1,
            download_sha256=None, action=action, workflow=value['workflow'], requested_path=value['requested_path'],
            started_utc=stamp, finished_utc=stamp, output='server-before.json' if action == 'observe' else 'artifacts/result.json',
            stdout=dict(path='transport/00.stdout.txt'), stderr=dict(path='transport/00.stderr.txt'))
        buffers = {'transport/00.stdout.txt': recovery.encode(value) if outcome == 'success' else b'',
                   'transport/00.stderr.txt': recovery.encode(value) if outcome != 'success' else b''}
        if outcome != 'success':
            value['partial_file'] = Path(a['output']).name + '.partial'
            buffers[a['output'] + '.partial'] = b''
            buffers[a['stderr']['path']] = recovery.encode(value)
        return a, buffers, value

    def test_selection_exact_policy_rows(self):
        entries = self.entries()
        recovery.validate_selection(entries, self.selected(entries))

    def test_selection_missing_extra_duplicate_or_wrong_source_row(self):
        entries = self.entries()
        good = self.selected(entries)
        recovery.validate_selection(entries, good)
        wrong = copy.deepcopy(good)
        wrong[0]['selector'] = 'nonphysical.Stale.test_other'
        for rows in (good[:-1], good + [good[0]], [good[0], good[0]], list(reversed(good)), wrong):
            with self.subTest(rows=rows), self.assertRaises(recovery.RecoveryError):
                recovery.validate_selection(entries, rows)

    def test_selection_binds_whole_origin_tree_uuid_and_row(self):
        entry = self.entries()[0]
        # Pure selection-policy fragment, no full method/result/packet claimed.
        origin = dict(kind='whole_attempt', path='attempts/0000/01', closure_sha256='1' * 64)
        observed = dict(files={'failed.partial': recovery.desc(b'NONPHYSICAL')}, directories=[])
        row = dict(status='NONPHYSICAL policy label')
        choice = dict(directory=entry['directory'], selector=entry['specification']['selector'],
            workflow=entry['workflow'], uuid=IDENTIFIER, origin=origin, case_tree=observed, row=row)
        recovery.selected_whole_case(choice, entry, IDENTIFIER, origin, observed, row)
        changes = [dict(uuid=OTHER), dict(origin=dict(kind='file_graft', path='artifacts/result.json')),
                   dict(case_tree=dict(files={}, directories=[])), dict(row=dict(status='passed')),
                   dict(extra_file='artifacts/result.json')]
        for change in changes:
            mutated = copy.deepcopy(choice)
            mutated.update(change)
            with self.subTest(change=change), self.assertRaises(recovery.RecoveryError):
                recovery.selected_whole_case(mutated, entry, IDENTIFIER, origin, observed, row)

    def test_release_requires_actual_recovery_source_bytes(self):
        source = recovery.sha(Path(recovery.__file__).read_bytes())
        # Not an authorization or actual closed06 release: dummy other pins.
        release = dict(schema='openmhd.galaxy-python-recovery-release.v1', recovery_source_sha256=source,
            base_manifest_sha256=recovery.BASE_MANIFEST, history_tree_sha256='2' * 64,
            history_outer_sha256='3' * 64, root_review_sha256='4' * 64)
        self.assertEqual(recovery.release_check(recovery.encode(release)), release)
        release['recovery_source_sha256'] = '0' * 64 if source != '0' * 64 else '1' * 64
        with self.assertRaisesRegex(recovery.RecoveryError, 'module source pin'):
            recovery.release_check(recovery.encode(release))

    def test_bounded_transport_losses_then_complete(self):
        calls = []
        def perform(index):
            calls.append(index)
            return dict(disposition='complete' if index == 3 else 'loss')
        result = recovery.bounded_attempts(perform)
        self.assertEqual(calls, [1, 2, 3])
        self.assertEqual(result['disposition'], 'complete')

    def test_three_losses_exhaust_without_fourth_attempt(self):
        calls = []
        def perform(index):
            calls.append(index)
            return dict(disposition='loss')
        with self.assertRaises(recovery.TransportExhausted):
            recovery.bounded_attempts(perform)
        self.assertEqual(calls, [1, 2, 3])

    def test_semantic_contradiction_stops_without_retry(self):
        calls = []
        sentinel = recovery.RecoveryError('NONPHYSICAL semantic sentinel')
        def perform(index):
            calls.append(index)
            raise sentinel
        with self.assertRaises(recovery.RecoveryError) as caught:
            recovery.bounded_attempts(perform)
        self.assertIs(caught.exception, sentinel)
        self.assertEqual(calls, [1])

    def test_complete_method_failure_stops_and_remains_failed(self):
        calls = []
        failed = dict(disposition='complete', row=dict(status='failed'))
        def perform(index):
            calls.append(index)
            return failed
        result = recovery.bounded_attempts(perform)
        self.assertIs(result, failed)
        self.assertEqual(result['row']['status'], 'failed')
        self.assertEqual(calls, [1])

    def test_unknown_attempt_has_no_retry_authority(self):
        calls = []
        sentinel = recovery.UnknownAttempt('NONPHYSICAL pending sentinel')
        def perform(index):
            calls.append(index)
            raise sentinel
        with self.assertRaises(recovery.UnknownAttempt) as caught:
            recovery.bounded_attempts(perform)
        self.assertIs(caught.exception, sentinel)
        self.assertEqual(calls, [1])

    def test_old_unfinished_history_remains_unknown_and_unmodified(self):
        status = recovery.encode(dict(status='collecting', finished_utc=None))
        outer = recovery.encode(dict(outcome='running', finished_utc=None, returncode=None))
        before = status, outer
        result = recovery.unknown_history(status, outer)
        self.assertEqual(result['assessment'], 'unknown')
        self.assertTrue(result['process_absence_is_not_completion'])
        self.assertEqual(result['status'], recovery.desc(status))
        self.assertEqual((status, outer), before)
        for changes in (dict(finished_utc='2026-11-22T00:00:00+00:00'), dict(outcome='success', returncode=0)):
            mutated = recovery.parse(outer)
            mutated.update(changes)
            with self.assertRaises(recovery.RecoveryError):
                recovery.unknown_history(status, recovery.encode(mutated))

    def test_network_loss_is_eligible_but_identity_and_auth_are_not(self):
        with recovery.frozen_api(BUNDLE) as old:
            good, buffers, _ = self.fragment()
            self.assertFalse(recovery.diagnostic(old, buffers, good, IDENTIFIER))
            for code in ('network_error', 'incomplete_body', 'content_length_mismatch', 'adapter_deadline'):
                a, buffers, _ = self.fragment(outcome='nonzero', code=code, ids=[])
                self.assertTrue(recovery.diagnostic(old, buffers, a, IDENTIFIER))
            for code in ('identity_changed', 'invalid_server_metadata', 'configuration', 'unauthorized'):
                a, buffers, _ = self.fragment(outcome='nonzero', code=code, ids=[])
                with self.subTest(code=code), self.assertRaises(recovery.RecoveryError):
                    recovery.diagnostic(old, buffers, a, IDENTIFIER)

    def test_http_loss_policy_is_bounded(self):
        with recovery.frozen_api(BUNDLE) as old:
            for status, retry in ((429, True), (500, True), (599, True), (401, False), (404, False)):
                a, buffers, value = self.fragment(outcome='nonzero', code='http_error', ids=[])
                value['http_status'] = status
                buffers[a['stderr']['path']] = recovery.encode(value)
                if retry:
                    self.assertTrue(recovery.diagnostic(old, buffers, a, IDENTIFIER))
                else:
                    with self.assertRaises(recovery.RecoveryError):
                        recovery.diagnostic(old, buffers, a, IDENTIFIER)

    def test_original_uuid_mismatch_is_not_transport_loss(self):
        with recovery.frozen_api(BUNDLE) as old:
            a, buffers, _ = self.fragment()
            self.assertFalse(recovery.diagnostic(old, buffers, a, IDENTIFIER))
            for outcome in ('success', 'nonzero'):
                a, buffers, _ = self.fragment(outcome=outcome, code='completed' if outcome == 'success' else 'network_error', ids=[OTHER])
                with self.assertRaisesRegex(recovery.RecoveryError, 'UUID'):
                    recovery.diagnostic(old, buffers, a, IDENTIFIER)

    def test_pending_or_invalid_publication_is_not_retryable(self):
        with recovery.frozen_api(BUNDLE) as old:
            a, buffers, _ = self.fragment()
            a.update(outcome='pending_launch', returncode=None)
            with self.assertRaises(recovery.UnknownAttempt):
                recovery.diagnostic(old, buffers, a, IDENTIFIER)
            for outcome in ('invalid_download', 'start_failed'):
                a['outcome'] = outcome
                with self.assertRaises(recovery.RecoveryError):
                    recovery.diagnostic(old, buffers, a, IDENTIFIER)

    def test_failed_receipt_partial_cannot_promote_canonical_body(self):
        with recovery.frozen_api(BUNDLE) as old:
            a, _, _ = self.fragment(outcome='nonzero', code='incomplete_body', ids=[], action='download')
            buffers = {'transport.json': recovery.encode(dict(attempts=[a])),
                       'artifacts/result.json.partial': b'NONPHYSICAL incomplete bytes'}
            self.assertEqual(recovery.visible_artifacts(old, buffers, {}, {}, b'', IDENTIFIER), {})
            buffers['artifacts/result.json'] = b'NONPHYSICAL cannot be promoted'
            with self.assertRaisesRegex(recovery.RecoveryError, 'Failed receipt'):
                recovery.visible_artifacts(old, buffers, {}, {}, b'', IDENTIFIER)

    def test_cross_attempt_original_bodies_cannot_change_or_graft(self):
        with recovery.frozen_api(BUNDLE) as old:
            a = dict(outcome='success', output='artifacts/stdout.txt')
            def capture(raw):
                return {'transport.json': recovery.encode(dict(attempts=[a])), 'artifacts/stdout.txt': raw}
            first, second = capture(b'NONPHYSICAL first body'), capture(b'NONPHYSICAL first body')
            recovery.consistent_history(old, [first, second])
            originals = copy.deepcopy([first, second])
            with self.assertRaisesRegex(recovery.RecoveryError, 'Changed original remote body'):
                recovery.consistent_history(old, [first, capture(b'NONPHYSICAL changed body')])
            self.assertEqual([first, second], originals)

    def test_visible_manifest_hash_contradiction_stops_incomplete_case(self):
        with recovery.frozen_api(BUNDLE) as old:
            attempts = [dict(outcome='success', output='artifacts/' + n) for n in ('stdout.txt', 'artifacts.sha256.json')]
            manifest = {'outputs/' + n: recovery.sha(b'NONPHYSICAL absent') for n in old.job.OUTPUT_NAMES if n != 'artifacts.sha256.json'}
            manifest['outputs/stdout.txt'] = recovery.sha(b'NONPHYSICAL stdout')
            buffers = {'transport.json': recovery.encode(dict(attempts=attempts)),
                'artifacts/stdout.txt': b'NONPHYSICAL stdout', 'artifacts/artifacts.sha256.json': recovery.encode(manifest)}
            recovery.visible_artifacts(old, buffers, {}, {}, b'', IDENTIFIER)
            buffers['artifacts/stdout.txt'] += b' changed'
            with self.assertRaisesRegex(recovery.RecoveryError, 'hash mismatch'):
                recovery.visible_artifacts(old, buffers, {}, {}, b'', IDENTIFIER)

    def test_bad_helper_pin_rejects_before_definition_loading(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in recovery.HELPERS:
                (root / name).write_bytes(b'# NONPHYSICAL wrong helper\n')
            launches = []
            def forbidden(*args, **kwargs):
                launches.append(args)
                raise AssertionError('definition loader must not be reached')
            with mock.patch.object(recovery.importlib.util, 'spec_from_file_location', forbidden):
                with self.assertRaisesRegex(recovery.RecoveryError, 'Exact original helper bundle'):
                    with recovery.frozen_api(root):
                        self.fail('bad helper accepted')
            self.assertEqual(launches, [])

    def test_exact_bundle_namespace_is_restored(self):
        names = ('reana_metadata_job', 'prepare_metadata_reana', 'collect_metadata_reana_results')
        before = {n: (n in recovery.sys.modules, recovery.sys.modules.get(n)) for n in names}
        bytecode = recovery.sys.dont_write_bytecode
        with recovery.frozen_api(BUNDLE) as old:
            self.assertEqual(old.host_tools.__name__, 'host_tools')
            self.assertEqual(Path(old.__file__).parent, BUNDLE.absolute())
            self.assertTrue(recovery.sys.dont_write_bytecode)
        self.assertEqual({n: (n in recovery.sys.modules, recovery.sys.modules.get(n)) for n in names}, before)
        self.assertEqual(recovery.sys.dont_write_bytecode, bytecode)

    def test_retained_tree_copy_preserves_partial_and_rejects_existing_destination(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, retained = root / 'source', root / 'retained'
            source.mkdir()
            (source / 'failed.partial').write_bytes(b'NONPHYSICAL failed partial')
            (source / 'empty').mkdir()
            before = recovery.tree(source)
            recovery.copy_tree(source, retained)
            self.assertEqual(recovery.tree(retained), before)
            self.assertEqual(recovery.tree(source), before)
            with self.assertRaises(recovery.RecoveryError):
                recovery.copy_tree(source, retained)
            (retained / 'failed.partial').write_bytes(b'changed')
            self.assertNotEqual(recovery.tree(retained), before)

    def test_type_sensitive_closure_cannot_alias_boolean_and_integer(self):
        self.assertTrue(recovery.same(dict(bytes=1), dict(bytes=1)))
        self.assertFalse(recovery.same(dict(bytes=1), dict(bytes=True)))
        self.assertFalse(recovery.same(dict(bytes=1), dict(bytes=1.0)))

    def test_offline_entrypoint_never_dispatches_acquisition(self):
        calls = []
        sentinel = recovery.RecoveryError('NONPHYSICAL no packet')
        def verify(path):
            calls.append(('verify', str(path)))
            raise sentinel
        def forbidden(*args, **kwargs):
            calls.append(('acquire',))
            raise AssertionError('offline must not acquire')
        with mock.patch.object(recovery, 'verify_recovered', verify), mock.patch.object(recovery, 'recover', forbidden):
            with self.assertRaises(recovery.RecoveryError) as caught:
                recovery.main(['verify-recovered', '--packet', '/NONPHYSICAL/packet'])
        self.assertIs(caught.exception, sentinel)
        self.assertEqual(calls, [('verify', '/NONPHYSICAL/packet')])


if __name__ == '__main__':
    unittest.main()
