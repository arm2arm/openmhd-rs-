#!/usr/bin/env python3
"""Bounded, prospectively specified M1 Heun investigation; not a full M1 gate."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from itertools import product
import math
from pathlib import Path
import platform
import shutil
import subprocess
import time

from run_m1_wave_loop import BOOST, ROOT, boost_error, dump, norms, physical_errors, read_snapshot, sha

PROFILES = ('bulk-frame-signal-v1', 'bulk-frame-heun-v1')
CAPS = (.0004, .0002, .0001, .000025)


def configurations(quick=False, auxiliary=False):
    configs = {}
    ladders = []
    pairs = []
    profiles = ('bulk-frame-heun-v1', 'bulk-frame-heun-spline-v1') if auxiliary else PROFILES
    for profile in profiles:
        for jitter, parallel, limited in product((0., .15), (0., 1.), (True, False) if auxiliary else (True,)):
            names = []
            for dt in CAPS:
                name = f'{profile}_j{jitter}_v{parallel}_dt{dt}'
                if auxiliary:
                    name += '_limited' if limited else '_unlimited'
                configs[name] = dict(name=name, profile=profile, jitter=jitter, parallel=parallel,
                                     dt=dt, n=8 if quick else 32, target=.004 if quick else .04,
                                     boost=[0., 0., 0.], limited=limited)
                names.append(name)
            boosted = names[2]+'_boost'
            configs[boosted] = dict(configs[names[2]], name=boosted, boost=list(BOOST))
            pairs.append([names[2], boosted])
            ladders.append(names)
    return configs, ladders, pairs


def differences(cells, reference):
    if len(cells) != len(reference):
        raise ValueError('time comparison cell count mismatch')
    if any(abs(a[k]-b[k]) > 1e-12 for a, b in zip(cells, reference) for k in ('x', 'y', 'volume')):
        raise ValueError('time comparison geometry differs')
    return {name: norms([math.sqrt(sum((a[k]-b[k])**2 for k in keys))
                        for a, b in zip(cells, reference)], cells)
            for name, keys in [('B', ('bx', 'by', 'bz')), ('v', ('vx', 'vy', 'vz')),
                               ('A', ('ax', 'ay', 'az')), ('phi', ('phi',))]}


def analyze(output, configs, ladders, pairs, records):
    if set(records) != set(configs) or any(r['status'] != 'completed' for r in records.values()):
        raise ValueError('Incomplete/failed runs; raw results and run records retained')
    cells = {name: read_snapshot(output/name/'final.csv', c['n'], c['target']) for name, c in configs.items()}
    temporal = []
    for names in ladders:
        errors = [differences(cells[name], cells[names[-1]]) for name in names[:-1]]
        orders = {field: [math.log(a[field]['L1']/b[field]['L1'], 2)
                          if a[field]['L1'] > 0 and b[field]['L1'] > 0 else None
                          for a, b in zip(errors, errors[1:])] for field in errors[0]}
        temporal.append({'names': names, 'profile': configs[names[0]]['profile'],
                         'limited': configs[names[0]].get('limited', True),
                         'jitter': configs[names[0]]['jitter'], 'parallel': configs[names[0]]['parallel'],
                         'caps': list(CAPS), 'errors': errors, 'adjacent_orders': orders})
    boosts = []
    for base, boosted in pairs:
        errors = boost_error(cells[base], cells[boosted], configs[base]['target'])
        relative = {field: errors[field]['L1']/.1 for field in ('B', 'v')}
        boosts.append({'names': [base, boosted], 'errors': errors, 'wave_relative': relative,
                       'field_gate': all(e <= 1e-8 for e in relative.values()),
                       'geometry_gate': errors['position_max'] <= 1e-9 and errors['relative_volume_max'] <= 1e-9})
    return {'scope': 'Bounded time study; finite dt reference; no M1 spatial or general boost acceptance claim.',
            'completed_evolutions': len(records), 'temporal': temporal, 'boost': boosts,
            'all_positive_and_conservative': all(r['positive_and_conservative'] for r in records.values()),
            'all_caps_reached': all(r['cap_reached'] for r in records.values()),
            'total_rejections': sum(sum(r['summary'][k] for k in ('rejected_cfl', 'rejected_state', 'rejected_geometry'))
                                    for r in records.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--quick', action='store_true', help='N8 t=.004 execution check, not the registered N32 measurement')
    parser.add_argument('--auxiliary-study', action='store_true', help='80-run projection/limiter factorial comparison')
    args = parser.parse_args()
    if not 1 <= args.jobs <= 24:
        parser.error('jobs must be between 1 and 24')
    output = args.output_dir.resolve()
    if output.exists():
        parser.error('Choose a fresh output directory to preserve provenance')
    output.mkdir(parents=True)
    configs, ladders, pairs = configurations(args.quick, args.auxiliary_study)
    dump(output/'manifest.json', {'configs': configs, 'ladders': ladders, 'pairs': pairs,
                                  'quick': args.quick, 'auxiliary_study': args.auxiliary_study})
    cargo = shutil.which('cargo') or str(Path.home()/'.cargo/bin/cargo')
    paths = sorted({*ROOT.glob('crates/**/*.rs'), *ROOT.glob('apps/**/*.rs'),
                    *ROOT.glob('crates/*/Cargo.toml'), *ROOT.glob('apps/*/Cargo.toml'), ROOT/'Cargo.toml',
                    ROOT/'Cargo.lock', ROOT/'rust-toolchain.toml', Path(__file__).resolve(),
                    ROOT/'scripts/run_m1_wave_loop.py', ROOT/'scripts/plot_heun_temporal.py',
                    ROOT/'docs/M1_HEUN_INVESTIGATION.md', ROOT/'docs/M1_AUXILIARY_INVESTIGATION.md'})
    sources = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    command = lambda c: subprocess.check_output(c, cwd=ROOT, text=True).strip()
    provenance = {'created_utc': datetime.now(timezone.utc).isoformat(), 'revision': command(['git', 'rev-parse', 'HEAD']),
                  'dirty_status': command(['git', 'status', '--short']), 'source_sha256': sources,
                  'platform': platform.platform(), 'python': platform.python_version(),
                  'rustc': command([str(Path(cargo).with_name('rustc')), '-Vv']), 'jobs': args.jobs,
                  'units': 'dimensionless mu0=1 gamma=5/3; f64; periodic unit square; centroid LS curl',
                  'per_run_ranks': 1, 'per_run_threads': 1}
    dump(output/'provenance.json', provenance)
    subprocess.run([cargo, 'build', '--release', '--locked', '-p', 'openmhd', '--bin', 'vector-potential'], cwd=ROOT, check=True)
    binary = ROOT/'target/release/vector-potential'
    provenance['binary_sha256'] = sha(binary)
    dump(output/'provenance.json', provenance)

    def run(c):
        dest = output/c['name']
        dest.mkdir()
        cmd = [str(binary), '--case', 'alfven', '--profile', c['profile'], '--n', str(c['n']),
               '--jitter', str(c['jitter']), '--parallel-velocity', str(c['parallel']), '--time', str(c['target']),
               '--dt', str(c['dt']), '--motion', 'rigid', '--mesh-x', str(c['boost'][0]), '--mesh-y', str(c['boost'][1]),
               '--boost-x', str(c['boost'][0]), '--boost-y', str(c['boost'][1]), '--boost-z', str(c['boost'][2]),
               '--output', str(dest)]
        if not c['limited']:
            cmd.append('--unlimited')
        start = time.monotonic()
        with (dest/'run.log').open('w') as log:
            result = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        record = {'command': cmd, 'returncode': result.returncode, 'seconds': time.monotonic()-start, 'status': 'failed'}
        try:
            summary = json.loads((dest/'summary.json').read_text())
            history = json.loads((dest/'history.json').read_text())
            if (result.returncode or not summary['completed'] or summary['time'] != c['target']
                    or summary['profile'] != c['profile'] or summary['limited'] != c['limited']):
                raise ValueError('unsuccessful/mismatched evolution')
            initial = read_snapshot(dest/'initial.csv', c['n'], 0.)
            final = read_snapshot(dest/'final.csv', c['n'], c['target'])
            record.update(status='completed', summary=summary, history=history,
                          positive_and_conservative=bool(history) and all(h['diagnostics']['rho_min'] > 0
                              and h['diagnostics']['p_min'] > 0 and max(map(abs, h['diagnostics']['normalized_budget'])) <= 1e-10 for h in history),
                          cap_reached=abs(summary['dt_max']/c['dt']-1) < 1e-12,
                          physical_errors={'initial': physical_errors(initial, 0., 'alfven', c['parallel'], c['boost']),
                                           'final': physical_errors(final, c['target'], 'alfven', c['parallel'], c['boost'])})
        except (ValueError, KeyError, OSError) as error:
            record['error'] = str(error)
        record['sha256'] = {p.name: sha(p) for p in dest.iterdir() if p.is_file()}
        return c['name'], record

    records = {}
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for future in as_completed([pool.submit(run, c) for c in configs.values()]):
            name, record = future.result()
            records[name] = record
            dump(output/'runs.json', records)
            print(f'{len(records)}/{len(configs)} {name}: {record["status"]} ({record["seconds"]:.2f}s)', flush=True)
    dump(output/'summary.json', analyze(output, configs, ladders, pairs, records))
    if sources != {str(p.relative_to(ROOT)): sha(p) for p in paths}:
        raise ValueError('Study sources changed during execution')
    provenance['result_sha256'] = {name: sha(output/name) for name in ('manifest.json', 'runs.json', 'summary.json')}
    dump(output/'provenance.json', provenance)


if __name__ == '__main__':
    main()
