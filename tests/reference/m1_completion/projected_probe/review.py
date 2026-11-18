from pathlib import Path
import hashlib,json,subprocess,io,math
import numpy as np
p=Path(__file__).resolve().parent;root=p.parents[2];study=root/'results/m1_projected_probe';sha=lambda b:hashlib.sha256(b).hexdigest();metadata={f:(study/f).read_bytes() for f in ['manifest.json','runs.json','provenance.json']};manifest=json.loads(metadata['manifest.json']);runs=json.loads(metadata['runs.json']);prov=json.loads(metadata['provenance.json']);revision='fb8bb14bf362a9eb42c2f32d6ec8c1252482790d';assert prov['revision']==revision and prov['dirty_status']=='' and prov['profile']=='bulk-frame-hll-projected-v1';assert set(manifest)==set(runs)=={'n32','n64','n128','n256'}
for f,h in prov['result_sha256'].items():assert sha(metadata[f])==h
binary=Path(runs['n32']['command'][0]);frozen=binary.parents[2];assert sha(binary.read_bytes())==prov['binary_sha256']
for f,h in prov['source_sha256'].items():assert sha(subprocess.check_output(['git','show',revision+':'+f],cwd=root))==h;assert sha((frozen/f).read_bytes())==h
cache_source_checks=0
for c in prov['mesh_caches'].values():
 assert sha(Path(c['path']).read_bytes())==c['sha256'];creator=c['creation']
 for f,h in creator['geometry_source_sha256'].items():assert sha(subprocess.check_output(['git','show',creator['revision']+':'+f],cwd=root))==h;cache_source_checks+=1
for f,b in metadata.items():(p/f).write_bytes(b)
rawdigests={};cases={};checks=0;maxabs=0.;maxrel=0.;max_totals_diff=0.;summaries={};histories={}
for n in [32,64,128,256]:
 name=f'n{n}';r=runs[name];config={'case':'alfven','jitter':.15,'n':n};assert manifest[name]==r['config']==config;assert r['status']=='completed' and r['exit_code']==0;expectedcmd=[str(binary),'--profile',prov['profile'],'--case','alfven','--n',str(n),'--jitter','.15','--time','1','--checkpoint','.25','--mesh-cache',prov['mesh_caches'][name]['path'],'--output',str(study/name)];assert r['command']==expectedcmd
 raw={f:(study/name/f).read_bytes() for f in r['sha256']};assert set(raw)=={'initial.csv','checkpoint_0.25000000.csv','final.csv','polygons.csv','history.json','summary.json','run.log'}
 for f,b in raw.items():assert sha(b)==r['sha256'][f];rawdigests[name+'/'+f]=dict(sha256=sha(b),bytes=len(b),local_path=str(study/name/f))
 s=json.loads(raw['summary.json']);assert s==r['summary'];summaries[name]=raw['summary.json'];histories[name]=raw['history.json'];expected={'completed':True,'requested_time':1,'profile':prov['profile'],'case':'alfven','n':n,'nx':n,'ny':n,'lengths':[1,1],'jitter':.15,'parallel_velocity':0,'time':1,'dt_cap':None,'limited':True,'motion':'fixed','boost':[0,0,0],'mesh_velocity':[0,0],'gamma':5/3,'mean_B':[1,0,0],'rejected_geometry':0,'rejected_state':0}
 for k,v in expected.items():assert s[k]==v,(name,k,s[k],v)
 history=json.loads(raw['history.json']);assert [x['time'] for x in history]==[0,.25,1];stages={};initial=None
 for stage,t in [('initial',0.),('checkpoint_0.25000000',.25),('final',1.)]:
  a=np.genfromtxt(io.BytesIO(raw[stage+'.csv']),delimiter=',',names=True);assert len(a)==n*n and np.array_equal(a['id'],np.arange(n*n)) and np.all(a['time']==t);assert all(np.all(np.isfinite(a[k])) for k in a.dtype.names);assert np.min(a['volume'])>0 and abs(np.sum(a['volume'])-1)<1e-12;assert np.min(a['rho'])>0 and np.min(a['p'])>0
  if initial is None:initial=a
  for k in ['id','x','y','volume']:assert np.array_equal(a[k],initial[k])
  phase=2*np.pi*(a['x']+t);w=a['volume']/np.sum(a['volume']);e={k:a[k]-ref for k,ref in [('bx',1),('by',.1*np.sin(phase)),('bz',.1*np.cos(phase)),('vx',0),('vy',.1*np.sin(phase)),('vz',.1*np.cos(phase))]};e['B']=np.sqrt(sum(e[k]**2 for k in ['bx','by','bz']));e['v']=np.sqrt(sum(e[k]**2 for k in ['vx','vy','vz']));norms={k:dict(L1=float(np.sum(w*abs(v))),L2=float(np.sqrt(np.sum(w*v*v))),max=float(np.max(abs(v)))) for k,v in e.items()}
  for k,d in norms.items():
   for metric,v in d.items():ref=r[stage+'_error'][k][metric];ad=abs(v-ref);rd=ad/max(abs(v),abs(ref),1e-25);maxabs=max(maxabs,ad);maxrel=max(maxrel,rd);assert ad<2e-14;checks+=1
  totals=np.array([np.sum(a['volume']*a['rho'])]+[np.sum(a['volume']*a['rho']*a[k]) for k in ['vx','vy','vz']]+[np.sum(a['volume']*a['energy'])]);reported=next(x for x in history if x['time']==t);d=float(np.max(abs(totals-np.array(reported['diagnostics']['totals']))));max_totals_diff=max(max_totals_diff,d);assert d<2e-13
  stages[stage]=dict(time=t,errors=norms,rho_min=float(np.min(a['rho'])),p_min=float(np.min(a['p'])),recomputed_conservative_totals=totals.tolist())
 cases[name]=dict(stages=stages,counts={k:s[k] for k in ['steps','rejected_cfl','rejected_state','rejected_geometry','dt_min','dt_max']},elapsed_monotonic_seconds=r['elapsed_seconds'],maximum_recorded_normalized_budget=max(abs(v) for x in history for v in x['diagnostics']['normalized_budget']))
 print(name,'verified B L1',stages['final']['errors']['B']['L1'],flush=True)
