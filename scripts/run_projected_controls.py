#!/usr/bin/env python3
"""Bounded accuracy/refinement controls of existing projection profiles; not M1 acceptance."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import subprocess
import tarfile
import time
from run_m1_wave_loop import ROOT, BOOST, dump, sha, read_cells, physical_errors, fitted_order, boost_error
from run_heun_temporal import differences
from run_m1_physics import boost_comparison

PROFILES = ('bulk-frame-heun-projected-v1', 'bulk-frame-heun-quadratic-v1')


def configurations():
    configs = {}
    for p in PROFILES:
        for j in [0., .15]:
            for v in [0., 1.]:
                for n in [8, 16, 32]:
                    name = f'{p}_j{j}_v{v}_n{n}'
                    configs[name] = dict(name=name, case='alfven', profile=p, n=n, jitter=j,
                                         parallel=v, time=.02, dt=.00025, boost=[0.,0.,0.])
                    if n == 16:
                        configs[name+'_boost'] = dict(configs[name], name=name+'_boost', boost=list(BOOST))
        original = f'{p}_j0.15_v1.0_n16'
        for dt in [.001, .0005, .000125]:
            name = original+f'_dt{dt}'
            configs[name] = dict(configs[original], name=name, dt=dt)
    for label, boost in [('base', [0.,0.,0.]), ('boost', list(BOOST))]:
        name = 'quadratic_brio_'+label
        configs[name] = dict(name=name, case='brio-wu', profile=PROFILES[1], n=512, jitter=.15,
                             parallel=0., time=.02, dt=None, boost=boost)
    return configs


def analyze(output, configs, runs):
    spatial, pairs, temporal = [], [], []
    complete = lambda names: all(runs[n]['status'] == 'completed' for n in names)
    cells = lambda name: read_cells(output/name/'final.csv')
    for p in PROFILES:
        for j in [0., .15]:
            for v in [0., 1.]:
                names = [f'{p}_j{j}_v{v}_n{n}' for n in [8,16,32]]
                row = dict(names=names, profile=p, jitter=j, parallel=v, passed=False)
                if complete(names):
                    row['orders'] = {stage: {f: fitted_order([8,16,32],
                        [runs[n]['errors'][stage][f]['L1'] for n in names])[0]
                        for f in ['B','v'] if not (stage == 'initial' and f == 'v') and all(runs[n]['errors'][stage][f]['L1'] > 0 for n in names)}
                        for stage in ['initial','final']}
                    row['errors'] = {stage: {f: [runs[n]['errors'][stage][f]['L1'] for n in names]
                        for f in ['B','v']} for stage in ['initial','final']}
                    row['passed'] = all(row['orders']['final'].get(f, -math.inf)>=1.8 for f in ['B','v'])
                spatial.append(row)
                base = names[1]; boosted = base+'_boost'; pair = dict(names=[base,boosted], passed=False)
                if complete([base, boosted]):
                    error = boost_error(cells(base), cells(boosted), .02)
                    pair.update(errors=error, passed=all(error[f]['L1']/.1<=1e-8 for f in ['B','v'])
                                and error['position_max']<1e-10 and error['relative_volume_max']<1e-10)
                pairs.append(pair)
        base = f'{p}_j0.15_v1.0_n16'
        names = [base+'_dt0.001',base+'_dt0.0005',base,base+'_dt0.000125']
        row = dict(names=names, profile=p, passed=False)
        if complete(names):
            diffs = [differences(cells(n),cells(names[-1])) for n in names[:-1]]
            orders = {f: [math.log(a[f]['L1']/b[f]['L1'], 2) for a,b in zip(diffs,diffs[1:])]
                      for f in ['B','v'] if all(e[f]['L1']>0 for e in diffs)}
            row.update(errors=diffs, orders=orders, passed=all(f in orders and min(orders[f])>=1.8 for f in ['B','v']))
        temporal.append(row)
    names = ['quadratic_brio_base','quadratic_brio_boost']; shock = dict(names=names, passed=False)
    if complete(names):
        shock.update(boost_comparison(cells(names[0]),cells(names[1]),configs[names[0]],runs[names[0]]['summary']))
    return dict(spatial=spatial, temporal=temporal, wave_boosts=pairs, shock_boost=shock,
                completed=sum(r['status']=='completed' for r in runs.values()), expected=len(configs),
                full_m1_accepted=False, scope='Short t=.02 development packet, not original M1 t=1 spatial/time validation.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--accelerated-projection',action='store_true')
    args=parser.parse_args();out=args.output_dir.resolve()
    if out.exists():parser.error('Use a fresh output directory')
    out.mkdir(parents=True)
    configs=configurations();dump(out/'manifest.json',configs)
    paths=sorted({*ROOT.glob('crates/**/*.rs'),*ROOT.glob('apps/**/*.rs'),*ROOT.glob('crates/*/Cargo.toml'),
                  *ROOT.glob('apps/*/Cargo.toml'),*ROOT.glob('scripts/*.py'),*[ROOT/p for p in
                  ['Cargo.toml','Cargo.lock','rust-toolchain.toml','docs/M1_SHOCK_INVESTIGATION.md','benchmarks/m0/packet.json']]})
    sources={str(p.relative_to(ROOT)):sha(p) for p in paths}
    with tarfile.open(out/'source.tar.gz','w:gz') as t:
        for p in paths:t.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
    cargo=shutil.which('cargo') or str(Path.home()/'.cargo/bin/cargo')
    subprocess.run([cargo,'build','--release','--locked','-p','openmhd','--bin','vector-potential'],cwd=ROOT,check=True)
    binary=ROOT/'target/release/vector-potential'
    provenance=dict(created_utc=datetime.now(timezone.utc).isoformat(),source_sha256=sources,
                    source_archive_sha256=sha(out/'source.tar.gz'),binary_sha256=sha(binary),
                    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                    jobs=3,threads_per_case=1,timeout_seconds=30,accelerated_projection=args.accelerated_projection)
    dump(out/'provenance.json',provenance)
    def run(c):
        d=out/c['name'];d.mkdir();b=c['boost']
        cmd=[str(binary),'--case',c['case'],'--profile',c['profile'],'--n',str(c['n']),'--jitter',str(c['jitter']),
             '--parallel-velocity',str(c['parallel']),'--time',str(c['time']),'--motion','rigid',
             '--mesh-x',str(b[0]),'--mesh-y',str(b[1]),'--boost-x',str(b[0]),'--boost-y',str(b[1]),
             '--boost-z',str(b[2]),'--trace-diagnostics','--output',str(d)]
        if c['dt'] is not None:cmd+=['--dt',str(c['dt'])]
        if args.accelerated_projection:cmd+=['--accelerated-projection']
        r=dict(config=c,command=cmd,status='failed');started=time.monotonic()
        try:
            with (d/'run.log').open('w') as log:done=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=30)
            summary=json.loads((d/'summary.json').read_text());r.update(summary=summary,returncode=done.returncode)
            if done.returncode or not summary['completed']:raise ValueError((d/'failure.txt').read_text())
            if summary['profile']!=c['profile'] or summary['time']!=c['time']:raise ValueError('summary/config mismatch')
            if args.accelerated_projection and summary.get('projection_solver')!='cached-cholesky-pcg':raise ValueError('projection solver mismatch')
            with (d/'accepted_diagnostics.csv').open() as f:h=[{k:float(v) for k,v in a.items()} for a in csv.DictReader(f)]
            if len(h)!=summary['steps']+1 or h[0]['time']!=0 or h[-1]['time']!=c['time']:raise ValueError('incomplete history')
            if any(not math.isfinite(v) for a in h for v in a.values()) or any(b['time']<=a['time'] for a,b in zip(h,h[1:])):raise ValueError('invalid history')
            r.update(history_p_min=min(a['p_min'] for a in h),history_rho_min=min(a['rho_min'] for a in h),budget_max=max(a['budget_max'] for a in h))
            if r['history_p_min']<=0 or r['history_rho_min']<=0 or r['budget_max']>1e-10:raise ValueError('positivity/budget failure')
            snapshots={s:read_cells(d/f'{s}.csv') for s in ['initial','final']}
            count=c['n']**2 if c['case']=='alfven' else c['n']*4
            if any(len(v)!=count for v in snapshots.values()):raise ValueError('cell count mismatch')
            if c['case']=='alfven':r['errors']={s:physical_errors(v,0. if s=='initial' else c['time'],c['case'],c['parallel'],c['boost']) for s,v in snapshots.items()}
            else:r['bx_max_error']=max(abs(a['bx']-.75) for a in snapshots['final'])
            r['status']='completed'
        except subprocess.TimeoutExpired:r.update(status='timeout',error='30-second cap')
        except (OSError,ValueError,KeyError) as e:r['error']=str(e)
        r['seconds']=time.monotonic()-started;r['files_sha256']={p.name:sha(p) for p in d.iterdir() if p.is_file()}
        return c['name'],r
    runs={}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for f in as_completed([pool.submit(run,c) for c in configs.values()]):
            n,r=f.result();runs[n]=r;dump(out/'runs.json',runs);print(n,r['status'],f'{r["seconds"]:.2f}s',flush=True)
    result=analyze(out,configs,runs)
    result['source_and_binary_unchanged']=sources=={str(p.relative_to(ROOT)):sha(p) for p in paths} and sha(binary)==provenance['binary_sha256']
    dump(out/'analysis.json',result)
    return 0 if result['completed']==result['expected'] and result['source_and_binary_unchanged'] else 1


if __name__=='__main__':raise SystemExit(main())
