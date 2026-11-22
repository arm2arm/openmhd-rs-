"""REANA-only metadata regression job; never runs scientific evolutions.

This file is uploaded as job.py by prepare_metadata_reana.py. A normal job
verifies its source package before running one named unittest, or a separate
source/import preflight. The child modes write machine-readable results.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import sys
import tarfile
import unittest

if not __debug__:
    raise RuntimeError('Metadata evidence jobs reject optimized Python')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=1, allow_nan=False) + '\n')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def child(mode, selector, result_path):
    """Executed only in the REANA child process, with the source as cwd."""
    sys.path.insert(0, str(Path.cwd()))
    if mode == 'preflight':
        snapshot = json.loads(Path('../snapshot.json').read_bytes())
        parsed = []
        for name in snapshot['source_sha256']:
            if name.endswith('.py'):
                source = Path(name).read_bytes()
                compile(ast.parse(source, filename=name), name, 'exec')
                parsed.append(name)
        loader = unittest.TestLoader()
        for name in snapshot['tests']:
            suite = loader.loadTestsFromName(name)
            require(not loader.errors and suite.countTestCases() == 1,
                    'Unresolvable one-case unittest: ' + name)
        value = dict(kind='preflight', status='completed', parsed_files=parsed,
                     test_selectors=snapshot['tests'], resolved_tests=len(snapshot['tests']),
                     scientific_tests_or_evolutions_run=False)
        dump(result_path, value)
        return 0
    require(mode == 'unittest' and selector, 'Invalid child mode')
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(selector)
    require(not loader.errors and suite.countTestCases() == 1,
            'Case must resolve to exactly one unittest')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    success = (result.wasSuccessful() and result.testsRun == 1 and not result.skipped
               and not result.expectedFailures and not result.unexpectedSuccesses)
    dump(result_path, dict(kind='unittest', selector=selector,
        status='completed' if success else 'failed', tests_run=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
        expected_failures=len(result.expectedFailures),
        unexpected_successes=len(result.unexpectedSuccesses), passed=success,
        scientific_tests_or_evolutions_run=False))
    return 0 if success else 1


def run():
    work = Path.cwd().resolve()
    payload_bytes = (work / 'payload.json').read_bytes()
    payload = json.loads(payload_bytes)
    for name, expected in payload['input_sha256'].items():
        path = PurePosixPath(name)
        require(not path.is_absolute() and '..' not in path.parts,
                'Unsafe input path')
        require(digest((work / name).read_bytes()) == expected, 'Changed input: ' + name)
    snapshot_bytes = (work / 'snapshot.json').read_bytes()
    snapshot = json.loads(snapshot_bytes)
    case = json.loads((work / 'case.json').read_bytes())
    require(snapshot['schema'] == 'openmhd.metadata-regression-source.v1', 'Snapshot schema')
    require(digest((work / 'source.tar.gz').read_bytes()) == snapshot['archive_sha256'],
            'Changed source archive')
    require(digest(Path(__file__).read_bytes()) == snapshot['job_sha256'], 'Changed job source')
    require(snapshot['job_sha256'] == snapshot['source_sha256'][
        'tools/m1_evidence/reana_metadata_job.py'], 'Job/source catalog link')
    require(case['kind'] in ('preflight', 'unittest'), 'Unknown case kind')
    if case['kind'] == 'unittest':
        require(case['selector'] in snapshot['tests'], 'Unregistered test selector')
        preflight_bytes = (work / 'preflight_result.json').read_bytes()
        preflight = json.loads(preflight_bytes)
        require(digest(preflight_bytes) == case['preflight_result_sha256'], 'Preflight link')
        require(preflight['status'] == 'completed' and preflight['passed'], 'Preflight failed')
        require(preflight['snapshot_sha256'] == digest(snapshot_bytes), 'Preflight source changed')
        require(preflight['child_result']['test_selectors'] == snapshot['tests'],
                'Preflight selector coverage')
    source = work / 'source'
    source.mkdir()
    with tarfile.open(work / 'source.tar.gz', 'r:gz') as archive:
        members = archive.getmembers()
        require(len(members) == len(snapshot['source_sha256']), 'Source archive count')
        require({m.name for m in members} == set(snapshot['source_sha256']), 'Source archive paths')
        for member in members:
            name = PurePosixPath(member.name)
            require(member.isfile() and not name.is_absolute() and '..' not in name.parts,
                    'Source archive must contain regular relative files')
            stream = archive.extractfile(member)
            require(stream is not None, 'Unreadable source member')
            data = stream.read()
            require(digest(data) == snapshot['source_sha256'][member.name],
                    'Source member hash: ' + member.name)
            target = source.joinpath(*name.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    output = work / 'outputs'
    output.mkdir()
    runtime = dict(python=sys.version, executable=sys.executable,
        implementation=platform.python_implementation(), platform=platform.platform(),
        optimized=sys.flags.optimize, image=snapshot['image'], visible_cpus=os.cpu_count(),
        declared_resources=case['resources'])
    for name in ('cpu.max', 'memory.max'):
        path = Path('/sys/fs/cgroup') / name
        runtime[name] = path.read_text().strip() if path.exists() else None
    dump(output / 'runtime.json', runtime)
    environment = dict(os.environ)
    environment.update(PYTHONDONTWRITEBYTECODE='1', PYTHONHASHSEED='0',
        OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', RAYON_NUM_THREADS='1')
    environment.pop('PYTHONOPTIMIZE', None)
    child_path = output / 'child_result.json'
    argv = [sys.executable, str(Path(__file__).resolve()),
            '--child', case['kind'], '--result', str(child_path)]
    if case['kind'] == 'unittest':
        argv += ['--selector', case['selector']]
    started = datetime.now(timezone.utc).isoformat()
    outcome, returncode, problem = 'start_failed', None, None
    with (output / 'stdout.txt').open('wb') as stdout, (output / 'stderr.txt').open('wb') as stderr:
        try:
            completed = subprocess.run(argv, cwd=source, env=environment,
                stdout=stdout, stderr=stderr, timeout=case['resources']['timeout_seconds'])
            returncode = completed.returncode
            outcome = 'success' if returncode == 0 else 'nonzero'
        except subprocess.TimeoutExpired:
            outcome = 'timeout'
        except OSError as error:
            problem = type(error).__name__
    result = json.loads(child_path.read_bytes()) if child_path.exists() else None
    passed = outcome == 'success' and result is not None and result['status'] == 'completed'
    if case['kind'] == 'unittest':
        passed = passed and result.get('passed') is True and result.get('tests_run') == 1
    record = dict(schema='openmhd.metadata-regression-result.v1',
        status='completed' if passed else 'failed', passed=passed,
        started_utc=started, finished_utc=datetime.now(timezone.utc).isoformat(),
        case=case, outcome=outcome, returncode=returncode, problem=problem,
        command=argv, child_result=result, source_revision=snapshot['source_revision'],
        snapshot_sha256=digest(snapshot_bytes), payload_sha256=digest(payload_bytes),
        source_sha256=snapshot['source_sha256'], runtime_sha256=digest((output / 'runtime.json').read_bytes()),
        scientific_tests_or_evolutions_run=False, full_m1_accepted=False)
    dump(output / 'result.json', record)
    manifest = {'outputs/' + p.name: digest(p.read_bytes())
                for p in sorted(output.iterdir()) if p.is_file()}
    dump(output / 'artifacts.sha256.json', manifest)
    print(case['kind'], case.get('selector', ''), record['status'], flush=True)
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child', choices=('preflight', 'unittest'))
    parser.add_argument('--selector')
    parser.add_argument('--result', type=Path)
    args = parser.parse_args()
    if args.child:
        require(args.result is not None, 'Missing child result path')
        return child(args.child, args.selector, args.result)
    return run()


if __name__ == '__main__':
    raise SystemExit(main())
