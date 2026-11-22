"""Prepare committed metadata workflows; collect read-only preflight evidence.

snapshot -> generic submit -> observe-preflight -> cases -> generic submit ->
collect-cases -> verify-results. Submission alone is never test evidence.
The observer adapter exposes only observe/download (never run/start/submit).
No tests are imported or executed by source/AST snapshot discovery.
"""
import argparse
import base64
from datetime import datetime, timezone
import gzip
import io
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import sys
import tarfile
import time

import reana_metadata_job as job

if not __debug__:
    raise RuntimeError('Metadata workflow preparation rejects optimized Python')

IMAGE, RESOURCES, TEST_FILES = job.IMAGE, job.RESOURCES, job.TEST_FILES
ROOTS = ('tools/m1_evidence/', 'tests/reference/m1_acceptance/',
         'tests/reference/m1_iterative_step_campaigns/')
require, digest, encode, dump = job.require, job.digest, job.encode, job.dump


def safe_name(value):
    require(re.fullmatch(r'[a-z][a-z0-9-]{0,36}', value) is not None,
            'Use a short lowercase workflow prefix')
    return value


def tests_from_source(sources):
    return list(job.identities_from_sources(sources))


def create_case(directory, workflow, source, snapshot_bytes, job_bytes, case, certificate=None):
    directory.mkdir(parents=True)
    case = dict(case, workflow=workflow + '.1')
    inputs = {'source.tar.gz': source, 'snapshot.json': snapshot_bytes,
              'job.py': job_bytes, 'case.json': encode(case)}
    if certificate is not None:
        inputs['preflight_certificate.json'] = certificate
    for name, data in inputs.items():
        (directory / name).write_bytes(data)
    payload_bytes = encode(dict(schema='openmhd.metadata-case-payload.v2',
                               input_sha256={n: digest(b) for n, b in inputs.items()}))
    (directory / 'payload.json').write_bytes(payload_bytes)
    spec_bytes = encode(job.workflow_document(inputs))
    (directory / 'reana.yaml').write_bytes(spec_bytes)
    return dict(directory=directory.name, specification=case, workflow=workflow + '.1',
                payload_sha256=digest(payload_bytes), workflow_sha256=digest(spec_bytes))


def snapshot(output, prefix):
    prefix = safe_name(prefix)
    repo = Path.cwd()
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', revision,
        '--', *[r.rstrip('/') for r in ROOTS]], text=True).splitlines()
    require(names and all(any(n.startswith(r) for r in ROOTS) for n in names), 'Source path set')
    sources = {}
    for name in names:
        require('__pycache__' not in PurePosixPath(name).parts, 'Tracked cache file')
        data = subprocess.check_output(['git', 'show', revision + ':' + name])
        require((repo / name).is_file() and not (repo / name).is_symlink(), 'Source must be regular: ' + name)
        require((repo / name).read_bytes() == data, 'Uncommitted source change: ' + name)
        sources[name] = data
    identities = job.identities_from_sources(sources)
    require(job.JOB_NAME in sources, 'Commit the metadata runner first')
    archive_bytes = io.BytesIO()
    with tarfile.open(fileobj=archive_bytes, mode='w', format=tarfile.PAX_FORMAT) as archive:
        for name, data in sorted(sources.items()):
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(data), 0o644, 0
            archive.addfile(info, io.BytesIO(data))
    packed = gzip.compress(archive_bytes.getvalue(), mtime=0)
    metadata = dict(schema=job.SOURCE_SCHEMA,
        created_utc=datetime.now(timezone.utc).isoformat(), source_revision=revision,
        source_sha256={n: digest(b) for n, b in sorted(sources.items())},
        archive_sha256=digest(packed), job_sha256=digest(sources[job.JOB_NAME]), image=IMAGE,
        tests=list(identities), test_identities=identities, test_files=list(TEST_FILES),
        resources=RESOURCES, scientific_tests_or_evolutions_run=False, full_m1_accepted=False)
    job.validate_snapshot(metadata)
    metadata_bytes = encode(metadata)
    require(not output.exists(), 'Preserve an existing metadata snapshot')
    output.mkdir(parents=True)
    (output / 'source.tar.gz').write_bytes(packed)
    (output / 'snapshot.json').write_bytes(metadata_bytes)
    (output / 'job.py').write_bytes(sources[job.JOB_NAME])
    plan_dir = output / 'preflight'
    workflow = prefix + '-' + digest(metadata_bytes)[:12] + '-preflight'
    entry = create_case(plan_dir / '0000', workflow, packed, metadata_bytes,
                        sources[job.JOB_NAME], dict(kind='preflight', resources=RESOURCES))
    dump(plan_dir / 'plan.json', dict(schema='openmhd.metadata-case-plan.v2',
        snapshot_sha256=digest(metadata_bytes), cases=[entry], full_m1_accepted=False))
    print('Prepared metadata preflight only:', plan_dir)
    print('Cases require actual terminal server/status/download certificate; no tests ran.')


