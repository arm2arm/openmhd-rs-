"""Stage and verify individual workspace tests using the archived G00 binaries."""
import argparse
import base64
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import sys
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'reana'))
import galaxy_test_case as launcher
import galaxy_workspace_case as original
import prebuilt_workspace_leaf as job
from verify_m2a_offline_leaf import PLAN_SHA256


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.write_bytes(original.encode(value))


def spec():
    step = dict(name='verify-and-run-one-prebuilt-workspace-leaf', environment=original.IMAGE,
                compute_backend='kubernetes', kubernetes_cpu_request='1', kubernetes_cpu_limit='1',
                kubernetes_memory_limit=job.RESOURCES['memory'],
                commands=['python3 -B runner.py'])
    return dict(version='0.9.0', inputs=dict(files=['runner.py', 'materials.zip', 'libtest.gz']),
                workflow=dict(type='serial', specification=dict(steps=[step])),
                outputs=dict(files=['outputs/evidence.tar.gz']))


def compress_targets(export_dir, shared, wanted):
    manifest = read(export_dir / 'export.json')
    original.require(manifest['archive_sha256'] == job.ARCHIVE and manifest['preflight_sha256'] == job.PREFLIGHT,
                     'Workspace build export')
    outputs = {}
    with tempfile.TemporaryFile(dir=shared) as archive:
        whole = hashlib.sha256()
        for index, part in enumerate(manifest['parts']):
            original.require(part['path'] == f'export.part{index:04d}', 'Ordered export parts')
            data = (export_dir / 'parts' / part['path']).read_bytes()
            original.require(len(data) == part['bytes'] and job.digest(data) == part['sha256'], 'Export part')
            archive.write(data)
            whole.update(data)
        original.require(whole.hexdigest() == job.ARCHIVE and archive.tell() == manifest['archive_bytes'],
                         'Complete build archive')
        archive.seek(0)
        with tarfile.open(fileobj=archive, mode='r|gz') as tar:
            for member in tar:
                if member.name not in wanted:
                    continue
                pin = manifest['members'][member.name]
                original.require(member.isfile() and member.name not in outputs and
                                 0 < member.size == pin['bytes'] <= original.MAX_EXECUTABLE_BYTES, 'Binary member')
                data = tar.extractfile(member).read()
                original.require(job.digest(data) == pin['sha256'] == wanted[member.name], 'Selected binary hash')
                packed = gzip.compress(data, compresslevel=1, mtime=0)
                path = shared / (pin['sha256'] + '.gz')
                path.write_bytes(packed)
                outputs[member.name] = (path, job.digest(packed))
    original.require(set(outputs) == set(wanted), 'Complete selected binary set')
    return outputs


def prepare(catalog_dir, export_dir, coverage_path, destination, select):
    plan_raw = (catalog_dir / 'plan.json').read_bytes()
    original.require(job.digest(plan_raw) == PLAN_SHA256, 'Original corrected workspace plan')
    entries = json.loads(plan_raw)['cases']
    missing = set(read(coverage_path)['awaiting_passing_capture'])
    chosen = [e for e in entries if e['directory'] in missing
              and (not select or e['directory'] in select)
              and (e['specification']['leaf']['manifest'], e['specification']['leaf']['target_name'])
              != ('apps/openmhd/Cargo.toml', 'restart')]
    original.require(bool(chosen) and (not select or {e['directory'] for e in chosen} == select),
                     'Unverified eligible original cases')
    destination.mkdir()
    shared = destination / 'shared'
    shared.mkdir()
    leaves = [e['specification']['leaf'] for e in chosen]
    compressed = compress_targets(export_dir, shared, {l['binary']: l['binary_sha256'] for l in leaves})
    runner = (ROOT / 'reana/prebuilt_workspace_leaf.py').read_bytes()
    runner_sha = job.digest(runner)
    (shared / 'runner.py').write_bytes(runner)
    export = (export_dir / 'export.json').read_bytes()
    cases = []
    for entry in chosen:
        index = entry['directory']
        case = catalog_dir / index
        folder = destination / index
        folder.mkdir()
        data = {n: (case / n).read_bytes() for n in original.FIXED | {'payload.json'}}
        original.require(all(entry['files'][n] == dict(bytes=len(raw), sha256=job.digest(raw))
                             for n, raw in data.items()), 'Original case material hashes')
        snapshot = json.loads(data['snapshot.json'])
        parts = snapshot['archives']['source.tar.gz']['parts']
        data['source.tar.gz'] = b''.join((case / n).read_bytes() for n in parts)
        data['export.json'] = export
        with zipfile.ZipFile(folder / 'materials.zip', 'x') as z:
            for n in sorted(data):
                z.writestr(zipfile.ZipInfo(n), data[n], compress_type=zipfile.ZIP_DEFLATED, compresslevel=1)
        packed = (folder / 'materials.zip').read_bytes()
        _, _, leaf, _, _, _ = job.materials(packed)
        original.require(leaf == entry['specification']['leaf'], 'Registered workspace leaf')
        path, binary_payload_sha = compressed[leaf['binary']]
        os.link(path, folder / 'libtest.gz')
        os.link(shared / 'runner.py', folder / 'runner.py')
        write(folder / 'reana.yaml', spec())
        cases.append(dict(directory=index, workflow=f'openmhd-m2a-prebuilt-{runner_sha[:10]}-{index}.1',
                          legacy=entry['original_workflow'], corrected=entry['workflow'], leaf=leaf,
                          runner_sha256=runner_sha, materials_sha256=job.digest(packed),
                          compressed_binary_sha256=binary_payload_sha,
                          workflow_spec_sha256=job.digest((folder / 'reana.yaml').read_bytes())))
    write(destination / 'plan.json', dict(original_plan_sha256=PLAN_SHA256, parent_uuid=job.PARENT_UUID,
                                          export_sha256=job.ARCHIVE, cases=cases))


