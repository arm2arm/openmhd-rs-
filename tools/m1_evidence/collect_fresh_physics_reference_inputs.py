"""Collect actual fresh REANA inputs; never submit, evolve or accept M1.

Shared helpers implement coherent metadata capture, verified byte copying and
durable credential-redacted command receipts. Numerical adapters are unchanged.
"""
if not __debug__:
    raise RuntimeError("M1 evidence tools require assertions: optimized Python is forbidden")

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shlex
import signal
import subprocess
import sys
import threading
import time
import uuid

SNAPSHOT = 'b67ce03779a194099983b7ff07c0cafed23e9ea3a9051047492d072255e0160f'
BINARY = '18afcf0308338e2ea0ea7ef5e03dba46af9d7025f3ccf4a6a48ebbfe800d0725'

# Load the complete captured helper inside a held-leader bootstrap. An import,
# source-open or compilation failure must not silently release an active group
# identity before its owner can cancel it. The isolated bootstrap uses only the
# working Python runtime/stdlib; actual command argv/environment stay unchanged.
GUARDIAN_BOOTSTRAP = '''import sys
source = sys.argv.pop(1)
sys.argv[0] = source
try:
    with open(source, 'rb') as stream:
        program = compile(stream.read(), source, 'exec')
    exec(program, {'__name__': '__main__', '__file__': source})
except SystemExit:
    raise
except BaseException as exc:
    try:
        print('Guardian bootstrap exception type: '+type(exc).__name__, file=sys.stderr, flush=True)
    except BaseException:
        pass
    import time
    while True:
        time.sleep(1)
'''


def require(condition, message):
    if not condition:
        raise ValueError(message)


def utc():
    return datetime.now(timezone.utc).isoformat()


def runtime_info():
    return dict(executable=sys.executable, version=sys.version,
                implementation=platform.python_implementation(),
                optimization=sys.flags.optimize, assertions_enabled=__debug__,
                pythonoptimize=os.environ.get('PYTHONOPTIMIZE'),
                platform=platform.platform())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=1, allow_nan=False) + '\n')
    temporary.replace(path)


def relative_path(name):
    p = PurePosixPath(name)
    require(bool(p.parts) and not p.is_absolute() and '..' not in p.parts
            and str(p) == name and '\\' not in name, 'Unsafe relative evidence path')
    return Path(*p.parts)


def generation(path):
    st = Path(path).stat()
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


class CaptureChanged(RuntimeError):
    pass


def read_once(path):
    """One byte read supplies parsing, hashing and copying; stat detects replacement."""
    before = generation(path)
    data = Path(path).read_bytes()
    after = generation(path)
    if before != after:
        raise CaptureChanged('Metadata changed while read: ' + str(path))
    return data, after


class MetadataCapture:
    def __init__(self, data, generations, attempts, base_paths, expand):
        self.data, self.generations, self.attempts = data, generations, attempts
        self.base_paths, self.expand = base_paths, expand

    @classmethod
    def take(cls, paths, expand=None, attempts=3, validate=None):
        """Bounded retry of the whole generation, including dynamically named files."""
        history = []
        paths = set(map(Path, paths))
        for attempt in range(1, attempts + 1):
            data, generations = {}, {}
            try:
                for path in sorted(paths):
                    data[path], generations[path] = read_once(path)
                if expand:
                    for path in sorted(set(map(Path, expand(data))) - set(data)):
                        data[path], generations[path] = read_once(path)
                if any(generation(p) != sig for p, sig in generations.items()):
                    raise CaptureChanged('Metadata generation changed across capture')
                if expand and paths | set(map(Path, expand(data))) != set(data):
                    raise CaptureChanged('Metadata file set changed across capture')
                if validate:
                    validate(data)
                history.append(dict(attempt=attempt, outcome='stable', finished_utc=utc()))
                return cls(data, generations, history, paths, expand)
            except (CaptureChanged, FileNotFoundError, json.JSONDecodeError) as exc:
                history.append(dict(attempt=attempt, outcome=type(exc).__name__, finished_utc=utc()))
        raise CaptureChanged('No stable metadata generation after bounded capture retries')

    def parsed(self, path):
        return json.loads(self.data[Path(path)])

    def unchanged(self):
        # No parsed objects are reconstructed from these later reads.
        if self.expand and self.base_paths | set(map(Path, self.expand(self.data))) != set(self.data):
            raise CaptureChanged('Original metadata file set changed')
        for path, data in self.data.items():
            current, sig = read_once(path)
            if sig != self.generations[path] or current != data:
                raise CaptureChanged('Original capture changed: ' + str(path))
        return dict(passed=True, checked_utc=utc(), files=len(self.data),
                    policy='Original generation and exact bytes unchanged; no hidden refresh')

    def export(self, out, destinations, source_name):
        records = {}
        for path, data in self.data.items():
            name = source_name(path)
            require(name not in records, 'Duplicate original capture source')
            copied = relative_path(destinations[path])
            target = Path(out) / copied
            require(not target.exists(), 'Capture destination already exists')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            records[name] = dict(copied_path=copied.as_posix(), sha256=digest(data), bytes=len(data))
        return dict(schema='m1-metadata-capture-v1', captured_utc=utc(),
                    runtime=runtime_info(), attempts=self.attempts, files=records,
                    final_unchanged_check=dict(passed=False))


