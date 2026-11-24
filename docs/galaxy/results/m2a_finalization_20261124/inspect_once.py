"""Read existing records and source bytes only; never import or run project code.

This is a coordinator's coverage inspection, not an independent numerical
review, a test runner, or a milestone acceptance program.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile


ROOT = Path('/Users/arm2arm/orca/openmhd-rs-')
HISTORICAL = Path('/Users/arm2arm/orca/workspaces/openmhd-rs-/m1-run-alfv-n-wave-and-field-loop-benchmarks')
OUT = Path(__file__).resolve().parent
OLD = HISTORICAL / 'results'
OPS216 = ROOT / 'results/branch_integration216_execution_20261123_attempt01'
OPS490 = OLD / 'workspace490_execution_20261123_attempt03'
INVENTORY = OPS490 / 'inventory_m2a20261124a01'
NATIVE = OLD / 'galaxy_native186_results_complete_20261123_attempt01'
COMPILED_REVISION = '58fe532f642e17f4961ce1ce7497882a88cbf069'
checks = 0
origins = {}
retained = {}


def need(value, message):
    global checks
    checks += 1
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def capture(path, name=None):
    need(path.is_file() and not path.is_symlink(), 'Regular original input: ' + str(path))
    raw = path.read_bytes()
    origins[str(path)] = dict(bytes=len(raw), sha256=sha(raw))
    if name is not None:
        need(name not in retained and not Path(name).is_absolute()
             and '..' not in Path(name).parts, 'Unique relative reading member')
        retained[name] = raw
    return raw


def read(path, name=None):
    return json.loads(capture(path, name))


def save(name, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    with (OUT / name).open('xb') as stream:
        stream.write(raw)


source_revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
need(not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT),
     'Clean tracked source before inspection')

# Geometry source must still be the source whose actual comparisons were read.
source_paths = sorted((ROOT / 'crates/moving-mesh/src/three_d').glob('*.rs'))
source_paths += [ROOT / n for n in (
    'crates/moving-mesh/src/lib.rs', 'crates/moving-mesh/Cargo.toml',
    'crates/moving-mesh/tests/geometry3_analytic.rs',
    'crates/moving-mesh/tests/geometry3_controls.rs',
    'crates/moving-mesh/examples/geometry3-case.rs',
    'crates/galaxy-types/src/lib.rs', 'crates/galaxy-types/Cargo.toml',
    'Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml',
)]
source_pins = {}
for path in source_paths:
    relative = path.relative_to(ROOT).as_posix()
    raw = capture(path, 'current-source/' + relative)
    original = subprocess.check_output(['git', 'show', COMPILED_REVISION + ':' + relative], cwd=ROOT)
    need(raw == original, 'Geometry source unchanged from compiled candidate: ' + relative)
    source_pins[relative] = dict(bytes=len(raw), sha256=sha(raw))

design = capture(ROOT / 'docs/galaxy/MESH_3D_SPEC.md', 'requirements/MESH_3D_SPEC.md')
for gate in ('G00', 'G01', 'G02', 'G03', 'G04'):
    need(('`' + gate + '`').encode() in design, 'Original registered gate: ' + gate)

# Read recorded integer counts/verdict strings; no scientific error is recomputed.
analytic_raw = capture(ROOT / 'docs/galaxy/results/geometry3_analytic_20261123.json',
                       'analytic252/actual_output_review.json')
need(sha(analytic_raw) == '36c3c04b9ffe0166e872166d6e5938e548db9455c9e71c0100d7528247dcce1c',
     'Published original analytic reading identity')
analytic = json.loads(analytic_raw)
need(analytic['errors'] == [] and analytic['static_analytic_comparison_outputs_pass'] is True,
     'Recorded analytic comparison output verdict')
need(analytic['component_accepted'] is False and analytic['g00_complete'] is False
     and analytic['g02_to_g04_complete'] is False, 'Original nonacceptance scope')
need(len(analytic['cases']) == 252 and analytic['registered_gate_groups'] == 2016,
     'Exact analytic coverage counts')
families = Counter(row['selection']['fixture'] for row in analytic['cases'])
need(len(families) == 7 and set(families.values()) == {36}, 'Seven complete analytic families')
need(len({r['uuid'] for r in analytic['cases']}) == 252
     and len({r['reference_uuid'] for r in analytic['cases']}) == 252,
     'Distinct recorded original candidate and reference executions')
for row in analytic['cases']:
    need(len(row['gate_verdicts']) == 8 and set(row['gate_verdicts'].values()) == {'pass'},
         'Every recorded analytic gate passes')
    need(row['cells'] > 0 and row['positive_faces'] > 0, 'Positive recorded inventories')

# The 56 actual geometry leaves are a subset of the reviewed 186-leaf packet.
summary = read(NATIVE / 'summary.json', 'native186/summary.json')
manifest = read(NATIVE / 'files.sha256.json', 'native186/files.sha256.json')
native_review = read(OLD / 'native186_output_review_20261123/actual_output_review.json',
                     'native186/actual_output_review.json')
capture(OLD / 'native186_output_review_20261123/REVIEW.md', 'native186/REVIEW.md')
need(summary['counts'] == {'passed': 186, 'failed': 0, 'pending': 0, 'incomplete': 0},
     'Original complete native unit/control results')
need(native_review['errors'] == [] and native_review['original_offline_returncode'] == 0
     and native_review['copied_offline_returncode'] == 0, 'Recorded native original and relocated checks')
need(native_review['packet_manifest_sha256'] == origins[str(NATIVE / 'files.sha256.json')]['sha256'],
     'Reviewed original native packet manifest')
geometry = [r for r in summary['cases'] if r['leaf']['manifest'] == 'crates/moving-mesh/Cargo.toml']
need(len(geometry) == 56 and all(r['status'] == 'passed' and r['observed_status'] == 'finished'
                               for r in geometry), '56 actual passing geometry workflows')
profiles = Counter((r['leaf']['selector'], r['leaf']['build_profile']) for r in geometry)
need(len(profiles) == 56 and set(profiles.values()) == {1}, 'No duplicated selected geometry leaf')
selectors = sorted({selector for selector, _ in profiles})
need(len(selectors) == 28 and all((s, p) in profiles for s in selectors for p in ('debug', 'release')),
     '28 methods in both profiles')
written = set()
for name in ('crates/moving-mesh/tests/geometry3_analytic.rs',
             'crates/moving-mesh/tests/geometry3_controls.rs',
             'crates/moving-mesh/src/three_d/exact.rs'):
    raw = (ROOT / name).read_text()
    written.update(re.findall(r'#\[test\]\s*fn\s+([A-Za-z_0-9]+)\s*\(', raw))
need(written == {s.split('::')[-1] for s in selectors}, 'Current direct source names equal executed methods')
selected_directories = {r['directory'] for r in geometry}
geometry_members = {}
for relative, identity in manifest['files'].items():
    if relative.split('/')[0] not in selected_directories:
        continue
    path = NATIVE / relative
    need(not Path(relative).is_absolute() and '..' not in Path(relative).parts, 'Relative native member')
    raw = capture(path)
    need(len(raw) == identity['bytes'] and sha(raw) == identity['sha256'], 'Original geometry body identity')
    geometry_members[relative] = identity
need(len(geometry_members) == 2352, 'Closed selected geometry reading boundary')
save('geometry_unit_coverage.json', dict(selectors=selectors, workflows=geometry,
     selected_original_bodies=geometry_members, parent_manifest_sha256=sha(capture(NATIVE / 'files.sha256.json')),
     arithmetic_recomputed=False, independent_review_claimed=False))

# Fresh GET observations are checked against exact original known identities.
inventory = read(INVENTORY / 'summary.json', 'workspace490/summary.json')
previous = read(OPS490 / 'inventory_a12/summary.json', 'workspace490/previous_summary.json')
need(len(inventory['cases']) == 490 and inventory['workflow_mutations'] is False,
     'Finite original 490-workflow observation only')
actual_counts = Counter()
for index, row in sorted(inventory['cases'].items()):
    need('observation' in row and 'command' in row and 'uuid' in row, 'Complete current GET observation')
    need(row['uuid'] == previous['cases'][index]['uuid'], 'Same original workspace workflow UUID')
    observation_raw = capture(INVENTORY / row['observation'], 'workspace490/observations/' + row['observation'])
    need(sha(observation_raw) == row['sha256'], 'Recorded original GET body digest')
    observation = json.loads(observation_raw)
    command_path = OPS490 / row['command']
    command = read(command_path, 'workspace490/commands/' + index + '/command.json')
    for channel in ('stdout', 'stderr'):
        raw = capture(command_path.parent / (channel + '.txt'),
                      'workspace490/commands/' + index + '/' + channel + '.txt')
        need(sha(raw) == command[channel]['sha256'] and len(raw) == command[channel]['bytes'],
             'Closed actual GET command log')
    diagnostic = json.loads((command_path.parent / 'stdout.txt').read_bytes())
    need(command['returncode'] == 0 and command['outcome'] == 'success'
         and diagnostic['outcome'] == 'success', 'Successful actual status transport')
    need(diagnostic['workflow_ids'] == [row['uuid']], 'Diagnostic original UUID')
    need(observation['origin'] == 'server' and len(observation['matches']) == 1,
         'Unique server observation')
    observed = observation['matches'][0]
    need(observed['workflow'] == row['workflow'] and observed['version'] == 1
         and observed['status'] == row['status'], 'Exact original status relation')
    actual_counts[row['status']] += 1
need(dict(actual_counts) == inventory['counts'] and sum(actual_counts.values()) == 490,
     'Current full inventory counts')
capture(OPS490 / 'STOP_SUBMISSION', 'workspace490/STOP_SUBMISSION')
for name in ('observe_original490_once.py', 'checkpoint_guard.py', 'log_command.py'):
    capture(OPS490 / name, 'workspace490/host-sources/' + name)
for name in ('reana_metadata_readonly_adapter.py',):
    capture(HISTORICAL / 'tools/galaxy_python_evidence' / name,
            'workspace490/host-sources/' + name)

outstanding = []
for index, uuid in (
    ('0123', 'ceb8d3ab-de2a-4112-a2c5-c4a81ea8b6f2'),
    ('0125', '63224758-14f6-43ac-acb1-64af7fa77285'),
    ('0180', '218c9734-b666-4638-ac4d-d72856913a17'),
):
    observation = read(OPS216 / ('m2a-check-20261124-' + index + '-a01.json'),
                       'original216/' + index + '/observation.json')
    need(observation['origin'] == 'server' and len(observation['matches']) == 1,
         'Actual prerequisite status')
    for action in ('check', 'status', 'logs'):
        label = 'm2a-' + action + '-20261124-' + index + '-a01'
        command_path = OPS216 / 'commands' / label / 'command.json'
        command = read(command_path, 'original216/' + index + '/' + action + '/command.json')
        need(command['outcome'] == 'success' and command['returncode'] == 0,
             'Completed prerequisite diagnostic')
        for channel in ('stdout', 'stderr'):
            raw = capture(command_path.parent / (channel + '.txt'),
                          'original216/' + index + '/' + action + '/' + channel + '.txt')
            need(sha(raw) == command[channel]['sha256'], 'Prerequisite diagnostic log identity')
    diagnostic = json.loads((OPS216 / 'commands' / ('m2a-check-20261124-' + index + '-a01') / 'stdout.txt').read_bytes())
    need(diagnostic['workflow_ids'] == [uuid], 'Unchanged prerequisite UUID')
    state = observation['matches'][0]
    legacy = json.loads((OPS216 / 'commands' / ('m2a-status-20261124-' + index + '-a01') / 'stdout.txt').read_bytes())
    logs = json.loads((OPS216 / 'commands' / ('m2a-logs-20261124-' + index + '-a01') / 'stdout.txt').read_bytes())
    need(len(legacy) == 1 and legacy[0]['id'] == uuid and legacy[0]['status'] == state['status'],
         'Separate UUID-targeted status agrees')
    need(state['version'] == 1 and logs['job_logs'] == {} and logs['workflow_logs'] == '',
         'Original uncompleted workflows retain empty available logs')
    outstanding.append(dict(index=index, uuid=uuid, status=state['status'],
                            workflow=state['workflow'], observed_utc=observation['observed_utc'],
                            available_job_logs=0, available_workflow_log_bytes=0))
capture(OPS216 / 'log_command.py', 'original216/host-sources/log_command.py')
capture(ROOT / 'tools/galaxy_python_evidence/reana_metadata_readonly_adapter.py',
        'original216/host-sources/reana_metadata_readonly_adapter.py')
capture(OLD / 'limiter_campaign_tools_20261113/reana-command.py',
        'original216/host-sources/reana-command.py')
for name in ('docs/galaxy/STATIC_GEOMETRY_COMPARISON_RESULTS.md',
             'docs/galaxy/OFFLINE_BUILD_CANARY_RESULTS_20261124.md',
             'docs/galaxy/M2A_IMPLEMENTATION.md'):
    capture(ROOT / name, 'context/' + Path(name).name)

# Retain exact original reading bytes compactly. This is data archival only.
archive_path = OUT / 'reading.tar.gz'
with archive_path.open('xb') as raw_stream:
    with tarfile.open(fileobj=raw_stream, mode='w:gz') as archive:
        for name, raw in sorted(retained.items()):
            member = tarfile.TarInfo(name)
            member.size = len(raw)
            member.mode = 0o644
            archive.addfile(member, io.BytesIO(raw))
with tarfile.open(archive_path, 'r:gz') as archive:
    need(set(archive.getnames()) == set(retained), 'Exact compact reading inventory')
    for name, raw in retained.items():
        member = archive.extractfile(name)
        need(member is not None and member.read() == raw, 'Archived original bytes: ' + name)
need(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == source_revision,
     'Unchanged inspected revision')
for relative, descriptor in source_pins.items():
    need(sha((ROOT / relative).read_bytes()) == descriptor['sha256'], 'Unchanged scientific source after reading')

save('source_and_reading_pins.json', dict(source_revision=source_revision,
     compiled_geometry_revision=COMPILED_REVISION, geometry_source=source_pins,
     original_paths=origins, compact_reading={name: dict(bytes=len(raw), sha256=sha(raw))
                                           for name, raw in sorted(retained.items())}))
assessment = dict(
    schema='openmhd.m2a-completion-assessment.v1', utc=datetime.now(timezone.utc).isoformat(),
    inspected_revision=source_revision, m2a_accepted=False, m1_scoped_acceptance_unchanged=True,
    numerical_code_changed=False, test_or_numerical_execution_on_host=False,
    workflow_mutations=False, independent_review_claimed=False,
    geometry_source_unchanged_from_actual_compiled_revision=COMPILED_REVISION,
    existing_evidence=dict(analytic_cases=252, recorded_analytic_gate_groups=2016,
                           direct_geometry_methods=28, debug_release_geometry_workflows=56,
                           selected_native_body_hashes_rechecked=len(geometry_members)),
    fresh_workspace490=dict(utc=inventory['utc'], counts=inventory['counts'],
                            all_terminal=inventory['all_terminal'], stop_submission_fenced=True),
    fresh_original216_outstanding=outstanding,
    gate_status={
        'G00': dict(status='blocked', missing='Complete passing workspace and applicable execution-control prerequisite outputs'),
        'G01': dict(status='analytic_slice_passed_prerequisite_open', recorded_cases=252,
                    missing='G00 and full declared geometry prerequisite acceptance'),
        'G02': dict(status='not_execution_ready', missing='Frozen jittered 4^3/6^3/8^3 seed-20261122 inputs; explicit clustered/sliver/boundary-near arrays; independent general-geometry reference and comparison; reviewed build/import and per-case outputs'),
        'G03': dict(status='partial', missing='Complete explicit separation/degeneracy families and registered typed-rejection/uncertainty accounting; existing 28 methods remain a subset'),
        'G04': dict(status='partial', missing='Full G02/G03 order/shuffle/repetition, 1/2/4-thread, seam/translation/multiple-winding matrix with unchanged canonical keys and declared normalized limits'),
    },
    execution_disposition='Preserve original failures and nonterminal UUIDs; no dependent long validation while G00 fails. Read-only service observations succeeded; the cause of queued/pending states is unresolved.',
    inspected_data_relations=checks, errors=[],
)
save('assessment.json', assessment)
body = {p.name: dict(bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
        for p in sorted(OUT.iterdir()) if p.is_file() and p.name != 'sha256.json'}
save('sha256.json', dict(schema='openmhd.retained-metadata-reading.v1', files=body,
                         m2a_accepted=False))
print(json.dumps(dict(checks=checks, errors=[], m2a_accepted=False,
     workspace490=inventory['counts'], outstanding216=[r['status'] for r in outstanding],
     compact_reading_bodies=len(retained))))
