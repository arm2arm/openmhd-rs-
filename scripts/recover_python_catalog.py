"""Unadopted additive original175 recovery. Import is inert; execution is gated.

Never submits/runs a workflow or evaluates test/reference code. The only live
operation is the exact original GET adapter via original adapter_attempt(300s).
All validators/imports/control tests must first execute on REANA after review.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import threading
import uuid

REVISION = '01db01aabca98816e4716f3f8e38acde5988a1c4'
SNAPSHOT = '6fa4f3a347e43ae327917bbc629646d772cd06ae5daf6f230a74247d4bccf463'
PLAN = '4c1115accf3498a8fbcf1a0e5391411380eb7c11309f737ade18f3697f1cd5fa'
SUBMISSION = '68a4f4d94efe9db35784fd8ca865299e1c682a9315a85d264482d2a662f3f390'
UUID_INVENTORY = '2c3a3354ee6dbe1c376868f1c76bf7512c9f9d17dc13f99bb52b7f155705a931'
BASE_MANIFEST = 'ba8f10272983cbc6dd06d563cf2f978d6fd9a19f32c87357d4e9b299beb09dba'
HELPERS = {
    'reana_metadata_job.py': 'fb3b10c3464d63ce6e80c1277eeb56abc0e79b2ece0f88453e4bd90bd65aca7c',
    'prepare_metadata_reana.py': '6db628a8b182638cb7043504d347825738f0838cd6b06a0fe473330004e6b2d4',
    'collect_metadata_reana_results.py': '0fc378fb8ba9dcff208dc2c3b6ed6aff628010ba3fe89eab9349d74f24c5eb7c',
    'reana_metadata_readonly_adapter.py': '09a7f0cbaaa657eb6d84668dced7693c57c9784e78135adc86e72737ded79c4a',
}
MAX_FILE, MAX_FILES, MAX_TOTAL = 16 * 1024 * 1024, 32000, 4 * 1024 * 1024 * 1024
LOCK = threading.RLock()
SCOPE = {'physical_evolutions_run': False, 'component_accepted': False}


class RecoveryError(ValueError):
    """Semantic/identity/storage failure: no automatic retry."""


class UnknownAttempt(RecoveryError):
    """Pending/interrupted authority is not a settled transport loss."""


class TransportExhausted(RecoveryError):
    pass


def require(value, message):
    if not value:
        raise RecoveryError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def desc(raw):
    return dict(sha256=sha(raw), bytes=len(raw))


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def same(left, right):
    """JSON type-sensitive equality (not Python's True == 1)."""
    return encode(left) == encode(right)


def parse(raw):
    require(type(raw) is bytes and len(raw) <= MAX_FILE, 'Bounded metadata bytes')
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, 'Duplicate metadata key')
            value[key] = item
        return value
    def finite(text):
        value = float(text)
        require(math.isfinite(value), 'Nonfinite metadata')
        return value
    return json.loads(raw, object_pairs_hook=unique, parse_float=finite,
        parse_constant=lambda _: require(False, 'Nonfinite metadata'))


def now():
    return datetime.now(timezone.utc).isoformat()


def root_path(path):
    path = Path(path).absolute()
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        require(not current.is_symlink(), 'Linked root/ancestor')
    require(path.is_dir(), 'Existing directory required')
    return path


def read(root, name):
    relative = PurePosixPath(name)
    require(type(name) is str and relative.parts and not relative.is_absolute()
            and relative.as_posix() == name and '..' not in relative.parts, 'Relative regular path required')
    path = root_path(root)
    for part in relative.parts:
        path /= part
        require(not path.is_symlink(), 'Linked file/ancestor')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_size <= MAX_FILE, 'Bounded regular file')
        pieces, total = [], 0
        while True:
            block = os.read(fd, min(65536, MAX_FILE + 1 - total))
            if not block:
                break
            total += len(block)
            require(total <= MAX_FILE, 'File grew beyond bound')
            pieces.append(block)
        after, named = os.fstat(fd), path.stat()
        keys = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        require(all(getattr(before, k) == getattr(after, k) == getattr(named, k) for k in keys)
                and total == after.st_size, 'Changed held file generation')
        return b''.join(pieces)
    finally:
        os.close(fd)


def tree(root, exclude=()):
    root = root_path(root)
    files, directories, total = {}, [], 0
    for path in sorted(root.rglob('*')):
        require(len(files) + len(directories) < MAX_FILES, 'Tree entry resource bound')
        require(not path.is_symlink(), 'Linked tree entry')
        name = path.relative_to(root).as_posix()
        if path.is_dir():
            directories.append(name)
        else:
            require(path.is_file(), 'Nonregular tree entry')
            if name in exclude:
                continue
            raw = read(root, name)
            total += len(raw)
            require(len(files) < MAX_FILES and total <= MAX_TOTAL, 'Tree resource bound')
            files[name] = desc(raw)
    return dict(files=files, directories=directories)


def copy_tree(source, destination):
    source = root_path(source)
    require(not destination.exists() and source not in destination.parents, 'Fresh disjoint retained tree')
    before = tree(source)
    destination.mkdir(parents=True)
    for name in before['directories']:
        (destination / name).mkdir(parents=True, exist_ok=True)
    for name, expected in before['files'].items():
        raw = read(source, name)
        require(desc(raw) == expected, 'Changed original before copy')
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    require(tree(source) == tree(destination) == before, 'Changed original/retained tree')
    return before


