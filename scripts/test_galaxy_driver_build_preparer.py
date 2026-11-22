"""Metadata-only controls; execute individually on REANA after source review.

Every synthetic digest/byte body below is a NONPHYSICAL schema fixture. None
represents an actual Rust build, compiler artifact, prerequisite or candidate.
"""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('driver_build_preparer',
    ROOT / 'scripts/prepare_galaxy_driver_build.py')
PREPARER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREPARER)


def fixture():
    sources = dict(PREPARER.PINS)
    for package, example in (('moving-mesh', 'geometry3-case'), ('gravity', 'gravity-force-case')):
        sources['crates/' + package + '/Cargo.toml'] = '1' * 64
        sources['crates/' + package + '/examples/' + example + '.rs'] = '2' * 64
    sources['reana/remote.py'] = '3' * 64
    workflow = b'{"SCHEMA_ONLY_NOT_A_REANA_EXECUTION":true}\n'
    snapshot = {'source_revision': 'a' * 40, 'dirty_status': '', 'source_sha256': sources,
                'upload_sha256': {'remote.py': '3' * 64, 'source.tar.gz.part000': '4' * 64},
                'workflow_sha256': PREPARER.sha(workflow)}
    release = {'schema': 'openmhd.galaxy-driver-build-release.v1',
               'source_revision': snapshot['source_revision'], 'source_sha256': copy.deepcopy(sources),
               'preflight_review_sha256': '5' * 64, 'coordinator_release_sha256': '6' * 64}
    return snapshot, release, workflow


