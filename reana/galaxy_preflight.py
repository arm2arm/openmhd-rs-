#!/usr/bin/env python3
"""Compile and list frozen Rust test leaves on REANA; execute no test method.

The ordinary pinned remote.py bootstrap owns Rust installation and the preceding
format/strict-Clippy/release-build gates. This exports debug/release libtest
executables and exact selectors for subsequent one-leaf-per-workflow execution.
Source/API references: Cargo JSON compiler-artifact/build-finished messages and
the rustc libtest --list contract (see docs/galaxy/REANA_IMPLEMENTATION_GATES.md).
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import time


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def source_receipts(source, snapshot):
    expected = snapshot['source_sha256']
    if not isinstance(expected, dict) or not expected:
        raise ValueError('Missing nonempty source inventory')
    for name, wanted in expected.items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Unsafe source inventory path')
        actual = source / path
        if actual.resolve() != actual or not actual.is_file() or digest(actual) != wanted:
            raise ValueError('Changed frozen source: ' + name)
    return {name: {'sha256': wanted, 'bytes': (source / name).stat().st_size}
            for name, wanted in sorted(expected.items())}


def execute(argv, source, output, journal, label, seconds):
    """Retain failed command bytes; never turn a timeout into passing evidence."""
    stdout = output / (label + '.stdout')
    stderr = output / (label + '.stderr')
    row = {'label': label, 'argv': argv, 'cwd': str(source),
           'started_utc': now(), 'status': 'running', 'returncode': None,
           'timeout_seconds': seconds, 'stdout': stdout.name, 'stderr': stderr.name}
    journal.append(row)
    write_json(output / 'commands.json', journal)
    start = time.monotonic()
    try:
        with stdout.open('wb') as out, stderr.open('wb') as err:
            result = subprocess.run(argv, cwd=source, stdout=out, stderr=err,
                                    timeout=seconds, check=False)
        row.update(status='complete' if result.returncode == 0 else 'failed',
                   returncode=result.returncode)
    except BaseException as error:
        row.update(status='interrupted_or_failed', error_type=type(error).__name__,
                   external_terminal_evidence_required=True)
        raise
    finally:
        row.update(finished_utc=now(), seconds=time.monotonic() - start)
        for channel, path in (('stdout', stdout), ('stderr', stderr)):
            if path.is_file():
                row[channel + '_sha256'] = digest(path)
                row[channel + '_bytes'] = path.stat().st_size
        write_json(output / 'commands.json', journal)
    if row['returncode'] != 0:
        raise RuntimeError('Command failed: ' + label)
    return stdout


def compiler_artifacts(path, source):
    artifacts = {}
    finished = []
    for line in path.read_text().splitlines():
        if not line.startswith('{'):
            continue  # Cargo documents possible non-JSON tool output.
        value = json.loads(line)
        if value.get('reason') == 'build-finished':
            finished.append(value.get('success'))
        if value.get('reason') != 'compiler-artifact':
            continue
        if value.get('profile', {}).get('test') is not True:
            continue
        executable = value.get('executable')
        if executable is None:
            continue
        target = value['target']
        binary = Path(executable)
        manifest = Path(value['manifest_path'])
        src = Path(target['src_path'])
        # No generated executable or manifest from outside the frozen source.
        manifest_name = str(manifest.relative_to(source))
        src_name = str(src.relative_to(source))
        binary.relative_to(source / 'target')
        if binary.is_symlink() or not binary.is_file():
            raise ValueError('Missing/linked test executable')
        if binary.resolve() != binary or manifest.resolve() != manifest or src.resolve() != src:
            raise ValueError('Noncanonical compiler artifact path')
        identity = (manifest_name, tuple(target['kind']), target['name'], src_name)
        if identity in artifacts:
            raise ValueError('Duplicate test target identity')
        artifacts[identity] = {'binary': binary, 'package_id': value['package_id'],
                               'manifest': manifest_name, 'target': target,
                               'source': src_name, 'profile': value['profile'],
                               'features': value['features']}
    if finished != [True] or not artifacts:
        raise ValueError('Missing unique successful Cargo build or test binaries')
    return [artifacts[key] for key in sorted(artifacts)]


def test_names(path):
    names = []
    for line in path.read_text().splitlines():
        if not line:
            continue
        match = re.fullmatch(r'([A-Za-z_][A-Za-z_0-9:]*)' + r': test', line)
        if match is None:
            raise ValueError('Unsupported libtest listing line: ' + line)
        names.append(match.group(1))
    if len(names) != len(set(names)):
        raise ValueError('Repeated libtest selector')
    return names


def compile_and_list(source, snapshot_path, output, jobs):
    if output.exists():
        raise ValueError('Preflight output must be fresh')
    if not 1 <= jobs <= 24:
        raise ValueError('Explicit build jobs must be in 1..24')
    snapshot_raw = snapshot_path.read_bytes()
    snapshot = json.loads(snapshot_raw)
    before = source_receipts(source, snapshot)
    if before.get('reana/galaxy_preflight.py', {}).get('sha256') != digest(Path(__file__)):
        raise ValueError('Preflight source is not pinned by snapshot')
    output.mkdir(parents=True)
    journal = []
    report = {'schema': 'openmhd.galaxy-rust-preflight.v1', 'status': 'running',
              'started_utc': now(), 'snapshot_sha256': hashlib.sha256(snapshot_raw).hexdigest(),
              'source_revision': snapshot['source_revision'], 'jobs': jobs,
              'test_methods_executed': 0, 'component_accepted': False,
              'visible_cpus': os.cpu_count(),
              'thread_controls': {name: os.environ.get(name) for name in
                                  ('CARGO_BUILD_JOBS', 'RUST_TEST_THREADS', 'RAYON_NUM_THREADS',
                                   'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')},
              'tests': [], 'binaries': [], 'source_files': before}
    write_json(output / 'preflight.json', report)
    try:
        for profile in ('debug', 'release'):
            command = ['cargo', 'test', '--workspace', '--all-targets', '--all-features',
                       '--locked', '--no-run', '--message-format=json', '--jobs', str(jobs)]
            if profile == 'release':
                command.append('--release')
            cargo_log = execute(command, source, output, journal, profile + '-compile', 1800)
            artifacts = compiler_artifacts(cargo_log, source)
            for number, artifact in enumerate(artifacts):
                binary = artifact.pop('binary')
                prefix = profile + '-' + str(number).zfill(4)
                listing = execute([str(binary), '--list', '--format', 'terse'], source,
                                  output, journal, prefix + '-list', 60)
                ignored = execute([str(binary), '--list', '--ignored', '--format', 'terse'],
                                  source, output, journal, prefix + '-ignored-list', 60)
                names = test_names(listing)
                if test_names(ignored):
                    raise ValueError('Ignored tests require explicit disposition before release')
                if artifact['manifest'] not in before or artifact['source'] not in before:
                    raise ValueError('Test target source/manifest missing from snapshot')
                relative = Path('binaries') / profile / binary.name
                copied = output / relative
                copied.parent.mkdir(parents=True, exist_ok=True)
                if copied.exists():
                    raise ValueError('Test executable export collision')
                original_hash = digest(binary)
                shutil.copyfile(binary, copied)
                copied.chmod(0o755)
                if digest(copied) != original_hash or digest(binary) != original_hash:
                    raise ValueError('Changed executable while exporting')
                record = {**artifact, 'build_profile': profile, 'path': relative.as_posix(),
                          'sha256': original_hash, 'bytes': copied.stat().st_size,
                          'list_label': prefix + '-list', 'selectors': names}
                report['binaries'].append(record)
                for name in names:
                    report['tests'].append({'build_profile': profile,
                                            'manifest': artifact['manifest'],
                                            'target_kind': artifact['target']['kind'],
                                            'target_name': artifact['target']['name'],
                                            'source': artifact['source'], 'selector': name,
                                            'binary': relative.as_posix(),
                                            'binary_sha256': original_hash})
        if not report['tests']:
            raise ValueError('No compiled test selectors')
        after = source_receipts(source, snapshot)
        if after != before or snapshot_path.read_bytes() != snapshot_raw:
            raise ValueError('Frozen source/snapshot changed during preflight')
        report.update(status='complete', finished_utc=now(),
                      compiled_binaries=len(report['binaries']), resolved_leaves=len(report['tests']),
                      before_after_source_identical=True)
        write_json(output / 'preflight.json', report)
        # Compact export is suitable for subsequent checksum-verified case inputs.
        archive = output / 'test-binaries.tar.gz'
        with tarfile.open(archive, 'w:gz') as stream:
            stream.add(output / 'preflight.json', arcname='preflight.json', recursive=False)
            for record in report['binaries']:
                stream.add(output / record['path'], arcname=record['path'], recursive=False)
        # Transfer only fixed-size regular parts over the bounded read-only API.
        # The original archive remains retained and separately hashed.
        parts = []
        with archive.open('rb') as stream:
            while True:
                block = stream.read(1024 * 1024)
                if not block:
                    break
                if len(parts) >= 4096:
                    raise ValueError('Export exceeds explicit 4-GiB transfer bound')
                name = 'export.part' + str(len(parts)).zfill(4)
                (output / name).write_bytes(block)
                parts.append({'path': name, 'sha256': digest(output / name), 'bytes': len(block)})
        write_json(output / 'export.json', {
            'schema': 'openmhd.galaxy-rust-preflight-export.v1',
            'snapshot_sha256': report['snapshot_sha256'],
            'preflight_sha256': digest(output / 'preflight.json'),
            'archive_sha256': digest(archive), 'archive_bytes': archive.stat().st_size,
            'parts': parts,
            'members': {'preflight.json': {'sha256': digest(output / 'preflight.json'),
                                         'bytes': (output / 'preflight.json').stat().st_size},
                        **{r['path']: {'sha256': r['sha256'], 'bytes': r['bytes']} for r in report['binaries']}},
            'test_methods_executed': 0, 'component_accepted': False})
    except BaseException as error:
        report.update(status='failed', finished_utc=now(), error_type=type(error).__name__,
                      error=str(error), component_accepted=False)
        write_json(output / 'preflight.json', report)
        raise
    finally:
        write_json(output / 'sha256.json', {
            str(path.relative_to(output)): {'sha256': digest(path), 'bytes': path.stat().st_size}
            for path in sorted(output.rglob('*')) if path.is_file() and path.name != 'sha256.json'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--jobs', type=int, required=True)
    args = parser.parse_args()
    compile_and_list(args.source.resolve(), args.snapshot.resolve(), args.output.resolve(), args.jobs)


if __name__ == '__main__':
    main()
