#!/usr/bin/env python3
"""Bounded planar-jitter mesh scan of the short Brio shock; diagnostic only.

Records where the literal paper profile loses positive pressure as the cell
aspect ratio, resolution and jitter amplitude change, and whether the projected
candidate survives the same meshes. It defines no gate and accepts nothing.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import math
from pathlib import Path
import shutil
import subprocess
import time

from run_m1_physics import load_json
from run_m1_wave_loop import ROOT, dump, read_cells, sha
from run_shock_symmetry import CANDIDATE, LITERAL, bx_errors

TIME = .02


def configurations():
    """(profile, nx, ny, jitter); the box is [0,2] x [0,1/8], so dy/dx = nx/(16 ny)."""
    cases = [(LITERAL, nx, ny, .15) for nx, ny in (
        (64, 4), (128, 4), (256, 4), (512, 4),      # registered ny=4 ladder: dy/dx 1, 2, 4, 8
        (128, 8), (192, 12), (256, 16), (320, 20), (384, 24),  # isotropic generators
        (256, 8), (512, 8), (512, 16))]             # intermediate aspect ratios
    cases += [(LITERAL, 256, 4, j) for j in (.03, .06, .1)]
    cases += [(LITERAL, 512, 4, j) for j in (.05, .1)]
    cases += [(CANDIDATE, nx, ny, .15) for nx, ny in ((256, 4), (512, 4), (512, 8))]
    return [dict(name=f'{p}_nx{nx}_ny{ny}_j{j}', profile=p, n=nx, ny=ny, jitter=j,
                 aspect_dy_over_dx=nx/(16*ny), time=TIME) for p, nx, ny, j in cases]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=3)
    parser.add_argument('--timeout', type=float, default=60.)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 4: parser.error('jobs must be 1..4')
    if not math.isfinite(args.timeout) or not 0 < args.timeout <= 60:
        parser.error('timeout must be in (0,60] seconds')
    output = args.output_dir.resolve()
    if output.exists(): parser.error('Use a fresh output directory')
    output.mkdir(parents=True)
    cargo = shutil.which('cargo') or str(Path.home()/'.cargo/bin/cargo')
    subprocess.run([cargo, 'build', '--release', '--locked', '-p', 'openmhd', '--bin', 'vector-potential'],
                   cwd=ROOT, check=True)
    binary = ROOT/'target/release/vector-potential'
    provenance = dict(
        created_utc=datetime.now(timezone.utc).isoformat(), binary_sha256=sha(binary),
        revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        worktree_dirty=bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),
        jobs=args.jobs, threads_per_case=1, timeout_seconds=args.timeout,
        scope='Diagnostic scan; rest frame, planar jitter, t=.02; no gate and no acceptance')

    def run(c):
        dest = output/c['name']
        command = [str(binary), '--case', 'brio-wu', '--profile', c['profile'], '--n', str(c['n']),
                   '--ny', str(c['ny']), '--jitter', str(c['jitter']), '--time', str(c['time']),
                   '--motion', 'rigid', '--output', str(dest)]
        if c['profile'] == CANDIDATE: command += ['--accelerated-projection']
        row = dict(c, command=command, status='failed'); start = time.monotonic()
        try:
            done = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=args.timeout)
            summary = load_json(dest/'summary.json')
            initial = read_cells(dest/'initial.csv')
            row.update(returncode=done.returncode, time_reached=summary['time'], steps=summary['steps'],
                       rejected_state=summary['rejected_state'], initial_bx_error=bx_errors(initial))
            if summary['completed'] and not done.returncode:
                history = load_json(dest/'history.json')
                row.update(status='completed', final_bx_error=bx_errors(read_cells(dest/'final.csv')),
                           p_min=min(h['diagnostics']['p_min'] for h in history),
                           budget_max=max(max(map(abs, h['diagnostics']['normalized_budget'])) for h in history))
            else:
                failure = dest/'failure.txt'
                row['error'] = failure.read_text() if failure.exists() else 'failed evolution'
        except subprocess.TimeoutExpired:
            row.update(status='timeout', error='Wall-time cap reached; incomplete execution')
        except (OSError, ValueError, KeyError) as error:
            row['error'] = str(error)
        row['seconds'] = time.monotonic()-start
        # Keep the small records, not the snapshots.
        row['files_sha256'] = {p.name: sha(p) for p in sorted(dest.iterdir()) if p.is_file()} if dest.exists() else {}
        for p in (dest.iterdir() if dest.exists() else ()):
            if p.suffix == '.csv' or p.name in ('geometry.json', 'history.json'): p.unlink()
        return row

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        rows = list(pool.map(run, configurations()))
    provenance['binary_unchanged'] = sha(binary) == provenance['binary_sha256']
    dump(output/'scan.json', dict(provenance=provenance, rows=rows))
    for r in rows:
        bx = r.get('final_bx_error', r.get('initial_bx_error', {}))
        print(f'{r["name"]:48} dy/dx={r["aspect_dy_over_dx"]:<4g} {r["status"]:9} t={r.get("time_reached", float("nan")):.6g} '
              f'p_min={r.get("p_min", float("nan")):.4g} Bx max/L1={bx.get("max", float("nan")):.3g}/{bx.get("L1", float("nan")):.3g} '
              f'{r["seconds"]:.1f}s')
    return 0


if __name__ == '__main__': raise SystemExit(main())
