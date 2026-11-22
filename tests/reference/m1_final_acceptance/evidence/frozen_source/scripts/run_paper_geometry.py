#!/usr/bin/env python3
"""Bounded observational geometry controls; never changes or awards M1 gates."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--pattern-controls', action='store_true',
                        help='Repeat/compress the exact original four-row pattern; includes face audits')
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists():
        parser.error('Use a fresh output directory')
    output.mkdir(parents=True)
    paths = sorted({*ROOT.glob('crates/**/*.rs'), *ROOT.glob('apps/**/*.rs'),
                    *ROOT.glob('crates/*/Cargo.toml'), *ROOT.glob('apps/*/Cargo.toml'),
                    ROOT/'Cargo.toml', ROOT/'Cargo.lock', ROOT/'rust-toolchain.toml',
                    Path(__file__).resolve(), ROOT/'docs/M1_SHOCK_INVESTIGATION.md'})
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    with tarfile.open(output/'source.tar.gz', 'w:gz') as archive:
        for p in paths:
            archive.add(p, arcname=str(p.relative_to(ROOT)))
    cargo = shutil.which('cargo') or str(Path.home()/'.cargo/bin/cargo')
    subprocess.run([cargo, 'build', '--release', '--locked', '-p', 'mhd-vector-pot',
                    '--example', 'paper-shock-geometry', '--example', 'paper-shock-audit'], cwd=ROOT, check=True)
    binary = ROOT/'target/release/examples/paper-shock-geometry'
    audit_binary = ROOT/'target/release/examples/paper-shock-audit'
    if args.pattern_controls:
        configs = [dict(name=name, nx=256, ny=4, jitter=.15, end=.01,
                        height=height, copies=copies, box=[2., height*copies])
                   for name, height, copies in [
                       ('original', .125, 1), ('repeat2', .125, 2), ('repeat4', .125, 4),
                       ('compressed2', .0625, 1), ('compressed4', .03125, 1),
                       ('compressed4_repeat4', .03125, 4)]]
    else:
        configs = [dict(name=f'n{nx}_ny{ny}_j{jitter}_t{end}', nx=nx, ny=ny, jitter=jitter,
                        end=end, box=[2., .125]) for nx, ny, jitter, end in [
            (64, 4, .15, .01), (128, 4, .15, .01), (256, 4, .15, .01),
            (256, 8, .15, .01), (256, 16, .15, .01),
            (64, 4, .15, .04), (128, 4, .15, .02), (256, 16, 0., .01)]]
    provenance = dict(created_utc=datetime.now(timezone.utc).isoformat(),
                      revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                      source_sha256=hashes, source_archive_sha256=sha(output/'source.tar.gz'),
                      binary_sha256=sha(binary), audit_binary_sha256=sha(audit_binary), configs=configs, jobs=3,
                      threads_per_case=1, timeout_seconds=30,
                      profile='paper-state-emf-v1', motion='fixed',
                      pattern_controls=args.pattern_controls, gamma=2., mean_B=[.75, 0., 0.])
    dump(output/'provenance.json', provenance)

    def run(config):
        name = config['name']
        destination = output/name
        command = [str(binary), *(str(config[k]) for k in ['nx', 'ny', 'jitter', 'end']), str(destination)]
        if args.pattern_controls:
            command += ['--pattern-height', str(config['height']), '--repeat', str(config['copies'])]
        record = dict(config=config, command=command)
        started = time.monotonic()
        try:
            with (output/f'{name}.log').open('w') as log:
                done = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=30)
            record['returncode'] = done.returncode
            status = dict(line.split('=', 1) for line in (destination/'status.txt').read_text().splitlines())
            record.update(status='completed' if done.returncode == 0 and status['completed'] == 'true' else 'failed',
                          reported_status=status)
            if (destination/'failure.txt').exists():
                record['error'] = (destination/'failure.txt').read_text()
            if args.pattern_controls:
                audit_command = [str(audit_binary), str(destination/'face_audit'),
                                 str(config['height']), str(config['copies'])]
                record['audit_command'] = audit_command
                remaining = max(.01, 30-(time.monotonic()-started))
                with (destination/'audit.log').open('w') as log:
                    audit = subprocess.run(audit_command, cwd=ROOT, stdout=log,
                                           stderr=subprocess.STDOUT, timeout=remaining)
                record['audit_returncode'] = audit.returncode
        except subprocess.TimeoutExpired:
            record.update(status='timeout', error='External 30-second cap; incomplete')
        except (OSError, ValueError, KeyError) as error:
            record.update(status='failed', error=str(error))
        record['seconds'] = time.monotonic()-started
        record['files_sha256'] = {str(p.relative_to(destination)): sha(p) for p in destination.rglob('*') if p.is_file()}
        return name, record

    runs = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for future in as_completed([pool.submit(run, c) for c in configs]):
            name, record = future.result()
            runs[name] = record
            dump(output/'runs.json', runs)
            print(name, record['status'], record.get('reported_status', {}).get('time'), flush=True)
    unchanged = (hashes == {str(p.relative_to(ROOT)): sha(p) for p in paths}
                 and sha(binary) == provenance['binary_sha256']
                 and sha(audit_binary) == provenance['audit_binary_sha256'])
    audits_complete = (not args.pattern_controls or
                       all(r.get('audit_returncode') == 0 for r in runs.values()))
    dump(output/'summary.json', dict(
        scope='Geometry observations only; no registered benchmark/gate changes or M1 acceptance.',
        recorded=len(runs), completed=sum(r['status'] == 'completed' for r in runs.values()),
        failed=sum(r['status'] == 'failed' for r in runs.values()),
        timed_out=sum(r['status'] == 'timeout' for r in runs.values()),
        face_audits_complete=audits_complete,
        source_and_binary_unchanged=unchanged, full_m1_accepted=False))
    print('Observations recorded; physical acceptance not evaluated.')
    return 0 if unchanged and audits_complete and len(runs) == len(configs) else 1


if __name__ == '__main__':
    raise SystemExit(main())
