#!/usr/bin/env python3
"""Independent read-only AI audit of 72 completed mean-field comparison runs.

The small numerical utilities are copied from the independent wave checker;
no production measurement code is imported and no simulation is performed.
Paper-global-v2 observations receive no retrospective boost success gate.
"""
import argparse,hashlib,json,math
from datetime import datetime,timezone
from pathlib import Path
import numpy as np

def norm(a,v):
    if a.ndim>1:a=np.sqrt(np.sum(a*a,axis=1))
    total=math.fsum(v)
    return {'L1':math.fsum(np.abs(a)*v)/total,'L2':math.sqrt(math.fsum(a*a*v)/total),'max':float(np.max(np.abs(a)))}

def read(path,n,time):
    with path.open() as f:keys=f.readline().strip().split(',')
    table=np.loadtxt(path,delimiter=',',skiprows=1);assert table.shape==(n*n,len(keys)) and np.isfinite(table).all()
    d={k:table[:,i] for i,k in enumerate(keys)}
    assert np.array_equal(d['id'],np.arange(n*n)) and np.all(d['time']==time)
    assert np.all(d['volume']>0) and abs(math.fsum(d['volume'])-1)<1e-9
    assert np.all((d['x']>=0)&(d['x']<1)&(d['y']>=0)&(d['y']<1))
    return d

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

