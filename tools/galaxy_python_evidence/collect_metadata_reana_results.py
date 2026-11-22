"""Read-only galaxy Python catalog acquisition and offline consistency checking.

Import is inert. Execution, including synthetic controls, is REANA-only until
the owner releases the reviewed host acquisition step. No submit/control API.
The eight original outputs and source/certificate bytes are never synthesized.
"""
from datetime import datetime, timezone
import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import tarfile

import prepare_metadata_reana as prepare
import reana_metadata_job as job

require, digest, encode = job.require, job.digest, job.encode
SUMMARY_SCHEMA = 'openmhd.galaxy-python-case-results.v1'
FILES_SCHEMA = 'openmhd.galaxy-python-case-results-files.v1'
CAPTURE_SCHEMA = 'openmhd.galaxy-python-case-context-capture.v1'
STATUS_SCHEMA = 'openmhd.galaxy-python-case-collection-status.v1'
TERMINAL_DOWNLOAD = frozenset(('finished', 'failed', 'stopped'))
SHARED = ('snapshot.json', 'source.tar.gz', 'job.py', 'preflight_certificate.json')
SMALL_CASE = ('case.json', 'payload.json', 'reana.yaml')
CASE_INPUTS = ('snapshot.json', 'source.tar.gz', 'job.py', 'preflight_certificate.json', *SMALL_CASE)
PREFLIGHT_INPUTS = ('plan.json', 'submission.json', '0000/payload.json', '0000/reana.yaml', '0000/case.json')
TOOLS = ('prepare_metadata_reana.py', 'reana_metadata_job.py',
         'reana_metadata_readonly_adapter.py', 'collect_metadata_reana_results.py')


