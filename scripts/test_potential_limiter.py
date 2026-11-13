"""Issue #26 limiter controls: explicit, validated, and absent from registered defaults."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import reana_cases as fanout
import run_m1_bounded as bounded
import run_m1_physics as physics
import run_m1_wave_loop as wave
import standing_limiter_cases as lists
from run_m1_wave_loop import limiter_arguments, limiter_matches
from run_projection_screening import configurations as screening
from run_shock_symmetry import configurations as symmetry

_remote = importlib.util.spec_from_file_location('limiter_remote', fanout.ROOT/'reana/remote.py')
remote = importlib.util.module_from_spec(_remote)
_remote.loader.exec_module(remote)

PROFILE = 'bulk-frame-heun-quadratic-v1'
OPTIONS = dict(accelerated_projection=True, projection_screening=1.)
RESOURCES = dict(threads=2, memory='4Gi', timeout_seconds=180.)


def wave_case():
    return dict(kind='wave', config=dict(name='alfven_probe_base', case='alfven', profile=PROFILE, n=32,
                jitter=0., parallel=1., motion_family='fixed', mesh_velocity=[0., 0.],
                boost=[0., 0., 0.], dt=None, target=1., riemann_solver='hlld-pressure'),
                resources=dict(RESOURCES), options=dict(OPTIONS))


def physics_case():
    return dict(kind='physics', config=dict(name='brio-wu_n64_j0.0_base', case='brio-wu', n=64, ny=4,
                jitter=0., jitter_mode='planar', boost=[0., 0., 0.], time=.1, profile=PROFILE,
                riemann_solver='hlld-pressure'), resources=dict(RESOURCES), options=dict(OPTIONS))


class LimiterControls(unittest.TestCase):
    def test_default_adds_no_argument_and_explicit_choices_are_routed(self):
        self.assertEqual(limiter_arguments(), [])
        self.assertEqual(limiter_arguments('smooth-extrema'), ['--potential-limiter', 'smooth-extrema'])
        self.assertEqual(limiter_arguments('none'), ['--potential-limiter', 'none'])
        self.assertEqual(limiter_arguments(None, True), ['--unlimited'])
        self.assertEqual(limiter_arguments('neighbour-extrema', True),
                         ['--unlimited', '--potential-limiter', 'neighbour-extrema'])
        for bad in ('minmod', '', 0, 'smooth-extrema-v1'):
            with self.assertRaises(ValueError): limiter_arguments(bad)
        for bad in ('yes', 1, None):
            with self.assertRaises(ValueError): limiter_arguments(None, bad)

    def test_summary_must_report_exactly_the_requested_configuration(self):
        self.assertTrue(limiter_matches(dict(limited=True)))
        self.assertTrue(limiter_matches(dict(limited=True, potential_limiter='smooth-extrema-v1'), 'smooth-extrema'))
        self.assertTrue(limiter_matches(dict(limited=True, potential_limiter='none'), 'none'))
        self.assertTrue(limiter_matches(dict(limited=False), None, True))
        self.assertTrue(limiter_matches(dict(limited=False, potential_limiter='neighbour-extrema'),
                                        'neighbour-extrema', True))
        for summary, limiter, unlimited in [
                (dict(limited=True, potential_limiter='none'), None, False),      # unrequested option
                (dict(limited=True), 'none', False),                              # option not applied
                (dict(limited=True, potential_limiter='smooth-extrema-v1'), 'none', False),
                (dict(limited=True, potential_limiter='smooth-extrema'), 'smooth-extrema', False),
                (dict(limited=False), None, False),                               # unrequested --unlimited
                (dict(limited=True), None, True),
                (dict(), None, False),                                            # missing metadata
                (dict(limited=True), 'minmod', False)]:
            self.assertFalse(limiter_matches(summary, limiter, unlimited))

    def test_fanout_accepts_only_explicit_valid_controls(self):
        fanout.validate_case(wave_case())
        fanout.validate_case(physics_case())
        for options in (dict(potential_limiter='smooth-extrema'), dict(potential_limiter='none'),
                        dict(unlimited=True), dict(potential_limiter='neighbour-extrema', unlimited=True)):
            spec = wave_case()
            spec['options'].update(options)
            fanout.validate_case(spec)
        for options in (dict(potential_limiter='minmod'), dict(potential_limiter=None), dict(unlimited='yes'),
                        dict(limiter='none'), dict(unlimited_primitives=True)):
            spec = wave_case()
            spec['options'].update(options)
            with self.assertRaises(ValueError): fanout.validate_case(spec)
        spec = physics_case()
        spec['options']['potential_limiter'] = 'smooth-extrema'
        fanout.validate_case(spec)
        # Unlimited primitives are a smooth-wave diagnostic, never a shock/vortex option.
        spec['options']['unlimited'] = True
        with self.assertRaises(ValueError): fanout.validate_case(spec)
        for key in OPTIONS:
            spec = wave_case()
            del spec['options'][key]
            with self.assertRaises(ValueError): fanout.validate_case(spec)

    def test_boost_pairs_must_share_limiter_options(self):
        base, boost = wave_case(), wave_case()
        boost['config'].update(name='alfven_probe_boost', boost=[2., -1., 0.], mesh_velocity=[2., -1.])
        boost['options']['potential_limiter'] = 'smooth-extrema'
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            metadata = dict(source_sha256={n: fanout.sha(fanout.ROOT/n) for n in (
                'reana/case.py', 'reana/remote.py', 'scripts/reana_cases.py',
                'scripts/run_m1_wave_loop.py', 'scripts/run_m1_physics.py')})
            (root/'snapshot').mkdir()
            fanout.dump(root/'snapshot/snapshot.json', metadata)
            (root/'preflight').mkdir()
            (root/'preflight/vector-potential').write_bytes(b'fixture')
            receipt = dict(binary_sha256=fanout.sha(root/'preflight/vector-potential'))
            with patch.object(fanout, 'verify_preflight', return_value=receipt):
                with self.assertRaisesRegex(ValueError, 'Mismatched boost-pair'):
                    fanout.prepare(root/'snapshot', root/'preflight', [base, boost], root/'plan', 'fixture')
            self.assertFalse((root/'plan').exists())

    def test_wave_and_physics_commands_carry_the_controls(self):
        done = SimpleNamespace(returncode=0)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(wave.subprocess, 'run', return_value=done):
                for kwargs, expected in [
                        (dict(), []),
                        (dict(potential_limiter='smooth-extrema'), ['--potential-limiter', 'smooth-extrema']),
                        (dict(potential_limiter='neighbour-extrema', unlimited=True),
                         ['--unlimited', '--potential-limiter', 'neighbour-extrema'])]:
                    config = copy.deepcopy(wave_case()['config'])
                    config['name'] = 'wave_'+str(len(expected))
                    _, record = wave.run_case(config, Path('binary'), root, threads=1, timeout=1.,
                                              **OPTIONS, **kwargs)
                    # The stub writes no summary: an incomplete run is never a completed case.
                    self.assertNotEqual(record['status'], 'completed')
                    command = record['command']
                    self.assertEqual([a for a in command if a in ('--unlimited', '--potential-limiter')],
                                     [a for a in expected if a.startswith('--')])
                    if '--potential-limiter' in expected:
                        self.assertEqual(command[command.index('--potential-limiter')+1], expected[-1])
            with patch.object(physics.subprocess, 'run', return_value=done):
                for limiter in (None, 'smooth-extrema'):
                    config = copy.deepcopy(physics_case()['config'])
                    config['name'] = 'physics_'+str(limiter)
                    _, record = physics.run_case(config, Path('binary'), root, {}, {}, threads=1, timeout=1.,
                                                 **OPTIONS, potential_limiter=limiter)
                    self.assertNotEqual(record['status'], 'completed')
                    command = record['command']
                    self.assertNotIn('--unlimited', command)
                    self.assertEqual('--potential-limiter' in command, limiter is not None)
                    if limiter:
                        self.assertEqual(command[command.index('--potential-limiter')+1], limiter)

    def test_bounded_stages_carry_the_explicit_limiter_and_the_default_adds_none(self):
        chosen = bounded.stages(PROFILE, 1., True, riemann='hlld-pressure', potential_limiter='smooth-extrema')
        default = bounded.stages(PROFILE, 1., True, riemann='hlld-pressure')
        self.assertEqual([s[0] for s in chosen], [s[0] for s in default])
        for (_, tail, *_), (_, plain, *_) in zip(chosen, default):
            self.assertNotIn('--potential-limiter', plain)
            self.assertEqual(tail, [*plain, '--potential-limiter', 'smooth-extrema'])
        with self.assertRaises(ValueError):
            bounded.stages(PROFILE, 1., False, potential_limiter='minmod')

    def test_bounded_gate_requires_exactly_the_requested_limiter_metadata(self):
        self.assertTrue(bounded.limiter_metadata_matches({}))
        self.assertTrue(bounded.limiter_metadata_matches(dict(potential_limiter='smooth-extrema-v1'), 'smooth-extrema'))
        for summary, limiter in [({}, 'smooth-extrema'), (dict(potential_limiter='none'), 'smooth-extrema'),
                                 (dict(potential_limiter='smooth-extrema-v1'), None),
                                 (dict(potential_limiter='smooth-extrema'), 'smooth-extrema'), ({}, 'minmod')]:
            self.assertFalse(bounded.limiter_metadata_matches(summary, limiter))
        configs = screening((1.,), (), riemann='hlld-pressure')
        summary = dict(profile=PROFILE, projection_screening=1., riemann_solver='hlld-pressure-blend-v1',
                       potential_limiter='smooth-extrema-v1')
        runs = {n: dict(config=c, status='completed', summary=dict(summary)) for n, c in configs.items()}
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            (dest/'manifest.json').write_text(json.dumps(configs))
            save = lambda: (dest/'runs.json').write_text(json.dumps(runs))
            save()
            match = lambda limiter=None: bounded.execution_matches('waves_short', dest, PROFILE, 1.,
                                                                   'hlld-pressure', limiter)
            self.assertTrue(match('smooth-extrema'))
            self.assertFalse(match())          # unrequested limiter in the summaries
            self.assertFalse(match('none'))
            name = next(iter(runs))
            del runs[name]['summary']['potential_limiter']; save()
            self.assertFalse(match('smooth-extrema'))   # one run without the requested limiter
            for record in runs.values(): record['summary'].pop('potential_limiter', None)
            save()
            self.assertTrue(match())           # the registered default carries no metadata
            self.assertFalse(match('smooth-extrema'))

    def test_literal_symmetry_controls_keep_the_default_limiter(self):
        configs = symmetry('hlld-pressure')
        runs = {}
        for name, c in configs.items():
            literal = c['profile'] == 'paper-global-v2'
            summary = dict(profile=c['profile'], projection_screening=0. if literal else 1.)
            if not literal:
                summary.update(riemann_solver='hlld-pressure-blend-v1', potential_limiter='smooth-extrema-v1')
            runs[name] = dict(config=c, status='completed', summary=summary)
            if literal and c['jitter_mode'] == 'planar':
                runs[name].update(status='failed', error='conservative/curl closure: positive density and pressure')
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            (dest/'manifest.json').write_text(json.dumps(configs))
            save = lambda: (dest/'runs.json').write_text(json.dumps(runs))
            save()
            match = lambda limiter: bounded.execution_matches('shock_symmetry', dest, PROFILE, 1.,
                                                              'hlld-pressure', limiter)
            self.assertTrue(match('smooth-extrema'))
            self.assertFalse(match(None))
            control = next(n for n, c in configs.items()
                           if c['profile'] == 'paper-global-v2' and c['jitter_mode'] == 'columns')
            runs[control]['summary']['potential_limiter'] = 'smooth-extrema-v1'; save()
            self.assertFalse(match('smooth-extrema'))   # a literal control must not use the candidate limiter

    def test_remote_study_runs_only_the_short_stages_of_the_explicit_configuration(self):
        self.assertIn('m1-limiter-bounded', remote.STUDIES)
        commands = remote.commands('m1-limiter-bounded', 3)
        self.assertEqual(commands[:7], remote.commands('smoke', 3)[:7])
        self.assertEqual(len(commands), 8)
        gate = commands[-1]
        self.assertEqual(gate[1], 'scripts/run_m1_bounded.py')
        self.assertNotIn('--medium', gate)
        for option, value in (('--riemann', 'hlld-pressure'), ('--potential-limiter', 'smooth-extrema'),
                              ('--case-timeout', '120'), ('--output-dir', 'results/reana_m1-bounded')):
            self.assertEqual(gate[gate.index(option)+1], value)
        # The registered bounded study and the fan-out preflight are unchanged.
        self.assertNotIn('--potential-limiter', remote.commands('m1-bounded', 3)[-1])
        self.assertEqual(len(remote.commands('m1-fanout-preflight', 1)), 8)
        self.assertFalse(any('--potential-limiter' in c for c in remote.commands('m1-fanout-preflight', 1)))

    def test_case_lists_use_registered_configurations_and_only_documented_options(self):
        expected = {'diag-none': (8, 'potential-none', False), 'diag-primitive': (6, 'primitive-unlimited', False),
                    'diag-linear': (6, 'all-unlimited', False), 'cand-standing': (16, 'smooth-extrema', True),
                    'cand-waves-medium': (48, 'smooth-extrema', True), 'cand-mean': (24, 'smooth-extrema', True),
                    'cand-physics-screen': (26, 'smooth-extrema', True), 'cand-physics': (30, 'smooth-extrema', True),
                    'full-medium': (48, 'smooth-extrema', True), 'full-mean': (24, 'smooth-extrema', True),
                    'full-physics': (30, 'smooth-extrema', True), 'full-waves': (112, 'smooth-extrema', True)}
        self.assertEqual(set(lists.PLANS), set(expected))
        self.assertEqual(lists.VARIANTS['default'], {})
        arguments = SimpleNamespace(suite='physical', candidate_mean=False, profile=PROFILE, quick=False,
                                    temporal=True, calibration=False, riemann='hlld-pressure')
        registered = dict(wave.configurations(arguments)[0])
        registered.update(physics.configurations(False, PROFILE, 'hlld-pressure'))
        for plan, (count, variant, paired) in expected.items():
            cases = lists.PLANS[plan]()
            names = {c['config']['name'] for c in cases}
            self.assertEqual((len(cases), len(names)), (count, count))
            for spec in cases:
                fanout.validate_case(spec)
                self.assertEqual(spec['options'], dict(OPTIONS, **lists.VARIANTS[variant]))
                config = spec['config']
                self.assertEqual((config['profile'], config['riemann_solver']), (PROFILE, 'hlld-pressure'))
                if config['case'] == 'smooth':
                    self.assertEqual((config['target'], config['motion_family']), (.02, 'fixed'))
                else:
                    self.assertEqual(config, registered[config['name']])
                partner = config['name'].removesuffix('_base')+'_boost'
                if config['name'].endswith('_base'):
                    self.assertEqual(partner in names, paired)
            waves = {c['config']['name']: c['config'] for c in cases if c['kind'] == 'wave'}
            # Temporal cases are unpaired; every other registered wave case has its boost partner.
            self.assertEqual(len(fanout.wave_pairs(waves)), sum(n.endswith('_base') for n in waves) if paired else 0)
        standing = lists.PLANS['cand-standing']()
        self.assertEqual({(c['config']['parallel'], c['config']['motion_family'], c['config']['case']) for c in standing},
                         {(1., 'fixed', 'alfven')})
        self.assertEqual(sorted({c['config']['n'] for c in standing}), [32, 64, 128, 256])
        self.assertEqual({c['config']['n'] for c in lists.PLANS['diag-linear']()}, {32, 64, 128})
        screen = lists.PLANS['cand-physics-screen']()
        self.assertFalse(any(c['config']['case'] == 'orszag-tang' and c['config']['n'] == 256 for c in screen))
        self.assertEqual({c['config']['n'] for c in screen if c['config']['case'] == 'brio-wu'}, {256, 512, 1024})

    def test_full_matrix_plans_are_the_registered_matrices_with_wide_execution_budgets(self):
        arguments = lambda **changes: SimpleNamespace(**dict(dict(
            suite='physical', candidate_mean=True, profile=PROFILE, quick=False, temporal=False,
            calibration=False, riemann='hlld-pressure'), **changes))
        registered = {
            'full-medium': wave.configurations(arguments(quick=True))[0],
            'full-mean': wave.configurations(arguments(suite='mean'))[0],
            'full-waves': wave.configurations(arguments(temporal=True))[0],
            'full-physics': physics.configurations(False, PROFILE, 'hlld-pressure')}
        self.assertEqual({k: len(v) for k, v in registered.items()},
                         {'full-medium': 48, 'full-mean': 24, 'full-waves': 112, 'full-physics': 30})
        for plan, configs in registered.items():
            cases = lists.PLANS[plan]()
            self.assertEqual({c['config']['name']: c['config'] for c in cases}, configs)
            for spec in cases:
                fanout.validate_case(spec)
                threads, memory, timeout = (spec['resources'][k] for k in ('threads', 'memory', 'timeout_seconds'))
                # REANA stops any job after 604800 s; a case cap must end first.
                self.assertTrue(0 < timeout < 604800)
                family = 'wave' if spec['kind'] == 'wave' else spec['config']['case']
                self.assertEqual((threads, memory, timeout), lists.CAMPAIGN_RESOURCES[family][spec['config']['n']])
                self.assertGreaterEqual(timeout, lists.RESOURCES[family][spec['config']['n']][2])
        waves = lists.PLANS['full-waves']()
        self.assertEqual(sum(c['config']['name'].startswith('temporal_') for c in waves), 16)
        self.assertEqual(len(fanout.wave_pairs({c['config']['name']: c['config'] for c in waves})), 48)
        # The screens keep their original budgets, so retained case lists regenerate unchanged.
        self.assertEqual(lists.PLANS['cand-waves-medium']()[0]['resources']['timeout_seconds'], 1800.)
        self.assertEqual(lists.PLANS['full-medium']()[0]['resources']['timeout_seconds'], 7200.)


if __name__ == '__main__':
    unittest.main()
