#!/usr/bin/env python3
"""Bounded accepted-state trace/parity investigation for #24, on REANA only."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

import remote


def main():
    if sys.platform != 'linux':
        raise ValueError('Run on the REANA Linux backend')
    report = dict(status='running', started_utc=datetime.now(timezone.utc).isoformat(),
                  snapshot_sha256=remote.sha(remote.WORK/'snapshot.json'), commands=[],
                  scientific_acceptance=False)
    dest = remote.OUTPUT/'trace_execution.json'
    env = remote.environment()
    checks = [
        ['cargo', 'fmt', '--check'],
        ['cargo', 'clippy', '--all-targets', '--all-features', '--locked', '--', '-D', 'warnings'],
        ['cargo', 'test', '--release', '--workspace', '--all-targets', '--locked'],
        ['cargo', 'build', '--release', '--workspace', '--locked'],
        [sys.executable, '-m', 'unittest', 'discover', '-s', 'scripts', '-p', 'test_*.py'],
        [sys.executable, 'scripts/check_m0_spec.py'],
        [sys.executable, 'scripts/check_reference_packet.py'],
    ]
    try:
        remote.verify_source(json.loads((remote.WORK/'snapshot.json').read_text()))
        for index, command in enumerate(checks):
            path = remote.OUTPUT/f'check_{index:02d}.log'
            start = time.monotonic()
            with path.open('w') as log:
                done = subprocess.run(command, cwd=remote.SOURCE, env=env,
                                      stdout=log, stderr=subprocess.STDOUT, timeout=900)
            report['commands'].append(dict(command=command, returncode=done.returncode,
                                            seconds=time.monotonic()-start, log_sha256=remote.sha(path)))
            remote.dump(dest, report)
            print(command, done.returncode, flush=True)
            if done.returncode:
                raise ValueError('Preflight command failed')
        binary = remote.SOURCE/'target/release/vector-potential'
        invalid = []
        for value in ('0', '-1', 'abc'):
            done = subprocess.run([str(binary), '--snapshot-stride', value], cwd=remote.SOURCE,
                                  env=env, capture_output=True, text=True, timeout=10)
            invalid.append(dict(value=value, returncode=done.returncode, stderr=done.stderr))
            if done.returncode == 0 or 'invalid positive snapshot stride' not in done.stderr:
                raise ValueError('Snapshot stride parser accepted an invalid value')
        report['invalid_stride_checks'] = invalid
        command = [sys.executable, str(remote.SOURCE/'scripts/run_column_boost_repro.py'),
                   '--binary', str(binary), '--snapshot-stride', '64',
                   '--output-dir', str(remote.OUTPUT/'column_trace')]
        with (remote.OUTPUT/'column_trace.log').open('w') as log:
            done = subprocess.run(command, cwd=remote.WORK, env=env,
                                  stdout=log, stderr=subprocess.STDOUT, timeout=900)
        report['trace_returncode'] = done.returncode
        report['instrumented_binary_sha256'] = remote.sha(binary)
        remote.verify_source(json.loads((remote.WORK/'snapshot.json').read_text()))
        if done.returncode:
            raise ValueError('Accepted-state trace/parity investigation failed')
        report['status'] = 'completed'
    except Exception as error:
        report.update(status='failed', error=f'{type(error).__name__}: {error}')
    finally:
        report['ended_utc'] = datetime.now(timezone.utc).isoformat()
        remote.dump(dest, report)
        remote.dump(remote.OUTPUT/'trace_artifacts.sha256.json', {
            str(p.relative_to(remote.OUTPUT)): remote.sha(p)
            for p in sorted(remote.OUTPUT.rglob('*')) if p.is_file()})
    return 0 if report['status'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
