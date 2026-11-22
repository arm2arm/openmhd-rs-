"""Source-pinned REANA Python arithmetic/harness job and certificate validators.

Import is inert. Only main/run/child execute work. All intentional executions,
including this module's synthetic controls, belong on REANA, never the host.
"""
import argparse
import ast
import base64
from datetime import datetime, timezone
import hashlib
import importlib.util
import inspect
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import signal
import stat
import subprocess
import sys
import tarfile
import time
import types
import unittest

IMAGE = ('gitlab-p4n.aip.de:5005/p4nreana/reana-env@sha256:'
         'aebd7911df9e1e97ad67d15f4c32ab23996000282183fad3bf7a480756522bd7')
RESOURCES = dict(threads=1, memory='2Gi', timeout_seconds=180)
TEST_FILES = ('scripts/test_galaxy_preflight.py',
              'scripts/test_galaxy_cases.py',
              'scripts/test_galaxy_submission.py',
              'scripts/test_galaxy_geometry3_reference.py',
              'scripts/test_galaxy_gravity_reference.py',
              'scripts/test_galaxy_geometry3_bridge.py',
              'scripts/test_galaxy_geometry3_compare.py',
              'scripts/test_galaxy_python_evidence.py',
              'scripts/test_galaxy_geometry3_reference_case.py',
              'scripts/test_prepare_geometry3_reference.py',
              'scripts/test_galaxy_gravity_bridge.py',
              'scripts/test_galaxy_gravity_compare.py')
JOB_NAME = 'tools/galaxy_python_evidence/reana_metadata_job.py'
OUTPUT_NAMES = ('result.json', 'runtime.json', 'command.json', 'stdout.txt',
                'stderr.txt', 'child_result.json', 'child_raw.bin', 'artifacts.sha256.json')
OUTPUTS = tuple('outputs/' + n for n in OUTPUT_NAMES)
SOURCE_SCHEMA = 'openmhd.galaxy-python-regression-source.v2'
RESULT_SCHEMA = 'openmhd.galaxy-python-regression-result.v2'
CHILD_SCHEMA = 'openmhd.galaxy-python-child-result.v2'
RUNTIME_SCHEMA = 'openmhd.galaxy-python-runtime.v2'
CERT_SCHEMA = 'openmhd.galaxy-python-preflight-certificate.v2'
SERVER_SCHEMA = 'openmhd.metadata-server-observation.v1'
MAX_FILE_BYTES = 16 * 1024 * 1024
DISPATCH_NAMES = ('__new__', '__init__', '__call__', '__getattribute__', '__getattr__',
                  '__setattr__', 'run', 'debug', 'id', 'countTestCases', 'defaultTestResult',
                  '_callTestMethod', '_callSetUp', '_callTearDown', '_callCleanup')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, indent=1, allow_nan=False) + '\n').encode()


def dump(path, value):
    path.write_bytes(encode(value))


def parse(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=unique,
                      parse_constant=lambda value: require(False, 'Nonfinite JSON: ' + value))


def exact_keys(value, keys, label):
    require(type(value) is dict and set(value) == set(keys), label + ' fields')


def is_hash(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def scope(value):
    require(value.get('physical_evolutions_run') is False
            and value.get('component_accepted') is False, 'Python arithmetic/harness scope')


def utc(value):
    require(type(value) is str, 'UTC timestamp type')
    parsed = datetime.fromisoformat(value)
    require(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0,
            'UTC timestamp')
    return parsed


def interval(value):
    require(utc(value['finished_utc']) >= utc(value['started_utc'])
            and type(value['duration_seconds']) in (int, float)
            and 0 <= value['duration_seconds'] < float('inf'), 'Command interval')


def regular_stamp(root, name):
    path = PurePosixPath(name)
    require(type(name) is str and path.as_posix() == name and path.parts
            and not path.is_absolute() and '..' not in path.parts, 'Unsafe relative path')
    current = root
    for part in path.parts:
        current = current / part
        require(not current.is_symlink(), 'Linked input: ' + name)
    info = current.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_size <= MAX_FILE_BYTES,
            'Nonregular or excessive metadata file: ' + name)
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def capture_files(root, names, attempts=3, reader=None):
    """One buffer per file per attempt, with before/after generation fences.

    A replaced generation is retried at most three times. No caller may parse,
    hash or export by reopening files; use these returned immutable buffers.
    This detects observable changes, not malicious in-place timestamp forgery.
    """
    require(type(attempts) is int and 1 <= attempts <= 3, 'Capture retry bound')
    reader = reader or (lambda path: path.read_bytes())
    names = tuple(sorted(names))
    require(len(names) == len(set(names)), 'Duplicate capture paths')
    for _ in range(attempts):
        try:
            before = {n: regular_stamp(root, n) for n in names}
            buffers = {n: reader(root / n) for n in names}
            after = {n: regular_stamp(root, n) for n in names}
            if before == after and all(len(buffers[n]) == after[n][2] for n in names):
                return buffers
        except FileNotFoundError:
            pass
    raise ValueError('Incoherent metadata generation; no dependent release')


def alias_for(module, source_hash):
    return 'galaxy_python_test_' + digest((module + ':' + source_hash).encode())[:20]


def identities_from_sources(sources, test_files=TEST_FILES):
    """Frozen supported form: undecorated plain TestCase/direct sync methods.

    Unsupported inheritance, factories, async/decorated methods, load_tests,
    custom TestCase dispatch/identity and duplicate definitions fail closed.
    Runtime checks additionally reject dynamic changes/imported test classes.
    """
    identities = {}
    for name in test_files:
        require(name in sources, 'Missing committed metadata tests: ' + name)
        module = name.removesuffix('.py').replace('/', '.')
        tree = ast.parse(sources[name], filename=name)
        require(not any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and n.name == 'load_tests' for n in tree.body), 'Unsupported load_tests')
        classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
        require(len({c.name for c in classes}) == len(classes), 'Duplicate test class')
        supported = []
        for cls in classes:
            methods = [m for m in cls.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                       and m.name.startswith('test_')]
            base = (len(cls.bases) == 1 and isinstance(cls.bases[0], ast.Attribute)
                    and isinstance(cls.bases[0].value, ast.Name)
                    and cls.bases[0].value.id == 'unittest' and cls.bases[0].attr == 'TestCase')
            if not methods:
                require(not base and not any(isinstance(b, ast.Name) and b.id in supported
                                             for b in cls.bases), 'Unsupported inherited/empty tests')
                continue
            require(base and not cls.decorator_list and not cls.keywords,
                    'Only plain unittest.TestCase classes are supported')
            require(not any(isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and m.name in DISPATCH_NAMES for m in cls.body),
                    'Custom TestCase dispatch/identity is unsupported')
            require(len({m.name for m in methods}) == len(methods), 'Duplicate test method')
            supported.append(cls.name)
            for method in methods:
                require(type(method) is ast.FunctionDef and not method.decorator_list
                        and len(method.args.args) == 1 and method.args.args[0].arg == 'self'
                        and not method.args.posonlyargs and not method.args.kwonlyargs
                        and method.args.vararg is None and method.args.kwarg is None
                        and not method.args.defaults, 'Unsupported unittest method')
                selector = module + '.' + cls.name + '.' + method.name
                source_hash = digest(sources[name])
                identities[selector] = dict(selector=selector, source_path=name,
                    source_sha256=source_hash, class_name=cls.name, method=method.name,
                    runtime_id=alias_for(module, source_hash) + '.' + cls.name + '.' + method.name)
        require(any(s.startswith(module + '.') for s in identities), 'No test methods: ' + name)
    return dict(sorted(identities.items()))


