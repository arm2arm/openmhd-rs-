#!/usr/bin/env python3
"""New-schema whole recovered-native acquisition; GET only, no retries or execution.

Import is stdlib-only. Real verification imports only pinned retained helpers,
uses ONE captured original context, and never executes a compiled artifact.
External dependency paths are supplied anew for relocation, never read from hints.
"""
import argparse
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

CONSUMER_SHA = 'f63583dee293341b3992d2571cebb87e36357fbebb0e2c21d507396fbfd2b58f'
RECOVERY_SHA = 'adb40fe70062c57371cfd8eceb306dc1ce668c6f573e806f866677e6bc181e07'
OUTPUTS = ('result.json', 'runtime.json', 'command.json', 'stdout.txt', 'stderr.txt',
           'child_result.json', 'child_raw.bin', 'artifacts.sha256.json')
DEPENDENCIES = ('recovery', 'origins', 'verifier', 'catalog', 'proof_tools', 'proof_packet',
                'review', 'original_proof_tools', 'original_proof_packet', 'original_review',
                'release_sha256')
CAPTURE_SCHEMA = 'openmhd.recovered-native-results-capture.v1'
SUMMARY_SCHEMA = 'openmhd.recovered-native-results.v1'
FILES_SCHEMA = 'openmhd.recovered-native-results-files.v1'
SOURCE = 'tools/galaxy_evidence/recovered_native_results.py'
TEST_SOURCE = 'scripts/test_galaxy_recovered_native_results.py'
STATUS = ('passed', 'failed', 'pending', 'incomplete')
MAX_FILE = 512 * 1024 * 1024


def require(value, code):
    if not value:
        raise ValueError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def parse(raw):
    def unique(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate_json_key')
            result[key] = value
        return result

    def finite_number(text):
        value = float(text)
        require(math.isfinite(value), 'nonfinite_json_number')
        return value

    return json.loads(raw, object_pairs_hook=unique, parse_float=finite_number,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite_json_constant')))


def keys(value, names):
    require(type(value) is dict and set(value) == set(names), 'exact_schema_keys')


def same(left, right):
    """JSON type-sensitive equality: True and 1 are different evidence."""
    return encode(left) == encode(right)


def now():
    return datetime.now(timezone.utc).isoformat()


def plain(root):
    root = Path(root).absolute()
    for path in (root, *root.parents):
        require(not path.is_symlink(), 'linked_root')
    return root


def path_at(root, name):
    require(type(name) is str, 'path_string')
    p = PurePosixPath(name)
    require(p.parts and p.as_posix() == name and not p.is_absolute()
            and '..' not in p.parts and '\\' not in name, 'unsafe_relative_path')
    target = plain(root)
    for part in p.parts:
        target /= part
        require(not target.is_symlink(), 'linked_path')
    return target


def generation(st):
    return tuple(getattr(st, k) for k in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))


def read(root, name):
    path = path_at(root, name)
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_size <= MAX_FILE, 'regular_bounded_file')
    with path.open('rb') as stream:
        opened = stream.fileno()
        require(generation(os.fstat(opened)) == generation(before), 'changed_open_generation')
        raw = stream.read(MAX_FILE + 1)
        require(generation(os.fstat(opened)) == generation(before), 'changed_read_generation')
    require(generation(path.stat()) == generation(before) and len(raw) == before.st_size,
            'changed_path_generation')
    return raw


def pin(raw):
    return dict(bytes=len(raw), sha256=sha(raw))


def put(root, name, raw):
    target = path_at(root, name)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        require(stream.write(raw) == len(raw), 'short_write')
        stream.flush()
        os.fsync(stream.fileno())


def persist(root, name, value):
    """Replace only our own journal; never a downloaded or original body."""
    target = path_at(root, name)
    tmp = name + '.tmp'
    put(root, tmp, encode(value))
    os.replace(path_at(root, tmp), target)


def inventory(root, exclude=()):
    root = plain(root)
    require(root.is_dir(), 'ordinary_directory')
    result = {}
    for p in sorted(root.rglob('*')):
        require(not p.is_symlink(), 'linked_inventory')
        if p.is_dir():
            continue
        require(p.is_file(), 'special_inventory')
        name = p.relative_to(root).as_posix()
        if name not in exclude:
            result[name] = pin(read(root, name))
    return result


def plain_manifest(raw):
    value = parse(raw)
    require(type(value) is dict and value, 'nonempty_plain_manifest')
    for name, item in value.items():
        require(type(name) is str, 'manifest_path_string')
        p = PurePosixPath(name)
        require(p.parts and p.as_posix() == name and not p.is_absolute()
                and '..' not in p.parts and '\\' not in name, 'manifest_path_syntax')
        keys(item, ('bytes', 'sha256'))
        require(type(item['bytes']) is int and item['bytes'] >= 0 and type(item['sha256']) is str
                and re.fullmatch('[0-9a-f]{64}', item['sha256']), 'typed_manifest_entry')
    return value


