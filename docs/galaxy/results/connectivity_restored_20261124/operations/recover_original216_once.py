"""Recover unstarted original submissions after the settled network outage.

No run/restart or method retry. Each original base may be created once only
after two empty complete GET scans. Existing created UUIDs keep their identity.
Each present input must match before missing-only upload and one first start.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import threading
from log_command import run

OPS = Path(__file__).resolve().parent
ROOT = OPS.parents[1]
CASES = ROOT / 'results/branch_integration216_cases_20261124_attempt01'
SOURCE = ROOT / 'results/branch_integration216_source_20261123_attempt01'
CLIENT = Path('/Users/arm2arm/orca/workspaces/openmhd-rs-/m1-run-alfv-n-wave-and-field-loop-benchmarks/results/limiter_campaign_tools_20261113/reana-command.py')
ADAPTER = ROOT / 'tools/galaxy_python_evidence/reana_metadata_readonly_adapter.py'
LEGACY = ['/usr/bin/python3', '-B', str(CLIENT)]
STOP = threading.Event()
DEST = OPS / 'recovery_restored_a01'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


release = load(OPS / 'method_release_20261124.json')
snapshot = load(SOURCE / 'snapshot.json')
plan_raw = (CASES / 'plan.json').read_bytes()
plan = json.loads(plan_raw)
submission_raw = (CASES / 'submission.json').read_bytes()
submission = json.loads(submission_raw)
initial = load(OPS / 'inventory_a01/summary.json')['cases']
submit = load(OPS / 'commands/19-submit-216-original-methods-once/command.json')
need(submit['finished_utc'] and submit['outcome'] == 'success' and submit['returncode'] == 0, 'Original submission ceased')
need(submission_raw == (ROOT / 'docs/galaxy/results/validation_checkpoint_20261124/operations/submission_original_final.json').read_bytes(), 'Untouched original settled submission')
need(sha(CLIENT.read_bytes()) == '07c7ad769deb0044db72af40f751399a9950499793511d20f43df1b090e9853e', 'Approved legacy client')
need(sha(plan_raw) == release['plan_sha256'] and len(plan['cases']) == 216, 'Original whole plan')
selected = [e for e in plan['cases'] if submission[e['workflow']]['status'] == 'submission uncertain']
need(len(selected) == 88, 'Original 88 uncertainty dispositions')
DEST.mkdir()
save(DEST / 'root_disposition.json', dict(utc=datetime.now(timezone.utc).isoformat(),
    authority='Original 216-method release and owner restoration/resume; complete original identities without repeating an executed method',
    selected=[e['directory'] for e in selected], original_map_sha256=sha(submission_raw),
    maximum_creations_per_absent_base=1, maximum_starts_per_unstarted_uuid=1,
    missing_only_upload=True, workflow_or_method_retries=False, component_accepted=False))


def staged_inventory(case):
    need(all(not p.is_symlink() for p in case.rglob('*')), 'No linked original inputs')
    return {str(p.relative_to(case)): dict(sha256=sha(p.read_bytes()), bytes=p.stat().st_size)
            for p in case.rglob('*') if p.is_file()}


def guard(entry, original):
    need(not STOP.is_set(), 'Recovery launch fence')
    need((CASES / 'submission.json').read_bytes() == submission_raw, 'Original uncertain rows unchanged')
    need(all(sha((ROOT / n).read_bytes()) == h for n, h in snapshot['source_sha256'].items()), '354 frozen sources unchanged')
    case = CASES / entry['directory']
    need(staged_inventory(case) == original and len(original) == 7, 'Original seven inputs unchanged')
    need(sha((case / 'payload.json').read_bytes()) == entry['payload_sha256']
         and sha((case / 'reana.yaml').read_bytes()) == entry['workflow_sha256'], 'Exact released plan inputs')
    payload = load(case / 'payload.json')
    need(all(sha((case / n).read_bytes()) == h for n, h in payload['input_sha256'].items()), 'Exact released payload inputs')


def recover(entry):
    index, workflow = entry['directory'], entry['workflow']
    case = CASES / index
    dest = DEST / index
    dest.mkdir()
    original = staged_inventory(case)
    guard(entry, original)
    save(dest / 'staged_before.json', original)

    def call(label, argv, cwd=ROOT, required=True):
        need(not STOP.is_set(), 'No launches after an unresolved operation')
        label = 'recover216-' + index + '-' + label
        try:
            code = run(label, argv, cwd, timeout=350)
        except BaseException:
            STOP.set()
            raise
        if code:
            STOP.set()
            need(not required, 'Operation failed; preserve outcome without automatic retry')
        return code, OPS / 'commands' / label

    def scan(label):
        _, folder = call(label, ['/usr/bin/python3', '-B', str(OPS / 'scan_original216_versions_once.py'), workflow])
        data = load(folder / 'stdout.txt')
        need(data['outcome'] == 'success', 'Actual complete normal-TLS scan')
        return data['rows']

    def created(rows, identifier=None):
        need(len(rows) == 1 and rows[0]['workflow'] == workflow and rows[0]['name'] == workflow[:-2]
             and rows[0]['version'] == 1 and rows[0]['status'] == 'created', 'Unique unstarted original version one')
        if identifier:
            need(rows[0]['id'] == identifier, 'Same original UUID')
        return rows[0]['id']

    def no_jobs(identifier, label):
        _, folder = call(label + '-status', [*LEGACY, 'status', '--workflow', identifier, '--json', '--verbose'])
        rows = load(folder / 'stdout.txt')
        need(len(rows) == 1 and rows[0]['id'] == identifier and rows[0]['name'] == workflow[:-2]
             and str(rows[0]['run_number']) == '1' and rows[0]['status'] == 'created'
             and rows[0].get('started', '-') == rows[0].get('ended', '-') == '-', 'Actual never-started workflow')
        _, folder = call(label + '-logs', [*LEGACY, 'logs', '--workflow', identifier, '--json'])
        need(load(folder / 'stdout.txt') == dict(workflow_logs='', job_logs={}, engine_specific=None), 'No prior workflow/job execution')

    rows = scan('01-scan-original-all-versions')
    if rows and len(rows) == 1 and rows[0]['version'] == 1 and rows[0]['workflow'] == workflow and rows[0]['status'] != 'created':
        need(rows[0]['id'] == initial[index].get('uuid'), 'Already-advanced original UUID')
        return dict(workflow=workflow, uuid=rows[0]['id'], status='already_advanced', server_status=rows[0]['status'], mutations=False)
    was_absent = not rows
    if was_absent:
        need(initial[index]['status'] == 'missing', 'Only originally absent planned identity')
        need(scan('02-second-empty-all-version-scan') == [], 'Two empty complete scans after settled original submit')
        guard(entry, original)
        save(dest / 'before_create_guard.json', dict(workflow=workflow, two_empty_all_version_scans=True,
             original_inputs=original, original_submission_unchanged=True, original_base_create_once=True, errors=[]))
        code, _ = call('03-create-original-base-once', [*LEGACY, 'create', '--workflow', workflow[:-2], '--file', 'reana.yaml'], case, required=False)
        need(code == 0, 'Unknown/failed create must be inspected without retry')
        rows = scan('04-after-create-all-versions')
    identifier = created(rows)
    if not was_absent:
        need(identifier == initial[index]['uuid'], 'Existing original created UUID')
    no_jobs(identifier, '05-initial')
    _, folder = call('06-list-original-inputs', [*LEGACY, 'ls', '--workflow', identifier, '--json'])
    present = [r['name'] for r in load(folder / 'stdout.txt')]
    need(len(present) == len(set(present)) and set(present) <= set(original), 'Only original input subset')
    available = dest / 'downloaded_present'
    available.mkdir()
    if present:
        call('07-download-present-inputs', [*LEGACY, 'download', '--workflow', identifier,
             '--output-directory', str(available), *sorted(present)])
    need(staged_inventory(available) == {n: original[n] for n in present}, 'All present actual original bytes match')
    missing = sorted(set(original) - set(present))
    save(dest / 'present_input_check.json', dict(workflow=workflow, uuid=identifier, actual=staged_inventory(available), missing=missing, errors=[]))
    guard(entry, original)
    created(scan('08-before-missing-upload'), identifier)
    if missing:
        call('09-upload-only-missing-once', [*LEGACY, 'upload', '--workflow', identifier, *missing], case)
    downloaded = dest / 'downloaded_all'
    downloaded.mkdir()
    call('10-download-all-seven-inputs', [*LEGACY, 'download', '--workflow', identifier,
         '--output-directory', str(downloaded), *sorted(original)])
    need(staged_inventory(downloaded) == original, 'All seven actual remote original inputs matched')
    save(dest / 'all_input_check.json', dict(actual=staged_inventory(downloaded), expected=original, errors=[]))
    created(scan('11-before-first-start'), identifier)
    no_jobs(identifier, '12-final')
    guard(entry, original)
    save(dest / 'first_start_guard.json', dict(workflow=workflow, uuid=identifier, source_and_seven_inputs_unchanged=True,
         all_actual_inputs_matched=True, no_execution=True, first_start_only=True, errors=[]))
    code, _ = call('13-first-uuid-start-once', [*LEGACY, 'start', '--workflow', identifier], required=False)
    # A failed start is never repeated here. Its next step is authoritative observation.
    need(code == 0, 'Unknown/failed first start retained without retry')
    target = dest / 'after_start.json'
    call('14-normal-after-start', ['/usr/bin/python3', '-B', str(ADAPTER), 'observe', '--workflow', workflow, '--output', str(target)])
    outcome = dict(workflow=workflow, uuid=identifier, status='first_start_succeeded', original_absent=was_absent,
                   missing_uploaded=missing, after=load(target), original_uncertainty_preserved=True,
                   method_rerun=False, method_pass_inferred=False, component_accepted=False)
    save(dest / 'recovery_outcome.json', outcome)
    return outcome


outcomes = {}
with ThreadPoolExecutor(max_workers=4) as pool:
    futures = {pool.submit(recover, entry): entry['directory'] for entry in selected}
    for future in as_completed(futures):
        index = futures[future]
        try:
            outcomes[index] = future.result()
        except BaseException as error:
            STOP.set()
            outcomes[index] = dict(status='held', error_type=type(error).__name__, reason=str(error))
        save(DEST / (index + '-outcome.json'), outcomes[index])
need((CASES / 'submission.json').read_bytes() == submission_raw, 'Final original map unchanged')
save(DEST / 'summary.json', dict(utc=datetime.now(timezone.utc).isoformat(), outcomes=outcomes,
    original_map_sha256=sha(submission_raw), launch_fenced=STOP.is_set(), component_accepted=False))
print(json.dumps(dict(recovery_cases=len(outcomes), first_starts=sum(r['status'] == 'first_start_succeeded' for r in outcomes.values()),
    already_advanced=sum(r['status'] == 'already_advanced' for r in outcomes.values()), held=sum(r['status'] == 'held' for r in outcomes.values()))))
raise SystemExit(int(STOP.is_set()))
