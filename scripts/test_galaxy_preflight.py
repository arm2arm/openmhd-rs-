"""Metadata-only controls for the compile/list exporter; execute only on REANA.

Fixtures are labelled synthetic metadata and contain no scientific results.
No Cargo command or Rust executable runs in these parser/identity controls.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('galaxy_preflight', ROOT / 'reana/galaxy_preflight.py')
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)
NATIVE_SPEC = importlib.util.spec_from_file_location('galaxy_test_case', ROOT / 'reana/galaxy_test_case.py')
native = importlib.util.module_from_spec(NATIVE_SPEC)
NATIVE_SPEC.loader.exec_module(native)


class GalaxyPreflightMetadataTests(unittest.TestCase):
    def test_exact_names_preserve_full_module_selectors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic-list.stdout'
            path.write_text('first::test_force_sign: test\nsecond::test_force_sign: test\n')
            self.assertEqual(preflight.test_names(path),
                             ['first::test_force_sign', 'second::test_force_sign'])

    def test_duplicate_full_selector_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic-list.stdout'
            path.write_text('same::test_value: test\nsame::test_value: test\n')
            with self.assertRaisesRegex(ValueError, 'Repeated'):
                preflight.test_names(path)

    def test_bench_or_execution_output_cannot_be_a_test_listing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic-list.stdout'
            for text in ('bench_name: benchmark\n', 'running 1 test\n', 'test value ... ok\n'):
                path.write_text(text)
                with self.subTest(text=text), self.assertRaisesRegex(ValueError, 'Unsupported'):
                    preflight.test_names(path)

    def test_source_digest_detects_actual_byte_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = root / 'source.rs'
            path.write_bytes(b'// synthetic source metadata\n')
            pin = hashlib.sha256(path.read_bytes()).hexdigest()
            snapshot = {'source_sha256': {'source.rs': pin}}
            self.assertEqual(preflight.source_receipts(root, snapshot)['source.rs']['sha256'], pin)
            path.write_bytes(b'// changed synthetic source metadata\n')
            with self.assertRaisesRegex(ValueError, 'Changed frozen source'):
                preflight.source_receipts(root, snapshot)

    def test_source_path_escape_and_linked_parent_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / 'source'
            source.mkdir()
            outside = root / 'outside'
            outside.mkdir()
            (outside / 'source.rs').write_bytes(b'// synthetic outside metadata\n')
            pin = hashlib.sha256((outside / 'source.rs').read_bytes()).hexdigest()
            for name in ('../outside/source.rs', str(outside / 'source.rs')):
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'Unsafe'):
                    preflight.source_receipts(source, {'source_sha256': {name: pin}})
            (source / 'linked').symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'Changed frozen source'):
                preflight.source_receipts(source, {'source_sha256': {'linked/source.rs': pin}})

    def fixture(self, root):
        """Make inert synthetic Cargo JSON and a non-executed byte placeholder."""
        source = root / 'source'
        (source / 'target/debug/deps').mkdir(parents=True)
        (source / 'crates/example/src').mkdir(parents=True)
        (source / 'crates/example/Cargo.toml').write_text('# synthetic metadata only\n')
        (source / 'crates/example/src/lib.rs').write_text('// synthetic metadata only\n')
        binary = source / 'target/debug/deps/example-synthetic'
        binary.write_bytes(b'not an executable; never executed by these controls')
        artifact = {
            'reason': 'compiler-artifact', 'package_id': 'synthetic-example#0.0.0',
            'manifest_path': str(source / 'crates/example/Cargo.toml'),
            'target': {'name': 'example', 'kind': ['lib'],
                       'src_path': str(source / 'crates/example/src/lib.rs')},
            'profile': {'test': True}, 'features': [], 'executable': str(binary)}
        return source, artifact

    def test_complete_cargo_messages_retain_exact_target_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source, artifact = self.fixture(root)
            path = root / 'synthetic-compile.stdout'
            path.write_text('non-JSON build-tool message\n' + json.dumps(artifact) + '\n' +
                            json.dumps({'reason': 'build-finished', 'success': True}) + '\n')
            values = preflight.compiler_artifacts(path, source)
            self.assertEqual(len(values), 1)
            self.assertEqual(values[0]['manifest'], 'crates/example/Cargo.toml')
            self.assertEqual(values[0]['source'], 'crates/example/src/lib.rs')
            self.assertEqual(values[0]['binary'], Path(artifact['executable']))

    def test_failed_missing_or_duplicate_build_completion_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source, artifact = self.fixture(root)
            path = root / 'synthetic-compile.stdout'
            for flags in ([], [False], [True, True]):
                path.write_text(json.dumps(artifact) + '\n' + ''.join(
                    json.dumps({'reason': 'build-finished', 'success': flag}) + '\n'
                    for flag in flags))
                with self.subTest(flags=flags), self.assertRaisesRegex(ValueError, 'Missing unique'):
                    preflight.compiler_artifacts(path, source)

    def test_duplicate_cargo_target_cannot_silently_replace_binary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source, artifact = self.fixture(root)
            path = root / 'synthetic-compile.stdout'
            path.write_text((json.dumps(artifact) + '\n') * 2 +
                            json.dumps({'reason': 'build-finished', 'success': True}) + '\n')
            with self.assertRaisesRegex(ValueError, 'Duplicate test target'):
                preflight.compiler_artifacts(path, source)

    def test_binary_escape_and_symlink_cannot_enter_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source, artifact = self.fixture(root)
            outside = root / 'outside-placeholder'
            outside.write_bytes(b'synthetic non-executable metadata')
            original = Path(artifact['executable'])
            path = root / 'synthetic-compile.stdout'
            for candidate in (outside, original):
                if candidate == original:
                    original.unlink()
                    original.symlink_to(outside)
                artifact['executable'] = str(candidate)
                path.write_text(json.dumps(artifact) + '\n' +
                                json.dumps({'reason': 'build-finished', 'success': True}) + '\n')
                with self.subTest(candidate=str(candidate)), self.assertRaises(ValueError):
                    preflight.compiler_artifacts(path, source)

    def test_non_test_compiler_output_cannot_release_empty_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source, artifact = self.fixture(root)
            artifact['profile']['test'] = False
            path = root / 'synthetic-compile.stdout'
            path.write_text(json.dumps(artifact) + '\n' +
                            json.dumps({'reason': 'build-finished', 'success': True}) + '\n')
            with self.assertRaisesRegex(ValueError, 'Missing unique'):
                preflight.compiler_artifacts(path, source)


class GalaxyNativeWitnessMetadataTests(unittest.TestCase):
    def sample(self, name='checks::force', passed=1, ignored=0, filtered=3):
        return (f'\nrunning 1 test\ntest {name} ... ok\n\n'
                f'test result: ok. {passed} passed; 0 failed; {ignored} ignored; 0 measured; '
                f'{filtered} filtered out; finished in 0.00s\n\n').encode()

    def test_one_actual_named_leaf_shape_is_required(self):
        # Synthetic parser metadata only; no native execution took place.
        value = native.witness(self.sample(), 'checks::force', 4)
        self.assertEqual(value['selector'], 'checks::force')
        self.assertEqual(value['passed'], 1)
        self.assertEqual(value['filtered_out'], 3)

    def test_zero_passed_or_ignored_cannot_satisfy_leaf(self):
        for data in (self.sample(passed=0), self.sample(ignored=1)):
            with self.subTest(data=data), self.assertRaisesRegex(ValueError, 'exactly one'):
                native.witness(data, 'checks::force', 4)

    def test_wrong_selector_and_wrong_target_count_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            native.witness(self.sample(name='other::force'), 'checks::force', 4)
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            native.witness(self.sample(filtered=2), 'checks::force', 4)

    def test_aggregate_or_duplicate_completion_cannot_pass(self):
        for data in (self.sample().replace(b'running 1 test', b'running 2 tests'),
                     self.sample().replace(b'test checks::force ... ok',
                                           b'test checks::force ... ok\ntest checks::force ... ok')):
            with self.subTest(data=data), self.assertRaisesRegex(ValueError, 'exactly one'):
                native.witness(data, 'checks::force', 4)

    def test_failed_or_truncated_summary_is_rejected(self):
        for data in (self.sample().replace(b'test result: ok.', b'test result: FAILED.'),
                     self.sample().split(b'test result:')[0]):
            with self.subTest(data=data), self.assertRaisesRegex(ValueError, 'exactly one'):
                native.witness(data, 'checks::force', 4)

    def test_should_panic_success_remains_one_leaf(self):
        data = self.sample().replace(b'test checks::force ...', b'test checks::force - should panic ...')
        self.assertEqual(native.witness(data, 'checks::force', 4)['passed'], 1)


if __name__ == '__main__':
    unittest.main()
