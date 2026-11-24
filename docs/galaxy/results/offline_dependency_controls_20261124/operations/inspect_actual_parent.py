"""Inspect retained bytes only; do not import a project module or run a test."""
import ast
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OPS = Path(__file__).resolve().parent
SOURCE = ROOT / 'results/offline_dependency_controls_source_20261124_attempt01'
CAPTURE = ROOT / 'results/offline_dependency_controls_preflight_observation_20261124_attempt01'
WORKFLOW = 'openmhd-offline11-00eb0d42ca1d-preflight.1'
UUID = '918f1918-ce69-4de9-9c51-c937c3ba55eb'
errors = []
checks = 0


def check(condition, label):
    global checks
    checks += 1
    if not condition:
        errors.append(label)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


snapshot_raw = (SOURCE / 'snapshot.json').read_bytes()
snapshot = json.loads(snapshot_raw)
certificate_raw = (CAPTURE / 'certificate.json').read_bytes()
certificate = json.loads(certificate_raw)
buffers = {name: base64.b64decode(raw, validate=True)
           for name, raw in certificate['buffers'].items()}
check(set(buffers) == set(certificate['capture_sha256']), 'Exact certificate inventory')
for name, raw in buffers.items():
    check(sha(raw) == certificate['capture_sha256'][name], 'Embedded digest: ' + name)
    check((CAPTURE / name).read_bytes() == raw, 'Retained original: ' + name)
check(certificate['snapshot_sha256'] == sha(snapshot_raw), 'Actual source snapshot')
check(certificate['component_accepted'] is False
      and certificate['physical_evolutions_run'] is False, 'Nonaccepting certificate')
check(len(snapshot['source_sha256']) == 356, 'Exact frozen source count')
for name, digest in snapshot['source_sha256'].items():
    check(sha((ROOT / name).read_bytes()) == digest, 'Current frozen source: ' + name)
check(sha((SOURCE / 'source.tar.gz').read_bytes()) == snapshot['archive_sha256'], 'Frozen archive')
check(sha((SOURCE / 'job.py').read_bytes()) == snapshot['job_sha256'], 'Frozen job')
for name in ('plan.json', 'submission.json', '0000/payload.json', '0000/reana.yaml', '0000/case.json'):
    check((SOURCE / 'preflight' / name).read_bytes() == buffers[Path(name).name], 'Original parent input: ' + name)

manifest = json.loads(buffers['artifacts/artifacts.sha256.json'])
expected = {name: sha(raw) for name, raw in buffers.items()
            if name.startswith('artifacts/') and name != 'artifacts/artifacts.sha256.json'}
check(manifest == {'outputs/' + Path(name).name: digest for name, digest in expected.items()}, 'Seven actual artifact digests')
for name in ('server-before.json', 'server-after.json'):
    observed = json.loads(buffers[name])
    check(observed['origin'] == 'server' and observed['matches'] == [dict(
        name=WORKFLOW.removesuffix('.1'), workflow=WORKFLOW, version=1, status='finished')], 'Unique finished parent: ' + name)
transport = json.loads(buffers['transport.json'])
check(len(transport['attempts']) == 10, 'Exact ten acquisition transports')
for index, row in enumerate(transport['attempts']):
    check(row['index'] == index and row['workflow'] == WORKFLOW
          and row['outcome'] == 'success' and type(row['returncode']) is int
          and row['returncode'] == 0, 'Successful transport: ' + str(index))
    diagnostic = json.loads(buffers[row['stdout']['path']])
    check(diagnostic['workflow_ids'] == [UUID] and diagnostic['outcome'] == 'success', 'Transport UUID: ' + str(index))
    check(sha(buffers[row['output']]) == row['download_sha256'], 'Transport body: ' + str(index))
    for stream in ('stdout', 'stderr'):
        check(sha(buffers[row[stream]['path']]) == row[stream]['sha256'], 'Transport log: ' + str(index) + stream)

result = json.loads(buffers['artifacts/result.json'])
envelope = json.loads(buffers['artifacts/child_result.json'])
child_raw = buffers['artifacts/child_raw.bin']
value = json.loads(child_raw)
check(result['status'] == 'completed' and result['passed'] is True
      and result['outcome'] == 'success' and result['returncode'] == 0
      and result['case']['kind'] == 'preflight', 'Actual successful import-only result')
check(envelope['state'] == 'valid' and envelope['problem'] is None
      and envelope['raw_bytes'] == len(child_raw) and envelope['raw_sha256'] == sha(child_raw)
      and envelope['value'] == value == result['child_result'], 'Raw child and outer result join')
check(value['kind'] == 'preflight' and value['status'] == 'completed' and value['passed'] is True
      and value['physical_evolutions_run'] is False and value['component_accepted'] is False,
      'Import-only child scope')
check(len(value['parsed_files']) == len(set(value['parsed_files'])) == 216, '216 parsed/compiled paths')
check(value['test_selectors'] == snapshot['tests'] and len(snapshot['tests']) == 11
      and len(set(snapshot['tests'])) == 11 and type(value['resolved_tests']) is int
      and value['resolved_tests'] == 11, '11 exact resolved leaves')
check(value['executed_identities'] == [snapshot['test_identities'][s] for s in snapshot['tests']], 'Exact resolved runtime identities')
derived = []
for name in snapshot['test_files']:
    tree = ast.parse((ROOT / name).read_bytes(), filename=name)
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        derived.extend(name[:-3].replace('/', '.') + '.' + cls.name + '.' + node.name
                       for node in cls.body if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'))
check(sorted(derived) == snapshot['tests'], 'Independent direct-method AST catalog')
command = json.loads(buffers['artifacts/command.json'])
cleanup = command['cleanup']
check(command['outcome'] == 'success' and command['returncode'] == 0
      and command['command'] == result['command'] and '--child' in command['command']
      and command['command'][command['command'].index('--child') + 1] == 'preflight', 'Only the preflight child was launched')
check(cleanup['direct_child_reaped'] is True and cleanup['writers_settled'] is True
      and cleanup['remaining_live_pids'] == [] and cleanup['leader_held_until_group_close'] is True
      and cleanup['group_authority_lost'] is False, 'Held-leader cleanup')
runtime = json.loads(buffers['artifacts/runtime.json'])
check(runtime['optimized'] == 0 and runtime['image'] == snapshot['image']
      and runtime['declared_resources'] == snapshot['resources'], 'Actual runtime and declared resources')
check(not subprocess.check_output(['git', 'status', '--short'], cwd=ROOT).strip(), 'Clean tracked main checkout')
report = dict(schema='openmhd.offline-dependency-control-parent-review.v1', utc=datetime.now(timezone.utc).isoformat(),
    workflow=WORKFLOW, uuid=UUID, certificate_sha256=sha(certificate_raw),
    snapshot_sha256=sha(snapshot_raw), source_revision=snapshot['source_revision'],
    frozen_source_members=356, parsed_compiled_paths=216, resolved_methods=11,
    methods_executed=0, acquisition_transports=10, checks=checks, errors=errors,
    component_accepted=False, physical_evolutions_run=False,
    inspection_corrections=['Initial exploratory readers assumed test_identities was a list and resolved_tests was a list; both TypeErrors were corrected using the actual mapping and integer schemas.'])
with (OPS / 'actual_parent_review_20261124.json').open('x') as stream:
    json.dump(report, stream, indent=2, allow_nan=False)
    stream.write('\n')
print(json.dumps(report, indent=2))
raise SystemExit(1 if errors else 0)
