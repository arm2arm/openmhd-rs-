#!/usr/bin/env python3
"""Build/export the two standalone candidate examples ON REANA, never run them.

Unadopted source proposal. Importing this file has no dynamic target imports,
network access or process launch. External source-preflight release remains a
coordinator decision; a digest of a release is not an attestation of its truth.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

JOB_PATH = 'reana/galaxy_driver_build.py'
NATIVE_PATH = 'reana/galaxy_test_case.py'
NATIVE_SHA = 'b600008f8724920a4fb75b74aa23d0cb94ca6bba56cddeec8c433d8e645cbca5'
SUPERVISOR_PATH = 'tools/m1_evidence/reana_metadata_job.py'
SUPERVISOR_SHA = '8d8a39844b631eb17d46f897bea71ae2464be1e400c75a54dd6c091a1fd2dbc3'
TARGETS = {
    'geometry': ('moving-mesh', 'geometry3-case', 'crates/moving-mesh'),
    'gravity': ('gravity', 'gravity-force-case', 'crates/gravity'),
}
MAX_METADATA = 16 * 1024 * 1024
MAX_BINARY = 512 * 1024 * 1024
PART_BYTES = 1024 * 1024
COMPILER_KEYS = ('RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
                 'CARGO_BUILD_RUSTC', 'CARGO_BUILD_RUSTC_WRAPPER',
                 'CARGO_BUILD_RUSTC_WORKSPACE_WRAPPER')


def require(value, message):
    if not value:
        raise ValueError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()


def parse(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, 'Repeated JSON key')
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def relative(name):
    require(type(name) is str, 'String path required')
    path = PurePosixPath(name)
    require(path.parts and path.as_posix() == name and not path.is_absolute()
            and '..' not in path.parts, 'Unsafe relative path')
    return path


def regular(root, name, maximum=MAX_METADATA):
    """Held-descriptor read, regular bounded input, unchanged metadata and bytes."""
    path = root
    for component in relative(name).parts:
        path /= component
        require(not path.is_symlink(), 'Linked path')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_size <= maximum,
                'Regular bounded file required')
        chunks, total = [], 0
        while True:
            block = os.read(fd, min(PART_BYTES, maximum + 1 - total))
            if not block:
                break
            chunks.append(block)
            total += len(block)
            require(total <= maximum, 'File grew beyond bound')
        after = os.fstat(fd)
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        require(all(getattr(before, key) == getattr(after, key) for key in fields)
                and total == after.st_size, 'Changed held file generation')
        current = path.stat()
        require(all(getattr(current, key) == getattr(after, key) for key in fields),
                'Changed pathname generation')
        return b''.join(chunks)
    finally:
        os.close(fd)


def descriptor(raw):
    return {'sha256': sha(raw), 'bytes': len(raw)}


def source_receipts(source, snapshot):
    mapping = snapshot.get('source_sha256')
    require(type(mapping) is dict and 0 < len(mapping) <= 10000, 'Bounded source inventory')
    rows, total = {}, 0
    for name, expected in sorted(mapping.items()):
        require(type(expected) is str and re.fullmatch(r'[0-9a-f]{64}', expected), 'Source digest')
        raw = regular(source, name)
        total += len(raw)
        require(total <= 512 * 1024 * 1024 and sha(raw) == expected, 'Changed/excessive source inventory')
        rows[name] = descriptor(raw)
    for _, target, base in TARGETS.values():
        require(base + '/Cargo.toml' in rows and base + '/examples/' + target + '.rs' in rows,
                'Example and manifest must belong to snapshot')
    return rows


def compiler_selection(rustc):
    """Only fixed public selections; never retain inherited override values."""
    require(rustc.is_absolute(), 'Absolute pinned compiler required')
    return {key: str(rustc) if key in ('RUSTC', 'CARGO_BUILD_RUSTC') else ''
            for key in COMPILER_KEYS}


def compiler_config(rustc):
    # Cargo at Rust1.85.1's submodule commit: --config overrides config/env,
    # direct RUSTC* environment has its own selection path. Fix BOTH routes.
    selection = compiler_selection(rustc)
    values = [('build.rustc', json.dumps(str(rustc))),
              ('build.rustc-wrapper', '""'), ('build.rustc-workspace-wrapper', '""')]
    # A config [env] force entry must not reintroduce a different selection in
    # child/build-script environments or recursive Cargo. Override only these
    # six public keys, without reading or publishing any config/secret values.
    values += [('env.' + key, '{value=' + json.dumps(value) + ',force=true,relative=false}')
               for key, value in selection.items()]
    return [item for key, value in values for item in ('--config', key + '=' + value)]


def build_environment(cargo, rustc, inherited):
    environment = dict(inherited)
    environment.update(PATH=str(cargo.parent) + os.pathsep + environment.get('PATH', ''),
                       CARGO_HOME=str(cargo.parents[2] / 'cargo'), CARGO_BUILD_JOBS='4',
                       RUST_TEST_THREADS='1', RAYON_NUM_THREADS='1', OMP_NUM_THREADS='1',
                       OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    environment.update(compiler_selection(rustc))
    return environment


def build_argv(cargo, kind, jobs, rustc=None):
    require(kind in TARGETS and type(jobs) is int and jobs == 4, 'Explicit driver and four build jobs')
    cargo = Path(cargo)
    rustc = cargo.parent / 'rustc' if rustc is None else rustc
    package, target, _ = TARGETS[kind]
    return [str(cargo), 'build', '--release', '--package', package, '--example', target,
            '--all-features', '--locked', '--message-format=json', '--jobs', str(jobs),
            *compiler_config(rustc)]


def artifact_metadata(raw, source, kind, files):
    """Interpret actual Cargo JSON; no binary is executed or test harness accepted."""
    require(type(raw) is bytes and len(raw) <= MAX_METADATA and kind in TARGETS,
            'Bounded Cargo metadata')
    _, wanted, base = TARGETS[kind]
    found, finished = [], []
    for line in raw.decode('utf-8').splitlines():
        if not line.startswith('{'):
            continue  # Cargo can interleave non-JSON tool output.
        row = parse(line)
        require(type(row) is dict, 'Cargo object')
        if row.get('reason') == 'build-finished':
            require(type(row.get('success')) is bool, 'Cargo completion boolean')
            finished.append(row['success'])
        if row.get('reason') != 'compiler-artifact':
            continue
        target = row.get('target', {})
        require(type(target) is dict, 'Cargo target object')
        if 'example' not in target.get('kind', []):
            continue
        require(target.get('kind') == ['example'] and target.get('crate_types') == ['bin']
                and target.get('name') == wanted and target.get('test') is False,
                'Exact standalone example target')
        profile = row.get('profile')
        require(type(profile) is dict and profile.get('test') is False
                and profile.get('opt_level') == '3', 'Release non-libtest compiler artifact')
        require(type(row.get('features')) is list and all(type(x) is str for x in row['features'])
                and type(row.get('package_id')) is str and bool(row['package_id']), 'Cargo package/features')
        paths = {'manifest': source / base / 'Cargo.toml',
                 'source': source / base / 'examples' / (wanted + '.rs')}
        require(row.get('manifest_path') == str(paths['manifest'])
                and target.get('src_path') == str(paths['source']), 'Exact Cargo source/manifest paths')
        require(all(path.relative_to(source).as_posix() in files for path in paths.values()),
                'Cargo source belongs to original snapshot')
        executable = row.get('executable')
        require(type(executable) is str, 'Actual executable required')
        binary = Path(executable)
        require(binary.is_absolute() and binary == binary.resolve()
                and binary.parent == source / 'target/release/examples'
                and binary.name == wanted and not binary.is_symlink(), 'Canonical example executable')
        found.append({'kind': kind, 'target': target, 'profile': profile,
                      'package_id': row['package_id'], 'features': row['features'],
                      'manifest': paths['manifest'].relative_to(source).as_posix(),
                      'source': paths['source'].relative_to(source).as_posix(),
                      'original_binary': binary.relative_to(source).as_posix()})
    require(finished == [True] and len(found) == 1, 'Unique successful Cargo build and example')
    return found[0]


def export_binary(source, record, output):
    """Export unchanged opaque executable bytes and one-MiB transfer parts."""
    raw = regular(source, record['original_binary'], MAX_BINARY)
    require(raw and len(raw) <= MAX_BINARY, 'Nonempty bounded executable')
    path = output / 'binaries' / TARGETS[record['kind']][1]
    path.parent.mkdir(exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)
    path.chmod(0o755)
    require(regular(output, path.relative_to(output).as_posix(), MAX_BINARY) == raw
            and regular(source, record['original_binary'], MAX_BINARY) == raw,
            'Binary changed during export')
    parts = []
    for index, start in enumerate(range(0, len(raw), PART_BYTES)):
        name = 'parts/' + record['kind'] + '.part' + str(index).zfill(4)
        target = output / name
        target.parent.mkdir(exist_ok=True)
        block = raw[start:start + PART_BYTES]
        with target.open('xb') as stream:
            stream.write(block)
        require(regular(output, name) == block, 'Changed exported part')
        parts.append({'path': name, **descriptor(block)})
    return {**record, 'path': path.relative_to(output).as_posix(), **descriptor(raw), 'parts': parts}



def verify_export(source, output, record):
    """Final fence after BOTH builds: originals, copied binary and all parts."""
    wanted = {'sha256': record['sha256'], 'bytes': record['bytes']}
    require(descriptor(regular(source, record['original_binary'], MAX_BINARY)) == wanted,
            'Original binary changed after build/export')
    require(descriptor(regular(output, record['path'], MAX_BINARY)) == wanted,
            'Copied binary changed after export')
    require(type(record['parts']) is list and 0 < len(record['parts']) <= 512,
            'Bounded final part inventory')
    total, digest = 0, hashlib.sha256()
    for index, row in enumerate(record['parts']):
        require(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'}
                and row['path'] == 'parts/' + record['kind'] + '.part' + str(index).zfill(4),
                'Ordered final part path')
        block = regular(output, row['path'], PART_BYTES)
        require(type(row['bytes']) is int and 0 < row['bytes'] <= PART_BYTES
                and descriptor(block) == {'bytes': row['bytes'], 'sha256': row['sha256']},
                'Exported part changed after export')
        require(index == len(record['parts']) - 1 or len(block) == PART_BYTES,
                'Nonfinal part must fill transfer block')
        total += len(block)
        digest.update(block)
    require(total == wanted['bytes'] and digest.hexdigest() == wanted['sha256'],
            'Final parts do not reassemble the actual exported binary')


def load_pinned(source, path, expected, name):
    raw = regular(source, path)
    require(sha(raw) == expected, 'Pinned helper source')
    spec = importlib.util.spec_from_file_location(name, source / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(regular(source, path) == raw, 'Changed imported helper')
    return module


def generation_fence(source, snapshot_path, snapshot_raw, release_path, release_raw,
                     work, prepared_runtime_raw, snapshot, before, compiler_files,
                     output, observation_raw):
    """Discrete settled-command/final fences, not continuous immutability."""
    require(source_receipts(source, snapshot) == before
            and regular(snapshot_path.parent, snapshot_path.name) == snapshot_raw
            and regular(release_path.parent, release_path.name) == release_raw
            and regular(work / 'outputs', 'runtime.json') == prepared_runtime_raw,
            'Original source/snapshot/release/runtime fence')
    require(compiler_files == {name: descriptor(regular(work, 'runtime/rust/bin/' + name, MAX_BINARY))
                               for name in ('cargo', 'rustc')}, 'Compiler bytes unchanged')
    require(regular(output, 'runtime.json') == observation_raw,
            'Initial build runtime changed before final attribution')


def command_receipt(output, label, argv, source, seconds, links, supervisor):
    destination = output / label
    require({p.name for p in destination.iterdir()} == {'command.json', 'stdout.txt', 'stderr.txt'},
            'Exact settled command/log inventory')
    raw = {name: regular(destination, name) for name in ('command.json', 'stdout.txt', 'stderr.txt')}
    command = parse(raw['command.json'])
    cleanup = command.get('cleanup', {})
    require(command.get('schema') == 'openmhd.metadata-command.v1'
            and command.get('outcome') == 'success' and type(command.get('returncode')) is int
            and command['returncode'] == 0 and command.get('external_terminal_evidence_required') is False
            and cleanup.get('writers_settled') is True and cleanup.get('direct_child_reaped') is True
            and cleanup.get('leader_held_until_group_close') is True
            and cleanup.get('group_authority_lost') is False and cleanup.get('remaining_live_pids') == [],
            'Successful supervised build and closed writers')
    require(command.get('command') == argv and command.get('cwd') == str(source)
            and type(command.get('timeout_seconds')) is int and command['timeout_seconds'] == seconds
            and command.get('timeout_scope') == 'direct-child-wait' and command.get('links') == links,
            'Exact settled build argv/cwd/timeout/links')
    supervisor.interval(command)
    return {'label': label, **{name.removesuffix('.json').removesuffix('.txt'):
            {'path': label + '/' + name, **descriptor(body)} for name, body in raw.items()}}


def verify_command_links(source, output, commands, links, supervisor, report, receipts):
    labels = ['compiler', 'geometry', 'gravity']
    require([row[0] for row in commands] == report['command_labels'] == labels
            and [row['label'] for row in receipts] == labels
            and encode(report['command_receipts']) == encode(receipts),
            'Exact compiler/geometry/gravity command coverage')
    actual = [command_receipt(output, label, argv, source, seconds, links, supervisor)
              for label, argv, seconds in commands]
    require(encode(actual) == encode(receipts), 'Settled command/stdout/stderr identities changed')
    require([row['kind'] for row in report['binaries']] == ['geometry', 'gravity'],
            'Exact two exported build records')
    for record, receipt in zip(report['binaries'], receipts[1:]):
        require(encode(record['build_receipt']) == encode(receipt)
                and record['build_command_sha256'] == receipt['command']['sha256']
                and record['cargo_stdout_sha256'] == receipt['stdout']['sha256']
                and record['cargo_stderr_sha256'] == receipt['stderr']['sha256'],
                'Export record contradicts final actual Cargo command/log receipt')


def output_inventory(output):
    rows = {}
    for path in sorted(output.rglob('*')):
        require(not path.is_symlink(), 'Linked output entry')
        if path.is_file() and path != output / 'files.sha256.json':
            name = path.relative_to(output).as_posix()
            rows[name] = descriptor(regular(output, name, MAX_BINARY))
        else:
            require(path.is_dir() or path == output / 'files.sha256.json', 'Special output entry')
    return rows


def close_output(output, native):
    rows = output_inventory(output)
    native.persist(output / 'files.sha256.json', rows)
    require(regular(output, 'files.sha256.json') == encode(rows) == encode(output_inventory(output)),
            'Changed final build closure')


def retain_failure(output, report, native, error):
    report.update(status='failed', finished_utc=now(), error_type=type(error).__name__,
                  external_terminal_evidence_required=True, component_accepted=False)
    # A closure/log hash on failure is forensic, never a writer-closure claim.
    # Preserve original success-view bytes while preventing their promotion.
    try:
        if native is None:
            (output / 'build.json').write_bytes(encode(report))
        else:
            native.persist(output / 'build.json', report)
    except BaseException:
        # Storage/interpreter loss can prevent even failure publication. Keep
        # the original exception; external command/status/log evidence required.
        pass
    for name, failed in (('files.sha256.json', 'files.failed.sha256.json'),
                         ('export.json', 'export.failed.json')):
        try:
            path = output / name
            if path.exists():
                path.rename(output / failed)
        except BaseException:
            pass
    if native is not None:
        try:
            close_output(output, native)
        except BaseException:
            pass


def publish_complete(output, report, native):
    """Internal publication phase, not a standalone successful-build verifier."""
    try:
        native.persist(output / 'build.json', report)
        native.persist(output / 'export.json', {'schema': 'openmhd.galaxy-driver-build-export.v1',
            'build_sha256': sha(regular(output, 'build.json')), 'binaries': report['binaries'],
            'test_methods_executed': 0, 'numerical_cases_executed': 0, 'component_accepted': False})
        close_output(output, native)
    except BaseException as error:
        retain_failure(output, report, native, error)
        raise


def run(source, snapshot_path, release_path, output):
    require(__debug__ and sys.flags.optimize == 0, 'Optimized driver build rejected')
    require(not output.exists() and source.is_absolute() and source == source.resolve(), 'Fresh output/canonical source')
    # These digest references are a coordinator release boundary, not a pass bit
    # or an authenticated receipt. The caller must inspect the named real prior
    # outputs before constructing this input; this job does not certify them.
    snapshot_raw = regular(snapshot_path.parent, snapshot_path.name)
    release_raw = regular(release_path.parent, release_path.name)
    snapshot, release = parse(snapshot_raw), parse(release_raw)
    require(type(release) is dict and set(release) == {'schema', 'source_revision',
            'source_sha256', 'preflight_review_sha256', 'coordinator_release_sha256'}, 'Build release schema')
    require(release['schema'] == 'openmhd.galaxy-driver-build-release.v1'
            and release['source_revision'] == snapshot['source_revision']
            and release['source_sha256'] == snapshot['source_sha256'], 'Exact released source generation')
    require(all(type(release[key]) is str and re.fullmatch(r'[0-9a-f]{64}', release[key])
                for key in ('preflight_review_sha256', 'coordinator_release_sha256')), 'Release receipt identities')
    before = source_receipts(source, snapshot)
    require(before.get(JOB_PATH) == descriptor(Path(__file__).read_bytes()), 'Build job snapshot pin')
    require(before.get(NATIVE_PATH, {}).get('sha256') == NATIVE_SHA
            and before.get(SUPERVISOR_PATH, {}).get('sha256') == SUPERVISOR_SHA, 'Reviewed launch helpers')
    output.mkdir(parents=True)
    report = {'schema': 'openmhd.galaxy-driver-build.v1', 'status': 'preparing',
              'started_utc': now(), 'source_revision': snapshot['source_revision'],
              'snapshot_sha256': sha(snapshot_raw), 'release_sha256': sha(release_raw),
              'source_files': before, 'binaries': [], 'command_labels': [], 'command_receipts': [],
              'test_methods_executed': 0, 'numerical_cases_executed': 0,
              'external_prerequisite_truth_verified': False, 'component_accepted': False}
    native = None
    try:
        native = load_pinned(source, NATIVE_PATH, NATIVE_SHA, 'driver_build_native')
        supervisor = load_pinned(source, SUPERVISOR_PATH, SUPERVISOR_SHA, 'driver_build_supervisor')
        native.persist(output / 'build.json', report)
        work = source.parent
        runtime_raw = regular(work / 'outputs', 'runtime.json')
        runtime = parse(runtime_raw)
        require(runtime['snapshot_sha256'] == sha(snapshot_raw)
                and runtime['bootstrap_file'] == 'remote.py'
                and runtime['bootstrap_sha256'] == snapshot['upload_sha256']['remote.py']
                == snapshot['source_sha256']['reana/remote.py']
                and runtime['rustc'].startswith('rustc 1.85.1 '), 'Actual prepared compiler/runtime links')
        cargo = work / 'runtime/rust/bin/cargo'
        rustc = work / 'runtime/rust/bin/rustc'
        compiler_files = {name: descriptor(regular(work, 'runtime/rust/bin/' + name, MAX_BINARY))
                          for name in ('cargo', 'rustc')}
        environment = build_environment(cargo, rustc, os.environ)
        observation = supervisor.runtime_record(work, Path(__file__).resolve())
        observation.update(declared_resources={'threads': 4, 'memory': '8Gi', 'command_timeout_seconds': 1800},
                           kind='standalone-example-build-only', compiler_files=compiler_files,
                           compiler_selection={'schema': 'openmhd.galaxy-compiler-selection.v1',
                               'environment': compiler_selection(rustc),
                               'cargo_config_argv': compiler_config(rustc),
                               'inherited_override_values_retained': False},
                           prepared_runtime_sha256=sha(runtime_raw), thread_controls={key: environment[key]
                           for key in ('CARGO_BUILD_JOBS', 'RUST_TEST_THREADS', 'RAYON_NUM_THREADS',
                                       'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')})
        native.persist(output / 'runtime.json', observation)
        observation_raw = encode(observation)
        require(regular(output, 'runtime.json') == observation_raw, 'Initial build runtime publication')
        links = {'snapshot': sha(snapshot_raw), 'release': sha(release_raw),
                 'runtime': sha(observation_raw), 'runner': before[JOB_PATH]['sha256'],
                 'supervisor': SUPERVISOR_SHA, 'launcher': NATIVE_SHA}
        commands = [('compiler', [str(rustc), '-Vv'], 60)] + [
            (kind, build_argv(cargo, kind, 4, rustc), 1800) for kind in TARGETS]
        receipts = []
        for label, argv, seconds in commands:
            destination = output / label
            destination.mkdir()
            report.update(status='building', active_command=label)
            native.persist(output / 'build.json', report)
            command = native.launch_native(supervisor, argv, source, environment,
                                           destination, seconds, links)
            require(regular(destination, 'command.json') == encode(command), 'Actual returned/persisted command identity')
            receipt = command_receipt(output, label, argv, source, seconds, links, supervisor)
            generation_fence(source, snapshot_path, snapshot_raw, release_path, release_raw,
                             work, runtime_raw, snapshot, before, compiler_files, output, observation_raw)
            stdout = regular(destination, 'stdout.txt')
            require(descriptor(stdout) == {key: receipt['stdout'][key] for key in ('sha256', 'bytes')},
                    'Cargo/compiler stdout changed before artifact attribution')
            if label == 'compiler':
                require(stdout.decode('utf-8') == runtime['rustc'], 'Actual compiler output matches preparation')
            else:
                record = artifact_metadata(stdout, source, label, before)
                record['build_command_sha256'] = receipt['command']['sha256']
                record['cargo_stdout_sha256'] = receipt['stdout']['sha256']
                record['cargo_stderr_sha256'] = receipt['stderr']['sha256']
                record['build_receipt'] = parse(encode(receipt))
                report['binaries'].append(export_binary(source, record, output))
            report['command_labels'].append(label)
            receipts.append(receipt)
            report['command_receipts'] = parse(encode(receipts))
        for exported in report['binaries']:
            verify_export(source, output, exported)
        generation_fence(source, snapshot_path, snapshot_raw, release_path, release_raw,
                         work, runtime_raw, snapshot, before, compiler_files, output, observation_raw)
        verify_command_links(source, output, commands, links, supervisor, report, receipts)
        report.update(status='complete', finished_utc=now(), active_command=None,
                      before_after_identical=True, prepared_runtime_sha256=sha(runtime_raw),
                      compiler_files=compiler_files, runtime_sha256=sha(observation_raw),
                      external_terminal_evidence_required=False)
        publish_complete(output, report, native)
        # Recheck the original evidence AFTER closure construction, so a late
        # re-inventory cannot silently reseal changed runtime/command/log bytes.
        generation_fence(source, snapshot_path, snapshot_raw, release_path, release_raw,
                         work, runtime_raw, snapshot, before, compiler_files, output, observation_raw)
        verify_command_links(source, output, commands, links, supervisor, report, receipts)
        for exported in report['binaries']:
            verify_export(source, output, exported)
        require(regular(output, 'build.json') == encode(report), 'Final build report changed')
        require(regular(output, 'export.json') == encode({'schema': 'openmhd.galaxy-driver-build-export.v1',
                'build_sha256': sha(encode(report)), 'binaries': report['binaries'],
                'test_methods_executed': 0, 'numerical_cases_executed': 0, 'component_accepted': False}),
                'Final export/build linkage changed')
        require(regular(output, 'files.sha256.json') == encode(output_inventory(output)), 'Final closure changed')
    except BaseException as error:
        if report['status'] != 'failed':
            retain_failure(output, report, native, error)
        raise
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.source.absolute(), args.snapshot.absolute(), args.release.absolute(), args.output.absolute())


if __name__ == '__main__':
    main()
