#!/usr/bin/env python3
"""Stage all registered reference cases from reviewed committed bytes.

Metadata only. No reference import/arithmetic, submission, observation, or test.
Release declarations must be inspected by the coordinator before invocation;
this program verifies their identities, not the scientific truth of prose.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess

IMAGE = ('gitlab-p4n.aip.de:5005/p4nreana/reana-env@sha256:'
         'aebd7911df9e1e97ad67d15f4c32ab23996000282183fad3bf7a480756522bd7')
SOURCE_PATHS = {
    'runner.py': 'reana/galaxy_geometry3_reference_case.py',
    'reference.py': 'scripts/galaxy_geometry3_reference.py',
    'design.json': 'docs/galaxy/fixtures/geometry3_analytic_v1.json',
    'launcher.py': 'reana/galaxy_test_case.py',
    'supervisor.py': 'tools/m1_evidence/reana_metadata_job.py',
    'preparer.py': 'tools/galaxy_evidence/prepare_geometry3_reference.py',
}
PINS = {
    'reference.py': '2b9f55d5ed72a08a90c3445fcd62b7702598174e04603e7ecd0d672c387df2df',
    'design.json': '69fd92fc2009df207d076441527161825eb50ae911a2ec2a8e398d687306f288',
    'launcher.py': 'b600008f8724920a4fb75b74aa23d0cb94ca6bba56cddeec8c433d8e645cbca5',
    'supervisor.py': '8d8a39844b631eb17d46f897bea71ae2464be1e400c75a54dd6c091a1fd2dbc3',
}
RECEIPTS = ('m1_acceptance', 'reference_source_review', 'reference_arithmetic_output_review',
            'job_source_review', 'job_method_output_review', 'preparer_method_output_review')
FIXTURES = ('periodic_one_cell_self_images', 'periodic_cartesian_2x2x2',
            'periodic_nonuniform_3x2x2', 'periodic_cartesian_4x4x4',
            'periodic_nonuniform_4x4x4', 'bounded_one_cell_2x3x4', 'bounded_oblique_bisector')
PERMUTATIONS = ('xyz', 'xzy', 'yxz', 'yzx', 'zxy', 'zyx')
RESOURCES = {'threads': 1, 'memory': '2Gi', 'timeout_seconds': 300}
ARTIFACTS = ('outputs/result.json', 'outputs/runtime.json', 'outputs/command.json',
             'outputs/stdout.txt', 'outputs/stderr.txt', 'outputs/artifacts.sha256.json',
             'outputs/reference/input.json', 'outputs/reference/reference.json',
             'outputs/reference/status.json', 'outputs/reference/sha256.json')
LIMIT = 16 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def parse(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, 'Duplicate JSON key')
            value[key] = item
        return value
    def invalid(_):
        raise ValueError('Nonfinite JSON')
    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)


def keys(value, expected, message):
    require(type(value) is dict and set(value) == set(expected), message)


def safe(name):
    require(type(name) is str, 'String relative path')
    path = PurePosixPath(name)
    require(path.parts and path.as_posix() == name and not path.is_absolute()
            and '..' not in path.parts, 'Canonical relative path')
    return path


def read(root, name):
    path = Path(root)
    require(not path.is_symlink(), 'Linked root rejected')
    for part in safe(name).parts:
        path /= part
        require(not path.is_symlink(), 'Linked entry rejected')
    flags = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_size <= LIMIT, 'Bounded regular input')
        raw = stream.read(LIMIT + 1)
        after = os.fstat(stream.fileno())
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    require(len(raw) == before.st_size and len(raw) <= LIMIT
            and all(getattr(before, k) == getattr(after, k) for k in fields), 'Changed input generation')
    return raw


def put(root, name, raw):
    safe(name)
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def catalog():
    return [dict(name=f'{fixture}__s{s}__p{p}__t{t}', fixture=fixture,
                 scale_index=s, permutation=p, translation_index=t)
            for fixture in FIXTURES for s in range(3) for p in PERMUTATIONS for t in range(2)]


def specification():
    return dict(version='0.9.0', inputs={'files': sorted((*(SOURCE_PATHS.keys() - {'preparer.py'}),
                                                       'case.json', 'payload.json'))},
                workflow={'type': 'serial', 'specification': {'steps': [dict(
                    name='one-independent-reference', environment=IMAGE,
                    commands=['python3 -B runner.py'], compute_backend='kubernetes',
                    kubernetes_cpu_request='1', kubernetes_cpu_limit='1',
                    kubernetes_memory_limit='2Gi')]}}, outputs={'files': list(ARTIFACTS)})


def validate_release(raw):
    release = parse(raw)
    keys(release, ('schema', 'source_revision', 'source_sha256', 'receipts', 'scope',
                   'import_certificate', 'coordinator_prerequisites_inspected',
                   'candidate_invoked', 'component_accepted'), 'Release exact keys')
    require(release['schema'] == 'openmhd.geometry3-reference-release.v1', 'Release schema')
    require(type(release['source_revision']) is str
            and re.fullmatch('[0-9a-f]{40}', release['source_revision']), 'Exact source revision')
    keys(release['source_sha256'], SOURCE_PATHS.values(), 'Exact committed source paths')
    require(all(type(v) is str and re.fullmatch('[0-9a-f]{64}', v)
                for v in release['source_sha256'].values()), 'Exact source digests')
    keys(release['receipts'], RECEIPTS, 'Six prerequisite receipts')
    descriptors = [*release['receipts'].values(), release['import_certificate']]
    for row in descriptors:
        keys(row, ('path', 'sha256', 'bytes'), 'Receipt descriptor')
        safe(row['path'])
        require(type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}', row['sha256'])
                and type(row['bytes']) is int and 0 < row['bytes'] <= LIMIT, 'Bounded receipt identity')
    require(len({r['path'] for r in descriptors}) == len(descriptors), 'Distinct receipt paths')
    require(release['scope'] == 'registered-252-independent-reference-only'
            and release['coordinator_prerequisites_inspected'] is True
            and release['candidate_invoked'] is False and release['component_accepted'] is False,
            'Explicit coordinator release with nonaccepting reference scope')
    return release


def git_blob(root, revision, relative):
    safe(relative)
    completed = subprocess.run(['git', 'cat-file', 'blob', revision + ':' + relative],
                               cwd=root, capture_output=True, timeout=30, check=True)
    require(len(completed.stdout) <= LIMIT, 'Bounded committed source')
    return completed.stdout


def capture(root, release):
    sources = {}
    for alias, relative in SOURCE_PATHS.items():
        raw = read(root, relative)
        require(sha(raw) == release['source_sha256'][relative]
                and raw == git_blob(root, release['source_revision'], relative),
                'Working/committed/released source bytes agree: ' + relative)
        if alias in PINS:
            require(sha(raw) == PINS[alias], 'Unchanged reviewed reference dependency: ' + alias)
        sources[alias] = raw
    require(sources['preparer.py'] == Path(__file__).read_bytes(), 'Actual loaded preparer source')
    receipts = {}
    for name, row in [*release['receipts'].items(), ('import_certificate', release['import_certificate'])]:
        raw = read(root, row['path'])
        require(sha(raw) == row['sha256'] and len(raw) == row['bytes'], 'Original prerequisite buffer: ' + name)
        receipts[name] = raw
    return sources, receipts


def stage(output, release_raw, sources, receipts, prefix):
    """Internal metadata publisher; public prepare performs all release fences."""
    release = validate_release(release_raw)
    require(type(prefix) is str and re.fullmatch('[a-z][a-z0-9-]{0,45}', prefix), 'Bounded fresh workflow prefix')
    require(set(sources) == set(SOURCE_PATHS) and set(receipts) == {*RECEIPTS, 'import_certificate'},
            'Exact captured context inventory')
    require(output.is_dir() and not output.is_symlink() and not any(output.iterdir()),
            'Owned empty staging directory')
    put(output, 'context/release.json', release_raw)
    for name, raw in sources.items():
        put(output, 'context/source/' + name, raw)
    for name, raw in receipts.items():
        put(output, 'context/receipts/' + name + '.bin', raw)
    context = {str(p.relative_to(output)): {'sha256': sha(p.read_bytes()), 'bytes': p.stat().st_size}
               for p in sorted((output / 'context').rglob('*')) if p.is_file()}
    plan = dict(schema='openmhd.geometry3-reference-plan.v1', source_revision=release['source_revision'],
                release_sha256=sha(release_raw), context=context, cases=[], candidate_invoked=False,
                component_accepted=False, external_prerequisite_truth_verified=False)
    for index, selection in enumerate(catalog()):
        directory = f'case_{index:04d}'
        case = dict(schema='openmhd.geometry3-reference-case.v1', selection=selection,
                    resources=RESOURCES, source_revision=release['source_revision'],
                    prerequisite_receipts={k: release['receipts'][k]['sha256'] for k in RECEIPTS[:5]},
                    candidate_invoked=False, component_accepted=False)
        inputs = {k: v for k, v in sources.items() if k != 'preparer.py'}
        inputs['case.json'] = encode(case)
        payload = encode(dict(schema='openmhd.geometry3-reference-job-inputs.v1',
                              input_sha256={k: sha(v) for k, v in inputs.items()}))
        workflow = encode(specification())
        for name, raw in {**inputs, 'payload.json': payload, 'reana.yaml': workflow}.items():
            put(output, directory + '/' + name, raw)
        plan['cases'].append(dict(directory=directory, workflow=f'{prefix}-{index:04d}.1',
                                 specification=directory + '/reana.yaml', selection=selection,
                                 resources=RESOURCES, payload_sha256=sha(payload), workflow_sha256=sha(workflow)))
    put(output, 'plan.json', encode(plan))
    return plan


def validate_plan(root):
    plan_raw = read(root, 'plan.json')
    plan = parse(plan_raw)
    keys(plan, ('schema', 'source_revision', 'release_sha256', 'context', 'cases', 'candidate_invoked',
                'component_accepted', 'external_prerequisite_truth_verified'), 'Plan exact keys')
    require(plan['schema'] == 'openmhd.geometry3-reference-plan.v1'
            and plan['candidate_invoked'] is False and plan['component_accepted'] is False
            and plan['external_prerequisite_truth_verified'] is False, 'Reference-only staged plan')
    release_raw = read(root, 'context/release.json')
    release = validate_release(release_raw)
    require(plan['release_sha256'] == sha(release_raw)
            and plan['source_revision'] == release['source_revision'], 'Original release identity')
    expected_context = {'context/release.json', *(f'context/source/{n}' for n in SOURCE_PATHS),
                        *(f'context/receipts/{n}.bin' for n in (*RECEIPTS, 'import_certificate'))}
    require(set(plan['context']) == expected_context, 'Exact captured context')
    allowed = {'plan.json', *expected_context}
    for name, row in plan['context'].items():
        raw = read(root, name)
        keys(row, ('sha256', 'bytes'), 'Context receipt keys')
        require(type(row['bytes']) is int and row == {'sha256': sha(raw), 'bytes': len(raw)}, 'Captured context identity')
    sources = {name: read(root, 'context/source/' + name) for name in SOURCE_PATHS}
    for alias, path in SOURCE_PATHS.items():
        require(sha(sources[alias]) == release['source_sha256'][path]
                and (alias not in PINS or sha(sources[alias]) == PINS[alias]), 'Released source identity')
    for name, row in [*release['receipts'].items(), ('import_certificate', release['import_certificate'])]:
        raw = read(root, 'context/receipts/' + name + '.bin')
        require(sha(raw) == row['sha256'] and len(raw) == row['bytes'], 'Released prerequisite identity')
    require(type(plan['cases']) is list and len(plan['cases']) == 252, 'Complete 252-case inventory')
    prefix = None
    for index, (row, selection) in enumerate(zip(plan['cases'], catalog())):
        directory = f'case_{index:04d}'
        keys(row, ('directory', 'workflow', 'specification', 'selection', 'resources',
                   'payload_sha256', 'workflow_sha256'), 'Case row exact keys')
        suffix = f'-{index:04d}.1'
        require(type(row['workflow']) is str and row['workflow'].endswith(suffix), 'Ordered unique workflow suffix')
        current_prefix = row['workflow'][:-len(suffix)]
        require(re.fullmatch('[a-z][a-z0-9-]{0,45}', current_prefix)
                and (prefix is None or prefix == current_prefix), 'One workflow prefix')
        prefix = current_prefix
        require(row['directory'] == directory and row['specification'] == directory + '/reana.yaml'
                and row['selection'] == selection and row['resources'] == RESOURCES
                and type(row['selection']['scale_index']) is int
                and type(row['selection']['translation_index']) is int
                and type(row['resources']['threads']) is int
                and type(row['resources']['timeout_seconds']) is int, 'Exact ordered case metadata')
        inputs = {n: read(root, directory + '/' + n) for n in (*PINS, 'runner.py', 'case.json')}
        require(all(inputs[n] == sources[n] for n in sources if n != 'preparer.py'), 'Shared original case source')
        case = dict(schema='openmhd.geometry3-reference-case.v1', selection=selection, resources=RESOURCES,
                    source_revision=release['source_revision'],
                    prerequisite_receipts={k: release['receipts'][k]['sha256'] for k in RECEIPTS[:5]},
                    candidate_invoked=False, component_accepted=False)
        require(inputs['case.json'] == encode(case), 'Exact canonical case buffer')
        payload = read(root, directory + '/payload.json')
        spec = read(root, directory + '/reana.yaml')
        require(payload == encode(dict(schema='openmhd.geometry3-reference-job-inputs.v1',
                    input_sha256={n: sha(inputs[n]) for n in inputs}))
                and sha(payload) == row['payload_sha256'], 'Original case payload')
        require(spec == encode(specification()) and sha(spec) == row['workflow_sha256'], 'Exact workflow/resources')
        allowed.update(directory + '/' + n for n in (*inputs, 'payload.json', 'reana.yaml'))
    actual = set()
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'Linked plan entry')
        require(path.is_file() or path.is_dir(), 'Special plan entry')
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    # The generic one-shot submitter later publishes this separate journal.
    require(actual in (allowed, allowed | {'submission.json'}), 'Closed staged file inventory')
    return plan


def prepare(repository, release_path, output, prefix):
    require(__debug__, 'Optimized preparation rejected')
    release_raw = read(release_path.parent, release_path.name)
    release = validate_release(release_raw)
    sources, receipts = capture(repository, release)
    output.mkdir()  # Exclusive creation precedes ownership of all failure writes.
    try:
        plan = stage(output, release_raw, sources, receipts, prefix)
        validate_plan(output)
        require(read(release_path.parent, release_path.name) == release_raw, 'Original release unchanged')
        require(capture(repository, release) == (sources, receipts), 'Original source/receipt generation unchanged')
    except BaseException as error:
        if output.is_dir() and not output.is_symlink():
            pending = output / 'plan.json'
            if pending.is_file():
                pending.rename(output / 'plan.failed.json')
            put(output, 'preparation_failure.json', encode(dict(status='failed', error_type=type(error).__name__,
                candidate_invoked=False, component_accepted=False, ready_for_submission=False)))
        raise
    return plan


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('prepare')
    p.add_argument('--repository', type=Path, required=True)
    p.add_argument('--release', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--prefix', required=True)
    p = commands.add_parser('verify-plan')
    p.add_argument('directory', type=Path)
    args = parser.parse_args(argv)
    if args.command == 'prepare':
        prepare(args.repository, args.release, args.output, args.prefix)
    else:
        validate_plan(args.directory)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
