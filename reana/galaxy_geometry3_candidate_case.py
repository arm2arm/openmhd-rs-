#!/usr/bin/env python3
"""One actual static geometry executable/reference comparison, on REANA only.

Import is inert. This wrapper reuses the reviewed held-leader supervisor,
durable native launcher, lossless bridge and exact-error reducer. Input hashes
provide internal consistency; authoritative workflow/build/prerequisite joins
belong to the separate host release and output review.
"""
import sys

if not __debug__ or sys.flags.optimize or __import__('os').environ.get('PYTHONOPTIMIZE', '') not in ('', '0'):
    raise RuntimeError('Optimized candidate execution rejected')

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import types

IMAGE = ('gitlab-p4n.aip.de:5005/p4nreana/reana-env@sha256:'
         'aebd7911df9e1e97ad67d15f4c32ab23996000282183fad3bf7a480756522bd7')
PINS = {
    'supervisor.py': '8d8a39844b631eb17d46f897bea71ae2464be1e400c75a54dd6c091a1fd2dbc3',
    'launcher.py': 'b600008f8724920a4fb75b74aa23d0cb94ca6bba56cddeec8c433d8e645cbca5',
    'galaxy_geometry3_bridge.py': 'bbb5f5d0603d665ac1f0904741bc868953a047418711e6c98280636c08a03c16',
    'compare.py': 'c4c57e5216a59d4578365fad88c636f04d13e41ef3465edb6f26cdba4293c530',
    'design.json': '69fd92fc2009df207d076441527161825eb50ae911a2ec2a8e398d687306f288',
}
FIXED = frozenset((*PINS, 'runner.py', 'case.json', 'root-release.json', 'input.json', 'reference.json'))
PREREQUISITES = frozenset(('m1_acceptance', 'original318_output_review',
    'later90_output_review', 'native186_output_review', 'standalone_build_output_review',
    'reference252_output_review', 'candidate_wrapper_output_review'))
GATES = frozenset(('cell_volume_relative_max', 'cell_centroid_max_over_Lref',
    'positive_face_area_relative_max', 'face_centroid_max_over_Lref',
    'unit_normal_max_component_error', 'central_moment_max_over_expected_V_Lref_squared',
    'normal_closure_norm_over_cell_surface', 'volume_closure_relative'))
RESOURCES = dict(threads=1, memory='2Gi', timeout_seconds=300)
OUTPUTS = ('result.json', 'runtime.json', 'command.json', 'stdout.txt', 'stderr.txt',
           'child_result.json', 'child_raw.bin', 'artifacts.sha256.json')
MAX_BYTES = 16 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()


def parse(raw):
    require(type(raw) is bytes and len(raw) <= MAX_BYTES, 'Bounded JSON buffer')
    def unique(pairs):
        result = {}
        for name, value in pairs:
            require(name not in result, 'Duplicate JSON key')
            result[name] = value
        return result
    def finite_float(text):
        value = float(text)
        require(math.isfinite(value), 'Finite metadata JSON')
        return value
    def invalid(_):
        raise ValueError('Finite metadata JSON')
    return json.loads(raw, object_pairs_hook=unique, parse_float=finite_float, parse_constant=invalid)


def keys(value, names, message):
    require(type(value) is dict and set(value) == set(names), message)


def descriptor(raw):
    return dict(sha256=sha(raw), bytes=len(raw))


def regular_bytes(root, name, limit=MAX_BYTES):
    relative = PurePosixPath(name)
    require(relative.parts and not relative.is_absolute() and '..' not in relative.parts
            and relative.as_posix() == name, 'Safe relative input path')
    path = root
    for part in relative.parts:
        path = path / part
        require(not path.is_symlink(), 'Linked input rejected')
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and before.st_size <= limit, 'Bounded regular unlinked input')
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    require(len(raw) <= limit and len(raw) == after.st_size
            and all(getattr(before, key) == getattr(after, key) for key in fields)
            and path.stat().st_ino == after.st_ino, 'Input generation remained coherent')
    return raw


