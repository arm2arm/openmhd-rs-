#!/usr/bin/env python3
"""Proposed one-case G01 reference job; actual arithmetic runs only on REANA.

Reuse the pinned held-leader supervisor and durable launcher, without changing
their process-ownership algorithm. No candidate binary or component acceptance.
"""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

IMAGE = ('gitlab-p4n.aip.de:5005/p4nreana/reana-env@sha256:'
         'aebd7911df9e1e97ad67d15f4c32ab23996000282183fad3bf7a480756522bd7')
PINS = {
    'reference.py': '2b9f55d5ed72a08a90c3445fcd62b7702598174e04603e7ecd0d672c387df2df',
    'design.json': '69fd92fc2009df207d076441527161825eb50ae911a2ec2a8e398d687306f288',
    'launcher.py': 'b600008f8724920a4fb75b74aa23d0cb94ca6bba56cddeec8c433d8e645cbca5',
    'supervisor.py': '8d8a39844b631eb17d46f897bea71ae2464be1e400c75a54dd6c091a1fd2dbc3',
}
INPUTS = frozenset((*PINS, 'runner.py', 'case.json'))
REFERENCE_FILES = frozenset(('input.json', 'reference.json', 'status.json', 'sha256.json'))
FIXTURES = ('periodic_one_cell_self_images', 'periodic_cartesian_2x2x2',
            'periodic_nonuniform_3x2x2', 'periodic_cartesian_4x4x4',
            'periodic_nonuniform_4x4x4', 'bounded_one_cell_2x3x4', 'bounded_oblique_bisector')
PERMUTATIONS = ('xyz', 'xzy', 'yxz', 'yzx', 'zxy', 'zyx')
RESOURCES = {'threads': 1, 'memory': '2Gi', 'timeout_seconds': 300}
MAX_BYTES = 16 * 1024 * 1024


def require(condition, message):
    if not condition:
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


def keys(value, names, message):
    require(type(value) is dict and set(value) == set(names), message)


def regular_bytes(root, name):
    relative = PurePosixPath(name)
    require(relative.parts and not relative.is_absolute() and '..' not in relative.parts
            and relative.as_posix() == name, 'Safe relative path')
    path = root
    for part in relative.parts:
        path = path / part
        require(not path.is_symlink(), 'Linked path rejected')
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_size <= MAX_BYTES,
            'Bounded regular file')
    raw = path.read_bytes()
    after = path.stat()
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    require(len(raw) == after.st_size and all(getattr(before, k) == getattr(after, k) for k in fields),
            'Changed file generation')
    return raw


def catalog():
    """Literal metadata names only; do not call or evaluate the reference here."""
    return [dict(name=f'{fixture}__s{s}__p{p}__t{t}', fixture=fixture,
                 scale_index=s, permutation=p, translation_index=t)
            for fixture in FIXTURES for s in range(3) for p in PERMUTATIONS for t in range(2)]