def copy_verified(source, target, expected, check_cancelled=None):
    """Hash the bytes actually copied; atomic replacement never follows target links."""
    source, target = Path(source), Path(target)
    before = generation(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + '.materializing')
    require(not temporary.exists(), 'Existing partial materialization must be preserved')
    h = hashlib.sha256()
    size = 0
    with source.open('rb') as stream, temporary.open('xb') as destination:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            if check_cancelled:
                check_cancelled()
            h.update(block)
            size += len(block)
            destination.write(block)
    if check_cancelled:
        check_cancelled()
    require(before == generation(source), 'Raw source changed during materialization')
    require(h.hexdigest() == expected, 'Actual fresh bytes differ from captured artifact identity')
    temporary.replace(target)
    require(not target.is_symlink(), 'Materialized target must be a regular file')
    return dict(sha256=h.hexdigest(), bytes=size)


def verify_capture_copies(out, record):
    out = Path(out).resolve()
    for row in record['files'].values():
        target = out / relative_path(row['copied_path'])
        require(target.resolve(strict=True).is_relative_to(out) and not target.is_symlink(),
                'Capture copy escaped its closed destination')
        data = target.read_bytes()
        require(len(data) == row['bytes'] and digest(data) == row['sha256'],
                'Exported metadata changed after capture')


def secret_values():
    values = [v for k, v in os.environ.items()
              if re.search(r'TOKEN|SECRET|PASSWORD|CREDENTIAL|AUTHORIZATION|COOKIE', k, re.I)
              and len(v) >= 4]
    # The documented transport adapter uses this private file. Read secrets
    # only for redaction, never serialize the configuration or its contents.
    path = Path.home() / '.config/openmhd/reana-p4n.json'
    if path.exists():
        config = json.loads(path.read_bytes())
        values += [v for k, v in config.items()
                   if isinstance(v, str) and len(v) >= 4
                   and re.search(r'token|secret|password|credential', k, re.I)]
    return values


def redact(data, secrets):
    text = data.decode('utf-8', errors='replace') if isinstance(data, bytes) else str(data)
    for secret in sorted(secrets, key=len, reverse=True):
        text = text.replace(secret, '[REDACTED]')
    text = re.sub(r'(?i)(authorization\s*[:=]\s*(?:bearer\s+)?)[^\s,;"}]+',
                  r'\1[REDACTED]', text)
    text = re.sub(r'(?i)((?:access[_-]?token|password|client[_-]?secret|api[_-]?key)'
                  r'["\']?\s*[:=]\s*["\']?)[^\s,;"}\']+', r'\1[REDACTED]', text)
    text = re.sub(r'(https?://)[^/\s:@]+:[^/\s@]+@', r'\1[REDACTED]@', text)
    return text


def credential_free_argv(argv, secrets):
    require(all(isinstance(a, str) for a in argv), 'Command argv must contain strings')
    require(not any(secret in a for secret in secrets for a in argv),
            'Credentials in command argv are forbidden; use the configured adapter')
    for a in argv:
        require(not re.search(r'(?i)(?:--(?:access-)?token|--password|--secret|'
                              r'(?:token|password|secret|api_key)=|https?://[^/\s]*@|'
                              r'https?://[^\s]*\?)', a),
                'Credential-bearing command arguments are forbidden')


class CommandFailed(RuntimeError):
    pass


def timeout_output_snapshot(exc, stdout, stderr):
    # communicate's timeout payload is cumulative, not a new chunk. None means
    # no newer observation for that channel; b'' is an available empty snapshot.
    return (stdout if exc.output is None else exc.output,
            stderr if exc.stderr is None else exc.stderr)


class CleanupIncomplete(RuntimeError):
    pass


@contextmanager
def ownership_lock(root):
    # POSIX flock is shared by the outer journal and separately grouped nested
    # collectors. No user/agent parent process group is ever registered.
    import fcntl
    with (root/'registry.lock').open('a+b') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def ownership_nodes(root):
    return {path.stem:read(path) for path in root.glob('*.json')}


@contextmanager
def defer_launch_signals():
    # Close the interrupt window between OS spawn and durable PID publication.
    # The guardian unblocks these inherited signals after installing handlers.
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


def cancellation_fenced(root, node_id):
    # Even an interrupted/failed atomic fence publication leaves a conservative
    # launch tombstone if its .tmp entry exists. A partial tombstone blocks
    # launches but never authorizes a signal. Wholly unavailable storage may
    # prevent both entries: no fencing or local finalization is claimed then.
    marker = root/(node_id+'.cancel')
    return any(path.exists() or path.is_symlink()
               for path in (marker, marker.with_name(marker.name+'.tmp')))


def publish_cancellation_fence(root, node_id):
    marker = root/(node_id+'.cancel')
    record = dict(schema='m1-command-cancellation-v1', node_id=node_id)
    if marker.exists() or marker.is_symlink():
        require(marker.is_file() and not marker.is_symlink() and read(marker) == record,
                'Invalid command cancellation fence')
    else:
        write_json(marker, record)


def cancelled_ancestor(nodes, node_id, root):
    seen = set()
    while node_id is not None:
        require(node_id in nodes and node_id not in seen, 'Invalid command ownership ancestry')
        seen.add(node_id)
        node = nodes[node_id]
        if node['cancelled'] or cancellation_fenced(root, node_id):
            return True
        node_id = node['parent_id']
    return False


