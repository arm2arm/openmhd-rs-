#!/usr/bin/env python3
"""Add one pinned binary to a prepared REANA snapshot directory as a checked input.

The file is split into 1 MiB parts and registered in snapshot.json exactly like
the source archives, so `remote.py prepare` reassembles it in the workspace as
`<name>` and verifies every part and the whole. Used for before/after
comparisons that need a baseline executable next to the new build.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

PART = 1024*1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def add(directory, name, binary):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,40}', name):
        raise ValueError('Use a short lowercase input name')
    metadata_file = directory/'snapshot.json'
    workflow_file = directory/'reana.yaml'
    metadata = json.loads(metadata_file.read_text())
    if name in metadata['archives']:
        raise ValueError('Input already registered')
    data = binary.read_bytes()
    if not data:
        raise ValueError('Empty binary')
    parts = []
    for offset in range(0, len(data), PART):
        part = f'{name}.part{len(parts):03d}'
        (directory/part).write_bytes(data[offset:offset+PART])
        metadata['upload_sha256'][part] = sha(data[offset:offset+PART])
        parts.append(part)
    metadata['archives'][name] = {'parts': parts, 'sha256': sha(data)}
    workflow = workflow_file.read_text()
    anchor = '    - snapshot.json\n'
    if workflow.count(anchor) != 1:
        raise ValueError('Unexpected workflow input list')
    workflow = workflow.replace(anchor, ''.join(f'    - {part}\n' for part in parts)+anchor)
    workflow_file.write_text(workflow)
    metadata['workflow_sha256'] = sha(workflow.encode())
    metadata.setdefault('added_inputs', {})[name] = {'sha256': sha(data), 'bytes': len(data)}
    metadata_file.write_text(json.dumps(metadata, indent=2)+'\n')
    return metadata['archives'][name]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path, help='output of prepare_reana.py, not yet submitted')
    parser.add_argument('name', help='workspace file name, for example baseline-vector-potential')
    parser.add_argument('binary', type=Path)
    args = parser.parse_args()
    record = add(args.directory.resolve(), args.name, args.binary.resolve())
    print(f"{args.name}: {len(record['parts'])} parts, sha256 {record['sha256']}")


if __name__ == '__main__':
    main()
