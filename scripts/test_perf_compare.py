"""Before/after performance comparisons require identical physical outputs."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
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

    def test_variants_are_explicit_edits_of_the_campaign_configuration(self):
        self.assertEqual(perf.configuration(), perf.CONFIGURATION)
        self.assertTrue(set(perf.IDENTITY_VARIANTS) <= set(perf.VARIANTS))
        for variant, (removed, added) in perf.VARIANTS.items():
            options = perf.configuration(variant)
            self.assertTrue(removed or added)
            self.assertEqual(options, [o for o in perf.CONFIGURATION if o not in removed]+list(added))
            built = perf.command(Path('binary'), ['--case', 'alfven'], 4, Path('out'), variant)
            self.assertFalse(set(removed) & set(built))
            self.assertEqual(built[-4:], ['--threads', '4', '--output', 'out'])
            # The baseline binary knows only existing options.
            if variant in perf.IDENTITY_VARIANTS:
                self.assertEqual(added, ())
        iterative = perf.configuration('iterative_projection')
        self.assertNotIn('--accelerated-projection', iterative)
        self.assertEqual(iterative[iterative.index('--projection-screening')+1], '1')
        for variant in ('step_fraction_0.95', 'iterative_step_fraction_0.95'):
            options = perf.configuration(variant)
            self.assertEqual(options[options.index('--trial-step-fraction')+1], '0.95')
            self.assertNotIn(variant, perf.IDENTITY_VARIANTS)
        for broken in ((('--no-such-option',), ()), ((), ('--profile', 'x'))):
            perf.VARIANTS['broken'] = broken
            try:
                with self.assertRaises(ValueError):
                    perf.configuration('broken')
            finally:
                del perf.VARIANTS['broken']

    def test_recorded_baseline_needs_the_same_binary_arguments_and_configuration(self):
        name = perf.RECORDED_CASES[0]
        arguments = perf.CASES[name][0]
        report = dict(status='completed', configuration=perf.CONFIGURATION, baseline_binary_sha256='b',
                      threads=4, created_utc='t', runs={
                          name+'_baseline': dict(status='completed', command=['/somewhere/binary', *arguments, '--x'],
                                                 steps=3, rejected_cfl=2, physical_sha256=dict(a='1'), wall_seconds=9.,
                                                 timing=dict(evolution_seconds=5., initialization_seconds=1., total_seconds=7.,
                                                             phases=dict(step=[5., 3]))),
                          name+'_candidate': dict(status='completed')})
        record = perf.record_of(report)
        self.assertEqual(set(record['cases']), {name})
        self.assertNotIn('somewhere', json.dumps(record))
        self.assertNotIn('phases', record['cases'][name]['timing'])
        row = perf.recorded(record, name, arguments, 'b')
        self.assertEqual((row['status'], row['steps'], row['physical_sha256'], row['recorded_threads']),
                         ('recorded', 3, dict(a='1'), 4))
        after = dict(physical_sha256=dict(a='1'), wall_seconds=3.,
                     timing=dict(evolution_seconds=1., initialization_seconds=1., total_seconds=2.))
        compared = perf.compare(row, after)
        self.assertTrue(compared['bit_identical'])
        self.assertEqual((compared['evolution_speedup'], compared['wall_speedup']), (5., 3.))
        self.assertIsNone(perf.recorded(None, name, arguments, 'b'))
        self.assertIsNone(perf.recorded(record, name, arguments, 'other binary'))
        self.assertIsNone(perf.recorded(record, name, [*arguments[:-1], '9'], 'b'))
        self.assertIsNone(perf.recorded(dict(record, configuration=['--profile', 'x']), name, arguments, 'b'))
        other = next(n for n in perf.CASES if n not in perf.RECORDED_CASES)
        self.assertIsNone(perf.recorded(dict(record, cases={other: record['cases'][name]}), other,
                                        arguments, 'b'))
        for broken in (dict(report, status='failed'), dict(report, configuration=[]),
                       dict(report, runs={name+'_baseline': dict(report['runs'][name+'_baseline'],
                                                                 command=['binary', '--case', 'loop'])})):
            with self.assertRaises(ValueError):
                perf.record_of(broken)

    def test_committed_record_is_the_campaign_baseline_without_paths(self):
        text = perf.RECORD.read_text()
        record = json.loads(text)
        self.assertEqual(record['configuration'], perf.CONFIGURATION)
        self.assertEqual(len(record['baseline_binary_sha256']), 64)
        for marker in ('/Users/', '/var/', '/home/', '@'):
            self.assertNotIn(marker, text)
        for name in perf.RECORDED_CASES:
            row = perf.recorded(record, name, perf.CASES[name][0], record['baseline_binary_sha256'])
            self.assertEqual(row['status'], 'recorded')
            self.assertTrue({'initial.csv', 'final.csv', 'summary.json', 'history.json'} <= set(row['physical_sha256']))
            self.assertGreater(row['timing']['evolution_seconds'], 0.)

    def test_variant_is_measured_column_by_column(self):
        header = 'id,time,'+','.join(perf.PHYSICAL+perf.POTENTIAL)+',volume'
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for label, shift, steps in (('a', 0., 5), ('b', 1e-9, 6)):
                (root/label).mkdir()
                rows = [header]
                for i in range(3):
                    values = [float(i), .5]+[1.+i+(shift if k == 2 else 0.) for k in range(len(perf.PHYSICAL))]
                    values += [-2.-i-(4*shift if k == 1 else 0.) for k in range(len(perf.POTENTIAL))]+[.25]
                    rows.append(','.join(f'{v:.17e}' for v in values))
                (root/label/'final.csv').write_text('\n'.join(rows)+'\n')
                (root/label/'summary.json').write_text(json.dumps(dict({k: 0 for k in perf.COUNTERS}, steps=steps)))
            measured = perf.measure(root/'a', root/'b')
            self.assertAlmostEqual(measured['largest_physical_difference'], 1e-9, delta=1e-15)
            self.assertAlmostEqual(measured['largest_potential_difference'], 4e-9, delta=1e-15)
            self.assertEqual(measured['columns'][perf.PHYSICAL[0]]['max_abs_difference'], 0.)
            self.assertEqual(measured['columns'][perf.PHYSICAL[0]]['max_abs_value'], 3.)
            self.assertEqual(measured['columns']['volume'], dict(max_abs_difference=0., max_abs_value=.25))
            self.assertEqual(measured['counters']['steps'], [5, 6])
            self.assertEqual(perf.measure(root/'a', root/'a')['largest_physical_difference'], 0.)
            (root/'b/final.csv').write_text(header+'\n')
            with self.assertRaises(ValueError):
                perf.measure(root/'a', root/'b')
        self.assertEqual(perf.phase(dict(timing=dict(phases={'x': [1.5, 2]})), 'x'), [1.5, 2])
        self.assertEqual(perf.phase(dict(timing={}), 'x'), [0., 0])

    def test_one_child_is_timed_and_capped_by_itself(self):
        with tempfile.TemporaryFile() as log:
            code, usage = perf.execute([sys.executable, '-c', 'raise SystemExit(3)'], log, 30)
            self.assertEqual(code, 3)
            self.assertGreater(usage.ru_maxrss, 0)
            with self.assertRaises(perf.subprocess.TimeoutExpired):
                perf.execute([sys.executable, '-c', 'import time; time.sleep(30)'], log, .2)

    def test_historical_suite_runs_other_profiles_without_campaign_options(self):
        self.assertEqual(set(perf.SUITES), {'campaign', 'historical'})
        self.assertFalse(set(perf.HISTORICAL) & set(perf.CASES))
        profiles = set()
        for name, (arguments, cap) in perf.HISTORICAL.items():
            self.assertTrue(cap > 0, name)
            for option in ('--profile', '--case', '--n', '--jitter', '--time'):
                self.assertEqual(arguments.count(option), 1, (name, option))
            self.assertLessEqual(float(arguments[arguments.index('--time')+1]), .03)
            built = perf.command(Path('binary'), arguments, 4, Path('out'), campaign=False)
            self.assertEqual(built, ['binary', *arguments, '--threads', '4', '--output', 'out'])
            for option in ('--accelerated-projection', '--riemann', '--potential-limiter', '--projection-screening',
                           '--trial-step-fraction'):
                self.assertNotIn(option, built)
            profiles.add(perf.expected_profile(arguments, campaign=False))
        # The historical default and every other Heun profile, with and without moving meshes.
        self.assertTrue({'paper-global-v2', 'bulk-frame-v1', 'bulk-frame-heun-v1', 'bulk-frame-heun-spline-v1',
                         'bulk-frame-heun-projected-v1', perf.PROFILE} <= profiles)
        motions = {a[a.index('--motion')+1] for a, _ in perf.HISTORICAL.values() if '--motion' in a}
        self.assertTrue({'fluid', 'rigid'} <= motions)
        self.assertEqual(perf.expected_profile(['--case', 'alfven']), perf.PROFILE)

    def test_remote_study_builds_then_compares_without_other_checks(self):
        for study, quick, historical in (('perf-compare', False, False), ('perf-compare-quick', True, False),
                                         ('perf-compare-historical', False, True)):
            self.assertIn(study, remote.STUDIES)
            self.assertIn(study, remote.PERF_STUDIES)
            build, compare = remote.commands(study, 4)
            self.assertEqual(build, ['cargo', 'build', '--release', '--workspace', '--locked'])
            self.assertEqual(compare[1], 'scripts/run_perf_compare.py')
            self.assertEqual(compare[compare.index('--threads')+1], '4')
            self.assertTrue(compare[compare.index('--baseline')+1].endswith('baseline-vector-potential'))
            self.assertEqual('--quick' in compare, quick)
            self.assertEqual('--suite' in compare, historical)
            if historical:
                self.assertEqual(compare[compare.index('--suite')+1], 'historical')

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
