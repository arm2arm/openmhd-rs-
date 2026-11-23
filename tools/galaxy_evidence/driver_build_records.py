"""Unadopted, inert standalone-build RECORD consistency validator.

No files, imports of target modules, subprocesses, network or binary execution.
The caller supplies retained bytes. This is deliberately NOT an authoritative
acquisition/offline packet verifier: authenticated observations, transports,
submitted inputs and the externally reviewed prerequisite are separate gates.
"""
from datetime import datetime
import hashlib
import json
import math
from pathlib import PurePosixPath
import re


PREFIX = 'outputs/galaxy-driver-build/'
PREPARED = 'outputs/runtime.json'
LABELS = ('compiler', 'geometry', 'gravity')
TARGETS = {
    'geometry': ('moving-mesh', 'geometry3-case', 'crates/moving-mesh'),
    'gravity': ('gravity', 'gravity-force-case', 'crates/gravity'),
}
PINS = {
    'reana/galaxy_driver_build.py':
        'cf268b9844f24ad96b1c525f02c68bc3f22063e5cbb6ea3dcea1d57675f033ca',
    'reana/galaxy_test_case.py':
        'b600008f8724920a4fb75b74aa23d0cb94ca6bba56cddeec8c433d8e645cbca5',
    'tools/m1_evidence/reana_metadata_job.py':
        '8d8a39844b631eb17d46f897bea71ae2464be1e400c75a54dd6c091a1fd2dbc3',
    'scripts/prepare_reana.py':
        'b723f625287c7e793d1881d83017ccffa5f332b75c6968730aa00843c9be36b0',
}
COMPILER_KEYS = ('RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
                 'CARGO_BUILD_RUSTC', 'CARGO_BUILD_RUSTC_WRAPPER',
                 'CARGO_BUILD_RUSTC_WORKSPACE_WRAPPER')
BLOCK = 1024 * 1024
MAX_METADATA = 16 * BLOCK
MAX_BINARY = 512 * BLOCK


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw):
    require(type(raw) is bytes and len(raw) <= MAX_METADATA, 'Bounded JSON bytes')
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, 'Duplicate JSON key')
            value[key] = item
        return value
    def finite_float(text):
        value = float(text)
        require(math.isfinite(value), 'Nonfinite JSON')
        return value
    return json.loads(raw, object_pairs_hook=unique,
        parse_float=finite_float,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def descriptor(raw):
    require(type(raw) is bytes, 'Byte buffer required')
    return {'sha256': sha(raw), 'bytes': len(raw)}


def same(left, right):
    """JSON structural equality preserving bool/int and integer/float types."""
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def digest(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value), 'Canonical SHA256')
    return value


def described(value, maximum=MAX_BINARY, nonempty=False):
    require(type(value) is dict and set(value) == {'sha256', 'bytes'}, 'Exact byte descriptor')
    digest(value['sha256'])
    require(type(value['bytes']) is int and int(nonempty) <= value['bytes'] <= maximum,
            'Bounded integer byte count')
    return value


def relative(name):
    require(type(name) is str, 'String relative path')
    path = PurePosixPath(name)
    require(path.parts and not path.is_absolute() and path.as_posix() == name
            and '..' not in path.parts, 'Canonical relative path')
    return name


def absolute(name):
    require(type(name) is str, 'String absolute path')
    path = PurePosixPath(name)
    require(path.is_absolute() and path.as_posix() == name and '..' not in path.parts
            and not name.startswith('//'), 'Canonical absolute POSIX path')
    return path


def utc(value):
    require(type(value) is str, 'UTC text')
    value = datetime.fromisoformat(value)
    require(value.tzinfo is not None and value.utcoffset().total_seconds() == 0, 'UTC timestamp')
    return value


def interval(row):
    start, finish = utc(row['started_utc']), utc(row['finished_utc'])
    require(finish >= start and type(row['duration_seconds']) in (int, float)
            and math.isfinite(row['duration_seconds']) and row['duration_seconds'] >= 0,
            'Settled command interval')
    return start, finish


