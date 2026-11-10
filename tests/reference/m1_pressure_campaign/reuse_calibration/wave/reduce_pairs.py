"""Independent early boost screen of completed, hash-verified REANA snapshots."""
from pathlib import Path
import argparse,gzip,hashlib,json,math
import numpy as np
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('raw',type=Path)
args=parser.parse_args();p=args.raw;root=Path(__file__).resolve().parent
assert (p/'runs.json').read_bytes()==gzip.decompress((root/'runs.json.gz').read_bytes())
runs=json.loads((p/'runs.json').read_text());assert len(runs)==2
pairs=[];pending=[]
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
for name,a in runs.items():
 if not name.endswith('_base'):continue
 other=name.removesuffix('_base')+'_boost'
 if other not in runs:pending.append([name,other]);continue
 b=runs[other]
 assert a['status']==b['status']=='completed'
 if any(not (p/n/'final.csv').exists() or sha(p/n/'final.csv')!=r['sha256']['final.csv'] for n,r in ((name,a),(other,b))):
  pending.append([name,other]);continue
 x,y=[np.genfromtxt(p/n/'final.csv',names=True,delimiter=',') for n in (name,other)]
 assert len(x)==len(y)==a['config']['n']**2
 assert np.array_equal(x['id'],y['id']) and np.array_equal(x['id'],np.arange(len(x)))
 assert all(np.isfinite(d[k]).all() for d in (x,y) for k in d.dtype.names)
 assert all((d['volume']>0).all() and (d['time']==a['config']['target']).all() for d in (x,y))
 assert a['config']['boost']==[0.,0.,0.] and b['config']['boost']==[2.,-1.,0.]
 boost=np.array(b['config']['boost']);t=a['config']['target']
 v=np.array([y[k] for k in ('vx','vy','vz')])-boost[:,None]
 energy=y['energy']-y['rho']*sum(y[k]*s for k,s in zip(('vx','vy','vz'),boost))+.5*y['rho']*sum(boost**2)
 norm=lambda d:float(np.dot(x['volume'],abs(d))/sum(x['volume']))
 errors={k:norm(y[k]-x[k]) for k in ('rho','p')}
 errors['energy']=norm(energy-x['energy'])
 errors['B']=norm(np.sqrt(sum((y[k]-x[k])**2 for k in ('bx','by','bz'))))
 errors['v']=norm(np.sqrt(np.sum((v-np.array([x[k] for k in ('vx','vy','vz')]))**2,axis=0)))
 position=max(float(max(abs((y[k]-x[k]-shift*t+.5)%1-.5))) for k,shift in zip(('x','y'),boost))
 volume=float(max(abs(y['volume']/x['volume']-1)))
 state=all(r['positive_and_conservative'] for r in (a,b))
 if a['config']['case']=='loop':
  relative={'B':errors['B']/(.001/math.sqrt(4*math.pi))};limit=.001
 else:
  parallel=a['config']['parallel'];scales={'B':.1,'v':.1,'rho':1.,'p':.1,'energy':.66+.5*parallel**2}
  relative={k:errors[k]/scales[k] for k in scales};limit=1e-8
  # The wave-amplitude convention is the stricter of both recorded conventions.
 passed=max(relative.values())<=limit and position<=1e-11 and volume<=1e-11 and state
 pairs.append(dict(names=[name,other],case=a['config']['case'],n=a['config']['n'],relative_L1=relative,limit=limit,position_max=position,relative_volume_max=volume,positive_and_conservative=state,passed=passed))
assert len(pairs)==1 and not pending
reported=json.loads(gzip.decompress((root/'summary.json.gz').read_bytes()))['pairs']
for pair in pairs:
 original=next(r for r in reported if r['names']==pair['names'])
 expected=original['relative_L1']['wave_amplitude'] if pair['case']=='alfven' else {'B':original['B_relative_L1']}
 pair['maximum_report_discrepancy']=max(abs(pair['relative_L1'][k]-expected[k]) for k in expected)
 assert pair['maximum_report_discrepancy']<1e-13
record=dict(scope='Independent complete N128 calibration boost screen from hash-verified final CSVs. The wave-amplitude convention is stricter than the second reported convention. No evolution, threshold change or full M1 acceptance.',run_map_sha256=sha(p/'runs.json'),pairs=pairs,pending=pending,failed=[r for r in pairs if not r['passed']],numpy=np.__version__,script_sha256=sha(Path(__file__)))
(root/'independent_pairs.json').write_text(json.dumps(record,indent=2)+'\n')
print('Completed records',len(runs),'; verified pairs',len(pairs),'; failed',len(record['failed']),'; pending',len(pending))
for case in ('alfven','loop'):
 subset=[r for r in pairs if r['case']==case]
 if subset:print(case,'max normalized L1',max(max(r['relative_L1'].values()) for r in subset))
if record['failed']:print(json.dumps(record['failed'],indent=2))
