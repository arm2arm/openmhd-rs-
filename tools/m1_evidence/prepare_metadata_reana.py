"""Prepare source-pinned per-case REANA metadata checks, without executing tests.

snapshot creates only the source/import preflight plan. cases requires its
downloaded successful output before preparing the independent unittest plan.
Use the unchanged scripts/reana_cases.py submit action for either plan; its
generic submission path pins payloads and never implicitly resubmits a plan.
"""
import argparse
import ast
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile

if not __debug__:
    raise RuntimeError('Metadata workflow preparation rejects optimized Python')

IMAGE = ('gitlab-p4n.aip.de:5005/p4nreana/reana-env@sha256:'
         'aebd7911df9e1e97ad67d15f4c32ab23996000282183fad3bf7a480756522bd7')
ROOTS = ('tools/m1_evidence/', 'tests/reference/m1_acceptance/',
         'tests/reference/m1_iterative_step_campaigns/')
TEST_FILES = ('tools/m1_evidence/tests/test_collection_metadata.py',
              'tools/m1_evidence/tests/test_archive_metadata.py')
RESOURCES = dict(threads=1, memory='2Gi', timeout_seconds=180)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, indent=1, allow_nan=False) + '\n').encode()


def dump(path, value):
    path.write_bytes(encode(value))


def safe_name(value):
    require(re.fullmatch(r'[a-z][a-z0-9-]{0,36}', value) is not None,
            'Use a short lowercase workflow prefix')
    return value


def tests_from_source(sources):
    selectors = []
    for name in TEST_FILES:
        require(name in sources, 'Missing committed metadata tests: ' + name)
        module = name.removesuffix('.py').replace('/', '.')
        tree = ast.parse(sources[name], filename=name)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                for method in node.body:
                    if isinstance(method, ast.FunctionDef) and method.name.startswith('test_'):
                        selectors.append(module + '.' + node.name + '.' + method.name)
        require(any(s.startswith(module + '.') for s in selectors), 'No test methods: ' + name)
    require(len(selectors) == len(set(selectors)), 'Duplicate test selectors')
    return sorted(selectors)


def create_case(directory, workflow, source, snapshot_bytes, job_bytes, case, preflight=None):
    directory.mkdir(parents=True)
    case = dict(case, workflow=workflow + '.1')
    inputs = {'source.tar.gz': source, 'snapshot.json': snapshot_bytes,
              'job.py': job_bytes, 'case.json': encode(case)}
    if preflight is not None:
        inputs['preflight_result.json'] = preflight
    for name, data in inputs.items():
        (directory / name).write_bytes(data)
    payload = dict(schema='openmhd.metadata-case-payload.v1',
                   input_sha256={n: digest(b) for n, b in inputs.items()})
    dump(directory / 'payload.json', payload)
    outputs = ['outputs/result.json', 'outputs/runtime.json', 'outputs/stdout.txt',
               'outputs/stderr.txt', 'outputs/child_result.json', 'outputs/artifacts.sha256.json']
    workflow_document = dict(version='0.9.0',
        inputs=dict(files=sorted(inputs) + ['payload.json']),
        workflow=dict(type='serial', specification=dict(steps=[dict(name='one-metadata-case',
            environment=IMAGE, compute_backend='kubernetes', kubernetes_memory_limit=RESOURCES['memory'],
            kubernetes_cpu_request='1', kubernetes_cpu_limit='1', commands=['python3 job.py'])])),
        outputs=dict(files=outputs))
    dump(directory / 'reana.yaml', workflow_document)
    return dict(directory=directory.name, specification=case, workflow=workflow + '.1',
        payload_sha256=digest((directory / 'payload.json').read_bytes()),
        workflow_sha256=digest((directory / 'reana.yaml').read_bytes()))


def snapshot(output, prefix):
    repo = Path.cwd()
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', revision,
        '--', *[r.rstrip('/') for r in ROOTS]], text=True).splitlines()
    require(names and all(any(n.startswith(r) for r in ROOTS) for n in names), 'Source path set')
    sources = {}
    for name in names:
        require('__pycache__' not in PurePosixPath(name).parts, 'Tracked cache file')
        data = subprocess.check_output(['git', 'show', revision + ':' + name])
        require((repo / name).is_file() and not (repo / name).is_symlink(), 'Source must be regular: ' + name)
        require((repo / name).read_bytes() == data, 'Uncommitted source change: ' + name)
        sources[name] = data
    selectors = tests_from_source(sources)
    job_name = 'tools/m1_evidence/reana_metadata_job.py'
    require(job_name in sources, 'Commit the metadata runner first')
    archive_bytes = io.BytesIO()
    with tarfile.open(fileobj=archive_bytes, mode='w', format=tarfile.PAX_FORMAT) as archive:
        for name, data in sorted(sources.items()):
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(data), 0o644, 0
            archive.addfile(info, io.BytesIO(data))
    packed = gzip.compress(archive_bytes.getvalue(), mtime=0)
    metadata = dict(schema='openmhd.metadata-regression-source.v1',
        created_utc=datetime.now(timezone.utc).isoformat(), source_revision=revision,
        source_sha256={n: digest(b) for n, b in sorted(sources.items())},
        archive_sha256=digest(packed), job_sha256=digest(sources[job_name]), image=IMAGE,
        tests=selectors, resources=RESOURCES, scientific_tests_or_evolutions_run=False,
        full_m1_accepted=False)
    metadata_bytes = encode(metadata)
    require(not output.exists(), 'Preserve an existing metadata snapshot')
    output.mkdir(parents=True)
    (output / 'source.tar.gz').write_bytes(packed)
    (output / 'snapshot.json').write_bytes(metadata_bytes)
    (output / 'job.py').write_bytes(sources[job_name])
    plan_dir = output / 'preflight'
    case = dict(kind='preflight', resources=RESOURCES)
    workflow = safe_name(prefix) + '-' + digest(metadata_bytes)[:12] + '-preflight'
    entry = create_case(plan_dir / '0000', workflow, packed, metadata_bytes, sources[job_name], case)
    dump(plan_dir / 'plan.json', dict(schema='openmhd.metadata-case-plan.v1',
        snapshot_sha256=digest(metadata_bytes), cases=[entry], full_m1_accepted=False))
    print('Prepared metadata preflight only:', plan_dir)
    print('Unittest cases remain gated on its actual downloaded successful result.')