def sealed_tree(root):
    raw = read(root, 'files.sha256.json')
    expected = plain_manifest(raw)
    require(same(expected, inventory(root, ('files.sha256.json',))), 'exact_original_seal')
    return raw, expected


def copy_inputs(source, output):
    """Single per-file buffer is checked/copied; final inode+generation fence.

    Full ordinary copies retain every original path (including the old seal).
    There is deliberately no binary/source deduplication or omitted-byte list.
    """
    manifest_raw, expected = sealed_tree(source)
    original = dict(expected, **{'files.sha256.json': pin(manifest_raw)})
    versions = {}
    mapping = {}
    for name, wanted in sorted(original.items()):
        p = path_at(source, name)
        versions[name] = generation(p.stat())
        raw = read(source, name)
        require(pin(raw) == wanted, 'copy_original_identity')
        if name.endswith('.json'):
            parse(raw)  # reject duplicate/nonfinite JSON before older validators
        put(output, name, raw)
        mapping[name] = dict(retained='inputs/' + name, **wanted)
    fence_inputs(source, original, versions)
    require(same(inventory(output), original), 'complete_copied_original_tree')
    return original, versions, mapping


def fence_inputs(root, expected, versions):
    require(same(inventory(root), expected), 'final_original_input_bytes')
    require(all(generation(path_at(root, name).stat()) == old for name, old in versions.items()),
            'final_original_input_generation')


