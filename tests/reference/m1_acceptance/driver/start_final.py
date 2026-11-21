"""Run the registered current-source M1 campaign, independently of the chat session.

Reuses the proven A/B driver and frozen production runners. Only A runs.
Also cancels the other long plan if one has a verified required failure;
observation errors are retried and never trigger cancellation.
"""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import time

import driver
import transport_plan

T = Path(__file__).resolve().parent
M = T.parents[1]
driver.SUBMISSION = M/'results/reana_submission_m1_final_20261121'
driver.CASES = M/'results/m1_final_campaign_cases_20261121'
driver.PREFLIGHT_WORKFLOW = 'openmhd-m1-final-preflight-20261121'
driver.PREFLIGHT = M/'results/reana_remote_m1_final_preflight_20261121'
driver.DATE = '20261121'
driver.CONFIGS = {'iter': driver.CONFIGS['iter']}
# Subprocess timeouts and same-workflow recovery are retained. Do not run the
# historical reaper, which matched all openmhd-fu-* client calls on this host.
driver.reap = lambda: None
transport_plan.install(driver)


def watch(label, phases, poll=60):
    previous = {}
    trigger = None
    while True:
        terminal = True
        checkpoints = {}
        for phase in phases:
            directory = driver.plan_directory(label, phase)
            try:
                _, out, err = driver.run([
                    'python3', 'reana_cases.py', 'check', '--directory', str(directory),
                    '--client', driver.CLIENT], timeout=3*3600)
                line = (out.strip().splitlines() or [driver.tail('', err, 300)])[-1]
            except subprocess.TimeoutExpired:
                line = 'check timed out; retry observation'
            if previous.get(phase) != line:
                driver.log(f'{label}-{phase}: {line}')
                previous[phase] = line
            try:
                report = json.loads((directory/'checkpoint.json').read_text())
            except (OSError, ValueError):
                report = {}
            checkpoints[phase] = report
            terminal = terminal and report.get('all_terminal') is True
            if trigger is None and (report.get('verified_required_failure') is True
                                    or report.get('execution_failures')):
                trigger = dict(utc=driver.stamp(), phase=phase,
                               verified_required_failure=report.get('verified_required_failure'),
                               execution_failures=report.get('execution_failures'),
                               failures=report.get('failures'))
                (T/'first_failure.json').write_text(json.dumps(trigger, indent=1)+'\n')
                driver.log(f'{label}: required failure in {phase}; cancel unnecessary siblings')
        if trigger is not None and not terminal:
            workflows = []
            for phase in phases:
                plan = json.loads((driver.plan_directory(label, phase)/'plan.json').read_text())
                states = checkpoints[phase].get('workflow_states', {})
                workflows += [entry['workflow'] for entry in plan['cases']
                              if states.get(entry['workflow'], {}).get('status') not in driver.FINAL]

            def stop(workflow):
                # Recheck authoritative status; a missing observation alone is
                # never a reason to stop a workflow in a healthy campaign.
                state = driver.status(workflow)
                if state in driver.FINAL or state in ('missing', 'unknown'):
                    return dict(workflow=workflow, observed=state, requested_stop=False)
                code, out, err = driver.client('stop', '-w', workflow)
                return dict(workflow=workflow, observed=state, requested_stop=True,
                            returncode=code, detail=driver.tail(out, err))

            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                actions = list(pool.map(stop, workflows))
            with (T/'cancellation.jsonl').open('a') as stream:
                stream.write(json.dumps(dict(utc=driver.stamp(), trigger=trigger, actions=actions))+'\n')
        if terminal:
            return
        time.sleep(poll)


driver.watch = watch

if __name__ == '__main__':
    pidfile = T/'driver.pid'
    if pidfile.exists():
        try:
            os.kill(int(pidfile.read_text()), 0)
        except (OSError, ValueError):
            pass
        else:
            raise SystemExit('An existing final-campaign driver is still running')
    if os.fork():
        raise SystemExit(0)
    os.setsid()
    if os.fork():
        raise SystemExit(0)
    null = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(null, fd)
    # Keep the client host available for supervision, not only uploads.
    subprocess.Popen(['caffeinate', '-i', '-w', str(os.getpid())],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)
    driver.log('Final current-source campaign: A only; no change to registered cases or gates')
    driver.main()
