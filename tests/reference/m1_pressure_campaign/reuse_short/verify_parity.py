"""Verify compact evidence against the preceding immutable short-stage archive."""
from pathlib import Path
import hashlib
import json
import tarfile


HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def members(path):
    with tarfile.open(path) as archive:
        return {entry.name: archive.extractfile(entry).read()
                for entry in archive if entry.isfile()}


def main():
    report = json.loads((HERE / 'verification.json').read_text())
    previous = HERE.parent / 'short'
    old_manifest = json.loads((previous / 'sha256.json').read_text())
    for name in ('measurements.tar.gz', 'members_sha256.json'):
        assert digest((previous / name).read_bytes()) == old_manifest[name]
    assert old_manifest['measurements.tar.gz'] == report['previous_archive_sha256']
    assert old_manifest['members_sha256.json'] == report['previous_members_sha256']
    old = members(previous / 'measurements.tar.gz')
    old_hashes = json.loads((previous / 'members_sha256.json').read_text())
    assert {n: digest(data) for n, data in old.items()} == old_hashes
    new = members(HERE / 'metadata_and_runtime.tar.gz')
    new_hashes = json.loads((HERE / 'members_sha256.json').read_text())
    assert {n: digest(data) for n, data in new.items()} == new_hashes
    raw_hashes = json.loads((HERE / 'raw_sha256.json').read_text())
    gate = json.loads((HERE / 'gate_checkpoint.json').read_text())
    expected_raw = {}
    for stage in gate['stages'][:4]:
        prefix = stage['name'] + '/'
        assert digest(new[prefix + 'runs.json']) == stage['runs_sha256']
        summary = 'analysis.json' if stage['name'] == 'waves_short' else 'summary.json'
        assert digest(new[prefix + summary]) == stage['summary_sha256']
        runs = json.loads(new[prefix + 'runs.json'])
        for case, row in runs.items():
            for name, checksum in row.get('sha256', row.get('files_sha256')).items():
                expected_raw[prefix + case + '/' + name] = checksum
    assert raw_hashes == expected_raw
    identical = changed = 0
    for name, checksum in raw_hashes.items():
        data = new.get(name, old.get(name))
        assert data is not None and digest(data) == checksum, name
        if checksum == old_hashes[name]:
            identical += 1
        else:
            assert Path(name).name in ('run.log', 'timing.json'), name
            changed += 1
    assert identical == report['scientifically_identical_files'] == 365
    assert changed == report['changed_runtime_files'] == 106
    assert len(raw_hashes) == report['raw_artifacts_verified'] == 471
    print(f'Verified {identical} identical scientific files and {changed} retained runtime files.')


if __name__ == '__main__':
    main()
