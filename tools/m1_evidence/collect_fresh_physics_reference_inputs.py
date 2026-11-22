"""Collect actual fresh REANA inputs for the existing independent reducers.

Read-only with respect to remote workflows and the live plan. No evolution,
production measurement imports, phase acceptance or inferred missing bytes.
Run frozen reana_cases.py check first; it supplies completed execution receipts.
Use a NEW destination for each checkpoint. Remote downloads are isolated there.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor

SNAPSHOT = 'b67ce03779a194099983b7ff07c0cafed23e9ea3a9051047492d072255e0160f'
BINARY = '18afcf0308338e2ea0ea7ef5e03dba46af9d7025f3ccf4a6a48ebbfe800d0725'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan', type=Path)
    p.add_argument('destination', type=Path)
    p.add_argument('--client', required=True)
    args = p.parse_args()
    root, out = args.plan.resolve(), args.destination.resolve()
    assert not out.exists(), 'Use a fresh isolated checkpoint directory'
    plan = read(root / 'plan.json')
    assert plan['snapshot_sha256'] == SNAPSHOT and len(plan['cases']) == 30
    assert len({e['workflow'] for e in plan['cases']}) == 30
    # Pin one coherent observer checkpoint before remote downloads. The live
    # supervisor may finish another pass while this isolated collector works.
    run_bytes = (root / 'runs.json').read_bytes()
    checkpoint_bytes = (root / 'checkpoint.json').read_bytes()
    observed_runs, checkpoint = json.loads(run_bytes), json.loads(checkpoint_bytes)
    assert checkpoint['completed_cases'] == len(observed_runs)
    assert checkpoint['expected_cases'] == 30
    assert not checkpoint['verified_required_failure'] and not checkpoint['execution_failures']
    assert all(run['status'] == 'completed' for run in observed_runs.values())
    out.mkdir(parents=True)
    shutil.copyfile(root / 'plan.json', out / 'plan.json')
    (out / 'observed_run_map.json').write_bytes(run_bytes)
    (out / 'checkpoint.json').write_bytes(checkpoint_bytes)
    shutil.copyfile(Path(__file__), out / 'collector.py')
    source_snapshot = root / plan['cases'][0]['directory'] / 'snapshot.json'
    assert sha(source_snapshot) == SNAPSHOT
    snapshot = read(source_snapshot)
    reference_paths = [Path('tests/reference/external_mhd') / name
                       for name in ('brio_8192.csv.gz', 'vortex_512.csv.gz')]
    packet = Path('benchmarks/m0/packet.json')
    assert sha(packet) == snapshot['source_sha256'][str(packet)]
    for path in reference_paths:
        assert sha(path) == snapshot['source_sha256'][str(path)]
    provenance = dict(
        scope='Fresh completed REANA raw inputs for independent reference reducers; not full staged-input/phase/M1 acceptance.',
        snapshot_sha256=SNAPSHOT, binary_sha256=BINARY,
        source_sha256={str(packet): sha(packet)},
        reference_sha256={path.name: sha(path) for path in reference_paths},
        collector_sha256=sha(Path(__file__)),
        observed_run_map_sha256=hashlib.sha256(run_bytes).hexdigest(),
        observer_checkpoint_sha256=hashlib.sha256(checkpoint_bytes).hexdigest(),
    )
    (out / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')

    def collect(entry):
        spec = entry['specification']
        config = spec['config']
        name = config['name']
        assert '/' not in name and '..' not in name
        assert spec['kind'] == 'physics'
        assert config['profile'] == 'bulk-frame-heun-quadratic-v1'
        assert config['riemann_solver'] == 'hlld-pressure'
        assert spec['options'] == dict(accelerated_projection=False,
                                      projection_screening=1., potential_limiter='smooth-extrema')
        case = root / entry['directory']
        assert sha(case / 'payload.json') == entry['payload_sha256']
        assert sha(case / 'reana.yaml') == entry['workflow_sha256']
        assert read(case / 'case.json') == spec
        if name not in observed_runs:
            return dict(name=name, pending='Not present in the pinned observer checkpoint; not a failure')
        received = root / 'download' / entry['directory'] / 'outputs'
        if not (received / 'execution.json').exists():
            return dict(name=name, pending='No collected execution receipt; not a failure')
        manifest = read(received / 'artifacts.sha256.json')
        for filename in ('execution.json', 'record.json'):
            assert sha(received / filename) == manifest['outputs/' + filename]
        execution, run = read(received / 'execution.json'), read(received / 'record.json')
        assert execution['case'] == spec and run['config'] == config
        assert execution['payload_sha256'] == entry['payload_sha256']
        assert execution['snapshot_sha256'] == SNAPSHOT and execution['binary_sha256'] == BINARY
        assert execution['preflight_sha256'] == sha(case / 'preflight/preflight.json')
        assert execution['record_sha256'] == sha(received / 'record.json')
        assert execution['status'] == 'completed' and execution['single_case_gates_passed']
        assert run['status'] == 'completed' and run['returncode'] == 0
        assert run == observed_runs[name]
        filenames = ['final.csv']  # All thirty are needed for independent boosts.
        primary_shock = (config['case'] == 'brio-wu'
                         and ((config['jitter'] == 0 and config['jitter_mode'] == 'planar')
                              or (config['jitter'] == .15 and config['jitter_mode'] == 'columns')))
        primary_vortex = config['case'] == 'orszag-tang' and config['jitter'] == 0
        if primary_shock or primary_vortex:
            filenames.append('geometry.json')
        if primary_vortex:
            filenames.append('projected_bins.json')
        remote = ['outputs/raw/' + name + '/' + filename for filename in filenames]
        local = out / 'download' / entry['directory']
        local.mkdir(parents=True)
        for filename in ('artifacts.sha256.json', 'execution.json', 'record.json'):
            target = local / 'outputs' / filename
            target.parent.mkdir(exist_ok=True)
            shutil.copyfile(received / filename, target)
        # Already-downloaded exact finals can be copied. Other raw files are
        # fetched from this exact remote workflow, never reused by historical hash.
        needed = []
        for filename in remote:
            source, target = received.parent / filename, local / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.exists() and sha(source) == manifest[filename]:
                shutil.copyfile(source, target)
            else:
                needed.append(filename)
        if needed:
            result = subprocess.run(shlex.split(args.client) + [
                'download', '-w', entry['workflow'], '-o', str(local), *needed,
            ], capture_output=True, text=True, timeout=1800)
            if result.returncode:
                raise RuntimeError('Download failed for ' + name + '; isolated partial directory retained')
        checked = {}
        for filename, remote_name in zip(filenames, remote):
            source = local / remote_name
            digest = sha(source)
            assert digest == run['sha256'][filename] == manifest[remote_name]
            target = out / name / filename
            target.parent.mkdir(exist_ok=True)
            shutil.copyfile(source, target)
            checked[filename] = digest
        return dict(name=name, workflow=entry['workflow'], run=run, verified=checked,
                    execution_sha256=sha(received / 'execution.json'),
                    manifest_sha256=sha(received / 'artifacts.sha256.json'))

    # Transport concurrency only; this submits/starts no computation.
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(collect, plan['cases']))
    runs = {row['name']: row.pop('run') for row in rows if 'run' in row}
    assert set(runs) == set(observed_runs), 'Pinned completed case lacks verified actual inputs'
    (out / 'runs.json').write_text(json.dumps(runs, indent=1) + '\n')
    report = dict(scope=provenance['scope'], completed=len(runs), expected=30,
                  observations=rows, full_m1_accepted=False)
    (out / 'input_receipts.json').write_text(json.dumps(report, indent=1) + '\n')
    print('Verified actual raw inputs for', len(runs), 'of 30 completed physics cases')


if __name__ == '__main__':
    main()
