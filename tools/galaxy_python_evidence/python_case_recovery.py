"""Additive complete-case Python evidence. Import is inert; no workflow mutation.

One original catalog per fresh interpreter. An out-of-band root release SHA is
mandatory before loading its frozen helpers. No old globals/cache are patched.
Origin roots are explicit offline dependencies, not historical argv locations.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

SOURCE = 'tools/galaxy_python_evidence/python_case_recovery.py'
RELEASE = 'openmhd.python-complete-case-release.v1'
SUMMARY = 'openmhd.python-complete-case-results.v1'
FILES = 'openmhd.python-complete-case-files.v1'
TOOLS = ('reana_metadata_job.py', 'prepare_metadata_reana.py',
         'collect_metadata_reana_results.py', 'reana_metadata_readonly_adapter.py')
OUTPUTS = ('result.json', 'runtime.json', 'command.json', 'stdout.txt', 'stderr.txt',
           'child_result.json', 'child_raw.bin', 'artifacts.sha256.json')
SCOPE = dict(physical_evolutions_run=False, component_accepted=False)
MAX_FILE, MAX_FILES, MAX_TOTAL, MAX_CASES = 16 << 20, 64000, 4 << 30, 4096


class Rejected(ValueError):
    """Semantic, identity or storage rejection; never a transport retry."""


class Unknown(Rejected):
    """Interrupted/pending authority requires external terminal evidence."""


def need(value, code):
    if not value:
        raise Rejected(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def same(a, b):
    return encode(a) == encode(b)


def parse(raw):
    need(type(raw) is bytes and len(raw) <= MAX_FILE, 'bounded_json')
    def unique(items):
        out = {}
        for name, value in items:
            need(name not in out, 'duplicate_json_key')
            out[name] = value
        return out
    def finite(text):
        value = float(text)
        need(math.isfinite(value), 'nonfinite_json')
        return value
    return json.loads(raw, object_pairs_hook=unique, parse_float=finite,
        parse_constant=lambda _: need(False, 'nonfinite_json'))


def keys(value, names):
    need(type(value) is dict and set(value) == set(names), 'exact_keys')


def hash_value(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def pin(raw):
    return dict(bytes=len(raw), sha256=sha(raw))


def utc():
    return datetime.now(timezone.utc).isoformat()


def plain(path):
    path = Path(path).absolute()
    need(all(not p.is_symlink() for p in (path, *path.parents)), 'linked_root')
    return path


def at(root, name):
    need(type(name) is str, 'path_string')
    p = PurePosixPath(name)
    need(p.parts and p.as_posix() == name and not p.is_absolute()
         and '..' not in p.parts and '\\' not in name, 'relative_path')
    path = plain(root)
    for part in p.parts:
        path /= part
        need(not path.is_symlink(), 'linked_path')
    return path


def stamp(s):
    return tuple(getattr(s, n) for n in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))


def read(root, name):
    path = at(root, name)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= MAX_FILE,
             'bounded_regular_unlinked_file')
        pieces, size = [], 0
        while True:
            block = os.read(fd, min(65536, MAX_FILE + 1 - size))
            if not block:
                break
            size += len(block)
            need(size <= MAX_FILE, 'growing_file')
            pieces.append(block)
        need(stamp(before) == stamp(os.fstat(fd)) == stamp(path.stat()) and size == before.st_size,
             'changed_file_generation')
        return b''.join(pieces)
    finally:
        os.close(fd)


def tree(root, exclude=()):
    root = plain(root)
    need(root.is_dir(), 'directory_required')
    files, directories, total = {}, [], 0
    for path in sorted(root.rglob('*')):
        need(len(files) + len(directories) < MAX_FILES and not path.is_symlink(), 'tree_bound_or_link')
        name = path.relative_to(root).as_posix()
        if path.is_dir():
            directories.append(name)
        else:
            need(stat.S_ISREG(path.stat().st_mode), 'special_file')
            if name in exclude:
                continue
            raw = read(root, name)
            total += len(raw)
            need(total <= MAX_TOTAL, 'tree_byte_bound')
            files[name] = pin(raw)
    return dict(files=files, directories=directories)


def put(root, name, raw):
    path = at(root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        need(stream.write(raw) == len(raw), 'short_write')
        stream.flush()
        os.fsync(stream.fileno())


def publish(root, name, value):
    put(root, name + '.tmp', encode(value))
    os.replace(at(root, name + '.tmp'), at(root, name))


def authenticate(raw, expected):
    """The external SHA authenticates root-supplied bytes, not their truth."""
    need(hash_value(expected) and sha(raw) == expected, 'external_root_release_digest')
    value = parse(raw)
    keys(value, ('schema', 'invocation_path', 'provider_sha256', 'catalog', 'helpers', 'uuid_map_sha256',
                 'origins', 'root_review_sha256', 'get_acquisition_authorized', *SCOPE))
    need(value['schema'] == RELEASE and all(value[n] is False for n in SCOPE)
         and type(value['get_acquisition_authorized']) is bool, 'release_scope')
    need(type(value['invocation_path']) is str and Path(value['invocation_path']).is_absolute()
         and str(Path(value['invocation_path'])) == value['invocation_path'], 'one_original_invocation_path')
    need(hash_value(value['provider_sha256']) and hash_value(value['uuid_map_sha256'])
         and hash_value(value['root_review_sha256']), 'release_hashes')
    keys(value['catalog'], ('source_revision', 'snapshot_sha256', 'archive_sha256', 'job_sha256',
                           'certificate_sha256', 'plan_sha256', 'submission_sha256', 'identities_sha256'))
    need(type(value['catalog']['source_revision']) is str
         and re.fullmatch('[0-9a-f]{40}', value['catalog']['source_revision'])
         and all(hash_value(v) for k, v in value['catalog'].items() if k != 'source_revision'), 'catalog_pins')
    keys(value['helpers'], TOOLS)
    need(all(hash_value(v) for v in value['helpers'].values()), 'helper_hashes')
    need(type(value['origins']) is list and 0 < len(value['origins']) <= 32, 'bounded_origins')
    seen = set()
    for item in value['origins']:
        keys(item, ('manifest_sha256', 'summary_sha256'))
        need(all(hash_value(v) for v in item.values()) and item['manifest_sha256'] not in seen,
             'duplicate_or_invalid_origin')
        seen.add(item['manifest_sha256'])
    return value


def own_source(release):
    need(sha(read(Path(__file__).absolute().parent, Path(__file__).name)) == release['provider_sha256'],
         'released_provider_source')


def helpers(directory, release):
    """Ordinary fresh-process imports only; conflicting caches fail closed."""
    need(sys.dont_write_bytecode and __debug__ and sys.flags.optimize == 0, 'unoptimized_B_required')
    directory = plain(directory)
    before = {name: read(directory, name) for name in TOOLS}
    need({n: sha(b) for n, b in before.items()} == release['helpers'], 'helper_source_before_import')
    names = ('reana_metadata_job', 'prepare_metadata_reana', 'collect_metadata_reana_results')
    need(not any(n in sys.modules for n in names), 'fresh_process_not_conflicting_cache')
    previous = list(sys.path)
    try:
        sys.path.insert(0, str(directory))
        modules = [importlib.import_module(n) for n in names]
    finally:
        sys.path[:] = previous
    need(all(Path(m.__file__).absolute() == directory / (n + '.py') for n, m in zip(names, modules)),
         'actual_loaded_helper_paths')
    need({n: read(directory, n) for n in TOOLS} == before, 'helper_source_after_import')
    old = modules[-1]
    need(set(old.TOOLS) == set(TOOLS) and tuple(old.job.OUTPUT_NAMES) == OUTPUTS
         and all(callable(getattr(old, n, None)) for n in ('validate_context', 'capture_context',
             'validate_witnesses', 'validate_transport', 'case_row', 'verify_packet', 'host_tools', 'pinned_tools'))
         and callable(getattr(old.prepare, 'adapter_attempt', None)), 'supported_frozen_python_metadata_api')
    return old


def context(old, root, release):
    names = {n for n in old.file_names(root) if n.startswith(('shared/', 'inputs/'))}
    buffers = {n: read(root, n) for n in names}
    for name, raw in buffers.items():
        if name.endswith('.json'):
            parse(raw)
    snapshot, plan, submission = old.validate_context(buffers)
    c = release['catalog']
    rawpins = dict(snapshot_sha256='shared/snapshot.json', archive_sha256='shared/source.tar.gz',
        job_sha256='shared/job.py', certificate_sha256='shared/preflight_certificate.json',
        plan_sha256='inputs/cases/plan.json', submission_sha256='inputs/cases/submission.json')
    need(all(sha(buffers[n]) == c[k] for k, n in rawpins.items())
         and snapshot['source_revision'] == c['source_revision']
         and sha(encode(snapshot['test_identities'])) == c['identities_sha256'], 'released_original_context')
    need(0 < len(plan['cases']) == len(snapshot['tests']) <= MAX_CASES, 'derived_original_catalog_bound')
    need(all(snapshot['source_sha256']['tools/galaxy_python_evidence/' + n] == h
             for n, h in release['helpers'].items()), 'original_helper_archive_membership')
    need(all(v['status'] in ('submitted', 'submission uncertain') for v in submission.values()),
         'settled_untouched_original_submission')
    return buffers, snapshot, plan, submission


def ids(raw, release, plan):
    need(sha(raw) == release['uuid_map_sha256'], 'root_original_uuid_map_pin')
    value = parse(raw)
    keys(value, ('schema', 'cases'))
    need(value['schema'] == 'openmhd.python-original-uuid-map.v1'
         and type(value['cases']) is list and len(value['cases']) == len(plan['cases']), 'uuid_map_coverage')
    result, seen = {}, set()
    for entry, row in zip(plan['cases'], value['cases']):
        keys(row, ('directory', 'workflow', 'uuid', 'version'))
        need(row['directory'] == entry['directory'] and row['workflow'] == entry['workflow']
             and type(row['version']) is int and row['version'] == 1
             and type(row['uuid']) is str and re.fullmatch(
                 '[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}', row['uuid'])
             and row['uuid'] not in seen, 'unique_original_version1_uuid')
        result[row['directory']] = row['uuid']
        seen.add(row['uuid'])
    return result


def case_buffers(root):
    current = tree(root)
    need(set(current['directories']) <= {'artifacts', 'transport'}, 'case_directory_inventory')
    return {n: read(root, n) for n in current['files']}


def diagnostic(old, buffers, a, identifier):
    outcome = a['outcome']
    if outcome in ('pending_launch', 'start_failed'):
        raise Unknown('unsettled_or_unstarted_adapter_not_transport_retry')
    if outcome == 'timeout':
        # subprocess.run(timeout=300) kills and communicates with its direct
        # single-process adapter before returning. No descendant claim is made.
        need(a['returncode'] is None and a['download_sha256'] is None, 'timeout_receipt')
        return True
    need(outcome in ('success', 'nonzero'), 'semantic_transport_outcome')
    good = outcome == 'success'
    value = parse(buffers[a['stdout' if good else 'stderr']['path']])
    keys(value, ('schema', 'outcome', 'code', 'started_utc', 'finished_utc', 'action', 'workflow',
        'requested_path', 'http_status', 'workflow_ids', 'page_count', 'received_bytes', 'retained_bytes', 'partial_file'))
    need(value['schema'] == 'openmhd.metadata-readonly-adapter-diagnostic.v1'
         and value['outcome'] == ('success' if good else 'failure')
         and value['action'] == a['action'] and value['workflow'] == a['workflow']
         and value['requested_path'] == a['requested_path']
         and value['workflow_ids'] in ([], [identifier]), 'diagnostic_identity')
    need(old.job.utc(a['started_utc']) <= old.job.utc(value['started_utc'])
         <= old.job.utc(value['finished_utc']) <= old.job.utc(a['finished_utc']), 'diagnostic_clock')
    need(all(type(value[n]) is int and value[n] >= 0 for n in
             ('page_count', 'received_bytes', 'retained_bytes'))
         and value['retained_bytes'] <= min(MAX_FILE, value['received_bytes']), 'diagnostic_integer_counts')
    if good:
        need(value['code'] == 'completed' and value['workflow_ids'] == [identifier]
             and value['http_status'] is None and value['partial_file'] is None
             and value['received_bytes'] == value['retained_bytes'] == len(buffers[a['output']])
             and buffers[a['stderr']['path']] == b'', 'successful_diagnostic')
        return False
    need(buffers[a['stdout']['path']] == b'', 'failed_diagnostic_stdout')
    partial = a['output'] + '.partial'
    retry = value['code'] in ('network_error', 'incomplete_body', 'content_length_mismatch', 'adapter_deadline')
    retry |= value['code'] == 'http_error' and type(value['http_status']) is int and (
        value['http_status'] == 429 or 500 <= value['http_status'] <= 599)
    need(retry and (value['http_status'] is None or (type(value['http_status']) is int
         and 100 <= value['http_status'] <= 599))
         and value['partial_file'] == PurePosixPath(partial).name and partial in buffers
         and len(buffers[partial]) == value['retained_bytes'], 'typed_transport_loss_and_retained_partial')
    return True


def observation(old, raw, workflow, identifier):
    value = parse(raw)
    need(type(value.get('matches')) is list and len(value['matches']) == 1, 'sole_observation')
    actual = value['matches'][0]
    need(type(actual['version']) is int and actual['version'] == 1 and actual['id'] == identifier,
         'observed_original_uuid_version')
    status = old.job.server_status(value, workflow)
    if status not in ('finished', 'failed', 'stopped'):
        raise Unknown('original_nonterminal_requires_external_evidence')
    need(status == 'finished', 'original_terminal_failure_not_retryable')


def visible(old, buffers, entry, snapshot, snapshot_raw, identifier):
    transport = parse(buffers['transport.json'])
    successful = {a['output'] for a in transport['attempts'] if a['outcome'] == 'success'}
    for a in transport['attempts']:
        if a['outcome'] != 'success':
            need(a['output'] not in buffers, 'failed_matching_partial_never_canonical')
    artifacts = {n: raw for n, raw in buffers.items() if n.startswith('artifacts/') and n in successful}
    for name, raw in artifacts.items():
        if name.endswith('.json') or name.endswith('child_raw.bin'):
            parse(raw)
    manifest = artifacts.get('artifacts/artifacts.sha256.json')
    if manifest is not None:
        values = parse(manifest)
        need(set(values) == {'outputs/' + n for n in OUTPUTS[:-1]}
             and all(hash_value(v) for v in values.values()), 'visible_artifact_manifest')
        need(all(sha(raw) == values['outputs/' + PurePosixPath(name).name]
                 for name, raw in artifacts.items() if name != 'artifacts/artifacts.sha256.json'),
             'visible_artifact_hash')
    result = artifacts.get('artifacts/result.json')
    if result is not None:
        value = parse(result)
        need(same(value['case'], entry['specification']) and value['source_revision'] == snapshot['source_revision']
             and value['snapshot_sha256'] == sha(snapshot_raw) and value['source_sha256'] == snapshot['source_sha256']
             and value['payload_sha256'] == entry['payload_sha256'], 'visible_source_drift')
        need(value.get('passed') is True, 'visible_job_or_method_failure')
    runtime = artifacts.get('artifacts/runtime.json')
    if runtime is not None:
        value = parse(runtime)
        need(identifier in PurePosixPath(value['job_path']).parts and type(value['optimized']) is int
             and value['optimized'] == 0, 'visible_runtime_uuid_drift')
        need(value['schema'] == old.job.RUNTIME_SCHEMA and value['declared_resources'] == old.job.RESOURCES
             and type(value['visible_cpus']) is int and value['visible_cpus'] > 0,
             'visible_runtime_schema_resources')
    command_raw = artifacts.get('artifacts/command.json')
    if command_raw is not None:
        value = parse(command_raw)
        cleanup = value['cleanup']
        leader = cleanup['leader_identity']
        need(value['schema'] == 'openmhd.galaxy-python-command.v1'
             and value['outcome'] == 'success' and type(value['returncode']) is int
             and value['returncode'] == 0 and value['error_type'] is None
             and type(value['pid']) is int and value['pid'] > 0
             and type(value['process_group']) is int and value['process_group'] == value['pid']
             and type(value['timeout_seconds']) is int and value['timeout_seconds'] == 180
             and value['timeout_scope'] == 'direct-child-wait'
             and all(cleanup[n] is True for n in ('direct_child_reaped', 'writers_settled', 'leader_held_until_group_close'))
             and cleanup['group_authority_lost'] is False and cleanup['remaining_live_pids'] == []
             and all(type(leader[n]) is int and leader[n] == value['pid'] for n in ('pid', 'process_group', 'session'))
             and type(leader['starttime']) is str and re.fullmatch('[0-9]+', leader['starttime']),
             'visible_command_held_leader_closure')
        old.job.interval(value)
        if runtime is not None:
            rt = parse(runtime)
            need(value['command'] == old.job.expected_command(rt, entry['specification'])
                 and value['cwd'] == str(Path(rt['job_path']).parent / 'source'), 'visible_actual_command')
        if result is not None:
            need(parse(result)['command_sha256'] == sha(command_raw), 'visible_command_result_hash')
    for name in ('artifacts/child_raw.bin', 'artifacts/child_result.json'):
        if name in artifacts:
            value = parse(artifacts[name])
            child = value['value'] if name.endswith('child_result.json') else value
            need(child['passed'] is True and child['selector'] == entry['specification']['selector']
                 and same(child['executed_identity'], snapshot['test_identities'][child['selector']])
                 and type(child['tests_run']) is int and child['tests_run'] == 1
                 and all(type(child[n]) is int and child[n] == 0 for n in
                         ('errors', 'failures', 'skipped', 'expected_failures', 'unexpected_successes')),
                 'visible_exact_one_leaf_or_failure')
            if runtime is not None:
                old.job.validate_child(child, entry['specification'], snapshot, parse(runtime))
    if result is not None:
        child = parse(result)['child_result']
        need(child['passed'] is True and type(child['tests_run']) is int and child['tests_run'] == 1
             and all(type(child[n]) is int and child[n] == 0 for n in
                     ('errors', 'failures', 'skipped', 'expected_failures', 'unexpected_successes')),
             'visible_embedded_child_failure')
        if runtime is not None:
            old.job.validate_child(child, entry['specification'], snapshot, parse(runtime))
    return artifacts


def disposition(row, losses):
    if row['status'] == 'failed':
        raise Rejected('actual_complete_method_failure_not_retryable')
    if losses:
        need(row['status'] == 'incomplete', 'loss_cannot_mask_semantic_verdict')
        return 'loss'
    need(row['status'] == 'passed' and row['classification'] == 'validated_independent_unittest'
         and row['external_evidence_required'] is False, 'semantic_invalid_complete_capture')
    return 'passed'


def inspect_case(old, buffers, snapshot, snapshot_raw, entry, submission, command, identifier):
    for name, raw in buffers.items():
        if name.endswith('.json') or name.endswith('child_raw.bin'):
            parse(raw)
    transport = parse(buffers['transport.json'])
    need(type(transport['attempts']) is list and transport['attempts'], 'attempts_required')
    if any(a.get('outcome') == 'pending_launch' for a in transport['attempts']):
        raise Unknown('pending_adapter_intent')
    old.validate_transport(buffers, entry, command)
    losses = [diagnostic(old, buffers, a, identifier) for a in transport['attempts']]
    visible(old, buffers, entry, snapshot, snapshot_raw, identifier)
    for a in transport['attempts']:
        if a['action'] == 'observe' and a['outcome'] == 'success':
            observation(old, buffers[a['output']], entry['workflow'], identifier)
    row = old.case_row(buffers, snapshot, snapshot_raw, entry, submission, command)
    result = disposition(row, any(losses))
    return dict(disposition=result, row=row)


def consistent(captures):
    """Detect changed successfully acquired remote artifacts; never graft them."""
    seen = {}
    for buffers in captures:
        for a in parse(buffers['transport.json'])['attempts']:
            name = a['output']
            if a['outcome'] == 'success' and name.startswith('artifacts/'):
                need(name not in seen or seen[name] == buffers[name], 'changed_remote_body_between_origins')
                seen[name] = buffers[name]


def select_complete(candidates):
    need(candidates and all(c['disposition'] in ('passed', 'loss') for c in candidates), 'candidate_disposition')
    return next((i for i, c in enumerate(candidates) if c['disposition'] == 'passed'), None)


def origin_graph(old, roots, release):
    need(type(roots) in (list, tuple) and len(roots) == len(release['origins']), 'exact_external_origin_roots')
    found, context_value = {}, None
    for root in roots:
        root = plain(root)
        original = tree(root)
        manifest_raw = read(root, 'files.sha256.json')
        digest = sha(manifest_raw)
        need(digest not in found, 'duplicate_external_origin')
        expected = next((r for r in release['origins'] if r['manifest_sha256'] == digest), None)
        need(expected is not None and sha(read(root, 'summary.json')) == expected['summary_sha256'], 'root_admitted_origin')
        for name in original['files']:
            if name.endswith('.json'):
                parse(read(root, name))
        summary = old.verify_packet(root)  # unchanged full old verifier, including source guards
        need(summary['collection_status'] == 'complete', 'closed_complete_origin_only')
        current = context(old, root, release)
        if context_value is None:
            context_value = current
        else:
            need(current == context_value, 'conflicting_original_context')
        need(tree(root) == original, 'origin_generation_fence')
        found[digest] = dict(root=root, tree=original, summary=summary,
                            command=parse(read(root, 'context_capture.json'))['adapter_argv'])
    need(set(found) == {r['manifest_sha256'] for r in release['origins']}, 'complete_origin_coverage')
    return found, context_value


def inspect_origins(old, graph, release, ctx, identifiers):
    buffers, snapshot, plan, submission = ctx
    result = {}
    for entry in plan['cases']:
        captures, candidates = [], []
        for origin in release['origins']:
            digest = origin['manifest_sha256']
            item = graph[digest]
            case = case_buffers(item['root'] / 'cases' / entry['directory'])
            inspected = inspect_case(old, case, snapshot, buffers['shared/snapshot.json'], entry,
                submission[entry['workflow']], item['command'], identifiers[entry['directory']])
            captures.append(case)
            candidates.append(dict(inspected, origin=dict(kind='original', manifest_sha256=digest,
                path='cases/' + entry['directory']), case_tree=tree(item['root'] / 'cases' / entry['directory'])))
        consistent(captures)
        choice = select_complete(candidates)
        result[entry['directory']] = dict(captures=captures, candidates=candidates, choice=choice)
    return result


def bounded(perform):
    for index in range(1, 4):
        value = perform(index)
        need(value['disposition'] in ('loss', 'passed'), 'unknown_retry_result')
        if value['disposition'] == 'passed':
            return value
    raise Rejected('three_settled_transport_losses_exhausted')


def attempt(old, root, entry, snapshot, snapshot_raw, submission, command, identifier, observe_only=False):
    root.mkdir(parents=True)
    state = dict(status='running', started_utc=utc(), finished_utc=None,
                 external_evidence_required=True, **SCOPE)
    try:
        publish(root, 'state.json', state)
        case = root / 'case'
        case.mkdir()
        (case / 'transport').mkdir()
        (case / 'artifacts').mkdir()
        record = dict(schema='openmhd.galaxy-python-transport.v1', client_argv=command,
                      workflow=entry['workflow'], attempts=[], origin='server')
        requests = [('observe', 'server-before.json')]
        if not observe_only:
            requests += [('download', n) for n in OUTPUTS] + [('observe', 'server-after.json')]
        loss = False
        for action, name in requests:
            a = old.prepare.adapter_attempt(command, action, entry['workflow'], name, case, record, required=False)
            captured = case_buffers(case)
            old.validate_transport(captured, entry, command)
            loss |= diagnostic(old, captured, a, identifier)
            visible(old, captured, entry, snapshot, snapshot_raw, identifier)
            if action == 'observe':
                if a['outcome'] == 'success':
                    observation(old, captured[name], entry['workflow'], identifier)
                elif name == 'server-before.json':
                    break  # consumes this attempt; no downloads under unknown identity
        captured = case_buffers(case)
        value = (dict(disposition='loss' if loss else 'passed', row=None) if observe_only else
            inspect_case(old, captured, snapshot, snapshot_raw, entry, submission, command, identifier))
        publish(root, 'capture.json', dict(schema='openmhd.python-whole-case-attempt.v1',
            directory=entry['directory'], workflow=entry['workflow'], uuid=identifier,
            observation_only=observe_only, case_tree=tree(case), result=value, **SCOPE))
        state.update(status=value['disposition'], finished_utc=utc(), external_evidence_required=False)
        publish(root, 'state.json', state)
        return dict(value, path=root)
    except BaseException as error:
        state.update(status='failed' if isinstance(error, Rejected) and not isinstance(error, Unknown)
                     else 'unknown', error_type=type(error).__name__, external_evidence_required=True)
        try:
            publish(root, 'state.json', state)
        except BaseException:
            pass
        raise


def seal(root):
    publish(root, 'files.sha256.json', dict(schema=FILES, tree=tree(root, ('files.sha256.json',)), **SCOPE))


def closed(root):
    raw = read(root, 'files.sha256.json')
    value = parse(raw)
    need(same(value, dict(schema=FILES, tree=tree(root, ('files.sha256.json',)), **SCOPE)), 'closed_recovered_inventory')
    return raw


def summary_value(release, expected_release, snapshot, plan, selected, graph):
    need(len(selected) == len(plan['cases']) and all(r['row']['status'] == 'passed' for r in selected),
         'full_catalog_strict_selection')
    return dict(schema=SUMMARY, source_revision=snapshot['source_revision'],
        snapshot_sha256=release['catalog']['snapshot_sha256'],
        preflight_certificate_sha256=release['catalog']['certificate_sha256'],
        plan_sha256=release['catalog']['plan_sha256'], submission_sha256=release['catalog']['submission_sha256'],
        release_sha256=expected_release, provider_sha256=release['provider_sha256'],
        catalog=dict(selectors=snapshot['tests'], test_identities=snapshot['test_identities'],
                     test_files=snapshot['test_files']), expected_cases=len(plan['cases']),
        counts=dict(passed=len(plan['cases']), failed=0, pending=0, incomplete=0),
        whole_catalog_passed=True, cases=selected,
        original_outcomes={h: dict(counts=v['summary']['counts'], whole_suite_passed=v['summary']['whole_suite_passed'])
                           for h, v in graph.items()},
        authenticated_external_prerequisite=False, **SCOPE)


def verify_attempt(old, root, entry, ctx, command, identifier, observe_only=False):
    buffers, snapshot, _, submission = ctx
    need({p.name for p in root.iterdir()} == {'case', 'state.json', 'capture.json'}, 'attempt_exact_inventory')
    state, capture = parse(read(root, 'state.json')), parse(read(root, 'capture.json'))
    case = case_buffers(root / 'case')
    transport = parse(case['transport.json'])
    old.validate_transport(case, entry, command)
    losses = [diagnostic(old, case, a, identifier) for a in transport['attempts']]
    if observe_only:
        need(len(transport['attempts']) == 1, 'one_inventory_observation')
        if not any(losses):
            observation(old, case['server-before.json'], entry['workflow'], identifier)
        actual = dict(disposition='loss' if any(losses) else 'passed', row=None)
    else:
        actual = inspect_case(old, case, snapshot, buffers['shared/snapshot.json'], entry,
                              submission[entry['workflow']], command, identifier)
    need(same(capture, dict(schema='openmhd.python-whole-case-attempt.v1', directory=entry['directory'],
        workflow=entry['workflow'], uuid=identifier, observation_only=observe_only,
        case_tree=tree(root / 'case'), result=actual, **SCOPE)), 'whole_attempt_capture_links')
    keys(state, ('status', 'started_utc', 'finished_utc', 'external_evidence_required', *SCOPE))
    need(state['status'] == actual['disposition'] and state['external_evidence_required'] is False
         and all(state[n] is False for n in SCOPE)
         and old.job.utc(state['started_utc']) <= old.job.utc(transport['attempts'][0]['started_utc'])
         <= old.job.utc(transport['attempts'][-1]['finished_utc']) <= old.job.utc(state['finished_utc']), 'closed_attempt_clock_authority')
    return actual, case


def sequence_paths(root):
    need(root.is_dir(), 'attempt_sequence_directory')
    paths = sorted(root.iterdir())
    need(0 < len(paths) <= 3 and [p.name for p in paths] == [f'{i:02d}' for i in range(1, len(paths) + 1)],
         'bounded_no_counter_reset_sequence')
    return paths


def live_selection(old, root, entry, ctx, command, identifier, captures):
    latest, clocks = None, {}
    for phase in ('before', 'case', 'after'):
        parent = root / ('attempts' if phase == 'case' else 'inventory/' + phase) / entry['directory']
        previous = None
        previous_end = None
        for path in sequence_paths(parent):
            need(previous is None or previous['disposition'] == 'loss', 'no_attempt_after_complete')
            actual, case = verify_attempt(old, path, entry, ctx, command, identifier, phase != 'case')
            times = parse(case['transport.json'])['attempts']
            clocks.setdefault(phase, []).append((old.job.utc(times[0]['started_utc']),
                                                 old.job.utc(times[-1]['finished_utc'])))
            need(previous_end is None or previous_end <= clocks[phase][-1][0], 'retry_clock_order')
            previous_end = clocks[phase][-1][1]
            if phase == 'case':
                captures.append(case)
                consistent(captures)
                latest = dict(actual, origin=dict(kind='attempt',
                    path='attempts/' + entry['directory'] + '/' + path.name,
                    capture_sha256=sha(read(path, 'capture.json'))), case_tree=tree(path / 'case'))
            previous = actual
        need(previous['disposition'] == 'passed', 'closed_successful_phase_required')
    need(max(e for _, e in clocks['before']) <= min(s for s, _ in clocks['case'])
         and max(e for _, e in clocks['case']) <= min(s for s, _ in clocks['after']), 'inventory_case_clock_bracket')
    return latest


def invocation_check(old, value, command, release, ctx):
    keys(value, ('schema', 'output_path', 'provider_sha256', 'adapter_sha256', 'adapter_interpreter',
                 'host_interpreter', 'input_sources', *SCOPE))
    need(value['schema'] == 'openmhd.python-complete-case-invocation.v1'
         and value['provider_sha256'] == release['provider_sha256']
         and value['adapter_sha256'] == release['helpers']['reana_metadata_readonly_adapter.py']
         and type(value['output_path']) is str and Path(value['output_path']).is_absolute()
         and value['output_path'] == release['invocation_path']
         and all(value[n] is False for n in SCOPE), 'invocation_source_links')
    host = value['host_interpreter']
    keys(host, ('executable', 'python', 'optimized'))
    need(type(host['executable']) is str and Path(host['executable']).is_absolute()
         and type(host['python']) is str and type(host['optimized']) is int and host['optimized'] == 0,
         'observed_host_interpreter')
    if command is None:
        need(value['adapter_interpreter'] is None and value['input_sources'] is None, 'offline_only_invocation')
        return
    old.job.credential_free_argv(command)
    need(command[1] == str(Path(value['output_path']) / 'tools/reana_metadata_readonly_adapter.py'),
         'retained_actual_adapter_source_path_link')
    item = value['adapter_interpreter']
    keys(item, ('bytes', 'sha256'))
    need(type(item['bytes']) is int and 0 < item['bytes'] <= MAX_FILE and hash_value(item['sha256']),
         'measured_interpreter_file_pin')
    buffers, snapshot, plan, _ = ctx
    # Original paths are retained observations; validate_witnesses binds their
    # stored bytes/roles without dereferencing them during offline relocation.
    old.validate_witnesses(dict(schema=old.CAPTURE_SCHEMA, sources=value['input_sources'],
        adapter_argv=command, adapter_source_sha256=value['adapter_sha256'], **SCOPE),
        buffers, plan, snapshot)


def verify(root, release_sha256, origins):
    root = plain(root)
    manifest_raw = closed(root)
    release_raw = read(root, 'release.json')
    release = authenticate(release_raw, release_sha256)
    own_source(release)
    old = helpers(root / 'tools', release)
    graph, ctx = origin_graph(old, origins, release)
    original, snapshot, plan, submission = ctx
    need({n: read(root / 'context', n) for n in tree(root / 'context')['files']} == original, 'retained_original_context')
    need(set(tree(root / 'context')['directories']) == {p.as_posix() for n in original
         for p in PurePosixPath(n).parents if p.as_posix() != '.'}, 'exact_context_directories')
    identifiers = ids(read(root, 'uuids.json'), release, plan)
    candidates = inspect_origins(old, graph, release, ctx, identifiers)
    state = parse(read(root, 'status.json'))
    keys(state, ('status', 'started_utc', 'finished_utc', 'external_evidence_required', *SCOPE))
    need(state['status'] == 'complete' and state['external_evidence_required'] is False
         and all(state[n] is False for n in SCOPE)
         and old.job.utc(state['started_utc']) <= old.job.utc(state['finished_utc']), 'finalized_invocation_only')
    command = parse(read(root, 'command.json'))
    need(command is None or (type(command) is list and len(command) == 2
         and all(type(n) is str and Path(n).is_absolute() for n in command)), 'retained_command_shape')
    invocation_check(old, parse(read(root, 'invocation.json')), command, release, ctx)
    selected, live_names = [], set()
    for entry in plan['cases']:
        index = entry['directory']
        values = candidates[index]
        choice = values['choice']
        if choice is not None:
            chosen = values['candidates'][choice]
        else:
            need(release['get_acquisition_authorized'] is True and command is not None, 'explicit_get_release')
            need(Path(command[1]).name == 'reana_metadata_readonly_adapter.py', 'original_adapter_name')
            live_names.add(index)
            chosen = live_selection(old, root, entry, ctx, command, identifiers[index], values['captures'])
        selected.append(dict(directory=index, selector=entry['specification']['selector'], workflow=entry['workflow'],
            uuid=identifiers[index], origin=chosen['origin'], case_tree=chosen['case_tree'], row=chosen['row']))
    for name in ('attempts', 'inventory/before', 'inventory/after'):
        need({p.name for p in (root / name).iterdir()} == live_names, 'no_unlisted_or_unselected_attempts')
    need(set(p.name for p in root.iterdir()) == {'release.json', 'uuids.json', 'tools', 'context', 'command.json',
        'status.json', 'invocation.json', 'attempts', 'inventory', 'selection.json', 'summary.json', 'files.sha256.json'}, 'exact_recovered_root')
    need({p.name for p in (root / 'inventory').iterdir()} == {'before', 'after'}
         and set(tree(root / 'tools')['files']) == set(TOOLS), 'exact_tools_and_inventory')
    need(not tree(root / 'tools')['directories'], 'no_hidden_tool_directories')
    for folder in (root / 'attempts', root / 'inventory/before', root / 'inventory/after'):
        for state_path in folder.glob('*/*/state.json'):
            attempt_state = parse(read(state_path.parent, state_path.name))
            need(old.job.utc(state['started_utc']) <= old.job.utc(attempt_state['started_utc'])
                 <= old.job.utc(attempt_state['finished_utc']) <= old.job.utc(state['finished_utc']),
                 'attempt_within_original_invocation')
    summary = summary_value(release, release_sha256, snapshot, plan, selected, graph)
    need(same(parse(read(root, 'selection.json')), selected)
         and same(parse(read(root, 'summary.json')), summary), 'derived_exact_selection_and_summary')
    need(old.host_tools(snapshot) == {n: read(root / 'tools', n) for n in TOOLS}, 'final_frozen_helper_fence')
    own_source(release)
    need(closed(root) == manifest_raw, 'final_recovery_closure_fence')
    for digest, item in graph.items():
        need(tree(item['root']) == item['tree'] and sha(read(item['root'], 'files.sha256.json')) == digest,
             'final_origin_fence')
    return summary


def recover(release_path, release_sha256, uuid_path, origins, tools_dir, output, interpreter=None,
            source_dir=None, preflight_dir=None, cases_dir=None):
    """Future root-authorized GET only; exclusive invocation, never resumable."""
    release_path, uuid_path, output = plain(release_path), plain(uuid_path), plain(output)
    release_raw = read(release_path.parent, release_path.name)
    release = authenticate(release_raw, release_sha256)  # before supplied code imports
    own_source(release)
    need(str(output) == release['invocation_path'], 'root_released_invocation_path')
    need(not output.exists() and not output.is_symlink() and output.parent.is_dir(), 'fresh_exclusive_destination')
    output.mkdir()
    state = dict(status='running', started_utc=utc(), finished_utc=None, external_evidence_required=True, **SCOPE)
    try:
        publish(output, 'status.json', state)
        old = helpers(tools_dir, release)
        graph, ctx = origin_graph(old, origins, release)
        original, snapshot, plan, submission = ctx
        uuid_raw = read(uuid_path.parent, uuid_path.name)
        identifiers = ids(uuid_raw, release, plan)
        candidates = inspect_origins(old, graph, release, ctx, identifiers)
        for name, raw in original.items():
            put(output / 'context', name, raw)
        for name in TOOLS:
            put(output / 'tools', name, read(tools_dir, name))
        put(output, 'release.json', release_raw)
        put(output, 'uuids.json', uuid_raw)
        for directory in ('attempts', 'inventory/before', 'inventory/after'):
            (output / directory).mkdir(parents=True)
        missing = [e for e in plan['cases'] if candidates[e['directory']]['choice'] is None]
        command, original_inputs = None, None
        if missing:
            need(release['get_acquisition_authorized'] is True and interpreter is not None
                 and all(p is not None for p in (source_dir, preflight_dir, cases_dir)), 'explicit_live_source_input_release')
            original_inputs = old.capture_context(source_dir, preflight_dir, cases_dir)
            need(original_inputs[0] == original, 'original_staged_input_bytes')
            command = [str(plain(interpreter)), str(output / 'tools/reana_metadata_readonly_adapter.py')]
            old.pinned_tools(snapshot, command)
        publish(output, 'command.json', command)
        interpreter_pin = pin(read(Path(command[0]).parent, Path(command[0]).name)) if command else None
        invocation = dict(schema='openmhd.python-complete-case-invocation.v1', output_path=str(output),
            provider_sha256=release['provider_sha256'],
            adapter_sha256=release['helpers']['reana_metadata_readonly_adapter.py'],
            adapter_interpreter=interpreter_pin,
            host_interpreter=dict(executable=sys.executable, python=sys.version, optimized=sys.flags.optimize),
            input_sources=original_inputs[1] if original_inputs else None, **SCOPE)
        invocation_check(old, invocation, command, release, ctx)
        publish(output, 'invocation.json', invocation)
        for entry in missing:
            index = entry['directory']
            for phase in ('before', 'case', 'after'):
                parent = output / ('attempts' if phase == 'case' else 'inventory/' + phase) / index
                def perform(number):
                    value = attempt(old, parent / f'{number:02d}', entry, snapshot,
                        original['shared/snapshot.json'], submission[entry['workflow']], command,
                        identifiers[index], phase != 'case')
                    if phase == 'case':
                        candidates[index]['captures'].append(case_buffers(value['path'] / 'case'))
                        consistent(candidates[index]['captures'])
                    return value
                bounded(perform)
        need(read(release_path.parent, release_path.name) == release_raw
             and read(uuid_path.parent, uuid_path.name) == uuid_raw, 'final_release_uuid_bytes')
        if original_inputs is not None:
            need(old.capture_context(source_dir, preflight_dir, cases_dir) == original_inputs, 'final_staged_input_generation')
            old.pinned_tools(snapshot, command)
            need(pin(read(Path(command[0]).parent, Path(command[0]).name)) == interpreter_pin,
                 'final_actual_interpreter_bytes')
        # Derive through the same offline logic in a subsequent fresh process.
        # No provisional success summary is accepted: build exact selections now.
        selected = []
        for entry in plan['cases']:
            index, values = entry['directory'], candidates[entry['directory']]
            if values['choice'] is not None:
                chosen = values['candidates'][values['choice']]
            else:
                chosen = live_selection(old, output, entry, ctx, command, identifiers[index], values['captures'])
            selected.append(dict(directory=index, selector=entry['specification']['selector'], workflow=entry['workflow'],
                uuid=identifiers[index], origin=chosen['origin'], case_tree=chosen['case_tree'], row=chosen['row']))
        for digest, item in graph.items():
            need(tree(item['root']) == item['tree'] and sha(read(item['root'], 'files.sha256.json')) == digest,
                 'final_unchanged_external_origin')
        need(old.host_tools(snapshot) == {n: read(output / 'tools', n) for n in TOOLS}, 'final_frozen_helper_fence')
        own_source(release)
        publish(output, 'selection.json', selected)
        publish(output, 'summary.json', summary_value(release, release_sha256, snapshot, plan, selected, graph))
        state.update(status='complete', finished_utc=utc(), external_evidence_required=False)
        publish(output, 'status.json', state)
        seal(output)
        return parse(read(output, 'summary.json'))
    except BaseException as error:
        state.update(status='failed' if isinstance(error, Rejected) and not isinstance(error, Unknown) else 'unknown',
                     error_type=type(error).__name__, external_evidence_required=True)
        try:
            publish(output, 'status.json', state)
            seal(output)  # forensic only; verify requires literal complete status
        except BaseException:
            pass  # inaccessible storage retains unfinished intent or external evidence
        raise


def compact(snapshot_raw, certificate_raw, summary_raw, manifest_raw, release_raw, expected_release):
    """Compact job-side consistency, NEVER full acquisition/output approval.

    Host preparation/results must call verify on the complete external graph.
    The original pinned job separately verifies its actual import certificate.
    """
    release = authenticate(release_raw, expected_release)
    own_source(release)
    snapshot, summary, manifest = parse(snapshot_raw), parse(summary_raw), parse(manifest_raw)
    need(summary['schema'] == SUMMARY and manifest['schema'] == FILES
         and summary['release_sha256'] == expected_release and summary['provider_sha256'] == release['provider_sha256'],
         'explicit_new_proof_schema')
    for n in SCOPE:
        need(summary[n] is False and manifest[n] is False, 'proof_nonacceptance')
    need(sha(snapshot_raw) == release['catalog']['snapshot_sha256'] == summary['snapshot_sha256']
         and sha(certificate_raw) == release['catalog']['certificate_sha256'] == summary['preflight_certificate_sha256']
         and snapshot['source_revision'] == release['catalog']['source_revision'] == summary['source_revision']
         and snapshot['job_sha256'] == release['catalog']['job_sha256'], 'compact_original_generation')
    need(same(summary['catalog']['selectors'], snapshot['tests'])
         and same(summary['catalog']['test_identities'], snapshot['test_identities'])
         and sha(encode(snapshot['test_identities'])) == release['catalog']['identities_sha256'], 'compact_full_ast_catalog')
    count = len(snapshot['tests'])
    need(type(summary['expected_cases']) is int and summary['expected_cases'] == count
         and same(summary['counts'], dict(passed=count, failed=0, pending=0, incomplete=0))
         and summary['whole_catalog_passed'] is True and type(summary['cases']) is list
         and len(summary['cases']) == count, 'compact_exact_whole_catalog')
    for index, (selector, row) in enumerate(zip(snapshot['tests'], summary['cases'])):
        need(row['directory'] == f'{index:04d}' and row['selector'] == selector
             and row['row']['status'] == 'passed'
             and same(row['row']['identity'], snapshot['test_identities'][selector]), 'compact_exact_selected_leaves')
    files = manifest['tree']['files']
    for name, raw in (('summary.json', summary_raw), ('release.json', release_raw),
                      ('context/shared/snapshot.json', snapshot_raw),
                      ('context/shared/preflight_certificate.json', certificate_raw)):
        need(same(files[name], pin(raw)), 'compact_manifest_body_links')
    return summary


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('recover', 'verify'))
    p.add_argument('--packet', type=Path)
    p.add_argument('--release-sha256', required=True)
    p.add_argument('--origin', type=Path, action='append', required=True)
    for name in ('release', 'uuids', 'tools', 'output', 'interpreter', 'source', 'preflight', 'cases'):
        p.add_argument('--' + name, type=Path)
    a = p.parse_args(argv)
    if a.action == 'verify':
        need(a.packet is not None and all(getattr(a, n) is None for n in
             ('release', 'uuids', 'tools', 'output', 'interpreter', 'source', 'preflight', 'cases')), 'offline_arguments_only')
        value = verify(a.packet, a.release_sha256, a.origin)
    else:
        need(a.packet is None and all(getattr(a, n) is not None for n in ('release', 'uuids', 'tools', 'output')),
             'explicit_recovery_arguments')
        value = recover(a.release, a.release_sha256, a.uuids, a.origin, a.tools, a.output,
                        a.interpreter, a.source, a.preflight, a.cases)
    print(json.dumps(dict(schema=SUMMARY, counts=value['counts'], whole_catalog_passed=value['whole_catalog_passed'], **SCOPE)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
