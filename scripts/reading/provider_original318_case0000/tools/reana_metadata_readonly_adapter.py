"""GET-only REANA 0.9 API adapter for the metadata observer protocol.

Source-audited interface, not a claim of configured-service readiness. The
installed OpenAPI/client and official tagged server/controller source receipts
are under ignored results/metadata_readonly_adapter_design_20261122/. This is
an independent stdlib implementation, not a copy of the dependency client.
Import is inert: private settings/network/files are accessed only by calls.
"""
import argparse
from datetime import datetime, timezone
from email.message import Message
import http.client
import json
import os
from pathlib import Path, PurePosixPath
import re
import socket
import ssl
import stat
import sys
import time
from urllib import error, parse, request
import uuid

MAX_BYTES = 16 * 1024 * 1024  # Same per-file bound as the frozen v2 runner.
PAGE_SIZE = 100
MAX_PAGES = 100
DEADLINE_SECONDS = 120  # Cooperative checkpoints, not interruption within buffered I/O/DNS.
SOCKET_SECONDS = 15  # Socket idle timeout, not a total transfer bound.
ARTIFACTS = frozenset(('result.json', 'runtime.json', 'command.json', 'stdout.txt',
    'stderr.txt', 'child_result.json', 'child_raw.bin', 'artifacts.sha256.json'))
DOWNLOAD_STATES = frozenset(('finished', 'failed', 'stopped'))


class AdapterError(Exception):
    """Only a registered static code and numeric HTTP status may be emitted."""
    def __init__(self, code, http_status=None):
        self.code, self.http_status = code, http_status
        super().__init__(code)


def ensure(condition, code):
    if not condition:
        raise AdapterError(code)


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False) + '\n').encode()


def parse_json(data):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            ensure(key not in value, 'duplicate_json_key')
            value[key] = item
        return value
    try:
        return json.loads(data, object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(AdapterError('nonfinite_json')))
    except (ValueError, UnicodeError, TypeError):
        raise AdapterError('invalid_json') from None


def workflow_identity(workflow):
    ensure(type(workflow) is str and re.fullmatch(r'[a-z][a-z0-9-]{0,62}\.[1-9][0-9]*', workflow),
           'invalid_workflow')
    name, version = workflow.rsplit('.', 1)
    return name, int(version)


def artifact_path(path):
    ensure(type(path) is str and path in {'outputs/' + n for n in ARTIFACTS}, 'unsafe_remote_path')
    return path


def settings_from_private(environ=None):
    """Read credentials in memory only; never return them in a public receipt.

    Both standard REANA variables override the private file as a pair. The
    OPENMHD_REANA_CONFIG variable selects a filename, never credential values.
    No target configuration is read during import or source/import preflight.
    """
    env = os.environ if environ is None else environ
    server, token = env.get('REANA_SERVER_URL'), env.get('REANA_ACCESS_TOKEN')
    if server is not None or token is not None:
        ensure(bool(server) and bool(token), 'incomplete_environment_connection')
    else:
        path = Path(env.get('OPENMHD_REANA_CONFIG',
                            str(Path.home() / '.config/openmhd/reana-p4n.json')))
        try:
            info = path.lstat()
            ensure(stat.S_ISREG(info.st_mode) and info.st_size <= 65536, 'invalid_private_config')
            with path.open('rb') as stream:
                data = stream.read(65537)
            ensure(len(data) <= 65536, 'invalid_private_config')
            value = parse_json(data)
            ensure(type(value) is dict, 'invalid_private_config')
            server, token = value.get('server_url'), value.get('access_token')
        except AdapterError:
            raise
        except OSError:
            raise AdapterError('private_config_unavailable') from None
    ensure(type(server) is str and type(token) is str and server and token
           and not any(c.isspace() for c in token), 'invalid_private_connection')
    try:
        parsed = parse.urlsplit(server)
        valid = (parsed.scheme == 'https' and parsed.hostname and parsed.username is None
                 and parsed.password is None and not parsed.query and not parsed.fragment
                 and parsed.path in ('', '/') and parsed.port != 0)
        ensure(valid and not any(c.isspace() for c in server), 'invalid_server_origin')
    except ValueError:
        raise AdapterError('invalid_server_origin') from None
    return server.rstrip('/'), token


class RejectRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AdapterError('redirect_rejected', code)


def https_opener():
    # The audited legacy client uses verify=False. We deliberately require
    # normal CA/hostname verification and never retry with verification disabled.
    context = ssl.create_default_context()
    return request.build_opener(request.ProxyHandler({}),
                                request.HTTPSHandler(context=context), RejectRedirect())


