"""Unintegrated whole252 reference acquisition and offline byte validation.

No reference arithmetic, candidate binary, submission, retry or acceptance API.
Only explicit collect performs network access; verify-results consumes originals.
"""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c
import prepare_geometry3_reference as p

SELF = 'tools/galaxy_evidence/geometry_reference_results.py'
ADAPTER = 'tools/galaxy_evidence/geometry_reference_readonly_adapter.py'
JOB = 'reana/galaxy_geometry3_reference_case.py'
TOOLS = (SELF, ADAPTER, JOB, 'tools/galaxy_evidence/prepare_geometry3_reference.py',
         'tools/galaxy_evidence/common.py', 'tools/galaxy_evidence/readonly_adapter.py',
         'reana/galaxy_test_case.py', 'tools/m1_evidence/reana_metadata_job.py',
         'tools/m1_evidence/reana_metadata_readonly_adapter.py')
THREADS = ('RAYON_NUM_THREADS', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
           'MKL_NUM_THREADS', 'RUST_TEST_THREADS')


def host_sources():
    sources = {n: p.read(c.ROOT, n) for n in TOOLS}
    p.require(sources[SELF] == Path(__file__).read_bytes(), 'Actual loaded reference collector source')
    return sources


def descriptor(raw):
    return dict(sha256=p.sha(raw), bytes=len(raw))


def tools_capture(root, sources):
    for name, raw in sources.items():
        p.put(root, 'host_sources/' + name, raw)
    return {name: descriptor(raw) for name, raw in sources.items()}


def tools_verify(root, expected):
    p.keys(expected, TOOLS, 'Exact host-helper source inventory')
    sources = {name: p.read(root, 'host_sources/' + name) for name in TOOLS}
    p.require(all(expected[n] == descriptor(raw) for n, raw in sources.items()), 'Retained complete helper identities')
    p.require(sources == host_sources(), 'Offline verification uses the exact original helper generation')
    return sources


def closed_inventory(root):
    value = c.verify_closed(root)
    p.require(all(type(row['bytes']) is int and row['bytes'] >= 0 for row in value.values()),
              'Closed inventory byte counts exclude Boolean aliases')
    return value


def diagnostic(raw, action, workflow, remote_path, output):
    """Only the pinned adapter's small typed protocol may enter retained logs."""
    value = c.parse(raw)
    required = {'schema', 'outcome', 'code', 'started_utc', 'finished_utc', 'action',
                'workflow', 'requested_path', 'workflow_ids', 'http_status', 'page_count'}
    optional = {'received_bytes', 'retained_bytes', 'partial_file'}
    p.require(type(value) is dict and required <= set(value) <= required | optional
              and value['schema'] == 'openmhd.galaxy-get-diagnostic.v1'
              and value['outcome'] in ('success', 'failure')
              and type(value['code']) is str and re.fullmatch('[a-z][a-z0-9_]{0,80}', value['code'])
              and value['action'] in (None, action) and value['workflow'] in (None, workflow)
              and value['requested_path'] in (None, remote_path)
              and type(value['workflow_ids']) is list
              and all(type(v) is str and str(uuid.UUID(v)) == v for v in value['workflow_ids'])
              and (value['http_status'] is None or type(value['http_status']) is int
                   and 100 <= value['http_status'] <= 599), 'Typed credential-free adapter diagnostic')
    p.require(c.supervisor.utc(value['finished_utc']) >= c.supervisor.utc(value['started_utc'])
              and all(type(value[n]) is int and value[n] >= 0
                      for n in ('page_count', *({'received_bytes', 'retained_bytes'} & set(value))))
              and value.get('partial_file') in (None, Path(output).name + '.partial'),
              'Diagnostic time/count/partial fields')
    return value


