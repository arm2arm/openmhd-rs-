"""Independent reductions of archived short-stage CSVs; no evolution."""
from pathlib import Path
import hashlib,io,json,math,tarfile
import numpy as np
root=Path(__file__).resolve().parent
with tarfile.open(root/'measurements.tar.gz') as tar:
 data={m.name:tar.extractfile(m).read() for m in tar if m.isfile()}
hashes=json.loads((root/'members_sha256.json').read_text())
assert set(data)==set(hashes)
assert all(hashlib.sha256(data[n]).hexdigest()==h for n,h in hashes.items())
load=lambda n:json.loads(data[n])
def cells(stage,name,file='final.csv'):
 a=np.genfromtxt(io.BytesIO(data[f'{stage}/{name}/{file}']),names=True,delimiter=',')
 assert np.array_equal(a['id'],np.arange(len(a)))
 assert all(np.isfinite(a[k]).all() for k in a.dtype.names)
 assert (a['volume']>0).all()
 return a
norm=lambda a,v:float(np.dot(a['volume'],v)/sum(a['volume']))
wave_errors={};vortices={};pairs=[];budgets={};failures=[]
for stage in ('shock_short','shock_symmetry','waves_short','physics_quick'):
 runs=load(stage+'/runs.json')
 for name,run in runs.items():
  if run['status']!='completed':
   failures.append(dict(stage=stage,name=name,status=run['status'],error=run.get('error')));continue
  a=cells(stage,name);initial=cells(stage,name,'initial.csv');c=run['config'];s=run['summary']
  assert np.all(a['time']==c['time'])
  def totals(d):
   return np.array([np.dot(d['volume'],d['rho']),*[np.dot(d['volume'],d['rho']*d[k]) for k in ('vx','vy','vz')],np.dot(d['volume'],d['energy'])])
  budget=(totals(a)-totals(initial))/s['initial']['budget_scales']
  discrepancy=float(max(abs(budget-np.array(s['final']['normalized_budget']))))
  assert discrepancy<2e-13,(name,discrepancy)
  budgets[stage+'/'+name]=dict(final_normalized_budget=budget.tolist(),maximum_discrepancy=discrepancy)
  if c['case']=='alfven':
   values={}
   for when,d in (('initial',initial),('final',a)):
    phase=2*np.pi*(d['x']+(1-c['parallel']-c['boost'][0])*d['time'])
    transverse=np.array([.1*np.sin(phase),.1*np.cos(phase)])
    expected_b=np.vstack((np.ones(len(d)),transverse))
    expected_v=np.vstack((np.full(len(d),c['parallel']),transverse))+np.array(c['boost'])[:,None]
    values[when]={}
    for field,keys,expected in (('B',('bx','by','bz'),expected_b),('v',('vx','vy','vz'),expected_v)):
     error=np.sqrt(np.sum((np.array([d[k] for k in keys])-expected)**2,axis=0))
     measured=norm(d,error);reported=run['errors'][when][field]['L1']
     assert abs(measured-reported)<2e-14,(name,field,measured,reported)
     values[when][field]=measured
   wave_errors[name]=values
  elif c['case']=='orszag-tang':
   b=np.sqrt(sum(a[k]**2 for k in ('bx','by','bz')))
   scaled=np.sqrt(a['volume']/np.pi)*a['div_b_limited']/(b+1e-12/math.sqrt(4*math.pi))
   rms=math.sqrt(norm(a,scaled**2));expected=s['final']['div_B_limited']['dimensionless']['rms']
   assert abs(rms-expected)<2e-13,(name,rms,expected)
   drift=[norm(a,a[k])-norm(initial,initial[k]) for k in ('bx','by','bz')]
   assert max(abs(np.array(drift)-s['final']['mean_B_drift']))<2e-13
   vortices[name]=dict(final_normalized_divergence=rms,final_mean_B_drift=drift,recorded_history_maxima=run['diagnostic_values'],state_and_diagnostic_gates=run['state_and_diagnostic_gates'])
 summary=load(stage+('/analysis.json' if stage=='waves_short' else '/summary.json'))
 for p in summary['boost_pairs']:
  if 'scales' not in p:continue
  n,m=p['names'];a,b=cells(stage,n),cells(stage,m);boost=runs[m]['config']['boost'];values={}
  for field,scale in p['scales'].items():
   expected=a[field].copy()
   if field in ('vx','vy','vz'):expected+=boost[('vx','vy','vz').index(field)]
   if field=='energy':expected+=a['rho']*(sum(a[k]*v for k,v in zip(('vx','vy','vz'),boost))+.5*sum(v*v for v in boost))
   values[field]=norm(a,abs(b[field]-expected)/scale)
  assert max(abs(values[k]-p['relative_L1'][k]) for k in values)<2e-15
  pairs.append(dict(stage=stage,names=[n,m],relative_L1=values))
orders=[]
for row in load('waves_short/analysis.json')['waves']:
 values={field:float(-np.polyfit(np.log([8,16,32]),np.log([wave_errors[n]['final'][field] for n in row['names']]),1)[0]) for field in ('B','v')}
 assert max(abs(values[k]-row['orders'][k]) for k in values)<1e-11
 orders.append(dict(jitter=row['jitter'],parallel=row['parallel'],orders=values))
result=dict(scope='Independent NumPy reductions from hash-verified CSVs; divergence operator values and intermediate history extrema are stored solver outputs, not independently reconstructed operators. No evolutions, changed thresholds or full M1 acceptance.',members_verified=len(hashes),wave_errors=wave_errors,wave_orders=orders,vortices=vortices,normalized_boost_pairs=pairs,final_conservation=budgets,retained_failed_controls=failures,numpy=np.__version__,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(root/'independent_reduction.json').write_text(json.dumps(result,indent=2)+'\n')
print('Verified',len(hashes),'members,',len(wave_errors),'wave cases,',len(vortices),'vortices,',len(pairs),'normalized boost pairs,',len(budgets),'final budgets;',len(failures),'failed controls retained.')
