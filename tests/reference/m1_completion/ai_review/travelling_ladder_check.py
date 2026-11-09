#!/usr/bin/env python3
"""Interim read-only AI review: 12 completed fixed-grid travelling-wave runs.

No simulation or production measurement code is called. The root packets may
still grow; only the named completed run records and checked input hashes enter
the resulting interim report. Requires NumPy; no plotting dependency.
"""
import argparse,hashlib,json,math
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
parser=argparse.ArgumentParser();parser.add_argument('original',type=Path);parser.add_argument('signal',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def norm(a,v):
    if a.ndim>1:a=np.sqrt(np.sum(a*a,axis=1))
    total=math.fsum(v)
    return {'L1':math.fsum(np.abs(a)*v)/total,'L2':math.sqrt(math.fsum(a*a*v)/total),'max':float(np.max(np.abs(a)))}
def fit(ns,errors):
    x=np.array([math.log(1/n) for n in ns]);y=np.log(errors);xm=x.mean();ym=y.mean()
    p=float(np.sum((x-xm)*(y-ym))/np.sum((x-xm)**2));residual=float(np.sum((y-ym-p*(x-xm))**2))
    return {'order':p,'residual_slope_SE':math.sqrt(residual/(len(ns)-2)/float(np.sum((x-xm)**2))),
            'adjacent_orders':[math.log2(a/b) for a,b in zip(errors,errors[1:])]}
def read(path,n,time):
    with path.open() as f:keys=f.readline().strip().split(',')
    table=np.loadtxt(path,delimiter=',',skiprows=1);assert table.shape==(n*n,len(keys)) and np.isfinite(table).all()
    d={k:table[:,i] for i,k in enumerate(keys)}
    assert np.array_equal(d['id'],np.arange(n*n)) and np.all(d['time']==time)
    assert np.all(d['volume']>0) and abs(math.fsum(d['volume'])-1)<1e-9
    assert np.all((d['x']>=0)&(d['x']<1)&(d['y']>=0)&(d['y']<1))
    return d

def measure(d,t):
    x=d['x'];v=d['volume'];angle=[2*math.pi*(xx+t) for xx in x]
    sine=np.array([math.sin(a) for a in angle]);cosine=np.array([math.cos(a) for a in angle])
    exact_b=np.column_stack([np.ones(len(x)),.1*sine,.1*cosine]);exact_v=np.column_stack([np.zeros(len(x)),.1*sine,.1*cosine])
    b=np.column_stack([d[k] for k in ('bx','by','bz')]);velocity=np.column_stack([d[k] for k in ('vx','vy','vz')]);eb=b-exact_b;ev=velocity-exact_v
    errors={'B':norm(eb,v),'v':norm(ev,v)}
    errors.update({k:norm(eb[:,i],v) for i,k in enumerate(('bx','by','bz'))});errors.update({k:norm(ev[:,i],v) for i,k in enumerate(('vx','vy','vz'))})
    extra={'rho_error':norm(d['rho']-1,v),'pressure_error':norm(d['p']-.1,v),
           'transverse_radial_error':norm(eb[:,1]*sine+eb[:,2]*cosine,v),
           'transverse_quadrature_error':norm(eb[:,1]*cosine-eb[:,2]*sine,v),
           'divergence':{k:norm(d[k],v) for k in ('div_b_ls','div_b_face','div_b_limited','div_a','phi')}}
    return errors,extra
report={'scope':'Interim independent AI review of completed travelling fixed-grid base ladders only; root packets still running, full review pending',
        'created_utc':datetime.now(timezone.utc).isoformat(),'numpy':np.__version__,'runs':{},'fits':{},'source_inputs':{}}
for root,profile in [(args.original,'paper-global-v2'),(args.signal,'bulk-frame-signal-v1')]:
    records=json.loads((root/'runs.json').read_text());manifest=json.loads((root/'manifest.json').read_text());provenance=json.loads((root/'provenance.json').read_text());checkout=root.parent.parent
    for name,digest in provenance['source_sha256'].items():assert sha(checkout/name)==digest,(profile,name)
    assert sha(checkout/'target/release/vector-potential')==provenance['binary_sha256']
    report['source_inputs'][profile]={'checkout':str(checkout),'revision':provenance['revision'],'configuration':provenance['configuration'],'source_sha256':provenance['source_sha256'],'binary_sha256':provenance['binary_sha256']}
    for jitter in (0.,.15):
        ladder=[]
        for n in (64,128,256):
            name=f'alfven_{profile}_v0.0_j{jitter}_fixed_n{n}_base';r=records[name];c=r['config'];s=r['summary']
            assert c==manifest[name] and r['status']=='completed' and r['returncode']==0
            assert s['completed'] and s['time']==s['requested_time']==1 and s['case']=='alfven' and s['profile']==profile
            assert s['n']==n and s['jitter']==jitter and s['parallel_velocity']==0 and s['mesh_velocity']==[0,0] and s['boost']==[0,0,0]
            assert s['gamma']==5/3 and s['mean_B']==[1,0,0] and s['limited'] and s['motion']=='rigid' and s['dt_cap'] is None
            assert json.loads((root/name/'summary.json').read_text())==s
            for filename,digest in r['sha256'].items():assert sha(root/name/filename)==digest,(name,filename)
            measured={};initial=None;final=None
            for stage,filename,time in [('initial','initial.csv',0.),('t0.25','checkpoint_0.25000000.csv',.25),('final','final.csv',1.)]:
                d=read(root/name/filename,n,time);errors,extra=measure(d,time)
                for key,norms in errors.items():
                    for normname,value in norms.items():assert math.isclose(value,r['errors'][stage][key][normname],rel_tol=3e-11,abs_tol=1e-17),(name,stage,key,normname,value,r['errors'][stage][key][normname])
                if initial is None:
                    initial=d
                    exact=np.column_stack([np.zeros(n*n),[.1/(2*math.pi)*math.sin(2*math.pi*x) for x in d['x']],[.1/(2*math.pi)*math.cos(2*math.pi*x) for x in d['x']]])
                    numerical=np.column_stack([d[k] for k in ('ax','ay','az')]);extra['analytic_initial_A_max']=float(np.max(np.abs(numerical-exact)))
                    assert extra['analytic_initial_A_max']<1e-16 and errors['v']['max']<1e-15
                else:
                    assert all(np.array_equal(d[k],initial[k]) for k in ('id','x','y','volume')),(name,stage,'fixed geometry changed')
                diagnostic=next(h['diagnostics'] for h in r['history'] if h['time']==time)
                for column,label in [('div_b_ls','div_B_ls'),('div_b_face','div_B_face'),('div_b_limited','div_B_limited')]:
                    assert math.isclose(extra['divergence'][column]['L2'],diagnostic[label]['dimensional']['rms'],rel_tol=3e-11,abs_tol=1e-16)
                extra['reported_conditions']={k:diagnostic[k] for k in ('neighbour_condition','face_condition')}
                extra['reported_normalized_budget']=diagnostic['normalized_budget']
                measured[stage]={'norms':errors,**extra};final=d
            v=initial['volume'];a=initial['bx']-1;b=final['bx']-1
            correlation=float(np.sum(v*a*b)/math.sqrt(np.sum(v*a*a)*np.sum(v*b*b))) if np.any(a) else None
            snapshot={'config':c,'command':r['command'],'input_sha256':r['sha256'],'summary':{k:value for k,value in s.items() if k!='auxiliary_roots'},
                      'auxiliary_roots_set':sorted(set(s['auxiliary_roots'])),'source_record_status':r['status'],'source_record_positive_and_conservative':r['positive_and_conservative'],
                      'measurements':measured,'initial_final_bx_uncentred_correlation':correlation}
            report['runs'][name]=snapshot;ladder.append(snapshot)
            print(f"{profile} j={jitter} N={n}: B L1 initial={measured['initial']['norms']['B']['L1']:.12e}, quarter={measured['t0.25']['norms']['B']['L1']:.12e}, final={measured['final']['norms']['B']['L1']:.12e}; initial A max={measured['initial']['analytic_initial_A_max']:.2e}; fallback={s['hll_fallbacks']}",flush=True)
        result={stage:fit([64,128,256],[r['measurements'][stage]['norms']['B']['L1'] for r in ladder]) for stage in ('initial','t0.25','final')};report['fits'][f'{profile}_j{jitter}']=result
        print('FITS',profile,jitter,json.dumps(result),flush=True)
args.output.write_text(json.dumps(report,indent=2)+'\n')
print('All 12 completed run inputs verified; all 36 snapshots independently remeasured. No simulation was run. Full packet review remains pending.')