def prepare_cases(source_dir, preflight_dir, output, prefix):
    snapshot_bytes = (source_dir / 'snapshot.json').read_bytes()
    metadata = json.loads(snapshot_bytes)
    packed, job = (source_dir / 'source.tar.gz').read_bytes(), (source_dir / 'job.py').read_bytes()
    require(digest(packed) == metadata['archive_sha256'] and digest(job) == metadata['job_sha256'],
            'Metadata source changed')
    plan = json.loads((source_dir / 'preflight/plan.json').read_bytes())
    require(len(plan['cases']) == 1 and plan['snapshot_sha256'] == digest(snapshot_bytes), 'Preflight plan')
    entry = plan['cases'][0]
    manifest = json.loads((preflight_dir / 'artifacts.sha256.json').read_bytes())
    expected = {'outputs/' + n for n in ('result.json', 'runtime.json', 'stdout.txt', 'stderr.txt', 'child_result.json')}
    require(set(manifest) == expected, 'Preflight output inventory')
    for name, expected_hash in manifest.items():
        require(digest((preflight_dir / PurePosixPath(name).name).read_bytes()) == expected_hash,
                'Changed preflight output: ' + name)
    result_bytes = (preflight_dir / 'result.json').read_bytes()
    result = json.loads(result_bytes)
    require(result['passed'] is True and result['status'] == 'completed'
            and result['outcome'] == 'success' and result['returncode'] == 0, 'Preflight did not pass')
    require(result['snapshot_sha256'] == digest(snapshot_bytes)
            and result['source_sha256'] == metadata['source_sha256']
            and result['source_revision'] == metadata['source_revision'], 'Preflight source identity')
    require(result['payload_sha256'] == entry['payload_sha256']
            and result['case'] == entry['specification'], 'Preflight payload/case identity')
    child = result['child_result']
    require(child == json.loads((preflight_dir / 'child_result.json').read_bytes()), 'Preflight child link')
    require(child['test_selectors'] == metadata['tests']
            and child['resolved_tests'] == len(metadata['tests']), 'Preflight test selector coverage')
    require(set(child['parsed_files']) == {n for n in metadata['source_sha256'] if n.endswith('.py')},
            'Preflight AST coverage')
    runtime_bytes = (preflight_dir / 'runtime.json').read_bytes()
    runtime = json.loads(runtime_bytes)
    require(digest(runtime_bytes) == result['runtime_sha256'] and runtime['optimized'] == 0
            and runtime['image'] == IMAGE and runtime['declared_resources'] == RESOURCES,
            'Preflight runtime identity')
    require(not result['full_m1_accepted'] and not result['scientific_tests_or_evolutions_run'],
            'Metadata-only scope')
    require(not output.exists(), 'Preserve an existing case plan')
    output.mkdir(parents=True)
    entries = []
    prefix = safe_name(prefix) + '-' + digest(snapshot_bytes)[:12]
    for index, selector in enumerate(metadata['tests']):
        case = dict(kind='unittest', selector=selector, resources=RESOURCES,
                    preflight_result_sha256=digest(result_bytes))
        entries.append(create_case(output / f'{index:04d}', f'{prefix}-{index:04d}',
            packed, snapshot_bytes, job, case, result_bytes))
    dump(output / 'plan.json', dict(schema='openmhd.metadata-case-plan.v1',
        snapshot_sha256=digest(snapshot_bytes), source_revision=metadata['source_revision'],
        preflight_workflow=entry['workflow'], preflight_result_sha256=digest(result_bytes),
        cases=entries, full_m1_accepted=False))
    print('Prepared', len(entries), 'independent metadata workflows:', output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('snapshot', 'cases'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prefix', default='openmhd-m1-archive-metadata')
    parser.add_argument('--snapshot', type=Path)
    parser.add_argument('--preflight', type=Path, help='Actual downloaded outputs directory')
    args = parser.parse_args()
    if args.action == 'snapshot':
        snapshot(args.output.resolve(), args.prefix)
    else:
        require(args.snapshot is not None and args.preflight is not None,
                'cases requires --snapshot and --preflight')
        prepare_cases(args.snapshot.resolve(), args.preflight.resolve(), args.output.resolve(), args.prefix)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
