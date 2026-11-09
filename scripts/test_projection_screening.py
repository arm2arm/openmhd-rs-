import unittest
from pathlib import Path
from unittest.mock import patch

import run_projection_screening as study


class ScreeningControls(unittest.TestCase):
    def test_registered_packet_compares_exact_and_screened_projection(self):
        configs = study.configurations()
        self.assertEqual(len(configs), 44)
        self.assertEqual({c['kappa'] for c in configs.values()}, {0., .3, 1., 3.})
        for k in study.KAPPAS:
            mine = [c for c in configs.values() if c['kappa'] == k]
            self.assertEqual(len(mine), 21)
            self.assertEqual(sum(c['case'] == 'alfven' for c in mine), 16)
        self.assertTrue(all(c['profile'] == study.PROFILE for c in configs.values()))

    def test_missing_failed_or_low_order_runs_cannot_pass(self):
        configs = study.configurations()
        good = lambda c: dict(status='completed', summary={}, bx=dict(passed=True),
                              errors=dict(final={f: dict(L1=1/c['n']**2) for f in ('B', 'v')}))
        runs = {n: good(c) for n, c in configs.items()}
        boost = dict(B=dict(L1=0.), v=dict(L1=0.), position_max=0., relative_volume_max=0.)
        with (patch.object(study, 'read_cells', return_value=[]),
              patch.object(study, 'boost_comparison', return_value=dict(passed=True)),
              patch.object(study, 'boost_error', return_value=boost)):
            result = study.analyze(Path('/unused'), configs, runs)
            self.assertTrue(all(all(v.values()) for v in result['by_kappa'].values()))
            self.assertFalse(result['full_m1_accepted'])
            for status in ('failed', 'timeout'):
                bad = dict(runs); bad['alfven_k1.0_j0.15_v1.0_n32'] = dict(status=status)
                verdict = study.analyze(Path('/unused'), configs, bad)['by_kappa']
                self.assertFalse(verdict['1.0']['wave_orders_passed'])
                self.assertFalse(verdict['1.0']['all_completed_positive_and_conservative'])
                self.assertTrue(verdict['0.0']['wave_orders_passed'])
            slow = dict(runs); name = 'alfven_k1.0_j0.0_v0.0_n32'
            slow[name] = dict(runs[name], errors=dict(final={f: dict(L1=1/32) for f in ('B', 'v')}))
            self.assertFalse(study.analyze(Path('/unused'), configs, slow)['by_kappa']['1.0']['wave_orders_passed'])
            self.assertFalse(study.analyze(Path('/unused'), configs, {})['by_kappa']['0.0']['boost_pairs_passed'])


if __name__ == '__main__': unittest.main()
