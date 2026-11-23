"""Durable host operation receipt; no automatic retry, recovery or workflow control."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def publish(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def run(label, argv, cwd, timeout=300):
    destination = Path(__file__).resolve().parent / 'commands' / label
    destination.mkdir(parents=True)
    row = dict(schema='openmhd.galaxy-python-host-command.v1', argv=argv, cwd=str(cwd),
               started_utc=now(), finished_utc=None, outcome='pending_launch', returncode=None,
               interpreter=dict(executable=sys.executable, version=sys.version,
                                optimized=sys.flags.optimize, sha256=digest(Path(sys.executable))),
               source_sha256=digest(Path(__file__)), allowlisted_environment={n: os.environ.get(n) for n in ('PYTHONDONTWRITEBYTECODE', 'PYTHONHASHSEED', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'RAYON_NUM_THREADS', 'PYTHONOPTIMIZE')}, pid=None, timeout_seconds=timeout,
               timeout_scope='host direct-process wait; no automatic mutation retry')
    publish(destination / 'command.json', row)
    start = time.monotonic()
    try:
        with (destination / 'stdout.txt').open('xb') as out, (destination / 'stderr.txt').open('xb') as err:
            process = subprocess.Popen(argv, cwd=cwd, stdout=out, stderr=err)
            row.update(pid=process.pid, outcome='running')
            publish(destination / 'command.json', row)
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                row.update(outcome='host_wait_timeout_unsettled', external_evidence_required=True)
                raise
            row.update(returncode=code, outcome='success' if code == 0 else 'nonzero')
    except BaseException as error:
        row['error_type'] = type(error).__name__
        if row['outcome'] == 'running':
            row.update(outcome='interrupted_or_unknown_closure', external_evidence_required=True)
        elif row['outcome'] == 'pending_launch':
            row['outcome'] = 'start_failed'
        raise
    finally:
        row.update(finished_utc=now(), duration_seconds=time.monotonic() - start)
        for channel in ('stdout', 'stderr'):
            path = destination / (channel + '.txt')
            if path.exists():
                row[channel] = dict(path=str(path), sha256=digest(path), bytes=path.stat().st_size,
                                    closure='observed bytes; see operation outcome')
        publish(destination / 'command.json', row)
    print(json.dumps(dict(label=label, pid=row['pid'], outcome=row['outcome'],
                          returncode=row['returncode'], started_utc=row['started_utc'], finished_utc=row['finished_utc'])))
    return row['returncode']


if __name__ == '__main__':
    # label, working directory, argv; all arguments are public/credential-free.
    sys.exit(run(sys.argv[1], sys.argv[3:], Path(sys.argv[2]).resolve()))
