"""Foreground, reboot-resumable host supervision of the existing M1 campaign.

Run from its live results/ directory with --launch-agent PATH --orca PATH.
Scientific source, cases, gates and workflow identities remain unchanged.
Successful completion notification removes this task-specific login plist.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import start_final


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--launch-agent', required=True, type=Path)
    parser.add_argument('--orca', required=True)
    args = parser.parse_args()
    directory = Path(__file__).resolve().parent
    repository = directory.parents[1]
    if (directory/'completion_notification.json').exists():
        args.launch_agent.unlink(missing_ok=True)
        return
    if (directory/'service_attention.json').exists():
        print('Saved service finding requires coordinator inspection; not restarting blindly', flush=True)
        return
    pidfile = directory/'driver.pid'
    if pidfile.exists():
        try:
            os.kill(int(pidfile.read_text()), 0)
        except ProcessLookupError:
            pass
        else:
            raise RuntimeError('An existing campaign driver is active; refusing duplicate supervision')
    if shutil.which('caffeinate'):
        subprocess.Popen(['caffeinate', '-i', '-w', str(os.getpid())],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    start_final.driver.log('Resuming existing campaign with reboot-resumable foreground supervision')
    start_final.driver.main()
    # Do not consume Orca mail. This only reports the stopped/finished local
    # campaign state to its existing coordinator; no automatic M1 acceptance.
    result = subprocess.run([
        sys.executable, str(directory/'wake_on_completion.py'), '--directory', str(directory),
        '--repository', str(repository), '--run', 'run_b6713cc700cf', '--orca', args.orca])
    if result.returncode == 0 and (directory/'completion_notification.json').exists():
        args.launch_agent.unlink(missing_ok=True)
        return
    # The notifier preserves every response. An unknown delivery outcome must
    # be inspected, rather than replayed as a new message after every restart.
    (directory/'service_attention.json').write_text(json.dumps(dict(
        kind='Completion notification requires inspection', notifier_exit=result.returncode,
        directory=str(directory), action='Inspect completion_send_attempt_* receipts before retrying.'), indent=1)+'\n')


if __name__ == '__main__':
    main()
