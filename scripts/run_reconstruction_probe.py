#!/usr/bin/env python3
"""Frozen reconstruction diagnostics; no evolution or M1 acceptance."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists():
        parser.error('Use a fresh output directory')
    output.mkdir(parents=True)
    paths = sorted({*ROOT.glob('crates/**/*.rs'), *ROOT.glob('apps/**/*.rs'),
                    *ROOT.glob('crates/*/Cargo.toml'), *ROOT.glob('apps/*/Cargo.toml'),
                    ROOT/'Cargo.toml', ROOT/'Cargo.lock', ROOT/'rust-toolchain.toml',
                    Path(__file__).resolve(), ROOT/'docs/M1_SHOCK_INVESTIGATION.md'})
    sources = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    with tarfile.open(output/'source.tar.gz', 'w:gz') as archive:
        for p in paths:
            archive.add(p, arcname=str(p.relative_to(ROOT)), recursive=False)
    cargo = shutil.which('cargo') or str(Path.home()/'.cargo/bin/cargo')
    subprocess.run([cargo, 'build', '--release', '--locked', '-p', 'mhd-vector-pot',
                    '--example', 'paper-shock-audit'], cwd=ROOT, check=True)
    binary = ROOT/'target/release/examples/paper-shock-audit'
    command = [str(binary), str(output/'data'), '--reconstruction-controls']
    record = dict(created_utc=datetime.now(timezone.utc).isoformat(), command=command,
                  revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=sources, source_archive_sha256=sha(output/'source.tar.gz'),
                  binary_sha256=sha(binary), timeout_seconds=30, threads=1,
                  full_m1_accepted=False, evolved=False)
    start = time.monotonic()
    try:
        with (output/'run.log').open('w') as log:
            done = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=30)
        record.update(returncode=done.returncode, completed=done.returncode == 0)
    except subprocess.TimeoutExpired:
        record.update(completed=False, error='30-second cap reached')
    record['seconds'] = time.monotonic()-start
    record['unchanged'] = (sources == {str(p.relative_to(ROOT)): sha(p) for p in paths}
                           and record['binary_sha256'] == sha(binary))
    record['files_sha256'] = {str(p.relative_to(output)): sha(p)
                              for p in output.rglob('*') if p.is_file()}
    (output/'provenance.json').write_text(json.dumps(record, indent=2, allow_nan=False)+'\n')
    print(f'Frozen probe completed={record["completed"]}; unchanged={record["unchanged"]}; {record["seconds"]:.3f}s')
    return 0 if record['completed'] and record['unchanged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