def live_group_members():
    """Linux/macOS POSIX ps; zombies have no open writers and are not live.

    This is deliberately bounded and fail-closed if process observation fails.
    The guardian stays the private group leader until all members have stopped.
    """
    probe = subprocess.Popen(['/bin/ps', '-axo', 'pid=,pgid=,stat='],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        data, _ = probe.communicate(timeout=2)
    except BaseException:
        probe.kill()
        probe.communicate(timeout=2)
        raise
    require(probe.returncode == 0, 'Cannot establish process ownership closure')
    groups = {}
    for line in data.decode('ascii').splitlines():
        pid, pgid, state = line.split()
        if not state.startswith('Z') and int(pid) != probe.pid:
            groups.setdefault(int(pgid), set()).add(int(pid))
    return groups


class OwnedCommand:
    """Cooperative POSIX command tree with a held private-session leader.

    Every nested CommandJournal joins the inherited registry. Registration,
    launch and cancellation share a lock, so cancellation fences new children.
    Canonical/partial cancellation tombstones fence ancestry launches even when
    a node publication fails. Only a canonical fence plus a persisted one-shot
    intent authorizes dispatch; an unresolved intent never authorizes a numeric
    group retry and remains unfinished pending external evidence. This is process
    publication ordering, not power-loss durability or recovery of old registries
    created by a different protocol/source version.
    The guardian reaps its actual command and remains alive when that command
    exits leaving pipe-holding descendants. The owner reaps the guardian.
    Requires Linux/macOS POSIX sessions, pthread signal masks, a visible /bin/ps
    in the same PID namespace, working flock and cooperative same-UID children
    preserving the ownership environment and groups. Buffered local copy threads
    check cancellation between blocks; blocked storage still needs OS recovery.
    Requires a working trusted Python runtime; interpreter death, SIGKILL/container
    loss, inaccessible storage/process tables, and deliberate
    unregistered setsid/daemon escapes cannot be finalized by this protocol:
    retain the running attempt and obtain external status/log evidence instead.
    No portable claim of reaping non-child orphans (the OS reaps those) is made.
    """
    def __init__(self, out, argv, cwd):
        require(os.name == 'posix', 'Command ownership requires POSIX sessions/flock/ps')
        inherited = os.environ.get('M1_COMMAND_REGISTRY')
        self.root = Path(inherited) if inherited else Path(out)/'command_ownership'
        self.root = self.root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.node_id = uuid.uuid4().hex
        self.parent_id = os.environ.get('M1_COMMAND_NODE') if inherited else None
        require(not inherited or self.parent_id is not None, 'Incomplete ownership environment')
        self.path = self.root/(self.node_id+'.json')
        self.argv, self.cwd = argv, str(cwd)
        self.process = None

    def start(self):
        with ownership_lock(self.root):
            nodes = ownership_nodes(self.root)
            if self.parent_id is not None:
                require(not cancelled_ancestor(nodes, self.parent_id, self.root), 'Command tree cancelled')
                parent = nodes[self.parent_id]
                require(parent['state'] == 'active' and not parent['writers_stopped']
                        and parent['guardian_pid'] == os.getpgrp(),
                        'Ownership environment is not the current private caller')
            node = dict(schema='m1-command-ownership-v1', node_id=self.node_id,
                        parent_id=self.parent_id, argv=self.argv, cwd=self.cwd,
                        guardian_pid=None, primary_pid=None, primary_returncode=None,
                        state='registered', cancelled=False, writers_stopped=False,
                        guardian_source=dict(path=str(Path(__file__).resolve()),
                                             sha256=sha(Path(__file__).resolve())))
            launcher = [sys.executable, '-I', '-S', '-B', '-c', GUARDIAN_BOOTSTRAP,
                        str(Path(__file__).resolve()), '--owned-command', str(self.path)]
            node['guardian_argv'] = launcher
            write_json(self.path, node)
            environment = dict(os.environ, PYTHONOPTIMIZE='0', PYTHONDONTWRITEBYTECODE='1',
                               M1_COMMAND_REGISTRY=str(self.root), M1_COMMAND_NODE=self.node_id)
            with defer_launch_signals():
                try:
                    self.process = subprocess.Popen(
                        launcher,
                        cwd=self.cwd, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        start_new_session=True)
                except BaseException:
                    node.update(state='start_failure', writers_stopped=True)
                    write_json(self.path, node)
                    raise
                # The guardian cannot launch before this lock is released.
                node.update(guardian_pid=self.process.pid, state='active')
                # A failed PID publication does not authorize an unrecorded
                # emergency signal. The caller retains this Popen and enters the
                # same fence/intent protocol below; inaccessible storage leaves
                # an unfinished attempt requiring external evidence/recovery.
                write_json(self.path, node)
        return self.process

    def receipt(self):
        node = read(self.path) if self.path.exists() else {}
        result = dict(schema='m1-command-ownership-v1', registry=str(self.root),
                    node_id=self.node_id, parent_id=self.parent_id,
                    guardian_pid=node.get('guardian_pid'), state=node.get('state', 'not_started'),
                    writers_stopped=node.get('writers_stopped', self.process is None))
        if 'signal_delivery' in node:
            result['signal_delivery'] = node['signal_delivery']
        return result

    def completed_returncode(self):
        node = read(self.path)
        require(node['writers_stopped'], 'Guardian exited without process closure')
        require(isinstance(node['primary_returncode'], int), 'Missing primary command result')
        return node['primary_returncode']

    def primary_start_error(self):
        node = read(self.path)
        return node.get('error_type') if node['primary_pid'] is None else None

    def cancel(self):
        try:
            self.cancel_registered()
        except BaseException:
            # Unknown/corrupt/inaccessible ownership is not authority to signal
            # an arbitrary PID. Keep this attempt unfinished, even if its direct
            # guardian can subsequently be reaped by bounded communicate.
            raise CleanupIncomplete('Command registry/writer closure unavailable') from None

    def cancel_registered(self):
        with ownership_lock(self.root):
            nodes = ownership_nodes(self.root)
            selected = {self.node_id}
            while True:
                expanded = selected | {key for key,node in nodes.items() if node['parent_id'] in selected}
                if expanded == selected:
                    break
                selected = expanded
            # A canonical/partial tombstone is checked by every ancestry launch
            # check. Publish the canonical fence before node copies or signals;
            # a later node-copy failure cannot silently reopen the subtree.
            if self.node_id in nodes:
                publish_cancellation_fence(self.root, self.node_id)
            # Complete the observable node fence pass before ANY dispatch.
            for key in sorted(selected & nodes.keys()):
                node = nodes[key]
                node['cancelled'] = True
                if key == self.node_id and self.process is not None and node['state'] == 'registered':
                    # Popen succeeded but PID publication failed. Only its own
                    # caller can recover the still-held direct child identity.
                    # No signal has been sent on that failed publication path.
                    if self.process.returncode is None:
                        node.update(guardian_pid=self.process.pid, state='active')
                    else:
                        node['state'] = 'leader_lost'
                if node['state'] == 'active':
                    node.setdefault('signal_delivery', dict(phase='unattempted'))
                write_json(self.root/(key+'.json'), node)
            for key in sorted(selected & nodes.keys()):
                node = nodes[key]
                if node['state'] == 'active':
                    if node['signal_delivery']['phase'] != 'unattempted':
                        # A prior intent consumes the one-shot authority even
                        # when dispatch may never have happened. No numeric retry.
                        continue
                    if (key == self.node_id and self.process is not None
                            and self.process.returncode is not None):
                        # An unexpectedly exited/reaped guardian broke the held
                        # identity contract. Its old PGID is not recovery authority.
                        node['state'] = 'leader_lost'
                        write_json(self.root/(key+'.json'), node)
                        continue
                    pgid = node['guardian_pid']
                    require(isinstance(pgid, int) and pgid > 1 and pgid != os.getpgrp(),
                            'Refusing shared process-group cancellation')
                    # Persist one-shot intent BEFORE the irreversible syscall.
                    # Readers seeing intent cannot tell whether a lost caller
                    # dispatched: it is uncertain delivery, never fresh authority.
                    node['state'] = 'signal_intent'
                    node['signal_delivery'] = dict(phase='intent', signal='SIGKILL',
                                                   pgid=pgid, by_node_id=self.node_id)
                    write_json(self.root/(key+'.json'), node)
                    try:
                        os.killpg(pgid, signal.SIGKILL)
                    except ProcessLookupError:
                        result = 'group_absent'
                    except BaseException as exc:
                        node['state'] = 'signal_uncertain'
                        node['signal_delivery'].update(phase='uncertain', error_type=type(exc).__name__)
                        write_json(self.root/(key+'.json'), node)
                        raise
                    else:
                        result = 'syscall_returned'
                    node['state'] = 'kill_sent'
                    node['signal_delivery'].update(phase='attempted', result=result)
                    # If this write fails, the persisted intent remains consumed;
                    # another owner must not dispatch to the old PGID again.
                    write_json(self.root/(key+'.json'), node)
            if any(node.get('signal_delivery', {}).get('phase') in ('intent', 'uncertain')
                   for key,node in nodes.items() if key in selected):
                raise CleanupIncomplete('Signal delivery uncertain; external ownership evidence required')
            if all(nodes[key]['writers_stopped'] for key in selected & nodes.keys()):
                return
        deadline = time.monotonic()+10
        while True:
            groups = live_group_members()
            with ownership_lock(self.root):
                nodes = ownership_nodes(self.root)
                pending = []
                for key in selected & nodes.keys():
                    node = nodes[key]
                    if node['state'] == 'kill_sent':
                        if groups.get(node['guardian_pid']):
                            pending.append(key)
                        else:
                            node.update(state='cancelled', writers_stopped=True)
                            write_json(self.root/(key+'.json'), node)
                    elif not node['writers_stopped']:
                        # Missing/lost identity after an uncatchable process or
                        # publication loss is uncertainty, never writer closure.
                        pending.append(key)
                if not pending:
                    return
            if time.monotonic() >= deadline:
                raise CleanupIncomplete('Owned process writers not established stopped')
            time.sleep(.02)


def owned_command_main(path):
    """Internal guardian; never a numerical adapter or a public collection mode."""
    path = Path(path).resolve()
    root, node_id = path.parent, path.stem
    # Caught dispositions reset to defaults in the exec'd command. Do not use
    # SIG_IGN, which would also be inherited by that command.
    signal.signal(signal.SIGINT, lambda *_: None)
    signal.signal(signal.SIGTERM, lambda *_: None)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGINT, signal.SIGTERM})
    with ownership_lock(root):
        nodes = ownership_nodes(root)
        node = nodes[node_id]
        require(node['guardian_pid'] == os.getpid() == os.getpgrp(), 'Not a private command leader')
        if cancelled_ancestor(nodes, node_id, root):
            node.update(state='cancelled_before_start', writers_stopped=True)
            write_json(path, node)
            return 130
        # Inherit guardian stdout/stderr: partial markers reach communicate even
        # when the entire owned tree must be killed during a timeout.
        try:
            primary = subprocess.Popen(node['argv'], cwd=node['cwd'])
        except BaseException as exc:
            node.update(state='settled', writers_stopped=True, primary_returncode=127,
                        error_type=type(exc).__name__)
            write_json(path, node)
            return 127
        node['primary_pid'] = primary.pid
        write_json(path, node)
    returncode = primary.wait()
    with ownership_lock(root):
        node = read(path)
        node['primary_returncode'] = returncode
        write_json(path, node)
    while True:
        groups = live_group_members()
        with ownership_lock(root):
            nodes = ownership_nodes(root)
            # Nested journals finish/reap before their caller's primary exits;
            # nevertheless refuse closure if any registered descendant remains.
            descendants = {node_id}
            while True:
                more = descendants | {k for k,n in nodes.items() if n['parent_id'] in descendants}
                if more == descendants:
                    break
                descendants = more
            nested_live = any(not nodes[k]['writers_stopped'] for k in descendants-{node_id})
            if groups.get(os.getpgrp(), set()) <= {os.getpid()} and not nested_live:
                node = nodes[node_id]
                node.update(state='settled', writers_stopped=True)
                write_json(path, node)
                return returncode if returncode >= 0 else 128-returncode
        time.sleep(.02)


