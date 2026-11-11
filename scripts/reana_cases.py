#!/usr/bin/env python3
"""Prepare, submit and monitor independent REANA case workflows (no local evolution)."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time
import uuid

from run_m1_wave_loop import ROOT, PHYSICAL_PROFILES, riemann_arguments

IMAGE = 'gitlab-p4n.aip.de:5005/p4nreana/reana-env@sha256:aebd7911df9e1e97ad67d15f4c32ab23996000282183fad3bf7a480756522bd7'
TERMINAL = {'finished', 'failed', 'stopped', 'deleted'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    temporary.replace(path)


def load(path):
    return json.loads(path.read_text())


def verify_preflight(snapshot, directory):
    receipt = load(directory/'preflight.json')
    execution = load(directory/'execution.json')
    runtime = load(directory/'runtime.json')
    artifacts = load(directory/'artifacts.sha256.json')
    for name in ('preflight.json', 'execution.json', 'runtime.json'):
        if sha(directory/name) != artifacts['outputs/'+name]:
            raise ValueError('Changed preflight artifact: '+name)
    if (execution['status'] != 'completed' or execution['study'] != 'm1-fanout-preflight'
            or execution['snapshot_sha256'] != sha(snapshot)
            or receipt['snapshot_sha256'] != sha(snapshot)
            or receipt['runtime_sha256'] != sha(directory/'runtime.json')
            or execution['runtime_sha256'] != receipt['runtime_sha256']
            or receipt['image'] != IMAGE or runtime['image'] != IMAGE
            or receipt['machine'] != runtime['machine']):
        raise ValueError('Missing successful matching preflight')
    # Check the actual required commands, not an untrusted success flag/count.
    spec = importlib.util.spec_from_file_location('fanout_preflight', ROOT/'reana/remote.py')
    remote = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(remote)
    def normalize(command):
        return ['python', *command[1:]] if Path(command[0]).name.startswith('python') else command
    expected = [normalize(c) for c in remote.commands('m1-fanout-preflight', 1)]
    checks = execution['commands']
    if (receipt['commands'] != checks or any(c['returncode'] != 0 for c in checks)
            or [normalize(c['command']) for c in checks] != expected
            or receipt['binary_sha256'] != artifacts['outputs/vector-potential']):
        raise ValueError('Incomplete or failed prerequisite commands')
    return receipt


def validate_case(spec):
    if spec['kind'] not in ('wave', 'physics'):
        raise ValueError('Unknown case kind')
    c, resources, options = (spec[k] for k in ('config', 'resources', 'options'))
    keys = ({'name', 'case', 'profile', 'n', 'jitter', 'parallel', 'motion_family', 'mesh_velocity', 'boost', 'dt', 'target'}
            if spec['kind'] == 'wave' else {'name', 'case', 'profile', 'n', 'ny', 'jitter', 'jitter_mode', 'boost', 'time'})
    if set(c)-{'riemann_solver'} != keys:
        raise ValueError('Missing or unsupported case configuration fields')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', c['name']) or c['name'] in ('.', '..'):
        raise ValueError('Unsafe case name')
    if c['profile'] not in PHYSICAL_PROFILES or not isinstance(c['n'], int) or c['n'] < 2:
        raise ValueError('Invalid profile/resolution')
    riemann_arguments(c)
    if not 1 <= resources['threads'] <= 24 or type(resources['threads']) is not int:
        raise ValueError('Threads per case must be an integer in 1..24')
    if not re.fullmatch(r'[1-9][0-9]*(?:Gi|G|Mi|M)', resources['memory']):
        raise ValueError('Specify explicit positive per-case memory')
    if not math.isfinite(resources['timeout_seconds']) or resources['timeout_seconds'] <= 0:
        raise ValueError('Specify a finite positive case timeout')
    if (set(options) != {'accelerated_projection', 'projection_screening'}
            or not isinstance(options['accelerated_projection'], bool)
            or not math.isfinite(options['projection_screening']) or options['projection_screening'] < 0):
        raise ValueError('Invalid projection options')
    if (options['accelerated_projection'] or options['projection_screening']) and c['profile'] not in PHYSICAL_PROFILES[-2:]:
        raise ValueError('Projection options require a projected-rate profile')
    target = c['target'] if spec['kind'] == 'wave' else c['time']
    allowed = ('alfven', 'loop', 'smooth') if spec['kind'] == 'wave' else ('brio-wu', 'orszag-tang')
    if c['case'] not in allowed or not math.isfinite(target) or target <= 0:
        raise ValueError('Invalid case/time')
    if len(c['boost']) != 3 or any(not math.isfinite(x) for x in c['boost']):
        raise ValueError('Invalid boost')
    if not math.isfinite(c['jitter']) or not 0 <= c['jitter'] <= .45:
        raise ValueError('Invalid mesh jitter')
    if spec['kind'] == 'wave':
        if (len(c['mesh_velocity']) != 2 or any(not math.isfinite(x) for x in c['mesh_velocity'])
                or not math.isfinite(c['parallel']) or c['motion_family'] not in ('fixed', 'comoving')
                or (c['dt'] is not None and (not math.isfinite(c['dt']) or c['dt'] <= 0))):
            raise ValueError('Invalid wave configuration')
    elif c['ny'] != (4 if c['case'] == 'brio-wu' else c['n']) or c['jitter_mode'] not in ('planar', 'columns'):
        raise ValueError('Invalid physics mesh')


def prepare(snapshot_dir, preflight_dir, specifications, destination, prefix):
    if destination.exists():
        raise ValueError('Use a fresh plan directory')
    if not specifications or not re.fullmatch(r'[a-z0-9-]{1,35}', prefix):
        raise ValueError('Nonempty cases and a short lowercase workflow prefix required')
    snapshot = snapshot_dir/'snapshot.json'
    metadata = load(snapshot)
    receipt = verify_preflight(snapshot, preflight_dir)
    if sha(preflight_dir/'vector-potential') != receipt['binary_sha256']:
        raise ValueError('Changed preflight binary')
    for name in ('reana/case.py', 'reana/remote.py', 'scripts/reana_cases.py',
                 'scripts/run_m1_wave_loop.py', 'scripts/run_m1_physics.py'):
        if sha(ROOT/name) != metadata['source_sha256'][name]:
            raise ValueError('Current execution code differs from preflight: '+name)
    names = set()
    for spec in specifications:
        validate_case(spec)
        if spec['config']['name'] in names:
            raise ValueError('Duplicate case name')
        names.add(spec['config']['name'])
    wave_configs = {s['config']['name']: s['config'] for s in specifications if s['kind'] == 'wave'}
    wave_pairs(wave_configs)
    if len({c['profile'] for c in wave_configs.values()}) > 1:
        raise ValueError('Use a separate plan per wave profile')
    by_name = {s['config']['name']: s for s in specifications}
    for name, spec in by_name.items():
        other = name.removesuffix('_base')+'_boost'
        if name.endswith('_base') and other in by_name:
            paired = by_name[other]
            expected = dict(spec['config'], name=other, boost=[2., -1., 0.])
            if spec['kind'] == 'wave':
                expected['mesh_velocity'] = [spec['config']['mesh_velocity'][k]+expected['boost'][k] for k in range(2)]
            if (any(spec['config']['boost']) or spec['kind'] != paired['kind']
                    or paired['config'] != expected or spec['options'] != paired['options']):
                raise ValueError('Mismatched boost-pair configuration/options')
    destination.mkdir(parents=True)
    plan = {'schema': 1, 'snapshot_sha256': sha(snapshot), 'cases': [],
            'analysis_sha256': {n: d for n, d in metadata['source_sha256'].items()
                                if n.startswith(('scripts/', 'benchmarks/'))},
            'scope': 'Independent workflows; a completed subset is not M1 acceptance.'}
    batch = uuid.uuid4().hex[:12]
    for index, spec in enumerate(specifications):
        directory = destination/f'case-{index:04d}'
        directory.mkdir()
        parts = {'source.tar.gz': metadata['archives']['source.tar.gz']['parts'],
                 'vector-potential': []}
        for name in parts['source.tar.gz']:
            if sha(snapshot_dir/name) != metadata['upload_sha256'][name]:
                raise ValueError('Changed source part')
            shutil.copyfile(snapshot_dir/name, directory/name)
        with (preflight_dir/'vector-potential').open('rb') as stream:
            while data := stream.read(1024*1024):
                name = f'vector-potential.part{len(parts["vector-potential"]):03d}'
                (directory/name).write_bytes(data)
                parts['vector-potential'].append(name)
        shutil.copyfile(snapshot, directory/'snapshot.json')
        shutil.copyfile(ROOT/'reana/case.py', directory/'case.py')
        (directory/'preflight').mkdir()
        for name in ('preflight.json', 'execution.json', 'runtime.json', 'artifacts.sha256.json'):
            shutil.copyfile(preflight_dir/name, directory/'preflight'/name)
        dump(directory/'case.json', spec)
        inputs = {str(p.relative_to(directory)): sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}
        dump(directory/'payload.json', {'input_sha256': inputs, 'parts': parts})
        step = dict(name='one-case', environment=IMAGE, compute_backend='kubernetes',
                    kubernetes_memory_limit=spec['resources']['memory'],
                    kubernetes_cpu_request=str(spec['resources']['threads']),
                    kubernetes_cpu_limit=str(spec['resources']['threads']),
                    commands=['python3 case.py'])
        workflow = {'version': '0.9.0', 'inputs': {'files': [*inputs, 'payload.json']},
                    'workflow': {'type': 'serial', 'specification': {'steps': [step]}},
                    'outputs': {'files': ['outputs/execution.json', 'outputs/record.json', 'outputs/artifacts.sha256.json']}}
        # JSON is a YAML subset; avoid introducing a local YAML dependency.
        dump(directory/'reana.yaml', workflow)
        plan['cases'].append({'directory': directory.name, 'specification': spec,
                              'workflow': f'{prefix}-{batch}-{index:04d}.1',
                              'payload_sha256': sha(directory/'payload.json'),
                              'workflow_sha256': sha(directory/'reana.yaml')})
    dump(destination/'plan.json', plan)
    return plan


def client(command, arguments, cwd=None):
    result = subprocess.run([*command, *arguments], cwd=cwd, capture_output=True, text=True, timeout=300)
    if result.returncode:
        # Never echo client output: credentials may be present in SDK errors.
        raise RuntimeError(f'REANA {arguments[0]} failed (exit {result.returncode}); inspect workflow status before retrying')
    return result.stdout


def submit(directory, command):
    state_file = directory/'submission.json'
    if state_file.exists():
        raise ValueError('Submission already attempted; inspect/recover, never implicitly duplicate workflows')
    plan = load(directory/'plan.json')
    for entry in plan['cases']:
        case = directory/entry['directory']
        if sha(case/'payload.json') != entry['payload_sha256'] or sha(case/'reana.yaml') != entry['workflow_sha256']:
            raise ValueError('Changed workflow plan')
        for name, digest in load(case/'payload.json')['input_sha256'].items():
            if sha(case/name) != digest:
                raise ValueError('Changed case input')
    state = {e['workflow']: {'status': 'submission pending'} for e in plan['cases']}
    dump(state_file, state)  # Preserve identities even if interrupted during upload/start.
    # Transport concurrency limits local HTTP clients, never remote running cases.
    with ThreadPoolExecutor(max_workers=min(8, len(plan['cases']))) as pool:
        futures = {pool.submit(client, command, ['run', '-w', e['workflow'].removesuffix('.1')],
                               directory/e['directory']): e for e in plan['cases']}
        for future in as_completed(futures):
            entry = futures[future]
            try:
                future.result()
                state[entry['workflow']] = {'status': 'submitted'}
            except Exception as error:
                state[entry['workflow']] = {'status': 'submission uncertain', 'error': str(error)}
            dump(state_file, state)
    return state


def wave_pairs(configs):
    pairs = []
    for name, c in configs.items():
        other = name.removesuffix('_base')+'_boost'
        if not name.endswith('_base') or other not in configs:
            continue
        b = configs[other]
        expected = dict(c, name=other, boost=[2., -1., 0.],
                        mesh_velocity=[c['mesh_velocity'][k]+[2., -1.][k] for k in range(2)])
        if any(c['boost']) or b != expected:
            raise ValueError('Mismatched boost-pair configurations')
        pairs.append(dict(names=[name, other], case=c['case'], profile=c['profile'], n=c['n'],
                          jitter=c['jitter'], parallel=c['parallel'], motion=c['motion_family'],
                          dt=c['dt'], time=c['target']))
    return pairs


def evaluate_ready(raw, specifications, runs):
    """Only complete pairs/ladders are evaluated; absence is never a physical failure."""
    failures = [n for n, r in runs.items() if r['status'] != 'completed'
                or not r.get('positive_and_conservative', False) or not r.get('state_and_diagnostic_gates', True)]
    summaries = {}
    for kind in ('wave', 'physics'):
        configs = {s['config']['name']: s['config'] for s in specifications if s['kind'] == kind}
        records = {n: copy.deepcopy(r) for n, r in runs.items() if n in configs}
        if not records:
            continue
        if kind == 'wave':
            from run_m1_wave_loop import evaluate
            profiles = {c['profile'] for c in configs.values()}
            if len(profiles) != 1:
                raise ValueError('Use a separate plan per wave profile')
            profile = next(iter(profiles))
            pairs = [p for p in wave_pairs(configs) if all(n in records for n in p['names'])]
            temporal_names = [f'temporal_{profile}_v{v}_j{j}_dt{dt}' for v in (0., 1.)
                              for j in (0., .15) for dt in (.0004, .0002, .0001, .000025)]
            summary = evaluate(raw, records, pairs, profile, all(n in records for n in temporal_names))
            failures += [p['names'] for p in summary['pairs'] if p['status'].startswith('fail')
                         or p['status'] == 'normalization clarification pending']
            failures += [s for s in summary['alfven_convergence'] if s['gate'].startswith('fail')]
            summary.pop('runs')
        else:
            from run_m1_physics import evaluate
            summary = evaluate(raw, configs, records, False, load(ROOT/'benchmarks/m0/packet.json'))
            failures += [p['names'] for p in summary['boost_pairs'] if p['status'] == 'fail']
            failures += [f for f in summary['profile_families'] if f['primary_profile_gate'] and f['status'] == 'fail']
        summaries[kind] = summary
    return {'summaries': summaries, 'verified_required_failure': bool(failures), 'failures': failures,
            'completed_cases': len(runs), 'expected_cases': len(specifications), 'full_m1_accepted': False}


def inspect(directory, command, cancel=True):
    plan = load(directory/'plan.json')
    for name, digest in plan['analysis_sha256'].items():
        if sha(ROOT/name) != digest:
            raise ValueError('Analysis differs from the frozen source: '+name)
    download = directory/'download'
    download.mkdir(exist_ok=True)
    raw = directory/'raw'
    raw.mkdir(exist_ok=True)
    runs, states, errors = {}, {}, {}
    def collect(entry):
        workflow = entry['workflow']
        name = entry['specification']['config']['name']
        try:
            status = json.loads(client(command, ['status', '-w', workflow, '--json', '-v']))
            if len(status) != 1:
                raise ValueError('Ambiguous workflow status')
            if status[0]['status'] not in TERMINAL:
                return workflow, status[0], None, None
            local = download/entry['directory']
            local.mkdir(exist_ok=True)
            filenames = ['outputs/artifacts.sha256.json', 'outputs/execution.json', 'outputs/record.json']
            client(command, ['download', '-w', workflow, '-o', str(local.resolve()), *filenames])
            hashes = load(local/filenames[0])
            for filename in filenames[1:]:
                if sha(local/filename) != hashes[filename]:
                    raise ValueError('Changed downloaded artifact')
            execution = load(local/'outputs/execution.json')
            record = load(local/'outputs/record.json')
            if (execution['case'] != entry['specification'] or record['config'] != entry['specification']['config']
                    or execution['payload_sha256'] != entry['payload_sha256']
                    or execution['snapshot_sha256'] != plan['snapshot_sha256']
                    or execution['record_sha256'] != sha(local/'outputs/record.json')):
                raise ValueError('Mismatched execution provenance')
            if record['status'] == 'completed':
                filename = f'outputs/raw/{name}/final.csv'
                final = local/filename
                expected = record['sha256']['final.csv']
                if not final.exists() or sha(final) != expected:
                    client(command, ['download', '-w', workflow, '-o', str(local.resolve()), filename])
                if sha(final) != expected or expected != hashes[filename]:
                    raise ValueError('Changed final snapshot')
                (raw/name).mkdir(exist_ok=True)
                shutil.copyfile(final, raw/name/'final.csv')
            return workflow, status[0], record, None
        except Exception as error:
            return workflow, status[0] if 'status' in locals() and len(status) == 1 else None, None, str(error)
    with ThreadPoolExecutor(max_workers=min(8, len(plan['cases']))) as pool:
        for future in as_completed([pool.submit(collect, e) for e in plan['cases']]):
            workflow, status, record, error = future.result()
            if status is not None:
                states[workflow] = status
            if record is not None:
                runs[record['config']['name']] = record
            if error:
                errors[workflow] = error
    report = evaluate_ready(raw, [e['specification'] for e in plan['cases']], runs)
    report.update(workflow_states=states, observation_errors=errors,
                  execution_failures=[n for n, s in states.items() if s['status'] in ('failed', 'stopped', 'deleted')],
                  cancellation={})
    dump(directory/'runs.json', runs)
    dump(directory/'checkpoint.json', report)  # Save the triggering evidence before cancellation.
    if cancel and (report['verified_required_failure'] or report['execution_failures']):
        failure = directory/'first_failure.json'
        if not failure.exists():
            dump(failure, report)  # Later network errors must not erase the stop reason.
        for entry in plan['cases']:
            workflow = entry['workflow']
            if states.get(workflow, {}).get('status') in TERMINAL:
                continue
            try:
                client(command, ['stop', '-w', workflow, '--force'])
                report['cancellation'][workflow] = 'stop requested; verify authoritative status'
            except Exception as error:
                report['cancellation'][workflow] = str(error)
        dump(directory/'checkpoint.json', report)
    report['all_terminal'] = len(states) == len(plan['cases']) and all(s['status'] in TERMINAL for s in states.values())
    dump(directory/'checkpoint.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'submit', 'check', 'watch'))
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--snapshot', type=Path)
    parser.add_argument('--preflight', type=Path)
    parser.add_argument('--cases', type=Path, help='JSON list of explicit case specifications')
    parser.add_argument('--prefix', default='openmhd-cases')
    parser.add_argument('--client', default='reana-client', help='Client argv string; no tokens in arguments')
    parser.add_argument('--observe-only', action='store_true', help='Do not stop sibling workflows')
    args = parser.parse_args()
    directory = args.directory.resolve()
    if args.action == 'prepare':
        if not all((args.snapshot, args.preflight, args.cases)):
            parser.error('prepare requires snapshot, preflight and cases')
        prepare(args.snapshot.resolve(), args.preflight.resolve(), load(args.cases), directory, args.prefix)
    elif args.action == 'submit':
        submit(directory, shlex.split(args.client))
    else:
        while True:
            report = inspect(directory, shlex.split(args.client), not args.observe_only)
            print(json.dumps({k: report[k] for k in ('completed_cases', 'expected_cases', 'verified_required_failure',
                                                     'execution_failures', 'observation_errors', 'all_terminal')}), flush=True)
            if args.action != 'watch' or report['all_terminal']:
                break
            time.sleep(30)


if __name__ == '__main__':
    main()
