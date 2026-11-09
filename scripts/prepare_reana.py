#!/usr/bin/env python3
"""Freeze the current source (including uncommitted work) for REANA upload."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = {'apps', 'crates', 'scripts', 'tests', 'benchmarks', 'docs',
               'examples', 'codex', 'reana', '.github'}
ROOT_FILES = {'Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml', 'README.md',
              'AGENTS.md', 'LICENSE', 'CONTRIBUTING.md', '.gitignore', 'reana.yaml'}
STUDY_EVIDENCE = ('m1_completion', 'm1_heun', 'm1_auxiliary', 'm1_physics_probe', 'm1_shock_diagnosis', 'm1_face_normal_probe', 'm1_projected_rate', 'm1_curl_audit', 'm1_quadratic_curl', 'm1_paper_audit', 'm1_paper_coupling', 'm1_pattern_controls', 'threading_scaling', 'threading_completion')


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def allowed(name):
    p = PurePosixPath(name)
    return (not p.is_absolute() and '..' not in p.parts and
            (name in ROOT_FILES or p.parts[0] in DIRECTORIES) and
            not any(part.startswith('.env') or part in {'__pycache__', '.git'} for part in p.parts) and
            p.suffix not in {'.pyc', '.pem', '.key'})


def prepare(destination, minimal=False):
    if destination.exists():
        raise ValueError('Use a fresh submission directory; previous snapshots are immutable.')
    git = lambda *args: subprocess.check_output(['git', *args], cwd=ROOT)
    names = sorted(set(git('ls-files', '--cached', '--others', '--exclude-standard', '-z').decode().split('\0')) - {''})
    paths = []
    for name in names:
        if not allowed(name):
            continue
        if minimal and any(name.startswith('tests/reference/'+part+'/') for part in STUDY_EVIDENCE):
            continue
        p = ROOT / name
        if p.is_symlink():
            raise ValueError(f'Symlinks are not accepted in source uploads: {name}')
        if p.is_file():
            paths.append((name, p))
    sources = {name: sha(p) for name, p in paths}
    destination.mkdir(parents=True)
    subprocess.run(['git', 'bundle', 'create', str(destination/'source.bundle'), 'HEAD'], cwd=ROOT, check=True)
    with tarfile.open(destination/'source.tar.gz', 'w:gz') as tar:
        for name, p in paths:
            tar.add(p, arcname=name, recursive=False)
    if sources != {name: sha(p) for name, p in paths}:
        raise ValueError('Source changed while creating the snapshot; create a new submission.')
    shutil.copyfile(ROOT/'reana/remote.py', destination/'remote.py')
    archives = {}
    workflow = (ROOT/'reana.yaml').read_text()
    for archive in ('source.tar.gz', 'source.bundle'):
        parts = []
        with (destination/archive).open('rb') as stream:
            while True:
                data = stream.read(1024 * 1024)
                if not data:
                    break
                name = f'{archive}.part{len(parts):03d}'
                (destination/name).write_bytes(data)
                parts.append(name)
        archives[archive] = {'parts': parts, 'sha256': sha(destination/archive)}
        workflow = workflow.replace('    - '+archive+'.part000',
                                    '\n'.join('    - '+name for name in parts))
    (destination/'reana.yaml').write_text(workflow)
    metadata = {'created_utc': datetime.now(timezone.utc).isoformat(),
                'revision': git('rev-parse', 'HEAD').decode().strip(),
                'dirty_status': git('status', '--short').decode(),
                'source_sha256': sources,
                'upload_sha256': {name: sha(destination/name) for name in
                                  ['remote.py', *(n for a in archives.values() for n in a['parts'])]},
                'archives': archives,
                'workflow_sha256': sha(destination/'reana.yaml'),
                'omitted_existing_m1_completion_results': minimal,
                'omitted_existing_study_evidence': list(STUDY_EVIDENCE) if minimal else [],
                'scope': 'Exact selected working files and required test references; local raw results excluded.'}
    (destination/'snapshot.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(f'Prepared {len(sources)} source files at {destination}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--minimal', action='store_true',
                        help='Omit existing M1 study outputs; retain source and references required by tests')
    args = parser.parse_args()
    prepare(args.output.resolve(), args.minimal)


if __name__ == '__main__':
    main()