@contextmanager
def collection_failure_envelope(out):
    """First operation after mkdir; preserve partial bytes and typed failures.

    A collecting status is intentionally durable through uncatchable termination.
    Storage loss may prevent even a failed-status write; that needs external
    status/log evidence, never a fabricated finalized collection.
    """
    out = Path(out)
    attempt = dict(stage='initializing')
    previous = {}
    def terminated(_signum, _frame):
        raise KeyboardInterrupt('Collection termination requested')
    try:
        write_json(out/'collection_status.json', dict(status='collecting', full_m1_accepted=False,
                                                      final_ai_output_review_passed=False))
        if threading.current_thread() is threading.main_thread():
            previous[signal.SIGTERM] = signal.signal(signal.SIGTERM, terminated)
        yield attempt
    except BaseException as exc:
        # A failed publication must not leave a successful collection manifest.
        # Exception arguments (transport credentials) are never serialized.
        invalidated = True
        try:
            manifest = out/'sha256.json'
            if manifest.exists():
                manifest.replace(out/'unfinished_sha256.json')
        except BaseException:
            invalidated = False
        try:
            unfinished = isinstance(exc, CleanupIncomplete)
            for path in out.rglob('*commands.json'):
                try:
                    unfinished |= any(row.get('outcome') == 'running' for row in read(path))
                except BaseException:
                    unfinished = True
            write_json(out/'collection_status.json', dict(status='failed', error_type=type(exc).__name__,
                       stage=attempt['stage'],
                       full_m1_accepted=False, final_ai_output_review_passed=False,
                       publication_manifest_invalidated=invalidated,
                       external_evidence_required=unfinished or not invalidated))
        except BaseException:
            # Keep the original failure and partial bytes. This cannot guarantee
            # local finalization when the destination itself ceases to work.
            pass
        raise
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


