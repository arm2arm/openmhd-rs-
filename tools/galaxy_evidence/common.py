"""Inert native-evidence byte, transport and catalog helpers; no acceptance API."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tarfile
import uuid

ROOT = Path(__file__).resolve().parents[2]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


native = load_module('galaxy_native', ROOT / 'reana/galaxy_test_case.py')
supervisor = load_module('galaxy_supervisor', ROOT / native.SUPERVISOR_SOURCE)
require, parse, encode, sha = native.require, native.parse, native.encode, native.sha


def now():
    return datetime.now(timezone.utc).isoformat()


def read(root, name):
    path = PurePosixPath(name)
    require(path.parts and path.as_posix() == name and not path.is_absolute()
            and '..' not in path.parts, 'Unsafe evidence path')
    current = root
    for part in path.parts:
        current /= part
        require(not current.is_symlink(), 'Linked evidence path')
    before = current.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_size <= 512 * 1024 * 1024,
            'Regular bounded evidence file')
    value = current.read_bytes()
    after = current.stat()
    require(all(getattr(before, f) == getattr(after, f) for f in
                ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))
            and len(value) == after.st_size, 'Changed evidence generation')
    return value


def put(root, name, data):
    path = root / name
    require(PurePosixPath(name).as_posix() == name and not Path(name).is_absolute()
            and '..' not in Path(name).parts, 'Unsafe publication path')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def write(root, name, value):
    put(root, name, encode(value))


def inventory(root):
    values = {}
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(), 'Linked evidence entry')
        if path.is_file() and path != root / 'files.sha256.json':
            name = path.relative_to(root).as_posix()
            data = read(root, name)
            values[name] = dict(sha256=sha(data), bytes=len(data))
        else:
            require(path.is_dir() or path.name == 'files.sha256.json', 'Special evidence entry')
    return values


def close(root):
    write(root, 'files.sha256.json', inventory(root))


def verify_closed(root):
    value = parse(read(root, 'files.sha256.json'))
    require(value == inventory(root) and bool(value), 'Exact closed evidence inventory')
    return value


def source_capture(source, output):
    snapshot_raw = read(source, 'snapshot.json')
    snapshot = parse(snapshot_raw)
    names = {'snapshot.json', 'reana.yaml', *snapshot['upload_sha256']}
    captured = {name: read(source, name) for name in names}
    require(sha(captured['reana.yaml']) == snapshot['workflow_sha256'], 'Original submitted specification')
    for name, digest in snapshot['upload_sha256'].items():
        require(sha(captured[name]) == digest, 'Original source upload digest')
    for name, data in captured.items():
        put(output, 'source/' + name, data)
    return snapshot, captured


def fence(root, captured):
    require(all(read(root, name) == data for name, data in captured.items()), 'Changed captured input generation')


def source_files(source_packet):
    """Decode ONLY regular members named by the original immutable source map."""
    snapshot = parse(read(source_packet, 'snapshot.json'))
    data = {}
    for name, record in snapshot['archives'].items():
        blocks = []
        for part in record['parts']:
            block = read(source_packet, part)
            require(sha(block) == snapshot['upload_sha256'][part], 'Original archive part')
            blocks.append(block)
        archive = b''.join(blocks)
        require(sha(archive) == record['sha256'], 'Original source archive identity')
        if name != 'source.tar.gz':
            continue  # History is retained; it is not substituted for source.
        with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as stream:
            for member in stream.getmembers():
                require(member.isfile() and member.name in snapshot['source_sha256']
                        and member.name not in data, 'Exact regular source archive member')
                raw = stream.extractfile(member).read()
                require(sha(raw) == snapshot['source_sha256'][member.name], 'Source member identity')
                data[member.name] = raw
    require(set(data) == set(snapshot['source_sha256']), 'Complete original source map')
    return data


def observation(data, workflow, identifier=None, finished=False):
    value = parse(data)
    require(value.get('schema') == 'openmhd.galaxy-server-observation.v1'
            and value.get('origin') == 'server' and len(value['matches']) == 1, 'Unique authoritative observation')
    row = value['matches'][0]
    require(row['workflow'] == workflow and workflow == row['name'] + '.' + str(row['version'])
            and type(row['version']) is int and row['version'] == 1
            and str(uuid.UUID(row['id'])) == row['id'], 'Original workflow/version/UUID')
    require(identifier is None or row['id'] == identifier, 'Workflow UUID changed')
    require(not finished or row['status'] == 'finished', 'Workflow must actually finish')
    return row


def attempt(root, action, workflow, path=None):
    """One bounded direct adapter call, journaled before launch. No retry or mutation."""
    transport = root / 'transport'
    transport.mkdir(exist_ok=True)
    number = len(list(transport.glob('*.json')))
    label = str(number).zfill(4)
    relative = 'downloads/' + label + '.body'
    (root / 'downloads').mkdir(exist_ok=True)
    adapter = (ROOT / 'tools/galaxy_evidence/readonly_adapter.py').resolve()
    argv = [sys.executable, '-B', str(adapter), action, '--workflow', workflow,
            '--output', str((root / relative).resolve())]
    if path is not None:
        argv += ['--path', path]
    supervisor.credential_free_argv(argv)
    row = dict(schema='openmhd.galaxy-transport-attempt.v1', action=action, workflow=workflow,
               remote_path=path, output=relative, argv=argv, cwd=str(root.resolve()),
               adapter_sha256=sha(adapter.read_bytes()),
               base_adapter_sha256=sha((ROOT / 'tools/m1_evidence/reana_metadata_readonly_adapter.py').read_bytes()),
               started_utc=now(), finished_utc=None, outcome='pending_launch', returncode=None)
    journal = transport / (label + '.json')
    native.persist(journal, row)
    out, err = b'', b''
    try:
        result = subprocess.run(argv, cwd=root, capture_output=True, timeout=300, check=False)
        out, err = result.stdout, result.stderr
        row.update(outcome='success' if result.returncode == 0 else 'nonzero', returncode=result.returncode)
    except subprocess.TimeoutExpired as error:
        out, err = error.stdout or b'', error.stderr or b''
        row.update(outcome='timeout', error_type='TimeoutExpired')
    except BaseException as error:
        row.update(outcome='interrupted_or_start_failed', error_type=type(error).__name__)
        raise
    finally:
        # Adapter prints only static typed diagnostics, not URLs or exception text.
        # Retain only its schema-valid diagnostic, never arbitrary child messages.
        for channel, raw in (('stdout', out), ('stderr', err)):
            try:
                value = parse(raw)
                require(value['schema'] == 'openmhd.galaxy-get-diagnostic.v1', 'Typed adapter diagnostic')
                retained = raw
            except (ValueError, KeyError, TypeError):
                retained = encode({'schema': 'openmhd.galaxy-unavailable-diagnostic.v1',
                                   'unretained_bytes': len(raw), 'sha256': sha(raw)})
            name = 'transport/' + label + '.' + channel
            put(root, name, retained)
            row[channel] = name
            row[channel + '_sha256'] = sha(retained)
        row['finished_utc'] = now()
        if (root / relative).exists():
            row['output_sha256'] = sha(read(root, relative))
        native.persist(journal, row)
    require(row['outcome'] == 'success' and row['returncode'] == 0, 'Unsuccessful read-only transport; retain attempt')
    diagnostic = parse(read(root, row['stdout']))
    require(diagnostic['outcome'] == 'success' and diagnostic['code'] == 'completed'
            and diagnostic['action'] == action and diagnostic['workflow'] == workflow
            and diagnostic['requested_path'] == path and len(diagnostic['workflow_ids']) == 1,
            'Adapter actual UUID/path diagnostic')
    return read(root, relative), 'transport/' + label + '.json', diagnostic['workflow_ids'][0]


def transport_body(root, label, workflow, identifier, action, remote_path):
    row = parse(read(root, label))
    require(row['schema'] == 'openmhd.galaxy-transport-attempt.v1'
            and row['workflow'] == workflow and row['action'] == action and row['remote_path'] == remote_path
            and row['outcome'] == 'success' and type(row['returncode']) is int and row['returncode'] == 0,
            'Actual successful transport receipt')
    argv = row['argv']
    require(type(argv) is list and len(argv) >= 3 and Path(argv[0]).is_absolute()
            and Path(argv[2]).is_absolute()
            and Path(argv[2]).parts[-3:] == ('tools', 'galaxy_evidence', 'readonly_adapter.py')
            and Path(row['cwd']).is_absolute(), 'Credential-free absolute adapter invocation')
    supervisor.credential_free_argv(argv)
    expected = [argv[0], '-B', argv[2], action, '--workflow', workflow,
                '--output', str(Path(row['cwd']) / row['output'])]
    if remote_path is not None:
        expected += ['--path', remote_path]
    require(argv == expected
            and row['adapter_sha256'] == sha(read(ROOT, 'tools/galaxy_evidence/readonly_adapter.py'))
            and row['base_adapter_sha256'] == sha(read(ROOT, 'tools/m1_evidence/reana_metadata_readonly_adapter.py'))
            and supervisor.utc(row['finished_utc']) >= supervisor.utc(row['started_utc']),
            'Actual adapter argv/source/time linkage')
    for channel in ('stdout', 'stderr'):
        require(sha(read(root, row[channel])) == row[channel + '_sha256'], 'Transport diagnostic identity')
    diagnostic = parse(read(root, row['stdout']))
    require(diagnostic['schema'] == 'openmhd.galaxy-get-diagnostic.v1'
            and diagnostic['outcome'] == 'success' and diagnostic['workflow_ids'] == [identifier]
            and diagnostic['workflow'] == workflow and diagnostic['action'] == action
            and diagnostic['requested_path'] == remote_path, 'Exact transport UUID/action/path')
    body = read(root, row['output'])
    require(sha(body) == row['output_sha256'], 'Actual downloaded body digest')
    return body


def transport_closure(root, labels):
    require(len(labels) == len(set(labels)), 'One distinct receipt per transport')
    actual = {'transport/' + p.name for p in (root / 'transport').glob('*.json')}
    require(actual == set(labels), 'No unreferenced transport attempts in successful capture')
    expected, bodies = set(), set()
    for label in labels:
        row = parse(read(root, label))
        expected.update((label, row['stdout'], row['stderr']))
        bodies.add(row['output'])
    require(len(bodies) == len(labels)
            and {'transport/' + n for n in inventory(root / 'transport')} == expected
            and {'downloads/' + n for n in inventory(root / 'downloads')} == bodies,
            'Exact transport/log/download closure; partials cannot be hidden in success')


def extract_export(data, members, destination):
    require(type(members) is dict and members, 'Nonempty exact export member map')
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as stream:
        values = stream.getmembers()
        require(len(values) == len(members) and {v.name for v in values} == set(members), 'Exact archive members')
        for value in values:
            require(value.isfile() and value.size == members[value.name]['bytes']
                    and 0 < value.size <= 512 * 1024 * 1024, 'Regular bounded export member')
            raw = stream.extractfile(value).read()
            require(sha(raw) == members[value.name]['sha256'], 'Export member digest')
            put(destination, value.name, raw)


def catalog(preflight, contract, snapshot):
    """Explicit reviewed target contracts, never eligibility by name alone."""
    require(contract['schema'] == 'openmhd.galaxy-reviewed-catalog.v1'
            and contract['component_accepted'] is False, 'Reviewed portability contract scope')
    selected, seen = [], set()
    for target in contract['targets']:
        component = {'crates/galaxy-types/Cargo.toml': 'identity',
                     'crates/moving-mesh/Cargo.toml': 'geometry',
                     'crates/gravity/Cargo.toml': 'gravity'}.get(target['manifest'])
        require(component is not None and target['component'] == component, 'Exact component/manifest role')
        prefix = target['manifest'].rsplit('/', 1)[0] + '/'
        required_sources = {n for n in snapshot['source_sha256']
                            if n.startswith(prefix) and (n.endswith('.rs') or n.endswith('/Cargo.toml'))}
        require(required_sources <= set(target['source_sha256']), 'Whole component Rust/manifest review pins')
        for name, digest in target['source_sha256'].items():
            require(snapshot['source_sha256'][name] == digest, 'Reviewed target source pin')
        require(target['manifest'] in target['source_sha256'] and target['source'] in target['source_sha256']
                and type(target['selectors']) is list and target['selectors']
                and len(set(target['selectors'])) == len(target['selectors']), 'Explicit reviewed source/selectors')
        require(type(target['review_sha256']) is str and re.fullmatch('[0-9a-f]{64}', target['review_sha256']),
                'Pin independent source/portability review')
        require(snapshot['source_sha256'][target['review_path']] == target['review_sha256'],
                'Original independent review document identity')
        require(target['component'] in ('identity', 'geometry', 'gravity'), 'New component only')
        resources = target['resources']
        require(resources['threads'] == 1 and type(resources['threads']) is int
                and resources['memory'] == ('1Gi' if target['component'] == 'gravity' else '2Gi')
                and type(resources['timeout_seconds']) is int
                and 0 < resources['timeout_seconds'] <= 1800, 'Explicit per-method resources')
        if target['component'] in ('identity', 'geometry'):
            require(resources['timeout_seconds'] == (180 if target['component'] == 'identity' else 300),
                    'Registered identity/geometry timeout')
        else:
            require(resources['timeout_seconds'] == 180, 'Registered direct-gravity timeout')
        for profile in ('debug', 'release'):
            actual = [v for v in preflight['tests'] if v['build_profile'] == profile
                and (v['manifest'], v['target_kind'], v['target_name'], v['source']) ==
                (target['manifest'], target['target_kind'], target['target_name'], target['source'])]
            if target['manifest'] == 'crates/moving-mesh/Cargo.toml' and target['target_kind'] == ['lib']:
                actual = [v for v in actual if v['selector'] in native.EXACT_LIBRARY_SELECTORS]
            require({v['selector'] for v in actual} == set(target['selectors'])
                    and len(actual) == len(target['selectors']), 'Complete exact target/profile coverage')
            for leaf in actual:
                identity = (profile, leaf['manifest'], leaf['target_name'], leaf['selector'])
                require(identity not in seen, 'Repeated reviewed leaf')
                seen.add(identity)
                selected.append((leaf, resources))
    identity = [v for v, _ in selected if v['build_profile'] == 'debug'
                and v['manifest'] == 'crates/galaxy-types/Cargo.toml']
    geometry = [v for v, _ in selected if v['build_profile'] == 'debug'
                and v['manifest'] == 'crates/moving-mesh/Cargo.toml']
    require(len(identity) == 26 and len(geometry) == 28
            and {v['selector'] for v in geometry if v['target_kind'] == ['lib']} == native.EXACT_LIBRARY_SELECTORS,
            'All 26 identity and 24+4 geometry selectors per profile')
    gravity = [v for v, _ in selected if v['build_profile'] == 'debug'
               and v['manifest'] == 'crates/gravity/Cargo.toml']
    require(len(gravity) == 39 and sum(v['target_kind'] == ['lib'] for v in gravity) == 9,
            'Complete reviewed 9-library/30-integration direct-gravity catalog')
    eligible = [v for v in preflight['tests'] if v['manifest'] in
                ('crates/galaxy-types/Cargo.toml', 'crates/gravity/Cargo.toml') and
                (v['manifest'] == 'crates/gravity/Cargo.toml' or v['target_kind'] == ['test'])]
    require(all((v['build_profile'], v['manifest'], v['target_name'], v['selector']) in seen for v in eligible),
            'No silently omitted identity/gravity standalone leaves')
    return sorted(selected, key=lambda item: (item[0]['build_profile'], item[0]['manifest'],
                                             item[0]['target_name'], item[0]['selector']))
