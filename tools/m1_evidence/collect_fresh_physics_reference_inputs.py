"""Collect actual fresh REANA inputs; never submit, evolve or accept M1.

Shared helpers implement coherent metadata capture, verified byte copying and
durable credential-redacted command receipts. Numerical adapters are unchanged.
"""
if not __debug__:
    raise RuntimeError("M1 evidence tools require assertions: optimized Python is forbidden")

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shlex
import signal
import subprocess
import sys
import threading
import time

SNAPSHOT = 'b67ce03779a194099983b7ff07c0cafed23e9ea3a9051047492d072255e0160f'
BINARY = '18afcf0308338e2ea0ea7ef5e03dba46af9d7025f3ccf4a6a48ebbfe800d0725'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def utc():
    return datetime.now(timezone.utc).isoformat()


def runtime_info():
    return dict(executable=sys.executable, version=sys.version,
                implementation=platform.python_implementation(),
                optimization=sys.flags.optimize, assertions_enabled=__debug__,
                pythonoptimize=os.environ.get('PYTHONOPTIMIZE'),
                platform=platform.platform())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=1, allow_nan=False) + '\n')
    temporary.replace(path)


def relative_path(name):
    p = PurePosixPath(name)
    require(bool(p.parts) and not p.is_absolute() and '..' not in p.parts
            and str(p) == name and '\\' not in name, 'Unsafe relative evidence path')
    return Path(*p.parts)


def generation(path):
    st = Path(path).stat()
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


class CaptureChanged(RuntimeError):
    pass


def read_once(path):
    """One byte read supplies parsing, hashing and copying; stat detects replacement."""
    before = generation(path)
    data = Path(path).read_bytes()
    after = generation(path)
    if before != after:
        raise CaptureChanged('Metadata changed while read: ' + str(path))
    return data, after


class MetadataCapture:
    def __init__(self, data, generations, attempts, base_paths, expand):
        self.data, self.generations, self.attempts = data, generations, attempts
        self.base_paths, self.expand = base_paths, expand

    @classmethod
    def take(cls, paths, expand=None, attempts=3, validate=None):
        """Bounded retry of the whole generation, including dynamically named files."""
        history = []
        paths = set(map(Path, paths))
        for attempt in range(1, attempts + 1):
            data, generations = {}, {}
            try:
                for path in sorted(paths):
                    data[path], generations[path] = read_once(path)
                if expand:
                    for path in sorted(set(map(Path, expand(data))) - set(data)):
                        data[path], generations[path] = read_once(path)
                if any(generation(p) != sig for p, sig in generations.items()):
                    raise CaptureChanged('Metadata generation changed across capture')
                if expand and paths | set(map(Path, expand(data))) != set(data):
                    raise CaptureChanged('Metadata file set changed across capture')
                if validate:
                    validate(data)
                history.append(dict(attempt=attempt, outcome='stable', finished_utc=utc()))
                return cls(data, generations, history, paths, expand)
            except (CaptureChanged, FileNotFoundError, json.JSONDecodeError) as exc:
                history.append(dict(attempt=attempt, outcome=type(exc).__name__, finished_utc=utc()))
        raise CaptureChanged('No stable metadata generation after bounded capture retries')

    def parsed(self, path):
        return json.loads(self.data[Path(path)])

    def unchanged(self):
        # No parsed objects are reconstructed from these later reads.
        if self.expand and self.base_paths | set(map(Path, self.expand(self.data))) != set(self.data):
            raise CaptureChanged('Original metadata file set changed')
        for path, data in self.data.items():
            current, sig = read_once(path)
            if sig != self.generations[path] or current != data:
                raise CaptureChanged('Original capture changed: ' + str(path))
        return dict(passed=True, checked_utc=utc(), files=len(self.data),
                    policy='Original generation and exact bytes unchanged; no hidden refresh')

    def export(self, out, destinations, source_name):
        records = {}
        for path, data in self.data.items():
            name = source_name(path)
            require(name not in records, 'Duplicate original capture source')
            copied = relative_path(destinations[path])
            target = Path(out) / copied
            require(not target.exists(), 'Capture destination already exists')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            records[name] = dict(copied_path=copied.as_posix(), sha256=digest(data), bytes=len(data))
        return dict(schema='m1-metadata-capture-v1', captured_utc=utc(),
                    runtime=runtime_info(), attempts=self.attempts, files=records,
                    final_unchanged_check=dict(passed=False))