def invoke(root, action, workflow, remote_path, sources):
    """One direct300s GET adapter attempt; no automatic retry or mutation."""
    transport = root / 'transport'
    transport.mkdir(exist_ok=True)
    label = f'{len(list(transport.glob("*.json"))):04d}'
    body_name = 'downloads/' + label + '.body'
    (root / 'downloads').mkdir(exist_ok=True)
    adapter = (c.ROOT / ADAPTER).resolve()
    argv = [sys.executable, '-B', str(adapter), action, '--workflow', workflow,
            '--output', str((root / body_name).resolve())]
    if remote_path is not None:
        argv += ['--path', remote_path]
    c.supervisor.credential_free_argv(argv)
    row = dict(schema='openmhd.geometry3-reference-transport.v1', action=action, workflow=workflow,
               remote_path=remote_path, output=body_name, argv=argv, cwd=str(root.resolve()),
               source_sha256={n: p.sha(sources[n]) for n in TOOLS}, timeout_seconds=300,
               started_utc=c.now(), finished_utc=None, outcome='pending_launch', returncode=None,
               direct_process_settled=None, captured_streams_closed=False,
               external_terminal_evidence_required=True,
               interpreter=dict(executable=sys.executable, python=sys.version, optimized=sys.flags.optimize))
    journal = transport / (label + '.json')
    c.native.persist(journal, row)  # Intent is durable before any launch.
    out, err = b'', b''
    try:
        result = subprocess.run(argv, cwd=root, capture_output=True, timeout=300, check=False)
        out, err = result.stdout, result.stderr
        row.update(outcome='success' if result.returncode == 0 else 'nonzero', returncode=result.returncode,
                   direct_process_settled=True, captured_streams_closed=True,
                   external_terminal_evidence_required=False)
    except subprocess.TimeoutExpired as error:
        out, err = error.stdout or b'', error.stderr or b''
        # subprocess.run kills/waits for its direct child before reraising, but
        # its timeout snapshot does not certify descendants or final stream EOF.
        row.update(outcome='timeout', error_type='TimeoutExpired', direct_process_settled=True)
    except BaseException as error:
        row.update(outcome='unknown_closure', error_type=type(error).__name__)
        raise
    finally:
        # Retain only the typed credential-free adapter diagnostic. Unstructured
        # output is represented by a digest/length receipt, never printed.
        for channel, raw in (('stdout', out), ('stderr', err)):
            try:
                diagnostic(raw, action, workflow, remote_path, str((root / body_name).resolve()))
                retained = raw
            except (ValueError, KeyError, TypeError, AttributeError):
                retained = c.encode(dict(schema='openmhd.galaxy-unavailable-diagnostic.v1',
                                         unretained_bytes=len(raw), sha256=p.sha(raw)))
            name = 'transport/' + label + '.' + channel
            p.put(root, name, retained)
            row[channel] = name
            row[channel + '_sha256'] = p.sha(retained)
        row['observation_finished_utc'] = c.now()
        if row['captured_streams_closed']:
            row['finished_utc'] = row['observation_finished_utc']
        if (root / body_name).exists():
            row['output_sha256'] = p.sha(p.read(root, body_name))
        c.native.persist(journal, row)
    p.require(row['outcome'] == 'success' and type(row['returncode']) is int and row['returncode'] == 0,
              'Unsuccessful reference transport; original partials remain nonpassing')
    observed = diagnostic(p.read(root, row['stdout']), action, workflow, remote_path,
                          str((root / body_name).resolve()))
    p.require(observed['outcome'] == 'success' and observed['code'] == 'completed'
              and observed['action'] == action and observed['workflow'] == workflow
              and observed['requested_path'] == remote_path and len(observed['workflow_ids']) == 1,
              'Actual reference adapter UUID/action/path diagnostic')
    return p.read(root, body_name), 'transport/' + label + '.json', observed['workflow_ids'][0]


