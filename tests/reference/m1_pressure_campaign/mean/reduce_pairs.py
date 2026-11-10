"""Independent mean-field boost reduction of hash-verified REANA snapshots."""
from pathlib import Path
import argparse,gzip,hashlib,json
import numpy as np
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('raw',type=Path);args=parser.parse_args()
root=Path(__file__).resolve().parent;p=args.raw;sha=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
assert (p/'runs.json').read_bytes()==gzip.decompress((root/'runs.json.gz').read_bytes())
s=json.loads(gzip.decompress((root/'summary.json.gz').read_bytes()));runs=s['runs'];assert len(runs)==24 and len(s['pairs'])==12
records=[]
for pair in s['pairs']:
 a,b=pair['names'];rows=[]
 for n in (a,b):
  assert sha(p/n/'final.csv')==runs[n]['sha256']['final.csv']
  d=np.genfromtxt(p/n/'final.csv',names=True,delimiter=',');assert np.array_equal(d['id'],np.arange(len(d)))
  assert all(np.isfinite(d[k]).all() for k in d.dtype.names);assert (d['time']==.02).all() and (d['volume']>0).all();rows.append(d)
 x,y=rows;assert len(x)==len(y)==runs[a]['config']['n']**2
 boost=np.array(runs[b]['config']['boost']);assert list(boost)==[2.,-1.,0.]
 transform={k:y[k].copy() for k in ('rho','p','vx','vy','vz','bx','by','bz','energy')}
 for k,v in zip(('vx','vy','vz'),boost):transform[k]-=v
 transform['energy']=y['energy']-y['rho']*sum(y[k]*v for k,v in zip(('vx','vy','vz'),boost))+.5*y['rho']*sum(boost**2)
 errors={k:float(max(abs(transform[k]-x[k]))) for k in transform}
 assert max(abs(errors[k]-pair['errors'][k]['max']) for k in errors)<1e-13
 position=max(float(max(abs((y[k]-x[k]-v*.02+.5)%1-.5))) for k,v in zip(('x','y'),boost))
 volume=float(max(abs(y['volume']/x['volume']-1)))
 passed=max(errors.values())<=1e-9 and position<=1e-11 and volume<=1e-11 and pair['matching_auxiliary_roots'] and all(runs[n]['positive_and_conservative'] for n in (a,b))
 records.append(dict(names=[a,b],maximum_errors=errors,position_max=position,volume_relative_max=volume,passed=passed))
result=dict(scope='Independent NumPy reduction of 12 complete mean-field boost pairs, not analytic accuracy or general invariance.',pairs=records,all_passed=all(r['passed'] for r in records),numpy=np.__version__,script_sha256=sha(Path(__file__)))
(root/'independent_pairs.json').write_text(json.dumps(result,indent=2)+'\n')
print('Verified',len(records),'mean-field pairs; all passed:',result['all_passed'],'largest component error',max(max(r['maximum_errors'].values()) for r in records))