def validate_inputs(buffers, payload_raw):
    require(type(buffers) is dict and set(buffers) == INPUTS, 'Exact reference-job input inventory')
    require(all(type(raw) is bytes and len(raw) <= MAX_BYTES for raw in buffers.values()),
            'Bounded input buffers')
    payload = parse(payload_raw)
    keys(payload, ('schema', 'input_sha256'), 'Payload keys')
    require(payload['schema'] == 'openmhd.geometry3-reference-job-inputs.v1', 'Reference payload schema')
    require(payload['input_sha256'] == {name: sha(raw) for name, raw in buffers.items()},
            'Exact input digests')
    require(all(sha(buffers[name]) == digest for name, digest in PINS.items()),
            'Pinned reference/design/launcher/supervisor source')
    case = parse(buffers['case.json'])
    keys(case, ('schema', 'selection', 'resources', 'source_revision', 'prerequisite_receipts',
                'candidate_invoked', 'component_accepted'), 'Reference case keys')
    require(case['schema'] == 'openmhd.geometry3-reference-case.v1', 'Reference case schema')
    require(case['selection'] in catalog(), 'Exact registered reference selection')
    selection = case['selection']
    require(type(selection['scale_index']) is int and type(selection['translation_index']) is int,
            'Integer selection indices')
    require(case['resources'] == RESOURCES and type(case['resources']['threads']) is int
            and type(case['resources']['timeout_seconds']) is int, 'Exact declared reference resources')
    require(type(case['source_revision']) is str and re.fullmatch('[0-9a-f]{40}', case['source_revision']),
            'Source revision encoding')
    receipts = case['prerequisite_receipts']
    keys(receipts, ('m1_acceptance', 'reference_source_review', 'reference_arithmetic_output_review',
                    'job_source_review', 'job_method_output_review'), 'Declared prerequisite receipt keys')
    require(all(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) for value in receipts.values()),
            'Declared prerequisite digest encoding')
    require(case['candidate_invoked'] is False and case['component_accepted'] is False,
            'Reference-only nonaccepting scope')
    return case


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_reference(output, case):
    directory = output / 'reference'
    require(not directory.is_symlink(), 'Linked reference directory rejected')
    require({str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file()} == REFERENCE_FILES,
            'Exact complete reference output inventory')
    buffers = {name: regular_bytes(directory, name) for name in REFERENCE_FILES}
    manifest = parse(buffers['sha256.json'])
    require(set(manifest) == REFERENCE_FILES - {'sha256.json'}, 'Reference body manifest inventory')
    for name, row in manifest.items():
        keys(row, ('sha256', 'bytes'), 'Reference body receipt keys')
        require(row == {'sha256': sha(buffers[name]), 'bytes': len(buffers[name])},
                'Actual reference body digest and size')
    status, inputs, reference = (parse(buffers[name]) for name in ('status.json', 'input.json', 'reference.json'))
    require(status['schema'] == 'openmhd.geometry3.reference-execution.v1'
            and status['status'] == 'complete' and status['case'] == case['selection']['name']
            and status['source_sha256'] == PINS['reference.py']
            and status['candidate_invoked'] is False and status['component_accepted'] is False,
            'Actual successful reference status/source')
    require(inputs['schema'] == 'openmhd.geometry3.literal-input.v1'
            and reference['schema'] == 'openmhd.geometry3.exact-reference.v1'
            and inputs['case'] == reference['case'] == case['selection']
            and inputs['design_sha256'] == reference['design_sha256'] == PINS['design.json']
            and reference['input_sha256'] == sha(buffers['input.json'])
            and reference['candidate_invoked'] is False and reference['component_accepted'] is False,
            'Exact case/input/design/reference joins')
    require(type(status['cells']) is int and status['cells'] == len(reference['cells'])
            and type(status['faces']) is int and status['faces'] == len(reference['faces']),
            'Actual reference output counts')
    return {name: {'sha256': sha(raw), 'bytes': len(raw)} for name, raw in buffers.items()}


