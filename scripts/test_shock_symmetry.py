import unittest
from run_m1_physics import bx_gate, mesh_family
from run_shock_symmetry import CANDIDATE, LITERAL, assess, bx_errors, configurations


def passing(configs):
    """Column runs carry a gated Bx check; planar runs record Bx as a diagnostic."""
    runs = {n: dict(status='completed', positive_and_conservative=True,
                    diagnostic_checks=dict(seam=True, **({'bx': True} if c['jitter_mode'] == 'columns' else {})))
            for n, c in configs.items()}
    pairs = [dict(names=[n, n.removesuffix('_base')+'_boost'], status='pass')
             for n in configs if n.endswith('_base')]
    return runs, pairs


class MeshSymmetryScreen(unittest.TestCase):
    def test_registered_cases_keep_the_unchanged_mesh_size_time_and_boost(self):
        configs = configurations()
        self.assertEqual(len(configs), 8)
        for c in configs.values():
            self.assertEqual((c['n'], c['ny'], c['jitter'], c['time']), (256, 4, .15, .1))
            self.assertEqual(c['accelerated_projection'], c['profile'] == CANDIDATE)
        self.assertEqual({c['jitter_mode'] for c in configs.values()}, {'columns', 'planar'})

    def test_timeouts_failures_and_missing_cases_cannot_pass(self):
        configs = configurations(); runs, pairs = passing(configs)
        result = assess(configs, runs, pairs)
        self.assertTrue(result['all_gates_passed'])
        self.assertFalse(result['full_m1_accepted'])
        victim = f'columns_{LITERAL}_base'
        for status in ('failed', 'timeout'):
            bad = assess(configs, {**runs, victim: dict(status=status)}, pairs)
            self.assertFalse(bad['symmetric_mesh_gates_passed'])
            self.assertFalse(bad['all_gates_passed'])
        self.assertFalse(assess(configs, {}, pairs)['symmetric_mesh_gates_passed'])
        self.assertFalse(assess(configs, runs, [])['all_gates_passed'])

    def test_bx_is_gated_on_columns_and_only_diagnostic_on_planar_jitter(self):
        configs = configurations(); runs, pairs = passing(configs)
        groups = {(g['jitter_mode'], g['profile']): g for g in assess(configs, runs, pairs)['groups']}
        self.assertEqual(groups['columns', LITERAL]['bx_gate'], 'pass')
        self.assertEqual(groups['planar', CANDIDATE]['bx_gate'], 'diagnostic')
        # A column run without a Bx check, or with a failed one, cannot pass.
        del runs[f'columns_{CANDIDATE}_base']['diagnostic_checks']['bx']
        self.assertFalse(assess(configs, runs, pairs)['symmetric_mesh_gates_passed'])
        runs[f'columns_{CANDIDATE}_base']['diagnostic_checks']['bx'] = False
        self.assertFalse(assess(configs, runs, pairs)['symmetric_mesh_gates_passed'])

    def test_planar_literal_pressure_failure_stays_a_failure(self):
        configs = configurations(); runs, pairs = passing(configs)
        for label in ('base', 'boost'): runs[f'planar_{LITERAL}_{label}'] = dict(status='failed')
        for p in pairs:
            if p['names'][0] == f'planar_{LITERAL}_base': p['status'] = 'unexecuted'
        result = assess(configs, runs, pairs)
        self.assertTrue(result['symmetric_mesh_gates_passed'])
        self.assertTrue(result['planar_candidate_gates_passed'])
        self.assertFalse(result['planar_literal_gates_passed'])
        self.assertFalse(result['all_gates_passed'])

    def test_amended_rule_by_mesh_family(self):
        good = [dict(volume=1., bx=.75)]; bad = [dict(volume=3., bx=.75), dict(volume=1., bx=.95)]
        self.assertEqual(mesh_family(dict(jitter=0.)), 'regular')
        self.assertEqual(mesh_family(dict(jitter=.15)), 'planar')
        for c in (dict(jitter=0.), dict(jitter=.15, jitter_mode='columns')):
            self.assertTrue(bx_gate(c, good, good)['passed'])
            self.assertFalse(bx_gate(c, good, bad)['passed'])
        planar = bx_gate(dict(jitter=.15, jitter_mode='planar'), good, bad)
        self.assertFalse(planar['gate_applies'])
        self.assertIsNone(planar['passed'])
        self.assertAlmostEqual(planar['final']['max'], .2)
        self.assertAlmostEqual(planar['final']['L1'], .05)
        self.assertAlmostEqual(bx_errors(bad)['L1'], .05)


if __name__ == '__main__': unittest.main()