def compiler_policy(rustc):
    rustc = str(absolute(rustc))
    environment = {key: rustc if key in ('RUSTC', 'CARGO_BUILD_RUSTC') else ''
                   for key in COMPILER_KEYS}
    fields = [('build.rustc', json.dumps(rustc)), ('build.rustc-wrapper', '""'),
              ('build.rustc-workspace-wrapper', '""')]
    fields += [('env.' + key + '.' + field, literal)
               for key, value in environment.items()
               for field, literal in (('value', json.dumps(value)),
                                      ('force', 'true'), ('relative', 'false'))]
    return {'schema': 'openmhd.galaxy-compiler-selection.v1', 'environment': environment,
            'cargo_config_argv': [item for key, value in fields for item in ('--config', key + '=' + value)],
            'inherited_override_values_retained': False}


def argv_for(label, source):
    source = absolute(source)
    rustc = str(source.parent / 'runtime/rust/bin/rustc')
    if label == 'compiler':
        return [rustc, '-Vv'], 60
    require(label in TARGETS, 'Known build label')
    package, target, _ = TARGETS[label]
    return [str(source.parent / 'runtime/rust/bin/cargo'), 'build', '--release', '--package',
            package, '--example', target, '--all-features', '--locked', '--message-format=json',
            '--jobs', '4', *compiler_policy(rustc)['cargo_config_argv']], 1800


def command_record(raw, label, source, links):
    row = parse(raw)
    require(type(row) is dict and row.get('schema') == 'openmhd.metadata-command.v1'
            and row.get('outcome') == 'success' and type(row.get('returncode')) is int
            and row['returncode'] == 0 and row.get('error_type') is None
            and row.get('external_terminal_evidence_required') is False, 'Successful native command')
    argv, seconds = argv_for(label, source)
    require(row.get('command') == argv and row.get('cwd') == source
            and type(row.get('timeout_seconds')) is int and row['timeout_seconds'] == seconds
            and row.get('timeout_scope') == 'direct-child-wait' and same(row.get('links'), links),
            'Exact native command invocation and links')
    cleanup = row.get('cleanup')
    require(type(cleanup) is dict and all(cleanup.get(k) is True for k in
            ('writers_settled', 'direct_child_reaped', 'leader_held_until_group_close'))
            and cleanup.get('group_authority_lost') is False
            and cleanup.get('remaining_live_pids') == [], 'Settled original command writers')
    leader = cleanup.get('leader_identity')
    require(type(leader) is dict and set(leader) == {'pid', 'process_group', 'session', 'starttime'},
            'Exact held leader identity')
    require(all(type(leader[k]) is int and leader[k] > 0 for k in ('pid', 'process_group', 'session'))
            and leader['pid'] == leader['process_group'] == leader['session']
            and type(row.get('pid')) is int and row['pid'] == leader['pid']
            and type(row.get('process_group')) is int and row['process_group'] == leader['process_group']
            and type(leader['starttime']) is str and re.fullmatch('[0-9]+', leader['starttime']),
            'Original private leader/session linkage')
    interval(row)
    return row


def command_receipt(buffers, label):
    require(label in LABELS, 'Known receipt label')
    result = {'label': label}
    for key, name in (('command', 'command.json'), ('stdout', 'stdout.txt'), ('stderr', 'stderr.txt')):
        path = label + '/' + name
        raw = buffers[PREFIX + path]
        require(type(raw) is bytes and len(raw) <= MAX_METADATA, 'Bounded command/log buffer')
        result[key] = {'path': path, **descriptor(raw)}
    return result


