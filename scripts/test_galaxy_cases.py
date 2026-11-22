"""Inert native-case metadata controls, written for separate REANA workflows.

No network, Rust executable, numerical reference or complete scientific packet
is produced by these controls. Archive fixtures contain labelled inert bytes.
"""
import io
import json
from pathlib import Path
import sys
import re
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/galaxy_evidence'))
import common as c
import pipeline
import readonly_adapter as adapter


class GalaxyCaseMetadataTests(unittest.TestCase):
    def test_transfer_paths_are_narrow_and_bounded_to_export_parts(self):
        for name in ('outputs/galaxy-preflight/export.json',
                     'outputs/galaxy-preflight/export.part0000',
                     'outputs/galaxy-preflight/debug-compile.stdout',
                     'outputs/logs/00.log', 'outputs/child_raw.bin'):
            self.assertEqual(adapter.artifact_path(name), name)
        for name in ('../secret', 'outputs/galaxy-preflight/../runtime.json',
                     'outputs/galaxy-preflight/test-binaries.tar.gz',
                     'outputs/galaxy-preflight/export.part00000', 'source/snapshot.json'):
            with self.subTest(name=name), self.assertRaises(adapter.base.AdapterError):
                adapter.artifact_path(name)

    def archive(self, names, link=False):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w:gz') as archive:
            for name in names:
                entry = tarfile.TarInfo(name)
                raw = b'synthetic inert archive member\n'
                if link:
                    entry.type, entry.linkname = tarfile.SYMTYPE, 'outside'
                    archive.addfile(entry)
                else:
                    entry.size = len(raw)
                    archive.addfile(entry, io.BytesIO(raw))
        return stream.getvalue(), raw

    def test_exact_regular_export_members_are_verified_before_use(self):
        data, raw = self.archive(['preflight.json'])
        members = {'preflight.json': {'sha256': c.sha(raw), 'bytes': len(raw)}}
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'export'
            c.extract_export(data, members, destination)
            self.assertEqual(c.read(destination, 'preflight.json'), raw)
            self.assertEqual(c.inventory(destination), members)

    def test_export_link_duplicate_and_path_escape_are_rejected(self):
        for names, linked in ((['preflight.json'], True), (['preflight.json'] * 2, False),
                              (['../outside'], False)):
            data, raw = self.archive(names, linked)
            members = {names[0]: {'sha256': c.sha(raw), 'bytes': len(raw)}}
            with tempfile.TemporaryDirectory() as directory, self.subTest(names=names, link=linked):
                with self.assertRaises(ValueError):
                    c.extract_export(data, members, Path(directory) / 'export')
                self.assertFalse((Path(directory) / 'outside').exists())

    def test_archive_hash_mismatch_cannot_materialize_a_member(self):
        data, raw = self.archive(['preflight.json'])
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'export'
            with self.assertRaisesRegex(ValueError, 'digest'):
                c.extract_export(data, {'preflight.json': {'sha256': '0' * 64, 'bytes': len(raw)}}, destination)
            self.assertFalse((destination / 'preflight.json').exists())

    def test_closure_includes_nested_manifest_and_rejects_extra_or_changed_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            c.put(root, 'nested/files.sha256.json', b'{"synthetic":true}\n')
            c.put(root, 'body', b'synthetic\n')
            c.close(root)
            self.assertIn('nested/files.sha256.json', c.verify_closed(root))
            (root / 'nested/files.sha256.json').write_bytes(b'{}\n')
            with self.assertRaisesRegex(ValueError, 'inventory'):
                c.verify_closed(root)

    def test_generation_fence_rejects_changed_original_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            c.put(root, 'original', b'synthetic initial\n')
            captured = {'original': c.read(root, 'original')}
            c.fence(root, captured)
            (root / 'original').write_bytes(b'synthetic changed\n')
            with self.assertRaisesRegex(ValueError, 'generation'):
                c.fence(root, captured)

    def observe(self, status='finished'):
        return c.encode(dict(schema='openmhd.galaxy-server-observation.v1', origin='server',
            observed_utc='2026-11-22T00:00:00+00:00', matches=[dict(workflow='synthetic-only.1',
                name='synthetic-only', version=1, status=status, id='00000000-0000-4000-8000-000000000001')]))

    def test_uuid_version_and_finished_status_are_required_beyond_origin_label(self):
        row = c.observation(self.observe(), 'synthetic-only.1', finished=True)
        self.assertEqual(row['version'], 1)
        for raw, workflow, identifier in (
            (self.observe('failed'), 'synthetic-only.1', None),
            (self.observe(), 'synthetic-only.2', None),
            (self.observe(), 'synthetic-only.1', '00000000-0000-4000-8000-000000000002')):
            with self.subTest(workflow=workflow, identifier=identifier), self.assertRaises(ValueError):
                c.observation(raw, workflow, identifier, finished=True)

    def test_duplicate_workflow_matches_are_not_deduplicated(self):
        value = c.parse(self.observe())
        value['matches'] *= 2
        with self.assertRaisesRegex(ValueError, 'Unique'):
            c.observation(c.encode(value), 'synthetic-only.1')

    def test_transport_needs_actual_download_diagnostic_and_body_not_server_label(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            identifier = '00000000-0000-4000-8000-000000000001'
            raw = b'labelled synthetic transport bytes, no real server observation\n'
            diagnostic = c.encode(dict(schema='openmhd.galaxy-get-diagnostic.v1', outcome='success',
                code='completed', workflow_ids=[identifier], workflow='synthetic-only.1',
                action='download', requested_path='outputs/result.json'))
            c.put(root, 'body', raw)
            c.put(root, 'out', diagnostic)
            c.put(root, 'err', b'')
            receipt = dict(schema='openmhd.galaxy-transport-attempt.v1', workflow='synthetic-only.1',
                action='download', remote_path='outputs/result.json', outcome='success', returncode=0,
                stdout='out', stdout_sha256=c.sha(diagnostic), stderr='err', stderr_sha256=c.sha(b''),
                output='body', output_sha256=c.sha(raw), cwd=str(root.resolve()),
                adapter_sha256=c.sha(c.read(ROOT, 'tools/galaxy_evidence/readonly_adapter.py')),
                base_adapter_sha256=c.sha(c.read(ROOT, 'tools/m1_evidence/reana_metadata_readonly_adapter.py')),
                started_utc='2026-11-22T00:00:00+00:00', finished_utc='2026-11-22T00:00:01+00:00',
                argv=[sys.executable, '-B', str(ROOT / 'tools/galaxy_evidence/readonly_adapter.py'),
                      'download', '--workflow', 'synthetic-only.1', '--output', str(root.resolve() / 'body'),
                      '--path', 'outputs/result.json'])
            c.write(root, 'receipt.json', receipt)
            self.assertEqual(c.transport_body(root, 'receipt.json', 'synthetic-only.1', identifier,
                                              'download', 'outputs/result.json'), raw)
            (root / 'body').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'digest'):
                c.transport_body(root, 'receipt.json', 'synthetic-only.1', identifier,
                                 'download', 'outputs/result.json')

    def test_original_uncertain_submission_is_preserved_without_invented_ack(self):
        raw = c.encode({'synthetic-only.1': {'status': 'submission uncertain'}})
        self.assertEqual(pipeline.submission_identity(raw, 'synthetic-only.1'), c.parse(raw))
        with self.assertRaisesRegex(ValueError, 'explicitly'):
            pipeline.submission_identity(raw, 'other.1')

    def test_case_spec_declares_one_job_and_no_aggregate_test_command(self):
        resources = dict(threads=1, memory='2Gi', timeout_seconds=300)
        value = pipeline.specification(['case.py', 'payload.json'], resources)
        steps = value['workflow']['specification']['steps']
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]['commands'], ['python3 -B case.py'])
        self.assertEqual(steps[0]['kubernetes_cpu_limit'], '1')
        self.assertEqual(steps[0]['kubernetes_memory_limit'], '2Gi')
        self.assertEqual(len(value['outputs']['files']), 8)

    def test_native_validator_rejects_unittest_and_incomplete_envelopes(self):
        with tempfile.TemporaryDirectory() as directory:
            for values in ({}, {'result.json': b'{"passed":true}'}):
                with self.subTest(values=values), self.assertRaisesRegex(ValueError, 'Eight'):
                    pipeline.validate_native(values, Path(directory), {})
            # Inert schema-only negatives: no binary, execution, source/runtime
            # claims or valid native result are fabricated. The nominal old-unit
            # pass flags below are deliberately invented parser inputs only.
            case_root = Path(directory)
            (case_root / 'case.json').write_bytes(c.encode({'leaf': {}}))
            (case_root / 'payload.json').write_bytes(c.encode({}))
            for result in (
                {'schema': 'openmhd.metadata-regression-result.v2', 'status': 'passed', 'passed': True},
                {'schema': 'openmhd.galaxy-native-test-result.v1', 'status': 'failed'},
            ):
                values = {
                    'result.json': c.encode(result), 'runtime.json': c.encode({}),
                    'command.json': c.encode({}), 'child_result.json': c.encode({}),
                    'stdout.txt': b'', 'stderr.txt': b'', 'child_raw.bin': b'',
                }
                values['artifacts.sha256.json'] = c.encode({
                    'outputs/' + name: c.sha(raw) for name, raw in values.items()})
                with self.subTest(schema=result['schema']), self.assertRaisesRegex(
                        ValueError, '^Actual one-leaf native result$'):
                    pipeline.validate_native(values, case_root, {})

    def catalog_fixture(self):
        """Synthetic compiler metadata, actual source names; no executed catalog."""
        names = lambda path: re.findall(r'#\[test\]\s*fn\s+(\w+)', (ROOT / path).read_text())
        library = [
            'three_d::exact::tests::exact_cancellation_retains_below_binary64_ulp_terms',
            'three_d::exact::tests::dyadic_subnormal_and_signed_zero_decode_exactly',
            'three_d::exact::tests::integer_product_carry_matches_binomial_identity',
            'three_d::exact::tests::determinant_orientation_and_exact_coplanar_contact']
        gravity = json.loads((ROOT / 'crates/gravity/SOURCE_INSPECTION.json').read_text())
        gravity_library = [r['selector'] for r in gravity['test_selector_enumeration']['selectors'] if r['target'] == 'lib']
        definitions = [
            ('galaxy-types', 'identity', ['test'], 'identity', 'tests/identity.rs', names('crates/galaxy-types/tests/identity.rs')),
            ('moving-mesh', 'geometry', ['test'], 'geometry3_analytic', 'tests/geometry3_analytic.rs', names('crates/moving-mesh/tests/geometry3_analytic.rs')),
            ('moving-mesh', 'geometry', ['test'], 'geometry3_controls', 'tests/geometry3_controls.rs', names('crates/moving-mesh/tests/geometry3_controls.rs')),
            ('moving-mesh', 'geometry', ['lib'], 'moving_mesh', 'src/lib.rs', library),
            ('gravity', 'gravity', ['lib'], 'gravity', 'src/lib.rs', gravity_library),
            ('gravity', 'gravity', ['test'], 'reference', 'tests/reference.rs', names('crates/gravity/tests/reference.rs'))]
        snapshot = {'source_sha256': {'docs/synthetic-review.md': c.sha(b'inert synthetic review identity')}}
        for crate in ('galaxy-types', 'moving-mesh', 'gravity'):
            for path in (ROOT / 'crates' / crate).rglob('*'):
                if path.is_file() and (path.suffix == '.rs' or path.name == 'Cargo.toml'):
                    snapshot['source_sha256'][path.relative_to(ROOT).as_posix()] = c.sha(path.read_bytes())
        contract = dict(schema='openmhd.galaxy-reviewed-catalog.v1', component_accepted=False, targets=[])
        report = {'tests': []}
        for crate, component, kind, target, source, selectors in definitions:
            manifest = 'crates/' + crate + '/Cargo.toml'
            source = 'crates/' + crate + '/' + source
            resources = dict(threads=1, memory='1Gi' if component == 'gravity' else '2Gi',
                             timeout_seconds=300 if component == 'geometry' else 180)
            contract['targets'].append(dict(manifest=manifest, component=component, source=source,
                target_kind=kind, target_name=target, selectors=selectors, resources=resources,
                source_sha256={k: v for k, v in snapshot['source_sha256'].items() if k.startswith('crates/' + crate + '/')},
                review_path='docs/synthetic-review.md', review_sha256=snapshot['source_sha256']['docs/synthetic-review.md']))
            for profile in ('debug', 'release'):
                for selector in selectors + (['old::not_selected'] if crate == 'moving-mesh' and kind == ['lib'] else []):
                    report['tests'].append(dict(build_profile=profile, manifest=manifest, target_kind=kind,
                        target_name=target, source=source, selector=selector,
                        binary='binaries/' + profile + '/' + target, binary_sha256='0' * 64))
        return report, contract, snapshot

    def test_complete_catalog_has_both_profiles_and_only_four_geometry_library_leaves(self):
        report, contract, snapshot = self.catalog_fixture()
        selected = c.catalog(report, contract, snapshot)
        self.assertEqual(len(selected), 186)  # 2 * (26 + 28 + 39), synthetic metadata only.
        self.assertFalse(any(v['selector'] == 'old::not_selected' for v, _ in selected))
        self.assertEqual(sum(v['selector'].startswith('three_d::exact::tests::') for v, _ in selected), 8)

    def test_missing_required_library_leaf_cannot_be_silently_skipped(self):
        report, contract, snapshot = self.catalog_fixture()
        c.catalog(report, contract, snapshot)  # Valid positive schema baseline first.
        report['tests'] = [v for v in report['tests'] if not (v['build_profile'] == 'release'
                           and v['selector'].endswith('exact_cancellation_retains_below_binary64_ulp_terms'))]
        with self.assertRaisesRegex(ValueError, 'coverage'):
            c.catalog(report, contract, snapshot)

    def test_omitted_gravity_target_is_not_authorized_by_a_familiar_name(self):
        report, contract, snapshot = self.catalog_fixture()
        c.catalog(report, contract, snapshot)
        contract['targets'] = [v for v in contract['targets'] if v['target_name'] != 'reference']
        with self.assertRaisesRegex(ValueError, 'direct-gravity catalog'):
            c.catalog(report, contract, snapshot)

    def test_changed_source_or_wrong_resource_contract_is_rejected(self):
        report, contract, snapshot = self.catalog_fixture()
        c.catalog(report, contract, snapshot)
        contract['targets'][0]['source_sha256']['crates/galaxy-types/src/lib.rs'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'source pin'):
            c.catalog(report, contract, snapshot)
        report, contract, snapshot = self.catalog_fixture()
        contract['targets'][-1]['resources']['memory'] = '2Gi'
        with self.assertRaisesRegex(ValueError, 'resources'):
            c.catalog(report, contract, snapshot)


if __name__ == '__main__':
    unittest.main()
