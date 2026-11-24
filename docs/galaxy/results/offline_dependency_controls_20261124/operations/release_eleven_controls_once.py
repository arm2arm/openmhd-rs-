"""Guard a single original submission; do not import or execute test modules."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from log_command import run

OPS=Path(__file__).resolve().parent
ROOT=OPS.parents[1]
SOURCE=ROOT/'results/offline_dependency_controls_source_20261124_attempt01'
CASES=ROOT/'results/offline_dependency_controls_cases_20261124_attempt01'
CAPTURE=ROOT/'results/offline_dependency_controls_preflight_observation_20261124_attempt01'
ADAPTER=ROOT/'tools/galaxy_python_evidence/reana_metadata_readonly_adapter.py'
CLIENT=Path('/Users/arm2arm/orca/workspaces/openmhd-rs-/m1-run-alfv-n-wave-and-field-loop-benchmarks/results/limiter_campaign_tools_20261113/reana-command.py')
checks=0

def need(ok,label):
 global checks
 checks+=1
 if not ok:raise ValueError(label)
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_bytes())
def save(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')

review=read(OPS/'actual_parent_review_20261124.json')
plan=read(CASES/'plan.json'); snapshot=read(SOURCE/'snapshot.json')
need(review['errors']==[] and review['methods_executed']==0 and review['resolved_methods']==11,'Actual reviewed import-only parent')
need(review['certificate_sha256']==sha((CAPTURE/'certificate.json').read_bytes())==plan['preflight_certificate_sha256'],'Exact actual certificate')
need(review['snapshot_sha256']==sha((SOURCE/'snapshot.json').read_bytes())==plan['snapshot_sha256'],'Frozen source snapshot')
need(snapshot['test_files']==['scripts/test_locked_dependencies.py'] and len(snapshot['tests'])==11,'Registered whole11 cohort')
need([e['specification']['selector'] for e in plan['cases']]==snapshot['tests'],'All eleven exact leaves once')
need(not (CASES/'submission.json').exists(),'No previous submit')
need(sha(ADAPTER.read_bytes())=='09a7f0cbaaa657eb6d84668dced7693c57c9784e78135adc86e72737ded79c4a','Approved normal-TLS GET adapter')
for name,h in snapshot['source_sha256'].items():need(sha((ROOT/name).read_bytes())==h,'Frozen source '+name)
need(sha(CLIENT.read_bytes())=='07c7ad769deb0044db72af40f751399a9950499793511d20f43df1b090e9853e','Original generic client')
need(len(plan['cases'])==len({e['workflow'] for e in plan['cases']})==11,'Exact unique plan')
files={}
for e in plan['cases']:
 folder=CASES/e['directory']; actual={p.name:dict(sha256=sha(p.read_bytes()),bytes=p.stat().st_size) for p in folder.iterdir() if p.is_file()}
 need(set(actual)=={'case.json','job.py','snapshot.json','source.tar.gz','preflight_certificate.json','payload.json','reana.yaml'},'Seven ordinary inputs')
 need(all(p.is_file() and not p.is_symlink() for p in folder.iterdir()),'Closed ordinary case')
 need(read(folder/'case.json')==e['specification'],'Case link')
 need(e['specification']['resources']=={'threads':1,'memory':'2Gi','timeout_seconds':180},'Declared independent resources')
 for n,h in read(folder/'payload.json')['input_sha256'].items():need(actual[n]['sha256']==h,'Payload '+n)
 need(actual['preflight_certificate.json']['sha256']==review['certificate_sha256'],'Actual certificate bytes')
 need(actual['snapshot.json']['sha256']==review['snapshot_sha256'],'Snapshot bytes')
 need(actual['source.tar.gz']['sha256']==snapshot['archive_sha256'],'Source bytes')
 need(actual['job.py']['sha256']==snapshot['job_sha256'],'Exact job bytes')
 need(actual['payload.json']['sha256']==e['payload_sha256'] and actual['reana.yaml']['sha256']==e['workflow_sha256'],'Plan identities')
 files[e['directory']]=actual
folder=OPS/'release_absence_observations';folder.mkdir()
def observe(e):
 out=folder/(e['directory']+'.json')
 code=run('pre-release-absence-'+e['directory'],['/usr/bin/python3','-B',str(ADAPTER),'observe','--workflow',e['workflow'],'--output',str(out)],ROOT,350)
 need(code==0,'Successful absence GET')
 value=read(out)
 need(value['origin']=='server' and value['matches']==[],'Original new name absent')
 return dict(workflow=e['workflow'],observation=str(out.relative_to(OPS)),sha256=sha(out.read_bytes()))
with ThreadPoolExecutor(max_workers=8) as pool:observations=list(pool.map(observe,plan['cases']))
for n,h in snapshot['source_sha256'].items():need(sha((ROOT/n).read_bytes())==h,'Source fence after observations')
for d,expected in files.items():need({p.name:dict(sha256=sha(p.read_bytes()),bytes=p.stat().st_size) for p in (CASES/d).iterdir() if p.is_file()}==expected,'Input fence before launch')
need(not (CASES/'submission.json').exists(),'Submission still absent')
save(OPS/'method_release_20261124.json',dict(schema='openmhd.offline11-control-release.v1',utc=datetime.now(timezone.utc).isoformat(),plan_sha256=sha((CASES/'plan.json').read_bytes()),certificate_sha256=review['certificate_sha256'],snapshot_sha256=review['snapshot_sha256'],methods=11,files=files,observations=observations,checks=checks,errors=[],method_retries_authorized=False,component_accepted=False,numerical_escalation_authorized=False))
code=run('11-submit-eleven-original-controls-once',['/usr/bin/python3','-B','scripts/reana_cases.py','submit','--directory',str(CASES),'--client','/usr/bin/python3 -B '+str(CLIENT)],ROOT,1200)
raise SystemExit(code)
