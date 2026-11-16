"""Before/after performance comparisons require identical physical outputs."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import add_reana_binary as inputs
import run_perf_compare as perf

_remote = importlib.util.spec_from_file_location('perf_remote', perf.ROOT/'reana/remote.py')
remote = importlib.util.module_from_spec(_remote)
_remote.loader.exec_module(remote)


def row(files, evolution, total=None, wall=None):
    total = evolution+1. if total is None else total
    return dict(physical_sha256=files, wall_seconds=total if wall is None else wall,
                timing=dict(evolution_seconds=evolution, initialization_seconds=1., total_seconds=total))


class PerformanceComparison(unittest.TestCase):
    def test_cases_are_short_excerpts_of_the_campaign_configuration(self):
        self.assertTrue(set(perf.QUICK) < set(perf.CASES))
        for name, (arguments, cap) in perf.CASES.items():
            self.assertTrue(cap > 0, name)
            for option in ('--case', '--n', '--jitter', '--time'):
                self.assertEqual(arguments.count(option), 1, (name, option))
            self.assertLessEqual(float(arguments[arguments.index('--time')+1]), .03)
            built = perf.command(Path('binary'), arguments, 4, Path('out'))
            self.assertEqual(built[0], 'binary')
            self.assertEqual(built[built.index('--threads')+1], '4')
            self.assertEqual(built[-2:], ['--output', 'out'])
            for option, value in (('--profile', perf.PROFILE), ('--riemann', 'hlld-pressure'),
                                  ('--potential-limiter', 'smooth-extrema'), ('--projection-screening', '1'),
                                  ('--motion', 'rigid')):
                self.assertEqual(built[built.index(option)+1], value)
            self.assertIn('--accelerated-projection', built)

    def test_identity_is_required_file_by_file(self):
        same = perf.compare(row(dict(a='1', b='2'), 10.), row(dict(a='1', b='2'), 4.))
        self.assertTrue(same['bit_identical'])
        self.assertEqual(same['different_files'], [])
        self.assertEqual(same['files_compared'], 2)
        self.assertEqual(same['evolution_speedup'], 2.5)
        self.assertEqual(same['total_speedup'], 11./5.)
        for other in (dict(a='1', b='3'), dict(a='1'), dict(a='1', b='2', c='4')):
            changed = perf.compare(row(dict(a='1', b='2'), 10.), row(other, 4.))
            self.assertFalse(changed['bit_identical'])
            self.assertTrue(changed['different_files'])
        self.assertIsNone(perf.compare(row({}, 1.), row({}, 0.))['evolution_speedup'])

    def test_physical_hashes_exclude_only_the_timing_record(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ('initial.csv', 'final.csv', 'summary.json', 'history.json', 'timing.json', 'run.log'):
                (root/name).write_text(name)
            files = perf.physical_hashes(root)
            self.assertEqual(set(files), {'initial.csv', 'final.csv', 'summary.json', 'history.json'})
            self.assertEqual(files['final.csv'], hashlib.sha256(b'final.csv').hexdigest())
            (root/'final.csv').unlink()
            with self.assertRaises(ValueError):
                perf.physical_hashes(root)

    def test_remote_study_builds_then_compares_without_other_checks(self):
        for study, quick in (('perf-compare', False), ('perf-compare-quick', True)):
            self.assertIn(study, remote.STUDIES)
            build, compare = remote.commands(study, 4)
            self.assertEqual(build, ['cargo', 'build', '--release', '--workspace', '--locked'])
            self.assertEqual(compare[1], 'scripts/run_perf_compare.py')
            self.assertEqual(compare[compare.index('--threads')+1], '4')
            self.assertTrue(compare[compare.index('--baseline')+1].endswith('baseline-vector-potential'))
            self.assertEqual('--quick' in compare, quick)

    def test_added_binary_is_registered_like_a_source_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = bytes(range(256))*5000   # 1.28 MB: two parts
            binary = root/'binary'
            binary.write_bytes(data)
            snapshot = root/'snapshot'
            snapshot.mkdir()
            (snapshot/'snapshot.json').write_text(json.dumps(dict(
                archives={'source.tar.gz': dict(parts=['source.tar.gz.part000'], sha256='0')},
                upload_sha256={'remote.py': '1'}, workflow_sha256='2')))
            (snapshot/'reana.yaml').write_text('inputs:\n  files:\n    - source.tar.gz.part000\n    - snapshot.json\n    - remote.py\n')
            record = inputs.add(snapshot, 'baseline-vector-potential', binary)
            self.assertEqual(record['parts'], ['baseline-vector-potential.part000', 'baseline-vector-potential.part001'])
            self.assertEqual(record['sha256'], hashlib.sha256(data).hexdigest())
            metadata = json.loads((snapshot/'snapshot.json').read_text())
            self.assertEqual(b''.join((snapshot/p).read_bytes() for p in record['parts']), data)
            for part in record['parts']:
                self.assertEqual(metadata['upload_sha256'][part], hashlib.sha256((snapshot/part).read_bytes()).hexdigest())
            workflow = (snapshot/'reana.yaml').read_text()
            self.assertEqual(workflow.count('baseline-vector-potential.part'), 2)
            self.assertLess(workflow.index('baseline-vector-potential.part001'), workflow.index('- snapshot.json'))
            self.assertEqual(metadata['workflow_sha256'], hashlib.sha256(workflow.encode()).hexdigest())
            self.assertEqual(metadata['archives']['source.tar.gz']['sha256'], '0')
            with self.assertRaises(ValueError):
                inputs.add(snapshot, 'baseline-vector-potential', binary)
            for bad in ('Baseline', '../x', ''):
                with self.assertRaises(ValueError):
                    inputs.add(snapshot, bad, binary)


if __name__ == '__main__':
    unittest.main()
