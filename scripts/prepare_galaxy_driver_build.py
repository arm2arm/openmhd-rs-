#!/usr/bin/env python3
"""Prepare a released standalone-example build; never submit or execute it.

Prospective canonical path: scripts/prepare_galaxy_driver_build.py.
Unadopted source proposal. Real external prerequisite review is the caller's
responsibility; digest references do not authenticate scientific acceptance.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat


ROOT = Path(__file__).resolve().parents[1]
IMAGE = ('gitlab-p4n.aip.de:5005/p4nreana/reana-env@sha256:'
         'aebd7911df9e1e97ad67d15f4c32ab23996000282183fad3bf7a480756522bd7')
JOB = 'reana/galaxy_driver_build.py'
PINS = {
    JOB: 'dcd9519315d20c963d25122ee50bd08e1836c10d24d3197796a1129c4a06c513',
    'reana/galaxy_test_case.py': 'b600008f8724920a4fb75b74aa23d0cb94ca6bba56cddeec8c433d8e645cbca5',
    'tools/m1_evidence/reana_metadata_job.py': '8d8a39844b631eb17d46f897bea71ae2464be1e400c75a54dd6c091a1fd2dbc3',
    'scripts/prepare_reana.py': 'b723f625287c7e793d1881d83017ccffa5f332b75c6968730aa00843c9be36b0',
}
MAX_METADATA = 16 * 1024 * 1024


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()


def parse(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Repeated JSON key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def regular(path, maximum=MAX_METADATA):
    require(path.is_absolute() and path == path.resolve(), 'Canonical absolute input path')
    cursor = Path(path.anchor)
    for component in path.parts[1:]:
        cursor /= component
        require(not cursor.is_symlink(), 'Linked input path')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= maximum,
                'Regular bounded metadata input')
        chunks, total = [], 0
        while True:
            block = os.read(fd, min(1024 * 1024, maximum + 1 - total))
            if not block:
                break
            chunks.append(block)
            total += len(block)
            require(total <= maximum, 'Growing metadata input')
        after = os.fstat(fd)
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        require(total == after.st_size
                and all(getattr(before, k) == getattr(after, k) for k in fields)
                and all(getattr(path.stat(), k) == getattr(after, k) for k in fields),
                'Changed metadata input generation')
        return b''.join(chunks)
    finally:
        os.close(fd)


def safe_name(name):
    require(type(name) is str, 'String input path')
    path = PurePosixPath(name)
    require(path.parts and not path.is_absolute() and path.as_posix() == name
            and '..' not in path.parts, 'Unsafe input path')
    return name


def validate_source_map(mapping):
    require(type(mapping) is dict and 0 < len(mapping) <= 10000, 'Bounded source inventory')
    for name, value in mapping.items():
        safe_name(name)
        require(type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value), 'Source digest')
    require(all(mapping.get(name) == value for name, value in PINS.items()),
            'Chosen reviewed builder/helper source pins')
    for package, example in (('moving-mesh', 'geometry3-case'), ('gravity', 'gravity-force-case')):
        require('crates/' + package + '/Cargo.toml' in mapping
                and 'crates/' + package + '/examples/' + example + '.rs' in mapping,
                'Both standalone example sources and manifests required')


def validate_release(release, snapshot):
    require(type(release) is dict and set(release) == {'schema', 'source_revision',
            'source_sha256', 'preflight_review_sha256', 'coordinator_release_sha256'},
            'Exact external build release schema')
    require(release['schema'] == 'openmhd.galaxy-driver-build-release.v1', 'Build release version')
    require(type(snapshot) is dict and snapshot.get('dirty_status') == '',
            'Committed clean selected source required')
    revision = snapshot.get('source_revision')
    require(type(revision) is str and re.fullmatch(r'[0-9a-f]{40}', revision)
            and release['source_revision'] == revision, 'Exact chosen development revision')
    validate_source_map(snapshot.get('source_sha256'))
    require(release['source_sha256'] == snapshot['source_sha256'], 'Exact released source inventory')
    for key in ('preflight_review_sha256', 'coordinator_release_sha256'):
        require(type(release[key]) is str and re.fullmatch(r'[0-9a-f]{64}', release[key]),
                'External receipt digest reference')
    require(type(snapshot.get('upload_sha256')) is dict
            and 'remote.py' in snapshot['upload_sha256']
            and 'reana/remote.py' in snapshot['source_sha256']
            and snapshot['upload_sha256'].get('remote.py') == snapshot['source_sha256'].get('reana/remote.py')
            and type(snapshot.get('workflow_sha256')) is str
            and re.fullmatch(r'[0-9a-f]{64}', snapshot['workflow_sha256']), 'Original bootstrap/specification pins')
    for name, digest in snapshot['upload_sha256'].items():
        safe_name(name)
        require(type(digest) is str and re.fullmatch(r'[0-9a-f]{64}', digest), 'Upload digest')
    require(not {'snapshot.json', 'reana.yaml', 'build_release.json'} & set(snapshot['upload_sha256']),
            'Reserved top-level input collision')


def specification(snapshot):
    files = ['snapshot.json', *sorted(snapshot['upload_sha256'])]
    require(len(files) == len(set(files)) and 'remote.py' in files and 'build_release.json' in files,
            'Exact complete original upload inputs')
    steps = []
    for name, command in (
            ('prepare-source-and-rust', 'python3 remote.py prepare'),
            ('build-standalone-examples-without-running',
             'python3 source/reana/galaxy_driver_build.py --source source --snapshot snapshot.json '
             '--release build_release.json --output outputs/galaxy-driver-build')):
        steps.append({'name': name, 'environment': IMAGE, 'compute_backend': 'kubernetes',
                      'kubernetes_cpu_request': '4', 'kubernetes_cpu_limit': '4',
                      'kubernetes_memory_limit': '8Gi', 'commands': [command]})
    output = 'outputs/galaxy-driver-build/'
    return {'version': '0.9.0', 'inputs': {'files': files},
            'workflow': {'type': 'serial', 'specification': {'steps': steps}},
            'outputs': {'files': ['outputs/runtime.json', output + 'build.json', output + 'runtime.json',
                                  output + 'export.json', output + 'files.sha256.json',
                                  *[output + label + '/' + name for label in ('compiler', 'geometry', 'gravity')
                                    for name in ('command.json', 'stdout.txt', 'stderr.txt')]]}}


def derive(destination, release_raw):
    """Derive only wrapper-owned metadata after the original freezer returns."""
    snapshot_path = destination / 'snapshot.json'
    snapshot_raw = regular(snapshot_path)
    snapshot = parse(snapshot_raw)
    validate_release(parse(release_raw), snapshot)
    workflow_path = destination / 'reana.yaml'
    old_workflow = regular(workflow_path)
    require(sha(old_workflow) == snapshot['workflow_sha256'], 'Original frozen specification changed')
    # Only our new top-level release is added; source tar/bundle/parts remain
    # exact original freezer inputs and are independently checked by remote.py.
    release_path = destination / 'build_release.json'
    with release_path.open('xb') as stream:
        stream.write(release_raw)
    require(regular(release_path) == release_raw, 'Copied external release changed')
    derived_snapshot = dict(snapshot)
    derived_snapshot['upload_sha256'] = dict(snapshot['upload_sha256'],
                                             **{'build_release.json': sha(release_raw)})
    derived_specification = encode(specification(derived_snapshot))
    derived_snapshot.update(workflow_sha256=sha(derived_specification), workflow_derivation={
        'schema': 'openmhd.galaxy-driver-build-workflow.v1',
        'base_workflow_sha256': sha(old_workflow), 'release_sha256': sha(release_raw),
        'job_source_sha256': PINS[JOB], 'declared_build_jobs': 4, 'declared_memory': '8Gi',
        'test_methods_to_execute': 0, 'numerical_cases_to_execute': 0,
        'external_prerequisite_truth_verified': False, 'component_accepted': False})
    require(regular(snapshot_path) == snapshot_raw and regular(workflow_path) == old_workflow,
            'Original derived-metadata generation changed')
    workflow_path.write_bytes(derived_specification)
    snapshot_path.write_bytes(encode(derived_snapshot))
    require(regular(workflow_path) == derived_specification
            and regular(snapshot_path) == encode(derived_snapshot)
            and regular(release_path) == release_raw, 'Final derived input metadata changed')
    return derived_snapshot


def prepare_driver_build(destination, release_path):
    require(destination.is_absolute() and destination.parent == destination.parent.resolve()
            and destination.name not in ('.', '..'), 'Canonical absolute destination parent')
    require(not destination.exists() and not destination.is_symlink(), 'Fresh build submission destination')
    release_raw = regular(release_path)
    # Metadata shape is checked early; actual source equality is available only
    # after the unchanged canonical freezer has captured the chosen generation.
    parse(release_raw)
    module_path = ROOT / 'scripts/prepare_reana.py'
    helper_raw = regular(module_path)
    require(sha(helper_raw) == PINS['scripts/prepare_reana.py'], 'Reviewed source freezer pin')
    spec = importlib.util.spec_from_file_location('standalone_build_freezer', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(regular(module_path) == helper_raw, 'Source freezer changed during import')
    # Failure here can leave the freezer's real partial destination. Never
    # delete it or call it a staged packet; the external command receipt is
    # authoritative. A wrapper failure status is attempted only after return.
    module.prepare(destination, minimal=True, compact_history=True)
    try:
        result = derive(destination, release_raw)
        require(result['source_sha256'].get('scripts/prepare_reana.py') == sha(helper_raw)
                and result['source_sha256'].get('scripts/prepare_galaxy_driver_build.py')
                == sha(regular(Path(__file__).resolve())), 'Actual invoked preparer/freezer source pins')
        require(regular(module_path) == helper_raw and regular(release_path) == release_raw,
                'Original release/freezer changed after preparation')
        return result
    except BaseException as error:
        (destination / 'driver_build_preparation_failed.json').write_bytes(encode({
            'schema': 'openmhd.galaxy-driver-build-preparation-failure.v1',
            'error_type': type(error).__name__, 'staged_successfully': False,
            'external_command_evidence_required': True}))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--release', type=Path, required=True)
    args = parser.parse_args()
    prepare_driver_build(args.output.absolute(), args.release.absolute())


if __name__ == '__main__':
    main()
