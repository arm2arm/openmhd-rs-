#!/usr/bin/env python3
"""One actual collisionless force comparison, executed on REANA only.

The Rust executable and independently implemented exact reference run as two
separately supervised processes. The original words, logs, source buffers,
reference packet and both command journals are retained. Import is inert.
This job does not implement a force law, time advance or scientific gate.
"""
import sys

if not __debug__ or sys.flags.optimize or __import__('os').environ.get('PYTHONOPTIMIZE', '') not in ('', '0'):
    raise RuntimeError('Optimized force comparison rejected')

import base64
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
    'galaxy_gravity_bridge.py': 'e5c5e9e432ba674ce3454095f4efa3e1b0412b6b2ae41c2b10b6b3808c07a7a6',
    'galaxy_gravity_compare.py': 'eb53c9dc3cf286280e03068c756847cda4903e93d805257c1703c4b391450a0e',
    'galaxy_gravity_reference.py': '91e11a87248f51f00dfa477708dd33f1f49b2cfd1e883a574991ec506fdeffbe',
    'galaxy_geometry3_reference.py': '2b9f55d5ed72a08a90c3445fcd62b7702598174e04603e7ecd0d672c387df2df',
}
FIXED = frozenset((*PINS, 'runner.py', 'case.json', 'root-release.json', 'input.txt'))
PREREQUISITES = frozenset(('m1_acceptance', 'original318_output_review',
    'later90_output_review', 'native186_output_review', 'standalone_build_output_review',
    'force_wrapper_output_review'))
PACKET_FILES = frozenset(('input.json', 'canonical_physical_input.json', 'reference.json',
    'status.json', 'sources.json', 'galaxy_gravity_reference.py',
    'galaxy_geometry3_reference.py', 'files.sha256.json'))
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
        value = {}
        for key, item in pairs:
            require(key not in value, 'Duplicate JSON key')
            value[key] = item
        return value
    def finite_float(text):
        value = float(text)
        require(math.isfinite(value), 'Finite metadata JSON')
        return value
    def invalid(_):
        raise ValueError('Finite metadata JSON')
    return json.loads(raw, object_pairs_hook=unique, parse_float=finite_float, parse_constant=invalid)


def keys(value, expected, message):
    require(type(value) is dict and set(value) == set(expected), message)


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
    keys(payload, ('schema', 'files', 'binary'), 'Exact force payload fields')
    require(payload['schema'] == 'openmhd.gravity-force-case-inputs.v1', 'Force payload schema')
    binary = payload['binary']
    keys(binary, ('sha256', 'bytes', 'parts'), 'Exact binary fields')
    parts = binary['parts']
    require(type(parts) is list and 0 < len(parts) <= 512
            and parts == ['gravity.part' + str(i).zfill(4) for i in range(len(parts))],
            'Ordered bounded binary parts')
    require(type(buffers) is dict and set(buffers) == FIXED | set(parts)
            and all(type(raw) is bytes and len(raw) <= MAX_BYTES for raw in buffers.values()),
            'Exact bounded input inventory')
    require(all(0 < len(buffers[n]) <= 1024 * 1024 for n in parts)
            and all(len(buffers[n]) == 1024 * 1024 for n in parts[:-1]), 'Contiguous binary parts')
    require(type(payload['files']) is dict and payload['files'] == {
        name: descriptor(raw) for name, raw in buffers.items()}
        and all(type(row.get('bytes')) is int for row in payload['files'].values()),
        'Exact input hashes and byte counts')
    require(all(sha(buffers[n]) == digest for n, digest in PINS.items()), 'Reviewed immutable source pins')
    executable = b''.join(buffers[n] for n in parts)
    require(type(binary['bytes']) is int and binary['bytes'] > 0
            and descriptor(executable) == {k: binary[k] for k in ('sha256', 'bytes')},
            'Actual exported executable identity')
    case, release = parse(buffers['case.json']), parse(buffers['root-release.json'])
    keys(case, ('schema', 'name', 'resources', 'root_release_sha256'), 'Exact force case fields')
    require(case['schema'] == 'openmhd.gravity-force-case.v1'
            and type(case['name']) is str and re.fullmatch('[A-Za-z0-9._-]{1,100}', case['name'])
            and case['resources'] == RESOURCES
            and type(case['resources']['threads']) is int
            and type(case['resources']['timeout_seconds']) is int
            and case['root_release_sha256'] == sha(buffers['root-release.json']), 'Case resources and release')
    keys(release, ('schema', 'wrapper_source_revision', 'build_source_revision',
                  'rust_source_inventory_sha256', 'runner_sha256', 'binary', 'input_sha256',
                  'prerequisites', 'component_accepted'), 'Exact root release fields')
    require(release['schema'] == 'openmhd.gravity-force-root-release.v1'
            and all(type(release[k]) is str and re.fullmatch('[0-9a-f]{40}', release[k])
                    for k in ('wrapper_source_revision', 'build_source_revision'))
            and type(release['rust_source_inventory_sha256']) is str
            and re.fullmatch('[0-9a-f]{64}', release['rust_source_inventory_sha256'])
            and release['runner_sha256'] == sha(buffers['runner.py'])
            and release['binary'] == descriptor(executable)
            and release['input_sha256'] == sha(buffers['input.txt'])
            and release['component_accepted'] is False, 'Source, binary and original input links')
    keys(release['prerequisites'], PREREQUISITES, 'All separately reviewed prerequisites')
    require(all(type(v) is str and re.fullmatch('[0-9a-f]{64}', v)
                for v in release['prerequisites'].values()), 'Prerequisite digest encoding')
    require(0 < len(buffers['input.txt']) <= 262144, 'Bounded original force input')
    return case, release, executable