class Target:
    """No-follow directory traversal, exclusive partial, no-replace publication.

    On failure only <name>.partial is retained, with a typed stderr diagnostic;
    the requested artifact is never published. SIGKILL may leave that partial
    without a process-local diagnostic; external transport receipts remain needed.
    """
    def __init__(self, path):
        self.parent_fd, self.fd = None, None
        self.received = self.written = 0
        self.published = False
        ensure(isinstance(path, (str, Path)), 'invalid_output')
        raw = str(path)
        ensure(raw and '\x00' not in raw and '\\' not in raw, 'unsafe_output_path')
        parts = PurePosixPath(raw).parts
        ensure(parts and '..' not in parts and parts[-1] not in ('/', '.', '..'), 'unsafe_output_path')
        self.name, self.partial = parts[-1], parts[-1] + '.partial'
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        current = os.open('/' if raw.startswith('/') else '.', flags)
        try:
            parents = parts[1:-1] if raw.startswith('/') else parts[:-1]
            for part in parents:
                next_fd = os.open(part, flags, dir_fd=current)
                os.close(current)
                current = next_fd
            for name in (self.name, self.partial):
                try:
                    os.stat(name, dir_fd=current, follow_symlinks=False)
                except FileNotFoundError:
                    continue
                raise AdapterError('output_exists')
            self.fd = os.open(self.partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                              0o600, dir_fd=current)
            self.parent_fd = current
        except BaseException:
            os.close(current)
            raise

    def append(self, data):
        ensure(type(data) is bytes, 'invalid_body_bytes')
        self.received += len(data)
        retained = data[:max(0, MAX_BYTES - self.written)]
        offset = 0
        while offset < len(retained):
            count = os.write(self.fd, retained[offset:])
            ensure(count > 0, 'output_write_failed')
            offset += count
            self.written += count
        ensure(self.received <= MAX_BYTES, 'size_limit')

    def publish(self):
        os.fsync(self.fd)
        info = os.fstat(self.fd)
        named = os.stat(self.partial, dir_fd=self.parent_fd, follow_symlinks=False)
        ensure(stat.S_ISREG(info.st_mode) and stat.S_ISREG(named.st_mode)
               and (info.st_dev, info.st_ino, info.st_size) ==
                   (named.st_dev, named.st_ino, self.written), 'changed_partial_file')
        linked = False
        try:
            os.link(self.partial, self.name, src_dir_fd=self.parent_fd,
                    dst_dir_fd=self.parent_fd, follow_symlinks=False)
            linked = True
            actual = os.stat(self.name, dir_fd=self.parent_fd, follow_symlinks=False)
            ensure(stat.S_ISREG(actual.st_mode) and (actual.st_dev, actual.st_ino, actual.st_size) ==
                   (info.st_dev, info.st_ino, self.written), 'changed_published_file')
            os.fsync(self.parent_fd)
            os.unlink(self.partial, dir_fd=self.parent_fd)
            self.published = True
        except FileExistsError:
            raise AdapterError('output_exists') from None
        except BaseException:
            if linked:
                try:
                    actual = os.stat(self.name, dir_fd=self.parent_fd, follow_symlinks=False)
                    if (actual.st_dev, actual.st_ino) == (info.st_dev, info.st_ino):
                        os.unlink(self.name, dir_fd=self.parent_fd)
                except OSError:
                    pass  # Storage loss may prevent cleanup; no success is emitted.
            raise

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        if self.parent_fd is not None:
            os.close(self.parent_fd)
            self.parent_fd = None


