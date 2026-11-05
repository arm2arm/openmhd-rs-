#!/usr/bin/env python3
"""Bounded prospective quadratic-A experiment, not the full M1 acceptance suite."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import hashlib,json,subprocess,time,platform
from pathlib import Path
from run_m1_wave_loop import read_cells,physical_errors
from m1_mesh_cache import prepare
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',required=True,type=Path);p.add_argument('--mesh-cache-dir',required=True,type=Path);p.add_argument('--jobs',type=int,default=2);p.add_argument('--profile',choices=('bulk-frame-hll-quadratic-v1','bulk-frame-hll-consistent-v1','bulk-frame-hll-matched-v1','bulk-frame-hll-compact-v1','bulk-frame-hll-projected-v1'),default='bulk-frame-hll-quadratic-v1');args=p.parse_args();out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
 if (out/'provenance.json').exists():raise ValueError('fresh output directory required')
 cargo=str(Path.home()/'.cargo/bin/cargo');subprocess.run([cargo,'build','--release','--locked','--bin','vector-potential'],cwd=ROOT,check=True);binary=ROOT/'target/release/vector-potential'
 configs={f'n{n}':{'case':'alfven','n':n,'jitter':.15} for n in (32,64,128,256)};caches=prepare(binary,configs,args.mesh_cache_dir,args.jobs)
 paths=sorted({*ROOT.glob('crates/*/src/**/*.rs'),ROOT/'apps/openmhd/src/bin/vector-potential.rs',ROOT/'docs/M1_COMPLETION_PLAN.md',Path(__file__).resolve(),ROOT/'scripts/run_m1_wave_loop.py',ROOT/'scripts/m1_mesh_cache.py',ROOT/'Cargo.toml',ROOT/'Cargo.lock',ROOT/'rust-toolchain.toml',*ROOT.glob('crates/*/Cargo.toml'),*ROOT.glob('apps/*/Cargo.toml')})
 sources={str(p.relative_to(ROOT)):sha(p) for p in paths}
 prov={'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'created_utc':datetime.now(timezone.utc).isoformat(),'binary_sha256':sha(binary),'source_sha256':sources,'dirty_status':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True).strip(),'rustc':subprocess.check_output([str(Path(cargo).with_name('rustc')),'-Vv'],text=True).strip(),'platform':platform.platform(),'profile':args.profile,'mesh_caches':caches,'scope':'quadratic reconstruction hypothesis, fixed jittered travelling wave only; full original gates unchanged'}
 dump(out/'provenance.json',prov);dump(out/'manifest.json',configs)
 def run(name,c):
  dest=out/name;dest.mkdir();cmd=[str(binary),'--profile',args.profile,'--case','alfven','--n',str(c['n']),'--jitter','.15','--time','1','--checkpoint','.25','--mesh-cache',caches[name]['path'],'--output',str(dest)]
  if sha(binary)!=prov['binary_sha256']:raise ValueError('probe binary changed before launch')
  start=time.monotonic()
  with (dest/'run.log').open('w') as f:r=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  record={'config':c,'command':cmd,'elapsed_seconds':time.monotonic()-start,'exit_code':r.returncode,'status':'completed' if r.returncode==0 else 'failed evolution'}
  if (dest/'summary.json').exists():record['summary']=json.loads((dest/'summary.json').read_text())
  if r.returncode==0 and any(not (dest/n).is_file() for n in ('summary.json','initial.csv','checkpoint_0.25000000.csv','final.csv')):raise ValueError('successful probe missing required artifacts')
  record['sha256']={p.name:sha(p) for p in dest.iterdir() if p.is_file()}
  for stage,t in [('initial',0.),('checkpoint_0.25000000',.25),('final',record.get('summary',{}).get('time',0.))]:
   if (dest/f'{stage}.csv').exists():
    cells=read_cells(dest/f'{stage}.csv')
    if len(cells)!=c['n']**2 or any(row['time']!=t for row in cells):raise ValueError('probe cell count/time mismatch')
    record[stage+'_error']=physical_errors(cells,t,'alfven',0.,[0.,0.,0.])
  if r.returncode==0:
   expected={'profile':args.profile,'case':'alfven','nx':c['n'],'ny':c['n'],'jitter':.15,'time':1.,'requested_time':1.,'completed':True,'motion':'fixed','boost':[0,0,0],'mean_B':[1,0,0],'gamma':5/3,'limited':True}
   if any(record['summary'][k]!=v for k,v in expected.items()):raise ValueError('probe configuration mismatch')
  return name,record
 runs={}
 with ThreadPoolExecutor(max_workers=args.jobs) as pool:
  for future in as_completed([pool.submit(run,n,c) for n,c in configs.items()]):
   name,r=future.result();runs[name]=r;dump(out/'runs.json',runs);print(name,r['status'],r['elapsed_seconds'],r.get('final_error',{}).get('B'),flush=True)
 if sha(binary)!=prov['binary_sha256']:raise ValueError('probe binary changed during execution')
 if any(sha(Path(c['path']))!=c['sha256'] for c in caches.values()):raise ValueError('probe mesh cache changed')
 if sources!={str(p.relative_to(ROOT)):sha(p) for p in paths}:raise ValueError('probe source changed')
 prov['result_sha256']={n:sha(out/n) for n in ('manifest.json','runs.json')};dump(out/'provenance.json',prov)
if __name__=='__main__':main()
