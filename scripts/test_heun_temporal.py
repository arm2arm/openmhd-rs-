"""Scientific measurement guards for the bounded time comparison."""
from pathlib import Path
import unittest

from run_heun_temporal import analyze, configurations, differences


class TimeMeasurements(unittest.TestCase):
    def test_missing_runs_cannot_be_measured_as_zero(self):
        configs, ladders, pairs = configurations()
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            analyze(Path('.'), configs, ladders, pairs, {})
        self.assertEqual(len(configs), 40)
        self.assertEqual(len(ladders), 8)
        self.assertEqual(len(pairs), 8)

    def test_auxiliary_factorial_comparisons_are_matched(self):
        configs, ladders, pairs = configurations(auxiliary=True)
        self.assertEqual(len(configs), 80)
        self.assertEqual(len(ladders), 16)
        self.assertEqual(len(pairs), 16)
        for names in ladders:
            rows = [configs[n] for n in names]
            self.assertEqual(len({(c['profile'], c['limited'], c['jitter'], c['parallel'], c['n'], c['target']) for c in rows}), 1)
            self.assertEqual([c['dt'] for c in rows], [.0004, .0002, .0001, .000025])
        for base, boosted in pairs:
            a, b = configs[base], configs[boosted]
            self.assertEqual({k:v for k,v in a.items() if k not in ('name','boost')},
                             {k:v for k,v in b.items() if k not in ('name','boost')})

    def test_vector_norm_and_scalar_time_errors(self):
        a = dict(volume=1., x=.5, y=.5, bx=3., by=4., bz=0., vx=0., vy=0., vz=0.,
                 ax=0., ay=0., az=2., phi=-.2)
        b = {**a, 'bx': 0., 'by': 0., 'az': 0., 'phi': 0.}
        errors = differences([a], [b])
        self.assertEqual(errors['B']['L1'], 5.)
        self.assertEqual(errors['A']['L1'], 2.)
        self.assertEqual(errors['phi']['L1'], .2)
        self.assertEqual(errors['v']['L1'], 0.)
        with self.assertRaisesRegex(ValueError, 'geometry'):
            differences([a], [{**b, 'x': .6}])
        with self.assertRaisesRegex(ValueError, 'count'):
            differences([a], [])


if __name__ == '__main__':
    unittest.main()
