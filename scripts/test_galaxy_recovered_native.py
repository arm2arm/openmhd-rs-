"""UNEXECUTED NONPHYSICAL metadata fragments; no complete passing parent/case.

These controls are intended as independent REANA unittest leaves only. Imports
resolve the proposed canonical layout; author inspections use ast.parse only.
"""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('recovered_native_under_test',
    ROOT / 'tools/galaxy_evidence/recovered_native.py')
n = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(n)


class RecoveredNativeMetadataTests(unittest.TestCase):
    def record(self):
        # Header fragment only: no bodies, catalog, archive, receipts or proof.
        return dict(schema='openmhd.galaxy-preflight-recovery.v1', status='complete', uuid=n.UUID,
            workflow=n.WORKFLOW, source_revision=n.REVISION, component_accepted=False, physical_accepted=False)

    def test_old_acquisition_is_not_relabelled_or_accepted(self):
        fragment = self.record()
        n.require_new_recovery(fragment)
        with self.assertRaisesRegex(ValueError, 'new_recovery_only'):
            n.require_new_recovery(dict(fragment, schema='openmhd.galaxy-preflight-acquisition.v1'))

    def test_incomplete_stale_UUID_or_compiler_generation_rejected(self):
        for change in (dict(status='incomplete'), dict(uuid='NONPHYSICAL stale UUID'),
                       dict(source_revision='0' * 40), dict(component_accepted=True)):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'new_recovery_only'):
                n.require_new_recovery(dict(self.record(), **change))

    def test_parent_must_call_actual_offline_verifier_with_full_explicit_origins(self):
        verifier = types.SimpleNamespace(verify=mock.Mock(side_effect=ValueError('incomplete_real_graph')))
        recovery, origins = Path('/NONPHYSICAL/recovery'), [Path('/NONPHYSICAL/a'), Path('/NONPHYSICAL/b')]
        with mock.patch.object(n, 'load_file', return_value=verifier) as loader:
            with self.assertRaisesRegex(ValueError, 'incomplete_real_graph'):
                n.parent_buffers(recovery, origins, Path('/NONPHYSICAL/verifier.py'), Path('/NONPHYSICAL/catalog'))
        loader.assert_called_once_with(Path('/NONPHYSICAL/verifier.py'), n.RECOVERY_SHA, 'recovered_parent_verifier')
        verifier.verify.assert_called_once_with(recovery, origins)

    def test_recovery_summary_boolean_or_missing_bodies_cannot_supply_parent(self):
        result = dict(logical_requests=866, archive_parts=395, archive_bytes=413154228,
            compiled_binaries=114, resolved_leaves=676, test_methods_executed=False)
        with self.assertRaisesRegex(ValueError, 'complete_original_recovery_result'):
            n.check_recovery_result(result, {})
        with self.assertRaisesRegex(ValueError, 'complete_original_recovery_result'):
            n.check_recovery_result(dict(result, test_methods_executed=0, logical_requests=865), {})

    def test_exact_single_fragment_profile_and_one_thread_resource_selection(self):
        # One deliberately nonphysical catalog fragment, not a full186 packet.
        leaf = dict(selector='NONPHYSICAL_fragment', build_profile='debug', binary_sha256='0' * 64)
        resources = dict(threads=1, memory='2Gi', timeout_seconds=180)
        n.single_leaf([(leaf, resources)], leaf, resources)
        for selected, wanted, request in (
            ([(leaf, resources)] * 2, leaf, resources),
            ([(leaf, resources)], dict(leaf, build_profile='release'), resources),
            ([(leaf, resources)], leaf, dict(resources, memory='1Gi')),
            ([(leaf, dict(resources, threads=True))], leaf, dict(resources, threads=True))):
            with self.subTest(wanted=wanted), self.assertRaises(ValueError):
                n.single_leaf(selected, wanted, request)

    def test_control_count_flags_are_not_actual_whole_output_verification(self):
        # This helper checks only a derived count fragment. prepare must call
        # the unchanged whole-packet verifier before this helper; see causal test.
        snapshot = dict(tests=['NONPHYSICAL control'])
        summary = dict(whole_suite_passed=True, counts=dict(passed=1, failed=0, pending=0, incomplete=0))
        n.require_control_success(summary, snapshot)
        for change in (dict(whole_suite_passed=1), dict(whole_suite_passed=False),
                       dict(counts=dict(passed=1, failed=0, pending=0, incomplete=1)),
                       dict(counts=dict(passed=1, failed=False, pending=0, incomplete=0))):
            with self.subTest(change=change), self.assertRaises(ValueError):
                n.require_control_success(dict(summary, **change), snapshot)

    def test_prepare_requires_actual_control_packet_verification_before_cases(self):
        # Deliberately incomplete NONPHYSICAL pre-parent fragments. This causal
        # control reaches the verifier call and stops there; it makes no passing
        # context, certificate, full recovery, catalog or native workflow.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            context, proof = root / 'context', root / 'proof'
            context.mkdir()
            n.put(context, 'fragment', b'NONPHYSICAL parent fragment\n')
            n.put(context, 'files.sha256.json', n.encode(n.inventory(context)))
            snapshot = dict(source_sha256={'tools/galaxy_python_evidence/' + name: '0' * 64
                                          for name in n.PROOF_TOOLS})
            raw = n.encode(snapshot)
            n.put(proof, 'shared/snapshot.json', raw)
            release = n.encode(dict(control_snapshot_sha256=n.sha(raw), control_job_sha256='0' * 64))
            n.put(root, 'release.json', release)
            collector = types.SimpleNamespace(verify_packet=mock.Mock(side_effect=ValueError('actual_control_packet_incomplete')))
            fresh = {'fragment': b'NONPHYSICAL parent fragment\n'}
            with mock.patch.object(n, 'parent_buffers', return_value=fresh), mock.patch.object(n, 'bundle',
                    return_value=(None, None, collector)):
                with self.assertRaisesRegex(ValueError, 'actual_control_packet_incomplete'):
                    n.prepare(context, root / 'recovery', [root / 'origin'], root / 'verifier.py', root / 'catalog',
                        root / 'tools', proof, root / 'release.json', n.sha(release), root / 'review.md',
                        root / 'cases', 'nonphysical')
            collector.verify_packet.assert_called_once_with(proof)
            self.assertFalse((root / 'cases').exists())

    def test_old_payload_schema_rejected_before_any_import_or_launch(self):
        raw = n.encode(dict(schema='openmhd.galaxy-native-test-inputs.v1', input_sha256={}, binary_parts=[]))
        with mock.patch.object(n, 'load_file') as loader, mock.patch.object(n, 'original_modules') as original:
            with self.assertRaisesRegex(ValueError, 'explicit_new_input_schema'):
                n.check_case_inputs(Path('/NONPHYSICAL'), {}, raw)
        loader.assert_not_called()
        original.assert_not_called()

    def test_root_release_needs_external_exact_pin_before_proof_import(self):
        buffers = {'proof/root-release.json': b'NONPHYSICAL unapproved release\n'}
        with mock.patch.object(n, 'load_file') as loader:
            with self.assertRaisesRegex(ValueError, 'explicit_root_release_pin'):
                n.release_proof(buffers, '0' * 64, b'NONPHYSICAL manifest', b'NONPHYSICAL source')
        loader.assert_not_called()

    def proof_fragment(self):
        # Source-membership fragment only. It has no raw original snapshot,
        # certificate, 318-row output, source archive or passing release proof.
        source = b'NONPHYSICAL later Python source\n'
        control = dict(source_sha256={n.JOB_SOURCE: n.sha(source), n.RECOVERY_SOURCE: n.RECOVERY_SHA,
            n.RECOVERY_TEST: n.RECOVERY_TEST_SHA,
            'tools/galaxy_python_evidence/reana_metadata_job.py': n.sha(b'NONPHYSICAL later job')},
            job_sha256=n.sha(b'NONPHYSICAL later job'),
            test_files=[n.TEST_SOURCE, 'scripts/test_galaxy_driver_build_acquisition.py'])
        original = dict(source_revision=n.ORIGINAL318_REVISION, job_sha256=n.ORIGINAL318_JOB,
            source_sha256={n.RECOVERY_SOURCE: n.RECOVERY_SHA, n.RECOVERY_TEST: n.RECOVERY_TEST_SHA,
                          'tools/galaxy_python_evidence/reana_metadata_job.py': n.ORIGINAL318_JOB},
            test_files=[n.RECOVERY_TEST])
        return control, original, source

    def test_later_python_code_has_own_proof_pin_and_cannot_borrow_Rust_snapshot(self):
        control, original, source = self.proof_fragment()
        self.assertNotIn(n.RECOVERY_TEST, control['test_files'])
        n.generation_proof(control, source, original)
        for changed in ({}, dict(original, source_revision=n.REVISION),
                        dict(original, source_sha256={}), dict(original, test_files=[])):
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, 'original318_source_proof_required'):
                n.generation_proof(control, source, changed)
        for name in (n.RECOVERY_SOURCE, n.RECOVERY_TEST):
            changed = dict(original, source_sha256=dict(original['source_sha256'], **{name: '0' * 64}))
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'original318_source_proof_required'):
                n.generation_proof(control, source, changed)
        with self.assertRaisesRegex(ValueError, 'later_orchestration_source_import_pins'):
            n.generation_proof(control, b'NONPHYSICAL changed code', original)
        changed = dict(control, source_sha256=dict(control['source_sha256']))
        del changed['source_sha256'][n.JOB_SOURCE]
        changed['source_sha256']['reana/galaxy_test_case.py'] = n.sha(source)
        with self.assertRaisesRegex(ValueError, 'later_orchestration_source_import_pins'):
            n.generation_proof(changed, source, original)
        # Hash-link-only old-proof fragment, not a valid pinned old generation.
        names = dict(snapshot='snapshot.json', certificate='certificate.json', job='job.py',
            results_manifest='control-manifest.json', results_summary='control-summary.json',
            root_output_review='root-output-review.md')
        buffers = {'proof/original318/' + name: ('NONPHYSICAL ' + name).encode() for name in names.values()}
        release = {'original318_' + field + '_sha256': n.sha(buffers['proof/original318/' + name])
                   for field, name in names.items()}
        n.original_proof_hashes(buffers, release)
        for name in ('control-manifest.json', 'root-output-review.md'):
            path = 'proof/original318/' + name
            changed = dict(buffers, **{path: b'NONPHYSICAL changed'})
            missing = dict(buffers)
            del missing[path]
            for invalid in (changed, missing):
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'root_release_original318_proof_hash'):
                    n.original_proof_hashes(invalid, release)
        # The real original CLI handoff is asserted outside the caught call.
        sentinel = ValueError('NONPHYSICAL strict original verifier sentinel')
        tools, packet = Path('/NONPHYSICAL/original-tools'), Path('/NONPHYSICAL/original-packet')
        with mock.patch.object(n.subprocess, 'run', side_effect=sentinel) as actual:
            with self.assertRaisesRegex(ValueError, 'strict original verifier sentinel') as caught:
                n.verify_original_packet(tools, packet)
        self.assertIs(caught.exception, sentinel)
        actual.assert_called_once_with([sys.executable, '-B', str(tools / 'prepare_metadata_reana.py'),
            'verify-results', '--packet', str(packet)], cwd=tools, check=True, timeout=300)
        # Missing old proof rejects the actual prepare path before case creation;
        # even the later one-row count fragment cannot substitute for that proof.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            context, proof = root / 'context', root / 'proof'
            context.mkdir()
            n.put(context, 'fragment', b'NONPHYSICAL parent fragment\n')
            n.put(context, 'files.sha256.json', n.encode(n.inventory(context)))
            snapshot = dict(source_sha256={'tools/galaxy_python_evidence/' + name: '0' * 64
                                          for name in n.PROOF_TOOLS}, tests=['NONPHYSICAL count fragment'])
            raw = n.encode(snapshot)
            n.put(proof, 'shared/snapshot.json', raw)
            auth = n.encode(dict(control_snapshot_sha256=n.sha(raw), control_job_sha256='0' * 64))
            n.put(root, 'release.json', auth)
            summary = dict(whole_suite_passed=True, counts=dict(passed=1, failed=0, pending=0, incomplete=0))
            collector = types.SimpleNamespace(verify_packet=mock.Mock(return_value=summary))
            with mock.patch.object(n, 'parent_buffers', return_value={'fragment': b'NONPHYSICAL parent fragment\n'}), \
                    mock.patch.object(n, 'bundle', return_value=(None, None, collector)):
                with self.assertRaisesRegex(ValueError, 'separate_original318_proof_required'):
                    n.prepare(context, root / 'recovery', [root / 'origin'], root / 'verifier.py', root / 'catalog',
                        root / 'tools', proof, root / 'release.json', n.sha(auth), root / 'review.md',
                        root / 'cases', 'nonphysical')
            collector.verify_packet.assert_called_once_with(proof)
            self.assertFalse((root / 'cases').exists())

            # The old fragments are intentionally invalid at the later fixed
            # generation guard. Here changed closure/review must hit their
            # earlier exact hash guard on the real prepare path, never mkdir.
            old_packet, old_review = root / 'old-packet', root / 'old-review.md'
            original_names = {'snapshot.json': 'shared/snapshot.json', 'job.py': 'shared/job.py',
                'certificate.json': 'shared/preflight_certificate.json', 'control-summary.json': 'summary.json',
                'control-manifest.json': 'files.sha256.json'}
            for name, target in original_names.items():
                n.put(old_packet, target, buffers['proof/original318/' + name])
            n.put(root, old_review.name, buffers['proof/original318/root-output-review.md'])
            auth = n.encode(dict(schema='openmhd.recovered-native-root-release.v2',
                control_snapshot_sha256=n.sha(raw), control_job_sha256='0' * 64, **release))
            (root / 'release.json').write_bytes(auth)
            for target in (old_packet / 'files.sha256.json', old_review):
                original_raw = target.read_bytes()
                target.write_bytes(b'NONPHYSICAL changed old closure or review')
                collector.verify_packet.reset_mock()
                with mock.patch.object(n, 'parent_buffers', return_value={'fragment': b'NONPHYSICAL parent fragment\n'}), \
                        mock.patch.object(n, 'bundle', return_value=(None, None, collector)), \
                        mock.patch.object(n, 'verify_original_packet') as old_verifier:
                    with self.assertRaisesRegex(ValueError, 'root_release_original318_proof_hash'):
                        n.prepare(context, root / 'recovery', [root / 'origin'], root / 'verifier.py', root / 'catalog',
                            root / 'tools', proof, root / 'release.json', n.sha(auth), root / 'review.md',
                            root / 'cases', 'nonphysical', original_proof_tools=root / 'old-tools',
                            original_proof_packet=old_packet, original_review_path=old_review)
                collector.verify_packet.assert_called_once_with(proof)
                old_verifier.assert_not_called()
                self.assertFalse((root / 'cases').exists())
                target.write_bytes(original_raw)

    def test_missing_consumer_control_suite_is_not_an_import_release(self):
        control, original, source = self.proof_fragment()
        control['test_files'] = [n.RECOVERY_TEST]
        with self.assertRaisesRegex(ValueError, 'later_orchestration_source_import_pins'):
            n.generation_proof(control, source, original)

    def test_unittest_failed_and_generic_zero_labels_are_not_native_outputs(self):
        for result in (dict(schema='openmhd.galaxy-python-regression-result.v2', status='passed'),
                       dict(schema='openmhd.galaxy-native-test-result.v1', input_route='recovered-native-v1',
                            status='failed', component_accepted=False), dict(returncode=0, passed=True)):
            values = {name: b'' for name in n.OUTPUT_NAMES}
            values['result.json'] = n.encode(result)
            with self.subTest(result=result), self.assertRaisesRegex(ValueError, 'actual_recovered_native_result_header'):
                n.output_header(values)
        with self.assertRaisesRegex(ValueError, 'eight_actual_native_outputs'):
            n.output_header({'result.json': b'{}'})

    def test_unchanged_strict_native_validator_failure_is_propagated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent, report = b'NONPHYSICAL parent\n', b'{}\n'
            n.put(root, 'parent.json', parent)
            n.put(root, 'preflight/preflight.json', report)
            n.put(root, 'payload.json', n.encode(dict(input_sha256={'parent.json': n.sha(parent),
                'preflight/preflight.json': n.sha(report)})))
            result = dict(schema='openmhd.galaxy-native-test-result.v1', input_route='recovered-native-v1',
                status='passed', component_accepted=False, parent_context_sha256=n.sha(parent), root_release_sha256='0' * 64)
            values = {name: b'' for name in n.OUTPUT_NAMES}
            values['result.json'] = n.encode(result)
            strict = mock.Mock(side_effect=ValueError('actual_writer_closure_required'))
            pipeline = types.SimpleNamespace(validate_native=strict)
            with mock.patch.object(n, 'check_case_inputs', return_value=(dict(root_release_sha256='0' * 64), {}, None, pipeline)):
                with self.assertRaisesRegex(ValueError, 'actual_writer_closure_required'):
                    n.validate_outputs(values, root)
            strict.assert_called_once_with(values, root, {})

    def test_conflicting_module_cache_is_rejected_without_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = b'NONPHYSICAL never imported bytes\n'
            n.put(root, 'consumer_fixture_only.py', raw)
            prior = types.SimpleNamespace(__file__='/NONPHYSICAL/another/consumer_fixture_only.py')
            with mock.patch.dict(sys.modules, {'consumer_fixture_only': prior}):
                with self.assertRaisesRegex(ValueError, 'conflicting_import_cache'):
                    n.bundle(root, ('consumer_fixture_only',), {'consumer_fixture_only.py': n.sha(raw)})
                self.assertIs(sys.modules['consumer_fixture_only'], prior)

    def test_one_case_spec_has_no_build_list_or_aggregate_test_action(self):
        value = n.specification(['case.py', 'payload.json'], dict(threads=1, memory='1Gi', timeout_seconds=180),
                                'NONPHYSICAL image label', n.OUTPUT_NAMES)
        steps = value['workflow']['specification']['steps']
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]['commands'], ['python3 -B case.py run'])
        self.assertEqual((steps[0]['kubernetes_cpu_request'], steps[0]['kubernetes_cpu_limit'],
                          steps[0]['kubernetes_memory_limit']), ('1', '1', '1Gi'))
        self.assertEqual(value['outputs']['files'], ['outputs/' + name for name in n.OUTPUT_NAMES])

    def test_linked_or_changed_context_bytes_cannot_be_read_as_frozen_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            n.put(root, 'body', b'NONPHYSICAL\n')
            (root / 'alias').symlink_to(root / 'body')
            with self.assertRaisesRegex(ValueError, 'linked_path'):
                n.read(root, 'alias')
            (root / 'alias').unlink()
            n.put(root, 'files.sha256.json', n.encode(n.inventory(root)))
            (root / 'body').write_bytes(b'NONPHYSICAL changed\n')
            with self.assertRaises(ValueError):
                n.closed(root)


