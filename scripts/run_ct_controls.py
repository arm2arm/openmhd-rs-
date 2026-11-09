#!/usr/bin/env python3
"""Bounded complete-CT comparator; neither paper reproduction nor M1 acceptance."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess
import time
from run_m1_wave_loop import ROOT, BOOST, FIELDS, dump, sha, read_cells, physical_errors, fitted_order


def configurations():
    configs = {}
    for n in [256, 512]:
        for j in [0., .15]:
            for t in [.01, .02]:
                for boosted in [False, True]:
                    name = f'brio_n{n}_j{j}_t{t}_' + ('boost' if boosted else 'base')
                    configs[name] = dict(case='brio-wu', n=n, jitter=j, time=t,
                                         boost=list(BOOST) if boosted else [0., 0., 0.])
    for j in [0., .15]:
        for v in [0., 1.]:
            for n in [8, 16, 32]:
                name = f'wave_j{j}_v{v}_n{n}_base'
                configs[name] = dict(case='alfven', n=n, jitter=j, parallel=v, time=.02,
                                     dt=.00025, boost=[0., 0., 0.])
                if n == 16:
                    configs[name.replace('_base', '_boost')] = dict(configs[name], boost=list(BOOST))
    return configs


def pair_error(base, boosted, config):
    if len(base) != len(boosted):
        raise ValueError('incomplete boost pair')
    lengths = [2., .125] if config['case'] == 'brio-wu' else [1., 1.]
    worst = {k: 0. for k in FIELDS}
    position = volume = 0.
    for a, b in zip(base, boosted):
        for k in FIELDS:
            expected = a[k]
            if k in ('vx', 'vy', 'vz'):
                expected += BOOST[('vx', 'vy', 'vz').index(k)]
            if k == 'energy':
                expected += a['rho'] * (sum(BOOST[i]*a[f] for i, f in enumerate(('vx', 'vy', 'vz'))) + .5*sum(v*v for v in BOOST))
            worst[k] = max(worst[k], abs(b[k]-expected))
        for k, length, shift in zip(('x', 'y'), lengths, BOOST):
            position = max(position, abs((b[k]-a[k]-shift*config['time']+length/2) % length-length/2))
        volume = max(volume, abs(b['volume']/a['volume']-1))
    return dict(component_max_absolute=worst, position_max=position, volume_relative_max=volume,
                passed=max(worst.values()) <= 1e-8 and position <= 1e-10 and volume <= 1e-10)


def analyze(output, configs, records):
    runs = {}
    for name, c in configs.items():
        path = output/name
        result = dict(records[name])
        if (path/'summary.json').exists():
            summary = json.loads((path/'summary.json').read_text())
            result['summary'] = summary
            if result['status'] == 'completed' and (summary['status'] != 'completed' or summary['time'] != c['time']):
                raise ValueError(f'inconsistent completion: {name}')
        if (path/'initial.csv').exists():
            initial = read_cells(path/'initial.csv')
            if c['case'] == 'brio-wu':
                result['initial_bx_error'] = max(abs(r['bx']-.75) for r in initial)
            else:
                result['initial_errors'] = physical_errors(initial, 0., 'alfven', c['parallel'], c['boost'])
        if (path/'final.csv').exists():
            final = read_cells(path/'final.csv')
            if c['case'] == 'brio-wu':
                result['final_bx_error'] = max(abs(r['bx']-.75) for r in final)
                result['bx_gate_passed'] = result['initial_bx_error'] <= 1e-8 and result['final_bx_error'] <= 1e-8
            else:
                result['final_errors'] = physical_errors(final, result['summary']['time'], 'alfven', c['parallel'], c['boost'])
        if (path/'accepted_diagnostics.csv').exists():
            with (path/'accepted_diagnostics.csv').open() as stream:
                history = list(csv.DictReader(stream))
            valid = [r for r in history if all(v is not None for v in r.values())]
            if valid:
                result['accepted'] = dict(rows=len(valid), time=float(valid[-1]['time']),
                    min_pressure=min(float(r['min_pressure']) for r in valid),
                    min_density=min(float(r['min_density']) for r in valid),
                    max_budget=max(float(r['budget_max']) for r in valid),
                    max_ct_divergence=max(float(r['div_ct_max']) for r in valid))
        if (path/'initial_energy_rates.csv').exists() and c['case'] == 'brio-wu':
            with (path/'initial_energy_rates.csv').open() as stream:
                rates = list(csv.DictReader(stream))
            result['cell253_initial_rates'] = {k: float(v) for k,v in rates[253].items() if k != 'id'}
        runs[name] = result
    pairs = []
    for name, c in configs.items():
        other = name.replace('_base', '_boost')
        if not name.endswith('_base') or other not in configs:
            continue
        row = dict(names=[name, other], passed=False)
        if all(runs[n]['status'] == 'completed' for n in [name, other]):
            row.update(pair_error(read_cells(output/name/'final.csv'), read_cells(output/other/'final.csv'), c))
        pairs.append(row)
    spatial = []
    for j in [0., .15]:
        for v in [0., 1.]:
            names = [f'wave_j{j}_v{v}_n{n}_base' for n in [8,16,32]]
            row = dict(names=names, jitter=j, parallel=v, passed=False)
            if all(runs[n]['status'] == 'completed' for n in names):
                row['orders'] = {f: fitted_order([8,16,32], [runs[n]['final_errors'][f]['L1'] for n in names])[0] for f in ['B','v']}
                row['passed'] = min(row['orders'].values()) >= 1.8
            spatial.append(row)
    return dict(profile='voronoi-ct-heun-v1', completed=sum(r['status']=='completed' for r in runs.values()),
                count=len(runs), runs=runs, boost_pairs=pairs, spatial=spatial, full_m1_accepted=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--analyze-only', action='store_true')
    args = p.parse_args()
    output = args.output_dir.resolve()
    configs = configurations()
    if args.analyze_only:
        configs = json.loads((output/'configurations.json').read_text())
        records = json.loads((output/'executions.json').read_text())
    else:
        output.mkdir(parents=True, exist_ok=False)
        cargo = shutil.which('cargo') or str(Path.home()/'.cargo/bin/cargo')
        subprocess.run([cargo, 'build', '--release', '--locked', '-p', 'openmhd', '--bin', 'ct-comparator'], cwd=ROOT, check=True)
        binary = ROOT/'target/release/ct-comparator'
        source_paths = subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
        source_paths += ['crates/mhd-vector-pot/src/ct.rs', 'crates/mhd-vector-pot/tests/ct.rs',
                         'apps/openmhd/src/bin/ct-comparator.rs', 'docs/M1_CT_COMPARATOR.md', 'scripts/run_ct_controls.py']
        paths = sorted(set(p for p in source_paths if p.startswith(('crates/','apps/')) or p in ('Cargo.toml','Cargo.lock','rust-toolchain.toml','docs/M1_CT_COMPARATOR.md','scripts/run_ct_controls.py')))
        dump(output/'source_manifest.json', {p:sha(ROOT/p) for p in paths if (ROOT/p).is_file()})
        (output/'working_tree.patch').write_bytes(subprocess.check_output(['git','diff','HEAD'],cwd=ROOT))
        dump(output/'provenance.json', dict(base_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
             source_state='working tree; exact files saved in source/', binary_sha256=sha(binary), python=platform.python_version(),
             platform=platform.platform(), max_concurrent_serial_cases=3, per_case_wall_limit_seconds=30,
             rustc=subprocess.check_output([str(Path(cargo).with_name('rustc')),'--version'],text=True).strip()))
        for path in paths:
            if not (ROOT/path).is_file():
                continue
            destination=output/'source'/path
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/path,destination)
        dump(output/'configurations.json', configs)
        def execute(name,c):
            path=output/name
            path.mkdir()
            command=[str(binary),'--case',c['case'],'--n',str(c['n']),'--jitter',str(c['jitter']),
                     '--time',str(c['time']),'--boost-x',str(c['boost'][0]),'--boost-y',str(c['boost'][1]),'--output',str(path)]
            for flag in ['parallel','dt']:
                if flag in c:
                    command += ['--'+flag,str(c[flag])]
            dump(path/'command.json',command)
            start=time.monotonic()
            with (path/'stdout.log').open('w') as out, (path/'stderr.log').open('w') as err:
                try:
                    result=subprocess.run(command,cwd=ROOT,stdout=out,stderr=err,timeout=30)
                    status='completed' if result.returncode==0 else 'failed'
                    code=result.returncode
                except subprocess.TimeoutExpired:
                    status='timeout';code=None
            record=dict(status=status,returncode=code,wall_seconds=time.monotonic()-start)
            print(f'{name}: {status} ({record["wall_seconds"]:.2f}s)',flush=True)
            return name,record
        records={}
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures=[pool.submit(execute,n,c) for n,c in configs.items()]
            for future in as_completed(futures):
                name,record=future.result();records[name]=record
                dump(output/'executions.json',records)
    result=analyze(output,configs,records)
    dump(output/'analysis.json',result)
    print(json.dumps({k:result[k] for k in ['completed','count','spatial','full_m1_accepted']},indent=2))


if __name__=='__main__':
    main()
