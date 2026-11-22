"""UNEXECUTED metadata controls; no live API and no complete positive preflight.

Every fixture below is a deliberately NONPHYSICAL isolated byte/receipt fragment.
The fixed real UUID is a protocol field only, never an asserted observation.
"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location('transfer_recovery_under_test',
    Path(__file__).resolve().parents[1] / 'recover_preflight.py')
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)


class TransferRecoveryMetadataTests(unittest.TestCase):
    def fragment(self, root, body=b'NONPHYSICAL opaque fragment\n', success=True, remote='outputs/logs/00.log'):
        root.mkdir(parents=True, exist_ok=True)
        helpers = {name: r.sha(('SYNTHETIC ' + name).encode()) for name in r.HELPERS}
        output = 'downloads/0000.body'
        argv = ['/usr/bin/python3', '-B', '/not-executed/tools/galaxy_evidence/readonly_adapter.py',
                'download', '--workflow', r.WORKFLOW, '--output', str(root / output), '--path', remote]
        diagnostic = dict(schema='openmhd.galaxy-get-diagnostic.v1', action='download', workflow=r.WORKFLOW,
            requested_path=remote, outcome='success' if success else 'failure',
            code='completed' if success else 'network_error', workflow_ids=[r.UUID] if success else [],
            partial_file=None if success else '0000.body.partial', retained_bytes=0)
        row = dict(schema='openmhd.galaxy-transport-attempt.v1', action='download', remote_path=remote,
            workflow=r.WORKFLOW, argv=argv, cwd=str(root), output=output,
            started_utc='2026-11-22T00:00:00+00:00', finished_utc='2026-11-22T00:00:01+00:00',
            outcome='success' if success else 'nonzero', returncode=0 if success else 1,
            adapter_sha256=helpers[r.HELPERS[0]], base_adapter_sha256=helpers[r.HELPERS[1]],
            stdout='transport/0000.stdout', stderr='transport/0000.stderr')
        unavailable = r.encode(dict(schema='openmhd.galaxy-unavailable-diagnostic.v1', unretained_bytes=0, sha256=r.sha(b'')))
        for channel, raw in (('stdout', r.encode(diagnostic) if success else unavailable),
                             ('stderr', unavailable if success else r.encode(diagnostic))):
            r.put(root, row[channel], raw)
            row[channel + '_sha256'] = r.sha(raw)
        if success:
            r.put(root, output, body)
            row['output_sha256'] = r.sha(body)
        else:
            r.put(root, output + '.partial', b'')
        r.put(root, 'transport/0000.json', r.encode(row))
        return row, helpers

    def audited(self, root, origin='synthetic-origin', **options):
        row, helpers = self.fragment(root, **options)
        return r.audit_attempt(root, 'transport/0000.json', origin, helpers, legacy=True)

    def test_authentic_shaped_nonphysical_fragment_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            item = self.audited(root)
            selected = r.choose([item], 'outputs/logs/00.log', item['identity'])
            self.assertEqual(selected['ref'], dict(origin='synthetic-origin', receipt='transport/0000.json'))
            self.assertEqual(selected['body'].read_bytes(), b'NONPHYSICAL opaque fragment\n')

    def test_missing_request_has_no_successful_selection(self):
        with self.assertRaises(r.Invalid):
            r.choose([], 'outputs/logs/00.log')

    def test_corrupted_success_body_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, helpers = self.fragment(root)
            (root / 'downloads/0000.body').write_bytes(b'CHANGED')
            with self.assertRaises(r.Invalid):
                r.audit_attempt(root, 'transport/0000.json', 'synthetic', helpers, legacy=True)

    def test_failed_partial_is_retained_but_never_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            item = self.audited(root, success=False)
            self.assertFalse(item['success'])
            self.assertTrue((root / 'downloads/0000.body.partial').is_file())
            with self.assertRaises(r.Invalid):
                r.choose([item], 'outputs/logs/00.log')

    def test_success_with_partial_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, helpers = self.fragment(root)
            r.put(root, 'downloads/0000.body.partial', b'forbidden')
            with self.assertRaises(r.Invalid):
                r.audit_attempt(root, 'transport/0000.json', 'synthetic', helpers, legacy=True)

    def test_duplicate_receipt_reference_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            item = self.audited(Path(directory))
            with self.assertRaises(r.Invalid):
                r.choose([item, item], 'outputs/logs/00.log')

    def test_identical_distinct_successes_choose_one_and_retain_both(self):
        with tempfile.TemporaryDirectory() as directory:
            a = self.audited(Path(directory) / 'a', origin='a')
            b = self.audited(Path(directory) / 'b', origin='b')
            records = [b, a]
            self.assertEqual(r.choose(records, 'outputs/logs/00.log')['ref']['origin'], 'a')
            self.assertEqual(len(records), 2)

    def test_changed_metadata_between_successes_is_not_voted_away(self):
        with tempfile.TemporaryDirectory() as directory:
            remote = 'outputs/galaxy-preflight/commands.json'
            a = self.audited(Path(directory) / 'a', origin='a', remote=remote, body=b'NONPHYSICAL first')
            b = self.audited(Path(directory) / 'b', origin='b', remote=remote, body=b'NONPHYSICAL changed')
            with self.assertRaises(r.Invalid):
                r.choose([a, b], remote)

    def test_descriptor_mismatch_is_semantic_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            item = self.audited(Path(directory))
            with self.assertRaises(r.Invalid):
                r.choose([item], 'outputs/logs/00.log', dict(bytes=1, sha256=r.sha(b'x')))

    def test_stale_UUID_success_diagnostic_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row, helpers = self.fragment(root)
            diagnostic = r.parse((root / row['stdout']).read_bytes())
            diagnostic['workflow_ids'] = ['00000000-0000-0000-0000-000000000000']
            raw = r.encode(diagnostic)
            (root / row['stdout']).write_bytes(raw)
            row['stdout_sha256'] = r.sha(raw)
            (root / 'transport/0000.json').write_bytes(r.encode(row))
            with self.assertRaises(r.Invalid):
                r.audit_attempt(root, 'transport/0000.json', 'synthetic', helpers, legacy=True)

    def test_changed_origin_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            r.put(root, 'header.json', r.encode(dict(workflow=r.WORKFLOW, uuid=r.UUID, snapshot_sha256=r.SNAPSHOT,
                component_accepted=False, status='failed')))
            with self.assertRaises(r.Invalid):
                r.check_origin_header(root, dict(source_revision='changed'), 'header.json')

    def test_retry_classification_excludes_protocol_and_hash_errors(self):
        row = dict(outcome='nonzero')
        for code in ('network_error', 'adapter_deadline', 'incomplete_body'):
            self.assertTrue(r.retryable(row, dict(code=code)))
        for code in ('http_error', 'download_workflow_changed', 'invalid_json', 'size_limit', 'descriptor_mismatch'):
            self.assertFalse(r.retryable(row, dict(code=code)))

    def test_three_attempt_bound_cannot_restart_inside_invocation(self):
        with tempfile.TemporaryDirectory() as directory:
            item = self.audited(Path(directory) / 'fixture', success=False)
            fetcher = r.Fetcher(Path(directory) / 'new', [])
            with mock.patch.object(r, 'attempt', return_value=item) as transport:
                with self.assertRaises(r.Invalid):
                    fetcher.fresh('download', 'outputs/logs/00.log', 'missing')
                self.assertEqual(transport.call_count, 3)
                with self.assertRaises(r.Invalid):
                    fetcher.fresh('download', 'outputs/logs/00.log', 'missing')
                self.assertEqual(transport.call_count, 3)

    def test_semantic_attempt_failure_is_not_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            fetcher = r.Fetcher(Path(directory), [])
            with mock.patch.object(r, 'attempt', side_effect=r.Invalid('stale_identity')) as transport:
                with self.assertRaises(r.Invalid):
                    fetcher.fresh('download', 'outputs/logs/00.log', 'missing')
                self.assertEqual(transport.call_count, 1)

    def test_unknown_lifecycle_and_unreaped_timeout_block_reuse(self):
        for row in (dict(outcome='pending_launch'), dict(outcome='unknown_lifecycle'),
                    dict(outcome='interrupted_or_start_failed'), dict(outcome='timeout', child_reaped=False)):
            with self.assertRaises(r.Invalid):
                r.retryable(row, None)

    def test_one_success_receipt_cannot_supply_two_logical_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            item = self.audited(Path(directory))
            record = dict(selected={'outputs/logs/00.log': item['ref'], 'outputs/logs/01.log': item['ref']})
            with self.assertRaises(r.Invalid):
                r.selected_values(record, [item])

    def test_ambiguous_or_nonterminal_observation_is_rejected(self):
        row = dict(id=r.UUID, name=r.WORKFLOW[:-2], status='finished', version=1, workflow=r.WORKFLOW)
        for matches in ([row, row], [dict(row, status='running')], [dict(row, version=True)]):
            raw = r.encode(dict(schema='openmhd.galaxy-server-observation.v1', origin='server',
                                observed_utc='2026-11-22T00:00:00+00:00', matches=matches))
            with self.assertRaises(r.Invalid):
                r.check_observation(raw)

    def test_linked_body_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'actual').write_bytes(b'NONPHYSICAL')
            (root / 'linked').symlink_to(root / 'actual')
            with self.assertRaises(r.Invalid):
                r.read(root, 'linked')

    def test_new_result_requires_matching_launch_and_reaping(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old, helpers = self.fragment(root)
            folder = 'attempts/000000'
            row = dict(old, schema='openmhd.galaxy-recovery-transport.v1',
                       output=folder + '/body', stdout=folder + '/stdout.json', stderr=folder + '/stderr.json',
                       phase='fixture', timeout_seconds=300, seconds=1.0, child_reaped=True, pid=123,
                       interpreter=dict(implementation='cpython', optimized=0,
                                        executable=old['argv'][0], python='SYNTHETIC unexecuted interpreter'))
            row['argv'] = [*old['argv']]
            row['argv'][2] = str(root / 'helpers' / r.HELPERS[0])
            row['argv'][row['argv'].index('--output') + 1] = str(root / row['output'])
            for channel in ('stdout', 'stderr'):
                r.put(root, row[channel], (root / old[channel]).read_bytes())
            r.put(root, row['output'], (root / old['output']).read_bytes())
            intent = dict(row, outcome='intent', pid=None, returncode=None, child_reaped=False)
            r.put(root, folder + '/intent.json', r.encode(intent))
            row['intent_sha256'] = r.sha(r.encode(intent))
            launch = dict(pid=123, argv=row['argv'], launched_utc='2026-11-22T00:00:00.5+00:00')
            r.put(root, folder + '/launch.json', r.encode(launch))
            r.put(root, folder + '/result.json', r.encode(row))
            self.assertTrue(r.audit_attempt(root, folder + '/result.json', 'synthetic', helpers)['success'])
            (root / folder / 'launch.json').write_bytes(r.encode(dict(launch, pid=124)))
            with self.assertRaises(r.Invalid):
                r.audit_attempt(root, folder + '/result.json', 'synthetic', helpers)
            (root / folder / 'launch.json').write_bytes(r.encode(launch))
            (root / folder / 'result.json').write_bytes(r.encode(dict(row, child_reaped=False)))
            with self.assertRaises(r.Invalid):
                r.audit_attempt(root, folder + '/result.json', 'synthetic', helpers)

    def test_initial_observation_retry_does_not_erase_download_fence(self):
        # Normalized NONPHYSICAL fragments exercise only interval/receipt rules;
        # this is not a complete recovery, archive, or workflow success fixture.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = dict(id=r.UUID, name=r.WORKFLOW[:-2], status='finished', version=1, workflow=r.WORKFLOW)
            raw = r.encode(dict(schema='openmhd.galaxy-server-observation.v1', origin='server',
                observed_utc='2026-11-22T00:00:01+00:00', matches=[row]))
            r.put(root, 'synthetic-observation', raw)
            def entry(number, action, phase, start, finish, remote=None, success=True):
                return dict(ref=dict(origin='self', receipt='synthetic-' + str(number)), action=action,
                    phase=phase, remote_path=remote, success=success, body=root / 'synthetic-observation',
                    identity=dict(bytes=len(raw), sha256=r.sha(raw)),
                    started_utc='2026-11-22T00:00:' + start + '+00:00',
                    finished_utc='2026-11-22T00:00:' + finish + '+00:00')
            failed = entry(0, 'observe', 'before', '00', '01', success=False)
            before = entry(1, 'observe', 'before', '01', '02')
            after = entry(2, 'observe', 'after', '05', '06')
            entries = [failed, before, after]
            record = dict(before=before['ref'], after=after['ref'], metadata_before={}, metadata_after={})
            for phase, start, finish in [('before', '02', '03'), ('after', '03', '04')]:
                for remote in r.PARENT:
                    item = entry(len(entries), 'download', 'metadata_' + phase, start, finish, remote)
                    entries.append(item)
                    record['metadata_' + phase][remote] = item['ref']
            r.check_fresh_fences(record, entries)
            entries[-1]['started_utc'] = '2026-11-22T00:00:00+00:00'
            with self.assertRaises(r.Invalid):
                r.check_fresh_fences(record, entries)
