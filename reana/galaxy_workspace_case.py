#!/usr/bin/env python3
"""Rebuild one Cargo target and run exactly one original libtest leaf on REANA.

The small build-input snapshot is separately compiled/listed before release.
Rebuilding preserves Cargo's real CARGO_BIN_EXE dependency for restart tests.
This route does not relax the exported-binary runner's portability restriction.
Imports are inert; component and physical acceptance remain separate.
"""
import sys

if not __debug__ or sys.flags.optimize or __import__('os').environ.get('PYTHONOPTIMIZE', '') not in ('', '0'):
    raise RuntimeError('Optimized workspace execution rejected')

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
}
OUTPUTS = ('result.json', 'runtime.json', 'command.json', 'stdout.txt', 'stderr.txt',
           'child_result.json', 'child_raw.bin', 'artifacts.sha256.json')
FIXED = frozenset((*PINS, 'workspace_case.py', 'case.json', 'root-release.json',
    'snapshot.json', 'parent/preflight.json', 'parent/execution.json',
    'parent/runtime.json', 'parent/artifacts.sha256.json', 'parent/commands.json',
    'parent/observation.json', 'parent/acquisition.json', 'parent/review.json'))
RESOURCES = dict(build_threads=4, test_threads=1, memory='8Gi', command_timeout_seconds=1800)
LEAF_KEYS = frozenset(('build_profile', 'manifest', 'target_kind', 'target_name',
                       'source', 'selector', 'binary', 'binary_sha256'))
PREREQUISITES = frozenset(('m1_acceptance', 'native186_output_review',
    'original_build_output_review', 'source_slice_output_review',
    'workspace_job_metadata_output_review'))
MAX_BYTES = 16 * 1024 * 1024
MAX_EXECUTABLE_BYTES = 128 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()


def parse(raw):
    require(type(raw) is bytes and len(raw) <= MAX_BYTES, 'Bounded JSON')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    def finite(text):
        value = float(text)
        require(math.isfinite(value), 'Finite JSON')
        return value
    def invalid(_):
        raise ValueError('Finite JSON')
    return json.loads(raw, object_pairs_hook=unique, parse_float=finite, parse_constant=invalid)


def keys(value, expected, label):
    require(type(value) is dict and set(value) == set(expected), label + ' fields')


def relative(name):
    require(type(name) is str, 'Relative path string')
    path = PurePosixPath(name)
    require(path.parts and path.as_posix() == name and not path.is_absolute()
            and '..' not in path.parts, 'Safe relative path')
    return path


def regular(root, name, limit=MAX_BYTES):
    path = root
    for part in relative(name).parts:
        path = path / part
        require(not path.is_symlink(), 'Linked file')
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and before.st_size <= limit, 'Bounded regular file')
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    require(len(raw) == after.st_size <= limit
            and all(getattr(before, n) == getattr(after, n) for n in
                    ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))
            and path.stat().st_ino == after.st_ino, 'Coherent file generation')
    return raw


def load_module(name, raw, path):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def compiler_pins(work):
    return {name: sha(regular(work, name, MAX_EXECUTABLE_BYTES))
            for name in ('runtime/rust/bin/rustc', 'runtime/rust/bin/cargo')}


