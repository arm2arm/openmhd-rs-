#!/usr/bin/env python3
"""REANA-only bounded reproduction using the hash-pinned original Linux binary.

Four original N1024 regular/column Brio runs, two threads each, 600 s per case.
A reproduced known failure is evidence, not a physical acceptance pass.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import csv
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


def alternating(values, nx):
    if len(values) != 4*nx:
        raise ValueError('Alternating-row diagnostic requires exactly four rows')
    return [((values[i]-values[i+nx])+(values[i+2*nx]-values[i+3*nx]))/4
            for i in range(nx)]


def growth_measurement(state, rates, nx):
    """Volume-weighted instantaneous logarithmic growth of the measured mode.

    No claim of an eigenvalue: coefficients are evaluated on a nonlinear,
    time-dependent shock. A zero mode has no defined relative growth rate.
    """
    if len(state) != len(rates):
        raise ValueError('Rate/state size mismatch')
    modes = {field: alternating([row[field] for row in state], nx)
             for field in ('rho', 'vx', 'by', 'reduced_az')}
    weights = [sum(state[i+nx*j]['volume'] for j in range(4)) for i in range(nx)]
    observations = {}
    for field, components in (
        ('rho', ('fluid_rho', 'fluid_x_rho', 'fluid_y_rho')),
        ('vx', ('fluid', 'fluid_x', 'fluid_y')),
        ('by', ('curl_y', 'fv_y', 'unprojected_y')),
        ('reduced_az', ('potential_z', 'potential_unprojected_z')),
    ):
        values = modes[field]
        square = sum(w*a*a for w, a in zip(weights, values))
        record = dict(volume_weighted_mode_square=square, rates={})
        for component in components:
            if field == 'vx':
                derivative = [(r[component+'_mx']-s['vx']*r[component+'_rho'])/s['rho']
                              for s, r in zip(state, rates)]
            else:
                derivative = [r[component] for r in rates]
            change = alternating(derivative, nx)
            product = sum(w*a*b for w, a, b in zip(weights, values, change))
            record['rates'][component] = dict(
                max_abs=max(map(abs, change)), mode_rate_inner_product=product,
                logarithmic_growth=product/square if square > 0 else None)
        observations[field] = record
    return observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, help='Optional instrumented binary; original science files must still match')
    parser.add_argument('--snapshot-stride', type=int)
    parser.add_argument('--trace-frozen-rates', action='store_true')
    parser.add_argument('--output-dir', type=Path, default=Path('outputs'))
    args = parser.parse_args()
    if args.snapshot_stride is not None and (args.snapshot_stride <= 0 or args.binary is None):
        parser.error('A positive snapshot stride requires an instrumented binary')
    if args.trace_frozen_rates and args.snapshot_stride is None:
        parser.error('Frozen rates require stride snapshots')
    root = Path.cwd()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
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
        source = root/'original-source'
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
        binary = root/'original-vector-potential'
        with binary.open('wb') as stream:
            for name in metadata['binary_parts']:
                stream.write((root/name).read_bytes())
        if sha(binary) != provenance['binary_sha256']:
            raise ValueError('Original binary hash differs')
        binary.chmod(0o755)
        report['binary_sha256'] = sha(binary)
        if args.binary is not None:
            binary = args.binary.resolve()
            report['instrumented_binary_sha256'] = sha(binary)
        report['snapshot_stride'] = args.snapshot_stride
        report['trace_frozen_rates'] = args.trace_frozen_rates
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
            if args.snapshot_stride is not None:
                command += ['--snapshot-stride', str(args.snapshot_stride)]
            if args.trace_frozen_rates:
                command += ['--trace-frozen-rates']
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
                if args.snapshot_stride is not None:
                    files = sorted(p for p in dest.glob('accepted_*.csv') if p.stem[9:].isdigit())
                    expected_steps = sorted({1, *range(args.snapshot_stride, summary['steps']+1, args.snapshot_stride)})
                    if [int(p.stem.split('_')[1]) for p in files] != expected_steps:
                        raise ValueError('Accepted snapshot cadence differs')
                    history = []
                    for path in [dest/'initial.csv', *files, dest/'final.csv']:
                        with path.open() as stream:
                            data = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(stream)]
                        if len(data) != 4096 or [r['id'] for r in data] != list(range(4096)):
                            raise ValueError('Unexpected snapshot row ordering')
                        fields = ('rho', 'p', 'vx', 'vy', 'bx', 'by', 'reduced_az', 'phi', 'energy')
                        modes = {}
                        for field in fields:
                            # Baseline-subtracted four-row Nyquist coefficient;
                            # the uniform-row component cancels before summation.
                            alt = alternating([r[field] for r in data], 1024)
                            index = max(range(1024), key=lambda i: abs(alt[i]))
                            modes[field] = dict(max_abs=max(map(abs, alt)), column=index,
                                                x=data[index]['x'], signed=alt[index],
                                                l1=sum(map(abs, alt))/1024)
                        history.append(dict(file=path.name, sha256=sha(path), time=data[0]['time'],
                                            row_variation=row_variation(data), alternating=modes))
                        if args.trace_frozen_rates:
                            rate_path = path.with_name(path.stem+'_rates.csv')
                            with rate_path.open() as stream:
                                rates = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(stream)]
                            if len(rates) != 4096 or any(r['id'] != s['id'] or r['time'] != s['time']
                                                       for r, s in zip(rates, data)):
                                raise ValueError('Mismatched frozen rates')
                            history[-1]['frozen_rates'] = dict(
                                sha256=sha(rate_path), file=rate_path.name,
                                growth=growth_measurement(data, rates, 1024))
                    dump(dest/'row_modes.json', history)
                    row['observed_snapshots'] = len(files)
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
