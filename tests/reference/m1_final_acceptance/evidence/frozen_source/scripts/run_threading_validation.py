#!/usr/bin/env python3
"""Measure one simulation at 1/4/12/24 threads, then run a complex 24-thread case."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import subprocess
import time

from run_m1_wave_loop import ROOT, dump, read_snapshot, sha

PHYSICAL_FILES = ('initial.csv', 'final.csv', 'summary.json', 'history.json')


def compare_outputs(reference, candidate):
    for name in PHYSICAL_FILES:
        if sha(reference/name) != sha(candidate/name):
            raise ValueError(f'Changed scientific output at {candidate.name}/{name}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--quick', action='store_true', help='N8/N16 execution check only')
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists():
        parser.error('Choose a fresh output directory')
    output.mkdir(parents=True)
    source_paths = sorted({*ROOT.glob('crates/**/*.rs'), *ROOT.glob('apps/**/*.rs'),
                           *ROOT.glob('crates/*/Cargo.toml'), *ROOT.glob('apps/*/Cargo.toml'),
                           ROOT/'Cargo.toml', ROOT/'Cargo.lock', ROOT/'rust-toolchain.toml',
                           Path(__file__).resolve(), ROOT/'scripts/run_m1_wave_loop.py',
                           ROOT/'docs/THREADING_PLAN.md'})
    sources = {str(p.relative_to(ROOT)): sha(p) for p in source_paths}
    cargo = shutil.which('cargo') or str(Path.home()/'.cargo/bin/cargo')
    subprocess.run([cargo, 'build', '--release', '--locked', '-p', 'openmhd', '--bin', 'vector-potential'], cwd=ROOT, check=True)
    binary = ROOT/'target/release/vector-potential'
    provenance = {'created_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': sources,
                  'binary_sha256': sha(binary), 'platform': platform.platform(), 'cpu_count': os.cpu_count(),
                  'cpu_affinity': sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None,
                  'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  'rustc': subprocess.check_output([str(Path(cargo).with_name('rustc')), '-Vv'], text=True),
                  'quick': args.quick, 'concurrent_simulations': 1, 'max_threads_per_simulation': 24,
                  'timing_scope': 'Shared cluster; wall/CPU timings are observations, not isolated-node guarantees.'}
    for name in ('cpu.max', 'memory.max'):
        path = Path('/sys/fs/cgroup')/name
        if path.exists():
            provenance[name] = path.read_text().strip()
    dump(output/'provenance.json', provenance)
    records = {}
    result = {'scaling': [], 'complex': None, 'status': 'running'}

    def run(n, jitter, threads, target, complex_case=False):
        name = f'n{n}_j{jitter}_threads{threads}'+('_complex' if complex_case else '')
        dest = output/name
        dest.mkdir()
        cmd = [str(binary), '--case', 'alfven', '--profile', 'paper-global-v2' if complex_case else 'bulk-frame-signal-v1',
               '--n', str(n), '--jitter', str(jitter), '--threads', str(threads), '--time', str(target),
               '--parallel-velocity', '0' if complex_case else '1', '--motion', 'fixed', '--output', str(dest)]
        if complex_case:
            for t in (.01, .1, .25, .5, .75):
                if t < target:
                    cmd += ['--checkpoint', str(t)]
        else:
            cmd += ['--dt', '.0002']
        print('Starting '+name, flush=True)
        started = time.monotonic()
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        with (dest/'run.log').open('w') as stream:
            completed = subprocess.run(cmd, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        record = {'command': cmd, 'returncode': completed.returncode, 'wall_seconds': time.monotonic()-started,
                  'cpu_seconds': after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
                  'status': 'failed', 'n': n, 'jitter': jitter, 'threads': threads, 'target': target}
        records[name] = record
        dump(output/'runs.json', records)
        if completed.returncode:
            raise ValueError('Evolution failed: '+name)
        summary = json.loads((dest/'summary.json').read_text())
        history = json.loads((dest/'history.json').read_text())
        if not summary['completed'] or summary['time'] != target:
            raise ValueError('Incomplete evolution: '+name)
        read_snapshot(dest/'initial.csv', n, 0.)
        read_snapshot(dest/'final.csv', n, target)
        if not history or any(h['diagnostics']['rho_min'] <= 0 or h['diagnostics']['p_min'] <= 0
                              or max(map(abs, h['diagnostics']['normalized_budget'])) > 1e-10 for h in history):
            raise ValueError('Positivity/conservation failure: '+name)
        record.update(status='completed', summary=summary,
                      timing=json.loads((dest/'timing.json').read_text()),
                      sha256={p.name: sha(p) for p in dest.iterdir() if p.is_file()})
        record['average_cpu_cores'] = record['cpu_seconds']/record['wall_seconds']
        dump(output/'runs.json', records)
        print(f'{name}: {record["wall_seconds"]:.3f} s wall, {record["cpu_seconds"]:.3f} s CPU', flush=True)
        return name, record

    try:
        for n, jitter in ((8 if args.quick else 64, 0.), (16 if args.quick else 128, .15)):
            target = .002 if args.quick else .02
            reference_name, reference = run(n, jitter, 1, target)
            for threads in (4, 12, 24):
                name, record = run(n, jitter, threads, target)
                compare_outputs(output/reference_name, output/name)
                result['scaling'].append({'n': n, 'jitter': jitter, 'threads': threads, 'bit_identical': True,
                    'wall_speedup': reference['wall_seconds']/record['wall_seconds'],
                    'mesh_speedup': reference['timing']['mesh_seconds']/record['timing']['mesh_seconds'],
                    'evolution_speedup': reference['timing']['evolution_seconds']/record['timing']['evolution_seconds']})
                dump(output/'summary.json', result)
        result['complex'], _ = run(16 if args.quick else 256, 0., 24, .01 if args.quick else 1., True)
        if sources != {str(p.relative_to(ROOT)): sha(p) for p in source_paths}:
            raise ValueError('Source changed during execution')
        result['status'] = 'completed'
    except Exception as error:
        result.update(status='failed', error=str(error))
        raise
    finally:
        dump(output/'summary.json', result)
        provenance['result_sha256'] = {name: sha(output/name) for name in ('runs.json', 'summary.json') if (output/name).exists()}
        dump(output/'provenance.json', provenance)


if __name__ == '__main__':
    main()