def read_source(source_dir):
    buffers = job.capture_files(source_dir, ('snapshot.json', 'source.tar.gz', 'job.py'))
    metadata = job.parse(buffers['snapshot.json'])
    job.validate_snapshot(metadata)
    require(digest(buffers['source.tar.gz']) == metadata['archive_sha256']
            and digest(buffers['job.py']) == metadata['job_sha256'], 'Metadata source changed')
    require(Path(job.__file__).read_bytes() == buffers['job.py'],
            'Use the exact committed certificate validator from this snapshot')
    return buffers, metadata


def redacted(data):
    """Retain diagnostics without known credential forms; never echo raw output.

    This is not general secret-content certification. Adapters/fixtures must not
    print credentials; review retained logs before distribution.
    """
    text = data.decode('utf-8', errors='replace') if isinstance(data, bytes) else (data or '')
    text = re.sub(r'(?i)(bearer\s+)[^\s\"\']+', r'\1[REDACTED]', text)
    text = re.sub(r'(?i)((?:token|password|secret|authorization)[\"\']?\s*[:=]\s*[\"\']?)[^\s\"\'&,]+',
                  r'\1[REDACTED]', text)
    return text.encode()


def adapter_attempt(command, action, workflow, name, output, transport, *, required=True):
    index = len(transport['attempts'])
    requested = None if action == 'observe' else 'outputs/' + name
    relative = name if action == 'observe' else 'artifacts/' + name
    argv = [*command, action, '--workflow', workflow]
    if requested:
        argv += ['--path', requested]
    argv += ['--output', relative]
    started, clock = datetime.now(timezone.utc).isoformat(), time.monotonic()
    receipt = dict(schema='openmhd.metadata-transport-attempt.v1', index=index, action=action,
        workflow=workflow, requested_path=requested, output=relative, command=argv,
        started_utc=started, finished_utc=started, duration_seconds=0.0,
        outcome='pending_launch', returncode=None, download_sha256=None,
        stdout=dict(path=f'transport/{index:02d}.stdout.txt', sha256=digest(b'')),
        stderr=dict(path=f'transport/{index:02d}.stderr.txt', sha256=digest(b'')))
    for stream in ('stdout', 'stderr'):
        (output / receipt[stream]['path']).write_bytes(b'')
    transport['attempts'].append(receipt)
    dump(output / 'transport.json', transport)  # Intent survives start/transport failure.
    stdout, stderr = b'', b''
    try:
        completed = subprocess.run(argv, cwd=output, capture_output=True, timeout=300)
        stdout, stderr = completed.stdout, completed.stderr
        receipt['returncode'] = completed.returncode
        receipt['outcome'] = 'success' if completed.returncode == 0 else 'nonzero'
    except subprocess.TimeoutExpired as error:
        stdout, stderr = error.stdout or b'', error.stderr or b''
        receipt['outcome'] = 'timeout'
    except OSError:
        receipt['outcome'] = 'start_failed'
    finally:
        for stream, raw in (('stdout', stdout), ('stderr', stderr)):
            retained = redacted(raw)
            (output / receipt[stream]['path']).write_bytes(retained)
            receipt[stream]['sha256'] = digest(retained)
        receipt.update(finished_utc=datetime.now(timezone.utc).isoformat(),
                       duration_seconds=time.monotonic() - clock)
        if receipt['outcome'] == 'success':
            try:
                buffers = job.capture_files(output, (relative,))
                receipt['download_sha256'] = digest(buffers[relative])
            except (ValueError, OSError):
                receipt['outcome'] = 'invalid_download'
        dump(output / 'transport.json', transport)
    if required:
        require(receipt['outcome'] == 'success', 'Read-only adapter failed; retain partial observation')
    return receipt


