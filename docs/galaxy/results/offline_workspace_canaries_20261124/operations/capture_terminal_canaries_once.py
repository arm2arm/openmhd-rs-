"""Finite GET-only acquisition of complete terminal cases, never test retries."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from log_command import run

OPS = Path(__file__).resolve().parent
ROOT = OPS.parents[1]
CASES = ROOT / 'results/offline_workspace_canary_cases_released_20261124_attempt01'
ADAPTER = ROOT / 'tools/galaxy_python_evidence/reana_metadata_readonly_adapter.py'
tag = sys.argv[1]
if not tag.isalnum():
    raise ValueError('Simple distinct finite capture tag')
inventory_path = OPS / ('inventory_' + tag) / 'summary.json'


def need(ok, label):
    if not ok:
        raise ValueError(label)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


release = load(OPS / 'root_release.json')
plan = load(CASES / 'plan.json')
inventory = load(inventory_path)
record = OPS / ('capture_batch_' + tag)
record.mkdir()
names = ('result.json', 'runtime.json', 'command.json', 'stdout.txt', 'stderr.txt',
         'child_result.json', 'child_raw.bin', 'artifacts.sha256.json')


def guard():
    need(sha((CASES / 'plan.json').read_bytes()) == release['plan_sha256'], 'Exact released canary plan')
    need(len(plan['cases']) == 2, 'Two released canaries only')
    need(sha((ROOT / 'reana/locked_dependencies.py').read_bytes()) == plan['cases'][0]['derivation']['installer_sha256'], 'Exact tested installer')
    expected = load(OPS / 'first_launch_a01/summary.json')['outcomes']
    need(all(inventory['cases'][i]['uuid'] == r['uuid'] and inventory['cases'][i]['workflow'] == r['workflow'] for i,r in expected.items()), 'Same first-started UUIDs')


def execute(entry, name, action, destination, remote=None):
    for attempt in range(1, 4):
        target = destination.with_name(destination.name + '.a' + str(attempt))
        label = name + '-a' + str(attempt)
        argv = ['/usr/bin/python3', '-B', str(ADAPTER), action, '--workflow', entry['workflow'], '--output', str(target)]
        if remote is not None:
            argv += ['--path', remote]
        code = run(label, argv, ROOT, timeout=350)
        command = OPS / 'commands' / label
        if code == 0:
            diagnostic = load(command / 'stdout.txt')
            need(diagnostic['outcome'] == 'success' and len(diagnostic['workflow_ids']) == 1, 'Successful original unique UUID GET')
            return dict(path=str(target.relative_to(OPS)), remote=remote, sha256=sha(target.read_bytes()),
                        bytes=target.stat().st_size, uuid=diagnostic['workflow_ids'][0], command='commands/' + label + '/command.json')
        diagnostic = load(command / 'stderr.txt')
        need((diagnostic['code'] in ('network_error', 'observation_changed', 'incomplete_body') or (diagnostic['code'] == 'http_error' and diagnostic.get('http_status') in (429,500,502,503,504))) and attempt < 3,
             'Bounded three transport-only GET attempts; preserve every failed partial')


def capture(entry):
    index, workflow = entry['directory'], entry['workflow']
    row = inventory['cases'][index]
    if row.get('status') not in ('finished', 'failed', 'stopped'):
        return dict(directory=index, status='not_terminal_in_this_inventory')
    base = OPS / 'captures' / index
    if base.exists():
        complete = sorted(base.glob('attempt*/capture.json'))
        if complete:
            need(len(complete) == 1 and load(complete[0])['uuid'] == row['uuid'], 'One original complete case capture')
            return dict(directory=index, status='existing_complete_case', capture=str(complete[0].relative_to(OPS)))
        return dict(directory=index, status='prior_unclosed_capture_preserved')
    dest = base / 'attempt01'
    dest.mkdir(parents=True)
    original = {p.relative_to(CASES / index).as_posix(): dict(sha256=sha(p.read_bytes()), bytes=p.stat().st_size)
                for p in (CASES / index).rglob('*') if p.is_file() and not p.is_symlink()}
    need(original == entry['files'], 'Exact released case input inventory')
    before = execute(entry, 'capture-canary-' + index + '-before', 'observe', dest / 'before.json')
    observed = load(OPS / before['path'])
    need(before['uuid'] == row['uuid'] and observed['origin'] == 'server' and len(observed['matches']) == 1
         and observed['matches'][0]['workflow'] == workflow and observed['matches'][0]['version'] == 1
         and observed['matches'][0]['status'] == row['status'], 'Same original terminal inventory identity')
    artifacts = []
    for name in names:
        artifacts.append(execute(entry, 'capture-canary-' + index + '-' + name.replace('.', '-'), 'download', dest / name, 'outputs/' + name))
    auxiliary = dest / 'offline_runtime'
    auxiliary.mkdir()
    legacy = Path('/Users/arm2arm/orca/workspaces/openmhd-rs-/m1-run-alfv-n-wave-and-field-loop-benchmarks/results/limiter_campaign_tools_20261113/reana-command.py')
    need(sha(legacy.read_bytes()) == '07c7ad769deb0044db72af40f751399a9950499793511d20f43df1b090e9853e', 'Pinned legacy read-only downloader')
    aux_label = 'capture-canary-' + index + '-auxiliary-offline-runtime'
    aux_code = run(aux_label, ['/usr/bin/python3', '-B', str(legacy), 'download', '--workflow', row['uuid'],
        '--output-directory', str(auxiliary), 'runtime/cargo/config.toml', 'runtime/locked-dependencies/installed.json',
        'runtime/locked-dependencies/status.json'], ROOT, 350)
    need(aux_code == 0, 'Actual auxiliary read-only download succeeded')
    aux_files = {p.relative_to(auxiliary).as_posix(): dict(sha256=sha(p.read_bytes()), bytes=p.stat().st_size)
                 for p in auxiliary.rglob('*') if p.is_file()}
    need(set(aux_files) == {'runtime/cargo/config.toml', 'runtime/locked-dependencies/installed.json', 'runtime/locked-dependencies/status.json'}, 'Exact auxiliary bytes')
    after = execute(entry, 'capture-canary-' + index + '-after', 'observe', dest / 'after.json')
    final = load(OPS / after['path'])
    need(final['matches'] == observed['matches'] and all(r['uuid'] == row['uuid'] for r in artifacts + [after]), 'Eight-body coherent same-UUID terminal sandwich')
    bodies = {Path(r['remote']).name: (OPS / r['path']).read_bytes() for r in artifacts}
    need(json.loads(bodies['artifacts.sha256.json']) == {'outputs/' + name: sha(body) for name, body in bodies.items()
         if name != 'artifacts.sha256.json'}, 'Exact ordinary seven-body output manifest')
    result = json.loads(bodies['result.json'])
    if result.get('status') != 'passed':
        try:
            save(OPS / 'STOP_SUBMISSION', dict(reason='Actual nonpassing source leaf capsule', directory=index,
                 workflow=workflow, uuid=row['uuid'], status=result.get('status'), utc=datetime.now(timezone.utc).isoformat()))
        except FileExistsError:
            pass
    value = dict(workflow=workflow, uuid=row['uuid'], status=row['status'], before=before, after=after,
                 artifacts=artifacts, auxiliary=dict(directory=str(auxiliary.relative_to(OPS)), files=aux_files, command='commands/' + aux_label + '/command.json'), inventory_sha256=sha(inventory_path.read_bytes()), workflow_mutations=False, component_accepted=False)
    save(dest / 'capture.json', value)
    return dict(directory=index, status='complete', result=result.get('status'), capture=str((dest / 'capture.json').relative_to(OPS)))


guard()
rows = []
with ThreadPoolExecutor(max_workers=2) as pool:
    futures = {pool.submit(capture, entry): entry for entry in plan['cases']}
    for future in as_completed(futures):
        entry = futures[future]
        try:
            rows.append(future.result())
        except BaseException as error:
            rows.append(dict(directory=entry['directory'], status='capture_error', error_type=type(error).__name__))
guard()
counts = {status: sum(r['status'] == status for r in rows) for status in sorted({r['status'] for r in rows})}
save(record / 'summary.json', dict(utc=datetime.now(timezone.utc).isoformat(), counts=counts, cases=rows,
     inventory_sha256=sha(inventory_path.read_bytes()), workflow_mutations=False, component_accepted=False))
print(json.dumps(dict(counts=counts, component_accepted=False)), flush=True)
