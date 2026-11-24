"""Finite read-only eleven-case acquisition, with actual terminal and input fences."""
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
from log_command import run
OPS=Path(__file__).resolve().parent;ROOT=OPS.parents[1]
SOURCE=ROOT/'results/offline_dependency_controls_source_20261124_attempt01'
CASES=ROOT/'results/offline_dependency_controls_cases_20261124_attempt01'
PREFLIGHT=ROOT/'results/offline_dependency_controls_preflight_observation_20261124_attempt01'
OUT=ROOT/'results/offline_dependency_controls_case_results_20261124_attempt01'
checks=0

def need(ok,label):
 global checks
 checks+=1
 if not ok:raise ValueError(label)
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_bytes())
def save(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
need(not OUT.exists(),'Fresh original output directory')
code=run('14-fresh-terminal-inventory-eleven-a03',['/usr/bin/python3','-B',str(OPS/'observe_eleven_controls_once.py'),'a03'],ROOT,600)
need(code==0,'Actual successful terminal inventory')
invpath=OPS/'inventory_a03/summary.json';inv=read(invpath);known=read(OPS/'inventory_a01/summary.json')['cases']
need(inv['counts']=={'finished':11} and len(inv['cases'])==11,'All original eleven finished')
need(all(r['uuid']==known[i]['uuid'] and r['workflow']==known[i]['workflow'] for i,r in inv['cases'].items()),'Same original UUIDs')
need(len({r['uuid'] for r in inv['cases'].values()})==11,'Distinct original identities')
release=read(OPS/'method_release_20261124.json');snapshot=read(SOURCE/'snapshot.json')
need(sha((SOURCE/'snapshot.json').read_bytes())==release['snapshot_sha256'],'Original source snapshot')
need(sha((CASES/'plan.json').read_bytes())==release['plan_sha256']==inv['plan_sha256'],'Exact original plan')
need(sha((PREFLIGHT/'certificate.json').read_bytes())==release['certificate_sha256'],'Actual reviewed parent')
submission=(CASES/'submission.json').read_bytes()
need(set(r['status'] for r in json.loads(submission).values())=={'submitted'} and len(json.loads(submission))==11,'Original eleven submitted')
need(sha(submission)==inv['submission_sha256'],'Actual original submission')
with (OPS/'submission_original_final.json').open('xb') as f:f.write(submission)
for n,h in snapshot['source_sha256'].items():need(sha((ROOT/n).read_bytes())==h,'Exact live source '+n)
for d,expected in release['files'].items():need({p.name:dict(sha256=sha(p.read_bytes()),bytes=p.stat().st_size) for p in (CASES/d).iterdir() if p.is_file()}==expected,'Original staged input '+d)
save(OPS/'terminal_acquisition_guard.json',dict(utc=datetime.now(timezone.utc).isoformat(),inventory_sha256=sha(invpath.read_bytes()),checks=checks,errors=[],component_accepted=False,workflow_mutations=False))
code=run('16-collect-eleven-controls-once',['/usr/bin/python3','-B','scripts/prepare_galaxy_python_reana.py','collect-cases','--snapshot',str(SOURCE),'--preflight',str(PREFLIGHT),'--cases',str(CASES),'--output',str(OUT),'--client','/usr/bin/python3 '+str(ROOT/'tools/galaxy_python_evidence/reana_metadata_readonly_adapter.py')],ROOT,1800)
need((OUT/'summary.json').is_file() and (OUT/'files.sha256.json').is_file(),'Closed actual packet before offline verification')
verify=run('17-offline-verify-eleven-controls',['/usr/bin/python3','-B','scripts/prepare_galaxy_python_reana.py','verify-results','--packet',str(OUT)],ROOT,600)
need((CASES/'submission.json').read_bytes()==submission,'Original submitted map unchanged')
for n,h in snapshot['source_sha256'].items():need(sha((ROOT/n).read_bytes())==h,'Final original source '+n)
for d,expected in release['files'].items():need({p.name:dict(sha256=sha(p.read_bytes()),bytes=p.stat().st_size) for p in (CASES/d).iterdir() if p.is_file()}==expected,'Final staged input '+d)
save(OPS/'acquisition_outcome.json',dict(utc=datetime.now(timezone.utc).isoformat(),collect_returncode=code,offline_returncode=verify,summary_sha256=sha((OUT/'summary.json').read_bytes()),manifest_sha256=sha((OUT/'files.sha256.json').read_bytes()),checks=checks,errors=[],component_accepted=False))
raise SystemExit(0 if code==verify==0 else 1)
