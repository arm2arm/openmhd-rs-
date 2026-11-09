import unittest
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

import run_m1_bounded as gate


def record(name, status='pass'): return dict(name=name, status=status)


class BoundedGate(unittest.TestCase):
    def test_every_stage_must_pass_and_acceptance_is_never_claimed(self):
        for medium in (False, True):
            names = [s[0] for s in gate.stages(gate.CANDIDATE, 1., medium)]
            self.assertEqual(len(names), 5 if medium else 4)
            good = [record(n) for n in names]
            result = gate.assess(good, medium)
            self.assertTrue(result['bounded_blockers_closed'])
            self.assertEqual(result['full_matrix_precondition_met'], medium)
            self.assertFalse(result['full_m1_accepted'])
            self.assertFalse(gate.assess(good, medium, unchanged=False)['bounded_blockers_closed'])
            for status in ('fail', 'timeout'):
                bad = [record(n, status if i == 1 else 'pass') for i, n in enumerate(names)]
                self.assertFalse(gate.assess(bad, medium)['bounded_blockers_closed'])
            self.assertFalse(gate.assess(good[:-1], medium)['bounded_blockers_closed'])
        short = [record(s[0]) for s in gate.stages(gate.CANDIDATE, 1., False)]
        self.assertFalse(gate.assess(short, True)['bounded_blockers_closed'])

    def test_stage_commands_carry_the_named_configuration(self):
        for name, tail, _, cap, expectation in gate.stages('some-profile', 2.5, True):
            self.assertTrue(expectation and cap > 0)
            if name in ('shock_short', 'physics_quick', 'waves_medium'):
                self.assertIn('some-profile', tail)
                self.assertIn('--accelerated-projection', tail)
            if name != 'waves_short':
                self.assertEqual(tail[tail.index('--projection-screening')+1], '2.5')
            else:
                self.assertEqual(tail[tail.index('--kappa')+1], '2.5')
            self.assertEqual(tail[tail.index('--jobs')+1], '3')
            self.assertEqual(float(tail[tail.index('--timeout')+1]), 600 if name == 'waves_medium' else 30)
        for name, tail, _, _, _ in gate.stages(gate.CANDIDATE, 1., True, 24, 120., 1800.):
            self.assertEqual(float(tail[tail.index('--timeout')+1]), 1800 if name=='waves_medium' else 120)

    def test_stage_verdicts_reject_hidden_failures(self):
        short = dict(complete=True, stability_and_budget=True, boost_checks=True,
                     short_diagnostic_checks=True, short_screen_passed=True)
        self.assertTrue(all(gate.verdict('shock_short', short, 1.).values()))
        self.assertFalse(all(gate.verdict('shock_short', dict(short, boost_checks=False), 1.).values()))
        waves = dict(completed=44, expected=44, source_and_binary_unchanged=True,
                     by_kappa={'1.0': dict(wave_orders_passed=True, boost_pairs_passed=True,
                                          all_completed_positive_and_conservative=True, regular_bx_gate_passed=True)})
        self.assertTrue(all(gate.verdict('waves_short', waves, 1.).values()))
        self.assertFalse(all(gate.verdict('waves_short', waves, .5).values()))
        self.assertFalse(all(gate.verdict('waves_short', dict(waves, completed=43), 1.).values()))
        self.assertFalse(all(gate.verdict('waves_short', dict(waves, by_kappa={'1.0': {}}), 1.).values()))
        run = lambda n, ok: dict(config=dict(case='orszag-tang', jitter=.15, jitter_mode='planar', n=n),
                                 positive_and_conservative=True, state_and_diagnostic_gates=ok)
        physics = dict(complete=True, registered_configuration=True, boost_pairs=[dict(status='pass')],
                       runs={'coarse': run(16, False), 'fine': run(32, True)})
        self.assertTrue(all(gate.verdict('physics_quick', physics, 1.).values()))
        physics['runs']['fine'] = run(32, False)
        self.assertFalse(gate.verdict('physics_quick', physics, 1.)['finest_quick_grid_gates'])
        medium = dict(runs={'a': dict(status='completed', positive_and_conservative=True)},
                      pairs=[dict(status='pass under both reported normalizations'), dict(status='pass')])
        self.assertTrue(all(gate.verdict('waves_medium', medium, 1.).values()))
        medium['pairs'].append(dict(status='fail'))
        self.assertFalse(gate.verdict('waves_medium', medium, 1.)['boost_pairs_passed'])
        self.assertFalse(gate.verdict('waves_medium', dict(runs={}, pairs=[]), 1.)['all_runs_completed'])

    def test_execution_requires_complete_matching_candidate(self):
        from run_projection_screening import configurations
        configs = configurations((1.,), ())
        runs = {n: dict(config=c, status='completed', summary=dict(profile=c['profile'], projection_screening=1.))
                for n, c in configs.items()}
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            (dest/'manifest.json').write_text(json.dumps(configs))
            save = lambda: (dest/'runs.json').write_text(json.dumps(runs))
            save()
            self.assertTrue(gate.execution_matches('waves_short', dest, gate.CANDIDATE, 1.))
            self.assertFalse(gate.execution_matches('waves_short', dest, 'wrong-profile', 1.))
            self.assertFalse(gate.execution_matches('waves_short', dest, gate.CANDIDATE, 0.))
            runs.pop(next(iter(runs))); save()
            self.assertFalse(gate.execution_matches('waves_short', dest, gate.CANDIDATE, 1.))

    def test_stage_timeout_stops_its_child_worker(self):
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp)/'surviving_worker'
            ready = Path(temp)/'ready'
            child = f'import time; from pathlib import Path; time.sleep(1); Path({str(marker)!r}).touch()'
            parent = (f'import subprocess, sys, time; from pathlib import Path; '
                      f'subprocess.Popen([sys.executable, "-c", {child!r}]); Path({str(ready)!r}).touch(); time.sleep(10)')
            with (Path(temp)/'log').open('w') as log:
                with self.assertRaises(subprocess.TimeoutExpired):
                    gate.run_stage([sys.executable, '-c', parent], log, .5)
            self.assertTrue(ready.exists())
            time.sleep(.8)
            self.assertFalse(marker.exists(), 'stage timeout left a simulation running')

    def test_literal_control_timeout_is_not_an_expected_pressure_failure(self):
        from run_shock_symmetry import configurations
        configs=configurations()
        runs={n:dict(config=c,status='completed',summary=dict(profile=c['profile'],
                   projection_screening=0. if c['profile']=='paper-global-v2' else 1.)) for n,c in configs.items()}
        literal=[n for n,c in configs.items() if c['profile']=='paper-global-v2' and c['jitter_mode']=='planar']
        for n in literal:
            runs[n].update(status='failed',error='conservative/curl closure: positive density and pressure')
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp)
            (dest/'manifest.json').write_text(json.dumps(configs))
            save=lambda: (dest/'runs.json').write_text(json.dumps(runs))
            save()
            self.assertTrue(gate.execution_matches('shock_symmetry',dest,gate.CANDIDATE,1.))
            runs[literal[0]]['status']='timeout';save()
            self.assertFalse(gate.execution_matches('shock_symmetry',dest,gate.CANDIDATE,1.))

    def test_short_failure_prevents_starting_medium_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in ('Cargo.toml','Cargo.lock','rust-toolchain.toml'):(root/name).touch()
            (root/'target/release').mkdir(parents=True)
            (root/'target/release/vector-potential').touch()
            out=root/'gate'
            fake_stages=[('shock_short',['unused.py'],'summary.json',1,'short control'),
                         ('waves_medium',['unused.py'],'summary.json',1,'must not launch')]
            with (patch.object(gate,'ROOT',root), patch.object(gate,'stages',return_value=fake_stages),
                  patch.object(gate,'run_stage',return_value=1) as run,
                  patch.object(gate.subprocess,'check_output',return_value='fixture'),
                  patch.object(sys,'argv',['gate','--medium','--output-dir',str(out)])):
                self.assertEqual(gate.main(),1)
            self.assertEqual(run.call_count,1)
            result=json.loads((out/'gate.json').read_text())
            self.assertEqual(len(result['stages']),1)
            self.assertFalse(result['bounded_blockers_closed'])


if __name__ == '__main__': unittest.main()
