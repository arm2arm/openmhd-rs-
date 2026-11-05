#!/usr/bin/env python3
"""Run and measure the remaining M1 passive loop, Brio-Wu and Orszag-Tang packet.

Use an immutable source checkout. Failures are archived, never dropped from gates.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess
import time
from m1_overlap import project, polygons, shock_error
from run_m1_wave_loop import read_cells, physical_errors, boost_error

ROOT=Path(__file__).resolve().parents[1]
PROFILE='bulk-frame-hll-v1'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v): p.write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n')
def reference(name):
    with gzip.open(ROOT/'tests/reference/external_mhd'/name,'rt') as f:
        return [{k:float(v) for k,v in r.items()} for r in csv.DictReader(f)]

def measure(output,runs):
    brio=reference('brio_8192.csv.gz'); vortex=reference('vortex_512.csv.gz')
    for name,r in runs.items():
        if r['status']!='completed': continue
        p=output/name; c=r['config']; a=read_cells(p/'initial.csv'); b=read_cells(p/'final.csv'); s=r['summary']
        if c['case']=='passive':
            r['analytic_errors']=physical_errors(b,1.,'loop',0.,[0.,0.,0.])
            amp=.001/math.sqrt(4*math.pi)
            r['discrete_A_relative_max']=max(abs(x['az']-y['az']) for x,y in zip(a,b))/(.3*amp)
            r['discrete_B_relative_max']=max(math.sqrt(sum((x[k]-y[k])**2 for k in ('bx','by','bz'))) for x,y in zip(a,b))/amp
            r['relative_A_L1']=r['analytic_errors']['passive_A']['L1']/(.3*amp)
            r['magnetic_energy_initial_final']=[sum(.5*x['volume']*sum(x[k]**2 for k in ('bx','by','bz')) for x in cells) for cells in (a,b)]
            continue
        r['positive_and_conservative']=(s['final']['rho_min']>0 and s['final']['p_min']>0 and max(map(abs,s['final']['normalized_budget']))<=1e-10)
        poly=polygons(p/'polygons.csv')
        if c['case']=='brio':
            r['reference_L1'],diagnostic,proj=shock_error(b,poly,brio)
            r['bx_max_error']=max(abs(x['bx']-.75) for x in b)
            r['signal_travel_upper']=s.get('integrated_signal_travel',.1*max(s['max_signal_x'],s['max_face_signal']))
            r['signal_diagnostic']='integral of accepted-stage maxima' if 'integrated_signal_travel' in s else 'global speed maximum times duration; conservative upper bound on integral'
        else:
            # Pull jointly boosted mesh/state back to the baseline frame before binning.
            if c['boost']:
                poly={i:[(x-2*s['time'],y+s['time']) for x,y in points] for i,points in poly.items()}
                b=[{**x,'vx':x['vx']-2.,'vy':x['vy']+1.} for x in b]
            proj,diagnostic=project(b,poly,[1.,1.],[64,64])
            scales={'rho':25/(36*math.pi),'p':5/(12*math.pi),'bx':1/math.sqrt(4*math.pi),'by':1/math.sqrt(4*math.pi)}
            r['reference_L1']={k:sum(abs(x[k]-y[k]) for x,y in zip(proj,vortex))/len(vortex) for k in scales}
            r['scaled_reference_L1']={k:v/scales[k] for k,v in r['reference_L1'].items()}
            r['mean_B_relative_drift']=math.sqrt(sum(x*x for x in s['final']['mean_B_drift']))/s['Bscale']
            r['limited_divB_dimensionless_rms']=s['final']['div_B_limited']['dimensionless']['rms']
        r['projection_checks']=diagnostic
        dump(p/'projection.json',proj)
    gates=[]
    for jitter in (0.,.15):
        for moving in (False,True):
            rows=sorted([r for r in runs.values() if r['config']['case']=='passive' and r['config']['jitter']==jitter and r['config']['comoving']==moving],key=lambda r:r['config']['n'])
            valid=len(rows)==4 and all(r['status']=='completed' for r in rows)
            ok=valid and (all(max(r['discrete_A_relative_max'],r['discrete_B_relative_max'])<=1e-10 for r in rows) if moving else rows[-1]['relative_A_L1']<=.1 and all(a['relative_A_L1']>b['relative_A_L1'] for a,b in zip(rows,rows[1:])))
            gates.append({'case':'passive','jitter':jitter,'comoving':moving,'status':'pass' if ok else 'fail','relative_A_L1':[r.get('relative_A_L1') for r in rows]})
    rows=sorted([r for r in runs.values() if r['config']['case']=='brio'],key=lambda r:r['config']['n'])
    valid=len(rows)==3 and all(r['status']=='completed' and r['positive_and_conservative'] for r in rows)
    ok=valid and all(rows[-1]['reference_L1'][k]<=limit and rows[-1]['reference_L1'][k]<rows[0]['reference_L1'][k] for k,limit in {'rho':.03,'p':.04,'vx':.03,'by':.04}.items()) and all(r['bx_max_error']<=1e-8 and r['signal_travel_upper']<.45 for r in rows)
    gates.append({'case':'brio','status':'pass' if ok else 'fail'})
    for jitter in (0.,.15):
        for boost in (False,True):
            rows=sorted([r for r in runs.values() if r['config']['case']=='vortex' and r['config']['jitter']==jitter and r['config']['boost']==boost],key=lambda r:r['config']['n'])
            valid=len(rows)==3 and all(r['status']=='completed' and r['positive_and_conservative'] for r in rows)
            ok=valid and all(rows[-1]['scaled_reference_L1'][k]<=limit and rows[-1]['scaled_reference_L1'][k]<rows[0]['scaled_reference_L1'][k] for k,limit in {'rho':.06,'p':.1,'bx':.1,'by':.1}.items()) and all(r['mean_B_relative_drift']<=.001 and r['limited_divB_dimensionless_rms']<=.1 for r in rows)
            gates.append({'case':'vortex','jitter':jitter,'boost':boost,'status':'pass' if ok else 'fail'})
    pairs=[]
    for jitter in (0.,.15):
        for n in (64,128,256):
            names=[f'vortex_n{n}_j{jitter}_b{b}' for b in (0,1)]
            pair={'names':names,'status':'failed evolution'}
            if all(runs[name]['status']=='completed' for name in names):
                cells=[read_cells(output/name/'final.csv') for name in names]
                e=boost_error(*cells,.5)
                rho=25/(36*math.pi);p=5/(12*math.pi);bs=1/math.sqrt(4*math.pi)
                scales={'rho':rho,'p':p,'B':bs,'v':math.sqrt(2.),'energy':p/(5/3-1)+rho+bs*bs}
                relative={k:e[k]['L1']/v for k,v in scales.items()}
                valid=all(runs[name]['summary']['time']==.5 and runs[name]['positive_and_conservative'] for name in names) and all(row['time']==.5 for rows in cells for row in rows) and e['position_max']<=1e-11 and e['relative_volume_max']<=1e-11
                pair.update(errors=e,relative_L1=relative,normalization_scales=scales,pairing_and_budgets_valid=valid,status='pass' if valid and max(relative.values())<=1e-8 else 'fail')
            pairs.append(pair)
    return {'profile':PROFILE,'scope':'remaining M1 cases; wave/loop packet and AI review also required','gates':gates,'vortex_boost_pairs':pairs,'runs':runs}

def reanalyze(out):
    original=out/'execution_provenance.json'
    if not original.exists(): shutil.copyfile(out/'provenance.json',original)
    execution=json.loads(original.read_text())
    for name in ('manifest.json','runs.json'):
        if sha(out/name)!=execution['result_sha256'][name]:raise ValueError(f'changed execution input {name}')
    immutable=out/'execution_summary.json'
    if not immutable.exists():
        if sha(out/'summary.json')!=execution['result_sha256']['summary.json']:raise ValueError('missing original summary')
        shutil.copyfile(out/'summary.json',immutable)
    if sha(immutable)!=execution['result_sha256']['summary.json']:raise ValueError('changed immutable execution summary')
    for name,digest in execution['external_reference_hashes'].items():
        if sha(ROOT/'tests/reference/external_mhd'/name)!=digest:raise ValueError(f'changed reference {name}')
    runs=json.loads((out/'runs.json').read_text())
    manifest=json.loads((out/'manifest.json').read_text())
    if set(runs)!=set(manifest):raise ValueError('missing/extra run records')
    for name,r in runs.items():
        if r['config']!=manifest[name]:raise ValueError('changed run configuration')
        for filename,digest in r['artifacts_sha256'].items():
            if sha(out/name/filename)!=digest:raise ValueError(f'changed raw input {name}/{filename}')
        if 'summary' in r and r['summary']!=json.loads((out/name/'summary.json').read_text()):raise ValueError('summary metadata disagreement')
    dump(out/'summary.json',measure(out,runs))
    dump(out/'measurement_provenance.json',{'execution_provenance_sha256':sha(original),'execution_summary_sha256':sha(immutable),'raw_runs_sha256':sha(out/'runs.json'),'measurement_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'measurement_dirty_status':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True).strip(),'measurement_sources_sha256':{str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__).resolve(),ROOT/'scripts/m1_overlap.py',ROOT/'scripts/run_m1_wave_loop.py')},'summary_sha256':sha(out/'summary.json'),'note':'Corrected analysis only; raw execution hashes verified, original analysis preserved.'})


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output-dir',type=Path,required=True); parser.add_argument('--jobs',type=int,default=4); parser.add_argument('--analyze-only',action='store_true'); args=parser.parse_args()
    out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    if args.analyze_only:
        reanalyze(out); return
    if (out/'manifest.json').exists(): raise SystemExit('Use a fresh output directory')
    cargo=shutil.which('cargo') or str(Path.home()/'.cargo/bin/cargo')
    paths=sorted({*ROOT.glob('crates/*/src/**/*.rs'),*ROOT.glob('crates/*/tests/**/*.rs'),*ROOT.glob('apps/*/src/**/*.rs'),*ROOT.glob('crates/*/Cargo.toml'),*ROOT.glob('apps/*/Cargo.toml'),ROOT/'Cargo.toml',ROOT/'Cargo.lock',ROOT/'rust-toolchain.toml',ROOT/'docs/M1_COMPLETION_PLAN.md',ROOT/'benchmarks/m1/packet-v2.json',Path(__file__).resolve(),ROOT/'scripts/m1_overlap.py',ROOT/'scripts/run_m1_wave_loop.py'})
    sources={str(p.relative_to(ROOT)):sha(p) for p in paths}
    command=lambda cmd:subprocess.check_output(cmd,cwd=ROOT,text=True).strip()
    provenance={'created_utc':datetime.now(timezone.utc).isoformat(),'revision':command(['git','rev-parse','HEAD']),'dirty_status':command(['git','status','--short']),'sources_sha256':sources,'platform':platform.platform(),'rustc':command([str(Path(cargo).with_name('rustc')),'-Vv']),'jobs':args.jobs,'ranks_per_run':1,'threads_per_run':1,'build':'release --locked','external_reference_hashes':{p.name:sha(p) for p in (ROOT/'tests/reference/external_mhd').glob('*')}}
    subprocess.run([cargo,'build','--release','--locked','--bins'],cwd=ROOT,check=True)
    binaries={name:ROOT/'target/release'/name for name in ('vector-potential','passive-voronoi')}
    provenance['binary_sha256']={name:sha(p) for name,p in binaries.items()}
    configs={}
    for n in (32,64,128,256):
        for jitter in (0.,.15):
            for comoving in (False,True):
                name=f'passive_n{n}_j{jitter}_m{int(comoving)}'; configs[name]=dict(case='passive',n=n,jitter=jitter,comoving=comoving)
    for n in (256,512,1024): configs[f'brio_n{n}']=dict(case='brio',n=n,jitter=0.)
    for n in (64,128,256):
        for jitter in (0.,.15):
            for boost in (False,True):
                name=f'vortex_n{n}_j{jitter}_b{int(boost)}';configs[name]=dict(case='vortex',n=n,jitter=jitter,boost=boost)
    dump(out/'manifest.json',configs);dump(out/'provenance.json',provenance)
    def run(name,c):
        p=out/name;p.mkdir(); passive=c['case']=='passive'
        cmd=[str(binaries['passive-voronoi' if passive else 'vector-potential']),'--n',str(c['n']),'--jitter',str(c['jitter']),'--output',str(p)]
        if passive:
            if c['comoving']: cmd+=['--comoving']
        else:
            cmd+=['--case',c['case'],'--profile',PROFILE,'--time','.1' if c['case']=='brio' else '.5']
            if c['case']=='brio': cmd+=['--ny','4']
            elif c['boost']: cmd+=['--motion','rigid','--mesh-x','2','--mesh-y','-1','--boost-x','2','--boost-y','-1']
        start=time.monotonic()
        with (p/'run.log').open('w') as log: result=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        r={'config':c,'command':cmd,'elapsed_seconds':time.monotonic()-start,'exit_code':result.returncode,'status':'completed' if result.returncode==0 else 'failed evolution'}
        if (p/'summary.json').exists(): r['summary']=json.loads((p/'summary.json').read_text())
        r['artifacts_sha256']={f.name:sha(f) for f in p.iterdir() if f.is_file()}
        return name,r
    runs={}
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures=[pool.submit(run,n,c) for n,c in configs.items()]
        for future in as_completed(futures):
            n,r=future.result();runs[n]=r;dump(out/'runs.json',runs);print(f"{n}: {r['status']}, {r['elapsed_seconds']:.2f}s",flush=True)
    dump(out/'summary.json',measure(out,runs))
    if sources!={str(p.relative_to(ROOT)):sha(p) for p in paths}:raise ValueError('study sources changed during execution')
    provenance['result_sha256']={n:sha(out/n) for n in ('manifest.json','runs.json','summary.json')};dump(out/'provenance.json',provenance)
    print(f'Measured packet: {out}',flush=True)
if __name__=='__main__':main()
