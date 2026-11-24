"""Read actual artifacts only; no target imports, tests, reducers or builds."""
from datetime import datetime, timezone
import hashlib,json
from pathlib import Path
OPS=Path(__file__).resolve().parent;ROOT=OPS.parents[1]
PACKET=ROOT/'results/offline_dependency_controls_case_results_20261124_attempt01'
checks=0

def need(ok,label):
 global checks
 checks+=1
 if not ok:raise ValueError(label)
def sha(b):return hashlib.sha256(b).hexdigest()
def raw(p):
 need(p.is_file() and not p.is_symlink(),'Ordinary body')
 return p.read_bytes()
def read(p):return json.loads(raw(p))
def pin(b):return dict(sha256=sha(b),bytes=len(b))
outcome=read(OPS/'acquisition_outcome.json')
need(outcome['collect_returncode']==outcome['offline_returncode']==0 and outcome['errors']==[],'Actual collection/offline success')
for label in ['16-collect-eleven-controls-once','17-offline-verify-eleven-controls']:
 c=read(OPS/'commands'/label/'command.json');need(c['outcome']=='success' and c['returncode']==0 and c['finished_utc'],'Settled host result')
 for n in ['stdout','stderr']:need(pin(raw(OPS/'commands'/label/(n+'.txt')))=={k:c[n][k] for k in ['sha256','bytes']},'Host log identity')
summary=read(PACKET/'summary.json');manifest=read(PACKET/'files.sha256.json')
need(summary['whole_suite_passed'] is True and summary['counts']=={'passed':11,'failed':0,'pending':0,'incomplete':0},'Actual strict whole-eleven verdict')
need(outcome['manifest_sha256']==sha(raw(PACKET/'files.sha256.json')) and outcome['summary_sha256']==sha(raw(PACKET/'summary.json')),'Original offline/packet identity')
actual={p.relative_to(PACKET).as_posix() for p in PACKET.rglob('*') if p.is_file()}
need(not any(p.is_symlink() for p in PACKET.rglob('*')) and actual==set(manifest['files'])|{'files.sha256.json'},'Closed regular body inventory')
for n,r in manifest['files'].items():need(pin(raw(PACKET/n))==r,'Manifest body '+n)
snapshot=read(PACKET/'shared/snapshot.json');plan=read(PACKET/'inputs/cases/plan.json')
need(len(plan['cases'])==len(snapshot['tests'])==11 and snapshot['test_files']==['scripts/test_locked_dependencies.py'],'Full registered cohort')
original=read(OPS/'inventory_a03/summary.json')['cases'];uuids=[];transports=0;leaves=[]
names={'result.json','runtime.json','command.json','stdout.txt','stderr.txt','child_result.json','child_raw.bin','artifacts.sha256.json'}
for e in plan['cases']:
 d=e['directory'];folder=PACKET/'cases'/d;workflow=e['workflow'];uuid=original[d]['uuid'];uuids.append(uuid)
 for n in ['server-before.json','server-after.json']:
  value=read(folder/n);need(value['origin']=='server' and len(value['matches'])==1 and value['matches'][0]['workflow']==workflow and value['matches'][0]['version']==1 and value['matches'][0]['status']=='finished','Actual original finished workflow')
 transport=read(folder/'transport.json');need(transport['origin']=='server' and transport['workflow']==workflow and len(transport['attempts'])==10,'Ten actual original transports')
 for i,r in enumerate(transport['attempts']):
  need(r['index']==i and r['outcome']=='success' and r['returncode']==0 and r['workflow']==workflow,'Successful indexed transport')
  diag=read(folder/r['stdout']['path']);need(diag['workflow_ids']==[uuid] and diag['outcome']=='success' and diag['workflow']==workflow,'Original UUID diagnostic')
  need(sha(raw(folder/r['output']))==r['download_sha256'],'Actual transport bytes')
  for stream in ['stdout','stderr']:need(pin(raw(folder/r[stream]['path']))=={k:r[stream][k] for k in ['sha256','bytes']},'Actual transport log')
  transports+=1
 art={p.name:raw(p) for p in (folder/'artifacts').iterdir()};need(set(art)==names,'Exactly eight actual outputs')
 need(json.loads(art['artifacts.sha256.json'])=={'outputs/'+n:sha(b) for n,b in art.items() if n!='artifacts.sha256.json'},'Seven actual artifact body hashes')
 result=json.loads(art['result.json']);child=json.loads(art['child_raw.bin']);envelope=json.loads(art['child_result.json']);command=json.loads(art['command.json']);runtime=json.loads(art['runtime.json'])
 need(result['status']=='completed' and result['passed'] is True and result['outcome']=='success' and result['returncode']==0 and result['case']==e['specification'],'Actual successful original case')
 need(result['snapshot_sha256']==plan['snapshot_sha256'] and result['payload_sha256']==e['payload_sha256'] and result['source_revision']==snapshot['source_revision'],'Source/payload pin')
 need(envelope['state']=='valid' and envelope['problem'] is None and envelope['value']==child==result['child_result'] and envelope['raw_sha256']==sha(art['child_raw.bin']) and envelope['raw_bytes']==len(art['child_raw.bin']),'Actual raw child joins')
 need(child['kind']=='unittest' and child['selector']==e['specification']['selector'] and child['status']=='completed' and child['passed'] is True and child['tests_run']==1,'One exact actual leaf')
 need(all(child[n]==0 for n in ['failures','errors','skipped','expected_failures','unexpected_successes']),'No masked nonpassing/skip outcome')
 need(child['executed_identity']==snapshot['test_identities'][child['selector']],'Exact resolved leaf identity')
 need(command['outcome']=='success' and command['returncode']==0 and command['command']==result['command'],'Actual child launch success')
 cleanup=command['cleanup'];need(cleanup['direct_child_reaped'] is True and cleanup['writers_settled'] is True and cleanup['remaining_live_pids']==[] and cleanup['leader_held_until_group_close'] is True and cleanup['group_authority_lost'] is False,'Held-leader/writer closure')
 for v in [result,child,runtime]:need(v['component_accepted'] is False and v['physical_evolutions_run'] is False,'No component/evolution acceptance')
 leaves.append(dict(directory=d,workflow=workflow,uuid=uuid,selector=child['selector'],raw_child_sha256=sha(art['child_raw.bin'])))
need(len(set(uuids))==11 and transports==110,'Unique original whole-eleven coverage')
report=dict(schema='openmhd.offline11-actual-output-root-review.v1',utc=datetime.now(timezone.utc).isoformat(),snapshot_sha256=plan['snapshot_sha256'],source_revision=snapshot['source_revision'],manifest_sha256=sha(raw(PACKET/'files.sha256.json')),summary_sha256=sha(raw(PACKET/'summary.json')),strict_passed_leaves=11,successful_transports=110,artifacts=88,body_files=len(manifest['files']),leaves=leaves,checks=checks,errors=[],physical_evolutions_run=False,component_accepted=False,independent_reviewer_claimed=False,target_execution_by_inspector=False,ordinary_and_restart_canaries_still_required=True)
with (OPS/'actual_output_root_review.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in report.items() if k!='leaves'},indent=2))