class Client:
    def __init__(self, server, token, opener=None, clock=None):
        # Public constructors must apply the same origin/credential checks as main.
        self.server, self.token = settings_from_private({
            'REANA_SERVER_URL': server, 'REANA_ACCESS_TOKEN': token})
        self.opener = https_opener() if opener is None else opener
        self.clock = time.monotonic if clock is None else clock
        self.deadline = self.clock() + DEADLINE_SECONDS
        self.page_count = 0

    def remaining(self):
        remaining = self.deadline - self.clock()
        ensure(remaining > 0, 'adapter_deadline')
        return min(SOCKET_SECONDS, remaining)

    def get(self, endpoint, parameters, consume):
        # Endpoints are built only by the two GET operations below. URLs carrying
        # the source-supported query token exist only in memory, never diagnostics.
        url = self.server + endpoint + '?' + parse.urlencode({**parameters, 'access_token': self.token})
        response = None
        try:
            req = request.Request(url, headers={'Accept-Encoding': 'identity', 'Cache-Control': 'no-cache'}, method='GET')
            response = self.opener.open(req, timeout=self.remaining())
            code = response.status
            if type(code) is not int or code != 200:
                raise AdapterError('redirect_rejected' if type(code) is int and 300 <= code < 400
                                   else 'http_error', code if type(code) is int else None)
            ensure(response.geturl() == url, 'redirect_rejected')
            headers = response.headers
            for name in ('Content-Length', 'Content-Type', 'Content-Encoding', 'Content-Disposition'):
                ensure(len(headers.get_all(name, [])) <= 1, 'duplicate_http_header')
            ensure(headers.get('Content-Encoding', 'identity').lower() == 'identity', 'encoded_body')
            length = headers.get('Content-Length')
            if length is not None:
                ensure(re.fullmatch(r'0|[1-9][0-9]*', length) is not None, 'invalid_content_length')
                length = int(length)
                ensure(length <= MAX_BYTES, 'size_limit')
            consume(response, headers, length)
        except AdapterError:
            raise
        except error.HTTPError as exc:
            # Do not read/retain error pages, Location, URL or exception arguments.
            exc.close()
            raise AdapterError('redirect_rejected' if 300 <= exc.code < 400 else 'http_error', exc.code) from None
        except (error.URLError, ssl.SSLError, socket.timeout, TimeoutError, ConnectionError):
            raise AdapterError('network_error') from None
        finally:
            if response is not None:
                response.close()

    def stream(self, response, append, length):
        received = 0
        try:
            while True:
                self.remaining()
                block = response.read(65536)
                if not block:
                    self.remaining()  # A late EOF must not authorize publication.
                    break
                received += len(block)
                append(block)
                self.remaining()  # Retain bytes honestly, then reject a late buffered read.
                ensure(received <= MAX_BYTES, 'size_limit')
        except http.client.IncompleteRead as exc:
            if exc.partial:
                append(exc.partial)
            raise AdapterError('incomplete_body') from None
        ensure(length is None or received == length, 'content_length_mismatch')

    def list_page(self, name, page):
        buffers = []
        def consume(response, headers, length):
            ensure(headers.get_content_type() == 'application/json', 'invalid_list_content_type')
            self.stream(response, buffers.append, length)
        self.get('/api/workflows', dict(type='batch', workflow_id_or_name=name,
            sort='asc', page=page, size=PAGE_SIZE, verbose='false',
            include_progress='false', include_workspace_size='false'), consume)
        self.page_count += 1
        value = parse_json(b''.join(buffers))
        ensure(type(value) is dict and type(value.get('items')) is list
               and type(value.get('total')) is int and value['total'] >= 0, 'invalid_rest_page')
        total, items = value['total'], value['items']
        ensure(total <= PAGE_SIZE * MAX_PAGES, 'pagination_limit')
        expected = max(0, min(PAGE_SIZE, total - (page - 1) * PAGE_SIZE))
        ensure(len(items) == expected, 'pagination_incomplete')
        for key, expected_value in (('page', page), ('size', PAGE_SIZE)):
            if key in value:
                ensure(type(value[key]) is int and value[key] == expected_value, 'pagination_mismatch')
        for key, expected_value in (('has_prev', page > 1), ('has_next', page * PAGE_SIZE < total)):
            if key in value:
                ensure(type(value[key]) is bool and value[key] == expected_value, 'pagination_mismatch')
        rows = []
        for row in items:
            ensure(type(row) is dict, 'invalid_rest_row')
            full = row.get('name')
            actual_name, version = workflow_identity(full)
            ensure(actual_name == name, 'workflow_filter_mismatch')
            status, identifier = row.get('status'), row.get('id')
            ensure(type(status) is str and re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', status), 'invalid_rest_status')
            try:
                ensure(type(identifier) is str and str(uuid.UUID(identifier)) == identifier
                       and uuid.UUID(identifier).version == 4, 'invalid_rest_workflow_id')
            except (ValueError, AttributeError):
                raise AdapterError('invalid_rest_workflow_id') from None
            # REST name is versioned; never infer it from the requested version
            # or CLI-only run_number strings, nor deduplicate ambiguous rows.
            rows.append(dict(id=identifier, workflow=full, name=actual_name, version=version, status=status))
        return total, rows

    def scan(self, name):
        total, rows = self.list_page(name, 1)
        for page in range(2, max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE) + 1):
            next_total, more = self.list_page(name, page)
            ensure(next_total == total, 'pagination_changed')
            rows.extend(more)
        ensure(len(rows) == total, 'pagination_incomplete')
        return rows

    def matching_rows(self, workflow):
        name, _ = workflow_identity(workflow)
        first, second = self.scan(name), self.scan(name)
        ensure(first == second, 'observation_changed')
        return [row for row in second if row['workflow'] == workflow]

    def observe(self, workflow):
        rows = self.matching_rows(workflow)
        receipt = dict(schema='openmhd.metadata-server-observation.v1', origin='server',
            observed_utc=datetime.now(timezone.utc).isoformat(),
            matches=[{k: row[k] for k in ('workflow', 'name', 'version', 'status')} for row in rows])
        return receipt, [row['id'] for row in rows]

    def download(self, workflow, path, target):
        artifact_path(path)
        rows = self.matching_rows(workflow)
        ensure(len(rows) == 1, 'ambiguous_or_missing_workflow')
        # Failed/stopped terminal workspaces are forensic evidence only. The
        # unchanged preflight release and all passing verdicts require finished
        # before/after observations independently of this download capability.
        ensure(rows[0]['status'] in DOWNLOAD_STATES, 'workflow_not_terminal')
        selected = rows[0]
        def consume(response, headers, length):
            ensure(headers.get_content_type() == 'application/octet-stream', 'invalid_artifact_content_type')
            disposition = headers.get('Content-Disposition')
            if disposition is not None:
                message = Message()
                message['Content-Disposition'] = disposition
                ensure(message.get_content_disposition() == 'attachment'
                       and message.get_filename() in (path, PurePosixPath(path).name), 'artifact_name_mismatch')
            self.stream(response, target.append, length)
        self.get('/api/workflows/' + selected['id'] + '/workspace/' + parse.quote(path, safe='/'), {}, consume)
        ensure(self.matching_rows(workflow) == [selected], 'download_workflow_changed')
        return [selected['id']]


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise AdapterError('invalid_arguments')