def validate_snapshot(snapshot):
    exact_keys(snapshot, ('schema', 'created_utc', 'source_revision', 'source_sha256',
        'archive_sha256', 'job_sha256', 'image', 'tests', 'test_identities', 'test_files',
        'resources', 'physical_evolutions_run', 'component_accepted'), 'Snapshot')
    require(snapshot['schema'] == SOURCE_SCHEMA and snapshot['image'] == IMAGE
            and snapshot['resources'] == RESOURCES and snapshot['test_files'] == list(TEST_FILES),
            'Snapshot schema/policy')
    require(type(snapshot['resources']) is dict
            and type(snapshot['resources']['threads']) is int
            and type(snapshot['resources']['timeout_seconds']) is int, 'Snapshot resource types')
    scope(snapshot)
    utc(snapshot['created_utc'])
    require(type(snapshot['source_revision']) is str
            and re.fullmatch('[0-9a-f]{40}', snapshot['source_revision']), 'Source revision')
    catalog = snapshot['source_sha256']
    require(type(catalog) is dict and catalog and all(is_hash(v) for v in catalog.values()),
            'Source catalog')
    require(is_hash(snapshot['archive_sha256']) and is_hash(snapshot['job_sha256'])
            and catalog.get(JOB_NAME) == snapshot['job_sha256'], 'Job/source identity')
    tests, identities = snapshot['tests'], snapshot['test_identities']
    require(type(tests) is list and tests == sorted(set(tests)) and tests
            and type(identities) is dict and set(identities) == set(tests), 'Selector coverage')
    for selector in tests:
        value = identities[selector]
        exact_keys(value, ('selector', 'source_path', 'source_sha256', 'class_name',
                          'method', 'runtime_id'), 'Test identity')
        module, cls, method = selector.rsplit('.', 2)
        path = module.replace('.', '/') + '.py'
        require(path in TEST_FILES and value == dict(selector=selector, source_path=path,
            source_sha256=catalog[path], class_name=cls, method=method,
            runtime_id=alias_for(module, catalog[path]) + '.' + cls + '.' + method), 'Selector identity')


def workflow_document(inputs):
    return dict(version='0.9.0', inputs=dict(files=sorted(inputs) + ['payload.json']),
        workflow=dict(type='serial', specification=dict(steps=[dict(name='one-galaxy-python-case',
            environment=IMAGE, compute_backend='kubernetes', kubernetes_memory_limit='2Gi',
            kubernetes_cpu_request='1', kubernetes_cpu_limit='1', commands=['python3 job.py'])])),
        outputs=dict(files=list(OUTPUTS)))


def load_one(selector, identity):
    """Import an explicit file and instantiate only its declared plain leaf."""
    module_name, class_name, method = selector.rsplit('.', 2)
    path = Path(identity['source_path']).resolve()
    data = path.read_bytes()
    require(digest(data) == identity['source_sha256'], 'Changed selector source')
    discovered = identities_from_sources({identity['source_path']: data}, (identity['source_path'],))
    require(discovered.get(selector) == identity, 'Selector absent from supported AST')
    alias = alias_for(module_name, identity['source_sha256'])
    if alias not in sys.modules:
        spec = importlib.util.spec_from_file_location(alias, path)
        require(spec is not None and spec.loader is not None, 'Invalid explicit module')
        module = importlib.util.module_from_spec(spec)
        sys.modules[alias] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(alias, None)
            raise
    module = sys.modules[alias]
    require(Path(module.__file__).resolve() == path and digest(path.read_bytes()) == digest(data),
            'Imported module/source identity')
    expected_classes = {v['class_name'] for v in discovered.values()}
    actual_classes = {n for n, c in vars(module).items() if isinstance(c, type)
                      and issubclass(c, unittest.TestCase) and c is not unittest.TestCase}
    require(actual_classes == expected_classes and not hasattr(module, 'load_tests'),
            'Dynamic/imported/inherited TestCase discovery is unsupported')
    cls = vars(module).get(class_name)
    require(type(cls) is type and cls.__bases__ == (unittest.TestCase,)
            and cls.__module__ == alias, 'Wrong test class')
    actual_methods = {n for n in cls.__dict__ if n.startswith('test_')}
    require(actual_methods == {v['method'] for v in discovered.values()
                               if v['class_name'] == class_name}, 'Dynamic test methods')
    function = cls.__dict__.get(method)
    require(type(function) is types.FunctionType and not inspect.iscoroutinefunction(function)
            and function.__module__ == alias and function.__qualname__ == class_name + '.' + method
            and function.__name__ == method and function.__code__.co_name == method
            and Path(function.__code__.co_filename).resolve() == path, 'Wrong test method/factory')
    compiled = compile(data, str(path), 'exec', dont_inherit=True, optimize=0)
    class_code = [c for c in compiled.co_consts if isinstance(c, types.CodeType) and c.co_name == class_name]
    method_code = [c for c in class_code[0].co_consts
                   if isinstance(c, types.CodeType) and c.co_name == method] if len(class_code) == 1 else []
    require(len(method_code) == 1 and function.__code__ == method_code[0],
            'Dynamically replaced unittest code is unsupported')
    for name in DISPATCH_NAMES:
        require(name not in cls.__dict__, 'Dynamic TestCase dispatch/identity')
    case = cls(methodName=method)
    require(type(case) is cls and case._testMethodName == method
            and case.id() == identity['runtime_id'] and case.countTestCases() == 1, 'Wrong leaf ID')
    actual = dict(selector=selector, source_path=path.relative_to(Path.cwd()).as_posix(),
        source_sha256=digest(data), class_name=type(case).__name__, method=case._testMethodName,
        runtime_id=case.id())
    require(actual == identity, 'Actual leaf/source identity')
    return unittest.TestSuite([case]), actual