parser=argparse.ArgumentParser();parser.add_argument('root',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
root=args.root;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
records=json.loads((root/'runs.json').read_text());manifest=json.loads((root/'manifest.json').read_text());execution=json.loads((root/'provenance.json').read_text());checkout=root.parent.parent
names=[n for n in manifest if n.startswith('mean_')];assert len(names)==72
assert all(n in records and records[n]['status']=='completed' and records[n]['returncode']==0 for n in names)
for name,digest in execution['source_sha256'].items():assert sha(checkout/name)==digest,name
assert sha(checkout/'target/release/vector-potential')==execution['binary_sha256']
report={'scope':'Independent AI audit of completed 72 mean-field evolutions only; no simulation, no certification of unfinished global packet or full M1 acceptance.',
        'created_utc':datetime.now(timezone.utc).isoformat(),'numpy':np.__version__,
        'source_inputs':{'checkout':str(checkout),'revision':execution['revision'],'configuration':execution['configuration'],'source_sha256':execution['source_sha256'],'binary_sha256':execution['binary_sha256']},
        'runs':{},'pairs':[],'refinement_observations':[]}
profiles=['paper-global-v2','bulk-frame-v1','bulk-frame-signal-v1']
for profile in profiles:
 for jitter in [0.,.15]:
  for n,dt in [(8,.00025),(16,.00025),(32,.00025),(64,.00025),(16,.001),(16,.0005)]:
   prefix=f'mean_{profile}_n{n}_j{jitter}_dt{dt}';data=[]
   for boosted in [False,True]:
    name=prefix+('_boost' if boosted else '_base');r=records[name];c=r['config'];s=r['summary'];boost=[2.,-1.,0.] if boosted else [0.,0.,0.]
    assert c==manifest[name] and c['name']==name and c['case']=='smooth' and c['profile']==profile and c['n']==n and c['jitter']==jitter and c['parallel']==0.
    assert c['motion_family']=='fixed' and c['mesh_velocity']==boost[:2] and c['boost']==boost and c['target']==.02 and c['dt']==dt
    assert s['completed'] and s['case']=='smooth' and s['profile']==profile and s['time']==s['requested_time']==.02 and s['dt_cap']==dt
    assert s['n']==n and s['jitter']==jitter and s['parallel_velocity']==0 and s['mesh_velocity']==boost[:2] and s['boost']==boost
    assert s['mean_B']==[.3,.2,.1] and s['Bscale']==.3 and s['gamma']==5/3 and s['limited'] and s['motion']=='rigid'
    assert len(r['command'])%2==1 and len(set(r['command'][1::2]))==len(r['command'][1::2]);cmd=dict(zip(r['command'][1::2],r['command'][2::2]))
    assert Path(r['command'][0]).resolve()==(checkout/'target/release/vector-potential').resolve()
    assert cmd['--case']=='smooth' and cmd['--profile']==profile and cmd['--motion']=='rigid' and '--checkpoint' not in cmd
    assert int(cmd['--n'])==n and float(cmd['--jitter'])==jitter and float(cmd['--parallel-velocity'])==0 and float(cmd['--dt'])==dt and float(cmd['--time'])==.02
    assert [float(cmd['--mean-b'+k]) for k in ['x','y','z']]==[.3,.2,.1]
    assert [float(cmd['--boost-'+k]) for k in ['x','y','z']]==boost and [float(cmd['--mesh-'+k]) for k in ['x','y']]==boost[:2]
    assert Path(cmd['--output']).resolve()==(root/name).resolve()
    assert json.loads((root/name/'summary.json').read_text())==s and json.loads((root/name/'history.json').read_text())==r['history']
    for filename,digest in r['sha256'].items():assert sha(root/name/filename)==digest,(name,filename)
    measured={};snapshots={};initial=None;positive=True;budget_pass=True
    for stage,t in [('initial',0.),('final',.02)]:
     d=read(root/name/(stage+'.csv'),n,t);diag=diagnostics(d);original=next(h['diagnostics'] for h in r['history'] if h['time']==t)
     if initial is None:
      initial=d;initial_diag=diag;scales=np.array(diag['initial_normalization_if_applied'])
      x=2*math.pi*d['x'];y=2*math.pi*d['y']
      sine_x=np.array([math.sin(v) for v in x]);cosine_x=np.array([math.cos(v) for v in x]);sine_y=np.array([math.sin(v) for v in y])
      velocity=np.column_stack([.2+.05*sine_y,-.1+.03*cosine_x,[.04*math.sin(a+b) for a,b in zip(x,y)]])+np.array(boost)
      potential=np.column_stack([.001*sine_y,.001*cosine_x,.001*sine_x*sine_y])
      initial_checks={'velocity_max':float(np.max(np.abs(velocity-np.column_stack([d[k] for k in ['vx','vy','vz']])))),
                      'potential_max':float(np.max(np.abs(potential-np.column_stack([d[k] for k in ['ax','ay','az']])))),
                      'rho_max':float(np.max(np.abs(d['rho']-1))),'p_max':float(np.max(np.abs(d['p']-1))),'phi_max':float(np.max(np.abs(d['phi'])))}
      assert max(initial_checks.values())<1e-14
      assert np.max(np.abs(np.array(original['budget_scales'])-scales)/scales)<1e-11
     geom=max(float(np.max(np.abs((d[k]-initial[k]-q*t+.5)%1-.5))) for k,q in zip(['x','y'],boost));vol=float(np.max(np.abs(d['volume']-initial['volume'])/initial['volume']))
     assert geom<=1e-11 and vol<=1e-11
     budgets=(np.array(diag['totals'])-np.array(initial_diag['totals']))/scales
     diag['normalized_budget_recomputed']=budgets.tolist();diag['normalized_budget_recorded']=original['normalized_budget'];diag['budget_reduction_difference_max']=float(np.max(np.abs(budgets-original['normalized_budget'])))
     assert diag['budget_reduction_difference_max']<1e-11
     for key in ['rho_min','rho_max','p_min','p_max']:assert math.isclose(diag[key],original[key],rel_tol=1e-12,abs_tol=1e-13)
     assert abs(diag['magnetic_energy']-original['magnetic_energy'])<1e-11
     bmag=np.hypot(np.hypot(d['bx'],d['by']),d['bz']);volume=math.fsum(d['volume']);scaled={}
     for column,label in [('div_b_ls','div_B_ls'),('div_b_face','div_B_face'),('div_b_limited','div_B_limited')]:
      scaled_values=np.sqrt(d['volume']/math.pi)*d[column]/(bmag+3e-13)
      scaled[column]=norm(scaled_values,d['volume'])
      for scale,values in [('dimensional',d[column]),('dimensionless',scaled_values)]:
       measured_norms=norm(values,d['volume']);measured_norms['mean']=math.fsum(values*d['volume'])/volume
       for key,rkey in [('L2','rms'),('max','max'),('mean','mean')]:assert math.isclose(measured_norms[key],original[label][scale][rkey],rel_tol=5e-10,abs_tol=1e-15),(name,stage,label,scale,key)
     diag['dimensionless_divergence']=scaled
     positive=positive and diag['rho_min']>0 and diag['p_min']>0;budget_pass=budget_pass and float(np.max(np.abs(budgets)))<=1e-10 and max(map(abs,original['normalized_budget']))<=1e-10
     measured[stage]={'diagnostics':diag,'rigid_position_residual_max':geom,'relative_volume_drift_max':vol};snapshots[stage]=d
    assert bool(positive and budget_pass)==r['positive_and_conservative']
    assert s['dt_max']<=dt*(1+1e-12)
    report['runs'][name]={'config':c,'command':r['command'],'input_sha256':r['sha256'],'summary':{k:v for k,v in s.items() if k not in ['auxiliary_roots','initial','final']},
      'auxiliary_root_values':sorted(set(s['auxiliary_roots'])),'auxiliary_root_sequence_length':len(s['auxiliary_roots']),
      'positive_and_conservative':positive and budget_pass,'initial_constructor_max_errors':initial_checks,'dt_cap_reached':math.isclose(s['dt_max'],dt,rel_tol=1e-12),'measurements':measured}
    data.append(snapshots)
   pair={'profile':profile,'n':n,'jitter':jitter,'dt_cap':dt,'names':[prefix+'_base',prefix+'_boost'],'times':{}}
   for stage,t in [('initial',0.),('final',.02)]:
    errors,geometry=pair_error(data[0][stage],data[1][stage],t);pair['times'][stage]={'errors':errors,**geometry}
   final=pair['times']['final'];pair['pairing_valid']=max(final['position_max'],final['relative_volume_max'])<=1e-11
   pair['matching_auxiliary_roots']=records[pair['names'][0]]['summary']['auxiliary_roots']==records[pair['names'][1]]['summary']['auxiliary_roots']
   pair['positive_and_conservative']=all(report['runs'][name]['positive_and_conservative'] for name in pair['names'])
   fields=['rho','p','vx','vy','vz','bx','by','bz','energy'];pair['maximum_transformed_physical_component_error']=max(final['errors'][key]['max'] for key in fields)
   if profile=='paper-global-v2':pair['status']='diagnostic observation; no retrospective boost gate';pair['boost_gate_applied']=False
   else:
    pair['boost_gate_applied']=True;pair['status']='pass' if pair['pairing_valid'] and pair['matching_auxiliary_roots'] and pair['positive_and_conservative'] and pair['maximum_transformed_physical_component_error']<=1e-9 else 'fail'
   report['pairs'].append(pair)
  selected=[p for p in report['pairs'] if p['profile']==profile and p['jitter']==jitter]
  for variable in ['n','dt_cap']:
   ladder=[p for p in selected if p['dt_cap']==.00025] if variable=='n' else [p for p in selected if p['n']==16]
   ladder.sort(key=lambda p:p[variable],reverse=variable=='dt_cap');coordinates=[p[variable] for p in ladder];values=[p['times']['final']['errors']['B']['L1'] for p in ladder]
   ratios=[b/a if variable=='n' else a/b for a,b in zip(coordinates,coordinates[1:])];orders=[math.log(a/b)/math.log(ratio) if a and b else None for a,b,ratio in zip(values,values[1:],ratios)]
   report['refinement_observations'].append({'profile':profile,'jitter':jitter,'variable':variable,'coordinates':coordinates,'B_boost_L1':values,'successive_orders':orders,
     'scope':'Joint-boost residual refinement observation, not exact physical error convergence or an acceptance target; roundoff-scale comparator orders are not meaningful accuracy estimates.'})
  print(profile,'jitter',jitter,'pair statuses',[p['status'] for p in selected],'max transformed component',max(p['maximum_transformed_physical_component_error'] for p in selected),'BboostL1 range',[min(p['times']['final']['errors']['B']['L1'] for p in selected),max(p['times']['final']['errors']['B']['L1'] for p in selected)],flush=True)
summary={'runs':len(report['runs']),'snapshot_count':2*len(report['runs']),'positive_budget_runs':sum(r['positive_and_conservative'] for r in report['runs'].values()),'pairs':len(report['pairs']),
         'geometry_valid_pairs':sum(p['pairing_valid'] for p in report['pairs']),'matching_auxiliary_root_pairs':sum(p['matching_auxiliary_roots'] for p in report['pairs']),
         'classification':{profile:{'diagnostic_pairs':sum(not p['boost_gate_applied'] for p in report['pairs'] if p['profile']==profile),'pass':sum(p['status']=='pass' for p in report['pairs'] if p['profile']==profile),'fail':sum(p['status']=='fail' for p in report['pairs'] if p['profile']==profile)} for profile in profiles},
         'all_runs_reached_dt_cap':all(r['dt_cap_reached'] for r in report['runs'].values()),
         'minimum_rho':min(v['diagnostics']['rho_min'] for r in report['runs'].values() for v in r['measurements'].values()),'minimum_p':min(v['diagnostics']['p_min'] for r in report['runs'].values() for v in r['measurements'].values()),
         'maximum_recorded_budget':max(abs(b) for r in report['runs'].values() for v in r['measurements'].values() for b in v['diagnostics']['normalized_budget_recorded']),
         'maximum_recomputed_budget':max(abs(b) for r in report['runs'].values() for v in r['measurements'].values() for b in v['diagnostics']['normalized_budget_recomputed'])}
report['review_summary']=summary;args.output.write_text(json.dumps(report,indent=2)+'\n');print('SUMMARY',json.dumps(summary),flush=True)