def validate_inputs(buffers, payload_raw):
    payload = parse(payload_raw)
    keys(payload, ('schema', 'files'), 'Payload')
    require(payload['schema'] == 'openmhd.g00-source-leaf-inputs.v1', 'Payload schema')
    require(type(buffers) is dict and set(buffers) == FIXED
            and payload['files'] == {n: dict(sha256=sha(raw), bytes=len(raw)) for n, raw in buffers.items()}
            and all(type(row['bytes']) is int for row in payload['files'].values()), 'Exact input bytes')
    require(all(sha(buffers[n]) == digest for n, digest in PINS.items()), 'Immutable supervisor and launcher')
    case, release = parse(buffers['case.json']), parse(buffers['root-release.json'])
    keys(case, ('schema', 'leaf', 'resources', 'parent_workflow', 'parent_uuid',
                'root_release_sha256'), 'Case')
    require(case['schema'] == 'openmhd.g00-source-leaf-case.v1'
            and case['resources'] == RESOURCES
            and all(type(case['resources'][n]) is int for n in ('build_threads', 'test_threads', 'command_timeout_seconds')),
            'Exact independent case resources')
    keys(release, ('schema', 'job_sha256', 'source_revision', 'compiled_source_revision',
                  'snapshot_sha256', 'parent_review_sha256', 'prerequisites', 'component_accepted'), 'Root release')
    require(release['schema'] == 'openmhd.g00-source-leaf-release.v1'
            and release['component_accepted'] is False
            and re.fullmatch('[0-9a-f]{40}', release['source_revision'])
            and release['job_sha256'] == sha(buffers['workspace_case.py'])
            and case['root_release_sha256'] == sha(buffers['root-release.json']), 'Explicit root release')
    require(type(release['prerequisites']) is dict and set(release['prerequisites']) == PREREQUISITES
            and all(type(v) is str and re.fullmatch('[0-9a-f]{64}', v) for v in release['prerequisites'].values()),
            'Separate prerequisite output reviews')
    snapshot = parse(buffers['snapshot.json'])
    report = parse(buffers['parent/preflight.json'])
    execution = parse(buffers['parent/execution.json'])
    runtime = parse(buffers['parent/runtime.json'])
    artifacts = parse(buffers['parent/artifacts.sha256.json'])
    observation = parse(buffers['parent/observation.json'])
    acquisition = parse(buffers['parent/acquisition.json'])
    review = parse(buffers['parent/review.json'])
    snapshot_hash = sha(buffers['snapshot.json'])
    require(release['snapshot_sha256'] == snapshot_hash == report['snapshot_sha256']
            == execution['snapshot_sha256'] == runtime['snapshot_sha256']
            and release['compiled_source_revision'] == report['source_revision'] == snapshot['source_revision'],
            'Exact original compiled source generation')
    require(report['schema'] == 'openmhd.galaxy-rust-preflight.v1' and report['status'] == 'complete'
            and report['before_after_source_identical'] is True and report['component_accepted'] is False
            and type(report['test_methods_executed']) is int and report['test_methods_executed'] == 0
            and report['compiled_binaries'] == len(report['binaries'])
            and report['resolved_leaves'] == len(report['tests'])
            and {n: v['sha256'] for n, v in report['source_files'].items()} == snapshot['source_sha256'],
            'Complete nonexecuting source preflight')
    require(execution['study'] == 'galaxy-source-preflight' and execution['status'] == 'completed'
            and execution['jobs'] == report['jobs'] == 4 and runtime['image'] == IMAGE
            and runtime['rustc'].startswith('rustc 1.85.1 ')
            and execution['runtime_sha256'] == sha(buffers['parent/runtime.json'])
            and runtime['bootstrap_sha256'] == snapshot['upload_sha256']['remote.py']
            == snapshot['source_sha256']['reana/remote.py'], 'Actual build/image/bootstrap prerequisite')
    for name, path in (('execution.json', 'execution.json'), ('runtime.json', 'runtime.json'),
                       ('preflight.json', 'galaxy-preflight/preflight.json'), ('commands.json', 'galaxy-preflight/commands.json')):
        require(artifacts['outputs/' + path] == sha(buffers['parent/' + name]), 'Parent artifact digest')
    rows = observation['matches']
    require(observation['origin'] == 'server' and len(rows) == 1
            and rows[0]['workflow'] == case['parent_workflow'] and rows[0]['id'] == case['parent_uuid']
            and type(rows[0]['version']) is int and rows[0]['version'] == 1 and rows[0]['status'] == 'finished'
            and re.fullmatch('[0-9a-f-]{36}', case['parent_uuid']), 'Unique actual finished parent UUID')
    require(acquisition['schema'] == 'openmhd.g00-source-parent-acquisition.v1'
            and acquisition['status'] == 'complete' and acquisition['workflow'] == case['parent_workflow']
            and acquisition['uuid'] == case['parent_uuid'] and acquisition['snapshot_sha256'] == snapshot_hash
            and acquisition['all_required_metadata_and_logs_verified'] is True
            and acquisition['binary_archive_acquired'] is False, 'Metadata-only parent acquisition scope')
    require(release['parent_review_sha256'] == sha(buffers['parent/review.json'])
            == release['prerequisites']['source_slice_output_review']
            and review['status'] == 'supported' and review['component_accepted'] is False
            and review['snapshot_sha256'] == snapshot_hash and review['uuid'] == case['parent_uuid']
            and review['errors'] == [] and review['logical_catalog_matches_original676'] is True,
            'Actual parent output review and original catalog join')
    commands = execution['commands']
    require(type(commands) is list and len(commands) == 4
            and all(type(r['returncode']) is int and r['returncode'] == 0 for r in commands), 'Four successful parent commands')
    source = Path(commands[-1]['command'][commands[-1]['command'].index('--source') + 1])
    expected = [['cargo', 'fmt', '--check'], ['cargo', 'clippy', '--workspace', '--all-targets', '--all-features',
        '--locked', '--', '-D', 'warnings'], ['cargo', 'build', '--release', '--workspace', '--all-features', '--locked'],
        ['python', 'reana/galaxy_preflight.py', '--source', str(source), '--snapshot', str(source.parent / 'snapshot.json'),
         '--output', str(source.parent / 'outputs/galaxy-preflight'), '--jobs', '4']]
    actual = [['python', *r['command'][1:]] if Path(r['command'][0]).name.startswith('python') else r['command'] for r in commands]
    require(source.is_absolute() and source.name == 'source' and actual == expected
            and all(artifacts[r['log']] == r['log_sha256'] for r in commands), 'Exact parent prerequisite commands')
    leaf = case['leaf']
    keys(leaf, LEAF_KEYS, 'Leaf')
    require(leaf['build_profile'] in ('debug', 'release') and leaf['target_kind'] in (['lib'], ['test'], ['bin'], ['example'])
            and re.fullmatch('[A-Za-z_][A-Za-z_0-9:]*', leaf['selector'])
            and re.fullmatch('[A-Za-z_][A-Za-z_0-9-]*', leaf['target_name'])
            and report['tests'].count(leaf) == 1, 'One exact original catalog leaf')
    for n in ('manifest', 'source'):
        relative(leaf[n])
        require(leaf[n] in snapshot['source_sha256'], 'Leaf source is frozen')
    matching = [b for b in report['binaries'] if b['path'] == leaf['binary']]
    require(len(matching) == 1 and matching[0]['sha256'] == leaf['binary_sha256']
            and matching[0]['selectors'].count(leaf['selector']) == 1
            and matching[0]['manifest'] == leaf['manifest'] and matching[0]['source'] == leaf['source']
            and matching[0]['target']['kind'] == leaf['target_kind']
            and matching[0]['target']['name'] == leaf['target_name']
            and matching[0]['build_profile'] == leaf['build_profile'], 'Parent target selector identity')
    return case, snapshot, matching[0]['selectors']


