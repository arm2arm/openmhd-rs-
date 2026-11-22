"""Host-only resumable transport of immutable per-case REANA inputs.

Never calls `run` on an existing workflow. Every uncertain mutation is followed
by authoritative observation; retries upload only missing/wrong-size inputs to
the same created workflow. The frozen case.py checks every input hash remotely.
This module changes no scientific runner, specification, resource or threshold.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading


LOCK = threading.Lock()
CLIENTS = set()
STOP = threading.Event()


def cancel_clients():
    STOP.set()
    with LOCK:
        for pid in tuple(CLIENTS):
            try:
                os.killpg(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def transfer(directory, adapter, log):
    plan = json.loads((directory/'plan.json').read_text())
    state_path = directory/'submission.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    for entry in plan['cases']:
        case = directory/entry['directory']
        assert sha(case/'payload.json') == entry['payload_sha256']
        assert sha(case/'reana.yaml') == entry['workflow_sha256']
        for name, digest in json.loads((case/'payload.json').read_text())['input_sha256'].items():
            assert sha(case/name) == digest, (entry['workflow'], name)
        state.setdefault(entry['workflow'], dict(status='submission pending'))

    def save(workflow, **fields):
        with LOCK:
            state[workflow].update(fields)
            temporary = state_path.with_suffix('.tmp')
            temporary.write_text(json.dumps(state, indent=2)+'\n')
            temporary.replace(state_path)
            with (directory/'transport.jsonl').open('a') as stream:
                stream.write(json.dumps(dict(workflow=workflow, **fields))+'\n')

    def client(arguments, cwd=None, timeout=900):
        with LOCK:
            if STOP.is_set():
                raise InterruptedError('Host transport stopped')
            process = subprocess.Popen([sys.executable, str(adapter), *arguments], cwd=cwd,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, start_new_session=True)
            CLIENTS.add(process.pid)
        try:
            stdout, _ = process.communicate(timeout=timeout)
            # Do not retain arbitrary SDK errors or credentials in host logs.
            return process.returncode, stdout
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            return None, ''
        finally:
            with LOCK:
                CLIENTS.discard(process.pid)

    def one(entry):
        workflow = entry['workflow']
        base = workflow.removesuffix('.1')
        case = directory/entry['directory']
        expected = json.loads((case/'reana.yaml').read_text())['inputs']['files']
        attempted_create = False
        while not STOP.is_set():
            stamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
            try:
                code, out = client(['list', '--filter', 'name='+base, '--json'])
                if code != 0:
                    raise ValueError('workflow observation unavailable')
                rows = [row for row in json.loads(out) if row['name'] == base]
                if not rows:
                    if attempted_create:
                        # A failed/uncertain create is never blindly replayed.
                        save(workflow, status='submission uncertain', transport_utc=stamp,
                             transport_observation='created workflow not visible; coordinator inspection required')
                        raise RuntimeError('Create attempt has no authoritative workflow identity: '+workflow)
                    attempted_create = True
                    save(workflow, status='submission uncertain', transport_utc=stamp,
                         transport_observation='authoritatively absent; creating this exact planned identity once')
                    client(['create', '-w', base, '-f', 'reana.yaml'], cwd=case)
                    continue
                if len(rows) != 1 or str(rows[0]['run_number']) != '1':
                    raise RuntimeError('Ambiguous workflow generation: '+workflow)
                remote_status = rows[0]['status']
                if remote_status != 'created':
                    save(workflow, status='submitted', transport_utc=stamp,
                         transport_observation='authoritative remote status '+remote_status)
                    log(workflow+': transport observed '+remote_status)
                    return
                code, out = client(['ls', '-w', workflow, '--json'])
                if code != 0:
                    raise ValueError('workspace observation unavailable')
                remote = {row['name']: int(row['size']) for row in json.loads(out)}
                wanted = [name for name in expected if remote.get(name) != (case/name).stat().st_size]
                if wanted:
                    save(workflow, status='submission uncertain', transport_utc=stamp,
                         transport_observation='created; completing '+str(len(wanted))+' input files')
                    client(['upload', '-w', workflow, *wanted], cwd=case, timeout=1800)
                    # Observe status and listing again even after timeout/error.
                    continue
                save(workflow, status='submission uncertain', transport_utc=stamp,
                     transport_observation='all input sizes match; starting same workflow; case.py verifies all hashes')
                code, _ = client(['start', '-w', workflow], cwd=case)
                # A failed/uncertain start is checked before any next action.
                STOP.wait(2 if code == 0 else 30)
            except (ValueError, KeyError, OSError) as error:
                save(workflow, status='submission uncertain', transport_utc=stamp,
                     transport_observation=type(error).__name__+'; retrying observation only')
                STOP.wait(30)
        raise RuntimeError('Host transport stopped')

    with ThreadPoolExecutor(max_workers=8) as pool:
        try:
            list(pool.map(one, plan['cases']))
        except BaseException:
            cancel_clients()
            raise


def install(driver):
    def launch(label, phase):
        directory = driver.plan_directory(label, phase)
        name = label+'-'+phase
        if not directory.exists():
            code, out, err = driver.run([
                sys.executable, 'reana_cases.py', 'prepare', '--directory', str(directory),
                '--snapshot', str(driver.SUBMISSION), '--preflight', str(driver.PREFLIGHT/'outputs'),
                '--cases', str(driver.CASES/(name+'.json')), '--prefix', 'openmhd-fu-'+name])
            driver.log(name+': prepare exit '+str(code)+'; '+driver.tail(out, err))
            if code:
                return False
        with driver.UPLOADS:
            transfer(directory, driver.ADAPTER, driver.log)
        return True
    driver.launch = launch
