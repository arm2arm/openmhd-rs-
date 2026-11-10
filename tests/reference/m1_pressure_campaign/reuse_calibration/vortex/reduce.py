"""Independent final-cell conservation/divergence reduction; no evolution."""
from pathlib import Path
import argparse, gzip, hashlib, json, math
import numpy as np
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('raw',type=Path);args=parser.parse_args()
root=Path(__file__).resolve().parent;raw=args.raw;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert (raw/'runs.json').read_bytes()==gzip.decompress((root/'runs.json.gz').read_bytes())
runs=json.loads((raw/'runs.json').read_text());assert len(runs)==1
name,run=next(iter(runs.items()));assert run['status']=='completed'
c=run['config'];assert c['case']=='orszag-tang' and c['n']==c['ny']==128 and c['time']==.5 and c['jitter']==.15 and c['boost']==[0.,0.,0.]
arrays=[]
for filename,time in [('initial.csv',0.),('final.csv',.5)]:
    p=raw/name/filename;assert sha(p)==run['sha256'][filename]
    d=np.genfromtxt(p,names=True,delimiter=',')
    assert np.array_equal(d['id'],np.arange(128**2)) and (d['time']==time).all()
    assert all(np.isfinite(d[k]).all() for k in d.dtype.names)
    assert all((d[k]>0).all() for k in ('volume','rho','p'))
    arrays.append(d)
a,b=arrays;weighted=lambda d,v:float(np.dot(d['volume'],v)/sum(d['volume']))
def totals(d):
    return np.array([np.dot(d['volume'],d['rho']),*[np.dot(d['volume'],d['rho']*d[k]) for k in ('vx','vy','vz')],np.dot(d['volume'],d['energy'])])
s=run['summary'];budget=(totals(b)-totals(a))/s['initial']['budget_scales']
assert max(abs(budget-np.array(s['final']['normalized_budget'])))<2e-13
bscale=1/math.sqrt(4*math.pi)
drift=np.array([weighted(b,b[k])-weighted(a,a[k]) for k in ('bx','by','bz')])
assert max(abs(drift-np.array(s['final']['mean_B_drift'])))<2e-13
field=np.sqrt(sum(b[k]**2 for k in ('bx','by','bz')))
normalized=np.sqrt(b['volume']/np.pi)*b['div_b_limited']/(field+1e-12*bscale)
rms=math.sqrt(weighted(b,normalized**2))
assert abs(rms-s['final']['div_B_limited']['dimensionless']['rms'])<2e-13
mean_norm=float(np.linalg.norm(drift))/bscale
report=dict(scope='Independent NumPy reductions of verified final cells and initial/final budgets. The limited-face operator values are exported solver data, not an independently rebuilt operator. No evolution or full M1 acceptance.',
    source_sha256=sha(Path(__file__)),run_map_sha256=sha(raw/'runs.json'),numpy=np.__version__,
    minimum_density=float(min(b['rho'])),minimum_pressure=float(min(b['p'])),
    final_normalized_budget=budget.tolist(),final_mean_B_drift=drift.tolist(),
    final_normalized_mean_B_drift=mean_norm,final_normalized_limited_divergence_RMS=rms,
    stored_history_maxima=run['diagnostic_values'],
    final_checks=dict(positive=True,budget=float(max(abs(budget)))<=1e-10,mean_B_drift=mean_norm<=.001,limited_divergence=rms<=.1))
assert all(report['final_checks'].values())
(root/'independent_reduction.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