def verify(folder, capture):
    plan = read(folder.parent / 'plan.json')
    entry, = [e for e in plan['cases'] if e['directory'] == folder.name]
    original.require(plan['original_plan_sha256'] == PLAN_SHA256 and plan['parent_uuid'] == job.PARENT_UUID
                     and plan['export_sha256'] == job.ARCHIVE, 'Original workspace build and plan')
    before, after = (read(capture / n) for n in ('before.json', 'after.json'))
    remote, = before
    original.require(before == after and remote['status'] == 'finished' and remote['version'] == 1
                     and remote['workflow'] == entry['workflow'], 'Same finished REANA workflow')
    packed = (folder / 'materials.zip').read_bytes()
    runner, _, leaf, names, _, binary_size = job.materials(packed)
    runner_bytes = (folder / 'runner.py').read_bytes()
    runner_hash = job.digest(runner_bytes)
    workflow_spec = (folder / 'reana.yaml').read_bytes()
    compressed = (folder / 'libtest.gz').read_bytes()
    original.require(0 < binary_size <= original.MAX_EXECUTABLE_BYTES, 'Original build member size')
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as binary:
        executable = binary.read(binary_size + 1)
    original.require(leaf == entry['leaf'] and job.digest(packed) == entry['materials_sha256']
                     and runner_bytes == Path(job.__file__).read_bytes() and runner_hash == entry['runner_sha256']
                     and entry['workflow'] == f'openmhd-m2a-prebuilt-{runner_hash[:10]}-{folder.name}.1'
                     and job.digest(compressed) == entry['compressed_binary_sha256']
                     and len(executable) == binary_size and job.digest(executable) == leaf['binary_sha256']
                     and job.digest(workflow_spec) == entry['workflow_spec_sha256']
                     and workflow_spec == original.encode(spec()), 'Registered executable and workflow inputs')
    packet = (capture / 'evidence.tar.gz').read_bytes()
    with tarfile.open(fileobj=io.BytesIO(packet), mode='r:gz') as tar:
        members = tar.getmembers()
        original.require(len(members) == len(job.CONTENTS) + 1
                         and {m.name for m in members} == set(job.CONTENTS) | {'manifest.json'}
                         and all(m.isfile() for m in members) and sum(m.size for m in members) <= 16*1024*1024,
                         'Bounded result capsule')
        raw = {m.name: tar.extractfile(m).read() for m in members}
    original.require(json.loads(raw['manifest.json']) == {n: job.digest(raw[n]) for n in job.CONTENTS},
                     'Result artifact hashes')
    result, stages = json.loads(raw['result.json']), json.loads(raw['command.json'])
    links = dict(materials_sha256=entry['materials_sha256'], runner_sha256=entry['runner_sha256'],
                 binary_sha256=leaf['binary_sha256'], preflight_sha256=job.PREFLIGHT)
    original.require(result['schema'] == 'openmhd.prebuilt-workspace-leaf.v1' and result['status'] == 'passed'
                     and result['component_accepted'] is False and result['uuid'] == remote['id']
                     and result['parent_uuid'] == job.PARENT_UUID and result['leaf'] == leaf
                     and result['resources'] == job.RESOURCES and result['input_links'] == links
                     and result['machine'] == 'x86_64' and result['thread_environment'] == dict.fromkeys(job.THREADS,'1'),
                     'Actual workspace, binary, runtime and leaf')
    original.require([s['label'] for s in stages] == ['list','ignored-list','leaf'], 'Complete native stages')
    source = PurePosixPath(stages[0]['command']['cwd'])
    original.require(source.is_absolute() and source.name == 'source' and source.parent.name == remote['id'],
                     'Actual REANA UUID in command path')
    binary = str(source / 'target' / leaf['build_profile'] / 'deps' / PurePosixPath(leaf['binary']).name)
    arguments = [['--list','--format','terse'], ['--list','--ignored','--format','terse'],
                 ['--exact',leaf['selector'],'--test-threads','1','--color','never','--show-output']]
    for stage, args in zip(stages, arguments):
        command = stage['command']
        runner.settled(command)
        original.require(stage['argv'] == command['command'] == [binary, *args]
                         and command['cwd'] == str(source) and command['links'] == links
                         and command['timeout_seconds'] == job.RESOURCES['command_timeout_seconds'],
                         'Exact supervised command and inputs')
    stdout = [base64.b64decode(s['stdout_base64'], validate=True) for s in stages]
    original.require(runner.listing(stdout[0]) == names and stdout[1] == b''
                     and stdout[2] == raw['stdout.txt']
                     and base64.b64decode(stages[2]['stderr_base64'], validate=True) == raw['stderr.txt']
                     and launcher.witness(stdout[2], leaf['selector'], len(names)) == result['witness'],
                     'Exact registered nonignored test and raw output')
    return dict(directory=entry['directory'], workflow=remote['workflow'], uuid=remote['id'], leaf=leaf,
                packet_sha256=job.digest(packet), stdout_sha256=job.digest(stdout[2]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    staging = commands.add_parser('prepare')
    for argument in ('catalog','export','coverage','destination'):
        staging.add_argument(argument, type=Path)
    staging.add_argument('--only', nargs='+', default=[])
    checking = commands.add_parser('verify')
    checking.add_argument('folder', type=Path)
    checking.add_argument('capture', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(args.catalog, args.export, args.coverage, args.destination, set(args.only))
    else:
        print(json.dumps(verify(args.folder, args.capture), indent=2))