def successful_command(command):
    require(command.get('schema') == 'openmhd.metadata-command.v1'
            and command.get('outcome') == 'success' and type(command.get('returncode')) is int
            and command['returncode'] == 0
            and command.get('external_terminal_evidence_required') is False
            and command.get('cleanup', {}).get('writers_settled') is True
            and command['cleanup'].get('direct_child_reaped') is True
            and command['cleanup'].get('leader_held_until_group_close') is True
            and command['cleanup'].get('group_authority_lost') is False
            and command['cleanup'].get('remaining_live_pids') == [], 'Successful closed actual process')


def process_evidence(command, raw_input, stdout, stderr, invocation):
    successful_command(command)
    return dict(schema='openmhd.gravity-force-process-evidence.v1', invocation_id=invocation,
        outcome='success', returncode=command['returncode'], timed_out=False,
        logs_closed=True, writers_stopped=True, input_sha256=sha(raw_input),
        stdout_sha256=sha(stdout), stdout_bytes=len(stdout), stderr_sha256=sha(stderr), stderr_bytes=len(stderr))


def read_reference_packet(root, projected_input):
    require({p.name for p in root.iterdir()} == PACKET_FILES, 'Exact eight-body reference packet')
    packet = {name: regular_bytes(root, name) for name in PACKET_FILES}
    manifest = parse(packet['files.sha256.json'])
    keys(manifest, ('schema', 'files'), 'Reference manifest fields')
    require(manifest['schema'] == 'openmhd.gravity-reference-files.v1'
            and manifest['files'] == {n: descriptor(raw) for n, raw in packet.items()
                                     if n != 'files.sha256.json'}
            and packet['input.json'] == projected_input
            and all(sha(packet[n]) == PINS[n] for n in
                    ('galaxy_gravity_reference.py', 'galaxy_geometry3_reference.py')),
            'Actual reference input, sources and complete closure')
    return packet


def comparison_passed(comparison):
    require(type(comparison) is dict
            and comparison.get('schema') == 'openmhd.gravity-static-comparison.v1'
            and comparison.get('external_execution_provenance_verified') is False
            and comparison.get('component_accepted') is False and comparison.get('merger_accepted') is False
            and comparison.get('candidate_scales_are_diagnostic_only') is True
            and comparison.get('candidate_residuals_repaired') is False, 'Unmodified arithmetic-only scope')
    gates = comparison.get('gates')
    particles = comparison.get('candidate_projection', {}).get('checked_source', {}).get('particles')
    require(type(particles) is list and len(particles) <= 32
            and all(type(p) is dict and type(p.get('id')) is str
                    and re.fullmatch('[0-9a-f]{32}', p['id']) for p in particles),
            'Checked capped32 ParticleId inventory')
    ids = [p['id'] for p in particles]
    require(ids == sorted(set(ids)), 'Unique sorted actual ParticleIds')
    expected_gates = {'pair_energy', 'raw_net_force', 'raw_net_torque_origin'}
    expected_gates.update('particle.' + identifier + suffix for identifier in ids
                          for suffix in ('.force', '.specific_potential'))
    require(type(gates) is dict and set(gates) == expected_gates
            and all(type(v) is dict and v.get('verdict') in ('pass', 'fail', 'unresolved')
                    for v in gates.values()), 'Exact per-particle and global arithmetic gates')
    verdicts = [v['verdict'] for v in gates.values()]
    expected = 'pass' if all(v == 'pass' for v in verdicts) else 'fail' if 'fail' in verdicts else 'unresolved'
    require(comparison.get('arithmetic_verdict') == expected, 'Gate summary consistency')
    return expected == 'pass'


