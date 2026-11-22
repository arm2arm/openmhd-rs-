"""Written runner-isolation controls; execute each only on REANA.

Fixtures are inert source/metadata. No candidate geometry, force, evolution,
network request or finished physical packet is produced by these controls.
"""
import copy
import gzip
import importlib.util
import io
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'galaxy_python_job_controls', ROOT / 'tools/galaxy_python_evidence/reana_metadata_job.py')
job = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(job)


class GalaxyPythonIsolationTests(unittest.TestCase):
    def fixture(self):
        # This synthetic inner leaf is resolved, never executed by a control.
        text = (b'import unittest\nclass Synthetic(unittest.TestCase):\n'
                b'    def test_leaf(self):\n'
                b'        raise AssertionError("synthetic resolution must not execute a leaf")\n')
        sources = {path: text for path in job.TEST_FILES}
        sources[job.JOB_NAME] = b'# inert synthetic job identity, never executed\n'
        identities = job.identities_from_sources(sources)
        snapshot = dict(schema=job.SOURCE_SCHEMA, created_utc='2026-11-22T00:00:00+00:00',
                        source_revision='0' * 40,
                        source_sha256={p: job.digest(b) for p, b in sorted(sources.items())},
                        archive_sha256='1' * 64, job_sha256=job.digest(sources[job.JOB_NAME]),
                        image=job.IMAGE, tests=list(identities), test_identities=identities,
                        test_files=list(job.TEST_FILES), resources=dict(job.RESOURCES),
                        physical_evolutions_run=False, component_accepted=False)
        return sources, snapshot

    def archive(self, sources):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w', format=tarfile.PAX_FORMAT) as stream:
            for name, raw in sorted(sources.items()):
                member = tarfile.TarInfo(name)
                member.size = len(raw)
                stream.addfile(member, io.BytesIO(raw))
        return gzip.compress(buffer.getvalue(), mtime=0)

    def test_snapshot_rejects_m1_namespace_missing_suite_and_bool_resource(self):
        _, snapshot = self.fixture()
        job.validate_snapshot(snapshot)
        old = copy.deepcopy(snapshot)
        old['schema'] = 'openmhd.metadata-regression-source.v2'
        with self.assertRaises(ValueError):
            job.validate_snapshot(old)
        missing = copy.deepcopy(snapshot)
        missing['test_files'].pop()
        with self.assertRaises(ValueError):
            job.validate_snapshot(missing)
        malformed = copy.deepcopy(snapshot)
        malformed['resources']['threads'] = True
        with self.assertRaises(ValueError):
            job.validate_snapshot(malformed)

    def test_scope_cannot_relabel_acceptance_or_physical_evolution(self):
        job.scope(dict(physical_evolutions_run=False, component_accepted=False))
        invalid = (
            dict(scientific_tests_or_evolutions_run=False, full_m1_accepted=False),
            dict(physical_evolutions_run=True, component_accepted=False),
            dict(physical_evolutions_run=False, component_accepted=True),
            dict(physical_evolutions_run=0, component_accepted=False),
            dict(physical_evolutions_run=False, component_accepted=0),
        )
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                job.scope(value)

    def test_extraction_binds_all_five_source_suites_and_rejects_changed_bytes(self):
        sources, snapshot = self.fixture()
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / 'actual'
            job.extract_source(self.archive(sources), snapshot, destination)
            self.assertEqual({p: (destination / p).read_bytes() for p in sources}, sources)
            changed = dict(sources)
            changed[job.TEST_FILES[0]] += b'# changed inert source\n'
            with self.assertRaisesRegex(ValueError, 'Source member hash'):
                job.extract_source(self.archive(changed), snapshot, Path(temporary) / 'changed')

    def test_new_alias_resolves_exactly_one_actual_leaf_without_running_it(self):
        sources, snapshot = self.fixture()
        selector = snapshot['tests'][0]
        identity = snapshot['test_identities'][selector]
        module = selector.rsplit('.', 2)[0]
        alias = job.alias_for(module, identity['source_sha256'])
        self.assertTrue(alias.startswith('galaxy_python_test_'))
        self.assertFalse(alias.startswith('m1_metadata_test_'))
        previous = Path.cwd()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                for name, raw in sources.items():
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(raw)
                os.chdir(root)
                suite, actual = job.load_one(selector, identity)
                self.assertEqual(actual, identity)
                self.assertEqual(suite.countTestCases(), 1)
                self.assertEqual(next(iter(suite)).id(), identity['runtime_id'])
        finally:
            os.chdir(previous)
            sys.modules.pop(alias, None)


if __name__ == '__main__':
    unittest.main()
