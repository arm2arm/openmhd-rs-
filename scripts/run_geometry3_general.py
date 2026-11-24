#!/usr/bin/env python3
"""Execute one general-geometry data/reference/reduction task on REANA.

Import performs no geometry calculation or filesystem access. The caller must
retain the authoritative workflow, held-child command and prerequisite joins;
these packets provide arithmetic and input identities, not that provenance.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import stat
import tarfile

import galaxy_geometry3_general_bridge as bridge
import galaxy_geometry3_general_compare as comparison
import galaxy_geometry3_general_fixtures as fixtures
import galaxy_geometry3_general_reference as reference

MAX_RAW_BYTES = 128 * 1024 * 1024
MAX_CAPSULE_BYTES = 16 * 1024 * 1024
SOURCE_NAMES = ('run_geometry3_general.py', 'galaxy_geometry3_general_bridge.py',
    'galaxy_geometry3_general_compare.py', 'galaxy_geometry3_general_fixtures.py',
    'galaxy_geometry3_general_reference.py', 'galaxy_geometry3_reference.py')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('ascii')


def parse(raw):
    def finite(text):
        value = float(text)
        require(math.isfinite(value), 'Finite JSON number')
        return value
    return json.loads(raw, object_pairs_hook=bridge.unique_object,
                      parse_constant=bridge.reject_constant, parse_float=finite)


def capture(path):
    """Read one held regular generation; never follow an input symlink."""
    path = Path(path).absolute()
    parent = path
    while parent != parent.parent:
        require(not parent.is_symlink(), 'Linked input path')
        parent = parent.parent
    descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(descriptor, 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_size <= MAX_RAW_BYTES,
                'Bounded regular input')
        raw = stream.read(MAX_RAW_BYTES + 1)
        after = os.fstat(stream.fileno())
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    require(len(raw) <= MAX_RAW_BYTES and len(raw) == after.st_size
            and all(getattr(before, f) == getattr(after, f) for f in fields)
            and path.lstat().st_ino == after.st_ino and not path.is_symlink(),
            'Held input generation remained coherent')
    return raw


def describe(raw):
    return dict(sha256=digest(raw), bytes=len(raw))


def capsule(files):
    require(type(files) is dict and files, 'Nonempty capsule')
    require(sum(len(raw) for raw in files.values()) <= MAX_RAW_BYTES,
            'Bounded uncompressed capsule')
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w', format=tarfile.PAX_FORMAT) as archive:
        for name, raw in sorted(files.items()):
            path = Path(name)
            require(path.parts and path.as_posix() != '.' and not path.is_absolute()
                    and '..' not in path.parts and '\\' not in name
                    and path.as_posix() == name and type(raw) is bytes,
                    'Safe exact capsule members')
            member = tarfile.TarInfo(name)
            member.size, member.mode, member.mtime = len(raw), 0o644, 0
            archive.addfile(member, io.BytesIO(raw))
    packed = gzip.compress(stream.getvalue(), mtime=0)
    require(len(packed) <= MAX_CAPSULE_BYTES, 'Bounded transport capsule')
    return packed


def literal_packet():
    """Freeze each actual word array once, before candidate/reference execution."""
    files, inputs = {}, {}
    for base in fixtures.BASES:
        for variant in fixtures.VARIANTS:
            value = fixtures.build(base, variant)
            raw = fixtures.encode(value)
            bridge.parse_input(raw)
            bridge.convert_input(raw)
            name = 'inputs/' + value['case']['name'] + '.json'
            files[name] = raw
            inputs[(base, variant)] = dict(path=name, **describe(raw),
                generators=len(value['generators']))
    cases = []
    for case in fixtures.catalog():
        cases.append(dict(case, input=inputs[(case['base'], case['variant'])]))
    files['catalog.json'] = encode(dict(schema='openmhd.geometry3.general-literals.v1',
        seed=fixtures.SEED, design_sha256=bridge.DESIGN_SHA256,
        method=bridge.METHOD, cases=cases, distinct_inputs=len(inputs),
        candidate_invoked=False, reference_evaluated=False, component_accepted=False))
    return files


def execute(action, output, paths):
    require(action in ('fixtures', 'reference', 'compare', 'reproducibility'), 'Named task')
    expected = dict(fixtures=(), reference=('input',),
        compare=('input', 'candidate', 'reference'),
        reproducibility=('left_input', 'left_candidate', 'right_input', 'right_candidate'))[action]
    require(set(paths) == set(expected), 'Exact task input set')
    output = Path(output).absolute()
    require(not output.exists() and not output.is_symlink(), 'Fresh task output')
    output.mkdir(parents=True)
    status = dict(schema='openmhd.geometry3.general-task.v1', action=action,
        status='preparing', started_utc=datetime.now(timezone.utc).isoformat(),
        execution_provenance_verified=False, component_accepted=False)
    status_path = output / 'status.json'
    status_path.write_bytes(encode(status))
    files, captured = {}, {}
    try:
        source_root = Path(__file__).resolve().parent
        sources = {name: capture(source_root / name) for name in SOURCE_NAMES}
        for name, path in paths.items():
            captured[name] = capture(path)
        status.update(source_sha256={n: digest(b) for n, b in sources.items()},
                      input_identities={n: describe(b) for n, b in captured.items()})
        if action == 'fixtures':
            files = literal_packet()
        elif action == 'reference':
            files = {'input.json': captured['input'],
                     'reference.json': encode(reference.evaluate(captured['input']))}
        elif action == 'compare':
            reduced = comparison.compare(captured['input'], captured['candidate'],
                                         parse(captured['reference']))
            files = {'input.json': captured['input'], 'candidate.txt': captured['candidate'],
                     'reference.json': captured['reference'], 'comparison.json': encode(reduced)}
            require(reduced['passed'] is True, 'Registered geometry comparison failed')
        else:
            reduced = comparison.reproducibility(captured['left_input'], captured['left_candidate'],
                captured['right_input'], captured['right_candidate'])
            files = {name + ('.txt' if 'candidate' in name else '.json'): raw
                     for name, raw in captured.items()}
            files['reproducibility.json'] = encode(reduced)
            require(reduced['passed'] is True, 'Registered reproducibility comparison failed')
        require(all(capture(source_root / name) == raw for name, raw in sources.items())
                and all(capture(paths[name]) == raw for name, raw in captured.items()),
                'Source and actual task inputs remained unchanged')
        status.update(status='complete', finished_utc=datetime.now(timezone.utc).isoformat())
        files['status.json'] = encode(status)
        identities = {name: describe(raw) for name, raw in sorted(files.items())}
        files['files.sha256.json'] = encode(identities)
        packed = capsule(files)
        # Complete status is published last. Consumers also require its exact manifest.
        for name, raw in files.items():
            if name == 'status.json':
                continue
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(raw)
        (output / 'packet.tar.gz').write_bytes(packed)
        (output / 'packet.sha256.json').write_bytes(encode(describe(packed)))
        status_path.write_bytes(files['status.json'])
        return status
    except BaseException as error:
        status.update(status='failed', finished_utc=datetime.now(timezone.utc).isoformat(),
                      error_type=type(error).__name__, error=str(error))
        # Preserve computed failing reductions and their actual inputs as failures.
        # An incomplete source/transport packet never becomes successful here.
        try:
            failed = {name: raw for name, raw in files.items()
                      if name not in ('status.json', 'files.sha256.json')}
            failed.update({'failed_inputs/' + name + '.bin': raw
                           for name, raw in captured.items()})
            failed['status.json'] = encode(status)
            failed['files.sha256.json'] = encode({name: describe(raw)
                for name, raw in sorted(failed.items())})
            (output / 'failure-records.tar.gz').write_bytes(capsule(failed))
        except BaseException as retention_error:
            status['failure_retention_error_type'] = type(retention_error).__name__
        status_path.write_bytes(encode(status))
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('fixtures', 'reference', 'compare', 'reproducibility'))
    parser.add_argument('--output', type=Path, required=True)
    for name in ('input', 'candidate', 'reference', 'left-input', 'left-candidate',
                 'right-input', 'right-candidate'):
        parser.add_argument('--' + name, type=Path)
    args = parser.parse_args(argv)
    paths = {n: v for n, v in vars(args).items() if n not in ('action', 'output') and v is not None}
    status = execute(args.action, args.output, paths)
    print(json.dumps(dict(action=status['action'], status=status['status'],
                          component_accepted=False)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
