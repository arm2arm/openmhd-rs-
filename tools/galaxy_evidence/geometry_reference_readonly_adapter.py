#!/usr/bin/env python3
"""Proposed fixed-path reference GET adapter; transport algorithms unchanged.

Prospective canonical path: tools/galaxy_evidence/geometry_reference_readonly_adapter.py.
Import reads pinned public source only; configuration/network is accessed by main.
"""
import hashlib
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
DEPENDENCIES = {
    'tools/galaxy_evidence/readonly_adapter.py':
        'c8986e20c1cc08cd9689387ead5ee5fd9c05653c469e16bcceae0fae2afe4591',
    'tools/m1_evidence/reana_metadata_readonly_adapter.py':
        '09a7f0cbaaa657eb6d84668dced7693c57c9784e78135adc86e72737ded79c4a',
}
ARTIFACTS = frozenset(('outputs/result.json', 'outputs/runtime.json', 'outputs/command.json',
                       'outputs/stdout.txt', 'outputs/stderr.txt', 'outputs/artifacts.sha256.json',
                       'outputs/reference/input.json', 'outputs/reference/reference.json',
                       'outputs/reference/status.json', 'outputs/reference/sha256.json'))
for relative, expected in DEPENDENCIES.items():
    path = ROOT / relative
    if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise RuntimeError('Reference transport source dependency changed')
SPEC = importlib.util.spec_from_file_location('geometry_reference_get_base',
    ROOT / 'tools/galaxy_evidence/readonly_adapter.py')
native = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(native)


def artifact_path(name):
    native.base.ensure(type(name) is str and name in ARTIFACTS, 'unsafe_remote_path')
    return name


# Both the native CLI argument check and Client.download resolve this module
# global at call time. Only the exact path classifier changes, not HTTP/TLS,
# pagination, credential handling, file publication or deadline behavior.
native.artifact_path = artifact_path


def main(argv=None):
    return native.main(argv)


if __name__ == '__main__':
    sys.exit(main())
