"""Finite GET-only inventory of the original, immutable 216-case plan."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from log_command import run

OPS = Path(__file__).resolve().parent
ROOT = OPS.parents[1]
CASES = ROOT / 'results/branch_integration216_cases_20261124_attempt01'
SOURCE = ROOT / 'results/branch_integration216_source_20261123_attempt01'
ADAPTER = ROOT / 'tools/galaxy_python_evidence/reana_metadata_readonly_adapter.py'
tag = sys.argv[1]
if not tag.isalnum():
    raise ValueError('Fresh simple inventory tag')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def need(ok, message):
    if not ok:
        raise ValueError(message)


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


release = read(OPS / 'method_release_20261124.json')
snapshot = read(SOURCE / 'snapshot.json')
need(sha((SOURCE / 'snapshot.json').read_bytes()) == release['snapshot_sha256'], 'Original source snapshot')
transition = read(OPS / 'original216_generation_transition.json')
need(transition['errors'] == [] and transition['source_snapshot_sha256'] == sha((SOURCE / 'snapshot.json').read_bytes()),
     'Closed original generation transition')
need(sha((SOURCE / 'source.tar.gz').read_bytes()) == snapshot['archive_sha256'], 'Exact original immutable source archive')
for name, row in transition['frozen_exact_host_tools'].items():
    need(sha((OPS / 'frozen_original216_host_tools' / name).read_bytes()) == row['sha256'], 'Frozen original host tool')
allowed = {'tools/galaxy_python_evidence/reana_metadata_job.py': 'c6c133c9bf59e6d28fe1ed89c8741c28c06730a54aff740db043883de9ea4215', 'tools/galaxy_python_evidence/prepare_metadata_reana.py': 'b39cda55410e22fee6a79777f520773cbb54c1e4104ecd0679e5386f2513ed22', 'tools/galaxy_python_evidence/collect_metadata_reana_results.py': '8daa1e572a19ccca148615996d7aabb11970134ef79adc72f81fb6d36bb45435'}
need(all(sha((ROOT / n).read_bytes()) == allowed.get(n, h) for n, h in snapshot['source_sha256'].items()),
     'Exact declared later helper generation; other original source members unchanged')
plan_raw = (CASES / 'plan.json').read_bytes()
need(sha(plan_raw) == release['plan_sha256'], 'Original released plan')
plan = json.loads(plan_raw)
submission_raw = (CASES / 'submission.json').read_bytes()
need(submission_raw == (ROOT / 'docs/galaxy/results/validation_checkpoint_20261124/operations/submission_original_final.json').read_bytes(),
     'Original settled map remains unchanged')
state = json.loads(submission_raw)
need(len(plan['cases']) == 216 and set(state) == {r['workflow'] for r in plan['cases']}, 'Exact original catalog')
destination = OPS / ('inventory_' + tag)
destination.mkdir()
(destination / 'submission_snapshot.json').write_bytes(submission_raw)


def observe(entry):
    index, workflow = entry['directory'], entry['workflow']
    for attempt in range(1, 4):
        output = destination / (index + '-a' + str(attempt) + '.json')
        label = 'inventory216-' + tag + '-' + index + '-a' + str(attempt)
        code = run(label, ['/usr/bin/python3', '-B', str(ADAPTER), 'observe',
                         '--workflow', workflow, '--output', str(output)], ROOT, timeout=350)
        log = OPS / 'commands' / label
        if code:
            diagnostic = read(log / 'stderr.txt')
            if diagnostic['code'] in ('network_error', 'observation_changed') and attempt < 3:
                continue
            return dict(workflow=workflow, observation_error=diagnostic['code'], command=label)
        observed, diagnostic = read(output), read(log / 'stdout.txt')
        need(observed['origin'] == 'server', 'Actual observation origin')
        if not observed['matches']:
            return dict(workflow=workflow, status='missing', command=label, observation=output.name)
        need(len(observed['matches']) == 1 and observed['matches'][0]['workflow'] == workflow
             and observed['matches'][0]['version'] == 1 and len(diagnostic['workflow_ids']) == 1,
             'Unique original version-one workflow')
        return dict(workflow=workflow, uuid=diagnostic['workflow_ids'][0],
                    status=observed['matches'][0]['status'], submission_status=state[workflow]['status'],
                    observation=output.name, observation_sha256=sha(output.read_bytes()), command=label)


rows = {}
with ThreadPoolExecutor(max_workers=8) as pool:
    pending = {pool.submit(observe, entry): entry['directory'] for entry in plan['cases']}
    for future in as_completed(pending):
        index = pending[future]
        try:
            rows[index] = future.result()
        except BaseException as error:
            rows[index] = dict(inspection_error_type=type(error).__name__)
need((CASES / 'submission.json').read_bytes() == submission_raw, 'Original map still unchanged')
counts = {}
for row in rows.values():
    status = row.get('status', 'observation_error')
    counts[status] = counts.get(status, 0) + 1
summary = dict(schema='openmhd.original216-inventory.v1', utc=datetime.now(timezone.utc).isoformat(),
               counts=counts, cases=rows, plan_sha256=sha(plan_raw), submission_sha256=sha(submission_raw),
               workflow_mutations=False, component_accepted=False)
save(destination / 'summary.json', summary)
print(json.dumps(dict(counts=counts, workflow_mutations=False)))
