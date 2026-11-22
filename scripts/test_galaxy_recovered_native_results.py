"""Unexecuted NONPHYSICAL metadata fragments; no complete parent/native campaign.

Each direct method needs its own future REANA workflow. Import has no target
side effects; setUp loads only this stdlib-only results module on REANA.
"""
from datetime import datetime
import importlib
import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_results():
    path = ROOT / 'tools/galaxy_evidence/recovered_native_results.py'
    spec = importlib.util.spec_from_file_location('nonphysical_recovered_results_controls', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fragment_row():
    return dict(directory='case_0000', workflow='nonphysical-control-0000.1',
        specification='case_0000/reana.yaml', leaf=dict(build_profile='debug', selector='NONPHYSICAL'),
        resources=dict(threads=1, memory='2Gi', timeout_seconds=180),
        payload_sha256='a' * 64, workflow_sha256='b' * 64)


def fragment_plan():
    return dict(schema='openmhd.recovered-native-case-plan.v1', component_accepted=False,
        physical_accepted=False, compiled_snapshot_sha256='a' * 64,
        later_python_snapshot_sha256='b' * 64, recovery_manifest_sha256='c' * 64,
        origin_manifest_sha256=['d' * 64], root_release_sha256='e' * 64,
        context_sha256={}, retained_dependencies={}, cases=[fragment_row()])


class RecoveredNativeResultsTests(unittest.TestCase):
    def setUp(self):
        self.m = load_results()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def closed_fragment(self, root, values):
        root.mkdir(parents=True)
        for name, raw in values.items():
            self.m.put(root, name, raw)
        self.m.put(root, 'files.sha256.json', self.m.encode(self.m.inventory(root)))

    def common_fragment(self):
        m = self.m
        return SimpleNamespace(
            verify_closed=lambda root: m.sealed_tree(root),
            close=lambda root: m.put(root, 'files.sha256.json', m.encode(m.inventory(root))),
            supervisor=SimpleNamespace(utc=lambda s: datetime.fromisoformat(s)),
            observation=lambda raw, workflow, identifier, finished: m.parse(raw)['matches'][0],
            transport_body=lambda root, label, *args: m.read(root, m.parse(m.read(root, label))['output']),
            transport_closure=lambda root, labels: None)

    def server(self, status='finished'):
        row = fragment_row()
        return self.m.encode(dict(schema='openmhd.galaxy-server-observation.v1', origin='server',
            observed_utc='2026-11-22T00:00:01+00:00', matches=[dict(workflow=row['workflow'],
            name=row['workflow'][:-2], version=1, id='00000000-0000-4000-8000-000000000001', status=status)]))

    def capsule_fragment(self):
        """Authentic-shaped transport fragment, INTENTIONALLY invalid native bodies.

        Patches below isolate caller checks. The strict native handoff always
        raises; no passing native/certificate/preflight packet is manufactured.
        """
        m, root, expected = self.m, self.root / 'capsule', fragment_row()
        root.mkdir()
        record = m.empty_capture(expected)
        record.update(status='passed', observed_status='finished', uuid='00000000-0000-4000-8000-000000000001',
                      failure_kind='none')
        runtime = dict(executable='/NONPHYSICAL/python')
        for index in range(10):
            action = 'observe' if index in (0, 9) else 'download'
            name = None if action == 'observe' else m.OUTPUTS[index - 1]
            label, output = 'transport/' + str(index).zfill(4) + '.json', 'downloads/' + str(index) + '.body'
            raw = self.server() if action == 'observe' else (b'{}\n' if name.endswith('.json') else b'NONPHYSICAL\n')
            if index == 0:
                start, end = '2026-11-22T00:00:00+00:00', '2026-11-22T00:00:02+00:00'
            elif index == 9:
                start, end = '2026-11-22T00:00:10+00:00', '2026-11-22T00:00:12+00:00'
                value = m.parse(raw)
                value['observed_utc'] = '2026-11-22T00:00:11+00:00'
                raw = m.encode(value)
            else:
                start, end = '2026-11-22T00:00:03+00:00', '2026-11-22T00:00:09+00:00'
            diagnostic = dict(schema='openmhd.galaxy-get-diagnostic.v1', outcome='success', code='completed',
                started_utc=start, finished_utc=end, action=action, workflow=expected['workflow'],
                requested_path=None if name is None else 'outputs/' + name, workflow_ids=[record['uuid']],
                http_status=200, received_bytes=len(raw), retained_bytes=len(raw), partial_file=None, page_count=1)
            stdout, stderr = 'transport/' + str(index) + '.stdout', 'transport/' + str(index) + '.stderr'
            m.put(root, stdout, m.encode(diagnostic))
            m.put(root, stderr, m.encode(dict(schema='openmhd.galaxy-unavailable-diagnostic.v1',
                unretained_bytes=0, sha256=m.sha(b''))))
            m.put(root, output, raw)
            receipt = dict(schema='openmhd.galaxy-transport-attempt.v1', action=action,
                workflow=expected['workflow'], remote_path=diagnostic['requested_path'], output=output,
                argv=[runtime['executable'], '-B', '/NONPHYSICAL/tools/galaxy_evidence/readonly_adapter.py'],
                cwd='/NONPHYSICAL/original-cwd', adapter_sha256='a' * 64, base_adapter_sha256='b' * 64,
                started_utc=start, finished_utc=end, outcome='success', returncode=0,
                stdout=stdout, stderr=stderr, stdout_sha256=m.sha(m.read(root, stdout)),
                stderr_sha256=m.sha(m.read(root, stderr)), output_sha256=m.sha(raw))
            m.put(root, label, m.encode(receipt))
            if index == 0:
                record['before'] = label
            elif index == 9:
                record['after'] = label
            else:
                record['files'][name] = label
        m.put(root, 'capture.json', m.encode(record))
        self.common_fragment().close(root)
        return root, expected, runtime

    def mutate_capsule(self, root, name, change):
        value = self.m.parse(self.m.read(root, name))
        change(value)
        (root / name).write_bytes(self.m.encode(value))
        (root / 'files.sha256.json').unlink()
        self.common_fragment().close(root)

    def test_duplicate_keys_and_exponent_overflow_reject(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":1e400}', b'{"x":NaN}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.m.parse(raw)
        self.assertFalse(self.m.same(True, 1))

    def test_exact_submission_status_preserves_uncertainty(self):
        plan = fragment_plan()
        for status in ('submitted', 'submission uncertain'):
            row = dict(status=status)
            if status == 'submission uncertain':
                row['error'] = 'NONPHYSICAL retained uncertainty'
            raw = self.m.encode({plan['cases'][0]['workflow']: row})
            self.assertEqual(self.m.submission_map(raw, plan)[plan['cases'][0]['workflow']], row)
        for status in ('submission_uncertain', 'submission pending', 'pending'):
            with self.subTest(status=status), self.assertRaisesRegex(ValueError, 'settled_original'):
                self.m.submission_map(self.m.encode({plan['cases'][0]['workflow']: dict(status=status)}), plan)

    def test_missing_extra_and_duplicate_catalog_rows_reject(self):
        m = self.m
        for mutate in (lambda p: p['cases'].clear(), lambda p: p['cases'].append(dict(p['cases'][0])),
                       lambda p: p.update(extra=True), lambda p: p['cases'][0]['resources'].update(threads=True)):
            value = fragment_plan()
            mutate(value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.plan_shape(value)

    def test_wrong_schema_and_profile_reject(self):
        self.m.plan_shape(fragment_plan())  # grammar-only NONPHYSICAL positive
        for mutate in (lambda p: p.update(schema='openmhd.galaxy-native-case-plan.v1'),
                       lambda p: p['cases'][0]['leaf'].update(build_profile='bench')):
            value = fragment_plan()
            mutate(value)
            with self.assertRaises(ValueError):
                self.m.plan_shape(value)

    def test_regular_copy_keeps_every_original_path_and_seal(self):
        source, target = self.root / 'source', self.root / 'target'
        self.closed_fragment(source, {'plan.json': b'{"NONPHYSICAL":true}\n', 'case_0000/test-binary.part000': b'opaque-not-executable'})
        expected, generations, mapping = self.m.copy_inputs(source, target)
        self.assertEqual(set(expected), {'plan.json', 'case_0000/test-binary.part000', 'files.sha256.json'})
        self.assertEqual(mapping['files.sha256.json']['retained'], 'inputs/files.sha256.json')
        self.assertEqual(self.m.inventory(source), self.m.inventory(target))
        self.m.fence_inputs(source, expected, generations)

    def test_copy_rejects_link_and_invalid_json_without_dependent_validation(self):
        source = self.root / 'source'
        self.closed_fragment(source, {'plan.json': b'{"x":1e400}\n'})
        with self.assertRaisesRegex(ValueError, 'nonfinite'):
            self.m.copy_inputs(source, self.root / 'copy')
        (source / 'linked').symlink_to(source / 'plan.json')
        with self.assertRaisesRegex(ValueError, 'linked'):
            self.m.inventory(source)

    def test_final_original_input_fence_detects_late_replacement(self):
        source = self.root / 'source'
        self.closed_fragment(source, {'plan.json': b'{"NONPHYSICAL":1}\n'})
        expected, versions, _ = self.m.copy_inputs(source, self.root / 'copy')
        replacement = source / 'new'
        replacement.write_bytes((source / 'plan.json').read_bytes())
        replacement.replace(source / 'plan.json')
        with self.assertRaisesRegex(ValueError, 'generation'):
            self.m.fence_inputs(source, expected, versions)

    def test_real_full_plan_verifier_called_on_captured_context_only(self):
        calls = []
        n = SimpleNamespace(check_plan=lambda *a: calls.append(a) or (_ for _ in ()).throw(ValueError('full-plan-sentinel')))
        deps = dict(recovery=self.root / 'recovery', origins=[self.root / 'origin'], verifier=self.root / 'verifier', catalog=self.root / 'catalog')
        captured = self.root / 'relocated-inputs'
        with self.assertRaisesRegex(ValueError, 'full-plan-sentinel'):
            self.m.dependency_check(n, captured, deps)
        self.assertEqual(calls, [(captured, deps['recovery'], deps['origins'], deps['verifier'], deps['catalog'])])

    def test_full_later_and_original_output_verifiers_cannot_be_skipped(self):
        m, inputs, packet = self.m, self.root / 'captured', self.root / 'proof-packet'
        proof_tools = ('reana_metadata_job.py', 'prepare_metadata_reana.py',
                       'reana_metadata_readonly_adapter.py', 'collect_metadata_reana_results.py')
        source_map = {'tools/galaxy_python_evidence/' + name: 'a' * 64 for name in proof_tools}
        source_map.update({m.SOURCE: m.sha(Path(m.__file__).read_bytes()), m.TEST_SOURCE: 'b' * 64})
        control = dict(source_sha256=source_map, test_files=[m.TEST_SOURCE], tests=['NONPHYSICAL'])
        summary = dict(whole_suite_passed=True, counts=dict(passed=1, failed=0, pending=0, incomplete=0))
        proof = {'snapshot.json': m.encode(control), 'certificate.json': b'NONPHYSICAL no certificate\n',
                 'control-manifest.json': b'{"NONPHYSICAL":true}\n', 'control-summary.json': m.encode(summary)}
        release_raw = b'{"NONPHYSICAL":true}\n'
        context = {'proof/' + name: body for name, body in proof.items()}
        context.update({'proof/root-release.json': release_raw, 'proof/root-output-review.md': b'NONPHYSICAL not reviewed\n'})
        for name, body in context.items():
            m.put(inputs / 'context', name, body)
        for source, name in (('shared/snapshot.json', 'snapshot.json'),
                            ('shared/preflight_certificate.json', 'certificate.json'),
                            ('files.sha256.json', 'control-manifest.json'), ('summary.json', 'control-summary.json')):
            m.put(packet, source, proof[name])
        review = self.root / 'review.md'
        review.write_bytes(context['proof/root-output-review.md'])
        plan = fragment_plan()
        plan.update(root_release_sha256=m.sha(release_raw), context_sha256={n: m.sha(b) for n, b in context.items()})
        calls = []
        def later(_):
            calls.append('actual later verify_packet API')
            raise ValueError('later-full-verifier-sentinel')
        n = SimpleNamespace(check_plan=lambda *a: plan, PROOF_TOOLS=proof_tools,
            bundle=lambda *a: (None, None, SimpleNamespace(verify_packet=later)),
            original_control_proof=lambda *a: calls.append('actual original_control_proof API') or
                (_ for _ in ()).throw(ValueError('original-full-verifier-sentinel')),
            require_control_success=lambda *a: None)
        deps = dict(recovery=self.root / 'r', origins=[self.root / 'o'], verifier=self.root / 'v',
            catalog=self.root / 'c', release_sha256=m.sha(release_raw), proof_tools=self.root / 'tools',
            proof_packet=packet, review=review, original_proof_tools=self.root / 'old-tools',
            original_proof_packet=self.root / 'old-packet', original_review=self.root / 'old-review')
        with self.assertRaisesRegex(ValueError, 'later-full-verifier-sentinel'):
            m.dependency_check(n, inputs, deps)
        self.assertEqual(calls, ['actual later verify_packet API'])
        n.bundle = lambda *a: (None, None, SimpleNamespace(verify_packet=lambda p: summary))
        calls.clear()
        with self.assertRaisesRegex(ValueError, 'original-full-verifier-sentinel'):
            m.dependency_check(n, inputs, deps)
        self.assertEqual(calls, ['actual original_control_proof API'])

    def test_strict_native_handoff_uses_shared_context_and_all_eight_bodies(self):
        root, expected, runtime = self.capsule_fragment()
        calls = []
        n = SimpleNamespace(validate_outputs=lambda *a, **kw: calls.append((a, kw)) or
                            (_ for _ in ()).throw(ValueError('strict-native-sentinel')))
        context = self.root / 'one-shared-context'
        with self.assertRaisesRegex(ValueError, 'strict-native-sentinel'):
            self.m.verify_capture(n, self.common_fragment(), root, self.root / 'case', context, expected, runtime)
        self.assertEqual(len(calls), 1)
        self.assertEqual(set(calls[0][0][0]), set(self.m.OUTPUTS))
        self.assertEqual(calls[0][1], {'original_root': context})

    def test_duplicate_transport_and_missing_artifact_reject_before_native(self):
        root, expected, runtime = self.capsule_fragment()
        self.mutate_capsule(root, 'capture.json', lambda v: v['files'].pop('runtime.json'))
        calls = []
        n = SimpleNamespace(validate_outputs=lambda *a, **kw: calls.append(a))
        with self.assertRaisesRegex(ValueError, 'eight_original'):
            self.m.verify_capture(n, self.common_fragment(), root, self.root / 'case', self.root / 'context', expected, runtime)
        self.assertEqual(calls, [])
        self.mutate_capsule(root, 'capture.json', lambda v: v['files'].update({'runtime.json': v['before']}))
        with self.assertRaises(ValueError):
            self.m.verify_capture(n, self.common_fragment(), root, self.root / 'case', self.root / 'context', expected, runtime)
        self.assertEqual(calls, [])

    def test_late_download_interval_and_partial_diagnostic_reject(self):
        root, expected, runtime = self.capsule_fragment()
        label = 'transport/0001.json'
        self.mutate_capsule(root, label, lambda v: v.update(started_utc='2026-11-22T00:00:00+00:00'))
        calls = []
        n = SimpleNamespace(validate_outputs=lambda *a, **kw: calls.append(a))
        with self.assertRaisesRegex(ValueError, 'downloads_between'):
            self.m.verify_capture(n, self.common_fragment(), root, self.root / 'case', self.root / 'context', expected, runtime)
        self.assertEqual(calls, [])
        self.mutate_capsule(root, label, lambda v: v.update(started_utc='2026-11-22T00:00:03+00:00'))
        self.mutate_capsule(root, 'transport/1.stdout', lambda v: v.update(partial_file='retained.partial'))
        with self.assertRaisesRegex(ValueError, 'transport_counts'):
            self.m.verify_capture(n, self.common_fragment(), root, self.root / 'case', self.root / 'context', expected, runtime)
        self.assertEqual(calls, [])

    def test_hidden_partial_and_swapped_profile_reject(self):
        root, expected, runtime = self.capsule_fragment()
        self.m.put(root, 'orphan.partial', b'NONPHYSICAL partial')
        (root / 'files.sha256.json').unlink()
        self.common_fragment().close(root)
        n = SimpleNamespace(validate_outputs=lambda *a, **kw: self.fail('must not reach native'))
        with self.assertRaisesRegex(ValueError, 'hidden_capture'):
            self.m.verify_capture(n, self.common_fragment(), root, self.root / 'case', self.root / 'context', expected, runtime)
        self.mutate_capsule(root, 'capture.json', lambda v: v['leaf'].update(build_profile='release'))
        with self.assertRaisesRegex(ValueError, 'capture_scope'):
            self.m.verify_capture(n, self.common_fragment(), root, self.root / 'case', self.root / 'context', expected, runtime)

    def acquisition_fragment(self, status, fail_name=None, interrupt=False):
        common, calls = self.common_fragment(), []
        m = self.m
        def attempt(root, action, workflow, path=None):
            calls.append((action, path))
            if action == 'download' and path == fail_name:
                m.put(root, 'retained.partial', b'NONPHYSICAL partial')
                if interrupt:
                    raise KeyboardInterrupt()
                raise TimeoutError('controlled transport loss')
            raw = self.server(status) if action == 'observe' else b'NONPHYSICAL artifact'
            return raw, 'NONPHYSICAL-' + str(len(calls)), '00000000-0000-4000-8000-000000000001'
        common.attempt = attempt
        return common, calls

    def test_nonterminal_is_pending_and_downloads_are_not_launched(self):
        common, calls = self.acquisition_fragment('running')
        record = self.m.acquire_case(None, common, self.root / 'pending', self.root / 'case', self.root / 'context', fragment_row(), {})
        self.assertEqual(record['status'], 'pending')
        self.assertEqual(calls, [('observe', None), ('observe', None)])
        self.assertEqual(record['files'], {})

    def test_failed_terminal_forensics_cannot_pass(self):
        common, calls = self.acquisition_fragment('failed')
        record = self.m.acquire_case(None, common, self.root / 'failed', self.root / 'case', self.root / 'context', fragment_row(), {})
        self.assertEqual(record['status'], 'failed')
        self.assertEqual(record['failure_kind'], 'remote_terminal_failure')
        self.assertEqual(len(calls), 10)
        self.assertEqual(set(record['files']), set(self.m.OUTPUTS))

    def test_transport_failure_retains_partial_without_retry_or_promotion(self):
        common, calls = self.acquisition_fragment('finished', 'outputs/runtime.json')
        root = self.root / 'partial'
        record = self.m.acquire_case(None, common, root, self.root / 'case', self.root / 'context', fragment_row(), {})
        self.assertEqual(record['status'], 'incomplete')
        self.assertNotIn('runtime.json', record['files'])
        self.assertEqual(calls.count(('download', 'outputs/runtime.json')), 1)
        self.assertEqual((root / 'retained.partial').read_bytes(), b'NONPHYSICAL partial')
        self.assertTrue(record['external_terminal_evidence_required'])

    def test_interruption_retains_unknown_closure_and_stops_later_downloads(self):
        common, calls = self.acquisition_fragment('finished', 'outputs/runtime.json', interrupt=True)
        root = self.root / 'interrupted'
        with self.assertRaises(KeyboardInterrupt):
            self.m.acquire_case(None, common, root, self.root / 'case', self.root / 'context', fragment_row(), {})
        record = self.m.parse((root / 'capture.json').read_bytes())
        self.assertEqual(record['failure_kind'], 'interrupted_or_unknown')
        self.assertTrue(record['external_terminal_evidence_required'])
        self.assertEqual(calls, [('observe', None), ('download', 'outputs/result.json'), ('download', 'outputs/runtime.json')])
        self.assertTrue((root / 'files.sha256.json').is_file())

    def test_stale_uuid_and_ambiguous_observation_reject(self):
        common = self.common_fragment()
        raw = self.m.parse(self.server())
        raw['matches'].append(dict(raw['matches'][0]))
        with self.assertRaisesRegex(ValueError, 'unique_actual'):
            self.m.observation(common, self.m.encode(raw), fragment_row()['workflow'])
        root, expected, runtime = self.capsule_fragment()
        self.mutate_capsule(root, 'downloads/9.body', lambda v: v['matches'][0].update(id='00000000-0000-4000-8000-000000000002'))
        with self.assertRaisesRegex(ValueError, 'stable_finished_uuid'):
            self.m.verify_capture(SimpleNamespace(), common, root, self.root / 'case', self.root / 'context', expected, runtime)

    def test_unique_UUIDs_are_rederived_across_catalog(self):
        plan = fragment_plan()
        second = dict(fragment_row(), directory='case_0001', workflow='nonphysical-control-0001.1',
                      specification='case_0001/reana.yaml', leaf=dict(build_profile='release', selector='NONPHYSICAL'))
        plan['cases'].append(second)
        for row in plan['cases']:
            record = self.m.empty_capture(row)
            record.update(status='failed', uuid='NONPHYSICAL duplicate')
            self.closed_fragment(self.root / row['directory'], {'capture.json': self.m.encode(record)})
        with self.assertRaisesRegex(ValueError, 'unique_actual_workflow_UUIDs'):
            self.m.derive(None, self.common_fragment(), self.root, plan, {})

    def verification_fragment(self, root):
        m = self.m
        self.closed_fragment(root / 'inputs', {'plan.json': b'{"NONPHYSICAL":true}\n'})
        original = m.inventory(root / 'inputs')
        m.put(root, 'submission_original.json', b'{"NONPHYSICAL":"unexecuted"}\n')
        helpers = {'recovered_native.py': (ROOT / 'tools/galaxy_evidence/recovered_native.py').read_bytes(),
                   'recover_preflight.py': (ROOT / 'scripts/recover_preflight.py').read_bytes(),
                   'recovered_native_results.py': Path(m.__file__).read_bytes()}
        for name, body in helpers.items():
            m.put(root, 'helpers/' + name, body)
        capture = dict(schema='openmhd.recovered-native-results-input-capture.v1',
            files={n: dict(retained='inputs/' + n, **v) for n, v in original.items()},
            original_manifest_sha256=m.sha(m.read(root / 'inputs', 'files.sha256.json')),
            plan_sha256=m.sha(m.read(root / 'inputs', 'plan.json')),
            submission_sha256=m.sha(m.read(root, 'submission_original.json')),
            dependencies={}, history=[], component_accepted=False, physical_accepted=False,
            helper_sha256={n: m.sha(b) for n, b in helpers.items()})
        m.put(root, 'input_capture.json', m.encode(capture))
        m.put(root, 'summary.json', b'{"whole_catalog_passed":true,"NONPHYSICAL":true}\n')
        m.seal(root)

    def test_relocated_offline_route_requires_real_dependency_check_before_flags(self):
        old, moved = self.root / 'old', self.root / 'moved'
        self.verification_fragment(old)
        shutil.move(old, moved)
        calls = []
        deps = dict(verifier=ROOT / 'scripts/recover_preflight.py')
        with patch.object(self.m, 'load_pinned', return_value=SimpleNamespace()), patch.object(self.m, 'dependency_check',
                side_effect=lambda *a: calls.append(a) or (_ for _ in ()).throw(ValueError('real-dependency-sentinel'))):
            with self.assertRaisesRegex(ValueError, 'real-dependency-sentinel'):
                self.m.verify_results(moved, deps)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], moved / 'inputs')
        self.assertFalse(old.exists())

    def test_corrupt_relocated_body_rejects_before_full_verifier(self):
        root = self.root / 'packet'
        self.verification_fragment(root)
        (root / 'inputs/plan.json').write_bytes(b'{"CHANGED":true}\n')
        with patch.object(self.m, 'dependency_check') as real:
            with self.assertRaisesRegex(ValueError, 'closed_results_inventory'):
                self.m.verify_results(root, {})
        real.assert_not_called()

    def test_two_cases_share_one_explicit_original_context(self):
        plan = fragment_plan()
        plan['cases'].append(dict(fragment_row(), directory='case_0001', workflow='nonphysical-control-0001.1'))
        for row in plan['cases']:
            record = self.m.empty_capture(row)
            record.update(status='passed', uuid=row['workflow'])
            self.closed_fragment(self.root / row['directory'], {'capture.json': self.m.encode(record)})
        calls = []
        with patch.object(self.m, 'verify_capture', side_effect=lambda *a: calls.append(a)):
            _, counts, passed = self.m.derive(None, self.common_fragment(), self.root, plan, {})
        self.assertEqual(counts, dict(passed=2, failed=0, pending=0, incomplete=0))
        self.assertTrue(passed)  # isolated caller fragment, NOT a verified native result
        self.assertEqual([a[4] for a in calls], [self.root / 'inputs/context'] * 2)

    def test_outer_collect_failure_seals_honest_failed_envelope(self):
        source = self.root / 'source'
        self.closed_fragment(source, {'plan.json': b'{"NONPHYSICAL":true}\n'})
        submission = self.root / 'submission.json'
        submission.write_bytes(b'{}\n')
        target = self.root / 'failed-collection'
        with self.assertRaises(ValueError):
            self.m.collect(source, submission, {}, self.root / 'consumer.py', target)
        value = self.m.parse((target / 'summary.json').read_bytes())
        self.assertEqual(value['status'], 'failed')
        self.assertFalse(value['whole_catalog_passed'])
        self.assertTrue(value['external_terminal_evidence_required'])
        self.m.closed_packet(target)

    def native_stage_fragment(self):
        """Only the output-validator stage: no certificate/source/export graph.

        The case-input stage is narrowly patched in the three controls below to
        reach real unchanged native runtime/cleanup/witness checks. Invalid
        witness ensures this fragment never supplies a passing native packet.
        """
        m = self.m
        previous = list(sys.path)
        try:
            sys.path.insert(0, str(ROOT / 'tools/galaxy_evidence'))
            pipeline = importlib.import_module('pipeline')
        finally:
            sys.path[:] = previous
        common = pipeline.c
        n = m.load_pinned(ROOT / 'tools/galaxy_evidence/recovered_native.py', m.CONSUMER_SHA, 'nonphysical_native_stage_consumer')
        root = self.root / 'native-stage'
        resources = dict(threads=1, memory='2Gi', timeout_seconds=180)
        leaf = dict(binary='NONPHYSICAL-BINARY', binary_sha256='c' * 64, selector='NONPHYSICAL')
        case = dict(leaf=leaf, resources=resources, root_release_sha256='d' * 64)
        report = dict(binaries=[dict(path=leaf['binary'], selectors=['NONPHYSICAL', 'OTHER'])])
        buffers = {'case.json': m.encode(case), 'snapshot.json': b'{"NONPHYSICAL":true}\n',
                   'preflight/preflight.json': m.encode(report), 'preflight/runtime.json':
                   m.encode(dict(machine='NONPHYSICAL', python='NONPHYSICAL')),
                   'parent.json': b'NONPHYSICAL no parent\n', 'case.py': b'# NONPHYSICAL\n',
                   'supervisor.py': b'# NONPHYSICAL\n'}
        for name, body in buffers.items():
            m.put(root, name, body)
        payload_raw = m.encode(dict(input_sha256={n: m.sha(b) for n, b in buffers.items()}))
        m.put(root, 'payload.json', payload_raw)
        runtime = dict(kind='native-rust-libtest', image=common.native.IMAGE, schema=common.supervisor.RUNTIME_SCHEMA,
            optimized=0, implementation='CPython', machine='NONPHYSICAL', python='NONPHYSICAL', visible_cpus=1,
            **{'cpu.max': None, 'memory.max': None}, declared_resources=resources,
            thread_environment={name: '1' for name in ('RUST_TEST_THREADS', 'RAYON_NUM_THREADS', 'OMP_NUM_THREADS',
                'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')}, job_path='/NONPHYSICAL/case.py',
            child_raw_path='/NONPHYSICAL/outputs/child_raw.bin')
        result = dict(schema='openmhd.galaxy-native-test-result.v1', input_route='recovered-native-v1',
            status='passed', component_accepted=False, case=case, test_leaves_executed=1, passing_leaves=1,
            payload_sha256=m.sha(payload_raw), snapshot_sha256=m.sha(buffers['snapshot.json']),
            preflight_sha256=m.sha(buffers['preflight/preflight.json']), binary_sha256=leaf['binary_sha256'],
            parent_context_sha256=m.sha(buffers['parent.json']), root_release_sha256=case['root_release_sha256'],
            started_utc='2026-11-22T00:00:00+00:00', finished_utc='2026-11-22T00:00:02+00:00')
        command = dict(schema='openmhd.metadata-command.v1', outcome='success', returncode=0,
            external_terminal_evidence_required=False, cleanup=dict(writers_settled=True, direct_child_reaped=True,
            leader_held_until_group_close=True, group_authority_lost=False, remaining_live_pids=[],
            leader_identity=dict(pid=42, process_group=42, session=42, starttime='1')), pid=42, process_group=42,
            cwd='/NONPHYSICAL', command=['/NONPHYSICAL/test-binary', '--exact', 'NONPHYSICAL', '--test-threads',
            '1', '--color', 'never', '--show-output'], timeout_seconds=180, timeout_scope='direct-child-wait',
            started_utc='2026-11-22T00:00:00+00:00', finished_utc='2026-11-22T00:00:02+00:00', duration_seconds=2)
        values = {'result.json': m.encode(result), 'runtime.json': m.encode(runtime),
                  'stdout.txt': b'NONPHYSICAL invalid witness\n', 'stderr.txt': b'',
                  'child_raw.bin': b'NONPHYSICAL invalid witness\n', 'child_result.json': m.encode(
                  dict(passed=1, failed=0, ignored=0, measured=0, filtered_out=0))}
        command['links'] = {name: m.sha(raw) for name, raw in (('snapshot', buffers['snapshot.json']),
            ('case', buffers['case.json']), ('payload', payload_raw), ('runtime', values['runtime.json']),
            ('runner', buffers['case.py']), ('supervisor', buffers['supervisor.py']))}
        command['links']['binary'] = leaf['binary_sha256']
        values['command.json'] = m.encode(command)
        self.refresh_artifacts(values)
        return n, pipeline, common, root, buffers, case, report['binaries'][0], values

    def refresh_artifacts(self, values):
        values['artifacts.sha256.json'] = self.m.encode({'outputs/' + name: self.m.sha(raw)
            for name, raw in values.items() if name != 'artifacts.sha256.json'})

    def test_real_native_validator_rejects_swapped_runtime_after_manifest_check(self):
        n, pipeline, common, root, buffers, case, binary, values = self.native_stage_fragment()
        runtime = self.m.parse(values['runtime.json'])
        runtime['machine'] = 'SWAPPED-NONPHYSICAL'
        values['runtime.json'] = self.m.encode(runtime)
        self.refresh_artifacts(values)
        with patch.object(n, 'check_case_inputs', return_value=(case, binary, common, pipeline)) as checked:
            with self.assertRaisesRegex(ValueError, 'Actual runtime'):
                n.validate_outputs(values, root, original_root=self.root / 'shared-context')
        self.assertEqual(checked.call_args.kwargs['original_root'], self.root / 'shared-context')

    def test_real_native_validator_rejects_unsettled_held_writer(self):
        n, pipeline, common, root, buffers, case, binary, values = self.native_stage_fragment()
        command = self.m.parse(values['command.json'])
        command['cleanup']['writers_settled'] = False
        values['command.json'] = self.m.encode(command)
        self.refresh_artifacts(values)
        with patch.object(n, 'check_case_inputs', return_value=(case, binary, common, pipeline)) as checked:
            with self.assertRaisesRegex(ValueError, 'Held leader'):
                n.validate_outputs(values, root, original_root=self.root / 'shared-context')
        self.assertEqual(checked.call_count, 1)

    def test_real_native_validator_rejects_raw_log_and_witness_links(self):
        n, pipeline, common, root, buffers, case, binary, values = self.native_stage_fragment()
        values['child_raw.bin'] = b'SWAPPED-NONPHYSICAL\n'
        self.refresh_artifacts(values)
        with patch.object(n, 'check_case_inputs', return_value=(case, binary, common, pipeline)) as checked:
            with self.assertRaisesRegex(ValueError, 'command/source/runtime/binary/raw links'):
                n.validate_outputs(values, root, original_root=self.root / 'shared-context')
            values['child_raw.bin'] = values['stdout.txt']
            self.refresh_artifacts(values)
            with self.assertRaises(ValueError):
                n.validate_outputs(values, root, original_root=self.root / 'shared-context')
        self.assertEqual(checked.call_count, 2)


if __name__ == '__main__':
    unittest.main()
