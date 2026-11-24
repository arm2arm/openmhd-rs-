"""Install unchanged Cargo.lock archives as a Cargo directory source.

Run after the existing REANA source/toolchain bootstrap and before Cargo.
No compiler, build script, crate code or test is executed here. The original
workspace leaf runner can keep its own compiler/thread/environment controls.
Cargo's source-replacement config is published only after crate materialization.
Any later recording failure still fails the workflow before Cargo may run.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tarfile
import tomllib


REGISTRY = 'registry+https://github.com/rust-lang/crates.io-index'
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_EXPANDED = 256 * 1024 * 1024
MAX_FILES = 20000


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def read(path, limit=MAX_ARCHIVE):
    path = path.absolute()
    need(not any(parent.is_symlink() for parent in (path, *path.parents)), 'Unlinked input path')
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
             and before.st_size <= limit, 'Bounded regular input')
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    named = path.stat()
    need(len(raw) == after.st_size <= limit
         and all(getattr(before, name) == getattr(after, name) == getattr(named, name)
                 for name in ('st_dev', 'st_ino', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')),
         'Coherent held input')
    return raw


def safe(name):
    path = PurePosixPath(name)
    need(path.parts and not path.is_absolute() and '..' not in path.parts
         and path.as_posix() == name and '\\' not in name, 'Canonical archive path')
    return path


def crate_members(raw, name, version):
    """Validate the entire authenticated archive before creating its directory."""
    files, seen, size = {}, set(), 0
    prefix = name + '-' + version
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        for member in archive:
            path = safe(member.name.rstrip('/') if member.isdir() else member.name)
            need(path.parts[0] == prefix and path.as_posix() not in seen, 'Exact distinct crate root')
            seen.add(path.as_posix())
            need(len(seen) <= MAX_FILES, 'Crate member bound')
            if member.isdir():
                continue
            need(member.isfile() and len(path.parts) > 1, 'Regular crate members only')
            relative = PurePosixPath(*path.parts[1:]).as_posix()
            need(relative.split('/')[0] != '.cargo-checksum.json', 'Generated Cargo checksum reserved')
            size += member.size
            need(0 <= member.size <= MAX_ARCHIVE and size <= MAX_EXPANDED, 'Expanded crate bound')
            stream = archive.extractfile(member)
            need(stream is not None, 'Crate member stream')
            with stream:
                content = stream.read(member.size + 1)
            need(len(content) == member.size, 'Complete crate member')
            files[relative] = (content, 0o755 if member.mode & 0o111 else 0o644)
    need('Cargo.toml' in files, 'Packaged Cargo manifest')
    package = tomllib.loads(files['Cargo.toml'][0].decode())['package']
    need(package['name'] == name and package['version'] == version, 'Actual packaged crate identity')
    # Reject a file used as another file's directory before any write occurs.
    for name in files:
        need(not any(parent.as_posix() in files for parent in PurePosixPath(name).parents
                     if parent != PurePosixPath('.')), 'Conflicting crate member paths')
    return files


def install(work, bundle_path, expected_digest):
    work, bundle_path = work.resolve(), bundle_path.absolute()
    bundle_raw = read(bundle_path)
    need(sha(bundle_raw) == expected_digest, 'Explicit workflow bundle identity')
    bundle = json.loads(bundle_raw)
    need(bundle['schema'] == 'openmhd.locked-crate-bundle.v1', 'Bundle schema')
    lock_raw = read(work / 'source/Cargo.lock')
    need(sha(lock_raw) == bundle['lock_sha256'], 'Actual frozen source lock')
    lock = tomllib.loads(lock_raw.decode())
    packages = [p for p in lock['package'] if 'source' in p]
    wanted = {}
    for package in packages:
        key = (package['name'], package['version'])
        need(package['source'] == REGISTRY and key not in wanted
             and re.fullmatch('[A-Za-z0-9_-]+', key[0]) is not None
             and re.fullmatch('[A-Za-z0-9.+_-]+', key[1]) is not None
             and re.fullmatch('[0-9a-f]{64}', package['checksum']) is not None,
             'Distinct locked crates.io package')
        wanted[key] = package['checksum']
    need(bundle['package_count'] == len(wanted), 'Complete locked dependency inventory')
    need(type(bundle['archive_bytes']) is int and 0 < bundle['archive_bytes'] <= MAX_ARCHIVE
         and type(bundle['parts']) is list and 0 < len(bundle['parts']) <= 64
         and all(type(part['bytes']) is int and 0 < part['bytes'] <= MAX_ARCHIVE
                 for part in bundle['parts'])
         and sum(part['bytes'] for part in bundle['parts']) == bundle['archive_bytes'],
         'Bounded complete part inventory before reads')
    blocks = []
    for index, part in enumerate(bundle['parts']):
        need(part['path'] == 'locked-crates.part%04d' % index, 'Ordered bundle parts')
        raw = read(bundle_path.parent / part['path'])
        need(len(raw) == part['bytes'] and sha(raw) == part['sha256'], 'Actual bundle part identity')
        blocks.append(raw)
    packed = b''.join(blocks)
    need(len(packed) == bundle['archive_bytes'] <= MAX_ARCHIVE
         and sha(packed) == bundle['archive_sha256'], 'Whole dependency archive')
    contents = {}
    with tarfile.open(fileobj=io.BytesIO(packed), mode='r:') as archive:
        for member in archive:
            safe(member.name)
            need(member.isfile() and member.name not in contents
                 and 0 <= member.size <= MAX_ARCHIVE, 'Regular distinct bundle members')
            stream = archive.extractfile(member)
            with stream:
                contents[member.name] = stream.read(member.size + 1)
            need(len(contents[member.name]) == member.size, 'Whole bundle member')
    need(contents.get('Cargo.lock') == lock_raw, 'Bundle and source lock bytes')
    manifest_raw = contents.get('manifest.json', b'')
    need(sha(manifest_raw) == bundle['manifest_sha256'], 'Dependency manifest identity')
    manifest = json.loads(manifest_raw)
    need(manifest['schema'] == 'openmhd.locked-crate-inputs.v1'
         and manifest['lock_sha256'] == bundle['lock_sha256'], 'Dependency manifest schema/lock')
    actual = {(r['name'], r['version']): r for r in manifest['packages']}
    need(len(actual) == len(manifest['packages']) and set(actual) == set(wanted), 'Exact dependency set')
    need(set(contents) == {'Cargo.lock', 'manifest.json', *[
        'crates/' + name + '-' + version + '.crate' for name, version in wanted]}, 'Closed input archive')
    for key, row in actual.items():
        path = 'crates/' + key[0] + '-' + key[1] + '.crate'
        need(row['source'] == REGISTRY and row['path'] == path
             and row['sha256'] == sha(contents[path]) == wanted[key]
             and row['bytes'] == len(contents[path]), 'Locked package byte/checksum link')
    runtime = work / 'runtime'
    destination = runtime / 'locked-dependencies'
    need(runtime.is_dir() and not runtime.is_symlink() and not destination.exists()
         and not destination.is_symlink(), 'Fresh prepared runtime destination')
    config = runtime / 'cargo/config.toml'
    need(not config.parent.is_symlink() and not config.exists() and not config.is_symlink()
         and not (runtime / 'cargo/config').exists(), 'Fresh Cargo source selection')
    for parent in [work / 'source', *work.parents, work]:
        need(not any((parent / '.cargo' / name).exists() for name in ('config', 'config.toml')),
             'No competing ancestor/source Cargo configuration')
    destination.mkdir()
    status_path = destination / 'status.json'
    status = dict(schema='openmhd.offline-dependency-install.v1', status='installing',
                  started_utc=datetime.now(timezone.utc).isoformat(), bundle_sha256=expected_digest,
                  lock_sha256=sha(lock_raw), package_count=len(wanted), target_executed=False)
    status_path.write_bytes(encode(status))
    try:
        records = []
        for (name, version), checksum in sorted(wanted.items()):
            raw = contents[actual[(name, version)]['path']]
            files = crate_members(raw, name, version)
            root = destination / (name + '-' + version)
            root.mkdir()
            hashes = {}
            for relative, (data, mode) in sorted(files.items()):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('xb') as stream:
                    stream.write(data)
                path.chmod(mode)
                hashes[relative] = sha(read(path))
                need(hashes[relative] == sha(data), 'Installed original crate file')
            checksum_bytes = encode(dict(package=checksum, files=hashes))
            (root / '.cargo-checksum.json').write_bytes(checksum_bytes)
            records.append(dict(name=name, version=version, package_sha256=checksum,
                                checksum_file_sha256=sha(checksum_bytes), files=hashes))
        vendor_config = ('[source.crates-io]\nreplace-with = "locked-inputs"\n'
                         '[source.locked-inputs]\ndirectory = ' + json.dumps(str(destination))
                         + '\n[net]\noffline = true\n').encode()
        install_raw = encode(dict(schema='openmhd.installed-crate-files.v1', packages=records,
                                  config_sha256=sha(vendor_config), bundle_sha256=expected_digest))
        (destination / 'installed.json').write_bytes(install_raw)
        prepared_path = work / 'outputs/runtime.json'
        prepared_raw = read(prepared_path)
        prepared = json.loads(prepared_raw)
        need('offline_dependencies' not in prepared, 'No prior dependency install claim')
        prepared['offline_dependencies'] = dict(bundle_sha256=expected_digest,
            installed_sha256=sha(install_raw), config_sha256=sha(vendor_config), packages=len(records),
            source_lock_sha256=sha(lock_raw), installer_sha256=sha(read(Path(__file__))),
            prior_runtime_sha256=sha(prepared_raw), source_replacement=True, network_offline=True)
        # Cargo cannot see the source replacement until every crate is complete.
        config.parent.mkdir(exist_ok=True)
        with config.open('xb') as stream:
            stream.write(vendor_config)
        prepared_path.write_bytes(encode(prepared))
        status.update(status='complete', installed_sha256=sha(install_raw),
                      config_sha256=sha(vendor_config))
    except BaseException as error:
        status.update(status='failed', error_type=type(error).__name__)
        raise
    finally:
        status['finished_utc'] = datetime.now(timezone.utc).isoformat()
        status_path.write_bytes(encode(status))
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path.cwd())
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(install(args.work, args.bundle, args.sha256)))


if __name__ == '__main__':
    main()