def observe_preflight(source_dir, output, command):
    """Actual read-only adapter calls; no fixture/status injection CLI exists."""
    job.credential_free_argv(command)
    source, _ = read_source(source_dir)
    paths = ('plan.json', 'submission.json', '0000/payload.json', '0000/reana.yaml', '0000/case.json')
    plan_buffers = job.capture_files(source_dir / 'preflight', paths)
    plan = job.parse(plan_buffers['plan.json'])
    require(type(plan.get('cases')) is list and len(plan['cases']) == 1, 'One planned preflight')
    entry = plan['cases'][0]
    require(plan['snapshot_sha256'] == digest(source['snapshot.json'])
            and entry['directory'] == '0000', 'Planned snapshot/preflight')
    require(not output.exists(), 'Preserve an existing immutable observation; use a fresh path')
    output.mkdir(parents=True)
    (output / 'artifacts').mkdir()
    (output / 'transport').mkdir()
    for name, data in plan_buffers.items():
        (output / PurePosixPath(name).name).write_bytes(data)
    transport = dict(schema='openmhd.metadata-transport.v1', client_argv=command,
                     workflow=entry['workflow'], attempts=[], origin='server')
    adapter_attempt(command, 'observe', entry['workflow'], 'server-before.json', output, transport)
    # Reject stopped/pending/ambiguous observations before attempting downloads.
    before = job.capture_files(output, ('server-before.json',))
    job.validate_server(job.parse(before['server-before.json']), entry['workflow'])
    for name in job.OUTPUT_NAMES:
        adapter_attempt(command, 'download', entry['workflow'], name, output, transport)
    adapter_attempt(command, 'observe', entry['workflow'], 'server-after.json', output, transport)
    names = {'plan.json', 'submission.json', 'payload.json', 'reana.yaml', 'case.json',
             'server-before.json', 'server-after.json', 'transport.json'}
    names |= {'artifacts/' + n for n in job.OUTPUT_NAMES}
    for attempt in transport['attempts']:
        names |= {attempt[s]['path'] for s in ('stdout', 'stderr')}
    buffers = job.capture_files(output, names)
    certificate_bytes = encode(dict(schema=job.CERT_SCHEMA,
        snapshot_sha256=digest(source['snapshot.json']),
        capture_sha256={n: digest(b) for n, b in buffers.items()},
        buffers={n: base64.b64encode(b).decode('ascii') for n, b in buffers.items()},
        scientific_tests_or_evolutions_run=False, full_m1_accepted=False))
    job.validate_certificate(certificate_bytes, source['snapshot.json'])
    # Every embedded original plan byte must still match the coherent source view.
    final_plan = job.capture_files(source_dir / 'preflight', paths)
    require(final_plan == plan_buffers, 'Changed preflight plan/submission during observation')
    # A final unchanged fence prevents release from a concurrently replaced download.
    require(job.capture_files(output, names, attempts=1) == buffers, 'Changed download before certificate release')
    (output / 'certificate.json').write_bytes(certificate_bytes)
    print('Collected terminal preflight certificate:', output / 'certificate.json')


