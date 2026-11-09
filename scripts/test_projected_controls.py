"""Incomplete bounded controls cannot become successful numerical evidence."""
from pathlib import Path
import unittest
from run_projected_controls import analyze, configurations


class ProjectionMeasurements(unittest.TestCase):
    def test_timeout_prefix_is_never_counted_as_a_pass(self):
        configs = configurations()
        runs = {n: {'status': 'timeout', 'summary': {'completed': True}}
                for n in configs}
        result = analyze(Path('/no-snapshots-needed-for-failed-runs'), configs, runs)
        self.assertEqual(result['completed'], 0)
        self.assertFalse(result['full_m1_accepted'])
        self.assertFalse(result['shock_boost']['passed'])
        for family in ['spatial', 'temporal', 'wave_boosts']:
            self.assertTrue(result[family])
            self.assertFalse(any(r['passed'] for r in result[family]))


if __name__ == '__main__':
    unittest.main()
