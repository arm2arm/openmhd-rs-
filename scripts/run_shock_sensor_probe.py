#!/usr/bin/env python3
"""REANA-only 24-case shock-sensor comparison, retaining exact HLLD/HLL controls."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import csv
import gzip
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

from run_column_boost_repro import row_variation
from run_m1_wave_loop import dump, sha, read_cells, with_riemann, riemann_arguments
from run_m1_physics import validate_run, reference, bx_gate, boost_comparison, case_scales, load_json
from physics_projection import polygons, shock_errors, vortex_bins

SCIENCE=('initial.csv','final.csv','history.json','summary.json','geometry.json','physics.json')


def command_for(original,binary,dest,config):
    command=[str(binary)];skip=False
    for value in original[1:]:
        if skip:skip=False;continue
        if value in ('--output','--threads','--riemann','--snapshot-stride'):
            skip=True;continue
        if value=='--trace-frozen-rates':continue
        command.append(value)
    return [*command,*riemann_arguments(config),'--threads','2','--output',str(dest)]


def sensor_observation(path,config):
    rows=list(csv.DictReader(path.open()))
    if not rows:raise ValueError('missing final sensor faces')
    result={};factor='omega' if config['riemann_solver']=='hlld-pressure' else 'theta'
    active='HlldPressure' if factor=='omega' else 'HlldShock'
    groups=[('all',rows)]
    if config['case']=='brio-wu':
        groups.append(('slow_shock_window',[r for r in rows if 1.05<=(float(r['x'])-config['boost'][0]*config['time'])%2.<=1.25]))
    for label,selected in groups:
        for direction in ('x','y'):
            part=[r for r in selected if ('x' if abs(float(r['nx']))>=abs(float(r['ny'])) else 'y')==direction]
            if part:
                result[label+'_'+direction]=dict(faces=len(part),active=sum(r['method']==active for r in part),
                    **{factor+'_min':min(float(r[factor]) for r in part)},
                    max_mass_flux_change=max(abs(float(r['mass_new'])-float(r['mass_hlld'])) for r in part),
                    max_energy_flux_change=max(abs(float(r['energy_new'])-float(r['energy_hlld'])) for r in part))
    return result


def main(candidate_solver='hlld-shock',study='shock_sensor_probe'):
    if sys.platform!='linux':raise ValueError('Run all evolutions on REANA Linux')
    root=Path(__file__).resolve().parents[1];source=Path(sys.argv[1]).resolve()
    packet=json.loads(gzip.decompress(source.read_bytes()));controls=packet['controls']
    names=sorted(controls['hlld']);assert len(names)==8 and set(names)==set(controls['hll'])
    solvers=('hlld','hll',candidate_solver)
    if candidate_solver not in ('hlld-shock','hlld-pressure'):raise ValueError('Unsupported candidate')
    out=root/'results'/study;out.mkdir(parents=True,exist_ok=False)
    binary=root/'target/release/vector-potential'
    refs={};ref_hash={}
    for case,file in [('brio-wu','brio_8192.csv.gz'),('orszag-tang','vortex_512.csv.gz')]:
        refs[case],ref_hash[case]=reference(file)
    m0=load_json(root/'benchmarks/m0/packet.json')
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',RAYON_NUM_THREADS='1')
    report=dict(status='running',scientific_acceptance=False,started_utc=datetime.now(timezone.utc).isoformat(),
        binary_sha256=sha(binary),controls_sha256=sha(source),reference_sha256=ref_hash,
        jobs=8,threads_per_case=2,timeout_seconds=600,expected=24,candidate_solver=candidate_solver,runs={},pairs=[],
        scope='Finest regular/column shocks and regular/jitter N32 vortices only; no full M1 acceptance')
    def run(solver,name):
        old=controls[solver if solver in controls else 'hlld'][name]
        config=dict(old['config']);config.pop('riemann_solver',None)
        config=with_riemann({'run':config},solver)['run']
        dest=out/(solver+'_'+name);dest.mkdir();command=command_for(old['command'],binary,dest,config)
        record=dict(status='running',solver=solver,config=config,command=command);start=time.monotonic()
        try:
            with (dest/'run.log').open('w') as log:
                done=subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600)
            record['returncode']=done.returncode
            if done.returncode:raise ValueError('Evolution failed')
            summary=load_json(dest/'summary.json');history=load_json(dest/'history.json')
            physics=load_json(dest/'physics.json');geometry=load_json(dest/'geometry.json')
            initial=read_cells(dest/'initial.csv');final=read_cells(dest/'final.csv')
            validate_run(config,summary,history,physics,geometry,initial,final)
            if summary.get('projection_screening')!=1.:raise ValueError('screening mismatch')
            positive=all(h['diagnostics']['rho_min']>0 and h['diagnostics']['p_min']>0
                and max(map(abs,h['diagnostics']['normalized_budget']))<=m0['solver']['budget_tolerance'] for h in history)
            pieces=polygons(geometry,final,[b*config['time'] for b in config['boost'][:2]])
            if config['case']=='brio-wu':
                bx=bx_gate(config,initial,final);isolated=physics['signal_tracking'] and 0<=physics['signal_travel_x']<.45
                rest=[dict(c,vx=c['vx']-config['boost'][0]) for c in final]
                errors=shock_errors(rest,pieces,refs['brio-wu'])
                reference_pass=all(errors[k]['L1']<=v for k,v in m0['cases']['brio-wu']['gate']['finest_scaled_L1_max'].items())
                record.update(bx=bx,seam_isolated=isolated,reference_errors=errors,reference_pass=reference_pass,
                    diagnostic_pass=bx['passed'] and isolated,final_row_variation=row_variation(final))
            else:
                scales=case_scales('orszag-tang');values=vortex_bins(final,pieces);dump(dest/'projected_bins.json',values)
                errors={f:math.fsum(abs(a[f]-b[f]) for a,b in zip(values,refs['orszag-tang']))/4096/scales[f] for f in values[0]}
                diagnostics=dict(mean_B_drift_over_Bscale_max=max(math.sqrt(sum(x*x for x in h['diagnostics']['mean_B_drift']))/scales['bx'] for h in history),
                    limited_face_dimensionless_divB_RMS_max=max(h['diagnostics']['div_B_limited']['dimensionless']['rms'] for h in history))
                record.update(reference_errors=errors,reference_pass=True,reference_scope='N32 profile errors diagnostic; full ladder still required',
                    diagnostic_values=diagnostics,diagnostic_pass=all(v<=m0['cases']['orszag-tang']['gate'][k] for k,v in diagnostics.items()))
            record.update(status='completed',summary=summary,history=history,positive_and_conservative=positive,
                scientific_file_parity={f:sha(dest/f)==old['sha256'][f] for f in SCIENCE} if solver in controls else None)
            if solver==candidate_solver:record['sensor']=sensor_observation(dest/'final_shock_faces.csv',config)
        except (ValueError,KeyError,OSError,subprocess.TimeoutExpired) as error:
            record.update(status='failed',error=f'{type(error).__name__}: {error}')
        record['seconds']=time.monotonic()-start
        record['sha256']={p.name:sha(p) for p in sorted(dest.iterdir()) if p.is_file()}
        return dest.name,record
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            for future in as_completed([pool.submit(run,s,n) for s in solvers for n in names]):
                name,row=future.result();report['runs'][name]=row;dump(out/'report.json',report)
                print(name,row['status'],round(row['seconds'],2),row.get('error',''),flush=True)
        old_runs=[r for r in report['runs'].values() if r['solver'] in controls]
        if len(old_runs)!=16 or any(r['status']!='completed' or not all(r['scientific_file_parity'].values()) for r in old_runs):
            raise ValueError('Historical HLLD/HLL control parity failed')
        for solver in solvers:
            for name in names:
                if not name.endswith('_base'):continue
                a=solver+'_'+name;b=a.removesuffix('_base')+'_boost';r=report['runs'][a]
                pair=dict(solver=solver,names=[a,b],passed=False)
                if all(report['runs'][n]['status']=='completed' for n in (a,b)):
                    pair.update(boost_comparison(read_cells(out/a/'final.csv'),read_cells(out/b/'final.csv'),r['config'],r['summary']))
                report['pairs'].append(pair)
        candidate=[r for r in report['runs'].values() if r['solver']==candidate_solver]
        pairs=[p for p in report['pairs'] if p['solver']==candidate_solver]
        report['candidate_bounded_pass']=len(candidate)==8 and len(pairs)==4 and all(p['passed'] for p in pairs) and all(
            r['status']=='completed' and r['positive_and_conservative'] and r['diagnostic_pass'] and r['reference_pass'] for r in candidate)
        report['control_parity_files']=sum(sum(r['scientific_file_parity'].values()) for r in old_runs)
        report['status']='completed'
    except Exception as error:report.update(status='failed',error=f'{type(error).__name__}: {error}')
    finally:
        report['ended_utc']=datetime.now(timezone.utc).isoformat();dump(out/'report.json',report)
        dump(out/'sha256.json',{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    return 0 if report['status']=='completed' else 1


if __name__=='__main__':raise SystemExit(main())
