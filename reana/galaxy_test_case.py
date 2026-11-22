#!/usr/bin/env python3
"""Run one exact, exported Rust libtest leaf in a separate REANA workflow.

Inputs are prepared only after actual immutable build-preflight/output review.
The reviewed metadata job supplies Linux held-leader/log-writer supervision;
this module implements the native catalog and libtest witness contract. No
standalone component/scientific acceptance is made by a passing leaf.
"""
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

IMAGE = ('gitlab-p4n.aip.de:5005/p4nreana/reana-env@sha256:'
         'aebd7911df9e1e97ad67d15f4c32ab23996000282183fad3bf7a480756522bd7')
SUPERVISOR_SOURCE = 'tools/m1_evidence/reana_metadata_job.py'
JOB_SOURCE = 'reana/galaxy_test_case.py'
OUTPUT_NAMES = ('result.json', 'runtime.json', 'command.json', 'stdout.txt',
                'stderr.txt', 'child_result.json', 'child_raw.bin', 'artifacts.sha256.json')
FIXED_INPUTS = ('case.py', 'supervisor.py', 'case.json', 'snapshot.json',
                'preflight/preflight.json', 'preflight/execution.json',
                'preflight/runtime.json', 'preflight/artifacts.sha256.json',
                'preflight/commands.json', 'preflight/server_observation.json',
                'preflight/acquisition.json')
EXACT_LIBRARY_SELECTORS = frozenset((
    'three_d::exact::tests::exact_cancellation_retains_below_binary64_ulp_terms',
    'three_d::exact::tests::dyadic_subnormal_and_signed_zero_decode_exactly',
    'three_d::exact::tests::integer_product_carry_matches_binomial_identity',
    'three_d::exact::tests::determinant_orientation_and_exact_coplanar_contact'))


def require(condition, text):
    if not condition:
        raise ValueError(text)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()


def parse(data):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, 'Repeated JSON key')
            value[key] = item
        return value
    return json.loads(data, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def keys(value, names, label):
    require(type(value) is dict and set(value) == set(names), label + ' keys')


def regular_bytes(root, name):
    path = PurePosixPath(name)
    require(path.parts and path.as_posix() == name and not path.is_absolute()
            and '..' not in path.parts, 'Unsafe input path')
    current = root
    for part in path.parts:
        current = current / part
        require(not current.is_symlink(), 'Linked input')
    before = current.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_size <= 16 * 1024 * 1024,
            'Nonregular/excessive input')
    data = current.read_bytes()
    after = current.stat()
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    require(all(getattr(before, field) == getattr(after, field) for field in fields)
            and len(data) == after.st_size, 'Changed input generation')
    return data


def expected_parent_commands(source):
    work = source.parent
    return [
        ['cargo', 'fmt', '--check'],
        ['cargo', 'clippy', '--workspace', '--all-targets', '--all-features',
         '--locked', '--', '-D', 'warnings'],
        ['cargo', 'build', '--release', '--workspace', '--all-features', '--locked'],
        ['python', 'reana/galaxy_preflight.py', '--source', str(source),
         '--snapshot', str(work / 'snapshot.json'),
         '--output', str(work / 'outputs/galaxy-preflight'), '--jobs', '4'],
    ]