def transport_body(root, label, workflow, identifier, action, remote_path, sources):
    p.require(type(label) is str and re.fullmatch(r'transport/[0-9]{4}\.json', label),
              'Canonical reference transport label')
    row = c.parse(p.read(root, label))
    number = Path(label).stem
    p.require(row['output'] == 'downloads/' + number + '.body'
              and row['stdout'] == 'transport/' + number + '.stdout'
              and row['stderr'] == 'transport/' + number + '.stderr', 'Canonical reference receipt/body/log paths')
    p.require(row['schema'] == 'openmhd.geometry3-reference-transport.v1'
              and row['workflow'] == workflow and row['action'] == action and row['remote_path'] == remote_path
              and row['outcome'] == 'success' and type(row['returncode']) is int and row['returncode'] == 0
              and type(row['timeout_seconds']) is int and row['timeout_seconds'] == 300
              and row['direct_process_settled'] is True and row['captured_streams_closed'] is True
              and row['external_terminal_evidence_required'] is False,
              'Actual successful300s reference transport receipt')
    argv = row['argv']
    p.require(type(argv) is list and len(argv) >= 3 and Path(argv[0]).is_absolute()
              and Path(argv[2]).is_absolute() and Path(argv[2]).parts[-3:] == tuple(ADAPTER.split('/'))
              and Path(row['cwd']).is_absolute(), 'Absolute credential-free reference adapter argv')
    c.supervisor.credential_free_argv(argv)
    p.require(row['interpreter']['executable'] == argv[0]
              and type(row['interpreter']['python']) is str
              and type(row['interpreter']['optimized']) is int and row['interpreter']['optimized'] == 0,
              'Original unoptimized transport interpreter')
    p.safe(row['output'])
    expected = [argv[0], '-B', argv[2], action, '--workflow', workflow,
                '--output', str(Path(row['cwd']) / row['output'])]
    if remote_path is not None:
        expected += ['--path', remote_path]
    p.require(argv == expected and row['source_sha256'] == {n: p.sha(sources[n]) for n in TOOLS}
              and c.supervisor.utc(row['finished_utc']) >= c.supervisor.utc(row['started_utc']),
              'Original reference transport argv/source/time linkage')
    for channel in ('stdout', 'stderr'):
        p.require(p.sha(p.read(root, row[channel])) == row[channel + '_sha256'], 'Transport diagnostic digest')
    observed = diagnostic(p.read(root, row['stdout']), action, workflow, remote_path,
                          str(Path(row['cwd']) / row['output']))
    p.require(observed['outcome'] == 'success' and observed['code'] == 'completed'
              and observed['workflow_ids'] == [identifier] and observed['workflow'] == workflow
              and observed['action'] == action and observed['requested_path'] == remote_path
              and c.supervisor.utc(row['started_utc']) <= c.supervisor.utc(observed['started_utc'])
              <= c.supervisor.utc(observed['finished_utc']) <= c.supervisor.utc(row['finished_utc']),
              'Exact reference transport UUID/action/path')
    raw = p.read(root, row['output'])
    p.require(p.sha(raw) == row['output_sha256']
              and observed['received_bytes'] == observed['retained_bytes'] == len(raw)
              and observed['partial_file'] is None, 'Original downloaded reference body digest/bytes')
    return raw


