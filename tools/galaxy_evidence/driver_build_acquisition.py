#!/usr/bin/env python3
"""Source proposal: authentic GET-only standalone-build acquisition/offline joins.

No submission, build, executable invocation or external-prerequisite attestation.
Imports are inert. Actual use requires the coordinator's real release and the
immutable REANA import/control prerequisite; this file has not been executed.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import types
import uuid

SCHEMA = 'openmhd.galaxy-driver-build-acquisition.v1'
AUTH_SCHEMA = 'openmhd.galaxy-driver-build-acquisition-release.v1'
TRANSPORT_SCHEMA = 'openmhd.galaxy-driver-build-get-attempt.v1'
SELF = 'tools/galaxy_evidence/driver_build_acquisition.py'
RECORDS = 'tools/galaxy_evidence/driver_build_records.py'
PREPARER = 'scripts/prepare_galaxy_driver_build.py'
ADAPTER = 'tools/galaxy_evidence/driver_build_readonly_adapter.py'
PINS = {
    RECORDS: '5ab7cb4bb87543a3f1ca0b744aeffa56501ad2b69d36457978622d58e465c73c',
    PREPARER: '490720e7b5c83af0fa1a98d2aa57b57cb2763f42d7850dbff17a82fbc07d4271',
    ADAPTER: 'eef5dee4fb788bec3da012b2e22a4292932b7534fb9e5395bf506bad1a601329',
    'tools/galaxy_evidence/readonly_adapter.py': 'c8986e20c1cc08cd9689387ead5ee5fd9c05653c469e16bcceae0fae2afe4591',
    'tools/m1_evidence/reana_metadata_readonly_adapter.py': '09a7f0cbaaa657eb6d84668dced7693c57c9784e78135adc86e72737ded79c4a',
}
PREFIX = 'outputs/galaxy-driver-build/'
LABELS = ('compiler', 'geometry', 'gravity')
FIXED = ('outputs/runtime.json', *[PREFIX + name for name in ('build.json', 'runtime.json', 'export.json', 'files.sha256.json')],
         *[PREFIX + label + '/' + name for label in LABELS for name in ('command.json', 'stdout.txt', 'stderr.txt')])
RETRY_CODES = frozenset(('network_error', 'adapter_deadline', 'incomplete_body'))
LIMIT = 3  # Per (action,path), shared by both fences, per explicit invocation.
BLOCK = 1024 * 1024
MAX_METADATA = 16 * BLOCK
MAX_FILE = 512 * BLOCK
MAX_ORIGIN_FILES = 32768
MAX_ORIGIN_TOTAL = 8 * 1024 ** 3


class Invalid(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise Invalid(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def descriptor(raw):
    return dict(bytes=len(raw), sha256=sha(raw))


def parse(raw):
    require(type(raw) is bytes and len(raw) <= MAX_METADATA, 'bounded_json_bytes')
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, 'duplicate_json_key')
            value[key] = item
        return value
    def finite(text):
        value = float(text)
        require(math.isfinite(value), 'nonfinite_json')
        return value
    return json.loads(raw, object_pairs_hook=pairs, parse_float=finite,
                      parse_constant=lambda _: (_ for _ in ()).throw(Invalid('nonfinite_json')))


def encode(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()


def same(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def keys(value, wanted, code):
    require(type(value) is dict and set(value) == set(wanted), code)


def digest(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value), 'digest')
    return value


def described(value, maximum=MAX_FILE, positive=False):
    keys(value, ('bytes', 'sha256'), 'descriptor_fields')
    require(type(value['bytes']) is int and int(positive) <= value['bytes'] <= maximum, 'descriptor_size')
    digest(value['sha256'])
    return value


def relative(name):
    require(type(name) is str and '\\' not in name and '\x00' not in name, 'relative_path_type')
    path = PurePosixPath(name)
    require(path.parts and path.as_posix() == name and not path.is_absolute() and '..' not in path.parts, 'relative_path')
    return name


def canonical(path):
    require(path.is_absolute() and path == path.absolute() and '..' not in path.parts, 'absolute_root')
    cursor = Path(path.anchor)
    for part in path.parts[1:]:
        cursor /= part
        require(not cursor.is_symlink(), 'linked_root')
    return path


def safe(root, name):
    canonical(root)
    cursor = root
    for part in PurePosixPath(relative(name)).parts:
        cursor /= part
        require(not cursor.is_symlink(), 'linked_path')
    return cursor


def read(root, name, maximum=MAX_METADATA):
    path = safe(root, name)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= maximum, 'regular_bounded_file')
        chunks, total = [], 0
        while True:
            block = os.read(fd, min(BLOCK, maximum + 1 - total))
            if not block:
                break
            chunks.append(block)
            total += len(block)
            require(total <= maximum, 'growing_file')
        after = os.fstat(fd)
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        require(total == after.st_size and all(getattr(before, key) == getattr(after, key) for key in fields)
                and all(getattr(path.stat(), key) == getattr(after, key) for key in fields), 'changed_file_generation')
        return b''.join(chunks)
    finally:
        os.close(fd)


def file_identity(root, name):
    path = safe(root, name)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= MAX_FILE, 'regular_bounded_file')
        total, hasher = 0, hashlib.sha256()
        while True:
            block = os.read(fd, BLOCK)
            if not block:
                break
            total += len(block)
            require(total <= MAX_FILE, 'growing_file')
            hasher.update(block)
        after = os.fstat(fd)
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        require(total == after.st_size and all(getattr(before, key) == getattr(after, key) for key in fields)
                and all(getattr(path.stat(), key) == getattr(after, key) for key in fields), 'changed_file_generation')
        return dict(bytes=total, sha256=hasher.hexdigest())
    finally:
        os.close(fd)


def put(root, name, raw):
    path = safe(root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def persist(root, name, value):
    path = safe(root, name)
    put(root, name + '.tmp', encode(value))
    os.replace(path.with_name(path.name + '.tmp'), path)  # Only journal/status, never a body.


def inventory(root, excluded=None):
    canonical(root)
    result, total = {}, 0
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(), 'linked_inventory')
        if path.is_dir():
            continue
        name = path.relative_to(root).as_posix()
        if name == excluded:
            continue
        result[name] = file_identity(root, name)
        total += result[name]['bytes']
        require(len(result) <= MAX_ORIGIN_FILES and total <= MAX_ORIGIN_TOTAL, 'inventory_resource_limit')
    return result


def closed(root):
    raw = read(root, 'files.sha256.json')
    require(same(parse(raw), inventory(root, 'files.sha256.json')), 'closed_inventory')
    return descriptor(raw)


def load_module(raw, path, name):
    value = types.ModuleType(name)
    value.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), value.__dict__)
    return value


def apis(packet):
    held = {}
    for name, pin in PINS.items():
        held[name] = read(packet / 'host', name)
        require(sha(held[name]) == pin, 'host_dependency_pin')
    return (load_module(held[RECORDS], packet / 'host' / RECORDS, 'driver_build_records_held'),
            load_module(held[PREPARER], packet / 'host' / PREPARER, 'driver_build_preparer_held'))


def authorization(value):
    keys(value, ('schema', 'workflow', 'uuid', 'source_revision', 'snapshot', 'submission', 'build_release',
                 'host_source_sha256', 'origins', 'receipts', 'prerequisite_outputs', 'coordinator_authorized',
                 'external_prerequisite_truth_verified', 'component_accepted'), 'authorization_fields')
    require(value['schema'] == AUTH_SCHEMA and value['coordinator_authorized'] is True
            and value['external_prerequisite_truth_verified'] is False and value['component_accepted'] is False,
            'coordinator_release_required')
    require(type(value['workflow']) is str and re.fullmatch('[a-z][a-z0-9-]{0,62}\\.1', value['workflow']), 'original_version_one')
    try:
        identifier = uuid.UUID(value['uuid']) if type(value['uuid']) is str else None
    except (ValueError, AttributeError):
        raise Invalid('canonical_uuid') from None
    require(identifier is not None and str(identifier) == value['uuid'] and identifier.version == 4, 'canonical_uuid')
    require(type(value['source_revision']) is str and re.fullmatch('[0-9a-f]{40}', value['source_revision']), 'source_revision')
    for name in ('snapshot', 'submission', 'build_release'):
        described(value[name], MAX_METADATA, True)
    host = value['host_source_sha256']
    keys(host, (*PINS, SELF), 'host_source_inventory')
    for name, pin in host.items():
        digest(pin)
        require(name == SELF or pin == PINS[name], 'host_source_pin')
    origins = value['origins']
    require(type(origins) is dict and 1 <= len(origins) <= 8, 'explicit_origin_inventory')
    for name, row in origins.items():
        require(type(name) is str and re.fullmatch('[a-z][a-z0-9_]{0,47}', name), 'origin_label')
        keys(row, ('manifest_path', 'manifest'), 'origin_descriptor')
        relative(row['manifest_path'])
        described(row['manifest'], MAX_METADATA, True)
    require(value['prerequisite_outputs'] in origins, 'actual_prerequisite_origin_required')
    keys(value['receipts'], ('preflight_review', 'coordinator_release', 'source_preparation_command',
                            'submission_command'), 'prerequisite_receipt_roles')
    for row in value['receipts'].values():
        keys(row, ('origin', 'path', 'descriptor'), 'receipt_descriptor')
        require(row['origin'] in origins, 'receipt_origin')
        relative(row['path'])
        described(row['descriptor'], MAX_METADATA, True)
    return value


def check_origins(packet, auth, roots, capture=False):
    require(set(roots) == set(auth['origins']), 'exact_explicit_origins')
    seen = set()
    for label, root in roots.items():
        canonical(root)
        row = auth['origins'][label]
        raw = read(root, row['manifest_path'])
        require(descriptor(raw) == row['manifest'], 'origin_manifest_identity')
        require(str(root) not in seen, 'duplicate_origin_root')
        seen.add(str(root))
        value = parse(raw)
        # Auth pins the complete manifest buffer. Support the two documented
        # retained manifest shapes, never implicit paths from either shape.
        entries = value['files'] if type(value) is dict and type(value.get('files')) is dict else value
        require(type(entries) is dict and 0 < len(entries) <= MAX_ORIGIN_FILES, 'origin_manifest_entries')
        for name, expected in entries.items():
            relative(name)
            described(expected)
        require(row['manifest_path'] not in entries and same(entries, inventory(root, row['manifest_path'])), 'origin_exact_closure')
        target = 'origins/' + label + '.json'
        if capture:
            put(packet, target, raw)
        else:
            require(read(packet, target) == raw, 'retained_origin_manifest')
    for role, row in auth['receipts'].items():
        raw = read(roots[row['origin']], row['path'])
        require(descriptor(raw) == row['descriptor'], 'prerequisite_receipt_bytes')
        if capture:
            put(packet, 'prerequisites/' + role, raw)
        else:
            require(read(packet, 'prerequisites/' + role) == raw, 'retained_prerequisite_receipt')


def validate_inputs(packet, auth, preparer):
    snapshot_raw = read(packet / 'source', 'snapshot.json')
    submission_raw = read(packet, 'submission_original.json')
    release_raw = read(packet / 'source', 'build_release.json')
    for key, raw in (('snapshot', snapshot_raw), ('submission', submission_raw), ('build_release', release_raw)):
        require(descriptor(raw) == auth[key], 'authorized_input_' + key)
    snapshot, release, submission = parse(snapshot_raw), parse(release_raw), parse(submission_raw)
    require(snapshot.get('dirty_status') == '' and snapshot.get('source_revision') == auth['source_revision']
            and release.get('source_revision') == auth['source_revision'], 'released_source_generation')
    require(snapshot.get('source_sha256', {}).get(PREPARER) == PINS[PREPARER], 'actual_original_preparer_pin')
    require(type(submission) is dict and set(submission) == {auth['workflow']}
            and type(submission[auth['workflow']]) is dict
            and submission[auth['workflow']].get('status') in ('submitted', 'submission uncertain'), 'original_submission_row')
    # Preserve an uncertain original row; requested UUID observations and the
    # coordinator's pinned original command evidence do not rewrite its ack.
    for role, field in (('preflight_review', 'preflight_review_sha256'), ('coordinator_release', 'coordinator_release_sha256')):
        require(sha(read(packet, 'prerequisites/' + role)) == release.get(field), 'original_release_receipt_' + role)
    require(snapshot.get('upload_sha256', {}).get('build_release.json') == sha(release_raw), 'release_upload_pin')
    inputs = {'snapshot.json', 'reana.yaml', *snapshot['upload_sha256']}
    require(set(inventory(packet / 'source')) == inputs, 'exact_original_input_capture')
    for name, pin in snapshot['upload_sha256'].items():
        digest(pin)
        require(file_identity(packet / 'source', name)['sha256'] == pin, 'original_upload_identity')
    spec_raw = read(packet / 'source', 'reana.yaml')
    require(sha(spec_raw) == snapshot['workflow_sha256'] and same(parse(spec_raw), preparer.specification(snapshot)), 'original_build_specification')
    derivation = snapshot.get('workflow_derivation')
    require(type(derivation) is dict and derivation.get('schema') == 'openmhd.galaxy-driver-build-workflow.v1'
            and derivation.get('release_sha256') == sha(release_raw)
            and derivation.get('job_source_sha256') == preparer.PINS[preparer.JOB]
            and type(derivation.get('declared_build_jobs')) is int and derivation['declared_build_jobs'] == 4
            and derivation.get('declared_memory') == '8Gi'
            and type(derivation.get('test_methods_to_execute')) is int and derivation['test_methods_to_execute'] == 0
            and type(derivation.get('numerical_cases_to_execute')) is int and derivation['numerical_cases_to_execute'] == 0
            and derivation.get('external_prerequisite_truth_verified') is False
            and derivation.get('component_accepted') is False, 'original_workflow_derivation')
    digest(derivation['base_workflow_sha256'])
    require(type(snapshot.get('compact_history')) is bool and snapshot['compact_history'] is True
            and snapshot.get('revision_scope') == 'private one-commit export fixture'
            and type(snapshot.get('revision')) is str and re.fullmatch('[0-9a-f]{40}', snapshot['revision']), 'explicit_compact_revision_scope')
    return snapshot_raw, release_raw, snapshot


def source_buffers(packet, snapshot):
    require(set(snapshot['archives']) == {'source.tar.gz', 'source.bundle'}, 'two_original_archives')
    result, used, source_total = {}, set(), 0
    with tempfile.TemporaryDirectory(prefix='openmhd-driver-source-') as directory:
        for name, row in snapshot['archives'].items():
            relative(name)
            require(type(row['parts']) is list and row['parts'] and len(row['parts']) <= 512, 'source_archive_parts')
            digest(row['sha256'])
            target = Path(directory) / name
            hasher, total = hashlib.sha256(), 0
            with target.open('xb') as stream:
                for index, part in enumerate(row['parts']):
                    require(part == name + '.part' + str(index).zfill(3) and part not in used, 'original_archive_part_order')
                    used.add(part)
                    raw = read(packet / 'source', part, BLOCK)
                    require(raw and sha(raw) == snapshot['upload_sha256'][part], 'original_archive_part_bytes')
                    total += len(raw)
                    require(total <= MAX_FILE, 'source_archive_bound')
                    hasher.update(raw)
                    stream.write(raw)
            require(hasher.hexdigest() == row['sha256'], 'source_archive_digest')
            if name != 'source.tar.gz':
                continue
            with tarfile.open(target, mode='r|gz') as archive:
                for member in archive:
                    require(member.isfile() and member.name in snapshot['source_sha256']
                            and member.name not in result and 0 <= member.size <= MAX_METADATA, 'exact_regular_source_member')
                    relative(member.name)
                    raw = archive.extractfile(member).read(MAX_METADATA + 1)
                    require(len(raw) == member.size and sha(raw) == snapshot['source_sha256'][member.name], 'source_member_bytes')
                    source_total += len(raw)
                    require(source_total <= MAX_FILE and len(result) < 10000, 'selected_source_bound')
                    result[member.name] = raw
    require(set(snapshot['upload_sha256']) == used | {'remote.py', 'build_release.json'}
            and set(result) == set(snapshot['source_sha256']), 'complete_source_and_upload_inventory')
    return result


def utc(value):
    require(type(value) is str, 'utc_text')
    value = datetime.fromisoformat(value)
    require(value.tzinfo is not None and value.utcoffset().total_seconds() == 0, 'utc_zone')
    return value


def now():
    return datetime.now(timezone.utc).isoformat()


def observation(raw, auth, finished=True):
    value = parse(raw)
    require(value.get('schema') == 'openmhd.galaxy-server-observation.v1' and value.get('origin') == 'server', 'server_observation')
    utc(value['observed_utc'])
    require(type(value.get('matches')) is list and len(value['matches']) == 1, 'unique_requested_workflow')
    row = value['matches'][0]
    require(type(row) is dict and type(row.get('version')) is int and row['version'] == 1
            and row.get('workflow') == auth['workflow'] and row.get('name') == auth['workflow'][:-2]
            and row.get('id') == auth['uuid'], 'requested_uuid_version')
    require(not finished or row.get('status') == 'finished', 'finished_build_required')
    return row


def diagnostic(raw):
    value = parse(raw)
    require(type(value) is dict and value.get('schema') == 'openmhd.galaxy-get-diagnostic.v1', 'typed_diagnostic')
    return value


def retain_log(raw):
    try:
        diagnostic(raw)
        return raw
    except (ValueError, KeyError, TypeError):
        return encode(dict(schema='openmhd.galaxy-unavailable-diagnostic.v1', bytes=len(raw), sha256=sha(raw)))


def remote_path(name):
    require(type(name) is str and (name in FIXED or re.fullmatch(PREFIX + r'parts/(geometry|gravity)\.part[0-9]{4}', name)), 'download_path')
    if name not in FIXED:
        require(int(name[-4:]) < 512, 'part_range')
    return name


def retryable(row, diag):
    require(row['outcome'] not in ('intent', 'unknown_lifecycle', 'running'), 'unknown_lifecycle')
    if row['outcome'] == 'timeout':
        require(row.get('child_reaped') is True, 'timeout_not_reaped')
        return True
    return row['outcome'] == 'nonzero' and diag is not None and diag.get('code') in RETRY_CODES


def audit_attempt(packet, number, auth):
    folder = 'attempts/' + number
    require(re.fullmatch('[0-9]{6}', number), 'attempt_number')
    raw = read(packet, folder + '/result.json')
    row, intent = parse(raw), parse(read(packet, folder + '/intent.json'))
    require(row['schema'] == intent['schema'] == TRANSPORT_SCHEMA and intent['outcome'] == 'intent'
            and intent['pid'] is None and intent['returncode'] is None and intent['child_reaped'] is False,
            'attempt_intent_schema')
    require(row['intent_sha256'] == sha(read(packet, folder + '/intent.json'))
            and all(same(row[key], intent[key]) for key in ('argv', 'cwd', 'workflow', 'uuid', 'action', 'remote_path',
                'phase', 'timeout_seconds', 'interpreter', 'host_source_sha256', 'started_utc')), 'intent_result_links')
    require(row['workflow'] == auth['workflow'] and row['uuid'] == auth['uuid']
            and same(row['host_source_sha256'], auth['host_source_sha256']), 'attempt_source_identity')
    require(row['action'] in ('observe', 'download') and (row['remote_path'] is None) == (row['action'] == 'observe'), 'attempt_action')
    if row['remote_path'] is not None:
        remote_path(row['remote_path'])
    cwd = PurePosixPath(row['cwd'])
    require(cwd.is_absolute() and cwd.as_posix() == row['cwd'] and '..' not in cwd.parts, 'original_attempt_cwd')
    interpreter = row['interpreter']
    require(type(interpreter) is dict and type(interpreter.get('python')) is str and interpreter['python']
            and interpreter.get('implementation') == 'cpython' and type(interpreter.get('optimized')) is int
            and interpreter['optimized'] == 0 and type(interpreter.get('executable')) is str
            and Path(interpreter['executable']).is_absolute(), 'actual_interpreter')
    expected = [interpreter['executable'], '-B', str(cwd / 'host' / ADAPTER), row['action'], '--workflow', auth['workflow'],
                '--output', str(cwd / folder / 'body')]
    if row['remote_path'] is not None:
        expected += ['--path', row['remote_path']]
    require(row['argv'] == expected and type(row['timeout_seconds']) is int and row['timeout_seconds'] == 300,
            'exact_direct_adapter_argv')
    launch = parse(read(packet, folder + '/launch.json'))
    require(type(row.get('pid')) is int and row['pid'] > 0 and row.get('child_reaped') is True
            and type(launch.get('pid')) is int and launch['pid'] == row['pid'] and launch['argv'] == expected
            and utc(row['started_utc']) <= utc(launch['launched_utc']) <= utc(row['finished_utc'])
            and type(row['seconds']) in (int, float) and math.isfinite(row['seconds']) and row['seconds'] >= 0,
            'settled_launch_and_reaping')
    for channel in ('stdout', 'stderr'):
        require(row[channel] == folder + '/' + channel + '.json'
                and sha(read(packet, row[channel])) == row[channel + '_sha256'], 'transport_log_identity')
    success = row['outcome'] == 'success' and type(row['returncode']) is int and row['returncode'] == 0
    diag = None if row['outcome'] == 'timeout' else diagnostic(read(packet, row['stdout'] if success else row['stderr']))
    if diag is not None:
        require(diag['action'] == row['action'] and diag['workflow'] == auth['workflow']
                and diag['requested_path'] == row['remote_path'], 'diagnostic_request')
        require(utc(row['started_utc']) <= utc(diag['started_utc']) <= utc(diag['finished_utc'])
                <= utc(row['finished_utc']) and type(diag['page_count']) is int and diag['page_count'] >= 0,
                'diagnostic_interval_and_pages')
    body_name = folder + '/body'
    if success:
        require(diag['outcome'] == 'success' and diag['code'] == 'completed' and diag['workflow_ids'] == [auth['uuid']]
                and file_identity(packet, body_name) == row['body_identity']
                and not (packet / (body_name + '.partial')).exists(), 'successful_body_uuid_identity')
        require(type(diag['received_bytes']) is int and type(diag['retained_bytes']) is int
                and diag['received_bytes'] == diag['retained_bytes'] == row['body_identity']['bytes']
                and diag['partial_file'] is None and diag['page_count'] > 0, 'successful_diagnostic_bytes')
        if row['action'] == 'observe':
            observation(read(packet, body_name), auth, finished=False)
    else:
        require(row['outcome'] in ('nonzero', 'timeout') and type(row['returncode']) is int and row['returncode'] != 0,
                'failed_attempt_outcome')
        require(diag is None or diag['outcome'] == 'failure', 'failed_diagnostic')
        require(not (packet / body_name).exists(), 'failed_body_cannot_be_promoted')
        partial = body_name + '.partial'
        if (packet / partial).exists():
            require(file_identity(packet, partial) == row['partial_identity'], 'retained_partial_identity')
            require(diag is None or (diag['partial_file'] == 'body.partial'
                    and diag['retained_bytes'] == row['partial_identity']['bytes']), 'partial_diagnostic')
        else:
            require('partial_identity' not in row and (diag is None or
                    (diag.get('partial_file') is None and diag.get('retained_bytes', 0) == 0)),
                    'missing_retained_partial')
        require(retryable(row, diag), 'nonretryable_failure')
    require({path.name for path in (packet / folder).iterdir()} <= {
        'intent.json', 'launch.json', 'result.json', 'stdout.json', 'stderr.json', 'body', 'body.partial'}, 'attempt_extra_file')
    return dict(number=number, action=row['action'], remote_path=row['remote_path'], phase=row['phase'],
                started_utc=row['started_utc'], finished_utc=row['finished_utc'], success=success,
                body=body_name if success else None, identity=row['body_identity'] if success else None)


def attempt(packet, auth, action, remote, phase, number):
    require(action in ('observe', 'download') and (remote is None) == (action == 'observe'), 'attempt_action')
    folder = 'attempts/' + number
    safe(packet, folder).mkdir(parents=True, exist_ok=False)
    argv = [sys.executable, '-B', str(packet / 'host' / ADAPTER), action, '--workflow', auth['workflow'],
            '--output', str(packet / folder / 'body')]
    if remote is not None:
        remote_path(remote)
        argv += ['--path', remote]
    row = dict(schema=TRANSPORT_SCHEMA, argv=argv, cwd=str(packet), workflow=auth['workflow'], uuid=auth['uuid'],
               action=action, remote_path=remote, phase=phase, timeout_seconds=300, started_utc=now(),
               finished_utc=None, outcome='intent', returncode=None, pid=None, child_reaped=False,
               host_source_sha256=auth['host_source_sha256'], interpreter=dict(executable=sys.executable,
               python=sys.version, implementation=sys.implementation.name, optimized=sys.flags.optimize))
    put(packet, folder + '/intent.json', encode(row))
    row['intent_sha256'] = sha(read(packet, folder + '/intent.json'))
    child, stdout, stderr = None, b'', b''
    started = time.monotonic()
    try:
        child = subprocess.Popen(argv, cwd=packet, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        row['pid'] = child.pid
        put(packet, folder + '/launch.json', encode(dict(pid=child.pid, argv=argv, launched_utc=now())))
        try:
            stdout, stderr = child.communicate(timeout=300)
            row.update(outcome='success' if child.returncode == 0 else 'nonzero', returncode=child.returncode, child_reaped=True)
        except subprocess.TimeoutExpired:
            child.kill()  # The only child is the pinned, single-process GET adapter.
            stdout, stderr = child.communicate()
            row.update(outcome='timeout', returncode=child.returncode, child_reaped=True)
    except BaseException:
        if child is not None and not row['child_reaped']:
            try:
                child.kill()
                stdout, stderr = child.communicate(timeout=15)
                row.update(returncode=child.returncode, child_reaped=True)
            except BaseException:
                pass
        row['outcome'] = 'unknown_lifecycle'
    finally:
        row.update(finished_utc=now(), seconds=time.monotonic() - started)
        for channel, raw in (('stdout', stdout), ('stderr', stderr)):
            row[channel] = folder + '/' + channel + '.json'
            held = retain_log(raw)
            put(packet, row[channel], held)
            row[channel + '_sha256'] = sha(held)
        for suffix, key in (('', 'body_identity'), ('.partial', 'partial_identity')):
            name = folder + '/body' + suffix
            if (packet / name).exists():
                row[key] = file_identity(packet, name)
        put(packet, folder + '/result.json', encode(row))
    return audit_attempt(packet, number, auth)


class Fetcher:
    def __init__(self, packet, auth):
        self.packet, self.auth, self.entries, self.counts = packet, auth, [], {}

    def fresh(self, action, remote, phase):
        key = (action, remote)
        while self.counts.get(key, 0) < LIMIT:
            self.counts[key] = self.counts.get(key, 0) + 1
            number = str(len(list((self.packet / 'attempts').glob('*/intent.json')))).zfill(6)
            row = attempt(self.packet, self.auth, action, remote, phase, number)
            self.entries.append(row)
            if row['success']:
                return row
        raise Invalid('transport_attempt_bound')


def choose(entries, remote):
    rows = [row for row in entries if row['success'] and row['action'] == 'download' and row['remote_path'] == remote]
    require(rows, 'missing_successful_body')
    require(len({row['number'] for row in rows}) == len(rows), 'duplicate_receipt')
    require(all(same(row['identity'], rows[0]['identity']) for row in rows), 'changed_successful_body')
    return min(rows, key=lambda row: row['number'])


def discovered_paths(metadata):
    require(set(metadata) == set(FIXED), 'fixed_metadata_inventory')
    build = parse(metadata[PREFIX + 'build.json'])
    require(build.get('schema') == 'openmhd.galaxy-driver-build.v1' and build.get('status') == 'complete'
            and build.get('component_accepted') is False and build.get('external_terminal_evidence_required') is False,
            'complete_build_before_part_discovery')
    records = build.get('binaries')
    require(type(records) is list and len(records) == 2 and [row.get('kind') for row in records] == ['geometry', 'gravity'], 'two_example_inventory')
    result = set(FIXED)
    for row in records:
        parts = row.get('parts')
        require(type(parts) is list and 1 <= len(parts) <= 512, 'part_descriptor_inventory')
        for index, part in enumerate(parts):
            keys(part, ('path', 'bytes', 'sha256'), 'part_descriptor_fields')
            require(part['path'] == 'parts/' + row['kind'] + '.part' + str(index).zfill(4), 'part_descriptor_order')
            described({key: part[key] for key in ('bytes', 'sha256')}, BLOCK, True)
            result.add(remote_path(PREFIX + part['path']))
    return result


def packet_attempts(packet, auth):
    folders = sorted((packet / 'attempts').iterdir())
    require([path.name for path in folders] == [str(index).zfill(6) for index in range(len(folders))], 'contiguous_attempt_inventory')
    entries, counts = [], {}
    for path in folders:
        require(path.is_dir() and not path.is_symlink(), 'attempt_directory')
        row = audit_attempt(packet, path.name, auth)
        require(not entries or utc(entries[-1]['finished_utc']) <= utc(row['started_utc']),
                'serial_attempt_intervals')
        entries.append(row)
        key = (row['action'], row['remote_path'])
        counts[key] = counts.get(key, 0) + 1
    require(all(value <= LIMIT for value in counts.values()), 'offline_retry_bound')
    return entries


def fences(packet, auth, record, entries):
    def linked(number):
        rows = [row for row in entries if row['number'] == number and row['success']]
        require(len(rows) == 1, 'successful_fence_receipt')
        return rows[0]
    before, after = linked(record['before']), linked(record['after'])
    require(before['number'] != after['number'] and before['action'] == after['action'] == 'observe'
            and before['phase'] == 'before' and after['phase'] == 'after', 'two_observation_receipts')
    require(same(observation(read(packet, before['body']), auth), observation(read(packet, after['body']), auth)), 'stable_finished_uuid')
    for row in entries:
        initial_failure = row['action'] == 'observe' and row['phase'] == 'before' and not row['success']
        require(row == before or (initial_failure and utc(row['finished_utc']) <= utc(before['started_utc']))
                or utc(row['started_utc']) >= utc(before['finished_utc']), 'download_before_baseline')
        require(row == after or utc(row['finished_utc']) <= utc(after['started_utc']), 'download_after_final_observation')
    for phase in ('before', 'after'):
        mapping = record['metadata_' + phase]
        require(set(mapping) == set(FIXED), 'fresh_fixed_metadata_inventory')
        for remote, number in mapping.items():
            row = linked(number)
            require(row['action'] == 'download' and row['remote_path'] == remote and row['phase'] == 'metadata_' + phase
                    and same(row['identity'], choose(entries, remote)['identity']), 'fresh_metadata_fence')


def selected_buffers(packet, record, entries):
    buffers, numbers = {}, set()
    for remote, number in record['selected'].items():
        row = choose(entries, remote)
        require(row['number'] == number and number not in numbers, 'canonical_unique_selection')
        numbers.add(number)
        raw = read(packet, row['body'])
        require(descriptor(raw) == row['identity'], 'selected_held_body_identity')
        buffers[remote] = raw
    require(all(row['action'] != 'download' or row['remote_path'] in buffers for row in entries), 'unexpected_download_request')
    return buffers


def material(packet, auth, record, entries, write=False):
    records, preparer = apis(packet)
    snapshot_raw, release_raw, snapshot = validate_inputs(packet, auth, preparer)
    buffers = selected_buffers(packet, record, entries)
    require(set(buffers) == discovered_paths({name: buffers[name] for name in FIXED}), 'complete_declared_download_inventory')
    result = records.verify_records(buffers, snapshot_raw, release_raw, source_buffers(packet, snapshot))
    runtime = parse(buffers[PREFIX + 'runtime.json'])
    # Records alone have no requested server UUID: add that concrete join here.
    job = PurePosixPath(runtime['job_path'])
    require(auth['uuid'] in job.parts and job.parts.count(auth['uuid']) == 1, 'requested_uuid_remote_workdir')
    build = parse(buffers[PREFIX + 'build.json'])
    for row in build['binaries']:
        name = row['path']
        relative(name)
        if write:
            path = safe(packet / 'export', name)
            path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                for part in row['parts']:
                    stream.write(buffers[PREFIX + part['path']])
                stream.flush()
                os.fsync(stream.fileno())
        require(file_identity(packet / 'export', name) == {key: row[key] for key in ('bytes', 'sha256')}, 'opaque_binary_reassembly')
    require(same(inventory(packet / 'export'), {row['path']: {key: row[key] for key in ('bytes', 'sha256')}
                 for row in build['binaries']}), 'exact_two_local_binary_copies')
    return result


def host_fence(packet, auth):
    require(set(inventory(packet / 'host')) == set(auth['host_source_sha256']), 'exact_host_capture')
    for name, expected in auth['host_source_sha256'].items():
        require(file_identity(packet / 'host', name)['sha256'] == expected, 'actual_host_source_fence')
    require(sha(read(packet / 'host', SELF)) == sha(read(Path(__file__).absolute().parent, Path(__file__).name)), 'invoked_acquisition_source')


def verify(packet, origins):
    canonical(packet)
    closed(packet)
    auth_raw = read(packet, 'authorization.json')
    auth = authorization(parse(auth_raw))
    record = parse(read(packet, 'acquisition.json'))
    require(record['schema'] == SCHEMA and record['status'] == 'complete' and record['authorization'] == descriptor(auth_raw)
            and record['workflow'] == auth['workflow'] and record['uuid'] == auth['uuid']
            and record['component_accepted'] is False and record['external_prerequisite_truth_verified'] is False
            and record['binary_execution_performed'] is False and record['physical_evolutions_performed'] is False,
            'complete_acquisition_scope')
    allowed = {'host', 'source', 'origins', 'prerequisites', 'export', 'attempts', 'authorization.json',
               'submission_original.json', 'acquisition.json', 'files.sha256.json'}
    require({path.name for path in packet.iterdir()} == allowed, 'complete_packet_layout')
    require(set(inventory(packet / 'origins')) == {name + '.json' for name in auth['origins']}
            and set(inventory(packet / 'prerequisites')) == set(auth['receipts']), 'exact_prerequisite_capture')
    host_fence(packet, auth)
    check_origins(packet, auth, origins)
    entries = packet_attempts(packet, auth)
    fences(packet, auth, record, entries)
    result = material(packet, auth, record, entries)
    require(same(result, record['record_validation'])
            and record['attempt_count'] == len(entries) and type(record['attempt_count']) is int, 'record_validation_and_attempt_count')
    check_origins(packet, auth, origins)
    host_fence(packet, auth)
    closed(packet)
    return dict(schema=SCHEMA, status='acquisition_consistent', records=result,
                component_accepted=False, external_prerequisite_truth_verified=False,
                binary_execution_performed=False)


def acquire(source, submission, authorization_path, repo, origins, output):
    require(__debug__ and sys.flags.optimize == 0, 'optimized_acquisition')
    for path in (source, submission.parent, authorization_path.parent, repo, output.parent):
        canonical(path)
    require(not output.exists() and not output.is_symlink(), 'fresh_acquisition_destination')
    auth_raw = read(authorization_path.parent, authorization_path.name)
    auth = authorization(parse(auth_raw))
    output.mkdir()
    record = dict(schema=SCHEMA, status='incomplete', authorization=descriptor(auth_raw),
        workflow=auth['workflow'], uuid=auth['uuid'], started_utc=now(), finished_utc=None,
        selected={}, metadata_before={}, metadata_after={}, before=None, after=None,
        component_accepted=False, external_prerequisite_truth_verified=False,
        binary_execution_performed=False, physical_evolutions_performed=False, record_validation=None, attempt_count=0,
        origin_locator_hints={label: str(path) for label, path in origins.items()})
    captured = {}
    try:
        put(output, 'authorization.json', auth_raw)
        put(output, 'submission_original.json', read(submission.parent, submission.name))
        snapshot_raw = read(source, 'snapshot.json')
        snapshot = parse(snapshot_raw)
        for name in sorted({'snapshot.json', 'reana.yaml', *snapshot['upload_sha256']}):
            raw = read(source, name, MAX_FILE)
            captured[name] = descriptor(raw)
            put(output / 'source', name, raw)
        for name, pin in auth['host_source_sha256'].items():
            raw = read(repo, name)
            require(sha(raw) == pin, 'live_host_source_pin')
            put(output / 'host', name, raw)
        host_fence(output, auth)
        check_origins(output, auth, origins, capture=True)
        records, preparer = apis(output)
        _, _, snapshot = validate_inputs(output, auth, preparer)
        records.source_records(snapshot, source_buffers(output, snapshot))
        persist(output, 'acquisition.json', record)
        fetcher = Fetcher(output, auth)
        record['before'] = fetcher.fresh('observe', None, 'before')['number']
        observation(read(output, 'attempts/' + record['before'] + '/body'), auth)
        metadata = {}
        for remote in FIXED:
            row = fetcher.fresh('download', remote, 'metadata_before')
            record['metadata_before'][remote] = row['number']
            record['selected'][remote] = row['number']
            metadata[remote] = read(output, row['body'])
            persist(output, 'acquisition.json', record)
        for remote in sorted(discovered_paths(metadata) - set(FIXED)):
            row = fetcher.fresh('download', remote, 'parts')
            record['selected'][remote] = row['number']
            persist(output, 'acquisition.json', record)
        # Refresh every fixed original buffer, not just its self-described digest.
        for remote in FIXED:
            row = fetcher.fresh('download', remote, 'metadata_after')
            record['metadata_after'][remote] = row['number']
            choose(fetcher.entries, remote)
        record['after'] = fetcher.fresh('observe', None, 'after')['number']
        fences(output, auth, record, fetcher.entries)
        record['record_validation'] = material(output, auth, record, fetcher.entries, write=True)
        record['attempt_count'] = len(fetcher.entries)
        for name, expected in captured.items():
            require(file_identity(source, name) == expected, 'original_input_generation_changed')
        require(read(submission.parent, submission.name) == read(output, 'submission_original.json')
                and read(authorization_path.parent, authorization_path.name) == auth_raw, 'original_release_or_submission_changed')
        for name, pin in auth['host_source_sha256'].items():
            require(file_identity(repo, name)['sha256'] == pin, 'live_host_source_changed')
        check_origins(output, auth, origins)
        host_fence(output, auth)
        record.update(status='complete', finished_utc=now())
    except BaseException as error:
        record.update(status='incomplete', finished_utc=now(), error_type=type(error).__name__,
                      failure_code=str(error) if isinstance(error, Invalid) else 'unavailable_or_invalid_input',
                      external_terminal_evidence_required=True)
        raise
    finally:
        record['attempt_count'] = len(list((output / 'attempts').glob('*/intent.json')))
        persist(output, 'acquisition.json', record)
        put(output, 'files.sha256.json', encode(inventory(output)))
    try:
        return verify(output, origins)
    except BaseException as error:
        # Preserve rather than silently replace the unsuccessful complete view.
        put(output, 'failed_complete_candidate.json', read(output, 'acquisition.json'))
        put(output, 'failed_complete_candidate_manifest.json', read(output, 'files.sha256.json'))
        (output / 'files.sha256.json').unlink()
        record.update(status='incomplete', error_type=type(error).__name__,
                      failure_code=str(error) if isinstance(error, Invalid) else 'offline_verification_failed',
                      external_terminal_evidence_required=True)
        persist(output, 'acquisition.json', record)
        put(output, 'files.sha256.json', encode(inventory(output)))
        raise


def origin_arguments(values):
    result = {}
    for value in values:
        require(type(value) is str and '=' in value, 'explicit_origin_argument')
        label, path = value.split('=', 1)
        require(label not in result and path, 'duplicate_origin_argument')
        result[label] = Path(path).absolute()
    return result


def main(argv=None):
    require(__debug__ and sys.flags.optimize == 0, 'optimized_acquisition')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    take = sub.add_parser('acquire')
    for name in ('source', 'submission', 'authorization', 'repo', 'output'):
        take.add_argument('--' + name, type=Path, required=True)
    take.add_argument('--origin', action='append', required=True)
    check = sub.add_parser('verify')
    check.add_argument('--packet', type=Path, required=True)
    check.add_argument('--origin', action='append', required=True)
    args = parser.parse_args(argv)
    origins = origin_arguments(args.origin)
    if args.action == 'acquire':
        result = acquire(args.source.absolute(), args.submission.absolute(), args.authorization.absolute(),
                         args.repo.absolute(), origins, args.output.absolute())
    else:
        result = verify(args.packet.absolute(), origins)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
