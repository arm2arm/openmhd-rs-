import unittest

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
            self.assertFalse(result['full_m1_accepted'])
            for status in ('fail', 'timeout'):
                bad = [record(n, status if i == 1 else 'pass') for i, n in enumerate(names)]
                self.assertFalse(gate.assess(bad, medium)['bounded_blockers_closed'])
            self.assertFalse(gate.assess(good[:-1], medium)['bounded_blockers_closed'])
        short = [record(s[0]) for s in gate.stages(gate.CANDIDATE, 1., False)]
        self.assertFalse(gate.assess(short, True)['bounded_blockers_closed'])

    def test_stage_commands_carry_the_named_configuration(self):
        for name, tail, _, cap, expectation in gate.stages('some-profile', 2.5, True):
            self.assertTrue(expectation and cap <= 3600)
            if name in ('shock_short', 'physics_quick', 'waves_medium'):
                self.assertIn('some-profile', tail)
                self.assertIn('--accelerated-projection', tail)
            if name != 'waves_short':
                self.assertEqual(tail[tail.index('--projection-screening')+1], '2.5')

    def test_stage_verdicts_reject_hidden_failures(self):
        short = dict(complete=True, stability_and_budget=True, boost_checks=True,
                     short_diagnostic_checks=True, short_screen_passed=True)
        self.assertTrue(all(gate.verdict('shock_short', short, 1.).values()))
        self.assertFalse(all(gate.verdict('shock_short', dict(short, boost_checks=False), 1.).values()))
        waves = dict(completed=44, expected=44, source_and_binary_unchanged=True,
                     by_kappa={'1.0': dict(wave_orders_passed=True, boost_pairs_passed=True)})
        self.assertTrue(all(gate.verdict('waves_short', waves, 1.).values()))
        self.assertFalse(all(gate.verdict('waves_short', waves, .5).values()))
        self.assertFalse(all(gate.verdict('waves_short', dict(waves, completed=43), 1.).values()))
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


if __name__ == '__main__': unittest.main()