def typed_equal(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def plain_root(path):
    path = Path(path).absolute()
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        require(not current.is_symlink(), 'Linked root/ancestor')
    require(path.is_dir(), 'Expected existing regular directory')
    return path


def file_names(root, *, with_directories=False):
    """Exact regular-file inventory, rejecting links and special files."""
    root = plain_root(root)
    names, directories = [], set()
    def visit(directory):
        for path in sorted(directory.iterdir()):
            require(not path.is_symlink(), 'Linked collection entry')
            mode = path.stat().st_mode
            if stat.S_ISDIR(mode):
                directories.add(path.relative_to(root).as_posix())
                visit(path)
            else:
                require(stat.S_ISREG(mode), 'Nonregular collection entry')
                names.append(path.relative_to(root).as_posix())
    visit(root)
    return (set(names), directories) if with_directories else set(names)


def validate_source(source):
    """Hash every archived member; independently enumerate all five AST suites.

    Large members are hashed in chunks, never omitted or extracted/executed.
    Only the five test texts are retained in memory for source enumeration.
    """
    snapshot = job.parse(source['snapshot.json'])
    job.validate_snapshot(snapshot)
    require(digest(source['source.tar.gz']) == snapshot['archive_sha256']
            and digest(source['job.py']) == snapshot['job_sha256'], 'Shared source pins')
    found, tests = set(), {}
    with tarfile.open(fileobj=io.BytesIO(source['source.tar.gz']), mode='r:gz') as archive:
        for member in archive:
            name, path = member.name, PurePosixPath(member.name)
            require(member.isfile() and path.parts and path.as_posix() == name
                    and not path.is_absolute() and '..' not in path.parts
                    and any(name.startswith(r) for r in prepare.ROOTS) and '__pycache__' not in path.parts
                    and name in snapshot['source_sha256'] and name not in found, 'Source member inventory')
            found.add(name)
            stream, hashed, count, pieces = archive.extractfile(member), hashlib.sha256(), 0, []
            require(stream is not None, 'Unreadable source member')
            with stream:
                while True:
                    block = stream.read(65536)
                    if not block:
                        break
                    count += len(block)
                    hashed.update(block)
                    if name in job.TEST_FILES:
                        require(count <= job.MAX_FILE_BYTES, 'Excessive test source')
                        pieces.append(block)
            require(count == member.size and hashed.hexdigest() == snapshot['source_sha256'][name],
                    'Archived source hash')
            if name in job.TEST_FILES:
                tests[name] = b''.join(pieces)
    require(found == set(snapshot['source_sha256']) and
            job.identities_from_sources(tests) == snapshot['test_identities'], 'Full AST catalog coverage')
    return snapshot


def validate_context(buffers):
    """Validate copied inputs without referring to any live development path."""
    shared = {n: buffers['shared/' + n] for n in SHARED}
    snapshot = validate_source(shared)
    certificate = job.validate_certificate(shared['preflight_certificate.json'], shared['snapshot.json'])
    expected = {'shared/' + n for n in SHARED}
    for name in PREFLIGHT_INPUTS:
        stored = 'inputs/preflight/' + name
        expected.add(stored)
        require(buffers[stored] == base64.b64decode(certificate['buffers'][PurePosixPath(name).name], validate=True),
                'Original preflight/certificate identity')
    plan_name, submission_name = 'inputs/cases/plan.json', 'inputs/cases/submission.json'
    expected |= {plan_name, submission_name}
    plan, submission = job.parse(buffers[plan_name]), job.parse(buffers[submission_name])
    job.exact_keys(plan, ('schema', 'snapshot_sha256', 'source_revision', 'coverage',
        'preflight_certificate_sha256', 'cases', 'component_accepted'), 'Unittest plan')
    cert_hash, snapshot_hash = digest(shared['preflight_certificate.json']), digest(shared['snapshot.json'])
    require(plan['schema'] == 'openmhd.galaxy-python-case-plan.v2' and plan['component_accepted'] is False
            and plan['snapshot_sha256'] == snapshot_hash and plan['source_revision'] == snapshot['source_revision']
            and plan['preflight_certificate_sha256'] == cert_hash
            and plan['coverage'] == dict(test_files=list(job.TEST_FILES), selectors=snapshot['tests'],
                                       test_identities=snapshot['test_identities'])
            and type(plan['cases']) is list and len(plan['cases']) == len(snapshot['tests']),
            'Exact whole-catalog plan coverage')
    workflows, prefix = set(), None
    for index, entry in enumerate(plan['cases']):
        job.exact_keys(entry, ('directory', 'specification', 'workflow', 'payload_sha256', 'workflow_sha256'),
                       'Unittest entry')
        directory = f'{index:04d}'
        require(entry['directory'] == directory, 'Exact case index/directory')
        case_buffers = {n: buffers['inputs/cases/' + directory + '/' + n] for n in SMALL_CASE}
        expected |= {'inputs/cases/' + directory + '/' + n for n in SMALL_CASE}
        case, payload, spec = (job.parse(case_buffers[n]) for n in SMALL_CASE)
        job.validate_case(case, snapshot)
        suffix = '-' + snapshot_hash[:12] + '-' + directory + '.1'
        require(case['kind'] == 'unittest' and case['selector'] == snapshot['tests'][index]
                and case['preflight_certificate_sha256'] == cert_hash and case == entry['specification']
                and entry['workflow'] == case['workflow'] and entry['workflow'].endswith(suffix),
                'Exact case/selector/workflow/certificate identity')
        actual_prefix = prepare.safe_name(entry['workflow'][:-len(suffix)])
        prefix = actual_prefix if prefix is None else prefix
        require(actual_prefix == prefix and entry['workflow'] not in workflows, 'Unique workflow/prefix')
        workflows.add(entry['workflow'])
        job.exact_keys(payload, ('schema', 'input_sha256'), 'Unittest payload')
        require(payload['schema'] == 'openmhd.galaxy-python-case-payload.v2' and payload['input_sha256'] == {
            'source.tar.gz': snapshot['archive_sha256'], 'snapshot.json': snapshot_hash,
            'job.py': snapshot['job_sha256'], 'case.json': digest(case_buffers['case.json']),
            'preflight_certificate.json': cert_hash}, 'Exact unittest input pins')
        require(digest(case_buffers['payload.json']) == entry['payload_sha256']
                and digest(case_buffers['reana.yaml']) == entry['workflow_sha256']
                and spec == job.workflow_document(payload['input_sha256']), 'Exact case payload/spec/resources')
    require(type(submission) is dict and set(submission) == workflows, 'Exact submission workflow catalog')
    for value in submission.values():
        require(type(value) is dict and value.get('status') in
                ('submitted', 'submission uncertain', 'submission pending'), 'Actual submission state')
        require(set(value) == ({'status', 'error'} if value['status'] == 'submission uncertain' else {'status'})
                and ('error' not in value or type(value['error']) is str), 'Submission receipt fields')
    require(set(buffers) == expected, 'Exact retained context inventory')
    return snapshot, plan, submission


def capture_context(source_dir, preflight_dir, cases_dir):
    """Capture each original input; deduplicate only byte-identical shared inputs."""
    source_dir, preflight_dir, cases_dir = map(plain_root, (source_dir, preflight_dir, cases_dir))
    source, _ = prepare.read_source(source_dir)
    source['preflight_certificate.json'] = job.capture_files(preflight_dir, ('certificate.json',))['certificate.json']
    retained, witnesses = {}, {}
    def add(role, original, stored, raw):
        require(stored not in retained or retained[stored] == raw, 'Conflicting shared input')
        retained[stored] = raw
        witnesses[role] = dict(original_path=str(original), stored_path=stored, sha256=digest(raw), bytes=len(raw))
    for name in SHARED:
        original = preflight_dir / 'certificate.json' if name == 'preflight_certificate.json' else source_dir / name
        add('source/' + name, original, 'shared/' + name, source[name])
    original_preflight = job.capture_files(source_dir / 'preflight', PREFLIGHT_INPUTS)
    for name, raw in original_preflight.items():
        add('preflight/' + name, source_dir / 'preflight' / name, 'inputs/preflight/' + name, raw)
    plan_buffers = job.capture_files(cases_dir, ('plan.json', 'submission.json'))
    for name, raw in plan_buffers.items():
        add('cases/' + name, cases_dir / name, 'inputs/cases/' + name, raw)
    plan = job.parse(plan_buffers['plan.json'])
    require(type(plan.get('cases')) is list, 'Case plan list')
    require({p.name for p in cases_dir.iterdir()} == {'plan.json', 'submission.json'} |
            {f'{i:04d}' for i in range(len(plan['cases']))}, 'Exact original case directories')
    for index in range(len(plan['cases'])):
        directory = f'{index:04d}'
        case_root = plain_root(cases_dir / directory)
        require(file_names(case_root, with_directories=True) == (set(CASE_INPUTS), set()),
                'Exact original case input inventory')
        case = job.capture_files(case_root, CASE_INPUTS)
        for name, raw in case.items():
            stored = 'inputs/cases/' + directory + '/' + name if name in SMALL_CASE else 'shared/' + name
            add('cases/' + directory + '/' + name, case_root / name, stored, raw)
    validate_context(retained)
    return retained, witnesses


def validate_witnesses(value, context, plan, snapshot):
    job.exact_keys(value, ('schema', 'sources', 'adapter_argv', 'adapter_source_sha256',
        'physical_evolutions_run', 'component_accepted'), 'Context capture')
    require(value['schema'] == CAPTURE_SCHEMA, 'Context capture schema')
    job.scope(value)
    job.credential_free_argv(value['adapter_argv'])
    require(len(value['adapter_argv']) == 2 and Path(value['adapter_argv'][1]).is_absolute()
            and Path(value['adapter_argv'][1]).name == 'reana_metadata_readonly_adapter.py'
            and value['adapter_source_sha256'] == snapshot['source_sha256'].get(
                'tools/galaxy_python_evidence/reana_metadata_readonly_adapter.py'), 'Frozen acquisition adapter identity')
    expected = {'source/' + n: 'shared/' + n for n in SHARED}
    expected.update({'preflight/' + n: 'inputs/preflight/' + n for n in PREFLIGHT_INPUTS})
    expected.update({'cases/' + n: 'inputs/cases/' + n for n in ('plan.json', 'submission.json')})
    for entry in plan['cases']:
        directory = entry['directory']
        expected.update({'cases/' + directory + '/' + n:
            ('inputs/cases/' + directory + '/' + n if n in SMALL_CASE else 'shared/' + n) for n in CASE_INPUTS})
    require(type(value['sources']) is dict and set(value['sources']) == set(expected), 'Input origin coverage')
    origins = set()
    for role, stored in expected.items():
        row = value['sources'][role]
        job.exact_keys(row, ('original_path', 'stored_path', 'sha256', 'bytes'), 'Input witness')
        require(type(row['original_path']) is str and Path(row['original_path']).is_absolute()
                and row['original_path'] not in origins and row['stored_path'] == stored
                and row['sha256'] == digest(context[stored]) and type(row['bytes']) is int
                and row['bytes'] == len(context[stored]), 'Input origin/materialization link')
        origins.add(row['original_path'])
    return value['adapter_argv']


def status_from(buffers, name, workflow):
    if name not in buffers:
        return None
    try:
        return job.server_status(job.parse(buffers[name]), workflow)
    except (ValueError, TypeError, KeyError, UnicodeError):
        return None


def expected_requests(before):
    return ([('observe', 'server-before.json')] +
            ([('download', n) for n in job.OUTPUT_NAMES] if before in TERMINAL_DOWNLOAD else []) +
            [('observe', 'server-after.json')])


def validate_transport(buffers, entry, command):
    transport = job.parse(buffers['transport.json'])
    job.exact_keys(transport, ('schema', 'client_argv', 'workflow', 'attempts', 'origin'), 'Case transport')
    require(transport['schema'] == 'openmhd.galaxy-python-transport.v1' and transport['origin'] == 'server'
            and transport['workflow'] == entry['workflow'], 'Case transport identity')
    job.credential_free_argv(transport['client_argv'])
    require(transport['client_argv'] == command, 'Captured actual adapter argv')
    requests = expected_requests(status_from(buffers, 'server-before.json', entry['workflow']))
    require(type(transport['attempts']) is list and len(transport['attempts']) <= len(requests), 'Case transport count')
    allowed, successful = {'transport.json'}, {}
    previous_end = None
    for index, attempt in enumerate(transport['attempts']):
        kind, name = requests[index]
        job.exact_keys(attempt, ('schema', 'index', 'action', 'workflow', 'requested_path', 'output',
            'command', 'started_utc', 'finished_utc', 'duration_seconds', 'outcome', 'returncode',
            'stdout', 'stderr', 'download_sha256'), 'Case transport attempt')
        relative = name if kind == 'observe' else 'artifacts/' + name
        requested = None if kind == 'observe' else 'outputs/' + name
        tail = [kind, '--workflow', entry['workflow']] + (['--path', requested] if requested else [])
        tail += ['--output', relative]
        require(attempt['schema'] == 'openmhd.galaxy-python-transport-attempt.v1'
                and type(attempt['index']) is int and attempt['index'] == index
                and attempt['action'] == kind and attempt['workflow'] == entry['workflow']
                and attempt['requested_path'] == requested and attempt['output'] == relative
                and attempt['command'] == transport['client_argv'] + tail, 'Exact read-only transport command')
        job.interval(attempt)
        require(previous_end is None or job.utc(attempt['started_utc']) >= previous_end,
                'Transport attempt time order')
        previous_end = job.utc(attempt['finished_utc'])
        outcome, code = attempt['outcome'], attempt['returncode']
        require(outcome in ('pending_launch', 'success', 'nonzero', 'timeout', 'start_failed', 'invalid_download')
                and (code is None or type(code) is int), 'Transport outcome types')
        require((outcome != 'success' or code == 0) and (outcome != 'nonzero' or code not in (None, 0))
                and (outcome not in ('pending_launch', 'timeout', 'start_failed') or code is None),
                'Transport outcome/returncode')
        for stream in ('stdout', 'stderr'):
            row, path = attempt[stream], f'transport/{index:02d}.{stream}.txt'
            job.exact_keys(row, ('path', 'sha256'), 'Case transport log')
            require(row['path'] == path and path in buffers and row['sha256'] == digest(buffers[path]),
                    'Case transport log link')
            allowed.add(path)
        allowed |= {relative, relative + '.partial'}
        if outcome == 'success':
            require(relative in buffers and relative + '.partial' not in buffers
                    and attempt['download_sha256'] == digest(buffers[relative]), 'Case downloaded byte link')
            successful[relative] = True
            if kind == 'observe':
                observed = job.utc(job.parse(buffers[relative])['observed_utc'])
                require(job.utc(attempt['started_utc']) <= observed <= job.utc(attempt['finished_utc']),
                        'Observation/command time link')
        else:
            require(attempt['download_sha256'] is None, 'Failed download cannot certify bytes')
    require(set(buffers) <= allowed, 'Unexpected case artifact/transport file')
    return dict(all_success=len(transport['attempts']) == len(requests) and len(successful) == len(requests),
                observations_success=all(n in successful for n in ('server-before.json', 'server-after.json')))


def case_row(buffers, snapshot, snapshot_bytes, entry, submission, command):
    row = dict(directory=entry['directory'], selector=entry['specification']['selector'],
        identity=snapshot['test_identities'][entry['specification']['selector']], workflow=entry['workflow'],
        submission_status=submission['status'], status='incomplete', classification='observation_or_transport_loss',
        before_status=status_from(buffers, 'server-before.json', entry['workflow']),
        after_status=status_from(buffers, 'server-after.json', entry['workflow']),
        observations={n: (dict(path=n, sha256=digest(buffers[n]), bytes=len(buffers[n])) if n in buffers else None)
                      for n in ('server-before.json', 'server-after.json')},
        transport_sha256=digest(buffers['transport.json']) if 'transport.json' in buffers else None,
        artifacts={n: (dict(path='artifacts/' + n, sha256=digest(buffers['artifacts/' + n]),
                           bytes=len(buffers['artifacts/' + n])) if 'artifacts/' + n in buffers else
                       dict(path=None, sha256=None, bytes=None)) for n in job.OUTPUT_NAMES},
        external_evidence_required=True)
    for name, artifact in row['artifacts'].items():
        partial = 'artifacts/' + name + '.partial'
        artifact.update(acquisition='retained_see_transport' if artifact['path'] else
                        'missing_see_transport_or_external_workflow_job_logs',
            partial=(dict(path=partial, sha256=digest(buffers[partial]), bytes=len(buffers[partial]))
                     if partial in buffers else None))
    try:
        transported = validate_transport(buffers, entry, command)
    except (ValueError, KeyError, TypeError, UnicodeError):
        return row
    before, after = row['before_status'], row['after_status']
    if before is None or after is None or not transported['observations_success']:
        return row
    if before not in TERMINAL_DOWNLOAD or after not in TERMINAL_DOWNLOAD:
        row.update(status='pending', classification='nonterminal_or_transition')
        if after in ('failed', 'stopped', 'deleted'):
            row.update(status='failed', classification='terminal_external_failure')
        return row
    if before != after:
        return row
    if before != 'finished':
        row.update(status='failed', classification='terminal_external_failure')
    if not transported['all_success'] or not all('artifacts/' + n in buffers for n in job.OUTPUT_NAMES):
        return row
    artifacts = {n: buffers['artifacts/' + n] for n in job.OUTPUT_NAMES}
    try:
        job.validate_case_outputs(artifacts, snapshot_bytes, entry)
    except (ValueError, TypeError, KeyError, UnicodeError):
        try:
            job.validate_case_outputs(artifacts, snapshot_bytes, entry, failed_unittest=True)
            row.update(status='failed', classification='validated_unittest_failure', external_evidence_required=False)
        except (ValueError, TypeError, KeyError, UnicodeError):
            row.update(classification='invalid_or_job_failure_envelope')
        return row
    if before == after == 'finished' and submission['status'] in ('submitted', 'submission uncertain'):
        row.update(status='passed', classification='validated_independent_unittest', external_evidence_required=False)
    else:
        row['classification'] = 'terminal_or_submission_context_not_successful'
    return row


def derive_packet(root):
    """Capture/parse/hash each group from identical buffers, under a global fence.

    Retain one case's output buffers at a time, not the entire output campaign.
    Metadata is bounded per file; archived source members are not omitted.
    """
    names, directories = file_names(root, with_directories=True)
    body = names - {'summary.json', 'files.sha256.json'}
    stamps = {n: job.regular_stamp(root, n) for n in names}
    context_names = {n for n in body if n.startswith(('shared/', 'inputs/'))}
    context = job.capture_files(root, context_names)
    snapshot, plan, submission = validate_context(context)
    allowed_directories = {p.as_posix() for n in names for p in PurePosixPath(n).parents if p.as_posix() != '.'}
    allowed_directories.add('cases')
    allowed_directories |= {'cases/' + e['directory'] + suffix for e in plan['cases']
                            for suffix in ('', '/artifacts', '/transport')}
    require(directories <= allowed_directories, 'Unknown empty packet/case directory')
    controls = job.capture_files(root, ('context_capture.json', 'collection_status.json'))
    command = validate_witnesses(job.parse(controls['context_capture.json']), context, plan, snapshot)
    status = job.parse(controls['collection_status.json'])
    job.exact_keys(status, ('schema', 'status', 'started_utc', 'finished_utc', 'problem',
        'physical_evolutions_run', 'component_accepted'), 'Collection status')
    require(status['schema'] == STATUS_SCHEMA and status['status'] in ('complete', 'failed')
            and (status['problem'] is None if status['status'] == 'complete' else
                 type(status['problem']) is str), 'Collection status/schema')
    job.scope(status)
    require(job.utc(status['finished_utc']) >= job.utc(status['started_utc']), 'Collection interval')
    inventory = {n: dict(sha256=digest(b), bytes=len(b)) for n, b in {**context, **controls}.items()}
    covered, rows = set(inventory), []
    for entry in plan['cases']:
        prefix = 'cases/' + entry['directory'] + '/'
        selected = {n for n in body if n.startswith(prefix)}
        raw = job.capture_files(root, selected)
        inventory.update({n: dict(sha256=digest(b), bytes=len(b)) for n, b in raw.items()})
        covered |= selected
        rows.append(case_row({n[len(prefix):]: b for n, b in raw.items()}, snapshot,
                             context['shared/snapshot.json'], entry,
                             submission[entry['workflow']], command))
    require(covered == body, 'Unknown packet files/case directories')
    require(file_names(root, with_directories=True) == (names, directories)
            and {n: job.regular_stamp(root, n) for n in names} == stamps,
            'Changed packet generation during validation')
    counts = {key: sum(r['status'] == key for r in rows) for key in ('passed', 'failed', 'pending', 'incomplete')}
    summary = dict(schema=SUMMARY_SCHEMA, source_revision=snapshot['source_revision'],
        snapshot_sha256=digest(context['shared/snapshot.json']), archive_sha256=snapshot['archive_sha256'],
        preflight_certificate_sha256=digest(context['shared/preflight_certificate.json']),
        plan_sha256=digest(context['inputs/cases/plan.json']), submission_sha256=digest(context['inputs/cases/submission.json']),
        catalog=dict(test_files=list(job.TEST_FILES), selectors=snapshot['tests'], test_identities=snapshot['test_identities']),
        expected_cases=len(snapshot['tests']), counts=counts, cases=rows, collection_status=status['status'],
        whole_suite_passed=status['status'] == 'complete' and counts['passed'] == len(snapshot['tests']),
        physical_evolutions_run=False, component_accepted=False)
    return summary, inventory


def close_packet(root):
    summary, inventory = derive_packet(root)
    raw = encode(summary)
    with (root / 'summary.json').open('xb') as stream:
        stream.write(raw)
    inventory['summary.json'] = dict(sha256=digest(raw), bytes=len(raw))
    require(file_names(root) == set(inventory) and all(job.capture_files(root, (n,), attempts=1)[n] == raw
            for n in ('summary.json',)), 'Changed closure inventory')
    manifest = dict(schema=FILES_SCHEMA, files=inventory,
                    physical_evolutions_run=False, component_accepted=False)
    with (root / 'files.sha256.json').open('xb') as stream:
        stream.write(encode(manifest))
    return verify_packet(root)


def verify_packet(root):
    root = plain_root(root)
    originals = job.capture_files(root, ('summary.json', 'files.sha256.json', 'shared/snapshot.json'))
    host_tools(job.parse(originals['shared/snapshot.json']))
    manifest = job.parse(originals['files.sha256.json'])
    job.exact_keys(manifest, ('schema', 'files', 'physical_evolutions_run', 'component_accepted'), 'Packet manifest')
    require(manifest['schema'] == FILES_SCHEMA, 'Packet manifest schema')
    job.scope(manifest)
    summary, inventory = derive_packet(root)
    require(typed_equal(job.parse(originals['summary.json']), summary), 'Derived whole-catalog verdict mismatch')
    inventory['summary.json'] = dict(sha256=digest(originals['summary.json']), bytes=len(originals['summary.json']))
    require(typed_equal(manifest['files'], inventory) and file_names(root) == set(inventory) | {'files.sha256.json'},
            'Closed packet hashes/bytes/paths')
    require(job.capture_files(root, originals, attempts=1) == originals, 'Changed final summary/manifest')
    return summary


def host_tools(snapshot):
    directory = plain_root(Path(__file__).parent)
    tools = job.capture_files(directory, TOOLS)
    require(all(digest(raw) == snapshot['source_sha256'].get('tools/galaxy_python_evidence/' + name)
                for name, raw in tools.items()), 'Use exact frozen collector/preparer/job/adapter sources')
    return tools


def pinned_tools(snapshot, command):
    job.credential_free_argv(command)
    require(len(command) == 2 and Path(command[1]).is_absolute()
            and Path(command[1]).name == 'reana_metadata_readonly_adapter.py', 'Exact Python/adapter argv')
    tools = host_tools(snapshot)
    actual = job.capture_files(plain_root(Path(command[1]).parent), (Path(command[1]).name,))
    require(actual[Path(command[1]).name] == tools['reana_metadata_readonly_adapter.py'], 'Frozen actual GET-only adapter')
    return tools


def observe_case(output, command, entry):
    output.mkdir(parents=True)
    (output / 'artifacts').mkdir()
    (output / 'transport').mkdir()
    transport = dict(schema='openmhd.galaxy-python-transport.v1', client_argv=command,
        workflow=entry['workflow'], attempts=[], origin='server')
    prepare.adapter_attempt(command, 'observe', entry['workflow'], 'server-before.json', output, transport, required=False)
    before = None
    if (output / 'server-before.json').exists():
        before = status_from(job.capture_files(output, ('server-before.json',)), 'server-before.json', entry['workflow'])
    for kind, name in expected_requests(before)[1:]:
        prepare.adapter_attempt(command, kind, entry['workflow'], name, output, transport, required=False)


def collect(source_dir, preflight_dir, cases_dir, output, command):
    """Only observe/download; each adapter process has the required 300s timeout.

    Sequential clients limit local API traffic only, never remote job resources.
    A fresh collection may observe the same immutable workflows again; no retry
    or mutation of workflows occurs here. Loss can leave an unclosed directory.
    """
    source_dir, preflight_dir, cases_dir = map(plain_root, (source_dir, preflight_dir, cases_dir))
    context, witnesses = capture_context(source_dir, preflight_dir, cases_dir)
    snapshot, plan, _ = validate_context(context)
    tools = pinned_tools(snapshot, command)
    output = Path(output).absolute()
    plain_root(output.parent)
    require(not output.exists() and not output.is_symlink(), 'Fresh collection destination required')
    output.mkdir()
    status = dict(schema=STATUS_SCHEMA, status='collecting', started_utc=datetime.now(timezone.utc).isoformat(),
        finished_utc=None, problem=None, physical_evolutions_run=False, component_accepted=False)
    job.dump(output / 'collection_status.json', status)
    stage = 'context_materialization'
    try:
        for name, raw in context.items():
            target = output / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(raw)
        job.dump(output / 'context_capture.json', dict(schema=CAPTURE_SCHEMA, sources=witnesses,
            adapter_argv=command, adapter_source_sha256=snapshot['source_sha256'][
                'tools/galaxy_python_evidence/reana_metadata_readonly_adapter.py'],
            physical_evolutions_run=False, component_accepted=False))
        stage = 'case_observation'
        for entry in plan['cases']:
            observe_case(output / 'cases' / entry['directory'], command, entry)
        stage = 'original_input_fence'
        require(capture_context(source_dir, preflight_dir, cases_dir) == (context, witnesses),
                'Changed original inputs before result closure')
        stage = 'frozen_tool_fence'
        require(pinned_tools(snapshot, command) == tools, 'Changed adapter/collector before closure')
        status['status'] = 'complete'
    except Exception as error:
        status.update(status='failed', problem=stage + ':' + type(error).__name__)
    finally:
        status['finished_utc'] = datetime.now(timezone.utc).isoformat()
        job.dump(output / 'collection_status.json', status)
    try:
        return close_packet(output)
    except Exception as error:
        status.update(status='failed', problem='ClosureRejected:' + type(error).__name__,
                      finished_utc=datetime.now(timezone.utc).isoformat())
        job.dump(output / 'collection_status.json', status)
        raise ValueError('Unclosed result collection; preserve actual bytes/external receipts') from None
