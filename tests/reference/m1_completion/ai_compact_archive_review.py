import gzip,hashlib,json,math,pathlib,shlex,subprocess
ROOT=pathlib.Path('/Users/arm2arm/orca/workspaces/openmhd-rs-/M0')
AR=ROOT/'tests/reference/m1_completion'
def sha(b): return hashlib.sha256(b).hexdigest()
def fsha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def archive(p,provname):
 a=json.loads((p/provname).read_bytes()); blobs={}
 compressed=a.get('archive_sha256',a.get('compressed_sha256'))
 for name,digest in compressed.items():assert fsha(p/name)==digest,(p,name,'compressed')
 for name,digest in a['uncompressed_sha256'].items():
  b=gzip.decompress((p/(name+'.gz')).read_bytes());assert sha(b)==digest,(p,name,'uncompressed');blobs[name]=b
 return a,blobs
p=AR/'matched_wave_interrupted';a,b=archive(p,'partial_archive_provenance.json')
s=json.loads(b['summary.json']);m=json.loads(b['manifest.json']);r=json.loads(b['runs.json']);i=json.loads(b['interruption.json'])
for n,h in i['captured_metadata_sha256'].items():assert sha(b[n])==h,(n,'captured')
script=subprocess.check_output(['git','show',a['measurement_revision']+':scripts/run_m1_wave_loop.py'],cwd=ROOT)
assert sha(script)==a['measurement_script_sha256']
part={k:set(v) for k,v in s['execution_partition'].items()}
assert all(len(part[k])==len(s['execution_partition'][k]) for k in part)
assert part['completed']==set(r)==set(s['runs'])
assert not(part['completed']&part['externally_stopped'] or part['completed']&part['unexecuted'] or part['externally_stopped']&part['unexecuted'])
assert set().union(*part.values())==set(m)
stopped=set()
for _,cmd in i['terminated_processes']:
 args=shlex.split(cmd)
 if '--output' in args:stopped.add(pathlib.Path(args[args.index('--output')+1]).name)
assert stopped==part['externally_stopped']
raw=0
for name,v in r.items():
 assert v['status']=='completed' and v['returncode']==0 and v['config']==m[name]
 assert {'initial.csv','final.csv','summary.json','run.log'}<=set(v['sha256'])
 for file,h in v['sha256'].items():
  assert fsha(ROOT/'results/m1_matched_full'/name/file)==h,(name,file);raw+=1
assert raw==a['verified_raw_artifacts']
ladder=[x for x in s['alfven_convergence'] if x['jitter']==.15 and x['parallel']==0 and x['motion']=='fixed'][0]
assert ladder['gate']=='fail' and abs(ladder['finest_three_order']-.7724306660224297)<1e-13
print(json.dumps({'packet':'matched_wave_interrupted','metadata_files':len(b),'raw_files':raw,'partition':{k:len(v) for k,v in part.items()},'order':ladder['finest_three_order'],'gate':ladder['gate']}),flush=True)
for name in ['quadratic','consistent','matched']:
 a,b=archive(AR/'wave_probes'/name,'archive_provenance.json');p=json.loads(b['provenance.json']);r=json.loads(b['runs.json']);m=json.loads(b['manifest.json']);raw=0
 for file,h in p['result_sha256'].items():assert sha(b[file])==h,(name,file,'seal')
 assert set(r)==set(m)=={'n32','n64','n128','n256'}
 for key,v in r.items():
  assert v['config']==m[key]
  for file,h in v['sha256'].items():
   assert fsha(ROOT/('results/m1_'+name+'_probe')/key/file)==h,(name,key,file);raw+=1
  if key!='n256' or name=='matched': assert v['status']=='completed' and v['exit_code']==0
  else:
   assert v['status']=='failed evolution' and v['exit_code']==-15 and 'final_error' not in v
   control=json.loads(b['external_stop.json']);assert len(control['terminated_processes'])==1
   args=shlex.split(control['terminated_processes'][0][1]);assert pathlib.Path(args[args.index('--output')+1]).name==key
 assert raw==a['verified_raw_artifacts']
 print(json.dumps({'packet':name,'metadata_files':len(b),'raw_files':raw,'final_B_L1':{k:v.get('final_error',{}).get('B',{}).get('L1') for k,v in r.items()},'external_stops':0 if name=='matched' else 1}),flush=True)
print('All archive checks passed.',flush=True)
