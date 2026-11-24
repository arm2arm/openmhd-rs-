"""Archive historical data with byte checks before removing expanded copies."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tarfile
from datetime import datetime, timezone

MAIN = Path('/Users/arm2arm/orca/openmhd-rs-')
SOURCE = Path('/Users/arm2arm/orca/workspaces/openmhd-rs-/m1-run-alfv-n-wave-and-field-loop-benchmarks/results')
OPS = MAIN / 'results/results_cleanup_20261124_attempt01'
DEST = Path('/Users/arm2arm/orca/archives/openmhd-rs-/wave-checkpoints-20261124-attempt02')
PREFIX = 'independent_fresh_waves_checkpoint_20261122_'


def now():
    return datetime.now(timezone.utc).isoformat()


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def save(path, data):
    with path.open('x') as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def event(data):
    data = dict(utc=now(), **data)
    with (DEST / 'events.jsonl').open('a') as stream:
        stream.write(json.dumps(data, sort_keys=True) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(data), flush=True)


def inventory(base):
    rows = {}
    for folder, dirs, files in os.walk(base, followlinks=False):
        for name in sorted(dirs + files):
            path = Path(folder) / name
            st = path.lstat()
            need(stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode), 'Nonregular data: ' + str(path))
            relative = path.relative_to(base).as_posix()
            row = dict(type='directory' if stat.S_ISDIR(st.st_mode) else 'file', mode=stat.S_IMODE(st.st_mode), mtime_ns=st.st_mtime_ns)
            if row['type'] == 'file':
                row.update(bytes=st.st_size, sha256=digest(path))
                after = path.lstat()
                need((st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns) == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'Data changed during read')
            rows[relative] = row
    return rows


def verify_tar(path, name, expected):
    seen = {}
    with tarfile.open(path, 'r|gz') as archive:
        for item in archive:
            if item.name == name:
                need(item.isdir(), 'Archive root directory')
                continue
            need(item.name.startswith(name + '/'), 'Archive member outside selected checkpoint')
            rel = item.name[len(name) + 1:]
            need(rel in expected and rel not in seen, 'Unexpected or duplicate archive member')
            row = expected[rel]
            need(item.mode == row['mode'], 'Archive permission changed')
            if row['type'] == 'directory':
                need(item.isdir(), 'Archive directory kind')
            else:
                need(item.isfile() and item.size == row['bytes'], 'Archive file shape')
                h = hashlib.sha256()
                stream = archive.extractfile(item)
                for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
                    h.update(chunk)
                need(h.hexdigest() == row['sha256'], 'Archive body changed: ' + rel)
            seen[rel] = True
    need(set(seen) == set(expected), 'Archive missing source entries')


def protected_publications():
    verified = []
    pairs = [
        ('tests/reference/m1_final_acceptance/archive_sha256.json', None),
        ('tests/reference/m1_final_acceptance/evidence/sha256.json', None),
        ('tests/reference/m1_final_acceptance/review/review_sha256.json', None),
        ('docs/images/geometry3_actual_20261123/publication.sha256.json', None),
        ('docs/images/mesh_motion_3d_preview/artifacts.json', 'outputs/'),
    ]
    for name, strip in pairs:
        manifest = MAIN / name
        rows = json.loads(manifest.read_bytes())
        for relative, record in rows.items():
            if strip:
                need(relative.startswith(strip), 'Expected render publication path')
                relative = relative[len(strip):]
            path = manifest.parent / relative
            expected = record if isinstance(record, str) else record['sha256']
            need(path.is_file() and not path.is_symlink() and digest(path) == expected, 'Published artifact hash: ' + str(path))
            if isinstance(record, dict) and 'bytes' in record:
                need(path.stat().st_size == record['bytes'], 'Published artifact length')
        verified.append(dict(manifest=name, sha256=digest(manifest), members=len(rows)))
    return verified


def main():
    need(not DEST.exists(), 'Fresh archive destination required')
    need((SOURCE / (PREFIX + '0021')).is_dir(), 'Keep the final expanded checkpoint')
    publications = protected_publications()
    paths = [SOURCE / (PREFIX + '%04d' % number) for number in range(2, 21)]
    need(all(path.is_dir() and not path.is_symlink() for path in paths), 'Expected exact nineteen historical directories')
    DEST.mkdir(parents=True, mode=0o700)
    save(DEST / 'plan.json', dict(schema='openmhd.local-results-compaction.v1', utc=now(), source=str(SOURCE), destination=str(DEST), exact_selected=[path.name for path in paths], keep_expanded=PREFIX + '0021', publications=publications, backup_scope='same-laptop local compressed archive; not an independent or GitHub backup'))
    rows = []
    for index, original in enumerate(paths, 1):
        name = original.name
        event(dict(phase='inventory', checkpoint=name, index=index, total=len(paths)))
        expected = inventory(original)
        inventory_path = DEST / (name + '.inventory.json')
        save(inventory_path, expected)
        partial = DEST / (name + '.tar.gz.partial')
        archive_path = DEST / (name + '.tar.gz')
        event(dict(phase='compress', checkpoint=name, file_count=sum(row['type'] == 'file' for row in expected.values())))
        with partial.open('xb') as output:
            with gzip.GzipFile(filename='', mode='wb', fileobj=output, compresslevel=1, mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode='w|', format=tarfile.PAX_FORMAT) as archive:
                    archive.add(original, arcname=name, recursive=True)
            output.flush()
            os.fsync(output.fileno())
        event(dict(phase='verify-archive', checkpoint=name))
        verify_tar(partial, name, expected)
        os.replace(partial, archive_path)
        need(inventory(original) == expected, 'Original changed before removal')
        event(dict(phase='archive-verified', checkpoint=name, archive_sha256=digest(archive_path), inventory_sha256=digest(inventory_path)))
        quarantine = DEST / (name + '.expanded-pending-removal')
        os.rename(original, quarantine)
        need(inventory(quarantine) == expected, 'Relocated expanded data changed; keep for recovery')
        row = dict(checkpoint=name, files=sum(row['type'] == 'file' for row in expected.values()), original_bytes=sum(row.get('bytes', 0) for row in expected.values()), archive_bytes=archive_path.stat().st_size, archive=archive_path.name, archive_sha256=digest(archive_path), inventory=inventory_path.name, inventory_sha256=digest(inventory_path))
        save(DEST / (name + '.verified-before-removal.json'), dict(utc=now(), **row))
        shutil.rmtree(quarantine)
        row['expanded_copy_removed'] = True
        rows.append(row)
        event(dict(phase='complete-checkpoint', **row))
    need(protected_publications() == publications, 'Published artifacts changed')
    final = dict(schema='openmhd.local-results-compaction.v1', utc=now(), status='complete', errors=[], original_source=str(SOURCE), archive_directory=str(DEST), checkpoints=rows, total_original_bytes=sum(row['original_bytes'] for row in rows), total_archive_bytes=sum(row['archive_bytes'] for row in rows), preserved_publications=publications, keep_expanded=PREFIX + '0021', independent_backup=False, workflow_mutations=False, numerical_or_test_execution=False)
    save(DEST / 'summary.json', final)
    save(OPS / 'summary.json', final)
    event(dict(phase='all-complete', original_bytes=final['total_original_bytes'], archive_bytes=final['total_archive_bytes'], checkpoints=len(rows)))


if __name__ == '__main__':
    main()
