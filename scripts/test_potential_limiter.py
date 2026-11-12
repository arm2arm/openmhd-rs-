"""Issue #26 limiter controls: explicit, validated, and absent from registered defaults."""
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import reana_cases as fanout
import run_m1_physics as physics
import run_m1_wave_loop as wave
import standing_limiter_cases as lists
from run_m1_wave_loop import limiter_arguments, limiter_matches

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

    def test_case_lists_use_registered_configurations_and_only_documented_options(self):
        expected = {'diag-none': (8, 'potential-none', False), 'diag-primitive': (6, 'primitive-unlimited', False),
                    'diag-linear': (6, 'all-unlimited', False), 'cand-standing': (16, 'smooth-extrema', True),
                    'cand-waves-medium': (48, 'smooth-extrema', True), 'cand-mean': (24, 'smooth-extrema', True),
                    'cand-physics-screen': (26, 'smooth-extrema', True), 'cand-physics': (30, 'smooth-extrema', True)}
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
            self.assertEqual(len(fanout.wave_pairs(waves)), len(waves)//2 if paired else 0)
        standing = lists.PLANS['cand-standing']()
        self.assertEqual({(c['config']['parallel'], c['config']['motion_family'], c['config']['case']) for c in standing},
                         {(1., 'fixed', 'alfven')})
        self.assertEqual(sorted({c['config']['n'] for c in standing}), [32, 64, 128, 256])
        self.assertEqual({c['config']['n'] for c in lists.PLANS['diag-linear']()}, {32, 64, 128})
        screen = lists.PLANS['cand-physics-screen']()
        self.assertFalse(any(c['config']['case'] == 'orszag-tang' and c['config']['n'] == 256 for c in screen))
        self.assertEqual({c['config']['n'] for c in screen if c['config']['case'] == 'brio-wu'}, {256, 512, 1024})


if __name__ == '__main__':
    unittest.main()
