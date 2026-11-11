"""Source-packaging checks: preserve edits, omit local data/secrets, verify bytes."""
import json
import hashlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

import prepare_reana as pack

spec = importlib.util.spec_from_file_location('remote', pack.ROOT/'reana/remote.py')
remote = importlib.util.module_from_spec(spec)
spec.loader.exec_module(remote)


class SourceSnapshotTests(unittest.TestCase):
    def test_bounded_study_checks_source_and_uses_one_worker_pool(self):
        commands = remote.commands('m1-bounded', 24)
        self.assertEqual(commands[:7], remote.commands('smoke', 24)[:7])
        gate = commands[-1]
        self.assertIn('--medium', gate)
        self.assertEqual(gate[gate.index('--medium-jobs')+1], '24')
        self.assertEqual(gate[-1], 'results/reana_m1-bounded')
        campaign = remote.commands('m1-campaign', 24)
        self.assertEqual(campaign[:7], commands[:7])
        self.assertEqual(campaign[-1][-1], 'results/reana_m1-campaign')
        self.assertIn(['cargo','test','--release','--workspace','--all-targets','--locked'],campaign)
        self.assertEqual(remote.environment()['RUST_TEST_THREADS'], '1')
        cached = remote.commands('m1-cache-campaign',24)
        self.assertEqual(cached[:-2],campaign[:-1])
        self.assertIn('scripts/run_projection_cache_benchmark.py',cached[-2])
        self.assertEqual(cached[-1],campaign[-1])
        corrected = remote.commands('m1-reporting-campaign',24)
        self.assertEqual(corrected[:-2],campaign[:-1])
        self.assertIn('scripts/run_projection_metadata_check.py',corrected[-2])
        self.assertEqual(corrected[-1],campaign[-1])
        hll = remote.commands('m1-hll-campaign',24)
        self.assertEqual(hll[:-1],campaign[:-1])
        self.assertEqual(hll[-1],[*campaign[-1],'--riemann','hll'])
        pressure = remote.commands('m1-pressure-campaign',24)
        self.assertEqual(pressure[:-1],campaign[:-1])
        self.assertEqual(pressure[-1],[*campaign[-1],'--riemann','hlld-pressure'])

    def test_upload_boundaries(self):
        for name in ('results/run/final.csv', 'target/release/openmhd', '.env',
                     'scripts/.env.local', 'docs/access.key', '../docs/a', '/etc/passwd',
                     '.git/config', 'scripts/__pycache__/a.pyc'):
            self.assertFalse(pack.allowed(name), name)
        self.assertTrue(pack.allowed('crates/mhd-core/src/lib.rs'))
        self.assertTrue(pack.allowed('tests/reference/m1_completion/original/summary.json.gz'))

    def test_dirty_snapshot_and_bundle_restore(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'repo'
            root.mkdir()
            def git(*args):
                return subprocess.run(['git', *args], cwd=root, check=True,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            git('init')
            git('config', 'user.email', 'test@example.invalid')
            git('config', 'user.name', 'Snapshot test')
            (root/'README.md').write_text('old\n')
            git('add', 'README.md')
            git('commit', '-m', 'fixture')
            revision = git('rev-parse', 'HEAD').stdout.decode().strip()
            (root/'README.md').write_text('uncommitted content\n')
            (root/'reana').mkdir()
            (root/'reana/remote.py').write_text('print("remote")\n')
            (root/'reana.yaml').write_text('version: 0.9.0\ninputs:\n  files:\n    - source.tar.gz.part000\n')
            (root/'.env').write_text('TOKEN=fixture-must-not-be-uploaded\n')
            (root/'results').mkdir()
            (root/'results/large.csv').write_text('local raw data\n')
            for study in pack.STUDY_EVIDENCE:
                (root/('tests/reference/'+study)).mkdir(parents=True)
                (root/('tests/reference/'+study+'/old.csv')).write_text('old benchmark output\n')
            (root/'tests/reference/external_mhd').mkdir()
            (root/'tests/reference/external_mhd/pinned.csv').write_text('required reference\n')
            dest = Path(temp)/'submission'
            with patch.object(pack, 'ROOT', root):
                pack.prepare(dest, minimal=True)
                with self.assertRaises(ValueError):
                    pack.prepare(dest)
            metadata = json.loads((dest/'snapshot.json').read_text())
            self.assertEqual(metadata['revision'], revision)
            self.assertTrue(metadata['omitted_existing_m1_completion_results'])
            self.assertEqual(set(metadata['source_sha256']), {'README.md', 'reana.yaml', 'reana/remote.py', 'tests/reference/external_mhd/pinned.csv'})
            self.assertEqual(metadata['omitted_existing_study_evidence'], list(pack.STUDY_EVIDENCE))
            for name, digest in metadata['upload_sha256'].items():
                self.assertEqual(pack.sha(dest/name), digest)
            for name, record in metadata['archives'].items():
                assembled = b''.join((dest/part).read_bytes() for part in record['parts'])
                self.assertEqual(assembled, (dest/name).read_bytes())
            with tarfile.open(dest/'source.tar.gz') as tar:
                self.assertEqual(tar.extractfile('README.md').read(), b'uncommitted content\n')
            clone = Path(temp)/'clone'
            subprocess.run(['git', 'clone', '--no-checkout', str(dest/'source.bundle'), str(clone)],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=clone, text=True).strip()
            self.assertEqual(actual, revision)

    def test_symlink_cannot_upload_external_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'repo'
            root.mkdir()
            subprocess.run(['git', 'init', str(root)], check=True, capture_output=True)
            (root/'docs').mkdir()
            (root/'docs/external').symlink_to('/etc/passwd')
            with patch.object(pack, 'ROOT', root), self.assertRaisesRegex(ValueError, 'Symlinks'):
                pack.prepare(Path(temp)/'upload')

    def test_compact_bundle_restores_exact_dirty_source_without_original_history(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'repo'
            root.mkdir()
            def git(*args):
                return subprocess.check_output(['git', '-c', 'user.name=Test', '-c',
                                                'user.email=test@example.invalid', *args], cwd=root,
                                               stderr=subprocess.PIPE)
            git('init')
            (root/'README.md').write_text('old source')
            git('add', '.')
            git('commit', '--no-gpg-sign', '-m', 'old fixture')
            original = git('rev-parse', 'HEAD').decode().strip()
            (root/'README.md').write_text('exact dirty source')
            (root/'reana').mkdir()
            (root/'reana/remote.py').write_text('print("fixture")\n')
            (root/'reana.yaml').write_text('inputs:\n  files:\n    - source.bundle.part000\n    - source.tar.gz.part000\n')
            destination = Path(temp)/'snapshot'
            with patch.object(pack, 'ROOT', root):
                pack.prepare(destination, minimal=True, compact_history=True)
            metadata = json.loads((destination/'snapshot.json').read_text())
            self.assertEqual(metadata['source_revision'], original)
            self.assertNotEqual(metadata['revision'], original)
            clone = Path(temp)/'clone'
            subprocess.run(['git', 'clone', str(destination/'source.bundle'), str(clone)],
                           check=True, capture_output=True)
            self.assertEqual((clone/'README.md').read_text(), 'exact dirty source')
            self.assertEqual(subprocess.check_output(['git', 'rev-list', '--count', 'HEAD'], cwd=clone).strip(), b'1')
            self.assertEqual(git('rev-parse', 'HEAD').decode().strip(), original)


class DownloadTests(unittest.TestCase):
    def test_preparation_never_overwrites_an_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'outputs').mkdir()
            (root/'outputs/execution.json').write_text('{}')
            with (patch.object(remote, 'OUTPUT', root/'outputs'),
                  patch.object(remote, 'SOURCE', root/'source'),
                  patch.object(remote, 'RUNTIME', root/'runtime')):
                with self.assertRaisesRegex(ValueError, 'execution record'):
                    remote.prepare(resume=True)
                (root/'outputs/execution.json').unlink()
                (root/'source').mkdir()
                with self.assertRaisesRegex(ValueError, 'fresh workflow'):
                    remote.prepare()

    def test_transient_failure_and_invalid_cache_are_retried(self):
        data = b'verified component bytes'
        digest = hashlib.sha256(data).hexdigest()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'component.tar.xz'
            path.write_bytes(b'incomplete old transfer')
            with (patch.object(remote.urllib.request, 'urlopen',
                              side_effect=[urllib.error.URLError('timeout'), io.BytesIO(data)]) as get,
                  patch.object(remote.time, 'sleep')):
                remote.download('https://example.invalid/component', path, digest)
                self.assertEqual(get.call_count, 2)
            self.assertEqual(path.read_bytes(), data)
            self.assertFalse(path.with_name(path.name+'.partial').exists())

    def test_bad_checksum_never_becomes_a_completed_download(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'component.tar.xz'
            with (patch.object(remote.urllib.request, 'urlopen', side_effect=lambda *a, **k: io.BytesIO(b'wrong')),
                  patch.object(remote.time, 'sleep'), self.assertRaises(RuntimeError)):
                remote.download('https://example.invalid/component', path, hashlib.sha256(b'right').hexdigest())
            self.assertFalse(path.exists())
            self.assertFalse(path.with_name(path.name+'.partial').exists())


if __name__ == '__main__':
    unittest.main()
