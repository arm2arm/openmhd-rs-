#!/usr/bin/env python3
"""Freeze source and declare resources for the post-M1 REANA build preflight.

This prepares files only. It neither submits a workflow nor runs a build/test.
The existing source freezer supplies its selected source and archive identities;
this wrapper records the actual derived submission specification in snapshot.json.
"""
import argparse
import hashlib
import json
from pathlib import Path

from prepare_reana import prepare


IMAGE = ('gitlab-p4n.aip.de:5005/p4nreana/reana-env@sha256:'
         'aebd7911df9e1e97ad67d15f4c32ab23996000282183fad3bf7a480756522bd7')
STUDY = 'galaxy-source-preflight'
JOBS = 4
MEMORY = '8Gi'


def encode(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()


def specification(snapshot):
    """Render JSON, a YAML subset, with the exact frozen upload list."""
    files = ['snapshot.json', *sorted(snapshot['upload_sha256'])]
    if len(files) != len(set(files)) or 'remote.py' not in files:
        raise ValueError('Unique complete preflight upload inventory required')
    steps = []
    for name, command in (
            ('prepare-source-and-rust', 'python3 remote.py prepare'),
            ('compile-and-list-without-running-tests',
             'python3 remote.py run --study ' + STUDY + ' --jobs ' + str(JOBS))):
        steps.append({
            'name': name, 'environment': IMAGE, 'compute_backend': 'kubernetes',
            'kubernetes_cpu_request': str(JOBS), 'kubernetes_cpu_limit': str(JOBS),
            'kubernetes_memory_limit': MEMORY, 'commands': [command],
        })
    return {
        'version': '0.9.0', 'inputs': {'files': files},
        'workflow': {'type': 'serial', 'specification': {'steps': steps}},
        'outputs': {'files': [
            'outputs/execution.json', 'outputs/runtime.json',
            'outputs/artifacts.sha256.json',
            'outputs/galaxy-preflight/preflight.json',
            'outputs/galaxy-preflight/commands.json',
            'outputs/galaxy-preflight/export.json',
            'outputs/galaxy-preflight/test-binaries.tar.gz',
            'outputs/galaxy-preflight/sha256.json',
        ]},
    }


def prepare_source(destination):
    # A new destination is mandatory in the underlying freezer. The compact
    # bundle retains the real source_revision separately from its export commit.
    prepare(destination, minimal=True, compact_history=True)
    snapshot_path = destination / 'snapshot.json'
    snapshot = json.loads(snapshot_path.read_bytes())
    workflow_path = destination / 'reana.yaml'
    original = workflow_path.read_bytes()
    original_hash = hashlib.sha256(original).hexdigest()
    if snapshot['workflow_sha256'] != original_hash:
        raise ValueError('Original frozen workflow changed before derivation')
    derived = encode(specification(snapshot))
    workflow_path.write_bytes(derived)
    snapshot.update(
        workflow_sha256=hashlib.sha256(derived).hexdigest(),
        workflow_derivation={
            'schema': 'openmhd.galaxy-build-workflow.v1',
            'base_workflow_sha256': original_hash,
            'study': STUDY, 'build_jobs': JOBS,
            'declared_cpu_request': str(JOBS), 'declared_cpu_limit': str(JOBS),
            'declared_memory_limit': MEMORY,
            'test_methods_to_execute': 0,
            'scope': 'Compile/list prerequisite; component acceptance remains separate',
        },
    )
    # snapshot.json is an original top-level input, never a source-tar member or
    # its own digest. The actual submitted specification is bound here instead.
    snapshot_path.write_bytes(encode(snapshot))
    print('Prepared declared-resource galaxy source preflight at ' + str(destination))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prepare_source(args.output.resolve())


if __name__ == '__main__':
    main()