def compiler_config(rustc):
    """Scalar Cargo1.85.1 overrides used by the actually validated driver builder."""
    require(rustc.is_absolute(), 'Absolute compiler')
    selection = {n: str(rustc) if n in ('RUSTC', 'CARGO_BUILD_RUSTC') else '' for n in
        ('RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'CARGO_BUILD_RUSTC',
         'CARGO_BUILD_RUSTC_WRAPPER', 'CARGO_BUILD_RUSTC_WORKSPACE_WRAPPER')}
    values = [('build.rustc', json.dumps(str(rustc))), ('build.rustc-wrapper', '""'),
              ('build.rustc-workspace-wrapper', '""'), ('build.rustflags', '[]')]
    values += [('env.' + n + '.' + field, literal) for n, value in selection.items()
               for field, literal in (('value', json.dumps(value)), ('force', 'true'), ('relative', 'false'))]
    return [item for n, value in values for item in ('--config', n + '=' + value)]


def environment(work):
    # No inherited Cargo target/runner/wrapper/flags selection survives. Public
    # compiler paths and flags are recorded; private settings are never emitted.
    env = {n: v for n, v in os.environ.items() if not n.startswith(('CARGO_', 'RUST'))}
    compiler = work / 'runtime/rust/bin/rustc'
    env.update(PATH=str(compiler.parent) + os.pathsep + env.get('PATH', ''),
        CARGO_HOME=str(work / 'runtime/cargo'), CARGO_BUILD_JOBS='4',
        CARGO_TARGET_DIR=str(work / 'source/target'), RUSTC=str(compiler),
        CARGO_BUILD_RUSTC=str(compiler), RUSTC_WRAPPER='', RUSTC_WORKSPACE_WRAPPER='',
        CARGO_BUILD_RUSTC_WRAPPER='', CARGO_BUILD_RUSTC_WORKSPACE_WRAPPER='',
        RUSTFLAGS='', CARGO_ENCODED_RUSTFLAGS='', RUST_TEST_THREADS='1',
        RAYON_NUM_THREADS='1', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    return env


def build_argv(work, leaf):
    target = {'lib': ['--lib'], 'test': ['--test', leaf['target_name']],
              'bin': ['--bin', leaf['target_name']], 'example': ['--example', leaf['target_name']]}[leaf['target_kind'][0]]
    argv = [str(work / 'runtime/rust/bin/cargo'), 'test', '--manifest-path',
            str(work / 'source' / leaf['manifest']), *target, '--all-features', '--locked',
            '--no-run', '--message-format=json', '--jobs', '4', '--target-dir', str(work / 'source/target'),
            *compiler_config(work / 'runtime/rust/bin/rustc')]
    return argv + (['--release'] if leaf['build_profile'] == 'release' else [])


def select_artifacts(raw, source, leaf):
    finished, tests, applications = [], [], []
    for line in raw.splitlines():
        if not line.startswith(b'{'):
            continue
        row = parse(line)
        if row.get('reason') == 'build-finished':
            finished.append(row.get('success'))
        if row.get('reason') != 'compiler-artifact' or row.get('executable') is None:
            continue
        target = row['target']
        identity = (str(Path(row['manifest_path']).relative_to(source)), target['kind'], target['name'],
                    str(Path(target['src_path']).relative_to(source)))
        wanted = (leaf['manifest'], leaf['target_kind'], leaf['target_name'], leaf['source'])
        if row['profile'].get('test') is True and identity == wanted:
            tests.append(row)
        if row['profile'].get('test') is False and identity == ('apps/openmhd/Cargo.toml', ['bin'],
                'vector-potential', 'apps/openmhd/src/bin/vector-potential.rs'):
            applications.append(row)
    require(finished == [True] and len(tests) == 1, 'Unique successful Cargo target')
    restart = leaf['manifest'] == 'apps/openmhd/Cargo.toml' and leaf['target_kind'] == ['test'] and leaf['target_name'] == 'restart'
    require(not restart or len(applications) == 1, 'Actual Cargo-created restart application dependency')
    selected = tests + (applications if restart else [])
    for row in selected:
        path = Path(row['executable'])
        require(path.is_absolute() and path.resolve() == path and path.is_relative_to(source / 'target'),
                'Actual canonical target executable')
    return selected


def listing(raw):
    names = []
    for line in raw.decode().splitlines():
        match = re.fullmatch(r'([A-Za-z_][A-Za-z_0-9:]*): test', line)
        require(match is not None, 'Plain libtest listing')
        names.append(match.group(1))
    require(len(names) == len(set(names)), 'Unique listing selectors')
    return names


def settled(command):
    require(command.get('outcome') == 'success' and type(command.get('returncode')) is int
            and command['returncode'] == 0 and command.get('cleanup', {}).get('writers_settled') is True
            and command['cleanup'].get('direct_child_reaped') is True
            and command['cleanup'].get('leader_held_until_group_close') is True
            and command['cleanup'].get('group_authority_lost') is False, 'Successful held-leader command closure')


def execute_stage(output, source, label, argv, supervisor, native, env, links, stages):
    destination = output / 'workspace_commands' / label
    destination.mkdir(parents=True)
    row = dict(label=label, argv=argv, command=None, stdout_base64='', stderr_base64='')
    stages.append(row)
    native.persist(output / 'command.json', dict(schema='openmhd.g00-source-commands.v1', stages=stages))
    try:
        command = native.launch_native(supervisor, argv, source, env, destination, 1800, links)
        settled(command)
    finally:
        if (destination / 'command.json').exists():
            row['command'] = parse(regular(destination, 'command.json'))
        for channel in ('stdout', 'stderr'):
            raw = regular(destination, channel + '.txt') if (destination / (channel + '.txt')).exists() else b''
            row[channel + '_base64'] = base64.b64encode(raw).decode()
        native.persist(output / 'command.json', dict(schema='openmhd.g00-source-commands.v1', stages=stages))
    return base64.b64decode(row['stdout_base64'])


def run(work):
    output = work / 'outputs'
    require(not output.is_symlink() and output.is_dir()
            and {p.name for p in output.iterdir()} == {'runtime.json'}, 'Fresh prepared workspace output')
    prepared_runtime = regular(output, 'runtime.json')
    result = dict(schema='openmhd.g00-source-leaf-result.v1', status='preparing',
        started_utc=datetime.now(timezone.utc).isoformat(), component_accepted=False)
    stages, binaries, inputs, source_before = [], [], {}, {}
    runtime, stdout, stderr, witness = {}, b'', b'', None
    code = 1
    def source_fence(snapshot):
        return {n: sha(regular(work / 'source', n)) for n in snapshot['source_sha256']}
    def stage(label, argv, supervisor, native, env):
        nonlocal stdout, stderr
        try:
            return execute_stage(output, work / 'source', label, argv, supervisor, native, env,
                dict(payload=sha(payload_raw), snapshot=sha(inputs['snapshot.json']), stage=label), stages)
        finally:
            if stages:
                stdout = base64.b64decode(stages[-1]['stdout_base64'])
                stderr = base64.b64decode(stages[-1]['stderr_base64'])
    try:
        payload_raw = regular(work, 'payload.json')
        inputs = {n: regular(work, n) for n in FIXED}
        case, snapshot, names = validate_inputs(inputs, payload_raw)
        require(inputs['workspace_case.py'] == regular(Path(__file__).resolve().parent, Path(__file__).name), 'Actual runner source')
        source_before = source_fence(snapshot)
        require(source_before == snapshot['source_sha256'], 'Exact prepared source closure')
        prepared = parse(prepared_runtime)
        require(prepared['snapshot_sha256'] == sha(inputs['snapshot.json']) and prepared['image'] == IMAGE
                and prepared['machine'] == os.uname().machine and prepared['rustc'].startswith('rustc 1.85.1 '), 'Actual prepared runtime')
        supervisor = load_module('workspace_supervisor', inputs['supervisor.py'], work / 'supervisor.py')
        native = load_module('workspace_native', inputs['launcher.py'], work / 'launcher.py')
        compiler = work / 'runtime/rust/bin/rustc'
        tool_pins = compiler_pins(work)
        env = environment(work)
        compiler_raw = stage('compiler', [str(compiler), '-Vv'], supervisor, native, env)
        require(compiler_raw.decode() == prepared['rustc'], 'Same prepared actual compiler')
        compile_raw = stage('compile', build_argv(work, case['leaf']), supervisor, native, env)
        artifacts = select_artifacts(compile_raw, work / 'source', case['leaf'])
        for artifact in artifacts:
            path = Path(artifact['executable'])
            raw = regular(work / 'source', str(path.relative_to(work / 'source')), MAX_EXECUTABLE_BYTES)
            binaries.append(dict(artifact=artifact, sha256=sha(raw), bytes=len(raw)))
        binary = artifacts[0]['executable']
        require(listing(stage('list', [binary, '--list', '--format', 'terse'], supervisor, native, env)) == names,
                'Exact parent target selector catalog')
        require(listing(stage('ignored-list', [binary, '--list', '--ignored', '--format', 'terse'], supervisor, native, env)) == [],
                'No ignored leaf substitution')
        argv = [binary, '--exact', case['leaf']['selector'], '--test-threads', '1', '--color', 'never', '--show-output']
        raw = stage('leaf', argv, supervisor, native, env)
        witness = native.witness(raw, case['leaf']['selector'], len(names))
        require(source_fence(snapshot) == source_before
                and all(regular(work, n) == raw for n, raw in inputs.items())
                and regular(work, 'payload.json') == payload_raw, 'Source and all inputs unchanged through leaf')
        require(compiler_pins(work) == tool_pins, 'Compiler and Cargo unchanged')
        require(all(sha(regular(work / 'source', str(Path(b['artifact']['executable']).relative_to(work / 'source')),
                    MAX_EXECUTABLE_BYTES)) == b['sha256'] for b in binaries), 'Test and real application binary unchanged')
        runtime = dict(image=IMAGE, machine=os.uname().machine, prepared_runtime_sha256=sha(prepared_runtime),
            declared_resources=RESOURCES, tool_pins=tool_pins, compiler_stdout_sha256=sha(compiler_raw),
            thread_environment={n: env[n] for n in ('CARGO_BUILD_JOBS', 'RUST_TEST_THREADS', 'RAYON_NUM_THREADS',
                'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')})
        result.update(status='passed', case=case, payload_sha256=sha(payload_raw),
            snapshot_sha256=sha(inputs['snapshot.json']), test_leaves_executed=1, passing_leaves=1)
        code = 0
    except BaseException as error:
        result.update(status='failed', error_type=type(error).__name__, error=str(error),
            external_terminal_evidence_required=any(not r.get('command')
                or r['command'].get('cleanup', {}).get('writers_settled') is not True for r in stages))
    finally:
        result['finished_utc'] = datetime.now(timezone.utc).isoformat()
        child = dict(schema='openmhd.g00-source-leaf-child.v1', prepared_runtime_base64=base64.b64encode(prepared_runtime).decode(),
            stages=stages, compiled_executables=binaries, witness=witness, component_accepted=False)
        for name, value in (('result.json', result), ('runtime.json', runtime),
                            ('command.json', dict(schema='openmhd.g00-source-commands.v1', stages=stages)), ('child_result.json', child)):
            (output / name).write_bytes(encode(value))
        (output / 'stdout.txt').write_bytes(stdout)
        (output / 'stderr.txt').write_bytes(stderr)
        (output / 'child_raw.bin').write_bytes(stdout)
        (output / 'artifacts.sha256.json').write_bytes(encode({'outputs/' + n: sha(regular(output, n))
            for n in OUTPUTS if n != 'artifacts.sha256.json'}))
    return code


if __name__ == '__main__':
    sys.exit(run(Path.cwd().resolve()))