def copy_verified(source, target, expected):
    """Hash the bytes actually copied; atomic replacement never follows target links."""
    source, target = Path(source), Path(target)
    before = generation(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + '.materializing')
    require(not temporary.exists(), 'Existing partial materialization must be preserved')
    h = hashlib.sha256()
    size = 0
    with source.open('rb') as stream, temporary.open('xb') as destination:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
            size += len(block)
            destination.write(block)
    require(before == generation(source), 'Raw source changed during materialization')
    require(h.hexdigest() == expected, 'Actual fresh bytes differ from captured artifact identity')
    temporary.replace(target)
    require(not target.is_symlink(), 'Materialized target must be a regular file')
    return dict(sha256=h.hexdigest(), bytes=size)


def verify_capture_copies(out, record):
    out = Path(out).resolve()
    for row in record['files'].values():
        target = out / relative_path(row['copied_path'])
        require(target.resolve(strict=True).is_relative_to(out) and not target.is_symlink(),
                'Capture copy escaped its closed destination')
        data = target.read_bytes()
        require(len(data) == row['bytes'] and digest(data) == row['sha256'],
                'Exported metadata changed after capture')


def secret_values():
    values = [v for k, v in os.environ.items()
              if re.search(r'TOKEN|SECRET|PASSWORD|CREDENTIAL|AUTHORIZATION|COOKIE', k, re.I)
              and len(v) >= 4]
    # The documented transport adapter uses this private file. Read secrets
    # only for redaction, never serialize the configuration or its contents.
    path = Path.home() / '.config/openmhd/reana-p4n.json'
    if path.exists():
        config = json.loads(path.read_bytes())
        values += [v for k, v in config.items()
                   if isinstance(v, str) and len(v) >= 4
                   and re.search(r'token|secret|password|credential', k, re.I)]
    return values


def redact(data, secrets):
    text = data.decode('utf-8', errors='replace') if isinstance(data, bytes) else str(data)
    for secret in sorted(secrets, key=len, reverse=True):
        text = text.replace(secret, '[REDACTED]')
    text = re.sub(r'(?i)(authorization\s*[:=]\s*(?:bearer\s+)?)[^\s,;"}]+',
                  r'\1[REDACTED]', text)
    text = re.sub(r'(?i)((?:access[_-]?token|password|client[_-]?secret|api[_-]?key)'
                  r'["\']?\s*[:=]\s*["\']?)[^\s,;"}\']+', r'\1[REDACTED]', text)
    text = re.sub(r'(https?://)[^/\s:@]+:[^/\s@]+@', r'\1[REDACTED]@', text)
    return text


def credential_free_argv(argv, secrets):
    require(all(isinstance(a, str) for a in argv), 'Command argv must contain strings')
    require(not any(secret in a for secret in secrets for a in argv),
            'Credentials in command argv are forbidden; use the configured adapter')
    for a in argv:
        require(not re.search(r'(?i)(?:--(?:access-)?token|--password|--secret|'
                              r'(?:token|password|secret|api_key)=|https?://[^/\s]*@|'
                              r'https?://[^\s]*\?)', a),
                'Credential-bearing command arguments are forbidden')


class CommandFailed(RuntimeError):
    pass


def kill_process(process):
    # Adapters may spawn a client. Close the entire private command group so
    # inherited stdout pipes cannot make timeout finalization wait forever.
    if os.name == 'posix':
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    else:
        process.kill()