final_errors=[cases[f'n{n}']['stages']['final']['errors']['B']['L1'] for n in [32,64,128,256]];x=np.log(np.array([64.,128.,256.]));y=np.log(np.array(final_errors[1:]));order=-float(np.sum((x-x.mean())*(y-y.mean()))/np.sum((x-x.mean())**2));pair_orders=[math.log(final_errors[i]/final_errors[i+1])/math.log(2) for i in range(3)];finest_relative=final_errors[-1]/.1
captured=root/'results/review_resume/openmhd_projected_cleaning_n256_ai';cp=json.loads((captured/'provenance.json').read_text());assert sha((captured/'baseline_quarter.csv').read_bytes())==cp['baseline_snapshot_sha256']==runs['n256']['sha256']['checkpoint_0.25000000.csv'];assert (captured/'n256/initial.csv').read_bytes()==(study/'n256/initial.csv').read_bytes()
result=dict(scope='Separate AI review of completed bounded projected irregular travelling-wave ladder; registered order gate FAIL, not full M1 acceptance',revision=revision,metadata_sha256={f:sha(b) for f,b in metadata.items()},verified_committed_and_frozen_source_hashes=len(prov['source_sha256']),verified_cache_geometry_source_hashes=cache_source_checks,binary_verified=True,mesh_cache_hashes_verified=4,verified_raw_artifact_digests=len(rawdigests),raw_artifacts=rawdigests,independent_norm_comparisons=checks,maximum_absolute_norm_difference=maxabs,maximum_relative_norm_difference=maxrel,maximum_absolute_total_difference=max_totals_diff,cases=cases,final_B_L1=final_errors,adjacent_orders=pair_orders,finest_three_order=order,registered_gates=dict(order=dict(minimum=1.8,measured=order,status='pass' if order>=1.8 else 'fail'),finest_B_L1_relative_to_wave_amplitude=dict(amplitude=.1,maximum=.02,measured=finest_relative,status='pass' if finest_relative<=.02 else 'fail')),captured_n256_quarter_matches_final_run_seal=True,captured_n256_quarter_sha256=cp['baseline_snapshot_sha256'],no_forcing_initial_matches_sealed_baseline=True,full_M1_acceptance=False,review_script_sha256=sha(Path(__file__).read_bytes()))
(p/'review.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
for name,b in summaries.items():(p/(name+'_summary.json')).write_bytes(b)
for name,b in histories.items():(p/(name+'_history.json')).write_bytes(b)
print('order',order,'adjacent',pair_orders,'finest relative',finest_relative,'normchecks',checks,'maxabsolute',maxabs,'budgetmax',max(v['maximum_recorded_normalized_budget'] for v in cases.values()))
