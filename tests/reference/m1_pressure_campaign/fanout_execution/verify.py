#!/usr/bin/env python3
"""Verify retained execution evidence and exact baseline parity; no evolution."""
import gzip
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(name):
    path = ROOT/name
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes())


for name, expected in load('archive_sha256.json').items():
    assert digest((ROOT/name).read_bytes()) == expected, name
snapshot = load('snapshot.json')
with tarfile.open(ROOT/'execution_sources.tar.gz') as archive:
    for member in archive.getmembers():
        assert digest(archive.extractfile(member).read()) == snapshot['source_sha256'][member.name]
preflight = load('preflight/preflight.json')
execution = load('preflight/execution.json')
assert execution['status'] == 'completed' and len(execution['commands']) == 8
assert all(c['returncode'] == 0 for c in execution['commands'])
assert preflight['commands'] == execution['commands']
assert preflight['snapshot_sha256'] == digest((ROOT/'snapshot.json').read_bytes())
artifacts = load('preflight/artifacts.sha256.json')
for p in (ROOT/'preflight').rglob('*'):
    name = 'outputs/'+str(p.relative_to(ROOT/'preflight'))
    if p.is_file() and name in artifacts:
        assert digest(p.read_bytes()) == artifacts[name]
baseline = load('baseline_runs.json.gz')
plan = load('smoke_plan.json')
for entry in plan['cases']:
    directory = 'cases/'+entry['directory']
    record = load(directory+'/record.json.gz')
    execution = load(directory+'/execution.json.gz')
    name = entry['specification']['config']['name']
    assert record['config'] == baseline[name]['config'] == entry['specification']['config']
    assert execution['status'] == record['status'] == 'completed'
    assert execution['binary_sha256'] == preflight['binary_sha256']
    assert record['positive_and_conservative'] and record.get('state_and_diagnostic_gates', True)
    final = gzip.decompress((ROOT/directory/'final.csv.gz').read_bytes())
    assert digest(final) == record['sha256']['final.csv'] == baseline[name]['sha256']['final.csv']
checkpoint = load('smoke_checkpoint.json')
assert checkpoint['all_terminal'] and not checkpoint['verified_required_failure']
assert not checkpoint['observation_errors'] and not checkpoint['execution_failures']
assert len(checkpoint['summaries']['wave']['pairs']) == 2
assert all(p['status'] == 'pass under both reported normalizations' for p in checkpoint['summaries']['wave']['pairs'])
assert len(checkpoint['summaries']['physics']['boost_pairs']) == 1
assert checkpoint['summaries']['physics']['boost_pairs'][0]['status'] == 'pass'
assert not checkpoint['full_m1_accepted']
control = load('cancellation/verification.json')
first = load('cancellation/first_failure.json')
terminal = load('cancellation/checkpoint.json')
failed, stopped = control['expected_timeout_workflow'], control['stopped_sibling_workflow']
assert first['verified_required_failure'] and first['workflow_states'][stopped]['status'] == 'running'
assert terminal['workflow_states'][failed]['status'] == 'failed'
assert terminal['workflow_states'][stopped]['status'] == 'stopped'
assert load('cancellation/runs.json.gz')['expected_timeout_control']['status'] == 'timeout'
print('Archive hashes, frozen execution sources, preflight and six baseline-identical snapshots verified.')
