#!/usr/bin/env python3
"""REANA-only bounded reproduction using the hash-pinned original Linux binary.

Four original N1024 regular/column Brio runs, two threads each, 600 s per case.
A reproduced known failure is evidence, not a physical acceptance pass.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import sys
import tarfile
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False)+'\n')


def row_variation(cells, nx=1024, ny=4):
    return {field: max(max(cells[i+nx*j][field] for j in range(ny))
                       - min(cells[i+nx*j][field] for j in range(ny)) for i in range(nx))
            for field in ('rho', 'p', 'vx', 'vy', 'bx', 'by')}


def main():
    root = Path.cwd()
    out = root/'outputs'
    out.mkdir(exist_ok=False)
    metadata = json.loads((root/'snapshot.json').read_text())
    report = dict(status='failed', scope=__doc__, started_utc=datetime.now(timezone.utc).isoformat(),
                  snapshot_sha256=sha(root/'snapshot.json'), original_workflow=metadata['original_workflow'],
                  python=sys.version, platform=platform.platform(), runs={}, pairs=[])
    try:
        if sys.platform != 'linux':
            raise ValueError('Run on the REANA Linux backend')
        for name, digest in metadata['input_sha256'].items():
            if sha(root/name) != digest:
                raise ValueError('Changed input: '+name)
        provenance = json.loads((root/'original-provenance.json').read_text())
        source = root/'source'
        source.mkdir()
        seen = set()
        with tarfile.open(root/'execution_sources.tar.gz') as archive:
            for item in archive.getmembers():
                name = PurePosixPath(item.name)
                if (not item.isfile() or name.is_absolute() or '..' in name.parts
                    or item.name in seen or item.name not in provenance['source_sha256']):
                    raise ValueError('Unexpected source member')
                data = archive.extractfile(item).read()
                if hashlib.sha256(data).hexdigest() != provenance['source_sha256'][item.name]:
                    raise ValueError('Source hash differs: '+item.name)
                dest = source/item.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                seen.add(item.name)
        if seen != set(provenance['source_sha256']):
            raise ValueError('Incomplete execution source export')
        binary = root/'vector-potential'
        with binary.open('wb') as stream:
            for name in metadata['binary_parts']:
                stream.write((root/name).read_bytes())
        if sha(binary) != provenance['binary_sha256']:
            raise ValueError('Original binary hash differs')
        binary.chmod(0o755)
        report['binary_sha256'] = sha(binary)
        sys.path.insert(0, str(source/'scripts'))
        from run_m1_wave_loop import read_cells
        from run_m1_physics import boost_comparison, validate_run
        original = json.loads(gzip.decompress((root/'original-runs.json.gz').read_bytes()))
        names = [f'brio-wu_n1024_j{mesh}_{frame}' for mesh in ('0.0', '0.15c')
                 for frame in ('base', 'boost')]
        env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
                   RAYON_NUM_THREADS='1', LC_ALL='C')
        for name in ('cpu.max', 'memory.max'):
            p = Path('/sys/fs/cgroup')/name
            if p.exists():
                report.setdefault('cgroup', {})[name] = p.read_text().strip()

        def run(name):
            old = original[name]
            dest = out/name
            dest.mkdir()
            command = list(old['command'])
            command[0] = str(binary)
            command[command.index('--output')+1] = str(dest)
            if command[command.index('--threads')+1] != '2':
                raise ValueError('Expected original two-thread configuration')
            row = dict(status='failed', config=old['config'], command=command, timeout_seconds=600)
            start = time.monotonic()
            try:
                with (dest/'run.log').open('w') as log:
                    done = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=600)
                if done.returncode:
                    raise ValueError('Evolution return code '+str(done.returncode))
                load = lambda name: json.loads((dest/name).read_text())
                summary, history = load('summary.json'), load('history.json')
                initial, final = read_cells(dest/'initial.csv'), read_cells(dest/'final.csv')
                validate_run(old['config'], summary, history, load('physics.json'), load('geometry.json'), initial, final)
                physical = ('initial.csv', 'final.csv', 'history.json', 'summary.json', 'geometry.json', 'physics.json')
                matches = {file: sha(dest/file) == old['sha256'][file] for file in physical}
                row.update(status='completed', scientific_file_parity=matches,
                           initial_row_variation=row_variation(initial), final_row_variation=row_variation(final),
                           positive_and_conservative=all(h['diagnostics']['rho_min'] > 0
                               and h['diagnostics']['p_min'] > 0
                               and max(map(abs, h['diagnostics']['normalized_budget'])) <= 1e-10 for h in history))
            except (ValueError, KeyError, OSError, subprocess.TimeoutExpired) as error:
                row['error'] = f'{type(error).__name__}: {error}'
            row['seconds'] = time.monotonic()-start
            row['sha256'] = {p.name: sha(p) for p in sorted(dest.iterdir()) if p.is_file()}
            return name, row

        with ThreadPoolExecutor(max_workers=4) as pool:
            for future in as_completed([pool.submit(run, name) for name in names]):
                name, row = future.result()
                report['runs'][name] = row
                dump(out/'report.json', report)
                print(name, row['status'], row['seconds'], flush=True)
        if any(r['status'] != 'completed' or not r['positive_and_conservative']
               or not all(r['scientific_file_parity'].values()) for r in report['runs'].values()):
            raise ValueError('Execution/state check or original scientific-file parity failed')
        for mesh in ('0.0', '0.15c'):
            a, b = (f'brio-wu_n1024_j{mesh}_{frame}' for frame in ('base', 'boost'))
            summary = json.loads((out/a/'summary.json').read_text())
            pair = boost_comparison(read_cells(out/a/'final.csv'), read_cells(out/b/'final.csv'),
                                    original[a]['config'], summary)
            report['pairs'].append(dict(names=[a, b], **pair))
        reproduced = report['pairs'][0]['passed'] and not report['pairs'][1]['passed']
        if not reproduced:
            raise ValueError('Original pass/failure pattern was not reproduced')
        report.update(status='completed', reproduced_known_column_boost_failure=True,
                      scientific_acceptance=False, total_worker_threads=8)
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
    finally:
        report['ended_utc'] = datetime.now(timezone.utc).isoformat()
        dump(out/'report.json', report)
        dump(out/'sha256.json', {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    return 0 if report['status'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
