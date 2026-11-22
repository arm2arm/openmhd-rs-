"""Verify completed REANA campaign inputs/receipts; no evolution or production imports.

Run from the repository root. The registered specifications argument must be the
immutable candidate's exported case list. Output is a new JSON file, never an
overwrite. Raw output files not downloaded are explicitly reported as unverified;
their retained remote manifest is not a substitute for reading their bytes.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


SNAPSHOT = 'b67ce03779a194099983b7ff07c0cafed23e9ea3a9051047492d072255e0160f'
BINARY = '18afcf0308338e2ea0ea7ef5e03dba46af9d7025f3ccf4a6a48ebbfe800d0725'
COUNTS = dict(medium=48, mean=24, waves=112, physics=30)


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=COUNTS)
    parser.add_argument('directory', type=Path)
    parser.add_argument('specifications', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    assert not args.output.exists(), 'Use a fresh output'
    root = args.directory
    plan = read(root/'plan.json')
    runs = read(root/'runs.json')
    checkpoint = read(root/'checkpoint.json')
    assert plan['snapshot_sha256'] == SNAPSHOT
    assert [row['specification'] for row in plan['cases']] == read(args.specifications)
    entries = {row['specification']['config']['name']: row for row in plan['cases']}
    assert len(entries) == len(runs) == COUNTS[args.phase]
    assert set(entries) == set(runs)
    assert checkpoint['all_terminal'] and not checkpoint['verified_required_failure']
    assert not checkpoint['failures'] and not checkpoint['execution_failures']
    assert checkpoint['completed_cases'] == checkpoint['expected_cases'] == len(runs)
    assert not checkpoint['full_m1_accepted']
    receipts = {}
    counters = {key: 0 for key in ('steps', 'rejected_geometry', 'rejected_state',
                                  'rejected_cfl', 'hll_fallbacks')}
    maximum_budget = 0.
    old = Path('results')/('followup_iter-'+args.phase+'_20261117')/'runs.json'
    old_runs = read(old) if old.exists() else {}
    same_old_final = 0
    for name, run in runs.items():
        entry = entries[name]
        case = root/entry['directory']
        spec = entry['specification']
        assert read(case/'case.json') == spec
        assert spec['config'] == run['config']
        assert spec['config']['profile'] == 'bulk-frame-heun-quadratic-v1'
        assert spec['config']['riemann_solver'] == 'hlld-pressure'
        assert spec['options'] == dict(accelerated_projection=False,
                                      projection_screening=1., potential_limiter='smooth-extrema')
        assert sha(case/'payload.json') == entry['payload_sha256']
        assert sha(case/'reana.yaml') == entry['workflow_sha256']
        payload = read(case/'payload.json')
        # Read every staged input, including source and binary parts, rather
        # than relying only on the remote launcher's self-reported identity.
        for filename, digest in payload['input_sha256'].items():
            assert sha(case/filename) == digest, (name, filename)
        snapshot = read(case/'snapshot.json')
        assert sha(case/'snapshot.json') == SNAPSHOT
        for filename, parts in payload['parts'].items():
            digest = hashlib.sha256()
            for part in parts:
                digest.update((case/part).read_bytes())
            expected = BINARY if filename == 'vector-potential' else snapshot['archives'][filename]['sha256']
            assert digest.hexdigest() == expected, (name, filename)
        workflow = read(case/'reana.yaml')
        assert set(workflow['inputs']['files']) == set(payload['input_sha256']) | {'payload.json'}
        step, = workflow['workflow']['specification']['steps']
        resources = spec['resources']
        assert step['kubernetes_memory_limit'] == resources['memory']
        assert step['kubernetes_cpu_request'] == step['kubernetes_cpu_limit'] == str(resources['threads'])
        assert resources['threads'] in (2, 4) and resources['timeout_seconds'] > 0
        command = run['command']
        for flag, value in (('--threads', resources['threads']), ('--profile', spec['config']['profile']),
                            ('--riemann', 'hlld-pressure'), ('--potential-limiter', 'smooth-extrema')):
            assert command[command.index(flag)+1] == str(value), (name, flag)
        assert float(command[command.index('--projection-screening')+1]) == 1.
        assert '--accelerated-projection' not in command and '--trial-step-fraction' not in command
        output = root/'download'/entry['directory']/'outputs'
        execution = read(output/'execution.json')
        assert execution['status'] == 'completed' and execution['single_case_gates_passed']
        assert execution['case'] == spec and execution['snapshot_sha256'] == SNAPSHOT
        assert execution['binary_sha256'] == BINARY
        assert execution['payload_sha256'] == entry['payload_sha256']
        assert execution['preflight_sha256'] == sha(case/'preflight/preflight.json')
        assert execution['record_sha256'] == sha(output/'record.json')
        assert read(output/'record.json') == run
        assert run['status'] == 'completed' and run['returncode'] == 0
        summary = run['summary']
        assert summary['completed'] and summary['profile'] == spec['config']['profile']
        assert summary['potential_limiter'] == 'smooth-extrema-v1'
        assert summary['riemann_solver'] == 'hlld-pressure-blend-v1'
        assert summary['projection_screening'] == 1.
        assert 'projection_solver' not in summary and 'trial_step_fraction' not in summary
        history = run['history']
        target = spec['config'].get('time', spec['config'].get('target'))
        assert history[0]['time'] == 0 and history[-1]['time'] == target
        assert all(x['time'] < y['time'] for x, y in zip(history, history[1:]))
        for row in history:
            diagnostic = row['diagnostics']
            assert diagnostic['rho_min'] > 0 and diagnostic['p_min'] > 0
            budget = max(abs(value) for value in diagnostic['normalized_budget'])
            assert math.isfinite(budget) and budget <= 1e-10
            maximum_budget = max(maximum_budget, budget)
        if args.phase == 'physics':
            assert run['state_and_diagnostic_gates'] and all(run['diagnostic_checks'].values())
        else:
            assert run['positive_and_conservative']
        for key in counters:
            counters[key] += summary[key]
        manifest = read(output/'artifacts.sha256.json')
        checked, absent = [], []
        for filename, digest in manifest.items():
            relative = Path(filename)
            assert relative.parts[0] == 'outputs' and '..' not in relative.parts
            path = output.joinpath(*relative.parts[1:])
            if path.exists():
                assert sha(path) == digest, (name, filename)
                checked.append(filename)
            else:
                absent.append(filename)
        final = root/'raw'/name/'final.csv'
        assert sha(final) == run['sha256']['final.csv'] == manifest['outputs/raw/'+name+'/final.csv']
        assert manifest['outputs/execution.json'] == sha(output/'execution.json')
        assert manifest['outputs/record.json'] == sha(output/'record.json')
        same_old_final += old_runs.get(name, {}).get('sha256', {}).get('final.csv') == sha(final)
        receipts[name] = dict(workflow=entry['workflow'], specification=spec,
            payload_sha256=entry['payload_sha256'], workflow_sha256=entry['workflow_sha256'],
            execution_sha256=sha(output/'execution.json'), execution=execution,
            artifact_manifest_sha256=sha(output/'artifacts.sha256.json'), artifacts=manifest,
            checked_downloads=checked, not_downloaded_not_byte_verified=absent,
            final_csv_sha256=sha(final), staged_input_files_verified=len(payload['input_sha256']))
    result = dict(scope='Read-only staged-input, execution-receipt and downloaded-output verification; no new evolution, no M1 acceptance.',
        phase=args.phase, cases=len(runs), snapshot_sha256=SNAPSHOT, binary_sha256=BINARY,
        analysis_source_sha256=sha(Path(__file__)), plan_sha256=sha(root/'plan.json'),
        run_map_sha256=sha(root/'runs.json'), checkpoint_sha256=sha(root/'checkpoint.json'),
        registered_specifications_sha256=sha(args.specifications),
        resource_scope='Kubernetes declarations and recorded cgroup values; cpu.max may report max. Requested Rayon thread count verified in each command.',
        counters=counters, maximum_recorded_budget=maximum_budget,
        final_csv_byte_identical_to_campaign_a=same_old_final,
        receipts=receipts, all_verified=True, full_m1_accepted=False)
    args.output.write_text(json.dumps(result, indent=1, allow_nan=False)+'\n')
    print(args.phase, len(runs), 'receipts verified; identical A final CSVs:', same_old_final)


if __name__ == '__main__':
    main()