def cargo_record(raw, kind, source):
    require(kind in TARGETS and type(raw) is bytes and len(raw) <= MAX_METADATA, 'Bounded Cargo log')
    _, target, base = TARGETS[kind]
    source = absolute(source)
    matches, finished = [], []
    for line in raw.decode('utf-8').splitlines():
        if not line.startswith('{'):
            continue
        row = parse(line.encode())
        require(type(row) is dict, 'Cargo JSON object')
        if row.get('reason') == 'build-finished':
            require(type(row.get('success')) is bool, 'Literal Cargo success boolean')
            finished.append(row['success'])
        if row.get('reason') != 'compiler-artifact':
            continue
        value = row.get('target')
        require(type(value) is dict, 'Cargo target object')
        if 'example' not in value.get('kind', []):
            continue
        require(value.get('name') == target and value.get('kind') == ['example']
                and value.get('crate_types') == ['bin'] and value.get('test') is False,
                'Exact standalone Cargo target')
        profile = row.get('profile')
        require(type(profile) is dict and profile.get('test') is False
                and profile.get('opt_level') == '3', 'Release non-libtest Cargo profile')
        require(type(row.get('features')) is list and all(type(x) is str for x in row['features'])
                and type(row.get('package_id')) is str and row['package_id'], 'Cargo package/features')
        require(row.get('manifest_path') == str(source / base / 'Cargo.toml')
                and value.get('src_path') == str(source / base / 'examples' / (target + '.rs'))
                and row.get('executable') == str(source / 'target/release/examples' / target),
                'Cargo source/manifest/executable paths')
        matches.append({'kind': kind, 'target': value, 'profile': profile,
            'package_id': row['package_id'], 'features': row['features'],
            'manifest': base + '/Cargo.toml', 'source': base + '/examples/' + target + '.rs',
            'original_binary': 'target/release/examples/' + target})
    require(finished == [True] and len(matches) == 1, 'One successful Cargo build and example')
    return matches[0]


def binary_parts(record, buffers):
    kind = record['kind']
    require(kind in TARGETS and record.get('path') == 'binaries/' + TARGETS[kind][1],
            'Exact exported binary path')
    wanted = described({key: record[key] for key in ('bytes', 'sha256')}, nonempty=True)
    parts = record.get('parts')
    require(type(parts) is list and 0 < len(parts) <= 512, 'Bounded binary parts')
    hasher, total, names = hashlib.sha256(), 0, []
    for index, row in enumerate(parts):
        name = 'parts/' + kind + '.part' + str(index).zfill(4)
        require(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'}
                and row['path'] == name, 'Contiguous ordered binary part paths')
        expected = described({key: row[key] for key in ('bytes', 'sha256')}, BLOCK, True)
        raw = buffers[PREFIX + name]
        require(descriptor(raw) == expected and len(raw) <= BLOCK
                and (index == len(parts) - 1 or len(raw) == BLOCK), 'Exact full binary part bytes')
        names.append(name)
        total += len(raw)
        hasher.update(raw)
    require(total == wanted['bytes'] and hasher.hexdigest() == wanted['sha256'],
            'Reassembled binary byte identity')
    return names


def source_records(snapshot, source_buffers):
    mapping = snapshot.get('source_sha256')
    require(type(mapping) is dict and 0 < len(mapping) <= 10000
            and type(source_buffers) is dict and set(source_buffers) == set(mapping), 'Exact selected source map')
    result, total = {}, 0
    for name, expected in mapping.items():
        relative(name)
        digest(expected)
        raw = source_buffers[name]
        require(type(raw) is bytes and len(raw) <= MAX_METADATA and sha(raw) == expected,
                'Selected source byte identity')
        total += len(raw)
        require(total <= MAX_BINARY, 'Bounded aggregate selected source')
        result[name] = descriptor(raw)
    require(all(mapping.get(name) == value for name, value in PINS.items()), 'Reviewed build/helper pins')
    for _, target, base in TARGETS.values():
        require(base + '/Cargo.toml' in mapping and base + '/examples/' + target + '.rs' in mapping,
                'Both example source/manifest pins')
    return result


def manifest_records(buffers, records):
    manifest = parse(buffers[PREFIX + 'files.sha256.json'])
    require(type(manifest) is dict, 'Build closure object')
    names = {'build.json', 'runtime.json', 'export.json',
             *[label + '/' + name for label in LABELS for name in ('command.json', 'stdout.txt', 'stderr.txt')]}
    for row in records:
        names.add(row['path'])
        names.update(binary_parts(row, buffers))
    require(set(manifest) == names, 'Exact complete remote build closure')
    omitted = {row['path']: {key: row[key] for key in ('sha256', 'bytes')} for row in records}
    for name, value in manifest.items():
        relative(name)
        described(value)
        require(same(value, omitted[name] if name in omitted else descriptor(buffers[PREFIX + name])),
                'Remote build closure byte identity')
    expected_buffers = {PREPARED, PREFIX + 'files.sha256.json',
                        *[PREFIX + name for name in names if name not in omitted]}
    require(set(buffers) == expected_buffers, 'Exact acquired record/part buffers; no failed or extra paths')
    return omitted