class CommandJournal:
    """Attempt is durable before Popen, including logs; finally closes every outcome."""
    def __init__(self, out, filename='commands.json', log_directory='logs'):
        self.out, self.path = Path(out), Path(out) / filename
        self.logs, self.rows, self.lock = log_directory, [], threading.Lock()
        require(not self.path.exists(), 'Preserve existing command journal')
        self.secrets = secret_values()
        write_json(self.path, self.rows)

    def run(self, label, argv, cwd, timeout=7200, **metadata):
        argv = list(map(str, argv))
        credential_free_argv(argv, self.secrets)
        started = time.monotonic()
        with self.lock:
            attempt_id = len(self.rows) + 1
            prefix = self.logs + '/' + str(attempt_id).zfill(3) + '-' + label
            stdout_path, stderr_path = prefix + '.stdout', prefix + '.stderr'
            for name in (stdout_path, stderr_path):
                path = self.out / relative_path(name)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch(exist_ok=False)
            row = dict(attempt_id=attempt_id, label=label, argv=argv, cwd=str(cwd),
                       started_utc=utc(), finished_utc=None, duration_seconds=None,
                       timeout_seconds=timeout,
                       outcome='running', returncode=None, interpreter=runtime_info(),
                       child_environment=dict(PYTHONOPTIMIZE='0', PYTHONDONTWRITEBYTECODE='1'),
                       stdout=dict(path=stdout_path, sha256=digest(b''), bytes=0),
                       stderr=dict(path=stderr_path, sha256=digest(b''), bytes=0), **metadata)
            self.rows.append(row)
            write_json(self.path, self.rows)
        process, stdout, stderr = None, b'', b''
        outcome, returncode = 'start_failure', None
        error_type = None
        try:
            environment = dict(os.environ, PYTHONOPTIMIZE='0', PYTHONDONTWRITEBYTECODE='1')
            process = subprocess.Popen(argv, cwd=cwd, env=environment,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       start_new_session=os.name == 'posix')
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                returncode = process.returncode
                outcome = 'success' if returncode == 0 else 'nonzero'
            except subprocess.TimeoutExpired:
                kill_process(process)
                stdout, stderr = process.communicate()
                returncode, outcome = process.returncode, 'timeout'
        except BaseException as exc:
            error_type = type(exc).__name__
            if process is not None:
                if process.poll() is None:
                    kill_process(process)
                stdout, stderr = process.communicate()
                returncode = process.returncode
                outcome = 'interrupted'
            # Do not echo exception arguments: a transport exception may carry secrets.
            stderr += ('\nCommand exception type: ' + error_type + '\n').encode()
        finally:
            with self.lock:
                for key, data in (('stdout', stdout), ('stderr', stderr)):
                    safe = redact(data, self.secrets).encode('utf-8')
                    (self.out / row[key]['path']).write_bytes(safe)
                    row[key].update(sha256=digest(safe), bytes=len(safe))
                row.update(finished_utc=utc(), duration_seconds=max(0., time.monotonic()-started),
                           outcome=outcome, returncode=returncode, error_type=error_type)
                write_json(self.path, self.rows)
        if outcome != 'success':
            raise CommandFailed('Preserved command failure: ' + label + ' (' + outcome + ')')
        return row


def physics_files(config):
    names = ['final.csv']
    primary_shock = (config['case'] == 'brio-wu'
                     and ((config['jitter'] == 0 and config['jitter_mode'] == 'planar')
                          or (config['jitter'] == .15 and config['jitter_mode'] == 'columns')))
    primary_vortex = config['case'] == 'orszag-tang' and config['jitter'] == 0
    if primary_shock or primary_vortex:
        names.append('geometry.json')
    if primary_vortex:
        names.append('projected_bins.json')
    return names