def load_pinned(path, expected, alias):
    raw = read(path.parent, path.name)
    require(sha(raw) == expected, 'pinned_module_before_import')
    spec = importlib.util.spec_from_file_location(alias, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(read(path.parent, path.name) == raw, 'pinned_module_after_import')
    return module


def dependency_arguments(value):
    keys(value, (*DEPENDENCIES, *(('python_evidence',) if 'python_evidence' in value else ())))
    result = {}
    for key in DEPENDENCIES:
        if key == 'release_sha256':
            require(type(value[key]) is str and re.fullmatch('[0-9a-f]{64}', value[key]), 'external_release_hash')
            result[key] = value[key]
        elif key == 'origins':
            require(type(value[key]) is list and value[key], 'explicit_complete_origin_roots')
            require(all(type(p) is str and Path(p).is_absolute() for p in value[key]), 'absolute_origin_roots')
            result[key] = [plain(p) for p in value[key]]
            require(len(result[key]) == len(set(result[key])), 'duplicate_origin_root')
        else:
            require(type(value[key]) is str and Path(value[key]).is_absolute(), 'explicit_absolute_dependency')
            result[key] = plain(value[key])
    if 'python_evidence' in value:
        extra = value['python_evidence']
        keys(extra, ('provider', 'original318_origins', 'later_selected_origins'))
        require(type(extra['provider']) is str and Path(extra['provider']).is_absolute(), 'absolute_python_provider')
        for name in ('original318_origins', 'later_selected_origins'):
            require(type(extra[name]) is list and extra[name]
                    and all(type(p) is str and Path(p).is_absolute() for p in extra[name])
                    and len(set(extra[name])) == len(extra[name]), 'explicit_python_origins')
        result['python_evidence'] = dict(provider=Path(extra['provider']),
            original318_origins=[Path(p) for p in extra['original318_origins']],
            later_selected_origins=[Path(p) for p in extra['later_selected_origins']])
    return result


def plan_shape(plan):
    keys(plan, ('schema', 'component_accepted', 'physical_accepted', 'compiled_snapshot_sha256',
        'later_python_snapshot_sha256', 'recovery_manifest_sha256', 'origin_manifest_sha256',
        'root_release_sha256', 'context_sha256', 'retained_dependencies', 'cases'))
    require(plan['schema'] == 'openmhd.recovered-native-case-plan.v1'
            and plan['component_accepted'] is False and plan['physical_accepted'] is False
            and type(plan['cases']) is list and plan['cases'], 'explicit_nonacceptance_plan')
    workflows, identities = set(), set()
    for index, row in enumerate(plan['cases']):
        keys(row, ('directory', 'workflow', 'specification', 'leaf', 'resources',
                   'payload_sha256', 'workflow_sha256'))
        require(row['directory'] == 'case_' + str(index).zfill(4)
                and row['specification'] == row['directory'] + '/reana.yaml'
                and type(row['workflow']) is str and re.fullmatch(r'[a-z][a-z0-9-]{0,62}\.1', row['workflow'])
                and row['workflow'] not in workflows, 'ordered_unique_workflow_plan')
        workflows.add(row['workflow'])
        leaf = row['leaf']
        require(type(leaf) is dict and type(leaf.get('build_profile')) is str
                and leaf['build_profile'] in ('debug', 'release'), 'actual_profile')
        identity = encode(leaf)
        require(identity not in identities, 'duplicate_leaf')
        identities.add(identity)
        keys(row['resources'], ('threads', 'memory', 'timeout_seconds'))
        r = row['resources']
        require(type(r['threads']) is int and r['threads'] == 1 and type(r['timeout_seconds']) is int
                and r['timeout_seconds'] > 0 and type(r['memory']) is str, 'typed_original_resources')


def submission_map(raw, plan):
    value = parse(raw)
    require(type(value) is dict and set(value) == {r['workflow'] for r in plan['cases']},
            'exact_original_submission_coverage')
    for row in value.values():
        require(type(row) is dict and row.get('status') in ('submitted', 'submission uncertain'),
                'settled_original_submission_status')
        keys(row, ('status',) if row['status'] == 'submitted' else ('status', 'error'))
        require('error' not in row or type(row['error']) is str, 'original_uncertainty_text')
    return value  # never rewrite or normalize the original bytes


def dependency_check(n, inputs, deps):
    """Real full recovery + both full Python output checks, not summary flags.

    Only THIS captured plan context is passed to original_modules/check_plan.
    The original supplied cases path is never imported or passed to a validator.
    """
    original_release = read(inputs / 'context', 'proof/root-release.json')
    require(sha(original_release) == deps['release_sha256'], 'external_release_before_supplied_verifiers')
    plan = n.check_plan(inputs, deps['recovery'], deps['origins'], deps['verifier'], deps['catalog'])
    plan_shape(plan)
    context = inputs / 'context'
    buffers = {name: read(context, name) for name in plan['context_sha256']}
    release_raw = buffers['proof/root-release.json']
    require(sha(release_raw) == deps['release_sha256'] == plan['root_release_sha256'],
            'external_root_release_matches_original_plan')
    release = parse(release_raw)
    control_raw = buffers['proof/snapshot.json']
    control = parse(control_raw)
    own = Path(__file__).absolute()
    require(control.get('source_sha256', {}).get(SOURCE) == sha(read(own.parent, own.name))
            and TEST_SOURCE in control.get('test_files', ())
            and type(control.get('source_sha256', {}).get(TEST_SOURCE)) is str
            and re.fullmatch('[0-9a-f]{64}', control['source_sha256'][TEST_SOURCE]),
            'results_source_and_selected_suite_in_later_proof')
    if release.get('schema') == 'openmhd.recovered-native-root-release.v3':
        evidence = deps.get('python_evidence')
        require(evidence is not None, 'explicit_complete_python_graph')
        later = n.complete_python_proof(deps['proof_packet'], deps['proof_tools'], deps['review'],
                                        release, 'later_selected', evidence)
        original = n.original_control_proof(deps['original_proof_tools'], deps['original_proof_packet'],
            deps['original_review'], release, python_evidence=evidence)
        require(all(buffers[name] == raw for name, raw in {**later, **original}.items()),
                'both_full_recovered_python_graphs_not_summary_normalization')
    else:
        require('python_evidence' not in deps, 'legacy_dependencies_unchanged')
        pins = {name: control['source_sha256']['tools/galaxy_python_evidence/' + name] for name in n.PROOF_TOOLS}
        _, _, collector = n.bundle(deps['proof_tools'],
            ('reana_metadata_job', 'prepare_metadata_reana', 'collect_metadata_reana_results'), pins)
        summary = collector.verify_packet(deps['proof_packet'])
        n.require_control_success(summary, control)
        require(same(summary, parse(buffers['proof/control-summary.json'])), 'full_later_output_summary')
        for source, retained in (('shared/snapshot.json', 'snapshot.json'),
                ('shared/preflight_certificate.json', 'certificate.json'), ('files.sha256.json', 'control-manifest.json'),
                ('summary.json', 'control-summary.json')):
            require(read(deps['proof_packet'], source) == buffers['proof/' + retained], 'whole_later_proof_exact_bytes')
        require(read(deps['review'].parent, deps['review'].name) == buffers['proof/root-output-review.md'],
                'later_root_output_review_bytes')
        original = n.original_control_proof(deps['original_proof_tools'], deps['original_proof_packet'],
                                           deps['original_review'], release)
        require(all(buffers[name] == raw for name, raw in original.items()), 'full_original318_proof_exact_bytes')
    common, _ = n.original_modules(context)
    selected = common.catalog(parse(buffers['preflight/preflight.json']),
        dict(schema='openmhd.galaxy-reviewed-catalog.v1', component_accepted=False,
             targets=parse(buffers['coverage.proposal.json'])['targets']), parse(buffers['snapshot.json']))
    require(len(selected) == len(plan['cases']) and all(same(row['leaf'], leaf)
            and same(row['resources'], resources) for row, (leaf, resources) in zip(plan['cases'], selected)),
            'type_exact_original_catalog_leaves_and_resources')
    # Explicit closure identities are relocation anchors. Absolute path strings
    # in original commands remain historical argv and are never dereferenced.
    anchor = dict(recovery=n.closed(deps['recovery']), origins=sorted(plan['origin_manifest_sha256']),
        catalog=n.closed(deps['catalog']), verifier=sha(read(deps['verifier'].parent, deps['verifier'].name)),
        root_release=sha(release_raw), python_proofs=n.proof_dependencies(release),
        original_compiled_snapshot=plan['compiled_snapshot_sha256'],
        later_python_snapshot=plan['later_python_snapshot_sha256'])
    return plan, common, anchor


def observation(common, raw, workflow, identifier=None, finished=False):
    value = parse(raw)
    keys(value, ('schema', 'origin', 'observed_utc', 'matches'))
    require(type(value['matches']) is list and len(value['matches']) == 1, 'unique_actual_observation')
    row = value['matches'][0]
    keys(row, ('workflow', 'name', 'version', 'status', 'id'))
    require(type(row['version']) is int and row['version'] == 1
            and all(type(row[k]) is str for k in ('workflow', 'name', 'status', 'id')),
            'typed_observed_identity')
    common.supervisor.utc(value['observed_utc'])
    actual = common.observation(raw, workflow, identifier, finished)
    return actual


def transport(common, root, label, workflow, identifier, action, remote, runtime):
    raw = common.transport_body(root, label, workflow, identifier, action, remote)
    row = parse(read(root, label))
    keys(row, ('schema', 'action', 'workflow', 'remote_path', 'output', 'argv', 'cwd', 'adapter_sha256',
               'base_adapter_sha256', 'started_utc', 'finished_utc', 'outcome', 'returncode',
               'stdout', 'stderr', 'stdout_sha256', 'stderr_sha256', 'output_sha256'))
    require(type(row['returncode']) is int and row['argv'][0] == runtime['executable'], 'transport_interpreter_link')
    diagnostic = parse(read(root, row['stdout']))
    stderr = parse(read(root, row['stderr']))
    require(type(stderr) is dict and stderr.get('schema') in
            ('openmhd.galaxy-unavailable-diagnostic.v1', 'openmhd.galaxy-get-diagnostic.v1'),
            'retained_typed_stderr')
    keys(diagnostic, ('schema', 'outcome', 'code', 'started_utc', 'finished_utc', 'action', 'workflow',
        'requested_path', 'workflow_ids', 'http_status', 'received_bytes', 'retained_bytes', 'partial_file', 'page_count'))
    require(diagnostic['partial_file'] is None and type(diagnostic['received_bytes']) is int
            and type(diagnostic['retained_bytes']) is int
            and diagnostic['received_bytes'] == diagnostic['retained_bytes'] == len(raw)
            and type(diagnostic['page_count']) is int and diagnostic['page_count'] > 0,
            'complete_actual_transport_counts')
    utc = common.supervisor.utc
    require(utc(row['started_utc']) <= utc(diagnostic['started_utc'])
            <= utc(diagnostic['finished_utc']) <= utc(row['finished_utc']), 'diagnostic_outer_interval')
    if action == 'observe':
        value = parse(raw)
        require(utc(row['started_utc']) <= utc(value['observed_utc']) <= utc(row['finished_utc']),
                'observed_utc_in_transport')
    return raw, row


def empty_capture(row):
    return dict(schema=CAPTURE_SCHEMA, status='incomplete', directory=row['directory'],
        workflow=row['workflow'], leaf=row['leaf'], resources=row['resources'], uuid=None,
        observed_status=None, before=None, after=None, files={}, error_type=None,
        failure_kind='unattempted', external_terminal_evidence_required=False,
        component_accepted=False, physical_accepted=False)


def verify_capture(n, common, root, case_root, original_context, expected, runtime):
    """Successful route only; forensic/partial packets categorically reject."""
    common.verify_closed(root)
    record = parse(read(root, 'capture.json'))
    keys(record, empty_capture(expected))
    require(record['schema'] == CAPTURE_SCHEMA and record['status'] == 'passed'
            and record['directory'] == expected['directory'] and record['workflow'] == expected['workflow']
            and same(record['leaf'], expected['leaf']) and same(record['resources'], expected['resources'])
            and record['observed_status'] == 'finished' and record['component_accepted'] is False
            and record['physical_accepted'] is False and record['error_type'] is None
            and record['failure_kind'] == 'none' and record['external_terminal_evidence_required'] is False,
            'actual_successful_capture_scope')
    require(type(record['files']) is dict and set(record['files']) == set(OUTPUTS), 'exact_eight_original_artifacts')
    before, first = transport(common, root, record['before'], record['workflow'], record['uuid'], 'observe', None, runtime)
    after, last = transport(common, root, record['after'], record['workflow'], record['uuid'], 'observe', None, runtime)
    require(same(observation(common, before, record['workflow'], record['uuid'], True),
                 observation(common, after, record['workflow'], record['uuid'], True)), 'stable_finished_uuid')
    values, labels = {}, [record['before']]
    for name in OUTPUTS:
        label = record['files'][name]
        raw, receipt = transport(common, root, label, record['workflow'], record['uuid'], 'download', 'outputs/' + name, runtime)
        utc = common.supervisor.utc
        require(utc(first['finished_utc']) <= utc(receipt['started_utc'])
                <= utc(receipt['finished_utc']) <= utc(last['started_utc']), 'downloads_between_observations')
        if name.endswith('.json'):
            parse(raw)
        values[name] = raw
        labels.append(label)
    labels.append(record['after'])
    require(len(labels) == len(set(labels)) == 10, 'ten_distinct_successful_transports')
    common.transport_closure(root, labels)
    allowed = {'capture.json'}
    for label in labels:
        receipt = parse(read(root, label))
        allowed.update((label, receipt['stdout'], receipt['stderr'], receipt['output']))
    require(set(inventory(root, ('files.sha256.json',))) == allowed, 'no_hidden_capture_files')
    case, _ = n.validate_outputs(values, case_root, original_root=original_context)
    result, native_runtime, command = (parse(values[name]) for name in
        ('result.json', 'runtime.json', 'command.json'))
    require(same(result['case'], case) and same(native_runtime['declared_resources'], case['resources'])
            and type(command['timeout_seconds']) is int
            and type(command['process_group']) is int
            and all(type(command['cleanup']['leader_identity'][name]) is int
                    for name in ('pid', 'process_group', 'session'))
            and ('physical_accepted' not in result or result['physical_accepted'] is False),
            'type_exact_native_identity_and_scope')
    require(case['workflow'] == expected['workflow'] and same(case['leaf'], expected['leaf'])
            and same(case['resources'], expected['resources']), 'validated_actual_case_identity')
    common.verify_closed(root)
    return record


def acquire_case(n, common, root, case_root, original_context, row, runtime):
    root.mkdir()
    record = empty_capture(row)
    persist(root, 'capture.json', record)
    observed = None
    try:
        raw, label, identifier = common.attempt(root, 'observe', row['workflow'])
        record.update(uuid=identifier, before=label)
        observed = observation(common, raw, row['workflow'], identifier)
        record['observed_status'] = observed['status']
        if observed['status'] not in ('finished', 'failed', 'stopped'):
            record.update(status='pending', failure_kind='remote_nonterminal')
        else:
            for name in OUTPUTS:
                try:
                    _, receipt, actual = common.attempt(root, 'download', row['workflow'], 'outputs/' + name)
                    require(actual == identifier, 'download_uuid_changed')
                    record['files'][name] = receipt
                except Exception as error:
                    record.update(status='incomplete', error_type=type(error).__name__,
                                  failure_kind='transport_or_observation', external_terminal_evidence_required=True)
                persist(root, 'capture.json', record)
        after, label, actual = common.attempt(root, 'observe', row['workflow'])
        record['after'] = label
        require(actual == identifier and same(observation(common, after, row['workflow'], identifier), observed),
                'after_identity_or_status_changed')
        if observed['status'] in ('failed', 'stopped'):
            record.update(status='failed', failure_kind='remote_terminal_failure')
        elif observed['status'] == 'finished' and len(record['files']) == len(OUTPUTS) and record['error_type'] is None:
            record.update(status='passed', failure_kind='none')
    except BaseException as error:
        record.update(status='incomplete', error_type=type(error).__name__, failure_kind='transport_or_observation',
                      external_terminal_evidence_required=True)
        if not isinstance(error, Exception):
            record['failure_kind'] = 'interrupted_or_unknown'
            raise
    finally:
        persist(root, 'capture.json', record)
        common.close(root)
    if record['status'] == 'passed':
        try:
            verify_capture(n, common, root, case_root, original_context, row, runtime)
        except Exception as error:
            # Not a sealed successful result: preserve all bodies, explicitly
            # supersede our own provisional capsule before whole publication.
            (root / 'files.sha256.json').unlink()
            record.update(status='failed', error_type=type(error).__name__, failure_kind='native_or_capture_rejected')
            persist(root, 'capture.json', record)
            common.close(root)
    return record


def derive(n, common, root, plan, runtime):
    rows, identifiers = [], set()
    for expected in plan['cases']:
        folder = root / expected['directory']
        common.verify_closed(folder)
        record = parse(read(folder, 'capture.json'))
        keys(record, empty_capture(expected))
        require(record['schema'] == CAPTURE_SCHEMA and record['status'] in STATUS
                and record['directory'] == expected['directory'] and record['workflow'] == expected['workflow']
                and same(record['leaf'], expected['leaf']) and same(record['resources'], expected['resources'])
                and record['component_accepted'] is False and record['physical_accepted'] is False
                and type(record['external_terminal_evidence_required']) is bool,
                'exact_actual_capture_coverage')
        if record['uuid'] is not None:
            require(type(record['uuid']) is str and record['uuid'] not in identifiers, 'unique_actual_workflow_UUIDs')
            identifiers.add(record['uuid'])
        if record['status'] == 'passed':
            verify_capture(n, common, folder, root / 'inputs' / expected['directory'], root / 'inputs/context', expected, runtime)
        rows.append(record)
    counts = {status: sum(r['status'] == status for r in rows) for status in STATUS}
    return rows, counts, bool(rows) and counts['passed'] == len(plan['cases'])


def runtime_record():
    return dict(schema='openmhd.recovered-native-results-host-runtime.v1', executable=sys.executable,
        python=sys.version, implementation=sys.implementation.name, optimized=sys.flags.optimize,
        adapter_timeout_seconds=300, scope='metadata acquisition/offline verification; no binary execution',
        component_accepted=False, physical_accepted=False)


def packet_layout(root, plan, capture, *, sealed):
    allowed = {'inputs', 'helpers', 'summary.json', 'runtime.json', 'submission_original.json',
               'input_capture.json'} | {r['directory'] for r in plan['cases']}
    if sealed:
        allowed.add('files.sha256.json')
    require(type(capture['history']) is list, 'history_list')
    if capture['history']:
        allowed.add('history')
    require({p.name for p in root.iterdir()} == allowed, 'exact_successful_root_inventory')
    require(set(inventory(root / 'helpers')) == set(capture['helper_sha256']), 'no_hidden_helpers')
    history_names = set()
    for index, item in enumerate(capture['history']):
        keys(item, ('original_path', 'retained', 'bytes', 'sha256'))
        require(type(item['original_path']) is str and Path(item['original_path']).is_absolute()
                and type(item['bytes']) is int and item['bytes'] >= 0
                and item['retained'] == 'history/' + str(index).zfill(4) + '.bin'
                and same(pin(read(root, item['retained'])), {k: item[k] for k in ('bytes', 'sha256')}),
                'retained_original_history')
        history_names.add(item['retained'])
    if history_names:
        require({'history/' + n for n in inventory(root / 'history')} == history_names, 'no_hidden_history')


def seal(root):
    put(root, 'files.sha256.json', encode(dict(schema=FILES_SCHEMA,
        files=inventory(root, ('files.sha256.json',)), component_accepted=False, physical_accepted=False)))


def closed_packet(root):
    raw = read(root, 'files.sha256.json')
    value = parse(raw)
    keys(value, ('schema', 'files', 'component_accepted', 'physical_accepted'))
    require(value['schema'] == FILES_SCHEMA and value['component_accepted'] is False
            and value['physical_accepted'] is False, 'new_results_closure_schema')
    require(same(value['files'], inventory(root, ('files.sha256.json',))), 'closed_results_inventory')
    return raw


def collect(cases, submission, dependencies, consumer, output, history=(), *, arguments=None):
    require(__debug__ and sys.flags.optimize == 0, 'optimized_results_rejected')
    require(sys.dont_write_bytecode, 'use_B_to_preserve_original_source_trees')
    cases, output = plain(cases), plain(output)
    require(not output.exists() and output != cases and cases not in output.parents, 'fresh_separate_results')
    require(cases not in plain(submission).parents, 'submission_external_to_original_seal')
    output.mkdir(parents=True)
    summary = dict(schema=SUMMARY_SCHEMA, status='preparing', whole_catalog_passed=False, cases=[],
        counts=dict.fromkeys(STATUS, 0), component_accepted=False, physical_accepted=False,
        error_type=None, external_terminal_evidence_required=False)
    persist(output, 'summary.json', summary)
    try:
        # Must happen BEFORE loading original modules anywhere in this process.
        originals, versions, mapping = copy_inputs(cases, output / 'inputs')
        submit_generation = generation(submission.stat())
        raw = read(submission.parent, submission.name)
        require(generation(submission.stat()) == submit_generation, 'submission_capture_generation')
        put(output, 'submission_original.json', raw)
        plan = parse(read(output / 'inputs', 'plan.json'))
        plan_shape(plan)
        submission_map(raw, plan)
        history_pins = []
        for index, source in enumerate(history):
            body = read(source.parent, source.name)
            name = 'history/' + str(index).zfill(4) + '.bin'
            put(output, name, body)
            history_pins.append(dict(original_path=str(source), retained=name, **pin(body)))
        for name, path, expected in (('recovered_native.py', consumer, CONSUMER_SHA),
                ('recover_preflight.py', dependencies['verifier'], RECOVERY_SHA)):
            body = read(path.parent, path.name)
            require(sha(body) == expected, 'exact_new_and_original_verifier_sources')
            put(output, 'helpers/' + name, body)
        own = Path(__file__).absolute()
        own_raw = read(own.parent, own.name)
        put(output, 'helpers/recovered_native_results.py', own_raw)
        n = load_pinned(output / 'helpers/recovered_native.py', CONSUMER_SHA, 'results_recovered_consumer')
        deps = dict(dependencies, verifier=output / 'helpers/recover_preflight.py')
        plan, common, anchors = dependency_check(n, output / 'inputs', deps)
        runtime = runtime_record()
        put(output, 'runtime.json', encode(runtime))
        capture = dict(schema='openmhd.recovered-native-results-input-capture.v1', files=mapping,
            original_manifest_sha256=originals['files.sha256.json']['sha256'],
            plan_sha256=sha(read(output / 'inputs', 'plan.json')), submission_sha256=sha(raw),
            dependencies=anchors, history=history_pins, component_accepted=False, physical_accepted=False,
            helper_sha256={name: sha(read(output / 'helpers', name))
                for name in ('recovered_native.py', 'recover_preflight.py', 'recovered_native_results.py')})
        put(output, 'input_capture.json', encode(capture))
        summary.update(status='collecting', cases=[empty_capture(row) for row in plan['cases']],
                       counts=dict(passed=0, failed=0, pending=0, incomplete=len(plan['cases'])))
        persist(output, 'summary.json', summary)
        for index, row in enumerate(plan['cases']):
            try:
                record = acquire_case(n, common, output / row['directory'], output / 'inputs' / row['directory'],
                                      output / 'inputs/context', row, runtime)
                summary['cases'][index] = record
            finally:
                capsule = output / row['directory'] / 'capture.json'
                if capsule.exists():
                    summary['cases'][index] = parse(read(capsule.parent, capsule.name))
                summary['counts'] = {s: sum(r['status'] == s for r in summary['cases']) for s in STATUS}
                persist(output, 'summary.json', summary)
        rows, counts, passed = derive(n, common, output, plan, runtime)
        # Repeating check_plan uses ONLY the same captured context/module path.
        final_plan, _, final_anchors = dependency_check(n, output / 'inputs', deps)
        require(same(final_plan, plan) and same(final_anchors, anchors), 'final_complete_dependency_fence')
        fence_inputs(cases, originals, versions)
        require(read(submission.parent, submission.name) == raw and generation(submission.stat()) == submit_generation,
                'final_untouched_original_submission')
        require(read(own.parent, own.name) == own_raw and read(consumer.parent, consumer.name)
                == read(output / 'helpers', 'recovered_native.py')
                and read(dependencies['verifier'].parent, dependencies['verifier'].name)
                == read(output / 'helpers', 'recover_preflight.py'), 'final_actual_host_source_fence')
        for source, item in zip(history, history_pins):
            require(pin(read(source.parent, source.name)) == {k: item[k] for k in ('bytes', 'sha256')}, 'final_original_history_fence')
        require(same(inventory(output / 'inputs'), originals), 'final_copied_inputs_fence')
        if arguments is not None:
            argument_path, argument_raw = arguments
            require(read(argument_path.parent, argument_path.name) == argument_raw, 'final_dependency_arguments_fence')
        packet_layout(output, plan, capture, sealed=False)
        summary.update(status='complete', cases=rows, counts=counts, whole_catalog_passed=passed)
    except BaseException as error:
        summary.update(status='failed', whole_catalog_passed=False, error_type=type(error).__name__,
                       external_terminal_evidence_required=True)
        raise
    finally:
        # A storage failure may prevent these writes: no manifest means no
        # completed packet. Uncatchable process/pod loss needs external evidence.
        persist(output, 'summary.json', summary)
        seal(output)
    return summary


def verify_results(root, dependencies):
    require(__debug__ and sys.flags.optimize == 0, 'optimized_results_rejected')
    require(sys.dont_write_bytecode, 'use_B_to_preserve_original_source_trees')
    root = plain(root)
    original_closure = closed_packet(root)
    capture_raw = read(root, 'input_capture.json')
    capture = parse(capture_raw)
    keys(capture, ('schema', 'files', 'original_manifest_sha256', 'plan_sha256', 'submission_sha256',
                   'dependencies', 'history', 'helper_sha256', 'component_accepted', 'physical_accepted'))
    require(capture['schema'] == 'openmhd.recovered-native-results-input-capture.v1'
            and capture['component_accepted'] is False and capture['physical_accepted'] is False,
            'input_capture_schema')
    originals = inventory(root / 'inputs')
    require(same(capture['files'], {name: dict(retained='inputs/' + name, **item) for name, item in originals.items()}),
            'complete_original_path_body_map')
    manifest_raw, _ = sealed_tree(root / 'inputs')
    require(sha(manifest_raw) == capture['original_manifest_sha256']
            and sha(read(root / 'inputs', 'plan.json')) == capture['plan_sha256'], 'original_plan_seal_links')
    raw = read(root, 'submission_original.json')
    require(sha(raw) == capture['submission_sha256'], 'untouched_submission_body_link')
    keys(capture['helper_sha256'], ('recovered_native.py', 'recover_preflight.py', 'recovered_native_results.py'))
    require(capture['helper_sha256']['recovered_native.py'] == CONSUMER_SHA
            and capture['helper_sha256']['recover_preflight.py'] == RECOVERY_SHA, 'exact_helper_generation')
    for name, digest in capture['helper_sha256'].items():
        require(sha(read(root / 'helpers', name)) == digest, 'retained_helper_body')
    own = Path(__file__).absolute()
    require(read(own.parent, own.name) == read(root / 'helpers', 'recovered_native_results.py'), 'same_frozen_results_validator')
    # Pre-scan original JSON before any less-strict legacy consumer parses it.
    for name in originals:
        if name.endswith('.json'):
            parse(read(root / 'inputs', name))
    n = load_pinned(root / 'helpers/recovered_native.py', CONSUMER_SHA, 'results_recovered_consumer')
    deps = dict(dependencies, verifier=root / 'helpers/recover_preflight.py')
    require(sha(read(dependencies['verifier'].parent, dependencies['verifier'].name)) == RECOVERY_SHA,
            'explicit_external_verifier_pin')
    plan, common, anchors = dependency_check(n, root / 'inputs', deps)
    require(same(anchors, capture['dependencies']), 'explicit_relocated_dependency_graph')
    submission_map(raw, plan)
    runtime = parse(read(root, 'runtime.json'))
    keys(runtime, ('schema', 'executable', 'python', 'implementation', 'optimized', 'adapter_timeout_seconds',
                   'scope', 'component_accepted', 'physical_accepted'))
    require(runtime['schema'] == 'openmhd.recovered-native-results-host-runtime.v1'
            and type(runtime['optimized']) is int and runtime['optimized'] == 0
            and type(runtime['adapter_timeout_seconds']) is int and runtime['adapter_timeout_seconds'] == 300
            and type(runtime['executable']) is str and Path(runtime['executable']).is_absolute()
            and type(runtime['python']) is str and runtime['implementation'] == 'cpython'
            and runtime['scope'] == 'metadata acquisition/offline verification; no binary execution'
            and runtime['component_accepted'] is False and runtime['physical_accepted'] is False,
            'actual_recorded_runtime')
    rows, counts, passed = derive(n, common, root, plan, runtime)
    summary = parse(read(root, 'summary.json'))
    keys(summary, ('schema', 'status', 'whole_catalog_passed', 'cases', 'counts', 'component_accepted',
        'physical_accepted', 'error_type', 'external_terminal_evidence_required'))
    expected = dict(schema=SUMMARY_SCHEMA, status='complete', whole_catalog_passed=passed, cases=rows,
        counts=counts, component_accepted=False, physical_accepted=False, error_type=None,
        external_terminal_evidence_required=False)
    require(passed and same(summary, expected), 'derived_exact_whole_catalog_pass_not_flags')
    packet_layout(root, plan, capture, sealed=True)
    final_plan, _, final_anchors = dependency_check(n, root / 'inputs', deps)
    require(same(final_plan, plan) and same(final_anchors, anchors), 'final_explicit_dependency_fence')
    require(closed_packet(root) == original_closure and read(root, 'input_capture.json') == capture_raw,
            'final_unchanged_packet_capture')
    return summary


def main(argv=None):
    require(__debug__ and sys.flags.optimize == 0, 'optimized_results_rejected')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    collect_parser = sub.add_parser('collect')
    for name in ('cases', 'submission', 'dependencies', 'consumer', 'output'):
        collect_parser.add_argument('--' + name, type=Path, required=True)
    collect_parser.add_argument('--history', type=Path, action='append', default=[])
    verify = sub.add_parser('verify-results')
    for name in ('packet', 'dependencies'):
        verify.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args(argv)
    dep_raw = read(args.dependencies.absolute().parent, args.dependencies.name)
    deps = dependency_arguments(parse(dep_raw))
    if args.action == 'collect':
        result = collect(plain(args.cases), plain(args.submission), deps, plain(args.consumer), plain(args.output),
                         [plain(p) for p in args.history], arguments=(plain(args.dependencies), dep_raw))
    else:
        result = verify_results(plain(args.packet), deps)
    require(read(args.dependencies.absolute().parent, args.dependencies.name) == dep_raw, 'unchanged_explicit_dependency_arguments')
    print(json.dumps(dict(schema=SUMMARY_SCHEMA, whole_catalog_passed=result['whole_catalog_passed'],
                          counts=result['counts'], component_accepted=False, physical_accepted=False)))
    return 0 if result['whole_catalog_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
