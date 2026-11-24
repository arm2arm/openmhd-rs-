"""Stage independent M2a reference and candidate workflows from the frozen literals.

Preparation reads existing evidence and writes workflow inputs. Submission,
review of G00, resource calibration and numerical verdicts happen separately.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / 'docs/galaxy/results/m2a_recovery_20261124'
IMAGE = ('gitlab-p4n.aip.de:5005/p4nreana/reana-env@sha256:'
         'aebd7911df9e1e97ad67d15f4c32ab23996000282183fad3bf7a480756522bd7')
SHARED = ('scripts/run_geometry3_general.py', 'scripts/galaxy_geometry3_general_bridge.py',
          'scripts/galaxy_geometry3_general_compare.py', 'scripts/galaxy_geometry3_general_fixtures.py',
          'scripts/galaxy_geometry3_general_reference.py', 'scripts/galaxy_geometry3_reference.py')
NATIVE = ('reana/general_geometry_candidate.py', 'reana/galaxy_test_case.py',
          'tools/m1_evidence/reana_metadata_job.py')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def read_literals():
    record = json.loads((RECORD / 'literal_packet.json').read_bytes())
    path = RECORD / 'literal_packet.tar.gz'
    if digest(path.read_bytes()) != record['packet']['sha256']:
        raise ValueError('Frozen input packet changed')
    with tarfile.open(path, 'r:gz') as archive:
        members = {name: archive.extractfile(name).read() for name in archive.getnames()}
    if digest(members['catalog.json']) != record['catalog']['sha256']:
        raise ValueError('Frozen input catalog changed')
    hashes = json.loads(members['files.sha256.json'])
    if hashes != {n: dict(sha256=digest(b), bytes=len(b)) for n, b in members.items()
                  if n != 'files.sha256.json'}:
        raise ValueError('Frozen literal manifest mismatch')
    return members


def stage(folder, inputs, command, outputs, threads, memory, timeout):
    folder.mkdir(parents=True)
    for name, raw in inputs.items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    env = f'env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 RAYON_NUM_THREADS={threads}'
    # Native runs use the reviewed held-leader supervisor for timeout and logs.
    prefix = f'timeout {timeout} ' if timeout else ''
    step = dict(name=folder.parent.name, environment=IMAGE, compute_backend='kubernetes',
                kubernetes_cpu_request=str(threads), kubernetes_cpu_limit=str(threads),
                kubernetes_memory_limit=memory, commands=[f'{env} {prefix}python3 -B {command}'])
    write_json(folder / 'reana.yaml', dict(version='0.9.0', inputs=dict(files=sorted(inputs)),
               workflow=dict(type='serial', specification=dict(steps=[step])),
               outputs=dict(files=['outputs/' + n for n in outputs])))
    return dict(directory=folder.name, inputs={n: digest(b) for n, b in inputs.items()},
                workflow_sha256=digest((folder / 'reana.yaml').read_bytes()))


def prepare(binary, destination):
    members = read_literals()
    driver = binary.read_bytes()
    driver_pin = json.loads((RECORD / 'general_controls.json').read_bytes())['checked_native_driver']
    if len(driver) != driver_pin['bytes'] or digest(driver) != driver_pin['binary_sha256']:
        raise ValueError('Wrong native executable for reviewed G01 build')
    shared = {n: (ROOT / n).read_bytes() for n in SHARED}
    frozen = json.loads(members['status.json'])['source_sha256']
    if {Path(n).name: digest(b) for n, b in shared.items()} != frozen:
        raise ValueError('Source differs from the frozen fixture workflow')
    native = {n: (ROOT / n).read_bytes() for n in NATIVE}
    catalog = json.loads(members['catalog.json'])
    plan = dict(reference=[], candidate=[])
    destination.mkdir()
    for case in catalog['cases']:
        name = case['name']
        threads = case['threads']
        raw = members[case['input']['path']]
        if digest(raw) != case['input']['sha256']:
            raise ValueError(f'Wrong selected input for {name}')
        inputs = {**shared, 'input.json': raw}
        if threads == 1:
            ref_name = Path(case['input']['path']).stem
            job = stage(destination / 'reference' / ref_name, inputs,
                        'scripts/run_geometry3_general.py reference --input input.json --output outputs',
                        ['status.json', 'packet.tar.gz', 'packet.sha256.json'], 1,
                        '4Gi' if case['required_success'] else '2Gi', 1800 if case['required_success'] else 300)
            plan['reference'].append(job)
        inputs.update(native, **{'catalog.json': members['catalog.json'], 'geometry.bin': driver})
        command = ('reana/general_geometry_candidate.py --input input.json --binary geometry.bin '
                   f'--catalog catalog.json --threads {threads} --output outputs')
        job = stage(destination / 'candidate' / name, inputs, command,
                    ['status.json', 'command.json', 'stdout.txt', 'stderr.txt'],
                    threads, '4Gi' if case['required_success'] or case['variant'] != 'base' or threads != 1 else '2Gi', None)
        plan['candidate'].append(job)
    write_json(destination / 'plan.json', plan)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    prepare(args.binary, args.destination)
