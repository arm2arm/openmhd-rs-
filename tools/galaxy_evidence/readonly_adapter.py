#!/usr/bin/env python3
"""Narrow GET-only native/preflight transfer; no submissions or mutations.

Reuse the unchanged reviewed TLS, pagination, no-redirect/no-proxy, exclusive
partial-file and 16-MiB body implementation. Only this adapter's additional
preflight path classification and UUID-bearing observations are new source.
Private settings are read only by main, never by import.
"""
import argparse
from datetime import datetime, timezone
from email.message import Message
import importlib.util
from pathlib import Path, PurePosixPath
import re
import sys
from urllib import parse

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('galaxy_get_base',
    ROOT / 'tools/m1_evidence/reana_metadata_readonly_adapter.py')
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)


def artifact_path(name):
    fixed = {'outputs/' + n for n in base.ARTIFACTS} | {
        'outputs/execution.json', 'outputs/galaxy-preflight/preflight.json',
        'outputs/galaxy-preflight/commands.json', 'outputs/galaxy-preflight/export.json',
        'outputs/galaxy-preflight/sha256.json'}
    base.ensure(type(name) is str and (name in fixed or re.fullmatch(
        r'outputs/galaxy-preflight/(?:export\.part[0-9]{4}|[a-zA-Z0-9_-]+\.(?:stdout|stderr)|binaries/(?:debug|release)/[a-zA-Z0-9_.-]+)', name)
        or re.fullmatch(r'outputs/logs/[0-9]{2}\.log', name)), 'unsafe_remote_path')
    return name


class Client(base.Client):
    def observe(self, workflow):
        rows = self.matching_rows(workflow)
        return dict(schema='openmhd.galaxy-server-observation.v1', origin='server',
                    observed_utc=datetime.now(timezone.utc).isoformat(), matches=rows), [r['id'] for r in rows]

    def download(self, workflow, path, target):
        artifact_path(path)
        rows = self.matching_rows(workflow)
        base.ensure(len(rows) == 1 and rows[0]['status'] in base.DOWNLOAD_STATES,
                    'ambiguous_missing_or_nonterminal_workflow')
        selected = rows[0]

        def consume(response, headers, length):
            base.ensure(headers.get_content_type() == 'application/octet-stream', 'invalid_artifact_content_type')
            if headers.get('Content-Disposition') is not None:
                message = Message()
                message['Content-Disposition'] = headers['Content-Disposition']
                base.ensure(message.get_content_disposition() == 'attachment'
                    and message.get_filename() in (path, PurePosixPath(path).name), 'artifact_name_mismatch')
            self.stream(response, target.append, length)

        self.get('/api/workflows/' + selected['id'] + '/workspace/' + parse.quote(path, safe='/'), {}, consume)
        base.ensure(self.matching_rows(workflow) == [selected], 'download_workflow_changed')
        return [selected['id']]


def main(argv=None):
    target, client = None, None
    diagnostic = dict(schema='openmhd.galaxy-get-diagnostic.v1', outcome='failure',
        code='initializing', started_utc=datetime.now(timezone.utc).isoformat(),
        action=None, workflow=None, requested_path=None, workflow_ids=[], http_status=None)
    code = 1
    try:
        base.ensure(__debug__ and sys.flags.optimize == 0, 'optimized_rejected')
        parser = base.SafeParser(description=__doc__)
        parser.add_argument('action', choices=('observe', 'download'))
        parser.add_argument('--workflow', required=True)
        parser.add_argument('--path')
        parser.add_argument('--output', type=Path, required=True)
        args = parser.parse_args(argv)
        base.workflow_identity(args.workflow)
        base.ensure((args.action == 'download') == (args.path is not None), 'invalid_arguments')
        if args.path is not None:
            artifact_path(args.path)
        diagnostic.update(action=args.action, workflow=args.workflow, requested_path=args.path)
        target = base.Target(args.output)
        server, token = base.settings_from_private()
        client = Client(server, token)
        if args.action == 'observe':
            value, ids = client.observe(args.workflow)
            target.append(base.json_bytes(value))
        else:
            ids = client.download(args.workflow, args.path, target)
        client.remaining()
        target.publish()
        diagnostic.update(outcome='success', code='completed', workflow_ids=ids)
        code = 0
    except base.AdapterError as error:
        diagnostic.update(code=error.code, http_status=error.http_status)
    except KeyboardInterrupt:
        diagnostic['code'] = 'interrupted'
    except Exception:
        # No exception message, private origin, URL, token or HTTP body is printed.
        diagnostic['code'] = 'local_or_protocol_error'
    finally:
        if target is not None:
            diagnostic.update(received_bytes=target.received, retained_bytes=target.written,
                              partial_file=target.partial if not target.published else None)
            try:
                target.close()
            except OSError:
                code = 1
                diagnostic.update(outcome='failure', code='output_close_failed')
        diagnostic['finished_utc'] = datetime.now(timezone.utc).isoformat()
        diagnostic['page_count'] = client.page_count if client is not None else 0
        (sys.stdout if code == 0 else sys.stderr).write(base.json_bytes(diagnostic).decode())
    return code


if __name__ == '__main__':
    sys.exit(main())
