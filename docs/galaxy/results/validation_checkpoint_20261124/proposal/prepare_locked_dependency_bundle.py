"""Acquire exact Cargo.lock registry archives; do not build or execute crates.

This operator preparation is separate from the active original workflows.
Every attempt and failed partial stays in this fresh destination. The output
is an input candidate, not a successful offline Cargo gate.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import time
import tomllib
import urllib.error
import urllib.request


REGISTRY = 'registry+https://github.com/rust-lang/crates.io-index'
MAX_CRATE = 64 * 1024 * 1024
PART = 3 * 1024 * 1024


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def write(path, value):
    path.write_bytes(encoded(value))


def fetch(output, package):
    name, version, checksum = (package[n] for n in ('name', 'version', 'checksum'))
    filename = name + '-' + version + '.crate'
    destination = output / 'crates' / filename
    url = 'https://static.crates.io/crates/' + name + '/' + filename
    attempt_root = output / 'transports' / (name + '-' + version)
    attempt_root.mkdir()
    for index in range(1, 4):
        receipt = attempt_root / ('attempt%02d.json' % index)
        partial = attempt_root / ('attempt%02d.body.partial' % index)
        row = dict(schema='openmhd.locked-crate-transport.v1', url=url,
                   started_utc=now(), finished_utc=None, outcome='pending',
                   expected_sha256=checksum, timeout_seconds=15,
                   checkpoint_deadline_seconds=90, retained_bytes=0)
        write(receipt, row)
        started = time.monotonic()
        try:
            with urllib.request.urlopen(url, timeout=15) as response, partial.open('xb') as stream:
                if response.status != 200 or response.url != url:
                    raise ValueError('Unexpected crate response origin/status')
                while True:
                    if time.monotonic() - started > 90:
                        raise TimeoutError('Crate transfer deadline')
                    block = response.read(64 * 1024)
                    if not block:
                        break
                    row['retained_bytes'] += len(block)
                    if row['retained_bytes'] > MAX_CRATE:
                        raise ValueError('Crate size bound')
                    stream.write(block)
            raw = partial.read_bytes()
            if sha(raw) != checksum:
                raise ValueError('Cargo.lock crate checksum mismatch')
            partial.rename(destination)
            row.update(outcome='success', sha256=sha(raw), bytes=len(raw))
            return dict(name=name, version=version, source=REGISTRY,
                        sha256=checksum, bytes=len(raw), path='crates/' + filename,
                        successful_attempt=str(receipt.relative_to(output)))
        except (OSError, urllib.error.URLError) as error:
            row.update(outcome='transport_error', error_type=type(error).__name__)
            if index == 3:
                raise
        except BaseException as error:
            row.update(outcome='rejected', error_type=type(error).__name__)
            raise
        finally:
            if partial.exists():
                row.update(partial_sha256=sha(partial.read_bytes()), partial_bytes=partial.stat().st_size)
            row.update(finished_utc=now(), duration_seconds=time.monotonic() - started)
            write(receipt, row)
    raise RuntimeError('Unreachable transport state')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--lock', type=Path, required=True)
    parser.add_argument('--lock-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = args.lock.read_bytes()
    if sha(raw) != args.lock_sha256:
        raise ValueError('Frozen scientific Cargo.lock identity')
    lock = tomllib.loads(raw.decode())
    packages = [p for p in lock['package'] if 'source' in p]
    identities = set()
    for package in packages:
        key = (package['name'], package['version'])
        if (package['source'] != REGISTRY or key in identities
                or not re.fullmatch('[A-Za-z0-9_-]+', key[0])
                or not re.fullmatch('[A-Za-z0-9.+_-]+', key[1])
                or not re.fullmatch('[0-9a-f]{64}', package.get('checksum', ''))):
            raise ValueError('Exact distinct crates.io lock package')
        identities.add(key)
    args.output.mkdir(parents=True, exist_ok=False)
    output = args.output.resolve()
    (output / 'crates').mkdir()
    (output / 'transports').mkdir()
    (output / 'Cargo.lock').write_bytes(raw)
    status = dict(schema='openmhd.locked-dependency-preparation.v1', status='collecting',
                  started_utc=now(), finished_utc=None, lock_sha256=sha(raw),
                  script_sha256=sha(Path(__file__).read_bytes()), package_count=len(packages),
                  target_executed=False, cargo_offline_validated=False)
    write(output / 'status.json', status)
    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            rows = list(executor.map(lambda p: fetch(output, p), packages))
        manifest = dict(schema='openmhd.locked-crate-inputs.v1', lock_sha256=sha(raw),
                        packages=sorted(rows, key=lambda r: (r['name'], r['version'])))
        write(output / 'manifest.json', manifest)
        archive = output / 'locked-crates.tar'
        with tarfile.open(archive, 'x', format=tarfile.USTAR_FORMAT) as tar:
            for name in ['Cargo.lock', 'manifest.json', *[r['path'] for r in manifest['packages']]]:
                content = (output / name).read_bytes()
                info = tarfile.TarInfo(name)
                info.size, info.mode, info.mtime = len(content), 0o644, 0
                tar.addfile(info, io.BytesIO(content))
        parts = []
        with archive.open('rb') as stream:
            index = 0
            while True:
                block = stream.read(PART)
                if not block:
                    break
                name = 'locked-crates.part%04d' % index
                (output / name).write_bytes(block)
                parts.append(dict(path=name, sha256=sha(block), bytes=len(block)))
                index += 1
        write(output / 'bundle.json', dict(schema='openmhd.locked-crate-bundle.v1',
            lock_sha256=sha(raw), manifest_sha256=sha((output / 'manifest.json').read_bytes()),
            archive_sha256=sha(archive.read_bytes()), archive_bytes=archive.stat().st_size,
            parts=parts, package_count=len(rows)))
        status.update(status='complete', bundle_sha256=sha((output / 'bundle.json').read_bytes()))
    except BaseException as error:
        status.update(status='failed', error_type=type(error).__name__)
        raise
    finally:
        status['finished_utc'] = now()
        write(output / 'status.json', status)
    print(json.dumps(dict(status=status['status'], packages=len(rows),
                         archive_bytes=archive.stat().st_size, parts=len(parts),
                         cargo_offline_validated=False)))


if __name__ == '__main__':
    main()
