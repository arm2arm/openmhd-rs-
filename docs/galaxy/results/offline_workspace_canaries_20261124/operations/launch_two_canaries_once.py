"""One guarded first launch of each released ordinary/restart offline canary."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import hashlib,json,threading
from pathlib import Path
from log_command import run
OPS=Path(__file__).resolve().parent;ROOT=OPS.parents[1]
CASES=ROOT/'results/offline_workspace_canary_cases_released_20261124_attempt01'
CLIENT=Path('/Users/arm2arm/orca/workspaces/openmhd-rs-/m1-run-alfv-n-wave-and-field-loop-benchmarks/results/limiter_campaign_tools_20261113/reana-command.py')
ADAPTER=ROOT/'tools/galaxy_python_evidence/reana_metadata_readonly_adapter.py'
LEGACY=['/usr/bin/python3','-B',str(CLIENT)]
DEST=OPS/'first_launch_a01';STOP=threading.Event()
def need(ok,label):
 if not ok:raise ValueError(label)
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_bytes())
def save(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def inventory(p):
 need(not any(q.is_symlink() for q in p.rglob('*')),'Ordinary closed input paths')
 return {q.relative_to(p).as_posix():dict(sha256=sha(q.read_bytes()),bytes=q.stat().st_size) for q in p.rglob('*') if q.is_file()}
release=read(OPS/'root_release.json');plan=read(CASES/'plan.json')
need(sha((CASES/'plan.json').read_bytes())==release['plan_sha256'],'Exact released two-case plan')
proof=plan['required_control_packet_and_root_review'];reviewpath=Path(proof['root_review'])
need(sha(reviewpath.read_bytes())==proof['root_review_sha256'],'Actual eleven-control root review')
review=read(reviewpath)
need(review['errors']==[] and review['strict_passed_leaves']==11 and review['successful_transports']==110,'All controls actually passed')
need(sha((Path(proof['packet'])/'files.sha256.json').read_bytes())==proof['manifest_sha256'],'Actual complete control packet')
need(sha(CLIENT.read_bytes())=='07c7ad769deb0044db72af40f751399a9950499793511d20f43df1b090e9853e','Exact legacy client')
DEST.mkdir()
def guard(e):
 need(not STOP.is_set(),'Fence after unresolved launch operation')
 need(sha((CASES/'plan.json').read_bytes())==release['plan_sha256'],'Released plan unchanged')
 need(inventory(CASES/e['directory'])==e['files'],'All original canary inputs unchanged')
 need(sha((ROOT/'reana/locked_dependencies.py').read_bytes())==e['derivation']['installer_sha256'],'Tested installer unchanged')
def launch(e):
 index=e['directory'];workflow=e['workflow'];case=CASES/index;dest=DEST/index;dest.mkdir();guard(e)
 def call(label,argv,cwd=ROOT):
  need(not STOP.is_set(),'No launch behind failure fence')
  name='canary-'+index+'-'+label
  code=run(name,argv,cwd,350)
  if code!=0:STOP.set();raise ValueError('Actual nonzero operation retained: '+name)
  return OPS/'commands'/name
 def scan(label):
  folder=call(label,['/usr/bin/python3','-B',str(OPS/'scan_canary_versions_once.py'),workflow])
  value=read(folder/'stdout.txt');need(value['outcome']=='success','Actual all-version scan');return value['rows']
 def created(rows,uuid=None):
  need(len(rows)==1 and rows[0]['workflow']==workflow and rows[0]['version']==1 and rows[0]['name']==workflow[:-2] and rows[0]['status']=='created','Unique original unstarted version1')
  if uuid:need(rows[0]['id']==uuid,'Same original canary UUID')
  return rows[0]['id']
 def no_jobs(uuid,label):
  folder=call(label+'-status',[*LEGACY,'status','--workflow',uuid,'--json','--verbose']);rows=read(folder/'stdout.txt')
  need(len(rows)==1 and rows[0]['id']==uuid and rows[0]['status']=='created' and str(rows[0]['run_number'])=='1' and rows[0].get('started','-')==rows[0].get('ended','-')=='-','Never-started same UUID')
  folder=call(label+'-logs',[*LEGACY,'logs','--workflow',uuid,'--json'])
  need(read(folder/'stdout.txt')==dict(workflow_logs='',job_logs={},engine_specific=None),'No previous job or workflow execution')
 need(scan('01-absence-all-versions')==[] and scan('02-second-absence-all-versions')==[],'Two fresh empty scans before one create')
 guard(e);save(dest/'before_create_guard.json',dict(workflow=workflow,root_release_sha256=sha((OPS/'root_release.json').read_bytes()),two_empty_all_version_scans=True,inputs=e['files'],errors=[]))
 call('03-create-original-base-once',[*LEGACY,'create','--workflow',workflow[:-2],'--file','reana.yaml'],case)
 uuid=created(scan('04-created-all-versions'));no_jobs(uuid,'05-before-upload')
 folder=call('06-list-created-inputs',[*LEGACY,'ls','--workflow',uuid,'--json']);listed=read(folder/'stdout.txt');present=[r['name'] for r in listed]
 need(len(present)==len(set(present)) and set(present)<=set(e['files']),'Only a released input subset')
 available=dest/'present_inputs';available.mkdir()
 if present:call('07-download-present-inputs',[*LEGACY,'download','--workflow',uuid,'--output-directory',str(available),*sorted(present)])
 need(inventory(available)=={n:e['files'][n] for n in present},'Every present input already exact')
 missing=sorted(set(e['files'])-set(present));save(dest/'present_input_check.json',dict(uuid=uuid,missing=missing,actual=inventory(available),errors=[]))
 guard(e);created(scan('08-before-missing-only-upload'),uuid)
 if missing:call('09-upload-missing-inputs-once',[*LEGACY,'upload','--workflow',uuid,*missing],case)
 all_inputs=dest/'all_inputs';all_inputs.mkdir()
 call('10-download-all-actual-inputs',[*LEGACY,'download','--workflow',uuid,'--output-directory',str(all_inputs),*sorted(e['files'])])
 need(inventory(all_inputs)==e['files'],'Every remote original source, bundle and test input matched')
 save(dest/'all_input_check.json',dict(uuid=uuid,actual=inventory(all_inputs),expected=e['files'],errors=[]))
 created(scan('11-before-first-start'),uuid);no_jobs(uuid,'12-final');guard(e)
 save(dest/'first_start_guard.json',dict(workflow=workflow,uuid=uuid,all_remote_inputs_exact=True,one_first_start_only=True,errors=[]))
 call('13-first-uuid-start-once',[*LEGACY,'start','--workflow',uuid])
 target=dest/'after_start.json';call('14-normal-TLS-after-start',['/usr/bin/python3','-B',str(ADAPTER),'observe','--workflow',workflow,'--output',str(target)])
 value=dict(workflow=workflow,uuid=uuid,status='first_start_succeeded',after=read(target),component_accepted=False,method_pass_inferred=False)
 save(dest/'first_launch_outcome.json',value);return value
outcomes={}
with ThreadPoolExecutor(max_workers=2) as pool:
 futures={pool.submit(launch,e):e['directory'] for e in plan['cases']}
 for f in as_completed(futures):
  i=futures[f]
  try:outcomes[i]=f.result()
  except BaseException as error:STOP.set();outcomes[i]=dict(status='held',error_type=type(error).__name__,reason=str(error))
  save(DEST/(i+'-outcome.json'),outcomes[i])
save(DEST/'summary.json',dict(utc=datetime.now(timezone.utc).isoformat(),outcomes=outcomes,launch_fenced=STOP.is_set(),component_accepted=False))
print(json.dumps(outcomes));raise SystemExit(1 if STOP.is_set() else 0)
