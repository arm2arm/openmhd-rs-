#!/usr/bin/env python3
"""Bounded mesh-symmetry controls for the Brio shock; never full M1 acceptance.

Separates a nonuniform mesh from a mesh that breaks the y-invariance of the
problem. Every case keeps the M0 positivity, budget, seam-isolation and
joint-boost gates. Bx <= 1e-8 is gated on the y-invariant column mesh and is a
recorded diagnostic on planar jitter (benchmarks/m1/shock-bx-amendment.json).
Known failures stay failures: the screen exits 0 only if every gate passes.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import math
from pathlib import Path
import shutil
import subprocess
import tarfile
import time

from physics_projection import polygons, shock_errors
from run_m1_physics import AMENDMENT, BOOST, boost_comparison, bx_gate, load_json, reference, validate_run
from run_m1_wave_loop import ROOT, dump, read_cells, sha

LITERAL = 'paper-global-v2'
CANDIDATE = 'bulk-frame-heun-quadratic-v1'
# Registered before execution; a mismatch is reported, never silently accepted.
EXPECTATIONS = {
    ('columns', LITERAL): 'pass: y-invariant nonuniform mesh, all gates including Bx',
    ('columns', CANDIDATE): 'pass: y-invariant nonuniform mesh, all gates including Bx',
    ('planar', LITERAL): 'known failure #20: loses positive pressure near t=.0034',
    ('planar', CANDIDATE): 'pass: positive, conservative and boost-consistent; Bx recorded as a diagnostic',
}


def configurations():
    configs = {}
    for mode in ('columns', 'planar'):
        for profile in (LITERAL, CANDIDATE):
            for label, boost in (('base', (0., 0., 0.)), ('boost', BOOST)):
                name = f'{mode}_{profile}_{label}'
                configs[name] = dict(
                    name=name, case='brio-wu', n=256, ny=4, jitter=.15, jitter_mode=mode,
                    boost=list(boost), time=.1, profile=profile,
                    accelerated_projection=profile == CANDIDATE,
                    expectation=EXPECTATIONS[mode, profile])
    return configs


def bx_errors(cells):
    volume = math.fsum(c['volume'] for c in cells)
    return dict(max=max(abs(c['bx']-.75) for c in cells),
                L1=math.fsum(c['volume']*abs(c['bx']-.75) for c in cells)/volume)


def assess(configs, runs, pairs):
    """Gates per mesh family and profile; incomplete runs never pass."""
    groups = []
    for mode in ('columns', 'planar'):
        for profile in (LITERAL, CANDIDATE):
            names = [n for n, c in configs.items()
                     if c['jitter_mode'] == mode and c['profile'] == profile]
            records = [runs.get(n, {}) for n in names]
            complete = len(names) == 2 and all(r.get('status') == 'completed' for r in records)
            stability = complete and all(r['positive_and_conservative'] for r in records)
            pair = [p for p in pairs if p['names'] == names]
            boost = len(pair) == 1 and pair[0]['status'] == 'pass'
            seam = complete and all(r['diagnostic_checks']['seam'] for r in records)
            # 'diagnostic' means the amended rule does not gate Bx on this mesh.
            if not complete: bx = 'incomplete'
            elif all('bx' in r['diagnostic_checks'] for r in records):
                bx = 'pass' if all(r['diagnostic_checks']['bx'] for r in records) else 'fail'
            elif mode == 'planar' and not any('bx' in r['diagnostic_checks'] for r in records):
                bx = 'diagnostic'
            else: bx = 'fail'
            groups.append(dict(
                jitter_mode=mode, profile=profile, names=names,
                expectation=EXPECTATIONS[mode, profile], complete=complete,
                stability_and_budget=stability, boost_check=boost,
                bx_gate=bx, seam_gate=seam,
                all_gates=stability and boost and seam and bx in ('pass', 'diagnostic')))
    expected = len(configs) == 8 and len(groups) == 4
    pick = lambda mode, profile: next(g for g in groups
                                      if g['jitter_mode'] == mode and g['profile'] == profile)
    symmetric = expected and all(pick('columns', p)['all_gates'] and pick('columns', p)['bx_gate'] == 'pass'
                                 for p in (LITERAL, CANDIDATE))
    return dict(
        groups=groups, completed_cases=sum(r.get('status') == 'completed' for r in runs.values()),
        expected_cases=8,
        symmetric_mesh_gates_passed=symmetric,
        planar_candidate_gates_passed=expected and pick('planar', CANDIDATE)['all_gates'],
        planar_literal_gates_passed=expected and pick('planar', LITERAL)['all_gates'],
        all_gates_passed=expected and all(g['all_gates'] for g in groups),
        full_m1_accepted=False,
        scope='Bounded nx256 x ny4, t=.1 mesh-symmetry controls. Planar-jitter failures remain failures; '
              'Bx is gated on y-invariant meshes only (owner-approved amendment); no threshold or initial state is changed and no long job is submitted.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=3)
    parser.add_argument('--timeout', type=float, default=30.,
                        help='Wall seconds per case; a timeout is incomplete, never a pass')
    parser.add_argument('--projection-screening', type=float, default=0.,
                        help='Opt-in damping kappa for the projected candidate cases; 0 is the exact projection')
    args = parser.parse_args()
    if not math.isfinite(args.projection_screening) or args.projection_screening < 0:
        parser.error('projection screening must be >= 0')
    if not 1 <= args.jobs <= 4: parser.error('jobs must be 1..4')
    if not math.isfinite(args.timeout) or not 0 < args.timeout <= 120:
        parser.error('timeout must be in (0,120] seconds')
    output = args.output_dir.resolve()
    if output.exists(): parser.error('Use a fresh output directory')
    output.mkdir(parents=True)
    paths = sorted({*ROOT.glob('crates/**/*.rs'), *ROOT.glob('apps/**/*.rs'),
                    *ROOT.glob('crates/*/Cargo.toml'), *ROOT.glob('apps/*/Cargo.toml'),
                    ROOT/'Cargo.toml', ROOT/'Cargo.lock', ROOT/'rust-toolchain.toml',
                    Path(__file__).resolve(), ROOT/'scripts/run_m1_physics.py',
                    ROOT/'scripts/run_m1_wave_loop.py', ROOT/'scripts/physics_projection.py',
                    ROOT/'benchmarks/m0/packet.json', AMENDMENT})
    sources = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    with tarfile.open(output/'source.tar.gz', 'w:gz') as archive:
        for p in paths: archive.add(p, arcname=str(p.relative_to(ROOT)))
    cargo = shutil.which('cargo') or str(Path.home()/'.cargo/bin/cargo')
    subprocess.run([cargo, 'build', '--release', '--locked', '-p', 'openmhd', '--bin', 'vector-potential'],
                   cwd=ROOT, check=True)
    binary = ROOT/'target/release/vector-potential'
    rows, reference_hash = reference('brio_8192.csv.gz')
    packet = load_json(ROOT/'benchmarks/m0/packet.json')
    gate = packet['cases']['brio-wu']['gate']
    provenance = dict(
        created_utc=datetime.now(timezone.utc).isoformat(), source_sha256=sources,
        binary_sha256=sha(binary), source_archive_sha256=sha(output/'source.tar.gz'),
        reference_sha256={'brio_8192.csv.gz': reference_hash},
        revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        rustc=subprocess.check_output([str(Path(cargo).with_name('rustc')), '-Vv'], text=True),
        jobs=args.jobs, threads_per_case=1, timeout_seconds=args.timeout,
        candidate_projection_screening=args.projection_screening,
        units='M0 packet; dimensionless mu0=1, f64, periodic, gamma=2, no floors/resets')
    configs = configurations()
    dump(output/'manifest.json', configs); dump(output/'provenance.json', provenance)

    def run(c):
        dest = output/c['name']; dest.mkdir()
        command = [str(binary), '--case', c['case'], '--profile', c['profile'], '--n', str(c['n']),
                   '--ny', str(c['ny']), '--jitter', str(c['jitter']), '--jitter-mode', c['jitter_mode'],
                   '--time', str(c['time']), '--motion', 'rigid',
                   '--mesh-x', str(c['boost'][0]), '--mesh-y', str(c['boost'][1]),
                   '--boost-x', str(c['boost'][0]), '--boost-y', str(c['boost'][1]), '--output', str(dest)]
        if c['accelerated_projection']:
            command += ['--accelerated-projection']
            if args.projection_screening: command += ['--projection-screening', str(args.projection_screening)]
        record = dict(config=c, command=command, status='failed'); start = time.monotonic()
        try:
            with (dest/'run.log').open('w') as log:
                done = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                      timeout=args.timeout)
            record['returncode'] = done.returncode
            summary = load_json(dest/'summary.json'); record['summary'] = summary
            initial = read_cells(dest/'initial.csv')
            record['initial_bx_error'] = bx_errors(initial)
            if done.returncode or not summary['completed']:
                failure = dest/'failure.txt'
                raise ValueError(failure.read_text() if failure.exists() else 'failed evolution; inspect run.log')
            if c['jitter_mode'] == 'columns' and summary.get('jitter_mode') != 'columns':
                raise ValueError('mesh family not recorded by the binary')
            history = load_json(dest/'history.json'); physics = load_json(dest/'physics.json')
            geometry = load_json(dest/'geometry.json'); cells = read_cells(dest/'final.csv')
            validate_run(c, summary, history, physics, geometry, initial, cells)
            positive = all(h['diagnostics']['rho_min'] > 0 and h['diagnostics']['p_min'] > 0
                           and max(map(abs, h['diagnostics']['normalized_budget'])) <= packet['solver']['budget_tolerance']
                           for h in history)
            pieces = polygons(geometry, cells, [b*c['time'] for b in c['boost'][:2]])
            rest = [dict(x, vx=x['vx']-c['boost'][0]) for x in cells]
            bx = bx_gate(c, initial, cells)
            checks = dict(seam=physics['signal_tracking'] and 0 <= physics['signal_travel_x'] < gate['seam_max_signal_travel'])
            if bx['gate_applies']: checks['bx'] = bx['passed']
            record.update(
                status='completed', positive_and_conservative=positive,
                p_min=min(h['diagnostics']['p_min'] for h in history),
                final_bx_error=bx['final'], bx_gate_applies=bx['gate_applies'], signal_travel_x=physics['signal_travel_x'],
                diagnostic_checks=checks,
                # Reported only: the packet limits apply to the finest nx=1024 regular run.
                reference_errors=shock_errors(rest, pieces, rows),
                reference_limits_finest_grid_only=gate['finest_scaled_L1_max'])
        except subprocess.TimeoutExpired:
            record.update(status='timeout', error='Wall-time cap reached; incomplete execution')
        except (OSError, ValueError, KeyError) as error:
            record['error'] = str(error)
        record['seconds'] = time.monotonic()-start
        record['files_sha256'] = {p.name: sha(p) for p in dest.iterdir() if p.is_file()}
        return c['name'], record

    runs = {}; started = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for future in as_completed([pool.submit(run, c) for c in configs.values()]):
            name, r = future.result(); runs[name] = r; dump(output/'runs.json', runs)
            print(f'{name}: {r["status"]} in {r["seconds"]:.2f}s; t={r.get("summary", {}).get("time", "incomplete")}', flush=True)
    pairs = []
    for name, c in configs.items():
        if not name.endswith('_base'): continue
        names = [name, name.removesuffix('_base')+'_boost']; pair = dict(names=names, status='unexecuted')
        if all(runs[n]['status'] == 'completed' for n in names):
            pair.update(boost_comparison(*(read_cells(output/n/'final.csv') for n in names), c, runs[name]['summary']))
            pair['status'] = 'pass' if pair['passed'] else 'fail'
        pairs.append(pair)
    summary = assess(configs, runs, pairs)
    summary.update(boost_pairs=pairs, wall_seconds=time.monotonic()-started)
    unchanged = (sources == {str(p.relative_to(ROOT)): sha(p) for p in paths}
                 and sha(binary) == provenance['binary_sha256'])
    summary['source_and_binary_unchanged'] = unchanged
    for key in ('symmetric_mesh_gates_passed', 'planar_candidate_gates_passed',
                'planar_literal_gates_passed', 'all_gates_passed'):
        summary[key] &= unchanged
    dump(output/'summary.json', summary)
    provenance['results_sha256'] = {n: sha(output/n) for n in ('manifest.json', 'runs.json', 'summary.json')}
    dump(output/'provenance.json', provenance)
    for g in summary['groups']:
        print(f'{g["jitter_mode"]:8} {g["profile"]:30} complete={g["complete"]} stable={g["stability_and_budget"]} '
              f'boost={g["boost_check"]} bx={g["bx_gate"]} seam={g["seam_gate"]}')
    print(f'Symmetric-mesh gates: {"PASS" if summary["symmetric_mesh_gates_passed"] else "FAIL"}; '
          f'planar candidate: {"PASS" if summary["planar_candidate_gates_passed"] else "FAIL"}; '
          f'all gates: {"PASS" if summary["all_gates_passed"] else "FAIL"}; '
          f'{summary["wall_seconds"]:.2f}s. Full M1 acceptance: not evaluated.')
    return 0 if summary['all_gates_passed'] else 1


if __name__ == '__main__': raise SystemExit(main())
