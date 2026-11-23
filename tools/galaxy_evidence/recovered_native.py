#!/usr/bin/env python3
"""Unexecuted additive recovered-parent native input route; no submission API.

Original compiler/source evidence and later Python orchestration are distinct.
The old native validate_inputs/run functions are never called or modified.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys

JOB_SOURCE = 'tools/galaxy_evidence/recovered_native.py'
TEST_SOURCE = 'scripts/test_galaxy_recovered_native.py'
RECOVERY_SOURCE = 'scripts/recover_preflight.py'
RECOVERY_TEST = 'scripts/tests/test_transfer_recovery.py'
RECOVERY_SHA = 'adb40fe70062c57371cfd8eceb306dc1ce668c6f573e806f866677e6bc181e07'
RECOVERY_TEST_SHA = '3a27be30b0426ffa21c401aa667b9fd0456bee2e72441c73a467cc7380724774'
ORIGINAL318_REVISION = '2900bbe3efc8500c16a79a16e918a3293a12ce30'
ORIGINAL318_SNAPSHOT = '61c465882f950062d4aa77fcf523b126867b63ae3956a54b7f3c07c0f2051009'
ORIGINAL318_JOB = 'c8295d688297dd5b1192cfe71fddbb49e045961a3292d90e31b6010539942afe'
ORIGINAL318_CERTIFICATE = '8a66156f0c8ea4360fb2ce31ac6e823427b328cfb81afb0f628b93ac17a71839'
SNAPSHOT = '7c4b82b58572cb3eb298e05f98ecf9cb64fc93abbbe089d2faf19c3ee0c19745'
REVISION = '6f032583a699b61706c95c6d2d95cdfea5ea6e87'
WORKFLOW = 'openmhd-galaxy-build-7c4b82b58572-a05.1'
UUID = '7f7d85c9-41a3-4d13-a300-1d9b39159145'
CATALOG_MANIFEST = '11d76a16b011618decd5c618254a6ca3da2dd0af3f4c78dafa8d93cfd199d603'
ORIGINAL = ('reana/galaxy_test_case.py', 'tools/m1_evidence/reana_metadata_job.py',
            'tools/galaxy_evidence/common.py', 'tools/galaxy_evidence/pipeline.py',
            'tools/galaxy_evidence/readonly_adapter.py', 'tools/m1_evidence/reana_metadata_readonly_adapter.py')
PARENT = ('execution.json', 'runtime.json', 'artifacts.sha256.json',
          'galaxy-preflight/preflight.json', 'galaxy-preflight/commands.json',
          'galaxy-preflight/export.json', 'galaxy-preflight/sha256.json')
PROOF_TOOLS = ('reana_metadata_job.py', 'prepare_metadata_reana.py',
               'reana_metadata_readonly_adapter.py', 'collect_metadata_reana_results.py')
PROOF_INPUTS = ('proof/job.py', 'proof/snapshot.json', 'proof/certificate.json',
                'proof/control-summary.json', 'proof/control-manifest.json',
                'proof/root-release.json', 'proof/root-output-review.md',
                *('proof/original318/' + name for name in ('job.py', 'snapshot.json', 'certificate.json',
                  'control-summary.json', 'control-manifest.json', 'root-output-review.md')))
PYTHON_PROVIDER_SOURCE = 'tools/galaxy_python_evidence/python_case_recovery.py'
PYTHON_PROVIDER_TEST = 'scripts/test_python_case_recovery.py'
RECOVERED_PROOF_INPUTS = ('proof/python_case_recovery.py', 'proof/python-evidence-release.json',
                          'proof/original318/python-evidence-release.json')
THREADS = ('RUST_TEST_THREADS', 'RAYON_NUM_THREADS', 'OMP_NUM_THREADS',
           'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')
OUTPUT_NAMES = ('result.json', 'runtime.json', 'command.json', 'stdout.txt',
                'stderr.txt', 'child_result.json', 'child_raw.bin', 'artifacts.sha256.json')


def require(condition, code):
    if not condition:
        raise ValueError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()


def parse(raw):
    def unique(items):
        result = {}
        for name, value in items:
            require(name not in result, 'duplicate_json_key')
            result[name] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite_json')))


def keys(value, names):
    require(type(value) is dict and set(value) == set(names), 'exact_schema_keys')


def path_at(root, name):
    path = PurePosixPath(name)
    require(type(name) is str and path.parts and path.as_posix() == name
            and not path.is_absolute() and '..' not in path.parts and '\\' not in name, 'unsafe_path')
    current = Path(root).absolute()
    for ancestor in (current, *current.parents):
        require(not ancestor.is_symlink(), 'linked_root')
    for part in path.parts:
        current /= part
        require(not current.is_symlink(), 'linked_path')
    return current


def read(root, name):
    path = path_at(root, name)
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_size <= 512 * 1024 * 1024, 'regular_bounded_input')
    raw = path.read_bytes()
    after = path.stat()
    require(len(raw) == after.st_size and all(getattr(before, k) == getattr(after, k) for k in
        ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')), 'changed_input_generation')
    return raw


def put(root, name, raw):
    path = path_at(root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(), 'linked_inventory')
        if path.is_file() and path != root / 'files.sha256.json':
            raw = read(root, path.relative_to(root).as_posix())
            result[path.relative_to(root).as_posix()] = dict(bytes=len(raw), sha256=sha(raw))
        else:
            require(path.is_dir() or path == root / 'files.sha256.json', 'special_inventory')
    return result


def closed(root):
    raw = read(root, 'files.sha256.json')
    require(parse(raw) == inventory(root), 'closed_inventory')
    return sha(raw)


def load_file(path, expected, alias):
    require(sha(read(path.parent, path.name)) == expected, 'source_before_import')
    spec = importlib.util.spec_from_file_location(alias, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(sha(read(path.parent, path.name)) == expected, 'source_after_import')
    return module


def bundle(directory, names, pins):
    """Ordinary imports of exact retained modules; conflicting caches fail closed.

    No function/constant/source guard is patched. CLI operations use a fresh
    interpreter. An embedding process with another module of these names must
    use a fresh interpreter rather than replacing sys.modules entries.
    """
    for name in names:
        require(sha(read(directory, name + '.py')) == pins[name + '.py'], 'bundle_source_pin')
        if name in sys.modules:
            require(Path(sys.modules[name].__file__).absolute() == directory / (name + '.py'), 'conflicting_import_cache')
    previous = list(sys.path)
    try:
        sys.path.insert(0, str(directory))
        modules = [importlib.import_module(name) for name in names]
    finally:
        sys.path[:] = previous
    for name in names:
        require(sha(read(directory, name + '.py')) == pins[name + '.py'], 'bundle_after_import')
    return modules


def original_modules(root):
    snapshot_raw = read(root, 'snapshot.json')
    snapshot = parse(snapshot_raw)
    require(sha(snapshot_raw) == SNAPSHOT and snapshot['source_revision'] == REVISION, 'original_compiler_snapshot')
    for name in ORIGINAL:
        require(sha(read(root / 'original', name)) == snapshot['source_sha256'][name], 'unchanged_original_helper')
    directory = root / 'original/tools/galaxy_evidence'
    common, pipeline = bundle(directory, ('common', 'pipeline'),
        {Path(name).name: snapshot['source_sha256'][name] for name in ORIGINAL if '/galaxy_evidence/' in name})
    require(Path(common.native.__file__).absolute() == root / 'original/reana/galaxy_test_case.py'
            and Path(common.supervisor.__file__).absolute() == root / 'original/tools/m1_evidence/reana_metadata_job.py',
            'captured_original_module_layout')
    return common, pipeline


def check_recovery_result(result, report):
    keys(result, ('logical_requests', 'archive_parts', 'archive_bytes', 'compiled_binaries',
                  'resolved_leaves', 'test_methods_executed'))
    require(all(type(v) is int for v in result.values()) and result['logical_requests'] == 866
            and result['archive_parts'] == 395 and result['archive_bytes'] == 413154228
            and result['compiled_binaries'] == report['compiled_binaries'] == len(report['binaries']) == 114
            and result['resolved_leaves'] == report['resolved_leaves'] == len(report['tests']) == 676
            and result['test_methods_executed'] == 0, 'complete_original_recovery_result')


def require_new_recovery(record):
    require(record['schema'] == 'openmhd.galaxy-preflight-recovery.v1'
            and record['status'] == 'complete' and record['uuid'] == UUID
            and record['workflow'] == WORKFLOW and record['source_revision'] == REVISION
            and record['component_accepted'] is False and record['physical_accepted'] is False, 'new_recovery_only')


def parent_buffers(recovery, origins, verifier_path, catalog):
    verifier = load_file(verifier_path, RECOVERY_SHA, 'recovered_parent_verifier')
    # This actual full offline verifier call is mandatory, not a true flag or
    # transplanted old acquisition record. It never executes an exported binary.
    result = verifier.verify(recovery, origins)
    record = parse(read(recovery, 'recovery.json'))
    require_new_recovery(record)
    roots, _, entries = verifier.load_origins(origins)
    entries += verifier.scan(recovery, 'self')[1]
    selected = verifier.selected_values(record, entries)
    buffers = {'snapshot.json': read(recovery / 'source', 'snapshot.json')}
    for name in ORIGINAL:
        buffers['original/' + name] = read(recovery / 'helpers', name)
    buffers['supervisor.py'] = buffers['original/tools/m1_evidence/reana_metadata_job.py']
    for name in PARENT:
        selected_path = selected['outputs/' + name]
        buffers['preflight/' + Path(name).name] = read(selected_path.parent, selected_path.name)
    for phase in ('before', 'after'):
        item = verifier.reference(entries, record[phase])
        buffers['preflight/server-' + phase + '.json'] = read(item['body'].parent, item['body'].name)
    buffers['preflight/recovery.json'] = read(recovery, 'recovery.json')
    graph = {verifier.closed(recovery): recovery, **roots}
    for digest, path in sorted(graph.items()):
        buffers['graph/' + digest + '.json'] = read(path, 'files.sha256.json')
    require(closed(catalog) == CATALOG_MANIFEST, 'exact_unadopted_catalog_proposal')
    coverage = read(catalog, 'coverage.proposal.json')
    proposal = parse(coverage)
    report = parse(buffers['preflight/preflight.json'])
    check_recovery_result(result, report)
    require(proposal['schema'] == 'openmhd.galaxy-native-catalog-proposal.v1'
            and proposal['status'] == 'unreleased_proposal' and proposal['component_accepted'] is False
            and proposal['native_case_preparation_authorized'] is False
            and type(proposal['test_methods_executed']) is int and proposal['test_methods_executed'] == 0
            and proposal['original_source_revision'] == REVISION and proposal['original_snapshot_sha256'] == SNAPSHOT
            and proposal['original_catalog_sha256'] == sha(buffers['preflight/preflight.json']),
            'original_unreleased_catalog_not_authorization')
    buffers['coverage.proposal.json'] = coverage
    buffers['catalog-proposal.manifest.json'] = read(catalog, 'files.sha256.json')
    certificate = dict(schema='openmhd.recovered-native-parent.v1', compiled_source_revision=REVISION,
        compiled_snapshot_sha256=SNAPSHOT, preflight_workflow=WORKFLOW, preflight_uuid=UUID,
        recovery_manifest_sha256=verifier.closed(recovery), origin_manifest_sha256=sorted(roots),
        recovery_verifier_sha256=RECOVERY_SHA, verification=result, catalog_manifest_sha256=CATALOG_MANIFEST,
        input_sha256={name: sha(raw) for name, raw in buffers.items()}, component_accepted=False, physical_accepted=False)
    buffers['parent.json'] = encode(certificate)
    # Copy manifests, not giant source/compiled archives into every case. The
    # complete recovery+origin graph is an explicit retained shared dependency.
    for digest, path in graph.items():
        require(verifier.closed(path) == digest, 'parent_graph_final_fence')
    require(closed(catalog) == CATALOG_MANIFEST, 'catalog_final_fence')
    return buffers


def make_context(recovery, origins, verifier, catalog, output):
    require(not output.exists(), 'fresh_context')
    buffers = parent_buffers(recovery, origins, verifier, catalog)
    output.mkdir(parents=True)
    for name, raw in buffers.items():
        put(output, name, raw)
    put(output, 'files.sha256.json', encode(inventory(output)))
    return closed(output)


def check_context_buffers(buffers, context_manifest_raw):
    manifest = parse(context_manifest_raw)
    require(manifest == {n: dict(bytes=len(b), sha256=sha(b)) for n, b in buffers.items()}, 'exact_parent_context_manifest')
    parent = parse(buffers['parent.json'])
    require(parent['schema'] == 'openmhd.recovered-native-parent.v1'
            and parent['compiled_source_revision'] == REVISION and parent['compiled_snapshot_sha256'] == SNAPSHOT
            and parent['preflight_workflow'] == WORKFLOW and parent['preflight_uuid'] == UUID
            and parent['recovery_verifier_sha256'] == RECOVERY_SHA
            and parent['catalog_manifest_sha256'] == CATALOG_MANIFEST
            and parent['component_accepted'] is False and parent['physical_accepted'] is False
            and parent['input_sha256'] == {n: sha(b) for n, b in buffers.items() if n != 'parent.json'}, 'parent_context_links')
    graph = [parent['recovery_manifest_sha256'], *parent['origin_manifest_sha256']]
    require(len(graph) == len(set(graph)) and {'graph/' + s + '.json' for s in graph}
            == {n for n in buffers if n.startswith('graph/')}, 'exact_graph_manifests')
    require(all(sha(buffers['graph/' + s + '.json']) == s for s in graph), 'original_graph_manifest_bytes')
    require(sha(buffers['catalog-proposal.manifest.json']) == CATALOG_MANIFEST, 'unadopted_catalog_manifest_pin')
    proposal_manifest = parse(buffers['catalog-proposal.manifest.json'])
    require(proposal_manifest['coverage.proposal.json'] == dict(bytes=len(buffers['coverage.proposal.json']),
            sha256=sha(buffers['coverage.proposal.json'])), 'unadopted_catalog_bytes')
    recovery = parse(buffers['preflight/recovery.json'])
    require(recovery['schema'] == 'openmhd.galaxy-preflight-recovery.v1' and recovery['status'] == 'complete'
            and recovery['uuid'] == UUID and recovery['workflow'] == WORKFLOW
            and recovery['verification'] == parent['verification']
            and sorted(recovery['origins']) == parent['origin_manifest_sha256'], 'explicit_recovery_parent')
    snapshot = parse(buffers['snapshot.json'])
    report = parse(buffers['preflight/preflight.json'])
    require(sha(buffers['snapshot.json']) == SNAPSHOT and snapshot['source_revision'] == REVISION, 'compiled_snapshot_unchanged')
    check_recovery_result(parent['verification'], report)
    for name in ORIGINAL:
        require(sha(buffers['original/' + name]) == snapshot['source_sha256'][name], 'original_helpers_not_replaced')
    require(buffers['supervisor.py'] == buffers['original/tools/m1_evidence/reana_metadata_job.py'], 'exact_supervisor_alias')
    return parent, snapshot, report


def python_evidence_release(release):
    value = release.get('python_evidence')
    keys(value, ('original318', 'later_selected'))
    for item in value.values():
        keys(item, ('schema', 'provider_sha256', 'release_sha256'))
        require(item['schema'] == 'openmhd.python-complete-case-proof.v1'
                and all(type(item[n]) is str and re.fullmatch('[0-9a-f]{64}', item[n])
                        for n in ('provider_sha256', 'release_sha256')), 'explicit_python_evidence_descriptor')
    require(value['original318']['provider_sha256'] == value['later_selected']['provider_sha256'],
            'one_shared_python_evidence_provider')
    return value


def python_evidence_arguments(value):
    keys(value, ('provider', 'original318_origins', 'later_selected_origins'))
    require(type(value['provider']) is str and Path(value['provider']).is_absolute(), 'absolute_python_provider')
    result = dict(provider=Path(value['provider']))
    for name in ('original318_origins', 'later_selected_origins'):
        require(type(value[name]) is list and value[name]
                and all(type(p) is str and Path(p).is_absolute() for p in value[name])
                and len(set(value[name])) == len(value[name]), 'explicit_python_origin_roots')
        result[name] = [Path(p) for p in value[name]]
    return result


def complete_python_proof(packet, tools, review, release, label, evidence):
    """Full fresh-process offline verification, then compact immutable inputs.

    Called only after the caller authenticates outer root-release bytes. The
    supplied original helpers are NOT imported in this parent process. Logs
    inherit the actual durable outer preparation/results command, as does the
    existing original318 verifier route. No retry or live acquisition here.
    """
    descriptor = python_evidence_release(release)[label]
    require(evidence is not None and tools == packet / 'tools', 'explicit_recovered_python_dependencies')
    provider = evidence['provider']
    raw_provider = read(provider.parent, provider.name)
    require(sha(raw_provider) == descriptor['provider_sha256'], 'python_provider_before_execution')
    prefix = 'proof/original318/' if label == 'original318' else 'proof/'
    names = {'snapshot.json': 'context/shared/snapshot.json', 'job.py': 'context/shared/job.py',
             'certificate.json': 'context/shared/preflight_certificate.json',
             'control-summary.json': 'summary.json', 'control-manifest.json': 'files.sha256.json',
             'python-evidence-release.json': 'release.json'}
    buffers = {prefix + name: read(packet, original) for name, original in names.items()}
    buffers[prefix + 'root-output-review.md'] = read(review.parent, review.name)
    buffers['proof/python_case_recovery.py'] = raw_provider
    require(sha(buffers[prefix + 'python-evidence-release.json']) == descriptor['release_sha256'],
            'root_pinned_python_recovery_release')
    argv = [sys.executable, '-B', str(provider), 'verify', '--packet', str(packet),
            '--release-sha256', descriptor['release_sha256']]
    for origin in evidence[label + '_origins']:
        argv += ['--origin', str(origin)]
    subprocess.run(argv, check=True, timeout=300)
    module = load_file(provider, descriptor['provider_sha256'], 'compact_python_evidence_provider')
    module.compact(buffers[prefix + 'snapshot.json'], buffers[prefix + 'certificate.json'],
        buffers[prefix + 'control-summary.json'], buffers[prefix + 'control-manifest.json'],
        buffers[prefix + 'python-evidence-release.json'], descriptor['release_sha256'])
    require(read(provider.parent, provider.name) == raw_provider
            and all(read(packet, source) == buffers[prefix + name] for name, source in names.items())
            and read(review.parent, review.name) == buffers[prefix + 'root-output-review.md'],
            'final_python_evidence_source_and_input_fence')
    return buffers


def release_proof(buffers, expected_release, context_manifest, consumer_raw):
    raw = buffers['proof/root-release.json']
    require(re.fullmatch('[0-9a-f]{64}', expected_release) and sha(raw) == expected_release, 'explicit_root_release_pin')
    release = parse(raw)
    new_python = release.get('schema') == 'openmhd.recovered-native-root-release.v3'
    keys(release, (*(('python_evidence',) if new_python else ()), 'schema', 'scope', 'parent_manifest_sha256', 'recovery_manifest_sha256',
        'origin_manifest_sha256', 'coverage_sha256', 'consumer_sha256', 'recovery_verifier_sha256',
        'control_snapshot_sha256', 'control_certificate_sha256', 'control_job_sha256',
        'control_results_manifest_sha256', 'control_results_summary_sha256', 'root_output_review_sha256',
        'original318_snapshot_sha256', 'original318_certificate_sha256', 'original318_job_sha256',
        'original318_results_manifest_sha256', 'original318_results_summary_sha256',
        'original318_root_output_review_sha256',
        'component_accepted', 'physical_accepted'))
    parent = parse(buffers['parent.json'])
    require(release['schema'] in ('openmhd.recovered-native-root-release.v2', 'openmhd.recovered-native-root-release.v3')
            and release['scope'] == '186 original portable libtest leaves; one leaf per workflow'
            and release['component_accepted'] is False and release['physical_accepted'] is False
            and release['parent_manifest_sha256'] == sha(context_manifest)
            and release['recovery_manifest_sha256'] == parent['recovery_manifest_sha256']
            and release['origin_manifest_sha256'] == parent['origin_manifest_sha256']
            and release['coverage_sha256'] == sha(buffers['coverage.proposal.json'])
            and release['consumer_sha256'] == sha(consumer_raw)
            and release['recovery_verifier_sha256'] == RECOVERY_SHA, 'root_release_original_and_later_code_links')
    for field, name in (('control_snapshot_sha256', 'snapshot.json'),
                        ('control_certificate_sha256', 'certificate.json'), ('control_job_sha256', 'job.py'),
                        ('control_results_manifest_sha256', 'control-manifest.json'),
                        ('control_results_summary_sha256', 'control-summary.json'),
                        ('root_output_review_sha256', 'root-output-review.md')):
        require(release[field] == sha(buffers['proof/' + name]), 'root_release_proof_hash')
    original_proof_hashes(buffers, release)
    require(release['original318_snapshot_sha256'] == ORIGINAL318_SNAPSHOT
            and release['original318_certificate_sha256'] == ORIGINAL318_CERTIFICATE
            and release['original318_job_sha256'] == ORIGINAL318_JOB, 'exact_original318_generation')
    control = parse(buffers['proof/snapshot.json'])
    original = parse(buffers['proof/original318/snapshot.json'])
    generation_proof(control, consumer_raw, original)
    require(control['job_sha256'] == release['control_job_sha256'], 'later_orchestration_source_import_pins')
    if new_python:
        descriptors = python_evidence_release(release)
        require(control['source_sha256'].get(PYTHON_PROVIDER_SOURCE) == descriptors['later_selected']['provider_sha256']
                and PYTHON_PROVIDER_TEST in control['test_files'], 'later_selected_provider_and_controls_required')
        require(sha(buffers['proof/python_case_recovery.py']) == descriptors['later_selected']['provider_sha256'],
                'retained_shared_python_provider')
        for label, prefix in (('original318', 'proof/original318/'), ('later_selected', 'proof/')):
            require(sha(buffers[prefix + 'python-evidence-release.json']) == descriptors[label]['release_sha256'],
                    'retained_root_pinned_python_release')
    return release, control


def generation_proof(control, consumer_raw, original):
    """Source-membership fragment only; not a certificate/output verifier."""
    require(type(original) is dict and original.get('source_revision') == ORIGINAL318_REVISION
            and original.get('job_sha256') == ORIGINAL318_JOB
            and original.get('source_sha256', {}).get(RECOVERY_SOURCE) == RECOVERY_SHA
            and original.get('source_sha256', {}).get(RECOVERY_TEST) == RECOVERY_TEST_SHA
            and original.get('source_sha256', {}).get('tools/galaxy_python_evidence/reana_metadata_job.py') == ORIGINAL318_JOB
            and RECOVERY_TEST in original.get('test_files', ()), 'original318_source_proof_required')
    require(control.get('source_sha256', {}).get(JOB_SOURCE) == sha(consumer_raw)
            and control.get('source_sha256', {}).get(RECOVERY_SOURCE) == RECOVERY_SHA
            and control.get('source_sha256', {}).get(RECOVERY_TEST) == RECOVERY_TEST_SHA
            and TEST_SOURCE in control.get('test_files', ())
            and control.get('source_sha256', {}).get('tools/galaxy_python_evidence/reana_metadata_job.py')
            == control.get('job_sha256'), 'later_orchestration_source_import_pins')


def original_proof_hashes(buffers, release):
    """Hash-link fragment only; fixed generation and actual verification follow."""
    for field, name in (('snapshot', 'snapshot.json'), ('certificate', 'certificate.json'), ('job', 'job.py'),
                        ('results_manifest', 'control-manifest.json'), ('results_summary', 'control-summary.json'),
                        ('root_output_review', 'root-output-review.md')):
        path = 'proof/original318/' + name
        require(path in buffers and release.get('original318_' + field + '_sha256') == sha(buffers[path]),
                'root_release_original318_proof_hash')


def proof_dependencies(release):
    result = {label: {name: release[('root_output_review' if label == 'later_selected'
        and field == 'root_output_review' else prefix + field) + '_sha256'] for name, field in (
        ('snapshot', 'snapshot'), ('job', 'job'), ('certificate', 'certificate'),
        ('results_manifest', 'results_manifest'), ('results_summary', 'results_summary'),
        ('root_output_review', 'root_output_review'))}
        for label, prefix in (('original318', 'original318_'), ('later_selected', 'control_'))}

    if release['schema'] == 'openmhd.recovered-native-root-release.v3':
        for label, item in python_evidence_release(release).items():
            result[label]['python_evidence'] = item
    return result


def compact_control_proof(buffers, prefix, snapshot, *, release=None, root=None):
    summary = parse(buffers[prefix + 'control-summary.json'])
    if release is not None and release['schema'] == 'openmhd.recovered-native-root-release.v3':
        label = 'original318' if prefix == 'proof/original318/' else 'later_selected'
        item = python_evidence_release(release)[label]
        require(root is not None, 'retained_python_provider_root')
        provider = load_file(root / 'proof/python_case_recovery.py', item['provider_sha256'], 'compact_python_evidence_provider')
        provider.compact(buffers[prefix + 'snapshot.json'], buffers[prefix + 'certificate.json'],
            buffers[prefix + 'control-summary.json'], buffers[prefix + 'control-manifest.json'],
            buffers[prefix + 'python-evidence-release.json'], item['release_sha256'])
        return
    require(summary['snapshot_sha256'] == sha(buffers[prefix + 'snapshot.json'])
            and summary['preflight_certificate_sha256'] == sha(buffers[prefix + 'certificate.json'])
            and summary['catalog']['selectors'] == snapshot['tests'], 'control_output_context_links')
    require_control_success(summary, snapshot)
    manifest = parse(buffers[prefix + 'control-manifest.json'])
    require(manifest['schema'] == 'openmhd.galaxy-python-case-results-files.v1'
            and manifest['component_accepted'] is False and manifest['physical_evolutions_run'] is False,
            'control_manifest_scope')
    for original, retained in (('summary.json', 'control-summary.json'),
                               ('shared/snapshot.json', 'snapshot.json'),
                               ('shared/preflight_certificate.json', 'certificate.json')):
        require(manifest['files'][original] == dict(bytes=len(buffers[prefix + retained]),
                sha256=sha(buffers[prefix + retained])), 'control_manifest_summary_source_certificate_links')


def require_control_success(summary, snapshot):
    require(type(summary['whole_suite_passed']) is bool and summary['whole_suite_passed'] is True
            and summary['counts'] == dict(passed=len(snapshot['tests']), failed=0, pending=0, incomplete=0)
            and all(type(n) is int for n in summary['counts'].values()), 'actual_whole_control_results_required')


def single_leaf(selected, leaf, resources):
    matches = [(value, expected) for value, expected in selected if value == leaf]
    require(len(matches) == 1 and matches[0][1] == resources, 'single_authorized_leaf_resources')
    require(type(resources['threads']) is int and resources['threads'] == 1, 'one_native_thread')


def check_case_inputs(root, buffers, payload_raw, *, architecture=True, original_root=None):
    payload = parse(payload_raw)
    keys(payload, ('schema', 'input_sha256', 'binary_parts'))
    require(payload['schema'] == 'openmhd.recovered-native-inputs.v1', 'explicit_new_input_schema')
    parts = payload['binary_parts']
    require(type(parts) is list and 0 < len(parts) <= 512
            and parts == ['test-binary.part' + str(i).zfill(3) for i in range(len(parts))]
            and set(payload['input_sha256']) == set(buffers)
            and payload['input_sha256'] == {name: sha(raw) for name, raw in buffers.items()}
            and all(0 < len(buffers[n]) <= 1024 * 1024 for n in parts), 'exact_frozen_payload')
    case = parse(buffers['case.json'])
    keys(case, ('schema', 'leaf', 'resources', 'preflight_workflow', 'preflight_uuid', 'input_pins',
                'root_release_sha256', 'later_python_snapshot_sha256', 'workflow', 'proof_dependencies'))
    require(case['schema'] == 'openmhd.recovered-native-case.v1' and case['preflight_workflow'] == WORKFLOW
            and type(case['workflow']) is str and re.fullmatch('[a-z][a-z0-9-]{0,62}\\.1', case['workflow'])
            and case['preflight_uuid'] == UUID and case['input_pins'] ==
            {n: sha(b) for n, b in buffers.items() if n not in parts and n != 'case.json'}, 'case_input_generation')
    context_names = set(parse(buffers['parent-context.manifest.json']))
    context = {name: buffers[name] for name in context_names}
    parent, snapshot, report = check_context_buffers(context, buffers['parent-context.manifest.json'])
    require(set(buffers) == context_names | set(PROOF_INPUTS) | (set(RECOVERED_PROOF_INPUTS) if
            parse(buffers['proof/root-release.json'])['schema'] == 'openmhd.recovered-native-root-release.v3' else set()) | {'case.py', 'case.json',
            'parent-context.manifest.json'} | set(parts), 'no_unregistered_case_inputs')
    release, control = release_proof(buffers, case['root_release_sha256'],
                                    buffers['parent-context.manifest.json'], buffers['case.py'])
    require(case['later_python_snapshot_sha256'] == sha(buffers['proof/snapshot.json']), 'later_python_snapshot_identity')
    require(case['proof_dependencies'] == proof_dependencies(release), 'case_two_proof_dependencies')
    # Each immutable job validates its own actual certificate. Compact records
    # remain consistency inputs, not another full verifier or authorization.
    for prefix, pin, alias in (('proof/', release['control_job_sha256'], 'recovered_control_certificate_validator'),
            ('proof/original318/', ORIGINAL318_JOB, 'original318_certificate_validator')):
        proof_job = load_file(root / (prefix + 'job.py'), pin, alias)
        proof_job.validate_certificate(buffers[prefix + 'certificate.json'], buffers[prefix + 'snapshot.json'])
        compact_control_proof(buffers, prefix, parse(buffers[prefix + 'snapshot.json']), release=release, root=root)
    common, pipeline = original_modules(original_root or root)
    contract = dict(schema='openmhd.galaxy-reviewed-catalog.v1', component_accepted=False,
                    targets=parse(buffers['coverage.proposal.json'])['targets'])
    # This derived contract is authorized only by the explicit root release;
    # the original unreleased proposal bytes remain untouched beside it.
    selected = common.catalog(report, contract, snapshot)
    require([x for x, _ in selected] == parse(buffers['coverage.proposal.json'])['actual_catalog_leaves'], 'exact_actual186_catalog')
    single_leaf(selected, case['leaf'], case['resources'])
    binary = [b for b in report['binaries'] if b['path'] == case['leaf']['binary']]
    require(len(binary) == 1 and binary[0]['selectors'].count(case['leaf']['selector']) == 1, 'unique_binary_selector')
    raw = b''.join(buffers[n] for n in parts)
    require(len(raw) == binary[0]['bytes'] and sha(raw) == binary[0]['sha256'] == case['leaf']['binary_sha256'], 'exact_original_binary')
    runtime = parse(buffers['preflight/runtime.json'])
    require(not architecture or runtime['machine'] == os.uname().machine, 'actual_execution_architecture')
    return case, binary[0], common, pipeline


def verify_original_packet(tools, packet):
    """Actual unchanged original CLI in a fresh import namespace; no network.

    stdout/stderr inherit the durably recorded outer preparation command. This
    bounded read-only verification is not a native execution/cleanup framework.
    Never retry a nonzero/timeout or replace the original packet.
    """
    require(__debug__ and sys.flags.optimize == 0 and tools.is_absolute() and packet.is_absolute(),
            'original318_unoptimized_absolute_verifier')
    subprocess.run([sys.executable, '-B', str(tools / 'prepare_metadata_reana.py'),
                    'verify-results', '--packet', str(packet)], cwd=tools, check=True, timeout=300)


def original_control_proof(tools, packet, review_path, release, *, python_evidence=None):
    require(tools is not None and packet is not None and review_path is not None, 'separate_original318_proof_required')
    if release['schema'] == 'openmhd.recovered-native-root-release.v3':
        buffers = complete_python_proof(packet, tools, review_path, release, 'original318', python_evidence)
        original_proof_hashes(buffers, release)
        require(sha(buffers['proof/original318/snapshot.json']) == ORIGINAL318_SNAPSHOT
                and sha(buffers['proof/original318/job.py']) == ORIGINAL318_JOB
                and sha(buffers['proof/original318/certificate.json']) == ORIGINAL318_CERTIFICATE,
                'exact_original318_generation')
        return buffers
    require(python_evidence is None, 'legacy_proof_has_no_recovery_override')
    names = {'snapshot.json': 'shared/snapshot.json', 'job.py': 'shared/job.py',
             'certificate.json': 'shared/preflight_certificate.json', 'control-summary.json': 'summary.json',
             'control-manifest.json': 'files.sha256.json'}
    buffers = {'proof/original318/' + name: read(packet, original) for name, original in names.items()}
    buffers['proof/original318/root-output-review.md'] = read(review_path.parent, review_path.name)
    original_proof_hashes(buffers, release)
    require(sha(buffers['proof/original318/snapshot.json']) == ORIGINAL318_SNAPSHOT
            and sha(buffers['proof/original318/job.py']) == ORIGINAL318_JOB
            and sha(buffers['proof/original318/certificate.json']) == ORIGINAL318_CERTIFICATE,
            'exact_original318_generation')
    original = parse(buffers['proof/original318/snapshot.json'])
    pins = {name: original['source_sha256']['tools/galaxy_python_evidence/' + name] for name in PROOF_TOOLS}
    require(pins['reana_metadata_job.py'] == ORIGINAL318_JOB
            and all(sha(read(tools, name)) == pin for name, pin in pins.items()), 'original318_verifier_sources')
    # The strict collector enforces its ORIGINAL host/source guards and derives
    # every original selected row/body, not just a summary success flag.
    verify_original_packet(tools, packet)
    compact_control_proof(buffers, 'proof/original318/', original)
    require(all(read(packet, original_name) == buffers['proof/original318/' + name]
                for name, original_name in names.items())
            and read(review_path.parent, review_path.name) == buffers['proof/original318/root-output-review.md']
            and all(sha(read(tools, name)) == pin for name, pin in pins.items()), 'original318_proof_final_fences')
    return buffers


def prepare(context, recovery, origins, verifier, catalog, proof_tools, proof_packet,
            release_path, expected_release, review_path, output, prefix, *,
            original_proof_tools=None, original_proof_packet=None, original_review_path=None, python_evidence=None):
    require(not output.exists() and re.fullmatch('[a-z][a-z0-9-]{0,36}', prefix), 'fresh_plan_prefix')
    release_raw = read(release_path.parent, release_path.name)
    require(sha(release_raw) == expected_release, 'explicit_root_release_before_import')
    fresh = parent_buffers(recovery, origins, verifier, catalog)  # Actual verifier again before preparation.
    require(closed(context) and {n: read(context, n) for n in inventory(context)} == fresh, 'context_revalidated_against_full_graph')
    release_value = parse(release_raw)
    if release_value.get('schema') == 'openmhd.recovered-native-root-release.v3':
        require(python_evidence is not None, 'new_proof_needs_explicit_dependencies')
        later = complete_python_proof(proof_packet, proof_tools, review_path,
                                      release_value, 'later_selected', python_evidence)
        original_proof = original_control_proof(original_proof_tools, original_proof_packet,
            original_review_path, release_value, python_evidence=python_evidence)
        later.update(original_proof)
        later['proof/root-release.json'] = release_raw
        control_snapshot_raw = later['proof/snapshot.json']
        control_snapshot = parse(control_snapshot_raw)
        pins = {name: control_snapshot['source_sha256']['tools/galaxy_python_evidence/' + name] for name in PROOF_TOOLS}
        job = load_file(proof_tools / 'reana_metadata_job.py', release_value['control_job_sha256'],
                        'recovered_control_certificate_validator')
        summary = None  # Full provider verification already derived both catalogs.
    else:
        require(python_evidence is None, 'legacy_proof_has_no_recovery_override')
        control_snapshot_raw = read(proof_packet, 'shared/snapshot.json')
        control_snapshot = parse(control_snapshot_raw)
        pins = {name: control_snapshot['source_sha256']['tools/galaxy_python_evidence/' + name] for name in PROOF_TOOLS}
        # Pin the explicit root release BEFORE importing supplied proof validators.
        require(sha(read(release_path.parent, release_path.name)) == expected_release, 'explicit_root_release_before_import')
        release_value = parse(read(release_path.parent, release_path.name))
        require(release_value['control_snapshot_sha256'] == sha(control_snapshot_raw)
                and release_value['control_job_sha256'] == pins['reana_metadata_job.py'], 'approved_proof_validator_source')
        job, _, collector = bundle(proof_tools,
            ('reana_metadata_job', 'prepare_metadata_reana', 'collect_metadata_reana_results'), pins)
        summary = collector.verify_packet(proof_packet)  # Derive actual full control results, never trust its flag alone.
        require_control_success(summary, control_snapshot)
        original_proof = original_control_proof(original_proof_tools, original_proof_packet,
                                                original_review_path, release_value)
        later = {'proof/job.py': read(proof_tools, 'reana_metadata_job.py'),
            'proof/snapshot.json': control_snapshot_raw,
            'proof/certificate.json': read(proof_packet, 'shared/preflight_certificate.json'),
            'proof/control-summary.json': read(proof_packet, 'summary.json'),
            'proof/control-manifest.json': read(proof_packet, 'files.sha256.json'),
            'proof/root-release.json': read(release_path.parent, release_path.name),
            'proof/root-output-review.md': read(review_path.parent, review_path.name), **original_proof}
    consumer_raw = read(Path(__file__).absolute().parent, Path(__file__).name)
    base = dict(fresh, **later, **{'case.py': consumer_raw,
        'parent-context.manifest.json': read(context, 'files.sha256.json')})
    release, control = release_proof(base, expected_release, base['parent-context.manifest.json'], consumer_raw)
    job.validate_certificate(base['proof/certificate.json'], base['proof/snapshot.json'])
    common, pipeline = original_modules(context)
    proposal = parse(base['coverage.proposal.json'])
    report = parse(base['preflight/preflight.json'])
    contract = dict(schema='openmhd.galaxy-reviewed-catalog.v1', component_accepted=False, targets=proposal['targets'])
    selected = common.catalog(report, contract, parse(base['snapshot.json']))
    require([x for x, _ in selected] == proposal['actual_catalog_leaves'], 'original_actual_catalog_order')
    output.mkdir(parents=True)
    for name, raw in base.items():
        put(output / 'context', name, raw)
    plan = dict(schema='openmhd.recovered-native-case-plan.v1', component_accepted=False, physical_accepted=False,
        compiled_snapshot_sha256=SNAPSHOT, later_python_snapshot_sha256=sha(control_snapshot_raw),
        recovery_manifest_sha256=release['recovery_manifest_sha256'], origin_manifest_sha256=release['origin_manifest_sha256'],
        root_release_sha256=expected_release, context_sha256={n: sha(b) for n, b in base.items()},
        retained_dependencies=dict(recovery=release['recovery_manifest_sha256'], origins=release['origin_manifest_sha256'],
            python_controls=release['control_results_manifest_sha256'], python_proofs=proof_dependencies(release),
            catalog_proposal=CATALOG_MANIFEST), cases=[])
    for index, (leaf, resources) in enumerate(selected):
        directory = 'case_' + str(index).zfill(4)
        destination = output / directory
        inputs = dict(base)
        case = dict(schema='openmhd.recovered-native-case.v1', leaf=leaf, resources=resources,
            workflow=prefix + '-' + str(index).zfill(4) + '.1',
            preflight_workflow=WORKFLOW, preflight_uuid=UUID, input_pins={n: sha(b) for n, b in base.items()},
            root_release_sha256=expected_release, later_python_snapshot_sha256=sha(control_snapshot_raw),
            proof_dependencies=proof_dependencies(release))
        inputs['case.json'] = encode(case)
        binary = read(recovery / 'export', leaf['binary'])
        require(sha(binary) == leaf['binary_sha256'], 'prepared_original_export_binary')
        parts = []
        for offset in range(0, len(binary), 1024 * 1024):
            name = 'test-binary.part' + str(len(parts)).zfill(3)
            parts.append(name)
            inputs[name] = binary[offset:offset + 1024 * 1024]
        payload_raw = encode(dict(schema='openmhd.recovered-native-inputs.v1',
            input_sha256={n: sha(b) for n, b in inputs.items()}, binary_parts=parts))
        for name, raw in inputs.items():
            put(destination, name, raw)
        put(destination, 'payload.json', payload_raw)
        check_case_inputs(destination, inputs, payload_raw, architecture=False, original_root=context)
        spec = specification([*inputs, 'payload.json'], resources, common.native.IMAGE, common.native.OUTPUT_NAMES)
        put(destination, 'reana.yaml', encode(spec))
        plan['cases'].append(dict(directory=directory, workflow=prefix + '-' + str(index).zfill(4) + '.1',
            specification=directory + '/reana.yaml', leaf=leaf, resources=resources,
            payload_sha256=sha(payload_raw), workflow_sha256=sha(encode(spec))))
    # A failed preparation remains a nonclosed partial directory, never a plan.
    require(parent_buffers(recovery, origins, verifier, catalog) == fresh, 'final_recovery_graph_fence')
    if python_evidence is not None:
        require(complete_python_proof(proof_packet, proof_tools, review_path, release_value,
                'later_selected', python_evidence) == {n: b for n, b in later.items()
                    if not n.startswith('proof/original318/') and n != 'proof/root-release.json'},
                'full_later_recovered_output_final_fence')
    else:
        require(collector.verify_packet(proof_packet) == summary, 'control_final_fence')
    require(all(read(context, n) == b for n, b in fresh.items()), 'context_final_fence')
    require(original_control_proof(original_proof_tools, original_proof_packet,
            original_review_path, release_value, python_evidence=python_evidence) == original_proof, 'original318_complete_output_final_fence')
    require(read(release_path.parent, release_path.name) == later['proof/root-release.json']
            and read(review_path.parent, review_path.name) == later['proof/root-output-review.md']
            and all(sha(read(proof_tools, n)) == h for n, h in pins.items())
            and read(Path(__file__).absolute().parent, Path(__file__).name) == consumer_raw, 'later_source_release_final_fences')
    put(output, 'plan.json', encode(plan))
    put(output, 'files.sha256.json', encode(inventory(output)))
    return plan


def specification(names, resources, image, outputs):
    return dict(version='0.9.0', inputs=dict(files=sorted(names)), workflow=dict(type='serial', specification=dict(steps=[
        dict(name='one-recovered-native-leaf', environment=image, commands=['python3 -B case.py run'],
             compute_backend='kubernetes', kubernetes_cpu_request='1', kubernetes_cpu_limit='1',
             kubernetes_memory_limit=resources['memory'])])), outputs=dict(files=['outputs/' + n for n in outputs]))


def output_header(values):
    require(set(values) == set(OUTPUT_NAMES), 'eight_actual_native_outputs')
    result = parse(values['result.json'])
    require(result.get('schema') == 'openmhd.galaxy-native-test-result.v1'
            and result.get('input_route') == 'recovered-native-v1' and result.get('status') == 'passed'
            and result.get('component_accepted') is False, 'actual_recovered_native_result_header')
    return result


def validate_outputs(values, case_root, *, original_root=None):
    result = output_header(values)
    payload_raw = read(case_root, 'payload.json')
    payload = parse(payload_raw)
    buffers = {n: read(case_root, n) for n in payload['input_sha256']}
    case, binary, common, pipeline = check_case_inputs(case_root, buffers, payload_raw,
        architecture=False, original_root=original_root)
    require(result.get('input_route') == 'recovered-native-v1'
            and result.get('parent_context_sha256') == sha(buffers['parent.json'])
            and result.get('root_release_sha256') == case['root_release_sha256'], 'new_route_result_links')
    # Reuse the unchanged strict native result/runtime/held-leader/raw witness
    # validator, not old validate_inputs and not a unittest result validator.
    pipeline.validate_native(values, case_root, parse(buffers['preflight/preflight.json']))
    return case, binary


def check_plan(root, recovery, origins, verifier, catalog):
    """Offline full-plan validation, with explicit retained recovery graph.

    The root-approved control packet was fully verified by prepare; its retained
    exact closure/summary and strict import certificate remain release inputs.
    This function rechecks the recovery and all case/code/source/part/spec links.
    It does not claim a remote leaf ran or review a control packet by a true flag.
    """
    closed(root)
    plan = parse(read(root, 'plan.json'))
    require(plan['schema'] == 'openmhd.recovered-native-case-plan.v1'
            and plan['component_accepted'] is False and plan['physical_accepted'] is False
            and plan['compiled_snapshot_sha256'] == SNAPSHOT, 'new_nonacceptance_plan')
    fresh = parent_buffers(recovery, origins, verifier, catalog)
    context = root / 'context'
    base = {n: read(context, n) for n in plan['context_sha256']}
    require(plan['context_sha256'] == {n: sha(b) for n, b in base.items()}
            and set(inventory(context)) == set(base)
            and all(base[n] == b for n, b in fresh.items()), 'full_original_parent_plan_context')
    release, control = release_proof(base, plan['root_release_sha256'],
        base['parent-context.manifest.json'], base['case.py'])
    require(plan['recovery_manifest_sha256'] == release['recovery_manifest_sha256']
            and plan['origin_manifest_sha256'] == release['origin_manifest_sha256']
            and plan['later_python_snapshot_sha256'] == sha(base['proof/snapshot.json'])
            and plan['retained_dependencies'] == dict(recovery=release['recovery_manifest_sha256'],
                origins=release['origin_manifest_sha256'], python_controls=release['control_results_manifest_sha256'],
                python_proofs=proof_dependencies(release),
                catalog_proposal=CATALOG_MANIFEST), 'plan_generations')
    common, _ = original_modules(context)
    proposal = parse(base['coverage.proposal.json'])
    selected = common.catalog(parse(base['preflight/preflight.json']),
        dict(schema='openmhd.galaxy-reviewed-catalog.v1', component_accepted=False, targets=proposal['targets']),
        parse(base['snapshot.json']))
    require([x for x, _ in selected] == proposal['actual_catalog_leaves']
            and len(plan['cases']) == len(selected), 'whole_actual_catalog_plan')
    seen = set()
    require({p.name for p in root.iterdir()} == {'context', 'plan.json', 'files.sha256.json'} |
            {'case_' + str(i).zfill(4) for i in range(len(selected))}, 'exact_plan_directories')
    for i, (row, (leaf, resources)) in enumerate(zip(plan['cases'], selected)):
        require(row['directory'] == 'case_' + str(i).zfill(4) and row['leaf'] == leaf
                and row['resources'] == resources and row['workflow'] not in seen
                and row['specification'] == row['directory'] + '/reana.yaml', 'ordered_unique_plan_cases')
        seen.add(row['workflow'])
        case_root = root / row['directory']
        payload_raw = read(case_root, 'payload.json')
        payload = parse(payload_raw)
        inputs = {n: read(case_root, n) for n in payload['input_sha256']}
        case, _, _, _ = check_case_inputs(case_root, inputs, payload_raw, architecture=False, original_root=context)
        require(case['workflow'] == row['workflow'] and case['leaf'] == leaf and case['resources'] == resources
                and all(inputs[n] == b for n, b in base.items()), 'actual_case_original_context')
        spec = read(case_root, 'reana.yaml')
        require(sha(payload_raw) == row['payload_sha256'] and sha(spec) == row['workflow_sha256']
                and parse(spec) == specification([*inputs, 'payload.json'], resources, common.native.IMAGE, OUTPUT_NAMES)
                and set(inventory(case_root)) == set(inputs) | {'payload.json', 'reana.yaml'}, 'exact_case_payload_spec_inventory')
    closed(root)
    return plan


def check_capture(packet, case_root, workflow):
    """Offline check of an actual common.attempt observe/8 GET/observe capture.

    Acquisition is left to an explicitly authorized caller; this function has
    no network or mutation action and cannot infer success from a label alone.
    """
    case, _, common, _ = check_case_inputs(case_root,
        {n: read(case_root, n) for n in parse(read(case_root, 'payload.json'))['input_sha256']},
        read(case_root, 'payload.json'), architecture=False)
    common.verify_closed(packet)
    require(workflow == case['workflow'], 'actual_planned_case_workflow')
    record = parse(read(packet, 'capture.json'))
    keys(record, ('schema', 'status', 'workflow', 'uuid', 'before', 'after', 'files', 'component_accepted'))
    require(record['schema'] == 'openmhd.recovered-native-output-capture.v1'
            and record['status'] == 'complete' and record['workflow'] == workflow
            and record['component_accepted'] is False, 'explicit_capture_context')
    before = common.transport_body(packet, record['before'], workflow, record['uuid'], 'observe', None)
    after = common.transport_body(packet, record['after'], workflow, record['uuid'], 'observe', None)
    require(common.observation(before, workflow, record['uuid'], True)
            == common.observation(after, workflow, record['uuid'], True), 'actual_finished_case_UUID_fences')
    require(set(record['files']) == set(common.native.OUTPUT_NAMES), 'actual_eight_artifacts')
    values = {name: common.transport_body(packet, receipt, workflow, record['uuid'], 'download', 'outputs/' + name)
              for name, receipt in record['files'].items()}
    common.transport_closure(packet, [record['before'], *record['files'].values(), record['after']])
    validate_outputs(values, case_root)
    common.verify_closed(packet)
    return dict(schema='openmhd.recovered-native-case-verdict.v1', workflow=workflow, uuid=record['uuid'],
        passing_native_leaves=1, component_accepted=False, physical_accepted=False)


def run(work):
    require(__debug__ and sys.flags.optimize == 0, 'optimized_native_rejected')
    output = work / 'outputs'
    output.mkdir()
    result = dict(schema='openmhd.galaxy-native-test-result.v1', input_route='recovered-native-v1',
        status='preparing', component_accepted=False, started_utc=datetime.now(timezone.utc).isoformat())
    runtime, command, child, raw = {}, {'status': 'not_launched'}, {'status': 'not_launched'}, b''
    code = 1
    for name in ('stdout.txt', 'stderr.txt'):
        put(output, name, b'')
    try:
        payload_raw = read(work, 'payload.json')
        payload = parse(payload_raw)
        buffers = {n: read(work, n) for n in payload['input_sha256']}
        require(buffers['case.py'] == read(Path(__file__).absolute().parent, Path(__file__).name), 'actual_later_runner_bytes')
        case, binary_info, common, _ = check_case_inputs(work, buffers, payload_raw)
        native, supervisor = common.native, common.supervisor
        binary = work / 'test-binary'
        put(work, 'test-binary', b''.join(buffers[n] for n in payload['binary_parts']))
        assembled = read(work, 'test-binary')
        require(len(assembled) == binary_info['bytes'] and sha(assembled) == case['leaf']['binary_sha256'], 'assembled_original_binary')
        binary.chmod(0o755)
        runtime = supervisor.runtime_record(work, Path(__file__).absolute())
        runtime.update(image=native.IMAGE, declared_resources=case['resources'], kind='native-rust-libtest')
        environment = dict(os.environ)
        environment.update({name: '1' for name in THREADS})
        runtime.update(machine=os.uname().machine, thread_environment={n: environment[n] for n in THREADS})
        result.update(status='running', case=case, payload_sha256=sha(payload_raw), snapshot_sha256=SNAPSHOT,
            preflight_sha256=sha(buffers['preflight/preflight.json']),
            binary_sha256=case['leaf']['binary_sha256'], parent_context_sha256=sha(buffers['parent.json']),
            root_release_sha256=case['root_release_sha256'])
        native.persist(output / 'runtime.json', runtime)
        native.persist(output / 'result.json', result)
        links = {name: sha(value) for name, value in (('snapshot', buffers['snapshot.json']),
            ('case', buffers['case.json']), ('payload', payload_raw), ('runtime', encode(runtime)),
            ('runner', buffers['case.py']), ('supervisor', buffers['original/tools/m1_evidence/reana_metadata_job.py']))}
        links['binary'] = case['leaf']['binary_sha256']
        child = {'status': 'execution_unverified'}
        argv = [str(binary), '--exact', case['leaf']['selector'], '--test-threads', '1', '--color', 'never', '--show-output']
        command = native.launch_native(supervisor, argv, work, environment, output, case['resources']['timeout_seconds'], links)
        raw = read(output, 'stdout.txt')
        require(command['outcome'] == 'success' and type(command['returncode']) is int and command['returncode'] == 0
                and command['cleanup']['writers_settled'] is True and command['cleanup']['direct_child_reaped'] is True,
                'actual_supervised_success_and_writer_closure')
        child = native.witness(raw, case['leaf']['selector'], len(binary_info['selectors']))
        require(payload_raw == read(work, 'payload.json') and all(read(work, n) == b for n, b in buffers.items()), 'unchanged_all_inputs')
        result.update(status='passed', test_leaves_executed=1, passing_leaves=1,
                      scope='One actual original Rust libtest leaf; no component/physical acceptance')
        code = 0
    except BaseException as error:
        result.update(status='failed', error_type=type(error).__name__)
        if (output / 'command.json').exists():
            command = parse(read(output, 'command.json'))
        if command.get('status') != 'not_launched' and command.get('cleanup', {}).get('writers_settled') is not True:
            result['external_terminal_evidence_required'] = True
            child = dict(status='unknown_closure', external_terminal_evidence_required=True)
        if (output / 'stdout.txt').exists():
            raw = read(output, 'stdout.txt')
    finally:
        result['finished_utc'] = datetime.now(timezone.utc).isoformat()
        for name, value in (('result.json', result), ('runtime.json', runtime),
                            ('command.json', command), ('child_result.json', child)):
            put(output, name + '.final', encode(value))
            os.replace(output / (name + '.final'), output / name)
        put(output, 'child_raw.bin', raw)
        names = ('result.json', 'runtime.json', 'command.json', 'stdout.txt', 'stderr.txt', 'child_result.json', 'child_raw.bin')
        put(output, 'artifacts.sha256.json', encode({'outputs/' + n: sha(read(output, n)) for n in names}))
    return code


def main(argv=None):
    require(__debug__ and sys.flags.optimize == 0, 'optimized_consumer_rejected')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    context = sub.add_parser('context')
    for name in ('recovery', 'verifier', 'catalog', 'output'):
        context.add_argument('--' + name, type=Path, required=True)
    context.add_argument('--origin', type=Path, action='append', required=True)
    prep = sub.add_parser('prepare')
    for name in ('context', 'recovery', 'verifier', 'catalog', 'proof-tools', 'proof-packet', 'release', 'review', 'output',
                 'original-proof-tools', 'original-proof-packet', 'original-review'):
        prep.add_argument('--' + name, type=Path, required=True)
    prep.add_argument('--origin', type=Path, action='append', required=True)
    prep.add_argument('--release-sha256', required=True)
    prep.add_argument('--prefix', required=True)
    prep.add_argument('--python-evidence', type=Path)
    check = sub.add_parser('check-plan')
    for name in ('directory', 'recovery', 'verifier', 'catalog'):
        check.add_argument('--' + name, type=Path, required=True)
    check.add_argument('--origin', type=Path, action='append', required=True)
    capture = sub.add_parser('check-capture')
    capture.add_argument('--packet', type=Path, required=True)
    capture.add_argument('--case-directory', type=Path, required=True)
    capture.add_argument('--workflow', required=True)
    sub.add_parser('run')
    args = parser.parse_args(argv)
    if args.action == 'context':
        result = make_context(args.recovery.absolute(), [x.absolute() for x in args.origin],
                              args.verifier.absolute(), args.catalog.absolute(), args.output.absolute())
    elif args.action == 'prepare':
        result = prepare(args.context.absolute(), args.recovery.absolute(), [x.absolute() for x in args.origin],
            args.verifier.absolute(), args.catalog.absolute(), args.proof_tools.absolute(), args.proof_packet.absolute(),
            args.release.absolute(), args.release_sha256, args.review.absolute(), args.output.absolute(), args.prefix,
            original_proof_tools=args.original_proof_tools.absolute(), original_proof_packet=args.original_proof_packet.absolute(),
            original_review_path=args.original_review.absolute(), python_evidence=(python_evidence_arguments(
                parse(read(args.python_evidence.absolute().parent, args.python_evidence.name)))
                if args.python_evidence is not None else None))
    elif args.action == 'check-plan':
        result = check_plan(args.directory.absolute(), args.recovery.absolute(), [x.absolute() for x in args.origin],
                            args.verifier.absolute(), args.catalog.absolute())
    elif args.action == 'check-capture':
        result = check_capture(args.packet.absolute(), args.case_directory.absolute(), args.workflow)
    else:
        return run(Path.cwd().absolute())
    print(json.dumps(dict(recovered_native_result=result, component_accepted=False, physical_accepted=False)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
