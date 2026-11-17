"""2026-11-17 follow-up configurations: explicit, validated, recorded, and absent from defaults.

`--iterative-projection` drops the cached factorization of the projected-rate
solve; `--trial-step-fraction S` makes the first trial S times the CFL bound.
"""
import copy
import importlib.util
import json
import math
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
from run_m1_wave_loop import projection_matches, step_arguments, step_matches
from run_projection_screening import configurations as screening
from run_shock_symmetry import configurations as symmetry

_remote = importlib.util.spec_from_file_location('solver_remote', fanout.ROOT/'reana/remote.py')
remote = importlib.util.module_from_spec(_remote)
_remote.loader.exec_module(remote)

PROFILE = 'bulk-frame-heun-quadratic-v1'
RESOURCES = dict(threads=2, memory='4Gi', timeout_seconds=180.)
CACHED = dict(accelerated_projection=True, projection_screening=1.)


def wave_case(options=CACHED):
    return dict(kind='wave', config=dict(name='alfven_probe_base', case='alfven', profile=PROFILE, n=32,
                jitter=0., parallel=1., motion_family='fixed', mesh_velocity=[0., 0.],
                boost=[0., 0., 0.], dt=None, target=1., riemann_solver='hlld-pressure'),
                resources=dict(RESOURCES), options=dict(options))


def physics_case(options=CACHED):
    return dict(kind='physics', config=dict(name='brio-wu_n64_j0.0_base', case='brio-wu', n=64, ny=4,
                jitter=0., jitter_mode='planar', boost=[0., 0., 0.], time=.1, profile=PROFILE,
                riemann_solver='hlld-pressure'), resources=dict(RESOURCES), options=dict(options))