def validate_artifacts(values, case_root, job):
    """Check actual retained metadata/command links without geometry arithmetic."""
    p.require(set(values) == set(p.ARTIFACTS), 'Exact ten raw reference artifacts')
    manifest = c.parse(values['outputs/artifacts.sha256.json'])
    expected = {name: descriptor(raw) for name, raw in values.items() if name != 'outputs/artifacts.sha256.json'}
    p.require(manifest == expected and all(type(row['bytes']) is int for row in manifest.values()),
              'Every original reference artifact body/digest/length')
    buffers = {name: p.read(case_root, name) for name in job.INPUTS}
    payload_raw = p.read(case_root, 'payload.json')
    case = job.validate_inputs(buffers, payload_raw)
    result, runtime, command = (c.parse(values['outputs/' + n]) for n in ('result.json', 'runtime.json', 'command.json'))
    p.require(result['schema'] == 'openmhd.geometry3-reference-job-result.v1' and result['status'] == 'complete'
              and p.encode(result['case']) == p.encode(case) and result['reference_case_evaluated'] is True
              and result['candidate_invoked'] is False and result['component_accepted'] is False
              and result['external_execution_provenance_verified'] is False
              and result.get('external_terminal_evidence_required', False) is False,
              'Actual complete reference-only result')
    p.require(result['payload_sha256'] == p.sha(payload_raw)
              and result['runtime_sha256'] == p.sha(values['outputs/runtime.json']), 'Result payload/runtime identities')
    p.require(c.supervisor.utc(result['finished_utc']) >= c.supervisor.utc(result['started_utc']), 'Reference result interval')
    p.require(runtime['schema'] == 'openmhd.geometry3-reference-runtime.v1'
              and type(runtime['optimized']) is int and runtime['optimized'] == 0
              and type(runtime['executable']) is str and Path(runtime['executable']).is_absolute()
              and type(runtime['python']) is str and runtime['system'] == 'Linux'
              and type(runtime['machine']) is str and type(runtime['release']) is str
              and runtime['image'] == p.IMAGE and runtime['image_and_resources_are_declared_labels'] is True
              and runtime['declared_resources'] == case['resources']
              and type(runtime['declared_resources']['threads']) is int
              and type(runtime['declared_resources']['timeout_seconds']) is int
              and type(runtime['visible_cpus']) is int and runtime['visible_cpus'] > 0
              and all(runtime[n] is None or type(runtime[n]) is str for n in ('cpu.max', 'memory.max'))
              and runtime['thread_environment'] == {n: '1' for n in THREADS}
              and runtime['prerequisite_receipts_declared_only'] is True
              and runtime['source_revision'] == case['source_revision']
              and runtime['payload_sha256'] == p.sha(payload_raw)
              and runtime['input_sha256'] == {n: p.sha(raw) for n, raw in buffers.items()},
              'Actual unoptimized Linux reference runtime/input/resource labels')
    cleanup = command['cleanup']
    p.require(command['schema'] == 'openmhd.metadata-command.v1' and command['outcome'] == 'success'
              and type(command['returncode']) is int and command['returncode'] == 0
              and command['external_terminal_evidence_required'] is False
              and cleanup['writers_settled'] is True and cleanup['direct_child_reaped'] is True
              and cleanup['leader_held_until_group_close'] is True and cleanup['group_authority_lost'] is False
              and cleanup['remaining_live_pids'] == [], 'Actual successful reference process and closed log writers')
    identity = cleanup['leader_identity']
    p.require(type(command['pid']) is int and command['pid'] > 0
              and type(command['process_group']) is int
              and all(type(identity[n]) is int for n in ('pid', 'process_group', 'session'))
              and command['pid'] == command['process_group'] == identity['pid'] == identity['process_group']
              == identity['session'] and type(identity['starttime']) is str
              and re.fullmatch('[0-9]+', identity['starttime']) and int(identity['starttime']) > 0,
              'Held reference PID/PGID/SID/starttime')
    work = Path(command['cwd'])
    p.require(work.is_absolute() and runtime['job_path'] == str(work / 'runner.py')
              and command['command'] == [runtime['executable'], str(work / 'reference.py'), '--design',
                  str(work / 'design.json'), '--case', case['selection']['name'], '--output', str(work / 'outputs/reference')]
              and type(command['timeout_seconds']) is int and command['timeout_seconds'] == 300
              and command['timeout_scope'] == 'direct-child-wait', 'Actual one-case reference argv/cwd/timeout')
    c.supervisor.interval(command)
    p.require(c.supervisor.utc(result['started_utc']) <= c.supervisor.utc(command['started_utc'])
              <= c.supervisor.utc(command['finished_utc']) <= c.supervisor.utc(result['finished_utc']),
              'Reference command inside actual result interval')
    p.require(command['links'] == dict(runtime=result['runtime_sha256'], payload=p.sha(payload_raw),
                 **{n: p.sha(raw) for n, raw in buffers.items()}), 'Original reference command/runtime/source links')
    # Inspect only the original reference metadata/bytes; do not import the
    # numerical reference or expand a geometry case in this host collector.
    reference = {n.removeprefix('outputs/reference/'): raw for n, raw in values.items()
                 if n.startswith('outputs/reference/')}
    status, inputs, target = (c.parse(reference[n]) for n in ('status.json', 'input.json', 'reference.json'))
    rm = c.parse(reference['sha256.json'])
    p.require(rm == {n: descriptor(raw) for n, raw in reference.items() if n != 'sha256.json'}
              and all(type(row['bytes']) is int for row in rm.values()), 'Exact independent reference body closure')
    p.require(status['schema'] == 'openmhd.geometry3.reference-execution.v1' and status['status'] == 'complete'
              and status['case'] == case['selection']['name'] and status['source_sha256'] == p.PINS['reference.py']
              and status['candidate_invoked'] is False and status['component_accepted'] is False,
              'Actual independent reference status/source')
    p.require(inputs['schema'] == 'openmhd.geometry3.literal-input.v1'
              and target['schema'] == 'openmhd.geometry3.exact-reference.v1'
              and inputs['case'] == target['case'] == case['selection']
              and all(type(value['case'][n]) is int for value in (inputs, target)
                      for n in ('scale_index', 'translation_index'))
              and inputs['design_sha256'] == target['design_sha256'] == p.PINS['design.json']
              and target['input_sha256'] == p.sha(reference['input.json'])
              and target['candidate_invoked'] is False and target['component_accepted'] is False,
              'Original rounded-input/design/reference selection links')
    p.require(type(target['cells']) is list and type(target['faces']) is list
              and type(status['cells']) is int and status['cells'] == len(target['cells'])
              and type(status['faces']) is int and status['faces'] == len(target['faces'])
              and result['reference_outputs'] == {n: descriptor(raw) for n, raw in reference.items()},
              'Reference counts and result body identities')