def case_metadata(root, plan):
    paths = []
    for entry in plan['cases']:
        case = root / relative_path(entry['directory'])
        paths += [case / n for n in ('case.json', 'payload.json', 'reana.yaml',
                                     'snapshot.json', 'preflight/preflight.json')]
        received = root / 'download' / relative_path(entry['directory']) / 'outputs'
        if (received / 'execution.json').exists():
            paths += [received / n for n in ('execution.json', 'record.json', 'artifacts.sha256.json')]
            if (received / 'runtime.json').exists():
                paths.append(received / 'runtime.json')
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--client', required=True)
    parser.add_argument('--require-complete', action='store_true')
    parser.add_argument('--original-root', type=Path,
                        help='Original live root when caller supplies a private captured view')
    parser.add_argument('--reference-root', type=Path,
                        help='Captured reference/packet cwd context supplied by complete collector')
    args = parser.parse_args()
    root, out, repo = args.plan.resolve(), args.destination.resolve(), Path.cwd()
    require(not out.exists(), 'Use a fresh isolated checkpoint directory')
    original = (args.original_root or root).resolve()
    reference_root = (args.reference_root or repo).resolve()
    reference_paths = [Path('tests/reference/external_mhd') / n
                       for n in ('brio_8192.csv.gz','vortex_512.csv.gz')]
    packet = Path('benchmarks/m0/packet.json')
    reference_metadata = Path('tests/reference/external_mhd/provenance.json')
    reference_inputs = {reference_root/p:p for p in [packet,*reference_paths,reference_metadata]}
    require(not out.is_relative_to(root) and not out.is_relative_to(original),
            'Never write into a live/captured source plan')
    for closed_packet in ('m1_acceptance','m1_iterative_step_campaigns'):
        require(not out.is_relative_to(repo/'tests/reference'/closed_packet),
                'Historical reference packets are closed')
    paths = [root / n for n in ('plan.json', 'runs.json', 'checkpoint.json')]
    paths += list(reference_inputs)
    def coherent(data):
        runs = json.loads(data[root/'runs.json'])
        checkpoint = json.loads(data[root/'checkpoint.json'])
        if checkpoint['completed_cases'] != len(runs):
            raise CaptureChanged('Observer checkpoint/run generation is incoherent')
    capture = MetadataCapture.take(paths, lambda data: case_metadata(root, json.loads(data[root/'plan.json'])),
                                   validate=coherent)
    plan, observed_runs, checkpoint = [capture.parsed(root/n) for n in ('plan.json','runs.json','checkpoint.json')]
    require(plan['snapshot_sha256'] == SNAPSHOT and len(plan['cases']) == 30, 'Wrong physics plan')
    entries = {e['specification']['config']['name']: e for e in plan['cases']}
    require(len(entries) == len({e['workflow'] for e in plan['cases']}) == 30, 'Duplicate physics identity')
    require(set(observed_runs) <= set(entries), 'Unknown observed case')
    require(checkpoint['completed_cases'] == len(observed_runs) and checkpoint['expected_cases'] == 30,
            'Incoherent observed checkpoint/run map')
    require(not checkpoint['verified_required_failure'] and not checkpoint['execution_failures'],
            'Required physical/execution failure blocks collection')
    require(all(r['status'] == 'completed' for r in observed_runs.values()), 'Non-completed run')
    if args.require_complete:
        require(checkpoint['all_terminal'] and set(observed_runs) == set(entries), 'Full physics not ready')
    out.mkdir(parents=True)
    destinations = {}
    for path in capture.data:
        if path in reference_inputs:
            destinations[path] = 'metadata/reference_inputs/'+str(reference_inputs[path])
            continue
        rel = path.relative_to(root).as_posix()
        if rel in ('plan.json', 'checkpoint.json'):
            destinations[path] = rel
        elif rel == 'runs.json':
            destinations[path] = 'observed_run_map.json'
        elif rel.startswith('download/'):
            destinations[path] = rel
        else:
            destinations[path] = 'metadata/' + rel
    def source_name(path):
        origin = (repo/reference_inputs[path] if path in reference_inputs
                  else original/path.relative_to(root))
        return str(origin.relative_to(repo)) if origin.is_relative_to(repo) else str(origin)
    record = capture.export(out, destinations, source_name)
    write_json(out/'metadata_capture.json', record)
    collector_bytes, collector_generation = read_once(Path(__file__).resolve())
    (out/'collector.py').write_bytes(collector_bytes)
    snapshot_path = root / relative_path(plan['cases'][0]['directory']) / 'snapshot.json'
    require(digest(capture.data[snapshot_path]) == SNAPSHOT, 'Wrong source snapshot')
    snapshot = capture.parsed(snapshot_path)
    source_digests = {str(path):digest(capture.data[reference_root/path])
                      for path in [packet,*reference_paths,reference_metadata]}
    require(all(value == snapshot['source_sha256'][key] for key,value in source_digests.items()),
            'Reference/source identity mismatch')
    provenance = dict(
        scope='Fresh completed REANA raw inputs for independent reference reducers; not full staged-input/phase/M1 acceptance.',
        snapshot_sha256=SNAPSHOT, binary_sha256=BINARY,
        source_sha256={str(packet): source_digests[str(packet)]},
        reference_sha256={path.name: source_digests[str(path)] for path in reference_paths},
        collector_sha256=digest(collector_bytes), runtime=runtime_info(),
        observed_run_map_sha256=digest(capture.data[root/'runs.json']),
        observer_checkpoint_sha256=digest(capture.data[root/'checkpoint.json']),
        plan_sha256=digest(capture.data[root/'plan.json']))
    write_json(out/'provenance.json', provenance)
    journal = CommandJournal(out, 'transport_commands.json', 'transport_logs')

    def collect(entry):
        spec, config = entry['specification'], entry['specification']['config']
        name = config['name']
        require(relative_path(name).parts == (name,), 'Invalid case name')
        require(spec['kind'] == 'physics' and config['profile'] == 'bulk-frame-heun-quadratic-v1'
                and config['riemann_solver'] == 'hlld-pressure'
                and spec['options'] == dict(accelerated_projection=False, projection_screening=1.,
                                           potential_limiter='smooth-extrema'), 'Wrong candidate')
        case = root / relative_path(entry['directory'])
        require(digest(capture.data[case/'payload.json']) == entry['payload_sha256']
                and digest(capture.data[case/'reana.yaml']) == entry['workflow_sha256']
                and capture.parsed(case/'case.json') == spec, 'Staged case metadata mismatch')
        if name not in observed_runs:
            return dict(name=name, pending='Absent in captured observer checkpoint; not a failure')
        received = root/'download'/relative_path(entry['directory'])/'outputs'
        require(received/'execution.json' in capture.data, 'Completed case lacks execution receipt')
        manifest = capture.parsed(received/'artifacts.sha256.json')
        execution, run = capture.parsed(received/'execution.json'), capture.parsed(received/'record.json')
        for filename in ('execution.json','record.json'):
            require(digest(capture.data[received/filename]) == manifest['outputs/'+filename],
                    'Execution/record manifest mismatch')
        require(execution['case'] == spec and run['config'] == config, 'Case/record config mismatch')
        require(execution['payload_sha256'] == entry['payload_sha256']
                and execution['snapshot_sha256'] == SNAPSHOT and execution['binary_sha256'] == BINARY
                and execution['preflight_sha256'] == digest(capture.data[case/'preflight/preflight.json'])
                and execution['record_sha256'] == digest(capture.data[received/'record.json']),
                'Execution provenance mismatch')
        require(execution['status'] == 'completed' and execution['single_case_gates_passed']
                and run['status'] == 'completed' and run['returncode'] == 0
                and run == observed_runs[name], 'Execution differs from captured run map')
        local = out/'download'/relative_path(entry['directory'])
        requested = ['outputs/raw/'+name+'/'+filename for filename in physics_files(config)]
        needed, artifacts = [], []
        for remote in requested:
            source, target = received.parent/relative_path(remote), local/relative_path(remote)
            if source.exists() and sha(source) == manifest[remote]:
                require(source.resolve(strict=True).is_relative_to(original),
                        'Cached raw input must originate inside this actual fresh phase')
                copy_verified(source, target, manifest[remote])
            else:
                needed.append(remote)
        transport = None
        if needed:
            transport = journal.run('download-'+name, shlex.split(args.client)+[
                'download','-w',entry['workflow'],'-o',str(local),*needed],
                cwd=repo, timeout=1800, workflow=entry['workflow'], requested_paths=needed)
        checked = {}
        for filename, remote in zip(physics_files(config), requested):
            source, target = local/relative_path(remote), out/name/filename
            expected = run['sha256'][filename]
            require(manifest[remote] == expected, 'Raw manifest/run identity mismatch')
            identity = copy_verified(source, target, expected)
            checked[filename] = expected
            original_source = (source if remote in needed else
                               original/'download'/relative_path(entry['directory'])/relative_path(remote))
            artifacts.append(dict(artifact=filename, remote_path=remote, **identity,
                copied_path=str(target.relative_to(out)), local_source=str(original_source),
                acquisition='fresh_workflow_download' if remote in needed else 'already_downloaded_fresh',
                transport_attempt_id=transport['attempt_id'] if remote in needed else None))
        return dict(name=name, workflow=entry['workflow'], run=run, verified=checked, artifacts=artifacts,
                    execution_sha256=digest(capture.data[received/'execution.json']),
                    manifest_sha256=digest(capture.data[received/'artifacts.sha256.json']))

    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(collect, plan['cases']))
    runs = {row['name']: row.pop('run') for row in rows if 'run' in row}
    require(set(runs) == set(observed_runs), 'Captured completed case lacks verified actual inputs')
    final_check = capture.unchanged()
    require(read_once(Path(__file__).resolve()) == (collector_bytes,collector_generation),
            'Collector source changed')
    verify_capture_copies(out,record)
    record['final_unchanged_check'] = final_check
    write_json(out/'metadata_capture.json', record)
    write_json(out/'runs.json', runs)
    write_json(out/'input_receipts.json', dict(scope=provenance['scope'],completed=len(runs),expected=30,
        observations=rows, transport_journal='transport_commands.json',
        capture_manifest_sha256=sha(out/'metadata_capture.json'), full_m1_accepted=False))
    print('Verified actual raw inputs for',len(runs),'of 30 captured completed physics cases')


if __name__ == '__main__':
    main()