def child(mode, selector, result_path):
    require(__debug__, 'Optimized metadata child rejected')
    sys.path.insert(0, str(Path.cwd()))
    sys.path.insert(0, str(Path.cwd() / 'scripts'))
    snapshot = parse(Path('../snapshot.json').read_bytes())
    validate_snapshot(snapshot)
    interpreter = dict(executable=sys.executable, python=sys.version, optimized=sys.flags.optimize,
                       implementation=platform.python_implementation())
    if mode == 'preflight':
        parsed = []
        for name, expected in snapshot['source_sha256'].items():
            if name.endswith('.py'):
                data = Path(name).read_bytes()
                require(digest(data) == expected, 'Changed AST source')
                compile(ast.parse(data, filename=name), name, 'exec')
                parsed.append(name)
        sources = {n: Path(n).read_bytes() for n in TEST_FILES}
        require(identities_from_sources(sources) == snapshot['test_identities'], 'AST selector catalog')
        resolved = []
        for name in snapshot['tests']:
            _, identity = load_one(name, snapshot['test_identities'][name])
            resolved.append(identity)
        value = dict(schema=CHILD_SCHEMA, kind=mode, status='completed', passed=True,
            interpreter=interpreter,
            parsed_files=sorted(parsed), test_selectors=snapshot['tests'],
            resolved_tests=len(resolved), executed_identities=resolved,
            physical_evolutions_run=False, component_accepted=False)
        dump(result_path, value)
        return 0
    require(mode == 'unittest' and selector in snapshot['tests'], 'Invalid child selector/mode')
    suite, identity = load_one(selector, snapshot['test_identities'][selector])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    passed = (result.wasSuccessful() and result.testsRun == 1 and not result.skipped
              and not result.expectedFailures and not result.unexpectedSuccesses)
    dump(result_path, dict(schema=CHILD_SCHEMA, kind=mode, selector=selector,
        interpreter=interpreter,
        executed_identity=identity, status='completed' if passed else 'failed', passed=passed,
        tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        skipped=len(result.skipped), expected_failures=len(result.expectedFailures),
        unexpected_successes=len(result.unexpectedSuccesses),
        physical_evolutions_run=False, component_accepted=False))
    return 0 if passed else 1


def validate_child(value, case, snapshot, runtime):
    require(type(value) is dict and value.get('schema') == CHILD_SCHEMA
            and value.get('kind') == case['kind'] and type(value.get('passed')) is bool,
            'Child schema/kind/bool')
    scope(value)
    interpreter = value.get('interpreter')
    exact_keys(interpreter, ('executable', 'python', 'optimized', 'implementation'), 'Child interpreter')
    require(type(interpreter['optimized']) is int and interpreter['optimized'] == 0
            and interpreter == {k: runtime[k] for k in interpreter}, 'Child/runtime interpreter link')
    require(value['status'] in ('completed', 'failed')
            and (value['status'] == 'completed') == value['passed'], 'Child status')
    if case['kind'] == 'preflight':
        exact_keys(value, ('schema', 'kind', 'status', 'passed', 'interpreter', 'parsed_files', 'test_selectors',
            'resolved_tests', 'executed_identities', 'physical_evolutions_run',
            'component_accepted'), 'Preflight child')
        require(value['passed'] is True and type(value['resolved_tests']) is int
                and value['resolved_tests'] == len(snapshot['tests'])
                and value['test_selectors'] == snapshot['tests']
                and value['parsed_files'] == sorted(n for n in snapshot['source_sha256']
                                                   if n.endswith('.py'))
                and value['executed_identities'] == [snapshot['test_identities'][s]
                                                     for s in snapshot['tests']],
                'Preflight AST/selector/actual-identity coverage')
    else:
        exact_keys(value, ('schema', 'kind', 'selector', 'executed_identity', 'status', 'passed', 'interpreter',
            'tests_run', 'failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes',
            'physical_evolutions_run', 'component_accepted'), 'Unittest child')
        require(value['selector'] == case['selector'] and value['executed_identity'] ==
                snapshot['test_identities'][case['selector']], 'Executed selector identity')
        for key in ('tests_run', 'failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes'):
            require(type(value[key]) is int and value[key] >= 0, 'Child count type')
        require(not value['passed'] or (value['tests_run'] == 1 and all(value[k] == 0 for k in
            ('failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes'))),
            'Contradictory child success')


def expected_command(runtime, case):
    argv = [runtime['executable'], runtime['job_path'], '--child', case['kind'],
            '--result', runtime['child_raw_path']]
    if case['kind'] == 'unittest':
        argv += ['--selector', case['selector']]
    return argv


def live_group_or_writers(held_identity, log_ids):
    """Find live group members and detached processes holding writable log FDs.

    held_identity is a currently verified, unreaped private leader, or None.
    No numeric group matching is allowed after that authority is lost.
    Supported children retain the job UID. Same-UID /proc permission failures
    are verification failures. starttime is checked again before signalling a
    detached writer, so a recycled PID is never knowingly signalled.
    """
    live, errors = {}, []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
            if fields[0] == 'Z':
                continue
            member = (held_identity is not None
                      and int(fields[2]) == held_identity['process_group']
                      and int(fields[3]) == held_identity['session'])
            if not member and entry.stat().st_uid == os.getuid():
                for fd in (entry / 'fd').iterdir():
                    try:
                        info = fd.stat()
                        if (info.st_dev, info.st_ino) in log_ids:
                            text = (entry / 'fdinfo' / fd.name).read_text()
                            flags = next(line.split()[1] for line in text.splitlines() if line.startswith('flags:'))
                            if (int(flags, 8) & os.O_ACCMODE) in (os.O_WRONLY, os.O_RDWR):
                                member = True
                                break
                    except FileNotFoundError:
                        continue
            if member:
                live[int(entry.name)] = fields[19]
        except (FileNotFoundError, ProcessLookupError):
            continue
        except (OSError, ValueError, IndexError, StopIteration):
            # Containers must expose their own UID's process/FD metadata.
            try:
                if entry.stat().st_uid == os.getuid():
                    errors.append(int(entry.name))
            except FileNotFoundError:
                pass
            except OSError:
                errors.append(int(entry.name))
    return live, errors


def signal_writer(pid, started, sig):
    try:
        fields = (Path('/proc') / str(pid) / 'stat').read_text().rsplit(')', 1)[1].split()
        if fields[19] == started:
            os.kill(pid, sig)
    except (OSError, ValueError, IndexError):
        pass