def catalog_rows(rows, expected):
    """Whole-catalog metadata only; incomplete rows never imply execution."""
    p.require(type(rows) is list and len(rows) == len(expected) == 252,
              'Complete ordered252 output inventory')
    identifiers = set()
    for row, original in zip(rows, expected):
        p.require(row['workflow'] == original['workflow'] and row['directory'] == original['directory']
                  and row['selection'] == original['selection']
                  and all(type(row['selection'][n]) is int for n in ('scale_index', 'translation_index'))
                  and row['status'] in ('passed', 'pending', 'incomplete', 'forensic'),
                  'Exact ordered reference case metadata')
        if 'uuid' in row:
            identifier = row['uuid']
            p.require(type(identifier) is str and str(uuid.UUID(identifier)) == identifier
                      and identifier not in identifiers, 'Unique original reference workflow UUID')
            identifiers.add(identifier)
    return rows


def validate_capture(directory, row, expected, sources, job, case_root):
    """One metadata capture, not numerical-reference correctness or provenance attestation."""
    p.keys(row, ('workflow', 'directory', 'selection', 'status', 'files', 'uuid', 'before', 'after'),
           'Successful reference case row')
    p.require(row['status'] == 'passed' and row['workflow'] == expected['workflow']
              and row['directory'] == expected['directory'] and row['selection'] == expected['selection'],
              'Exact successful reference case metadata')
    labels = ['transport/' + str(n).zfill(4) + '.json' for n in range(12)]
    p.require(row['before'] == labels[0] and row['after'] == labels[-1]
              and row['files'] == dict(zip(p.ARTIFACTS, labels[1:-1])),
              'Exact observe/ten-download/observe receipt order')
    c.transport_closure(directory, labels)
    values, observed, previous = {}, [], None
    for index, label in enumerate(labels):
        action = 'observe' if index in (0, 11) else 'download'
        name = None if action == 'observe' else p.ARTIFACTS[index - 1]
        raw = transport_body(directory, label, row['workflow'], row['uuid'], action, name, sources)
        record = c.parse(p.read(directory, label))
        p.require(Path(record['cwd']).name == row['directory']
                  and (previous is None or c.supervisor.utc(record['started_utc']) >= previous),
                  'Serial reference acquisition interval/cwd')
        previous = c.supervisor.utc(record['finished_utc'])
        if action == 'observe':
            value = c.parse(raw)
            p.require(c.supervisor.utc(record['started_utc']) <= c.supervisor.utc(value['observed_utc'])
                      <= c.supervisor.utc(record['finished_utc']), 'Observation inside actual transport interval')
            observed.append(c.observation(raw, row['workflow'], row['uuid'], True))
        else:
            values[name] = raw
    p.require(observed[0] == observed[1], 'Stable actual finished reference workflow')
    validate_artifacts(values, case_root, job)