class DriverBuildPreparerTests(unittest.TestCase):
    def test_release_is_exact_source_metadata_not_an_acceptance_bit(self):
        snapshot, release, _ = fixture()
        PREPARER.validate_release(release, snapshot)
        for key in ('accepted', 'passed', 'component_accepted'):
            changed = dict(release, **{key: True})
            with self.assertRaisesRegex(ValueError, 'Exact external build release schema'):
                PREPARER.validate_release(changed, snapshot)

    def test_different_revision_or_source_inventory_cannot_be_relabelled(self):
        snapshot, release, _ = fixture()
        changed = copy.deepcopy(release)
        changed['source_revision'] = 'b' * 40
        with self.assertRaisesRegex(ValueError, 'Exact chosen development revision'):
            PREPARER.validate_release(changed, snapshot)
        changed = copy.deepcopy(release)
        changed['source_sha256']['crates/gravity/examples/gravity-force-case.rs'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Exact released source inventory'):
            PREPARER.validate_release(changed, snapshot)

    def test_dirty_boolean_or_missing_revision_does_not_mean_clean(self):
        snapshot, release, _ = fixture()
        for value in (False, None, ' M crates/gravity/src/lib.rs\n'):
            changed = dict(snapshot, dirty_status=value)
            with self.assertRaisesRegex(ValueError, 'Committed clean selected source required'):
                PREPARER.validate_release(release, changed)
        changed = dict(snapshot, source_revision=True)
        with self.assertRaisesRegex(ValueError, 'Exact chosen development revision'):
            PREPARER.validate_release(release, changed)

    def test_changed_builder_or_launcher_pin_fails_even_if_release_agrees(self):
        snapshot, release, _ = fixture()
        for name in PREPARER.PINS:
            changed = copy.deepcopy(snapshot)
            changed['source_sha256'][name] = '0' * 64
            coherent = dict(release, source_sha256=changed['source_sha256'])
            with self.assertRaisesRegex(ValueError, 'Chosen reviewed builder/helper source pins'):
                PREPARER.validate_release(coherent, changed)

    def test_unsafe_source_paths_or_incomplete_example_inventory_are_rejected(self):
        snapshot, release, _ = fixture()
        for name in ('../escape', '/absolute', 'crates//gravity/Cargo.toml'):
            changed = copy.deepcopy(snapshot)
            changed['source_sha256'][name] = '0' * 64
            coherent = dict(release, source_sha256=changed['source_sha256'])
            with self.assertRaisesRegex(ValueError, 'Unsafe input path'):
                PREPARER.validate_release(coherent, changed)
        changed = copy.deepcopy(snapshot)
        del changed['source_sha256']['crates/moving-mesh/examples/geometry3-case.rs']
        with self.assertRaisesRegex(ValueError, 'Both standalone example sources and manifests required'):
            PREPARER.validate_release(dict(release, source_sha256=changed['source_sha256']), changed)

    def test_bootstrap_and_reserved_uploads_are_bound_before_derivation(self):
        snapshot, release, _ = fixture()
        for replacement in ({}, {'remote.py': '0' * 64}):
            with self.assertRaisesRegex(ValueError, 'Original bootstrap/specification pins'):
                PREPARER.validate_release(release, dict(snapshot, upload_sha256=replacement))
        for name in ('snapshot.json', 'reana.yaml', 'build_release.json'):
            changed = copy.deepcopy(snapshot)
            changed['upload_sha256'][name] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'Reserved top-level input collision'):
                PREPARER.validate_release(release, changed)

    def test_external_receipt_hashes_are_strict_digest_references(self):
        snapshot, release, _ = fixture()
        for value in (True, 0, 'A' * 64, '0' * 63, '0' * 65):
            with self.assertRaisesRegex(ValueError, 'External receipt digest reference'):
                PREPARER.validate_release(dict(release, preflight_review_sha256=value), snapshot)

    def test_duplicate_keys_and_nonfinite_metadata_never_normalize_to_release(self):
        with self.assertRaisesRegex(ValueError, 'Repeated JSON key'):
            PREPARER.parse(b'{"schema":1,"schema":2}')
        with self.assertRaisesRegex(ValueError, 'Nonfinite JSON'):
            PREPARER.parse(b'{"value":NaN}')

    def test_specification_has_serial_prepare_and_build_only_with_declared_resources(self):
        snapshot, release, _ = fixture()
        snapshot['upload_sha256']['build_release.json'] = PREPARER.sha(PREPARER.encode(release))
        spec = PREPARER.specification(snapshot)
        self.assertEqual(spec['inputs']['files'], ['snapshot.json', *sorted(snapshot['upload_sha256'])])
        self.assertEqual(spec['workflow']['type'], 'serial')
        steps = spec['workflow']['specification']['steps']
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0]['commands'], ['python3 remote.py prepare'])
        self.assertEqual(steps[1]['commands'], [
            'python3 source/reana/galaxy_driver_build.py --source source --snapshot snapshot.json '
            '--release build_release.json --output outputs/galaxy-driver-build'])
        for step in steps:
            self.assertEqual(step['environment'], PREPARER.IMAGE)
            self.assertEqual(step['kubernetes_cpu_request'], '4')
            self.assertEqual(step['kubernetes_cpu_limit'], '4')
            self.assertEqual(step['kubernetes_memory_limit'], '8Gi')

    def test_derivation_preserves_original_uploads_and_binds_exact_external_release(self):
        snapshot, release, workflow = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / 'snapshot.json').write_bytes(PREPARER.encode(snapshot))
            (root / 'reana.yaml').write_bytes(workflow)
            raw = PREPARER.encode(release)
            result = PREPARER.derive(root, raw)
            self.assertEqual((root / 'build_release.json').read_bytes(), raw)
            self.assertEqual(result['source_sha256'], snapshot['source_sha256'])
            self.assertEqual(result['source_revision'], snapshot['source_revision'])
            for name, digest in snapshot['upload_sha256'].items():
                self.assertEqual(result['upload_sha256'][name], digest)
            self.assertEqual(result['upload_sha256']['build_release.json'], PREPARER.sha(raw))
            self.assertEqual(result['workflow_sha256'], PREPARER.sha((root / 'reana.yaml').read_bytes()))
            declaration = result['workflow_derivation']
            self.assertEqual(declaration['base_workflow_sha256'], snapshot['workflow_sha256'])
            self.assertIs(declaration['external_prerequisite_truth_verified'], False)
            self.assertIs(declaration['component_accepted'], False)
            self.assertEqual(declaration['test_methods_to_execute'], 0)
            self.assertEqual(declaration['numerical_cases_to_execute'], 0)

    def test_changed_original_workflow_rejects_before_release_publication(self):
        snapshot, release, _ = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / 'snapshot.json').write_bytes(PREPARER.encode(snapshot))
            (root / 'reana.yaml').write_bytes(b'CHANGED_SCHEMA_ONLY')
            with self.assertRaisesRegex(ValueError, 'Original frozen specification changed'):
                PREPARER.derive(root, PREPARER.encode(release))
            self.assertFalse((root / 'build_release.json').exists())

    def test_preexisting_release_is_exclusive_and_never_overwritten(self):
        snapshot, release, workflow = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / 'snapshot.json').write_bytes(PREPARER.encode(snapshot))
            (root / 'reana.yaml').write_bytes(workflow)
            path = root / 'build_release.json'
            path.write_bytes(b'EXISTING_SCHEMA_ONLY')
            with self.assertRaises(FileExistsError):
                PREPARER.derive(root, PREPARER.encode(release))
            self.assertEqual(path.read_bytes(), b'EXISTING_SCHEMA_ONLY')
            self.assertEqual((root / 'reana.yaml').read_bytes(), workflow)

    def test_regular_metadata_reader_rejects_links_and_oversize_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / 'metadata.json'
            source.write_bytes(b'NONPHYSICAL')
            linked = root / 'linked.json'
            linked.symlink_to(source)
            with self.assertRaisesRegex(ValueError, 'Canonical absolute input path|Linked input path'):
                PREPARER.regular(linked)
            with self.assertRaisesRegex(ValueError, 'Regular bounded metadata input'):
                PREPARER.regular(source, maximum=2)


if __name__ == '__main__':
    unittest.main()
