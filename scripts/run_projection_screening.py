#!/usr/bin/env python3
"""Bounded controls of the opt-in projection screening; not M1 acceptance.

Compares the quadratic projected candidate with the exact projection (kappa=0)
and with a damped correction (--projection-screening kappa) on planar-jittered
Brio shocks and short Alfven-wave convergence families. Every run keeps the
positivity and 1e-10 budget requirements; timeouts and failures stay failures.
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
from run_m1_physics import AMENDMENT, boost_comparison, bx_gate, load_json, reference
from run_m1_wave_loop import BOOST, ROOT, boost_error, dump, fitted_order, physical_errors, read_cells, sha

PROFILE = 'bulk-frame-heun-quadratic-v1'
KAPPAS = (0., 1.)
SENSITIVITY = (.3, 3.)
WAVE_ORDER = 1.8


def configurations():
    configs = {}
    def add(name, **c):
        configs[name] = dict(name=name, profile=PROFILE, ny=None, dt=None, parallel=0.,
                             boost=[0., 0., 0.], **c)
    for k in KAPPAS:
        for label, boost in (('base', [0., 0., 0.]), ('boost', list(BOOST))):
            add(f'brio_k{k}_n256_{label}', case='brio-wu', n=256, jitter=.15, time=.1, kappa=k)
            configs[f'brio_k{k}_n256_{label}']['boost'] = boost
        add(f'brio_k{k}_n256_regular', case='brio-wu', n=256, jitter=0., time=.1, kappa=k)
        add(f'brio_k{k}_n512', case='brio-wu', n=512, jitter=.15, time=.02, kappa=k)
        add(f'brio_k{k}_n512_ny8', case='brio-wu', n=512, jitter=.15, time=.02, kappa=k)
        configs[f'brio_k{k}_n512_ny8']['ny'] = 8
        for j in (0., .15):
            for v in (0., 1.):
                for n in (8, 16, 32):
                    name = f'alfven_k{k}_j{j}_v{v}_n{n}'
                    add(name, case='alfven', n=n, jitter=j, time=.02, kappa=k)
                    configs[name].update(parallel=v, dt=.00025)
                    if n == 16:
                        configs[name+'_boost'] = dict(configs[name], name=name+'_boost', boost=list(BOOST))
    for k in SENSITIVITY:
        add(f'brio_k{k}_n256_base', case='brio-wu', n=256, jitter=.15, time=.1, kappa=k)
    return configs


def analyze(output, configs, runs):
    done = lambda names: all(runs.get(n, {}).get('status') == 'completed' for n in names)
    cells = lambda n: read_cells(output/n/'final.csv')
    shocks, waves, pairs = [], [], []
    for name, c in configs.items():
        if c['case'] == 'brio-wu':
            r = runs.get(name, {})
            shocks.append({k: r.get(k) for k in ('status', 'p_min', 'bx', 'reference_errors', 'seconds', 'error')}
                          | dict(name=name, kappa=c['kappa'], n=c['n'], ny=c['ny'] or 4, jitter=c['jitter'], time=c['time']))
    for k in KAPPAS:
        names = [f'brio_k{k}_n256_base', f'brio_k{k}_n256_boost']; pair = dict(names=names, kappa=k, passed=False)
        if done(names):
            pair.update(boost_comparison(cells(names[0]), cells(names[1]), configs[names[0]], runs[names[0]]['summary']))
        pairs.append(pair)
        for j in (0., .15):
            for v in (0., 1.):
                names = [f'alfven_k{k}_j{j}_v{v}_n{n}' for n in (8, 16, 32)]
                row = dict(names=names, kappa=k, jitter=j, parallel=v, passed=False)
                if done(names):
                    row['errors'] = {f: [runs[n]['errors']['final'][f]['L1'] for n in names] for f in ('B', 'v')}
                    row['orders'] = {f: fitted_order([8, 16, 32], row['errors'][f])[0] for f in ('B', 'v')}
                    row['passed'] = min(row['orders'].values()) >= WAVE_ORDER
                waves.append(row)
                names = [f'alfven_k{k}_j{j}_v{v}_n16', f'alfven_k{k}_j{j}_v{v}_n16_boost']
                pair = dict(names=names, kappa=k, passed=False)
                if done(names):
                    error = boost_error(cells(names[0]), cells(names[1]), .02)
                    pair.update(errors=error, passed=all(error[f]['L1']/.1 <= 1e-8 for f in ('B', 'v'))
                                and error['position_max'] < 1e-10 and error['relative_volume_max'] < 1e-10)
                pairs.append(pair)
    by_kappa = {}
    for k in KAPPAS:
        mine = [n for n, c in configs.items() if c['kappa'] == k]
        by_kappa[str(k)] = dict(
            all_completed_positive_and_conservative=done(mine),
            wave_orders_passed=all(w['passed'] for w in waves if w['kappa'] == k),
            boost_pairs_passed=all(p['passed'] for p in pairs if p['kappa'] == k),
            regular_bx_gate_passed=bool(runs.get(f'brio_k{k}_n256_regular', {}).get('bx', {}).get('passed')))
    return dict(shocks=shocks, waves=waves, boost_pairs=pairs, by_kappa=by_kappa,
                completed=sum(r.get('status') == 'completed' for r in runs.values()), expected=len(configs),
                full_m1_accepted=False,
                scope='Bounded t<=.1 shock and t=.02 N8-32 wave controls of an opt-in damping; planar-jitter Bx is a '
                      'diagnostic. Not the original M1 ladders and no long job.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=3)
    parser.add_argument('--timeout', type=float, default=30.)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 4: parser.error('jobs must be 1..4')
    if not math.isfinite(args.timeout) or not 0 < args.timeout <= 60: parser.error('timeout must be in (0,60] seconds')
    out = args.output_dir.resolve()
    if out.exists(): parser.error('Use a fresh output directory')
    out.mkdir(parents=True)
    paths = sorted({*ROOT.glob('crates/**/*.rs'), *ROOT.glob('apps/**/*.rs'), *ROOT.glob('crates/*/Cargo.toml'),
                    *ROOT.glob('apps/*/Cargo.toml'), ROOT/'Cargo.toml', ROOT/'Cargo.lock', ROOT/'rust-toolchain.toml',
                    Path(__file__).resolve(), ROOT/'scripts/run_m1_physics.py', ROOT/'scripts/run_m1_wave_loop.py',
                    ROOT/'scripts/physics_projection.py', ROOT/'benchmarks/m0/packet.json', AMENDMENT})
    sources = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    with tarfile.open(out/'source.tar.gz', 'w:gz') as archive:
        for p in paths: archive.add(p, arcname=str(p.relative_to(ROOT)))
    cargo = shutil.which('cargo') or str(Path.home()/'.cargo/bin/cargo')
    subprocess.run([cargo, 'build', '--release', '--locked', '-p', 'openmhd', '--bin', 'vector-potential'], cwd=ROOT, check=True)
    binary = ROOT/'target/release/vector-potential'
    rows, reference_hash = reference('brio_8192.csv.gz')
    provenance = dict(created_utc=datetime.now(timezone.utc).isoformat(), source_sha256=sources,
                      source_archive_sha256=sha(out/'source.tar.gz'), binary_sha256=sha(binary),
                      reference_sha256={'brio_8192.csv.gz': reference_hash},
                      revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                      rustc=subprocess.check_output([str(Path(cargo).with_name('rustc')), '-Vv'], text=True),
                      jobs=args.jobs, threads_per_case=1, timeout_seconds=args.timeout,
                      units='dimensionless mu0=1, f64, periodic, no floors/resets; accelerated projection')
    configs = configurations(); dump(out/'manifest.json', configs); dump(out/'provenance.json', provenance)

    def run(c):
        d = out/c['name']; d.mkdir(); b = c['boost']
        cmd = [str(binary), '--case', c['case'], '--profile', c['profile'], '--n', str(c['n']), '--jitter', str(c['jitter']),
               '--parallel-velocity', str(c['parallel']), '--time', str(c['time']), '--motion', 'rigid',
               '--mesh-x', str(b[0]), '--mesh-y', str(b[1]), '--boost-x', str(b[0]), '--boost-y', str(b[1]),
               '--boost-z', str(b[2]), '--accelerated-projection', '--output', str(d)]
        if c['dt'] is not None: cmd += ['--dt', str(c['dt'])]
        if c['ny'] is not None: cmd += ['--ny', str(c['ny'])]
        if c['kappa']: cmd += ['--projection-screening', str(c['kappa'])]
        r = dict(config=c, command=cmd, status='failed'); started = time.monotonic()
        try:
            with (d/'run.log').open('w') as log:
                done = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout)
            summary = load_json(d/'summary.json'); r.update(summary=summary, returncode=done.returncode)
            if done.returncode or not summary['completed']:
                failure = d/'failure.txt'
                raise ValueError(failure.read_text() if failure.exists() else 'failed evolution')
            if (summary['profile'] != c['profile'] or summary['time'] != c['time']
                    or summary.get('projection_screening', 0.) != c['kappa']):
                raise ValueError('summary/config mismatch')
            history = load_json(d/'history.json')
            r.update(p_min=min(h['diagnostics']['p_min'] for h in history),
                     rho_min=min(h['diagnostics']['rho_min'] for h in history),
                     budget_max=max(max(map(abs, h['diagnostics']['normalized_budget'])) for h in history))
            if r['p_min'] <= 0 or r['rho_min'] <= 0 or r['budget_max'] > 1e-10: raise ValueError('positivity/budget failure')
            initial = read_cells(d/'initial.csv'); cells = read_cells(d/'final.csv')
            if c['case'] == 'alfven':
                r['errors'] = {s: physical_errors(v, 0. if s == 'initial' else c['time'], c['case'], c['parallel'], c['boost'])
                               for s, v in (('initial', initial), ('final', cells))}
            else:
                r['bx'] = bx_gate(c, initial, cells)
                if r['bx']['gate_applies'] and not r['bx']['passed']: raise ValueError('regular-mesh Bx gate failure')
                if c['time'] == .1:
                    pieces = polygons(load_json(d/'geometry.json'), cells, [x*c['time'] for x in b[:2]])
                    r['reference_errors'] = shock_errors([dict(x, vx=x['vx']-b[0]) for x in cells], pieces, rows)
            r['status'] = 'completed'
        except subprocess.TimeoutExpired: r.update(status='timeout', error='Wall-time cap reached; incomplete execution')
        except (OSError, ValueError, KeyError) as e: r['error'] = str(e)
        r['seconds'] = time.monotonic()-started
        r['files_sha256'] = {p.name: sha(p) for p in d.iterdir() if p.is_file()}
        return c['name'], r

    runs = {}
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for f in as_completed([pool.submit(run, c) for c in configs.values()]):
            n, r = f.result(); runs[n] = r; dump(out/'runs.json', runs)
            print(n, r['status'], f'{r["seconds"]:.2f}s', r.get('error', '')[:80], flush=True)
    result = analyze(out, configs, runs)
    result['source_and_binary_unchanged'] = (sources == {str(p.relative_to(ROOT)): sha(p) for p in paths}
                                             and sha(binary) == provenance['binary_sha256'])
    dump(out/'analysis.json', result)
    for k, v in result['by_kappa'].items(): print(f'kappa={k}: {v}')
    ok = result['completed'] == result['expected'] and result['source_and_binary_unchanged'] and all(
        all(v.values()) for v in result['by_kappa'].values())
    print(f'Screening controls: {"PASS" if ok else "FAIL"}. Full M1 acceptance: not evaluated.')
    return 0 if ok else 1


if __name__ == '__main__': raise SystemExit(main())
