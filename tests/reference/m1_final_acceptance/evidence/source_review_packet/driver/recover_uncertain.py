"""Finish 'submission uncertain' workflows of one fan-out plan without creating duplicates.

For each uncertain entry whose workflow exists in state 'created': compare the remote
workspace with the expected inputs, upload only missing or wrong-size files to that same
workflow, start it, and annotate submission.json. Anything else is reported, not touched.
Usage: recover_uncertain.py <client-adapter> <plan-directory>
"""
import json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

CLIENT = ['python3', sys.argv[1]]


def client(arguments, cwd=None):
    return subprocess.run([*CLIENT, *arguments], cwd=cwd, capture_output=True, text=True, timeout=900)


directory = Path(sys.argv[2]).resolve()
plan = json.loads((directory/'plan.json').read_text())
state_file = directory/'submission.json'
state = json.loads(state_file.read_text())
for entry in plan['cases']:
    workflow = entry['workflow']
    record = state[workflow]
    if record['status'] != 'submission uncertain' or 'recovery' in record:
        continue
    name = workflow.removesuffix('.1')
    case = directory/entry['directory']
    try:
        status = client(['status', '-w', name, '--json'])
        rows = json.loads(status.stdout) if status.returncode == 0 else []
        if len(rows) != 1:
            print(name, 'NOT RECOVERED: workflow missing or ambiguous; inspect by hand'); continue
        if rows[0]['status'] != 'created':
            print(name, 'left alone: remote status is', rows[0]['status'])
            record['recovery'] = dict(utc=datetime.now(timezone.utc).isoformat(timespec='seconds'),
                                      observed='remote status '+rows[0]['status'], action='none')
            continue
        listing = client(['ls', '-w', name, '--json'])
        if listing.returncode != 0:
            print(name, 'NOT RECOVERED: cannot list workspace'); continue
        remote = {f['name']: int(f['size']) for f in json.loads(listing.stdout)}
        expected = json.loads((case/'reana.yaml').read_text())['inputs']['files']
        wanted = [f for f in expected if remote.get(f) != (case/f).stat().st_size]
        failed = [f for f in wanted if client(['upload', '-w', name, f], cwd=case).returncode != 0]
        if failed:
            print(name, 'NOT RECOVERED: upload failed for', failed); continue
        if client(['start', '-w', name], cwd=case).returncode != 0:
            print(name, 'NOT RECOVERED: start failed'); continue
        record['recovery'] = dict(utc=datetime.now(timezone.utc).isoformat(timespec='seconds'),
                                  observed='workflow existed in state created; missing or incomplete inputs: '+', '.join(wanted),
                                  action='uploaded those files to the same workflow and started it; no new workflow created',
                                  verification='case.py verifies every input hash from payload.json before running')
        print(name, 'recovered:', wanted)
    except (subprocess.TimeoutExpired, ValueError, KeyError, OSError) as error:
        print(name, 'NOT RECOVERED:', type(error).__name__)
state_file.write_text(json.dumps(state, indent=2)+'\n')
print({s: sum(1 for v in state.values() if v['status'] == s) for s in sorted({v['status'] for v in state.values()})})