def leader_authority(process, identity):
    """Prove our original child remains waitable and holds its private PID/SID.

    Supported callers have no competing reaper/SIGCHLD auto-reaping handler.
    WNOWAIT retains even an exited leader as a zombie until all group signals
    and scans finish, preventing its PID/PGID/SID from being recycled. A lost
    lease is failure; a current numeric PGID alone never reacquires authority.
    """
    if identity is None or process.returncode is not None:
        return False
    try:
        os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        fields = (Path('/proc') / str(process.pid) / 'stat').read_text().rsplit(')', 1)[1].split()
        return identity == dict(pid=process.pid, process_group=int(fields[2]),
                                session=int(fields[3]), starttime=fields[19])
    except (OSError, ValueError, IndexError):
        return False


def capture_leader_identity(process):
    fields = (Path('/proc') / str(process.pid) / 'stat').read_text().rsplit(')', 1)[1].split()
    identity = dict(pid=process.pid, process_group=int(fields[2]),
                    session=int(fields[3]), starttime=fields[19])
    require(identity['process_group'] == process.pid == identity['session']
            and leader_authority(process, identity), 'Missing held private leader authority')
    return identity


def signal_owned_group(process, identity, sig):
    if not leader_authority(process, identity):
        return False
    try:
        os.killpg(identity['process_group'], sig)
    except ProcessLookupError:
        pass  # Held leader still prevents recycling even when no live members remain.
    return True


def wait_primary_held(process, identity, timeout):
    deadline = time.monotonic() + timeout
    while True:
        require(leader_authority(process, identity), 'Held leader authority lost')
        status = os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        if status is not None:
            return status
        if time.monotonic() >= deadline:
            return None
        time.sleep(min(0.02, max(0, deadline - time.monotonic())))


def supervise(argv, cwd, environment, stdout, stderr, timeout):
    """Linux process-group/session supervision; timeout covers child wait only.

    WNOWAIT holds the original private leader through every group signal and
    /proc group/writable-log-FD check; only then is the direct child reaped.
    Zombies cannot write. Detached same-UID log writers are included.
    Arbitrary escaped nonwriters/UID changes are unsupported, not certified
    descendant containment. Validation/extraction are outside the timeout.
    """
    require(sys.platform.startswith('linux'), 'Linux process supervision required')
    require(all(hasattr(os, n) for n in ('waitid', 'WNOWAIT', 'WEXITED', 'WNOHANG', 'P_PID')),
            'Linux WNOWAIT process ownership required')
    started, clock = datetime.now(timezone.utc).isoformat(), time.monotonic()
    value = dict(schema='openmhd.galaxy-python-command.v1', command=list(argv), cwd=str(cwd),
        started_utc=started, finished_utc=started, duration_seconds=0.0,
        outcome='start_failed', returncode=None, error_type=None, pid=None, process_group=None,
        timeout_seconds=timeout, timeout_scope='direct-child-wait',
        cleanup=dict(term_sent=False, kill_sent=False, direct_child_reaped=False,
                     writers_settled=False, remaining_live_pids=[], leader_identity=None,
                     leader_held_until_group_close=False, group_authority_lost=False))
    process, identity = None, None
    log_ids = {(os.fstat(stream.fileno()).st_dev, os.fstat(stream.fileno()).st_ino)
               for stream in (stdout, stderr)}
    try:
        process = subprocess.Popen(argv, cwd=cwd, env=environment, stdout=stdout,
                                   stderr=stderr, start_new_session=True)
        value['pid'] = value['process_group'] = process.pid
        identity = capture_leader_identity(process)
        value['cleanup']['leader_identity'] = identity
        try:
            status = wait_primary_held(process, identity, timeout)
            value['outcome'] = ('timeout' if status is None else
                'success' if status.si_code == os.CLD_EXITED and status.si_status == 0 else 'nonzero')
        except KeyboardInterrupt:
            value['outcome'] = 'interrupted'
    except (OSError, ValueError, IndexError) as error:
        value['error_type'] = type(error).__name__
    finally:
        if process is not None:
            for sig, label in ((signal.SIGTERM, 'term_sent'), (signal.SIGKILL, 'kill_sent')):
                if signal_owned_group(process, identity, sig):
                    value['cleanup'][label] = True
                else:
                    value['cleanup']['group_authority_lost'] = True
                held = identity if leader_authority(process, identity) else None
                if held is None:
                    value['cleanup']['group_authority_lost'] = True
                writers, _ = live_group_or_writers(held, log_ids)
                for pid, observed_start in writers.items():
                    signal_writer(pid, observed_start, sig)
                    value['cleanup'][label] = True
                if sig == signal.SIGTERM:
                    grace = time.monotonic() + 0.5
                    while writers and time.monotonic() < grace:
                        time.sleep(0.02)
                        held = identity if leader_authority(process, identity) else None
                        if held is None:
                            value['cleanup']['group_authority_lost'] = True
                        writers, _ = live_group_or_writers(held, log_ids)
            deadline = time.monotonic() + 2
            while True:
                held = identity if leader_authority(process, identity) else None
                if held is None:
                    value['cleanup']['group_authority_lost'] = True
                live, errors = live_group_or_writers(held, log_ids)
                if not live or time.monotonic() >= deadline:
                    break
                time.sleep(0.02)
            value['cleanup']['remaining_live_pids'] = sorted(live)
            closed = not live and not errors and not value['cleanup']['group_authority_lost']
            value['cleanup']['leader_held_until_group_close'] = closed
            # No group signal or numeric group scan is permitted after this reap.
            if leader_authority(process, identity):
                try:
                    value['returncode'] = process.wait(timeout=2)
                    value['cleanup']['direct_child_reaped'] = True
                except subprocess.TimeoutExpired:
                    value['error_type'] = 'PrimaryReapTimeout'
            else:
                value['cleanup']['group_authority_lost'] = True
                value['cleanup']['direct_child_reaped'] = process.returncode is not None
                value['error_type'] = 'LeaderAuthorityLost'
            value['cleanup']['writers_settled'] = (closed and value['cleanup']['direct_child_reaped']
                                                    and not value['cleanup']['group_authority_lost'])
            if errors:
                value['error_type'] = 'ProcessInspectionFailed'
            if not value['cleanup']['writers_settled']:
                value['outcome'] = 'cleanup_failed'
        else:
            value['cleanup']['writers_settled'] = True
        value['finished_utc'] = datetime.now(timezone.utc).isoformat()
        value['duration_seconds'] = time.monotonic() - clock
    return value


