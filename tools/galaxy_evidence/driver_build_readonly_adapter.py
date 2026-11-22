#!/usr/bin/env python3
"""GET-only standalone-build metadata/one-MiB parts; no workflow mutation.

Unadopted purpose adapter. It supplies no build verdict, binary reassembly,
acquisition/offline verifier, numerical evaluation or candidate execution.
"""
import hashlib
import importlib.util
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
DEPENDENCIES = {
    'tools/galaxy_evidence/readonly_adapter.py':
        'c8986e20c1cc08cd9689387ead5ee5fd9c05653c469e16bcceae0fae2afe4591',
    'tools/m1_evidence/reana_metadata_readonly_adapter.py':
        '09a7f0cbaaa657eb6d84668dced7693c57c9784e78135adc86e72737ded79c4a',
}
PREFIX = 'outputs/galaxy-driver-build/'
FIXED = frozenset(['outputs/runtime.json', *[PREFIX + name for name in
    ('build.json', 'runtime.json', 'export.json', 'files.sha256.json',
     'export.failed.json', 'files.failed.sha256.json')],
    *[PREFIX + command + '/' + name for command in ('compiler', 'geometry', 'gravity')
      for name in ('command.json', 'stdout.txt', 'stderr.txt')]])
PART = re.compile(r'outputs/galaxy-driver-build/parts/(geometry|gravity)\.part([0-9]{4})')

for name, expected in DEPENDENCIES.items():
    path = ROOT / name
    if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise RuntimeError('Standalone-build transport dependency changed')
SPEC = importlib.util.spec_from_file_location('standalone_build_get_base',
    ROOT / 'tools/galaxy_evidence/readonly_adapter.py')
native = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(native)


def artifact_path(name):
    native.base.ensure(type(name) is str, 'unsafe_remote_path')
    match = PART.fullmatch(name)
    native.base.ensure(name in FIXED or (match is not None and int(match.group(2)) < 512),
                       'unsafe_remote_path')
    return name


# The unchanged native CLI and Client.download both resolve the same module
# global at call time. Raw binaries are intentionally excluded: the inherited
# 16-MiB response cap remains unchanged; opaque exports use one-MiB parts.
native.artifact_path = artifact_path


def main(argv=None):
    return native.main(argv)


if __name__ == '__main__':
    sys.exit(main())