def publish(path, value):
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('xb') as stream:
        stream.write(encode(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


@contextmanager
def frozen_api(directory):
    """Preserve old host_tools/read_source guards; no source patch or reload.

    Bare legacy imports get exact private objects under a serialized temporary
    namespace. All sys.modules entries and bytecode policy are restored. Only
    these reviewed validator definitions are loaded, never any test/source tree.
    """
    directory = root_path(directory)
    before = {name: read(directory, name) for name in HELPERS}
    require({name: sha(raw) for name, raw in before.items()} == HELPERS, 'Exact original helper bundle')
    with LOCK:
        names = ('reana_metadata_job', 'prepare_metadata_reana', 'collect_metadata_reana_results')
        saved = {name: (name in sys.modules, sys.modules.get(name)) for name in names}
        bytecode = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            for name in names:
                spec = importlib.util.spec_from_file_location(name, directory / (name + '.py'))
                module = importlib.util.module_from_spec(spec)
                sys.modules[name] = module
                spec.loader.exec_module(module)
            old = sys.modules[names[-1]]
            require({name: read(directory, name) for name in HELPERS} == before, 'Changed loaded helper bundle')
            yield old
            require({name: read(directory, name) for name in HELPERS} == before, 'Changed helper bundle after use')
        finally:
            for name in names:
                if not saved[name][0]:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = saved[name][1]
            sys.dont_write_bytecode = bytecode


def original_context(old, base):
    names = {n for n in old.file_names(base) if n.startswith(('shared/', 'inputs/'))}
    context = old.job.capture_files(base, names, attempts=1)
    snapshot, plan, submission = old.validate_context(context)
    require(sha(context['shared/snapshot.json']) == SNAPSHOT and snapshot['source_revision'] == REVISION
            and len(snapshot['tests']) == len(plan['cases']) == 175
            and sha(context['inputs/cases/plan.json']) == PLAN
            and sha(context['inputs/cases/submission.json']) == SUBMISSION, 'Original175 source/plan/submission only')
    require(all(snapshot['source_sha256'].get('tools/galaxy_python_evidence/' + n) == h
                for n, h in HELPERS.items()), 'Original helper/source guard')
    return context, snapshot, plan, submission


def original_ids(raw, plan):
    require(sha(raw) == UUID_INVENTORY, 'Original UUID inventory byte pin')
    rows = parse(raw)['rows']
    require(type(rows) is list and len(rows) == len(plan['cases']) == 175, 'Original UUID coverage')
    result = {}
    for entry, row in zip(plan['cases'], rows):
        value = row['value']
        require(row['directory'] == entry['directory'] and row['workflow'] == entry['workflow']
                and type(row['returncode']) is int and row['returncode'] == 0
                and value['outcome'] == 'success' and len(value['rows']) == 1, 'Original unique workflow row')
        actual = value['rows'][0]
        identifier = actual['id']
        require(type(identifier) is str and str(uuid.UUID(identifier)) == identifier
                and uuid.UUID(identifier).version == 4 and actual['workflow'] == entry['workflow']
                and actual['name'] + '.1' == entry['workflow'] and type(actual['version']) is int
                and actual['version'] == 1 and actual['status'] == 'finished'
                and identifier not in result.values(), 'Original unique version1 UUID')
        result[entry['directory']] = identifier
    return result


def unknown_history(status_raw, outer_raw):
    status, outer = parse(status_raw), parse(outer_raw)
    require(status['status'] == 'collecting' and status['finished_utc'] is None
            and outer['outcome'] == 'running' and outer['finished_utc'] is None
            and outer['returncode'] is None, 'Original05 remains unfinished/unknown')
    return {'assessment': 'unknown', 'process_absence_is_not_completion': True,
            'status': desc(status_raw), 'outer': desc(outer_raw)}


def diagnostic(old, buffers, attempt, identifier):
    """True means settled retryable transport loss; all contradictions raise."""
    outcome = attempt['outcome']
    if outcome == 'pending_launch':
        raise UnknownAttempt('Pending transport is not a closed retry authority')
    if outcome == 'timeout':
        require(attempt['returncode'] is None and attempt['download_sha256'] is None, 'Loss receipt consistency')
        return True  # Exact adapter is single process; no new process-tree claim.
    require(outcome in ('success', 'nonzero'), 'Invalid publication is not retryable loss')
    good = outcome == 'success'
    raw = buffers[attempt['stdout' if good else 'stderr']['path']]
    value = parse(raw)
    old.job.exact_keys(value, ('schema', 'outcome', 'code', 'started_utc', 'finished_utc',
        'action', 'workflow', 'requested_path', 'http_status', 'workflow_ids', 'page_count',
        'received_bytes', 'retained_bytes', 'partial_file'), 'Original adapter diagnostic')
    require(value['schema'] == 'openmhd.metadata-readonly-adapter-diagnostic.v1'
            and value['outcome'] == ('success' if good else 'failure')
            and value['action'] == attempt['action'] and value['workflow'] == attempt['workflow']
            and value['requested_path'] == attempt['requested_path']
            and value['workflow_ids'] in ([], [identifier]), 'Diagnostic original UUID/action linkage')
    require(old.job.utc(attempt['started_utc']) <= old.job.utc(value['started_utc'])
            <= old.job.utc(value['finished_utc']) <= old.job.utc(attempt['finished_utc']), 'Diagnostic interval')
    require(all(type(value[k]) is int and value[k] >= 0 for k in ('page_count', 'received_bytes', 'retained_bytes'))
            and value['retained_bytes'] <= min(MAX_FILE, value['received_bytes']), 'Diagnostic integer byte counts')
    if good:
        require(value['code'] == 'completed' and value['workflow_ids'] == [identifier]
                and value['http_status'] is None and value['partial_file'] is None
                and buffers[attempt['stderr']['path']] == b'', 'Closed successful adapter diagnostic')
        return False
    require(buffers[attempt['stdout']['path']] == b'', 'Contradictory failure stdout')
    partial = attempt['output'] + '.partial'
    require((value['partial_file'] is None and partial not in buffers and value['retained_bytes'] == 0)
            or (value['partial_file'] == PurePosixPath(partial).name and partial in buffers
                and value['retained_bytes'] == len(buffers[partial])), 'Failed diagnostic/partial byte link')
    retry = value['code'] in ('network_error', 'incomplete_body', 'content_length_mismatch', 'adapter_deadline')
    retry |= value['code'] == 'http_error' and type(value['http_status']) is int and (
        value['http_status'] == 429 or 500 <= value['http_status'] <= 599)
    require(retry, 'Semantic/identity/protocol failure cannot retry')
    require(value['partial_file'] == PurePosixPath(partial).name and partial in buffers,
            'Exact GET adapter retains a partial on retryable loss')
    return True


def visible_artifacts(old, buffers, entry, snapshot, snapshot_raw, identifier):
    """Stop on observable contradictions even in a transport-incomplete case.

    This is NOT a partial-case pass validator. Only old.case_row's complete
    eight-file validator can establish either a passing or failing method.
    """
    transport = old.job.parse(buffers['transport.json'])
    successful = {a['output'] for a in transport['attempts'] if a['outcome'] == 'success'}
    for a in transport['attempts']:
        if a['outcome'] != 'success':
            require(a['output'] not in buffers, 'Failed receipt cannot publish canonical bytes')
    artifacts = {n: raw for n, raw in buffers.items() if n.startswith('artifacts/') and n in successful}
    manifest_name = 'artifacts/artifacts.sha256.json'
    if manifest_name in artifacts:
        manifest = old.job.parse(artifacts[manifest_name])
        expected = {'outputs/' + n for n in old.job.OUTPUT_NAMES if n != 'artifacts.sha256.json'}
        require(type(manifest) is dict and set(manifest) == expected
                and all(old.job.is_hash(h) for h in manifest.values()), 'Partial original artifact manifest grammar')
        for n, raw in artifacts.items():
            if n != manifest_name:
                require(sha(raw) == manifest['outputs/' + PurePosixPath(n).name], 'Visible original artifact hash mismatch')
    if 'artifacts/result.json' in artifacts:
        result = old.job.parse(artifacts['artifacts/result.json'])
        require(same(result['case'], entry['specification']) and result['source_revision'] == REVISION
                and result['snapshot_sha256'] == sha(snapshot_raw)
                and result['source_sha256'] == snapshot['source_sha256']
                and result['payload_sha256'] == entry['payload_sha256'], 'Visible result source/case mismatch')
    if 'artifacts/runtime.json' in artifacts:
        runtime = old.job.parse(artifacts['artifacts/runtime.json'])
        require(type(runtime['job_path']) is str and identifier in PurePosixPath(runtime['job_path']).parts,
                'Visible runtime original UUID mismatch')
    return artifacts


def consistent_history(old, captures):
    """Compare whole captures without grafting any body into another attempt."""
    seen = {}
    for buffers in captures:
        transport = old.job.parse(buffers['transport.json'])
        for a in transport['attempts']:
            name = a['output']
            if a['outcome'] == 'success' and name.startswith('artifacts/'):
                raw = buffers[name]
                require(name not in seen or seen[name] == raw, 'Changed original remote body across whole captures')
                seen[name] = raw


def case_buffers(old, path, *, observation_only=False):
    names, directories = old.file_names(path, with_directories=True)
    require(directories == ({'transport'} if observation_only else {'transport', 'artifacts'}),
            'Exact case/observation directory inventory')
    return old.job.capture_files(path, names, attempts=1)


def inspect_case(old, buffers, snapshot, snapshot_raw, entry, submission, command, identifier):
    # Old strict transport and output validators remain the authority; never
    # repair a manifest, scalar, row, failed receipt or incomplete child.
    transport = old.job.parse(buffers['transport.json'])
    require(type(transport['attempts']) is list, 'Transport attempt list')
    if any(a.get('outcome') == 'pending_launch' for a in transport['attempts']):
        raise UnknownAttempt('Retained pending launch needs external closure, never automatic retry')
    transported = old.validate_transport(buffers, entry, command)
    losses = [diagnostic(old, buffers, a, identifier) for a in transport['attempts']]
    visible_artifacts(old, buffers, entry, snapshot, snapshot_raw, identifier)
    for name in ('server-before.json', 'server-after.json'):
        if name in buffers and any(a['outcome'] == 'success' and a['output'] == name for a in transport['attempts']):
            require(old.job.server_status(old.job.parse(buffers[name]), entry['workflow']) == 'finished',
                    'Original workflow is not finished')
    if any(losses):
        return dict(disposition='loss', row=None)
    require(transported['all_success'], 'Unexplained incomplete transport cannot retry')
    row = old.case_row(buffers, snapshot, snapshot_raw, entry, submission, command)
    require((row['status'], row['classification']) in (
        ('passed', 'validated_independent_unittest'), ('failed', 'validated_unittest_failure'))
        and row['external_evidence_required'] is False, 'Invalid output or method contradiction')
    runtime = old.job.parse(buffers['artifacts/runtime.json'])
    require(identifier in PurePosixPath(runtime['job_path']).parts, 'Actual runtime original UUID')
    return dict(disposition='complete', row=row)


def bounded_attempts(perform):
    """Policy helper, not a case validator. Complete method failure is final."""
    for index in range(1, 4):
        result = perform(index)
        require(result['disposition'] in ('loss', 'complete'), 'Unknown retry result')
        if result['disposition'] == 'complete':
            return result
    raise TransportExhausted('Three settled whole-case transport losses; preserve all attempts')


def whole_case(old, destination, entry, snapshot, snapshot_raw, submission, command, identifier):
    destination.mkdir(parents=True)
    case = destination / 'case'
    transport = dict(schema='openmhd.galaxy-python-transport.v1', client_argv=command,
                     workflow=entry['workflow'], attempts=[], origin='server')
    requests = [('observe', 'server-before.json')] + [('download', n) for n in old.job.OUTPUT_NAMES] + [
        ('observe', 'server-after.json')]
    try:
        publish(destination / 'state.json', dict(state='running', finished_utc=None, **SCOPE))
        case.mkdir()
        (case / 'artifacts').mkdir()
        (case / 'transport').mkdir()
        for action, name in requests:
            attempt = old.prepare.adapter_attempt(command, action, entry['workflow'], name, case, transport, required=False)
            buffers = case_buffers(old, case)
            old.validate_transport(buffers, entry, command)  # strict allowed prefix
            visible_artifacts(old, buffers, entry, snapshot, snapshot_raw, identifier)
            if diagnostic(old, buffers, attempt, identifier):
                break
            if action == 'observe':
                require(old.job.server_status(old.job.parse(buffers[name]), entry['workflow']) == 'finished',
                        'Nonterminal/identity transition cannot retry')
        result = inspect_case(old, case_buffers(old, case), snapshot, snapshot_raw, entry, submission, command, identifier)
        publish(destination / 'state.json', dict(state=result['disposition'], finished_utc=now(), **SCOPE))
        capture = dict(schema='openmhd.galaxy-python-recovery-case.v1', directory=entry['directory'],
            workflow=entry['workflow'], uuid=identifier, case_tree=tree(case), result=result, **SCOPE)
        publish(destination / 'capture.json', capture)
        return dict(result, path=str(destination), capture_sha256=sha(read(destination, 'capture.json')))
    except BaseException as error:
        try:
            publish(destination / 'state.json', dict(state='unknown' if not isinstance(error, Exception)
                or isinstance(error, UnknownAttempt) else 'rejected', finished_utc=None,
                error_type=type(error).__name__, external_evidence_required=True, **SCOPE))
        except BaseException:
            pass
        raise


def inventory_round(old, root, plan, ids, command, acquire):
    rows = []
    for entry in plan['cases']:
        path = root / entry['directory']
        if acquire:
            path.mkdir(parents=True)
            (path / 'transport').mkdir()
            transport = dict(schema='openmhd.galaxy-python-transport.v1', client_argv=command,
                workflow=entry['workflow'], attempts=[], origin='server')
            old.prepare.adapter_attempt(command, 'observe', entry['workflow'], 'server-before.json',
                path, transport, required=False)
        buffers = case_buffers(old, path, observation_only=True)
        old.validate_transport(buffers, entry, command)
        attempts = old.job.parse(buffers['transport.json'])['attempts']
        require(len(attempts) == 1 and not diagnostic(old, buffers, attempts[0], ids[entry['directory']]),
                'Fresh full inventory cannot use failed observation')
        require(old.job.server_status(old.job.parse(buffers['server-before.json']), entry['workflow']) == 'finished',
                'Fresh inventory must be original terminal version1')
        rows.append(dict(directory=entry['directory'], workflow=entry['workflow'], uuid=ids[entry['directory']],
                         tree=tree(path)))
    require({p.name for p in root.iterdir()} == {e['directory'] for e in plan['cases']}, 'Exact inventory coverage')
    return rows


def validate_selection(entries, selected):
    require(type(selected) is list and len(selected) == len(entries), 'Exact selected leaf coverage')
    for entry, row in zip(entries, selected):
        require(row['directory'] == entry['directory'] and row['selector'] == entry['specification']['selector']
                and row['workflow'] == entry['workflow'], 'Selection original index/selector/workflow')


def selected_whole_case(choice, entry, identifier, origin, case_tree, row):
    require(same(choice, dict(directory=entry['directory'], selector=entry['specification']['selector'],
        workflow=entry['workflow'], uuid=identifier, origin=origin, case_tree=case_tree, row=row)),
        'Selected entire-case provenance/row mismatch')


def retained_command(old, root, snapshot, command, origins):
    """Offline structural/source checks; never dereference old absolute argv.

    The actual launch path is byte-fenced by old.pinned_tools during recovery.
    Offline portability preserves that argv as an observation, not attestation.
    The original host_tools guard is still applied to the retained bundle.
    """
    old.job.credential_free_argv(command)
    require(type(origins['output_path']) is str and Path(origins['output_path']).is_absolute()
            and len(command) == 2 and Path(command[1]).is_absolute()
            and command[1] == str(Path(origins['output_path']) / 'frozen_tools/reana_metadata_readonly_adapter.py'),
            'Actual retained command/output link')
    old.host_tools(snapshot)
    require(sha(read(root / 'frozen_tools', 'reana_metadata_readonly_adapter.py')) == HELPERS['reana_metadata_readonly_adapter.py'],
            'Retained actual adapter bytes')
    require(type(origins['interpreter']) is dict and set(origins['interpreter']) == {'sha256', 'bytes'}
            and re.fullmatch('[0-9a-f]{64}', origins['interpreter']['sha256'])
            and type(origins['interpreter']['bytes']) is int and origins['interpreter']['bytes'] > 0,
            'Retained interpreter observation, not external attestation')


def temporal_fence(old, before_root, after_root, attempt_captures):
    before, after = [], []
    for folder, times in ((before_root, before), (after_root, after)):
        for case in sorted(folder.iterdir()):
            transport = old.job.parse(read(case, 'transport.json'))
            a = transport['attempts'][0]
            times.append((old.job.utc(a['started_utc']), old.job.utc(a['finished_utc'])))
    require(max(end for _, end in before) <= min(start for start, _ in after), 'Full inventory phase ordering')
    for buffers in attempt_captures:
        times = old.job.parse(buffers['transport.json'])['attempts']
        require(max(end for _, end in before) <= old.job.utc(times[0]['started_utc'])
                and old.job.utc(times[-1]['finished_utc']) <= min(start for start, _ in after),
                'Whole-case attempt outside fresh inventory bracket')


def release_check(raw):
    value = parse(raw)
    require(type(value) is dict and set(value) == {'schema', 'recovery_source_sha256', 'base_manifest_sha256',
        'history_tree_sha256', 'history_outer_sha256', 'root_review_sha256'}, 'Recovery release fields')
    require(value['schema'] == 'openmhd.galaxy-python-recovery-release.v1'
            and all(type(value[k]) is str and re.fullmatch('[0-9a-f]{64}', value[k])
                    for k in value if k != 'schema'), 'Explicit reviewed recovery pins')
    require(value['base_manifest_sha256'] == BASE_MANIFEST, 'Exact original closed06 manifest')
    require(sha(Path(__file__).read_bytes()) == value['recovery_source_sha256'], 'Recovery module source pin')
    return value


def close_root(root):
    publish(root / 'recovery_files.json', dict(schema='openmhd.galaxy-python-recovered-files.v1',
        tree=tree(root, ('recovery_files.json',)), **SCOPE))


def derive(old, root):
    require({p.name for p in root.iterdir()} <= {'release.json', 'original_uuid_inventory.json', 'unknown05_outer.json',
        'recovery_command.json', 'input_origins.json', 'recovery_status.json', 'selection.json', 'summary.json',
        'recovery_files.json', 'sources', 'frozen_tools', 'inventory', 'attempts'}, 'Unknown recovered root entry')
    require({p.name for p in (root / 'sources').iterdir()} == {'base', 'unknown05'}
            and {p.name for p in (root / 'frozen_tools').iterdir()} == set(HELPERS)
            and {p.name for p in (root / 'inventory').iterdir()} == {'before', 'after'}, 'Exact retained source/inventory directories')
    release = release_check(read(root, 'release.json'))
    require(sha(read(root / 'sources/base', 'files.sha256.json')) == release['base_manifest_sha256'], 'Original closed06 manifest pin')
    old.verify_packet(root / 'sources/base')
    context, snapshot, plan, submission = original_context(old, root / 'sources/base')
    ids = original_ids(read(root, 'original_uuid_inventory.json'), plan)
    require(sha(encode(tree(root / 'sources/unknown05'))) == release['history_tree_sha256']
            and sha(read(root, 'unknown05_outer.json')) == release['history_outer_sha256'], 'Original unknown history byte pins')
    history = unknown_history(read(root / 'sources/unknown05', 'collection_status.json'), read(root, 'unknown05_outer.json'))
    command = parse(read(root, 'recovery_command.json'))
    origins = parse(read(root, 'input_origins.json'))
    require(set(origins) == {'sources', 'closed06_path', 'unknown05_path', 'interpreter', 'output_path',
        'original_source_generation', 'recovery_source_sha256', *SCOPE}, 'Input origin fields')
    old.job.scope(origins)
    require(same(origins['sources'], old.job.parse(read(root / 'sources/base', 'context_capture.json'))['sources'])
            and origins['original_source_generation'] == REVISION
            and origins['recovery_source_sha256'] == release['recovery_source_sha256']
            and all(type(origins[n]) is str and Path(origins[n]).is_absolute() for n in ('closed06_path', 'unknown05_path'))
            and Path(origins['closed06_path']).name == 'galaxy_python_case_results_20261122_attempt06'
            and Path(origins['unknown05_path']).name == 'galaxy_python_case_results_20261122_attempt05', 'Original input origin links')
    retained_command(old, root, snapshot, command, origins)
    before = inventory_round(old, root / 'inventory/before', plan, ids, command, False)
    after = inventory_round(old, root / 'inventory/after', plan, ids, command, False)
    require(all(a['workflow'] == b['workflow'] and a['uuid'] == b['uuid'] for a, b in zip(before, after)), 'Inventory identity changed')
    selected = parse(read(root, 'selection.json'))
    old.job.exact_keys(selected, ('schema', 'snapshot_sha256', 'plan_sha256', 'submission_sha256', 'cases',
        'physical_evolutions_run', 'component_accepted'), 'Recovery selection')
    require(selected['schema'] == 'openmhd.galaxy-python-recovery-selection.v1' and selected['snapshot_sha256'] == SNAPSHOT
            and selected['plan_sha256'] == PLAN and selected['submission_sha256'] == SUBMISSION, 'Selection original context')
    old.job.scope(selected)
    validate_selection(plan['cases'], selected['cases'])
    expected_attempts, verdicts, fresh_captures = set(), [], []
    for entry, choice in zip(plan['cases'], selected['cases']):
        directory = entry['directory']
        require(choice['uuid'] == ids[directory], 'Selected original UUID')
        base_buffers = case_buffers(old, root / 'sources/base/cases' / directory)
        base_command = old.job.parse(read(root / 'sources/base', 'context_capture.json'))['adapter_argv']
        baseline = inspect_case(old, base_buffers, snapshot, context['shared/snapshot.json'], entry,
                                submission[entry['workflow']], base_command, ids[directory])
        captures = [base_buffers]
        attempt_paths = sorted((root / 'attempts' / directory).iterdir()) if (root / 'attempts' / directory).exists() else []
        results = []
        for index, path in enumerate(attempt_paths, 1):
            require(baseline['disposition'] == 'loss' and index <= 3 and path.name == f'{index:02d}'
                    and (not results or results[-1]['disposition'] == 'loss'), 'No retry after complete method/semantic verdict')
            expected_attempts.add(directory + '/' + path.name)
            require({p.name for p in path.iterdir()} == {'case', 'state.json', 'capture.json'}, 'Whole-attempt closed inventory')
            cap = parse(read(path, 'capture.json'))
            captured = case_buffers(old, path / 'case')
            actual = inspect_case(old, captured, snapshot, context['shared/snapshot.json'],
                entry, submission[entry['workflow']], command, ids[directory])
            captures.append(captured)
            fresh_captures.append(captured)
            consistent_history(old, captures)
            require(same(cap, dict(schema='openmhd.galaxy-python-recovery-case.v1', directory=directory,
                workflow=entry['workflow'], uuid=ids[directory], case_tree=tree(path / 'case'), result=actual, **SCOPE)),
                'Whole-attempt source/UUID/body/transport closure')
            state = parse(read(path, 'state.json'))
            require(set(state) == {'state', 'finished_utc', *SCOPE} and state['state'] == actual['disposition']
                    and old.job.utc(state['finished_utc']) >= old.job.utc(
                        old.job.parse(captured['transport.json'])['attempts'][-1]['finished_utc']), 'Unfinished attempt cannot select')
            old.job.scope(state)
            results.append(actual)
        if baseline['disposition'] == 'complete':
            expected = dict(kind='closed06', path='sources/base/cases/' + directory,
                            closure_sha256=release['base_manifest_sha256'])
            actual, case_path = baseline, root / expected['path']
        else:
            require(results and results[-1]['disposition'] == 'complete', 'No complete whole-case recovery')
            path = attempt_paths[-1]
            expected = dict(kind='whole_attempt', path=path.relative_to(root).as_posix(),
                            closure_sha256=sha(read(path, 'capture.json')))
            actual, case_path = results[-1], path / 'case'
        selected_whole_case(choice, entry, ids[directory], expected, tree(case_path), actual['row'])
        verdicts.append(actual['row'])
    actual_attempts = {p.parent.name + '/' + p.name for p in (root / 'attempts').glob('*/*')}
    require(actual_attempts == expected_attempts and {p.name for p in (root / 'attempts').iterdir()}
            == {n.split('/')[0] for n in expected_attempts}, 'Unselected/extra attempt leaf')
    temporal_fence(old, root / 'inventory/before', root / 'inventory/after', fresh_captures)
    counts = {name: sum(row['status'] == name for row in verdicts) for name in ('passed', 'failed')}
    return dict(schema='openmhd.galaxy-python-recovered-catalog.v1', source_revision=REVISION,
        snapshot_sha256=SNAPSHOT, plan_sha256=PLAN, submission_sha256=SUBMISSION,
        catalog_complete=True, expected_cases=175, counts=counts, cases=verdicts,
        whole_catalog_passed=counts['passed'] == 175, unknown05_history=history,
        authenticated_external_prerequisite=False, **SCOPE)


def verify_recovered(root):
    """Offline ONLY: no call path to inventory acquisition/adapter/network."""
    require(__debug__ and sys.flags.optimize == 0, 'Unoptimized recovery verifier required')
    root = root_path(root)
    manifest = parse(read(root, 'recovery_files.json'))
    require(same(manifest, dict(schema='openmhd.galaxy-python-recovered-files.v1',
        tree=tree(root, ('recovery_files.json',)), **SCOPE)), 'Exact recovered packet closure')
    status = parse(read(root, 'recovery_status.json'))
    require(set(status) == {'status', 'started_utc', 'finished_utc', 'external_evidence_required', *SCOPE}
            and status['status'] == 'complete' and status['finished_utc'] is not None
            and status['external_evidence_required'] is False, 'Only finalized new recovery can verify')
    with frozen_api(root / 'frozen_tools') as old:
        summary = derive(old, root)
        old.job.scope(status)
        require(old.job.utc(status['finished_utc']) >= old.job.utc(status['started_utc']), 'Recovery status clock')
        require(same(parse(read(root, 'summary.json')), summary), 'Derived recovered catalog differs')
    require(same(parse(read(root, 'recovery_files.json')), manifest)
            and same(tree(root, ('recovery_files.json',)), manifest['tree']), 'Changed recovery during verification')
    return summary


def recover(base, unknown05, source_dir, preflight_dir, cases_dir, tools_dir,
            uuid_inventory_path, unknown_outer_path, release_path, output, interpreter):
    """Future authorized acquisition only, fresh destination; NEVER call now.

    release pins are supplied after CLOSED06 + exact revision inspection. This
    function cannot turn live06 into a source packet or infer old05 termination.
    """
    require(__debug__ and sys.flags.optimize == 0, 'Unoptimized recovery required')
    base, unknown05, tools_dir = map(root_path, (base, unknown05, tools_dir))
    require(base.name == 'galaxy_python_case_results_20261122_attempt06'
            and unknown05.name == 'galaxy_python_case_results_20261122_attempt05', 'Exact original06/unknown05 source roots')
    output = Path(output).absolute()
    root_path(output.parent)
    require(not output.exists() and not output.is_symlink(), 'Fresh recovery output')
    output.mkdir()
    status = dict(status='running', started_utc=now(), finished_utc=None,
        external_evidence_required=True, **SCOPE)
    try:
        publish(output / 'recovery_status.json', status)
        release_raw = read(Path(release_path).parent, Path(release_path).name)
        release = release_check(release_raw)
        with frozen_api(tools_dir) as old:
            old.verify_packet(base)  # Must be closed, with old complete/failed status and finite finish.
            require(sha(read(base, 'files.sha256.json')) == release['base_manifest_sha256'], 'Reviewed closed06 source')
            context, snapshot, plan, submission = original_context(old, base)
            original_inputs = old.capture_context(source_dir, preflight_dir, cases_dir)
            require(original_inputs[0] == context and same(original_inputs[1],
                parse(read(base, 'context_capture.json'))['sources']), 'Original input/closed06 context fence')
            ids_raw = read(Path(uuid_inventory_path).parent, Path(uuid_inventory_path).name)
            ids = original_ids(ids_raw, plan)
            outer_raw = read(Path(unknown_outer_path).parent, Path(unknown_outer_path).name)
            unknown_history(read(unknown05, 'collection_status.json'), outer_raw)
            require(sha(outer_raw) == release['history_outer_sha256'], 'Original unknown outer command pin')
            base_tree = copy_tree(base, output / 'sources/base')
            history_tree = copy_tree(unknown05, output / 'sources/unknown05')
            require(sha(encode(history_tree)) == release['history_tree_sha256'], 'Reviewed unknown05 forensic tree')
            (output / 'frozen_tools').mkdir()
            for name, expected in HELPERS.items():
                raw = read(tools_dir, name)
                require(sha(raw) == expected, 'Original helper copy')
                (output / 'frozen_tools' / name).write_bytes(raw)
            for name, raw in (('release.json', release_raw), ('original_uuid_inventory.json', ids_raw),
                              ('unknown05_outer.json', outer_raw)):
                (output / name).write_bytes(raw)
            interpreter = Path(interpreter)
            require(interpreter.is_absolute(), 'Absolute adapter interpreter')
            interpreter_pin = desc(read(interpreter.parent, interpreter.name))
            command = [str(interpreter), str(output / 'frozen_tools/reana_metadata_readonly_adapter.py')]
            old.pinned_tools(snapshot, command)
            publish(output / 'recovery_command.json', command)
            publish(output / 'input_origins.json', dict(sources=original_inputs[1],
                closed06_path=str(base), unknown05_path=str(unknown05), interpreter=interpreter_pin,
                output_path=str(output),
                original_source_generation=REVISION, recovery_source_sha256=release['recovery_source_sha256'], **SCOPE))
            (output / 'attempts').mkdir()
            inventory_round(old, output / 'inventory/before', plan, ids, command, True)
            choices = []
            base_command = parse(read(base, 'context_capture.json'))['adapter_argv']
            for entry in plan['cases']:
                directory = entry['directory']
                case_path = output / 'sources/base/cases' / directory
                result = inspect_case(old, case_buffers(old, case_path), snapshot, context['shared/snapshot.json'],
                    entry, submission[entry['workflow']], base_command, ids[directory])
                origin = dict(kind='closed06', path=case_path.relative_to(output).as_posix(),
                              closure_sha256=release['base_manifest_sha256'])
                if result['disposition'] == 'loss':
                    captures = [case_buffers(old, case_path)]
                    def perform(index):
                        value = whole_case(old, output / 'attempts' / directory / f'{index:02d}', entry,
                            snapshot, context['shared/snapshot.json'], submission[entry['workflow']], command, ids[directory])
                        captures.append(case_buffers(old, Path(value['path']) / 'case'))
                        consistent_history(old, captures)
                        return value
                    result = bounded_attempts(perform)
                    path = Path(result['path'])
                    case_path = path / 'case'
                    origin = dict(kind='whole_attempt', path=path.relative_to(output).as_posix(),
                                  closure_sha256=result['capture_sha256'])
                choices.append(dict(directory=directory, selector=entry['specification']['selector'],
                    workflow=entry['workflow'], uuid=ids[directory], origin=origin,
                    case_tree=tree(case_path), row=result['row']))
            inventory_round(old, output / 'inventory/after', plan, ids, command, True)
            require(old.capture_context(source_dir, preflight_dir, cases_dir) == original_inputs
                    and tree(base) == base_tree and tree(unknown05) == history_tree
                    and desc(read(interpreter.parent, interpreter.name)) == interpreter_pin
                    and read(Path(release_path).parent, Path(release_path).name) == release_raw
                    and read(Path(uuid_inventory_path).parent, Path(uuid_inventory_path).name) == ids_raw
                    and read(Path(unknown_outer_path).parent, Path(unknown_outer_path).name) == outer_raw,
                    'Final original input/history/interpreter fence')
            old.pinned_tools(snapshot, command)
            require({n: sha(read(tools_dir, n)) for n in HELPERS} == HELPERS, 'Final original helper fence')
            publish(output / 'selection.json', dict(schema='openmhd.galaxy-python-recovery-selection.v1',
                snapshot_sha256=SNAPSHOT, plan_sha256=PLAN, submission_sha256=SUBMISSION, cases=choices, **SCOPE))
            summary = derive(old, output)
            publish(output / 'summary.json', summary)
        status.update(status='complete', finished_utc=now(), external_evidence_required=False)
        publish(output / 'recovery_status.json', status)
        close_root(output)
        return verify_recovered(output)
    except BaseException as error:
        unknown = not isinstance(error, Exception) or isinstance(error, UnknownAttempt)
        status.update(status='unknown' if unknown else 'failed', finished_utc=None if unknown else now(),
            error_type=type(error).__name__, external_evidence_required=True)
        try:
            publish(output / 'recovery_status.json', status)
            for name in ('selection.json', 'summary.json'):
                if (output / name).exists():
                    (output / name).rename(output / (name + '.failed'))
            close_root(output)  # Forensic closure is not a passing recovered catalog.
        except BaseException:
            pass  # Storage/process loss can prevent finalization; running intent persists.
        raise RecoveryError('Recovery unfinished/nonpassing; retain all original and attempt bytes') from None


def main(argv=None):
    """Future reviewed CLI. Merely importing this proposal performs no work."""
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('verify-recovered', 'recover'))
    parser.add_argument('--packet', type=Path)
    for name in ('base', 'unknown05', 'source-dir', 'preflight-dir', 'cases-dir', 'tools-dir',
                 'uuid-inventory-path', 'unknown-outer-path', 'release-path', 'output', 'interpreter'):
        parser.add_argument('--' + name, type=Path)
    args = parser.parse_args(argv)
    if args.action == 'verify-recovered':
        require(args.packet is not None, 'Offline verification needs --packet')
        require(all(getattr(args, n) is None for n in ('base', 'unknown05', 'source_dir', 'preflight_dir',
            'cases_dir', 'tools_dir', 'uuid_inventory_path', 'unknown_outer_path', 'release_path', 'output', 'interpreter')),
            'Offline verification cannot take live acquisition arguments')
        summary = verify_recovered(args.packet)
    else:
        fields = ('base', 'unknown05', 'source_dir', 'preflight_dir', 'cases_dir', 'tools_dir',
                  'uuid_inventory_path', 'unknown_outer_path', 'release_path', 'output', 'interpreter')
        require(args.packet is None and all(getattr(args, n) is not None for n in fields), 'Explicit fresh recovery arguments')
        summary = recover(**{n: getattr(args, n) for n in fields})
    print('Recovered original175 catalog:', summary['counts'], 'whole_catalog_passed=', summary['whole_catalog_passed'])
    print('External prerequisite, physical/component/merger acceptance are not established.')
    return 0 if summary['whole_catalog_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