def validate_case(case, snapshot):
    require(type(case) is dict and case.get('kind') in ('preflight', 'unittest'), 'Case kind')
    keys = {'kind', 'resources', 'workflow'}
    if case['kind'] == 'unittest':
        keys |= {'selector', 'preflight_certificate_sha256'}
        require(case.get('selector') in snapshot['tests']
                and is_hash(case.get('preflight_certificate_sha256')), 'Case selector/certificate')
    exact_keys(case, keys, 'Case')
    require(type(case['resources']) is dict and case['resources'] == RESOURCES
            and type(case['resources']['threads']) is int
            and type(case['resources']['timeout_seconds']) is int, 'Case resources')
    require(type(case['workflow']) is str and re.fullmatch('[a-z][a-z0-9-]*\.1', case['workflow']),
            'Workflow version identity')


def extract_source(data, snapshot, source):
    source.mkdir()
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        members = archive.getmembers()
        catalog = snapshot['source_sha256']
        require(len(members) == len(catalog) and {m.name for m in members} == set(catalog),
                'Source archive count/path set')
        for member in members:
            path = PurePosixPath(member.name)
            require(member.isfile() and not path.is_absolute() and '..' not in path.parts
                    and path.as_posix() == member.name and path.parts,
                    'Source archive must contain regular relative files')
            stream = archive.extractfile(member)
            require(stream is not None, 'Unreadable source member')
            raw = stream.read()
            require(digest(raw) == catalog[member.name], 'Source member hash: ' + member.name)
            target = source.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
    require(identities_from_sources({n: (source / n).read_bytes() for n in TEST_FILES}) ==
            snapshot['test_identities'], 'Extracted selector catalog')


