"""Notify the Orca coordinator when the existing REANA driver exits.

Reads only local driver state. It never consumes Orca mail, submits a workflow,
accepts M1, or restarts a process. The long-running scientific work remains in
the already launched gated REANA driver. This is an orchestration source record.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


def read(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--repository', required=True, type=Path)
    parser.add_argument('--run', required=True)
    parser.add_argument('--orca', required=True)
    args = parser.parse_args()
    directory, repository = args.directory.resolve(), args.repository.resolve()
    pidfile = directory/'completion_watch.pid'
    if pidfile.exists():
        old = int(pidfile.read_text())
        try:
            os.kill(old, 0)
        except ProcessLookupError:
            pass
        else:
            raise SystemExit('Completion notification is already armed')
    if (directory/'completion_notification.json').exists():
        raise SystemExit('Completion notification was already sent')
    pidfile.write_text(str(os.getpid()))
    if shutil.which('caffeinate'):
        subprocess.Popen(['caffeinate', '-i', '-w', str(os.getpid())],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        while True:
            driver_pidfile = directory/'driver.pid'
            running = driver_pidfile.exists()
            if running:
                try:
                    os.kill(int(driver_pidfile.read_text()), 0)
                except ProcessLookupError:
                    running = False
            if not running:
                break
            time.sleep(30)
        state = read(directory/'state.json')
        verdict_path = repository/'results/followup_iter_verdict_20261121.json'
        verdict = read(verdict_path)
        passed = bool(verdict and verdict.get('all_registered_phase_checks_passed') is True)
        context = dict(
            kind='Existing gated REANA driver ended; coordinator continuation required, not M1 acceptance.',
            utc=datetime.now(timezone.utc).isoformat(), driver_state=state,
            all_registered_phase_checks_passed=passed, verdict_path=str(verdict_path),
            live_directory=str(directory), repository=str(repository))
        (directory/'completion_state.json').write_text(json.dumps(context, indent=1)+'\n')
        body = (
            'Continue the owner-authorized M1 task automatically; do not ask routine questions. '
            'The detached current-source REANA driver has ended. This is a local-state notification, '
            'not an assertion of acceptance. Inspect actual driver logs/state and recover missing '
            'observations in the same workflows. If required gates failed, investigate and fix before '
            'launching more long work. If all gates passed, archive/verify the 214 new receipts, source '
            'and binary identities, run independent fresh reductions (or prove every reused input '
            'byte-identical), and obtain the final output review from dispatch ctx_7e6d6153b3d9. '
            'Then write a scoped M1 acceptance record only if every condition passes. '
            'Read docs/M1_FINAL_ACCEPTANCE_PLAN.md and docs/M1_FINAL_AI_REVIEW.md. '
            'Frozen development source is 2bdcea0; scientific files must remain unchanged. '
            'The parent verifier now handles the separately hashed reviewer subpacket.\n\n'
            + json.dumps(context, indent=1))
        body_path = directory/'completion_message.txt'
        body_path.write_text(body+'\n')
        command = [args.orca, 'orchestration', 'send', '--to', 'run:'+args.run,
                   '--subject', 'M1 current-source campaign ready for continuation' if passed
                   else 'M1 current-source campaign stopped; investigate',
                   '--type', 'status', '--body-file', str(body_path), '--json']
        # A transient runtime_unavailable cannot deliver the message. Preserve
        # receipts and retry that explicit no-delivery state only. Unknown
        # outcomes remain visible instead of silently duplicating messages.
        attempt = 0
        while True:
            attempt += 1
            try:
                result = subprocess.run(command, cwd=repository, capture_output=True, text=True, timeout=60)
                receipt = dict(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
            except subprocess.TimeoutExpired as error:
                receipt = dict(error='notification_timeout', detail=str(error))
            (directory/f'completion_send_attempt_{attempt:03d}.json').write_text(json.dumps(receipt, indent=1)+'\n')
            if receipt.get('returncode') == 0:
                payload = json.loads(receipt['stdout'])
                if payload.get('ok') is True:
                    (directory/'completion_notification.json').write_text(json.dumps(receipt, indent=1)+'\n')
                    return
            if 'runtime_unavailable' not in receipt.get('stdout', '')+receipt.get('stderr', ''):
                raise RuntimeError('Notification not confirmed; inspect the saved attempt receipt')
            time.sleep(30)
    finally:
        pidfile.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
