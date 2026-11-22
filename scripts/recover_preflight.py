#!/usr/bin/env python3
"""Unexecuted proposal: bounded GET-only recovery of the original Rust preflight05.

No compiler, artifact execution, submission, case preparation or old-schema
promotion is implemented. Offline verification requires all named origin roots.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
import time

SCHEMA = 'openmhd.galaxy-preflight-recovery.v1'
WORKFLOW = 'openmhd-galaxy-build-7c4b82b58572-a05.1'
UUID = '7f7d85c9-41a3-4d13-a300-1d9b39159145'
REVISION = '6f032583a699b61706c95c6d2d95cdfea5ea6e87'
SNAPSHOT = '7c4b82b58572cb3eb298e05f98ecf9cb64fc93abbbe089d2faf19c3ee0c19745'
ARCHIVE = '4d046fb465fcc6e4c1b6a0f62d1c947e3a8d32b465d3963cd80975a1361c9823'
PLAN = 'd15cf1404a5abcb3bea8f8f319c25b7ab910627bc24bf645188acf60b390754b'
PAYLOAD = '804e30331fe977d61eb903bacb5b2e9c6423fd8cad9b98b7ee5cb817c1c88d6c'
SUBMISSION = 'dc872ff399ee32af0f9c34a5411513c283acaf6310bfa3e2a572bfa80f481888'
IMAGE = 'gitlab-p4n.aip.de:5005/p4nreana/reana-env@sha256:aebd7911df9e1e97ad67d15f4c32ab23996000282183fad3bf7a480756522bd7'
ORIGINALS = {'948349c4d7596c8cfb1fad9a204e29fc2e294254116e7c6aea56378b3731ea1f',
             'bbb8014731d72c3206189a9f5545ea8088b1eae0c64dbd22e9fa6c81dbdca189'}
PARENT = ('outputs/execution.json', 'outputs/runtime.json', 'outputs/artifacts.sha256.json',
          'outputs/galaxy-preflight/preflight.json', 'outputs/galaxy-preflight/commands.json',
          'outputs/galaxy-preflight/export.json', 'outputs/galaxy-preflight/sha256.json')
HELPERS = ('tools/galaxy_evidence/readonly_adapter.py',
           'tools/m1_evidence/reana_metadata_readonly_adapter.py',
           'tools/galaxy_evidence/common.py', 'tools/galaxy_evidence/pipeline.py',
           'reana/galaxy_test_case.py', 'tools/m1_evidence/reana_metadata_job.py',
           'scripts/prepare_galaxy_cases.py')
RETRY_CODES = {'network_error', 'adapter_deadline', 'incomplete_body'}
LIMIT = 3
MAX_FILE = 512 * 1024 * 1024


class Invalid(ValueError):
    pass


def require(value, code):
    if not value:
        raise Invalid(code)


def parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate_json_key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(Invalid('nonfinite_json')))


def encode(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def utc(value):
    require(type(value) is str, 'utc_type')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None and result.utcoffset().total_seconds() == 0, 'utc_zone')
    return result


def safe(root, name):
    p = PurePosixPath(name)
    require(type(name) is str and p.parts and p.as_posix() == name and not p.is_absolute()
            and '..' not in p.parts and '\\' not in name, 'unsafe_path')
    current = Path(root.anchor)
    for part in root.absolute().parts[1:]:
        current /= part
        require(not current.is_symlink(), 'linked_root_ancestor')
    current = root
    for part in p.parts:
        current /= part
        require(not current.is_symlink(), 'linked_path')
    return current


def identity(path):
    a = path.stat()
    require(not path.is_symlink() and stat.S_ISREG(a.st_mode) and a.st_size <= MAX_FILE, 'regular_bounded_file')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    b = path.stat()
    require(all(getattr(a, k) == getattr(b, k) for k in
                ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')), 'changed_file_generation')
    return dict(bytes=a.st_size, sha256=digest.hexdigest())


def read(root, name):
    path = safe(root, name)
    before = identity(path)
    raw = path.read_bytes()
    require(dict(bytes=len(raw), sha256=sha(raw)) == before == identity(path), 'changed_read_generation')
    return raw


def put(root, name, raw):
    path = safe(root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def persist(root, name, value):
    path = safe(root, name)
    temporary = path.with_name(path.name + '.tmp')
    require(not temporary.exists(), 'journal_temporary_exists')
    with temporary.open('xb') as stream:
        stream.write(encode(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)  # Journal only; never bodies/partials/intents.


def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(), 'linked_inventory')
        if path.is_file() and path != root / 'files.sha256.json':
            result[path.relative_to(root).as_posix()] = identity(path)
        else:
            require(path.is_dir() or path == root / 'files.sha256.json', 'special_inventory')
    return result


def closed(root):
    raw = read(root, 'files.sha256.json')
    require(parse(raw) == inventory(root), 'closed_inventory_mismatch')
    return sha(raw)


def check_observation(raw):
    value = parse(raw)
    require(value['schema'] == 'openmhd.galaxy-server-observation.v1'
            and value['origin'] == 'server', 'not_server_observation')
    utc(value['observed_utc'])
    require(len(value['matches']) == 1, 'ambiguous_observation')
    row = value['matches'][0]
    require(type(row['version']) is int and row == dict(id=UUID, name=WORKFLOW[:-2],
            status='finished', version=1, workflow=WORKFLOW), 'stale_workflow_UUID_status')
    return row


def check_source(root):
    raw = read(root, 'snapshot.json')
    snapshot = parse(raw)
    require(sha(raw) == SNAPSHOT and snapshot['source_revision'] == REVISION, 'source_identity')
    spec_raw = read(root, 'reana.yaml')
    require(sha(spec_raw) == snapshot['workflow_sha256'], 'source_spec_identity')
    spec = parse(spec_raw)
    require(spec['inputs']['files'] == ['snapshot.json', *sorted(snapshot['upload_sha256'])], 'source_upload_inventory')
    for name, digest in snapshot['upload_sha256'].items():
        require(identity(safe(root, name))['sha256'] == digest, 'source_upload_changed')
    steps = spec['workflow']['specification']['steps']
    require(spec['workflow']['type'] == 'serial' and len(steps) == 2
            and [s['commands'] for s in steps] == [['python3 remote.py prepare'],
                ['python3 remote.py run --study galaxy-source-preflight --jobs 4']], 'source_study')
    for step in steps:
        require(step['environment'] == IMAGE and step['kubernetes_cpu_request'] == step['kubernetes_cpu_limit'] == '4'
                and step['kubernetes_memory_limit'] == '8Gi', 'source_resources')
    return snapshot


def check_origin_header(root, snapshot, source_name):
    value = parse(read(root, source_name))
    require(value['workflow'] == WORKFLOW and value['uuid'] == UUID
            and value['snapshot_sha256'] == SNAPSHOT and value['component_accepted'] is False,
            'origin_identity')
    require(value['status'] in ('failed', 'incomplete', 'complete'), 'origin_status')
    require(snapshot['source_revision'] == REVISION, 'origin_source')
    return value


def diagnostic(raw):
    value = parse(raw)
    require(value['schema'] == 'openmhd.galaxy-get-diagnostic.v1', 'untyped_diagnostic')
    return value


def retryable(row, diag):
    require(row['outcome'] not in ('intent', 'running', 'pending_launch', 'unknown_lifecycle',
                                 'interrupted_or_start_failed'), 'unknown_lifecycle')
    if row['outcome'] == 'timeout':
        require(row.get('child_reaped') is True, 'timeout_without_reaping')
        return True
    return row['outcome'] == 'nonzero' and diag is not None and diag.get('code') in RETRY_CODES


def audit_attempt(root, name, origin, helper_hashes, legacy=False):
    row = parse(read(root, name))
    require(row['schema'] == ('openmhd.galaxy-transport-attempt.v1' if legacy
                             else 'openmhd.galaxy-recovery-transport.v1'), 'attempt_schema')
    if legacy:
        require(re.fullmatch(r'transport/[0-9]{4}\.json', name), 'legacy_receipt_path')
        stem = Path(name).stem
        require(row['output'] == 'downloads/' + stem + '.body'
                and row['stdout'] == 'transport/' + stem + '.stdout'
                and row['stderr'] == 'transport/' + stem + '.stderr', 'legacy_body_namespace')
    else:
        require(re.fullmatch(r'attempts/[0-9]{6}/result\.json', name), 'new_receipt_path')
        folder = name.rsplit('/', 1)[0]
        require(row['output'] == folder + '/body' and row['stdout'] == folder + '/stdout.json'
                and row['stderr'] == folder + '/stderr.json', 'new_body_namespace')
    action, remote = row['action'], row['remote_path']
    require(action in ('observe', 'download') and (action == 'observe') == (remote is None), 'attempt_mode')
    require(row['workflow'] == WORKFLOW and utc(row['finished_utc']) >= utc(row['started_utc']), 'attempt_workflow_time')
    argv = row['argv']
    require(type(argv) is list and all(type(v) is str for v in argv) and len(argv) >= 3
            and Path(argv[0]).is_absolute() and Path(argv[2]).is_absolute()
            and Path(row['cwd']).is_absolute(), 'attempt_argv')
    expected = [argv[0], '-B', argv[2], action, '--workflow', WORKFLOW,
                '--output', str(Path(row['cwd']) / row['output'])]
    if remote is not None:
        expected += ['--path', remote]
    require(argv == expected and Path(argv[2]).parts[-3:] == ('tools', 'galaxy_evidence', 'readonly_adapter.py')
            and row['adapter_sha256'] == helper_hashes[HELPERS[0]]
            and row['base_adapter_sha256'] == helper_hashes[HELPERS[1]], 'attempt_helper_links')
    if not legacy:
        intent_name = name.rsplit('/', 1)[0] + '/intent.json'
        intent = parse(read(root, intent_name))
        require(row['intent_sha256'] == sha(read(root, intent_name)) and intent['outcome'] == 'intent'
                and intent['pid'] is None and intent['returncode'] is None and intent['child_reaped'] is False
                and all(row[k] == intent[k] for k in ('argv', 'cwd', 'workflow', 'remote_path', 'action',
                    'interpreter', 'timeout_seconds', 'adapter_sha256', 'base_adapter_sha256', 'started_utc', 'phase'))
                and row['timeout_seconds'] == 300 and row['child_reaped'] is True
                and type(row['seconds']) in (int, float) and row['seconds'] >= 0
                and type(row['pid']) is int and row['pid'] > 0, 'new_attempt_lifecycle')
        launch = parse(read(root, name.rsplit('/', 1)[0] + '/launch.json'))
        require(launch['pid'] == row['pid'] and launch['argv'] == argv
                and type(launch['pid']) is int
                and utc(row['started_utc']) <= utc(launch['launched_utc']) <= utc(row['finished_utc'])
                and row['interpreter']['implementation'] == 'cpython'
                and row['interpreter']['executable'] == argv[0]
                and type(row['interpreter']['python']) is str and bool(row['interpreter']['python'])
                and Path(argv[2]) == Path(row['cwd']) / 'helpers' / HELPERS[0]
                and type(row['interpreter']['optimized']) is int and row['interpreter']['optimized'] == 0,
                'actual_launch_interpreter_link')
    for channel in ('stdout', 'stderr'):
        require(sha(read(root, row[channel])) == row[channel + '_sha256'], 'attempt_log_hash')
    success = row['outcome'] == 'success' and type(row['returncode']) is int and row['returncode'] == 0
    body = safe(root, row['output'])
    diag = diagnostic(read(root, row['stdout'] if success else row['stderr'])) if row['outcome'] != 'timeout' else None
    if diag is not None:
        require(diag['action'] == action and diag['workflow'] == WORKFLOW
                and diag['requested_path'] == remote, 'diagnostic_request_link')
    if success:
        require(diag['outcome'] == 'success' and diag['code'] == 'completed'
                and diag['workflow_ids'] == [UUID] and body.is_file()
                and identity(body)['sha256'] == row['output_sha256'], 'unsound_success_body')
        require(not body.with_name(body.name + '.partial').exists(), 'success_with_partial')
        if action == 'observe':
            check_observation(read(root, row['output']))
    else:
        require(row['outcome'] in ('nonzero', 'timeout') and (row['outcome'] == 'timeout'
                or type(row['returncode']) is int and row['returncode'] != 0), 'failed_returncode_outcome')
        if diag is not None:
            require(diag['outcome'] == 'failure', 'failed_diagnostic_outcome')
        require(not body.exists(), 'failed_published_body')
        partial = body.with_name(body.name + '.partial')
        if partial.exists():
            actual_partial = identity(partial)
            if not legacy:
                require(actual_partial == row['partial_identity'], 'partial_identity_link')
            if diag is not None:
                require(diag['partial_file'] == partial.name and diag['retained_bytes'] == actual_partial['bytes'],
                        'partial_diagnostic_link')
        if legacy and row['outcome'] == 'timeout':
            # Exact pinned common.py uses subprocess.run(timeout), which kills
            # and reaps the one-process adapter before returning TimeoutExpired.
            row = dict(row, child_reaped=True)
        require(retryable(row, diag), 'nonretryable_or_unknown_failure')
    return dict(ref=dict(origin=origin, receipt=name), action=action, remote_path=remote, phase=row.get('phase'),
                started_utc=row['started_utc'], finished_utc=row['finished_utc'],
                success=success, body=body if success else None,
                identity=identity(body) if success else None)


def scan(root, origin):
    snapshot = check_source(root / 'source')
    helper_hashes = {name: snapshot['source_sha256'][name] for name in HELPERS}
    old = (root / 'acquisition.json').exists()
    record = check_origin_header(root, snapshot, 'acquisition.json' if old else 'recovery.json')
    if old:
        require(record['schema'] == 'openmhd.galaxy-preflight-acquisition.v1', 'legacy_schema')
        for name in HELPERS:
            # The old packet copied seven helpers, including the base adapter
            # only through source parts; inspect present retained copies here.
            copied = root / 'tools' / name
            if copied.exists():
                require(identity(copied)['sha256'] == helper_hashes[name], 'legacy_helper_copy')
        names = sorted('transport/' + p.name for p in (root / 'transport').glob('*.json'))
    else:
        require(record['schema'] == SCHEMA and record['physical_accepted'] is False, 'recovery_schema')
        require(read(root, 'recovery_source.py') == Path(__file__).read_bytes(), 'recovery_generation_changed')
        check_input_metadata(root, record)
        for name in HELPERS:
            require(identity(safe(root / 'helpers', name))['sha256'] == helper_hashes[name], 'captured_helper_generation')
        names = sorted(p.relative_to(root).as_posix() for p in (root / 'attempts').glob('*/result.json'))
        intents = sorted(p.parent for p in (root / 'attempts').glob('*/intent.json'))
        require(len(intents) == len(names) and all((p / 'result.json').is_file() for p in intents), 'unknown_lifecycle')
        require({p for p in (root / 'attempts').iterdir()} == set(intents), 'unregistered_attempt_directory')
        for folder in intents:
            require(re.fullmatch('[0-9]{6}', folder.name) and {p.name for p in folder.iterdir()} <=
                    {'intent.json', 'launch.json', 'result.json', 'stdout.json', 'stderr.json', 'body', 'body.partial'},
                    'unknown_attempt_artifact')
    entries = [audit_attempt(root, name, origin, helper_hashes, old) for name in names]
    require(len(names) == len(set(names)), 'duplicate_attempt_receipt')
    if old:
        successful = {x['remote_path']: x['ref']['receipt'] for x in entries if x['success'] and x['action'] == 'download'}
        require(record['files'] == successful and len(successful) == sum(x['success'] and x['action'] == 'download'
                for x in entries), 'legacy_success_map')
        original = read(root, 'submission_original.json')
        require(sha(original) == record['submission_sha256'] == SUBMISSION
                and parse(original) == {WORKFLOW: {'status': 'submitted'}}, 'legacy_submission_identity')
    else:
        counts = {}
        for item in entries:
            key = (item['action'], item['remote_path'])
            counts[key] = counts.get(key, 0) + 1
        require(all(n <= LIMIT for n in counts.values()), 'invocation_retry_bound')
    return record, entries


def choose(entries, remote, expected=None):
    candidates = [x for x in entries if x['action'] == 'download' and x['remote_path'] == remote and x['success']]
    refs = [(x['ref']['origin'], x['ref']['receipt']) for x in candidates]
    require(len(refs) == len(set(refs)), 'duplicate_candidate_reference')
    require(bool(candidates), 'missing_successful_request')
    identities = {(x['identity']['bytes'], x['identity']['sha256']) for x in candidates}
    require(len(identities) == 1, 'ambiguous_changed_metadata_or_body')
    if expected is not None:
        require(candidates[0]['identity'] == expected, 'descriptor_mismatch')
    # Multiple byte-identical successes are retained, but one exact receipt is
    # selected deterministically. Conflicting successes are never voted away.
    return sorted(candidates, key=lambda x: (x['ref']['origin'], x['ref']['receipt']))[0]


def load_origins(paths):
    roots, records, entries = {}, {}, []
    for path in paths:
        root = path.absolute()
        digest = closed(root)
        require(digest not in roots, 'duplicate_origin')
        record, items = scan(root, digest)
        require(record['schema'] == SCHEMA or digest in ORIGINALS, 'unregistered_legacy_origin')
        roots[digest], records[digest] = root, record
        entries.extend(items)
    require(ORIGINALS <= set(roots), 'missing_original_failed_histories')
    for digest, record in records.items():
        if record['schema'] == SCHEMA:
            require(set(record['origins']) <= set(roots) and digest not in record['origins'], 'missing_or_cyclic_origin')
            for other in record['origins']:
                require(read(roots[digest], 'origins/' + other + '.json')
                        == read(roots[other], 'files.sha256.json'), 'prior_origin_manifest_link')
    def visit(digest, chain):
        require(digest not in chain, 'cyclic_origin')
        for other in records[digest].get('origins', {}):
            visit(other, chain | {digest})
    for digest in records:
        visit(digest, set())
    return roots, records, entries


def retain_log(raw):
    try:
        diagnostic(raw)
        return raw
    except (ValueError, KeyError, TypeError):
        return encode(dict(schema='openmhd.galaxy-unavailable-diagnostic.v1',
                           unretained_bytes=len(raw), sha256=sha(raw)))


def attempt(root, action, remote, phase, number):
    folder = 'attempts/' + str(number).zfill(6)
    (root / folder).mkdir(parents=True, exist_ok=False)
    adapter = root / 'helpers' / HELPERS[0]
    argv = [sys.executable, '-B', str(adapter.absolute()), action, '--workflow', WORKFLOW,
            '--output', str((root / folder / 'body').absolute())]
    if remote is not None:
        argv += ['--path', remote]
    row = dict(schema='openmhd.galaxy-recovery-transport.v1', action=action, remote_path=remote,
        workflow=WORKFLOW, phase=phase, output=folder + '/body', argv=argv, cwd=str(root.absolute()),
        timeout_seconds=300, started_utc=now(), finished_utc=None, outcome='intent', returncode=None,
        adapter_sha256=identity(adapter)['sha256'],
        base_adapter_sha256=identity(root / 'helpers' / HELPERS[1])['sha256'],
        interpreter=dict(executable=sys.executable, python=sys.version,
                         implementation=sys.implementation.name, optimized=sys.flags.optimize),
        child_reaped=False, pid=None)
    put(root, folder + '/intent.json', encode(row))
    row['intent_sha256'] = sha(read(root, folder + '/intent.json'))
    process, out, err = None, b'', b''
    start = time.monotonic()
    try:
        process = subprocess.Popen(argv, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        row['pid'] = process.pid
        persist(root, folder + '/launch.json', dict(pid=process.pid, argv=argv, launched_utc=now()))
        try:
            out, err = process.communicate(timeout=300)
            row.update(outcome='success' if process.returncode == 0 else 'nonzero', returncode=process.returncode,
                       child_reaped=True)
        except subprocess.TimeoutExpired:
            process.kill()  # Direct child remains owned/unreaped; adapter is one process.
            out, err = process.communicate()
            row.update(outcome='timeout', returncode=process.returncode, child_reaped=True)
    except BaseException:
        if process is not None and not row['child_reaped']:
            try:
                process.kill()
                out, err = process.communicate(timeout=15)
                row.update(returncode=process.returncode, child_reaped=True)
            except BaseException:
                pass
        row['outcome'] = 'unknown_lifecycle'  # Never automatically retried.
    finally:
        row.update(finished_utc=now(), seconds=time.monotonic() - start)
        for channel, raw in (('stdout', out), ('stderr', err)):
            row[channel] = folder + '/' + channel + '.json'
            retained = retain_log(raw)
            put(root, row[channel], retained)
            row[channel + '_sha256'] = sha(retained)
        body = root / row['output']
        if body.exists():
            row['output_sha256'] = identity(body)['sha256']
        partial = body.with_name(body.name + '.partial')
        if partial.exists():
            row['partial_identity'] = identity(partial)
        put(root, folder + '/result.json', encode(row))
    return audit_attempt(root, folder + '/result.json', 'self',
        {name: identity(root / 'helpers' / name)['sha256'] for name in HELPERS})


class Fetcher:
    def __init__(self, root, entries):
        self.root, self.entries, self.counts = root, list(entries), {}

    def fresh(self, action, remote, phase):
        key = (action, remote)
        while self.counts.get(key, 0) < LIMIT:
            self.counts[key] = self.counts.get(key, 0) + 1
            number = len(list((self.root / 'attempts').glob('*/intent.json')))
            item = attempt(self.root, action, remote, phase, number)
            self.entries.append(item)
            if item['success']:
                return item
        raise Invalid('bounded_transport_attempts_exhausted')

    def obtain(self, remote, expected=None, force=False, phase='missing'):
        if force or not any(x['success'] and x['remote_path'] == remote for x in self.entries):
            self.fresh('download', remote, phase)
        return choose(self.entries, remote, expected)


def descriptors(values, captured=None):
    if captured is None:
        captured = {name: read(path.parent, path.name) for name, path in values.items() if name in PARENT}
    def obj(name):
        return parse(captured[name])
    artifacts, export, commands, execution = (obj(name) for name in
        ('outputs/artifacts.sha256.json', 'outputs/galaxy-preflight/export.json',
         'outputs/galaxy-preflight/commands.json', 'outputs/execution.json'))
    require(export['schema'] == 'openmhd.galaxy-rust-preflight-export.v1'
            and export['snapshot_sha256'] == SNAPSHOT and export['archive_sha256'] == ARCHIVE
            and type(export['archive_bytes']) is int and export['archive_bytes'] == 413154228
            and type(export['test_methods_executed']) is int and export['test_methods_executed'] == 0
            and export['component_accepted'] is False, 'export_metadata_identity')
    parts = export['parts']
    require(type(parts) is list and len(parts) == 395, 'original_part_inventory')
    result = {name: None for name in PARENT}
    for index, part in enumerate(parts):
        require(part['path'] == 'export.part' + str(index).zfill(4)
                and type(part['bytes']) is int and 0 < part['bytes'] <= 1024 * 1024, 'part_descriptor')
        result['outputs/galaxy-preflight/' + part['path']] = dict(bytes=part['bytes'], sha256=part['sha256'])
    require(type(commands) is list and commands and type(execution['commands']) is list, 'command_arrays')
    for row in commands:
        for channel in ('stdout', 'stderr'):
            remote = 'outputs/galaxy-preflight/' + row[channel]
            require(re.fullmatch(r'outputs/galaxy-preflight/[a-zA-Z0-9_-]+\.(stdout|stderr)', remote), 'log_path')
            require(remote not in result and type(row[channel + '_bytes']) is int
                    and 0 <= row[channel + '_bytes'] <= 16 * 1024 * 1024, 'unique_log_descriptor')
            result[remote] = dict(bytes=row[channel + '_bytes'], sha256=row[channel + '_sha256'])
    for index, row in enumerate(execution['commands']):
        require(row['log'] == 'outputs/logs/' + str(index).zfill(2) + '.log' and row['log'] not in result, 'parent_log_path')
        result[row['log']] = None
    require(len(result) == 866, 'original_866_logical_requests')
    for name in result:
        if name != 'outputs/artifacts.sha256.json':
            require(name in artifacts and re.fullmatch('[0-9a-f]{64}', artifacts[name]), 'artifact_descriptor')
            if result[name] is not None:
                require(result[name]['sha256'] == artifacts[name], 'descriptor_artifact_disagreement')
    return result


def join_parts(source, parts, destination, wanted):
    digest, size = hashlib.sha256(), 0
    with destination.open('xb') as stream:
        for path in parts:
            with path.open('rb') as original:
                for block in iter(lambda: original.read(1024 * 1024), b''):
                    digest.update(block)
                    stream.write(block)
                    size += len(block)
    require(dict(bytes=size, sha256=digest.hexdigest()) == wanted, 'archive_concatenation')


def source_archive_check(source, snapshot, temporary):
    actual = {}
    for name, record in snapshot['archives'].items():
        path = temporary / name
        size = sum(identity(safe(source, part))['bytes'] for part in record['parts'])
        join_parts(source, [safe(source, part) for part in record['parts']], path,
                   dict(bytes=size, sha256=record['sha256']))
        if name != 'source.tar.gz':
            continue
        with tarfile.open(path, mode='r|gz') as stream:
            for member in stream:
                require(member.isfile() and member.name in snapshot['source_sha256']
                        and member.name not in actual, 'source_tar_inventory')
                safe(source, member.name)  # Validate lexical path without extracting.
                raw = stream.extractfile(member)
                digest, count = hashlib.sha256(), 0
                for block in iter(lambda: raw.read(1024 * 1024), b''):
                    digest.update(block)
                    count += len(block)
                require(digest.hexdigest() == snapshot['source_sha256'][member.name]
                        and count == member.size, 'source_tar_member')
                actual[member.name] = dict(bytes=count, sha256=digest.hexdigest())
    require(set(actual) == set(snapshot['source_sha256']), 'whole_original_source_tar')
    return actual


def listed(raw):
    names = []
    for line in raw.decode('utf-8').splitlines():
        if not line:
            continue
        match = re.fullmatch(r'([A-Za-z_][A-Za-z_0-9:]*): test', line)
        require(match is not None, 'invalid_list_line')
        names.append(match.group(1))
    require(len(names) == len(set(names)), 'duplicate_list_selector')
    return names


def validate_material(root, values, extract=False):
    snapshot = check_source(root / 'source')
    captured = {name: read(values[name].parent, values[name].name) for name in PARENT}
    get = lambda name: captured[name] if name in captured else read(values[name].parent, values[name].name)
    artifacts = parse(get(PARENT[2]))
    report, commands, export, local = (parse(get(name)) for name in PARENT[3:])
    execution, runtime = parse(get(PARENT[0])), parse(get(PARENT[1]))
    required = descriptors(values, captured)
    require(set(values) == set(required), 'exact_chosen_866_requests')
    for name, path in values.items():
        if name in captured:
            require(identity(path) == dict(bytes=len(captured[name]), sha256=sha(captured[name])), 'captured_metadata_generation')
        if name != PARENT[2]:
            require(identity(path)['sha256'] == artifacts[name], 'chosen_artifact_hash')
        if required[name] is not None:
            require(identity(path) == required[name], 'chosen_descriptor')
    require(report['schema'] == 'openmhd.galaxy-rust-preflight.v1' and report['status'] == 'complete'
            and report['component_accepted'] is False and type(report['test_methods_executed']) is int
            and report['test_methods_executed'] == 0 and report['before_after_source_identical'] is True
            and report['source_revision'] == REVISION and report['snapshot_sha256'] == SNAPSHOT
            and execution['snapshot_sha256'] == runtime['snapshot_sha256'] == SNAPSHOT, 'catalog_scope')
    require(execution['status'] == 'completed' and execution['study'] == 'galaxy-source-preflight'
            and type(execution['jobs']) is int and execution['jobs'] == report['jobs'] == 4
            and execution['runtime_sha256'] == sha(get(PARENT[1])) and runtime['image'] == IMAGE
            and runtime['rustc'].startswith('rustc 1.85.1 ') and runtime['machine']
            and runtime['bootstrap_file'] == 'remote.py'
            and runtime['bootstrap_sha256'] == runtime['source_bootstrap_sha256']
            == snapshot['upload_sha256']['remote.py'] == snapshot['source_sha256']['reana/remote.py'], 'runtime_source_links')
    require(execution['execution_cgroup'] == {name: runtime[name] for name in ('cpu.max', 'memory.max')}
            and execution['visible_cpus'] == runtime['visible_cpus'], 'resource_observation_links')
    rows = execution['commands']
    require(len(rows) == 4 and all(type(x['returncode']) is int and x['returncode'] == 0 for x in rows), 'four_zero_gates')
    source = Path(rows[3]['command'][3])
    require(source.is_absolute() and source.name == 'source' and UUID in source.parts, 'original_remote_source_path')
    expected = [['cargo', 'fmt', '--check'],
                ['cargo', 'clippy', '--workspace', '--all-targets', '--all-features', '--locked', '--', '-D', 'warnings'],
                ['cargo', 'build', '--release', '--workspace', '--all-features', '--locked'],
                [rows[3]['command'][0], 'reana/galaxy_preflight.py', '--source', str(source),
                 '--snapshot', str(source.parent / 'snapshot.json'), '--output',
                 str(source.parent / 'outputs/galaxy-preflight'), '--jobs', '4']]
    require(Path(expected[3][0]).is_absolute() and Path(expected[3][0]).name.startswith('python')
            and [x['command'] for x in rows] == expected, 'exact_parent_command_order')
    for row in rows:
        require(sha(get(row['log'])) == row['log_sha256'], 'parent_raw_log')
    labels = {}
    for row in commands:
        require(row['label'] not in labels and row['status'] == 'complete'
                and type(row['returncode']) is int and row['returncode'] == 0
                and row['cwd'] == str(source) and utc(row['finished_utc']) >= utc(row['started_utc']), 'compile_list_lifecycle')
        labels[row['label']] = row
        for channel in ('stdout', 'stderr'):
            raw = get('outputs/galaxy-preflight/' + row[channel])
            require(len(raw) == row[channel + '_bytes'] and sha(raw) == row[channel + '_sha256'], 'compile_list_raw_log')
    all_expected_labels, compiler_maps = set(), {}
    for profile in ('debug', 'release'):
        label = profile + '-compile'
        all_expected_labels.add(label)
        wanted = ['cargo', 'test', '--workspace', '--all-targets', '--all-features', '--locked',
                  '--no-run', '--message-format=json', '--jobs', '4'] + (['--release'] if profile == 'release' else [])
        require(labels[label]['argv'] == wanted, 'exact_no_run_compile')
        finished, mapping = [], {}
        for line in get('outputs/galaxy-preflight/' + labels[label]['stdout']).splitlines():
            if not line.startswith(b'{'):
                continue
            value = parse(line)
            if value.get('reason') == 'build-finished':
                finished.append(value.get('success'))
            if value.get('reason') == 'compiler-artifact' and value.get('profile', {}).get('test') is True and value.get('executable'):
                target = value['target']
                key = (str(Path(value['manifest_path']).relative_to(source)), tuple(target['kind']),
                       target['name'], str(Path(target['src_path']).relative_to(source)))
                require(key not in mapping, 'duplicate_compiler_artifact')
                binary = Path(value['executable'])
                require(binary.is_absolute() and binary.is_relative_to(source / 'target'), 'compiler_binary_location')
                mapping[key] = value
        require(len(finished) == 1 and finished[0] is True and mapping, 'unique_successful_compiler_finish')
        compiler_maps[profile] = mapping
    tests, binary_paths, seen = [], set(), {'debug': set(), 'release': set()}
    members = {'preflight.json': dict(bytes=len(get(PARENT[3])), sha256=sha(get(PARENT[3])))}
    for binary in report['binaries']:
        profile = binary['build_profile']
        require(profile in compiler_maps and binary['path'] not in binary_paths, 'unique_profile_binary')
        binary_paths.add(binary['path'])
        key = (binary['manifest'], tuple(binary['target']['kind']), binary['target']['name'], binary['source'])
        require(key in compiler_maps[profile] and key not in seen[profile], 'complete_compiler_catalog_binding')
        seen[profile].add(key)
        actual = compiler_maps[profile][key]
        require(binary['target'] == actual['target'] and binary['features'] == actual['features']
                and binary['profile'] == actual['profile'] and binary['package_id'] == actual['package_id']
                and binary['path'] == 'binaries/' + profile + '/' + Path(actual['executable']).name
                and binary['manifest'] in snapshot['source_sha256'] and binary['source'] in snapshot['source_sha256'], 'binary_target_source')
        label = binary['list_label']
        ignored = label[:-5] + '-ignored-list'
        all_expected_labels.update((label, ignored))
        require(labels[label]['argv'] == [actual['executable'], '--list', '--format', 'terse']
                and labels[ignored]['argv'] == [actual['executable'], '--list', '--ignored', '--format', 'terse'], 'list_only_argv')
        names = listed(get('outputs/galaxy-preflight/' + labels[label]['stdout']))
        require(names == binary['selectors'] and listed(get('outputs/galaxy-preflight/' + labels[ignored]['stdout'])) == [], 'raw_selector_catalog')
        for name in names:
            tests.append(dict(build_profile=profile, manifest=binary['manifest'], target_kind=binary['target']['kind'],
                target_name=binary['target']['name'], source=binary['source'], selector=name,
                binary=binary['path'], binary_sha256=binary['sha256']))
        require(type(binary['bytes']) is int and 0 < binary['bytes'] <= MAX_FILE, 'binary_byte_bound')
        members[binary['path']] = dict(bytes=binary['bytes'], sha256=binary['sha256'])
    require(set(labels) == all_expected_labels and all(seen[p] == set(compiler_maps[p]) for p in seen)
            and tests == report['tests'] and type(report['compiled_binaries']) is int
            and report['compiled_binaries'] == len(binary_paths) and type(report['resolved_leaves']) is int
            and report['resolved_leaves'] == len(tests), 'whole_profile_catalog_and_commands')
    require(export['preflight_sha256'] == sha(get(PARENT[3])) and export['members'] == members
            and sum(x['bytes'] for x in members.values()) <= 8 * 1024 ** 3, 'exact_bounded_export_members')
    expected_local = {name.removeprefix('outputs/galaxy-preflight/'): identity(path) for name, path in values.items()
                      if name.startswith('outputs/galaxy-preflight/') and name != PARENT[6]}
    expected_local.update(members)
    expected_local['test-binaries.tar.gz'] = dict(bytes=export['archive_bytes'], sha256=export['archive_sha256'])
    require(local == expected_local, 'complete_original_local_sha_inventory')
    expected_artifacts = {'outputs/galaxy-preflight/' + name: value['sha256'] for name, value in local.items()}
    expected_artifacts.update({name: sha(get(name)) for name in (PARENT[0], PARENT[1], PARENT[6])})
    expected_artifacts.update({row['log']: sha(get(row['log'])) for row in rows})
    require(artifacts == expected_artifacts, 'complete_original_artifact_inventory')
    with tempfile.TemporaryDirectory(prefix='openmhd-readonly-verify-') as directory:
        temporary = Path(directory)
        require(source_archive_check(root / 'source', snapshot, temporary) == report['source_files'], 'whole_source_receipt')
        archive = temporary / 'export.tar.gz'
        join_parts(root, [values['outputs/galaxy-preflight/' + part['path']] for part in export['parts']], archive,
                   dict(bytes=export['archive_bytes'], sha256=export['archive_sha256']))
        found = set()
        if extract:
            (root / 'export').mkdir(exist_ok=False)
        with tarfile.open(archive, mode='r|gz') as stream:
            for member in stream:
                require(member.isfile() and member.name in members and member.name not in found
                        and member.size == members[member.name]['bytes'], 'exact_regular_archive_member')
                found.add(member.name)
                destination = safe(root / 'export', member.name)
                raw = stream.extractfile(member)
                digest = hashlib.sha256()
                target = None
                if extract:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    target = destination.open('xb')
                try:
                    for block in iter(lambda: raw.read(1024 * 1024), b''):
                        digest.update(block)
                        if target is not None:
                            target.write(block)
                finally:
                    if target is not None:
                        target.close()
                require(digest.hexdigest() == members[member.name]['sha256'], 'archive_member_hash')
        require(found == set(members) and inventory(root / 'export') == members, 'complete_exact_extracted_export')
    return dict(logical_requests=len(values), archive_parts=len(export['parts']), archive_bytes=export['archive_bytes'],
                compiled_binaries=len(binary_paths), resolved_leaves=len(tests), test_methods_executed=0)


def reference(entries, ref, owner='self'):
    require(type(ref) is dict and set(ref) == {'origin', 'receipt'}, 'reference_schema')
    wanted = dict(origin=owner if ref['origin'] == 'self' else ref['origin'], receipt=ref['receipt'])
    matches = [x for x in entries if x['ref'] == wanted]
    require(len(matches) == 1 and matches[0]['success'], 'chosen_reference_missing_failed_or_duplicate')
    return matches[0]


def selected_values(record, entries, owner='self', canonical=True):
    result, refs = {}, set()
    for name, ref in record['selected'].items():
        item = reference(entries, ref, owner)
        key = (item['ref']['origin'], item['ref']['receipt'])
        require(key not in refs and item['action'] == 'download' and item['remote_path'] == name, 'unique_chosen_request')
        refs.add(key)
        if canonical:
            require(item['ref'] == choose(entries, name)['ref'], 'noncanonical_or_ambiguous_selection')
        result[name] = item['body']
    return result


def check_fresh_fences(record, entries, owner='self'):
    for phase in ('before', 'after'):
        item = reference(entries, record[phase], owner)
        require(item['ref']['origin'] == owner and item['action'] == 'observe' and item['phase'] == phase,
                'fresh_same_invocation_observation_required')
        check_observation(read(item['body'].parent, item['body'].name))
        mapping = record['metadata_' + phase]
        require(set(mapping) == set(PARENT), 'fresh_metadata_inventory')
        for name, ref in mapping.items():
            fresh = reference(entries, ref, owner)
            require(fresh['ref']['origin'] == owner and fresh['action'] == 'download'
                    and fresh['remote_path'] == name and fresh['phase'] == 'metadata_' + phase,
                    'fresh_metadata_receipt_required')
            require(fresh['identity'] == choose(entries, name)['identity'], 'changed_metadata_fence')
    require(record['before'] != record['after'], 'distinct_observation_fences')
    before = reference(entries, record['before'], owner)
    after = reference(entries, record['after'], owner)
    own = [x for x in entries if x['ref']['origin'] == owner]
    # Failed initial observations precede the successful baseline; they remain
    # audited history. Every download and all later observation attempts must
    # lie inside the successful same-UUID baseline/final interval.
    require(all(x == before or (x['action'] == 'observe' and x['phase'] == 'before' and not x['success']
                and utc(x['finished_utc']) <= utc(before['started_utc']))
                or utc(x['started_utc']) >= utc(before['finished_utc']) for x in own)
            and all(x == after or utc(x['finished_utc']) <= utc(after['started_utc']) for x in own),
            'observation_interval_must_surround_attempts')


def check_input_metadata(root, record):
    snapshot = check_source(root / 'source')
    require(record['recovery_sha256'] == sha(read(root, 'recovery_source.py')) == sha(Path(__file__).read_bytes()), 'recovery_source_pin')
    require(set(record['input_sha256']) == set(snapshot['upload_sha256']) | {'snapshot.json', 'reana.yaml', 'plan.json', 'payload.json'},
            'recovery_input_inventory')
    require(inventory(root / 'source') == {name: dict(bytes=identity(safe(root / 'source', name))['bytes'], sha256=digest)
            for name, digest in record['input_sha256'].items()}, 'recovery_input_hashes')
    for name, digest in record['helper_sha256'].items():
        require(name in HELPERS and identity(safe(root / 'helpers', name))['sha256'] == digest == snapshot['source_sha256'][name], 'helper_pin')
    require(set(record['helper_sha256']) == set(HELPERS), 'helper_inventory')
    require(set(inventory(root / 'helpers')) == set(HELPERS), 'exact_helper_file_inventory')
    allowed = {'source', 'helpers', 'origins', 'attempts', 'export', 'recovery_source.py', 'recovery.json',
               'submission_original.json', 'files.sha256.json', 'failed_complete_candidate.json',
               'failed_complete_candidate_manifest.json'}
    require({p.name for p in root.iterdir()} <= allowed and record['source_revision'] == REVISION, 'recovery_layout_generation')
    if (root / 'origins').exists():
        require({p.name for p in (root / 'origins').iterdir()} == {x + '.json' for x in record['origins']}, 'origin_manifest_inventory')
    for value in record['origins'].values():
        require(set(value) == {'locator_hint', 'resolver_required'} and value['resolver_required'] is True
                and type(value['locator_hint']) is str and Path(value['locator_hint']).is_absolute(), 'origin_locator_schema')
    original = read(root, 'submission_original.json')
    require(sha(original) == record['submission_sha256'] == SUBMISSION
            and parse(original) == {WORKFLOW: {'status': 'submitted'}}, 'original_submission')
    require(sha(read(root / 'source', 'plan.json')) == PLAN
            and sha(read(root / 'source', 'payload.json')) == PAYLOAD, 'original_plan_payload_bytes')
    plan, payload = (parse(read(root / 'source', name)) for name in ('plan.json', 'payload.json'))
    require(plan['schema'] == 'openmhd.galaxy-build-plan.v1' and plan['source_revision'] == REVISION
            and plan['snapshot_sha256'] == SNAPSHOT and plan['component_accepted'] is False
            and len(plan['cases']) == 1 and plan['cases'][0]['directory'] == '.'
            and plan['cases'][0]['workflow'] == WORKFLOW
            and plan['cases'][0]['workflow_sha256'] == snapshot['workflow_sha256']
            and plan['cases'][0]['payload_sha256'] == sha(read(root / 'source', 'payload.json')), 'original_prepared_plan')
    expected_inputs = {name: record['input_sha256'][name] for name in ('snapshot.json', *snapshot['upload_sha256'])}
    require(payload['schema'] == 'openmhd.galaxy-build-payload.v1' and payload['input_sha256'] == expected_inputs, 'original_prepared_payload')
    return snapshot


def verify(root, paths):
    closed(root)
    record, own = scan(root, 'self')
    require(record['schema'] == SCHEMA and record['status'] == 'complete'
            and record['physical_accepted'] is False and record['component_accepted'] is False,
            'recovery_not_complete')
    check_input_metadata(root, record)
    roots, history, entries = load_origins(paths)
    require(set(roots) == set(record['origins']), 'exact_origin_resolver_coverage')
    for digest, path in roots.items():
        require(read(root, 'origins/' + digest + '.json') == read(path, 'files.sha256.json'), 'retained_origin_manifest')
    entries += own
    # Verify even unselected history receipts and each prior selection; a
    # reference to a failed body, unknown child, or absent ancestor is fatal.
    for digest, previous in history.items():
        if previous['schema'] == SCHEMA:
            check_input_metadata(roots[digest], previous)
            previous_entries = [x for x in entries if x['ref']['origin'] == digest or x['ref']['origin'] in previous['origins']]
            values = selected_values(previous, previous_entries, digest, canonical=False)
            if previous['status'] == 'complete':
                check_fresh_fences(previous, previous_entries, digest)
                validate_material(roots[digest], values)
    check_fresh_fences(record, entries)
    values = selected_values(record, entries)
    require(all(x['action'] != 'download' or x['remote_path'] in values for x in entries), 'unexpected_logical_request')
    result = validate_material(root, values)
    require(record['verification'] == result
            and all(type(record['verification'][name]) is int for name in result), 'offline_verification_result_link')
    # End fences read every origin closure and this closure again. No mutable
    # development tree, HTTP or executable is consulted by this action.
    for digest, path in roots.items():
        require(closed(path) == digest, 'origin_changed_during_verification')
    closed(root)
    return result


def recover(source, submission, repo, paths, output):
    require(not output.exists(), 'fresh_recovery_destination_required')
    safe(output.parent, output.name)
    output.mkdir(parents=True)
    record = dict(schema=SCHEMA, status='incomplete', workflow=WORKFLOW, uuid=UUID, snapshot_sha256=SNAPSHOT,
        source_revision=REVISION, component_accepted=False, physical_accepted=False, started_utc=now(),
        origins={}, selected={}, metadata_before={}, metadata_after={}, before=None, after=None,
        verification=None, failure=None, execution_scope='GET-only opaque-byte recovery; zero test methods')
    roots, entries, captured = {}, [], {}
    try:
        snapshot = check_source(source)
        names = {'snapshot.json', 'reana.yaml', 'plan.json', 'payload.json', *snapshot['upload_sha256']}
        for name in sorted(names):
            raw = read(source, name)
            captured[name] = sha(raw)
            put(output / 'source', name, raw)
        record['input_sha256'] = captured
        raw = read(submission.parent, submission.name)
        put(output, 'submission_original.json', raw)
        record['submission_sha256'] = sha(raw)
        for name in HELPERS:
            raw = read(repo, name)
            require(sha(raw) == snapshot['source_sha256'][name], 'canonical_helper_differs_from_original_snapshot')
            put(output / 'helpers', name, raw)
        record['helper_sha256'] = {name: snapshot['source_sha256'][name] for name in HELPERS}
        recovery_raw = read(Path(__file__).absolute().parent, Path(__file__).name)
        put(output, 'recovery_source.py', recovery_raw)
        record['recovery_sha256'] = sha(recovery_raw)
        check_input_metadata(output, record)
        roots, history, entries = load_origins(paths)
        for digest, path in roots.items():
            put(output, 'origins/' + digest + '.json', read(path, 'files.sha256.json'))
            record['origins'][digest] = dict(locator_hint=str(path), resolver_required=True)
        persist(output, 'recovery.json', record)
        fetcher = Fetcher(output, entries)
        item = fetcher.fresh('observe', None, 'before')
        record['before'] = item['ref']
        for name in PARENT:
            fresh = fetcher.fresh('download', name, 'metadata_before')
            record['metadata_before'][name] = fresh['ref']
            record['selected'][name] = choose(fetcher.entries, name)['ref']
            persist(output, 'recovery.json', record)
        values = selected_values(record, fetcher.entries)
        required = descriptors(values)
        for name, expected in required.items():
            record['selected'][name] = fetcher.obtain(name, expected)['ref']
            persist(output, 'recovery.json', record)
        for name in PARENT:
            fresh = fetcher.fresh('download', name, 'metadata_after')
            record['metadata_after'][name] = fresh['ref']
            choose(fetcher.entries, name)  # Must remain identical to all earlier successes.
        record['after'] = fetcher.fresh('observe', None, 'after')['ref']
        check_fresh_fences(record, fetcher.entries)
        values = selected_values(record, fetcher.entries)
        record['verification'] = validate_material(output, values, extract=True)
        require(all(sha(read(source, name)) == digest for name, digest in captured.items())
                and sha(read(submission.parent, submission.name)) == record['submission_sha256'], 'original_inputs_changed')
        require(all(sha(read(repo, name)) == digest for name, digest in record['helper_sha256'].items()), 'canonical_helpers_changed')
        for digest, path in roots.items():
            require(closed(path) == digest, 'history_changed_during_recovery')
        record.update(status='complete', finished_utc=now())
    except BaseException as error:
        record.update(status='incomplete', finished_utc=now(), failure=type(error).__name__,
                      failure_code=str(error) if isinstance(error, Invalid) else 'unavailable_or_invalid_input',
                      external_terminal_evidence_required=True)
        raise
    finally:
        persist(output, 'recovery.json', record)
        put(output, 'files.sha256.json', encode(inventory(output)))
    try:
        return verify(output, paths)
    except BaseException as error:
        # Preserve the unsuccessful candidate and its exact closure instead of
        # leaving a closed "complete" flag after a failed final offline check.
        put(output, 'failed_complete_candidate.json', read(output, 'recovery.json'))
        put(output, 'failed_complete_candidate_manifest.json', read(output, 'files.sha256.json'))
        (output / 'files.sha256.json').unlink()
        record.update(status='incomplete', failure=type(error).__name__,
                      failure_code=str(error) if isinstance(error, Invalid) else 'offline_unavailable_or_invalid_input',
                      external_terminal_evidence_required=True)
        persist(output, 'recovery.json', record)
        put(output, 'files.sha256.json', encode(inventory(output)))
        raise


def main(argv=None):
    require(__debug__ and sys.flags.optimize == 0, 'optimized_rejected')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    take = sub.add_parser('recover')
    for name in ('source', 'submission', 'repo', 'output'):
        take.add_argument('--' + name, type=Path, required=True)
    take.add_argument('--history', type=Path, action='append', required=True)
    check = sub.add_parser('verify')
    check.add_argument('--packet', type=Path, required=True)
    check.add_argument('--origin', type=Path, action='append', required=True)
    args = parser.parse_args(argv)
    if args.action == 'recover':
        result = recover(args.source.absolute(), args.submission.absolute(), args.repo.absolute(),
                         args.history, args.output.absolute())
    else:
        result = verify(args.packet.absolute(), args.origin)
    print(json.dumps(dict(schema=SCHEMA, verified=result, component_accepted=False, physical_accepted=False)))


if __name__ == '__main__':
    main()