def summary_scope(summary):
    p.require(summary['schema'] == 'openmhd.geometry3-reference-results.v1'
              and summary['status'] == 'complete'
              and summary['candidate_invoked'] is False and summary['component_accepted'] is False
              and summary['external_prerequisite_truth_verified'] is False
              and summary['numerical_output_review_passed'] is False
              and summary['external_terminal_evidence_required'] is False,
              'Complete reference-only metadata scope')


def collect(cases, submission, output):
    p.require(__debug__ and sys.flags.optimize == 0, 'Optimized reference collection rejected')
    plan = p.validate_plan(cases)
    original = p.read(submission.parent, submission.name)
    state = c.parse(original)
    p.keys(state, (r['workflow'] for r in plan['cases']), 'Original whole252 submission coverage')
    sources = host_sources()
    p.require(sources[JOB] == p.read(cases, 'context/source/runner.py')
              and sources['tools/galaxy_evidence/prepare_geometry3_reference.py'] ==
                  p.read(cases, 'context/source/preparer.py'), 'Original released job and preparer source generation')
    job = c.load_module('geometry_reference_result_contract', c.ROOT / JOB)
    output.mkdir()  # A preexisting destination never becomes owned by this call.
    summary = dict(schema='openmhd.geometry3-reference-results.v1', status='collecting', cases=[],
                   candidate_invoked=False, component_accepted=False, external_prerequisite_truth_verified=False,
                   numerical_output_review_passed=False, whole_catalog_passed=False,
                   external_terminal_evidence_required=False, submission_sha256=p.sha(original))
    try:
        c.native.persist(output / 'summary.json', summary)
        p.put(output, 'submission_original.json', original)
        summary['host_sources'] = tools_capture(output, sources)
        captured = {n: r for n, r in c.inventory(cases).items() if n != 'submission.json'}
        for name, row in captured.items():
            raw = p.read(cases, name)
            p.require(row == descriptor(raw), 'Coherent original prepared file capture')
            p.put(output / 'inputs', name, raw)
        input_inventory = c.inventory(output / 'inputs')
        summary['input_inventory'] = input_inventory
        identifiers = set()
        for expected in plan['cases']:
            destination = output / expected['directory']
            destination.mkdir()
            row = dict(workflow=expected['workflow'], directory=expected['directory'],
                       selection=expected['selection'], status='incomplete', files={})
            summary['cases'].append(row)
            try:
                raw, label, identifier = invoke(destination, 'observe', row['workflow'], None, sources)
                observed = c.observation(raw, row['workflow'], identifier)
                row.update(uuid=identifier, before=label)
                p.require(identifier not in identifiers, 'Unique original reference workflow UUID')
                identifiers.add(identifier)
                if observed['status'] not in ('finished', 'failed', 'stopped'):
                    row['status'] = 'pending'
                    continue
                values = {}
                for name in p.ARTIFACTS:
                    raw, label, actual = invoke(destination, 'download', row['workflow'], name, sources)
                    p.require(actual == identifier, 'Reference artifact workflow UUID changed')
                    row['files'][name] = label
                    values[name] = raw
                raw, label, actual = invoke(destination, 'observe', row['workflow'], None, sources)
                row['after'] = label
                p.require(actual == identifier and c.observation(raw, row['workflow'], identifier) == observed,
                          'Stable original reference observe/download/observe generation')
                if observed['status'] != 'finished':
                    row['status'] = 'forensic'
                    continue
                validate_artifacts(values, output / 'inputs' / expected['directory'], job)
                row['status'] = 'passed'
            except Exception as error:
                row.update(status='incomplete', error_type=type(error).__name__)
                summary['external_terminal_evidence_required'] = True
            finally:
                c.native.persist(output / 'summary.json', summary)
        p.require(p.read(submission.parent, submission.name) == original and p.validate_plan(cases) == plan
                  and {n: r for n, r in c.inventory(cases).items() if n != 'submission.json'} == captured
                  and c.inventory(output / 'inputs') == input_inventory and host_sources() == sources,
                  'Complete original input/submission/host-source generation fence')
        summary.update(status='complete', whole_catalog_passed=all(r['status'] == 'passed' for r in summary['cases']),
                       counts={name: sum(r['status'] == name for r in summary['cases'])
                               for name in ('passed', 'pending', 'incomplete', 'forensic')})
        c.native.persist(output / 'summary.json', summary)
        c.close(output)
        verify_results(output)
        return summary
    except BaseException as error:
        summary.update(status='failed', error_type=type(error).__name__, whole_catalog_passed=False,
                       external_terminal_evidence_required=True)
        # Invalidate a published success view while preserving its original bytes.
        # Storage/interpreter loss may prevent even this envelope; callers must
        # retain the failing command and may never infer success from directory existence.
        try:
            manifest = output / 'files.sha256.json'
            if manifest.exists():
                manifest.rename(output / 'files.failed.sha256.json')
            c.native.persist(output / 'summary.json', summary)
            c.close(output)
        except BaseException:
            pass
        raise


