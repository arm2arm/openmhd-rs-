#!/usr/bin/env python3
"""REANA-only HLL/HLLD shock isolation; no default or acceptance-gate change."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from run_column_boost_repro import alternating, dump, row_variation, sha
from run_m1_wave_loop import read_cells, with_riemann
from run_m1_physics import boost_comparison, validate_run, reference, bx_gate, shock_errors
from physics_projection import polygons


def main():
    if sys.platform != 'linux':raise ValueError('Run on REANA Linux')
    root=Path(__file__).resolve().parents[1]
    source=Path(sys.argv[1]).resolve()
    original=json.loads(gzip.decompress(source.read_bytes()))
    out=root/'results/hll_shock_probe';out.mkdir(parents=True,exist_ok=False)
    binary=root/'target/release/vector-potential'
    refs,reference_sha=reference('brio_8192.csv.gz')
    report=dict(status='running',scientific_acceptance=False,
                scope='Controlled flux comparison on the original four finest regular/column shocks; no full M1 acceptance',
                started_utc=datetime.now(timezone.utc).isoformat(),
                binary_sha256=sha(binary),original_runs_sha256=sha(source),reference_sha256=reference_sha,
                jobs=8,threads_per_case=2,timeout_seconds=600,runs={},pairs=[])
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',RAYON_NUM_THREADS='1')
    names=[f'brio-wu_n1024_j{mesh}_{frame}' for mesh in ('0.0','0.15c') for frame in ('base','boost')]
    def run(solver,name):
        old=dict(original[name]);old['config']=with_riemann({'run':old['config']},solver)['run']
        dest=out/(solver+'_'+name);dest.mkdir();command=list(old['command'])
        command[0]=str(binary);command[command.index('--output')+1]=str(dest)
        if solver=='hll':command+=['--riemann','hll']
        command+=['--snapshot-stride','64']
        record=dict(status='running',solver=solver,config=old['config'],command=command)
        start=time.monotonic()
        try:
            with (dest/'run.log').open('w') as log:
                done=subprocess.run(command,env=env,cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=600)
            record['returncode']=done.returncode
            if done.returncode:raise ValueError('Evolution failed')
            load=lambda n:json.loads((dest/n).read_text())
            summary=load('summary.json');history=load('history.json');physics=load('physics.json');geometry=load('geometry.json')
            initial=read_cells(dest/'initial.csv');final=read_cells(dest/'final.csv')
            validate_run(old['config'],summary,history,physics,geometry,initial,final)
            if summary.get('riemann_solver','hlld') != ('hll-comparator-v1' if solver=='hll' else 'hlld'):
                raise ValueError('Incorrect flux metadata')
            positive=all(h['diagnostics']['rho_min']>0 and h['diagnostics']['p_min']>0
                         and max(map(abs,h['diagnostics']['normalized_budget']))<=1e-10 for h in history)
            bx=bx_gate(old['config'],initial,final)
            isolated=physics['signal_tracking'] and 0<=physics['signal_travel_x']<.45
            pieces=polygons(geometry,final,[b*.1 for b in old['config']['boost'][:2]])
            rest=[dict(c,vx=c['vx']-old['config']['boost'][0]) for c in final]
            errors=shock_errors(rest,pieces,refs)
            reference_pass=all(errors[k]['L1']<=v for k,v in dict(rho=.03,p=.04,vx=.03,by=.04).items())
            parity={n:sha(dest/n)==old['sha256'][n] for n in ('initial.csv','final.csv','history.json','summary.json','geometry.json','physics.json')}
            modes=[]
            for p in [dest/'initial.csv',*sorted(dest.glob('accepted_*.csv')),dest/'final.csv']:
                cells=read_cells(p);alt=alternating([r['vx'] for r in cells],1024)
                modes.append(dict(file=p.name,sha256=sha(p),time=cells[0]['time'],vx_alternating_max=max(map(abs,alt))))
            dump(dest/'row_modes.json',modes)
            record.update(status='completed',summary=summary,positive_and_conservative=positive,
                          bx=bx,seam_isolated=isolated,reference_errors=errors,reference_pass=reference_pass,
                          state_and_diagnostic_gates=positive and bx['passed'] and isolated,
                          scientific_file_parity=parity if solver=='hlld' else None,
                          final_row_variation=row_variation(final))
        except (ValueError,KeyError,OSError,subprocess.TimeoutExpired) as error:
            record.update(status='failed',error=f'{type(error).__name__}: {error}')
        record['seconds']=time.monotonic()-start
        record['sha256']={p.name:sha(p) for p in sorted(dest.iterdir()) if p.is_file()}
        return dest.name,record
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            for future in as_completed([pool.submit(run,s,n) for s in ('hlld','hll') for n in names]):
                name,row=future.result();report['runs'][name]=row;dump(out/'report.json',report)
                print(name,row['status'],row['seconds'],flush=True)
        controls=[r for r in report['runs'].values() if r['solver']=='hlld']
        if len(controls)!=4 or any(r['status']!='completed' or not all(r['scientific_file_parity'].values()) for r in controls):
            raise ValueError('Default control failed original scientific-file parity')
        for solver in ('hlld','hll'):
            for mesh in ('0.0','0.15c'):
                a=f'{solver}_brio-wu_n1024_j{mesh}_base';b=a.removesuffix('base')+'boost'
                if all(report['runs'][n]['status']=='completed' for n in (a,b)):
                    measured=boost_comparison(read_cells(out/a/'final.csv'),read_cells(out/b/'final.csv'),
                        report['runs'][a]['config'],report['runs'][a]['summary'])
                    report['pairs'].append(dict(solver=solver,mesh=mesh,**measured))
        candidate=[r for r in report['runs'].values() if r['solver']=='hll']
        pairs=[p for p in report['pairs'] if p['solver']=='hll']
        report['hll_bounded_pass']=len(candidate)==4 and len(pairs)==2 and all(p['passed'] for p in pairs) and all(
            r['status']=='completed' and r['state_and_diagnostic_gates'] and r['reference_pass'] for r in candidate)
        report['status']='completed'
    except Exception as error:report.update(status='failed',error=f'{type(error).__name__}: {error}')
    finally:
        report['ended_utc']=datetime.now(timezone.utc).isoformat();dump(out/'report.json',report)
        dump(out/'sha256.json',{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    return 0 if report['status']=='completed' else 1


if __name__=='__main__':raise SystemExit(main())