def parser():
    value = SafeParser(description=__doc__)
    value.add_argument('action', choices=('observe', 'download'))
    value.add_argument('--workflow', required=True)
    value.add_argument('--output', type=Path, required=True)
    value.add_argument('--path')
    return value


def main(argv=None):
    started = datetime.now(timezone.utc).isoformat()
    target, client, args = None, None, None
    diagnostic = dict(schema='openmhd.metadata-readonly-adapter-diagnostic.v1',
        outcome='failure', code='initializing', started_utc=started, finished_utc=started,
        action=None, workflow=None, requested_path=None, http_status=None,
        workflow_ids=[], page_count=0, received_bytes=0, retained_bytes=0, partial_file=None)
    try:
        ensure(__debug__ and sys.flags.optimize == 0, 'optimized_rejected')
        args = parser().parse_args(argv)
        workflow_identity(args.workflow)
        ensure((args.action == 'download' and args.path is not None)
               or (args.action == 'observe' and args.path is None), 'invalid_arguments')
        if args.path is not None:
            artifact_path(args.path)
        diagnostic.update(action=args.action, workflow=args.workflow, requested_path=args.path)
        target = Target(args.output)
        server, token = settings_from_private()
        client = Client(server, token)
        if args.action == 'observe':
            value, ids = client.observe(args.workflow)
            target.append(json_bytes(value))
        else:
            ids = client.download(args.workflow, args.path, target)
        client.remaining()  # Also covers final list/JSON/observation processing.
        target.publish()
        diagnostic.update(outcome='success', code='completed', workflow_ids=ids)
        returncode = 0
    except AdapterError as exc:
        diagnostic.update(code=exc.code, http_status=exc.http_status)
        returncode = 1
    except (OSError, ValueError, TypeError):
        diagnostic['code'] = 'local_or_protocol_error'
        returncode = 1
    except KeyboardInterrupt:
        diagnostic['code'] = 'interrupted'
        returncode = 1
    except Exception:
        # Never serialize exception text/tracebacks/URLs from stdlib or a server.
        diagnostic['code'] = 'unexpected_failure'
        returncode = 1
    finally:
        if target is not None:
            diagnostic.update(received_bytes=target.received, retained_bytes=target.written,
                partial_file=target.partial if not target.published else None)
            try:
                target.close()
            except OSError:
                diagnostic.update(outcome='failure', code='output_close_failed')
                returncode = 1
        if client is not None:
            diagnostic['page_count'] = client.page_count
        diagnostic['finished_utc'] = datetime.now(timezone.utc).isoformat()
        stream = sys.stdout if diagnostic['outcome'] == 'success' else sys.stderr
        stream.write(json_bytes(diagnostic).decode())
    return returncode


if __name__ == '__main__':
    raise SystemExit(main())