class CommandJournal:
    """Durable attempts; hashes are closed only after owned writers stop/reap."""
    def __init__(self, out, filename='commands.json', log_directory='logs'):
        self.out, self.path = Path(out), Path(out) / filename
        self.logs, self.rows, self.lock = log_directory, [], threading.Lock()
        self.cancelled, self.owners = threading.Event(), []
        require(not self.path.exists(), 'Preserve existing command journal')
        self.secrets = secret_values()
        write_json(self.path, self.rows)

    def check_cancelled(self):
        if self.cancelled.is_set():
            raise CommandFailed('Collection command pool cancelled')

    def cancel(self):
        with self.lock:
            self.cancelled.set()
            owners = list(self.owners)
        errors = []
        for owner in owners:
            try:
                owner.cancel()
            except BaseException as exc:
                errors.append(type(exc).__name__)
        if errors:
            raise CleanupIncomplete('Command pool ownership cleanup incomplete')

    def run(self, label, argv, cwd, timeout=7200, **metadata):
        argv = list(map(str, argv))
        credential_free_argv(argv, self.secrets)
        self.check_cancelled()
        started = time.monotonic()
        with self.lock:
            attempt_id = len(self.rows) + 1
            prefix = self.logs + '/' + str(attempt_id).zfill(3) + '-' + label
            stdout_path, stderr_path = prefix + '.stdout', prefix + '.stderr'
            for name in (stdout_path, stderr_path):
                path = self.out / relative_path(name)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch(exist_ok=False)
            row = dict(attempt_id=attempt_id, label=label, argv=argv, cwd=str(cwd),
                       started_utc=utc(), finished_utc=None, duration_seconds=None,
                       timeout_seconds=timeout,
                       outcome='running', returncode=None, interpreter=runtime_info(),
                       child_environment=dict(PYTHONOPTIMIZE='0', PYTHONDONTWRITEBYTECODE='1'),
                       stdout=dict(path=stdout_path, sha256=digest(b''), bytes=0),
                       stderr=dict(path=stderr_path, sha256=digest(b''), bytes=0), **metadata)
            self.rows.append(row)
            write_json(self.path, self.rows)
        process, owner, stdout, stderr = None, None, b'', b''
        outcome, returncode = 'start_failure', None
        error_type = None
        closed = True
        try:
            owner = OwnedCommand(self.out, argv, cwd)
            with self.lock:
                self.check_cancelled()
                self.owners.append(owner)
                process = owner.start()
                row['ownership'] = owner.receipt()
                write_json(self.path, self.rows)
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                returncode = owner.completed_returncode()
                error_type = owner.primary_start_error()
                if error_type is not None:
                    returncode, outcome = None, 'start_failure'
                else:
                    outcome = 'success' if returncode == 0 else 'nonzero'
            except subprocess.TimeoutExpired as exc:
                stdout, stderr = timeout_output_snapshot(exc, stdout, stderr)
                owner.cancel()
                stdout, stderr = process.communicate(timeout=10)
                returncode, outcome = process.returncode, 'timeout'
        except BaseException as exc:
            error_type = type(exc).__name__
            if isinstance(exc, subprocess.TimeoutExpired):
                stdout, stderr = timeout_output_snapshot(exc, stdout, stderr)
            if process is None and owner is not None:
                # A receipt write can fail after Popen but before start returns.
                process = owner.process
            if process is not None:
                try:
                    # Do this even if the actual command/guardian already exited:
                    # registered nested groups can still own the inherited pipes.
                    owner.cancel()
                except BaseException as cleanup_exc:
                    closed = False
                    error_type = type(cleanup_exc).__name__
                try:
                    # Reap the direct guardian even if registry closure failed.
                    # Bounded draining cannot turn uncertainty into closed logs.
                    stdout, stderr = process.communicate(timeout=10)
                    returncode = process.returncode
                except BaseException as cleanup_exc:
                    if isinstance(cleanup_exc, subprocess.TimeoutExpired):
                        stdout, stderr = timeout_output_snapshot(cleanup_exc, stdout, stderr)
                    closed = False
                    error_type = type(cleanup_exc).__name__
                outcome = 'interrupted'
            # Do not echo exception arguments: a transport exception may carry secrets.
            stderr += ('\nCommand exception type: ' + error_type + '\n').encode()
        finally:
            with self.lock:
                for key, data in (('stdout', stdout), ('stderr', stderr)):
                    safe = redact(data, self.secrets).encode('utf-8')
                    (self.out / row[key]['path']).write_bytes(safe)
                    row[key].update(sha256=digest(safe) if closed else None, bytes=len(safe))
                row.update(finished_utc=utc() if closed else None,
                           duration_seconds=max(0., time.monotonic()-started),
                           outcome=outcome if closed else 'running', returncode=returncode,
                           error_type=error_type, logs_closed=closed,
                           external_evidence_required=not closed)
                if owner is not None:
                    row['ownership'] = owner.receipt()
                write_json(self.path, self.rows)
        if not closed:
            raise CleanupIncomplete('Retained unfinished command; external status/log evidence required')
        if outcome != 'success':
            raise CommandFailed('Preserved command failure: ' + label + ' (' + outcome + ')')
        return row