class RecoveredNativePythonProofTests(unittest.TestCase):
    """UNEXECUTED isolated new-proof controls, never complete native evidence."""

    def descriptor(self):
        item = dict(schema='openmhd.python-complete-case-proof.v1', provider_sha256='a' * 64,
                    release_sha256='b' * 64)
        return dict(schema='openmhd.recovered-native-root-release.v3',
                    python_evidence=dict(original318=dict(item), later_selected=dict(item)))

    def proof_fragment(self, root):
        # Incomplete file fragments solely to reach the external verifier call.
        provider, packet, review = root / 'provider.py', root / 'packet', root / 'review.md'
        raw = b'# NONPHYSICAL inert provider fragment, never executed\n'
        n.put(root, provider.name, raw)
        n.put(root, review.name, b'NONPHYSICAL not output approval\n')
        for name in ('context/shared/snapshot.json', 'context/shared/job.py',
                     'context/shared/preflight_certificate.json', 'summary.json', 'files.sha256.json', 'release.json'):
            n.put(packet, name, b'NONPHYSICAL not a complete proof\n')
        release = self.descriptor()
        for item in release['python_evidence'].values():
            item.update(provider_sha256=n.sha(raw), release_sha256=n.sha(n.read(packet, 'release.json')))
        evidence = dict(provider=provider, original318_origins=[root / 'a'], later_selected_origins=[root / 'b'])
        return packet, review, release, evidence

    def test_new_proof_requires_both_exact_descriptors_and_one_provider(self):
        value = self.descriptor()
        self.assertEqual(set(n.python_evidence_release(value)), {'original318', 'later_selected'})
        value['python_evidence']['original318']['provider_sha256'] = 'c' * 64
        with self.assertRaisesRegex(ValueError, '^one_shared_python_evidence_provider$'):
            n.python_evidence_release(value)
        value = self.descriptor()
        del value['python_evidence']['original318']
        with self.assertRaisesRegex(ValueError, '^exact_schema_keys$'):
            n.python_evidence_release(value)

    def test_new_proof_paths_are_explicit_external_relocation_arguments(self):
        value = dict(provider='/NONPHYSICAL/provider.py', original318_origins=['/NONPHYSICAL/a'],
                     later_selected_origins=['/NONPHYSICAL/b'])
        parsed = n.python_evidence_arguments(value)
        self.assertEqual(parsed['original318_origins'], [Path('/NONPHYSICAL/a')])
        for change in (dict(provider='relative.py'), dict(original318_origins=[]),
                       dict(later_selected_origins=['/NONPHYSICAL/b'] * 2)):
            with self.subTest(change=change), self.assertRaises(ValueError):
                n.python_evidence_arguments(dict(value, **change))

    def test_legacy_compact_branch_cannot_admit_new_summary_or_nonpassing_old_output(self):
        snapshot = dict(tests=['NONPHYSICAL'])
        buffers = {'proof/snapshot.json': n.encode(snapshot), 'proof/certificate.json': b'NONPHYSICAL'}
        summary = dict(schema='openmhd.python-complete-case-results.v1', whole_suite_passed=False,
            snapshot_sha256=n.sha(buffers['proof/snapshot.json']),
            preflight_certificate_sha256=n.sha(buffers['proof/certificate.json']),
            catalog=dict(selectors=snapshot['tests']), counts=dict(passed=1, failed=0, pending=0, incomplete=0))
        buffers['proof/control-summary.json'] = n.encode(summary)
        with self.assertRaisesRegex(ValueError, '^actual_whole_control_results_required$'):
            n.compact_control_proof(buffers, 'proof/', snapshot)

    def test_new_compact_branch_calls_only_explicit_pinned_provider_and_propagates_sentinel(self):
        release = self.descriptor()
        prefix = 'proof/original318/'
        buffers = {prefix + k: b'{}' for k in ('control-summary.json', 'snapshot.json', 'certificate.json',
                    'control-manifest.json', 'python-evidence-release.json')}
        seen = []
        sentinel = RuntimeError('NONPHYSICAL compact rejection sentinel')
        def compact(*args):
            seen.append(args)
            raise sentinel
        provider = types.SimpleNamespace(compact=compact)
        with mock.patch.object(n, 'load_file', return_value=provider) as loaded:
            with self.assertRaises(RuntimeError) as caught:
                n.compact_control_proof(buffers, prefix, {}, release=release, root=Path('/NONPHYSICAL/root'))
        self.assertIs(caught.exception, sentinel)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][-1], 'b' * 64)
        loaded.assert_called_once_with(Path('/NONPHYSICAL/root/proof/python_case_recovery.py'), 'a' * 64,
                                       'compact_python_evidence_provider')

    def test_provider_source_authentication_precedes_external_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet, review, release, evidence = self.proof_fragment(root)
            # Both proof descriptors must agree to reach the source-authentication guard.
            for item in release['python_evidence'].values():
                item['provider_sha256'] = '0' * 64
            with mock.patch.object(n.subprocess, 'run') as run:
                with self.assertRaisesRegex(ValueError, '^python_provider_before_execution$'):
                    n.complete_python_proof(packet, packet / 'tools', review, release, 'later_selected', evidence)
            run.assert_not_called()

    def test_recovery_release_bytes_must_match_root_before_external_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet, review, release, evidence = self.proof_fragment(root)
            release['python_evidence']['later_selected']['release_sha256'] = '0' * 64
            with mock.patch.object(n.subprocess, 'run') as run:
                with self.assertRaisesRegex(ValueError, '^root_pinned_python_recovery_release$'):
                    n.complete_python_proof(packet, packet / 'tools', review, release, 'later_selected', evidence)
            run.assert_not_called()

    def test_full_verifier_uses_fresh_process_all_origins_and_no_retry_after_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet, review, release, evidence = self.proof_fragment(root)
            calls = []
            sentinel = RuntimeError('NONPHYSICAL full verifier failure sentinel')
            def stop(*args, **kwargs):
                calls.append((args, kwargs))
                raise sentinel
            with mock.patch.object(n.subprocess, 'run', side_effect=stop):
                with self.assertRaises(RuntimeError) as caught:
                    n.complete_python_proof(packet, packet / 'tools', review, release, 'later_selected', evidence)
            self.assertIs(caught.exception, sentinel)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][0][0], [sys.executable, '-B', str(evidence['provider']), 'verify',
                '--packet', str(packet), '--release-sha256', release['python_evidence']['later_selected']['release_sha256'],
                '--origin', str(root / 'b')])
            self.assertEqual(calls[0][1], dict(check=True, timeout=300))

    def test_original318_fixed_generation_cannot_be_replaced_by_recovered_later_proof(self):
        release = self.descriptor()
        buffers = {'proof/original318/' + key: b'NONPHYSICAL later generation' for key in
            ('snapshot.json', 'job.py', 'certificate.json', 'control-manifest.json', 'control-summary.json', 'root-output-review.md')}
        for field, key in (('snapshot', 'snapshot.json'), ('job', 'job.py'), ('certificate', 'certificate.json'),
                ('results_manifest', 'control-manifest.json'), ('results_summary', 'control-summary.json'),
                ('root_output_review', 'root-output-review.md')):
            release['original318_' + field + '_sha256'] = n.sha(buffers['proof/original318/' + key])
        with mock.patch.object(n, 'complete_python_proof', return_value=buffers) as checked:
            with self.assertRaisesRegex(ValueError, '^exact_original318_generation$'):
                n.original_control_proof(Path('/NONPHYSICAL/tools'), Path('/NONPHYSICAL/packet'),
                    Path('/NONPHYSICAL/review'), release, python_evidence={})
        self.assertEqual(checked.call_count, 1)

    def test_prepare_authenticates_outer_release_before_any_supplied_verifier(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            n.put(root, 'release.json', b'NONPHYSICAL not authenticated')
            with mock.patch.object(n, 'parent_buffers') as parent:
                with self.assertRaisesRegex(ValueError, '^explicit_root_release_before_import$'):
                    n.prepare(root / 'context', root / 'recovery', [root / 'origin'], root / 'verifier.py',
                        root / 'catalog', root / 'tools', root / 'packet', root / 'release.json', '0' * 64,
                        root / 'review', root / 'out', 'nonphysical')
            parent.assert_not_called()

    def test_dependency_anchors_retain_two_whole_proof_scopes_and_explicit_new_schema(self):
        release = self.descriptor()
        for prefix in ('original318_', 'control_'):
            for field in ('snapshot', 'job', 'certificate', 'results_manifest', 'results_summary', 'root_output_review'):
                key = 'root_output_review' if prefix == 'control_' and field == 'root_output_review' else prefix + field
                release[key + '_sha256'] = 'f' * 64
        anchors = n.proof_dependencies(release)
        self.assertEqual(set(anchors), {'original318', 'later_selected'})
        self.assertEqual(anchors['original318']['python_evidence'], release['python_evidence']['original318'])
        self.assertEqual(anchors['later_selected']['python_evidence'], release['python_evidence']['later_selected'])
        release['schema'] = 'openmhd.recovered-native-root-release.v2'
        self.assertTrue(all('python_evidence' not in item for item in n.proof_dependencies(release).values()))
