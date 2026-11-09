import unittest
from run_shock_symmetry import CANDIDATE, LITERAL, assess, bx_errors, configurations


def passing(configs):
    good = dict(status='completed', positive_and_conservative=True,
                diagnostic_checks=dict(bx=True, seam=True))
    runs = {n: dict(good, diagnostic_checks=dict(good['diagnostic_checks'])) for n in configs}
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
        self.assertTrue(result['all_unchanged_gates_passed'])
        self.assertFalse(result['full_m1_accepted'])
        victim = f'columns_{LITERAL}_base'
        for status in ('failed', 'timeout'):
            bad = assess(configs, {**runs, victim: dict(status=status)}, pairs)
            self.assertFalse(bad['symmetric_mesh_gates_passed'])
            self.assertFalse(bad['all_unchanged_gates_passed'])
        self.assertFalse(assess(configs, {}, pairs)['symmetric_mesh_gates_passed'])
        self.assertFalse(assess(configs, runs, [])['all_unchanged_gates_passed'])

    def test_known_planar_failures_stay_failures_without_hiding_symmetric_result(self):
        configs = configurations(); runs, pairs = passing(configs)
        for label in ('base', 'boost'):
            runs[f'planar_{LITERAL}_{label}'] = dict(status='failed')
            runs[f'planar_{CANDIDATE}_{label}']['diagnostic_checks']['bx'] = False
        for p in pairs:
            if p['names'][0] == f'planar_{LITERAL}_base': p['status'] = 'unexecuted'
        result = assess(configs, runs, pairs)
        self.assertTrue(result['symmetric_mesh_gates_passed'])
        self.assertTrue(result['planar_candidate_stable_and_boost_consistent'])
        self.assertFalse(result['planar_bx_gate_passed'])
        self.assertFalse(result['all_unchanged_gates_passed'])

    def test_bx_error_is_volume_weighted(self):
        cells = [dict(volume=3., bx=.75), dict(volume=1., bx=.95)]
        errors = bx_errors(cells)
        self.assertAlmostEqual(errors['max'], .2)
        self.assertAlmostEqual(errors['L1'], .05)


if __name__ == '__main__': unittest.main()