def validate_inputs(buffers, payload_raw):
    payload = parse(payload_raw)
    keys(payload, ('schema', 'files', 'binary'), 'Exact candidate payload fields')
    require(payload['schema'] == 'openmhd.geometry3-candidate-inputs.v1', 'Candidate payload schema')
    binary = payload['binary']
    keys(binary, ('sha256', 'bytes', 'parts'), 'Exact binary identity fields')
    parts = binary['parts']
    require(type(parts) is list and 0 < len(parts) <= 512
            and parts == ['geometry.part' + str(index).zfill(4) for index in range(len(parts))],
            'Ordered unique bounded binary parts')
    require(type(buffers) is dict and set(buffers) == FIXED | set(parts)
            and all(type(raw) is bytes and len(raw) <= MAX_BYTES for raw in buffers.values()),
            'Exact bounded candidate input inventory')
    require(all(0 < len(buffers[name]) <= 1024 * 1024 for name in parts)
            and all(len(buffers[name]) == 1024 * 1024 for name in parts[:-1]),
            'Contiguous one-MiB binary export parts')
    require(type(payload['files']) is dict and payload['files'] == {
        name: descriptor(raw) for name, raw in buffers.items()}
        and all(type(row.get('bytes')) is int for row in payload['files'].values()),
        'Every exact input digest and byte count')
    require(all(sha(buffers[name]) == expected for name, expected in PINS.items()),
            'Unchanged reviewed source and design pins')
    actual_binary = b''.join(buffers[name] for name in parts)
    require(type(binary['bytes']) is int and binary['bytes'] > 0
            and descriptor(actual_binary) == {key: binary[key] for key in ('sha256', 'bytes')},
            'Reassembled exact build-export executable')
    case, release = parse(buffers['case.json']), parse(buffers['root-release.json'])
    keys(case, ('schema', 'selection', 'resources', 'root_release_sha256'), 'Exact candidate case fields')
    require(case['schema'] == 'openmhd.geometry3-candidate-case.v1'
            and case['resources'] == RESOURCES
            and type(case['resources']['threads']) is int
            and type(case['resources']['timeout_seconds']) is int
            and case['root_release_sha256'] == sha(buffers['root-release.json']), 'Case resources and release link')
    keys(release, ('schema', 'source_revision', 'runner_sha256', 'binary', 'input_sha256',
                  'reference_sha256', 'prerequisites', 'component_accepted'), 'Exact root release fields')
    require(release['schema'] == 'openmhd.geometry3-candidate-root-release.v1'
            and type(release['source_revision']) is str
            and re.fullmatch('[0-9a-f]{40}', release['source_revision'])
            and release['runner_sha256'] == sha(buffers['runner.py'])
            and release['binary'] == descriptor(actual_binary)
            and release['input_sha256'] == sha(buffers['input.json'])
            and release['reference_sha256'] == sha(buffers['reference.json'])
            and release['component_accepted'] is False, 'Exact source, executable and scientific input links')
    keys(release['prerequisites'], PREREQUISITES, 'Every separately scoped prerequisite receipt')
    require(all(type(value) is str and re.fullmatch('[0-9a-f]{64}', value)
                for value in release['prerequisites'].values()), 'Prerequisite digest encoding')
    literal, reference = parse(buffers['input.json']), parse(buffers['reference.json'])
    require(literal['schema'] == 'openmhd.geometry3.literal-input.v1'
            and reference['schema'] == 'openmhd.geometry3.exact-reference.v1'
            and literal['case'] == reference['case'] == case['selection']
            and literal['design_sha256'] == reference['design_sha256'] == PINS['design.json']
            and reference['input_sha256'] == sha(buffers['input.json'])
            and reference['candidate_invoked'] is False and reference['component_accepted'] is False,
            'Actual once-rounded input and independent reference identity')
    return case, release, actual_binary


def load_held(raw, path, name):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def successful_command(command):
    require(command.get('schema') == 'openmhd.metadata-command.v1'
            and command.get('outcome') == 'success' and type(command.get('returncode')) is int
            and command['returncode'] == 0
            and command.get('external_terminal_evidence_required') is False
            and command.get('cleanup', {}).get('writers_settled') is True
            and command.get('cleanup', {}).get('direct_child_reaped') is True
            and command['cleanup'].get('leader_held_until_group_close') is True
            and command['cleanup'].get('group_authority_lost') is False
            and command['cleanup'].get('remaining_live_pids') == [],
            'Successful actual executable and closed child writers required before comparison')


def comparison_passed(comparison):
    require(type(comparison) is dict
            and comparison.get('schema') == 'openmhd.geometry3.exact-error-comparison.proposal.v1'
            and comparison.get('numeric_gates_evaluated') is True
            and comparison.get('execution_provenance_verified') is False
            and comparison.get('component_accepted') is False, 'Separate arithmetic-only comparison scope')
    keys(comparison['gate_verdicts'], GATES, 'Exact eight registered numeric gates')
    require(all(value in ('pass', 'fail', 'unresolved') for value in comparison['gate_verdicts'].values()),
            'Explicit numeric verdict values')
    return all(value == 'pass' for value in comparison['gate_verdicts'].values())