def runtime_record(work, job_path):
    """Actual direct Unix observations; no processor/libc/hostname probe.

    The tagged platform string is not platform.platform()'s historical pretty
    format or image/resource attestation. Keep the implementation display label
    identical to the child's separately captured interpreter label.
    """
    kernel = os.uname()
    platform_value = 'posix-uname-v1:' + json.dumps(dict(sys_platform=sys.platform,
        system=kernel.sysname, release=kernel.release, version=kernel.version,
        machine=kernel.machine), sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    value = dict(schema=RUNTIME_SCHEMA, python=sys.version, executable=sys.executable,
        implementation=platform.python_implementation(), platform=platform_value,
        optimized=sys.flags.optimize, image=None, visible_cpus=os.cpu_count(),
        declared_resources=None, image_and_resources_are_declared_labels=True,
        job_path=str(job_path), child_raw_path=str(work / 'outputs/child_raw.bin'))
    require(all(type(value[k]) is str and value[k] for k in
                ('python', 'executable', 'implementation', 'platform')),
            'Unavailable required runtime text')
    require(type(value['visible_cpus']) is int and value['visible_cpus'] > 0,
            'Unavailable logical CPU count')
    for name in ('cpu.max', 'memory.max'):
        try:
            value[name] = (Path('/sys/fs/cgroup') / name).read_text().strip()
        except OSError:
            value[name] = None
    return value


def child_raw_bytes(path):
    try:
        return path.read_bytes()
    except FileNotFoundError:
        # Explicit absent artifact, not a fabricated successful child result.
        path.write_bytes(b'')
        return b''


def run(work=None, job_path=None, argument_error=None):
    """Always finalize a closed packet for handled failures in a writable cwd.

    Pod loss, SIGKILL, disk loss/full and permission failures may prevent this;
    retain external workflow/status/job logs in those infrastructure cases.
    """
    work = Path(work or Path.cwd()).resolve()
    job_path = Path(job_path or __file__).resolve()
    output = work / 'outputs'
    output.mkdir()  # Existing output is never silently replaced.
    for name in OUTPUT_NAMES:
        (output / name).write_bytes(b'')
    started, clock = datetime.now(timezone.utc).isoformat(), time.monotonic()
    # Failure-only initial state: null fields are unavailable observations,
    # not an observed OS/implementation or a complete-success runtime record.
    # No fallible platform/CPU/cgroup capture runs before the handled boundary.
    runtime = dict(schema=RUNTIME_SCHEMA, python=sys.version, executable=sys.executable,
        implementation=None, platform=None, optimized=sys.flags.optimize,
        image=None, visible_cpus=None, declared_resources=None,
        image_and_resources_are_declared_labels=True, job_path=str(job_path),
        child_raw_path=str(work / 'outputs/child_raw.bin'),
        **{'cpu.max': None, 'memory.max': None})
    command = dict(schema='openmhd.galaxy-python-command.v1', outcome='not_started', command=[],
        cwd=str(work / 'source'), started_utc=started, finished_utc=started,
        duration_seconds=0.0, returncode=None, error_type=None, pid=None, process_group=None,
        timeout_seconds=RESOURCES['timeout_seconds'], timeout_scope='direct-child-wait',
        cleanup=dict(term_sent=False, kill_sent=False, direct_child_reaped=False,
                     writers_settled=True, remaining_live_pids=[], leader_identity=None,
                     leader_held_until_group_close=False, group_authority_lost=False))
    record = dict(schema=RESULT_SCHEMA, status='failed', passed=False, started_utc=started,
        finished_utc=started, duration_seconds=0.0, case=None, outcome='validation_failed',
        returncode=None, problem=None, command=[], child_result=None, source_revision=None,
        snapshot_sha256=None, payload_sha256=None, source_sha256=None, runtime_sha256=None,
        command_sha256=None, physical_evolutions_run=False, component_accepted=False)
    child_record = dict(schema='openmhd.galaxy-python-child-envelope.v1', state='absent',
                        raw_sha256=digest(b''), raw_bytes=0, problem=None, value=None)
    stage, snapshot = 'validation_failed', None
    dump(output / 'runtime.json', runtime)
    dump(output / 'command.json', command)  # Durable intent before input checks/launch.
    dump(output / 'child_result.json', child_record)
    dump(output / 'result.json', record)
    try:
        stage = 'optimized_rejected'
        require(__debug__ and sys.flags.optimize == 0, 'Optimized metadata evidence rejected')
        stage = 'runtime_observation_failed'
        runtime = runtime_record(work, job_path)
        stage = 'validation_failed'
        require(argument_error is None, argument_error or 'Invalid arguments')
        fixed = capture_files(work, ('payload.json', 'snapshot.json', 'case.json', 'source.tar.gz', 'job.py'))
        payload = parse(fixed['payload.json'])
        exact_keys(payload, ('schema', 'input_sha256'), 'Payload')
        require(payload['schema'] == 'openmhd.galaxy-python-case-payload.v2', 'Payload schema')
        snapshot_bytes = fixed['snapshot.json']
        snapshot, case = parse(snapshot_bytes), parse(fixed['case.json'])
        validate_snapshot(snapshot)
        validate_case(case, snapshot)
        names = {'source.tar.gz', 'snapshot.json', 'job.py', 'case.json'}
        if case['kind'] == 'unittest':
            names.add('preflight_certificate.json')
        require(type(payload['input_sha256']) is dict and set(payload['input_sha256']) == names,
                'Exact uploaded input set')
        if 'preflight_certificate.json' in names:
            fixed.update(capture_files(work, ('preflight_certificate.json',)))
        require(all(is_hash(h) and digest(fixed[n]) == h for n, h in payload['input_sha256'].items()),
                'Changed uploaded input')
        require(digest(fixed['source.tar.gz']) == snapshot['archive_sha256']
                and digest(fixed['job.py']) == snapshot['job_sha256']
                and job_path.read_bytes() == fixed['job.py'], 'Changed archive/job source')
        record.update(case=case, source_revision=snapshot['source_revision'],
            snapshot_sha256=digest(snapshot_bytes), payload_sha256=digest(fixed['payload.json']),
            source_sha256=snapshot['source_sha256'])
        runtime.update(image=snapshot['image'], declared_resources=case['resources'])
        if case['kind'] == 'unittest':
            certificate = fixed['preflight_certificate.json']
            require(digest(certificate) == case['preflight_certificate_sha256'], 'Certificate input link')
            validate_certificate(certificate, snapshot_bytes)
        stage = 'extraction_failed'
        extract_source(fixed['source.tar.gz'], snapshot, work / 'source')
        stage = 'launch_failed'
        argv = expected_command(runtime, case)
        command['command'] = argv
        command['outcome'] = 'pending_launch'
        command['cleanup']['writers_settled'] = False
        dump(output / 'command.json', command)
        environment = dict(os.environ)
        environment.update(PYTHONDONTWRITEBYTECODE='1', PYTHONHASHSEED='0',
            OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', RAYON_NUM_THREADS='1')
        environment.pop('PYTHONOPTIMIZE', None)
        with (output / 'stdout.txt').open('wb') as stdout, (output / 'stderr.txt').open('wb') as stderr:
            command = supervise(argv, work / 'source', environment, stdout, stderr,
                                case['resources']['timeout_seconds'])
        record.update(outcome=command['outcome'], returncode=command['returncode'], command=argv)
        stage = 'invalid_child'
        raw = child_raw_bytes(output / 'child_raw.bin')
        child_record.update(raw_sha256=digest(raw), raw_bytes=len(raw))
        if not raw:
            record['outcome'] = command['outcome'] if command['outcome'] != 'success' else 'missing_child'
        else:
            try:
                value = parse(raw)
                validate_child(value, case, snapshot, runtime)
                child_record.update(state='valid', value=value)
                record['child_result'] = value
                record['passed'] = command['outcome'] == 'success' and value['passed'] is True
                if command['outcome'] == 'success' and not record['passed']:
                    record['outcome'] = 'child_failed'
            except (ValueError, TypeError, KeyError, AttributeError) as error:
                child_record.update(state='invalid', problem=type(error).__name__)
                record['outcome'] = 'invalid_child' if command['outcome'] == 'success' else command['outcome']
    except (Exception, KeyboardInterrupt) as error:
        record.update(outcome='interrupted' if isinstance(error, KeyboardInterrupt) else stage,
                      problem=type(error).__name__)
        if command['outcome'] == 'pending_launch':
            command.update(outcome='supervision_failed', error_type=type(error).__name__,
                           finished_utc=datetime.now(timezone.utc).isoformat(),
                           duration_seconds=time.monotonic() - clock)
        record['command'] = command['command']
    finally:
        # No child writer remains on a successful supervised path. Cleanup failure
        # is retained as failure, never presented as immutable successful logs.
        raw = child_raw_bytes(output / 'child_raw.bin')
        child_record.update(raw_sha256=digest(raw), raw_bytes=len(raw))
        if raw and child_record['state'] == 'absent':
            child_record.update(state='invalid', problem='UnvalidatedChildBytes')
        dump(output / 'child_result.json', child_record)
        dump(output / 'runtime.json', runtime)
        dump(output / 'command.json', command)
        record.update(status='completed' if record['passed'] else 'failed',
            finished_utc=datetime.now(timezone.utc).isoformat(), duration_seconds=time.monotonic() - clock,
            runtime_sha256=digest((output / 'runtime.json').read_bytes()),
            command_sha256=digest((output / 'command.json').read_bytes()))
        dump(output / 'result.json', record)
        manifest = {'outputs/' + n: digest((output / n).read_bytes())
                    for n in OUTPUT_NAMES if n != 'artifacts.sha256.json'}
        dump(output / 'artifacts.sha256.json', manifest)
    return 0 if record['passed'] else 1


def server_status(value, workflow):
    exact_keys(value, ('schema', 'origin', 'observed_utc', 'matches'), 'Server observation')
    require(value['schema'] == SERVER_SCHEMA and value['origin'] == 'server', 'Actual server observation')
    utc(value['observed_utc'])
    require(type(value['matches']) is list and len(value['matches']) == 1, 'Unique workflow observation')
    match = value['matches'][0]
    exact_keys(match, ('workflow', 'name', 'version', 'status'), 'Workflow observation')
    require(match['workflow'] == workflow and match['name'] + '.' + str(match['version']) == workflow
            and type(match['version']) is int and match['version'] == 1
            and type(match['status']) is str and re.fullmatch('[a-z][a-z0-9_-]{0,63}', match['status']),
            'Successful terminal workflow/version required')
    return match['status']


def validate_server(value, workflow):
    require(server_status(value, workflow) == 'finished', 'Successful terminal workflow/version required')


def validate_case_outputs(buffers, snapshot_bytes, entry, *, failed_unittest=False):
    """Validate the exact expected preflight/unittest, never its label alone.

    The forensic option establishes a coherent failed unittest child, not a
    pass or preflight. Other job/infrastructure failures retain their bytes but
    cannot satisfy this validator. Every parse/hash uses the supplied buffers.
    """
    snapshot = parse(snapshot_bytes)
    validate_snapshot(snapshot)
    require(set(buffers) == set(OUTPUT_NAMES), 'Preflight exact artifact set')
    manifest = parse(buffers['artifacts.sha256.json'])
    require(type(manifest) is dict and set(manifest) == set(OUTPUTS) - {'outputs/artifacts.sha256.json'}
            and all(is_hash(h) and digest(buffers[PurePosixPath(n).name]) == h
                    for n, h in manifest.items()), 'Preflight artifact manifest')
    result, runtime, command = (parse(buffers[n]) for n in ('result.json', 'runtime.json', 'command.json'))
    exact_keys(result, ('schema', 'status', 'passed', 'started_utc', 'finished_utc', 'duration_seconds',
        'case', 'outcome', 'returncode', 'problem', 'command', 'child_result', 'source_revision',
        'snapshot_sha256', 'payload_sha256', 'source_sha256', 'runtime_sha256', 'command_sha256',
        'physical_evolutions_run', 'component_accepted'), 'Preflight result')
    exact_keys(runtime, ('schema', 'python', 'executable', 'implementation', 'platform', 'optimized',
        'image', 'visible_cpus', 'declared_resources', 'image_and_resources_are_declared_labels',
        'job_path', 'child_raw_path', 'cpu.max', 'memory.max'), 'Runtime')
    exact_keys(command, ('schema', 'command', 'cwd', 'started_utc', 'finished_utc', 'duration_seconds',
        'outcome', 'returncode', 'error_type', 'pid', 'process_group', 'timeout_seconds',
        'timeout_scope', 'cleanup'), 'Command')
    exact_keys(command['cleanup'], ('term_sent', 'kill_sent', 'direct_child_reaped',
        'writers_settled', 'remaining_live_pids', 'leader_identity', 'leader_held_until_group_close',
        'group_authority_lost'), 'Cleanup')
    require(all(type(command['cleanup'][n]) is bool for n in
                ('term_sent', 'kill_sent', 'direct_child_reaped', 'writers_settled',
                 'leader_held_until_group_close', 'group_authority_lost'))
            and type(command['pid']) is int and command['pid'] > 0
            and type(command['process_group']) is int and command['process_group'] == command['pid']
            and command['error_type'] is None and result['problem'] is None
            and type(command['timeout_seconds']) is int
            and type(runtime['visible_cpus']) is int and runtime['visible_cpus'] > 0,
            'Command/runtime scalar types')
    leader = command['cleanup']['leader_identity']
    exact_keys(leader, ('pid', 'process_group', 'session', 'starttime'), 'Held leader identity')
    require(all(type(leader[n]) is int and leader[n] == command['pid']
                for n in ('pid', 'process_group', 'session'))
            and type(leader['starttime']) is str and re.fullmatch('[0-9]+', leader['starttime'])
            and command['cleanup']['leader_held_until_group_close'] is True
            and command['cleanup']['group_authority_lost'] is False, 'Held group authority/closure')
    require(result.get('schema') == RESULT_SCHEMA and type(result.get('passed')) is bool
            and result['passed'] is (not failed_unittest)
            and result.get('status') == ('failed' if failed_unittest else 'completed')
            and result.get('outcome') == ('nonzero' if failed_unittest else 'success')
            and type(result.get('returncode')) is int
            and result['returncode'] == (1 if failed_unittest else 0), 'Preflight result')
    scope(result)
    interval(result)
    case = entry['specification']
    validate_case(case, snapshot)
    validate_case(result['case'], snapshot)
    require(not failed_unittest or case['kind'] == 'unittest', 'Failure mode is unittest-only')
    require(result['case'] == case
            and result['snapshot_sha256'] == digest(snapshot_bytes)
            and result['source_sha256'] == snapshot['source_sha256']
            and result['source_revision'] == snapshot['source_revision']
            and result['payload_sha256'] == entry['payload_sha256'], 'Preflight source/case link')
    require(runtime.get('schema') == RUNTIME_SCHEMA and type(runtime.get('optimized')) is int
            and runtime['optimized'] == 0 and runtime.get('image') == IMAGE
            and runtime.get('declared_resources') == RESOURCES
            and type(runtime['declared_resources']['threads']) is int
            and type(runtime['declared_resources']['timeout_seconds']) is int
            and runtime.get('image_and_resources_are_declared_labels') is True
            and all(type(runtime.get(k)) is str and runtime[k]
                    for k in ('python', 'executable', 'implementation', 'platform', 'job_path', 'child_raw_path'))
            and digest(buffers['runtime.json']) == result['runtime_sha256'], 'Preflight runtime link')
    require(command.get('schema') == 'openmhd.galaxy-python-command.v1'
            and command.get('outcome') == ('nonzero' if failed_unittest else 'success')
            and type(command.get('returncode')) is int
            and command['returncode'] == (1 if failed_unittest else 0)
            and command.get('timeout_seconds') == RESOURCES['timeout_seconds']
            and command.get('timeout_scope') == 'direct-child-wait'
            and command.get('command') == expected_command(runtime, case) == result['command']
            and command.get('cleanup', {}).get('writers_settled') is True
            and command['cleanup'].get('direct_child_reaped') is True
            and command['cleanup'].get('remaining_live_pids') == []
            and digest(buffers['command.json']) == result['command_sha256'], 'Preflight command/cleanup link')
    work = Path(runtime['job_path']).parent
    require(Path(runtime['job_path']).is_absolute() and Path(runtime['job_path']).name == 'job.py'
            and Path(runtime['executable']).is_absolute()
            and runtime['child_raw_path'] == str(work / 'outputs/child_raw.bin')
            and command['cwd'] == str(work / 'source'), 'Preflight command paths')
    interval(command)
    envelope = parse(buffers['child_result.json'])
    exact_keys(envelope, ('schema', 'state', 'raw_sha256', 'raw_bytes', 'problem', 'value'), 'Child envelope')
    require(envelope['schema'] == 'openmhd.galaxy-python-child-envelope.v1' and envelope['state'] == 'valid'
            and type(envelope['raw_bytes']) is int and envelope['raw_bytes'] == len(buffers['child_raw.bin'])
            and envelope['raw_sha256'] == digest(buffers['child_raw.bin']) and envelope['problem'] is None,
            'Preflight raw child link')
    value = parse(buffers['child_raw.bin'])
    require(value == envelope['value'] == result['child_result'], 'Preflight parsed child link')
    validate_child(value, case, snapshot, runtime)
    validate_child(envelope['value'], case, snapshot, runtime)
    validate_child(result['child_result'], case, snapshot, runtime)
    require(value['passed'] is (not failed_unittest), 'Expected child pass/failure')
    if failed_unittest:
        require(value['tests_run'] != 1 or any(value[n] != 0 for n in
            ('failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes')),
            'Contradictory child failure')
    return result


def validate_preflight_outputs(buffers, snapshot_bytes, entry):
    """Unchanged strict API: a unittest/forensic packet cannot release cases."""
    require(entry['specification'].get('kind') == 'preflight', 'Expected preflight mode')
    return validate_case_outputs(buffers, snapshot_bytes, entry)


def credential_free_argv(argv):
    require(type(argv) is list and argv and all(type(a) is str and a for a in argv)
            and Path(argv[0]).is_absolute(), 'Absolute credential-free adapter argv required')
    require(not any(re.search(r'(?i)(token|password|secret|authorization|bearer|https?://|=)', a)
                    for a in argv), 'Keep credentials/configuration out of client argv')


def validate_certificate(certificate_bytes, snapshot_bytes):
    certificate = parse(certificate_bytes)
    exact_keys(certificate, ('schema', 'snapshot_sha256', 'capture_sha256', 'buffers',
        'physical_evolutions_run', 'component_accepted'), 'Certificate')
    require(certificate['schema'] == CERT_SCHEMA
            and certificate['snapshot_sha256'] == digest(snapshot_bytes), 'Certificate snapshot/schema')
    scope(certificate)
    encoded = certificate['buffers']
    require(type(encoded) is dict and type(certificate['capture_sha256']) is dict
            and set(encoded) == set(certificate['capture_sha256']), 'Certificate capture inventory')
    buffers = {n: base64.b64decode(b, validate=True) for n, b in encoded.items()}
    require(all(len(b) <= MAX_FILE_BYTES and digest(b) == certificate['capture_sha256'][n]
                for n, b in buffers.items()), 'Certificate captured bytes')
    plan, payload, case, spec, submission = (parse(buffers[n]) for n in
        ('plan.json', 'payload.json', 'case.json', 'reana.yaml', 'submission.json'))
    exact_keys(plan, ('schema', 'snapshot_sha256', 'cases', 'component_accepted'), 'Preflight plan')
    require(plan['schema'] == 'openmhd.galaxy-python-case-plan.v2' and plan['component_accepted'] is False
            and plan['snapshot_sha256'] == digest(snapshot_bytes)
            and type(plan['cases']) is list and len(plan['cases']) == 1, 'Preflight plan identity')
    entry = plan['cases'][0]
    exact_keys(entry, ('directory', 'specification', 'workflow', 'payload_sha256', 'workflow_sha256'), 'Plan entry')
    require(entry['directory'] == '0000' and entry['specification'] == case
            and entry['workflow'] == case['workflow']
            and entry['payload_sha256'] == digest(buffers['payload.json'])
            and entry['workflow_sha256'] == digest(buffers['reana.yaml']), 'Planned identities')
    snapshot = parse(snapshot_bytes)
    validate_snapshot(snapshot)
    exact_keys(payload, ('schema', 'input_sha256'), 'Preflight payload')
    require(payload['schema'] == 'openmhd.galaxy-python-case-payload.v2' and payload['input_sha256'] == {
        'source.tar.gz': snapshot['archive_sha256'], 'snapshot.json': digest(snapshot_bytes),
        'job.py': snapshot['job_sha256'], 'case.json': digest(buffers['case.json'])}, 'Uploaded preflight pins')
    require(spec == workflow_document(payload['input_sha256']), 'Exact workflow command/resources/outputs')
    require(type(submission) is dict and set(submission) == {entry['workflow']}
            and submission[entry['workflow']].get('status') in ('submitted', 'submission uncertain'),
            'Actual submission receipt')
    before, after = (parse(buffers[n]) for n in ('server-before.json', 'server-after.json'))
    validate_server(before, entry['workflow'])
    validate_server(after, entry['workflow'])
    require(utc(after['observed_utc']) >= utc(before['observed_utc']), 'Observation order')
    transport = parse(buffers['transport.json'])
    exact_keys(transport, ('schema', 'client_argv', 'workflow', 'attempts', 'origin'), 'Transport')
    require(transport['schema'] == 'openmhd.galaxy-python-transport.v1' and transport['origin'] == 'server'
            and transport['workflow'] == entry['workflow'], 'Actual transport workflow')
    credential_free_argv(transport['client_argv'])
    requests = [('observe', 'server-before.json')] + [('download', n) for n in OUTPUT_NAMES] + [
        ('observe', 'server-after.json')]
    require(type(transport['attempts']) is list and len(transport['attempts']) == len(requests),
            'Exact status/download attempts')
    required = {'plan.json', 'payload.json', 'case.json', 'reana.yaml', 'submission.json',
                'server-before.json', 'server-after.json', 'transport.json'}
    required |= {'artifacts/' + n for n in OUTPUT_NAMES}
    for index, (attempt, (kind, name)) in enumerate(zip(transport['attempts'], requests)):
        exact_keys(attempt, ('schema', 'index', 'action', 'workflow', 'requested_path', 'output',
            'command', 'started_utc', 'finished_utc', 'duration_seconds', 'outcome', 'returncode',
            'stdout', 'stderr', 'download_sha256'), 'Transport attempt')
        relative = name if kind == 'observe' else 'artifacts/' + name
        requested = None if kind == 'observe' else 'outputs/' + name
        tail = [kind, '--workflow', entry['workflow']]
        if requested:
            tail += ['--path', requested]
        tail += ['--output', relative]
        require(attempt['schema'] == 'openmhd.galaxy-python-transport-attempt.v1'
                and type(attempt['index']) is int and attempt['index'] == index
                and attempt['action'] == kind and attempt['workflow'] == entry['workflow']
                and attempt['requested_path'] == requested and attempt['output'] == relative
                and attempt['command'] == transport['client_argv'] + tail
                and attempt['outcome'] == 'success' and type(attempt['returncode']) is int
                and attempt['returncode'] == 0 and attempt['download_sha256'] == digest(buffers[relative]),
                'Transport command/download link')
        interval(attempt)
        for stream in ('stdout', 'stderr'):
            value = attempt[stream]
            exact_keys(value, ('path', 'sha256'), 'Transport log')
            path = f'transport/{index:02d}.{stream}.txt'
            require(value['path'] == path and digest(buffers[path]) == value['sha256'], 'Transport log link')
            required.add(path)
    require(set(buffers) == required, 'Closed certificate capture paths')
    validate_preflight_outputs({n: buffers['artifacts/' + n] for n in OUTPUT_NAMES}, snapshot_bytes, entry)
    return certificate


def main():
    if not __debug__ or sys.flags.optimize != 0:
        return run()  # Rejection retains the same handled-failure output envelope.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child', choices=('preflight', 'unittest'))
    parser.add_argument('--selector')
    parser.add_argument('--result', type=Path)
    try:
        args = parser.parse_args()
    except SystemExit as error:
        if error.code == 0:
            return 0
        return run(argument_error='Invalid command arguments')
    if args.child:
        if args.result is None:
            return run(argument_error='Missing child result path')
        return child(args.child, args.selector, args.result)
    if args.selector is not None or args.result is not None:
        return run(argument_error='Child-only arguments without child mode')
    return run()


if __name__ == '__main__':
    raise SystemExit(main())
