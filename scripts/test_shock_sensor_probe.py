import unittest
from pathlib import Path
import tempfile
from run_shock_sensor_probe import command_for, sensor_observation
from run_m1_wave_loop import HLL_PROFILE


class ControlCommands(unittest.TestCase):
    def test_observation_uses_rest_frame_window_and_correct_factor(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'faces.csv'
            path.write_text('x,nx,ny,omega,method,mass_new,mass_hlld,energy_new,energy_hlld\n1.34,0,1,.125,HlldPressure,.3,.2,.4,.2\n1.1,0,1,1,Hlld,0,0,0,0\n')
            config=dict(case='brio-wu',riemann_solver='hlld-pressure',boost=[2.,-1.,0.],time=.1)
            observation=sensor_observation(path,config)['slow_shock_window_y']
            self.assertEqual(observation['faces'],1)
            self.assertEqual(observation['active'],1)
            self.assertEqual(observation['omega_min'],.125)
            self.assertNotIn('theta_min',observation)
            config['case']='orszag-tang'
            self.assertNotIn('slow_shock_window_y',sensor_observation(path,config))

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
