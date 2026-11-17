"""The campaign comparison measures relative differences of registered diagnostics only."""
import json
import math
from pathlib import Path
import tempfile
import unittest

import compare_campaign_runs as compare


def write(directory, runs, summaries):
    directory.mkdir(parents=True)
    (directory/'runs.json').write_text(json.dumps(runs))
    (directory/'checkpoint.json').write_text(json.dumps(dict(summaries=summaries)))


def wave_run(b_l1, steps=10, seconds=5.):
    return dict(status='completed', seconds=seconds, config=dict(case='alfven'),
                summary=dict(steps=steps, rejected_cfl=1, rejected_state=0, rejected_geometry=0, hll_fallbacks=0),
                errors=dict(initial=dict(B=dict(L1=9.)), final=dict(B=dict(L1=b_l1, max=2*b_l1), v=dict(L1=.5))))


class CampaignComparison(unittest.TestCase):
    def test_numeric_leaves_exclude_flags_text_and_nonfinite_values(self):
        value = dict(a=1, b=True, c='pass', d=[2., math.nan, dict(e=3)], f=None, g=math.inf)
        self.assertEqual(dict(compare.leaves(value)), {'a': 1., 'd[0]': 2., 'd[2].e': 3.})

    def test_largest_relative_difference_and_its_location(self):
        result = compare.compare_values(dict(x=1., y=dict(z=4.), only=1.), dict(x=1.5, y=dict(z=4.), new=2.))
        self.assertEqual((result['compared'], result['only_reference'], result['only_candidate']), (2, 1, 1))
        self.assertAlmostEqual(result['largest_relative'], .5/1.5)
        self.assertEqual(result['at'], 'x')
        self.assertEqual(compare.compare_values(dict(x=0.), dict(x=0.))['largest_relative'], 0.)
        self.assertEqual(compare.compare_values({}, {})['at'], None)

    def test_phase_comparison_matches_cases_by_name(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            summary = dict(wave=dict(pairs=[dict(errors=dict(B=dict(L1=1e-12)))], alfven_convergence=[dict(order=1.9)]))
            write(root/'a', dict(one=wave_run(1e-3), two=wave_run(2e-3), gone=wave_run(1.)), summary)
            changed = dict(wave=dict(pairs=[dict(errors=dict(B=dict(L1=1e-12)))], alfven_convergence=[dict(order=1.95)]))
            write(root/'b', dict(one=wave_run(1e-3), two=wave_run(2.2e-3, steps=6, seconds=2.), new=wave_run(1.)), changed)
            result = compare.compare_phase(root/'a', root/'b')
        self.assertEqual(result['cases_compared'], 2)
        self.assertEqual((result['only_reference'], result['only_candidate']), (['gone'], ['new']))
        self.assertEqual(result['cases_with_identical_counters'], 1)
        largest = result['largest_by_section']['final_errors']
        self.assertEqual(largest['case'], 'two')
        self.assertAlmostEqual(largest['largest_relative'], .2e-3/2.2e-3)
        self.assertIsNone(result['largest_by_section']['reference_errors'])
        self.assertAlmostEqual(result['summary_sections']['alfven_convergence']['largest_relative'], .05/1.95)
        self.assertEqual(result['summary_sections']['pairs']['largest_relative'], 0.)
        self.assertEqual(result['case_seconds'], dict(reference=10., candidate=7.))
        self.assertEqual(result['cases']['two']['counters']['steps'], [10, 6])


if __name__ == '__main__':
    unittest.main()
