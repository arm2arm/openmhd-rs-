"""Independent partial physics boost reduction from downloaded raw snapshots."""
from pathlib import Path
import argparse,gzip,hashlib,json,math
import numpy as np
root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('raw',type=Path);args=parser.parse_args();p=args.raw
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
run_bytes=gzip.decompress((root/'runs.json.gz').read_bytes())
runs=json.loads(run_bytes)
pairs=[];pending=[]
for name,a in runs.items():
    if not name.endswith('_base') or a['status']!='completed':continue
    other=name.removesuffix('_base')+'_boost'
    if other not in runs or runs[other]['status']!='completed':pending.append([name,other]);continue
    b=runs[other];c=a['config'];boost=np.array(b['config']['boost']);assert list(boost)==[2.,-1.,0.] and c['boost']==[0.,0.,0.]
    arrays=[]
    for n,row in ((name,a),(other,b)):
        f=p/n/'final.csv';assert sha(f)==row['sha256']['final.csv']
        d=np.genfromtxt(f,names=True,delimiter=',');assert np.array_equal(d['id'],np.arange(c['n']*c['ny']))
        assert (d['time']==c['time']).all() and all(np.isfinite(d[k]).all() for k in d.dtype.names)
        assert (d['volume']>0).all();arrays.append(d)
    x,y=arrays;volume=float(sum(x['volume']));s=a['summary']['initial']
    speed=s['budget_scales'][1]/s['budget_scales'][0]
    scales=dict(rho=1.,p=1.,vx=1.,by=1.,bx=1.,bz=1.) if c['case']=='brio-wu' else dict(rho=25/(36*math.pi),p=5/(12*math.pi),bx=1/math.sqrt(4*math.pi),by=1/math.sqrt(4*math.pi),bz=1/math.sqrt(4*math.pi))
    scales.update(vx=scales.get('vx',speed),vy=speed,vz=speed,energy=s['budget_scales'][4]/volume)
    relative={}
    for k,scale in scales.items():
        expected=x[k].copy()
        if k in ('vx','vy','vz'):expected+=boost[('vx','vy','vz').index(k)]
        if k=='energy':expected+=x['rho']*(sum(x[k]*v for k,v in zip(('vx','vy','vz'),boost))+.5*sum(boost**2))
        relative[k]=float(np.dot(x['volume'],abs(y[k]-expected))/volume)/scale
    lengths=(2.,.125) if c['case']=='brio-wu' else (1.,1.)
    position=max(float(max(abs((y[k]-x[k]-v*c['time']+l/2)%l-l/2))) for k,v,l in zip(('x','y'),boost,lengths))
    volumes=float(max(abs(y['volume']/x['volume']-1)))
    state=all(r.get('state_and_diagnostic_gates') for r in (a,b))
    passed=max(relative.values())<=1e-8 and position<=1e-9 and volumes<=1e-9 and state
    pairs.append(dict(names=[name,other],relative_L1=relative,position_max=position,volume_relative_max=volumes,state_and_diagnostic_gates=state,passed=passed))
failed_runs=[dict(name=n,status=r['status'],error=r.get('error'),diagnostics=r.get('diagnostic_values')) for n,r in runs.items() if r['status']!='completed' or not r.get('state_and_diagnostic_gates')]
report=dict(scope='Independent partial screen of completed physics pairs. Missing cases, reference/refinement ladders and full M1 remain pending.',run_map_sha256=hashlib.sha256(run_bytes).hexdigest(),script_sha256=sha(Path(__file__)),numpy=np.__version__,completed_records=len(runs),pairs=pairs,pending=pending,failed_runs=failed_runs,failed_pairs=[r for r in pairs if not r['passed']])
(root/'physics_pair_checkpoint.json').write_text(json.dumps(report,indent=2)+'\n')
print('records',len(runs),'verified pairs',len(pairs),'failed pairs',len(report['failed_pairs']),'failed run gates',len(failed_runs))
for r in pairs:print(r['names'][0],max(r['relative_L1'].values()),r['passed'])
if failed_runs or report['failed_pairs']:print(json.dumps(report,indent=2))
