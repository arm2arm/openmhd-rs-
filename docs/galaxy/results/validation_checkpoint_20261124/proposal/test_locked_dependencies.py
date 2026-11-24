"""REANA-only controls for archive/config preparation; no Cargo/crate code runs."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('locked_dependency_job', ROOT / 'reana/locked_dependencies.py')
JOB = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(JOB)


def archive(entries, mode):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode=mode, format=tarfile.USTAR_FORMAT) as stream:
        for name, raw, kind in entries:
            info = tarfile.TarInfo(name)
            if kind == 'file':
                info.size = len(raw)
                info.mode = 0o644
                stream.addfile(info, io.BytesIO(raw))
            else:
                info.type = tarfile.SYMTYPE
                info.linkname = raw.decode()
                stream.addfile(info)
    return output.getvalue()


def fixture(work, extra=None):
    """Explicit nonphysical package bytes; neither compiler nor build is invoked."""
    package_manifest = b'[package]\nname="nonphysical-control"\nversion="1.0.0"\nedition="2021"\n'
    source = b'// NONPHYSICAL INERT SOURCE. This control does not compile it.\n'
    entries = [('nonphysical-control-1.0.0/Cargo.toml', package_manifest, 'file'),
               ('nonphysical-control-1.0.0/src/lib.rs', source, 'file')]
    if extra:
        entries.extend(extra)
    crate = archive(entries, 'w:gz')
    digest = JOB.sha(crate)
    lock = ('version = 4\n[[package]]\nname="nonphysical-control"\nversion="1.0.0"\n'
            'source="' + JOB.REGISTRY + '"\nchecksum="' + digest + '"\n').encode()
    for directory in ('source', 'runtime', 'outputs', 'input'):
        (work / directory).mkdir()
    (work / 'source/Cargo.lock').write_bytes(lock)
    (work / 'outputs/runtime.json').write_bytes(b'{"nonphysical_control":true}\n')
    path = 'crates/nonphysical-control-1.0.0.crate'
    manifest = JOB.encode(dict(schema='openmhd.locked-crate-inputs.v1', lock_sha256=JOB.sha(lock),
        packages=[dict(name='nonphysical-control', version='1.0.0', source=JOB.REGISTRY,
                       sha256=digest, bytes=len(crate), path=path, successful_attempt='INERT')]))
    packed = archive([('Cargo.lock', lock, 'file'), ('manifest.json', manifest, 'file'),
                      (path, crate, 'file')], 'w')
    (work / 'input/locked-crates.part0000').write_bytes(packed)
    descriptor = dict(schema='openmhd.locked-crate-bundle.v1', lock_sha256=JOB.sha(lock),
        manifest_sha256=JOB.sha(manifest), archive_sha256=JOB.sha(packed), archive_bytes=len(packed),
        package_count=1, parts=[dict(path='locked-crates.part0000', bytes=len(packed), sha256=JOB.sha(packed))])
    bundle = work / 'input/bundle.json'
    bundle.write_bytes(JOB.encode(descriptor))
    return bundle, JOB.sha(bundle.read_bytes()), source


class LockedDependencyTests(unittest.TestCase):
    def test_exact_archive_installs_offline_config_and_retains_original_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            bundle, digest, source = fixture(work)
            original_lock = (work / 'source/Cargo.lock').read_bytes()
            original_runtime = (work / 'outputs/runtime.json').read_bytes()
            result = JOB.install(work, bundle, digest)
            self.assertEqual(result['status'], 'complete')
            self.assertFalse(result['target_executed'])
            root = work / 'runtime/locked-dependencies/nonphysical-control-1.0.0'
            self.assertEqual((root / 'src/lib.rs').read_bytes(), source)
            checksum = json.loads((root / '.cargo-checksum.json').read_bytes())
            self.assertEqual(checksum['files']['src/lib.rs'], hashlib.sha256(source).hexdigest())
            config = (work / 'runtime/cargo/config.toml').read_text()
            self.assertIn('offline = true', config)
            self.assertIn('replace-with = "locked-inputs"', config)
            runtime = json.loads((work / 'outputs/runtime.json').read_bytes())
            self.assertEqual(runtime['offline_dependencies']['prior_runtime_sha256'], JOB.sha(original_runtime))
            self.assertEqual(runtime['offline_dependencies']['bundle_sha256'], digest)
            self.assertEqual((work / 'source/Cargo.lock').read_bytes(), original_lock)

    def test_changed_descriptor_rejected_before_any_runtime_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            bundle, digest, _ = fixture(work)
            bundle.write_bytes(bundle.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'Explicit workflow bundle identity'):
                JOB.install(work, bundle, digest)
            self.assertFalse((work / 'runtime/locked-dependencies').exists())

    def test_changed_source_lock_rejected_without_cargo_config(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            bundle, digest, _ = fixture(work)
            (work / 'source/Cargo.lock').write_bytes(b'CHANGED')
            with self.assertRaisesRegex(ValueError, 'Actual frozen source lock'):
                JOB.install(work, bundle, digest)
            self.assertFalse((work / 'runtime/cargo/config.toml').exists())

    def test_changed_part_rejected_before_crate_materialization(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            bundle, digest, _ = fixture(work)
            (work / 'input/locked-crates.part0000').write_bytes(b'CHANGED')
            with self.assertRaisesRegex(ValueError, 'Actual bundle part identity'):
                JOB.install(work, bundle, digest)
            self.assertFalse((work / 'runtime/locked-dependencies').exists())

    def test_authenticated_parent_traversal_member_leaves_failed_install_unpublished(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            bundle, digest, _ = fixture(work, [('nonphysical-control-1.0.0/../escape', b'NO', 'file')])
            with self.assertRaisesRegex(ValueError, 'Canonical archive path'):
                JOB.install(work, bundle, digest)
            self.assertFalse((work / 'runtime/cargo/config.toml').exists())
            self.assertFalse((work / 'runtime/escape').exists())
            status = json.loads((work / 'runtime/locked-dependencies/status.json').read_bytes())
            self.assertEqual(status['status'], 'failed')

    def test_authenticated_symbolic_link_cannot_enter_directory_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            bundle, digest, _ = fixture(work, [('nonphysical-control-1.0.0/alias', b'src/lib.rs', 'link')])
            with self.assertRaisesRegex(ValueError, 'Regular crate members only'):
                JOB.install(work, bundle, digest)
            self.assertFalse((work / 'runtime/cargo/config.toml').exists())

    def test_authenticated_duplicate_path_cannot_replace_original_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            bundle, digest, _ = fixture(work, [('nonphysical-control-1.0.0/src/lib.rs', b'REPLACEMENT', 'file')])
            with self.assertRaisesRegex(ValueError, 'Exact distinct crate root'):
                JOB.install(work, bundle, digest)
            self.assertFalse((work / 'runtime/cargo/config.toml').exists())

    def test_existing_cargo_selection_is_preserved_and_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            bundle, digest, _ = fixture(work)
            config = work / 'runtime/cargo/config.toml'
            config.parent.mkdir()
            config.write_bytes(b'EXISTING')
            with self.assertRaisesRegex(ValueError, 'Fresh Cargo source selection'):
                JOB.install(work, bundle, digest)
            self.assertEqual(config.read_bytes(), b'EXISTING')
            self.assertFalse((work / 'runtime/locked-dependencies').exists())
