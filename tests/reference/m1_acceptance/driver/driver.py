#!/usr/bin/env python3
"""Detached driver of the 2026-11-17 follow-up campaigns (docs/M1_FULL_VALIDATION_PLAN.md).

A ('iter') is the issue #26 configuration solved without the cached
factorization; B ('step') adds the first trial at 0.95 of the CFL bound.
After the shared preflight each configuration runs, in its own thread and
with its own stop rules, the registered phases: the short bounded stages;
the medium and mean plans and the precondition verdict; the physics and
waves plans and the final verdict. Every step is skipped when its evidence
already exists, so a restarted driver resumes instead of resubmitting.
Everything lives under results/; it is independent of any Claude Code session.

Stop it with: kill $(cat results/followup_campaign_tools_20261117/driver.pid)
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import traceback

T = Path(__file__).resolve().parent
M = T.parents[1]
FROZEN = T/'frozen/scripts'
ADAPTER = M/'results/limiter_campaign_tools_20261113/reana-command.py'
CLIENT = f'python3 {ADAPTER}'
SUBMISSION = M/'results/reana_submission_followup_20261117'
CASES = M/'results/followup_campaign_cases_20261117'
PREFLIGHT_WORKFLOW = 'openmhd-fu-preflight-20261117'
PREFLIGHT = M/'results/reana_remote_followup_preflight_20261117'
DATE = '20261117'
CONFIGS = {
    'iter': dict(study='m1-iterative-bounded', verdict=['--iterative-projection']),
    'step': dict(study='m1-iterative-step-bounded',
                 verdict=['--iterative-projection', '--trial-step-fraction', '0.95']),
}
FINAL = {'finished', 'failed', 'stopped', 'deleted'}
LOGS = [f'outputs/logs/{i:02d}.log' for i in range(8)]
LOCK = threading.Lock()
# One plan uploads at a time. The frozen submit step runs eight uploads of about
# 28 MB each with a 300 s client timeout; two plans at once exceeded it for most
# cases on 2026-11-17, which left them for the recovery step.
UPLOADS = threading.Lock()
STATE = {}


def stamp():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def log(text):
    with LOCK:
        with (T/'driver.log').open('a') as stream:
            stream.write(f'{stamp()} {text}\n')


def save(label, **fields):
    with LOCK:
        STATE.setdefault(label, {}).update(fields, updated_utc=stamp())
        (T/'state.json').write_text(json.dumps(STATE, indent=1)+'\n')


def run(arguments, cwd=FROZEN, timeout=7200):
    done = subprocess.run(arguments, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return done.returncode, done.stdout, done.stderr


def client(*arguments, cwd=M, timeout=900):
    return run([sys.executable, str(ADAPTER), *arguments], cwd=cwd, timeout=timeout)


def status(workflow):
    try:
        code, out, _ = client('list', '--filter', f'name={workflow}', '--json')
        rows = json.loads(out) if code == 0 else None
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return 'unknown'
    if rows is None:
        return 'unknown'
    return rows[0]['status'] if rows else 'missing'


def known_status(workflow, poll=60):
    """A transient client error is never read as a missing workflow."""
    while True:
        state = status(workflow)
        if state != 'unknown':
            return state
        time.sleep(poll)


def wait_for(workflow, poll=120, stall=1800):
    """A final state, or the state of a workflow that never started within `stall` seconds."""
    since = None
    while True:
        state = status(workflow)
        if state in FINAL:
            return state
        if state in ('created', 'missing'):
            since = since or time.monotonic()
            if time.monotonic()-since > stall:
                log(f'{workflow}: still {state} after {stall} s; not waiting longer')
                return state
        else:
            since = None
        time.sleep(poll)


def download(workflow, destination, files):
    destination.mkdir(parents=True, exist_ok=True)
    missing = []
    for name in files:
        for attempt in range(4):
            if (destination/name).exists():
                break
            if attempt:
                time.sleep(60)
            try:
                client('download', '-w', workflow, '-o', str(destination), name, timeout=1800)
            except subprocess.TimeoutExpired:
                pass
        if not (destination/name).exists():
            missing.append(name)
    return missing


def tail(out, err, characters=400):
    return ' '.join((out+err).split())[-characters:]


def preflight():
    state = wait_for(PREFLIGHT_WORKFLOW)
    missing = download(PREFLIGHT_WORKFLOW, PREFLIGHT,
                       ['outputs/preflight.json', 'outputs/execution.json', 'outputs/runtime.json',
                        'outputs/artifacts.sha256.json', 'outputs/vector-potential', *LOGS])
    record = PREFLIGHT/'outputs/execution.json'
    execution = json.loads(record.read_text()) if record.exists() else {}
    passed = (state == 'finished' and not missing and execution.get('status') == 'completed'
              and bool(execution.get('commands')) and all(c['returncode'] == 0 for c in execution['commands']))
    log(f'preflight {state}; commands {[c["returncode"] for c in execution.get("commands", [])]}; '
        f'missing {missing}; passed {passed}')
    save('preflight', workflow=PREFLIGHT_WORKFLOW, status=state, missing=missing, passed=passed)
    return passed


def bounded(label):
    study = CONFIGS[label]['study']
    workflow = f'openmhd-fu-bounded-{label}-{DATE}'
    destination = M/f'results/reana_remote_followup_bounded_{label}_{DATE}'
    if known_status(workflow) == 'missing':
        code, out, err = client('run', '-w', workflow, '-p', f'study={study}', '-p', 'jobs=3',
                                cwd=SUBMISSION, timeout=3600)
        log(f'{label}: submitted {workflow}: exit {code}; {tail(out, err, 200)}')
    state = wait_for(workflow)
    missing = download(workflow, destination,
                       ['outputs/execution.json', 'outputs/runtime.json', 'outputs/artifacts.sha256.json',
                        f'outputs/{study}/gate.json', f'outputs/{study}-raw.tar.gz', *LOGS])
    gate_file = destination/'outputs'/study/'gate.json'
    gate = json.loads(gate_file.read_text()) if gate_file.exists() else {}
    passed = state == 'finished' and gate.get('bounded_blockers_closed') is True
    log(f'{label}: bounded {state}; closed {gate.get("bounded_blockers_closed")}; '
        f'stages {[(s["name"], s["status"]) for s in gate.get("stages", [])]}; missing {missing}')
    save(label, bounded=dict(workflow=workflow, status=state, passed=passed, missing=missing))
    return passed, destination/'outputs'


def plan_directory(label, phase):
    return M/f'results/followup_{label}-{phase}_{DATE}'


def launch(label, phase):
    directory = plan_directory(label, phase)
    name = f'{label}-{phase}'
    if not directory.exists():
        code, out, err = run([sys.executable, 'reana_cases.py', 'prepare', '--directory', str(directory),
                              '--snapshot', str(SUBMISSION), '--preflight', str(PREFLIGHT/'outputs'),
                              '--cases', str(CASES/f'{name}.json'), '--prefix', f'openmhd-fu-{name}'])
        log(f'{name}: prepare exit {code}; {tail(out, err)}')
        if code:
            return False
    with UPLOADS:
        if not (directory/'submission.json').exists():
            # Keep the machine awake for the uploads only.
            code, out, err = run(['caffeinate', '-i', sys.executable, 'reana_cases.py', 'submit', '--directory',
                                  str(directory), '--client', CLIENT], timeout=6*3600)
            log(f'{name}: submit exit {code}; {tail(out, err)}')
            if not (directory/'submission.json').exists():
                return False
        code, out, err = run(['caffeinate', '-i', sys.executable, str(T/'recover_uncertain.py'), str(ADAPTER),
                              str(directory)], timeout=6*3600)
    for line in (out+err).strip().splitlines():
        log(f'{name}: recovery: {line}')
    return True


def watch(label, phases, poll=600):
    last = {}
    while True:
        terminal = True
        for phase in phases:
            try:
                _, out, err = run([sys.executable, 'reana_cases.py', 'check', '--directory',
                                   str(plan_directory(label, phase)), '--client', CLIENT], timeout=3*3600)
                line = (out.strip().splitlines() or [tail('', err, 300)])[-1]
            except subprocess.TimeoutExpired:
                line = 'check timed out'
            if line != last.get(phase):
                log(f'{label}-{phase}: {line}')
                last[phase] = line
            try:
                report = json.loads(line)
            except json.JSONDecodeError:
                report = {}
            terminal = terminal and report.get('all_terminal') is True
        if terminal:
            return
        time.sleep(poll)


def verdict(label, bounded_outputs, name):
    output = M/f'results/followup_{label}_{name}_{DATE}.json'
    if not output.exists():
        directories = [x for phase in ('medium', 'mean', 'physics', 'waves')
                       for x in (f'--{phase}', str(plan_directory(label, phase)))]
        code, out, err = run([sys.executable, 'fanout_campaign_verdict.py', '--snapshot', str(SUBMISSION/'snapshot.json'),
                              '--preflight', str(PREFLIGHT/'outputs'), '--bounded', str(bounded_outputs), *directories,
                              *CONFIGS[label]['verdict'], '--output', str(output)])
        for line in (out+err).strip().splitlines():
            log(f'{label} {name}: {line}')
    return json.loads(output.read_text()) if output.exists() else None


def seconds(etime):
    """`ps` elapsed time [[dd-]hh:]mm:ss in seconds."""
    days, _, clock = etime.rpartition('-')
    parts = [int(x) for x in clock.split(':')]
    while len(parts) < 3:
        parts.insert(0, 0)
    return (int(days) if days else 0)*86400 + parts[0]*3600 + parts[1]*60 + parts[2]


def reap(age=1800, poll=120):
    """Stop upload, start and listing calls of this campaign older than `age` s.

    A 29.5 MB case upload takes minutes. After this computer slept, a call's
    connection is gone and it never returns, and the frozen submit step waits
    for it forever (2026-11-17, 19:10-20:11 UTC). The recovery step uploads
    what is missing to the same workflow and starts it.
    """
    while True:
        try:
            listing = subprocess.run(['ps', '-axo', 'pid=,etime=,command='], capture_output=True, text=True).stdout
            for line in listing.splitlines():
                pid, etime, command = line.split(None, 2)
                words = command.split()
                # The Python process of reana-client, not its `uv tool run` launcher.
                if ('reana-client' in command and 'openmhd-fu-' in command and os.path.basename(words[0]) != 'uv'
                        and any(w in words for w in ('run', 'upload', 'start', 'ls')) and seconds(etime) > age):
                    os.kill(int(pid), signal.SIGTERM)
                    log(f'stopped a client call running {etime}: {" ".join(words[-3:])}')
        except Exception:
            log(f'reaper error: {traceback.format_exc()[-300:]}')
        time.sleep(poll)


def flow(label):
    try:
        passed, bounded_outputs = bounded(label)
        if not passed:
            log(f'{label}: STOP after the short bounded stages')
            save(label, stopped='bounded')
            return
        for phase in ('medium', 'mean'):
            if not launch(label, phase):
                save(label, stopped=f'launch {phase}')
                return
        watch(label, ('medium', 'mean'))
        result = verdict(label, bounded_outputs, 'precondition') or {}
        phases = {k: v['passed'] for k, v in result.get('phases', {}).items()}
        passed = all(phases.get(p) is True for p in ('bounded_short', 'bounded_medium', 'mean'))
        save(label, precondition=dict(passed=passed, phases=phases))
        if not passed:
            log(f'{label}: STOP: the precondition phases did not all pass')
            return
        # The wave matrix holds the longest cases (N256 loops), so it uploads first.
        for phase in ('waves', 'physics'):
            if not launch(label, phase):
                save(label, stopped=f'launch {phase}')
                return
        watch(label, ('physics', 'waves'))
        result = verdict(label, bounded_outputs, 'verdict') or {}
        save(label, verdict=dict(all_passed=result.get('all_registered_phase_checks_passed'),
                                 phases={k: v['passed'] for k, v in result.get('phases', {}).items()}))
        log(f'{label}: done; all registered phase checks passed: {result.get("all_registered_phase_checks_passed")}')
    except Exception:
        log(f'{label}: driver error: {traceback.format_exc()}')
        save(label, error=traceback.format_exc()[-2000:])


def main():
    (T/'driver.pid').write_text(str(os.getpid()))
    log(f'driver start pid {os.getpid()}')
    threading.Thread(target=reap, daemon=True).start()
    try:
        if not preflight():
            log('STOP: the preflight did not pass')
            return
        threads = [threading.Thread(target=flow, args=(label,)) for label in CONFIGS]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        log('driver done')
    except Exception:
        log(f'driver error: {traceback.format_exc()}')
    finally:
        (T/'driver.pid').unlink(missing_ok=True)


if __name__ == '__main__':
    if os.fork():
        sys.exit(0)
    os.setsid()
    if os.fork():
        sys.exit(0)
    devnull = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(devnull, fd)
    main()
