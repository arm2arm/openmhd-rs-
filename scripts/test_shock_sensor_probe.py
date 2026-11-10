import unittest
from run_shock_sensor_probe import command_for
from run_m1_wave_loop import HLL_PROFILE


class ControlCommands(unittest.TestCase):
    def test_existing_flux_and_observation_options_cannot_leak_into_trial(self):
        old=['old-binary','--case','brio-wu','--n','1024','--time','.1',
             '--riemann','hll','--threads','1','--snapshot-stride','64',
             '--trace-frozen-rates','--output','old-destination','--accelerated-projection',
             '--projection-screening','1']
        trial=command_for(old,'new-binary','new-destination',dict(profile=HLL_PROFILE,riemann_solver='hlld-shock'))
        self.assertEqual(trial,['new-binary','--case','brio-wu','--n','1024','--time','.1',
             '--accelerated-projection','--projection-screening','1','--riemann','hlld-shock',
             '--threads','2','--output','new-destination'])
        historical=command_for(old,'binary','destination',dict(profile=HLL_PROFILE))
        self.assertNotIn('--riemann',historical)
        for option,value in [('--n','1024'),('--time','.1'),('--projection-screening','1')]:
            self.assertEqual(historical[historical.index(option)+1],value)


if __name__=='__main__':unittest.main()