class SolverOptions(unittest.TestCase):
    def test_historical_controller_and_factorization_add_no_argument(self):
        self.assertEqual(step_arguments(), [])
        self.assertEqual(step_arguments(.95), ['--trial-step-fraction', '0.95'])
        self.assertEqual(step_arguments(.5), ['--trial-step-fraction', '0.5'])
        # One is the historical controller: it is selected by omission, never spelled out.
        for bad in (1., 0., -.5, 1.5, math.nan, math.inf, True, 1, '0.95'):
            with self.assertRaises(ValueError):
                step_arguments(bad)

    def test_summaries_must_report_exactly_the_requested_solver_and_controller(self):
        cached = dict(projection_solver='cached-cholesky-pcg', projection_preconditioner_shift=1)
        self.assertTrue(projection_matches(cached, True))
        self.assertTrue(projection_matches({}, False))
        self.assertFalse(projection_matches({}, True))
        self.assertFalse(projection_matches(cached, False))
        self.assertFalse(projection_matches(dict(projection_solver='other'), True))
        self.assertTrue(step_matches({}))
        self.assertTrue(step_matches(dict(trial_step_fraction=.95), .95))
        for summary, step in (({}, .95), (dict(trial_step_fraction=.95), None),
                              (dict(trial_step_fraction=.9), .95), (dict(trial_step_fraction=1), None),
                              (dict(trial_step_fraction=.95), 1.)):
            self.assertFalse(step_matches(summary, step))

    def test_fanout_accepts_only_an_explicit_valid_fraction(self):
        iterative = dict(CACHED, accelerated_projection=False)
        for make in (wave_case, physics_case):
            fanout.validate_case(make(iterative))
            fanout.validate_case(make(dict(iterative, trial_step_fraction=.95)))
            fanout.validate_case(make(dict(CACHED, trial_step_fraction=.95)))
            for bad in (None, 1., 0., 1.5, math.nan, 'x', True):
                with self.assertRaises(ValueError):
                    fanout.validate_case(make(dict(iterative, trial_step_fraction=bad)))
            with self.assertRaises(ValueError):
                fanout.validate_case(make(dict(iterative, step_fraction=.95)))

    def test_wave_and_physics_commands_carry_the_configuration(self):
        done = SimpleNamespace(returncode=0)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for module, make in ((wave, wave_case), (physics, physics_case)):
                with patch.object(module.subprocess, 'run', return_value=done):
                    for accelerated, step in ((True, None), (False, None), (False, .95)):
                        config = copy.deepcopy(make()['config'])
                        config['name'] = f'{module.__name__}_{accelerated}_{step}'
                        extra = () if module is wave else ({}, {})
                        _, record = module.run_case(config, Path('binary'), root, *extra, threads=1, timeout=1.,
                                                    accelerated_projection=accelerated, projection_screening=1.,
                                                    potential_limiter='smooth-extrema', trial_step_fraction=step)
                        # The stub writes no summary: an incomplete run is never a completed case.
                        self.assertNotEqual(record['status'], 'completed')
                        command = record['command']
                        self.assertEqual('--accelerated-projection' in command, accelerated)
                        self.assertEqual(command[command.index('--projection-screening')+1], '1.0')
                        self.assertEqual('--trial-step-fraction' in command, step is not None)
                        if step is not None:
                            self.assertEqual(command[command.index('--trial-step-fraction')+1], '0.95')

    def test_follow_up_plans_are_the_registered_matrices_with_one_changed_solver(self):
        for label, solver, changed in (('iter', 'iterative', dict(accelerated_projection=False)),
                                       ('step', 'iterative-step',
                                        dict(accelerated_projection=False, trial_step_fraction=.95))):
            self.assertEqual(lists.SOLVERS[solver], changed)
            for phase in ('medium', 'mean', 'physics', 'waves'):
                registered = lists.PLANS[f'full-{phase}']()
                follow = lists.PLANS[f'{label}-{phase}']()
                self.assertEqual(len(follow), len(registered))
                for old, new in zip(registered, follow):
                    fanout.validate_case(new)
                    self.assertEqual((new['kind'], new['config'], new['resources']),
                                     (old['kind'], old['config'], old['resources']))
                    self.assertEqual(new['options'], dict(old['options'], **changed))

    def test_bounded_stages_change_only_the_requested_options(self):
        arguments = dict(riemann='hlld-pressure', potential_limiter='smooth-extrema')
        default = bounded.stages(PROFILE, 1., True, **arguments)
        self.assertEqual(default, bounded.stages(PROFILE, 1., True, **arguments, iterative=False, trial_step_fraction=None))
        for iterative, step in ((True, None), (True, .95), (False, .95)):
            chosen = bounded.stages(PROFILE, 1., True, **arguments, iterative=iterative, trial_step_fraction=step)
            self.assertEqual([s[0] for s in chosen], [s[0] for s in default])
            for (name, tail, *rest), (_, plain, *plain_rest) in zip(chosen, default):
                self.assertEqual(rest, plain_rest)
                expected = [a for a in plain if not (iterative and a == '--accelerated-projection')]
                if iterative and name in ('shock_symmetry', 'waves_short'):
                    expected.append('--iterative-projection')
                if step is not None:
                    expected += ['--trial-step-fraction', '0.95']
                self.assertEqual(tail, expected)
                self.assertNotIn('--accelerated-projection', tail if iterative else [])

    def test_bounded_gate_requires_the_solver_and_controller_of_its_configuration(self):
        configs = screening((1.,), (), riemann='hlld-pressure')
        base = dict(profile=PROFILE, projection_screening=1., riemann_solver='hlld-pressure-blend-v1',
                    potential_limiter='smooth-extrema-v1')
        cached = dict(base, projection_solver='cached-cholesky-pcg')
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            (dest/'manifest.json').write_text(json.dumps(configs))

            def match(summary, iterative=False, step=None):
                runs = {n: dict(config=c, status='completed', summary=dict(summary)) for n, c in configs.items()}
                (dest/'runs.json').write_text(json.dumps(runs))
                return bounded.execution_matches('waves_short', dest, PROFILE, 1., 'hlld-pressure', 'smooth-extrema',
                                                 iterative, step)
            self.assertTrue(match(cached))
            self.assertTrue(match(base, True))
            self.assertTrue(match(dict(base, trial_step_fraction=.95), True, .95))
            self.assertFalse(match(base))                                   # no factorization recorded
            self.assertFalse(match(cached, True))                           # factorization used
            self.assertFalse(match(base, True, .95))                        # controller not applied
            self.assertFalse(match(dict(base, trial_step_fraction=.95), True))
            self.assertFalse(match(dict(base, trial_step_fraction=.9), True, .95))

    def test_literal_symmetry_controls_keep_their_defaults(self):
        for iterative in (False, True):
            configs = symmetry('hlld-pressure', iterative)
            for c in configs.values():
                self.assertEqual(c['accelerated_projection'], c['profile'] == PROFILE and not iterative)
        configs = symmetry('hlld-pressure', True)
        runs = {}
        for name, c in configs.items():
            literal = c['profile'] == 'paper-global-v2'
            summary = dict(profile=c['profile'], projection_screening=0. if literal else 1.)
            if not literal:
                summary.update(riemann_solver='hlld-pressure-blend-v1', potential_limiter='smooth-extrema-v1',
                               trial_step_fraction=.95)
            runs[name] = dict(config=c, status='completed', summary=summary)
            if literal and c['jitter_mode'] == 'planar':
                runs[name].update(status='failed', error='conservative/curl closure: positive density and pressure')
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            (dest/'manifest.json').write_text(json.dumps(configs))
            save = lambda: (dest/'runs.json').write_text(json.dumps(runs))
            save()
            match = lambda: bounded.execution_matches('shock_symmetry', dest, PROFILE, 1., 'hlld-pressure',
                                                      'smooth-extrema', True, .95)
            self.assertTrue(match())
            control = next(n for n, c in configs.items()
                           if c['profile'] == 'paper-global-v2' and c['jitter_mode'] == 'columns')
            runs[control]['summary']['trial_step_fraction'] = .95; save()
            self.assertFalse(match())     # a literal control must keep the historical controller

    def test_remote_studies_add_only_the_follow_up_options(self):
        limiter = remote.commands('m1-limiter-bounded', 3)
        for study, extra in (('m1-iterative-bounded', ['--iterative-projection']),
                             ('m1-iterative-step-bounded', ['--iterative-projection', '--trial-step-fraction', '0.95'])):
            self.assertIn(study, remote.STUDIES)
            commands = remote.commands(study, 3)
            self.assertEqual(commands[:7], limiter[:7])
            gate, original = commands[-1], limiter[-1]
            self.assertEqual(gate[:-2], [*original[:-2], *extra])
            self.assertEqual(gate[-2:], ['--output-dir', 'results/reana_m1-bounded'])
        # The registered studies and the fan-out preflight are unchanged.
        self.assertNotIn('--iterative-projection', limiter[-1])
        self.assertFalse(any('--trial-step-fraction' in c for c in remote.commands('m1-fanout-preflight', 1)))
        self.assertNotIn('--iterative-projection', remote.commands('m1-bounded', 3)[-1])


if __name__ == '__main__':
    unittest.main()
