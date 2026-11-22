import unittest
from run_shock_repro import assess, configurations


class ShortShockScreen(unittest.TestCase):
    def test_incomplete_timeout_and_failed_cases_cannot_pass(self):
        configs=configurations('test-profile')
        good=dict(status='completed',positive_and_conservative=True,diagnostic_checks_passed=True)
        runs={n:dict(good) for n in configs}
        pairs=[dict(status='pass'),dict(status='pass')]
        result=assess(configs,runs,pairs)
        self.assertTrue(result['short_screen_passed'])
        self.assertFalse(result['full_m1_accepted'])
        for status in ('failed','timeout'):
            bad={**runs,next(iter(runs)):dict(status=status)}
            self.assertFalse(assess(configs,bad,pairs)['short_screen_passed'])
        self.assertFalse(assess(configs,{},pairs)['short_screen_passed'])
        self.assertFalse(assess({}, {}, [])['short_screen_passed'])

    def test_stability_does_not_hide_diagnostic_or_boost_failures(self):
        configs=configurations('test-profile')
        runs={n:dict(status='completed',positive_and_conservative=True,diagnostic_checks_passed=True) for n in configs}
        pairs=[dict(status='pass'),dict(status='pass')]
        runs[next(iter(runs))]['diagnostic_checks_passed']=False
        result=assess(configs,runs,pairs)
        self.assertTrue(result['stability_and_budget'])
        self.assertFalse(result['short_screen_passed'])
        self.assertFalse(assess(configs,runs,pairs[:1])['boost_checks'])
        pairs[0]['status']='fail'
        self.assertFalse(assess(configs,runs,pairs)['boost_checks'])


if __name__=='__main__':unittest.main()
