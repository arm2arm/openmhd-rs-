#!/usr/bin/env python3
"""Independent AI read-only audit of completed coupled-loop inputs.

No solver/production measurement import or simulation. Incomplete evolutions
and pairs stay explicit; --require-complete refuses incomplete matrices.
Norm/read/diagnostic utilities reuse the independently archived mean checker.
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


AMPLITUDE=.001/math.sqrt(4*math.pi)
def passive(d,t,boost):
    dx=(d['x']-(2+boost[0])*t)%1-.5;dy=(d['y']-(1+boost[1])*t)%1-.5
    radius=np.array([math.hypot(x,y) for x,y in zip(dx,dy)]);a=AMPLITUDE*np.maximum(0.,.3-radius)
    use=(radius>1e-12)&(np.abs(radius-.3)>1e-12);inside=(radius>0)&(radius<.3)
    exact=np.zeros((len(radius),3));exact[inside,0]=-AMPLITUDE*dy[inside]/radius[inside];exact[inside,1]=AMPLITUDE*dx[inside]/radius[inside]
    field=np.column_stack([d[k] for k in ['bx','by','bz']])
    return {'passive_A':norm(d['az']-a,d['volume']),'passive_B':norm((field-exact)[use],d['volume'][use]),'passive_B_excluded_cells':int(np.sum(~use)),
      'reference_scope':'Passive diagnostic, not an exact coupled-MHD solution'},a

def check_norms(values,weights,reported,label):
    measured=norm(values,weights);measured['mean']=math.fsum(values*weights)/math.fsum(weights)
    for key,target in [('L2','rms'),('max','max')]:assert math.isclose(measured[key],reported[target],rel_tol=5e-10,abs_tol=1e-22),(label,key,measured[key],reported[target])
    # The signed mean may nearly cancel huge scaled values; account for reduction error.
    assert abs(measured['mean']-reported['mean'])<=5e-11*measured['L1']+1e-22,(label,'mean',measured['mean'],reported['mean'],measured['L1'])
    return measured

parser=argparse.ArgumentParser();parser.add_argument('original',type=Path);parser.add_argument('signal',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--require-complete',action='store_true');args=parser.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();repository=Path(__file__).resolve().parents[4]
packet_path=repository/'benchmarks/m1/packet-v2.json';packet=json.loads(packet_path.read_text());gate=packet['cases']['loop']['gate']['coupled_boost_relative_B_L1_max'];assert gate==.001
report={'scope':'Independent AI audit of completed coupled-loop evolutions only; incomplete runs/pairs remain unexecuted. No certification of global packet completion, final archives or full M1.',
 'created_utc':datetime.now(timezone.utc).isoformat(),'numpy':np.__version__,'expected_runs':64,'expected_pairs':32,'source_inputs':{},'runs':{},'unfinished_runs':[],'pairs':[],'resolution_observations':[],
 'registered_requirement_sha256':{path:sha(repository/path) for path in ['benchmarks/m1/packet-v2.json','docs/M1_WAVE_LOOP_PLAN.md','docs/M1_COMPLETION_PLAN.md','docs/M0_BENCHMARK_PACKET.md']},
 'gate_definition':{'B_vector_boost_L1_divided_by':AMPLITUDE,'maximum':gate,'pairing_position_and_relative_volume_max':1e-11,'periodic_conservative_budget_max':1e-10,'rho_and_p':'strictly positive'},
 'interpretation':'Coupled finite-field MHD has magnetic feedback. Passive A/B comparisons are diagnostics, not exact coupled-solution errors; prescribed-flow drift and finest-A gates are not applied to this matrix. No second-order requirement for the nonsmooth loop. Divergence norms independently reduced from CSV operator columns, not a fresh reconstruction of face stencils.'}
for root,profile in [(args.original,'paper-global-v2'),(args.signal,'bulk-frame-signal-v1')]:
    inputs={name:(root/name).read_bytes() for name in ['manifest.json','runs.json','provenance.json']};records=json.loads(inputs['runs.json']);manifest=json.loads(inputs['manifest.json']);execution=json.loads(inputs['provenance.json']);checkout=root.parent.parent
    names=[n for n in manifest if n.startswith('loop_')];assert len(names)==32
    for path,digest in execution['source_sha256'].items():assert sha(checkout/path)==digest,(profile,path)
    assert sha(checkout/'target/release/vector-potential')==execution['binary_sha256']
    report['source_inputs'][profile]={'checkout':str(checkout),'root':str(root),'revision':execution['revision'],'configuration':execution['configuration'],'source_sha256':execution['source_sha256'],'binary_sha256':execution['binary_sha256'],
      'observed_containing_file_sha256':{name:hashlib.sha256(data).hexdigest() for name,data in inputs.items()},'containing_hash_scope':'Exact observed bytes only; not global execution completion certification.'}
    for jitter in [0.,.15]:
      for motion in ['fixed','comoving']:
        for n in [32,64,128,256]:
          prefix=f'loop_{profile}_v0.0_j{jitter}_{motion}_n{n}';data={};pair_names=[prefix+'_base',prefix+'_boost']
          for boosted,name in zip([False,True],pair_names):
            boost=[2.,-1.,0.] if boosted else [0.,0.,0.];base_mesh=[0.,0.] if motion=='fixed' else [2.,1.];mesh=[a+b for a,b in zip(base_mesh,boost)]
            expected={'name':name,'case':'loop','profile':profile,'n':n,'jitter':jitter,'parallel':0.,'motion_family':motion,'mesh_velocity':mesh,'boost':boost,'dt':None,'target':1.}
            assert manifest[name]==expected
            if name not in records or records[name]['status']!='completed':
                report['unfinished_runs'].append({'name':name,'config':expected,'observed_status':records.get(name,{}).get('status','not yet recorded'),'observed_record_sha256':hashlib.sha256(json.dumps(records.get(name),sort_keys=True,separators=(',',':')).encode()).hexdigest() if name in records else None});continue
            r=records[name];c=r['config'];s=r['summary'];assert r['returncode']==0 and c==expected
            assert s['completed'] and s['case']=='loop' and s['profile']==profile and s['time']==s['requested_time']==1. and s['dt_cap'] is None
            assert s['n']==n and s['jitter']==jitter and s['parallel_velocity']==0. and s['mesh_velocity']==mesh and s['boost']==boost
            assert s['gamma']==5/3 and s['mean_B']==[0.,0.,0.] and math.isclose(s['Bscale'],AMPLITUDE,rel_tol=1e-15) and s['limited'] and s['motion']=='rigid' and s['gauge_offset']==[0.,0.,0.]
            assert len(r['command'])%2==1 and len(set(r['command'][1::2]))==len(r['command'][1::2]);cmd=dict(zip(r['command'][1::2],r['command'][2::2]))
            assert Path(r['command'][0]).resolve()==(checkout/'target/release/vector-potential').resolve()
            assert cmd['--case']=='loop' and cmd['--profile']==profile and cmd['--motion']=='rigid' and '--dt' not in cmd
            assert int(cmd['--n'])==n and float(cmd['--jitter'])==jitter and float(cmd['--parallel-velocity'])==0. and float(cmd['--time'])==1. and float(cmd['--checkpoint'])==.25
            assert [float(cmd['--boost-'+k]) for k in ['x','y','z']]==boost and [float(cmd['--mesh-'+k]) for k in ['x','y']]==mesh
            assert Path(cmd['--output']).resolve()==(root/name).resolve()
            assert json.loads((root/name/'summary.json').read_text())==s and json.loads((root/name/'history.json').read_text())==r['history']
            assert set(r['sha256'])=={'initial.csv','checkpoint_0.25000000.csv','final.csv','summary.json','history.json','run.log'}
            for filename,digest in r['sha256'].items():assert sha(root/name/filename)==digest,(name,filename)
            assert [h['time'] for h in r['history']]==[0.,.25,1.] and s['initial']==r['history'][0]['diagnostics'] and s['final']==r['history'][-1]['diagnostics']
            assert len(s['auxiliary_roots'])==s['steps'] and s['steps']>0 and 0<s['dt_min']<=s['dt_max']
            measurements={};snapshots={};initial=None;positive=True;budget_pass=True
            for stage,filename,t in [('initial','initial.csv',0.),('t0.25','checkpoint_0.25000000.csv',.25),('final','final.csv',1.)]:
              d=read(root/name/filename,n,t);diag=diagnostics(d);errors,analytic_a=passive(d,t,boost);original=next(h['diagnostics'] for h in r['history'] if h['time']==t)
              for key in ['passive_A','passive_B']:
                for nk,value in errors[key].items():assert math.isclose(value,r['errors'][stage][key][nk],rel_tol=5e-10,abs_tol=2e-18),(name,stage,key,nk,value,r['errors'][stage][key][nk])
              assert errors['passive_B_excluded_cells']==r['errors'][stage]['passive_B_excluded_cells'] and r['errors'][stage]['reference_scope']=='passive diagnostic, not an exact coupled-MHD solution'
              if initial is None:
                initial=d;initial_diag=diag;scales=np.array(diag['initial_normalization_if_applied'])
                initial_checks={'Az_max':errors['passive_A']['max'],'Ax_max':float(np.max(np.abs(d['ax']))),'Ay_max':float(np.max(np.abs(d['ay']))),
                  'v_max':float(np.max(np.abs(np.column_stack([d[k] for k in ['vx','vy','vz']])-np.array([2.+boost[0],1.+boost[1],boost[2]])))),
                  'rho_max':float(np.max(np.abs(d['rho']-1))),'p_max':float(np.max(np.abs(d['p']-1))),'phi_max':float(np.max(np.abs(d['phi'])))}
                assert max(initial_checks.values())<1e-14 and np.max(np.abs(np.array(original['budget_scales'])-scales)/scales)<1e-11
              geom=max(float(np.max(np.abs((d[k]-initial[k]-q*t+.5)%1-.5))) for k,q in zip(['x','y'],mesh));vol=float(np.max(np.abs(d['volume']-initial['volume'])/initial['volume']))
              assert geom<=1e-11 and vol<=1e-11,(name,stage,'geometry',geom,vol)
              budgets=(np.array(diag['totals'])-np.array(initial_diag['totals']))/scales;diag['normalized_budget_recomputed']=budgets.tolist();diag['normalized_budget_recorded']=original['normalized_budget'];diag['budget_reduction_difference_max']=float(np.max(np.abs(budgets-original['normalized_budget'])))
              assert diag['budget_reduction_difference_max']<1e-11
              for key in ['rho_min','rho_max','p_min','p_max']:assert math.isclose(diag[key],original[key],rel_tol=1e-12,abs_tol=1e-13)
              assert math.isclose(diag['magnetic_energy'],original['magnetic_energy'],rel_tol=1e-11,abs_tol=1e-22)
              assert np.max(np.abs(np.array(diag['mean_B'])-original['mean_B']))<1e-15
              bmag=np.hypot(np.hypot(d['bx'],d['by']),d['bz']);norms={}
              for column,label in [('div_b_ls','div_B_ls'),('div_b_face','div_B_face'),('div_b_limited','div_B_limited')]:
                scaled=np.sqrt(d['volume']/math.pi)*d[column]/(bmag+1e-12*AMPLITUDE)
                norms[column]={scale:check_norms(values,d['volume'],original[label][scale],(name,stage,label,scale)) for scale,values in [('dimensional',d[column]),('dimensionless',scaled)]}
              for column,label in [('div_a','div_A'),('phi','phi')]:norms[column]=check_norms(d[column],d['volume'],original[label],(name,stage,label))
              diag['all_operator_norms']=norms;diag['recorded_condition_numbers']={k:original[k] for k in ['neighbour_condition','face_condition']}
              positive=positive and diag['rho_min']>0 and diag['p_min']>0;budget_pass=budget_pass and float(np.max(np.abs(budgets)))<=1e-10 and max(map(abs,original['normalized_budget']))<=1e-10
              drift={key:norm(d[key]-initial[key],d['volume']) for key in ['ax','ay','az','phi']};drift['B']=norm(np.column_stack([d[k]-initial[k] for k in ['bx','by','bz']]),d['volume'])
              measurements[stage]={'passive_errors':errors,'passive_A_L1_over_peak':errors['passive_A']['L1']/(.3*AMPLITUDE),'passive_B_L1_over_amplitude':errors['passive_B']['L1']/AMPLITUDE,
                'diagnostics':diag,'rigid_position_residual_max':geom,'relative_volume_drift_max':vol,'magnetic_energy_over_initial':diag['magnetic_energy']/initial_diag['magnetic_energy'],
                'maximum_B_over_amplitude':float(np.max(bmag))/AMPLITUDE,'discrete_persistent_id_drift':drift,'discrete_drift_scope':'Comoving comparisons include finite magnetic feedback; no prescribed-flow exact-drift gate applies. Fixed-grid persistent-ID drift is not a transport error.'}
              snapshots[stage]=d
            assert bool(positive and budget_pass)==r['positive_and_conservative']
            report['runs'][name]={'config':c,'command':r['command'],'input_sha256':r['sha256'],'source_record_sha256':hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
              'summary':{k:v for k,v in s.items() if k not in ['auxiliary_roots','initial','final']},'auxiliary_root_values':sorted(set(s['auxiliary_roots'])),'auxiliary_root_sequence_length':len(s['auxiliary_roots']),
              'positive_at_recorded_outputs':positive,'budget_gate':budget_pass,'positive_and_conservative':positive and budget_pass,'initial_constructor_max_errors':initial_checks,'measurements':measurements}
            data[name]=snapshots;print('verified',name,flush=True)
          pair={'profile':profile,'n':n,'jitter':jitter,'motion':motion,'names':pair_names}
          if len(data)!=2:pair['status']='unexecuted: incomplete pair';pair['completed_names']=list(data)
          else:
            pair['times']={stage:dict(zip(['errors','geometry'],pair_error(data[pair_names[0]][stage],data[pair_names[1]][stage],t))) for stage,t in [('initial',0.),('t0.25',.25),('final',1.)]}
            final=pair['times']['final'];pair['pairing_valid']=max(final['geometry'].values())<=1e-11
            pair['positive_and_conservative']=all(report['runs'][name]['positive_and_conservative'] for name in pair_names)
            pair['matching_auxiliary_roots']=records[pair_names[0]]['summary']['auxiliary_roots']==records[pair_names[1]]['summary']['auxiliary_roots']
            pair['B_relative_L1']=final['errors']['B']['L1']/AMPLITUDE;pair['status']='pass' if pair['pairing_valid'] and pair['positive_and_conservative'] and pair['B_relative_L1']<=gate else 'fail'
            print('pair',prefix,pair['status'],'B L1/amplitude',pair['B_relative_L1'],'geometry',pair['pairing_valid'],'matching roots',pair['matching_auxiliary_roots'],flush=True)
          report['pairs'].append(pair)
        selected=[r for name,r in report['runs'].items() if r['config']['profile']==profile and r['config']['jitter']==jitter and r['config']['motion_family']==motion and name.endswith('_base')];selected.sort(key=lambda r:r['config']['n'])
        coordinates=[r['config']['n'] for r in selected];values=[r['measurements']['final']['passive_A_L1_over_peak'] for r in selected];orders=[math.log(a/b)/math.log(nb/na) if a and b else None for a,b,na,nb in zip(values,values[1:],coordinates,coordinates[1:])]
        report['resolution_observations'].append({'profile':profile,'jitter':jitter,'motion':motion,'n':coordinates,'passive_A_L1_over_peak':values,'passive_B_L1_over_amplitude':[r['measurements']['final']['passive_B_L1_over_amplitude'] for r in selected],
          'magnetic_energy_over_initial':[r['measurements']['final']['magnetic_energy_over_initial'] for r in selected],'adjacent_passive_A_L1_slopes':orders,'complete_resolution_ladder':coordinates==[32,64,128,256],
          'scope':'Coupled-MHD passive-reference resolution diagnostics only; no prescribed-flow A gate or second-order expectation imposed.'})
summary={'runs_reviewed':len(report['runs']),'snapshot_count':3*len(report['runs']),'unfinished_runs':len(report['unfinished_runs']),'complete_loop_matrix':len(report['runs'])==64 and not report['unfinished_runs'],
 'positive_budget_runs':sum(r['positive_and_conservative'] for r in report['runs'].values()),'pairs_pass':sum(p['status']=='pass' for p in report['pairs']),'pairs_fail':sum(p['status']=='fail' for p in report['pairs']),'pairs_unexecuted':sum(p['status'].startswith('unexecuted') for p in report['pairs']),
 'per_profile':{profile:{'runs_reviewed':sum(r['config']['profile']==profile for r in report['runs'].values()),'pairs_pass':sum(p['profile']==profile and p['status']=='pass' for p in report['pairs']),'pairs_fail':sum(p['profile']==profile and p['status']=='fail' for p in report['pairs']),'pairs_unexecuted':sum(p['profile']==profile and p['status'].startswith('unexecuted') for p in report['pairs'])} for profile in ['paper-global-v2','bulk-frame-signal-v1']},
 'minimum_rho':min(v['diagnostics']['rho_min'] for r in report['runs'].values() for v in r['measurements'].values()),'minimum_p':min(v['diagnostics']['p_min'] for r in report['runs'].values() for v in r['measurements'].values()),
 'maximum_recorded_budget':max(abs(b) for r in report['runs'].values() for v in r['measurements'].values() for b in v['diagnostics']['normalized_budget_recorded']),
 'maximum_recomputed_budget':max(abs(b) for r in report['runs'].values() for v in r['measurements'].values() for b in v['diagnostics']['normalized_budget_recomputed']),
 'maximum_B_relative_boost_L1':max(p['B_relative_L1'] for p in report['pairs'] if 'B_relative_L1' in p)}
report['review_summary']=summary
if args.require_complete:assert summary['complete_loop_matrix'],'Refusing complete-loop report while inputs remain unfinished'
args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print('SUMMARY',json.dumps(summary),flush=True)
