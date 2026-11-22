"""Metadata controls, not reference computations or scientific review receipts."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('reference_metadata_preparer',
    ROOT / 'tools/galaxy_evidence/prepare_geometry3_reference.py')
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)


class GeometryReferencePreparationTests(unittest.TestCase):
    def fixture(self):
        # All receipts here are explicitly NONPHYSICAL schema controls. This
        # bypasses public Git capture only to inspect staging/parser behavior.
        sources = {name: (ROOT / relative).read_bytes() for name, relative in p.SOURCE_PATHS.items()}
        receipts = {name: ('NONPHYSICAL METADATA FIXTURE: ' + name).encode()
                    for name in (*p.RECEIPTS, 'import_certificate')}
        descriptions = {name: dict(path='fixtures/' + name + '.bin', sha256=p.sha(raw), bytes=len(raw))
                        for name, raw in receipts.items()}
        release = dict(schema='openmhd.geometry3-reference-release.v1', source_revision='a' * 40,
                       source_sha256={p.SOURCE_PATHS[n]: p.sha(raw) for n, raw in sources.items()},
                       receipts={n: descriptions[n] for n in p.RECEIPTS},
                       import_certificate=descriptions['import_certificate'],
                       scope='registered-252-independent-reference-only',
                       coordinator_prerequisites_inspected=True, candidate_invoked=False, component_accepted=False)
        return release, sources, receipts

    def staged(self, root):
        release, sources, receipts = self.fixture()
        root.mkdir()
        plan = p.stage(root, p.encode(release), sources, receipts, 'nonphysical-schema-control')
        return plan

    def test_literal_catalog_is_exact_complete_ordered_252(self):
        rows = p.catalog()
        self.assertEqual(len(rows), 252)
        self.assertEqual(len({r['name'] for r in rows}), 252)
        for fixture in p.FIXTURES:
            self.assertEqual(sum(r['fixture'] == fixture for r in rows), 36)
        self.assertEqual(rows[0]['name'], 'periodic_one_cell_self_images__s0__pxyz__t0')
        self.assertEqual(rows[-1]['name'], 'bounded_oblique_bisector__s2__pzyx__t1')

    def test_exact_workflow_seven_inputs_ten_outputs_and_resources(self):
        value = p.specification()
        self.assertEqual(set(value['inputs']['files']), {*p.PINS, 'runner.py', 'case.json', 'payload.json'})
        self.assertEqual(len(value['inputs']['files']), 7)
        self.assertEqual(value['outputs']['files'], list(p.ARTIFACTS))
        step, = value['workflow']['specification']['steps']
        self.assertEqual(step['commands'], ['python3 -B runner.py'])
        self.assertEqual((step['kubernetes_cpu_request'], step['kubernetes_cpu_limit'],
                          step['kubernetes_memory_limit']), ('1', '1', '2Gi'))
        self.assertEqual(step['environment'], p.IMAGE)

    def test_release_requires_all_distinct_prerequisite_buffers(self):
        release, _, _ = self.fixture()
        p.validate_release(p.encode(release))
        release['receipts'].pop('preparer_method_output_review')
        with self.assertRaisesRegex(ValueError, 'Six prerequisite'):
            p.validate_release(p.encode(release))
        release, _, _ = self.fixture()
        release['receipts']['job_method_output_review']['path'] = release['receipts']['job_source_review']['path']
        with self.assertRaisesRegex(ValueError, 'Distinct receipt'):
            p.validate_release(p.encode(release))

    def test_release_rejects_bool_counts_and_acceptance_claim(self):
        release, _, _ = self.fixture()
        release['import_certificate']['bytes'] = True
        with self.assertRaisesRegex(ValueError, 'Bounded receipt'):
            p.validate_release(p.encode(release))
        release, _, _ = self.fixture()
        release['component_accepted'] = True
        with self.assertRaisesRegex(ValueError, 'nonaccepting reference scope'):
            p.validate_release(p.encode(release))

    def test_parser_rejects_duplicate_nonfinite_and_unsafe_paths(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON'):
            p.parse(b'{"x":1,"x":2}')
        with self.assertRaisesRegex(ValueError, 'Nonfinite JSON'):
            p.parse(b'{"x":NaN}')
        for name in ('../x', '/x', './x', 'a//x', ''):
            with self.assertRaisesRegex(ValueError, 'Canonical relative'):
                p.safe(name)

    def test_metadata_positive_packet_has_no_reference_results_or_acceptance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'plan'
            original = self.staged(root)
            checked = p.validate_plan(root)
            self.assertEqual(checked, original)
            self.assertFalse(checked['external_prerequisite_truth_verified'])
            self.assertFalse(checked['component_accepted'])
            self.assertFalse(any(path.name == 'reference.json' for path in root.rglob('*')))
            for row in checked['cases']:
                self.assertEqual(p.parse(p.read(root, row['directory'] + '/case.json'))['selection'], row['selection'])

    def test_plan_rejects_missing_duplicate_reordered_catalog(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'plan'
            original = self.staged(root)
            for mode in ('missing', 'duplicate', 'reorder'):
                plan = copy.deepcopy(original)
                if mode == 'missing':
                    plan['cases'].pop()
                elif mode == 'duplicate':
                    plan['cases'][1] = copy.deepcopy(plan['cases'][0])
                else:
                    plan['cases'][0], plan['cases'][1] = plan['cases'][1], plan['cases'][0]
                (root / 'plan.json').write_bytes(p.encode(plan))
                with self.assertRaises(ValueError):
                    p.validate_plan(root)

    def test_plan_rejects_bool_selection_and_resources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'plan'
            original = self.staged(root)
            for field in ('selection', 'resources'):
                plan = copy.deepcopy(original)
                if field == 'selection':
                    plan['cases'][0]['selection']['scale_index'] = False
                else:
                    plan['cases'][0]['resources']['threads'] = True
                (root / 'plan.json').write_bytes(p.encode(plan))
                with self.assertRaisesRegex(ValueError, 'Exact ordered case metadata'):
                    p.validate_plan(root)

    def test_plan_rejects_changed_payload_source_and_receipt_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'plan'
            self.staged(root)
            for name in ('case_0000/payload.json', 'case_0000/reference.py',
                         'context/receipts/m1_acceptance.bin'):
                path = root / name
                old = path.read_bytes()
                path.write_bytes(old + b'changed')
                with self.assertRaises(ValueError):
                    p.validate_plan(root)
                path.write_bytes(old)

    def test_plan_rejects_source_context_even_if_outer_hash_is_updated(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'plan'
            plan = self.staged(root)
            name = 'context/source/reference.py'
            (root / name).write_bytes(b'NONPHYSICAL wrong source')
            raw = (root / name).read_bytes()
            plan['context'][name] = dict(sha256=p.sha(raw), bytes=len(raw))
            (root / 'plan.json').write_bytes(p.encode(plan))
            with self.assertRaisesRegex(ValueError, 'Released source identity'):
                p.validate_plan(root)

    def test_plan_rejects_workflow_change_even_with_updated_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'plan'
            plan = self.staged(root)
            spec = p.specification()
            spec['workflow']['specification']['steps'][0]['kubernetes_memory_limit'] = '1Gi'
            raw = p.encode(spec)
            (root / 'case_0000/reana.yaml').write_bytes(raw)
            plan['cases'][0]['workflow_sha256'] = p.sha(raw)
            (root / 'plan.json').write_bytes(p.encode(plan))
            with self.assertRaisesRegex(ValueError, 'Exact workflow/resources'):
                p.validate_plan(root)

    def test_plan_rejects_extra_files_and_links_but_allows_submission_journal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'plan'
            self.staged(root)
            extra = root / 'unexpected'
            extra.write_bytes(b'x')
            with self.assertRaisesRegex(ValueError, 'Closed staged file'):
                p.validate_plan(root)
            extra.unlink()
            extra.symlink_to(root / 'context/release.json')
            with self.assertRaisesRegex(ValueError, 'Linked plan entry'):
                p.validate_plan(root)
            extra.unlink()
            (root / 'submission.json').write_bytes(b'NONPHYSICAL opaque transport journal')
            checked = p.validate_plan(root)
            self.assertEqual(len(checked['cases']), 252)

    def test_read_rejects_linked_parent_and_fifo_without_blocking(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'real').mkdir()
            (root / 'real/file').write_bytes(b'x')
            (root / 'link').symlink_to(root / 'real', target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'Linked entry'):
                p.read(root, 'link/file')
            p.os.mkfifo(root / 'pipe')
            with self.assertRaisesRegex(ValueError, 'Bounded regular'):
                p.read(root, 'pipe')

    def test_capture_checks_each_git_blob_without_swallowing_observations(self):
        release, sources, receipts = self.fixture()
        reads = {p.SOURCE_PATHS[n]: raw for n, raw in sources.items()}
        reads.update({row['path']: receipts[n] for n, row in release['receipts'].items()})
        reads[release['import_certificate']['path']] = receipts['import_certificate']
        observations = []
        def blob(root, revision, relative):
            observations.append((revision, relative))
            return reads[relative]
        with mock.patch.object(p, 'read', side_effect=lambda root, name: reads[name]), \
             mock.patch.object(p, 'git_blob', side_effect=blob):
            captured = p.capture(ROOT, release)
        self.assertEqual(captured, (sources, receipts))
        self.assertEqual(observations, [(release['source_revision'], rel) for rel in p.SOURCE_PATHS.values()])

    def test_capture_rejects_git_mismatch_and_receipt_mismatch(self):
        release, sources, receipts = self.fixture()
        reads = {p.SOURCE_PATHS[n]: raw for n, raw in sources.items()}
        reads.update({row['path']: receipts[n] for n, row in release['receipts'].items()})
        reads[release['import_certificate']['path']] = receipts['import_certificate']
        with mock.patch.object(p, 'read', side_effect=lambda root, name: reads[name]), \
             mock.patch.object(p, 'git_blob', return_value=b'NONPHYSICAL wrong Git blob'):
            with self.assertRaisesRegex(ValueError, 'Working/committed/released'):
                p.capture(ROOT, release)
        reads[release['receipts']['job_source_review']['path']] += b'changed'
        with mock.patch.object(p, 'read', side_effect=lambda root, name: reads[name]), \
             mock.patch.object(p, 'git_blob', side_effect=lambda root, rev, name: reads[name]):
            with self.assertRaisesRegex(ValueError, 'Original prerequisite buffer'):
                p.capture(ROOT, release)

    def test_public_prepare_never_mutates_existing_destination(self):
        release, sources, receipts = self.fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            release_path = root / 'release.json'
            release_path.write_bytes(p.encode(release))
            output = root / 'existing'
            output.mkdir()
            (output / 'plan.json').write_bytes(b'preexisting user bytes')
            with mock.patch.object(p, 'capture', return_value=(sources, receipts)):
                with self.assertRaises(FileExistsError):
                    p.prepare(ROOT, release_path, output, 'nonphysical')
            self.assertEqual((output / 'plan.json').read_bytes(), b'preexisting user bytes')
            self.assertEqual({v.name for v in output.iterdir()}, {'plan.json'})

    def test_public_failure_invalidates_completed_plan_and_retains_failure(self):
        release, sources, receipts = self.fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            release_path = root / 'release.json'
            release_path.write_bytes(p.encode(release))
            output = root / 'new'
            sentinel = RuntimeError('NONPHYSICAL source-fence failure')
            caught = None
            with mock.patch.object(p, 'capture', side_effect=[(sources, receipts), sentinel]):
                try:
                    p.prepare(ROOT, release_path, output, 'nonphysical')
                except RuntimeError as error:
                    caught = error
            self.assertIs(caught, sentinel)
            self.assertFalse((output / 'plan.json').exists())
            self.assertTrue((output / 'plan.failed.json').is_file())
            failure = p.parse((output / 'preparation_failure.json').read_bytes())
            self.assertFalse(failure['ready_for_submission'])
            self.assertFalse(failure['component_accepted'])

    def test_public_prepare_source_and_release_are_fenced_twice(self):
        release, sources, receipts = self.fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            release_path = root / 'release.json'
            release_path.write_bytes(p.encode(release))
            seen = []
            def captured(repository, value):
                seen.append((repository, value))
                return sources, receipts
            with mock.patch.object(p, 'capture', side_effect=captured):
                result = p.prepare(ROOT, release_path, root / 'new', 'nonphysical')
            self.assertEqual(seen, [(ROOT, release), (ROOT, release)])
            self.assertEqual(len(result['cases']), 252)


if __name__ == '__main__':
    unittest.main()
