#!/usr/bin/env python3
"""Separate fixed/rigid regular/jittered Voronoi prescribed-flow loop packet."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess
import time
from run_m1_wave_loop import ROOT, BOOST, dump, norms, physical_errors, read_cells, read_snapshot, sha

AMPLITUDE = .001/math.sqrt(4*math.pi)


def diagnostics(cells):
    volume = sum(c['volume'] for c in cells)
    result = {'magnetic_energy': sum(.5*c['volume']*sum(c[k]**2 for k in ('bx','by','bz')) for c in cells),
              'A_integral': sum(c['volume']*c['az'] for c in cells),
              'A_min': min(c['az'] for c in cells), 'A_max': max(c['az'] for c in cells)}
    for key in ('div_b_ls', 'div_b_face', 'div_b_limited'):
        scaled = [math.sqrt(c['volume']/math.pi)*c[key]/(math.sqrt(sum(c[k]**2 for k in ('bx','by','bz')))+1e-12*AMPLITUDE) for c in cells]
        result[key] = {'dimensional': norms([c[key] for c in cells],cells),
                       'dimensionless': norms(scaled,cells),
                       'signed_mean':sum(c['volume']*c[key] for c in cells)/volume}
    return result


def pair_errors(a,b):
    if len(a)!=len(b):
        raise ValueError('cell-count mismatch')
    return {'A':norms([x['az']-y['az'] for x,y in zip(a,b)],a),
            'B':norms([math.sqrt(sum((x[k]-y[k])**2 for k in ('bx','by','bz'))) for x,y in zip(a,b)],a)}


def evaluate(output,runs,pairs):
    for pair in pairs:
        names=pair['names']
        if any(runs[n]['status']!='completed' for n in names):
            pair['status']='failed evolution'; continue
        a,b=[read_snapshot(output/n/'final.csv',runs[n]['config']['n'],1.) for n in names]
        pair['errors']=pair_errors(a,b)
        pair['position_max']=max(abs((y[k]-x[k]-shift+.5)%1-.5) for x,y in zip(a,b) for k,shift in zip(('x','y'),BOOST))
        pair['relative_volume_max']=max(abs(x['volume']-y['volume'])/x['volume'] for x,y in zip(a,b))
        pair['pairing_valid']=all(c['time']==1. for c in a+b) and max(pair['position_max'],pair['relative_volume_max'])<=1e-11
        # This is a separate prospective constant-flow covariance check.
        pair['status']='pass' if pair['pairing_valid'] and pair['errors']['A']['max']/(.3*AMPLITUDE)<=1e-10 and pair['errors']['B']['max']/AMPLITUDE<=1e-10 else 'fail'
    fixed=[]
    for jitter in (0.,.15):
        selected=sorted([r for n,r in runs.items() if n.endswith('_base') and r['config']['jitter']==jitter and r['config']['motion']=='fixed'],key=lambda r:r['config']['n'])
        rows=[]
        for r in selected:
            error=r.get('errors',{}).get('passive_A',{}).get('L1')
            valid=error is not None and math.isfinite(error) and error>=0.
            rows.append({'n':r['config']['n'],'status':r['status'] if valid else 'failed: missing/invalid A error',
                         'A_L1_over_peak':error/(.3*AMPLITUDE) if valid and r['status']=='completed' else None})
        gate='unexecuted: requires N32/64/128/256'
        if any(r['status']!='completed' for r in rows):
            gate='fail: evolution'
        elif [r['n'] for r in rows]==[32,64,128,256]:
            gate='pass' if all(a['A_L1_over_peak']>b['A_L1_over_peak'] for a,b in zip(rows,rows[1:])) and rows[-1]['A_L1_over_peak']<=.1 else 'fail'
        fixed.append({'jitter':jitter,'rows':rows,'gate':gate})
    return {'scope':'constant prescribed flow; no gas/EOS/budget evolution; not coupled MHD',
            'pairs':pairs,'fixed_convergence':fixed,'runs':runs}


def reanalyze(output):
    original=output/'execution_provenance.json'
    if not original.exists(): shutil.copyfile(output/'provenance.json',original)
    execution=json.loads(original.read_text())
    for name in ('runs.json','manifest.json'):
        if sha(output/name)!=execution['result_sha256'][name]: raise ValueError(f'changed execution {name}')
    immutable=output/'execution_summary.json'
    if not immutable.exists():
        if sha(output/'summary.json')!=execution['result_sha256']['summary.json']: raise ValueError('missing original summary')
        shutil.copyfile(output/'summary.json',immutable)
    if sha(immutable)!=execution['result_sha256']['summary.json']: raise ValueError('changed immutable summary')
    old=json.loads(immutable.read_text());runs=json.loads((output/'runs.json').read_text())
    pairs=[{k:p[k] for k in ('names','n','jitter','motion')} for p in old['pairs']]
    for name,record in runs.items():
        for filename,digest in record['sha256'].items():
            if sha(output/name/filename)!=digest: raise ValueError(f'changed raw file {name}/{filename}')
        c=record['config']
        if 'summary' not in record: continue
        initial,final=[read_snapshot(output/name/f'{s}.csv',c['n'],t) for s,t in [('initial',0.),('final',record['summary']['time'])]]
        if not record['summary']['completed'] or record['summary']['time']!=1.: record['status']='failed evolution'
        record['errors']=physical_errors(final,record['summary']['time'],'loop',0.,c['boost'])
        record['errors']['reference_scope']='exact prescribed-flow transport; cusp/edge excluded for B'
        record['diagnostics']={stage:diagnostics(cells) for stage,cells in [('initial',initial),('final',final)]}
        if c['motion']=='comoving':
            record['discrete_drift']=pair_errors(initial,final)
            record['comoving_gate']='pass' if record['status']=='completed' and record['discrete_drift']['A']['max']/(.3*AMPLITUDE)<=1e-10 and record['discrete_drift']['B']['max']/AMPLITUDE<=1e-10 else 'fail'
    dump(output/'summary.json',evaluate(output,runs,pairs))
    dump(output/'measurement_provenance.json',{'execution_provenance_sha256':sha(original),'execution_revision':execution['revision'],
         'measurement_source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__).resolve(),ROOT/'scripts/run_m1_wave_loop.py')},
         'execution_summary_sha256':sha(immutable),'summary_sha256':sha(output/'summary.json'),
         'note':'No evolution rerun; validated raw hashes, full cell counts, times and unit-domain volumes.'})
    print(f'Remeasured verified prescribed-flow packet: {output}')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quick',action='store_true')
    parser.add_argument('--analyze-only',action='store_true')
    parser.add_argument('--jobs',type=int,default=4)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'results/prescribed_loop')
    args=parser.parse_args()
    if args.jobs<1: parser.error('jobs must be positive')
    output=args.output_dir.resolve();output.mkdir(parents=True,exist_ok=True)
    if args.analyze_only:
        reanalyze(output); return
    if (output/'manifest.json').exists(): raise SystemExit('Choose a fresh output directory.')
    cargo=shutil.which('cargo') or str(Path.home()/'.cargo/bin/cargo')
    command=lambda c:subprocess.check_output(c,cwd=ROOT,text=True).strip()
    sources=sorted({*ROOT.glob('crates/**/*.rs'),*ROOT.glob('apps/**/*.rs'),*ROOT.glob('crates/*/Cargo.toml'),*ROOT.glob('apps/*/Cargo.toml'),
                    ROOT/'Cargo.toml',ROOT/'Cargo.lock',ROOT/'rust-toolchain.toml',ROOT/'benchmarks/m1/packet-v2.json',ROOT/'docs/M1_COMPLETION_PLAN.md',Path(__file__).resolve(),ROOT/'scripts/run_m1_wave_loop.py'})
    provenance={'created_utc':datetime.now(timezone.utc).isoformat(),'revision':command(['git','rev-parse','HEAD']),
                'dirty_status':command(['git','status','--short']),'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources},
                'platform':platform.platform(),'rustc':command([str(Path(cargo).with_name('rustc')),'-Vv']),
                'config':{'units':'dimensionless, mu0=1','precision':'f64','EOS':'not used; prescribed flow',
                          'geometry':'periodic unit-square ordered clipping Voronoi','cfl':.3,'integrator':'Heun',
                          'gas_evolution':False,'magnetic_scale':AMPLITUDE,'divergence_floor':1e-12*AMPLITUDE,
                          'jobs':args.jobs,'ranks_per_run':1,'threads_per_run':1,'quick':args.quick}}
    subprocess.run([cargo,'build','--release','--locked','-p','openmhd','--bin','prescribed-loop'],cwd=ROOT,check=True)
    metadata=json.loads(command([cargo,'metadata','--no-deps','--format-version','1']))
    binary=Path(metadata['target_directory'])/'release/prescribed-loop';provenance['binary_sha256']=sha(binary)
    configs={};pairs=[]
    for jitter in (0.,.15):
        for motion in ('fixed','comoving'):
            for n in ((32,64) if args.quick else (32,64,128,256)):
                names=[]
                for boosted in (False,True):
                    name=f'loop_j{jitter}_{motion}_n{n}'+('_boost' if boosted else '_base')
                    b=BOOST[:2] if boosted else (0.,0.)
                    v=[2.+b[0],1.+b[1]];w=list(v) if motion=='comoving' else list(b)
                    configs[name]={'n':n,'jitter':jitter,'motion':motion,'velocity':v,'mesh_velocity':w,'boost':[b[0],b[1],0.]}
                    names.append(name)
                pairs.append({'names':names,'n':n,'jitter':jitter,'motion':motion})
    dump(output/'manifest.json',configs);dump(output/'provenance.json',provenance)
    def run(name,c):
        dest=output/name;dest.mkdir()
        cmd=[str(binary),'--n',str(c['n']),'--jitter',str(c['jitter']),'--time','1','--vx',str(c['velocity'][0]),'--vy',str(c['velocity'][1]),'--mesh-x',str(c['mesh_velocity'][0]),'--mesh-y',str(c['mesh_velocity'][1]),'--output',str(dest)]
        start=time.monotonic()
        with (dest/'run.log').open('w') as log: completed=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        record={'config':c,'command':cmd,'returncode':completed.returncode,'seconds':time.monotonic()-start,'status':'completed' if completed.returncode==0 else 'failed'}
        try:
            if (dest/'summary.json').exists():
                record['summary']=json.loads((dest/'summary.json').read_text())
                initial,final=[read_snapshot(dest/f'{s}.csv',c['n'],t) for s,t in [('initial',0.),('final',record['summary']['time'])]]
                if not record['summary']['completed'] or record['summary']['time']!=1. or any(c['time']!=1. for c in final): record['status']='failed'
                record['errors']=physical_errors(final,record['summary']['time'],'loop',0.,c['boost'])
                record['errors']['reference_scope']='exact prescribed-flow transport; cusp/edge excluded for B'
                record['diagnostics']={stage:diagnostics(cells) for stage,cells in [('initial',initial),('final',final)]}
                if c['motion']=='comoving':
                    record['discrete_drift']=pair_errors(initial,final)
                    record['comoving_gate']='pass' if record['status']=='completed' and record['discrete_drift']['A']['max']/(.3*AMPLITUDE)<=1e-10 and record['discrete_drift']['B']['max']/AMPLITUDE<=1e-10 else 'fail'
            else:
                raise ValueError('missing run summary')
        except (ValueError, KeyError, OSError) as error:
            record['status']='failed snapshot validation';record['validation_error']=str(error)
        record['sha256']={p.name:sha(p) for p in dest.iterdir() if p.is_file()}
        return name,record
    runs={}
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures=[pool.submit(run,n,c) for n,c in configs.items()]
        for future in as_completed(futures):
            n,r=future.result();runs[n]=r;dump(output/'runs.json',runs)
            print(f'{n}: {r["status"]}, {r["seconds"]:.2f}s',flush=True)
    dump(output/'summary.json',evaluate(output,runs,pairs))
    if provenance['source_sha256']!={str(p.relative_to(ROOT)):sha(p) for p in sources}: raise ValueError('sources changed during execution')
    provenance['result_sha256']={n:sha(output/n) for n in ('manifest.json','runs.json','summary.json')}
    dump(output/'provenance.json',provenance)
    print(f'Results: {output}',flush=True)


if __name__=='__main__': main()