def run(work):
    output = work / 'outputs'
    output.mkdir()  # Existing output is never reused or overwritten.
    result = dict(schema='openmhd.geometry3-reference-job-result.v1', status='preparing',
                  started_utc=datetime.now(timezone.utc).isoformat(), candidate_invoked=False,
                  component_accepted=False, external_execution_provenance_verified=False)
    runtime, command = {}, {'status': 'not_launched'}
    code = 1
    for name in ('stdout.txt', 'stderr.txt'):
        (output / name).write_bytes(b'')
    try:
        require(__debug__ and sys.flags.optimize == 0, 'Optimized reference execution rejected')
        sys.dont_write_bytecode = True
        payload_raw = regular_bytes(work, 'payload.json')
        buffers = {name: regular_bytes(work, name) for name in INPUTS}
        case = validate_inputs(buffers, payload_raw)
        require(Path(__file__).read_bytes() == buffers['runner.py'], 'Actual loaded runner source')
        launcher = load_module(work / 'launcher.py', 'geometry_reference_durable_launcher')
        supervisor = load_module(work / 'supervisor.py', 'geometry_reference_held_leader')
        environment = dict(os.environ)
        environment.pop('PYTHONOPTIMIZE', None)
        environment.update(PYTHONDONTWRITEBYTECODE='1', PYTHONHASHSEED='0',
                           RAYON_NUM_THREADS='1', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                           MKL_NUM_THREADS='1', RUST_TEST_THREADS='1')
        uname = os.uname()
        runtime = dict(schema='openmhd.geometry3-reference-runtime.v1',
                       executable=sys.executable, python=sys.version, optimized=sys.flags.optimize,
                       system=uname.sysname, machine=uname.machine, release=uname.release,
                       image=IMAGE, image_and_resources_are_declared_labels=True,
                       declared_resources=case['resources'], visible_cpus=os.cpu_count(),
                       input_sha256={name:sha(raw) for name,raw in buffers.items()},
                       payload_sha256=sha(payload_raw), source_revision=case['source_revision'],
                       prerequisite_receipts_declared_only=True,
                       job_path=str(Path(__file__).resolve()),
                       thread_environment={name:environment[name] for name in
                           ('RAYON_NUM_THREADS','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','RUST_TEST_THREADS')})
        for name in ('cpu.max', 'memory.max'):
            path = Path('/sys/fs/cgroup') / name
            runtime[name] = path.read_text().strip() if path.is_file() else None
        launcher.persist(output / 'runtime.json', runtime)
        result.update(status='running', case=case, payload_sha256=sha(payload_raw),
                      runtime_sha256=sha(regular_bytes(output, 'runtime.json')))
        launcher.persist(output / 'result.json', result)
        argv = [sys.executable, str(work / 'reference.py'), '--design', str(work / 'design.json'),
                '--case', case['selection']['name'], '--output', str(output / 'reference')]
        links = dict(runtime=result['runtime_sha256'], payload=sha(payload_raw),
                     **{name:sha(raw) for name,raw in buffers.items()})
        command = launcher.launch_native(supervisor, argv, work, environment, output,
                                         RESOURCES['timeout_seconds'], links)
        require(command['outcome'] == 'success' and command['returncode'] == 0
                and command['cleanup']['direct_child_reaped'] is True
                and command['cleanup']['writers_settled'] is True
                and command['cleanup']['leader_held_until_group_close'] is True
                and command['cleanup']['group_authority_lost'] is False,
                'Successful exact reference command and closed writers')
        result['reference_outputs'] = validate_reference(output, case)
        require(payload_raw == regular_bytes(work, 'payload.json')
                and all(regular_bytes(work, name) == raw for name,raw in buffers.items()),
                'Original inputs unchanged after reference computation')
        result.update(status='complete', reference_case_evaluated=True,
                      scope='One actual independent reference only; candidate and component acceptance remain separate')
        code = 0
    except BaseException as error:
        result.update(status='failed', error_type=type(error).__name__, error=str(error))
        if (output / 'command.json').is_file():
            command = parse((output / 'command.json').read_bytes())
        if command.get('status') != 'not_launched' and command.get('cleanup', {}).get('writers_settled') is not True:
            result['external_terminal_evidence_required'] = True
    finally:
        result['finished_utc'] = datetime.now(timezone.utc).isoformat()
        for name, value in (('result.json', result), ('runtime.json', runtime), ('command.json', command)):
            (output / name).write_bytes(encode(value))
        inventory = {}
        for path in sorted(output.rglob('*')):
            require(not path.is_symlink(), 'Linked output rejected')
            if path.is_file() and path != output / 'artifacts.sha256.json':
                raw = regular_bytes(output, str(path.relative_to(output)))
                inventory['outputs/' + str(path.relative_to(output))] = {'sha256':sha(raw), 'bytes':len(raw)}
        (output / 'artifacts.sha256.json').write_bytes(encode(inventory))
    return code


if __name__ == '__main__':
    sys.exit(run(Path.cwd().resolve()))