def prepare_cases(source_dir, preflight_dir, output, prefix):
    prefix = safe_name(prefix)
    source, metadata = read_source(source_dir)
    observation = job.capture_files(preflight_dir, ('certificate.json',))
    certificate_bytes = observation['certificate.json']
    certificate = job.validate_certificate(certificate_bytes, source['snapshot.json'])
    # Bind to the exact original locally retained plan, not just its workflow label.
    plan_names = ('plan.json', 'submission.json', '0000/payload.json', '0000/reana.yaml', '0000/case.json')
    original = job.capture_files(source_dir / 'preflight', plan_names)
    for name, data in original.items():
        key = PurePosixPath(name).name
        require(base64.b64decode(certificate['buffers'][key], validate=True) == data,
                'Certificate/original plan identity: ' + name)
    require(not output.exists(), 'Preserve an existing case plan')
    # All checks complete before producing any dependent directory or plan.
    output.mkdir(parents=True)
    entries = []
    prefix = prefix + '-' + digest(source['snapshot.json'])[:12]
    for index, selector in enumerate(metadata['tests']):
        case = dict(kind='unittest', selector=selector, resources=RESOURCES,
                    preflight_certificate_sha256=digest(certificate_bytes))
        entries.append(create_case(output / f'{index:04d}', f'{prefix}-{index:04d}',
            source['source.tar.gz'], source['snapshot.json'], source['job.py'], case, certificate_bytes))
    dump(output / 'plan.json', dict(schema='openmhd.metadata-case-plan.v2',
        snapshot_sha256=digest(source['snapshot.json']), source_revision=metadata['source_revision'],
        coverage=dict(test_files=list(TEST_FILES), selectors=metadata['tests'],
                      test_identities=metadata['test_identities']),
        preflight_certificate_sha256=digest(certificate_bytes), cases=entries, full_m1_accepted=False))
    print('Prepared', len(entries), 'independent metadata workflows:', output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('snapshot', 'observe-preflight', 'cases', 'collect-cases', 'verify-results'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--prefix', default='openmhd-m1-archive-metadata')
    parser.add_argument('--snapshot', type=Path)
    parser.add_argument('--preflight', type=Path, help='Immutable observation directory with certificate.json')
    parser.add_argument('--client', help='Credential-free absolute read-only adapter argv, shell-quoted')
    parser.add_argument('--cases', type=Path, help='Original immutable unittest-case plan and submission directory')
    parser.add_argument('--packet', type=Path, help='Closed metadata result packet for offline verification')
    args = parser.parse_args()
    if args.action in ('collect-cases', 'verify-results'):
        import collect_metadata_reana_results as results
        if args.action == 'collect-cases':
            require(all(v is not None for v in (args.snapshot, args.preflight, args.cases, args.output))
                    and args.client, 'collect-cases needs --snapshot --preflight --cases --output --client')
            summary = results.collect(args.snapshot, args.preflight, args.cases, args.output,
                                      shlex.split(args.client))
        else:
            require(args.packet is not None, 'verify-results needs --packet')
            summary = results.verify_packet(args.packet)
        print('Metadata-only case verdict:', summary['counts'], 'whole_suite_passed=', summary['whole_suite_passed'])
        print('Scientific execution/acceptance flags remain false; retain separate output review.')
        return 0 if summary['whole_suite_passed'] else 1
    require(args.output is not None, 'Preparation/observation requires --output')
    if args.action == 'snapshot':
        snapshot(args.output.resolve(), args.prefix)
    elif args.action == 'observe-preflight':
        require(args.snapshot is not None and args.client, 'observe-preflight needs --snapshot and --client')
        observe_preflight(args.snapshot.resolve(), args.output.resolve(), shlex.split(args.client))
    else:
        require(args.snapshot is not None and args.preflight is not None,
                'cases requires --snapshot and --preflight')
        prepare_cases(args.snapshot.resolve(), args.preflight.resolve(), args.output.resolve(), args.prefix)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
