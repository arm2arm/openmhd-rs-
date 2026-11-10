#!/usr/bin/env python3
"""General A/gauge solver versus the unchanged M0 shock/vortex reference packet."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import csv
import gzip
import io
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess
import time

from physics_projection import polygons, shock_errors, vortex_bins
from run_m1_wave_loop import ROOT, dump, read_cells, sha, validate_parallelism

from run_m1_wave_loop import RIEMANN_SOLVERS, with_riemann, riemann_arguments, riemann_matches

PROFILE = 'bulk-frame-heun-spline-v1'
BOOST = (2., -1., 0.)
AMENDMENT = ROOT/'benchmarks/m1/shock-bx-amendment.json'


def mesh_family(c):
    """regular/columns keep the Brio y-invariance; planar jitter does not."""
    if c['jitter']==0.:return 'regular'
    return c.get('jitter_mode','planar')


def bx_gate(c,initial,cells):
    """Owner-approved amendment: gate Bx only where the mesh is y-invariant."""
    rule=json.loads(AMENDMENT.read_text())
    def errors(rows):
        volume=math.fsum(x['volume'] for x in rows)
        return dict(max=max(abs(x['bx']-.75) for x in rows),
                    L1=math.fsum(x['volume']*abs(x['bx']-.75) for x in rows)/volume)
    values=dict(initial=errors(initial),final=errors(cells))
    applies=mesh_family(c) in rule['bx_gate_meshes']
    return dict(values,gate_applies=applies,
                passed=values['final']['max']<=rule['bx_max_error'] if applies else None)


# The y-invariant column family is the amendment's nonuniform Brio control.
MESHES = {'brio-wu': ((0.,'planar'),(.15,'planar'),(.15,'columns')),
          'orszag-tang': ((0.,'planar'),(.15,'planar'))}


def configurations(quick=False, profile=PROFILE, riemann='hlld'):
    result = {}
    for case, ns in [('brio-wu', (64,128) if quick else (256,512,1024)),
                     ('orszag-tang', (16,32) if quick else (64,128,256))]:
        for n in ns:
            for jitter,mode in MESHES[case]:
                for boosted in (False, True):
                    name=f'{case}_n{n}_j{jitter}'+('c' if mode=='columns' else '')+('_boost' if boosted else '_base')
                    result[name]=dict(name=name, case=case, n=n, ny=4 if case=='brio-wu' else n,
                                      jitter=jitter, jitter_mode=mode, boost=list(BOOST if boosted else (0.,0.,0.)),
                                      time=.1 if case=='brio-wu' else .5, profile=profile)
    return with_riemann(result,riemann)


def reference(name):
    directory=ROOT/'tests/reference/external_mhd'
    metadata=json.loads((directory/'provenance.json').read_text())
    path=directory/name
    if sha(path)!=metadata['result_sha256'][name]:raise ValueError('changed independent reference')
    rows=[{k:float(v) for k,v in row.items()} for row in csv.DictReader(io.StringIO(gzip.decompress(path.read_bytes()).decode()))]
    if not rows or any(not math.isfinite(v) for r in rows for v in r.values()):raise ValueError('invalid reference')
    return rows,sha(path)


def case_scales(case):
    if case=='brio-wu':return dict(rho=1.,p=1.,vx=1.,by=1.,bx=1.,bz=1.)
    return dict(rho=25/(36*math.pi),p=5/(12*math.pi),bx=1/math.sqrt(4*math.pi),by=1/math.sqrt(4*math.pi),bz=1/math.sqrt(4*math.pi))


def initial_magnetic_error(cells,case):
    differences=[]
    for c in cells:
        expected=(.75, 1. if c['x']<1. else -1.,0.) if case=='brio-wu' else (
            -math.sin(2*math.pi*c['y'])/math.sqrt(4*math.pi),
            math.sin(4*math.pi*c['x'])/math.sqrt(4*math.pi),0.)
        differences.append(c['volume']*math.sqrt(sum((c[k]-v)**2 for k,v in zip(('bx','by','bz'),expected))))
    return math.fsum(differences)/math.fsum(c['volume'] for c in cells)


def boost_comparison(a,b,config,summary):
    if len(a)!=len(b) or not a:raise ValueError('incomplete boost pair')
    lengths=(2.,.125) if config['case']=='brio-wu' else (1.,1.)
    volume=math.fsum(c['volume'] for c in a)
    scales=case_scales(config['case'])
    speed=summary['initial']['budget_scales'][1]/summary['initial']['budget_scales'][0]
    scales.update(vx=scales.get('vx',speed),vy=speed,vz=speed,
                  energy=summary['initial']['budget_scales'][4]/volume)
    errors={k:[] for k in scales};position=0.;vol_error=0.
    for i,(x,y) in enumerate(zip(a,b)):
        if x['id']!=i or y['id']!=i or x['time']!=config['time'] or y['time']!=config['time']:
            raise ValueError('boost ID/time mismatch')
        for k,l in enumerate(lengths):
            coordinate=('x','y')[k]
            position=max(position,abs((y[coordinate]-x[coordinate]-BOOST[k]*config['time']+l/2)%l-l/2))
        vol_error=max(vol_error,abs(y['volume']/x['volume']-1))
        for field in scales:
            expected=x[field]
            if field in ('vx','vy','vz'):expected+=BOOST[('vx','vy','vz').index(field)]
            if field=='energy':expected+=x['rho']*(sum(BOOST[k]*x[f] for k,f in enumerate(('vx','vy','vz')))+.5*sum(v*v for v in BOOST))
            errors[field].append(x['volume']*abs(y[field]-expected)/scales[field])
    values={k:math.fsum(v)/volume for k,v in errors.items()}
    return dict(relative_L1=values,scales=scales,position_max=position,volume_relative_max=vol_error,
                passed=max(values.values())<=1e-8 and position<=1e-9 and vol_error<=1e-9)


def evaluate(output,configs,runs,quick,packet):
    profiles={c['profile'] for c in configs.values()}
    solvers={c.get('riemann_solver','hlld') for c in configs.values()}
    registered = (len(profiles)==1 and len(solvers)==1
                  and configs == configurations(quick,next(iter(profiles)),next(iter(solvers))))
    complete=set(runs)==set(configs) and all(r['status']=='completed' for r in runs.values())
    families=[];pairs=[]
    for case in ('brio-wu','orszag-tang'):
        gate=packet['cases'][case]['gate']
        for jitter,mode in MESHES[case]:
            names=sorted([n for n,c in configs.items() if c['case']==case and c['jitter']==jitter and c['jitter_mode']==mode and n.endswith('_base')],key=lambda n:configs[n]['n'])
            family=dict(case=case,jitter=jitter,jitter_mode=mode,names=names,
                        primary_profile_gate=jitter==0. or mode=='columns',status='unexecuted')
            if registered and not quick and len(names)==3 and all(runs.get(n,{}).get('status')=='completed' for n in names):
                limits=gate['finest_scaled_L1_max'] if case=='brio-wu' else gate['finest_scaled_bin_L1_max']
                first,last=(runs[n]['reference_errors'] for n in (names[0],names[-1]))
                checks={f:last[f]['L1']<=limit and last[f]['L1']<first[f]['L1'] for f,limit in limits.items()}
                family.update(status='pass' if all(checks.values()) else 'fail',checks=checks,finest_errors=last)
            families.append(family)
    for name,c in configs.items():
        if not name.endswith('_base'):continue
        other=name.removesuffix('_base')+'_boost'
        pair=dict(names=[name,other],status='unexecuted')
        if all(runs.get(n,{}).get('status')=='completed' for n in (name,other)):
            pair.update(boost_comparison(read_cells(output/name/'final.csv'),read_cells(output/other/'final.csv'),c,runs[name]['summary']))
            pair['status']='pass' if pair['passed'] else 'fail'
        pairs.append(pair)
    all_checks=registered and complete and all(r['state_and_diagnostic_gates'] for r in runs.values())
    passed=(not quick and all_checks and all(p['status']=='pass' for p in pairs)
            and all(f['status']=='pass' for f in families if f['primary_profile_gate']))
    return dict(complete=complete,registered_configuration=registered,completed_evolutions=sum(r['status']=='completed' for r in runs.values()),
                expected_evolutions=len(configs),quick=quick,profile_families=families,boost_pairs=pairs,
                state_and_diagnostic_gates=all_checks,all_registered_physics_gates=passed,
                scope='General solver M0 shock/vortex subset only; full M1 also requires wave/loop/mean-field gates. Planar-jittered profile errors are diagnostic per the original packet; planar-jitter Bx is diagnostic and the column family is gated per benchmarks/m1/shock-bx-amendment.json.')


def load_json(path):
    def reject(value):
        raise ValueError('nonfinite JSON constant: '+value)
    def number(value):
        result=float(value)
        if not math.isfinite(result):reject(value)
        return result
    return json.loads(path.read_text(), parse_constant=reject, parse_float=number)


def validate_run(c, summary, history, physics, geometry, initial, cells):
    if not riemann_matches(c,summary):raise ValueError('Riemann configuration/summary mismatch')
    lengths=[2.,.125] if c['case']=='brio-wu' else [1.,1.]
    gamma=2. if c['case']=='brio-wu' else 5/3
    expected=dict(case=c['case'],n=c['n'],jitter=c['jitter'],boost=c['boost'],
                  mesh_velocity=c['boost'][:2],motion='rigid',gamma=gamma,
                  profile=c['profile'],time=c['time'],requested_time=c['time'],completed=True,
                  mean_B=[.75,0.,0.] if c['case']=='brio-wu' else [0.,0.,0.],limited=True)
    if any(summary[k]!=v for k,v in expected.items()):raise ValueError('configuration/summary mismatch')
    if summary.get('jitter_mode','planar')!=c.get('jitter_mode','planar') or summary.get('ny',c['ny'])!=c['ny']:
        raise ValueError('mesh family/summary mismatch')
    if (physics['nx']!=c['n'] or physics['ny']!=c['ny'] or physics['lengths']!=lengths
        or geometry['lengths']!=lengths or geometry['time']!=c['time']):
        raise ValueError('configuration/geometry mismatch')
    for values,t in ((initial,0.),(cells,c['time'])):
        if len(values)!=c['n']*c['ny'] or any(x['time']!=t for x in values):raise ValueError('incomplete snapshot')
        if abs(math.fsum(x['volume'] for x in values)/(lengths[0]*lengths[1])-1)>1e-9:
            raise ValueError('snapshot domain volume mismatch')
    times=[h['time'] for h in history]
    if not times or times[0]!=0. or times[-1]!=c['time'] or any(a>=b for a,b in zip(times,times[1:])):
        raise ValueError('incomplete diagnostic history')
    if history[0]['diagnostics']!=summary['initial'] or history[-1]['diagnostics']!=summary['final']:
        raise ValueError('diagnostic history/summary mismatch')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--jobs',type=int,default=4)
    parser.add_argument('--threads',type=int,default=1,help='Threads per evolution; jobs*threads <= 24')
    parser.add_argument('--timeout',type=float,help='Wall seconds per evolution; a timeout fails the run')
    parser.add_argument('--quick',action='store_true')
    parser.add_argument('--calibration',action='store_true',help='Only the N128 jittered vortex at t=.5; no full acceptance')
    parser.add_argument('--profile',default=PROFILE,help='Evolution profile; the registered default is unchanged')
    parser.add_argument('--accelerated-projection',action='store_true',help='Cached projection solve; projected-rate profiles only')
    parser.add_argument('--projection-screening',type=float,default=0.,help='Opt-in damping kappa of the projected-rate correction; 0 is the exact projection')
    parser.add_argument('--riemann',choices=RIEMANN_SOLVERS,default='hlld')
    args=parser.parse_args()
    if not math.isfinite(args.projection_screening) or args.projection_screening<0:parser.error('projection screening must be >= 0')
    try:validate_parallelism(args.jobs,args.threads)
    except ValueError as error:parser.error(str(error))
    if args.calibration and args.quick:parser.error('calibration and quick are separate subsets')
    if args.timeout is not None and (not math.isfinite(args.timeout) or args.timeout<=0):parser.error('timeout must be finite and positive')
    output=args.output_dir.resolve()
    if output.exists():parser.error('Use a fresh output directory')
    output.mkdir(parents=True)
    refs={};hashes={}
    for case,name in [('brio-wu','brio_8192.csv.gz'),('orszag-tang','vortex_512.csv.gz')]:refs[case],hashes[name]=reference(name)
    if len(refs['brio-wu'])!=8192 or len(refs['orszag-tang'])!=4096:raise ValueError('wrong reference resolution')
    for i,r in enumerate(refs['orszag-tang']):
        if abs(r['x']-(i%64+.5)/64)>1e-12 or abs(r['y']-(i//64+.5)/64)>1e-12:raise ValueError('vortex reference coordinate mismatch')
    configs=configurations(args.quick,args.profile,args.riemann);packet=json.loads((ROOT/'benchmarks/m0/packet.json').read_text())
    if args.calibration:
        configs={n:c for n,c in configs.items() if c['case']=='orszag-tang' and c['n']==128
                 and c['jitter']==.15 and not any(c['boost'])}
    paths=sorted({*ROOT.glob('crates/**/*.rs'),*ROOT.glob('apps/**/*.rs'),*ROOT.glob('crates/*/Cargo.toml'),*ROOT.glob('apps/*/Cargo.toml'),
                  ROOT/'Cargo.toml',ROOT/'Cargo.lock',ROOT/'rust-toolchain.toml',Path(__file__).resolve(),ROOT/'scripts/physics_projection.py',
                  ROOT/'scripts/run_m1_wave_loop.py',ROOT/'benchmarks/m0/packet.json',AMENDMENT,ROOT/'docs/M1_PHYSICS_PLAN.md'})
    sources={str(p.relative_to(ROOT)):sha(p) for p in paths}
    cargo=shutil.which('cargo') or str(Path.home()/'.cargo/bin/cargo')
    subprocess.run([cargo,'build','--release','--locked','-p','openmhd','--bin','vector-potential'],cwd=ROOT,check=True)
    binary=ROOT/'target/release/vector-potential'
    provenance=dict(created_utc=datetime.now(timezone.utc).isoformat(),source_sha256=sources,binary_sha256=sha(binary),
                    reference_sha256=hashes,revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                    rustc=subprocess.check_output([str(Path(cargo).with_name('rustc')),'-Vv'],text=True),
                    platform=platform.platform(),python=platform.python_version(),jobs=args.jobs,threads_per_case=args.threads,
                    accelerated_projection=args.accelerated_projection,projection_screening=args.projection_screening,
                    timeout_seconds=args.timeout,
                    calibration=args.calibration,
                    units='M0 packet; dimensionless mu0=1, f64, periodic, no floors/resets')
    if args.riemann != 'hlld':provenance['riemann_solver']=args.riemann
    dump(output/'manifest.json',configs);dump(output/'provenance.json',provenance)

    def run(c):
        dest=output/c['name'];dest.mkdir()
        cmd=[str(binary),'--case',c['case'],'--profile',c['profile'],'--n',str(c['n']),'--jitter',str(c['jitter']),
             *(['--jitter-mode','columns'] if c['jitter_mode']=='columns' else []),'--time',str(c['time']),'--motion','rigid','--mesh-x',str(c['boost'][0]),'--mesh-y',str(c['boost'][1]),
             '--boost-x',str(c['boost'][0]),'--boost-y',str(c['boost'][1]),'--boost-z',str(c['boost'][2]),'--output',str(dest),
             '--threads',str(args.threads)]
        cmd+=riemann_arguments(c)
        if args.accelerated_projection:cmd+=['--accelerated-projection']
        if args.projection_screening:cmd+=['--projection-screening',str(args.projection_screening)]
        started=time.monotonic()
        r=dict(config=c,command=cmd,status='failed')
        try:
            with (dest/'run.log').open('w') as stream:
                done=subprocess.run(cmd,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=args.timeout)
            r['returncode']=done.returncode
            summary=load_json(dest/'summary.json');history=load_json(dest/'history.json')
            r.update(summary=summary,history=history)
            if done.returncode or not summary['completed'] or summary['time']!=c['time'] or summary['profile']!=c['profile']:
                raise ValueError('failed or mismatched evolution')
            if summary.get('projection_screening',0.)!=args.projection_screening:
                raise ValueError('screening configuration mismatch')
            cells=read_cells(dest/'final.csv');initial=read_cells(dest/'initial.csv')
            geometry=load_json(dest/'geometry.json');physics=load_json(dest/'physics.json')
            validate_run(c,summary,history,physics,geometry,initial,cells)
            pieces=polygons(geometry,cells,[b*c['time'] for b in c['boost'][:2]])
            dump(dest/'geometry_vertices.json',geometry)
            scales=case_scales(c['case'])
            # Remove the velocity boost before comparing with the stationary shock reference.
            rest=[dict(x,vx=x['vx']-c['boost'][0]) for x in cells]
            if c['case']=='brio-wu':errors=shock_errors(rest,pieces,refs[c['case']])
            else:
                values=vortex_bins(cells,pieces);dump(dest/'projected_bins.json',values)
                errors={f:{'L1':math.fsum(abs(a[f]-b[f]) for a,b in zip(values,refs[c['case']]))/4096/scales[f],
                           'L2':math.sqrt(math.fsum((a[f]-b[f])**2 for a,b in zip(values,refs[c['case']]))/4096)/scales[f]} for f in values[0]}
            positive=all(h['diagnostics']['rho_min']>0 and h['diagnostics']['p_min']>0 and max(map(abs,h['diagnostics']['normalized_budget']))<=packet['solver']['budget_tolerance'] for h in history)
            gate=packet['cases'][c['case']]['gate']
            if c['case']=='brio-wu':
                bx=bx_gate(c,initial,cells)
                values=dict(bx_max_error=bx['final']['max'],bx=bx,signal_travel_x=physics['signal_travel_x'])
                checks=dict(signal_tracking=physics['signal_tracking'],
                            seam_isolated=0<=values['signal_travel_x']<gate['seam_max_signal_travel'])
                # Planar jitter: recorded diagnostic only, never counted as a passed Bx gate.
                if bx['gate_applies']:checks['bx_preserved']=bx['passed']
            else:
                values=dict(mean_B_drift_over_Bscale_max=max(math.sqrt(sum(x*x for x in h['diagnostics']['mean_B_drift']))/scales['bx'] for h in history),
                            limited_face_dimensionless_divB_RMS_max=max(h['diagnostics']['div_B_limited']['dimensionless']['rms'] for h in history))
                checks={field:value<=gate[field] for field,value in values.items()}
            diagnostic=all(checks.values())
            r.update(status='completed',physics=physics,reference_errors=errors,initial_B_L1=initial_magnetic_error(initial,c['case']),
                     state_and_diagnostic_gates=positive and diagnostic,positive_and_conservative=positive,
                     diagnostic_gates=diagnostic,diagnostic_values=values,diagnostic_checks=checks)
        except subprocess.TimeoutExpired:r.update(status='timeout',error='Wall-time cap reached; incomplete execution')
        except (ValueError,KeyError,OSError) as e:r['error']=str(e)
        r['seconds']=time.monotonic()-started
        r['sha256']={p.name:sha(p) for p in dest.iterdir() if p.is_file()}
        return c['name'],r

    runs={}
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for future in as_completed([pool.submit(run,c) for c in configs.values()]):
            name,r=future.result();runs[name]=r;dump(output/'runs.json',runs)
            print(f'{len(runs)}/{len(configs)} {name}: {r["status"]} ({r["seconds"]:.1f}s)',flush=True)
    summary=evaluate(output,configs,runs,args.quick,packet)
    if args.riemann != 'hlld':summary['riemann_solver']=args.riemann
    dump(output/'summary.json',summary)
    if sources!={str(p.relative_to(ROOT)):sha(p) for p in paths}:raise ValueError('sources changed during study')
    provenance['result_sha256']={n:sha(output/n) for n in ('manifest.json','runs.json','summary.json')};dump(output/'provenance.json',provenance)


if __name__=='__main__':main()