def validate_inputs(buffers, supervisor, check_architecture=True):
    """Metadata validation is reusable on a client; jobs MUST check architecture."""
    case = parse(buffers['case.json'])
    keys(case, ('schema', 'leaf', 'resources', 'preflight_workflow', 'preflight_uuid', 'input_pins'), 'Case')
    require(case['schema'] == 'openmhd.galaxy-rust-test-case.v1', 'Native case schema')
    resources = case['resources']
    keys(resources, ('threads', 'memory', 'timeout_seconds'), 'Resources')
    require(type(resources['threads']) is int and resources['threads'] == 1,
            'One libtest thread per workflow')
    require(type(resources['memory']) is str and re.fullmatch(r'[1-9][0-9]*Gi', resources['memory']),
            'Explicit per-case GiB memory')
    require(type(resources['timeout_seconds']) in (int, float)
            and math.isfinite(resources['timeout_seconds']) and 0 < resources['timeout_seconds'] <= 1800,
            'Explicit finite child timeout')
    snapshot = parse(buffers['snapshot.json'])
    preflight = parse(buffers['preflight/preflight.json'])
    execution = parse(buffers['preflight/execution.json'])
    runtime = parse(buffers['preflight/runtime.json'])
    artifacts = parse(buffers['preflight/artifacts.sha256.json'])
    commands = parse(buffers['preflight/commands.json'])
    snapshot_hash = sha(buffers['snapshot.json'])
    require(snapshot['source_sha256'][JOB_SOURCE] == sha(buffers['case.py'])
            and snapshot['source_sha256'][SUPERVISOR_SOURCE] == sha(buffers['supervisor.py']),
            'Job/supervisor source must match original snapshot')
    for path in ('preflight.json', 'commands.json'):
        require(artifacts['outputs/galaxy-preflight/' + path] == sha(buffers['preflight/' + path]),
                'Actual parent artifact digest')
    require(artifacts['outputs/runtime.json'] == sha(buffers['preflight/runtime.json'])
            and artifacts['outputs/execution.json'] == sha(buffers['preflight/execution.json']),
            'Actual parent execution/runtime digest')
    require(preflight['schema'] == 'openmhd.galaxy-rust-preflight.v1'
            and preflight['status'] == 'complete'
            and type(preflight['test_methods_executed']) is int and preflight['test_methods_executed'] == 0
            and preflight['component_accepted'] is False and preflight['before_after_source_identical'] is True
            and preflight['snapshot_sha256'] == execution['snapshot_sha256'] == runtime['snapshot_sha256'] == snapshot_hash,
            'Complete compile/list preflight for exact snapshot')
    require(preflight['source_revision'] == snapshot['source_revision']
            and {name: row['sha256'] for name, row in preflight['source_files'].items()}
            == snapshot['source_sha256']
            and type(preflight['compiled_binaries']) is int
            and preflight['compiled_binaries'] == len(preflight['binaries'])
            and type(preflight['resolved_leaves']) is int
            and preflight['resolved_leaves'] == len(preflight['tests']),
            'Complete matching source/target/leaf inventory')
    require(execution['status'] == 'completed' and execution['study'] == 'galaxy-source-preflight'
            and execution['jobs'] == preflight['jobs'] == 4
            and execution['runtime_sha256'] == sha(buffers['preflight/runtime.json'])
            and runtime['image'] == IMAGE
            and type(runtime['rustc']) is str and runtime['rustc'].startswith('rustc 1.85.1 ')
            and type(runtime['machine']) is str and bool(runtime['machine'])
            and (not check_architecture or runtime['machine'] == os.uname().machine)
            and runtime['bootstrap_sha256'] == snapshot['upload_sha256']['remote.py']
            == snapshot['source_sha256']['reana/remote.py']
            and runtime['bootstrap_file'] == 'remote.py'
            and runtime['source_bootstrap_sha256'] == snapshot['source_sha256']['reana/remote.py'],
            'Passing parent execution/image/architecture/source')
    rows = execution['commands']
    require(type(rows) is list and len(rows) == 4, 'Four source prerequisite commands')
    actual = []
    for row in rows:
        argv = row['command']
        require(type(argv) is list and argv and type(row['returncode']) is int and row['returncode'] == 0
                and artifacts[row['log']] == row['log_sha256'], 'Successful source command/log')
        actual.append(['python', *argv[1:]] if Path(argv[0]).name.startswith('python') else argv)
    source = Path(actual[-1][actual[-1].index('--source') + 1])
    require(source.is_absolute() and source.name == 'source'
            and actual == expected_parent_commands(source), 'Exact source prerequisite command inventory')
    supervisor.validate_server(parse(buffers['preflight/server_observation.json']), case['preflight_workflow'])
    acquisition = parse(buffers['preflight/acquisition.json'])
    require(acquisition['schema'] == 'openmhd.galaxy-preflight-acquisition.v1'
            and acquisition['status'] == 'complete'
            and acquisition['workflow'] == case['preflight_workflow']
            and acquisition['uuid'] == case['preflight_uuid']
            and acquisition['snapshot_sha256'] == snapshot_hash,
            'Original UUID-linked preflight acquisition')
    pins = {name: sha(buffers[name]) for name in FIXED_INPUTS if name != 'case.json'}
    require(case['input_pins'] == pins, 'Exact case-bound dependency inputs')
    require(type(commands) is list and commands, 'Actual compile/list command journal')
    labels = {}
    for row in commands:
        require(row['label'] not in labels and row['status'] == 'complete'
                and type(row['returncode']) is int and row['returncode'] == 0,
                'Unique successful compile/list command')
        labels[row['label']] = row
        for channel in ('stdout', 'stderr'):
            require(artifacts['outputs/galaxy-preflight/' + row[channel]] == row[channel + '_sha256'],
                    'Compile/list raw log digest')
    for profile in ('debug', 'release'):
        expected = ['cargo', 'test', '--workspace', '--all-targets', '--all-features', '--locked',
                    '--no-run', '--message-format=json', '--jobs', '4']
        if profile == 'release':
            expected.append('--release')
        require(labels[profile + '-compile']['argv'] == expected, 'Exact non-executing compile command')
    leaf = case['leaf']
    keys(leaf, ('build_profile', 'manifest', 'target_kind', 'target_name', 'source',
                'selector', 'binary', 'binary_sha256'), 'Leaf')
    # This first reusable-binary route is for the new standalone component tests.
    # Existing restart tests embed CARGO_BIN_EXE paths and need their source-layout route.
    portable = leaf['manifest'] in ('crates/galaxy-types/Cargo.toml', 'crates/gravity/Cargo.toml') or (
        leaf['manifest'] == 'crates/moving-mesh/Cargo.toml' and leaf['target_kind'] == ['test']
        and leaf['target_name'] in ('geometry3_analytic', 'geometry3_controls')) or (
        leaf['manifest'] == 'crates/moving-mesh/Cargo.toml' and leaf['target_kind'] == ['lib']
        and leaf['target_name'] == 'moving_mesh' and leaf['selector'] in EXACT_LIBRARY_SELECTORS)
    require(portable, 'Only reviewed new standalone component targets are portable here')
    require(preflight['tests'].count(leaf) == 1, 'Exactly one resolved leaf in parent catalog')
    matching = [row for row in preflight['binaries'] if row['path'] == leaf['binary']]
    require(len(matching) == 1, 'Unique exported target binary')
    binary = matching[0]
    require(binary['sha256'] == leaf['binary_sha256']
            and binary['selectors'].count(leaf['selector']) == 1
            and binary['manifest'] == leaf['manifest'] and binary['source'] == leaf['source']
            and binary['build_profile'] == leaf['build_profile']
            and binary['target']['kind'] == leaf['target_kind']
            and binary['target']['name'] == leaf['target_name']
            and artifacts['outputs/galaxy-preflight/' + leaf['binary']] == leaf['binary_sha256'],
            'Exact selector/binary/target/source binding')
    listing = labels[binary['list_label']]
    require(listing['argv'] == [str(source / 'target' / leaf['build_profile'] / 'deps' / Path(leaf['binary']).name),
                                '--list', '--format', 'terse'], 'Actual target discovery command')
    return case, leaf, len(binary['selectors']), binary['bytes']


