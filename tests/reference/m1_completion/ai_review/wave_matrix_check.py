#!/usr/bin/env python3
"""Independent read-only AI audit of one completed 64-run spatial wave matrix.

The containing root execution packet may still be active. This script verifies
only completed alfven_* runs; no simulation or production measurement code runs.
"""
import argparse,hashlib,json,math
from datetime import datetime,timezone
from pathlib import Path
import numpy as np

parser=argparse.ArgumentParser();parser.add_argument('root',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def norm(a,v):
    if a.ndim>1:a=np.sqrt(np.sum(a*a,axis=1))
    total=math.fsum(v)
    return {'L1':math.fsum(np.abs(a)*v)/total,'L2':math.sqrt(math.fsum(a*a*v)/total),'max':float(np.max(np.abs(a)))}
def fit(ns,errors):
    x=np.log(1/np.array(ns,dtype=float));y=np.log(errors);xm=x.mean();ym=y.mean();ss=float(np.sum((x-xm)**2))
    p=float(np.sum((x-xm)*(y-ym))/ss);residual=float(np.sum((y-ym-p*(x-xm))**2))
    return {'order':p,'residual_slope_SE':math.sqrt(residual/(len(ns)-2)/ss),'adjacent_orders':[math.log2(a/b) for a,b in zip(errors,errors[1:])]}
def read(path,n,time):
    with path.open() as f:keys=f.readline().strip().split(',')
    table=np.loadtxt(path,delimiter=',',skiprows=1);assert table.shape==(n*n,len(keys)) and np.isfinite(table).all()
    d={k:table[:,i] for i,k in enumerate(keys)}
    assert np.array_equal(d['id'],np.arange(n*n)) and np.all(d['time']==time)
    assert np.all(d['volume']>0) and abs(math.fsum(d['volume'])-1)<1e-9
    assert np.all((d['x']>=0)&(d['x']<1)&(d['y']>=0)&(d['y']<1))
    return d

def physical(d,t,c):
    angle=[2*math.pi*(x+(1-c['parallel']-c['boost'][0])*t) for x in d['x']]
    sine=np.array([math.sin(a) for a in angle]);cosine=np.array([math.cos(a) for a in angle]);vol=d['volume']
    exact_b=np.column_stack([np.ones(len(vol)),.1*sine,.1*cosine]);exact_v=np.column_stack([np.full(len(vol),c['parallel']),.1*sine,.1*cosine])+np.array(c['boost'])
    b=np.column_stack([d[k] for k in ('bx','by','bz')]);v=np.column_stack([d[k] for k in ('vx','vy','vz')]);eb=b-exact_b;ev=v-exact_v
    errors={'B':norm(eb,vol),'v':norm(ev,vol)}
    errors.update({k:norm(eb[:,i],vol) for i,k in enumerate(('bx','by','bz'))});errors.update({k:norm(ev[:,i],vol) for i,k in enumerate(('vx','vy','vz'))})
    extra={'rho_error':norm(d['rho']-1,vol),'pressure_error':norm(d['p']-.1,vol),'transverse_radial_error':norm(eb[:,1]*sine+eb[:,2]*cosine,vol),'transverse_quadrature_error':norm(eb[:,1]*cosine-eb[:,2]*sine,vol)}
    return errors,extra

def diagnostics(d):
    vol=d['volume'];total=math.fsum(vol);rho=d['rho'];v=np.column_stack([d[k] for k in ('vx','vy','vz')]);b=np.column_stack([d[k] for k in ('bx','by','bz')])
    conserved=np.column_stack([rho,rho[:,None]*v,d['energy']]);integrals=np.array([math.fsum(vol*conserved[:,k]) for k in range(5)])
    rho_scale=float(np.max(rho));speed=float(np.max(np.maximum(np.sqrt(np.sum(v*v,axis=1)),np.sqrt((5/3)*d['p']/rho))));e_scale=float(np.max(d['energy']))
    scales=np.array([max(math.fsum(vol*np.abs(conserved[:,k])),total*scale,1e-30) for k,scale in enumerate([rho_scale]+[rho_scale*speed]*3+[e_scale])])
    reconstructed_pressure=(5/3-1)*(d['energy']-.5*rho*np.sum(v*v,axis=1)-.5*np.sum(b*b,axis=1))
    assert np.max(np.abs(reconstructed_pressure-d['p']))<1e-12
    return {'totals':integrals.tolist(),'initial_normalization_if_applied':scales.tolist(),'rho_min':float(np.min(rho)),'rho_max':float(np.max(rho)),'p_min':float(np.min(d['p'])),'p_max':float(np.max(d['p'])),
            'magnetic_energy':math.fsum(.5*vol*np.sum(b*b,axis=1)),'mean_B':[math.fsum(vol*b[:,k])/total for k in range(3)],
            'divergence':{k:norm(d[k],vol) for k in ('div_b_ls','div_b_face','div_b_limited','div_a','phi')}}

def pair_error(a,b,t):
    shift=np.array([2.,-1.,0.]);transformed=dict(b)
    for k,value in zip(('vx','vy','vz'),shift):transformed[k]=b[k]-value
    transformed['energy']=b['energy']-b['rho']*(2*b['vx']-b['vy'])+2.5*b['rho']
    errors={k:norm(transformed[k]-a[k],a['volume']) for k in ('rho','p','vx','vy','vz','bx','by','bz','energy')}
    for label,keys in [('B',('bx','by','bz')),('v',('vx','vy','vz'))]:errors[label]=norm(np.column_stack([transformed[k]-a[k] for k in keys]),a['volume'])
    geom={'position_max':max(float(np.max(np.abs((b[k]-a[k]-q*t+.5)%1-.5))) for k,q in [('x',2.),('y',-1.)]),'relative_volume_max':float(np.max(np.abs(a['volume']-b['volume'])/a['volume']))}
    return errors,geom

root=args.root;records=json.loads((root/'runs.json').read_text());manifest=json.loads((root/'manifest.json').read_text());execution=json.loads((root/'provenance.json').read_text());checkout=root.parent.parent
names=[n for n in manifest if n.startswith('alfven_')];assert len(names)==64
assert all(n in records and records[n]['status']=='completed' and records[n]['returncode']==0 for n in names),'wave matrix not yet complete'
profiles={manifest[n]['profile'] for n in names};assert len(profiles)==1;profile=profiles.pop()
for name,digest in execution['source_sha256'].items():assert sha(checkout/name)==digest,(profile,name)
assert sha(checkout/'target/release/vector-potential')==execution['binary_sha256']
report={'scope':'Independent AI review of completed 64-run spatial Alfven matrix only; containing execution packet may still be active. Not full M1 acceptance.',
        'created_utc':datetime.now(timezone.utc).isoformat(),'profile':profile,'numpy':np.__version__,
        'source_inputs':{'checkout':str(checkout),'revision':execution['revision'],'configuration':execution['configuration'],'source_sha256':execution['source_sha256'],'binary_sha256':execution['binary_sha256']},
        'runs':{},'pairs':[],'ladders':[]}
for parallel in (0.,1.):
 for jitter in (0.,.15):
  for motion in ('fixed','comoving'):
   for n in (32,64,128,256):
    prefix=f'alfven_{profile}_v{parallel}_j{jitter}_{motion}_n{n}';data=[]
    for boosted in (False,True):
     name=prefix+('_boost' if boosted else '_base');r=records[name];c=r['config'];s=r['summary'];shift=[2.,-1.,0.] if boosted else [0.,0.,0.]
     mesh_base=[parallel,0.] if motion=='comoving' else [0.,0.];expected_mesh=[mesh_base[k]+shift[k] for k in range(2)]
     assert c==manifest[name] and c['profile']==profile and c['case']=='alfven' and c['boost']==shift and c['mesh_velocity']==expected_mesh and c['dt'] is None and c['target']==1.
     assert s['completed'] and s['time']==s['requested_time']==1 and s['case']=='alfven' and s['profile']==profile
     assert s['n']==n and s['jitter']==jitter and s['parallel_velocity']==parallel and s['mesh_velocity']==expected_mesh and s['boost']==shift
     assert s['gamma']==5/3 and s['mean_B']==[1,0,0] and s['limited'] and s['motion']=='rigid' and s['dt_cap'] is None
     assert json.loads((root/name/'summary.json').read_text())==s and json.loads((root/name/'history.json').read_text())==r['history']
     for filename,digest in r['sha256'].items():assert sha(root/name/filename)==digest,(name,filename)
     measured={};initial=None;snapshots={};budget_pass=True;positive=True
     for stage,filename,t in [('initial','initial.csv',0.),('t0.25','checkpoint_0.25000000.csv',.25),('final','final.csv',1.)]:
      d=read(root/name/filename,n,t);errors,extra=physical(d,t,c);diag=diagnostics(d);original=next(h['diagnostics'] for h in r['history'] if h['time']==t)
      for key,norms in errors.items():
       for normname,value in norms.items():assert math.isclose(value,r['errors'][stage][key][normname],rel_tol=5e-10,abs_tol=2e-17),(name,stage,key,normname,value,r['errors'][stage][key][normname])
      if initial is None:
       initial=d;initial_diag=diag;scales=np.array(diag['initial_normalization_if_applied'])
       analytic_a=np.column_stack([np.zeros(n*n),[.1/(2*math.pi)*math.sin(2*math.pi*x) for x in d['x']],[.1/(2*math.pi)*math.cos(2*math.pi*x) for x in d['x']]])
       extra['analytic_initial_A_max']=float(np.max(np.abs(np.column_stack([d[k] for k in ('ax','ay','az')])-analytic_a)))
       assert extra['analytic_initial_A_max']<1e-16 and errors['v']['max']<1e-15
       assert np.max(np.abs(np.array(original['budget_scales'])-scales)/scales)<1e-11
      geom=max(float(np.max(np.abs((d[k]-initial[k]-q*t+.5)%1-.5))) for k,q in zip(('x','y'),expected_mesh))
      vol=float(np.max(np.abs(d['volume']-initial['volume'])/initial['volume']))
      assert geom<1e-10 and vol<1e-11,(name,t,'rigid geometry mismatch',geom,vol)
      budgets=(np.array(diag['totals'])-np.array(initial_diag['totals']))/scales
      diag['normalized_budget_recomputed']=budgets.tolist();diag['normalized_budget_recorded']=original['normalized_budget']
      diag['budget_reduction_difference_max']=float(np.max(np.abs(budgets-original['normalized_budget'])))
      assert diag['budget_reduction_difference_max']<1e-11
      for key in ('rho_min','rho_max','p_min','p_max'):assert math.isclose(diag[key],original[key],rel_tol=1e-12,abs_tol=1e-13)
      assert abs(diag['magnetic_energy']-original['magnetic_energy'])<1e-11
      for column,label in [('div_b_ls','div_B_ls'),('div_b_face','div_B_face'),('div_b_limited','div_B_limited')]:assert math.isclose(diag['divergence'][column]['L2'],original[label]['dimensional']['rms'],rel_tol=5e-10,abs_tol=1e-15)
      positive=positive and diag['rho_min']>0 and diag['p_min']>0
      budget_pass=budget_pass and float(np.max(np.abs(budgets)))<=1e-10 and max(map(abs,original['normalized_budget']))<=1e-10
      measured[stage]={'norms':errors,**extra,'diagnostics':diag,'rigid_position_residual_max':geom,'relative_volume_drift_max':vol}
      snapshots[stage]=d
     assert bool(positive and budget_pass)==r['positive_and_conservative'],(name,'positivity/budget verdict mismatch')
     report['runs'][name]={'config':c,'command':r['command'],'input_sha256':r['sha256'],'summary':{k:v for k,v in s.items() if k!='auxiliary_roots'},'auxiliary_roots_set':sorted(set(s['auxiliary_roots'])),
      'source_record_status':r['status'],'positive_at_recorded_outputs':positive,'budget_gate':budget_pass,'positive_and_conservative':positive and budget_pass,'measurements':measured}
     data.append(snapshots)
    pair={'names':[prefix+'_base',prefix+'_boost'],'n':n,'parallel':parallel,'jitter':jitter,'motion':motion,'times':{}}
    for stage,t in [('initial',0.),('t0.25',.25),('final',1.)]:
     errors,geometry=pair_error(data[0][stage],data[1][stage],t);pair['times'][stage]={'errors':errors,**geometry}
    final=pair['times']['final'];pair['pairing_valid']=max(final['position_max'],final['relative_volume_max'])<=1e-11
    pair['positive_and_conservative']=all(report['runs'][name]['positive_and_conservative'] for name in pair['names'])
    pair['matching_auxiliary_roots']=records[pair['names'][0]]['summary']['auxiliary_roots']==records[pair['names'][1]]['summary']['auxiliary_roots']
    shared={'rho':1.,'p':.1,'energy':.66+.5*parallel**2};scales={'wave_amplitude':{**shared,'B':.1,'v':.1},'mean_field_and_initial_speed':{**shared,'B':1.,'v':max(math.sqrt(parallel**2+.01),math.sqrt(1/6))}}
    pair['relative_L1']={label:{key:final['errors'][key]['L1']/value for key,value in scale.items()} for label,scale in scales.items()}
    pair['normalization_verdicts']={label:pair['pairing_valid'] and pair['positive_and_conservative'] and max(vals.values())<=1e-8 for label,vals in pair['relative_L1'].items()}
    pair['status']='pass under both reported normalizations' if all(pair['normalization_verdicts'].values()) else 'fail under both reported normalizations' if not any(pair['normalization_verdicts'].values()) else 'normalization clarification pending'
    report['pairs'].append(pair)
   base_runs=[report['runs'][f'alfven_{profile}_v{parallel}_j{jitter}_{motion}_n{n}_base'] for n in (32,64,128,256)]
   values=[r['measurements']['final']['norms']['B']['L1'] for r in base_runs];result=fit([64,128,256],values[1:])
   ladder={'parallel':parallel,'jitter':jitter,'motion':motion,'n':[32,64,128,256],'B_L1':values,'finest_three':result,'finest_B_L1_over_amplitude':values[-1]/.1,
           'gate':bool(result['order']>=1.8 and values[-1]/.1<=.02 and all(r['positive_and_conservative'] for r in base_runs)),
           'initial_finest_three':fit([64,128,256],[r['measurements']['initial']['norms']['B']['L1'] for r in base_runs[1:]])}
   report['ladders'].append(ladder)
   print(f"{profile} v={parallel} j={jitter} {motion}: p={result['order']:.10f} SE={result['residual_slope_SE']:.10f}; finest B_L1/.1={values[-1]/.1:.8e}; gate={ladder['gate']}; boost-passes={sum(all(p['normalization_verdicts'].values()) for p in report['pairs'][-4:])}/4",flush=True)
summary={'runs':len(report['runs']),'positive_budget_runs':sum(r['positive_and_conservative'] for r in report['runs'].values()),'spatial_gate_passes':sum(s['gate'] for s in report['ladders']),
         'boost_pairs':len(report['pairs']),'geometry_valid_pairs':sum(p['pairing_valid'] for p in report['pairs']),
         'boost_pass_both':sum(all(p['normalization_verdicts'].values()) for p in report['pairs']),'boost_fail_both':sum(not any(p['normalization_verdicts'].values()) for p in report['pairs']),
         'mixed_normalization_pairs':sum(len(set(p['normalization_verdicts'].values()))>1 for p in report['pairs']),
         'minimum_rho':min(v['diagnostics']['rho_min'] for r in report['runs'].values() for v in r['measurements'].values()),'minimum_p':min(v['diagnostics']['p_min'] for r in report['runs'].values() for v in r['measurements'].values()),
         'maximum_recomputed_budget':max(abs(b) for r in report['runs'].values() for v in r['measurements'].values() for b in v['diagnostics']['normalized_budget_recomputed']),
         'maximum_budget_reduction_difference':max(v['diagnostics']['budget_reduction_difference_max'] for r in report['runs'].values() for v in r['measurements'].values())}
report['review_summary']=summary;args.output.write_text(json.dumps(report,indent=2)+'\n')
print('SUMMARY',json.dumps(summary),flush=True)
print('Completed per-run wave review only; full packet/loop/temporal evidence remains outside this review.')