def load_held(raw, path, name):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def run(work):
    output = work / 'outputs'
    output.mkdir()
    result = dict(schema='openmhd.gravity-force-case-result.v1', status='preparing',
        started_utc=datetime.now(timezone.utc).isoformat(), component_accepted=False,
        merger_accepted=False, physical_evolution_performed=False,
        external_execution_provenance_verified=False)
    commands = dict(schema='openmhd.gravity-force-commands.v1', candidate=dict(status='not_launched'),
                    reference=dict(status='not_launched'))
    runtime, child, code = {}, dict(status='not_compared'), 1
    raw, stderr = b'', b''
    stage_outputs = {}
    saved_modules = {n: sys.modules.get(n) for n in ('force_supervisor', 'force_launcher',
                     'galaxy_gravity_bridge', 'force_comparison')}
    try:
        payload_raw = regular_bytes(work, 'payload.json')
        payload = parse(payload_raw)
        require(type(payload.get('files')) is dict and len(payload['files']) <= len(FIXED) + 512,
                'Bounded declared inputs')
        buffers = {n: regular_bytes(work, n) for n in payload['files']}
        case, release, binary = validate_inputs(buffers, payload_raw)
        require(buffers['runner.py'] == Path(__file__).read_bytes(), 'Actual executing runner source')
        private = work / 'force_private'
        private.mkdir()
        for name in PINS:
            (private / name).write_bytes(buffers[name])
        executable, input_path = private / 'gravity-force-case', private / 'input.txt'
        executable.write_bytes(binary)
        executable.chmod(0o755)
        input_path.write_bytes(buffers['input.txt'])
        supervisor = load_held(buffers['supervisor.py'], private / 'supervisor.py', 'force_supervisor')
        launcher = load_held(buffers['launcher.py'], private / 'launcher.py', 'force_launcher')
        bridge = load_held(buffers['galaxy_gravity_bridge.py'], private / 'galaxy_gravity_bridge.py',
                           'galaxy_gravity_bridge')
        reducer = load_held(buffers['galaxy_gravity_compare.py'], private / 'galaxy_gravity_compare.py',
                            'force_comparison')
        runtime = supervisor.runtime_record(work, Path(__file__).resolve())
        environment = dict(os.environ)
        thread_names = ('RUST_TEST_THREADS', 'RAYON_NUM_THREADS', 'OMP_NUM_THREADS',
                        'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')
        environment.update({n: '1' for n in thread_names})
        runtime.update(image=IMAGE, declared_resources=RESOURCES,
                       thread_environment={n: environment[n] for n in thread_names})
        links = dict(payload_sha256=sha(payload_raw), root_release_sha256=sha(buffers['root-release.json']),
                     binary_sha256=sha(binary), input_sha256=sha(buffers['input.txt']),
                     source_sha256={n: sha(buffers[n]) for n in PINS})
        result.update(status='running_candidate', name=case['name'], links=links)
        (output / 'result.json').write_bytes(encode(result))
        (output / 'runtime.json').write_bytes(encode(runtime))
        for stage in ('candidate', 'reference'):
            folder = private / (stage + '_command')
            folder.mkdir()
            stage_outputs[stage] = folder
        commands['candidate'] = launcher.launch_native(supervisor, [str(executable), str(input_path)],
            private, environment, stage_outputs['candidate'], RESOURCES['timeout_seconds'], links)
        successful_command(commands['candidate'])
        raw = regular_bytes(stage_outputs['candidate'], 'stdout.txt')
        stderr = regular_bytes(stage_outputs['candidate'], 'stderr.txt')
        evidence = process_evidence(commands['candidate'], buffers['input.txt'], raw, stderr, case['name'])
        snapshot = bridge.decode_snapshot(buffers['input.txt'], raw, stderr, evidence)
        projection = bridge.project_reference(snapshot)
        reference_input = projection['reference_input_bytes']
        reference_path = private / 'reference_input.json'
        reference_path.write_bytes(reference_input)
        reference_links = dict(links, projected_reference_input_sha256=sha(reference_input),
                               candidate_command_sha256=sha(regular_bytes(stage_outputs['candidate'], 'command.json')))
        result['status'] = 'running_reference'
        (output / 'result.json').write_bytes(encode(result))
        commands['reference'] = launcher.launch_native(supervisor,
            [sys.executable, '-B', str(private / 'galaxy_gravity_reference.py'), '--input', str(reference_path),
             '--output', str(private / 'reference_packet')], private, environment,
            stage_outputs['reference'], RESOURCES['timeout_seconds'], reference_links)
        successful_command(commands['reference'])
        packet = read_reference_packet(private / 'reference_packet', reference_input)
        child = dict(status='comparing', candidate_process_evidence=evidence,
            reference_packet_base64={n: base64.b64encode(v).decode('ascii') for n, v in packet.items()})
        comparison = reducer.compare(snapshot, packet)
        passed = comparison_passed(comparison)
        child.update(status='compared', comparison=comparison)
        require(len(encode(child)) <= MAX_BYTES, 'Bounded complete comparison evidence')
        require(payload_raw == regular_bytes(work, 'payload.json')
                and all(regular_bytes(work, n) == v for n, v in buffers.items())
                and executable.read_bytes() == binary and input_path.read_bytes() == buffers['input.txt']
                and reference_path.read_bytes() == reference_input
                and all(regular_bytes(private, n) == buffers[n] for n in PINS),
                'Original inputs, sources and actual executable unchanged')
        result.update(status='passed' if passed else 'numeric_gate_failed',
                      arithmetic_verdict=comparison['arithmetic_verdict'], candidate_executions=1,
                      reference_executions=1, projected_reference_input_sha256=sha(reference_input))
        code = 0 if passed else 1
    except BaseException as error:
        result.update(status='failed', error_type=type(error).__name__, error=str(error))
    finally:
        journals = {}
        for stage, folder in stage_outputs.items():
            journals[stage] = {}
            for name in ('command.json', 'stdout.txt', 'stderr.txt'):
                path = folder / name
                if path.exists():
                    captured = path.read_bytes()
                    journals[stage][name] = dict(**descriptor(captured),
                        base64=base64.b64encode(captured).decode('ascii'))
                    if name == 'command.json':
                        try:
                            commands[stage] = parse(captured)
                        except BaseException:
                            commands[stage] = dict(status='unparsed_unknown_closure', sha256=sha(captured))
            if commands[stage].get('status') != 'not_launched' and commands[stage].get('cleanup', {}).get('writers_settled') is not True:
                result['external_terminal_evidence_required'] = True
        if 'candidate' in stage_outputs:
            for name in ('stdout.txt', 'stderr.txt'):
                path = stage_outputs['candidate'] / name
                if path.exists():
                    if name == 'stdout.txt':
                        raw = path.read_bytes()
                    else:
                        stderr = path.read_bytes()
        child['original_stage_journals'] = journals
        if len(encode(child)) > MAX_BYTES:
            # Preserve the full forensic body, but never publish it as a
            # successful packet under the bounded GET protocol.
            result.update(status='failed', error_type='EvidenceSizeLimit',
                          error='Complete original evidence exceeds the export protocol')
            code = 1
        result['finished_utc'] = datetime.now(timezone.utc).isoformat()
        for name, value in (('result.json', result), ('runtime.json', runtime),
                            ('command.json', commands), ('child_result.json', child)):
            (output / name).write_bytes(encode(value))
        (output / 'stdout.txt').write_bytes(raw)
        (output / 'stderr.txt').write_bytes(stderr)
        (output / 'child_raw.bin').write_bytes(raw)
        (output / 'artifacts.sha256.json').write_bytes(encode({
            'outputs/' + name: sha((output / name).read_bytes())
            for name in OUTPUTS if name != 'artifacts.sha256.json'}))
        for name, previous in saved_modules.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
    return code


if __name__ == '__main__':
    sys.exit(run(Path.cwd().resolve()))