def run(work):
    output = work / 'outputs'
    output.mkdir()  # No reuse of a previous execution directory.
    result = dict(schema='openmhd.geometry3-candidate-result.v1', status='preparing',
        started_utc=datetime.now(timezone.utc).isoformat(), component_accepted=False,
        external_execution_provenance_verified=False, physical_evolution_performed=False,
        scope='One static actual-input comparison; no moving-MHD or merger acceptance')
    runtime, child, command = {}, dict(status='not_compared'), dict(status='not_launched')
    raw, code = b'', 1
    for name in ('stdout.txt', 'stderr.txt'):
        (output / name).write_bytes(b'')
    try:
        payload_raw = regular_bytes(work, 'payload.json')
        payload = parse(payload_raw)
        require(type(payload.get('files')) is dict, 'Declared bounded input files')
        require(len(payload['files']) <= len(FIXED) + 512, 'Bounded input count')
        buffers = {name: regular_bytes(work, name) for name in payload['files']}
        case, release, binary_raw = validate_inputs(buffers, payload_raw)
        require(buffers['runner.py'] == Path(__file__).read_bytes(), 'Actual executing runner source')
        private = work / 'candidate_private'
        private.mkdir()
        for name in ('supervisor.py', 'launcher.py', 'galaxy_geometry3_bridge.py', 'compare.py'):
            (private / name).write_bytes(buffers[name])
        supervisor = load_held(buffers['supervisor.py'], private / 'supervisor.py', 'candidate_supervisor')
        launcher = load_held(buffers['launcher.py'], private / 'launcher.py', 'candidate_launcher')
        bridge = load_held(buffers['galaxy_geometry3_bridge.py'], private / 'galaxy_geometry3_bridge.py',
                           'galaxy_geometry3_bridge')
        old_bridge = sys.modules.get('galaxy_geometry3_bridge')
        sys.modules['galaxy_geometry3_bridge'] = bridge
        try:
            reducer = load_held(buffers['compare.py'], private / 'compare.py', 'candidate_exact_reducer')
        finally:
            if old_bridge is None:
                del sys.modules['galaxy_geometry3_bridge']
            else:
                sys.modules['galaxy_geometry3_bridge'] = old_bridge
        converted = bridge.convert_input(buffers['input.json'])
        input_path, executable = private / 'input.txt', private / 'geometry3-case'
        input_path.write_bytes(converted)
        executable.write_bytes(binary_raw)
        executable.chmod(0o755)
        runtime = supervisor.runtime_record(work, Path(__file__).resolve())
        environment = dict(os.environ)
        thread_names = ('RUST_TEST_THREADS', 'RAYON_NUM_THREADS', 'OMP_NUM_THREADS',
                        'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')
        environment.update({name: '1' for name in thread_names})
        runtime.update(image=IMAGE, declared_resources=RESOURCES,
                       thread_environment={name: environment[name] for name in thread_names})
        links = dict(payload_sha256=sha(payload_raw), root_release_sha256=sha(buffers['root-release.json']),
                     binary_sha256=sha(binary_raw), input_sha256=sha(buffers['input.json']),
                     converted_input_sha256=sha(converted), reference_sha256=sha(buffers['reference.json']),
                     source_sha256={name: sha(buffers[name]) for name in PINS})
        result.update(status='running', case=case['selection'], links=links)
        (output / 'result.json').write_bytes(encode(result))
        (output / 'runtime.json').write_bytes(encode(runtime))
        command = launcher.launch_native(supervisor, [str(executable), str(input_path)], private,
            environment, output, RESOURCES['timeout_seconds'], links)
        successful_command(command)
        raw = regular_bytes(output, 'stdout.txt')
        comparison = reducer.compare(buffers['input.json'], buffers['reference.json'], raw,
                                     buffers['design.json'])
        passed = comparison_passed(comparison)
        child = comparison
        require(payload_raw == regular_bytes(work, 'payload.json')
                and all(regular_bytes(work, name) == value for name, value in buffers.items())
                and executable.read_bytes() == binary_raw and input_path.read_bytes() == converted,
                'Original inputs and executed binary remained unchanged')
        result.update(status='passed' if passed else 'numeric_gate_failed',
                      gate_verdicts=comparison['gate_verdicts'], candidate_executions=1)
        code = 0 if passed else 1
    except BaseException as error:
        result.update(status='failed', error_type=type(error).__name__, error=str(error))
        if (output / 'command.json').exists():
            command = parse((output / 'command.json').read_bytes())
        if command.get('status') != 'not_launched' and command.get('cleanup', {}).get('writers_settled') is not True:
            result['external_terminal_evidence_required'] = True
        if (output / 'stdout.txt').exists():
            raw = (output / 'stdout.txt').read_bytes()
    finally:
        result['finished_utc'] = datetime.now(timezone.utc).isoformat()
        for name, value in (('result.json', result), ('runtime.json', runtime),
                            ('command.json', command), ('child_result.json', child)):
            (output / name).write_bytes(encode(value))
        (output / 'child_raw.bin').write_bytes(raw)
        (output / 'artifacts.sha256.json').write_bytes(encode({
            'outputs/' + name: sha((output / name).read_bytes())
            for name in OUTPUTS if name != 'artifacts.sha256.json'}))
    return code


if __name__ == '__main__':
    sys.exit(run(Path.cwd().resolve()))