def verify_records(buffers, snapshot_raw, release_raw, source_buffers):
    """Check bytes only; successful return is NOT a server/acquisition verdict.

    No positive fixture may be presented as a real Rust build. The eventual
    collector must first bind these exact buffers to actual finished, unique
    workflow observations and successful original UUID-linked transports.
    """
    require(type(buffers) is dict and len(buffers) <= 14 + 2 * 512, 'Remote buffer mapping')
    total = 0
    for name, raw in buffers.items():
        relative(name)
        require(type(raw) is bytes and len(raw) <= MAX_METADATA, 'Bounded acquired record buffer')
        total += len(raw)
        require(total <= 2 * MAX_BINARY + 14 * MAX_METADATA, 'Bounded aggregate acquired records')
    snapshot, release = parse(snapshot_raw), parse(release_raw)
    require(type(snapshot) is dict and type(release) is dict and set(release) == {
        'schema', 'source_revision', 'source_sha256', 'preflight_review_sha256', 'coordinator_release_sha256'},
        'Exact snapshot/release objects')
    require(release['schema'] == 'openmhd.galaxy-driver-build-release.v1'
            and type(snapshot.get('source_revision')) is str
            and re.fullmatch('[0-9a-f]{40}', snapshot['source_revision'])
            and release['source_revision'] == snapshot['source_revision']
            and snapshot.get('dirty_status') == '' and same(release['source_sha256'], snapshot.get('source_sha256')),
            'Exact committed released source')
    for key in ('preflight_review_sha256', 'coordinator_release_sha256'):
        digest(release[key])
    require(type(snapshot.get('upload_sha256')) is dict
            and snapshot['upload_sha256'].get('build_release.json') == sha(release_raw), 'Original release upload pin')
    sources = source_records(snapshot, source_buffers)
    digest(snapshot['source_sha256'].get('reana/remote.py'))
    build_raw, runtime_raw = buffers[PREFIX + 'build.json'], buffers[PREFIX + 'runtime.json']
    build, runtime, prepared = parse(build_raw), parse(runtime_raw), parse(buffers[PREPARED])
    require(type(build) is dict and build.get('schema') == 'openmhd.galaxy-driver-build.v1'
            and build.get('status') == 'complete' and build.get('before_after_identical') is True
            and build.get('active_command') is None and build.get('component_accepted') is False
            and build.get('external_prerequisite_truth_verified') is False
            and build.get('external_terminal_evidence_required') is False
            and type(build.get('test_methods_executed')) is int and build['test_methods_executed'] == 0
            and type(build.get('numerical_cases_executed')) is int and build['numerical_cases_executed'] == 0,
            'Complete nonaccepting build-only record')
    start, finish = utc(build['started_utc']), utc(build['finished_utc'])
    require(finish >= start and build.get('source_revision') == snapshot['source_revision']
            and same(build.get('source_files'), sources) and build.get('snapshot_sha256') == sha(snapshot_raw)
            and build.get('release_sha256') == sha(release_raw), 'Build source/release/time joins')
    require(type(prepared) is dict and prepared.get('snapshot_sha256') == sha(snapshot_raw)
            and prepared.get('bootstrap_file') == 'remote.py'
            and prepared.get('bootstrap_sha256') == snapshot['upload_sha256'].get('remote.py')
            == snapshot['source_sha256'].get('reana/remote.py')
            and prepared.get('source_bootstrap_sha256') == prepared['bootstrap_sha256']
            and type(prepared.get('rustc')) is str and prepared['rustc'].startswith('rustc 1.85.1 '),
            'Prepared runtime/bootstrap/compiler joins')
    require(type(runtime) is dict and runtime.get('schema') == 'openmhd.metadata-runtime.v2'
            and type(runtime.get('optimized')) is int and runtime['optimized'] == 0
            and runtime.get('kind') == 'standalone-example-build-only'
            and runtime.get('image_and_resources_are_declared_labels') is True,
            'Actual unoptimized build-runtime record')
    for key in ('python', 'executable', 'implementation', 'platform'):
        require(type(runtime.get(key)) is str and runtime[key], 'Required actual runtime text')
    require(type(runtime.get('visible_cpus')) is int and runtime['visible_cpus'] > 0,
            'Observed CPU count distinct from declaration')
    job_path = absolute(runtime['job_path'])
    source = str(job_path.parent.parent)
    require(str(job_path) == source + '/reana/galaxy_driver_build.py', 'Actual build-job source path')
    rustc = str(absolute(source).parent / 'runtime/rust/bin/rustc')
    require(same(runtime.get('compiler_selection'), compiler_policy(rustc)), 'Exact pinned compiler selection policy')
    require(same(runtime.get('declared_resources'), {'threads': 4, 'memory': '8Gi', 'command_timeout_seconds': 1800})
            and type(runtime['declared_resources']['threads']) is int
            and type(runtime['declared_resources']['command_timeout_seconds']) is int
            and same(runtime.get('thread_controls'), {'CARGO_BUILD_JOBS': '4', 'RUST_TEST_THREADS': '1',
                'RAYON_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'}),
            'Declared resources and no nested library threads')
    compiler_files = runtime.get('compiler_files')
    require(type(compiler_files) is dict and set(compiler_files) == {'cargo', 'rustc'}, 'Two actual compiler identities')
    for value in compiler_files.values():
        described(value, nonempty=True)
    require(same(build.get('compiler_files'), compiler_files) and build.get('runtime_sha256') == sha(runtime_raw)
            and build.get('prepared_runtime_sha256') == runtime.get('prepared_runtime_sha256')
            == sha(buffers[PREPARED]), 'Initial prepared/runtime/compiler identities')
    links = {'snapshot': sha(snapshot_raw), 'release': sha(release_raw), 'runtime': sha(runtime_raw),
             'runner': PINS['reana/galaxy_driver_build.py'], 'supervisor': PINS['tools/m1_evidence/reana_metadata_job.py'],
             'launcher': PINS['reana/galaxy_test_case.py']}
    receipts = [command_receipt(buffers, label) for label in LABELS]
    require(build.get('command_labels') == list(LABELS) and same(build.get('command_receipts'), receipts),
            'Exact three-command receipt inventory')
    previous = start
    for label in LABELS:
        row = command_record(buffers[PREFIX + label + '/command.json'], label, source, links)
        command_start, command_finish = interval(row)
        require(previous <= command_start <= command_finish <= finish, 'Ordered build/command intervals')
        previous = command_finish
    require(buffers[PREFIX + 'compiler/stdout.txt'].decode('utf-8') == prepared['rustc'],
            'Actual compiler command output equals prepared compiler')
    records = build.get('binaries')
    require(type(records) is list and all(type(row) is dict for row in records)
            and [row.get('kind') for row in records] == ['geometry', 'gravity'],
            'Exact geometry/gravity binary order')
    for row, receipt in zip(records, receipts[1:]):
        actual = cargo_record(buffers[PREFIX + row['kind'] + '/stdout.txt'], row['kind'], source)
        require(all(same(row.get(key), value) for key, value in actual.items())
                and same(row.get('build_receipt'), receipt)
                and row.get('build_command_sha256') == receipt['command']['sha256']
                and row.get('cargo_stdout_sha256') == receipt['stdout']['sha256']
                and row.get('cargo_stderr_sha256') == receipt['stderr']['sha256'],
                'Actual Cargo artifact and final command/stdout/stderr joins')
    exported = parse(buffers[PREFIX + 'export.json'])
    require(same(exported, {'schema': 'openmhd.galaxy-driver-build-export.v1', 'build_sha256': sha(build_raw),
        'binaries': records, 'test_methods_executed': 0, 'numerical_cases_executed': 0, 'component_accepted': False})
        and type(exported['test_methods_executed']) is int and type(exported['numerical_cases_executed']) is int
        and exported['component_accepted'] is False, 'Exact final export/build linkage')
    omitted = manifest_records(buffers, records)
    return {'schema': 'openmhd.galaxy-driver-build-record-check.v1', 'status': 'records_consistent',
            'source_revision': snapshot['source_revision'], 'build_sha256': sha(build_raw),
            'binaries': [{key: row[key] for key in ('kind', 'path', 'sha256', 'bytes')} for row in records],
            'raw_binary_copies_not_downloaded': omitted, 'authoritative_acquisition_verified': False,
            'external_prerequisite_truth_verified': False, 'component_accepted': False,
            'binary_execution_performed': False, 'numerical_cases_executed': 0}
