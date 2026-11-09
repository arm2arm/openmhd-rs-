#!/usr/bin/env python3
"""Independent read-only AI audit of completed physical temporal runs.

No production measurement code is imported; no simulation is run. Numerical
utilities are copied from the independently archived wave checker. Same-grid
finite-reference errors and cap-ratio slopes are diagnostics, without a new
accuracy gate or claims about roundoff-scale slopes.
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


def cap_clock(dt):
    """Clock-only repeated cap model; not a solver or a per-step timestep trace."""
    t=0.; steps=[]
    for target in [.25,1.]:
        while t<target:
            step=min(dt,target-t);steps.append(step);t=min(t+step,target)
    return {'steps':len(steps),'dt_min':min(steps),'dt_max':max(steps),'sub_cap_steps':[v for v in steps if v<dt]}

parser=argparse.ArgumentParser();parser.add_argument('original',type=Path);parser.add_argument('signal',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'scope':'Independent AI audit of completed 32-run physical temporal packet only. Containing global execution packets may still be active; not full M1 acceptance.',
 'created_utc':datetime.now(timezone.utc).isoformat(),'numpy':np.__version__,'source_inputs':{},'runs':{},'ladders':[],
 'interpretation':{'reference':'Same N64 fixed grid and initial state, dt cap 2.5e-5; this reference is finite, not the exact semi-discrete solution.',
 'order':'Adjacent L1 cap-ratio slopes only, no prospective physical temporal accuracy gate exists. Preserve negative/noise-dominated values without claiming physical accuracy orders.',
 'gauge':'A components are total A in each profile gauge; phi is cleaning scalar. They are reported separately from physical B. Profiles are compared only to references in their own gauge.',
 'frozen_C1':'Frozen initial div(A) and sound speed retained in endpoint cleaning stage; this packet does not replace the independent gauge-mode test or establish general second-order time accuracy.',
 'time_history':'Only aggregate accepted min/max/step counts, rejection counts, root sequence and output-time diagnostics are available. Clock-model agreement is not a recorded full per-step dt trace.',
 'finite_reference_linear_error_example':{'assumption':'If the leading same-grid error is C*dt with fixed C, subtraction of a nonzero dt_ref gives these apparent slopes; this is an illustration, not a fitted mechanism proof.','adjacent_slopes':[math.log2((4e-4-2.5e-5)/(2e-4-2.5e-5)),math.log2((2e-4-2.5e-5)/(1e-4-2.5e-5))]},
 'roundoff_components':'Regular travelling bx in both profiles is about 1.5e-16; regular standing signal bx is about 2e-15. Their recorded positive/negative slopes are roundoff diagnostics, not accuracy orders.'}}
repository=Path(__file__).resolve().parents[4]
registration={
 'docs/M1_WAVE_LOOP_PLAN.md':'Preserve the original N64 temporal ladder and same-grid finer-dt reference; gauge and physical-field accuracy remain distinct.',
 'docs/M1_COMPLETION_PLAN.md':'Run the full original-profile physical spatial/temporal packet from a frozen',
 'docs/M0_BENCHMARK_PACKET.md':'At fixed N64 use the listed dt ladder against the same-grid finer-dt reference, report order, and distinguish physical B from the first-order gauge-cleaning mode.',
 'docs/M0_ENGINEERING_DECISIONS.md':'Report temporal errors of physical B and gauge-dependent A/phi independently.'}
for path,excerpt in registration.items():assert excerpt in (repository/path).read_text()
packet_path=repository/'benchmarks/m1/packet-v2.json';packet=json.loads(packet_path.read_text())
assert packet['cases']['alfven']['temporal']=={'resolution':64,'fixed_dt':[.0004,.0002,.0001],'compare':'same-grid dt=0.000025 reference; report physical B and A/phi separately'}
report['registration_cross_check']={'required_file_sha256':{path:sha(repository/path) for path in [*registration,'benchmarks/m1/packet-v2.json']},
 'reviewed_excerpts':registration,'temporal_packet':packet['cases']['alfven']['temporal'],
 'assessment':'The explicit 1.8 order gate applies to spatial N refinement. The physical temporal protocol requires the stated same-grid reference and separate B/A/phi error/order reporting, without a numeric temporal-order gate. This is checked against the plans and inherited M0 contract, not inferred from the production runner. Failed/nonmonotone/sublinear physical behavior remains reported; second-order physical time accuracy is not established.'}
for root,profile in [(args.original,'paper-global-v2'),(args.signal,'bulk-frame-signal-v1')]:
    inputs={name:(root/name).read_bytes() for name in ['manifest.json','runs.json','provenance.json']}
    records=json.loads(inputs['runs.json']);manifest=json.loads(inputs['manifest.json']);execution=json.loads(inputs['provenance.json']);checkout=root.parent.parent
    names=[n for n in manifest if n.startswith('temporal_')];assert len(names)==16
    assert all(n in records and records[n]['status']=='completed' and records[n]['returncode']==0 for n in names)
    for path,digest in execution['source_sha256'].items():assert sha(checkout/path)==digest,(profile,path)
    assert sha(checkout/'target/release/vector-potential')==execution['binary_sha256']
    report['source_inputs'][profile]={'checkout':str(checkout),'root':str(root),'revision':execution['revision'],'configuration':execution['configuration'],
      'source_sha256':execution['source_sha256'],'binary_sha256':execution['binary_sha256'],
      'observed_containing_file_sha256':{name:hashlib.sha256(data).hexdigest() for name,data in inputs.items()},
      'containing_hash_scope':'Exact bytes inspected, not completion certification; runs.json/provenance.json may continue changing as unreviewed loop runs finish.'}
    for parallel in [0.,1.]:
      for jitter in [0.,.15]:
        data={}
        for dt in [.0004,.0002,.0001,.000025]:
          name=f'temporal_{profile}_v{parallel}_j{jitter}_dt{dt}';r=records[name];c=r['config'];s=r['summary']
          expected={'name':name,'case':'alfven','profile':profile,'n':64,'jitter':jitter,'parallel':parallel,'motion_family':'fixed','mesh_velocity':[0.,0.],'boost':[0.,0.,0.],'dt':dt,'target':1.}
          assert c==manifest[name]==expected
          assert s['completed'] and s['case']=='alfven' and s['profile']==profile and s['time']==s['requested_time']==1. and s['dt_cap']==dt
          assert s['n']==64 and s['jitter']==jitter and s['parallel_velocity']==parallel and s['mesh_velocity']==[0.,0.] and s['boost']==[0.,0.,0.]
          assert s['gamma']==5/3 and s['mean_B']==[1.,0.,0.] and s['Bscale']==1 and s['limited'] and s['motion']=='rigid'
          assert len(r['command'])%2==1 and len(set(r['command'][1::2]))==len(r['command'][1::2]);cmd=dict(zip(r['command'][1::2],r['command'][2::2]))
          assert Path(r['command'][0]).resolve()==(checkout/'target/release/vector-potential').resolve()
          assert cmd['--case']=='alfven' and cmd['--profile']==profile and cmd['--motion']=='rigid'
          assert int(cmd['--n'])==64 and float(cmd['--jitter'])==jitter and float(cmd['--parallel-velocity'])==parallel and float(cmd['--dt'])==dt and float(cmd['--time'])==1. and float(cmd['--checkpoint'])==.25
          assert [float(cmd['--boost-'+k]) for k in ['x','y','z']]==[0.,0.,0.] and [float(cmd['--mesh-'+k]) for k in ['x','y']]==[0.,0.]
          assert Path(cmd['--output']).resolve()==(root/name).resolve()
          assert json.loads((root/name/'summary.json').read_text())==s and json.loads((root/name/'history.json').read_text())==r['history']
          expected_files={'initial.csv','checkpoint_0.25000000.csv','final.csv','summary.json','history.json','run.log'}
          assert set(r['sha256'])==expected_files
          for filename,digest in r['sha256'].items():assert sha(root/name/filename)==digest,(name,filename)
          assert [h['time'] for h in r['history']]==[0.,.25,1.]
          assert s['initial']==r['history'][0]['diagnostics'] and s['final']==r['history'][-1]['diagnostics']
          assert len(s['auxiliary_roots'])==s['steps'] and s['steps']>0
          clock=cap_clock(dt);clock_match=all(s[k]==clock[k] for k in ['steps','dt_min','dt_max'])
          assert clock_match and s['dt_max']<=dt and s['dt_min']>0
          assert all(s[k]==0 for k in ['rejected_geometry','rejected_state','rejected_cfl'])
          measured={};snapshots={};initial=None;positive=True;budget_pass=True
          for stage,filename,t in [('initial','initial.csv',0.),('t0.25','checkpoint_0.25000000.csv',.25),('final','final.csv',1.)]:
            d=read(root/name/filename,64,t);diag=diagnostics(d);errors,extra=physical(d,t,c);original=next(h['diagnostics'] for h in r['history'] if h['time']==t)
            for key,values in errors.items():
              for nk,value in values.items():assert math.isclose(value,r['errors'][stage][key][nk],rel_tol=5e-10,abs_tol=2e-17),(name,stage,key,nk)
            if initial is None:
              initial=d;initial_diag=diag;scales=np.array(diag['initial_normalization_if_applied'])
              analytic_a=np.column_stack([np.zeros(64**2),[.1/(2*math.pi)*math.sin(2*math.pi*x) for x in d['x']],[.1/(2*math.pi)*math.cos(2*math.pi*x) for x in d['x']]])
              initial_checks={'A_max':float(np.max(np.abs(np.column_stack([d[k] for k in ['ax','ay','az']])-analytic_a))),
                  'v_max':errors['v']['max'],'rho_max':float(np.max(np.abs(d['rho']-1))),'p_max':float(np.max(np.abs(d['p']-.1))),'phi_max':float(np.max(np.abs(d['phi'])))}
              assert max(initial_checks.values())<1e-14
              assert np.max(np.abs(np.array(original['budget_scales'])-scales)/scales)<1e-11
            geom=max(float(np.max(np.abs(d[k]-initial[k]))) for k in ['x','y']);vol=float(np.max(np.abs(d['volume']-initial['volume'])/initial['volume']))
            assert geom==vol==0.,(name,stage,'fixed mesh changed')
            budgets=(np.array(diag['totals'])-np.array(initial_diag['totals']))/scales
            diag['normalized_budget_recomputed']=budgets.tolist();diag['normalized_budget_recorded']=original['normalized_budget'];diag['budget_reduction_difference_max']=float(np.max(np.abs(budgets-original['normalized_budget'])))
            assert diag['budget_reduction_difference_max']<1e-11
            for key in ['rho_min','rho_max','p_min','p_max']:assert math.isclose(diag[key],original[key],rel_tol=1e-12,abs_tol=1e-13)
            assert abs(diag['magnetic_energy']-original['magnetic_energy'])<1e-11
            for column,label in [('div_b_ls','div_B_ls'),('div_b_face','div_B_face'),('div_b_limited','div_B_limited')]:
              assert math.isclose(diag['divergence'][column]['L2'],original[label]['dimensional']['rms'],rel_tol=5e-10,abs_tol=1e-15)
            positive=positive and diag['rho_min']>0 and diag['p_min']>0
            budget_pass=budget_pass and float(np.max(np.abs(budgets)))<=1e-10 and max(map(abs,original['normalized_budget']))<=1e-10
            measured[stage]={'physical_errors':errors,'diagnostics':diag,'fixed_position_residual_max':geom,'relative_volume_drift_max':vol}
            snapshots[stage]=d
          assert bool(positive and budget_pass)==r['positive_and_conservative']
          report['runs'][name]={'config':c,'command':r['command'],'input_sha256':r['sha256'],
            'source_record_sha256':hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'summary':{k:v for k,v in s.items() if k not in ['auxiliary_roots','initial','final']},
            'auxiliary_root_values':sorted(set(s['auxiliary_roots'])),'auxiliary_root_sequence_length':len(s['auxiliary_roots']),
            'positive_at_recorded_outputs':positive,'budget_gate':budget_pass,'positive_and_conservative':positive and budget_pass,
            'initial_constructor_max_errors':initial_checks,'dt_cap_reached':s['dt_max']==dt,'cap_clock_model':clock,'aggregate_clock_model_matches':clock_match,'measurements':measured}
          data[dt]=snapshots
        ref=data[.000025];refname=f'temporal_{profile}_v{parallel}_j{jitter}_dt2.5e-05';comparisons=[]
        for dt in [.0004,.0002,.0001]:
          name=f'temporal_{profile}_v{parallel}_j{jitter}_dt{dt}';initial=data[dt]['initial'];reference_initial=ref['initial']
          assert set(initial)==set(reference_initial) and all(np.array_equal(initial[k],reference_initial[k]) for k in initial)
          times={}
          for stage in ['t0.25','final']:
            d=data[dt][stage];rr=ref[stage];v=rr['volume']
            assert all(np.array_equal(d[k],rr[k]) for k in ['id','time','x','y','volume'])
            errors={k:norm(d[k]-rr[k],v) for k in ['bx','by','bz','ax','ay','az','phi','reduced_ax','reduced_ay','reduced_az']}
            for label,keys in [('B',['bx','by','bz']),('A',['ax','ay','az']),('reduced_A',['reduced_ax','reduced_ay','reduced_az'])]:
              errors[label]=norm(np.column_stack([d[k]-rr[k] for k in keys]),v)
            times[stage]={'errors':errors,'position_difference_max':0.,'relative_volume_difference_max':0.}
          comparisons.append({'name':name,'reference':refname,'dt_cap':dt,'initial_snapshots_bitwise_identical':True,'same_grid_pairing_valid':True,'times':times})
        orders={stage:{key:[math.log2(left['times'][stage]['errors'][key]['L1']/right['times'][stage]['errors'][key]['L1']) if left['times'][stage]['errors'][key]['L1'] and right['times'][stage]['errors'][key]['L1'] else None for left,right in zip(comparisons,comparisons[1:])] for key in comparisons[0]['times'][stage]['errors']} for stage in ['t0.25','final']}
        ladder={'profile':profile,'parallel':parallel,'jitter':jitter,'n':64,'motion':'fixed','dt_caps':[.0004,.0002,.0001],'reference_dt_cap':.000025,'comparisons':comparisons,'adjacent_cap_ratio_L1_orders':orders,'temporal_accuracy_gate_applied':False}
        report['ladders'].append(ladder)
        print(profile,'v',parallel,'jitter',jitter,flush=True)
        for key in ['B','ax','ay','az','phi','A']:
          print(' ',key,'L1',[p['times']['final']['errors'][key]['L1'] for p in comparisons],'adjacent slopes',orders['final'][key],flush=True)
summary={'runs':len(report['runs']),'snapshots':3*len(report['runs']),'ladders':len(report['ladders']),'reference_comparisons':sum(len(x['comparisons']) for x in report['ladders']),
 'positive_budget_runs':sum(r['positive_and_conservative'] for r in report['runs'].values()),'cap_reached_runs':sum(r['dt_cap_reached'] for r in report['runs'].values()),
 'cap_clock_aggregate_matches':sum(r['aggregate_clock_model_matches'] for r in report['runs'].values()),
 'minimum_rho':min(v['diagnostics']['rho_min'] for r in report['runs'].values() for v in r['measurements'].values()),'minimum_p':min(v['diagnostics']['p_min'] for r in report['runs'].values() for v in r['measurements'].values()),
 'maximum_recorded_budget':max(abs(b) for r in report['runs'].values() for v in r['measurements'].values() for b in v['diagnostics']['normalized_budget_recorded']),
 'maximum_recomputed_budget':max(abs(b) for r in report['runs'].values() for v in r['measurements'].values() for b in v['diagnostics']['normalized_budget_recomputed']),
 'rejected_geometry':sum(r['summary']['rejected_geometry'] for r in report['runs'].values()),'rejected_state':sum(r['summary']['rejected_state'] for r in report['runs'].values()),'rejected_cfl':sum(r['summary']['rejected_cfl'] for r in report['runs'].values()),
 'all_auxiliary_root_values':sorted({v for r in report['runs'].values() for v in r['auxiliary_root_values']}),
 'auxiliary_coarsenings':sum(r['summary']['auxiliary_coarsenings'] for r in report['runs'].values()),
 'hll_fallbacks_accepted_equal_attempted':all(r['summary']['hll_fallbacks']==r['summary']['hll_fallbacks_attempted'] for r in report['runs'].values())}
report['review_summary']=summary;args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print('SUMMARY',json.dumps(summary),flush=True)
print('Completed per-run temporal review only; no temporal accuracy pass/fail gate introduced; loop/final archive review remains pending.',flush=True)