def verify_results(root):
    p.require(__debug__ and sys.flags.optimize == 0, 'Optimized reference verification rejected')
    closed_inventory(root)
    summary = c.parse(p.read(root, 'summary.json'))
    summary_scope(summary)
    sources = tools_verify(root, summary['host_sources'])
    plan = p.validate_plan(root / 'inputs')
    state = c.parse(p.read(root, 'submission_original.json'))
    p.keys(state, (r['workflow'] for r in plan['cases']), 'Original whole252 submission')
    catalog_rows(summary['cases'], plan['cases'])
    p.require(summary['submission_sha256'] == p.sha(p.read(root, 'submission_original.json'))
              and summary['input_inventory'] == c.inventory(root / 'inputs'),
              'Original complete input/submission capture identity')
    p.require(sources[JOB] == p.read(root / 'inputs', 'context/source/runner.py')
              and sources['tools/galaxy_evidence/prepare_geometry3_reference.py'] ==
                  p.read(root / 'inputs', 'context/source/preparer.py'), 'Original offline job/preparer generation')
    job = c.load_module('geometry_reference_result_contract', c.ROOT / JOB)
    identifiers = set()
    for row, expected in zip(summary['cases'], plan['cases']):
        p.require(row['workflow'] == expected['workflow'] and row['directory'] == expected['directory']
                  and row['selection'] == expected['selection'] and row['status'] == 'passed'
                  and row['uuid'] not in identifiers, 'Exact ordered case/workflow/unique UUID/pass coverage')
        identifiers.add(row['uuid'])
        validate_capture(root / row['directory'], row, expected, sources, job,
                         root / 'inputs' / row['directory'])
    p.require(summary['whole_catalog_passed'] is True and summary['counts'] ==
                  dict(passed=252, pending=0, incomplete=0, forensic=0)
              and all(type(v) is int for v in summary['counts'].values()), 'Strict whole252 reference counts')
    allowed = {'summary.json', 'submission_original.json',
               *('host_sources/' + n for n in TOOLS),
               *('inputs/' + n for n in c.inventory(root / 'inputs'))}
    p.require('inputs/submission.json' not in allowed, 'Input journal remains a separate original receipt')
    for row in summary['cases']:
        directory = root / row['directory']
        for label in (row['before'], *row['files'].values(), row['after']):
            record = c.parse(p.read(directory, label))
            allowed.update(row['directory'] + '/' + n for n in
                           (label, record['stdout'], record['stderr'], record['output']))
    p.require(set(c.inventory(root)) == allowed, 'No unreferenced files in successful whole252 packet')
    # Recheck the packet after all reads. No code accepts an inventory alone as
    # a numerical correctness review or candidate geometry comparison.
    closed_inventory(root)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    collect_parser = commands.add_parser('collect')
    for name in ('cases', 'submission', 'output'):
        collect_parser.add_argument('--' + name, type=Path, required=True)
    verify = commands.add_parser('verify-results')
    verify.add_argument('--packet', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.action == 'collect':
        collect(args.cases, args.submission, args.output)
    else:
        verify_results(args.packet)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