def physics_files(config):
    names = ['final.csv']
    primary_shock = (config['case'] == 'brio-wu'
                     and ((config['jitter'] == 0 and config['jitter_mode'] == 'planar')
                          or (config['jitter'] == .15 and config['jitter_mode'] == 'columns')))
    primary_vortex = config['case'] == 'orszag-tang' and config['jitter'] == 0
    if primary_shock or primary_vortex:
        names.append('geometry.json')
    if primary_vortex:
        names.append('projected_bins.json')
    return names


def case_metadata(root, plan):
    paths = []
    for entry in plan['cases']:
        case = root / relative_path(entry['directory'])
        paths += [case / n for n in ('case.json', 'payload.json', 'reana.yaml',
                                     'snapshot.json', 'preflight/preflight.json')]
        received = root / 'download' / relative_path(entry['directory']) / 'outputs'
        if (received / 'execution.json').exists():
            paths += [received / n for n in ('execution.json', 'record.json', 'artifacts.sha256.json')]
            if (received / 'runtime.json').exists():
                paths.append(received / 'runtime.json')
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--client', required=True)
    parser.add_argument('--require-complete', action='store_true')
    parser.add_argument('--original-root', type=Path,
                        help='Original live root when caller supplies a private captured view')
    parser.add_argument('--reference-root', type=Path,
                        help='Captured reference/packet cwd context supplied by complete collector')
    args = parser.parse_args()
    root, out, repo = args.plan.resolve(), args.destination.resolve(), Path.cwd()
    require(not out.exists(), 'Use a fresh isolated checkpoint directory')
    original = (args.original_root or root).resolve()
    reference_root = (args.reference_root or repo).resolve()
    reference_paths = [Path('tests/reference/external_mhd') / n
                       for n in ('brio_8192.csv.gz','vortex_512.csv.gz')]
    packet = Path('benchmarks/m0/packet.json')
    reference_metadata = Path('tests/reference/external_mhd/provenance.json')
    reference_inputs = {reference_root/p:p for p in [packet,*reference_paths,reference_metadata]}
    require(not out.is_relative_to(root) and not out.is_relative_to(original),
            'Never write into a live/captured source plan')
    for closed_packet in ('m1_acceptance','m1_iterative_step_campaigns'):
        require(not out.is_relative_to(repo/'tests/reference'/closed_packet),
                'Historical reference packets are closed')
    paths = [root / n for n in ('plan.json', 'runs.json', 'checkpoint.json')]
    paths += list(reference_inputs)
    def coherent(data):
        runs = json.loads(data[root/'runs.json'])
        checkpoint = json.loads(data[root/'checkpoint.json'])
        if checkpoint['completed_cases'] != len(runs):
            raise CaptureChanged('Observer checkpoint/run generation is incoherent')
    capture = MetadataCapture.take(paths, lambda data: case_metadata(root, json.loads(data[root/'plan.json'])),
                                   validate=coherent)
    plan, observed_runs, checkpoint = [capture.parsed(root/n) for n in ('plan.json','runs.json','checkpoint.json')]
    require(plan['snapshot_sha256'] == SNAPSHOT and len(plan['cases']) == 30, 'Wrong physics plan')
    entries = {e['specification']['config']['name']: e for e in plan['cases']}
    require(len(entries) == len({e['workflow'] for e in plan['cases']}) == 30, 'Duplicate physics identity')
    require(set(observed_runs) <= set(entries), 'Unknown observed case')
    require(checkpoint['completed_cases'] == len(observed_runs) and checkpoint['expected_cases'] == 30,
            'Incoherent observed checkpoint/run map')
    require(not checkpoint['verified_required_failure'] and not checkpoint['execution_failures'],
            'Required physical/execution failure blocks collection')
    require(all(r['status'] == 'completed' for r in observed_runs.values()), 'Non-completed run')
    if args.require_complete:
        require(checkpoint['all_terminal'] and set(observed_runs) == set(entries), 'Full physics not ready')
    out.mkdir(parents=True)
    with collection_failure_envelope(out) as attempt:
        attempt['stage'] = 'capture_mapping'
        destinations = {}
        for path in capture.data:
            if path in reference_inputs:
                destinations[path] = 'metadata/reference_inputs/'+str(reference_inputs[path])
                continue
            rel = path.relative_to(root).as_posix()
            if rel in ('plan.json', 'checkpoint.json'):
                destinations[path] = rel
            elif rel == 'runs.json':
                destinations[path] = 'observed_run_map.json'
            elif rel.startswith('download/'):
                destinations[path] = rel
            else:
                destinations[path] = 'metadata/' + rel
        def source_name(path):
            origin = (repo/reference_inputs[path] if path in reference_inputs
                      else original/path.relative_to(root))
            return str(origin.relative_to(repo)) if origin.is_relative_to(repo) else str(origin)
        attempt['stage'] = 'capture_export'
        record = capture.export(out, destinations, source_name)
        attempt['stage'] = 'metadata_and_provenance'
        write_json(out/'metadata_capture.json', record)
        collector_bytes, collector_generation = read_once(Path(__file__).resolve())
        (out/'collector.py').write_bytes(collector_bytes)
        snapshot_path = root / relative_path(plan['cases'][0]['directory']) / 'snapshot.json'
        require(digest(capture.data[snapshot_path]) == SNAPSHOT, 'Wrong source snapshot')
        snapshot = capture.parsed(snapshot_path)
        source_digests = {str(path):digest(capture.data[reference_root/path])
                          for path in [packet,*reference_paths,reference_metadata]}
        require(all(value == snapshot['source_sha256'][key] for key,value in source_digests.items()),
                'Reference/source identity mismatch')
        provenance = dict(
            scope='Fresh completed REANA raw inputs for independent reference reducers; not full staged-input/phase/M1 acceptance.',
            snapshot_sha256=SNAPSHOT, binary_sha256=BINARY,
            source_sha256={str(packet): source_digests[str(packet)]},
            reference_sha256={path.name: source_digests[str(path)] for path in reference_paths},
            collector_sha256=digest(collector_bytes), runtime=runtime_info(),
            observed_run_map_sha256=digest(capture.data[root/'runs.json']),
            observer_checkpoint_sha256=digest(capture.data[root/'checkpoint.json']),
            plan_sha256=digest(capture.data[root/'plan.json']))
        write_json(out/'provenance.json', provenance)
        attempt['stage'] = 'journal_initialization'
        journal = CommandJournal(out, 'transport_commands.json', 'transport_logs')

        def collect(entry):
            journal.check_cancelled()
            spec, config = entry['specification'], entry['specification']['config']
            name = config['name']
            require(relative_path(name).parts == (name,), 'Invalid case name')
            require(spec['kind'] == 'physics' and config['profile'] == 'bulk-frame-heun-quadratic-v1'
                    and config['riemann_solver'] == 'hlld-pressure'
                    and spec['options'] == dict(accelerated_projection=False, projection_screening=1.,
                                               potential_limiter='smooth-extrema'), 'Wrong candidate')
            case = root / relative_path(entry['directory'])
            require(digest(capture.data[case/'payload.json']) == entry['payload_sha256']
                    and digest(capture.data[case/'reana.yaml']) == entry['workflow_sha256']
                    and capture.parsed(case/'case.json') == spec, 'Staged case metadata mismatch')
            if name not in observed_runs:
                return dict(name=name, pending='Absent in captured observer checkpoint; not a failure')
            received = root/'download'/relative_path(entry['directory'])/'outputs'
            require(received/'execution.json' in capture.data, 'Completed case lacks execution receipt')
            manifest = capture.parsed(received/'artifacts.sha256.json')
            execution, run = capture.parsed(received/'execution.json'), capture.parsed(received/'record.json')
            for filename in ('execution.json','record.json'):
                require(digest(capture.data[received/filename]) == manifest['outputs/'+filename],
                        'Execution/record manifest mismatch')
            require(execution['case'] == spec and run['config'] == config, 'Case/record config mismatch')
            require(execution['payload_sha256'] == entry['payload_sha256']
                    and execution['snapshot_sha256'] == SNAPSHOT and execution['binary_sha256'] == BINARY
                    and execution['preflight_sha256'] == digest(capture.data[case/'preflight/preflight.json'])
                    and execution['record_sha256'] == digest(capture.data[received/'record.json']),
                    'Execution provenance mismatch')
            require(execution['status'] == 'completed' and execution['single_case_gates_passed']
                    and run['status'] == 'completed' and run['returncode'] == 0
                    and run == observed_runs[name], 'Execution differs from captured run map')
            local = out/'download'/relative_path(entry['directory'])
            requested = ['outputs/raw/'+name+'/'+filename for filename in physics_files(config)]
            needed, artifacts = [], []
            for remote in requested:
                journal.check_cancelled()
                source, target = received.parent/relative_path(remote), local/relative_path(remote)
                if source.exists() and sha(source) == manifest[remote]:
                    require(source.resolve(strict=True).is_relative_to(original),
                            'Cached raw input must originate inside this actual fresh phase')
                    copy_verified(source, target, manifest[remote], journal.check_cancelled)
                else:
                    needed.append(remote)
            transport = None
            if needed:
                transport = journal.run('download-'+name, shlex.split(args.client)+[
                    'download','-w',entry['workflow'],'-o',str(local),*needed],
                    cwd=repo, timeout=1800, workflow=entry['workflow'], requested_paths=needed)
            checked = {}
            for filename, remote in zip(physics_files(config), requested):
                journal.check_cancelled()
                source, target = local/relative_path(remote), out/name/filename
                expected = run['sha256'][filename]
                require(manifest[remote] == expected, 'Raw manifest/run identity mismatch')
                identity = copy_verified(source, target, expected, journal.check_cancelled)
                checked[filename] = expected
                original_source = (source if remote in needed else
                                   original/'download'/relative_path(entry['directory'])/relative_path(remote))
                artifacts.append(dict(artifact=filename, remote_path=remote, **identity,
                    copied_path=str(target.relative_to(out)), local_source=str(original_source),
                    acquisition='fresh_workflow_download' if remote in needed else 'already_downloaded_fresh',
                    transport_attempt_id=transport['attempt_id'] if remote in needed else None))
            return dict(name=name, workflow=entry['workflow'], run=run, verified=checked, artifacts=artifacts,
                        execution_sha256=digest(capture.data[received/'execution.json']),
                        manifest_sha256=digest(capture.data[received/'artifacts.sha256.json']))

        attempt['stage'] = 'case_collection'
        pool, futures = ThreadPoolExecutor(max_workers=4), []
        try:
            for entry in plan['cases']:
                journal.check_cancelled()
                futures.append(pool.submit(collect, entry))
            positions = {future:index for index,future in enumerate(futures)}
            rows = [None]*len(futures)
            for future in as_completed(futures):
                rows[positions[future]] = future.result()
        except BaseException:
            # Fence new transport launches, cancel queued cases, and stop all
            # registered running transport trees before waiting for worker exits.
            for future in futures:
                future.cancel()
            try:
                journal.cancel()
            finally:
                pool.shutdown(wait=True, cancel_futures=True)
            raise
        else:
            pool.shutdown(wait=True)
        attempt['stage'] = 'verification_and_publication'
        runs = {row['name']: row.pop('run') for row in rows if 'run' in row}
        require(set(runs) == set(observed_runs), 'Captured completed case lacks verified actual inputs')
        final_check = capture.unchanged()
        require(read_once(Path(__file__).resolve()) == (collector_bytes,collector_generation),
                'Collector source changed')
        verify_capture_copies(out,record)
        record['final_unchanged_check'] = final_check
        write_json(out/'metadata_capture.json', record)
        write_json(out/'runs.json', runs)
        write_json(out/'input_receipts.json', dict(scope=provenance['scope'],completed=len(runs),expected=30,
            observations=rows, transport_journal='transport_commands.json',
            capture_manifest_sha256=sha(out/'metadata_capture.json'), full_m1_accepted=False))
        print('Verified actual raw inputs for',len(runs),'of 30 captured completed physics cases')

        write_json(out/'collection_status.json', dict(status='complete', full_m1_accepted=False,
                                                   final_ai_output_review_passed=False))


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--owned-command':
        try:
            guardian_code = owned_command_main(sys.argv[2])
        except BaseException as guardian_exc:
            # Keep the registered private leader alive on observation/storage
            # failure. Its owner can safely cancel it, without reusing a stale
            # PID/group identity. No exception arguments enter the log.
            print('Ownership guardian exception type: '+type(guardian_exc).__name__,
                  file=sys.stderr, flush=True)
            while True:
                time.sleep(1)
        raise SystemExit(guardian_code)
    main()
