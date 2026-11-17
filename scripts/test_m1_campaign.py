import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import run_m1_campaign as campaign


class CampaignGate(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'linux', 'Linux campaign/process groups')
    def test_calibration_failure_cancels_sibling_and_preserves_both_outcomes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);out=root/'results';started=threading.Event();commands=[]
            for name in ('Cargo.toml','Cargo.lock','rust-toolchain.toml'):
                (root/name).write_text('provenance fixture')
            binary=root/'target/release/vector-potential';binary.parent.mkdir(parents=True)
            binary.write_bytes(b'preflight executable fixture')
            digest=hashlib.sha256(binary.read_bytes()).hexdigest()
            def stage(command, log, cap, cancel=None):
                commands.append(command)
                dest=Path(command[command.index('--output-dir')+1]);dest.mkdir()
                if dest.name=='bounded':
                    (dest/'gate.json').write_text(json.dumps(dict(full_matrix_precondition_met=True,
                        provenance=dict(riemann_solver='hlld-pressure'))))
                    return 0
                if dest.name=='mean':
                    (dest/'summary.json').write_text('{}')
                    return 0
                if dest.name=='calibration_wave':
                    self.assertTrue(started.wait(2), 'Sibling did not start')
                    return 101
                self.assertEqual(dest.name,'calibration_vortex')
                started.set()
                self.assertTrue(cancel.wait(2), 'Sibling failure did not trigger cancellation')
                raise InterruptedError('Sibling phase failed; stage cancelled')
            args=['campaign','--output-dir',str(out),'--riemann','hlld-pressure','--jobs','24']
            with patch.object(campaign,'ROOT',root), patch.object(campaign,'run_stage',side_effect=stage), \
                    patch.object(campaign,'mean_checks',return_value={'test_fixture':True}), \
                    patch.object(campaign.subprocess,'check_output',return_value='fixture'), \
                    patch.object(sys,'argv',args):
                self.assertEqual(campaign.main(),1)
            report=json.loads((out/'campaign.json').read_text())
            phases={r['name']:r for r in report['phases']}
            self.assertEqual(set(phases),{'bounded','mean','calibration_wave','calibration_vortex'})
            self.assertEqual(phases['calibration_wave']['returncode'],101)
            self.assertEqual(phases['calibration_wave']['status'],'failed')
            self.assertEqual(phases['calibration_vortex']['status'],'cancelled')
            self.assertFalse(report['all_new_candidate_gates_passed'])
            self.assertTrue(report['source_and_binary_unchanged'])
            for command in commands:
                if Path(command[command.index('--output-dir')+1]).name!='bounded':
                    self.assertEqual(command[command.index('--reuse-binary-sha256')+1],digest)

    @unittest.skipUnless(sys.platform == 'linux', 'Linux process-group cancellation')
    def test_cancelled_stage_kills_its_child_process(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);ready=root/'ready.json';cancel=threading.Event()
            program=('import json,os,subprocess,sys,time; from pathlib import Path; '
                     'child=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"]); '
                     f'p=Path({str(root/"writing.json")!r}); '
                     'p.write_text(json.dumps([os.getpid(),child.pid])); '
                     f'p.replace({str(ready)!r}); time.sleep(30)')
            def interrupt():
                deadline=time.monotonic()+2
                while not ready.exists() and time.monotonic()<deadline:
                    time.sleep(.01)
                cancel.set()
            thread=threading.Thread(target=interrupt);thread.start()
            try:
                with (root/'stage.log').open('w') as log:
                    with self.assertRaises(InterruptedError):
                        campaign.run_stage([sys.executable,'-c',program],log,5,cancel)
            finally:
                thread.join()
            pids=json.loads(ready.read_text())
            def alive(pid):
                try:return Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1][0]!='Z'
                except FileNotFoundError:return False
            deadline=time.monotonic()+1
            while any(alive(pid) for pid in pids) and time.monotonic()<deadline:
                time.sleep(.01)
            self.assertFalse(any(alive(pid) for pid in pids))

    def test_memory_budget_and_missing_measurements(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'memory.json'
            p.write_text(json.dumps(dict(returncode=0,peak_process_rss_bytes=1024**3)))
            self.assertEqual(campaign.memory_bytes(p), 1024**3)
            budget=campaign.worker_budget(campaign.memory_bytes(p),24)
            self.assertEqual(budget['workers'],6)
            self.assertEqual(budget['threads_per_case'],4)
            self.assertLessEqual(budget['workers']*budget['estimated_n256_peak_bytes']+budget['reserved_bytes'],64e9)
            self.assertEqual(campaign.worker_budget(1024**3,2)['workers'],2)
            p.write_text(json.dumps(dict(returncode=1,peak_process_rss_bytes=1024**3)))
            with self.assertRaises(ValueError): campaign.memory_bytes(p)
        for peak in (0, 8_000_000_000):
            with self.assertRaises(ValueError): campaign.worker_budget(peak,24)

    def test_parallelism_rejects_oversubscription(self):
        for jobs,threads in ((24,1),(3,8),(2,12),(1,24)):
            campaign.validate_parallelism(jobs,threads)
        for jobs,threads in ((24,2),(3,9),(0,1),(1,25)):
            with self.assertRaises(ValueError):campaign.validate_parallelism(jobs,threads)

    @unittest.skipUnless(sys.platform == 'linux', 'Linux wait4 measurement')
    def test_measurement_wrapper_records_success_failure_and_memory(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'memory.json'
            command=[sys.executable,str(campaign.SCRIPTS/'measure_process.py'),'--output',str(p),'--',sys.executable]
            subprocess.run([*command,'-c','x=bytearray(16*1024*1024)'],check=True)
            self.assertGreaterEqual(campaign.memory_bytes(p),16*1024*1024)
            self.assertEqual(subprocess.run([*command,'-c','raise SystemExit(7)']).returncode,7)
            with self.assertRaises(ValueError): campaign.memory_bytes(p)

    def test_mean_gate_requires_candidate_refinement_observations(self):
        summary=dict(runs={str(i):dict(status='completed',positive_and_conservative=True) for i in range(24)},
                     pairs=[dict(status='pass') for _ in range(12)],mean_refinement=[])
        self.assertFalse(campaign.mean_checks(summary)['mean_refinement_measured'])
        for jitter in (0.,.15):
            for variable,coordinates in (('n',[8,16,32,64]),('dt',[.001,.0005,.00025])):
                summary['mean_refinement'].append(dict(profile=campaign.CANDIDATE,jitter=jitter,variable=variable,
                    values=[[x,0.] for x in coordinates],successive_B_L1_orders=[None]*(len(coordinates)-1)))
        self.assertTrue(all(campaign.mean_checks(summary).values()))
        for replacement in (None,float('nan'),-1.):
            bad=copy.deepcopy(summary);bad['mean_refinement'][0]['values'][0][1]=replacement
            self.assertFalse(campaign.mean_checks(bad)['mean_refinement_measured'])
        bad=copy.deepcopy(summary);bad['mean_refinement'][0]['profile']='paper-global-v2'
        self.assertFalse(campaign.mean_checks(bad)['mean_refinement_measured'])
        bad=copy.deepcopy(summary);bad['mean_refinement'].pop()
        self.assertFalse(campaign.mean_checks(bad)['mean_refinement_measured'])

    def test_full_wave_gate_cannot_hide_missing_or_failed_measurements(self):
        summary=dict(runs={str(i):dict(status='completed',positive_and_conservative=True) for i in range(112)},
                     pairs=[dict(status='pass under both reported normalizations') for _ in range(48)],
                     alfven_convergence=[dict(gate='pass') for _ in range(8)],
                     temporal=[dict(status='completed',errors=dict(B=dict(L1=.001))) for _ in range(12)])
        self.assertTrue(all(campaign.wave_checks(summary,112,48,full=True).values()))
        for field in ('runs','pairs','alfven_convergence','temporal'):
            bad=copy.deepcopy(summary)
            if field=='runs':bad[field].pop('0')
            else:bad[field].pop()
            self.assertFalse(all(campaign.wave_checks(bad,112,48,full=True).values()))
        bad=copy.deepcopy(summary);bad['alfven_convergence'][0]['gate']='fail'
        self.assertFalse(campaign.wave_checks(bad,112,48,full=True)['spatial_gates'])
        bad=copy.deepcopy(summary);bad['runs']['0']['status']='timeout'
        self.assertFalse(campaign.wave_checks(bad,112,48,full=True)['all_completed'])
        bad=copy.deepcopy(summary);bad['pairs'][0]['status']='fail'
        self.assertFalse(campaign.wave_checks(bad,112,48,full=True)['boost_pairs'])


if __name__=='__main__': unittest.main()