def persist(path, value):
    """Observable atomic publication, not a power-loss recovery guarantee."""
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('wb') as stream:
        stream.write(encode(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def launch_native(supervisor, argv, work, environment, output, timeout, links):
    # Publish this BEFORE entering code which may launch. An escaping exception
    # cannot prove no child was launched, nor authorize any guessed PID signal.
    intent = dict(schema='openmhd.galaxy-native-launch-intent.v1',
                  command=list(argv), cwd=str(work), started_utc=datetime.now(timezone.utc).isoformat(),
                  finished_utc=None, outcome='running', status='pending_launch', returncode=None,
                  timeout_seconds=timeout, timeout_scope='direct-child-wait', links=links,
                  cleanup={'writers_settled': None, 'direct_child_reaped': None},
                  external_terminal_evidence_required=True)
    persist(output / 'command.json', intent)
    try:
        with (output / 'stdout.txt').open('wb') as out, (output / 'stderr.txt').open('wb') as err:
            command = supervisor.supervise(argv, work, environment, out, err, timeout)
    except BaseException as error:
        intent.update(status='unknown_closure', outcome='unknown', error_type=type(error).__name__)
        # Keep null finish/unknown writers. Failed publication leaves the original
        # pending intent, which is also nonpassing and requires external evidence.
        persist(output / 'command.json', intent)
        raise
    command['links'] = links
    command['external_terminal_evidence_required'] = command.get('cleanup', {}).get('writers_settled') is not True
    persist(output / 'command.json', command)
    return command


def witness(stdout, selector, count):
    text = stdout.decode('utf-8')
    starts = re.findall(r'^running ([0-9]+) tests?$', text, flags=re.MULTILINE)
    completions = re.findall(r'^test ' + re.escape(selector) + r'(?: - should panic)? \.\.\. ok$',
                             text, flags=re.MULTILINE)
    result = re.findall(r'^test result: ok\. ([0-9]+) passed; ([0-9]+) failed; ([0-9]+) ignored; '
                        r'([0-9]+) measured; ([0-9]+) filtered out; finished in [^\n]+\n*\Z', text,
                        flags=re.MULTILINE)
    require(starts == ['1'] and len(completions) == 1
            and result == [('1', '0', '0', '0', str(count - 1))],
            'Expected exactly one successful nonignored libtest leaf')
    return {'schema': 'openmhd.galaxy-libtest-witness.v1', 'selector': selector,
            'passed': 1, 'failed': 0, 'ignored': 0, 'measured': 0,
            'filtered_out': count - 1, 'stdout_sha256': sha(stdout)}


def run(work):
    require(__debug__ and sys.flags.optimize == 0, 'Optimized native execution rejected')
    output = work / 'outputs'
    output.mkdir()  # Never overwrite a prior case execution.
    result = {'schema': 'openmhd.galaxy-native-test-result.v1', 'status': 'preparing',
              'started_utc': datetime.now(timezone.utc).isoformat(),
              'component_accepted': False}
    runtime, command = {}, {'status': 'not_launched'}
    child, raw = {'status': 'not_launched'}, b''
    code = 1
    for name in ('stdout.txt', 'stderr.txt'):
        (output / name).write_bytes(b'')
    try:
        payload_bytes = regular_bytes(work, 'payload.json')
        payload = parse(payload_bytes)
        keys(payload, ('schema', 'input_sha256', 'binary_parts'), 'Payload')
        require(payload['schema'] == 'openmhd.galaxy-native-test-inputs.v1', 'Native payload schema')
        parts = payload['binary_parts']
        require(type(parts) is list and 0 < len(parts) <= 512
                and parts == ['test-binary.part' + str(index).zfill(3) for index in range(len(parts))],
                'Ordered unique binary parts')
        require(set(payload['input_sha256']) == set(FIXED_INPUTS) | set(parts), 'Exact input inventory')
        buffers = {name: regular_bytes(work, name) for name in payload['input_sha256']}
        require(all(0 < len(buffers[name]) <= 1024 * 1024 for name in parts),
                'At most 512 nonempty one-MiB binary parts')
        require(all(sha(data) == payload['input_sha256'][name] for name, data in buffers.items()),
                'Verified actual input bytes')
        snapshot = parse(buffers['snapshot.json'])
        require(snapshot['source_sha256'][JOB_SOURCE] == sha(buffers['case.py'])
                and sha(Path(__file__).read_bytes()) == sha(buffers['case.py'])
                and snapshot['source_sha256'][SUPERVISOR_SOURCE] == sha(buffers['supervisor.py']),
                'Pinned native runner and reviewed supervisor')
        module_spec = importlib.util.spec_from_file_location('native_supervisor', work / 'supervisor.py')
        supervisor = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(supervisor)
        case, leaf, count, binary_bytes = validate_inputs(buffers, supervisor)
        binary = work / 'test-binary'
        with binary.open('xb') as stream:
            for name in parts:
                stream.write(buffers[name])
        require(binary.stat().st_size == binary_bytes
                and sha(binary.read_bytes()) == leaf['binary_sha256'], 'Reassembled exact exported executable')
        binary.chmod(0o755)
        runtime = supervisor.runtime_record(work, Path(__file__).resolve())
        runtime.update(image=IMAGE, declared_resources=case['resources'], kind='native-rust-libtest')
        environment = dict(os.environ)
        environment.update(RUST_TEST_THREADS='1', RAYON_NUM_THREADS='1', OMP_NUM_THREADS='1',
                           OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
        argv = [str(binary), '--exact', leaf['selector'], '--test-threads', '1',
                '--color', 'never', '--show-output']
        result.update(status='running', case=case, payload_sha256=sha(payload_bytes),
                      snapshot_sha256=sha(buffers['snapshot.json']),
                      preflight_sha256=sha(buffers['preflight/preflight.json']),
                      binary_sha256=leaf['binary_sha256'])
        runtime.update(machine=os.uname().machine, thread_environment={key: environment[key] for key in
            ('RUST_TEST_THREADS', 'RAYON_NUM_THREADS', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')})
        persist(output / 'runtime.json', runtime)
        persist(output / 'result.json', result)
        links = {name: sha(data) for name, data in (
            ('snapshot', buffers['snapshot.json']), ('case', buffers['case.json']),
            ('payload', payload_bytes), ('runtime', encode(runtime)), ('binary', binary.read_bytes()),
            ('runner', buffers['case.py']), ('supervisor', buffers['supervisor.py']))}
        child = {'status': 'execution_unverified'}
        command = launch_native(supervisor, argv, work, environment, output,
                                case['resources']['timeout_seconds'], links)
        raw = (output / 'stdout.txt').read_bytes()
        require(command['outcome'] == 'success' and command['returncode'] == 0
                and command['cleanup']['writers_settled'] is True
                and command['cleanup']['direct_child_reaped'] is True,
                'Successful supervised native child and closed writers')
        child = witness(raw, leaf['selector'], count)
        require(payload_bytes == regular_bytes(work, 'payload.json')
                and all(regular_bytes(work, name) == data for name, data in buffers.items()),
                'Frozen input bytes remained unchanged')
        result.update(status='passed', test_leaves_executed=1, passing_leaves=1,
                      scope='One actual native test leaf; component and physical acceptance remain separate')
        code = 0
    except BaseException as error:
        result.update(status='failed', error_type=type(error).__name__, error=str(error))
        # Reload durable intent if supervise or its receipt publication escaped.
        if (output / 'command.json').exists():
            command = parse((output / 'command.json').read_bytes())
        if command.get('status') != 'not_launched' and command.get('cleanup', {}).get('writers_settled') is not True:
            result['external_terminal_evidence_required'] = True
            child = {'status': 'unknown_closure', 'external_terminal_evidence_required': True}
        elif command.get('status') == 'not_launched':
            child = {'status': 'not_launched'}
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
            for name in OUTPUT_NAMES if name != 'artifacts.sha256.json'}))
    return code


if __name__ == '__main__':
    sys.exit(run(Path.cwd().resolve()))
