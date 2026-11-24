"""Finite normal-TLS observations of the two first-started offline canaries."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
import sys
from log_command import run
OPS=Path(__file__).resolve().parent;ROOT=OPS.parents[1];tag=sys.argv[1]
if not tag.isalnum():raise ValueError('Fresh simple tag')
release=json.loads((OPS/'root_release.json').read_bytes());cases=ROOT/'results/offline_workspace_canary_cases_released_20261124_attempt01'
if hashlib.sha256((cases/'plan.json').read_bytes()).hexdigest()!=release['plan_sha256']:raise ValueError('Exact release')
plan=json.loads((cases/'plan.json').read_bytes());original=json.loads((OPS/'first_launch_a01/summary.json').read_bytes())['outcomes']
out=OPS/('inventory_'+tag);out.mkdir()
adapter=ROOT/'tools/galaxy_python_evidence/reana_metadata_readonly_adapter.py'
if hashlib.sha256(adapter.read_bytes()).hexdigest()!='09a7f0cbaaa657eb6d84668dced7693c57c9784e78135adc86e72737ded79c4a':raise ValueError('Original GET adapter')
def observe(e):
 index=e['directory'];workflow=e['workflow'];target=out/(index+'.json');label='canary-observe-'+tag+'-'+index
 code=run(label,['/usr/bin/python3','-B',str(adapter),'observe','--workflow',workflow,'--output',str(target)],ROOT,350)
 if code:raise ValueError('Actual GET failed; no mutation retry')
 value=json.loads(target.read_bytes());diag=json.loads((OPS/'commands'/label/'stdout.txt').read_bytes())
 if value['origin']!='server' or len(value['matches'])!=1 or value['matches'][0]['version']!=1 or value['matches'][0]['workflow']!=workflow or diag['workflow_ids']!=[original[index]['uuid']]:raise ValueError('Original unique version1 UUID')
 return index,dict(workflow=workflow,uuid=original[index]['uuid'],status=value['matches'][0]['status'],observation=str(target.relative_to(OPS)),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),command='commands/'+label+'/command.json')
with ThreadPoolExecutor(max_workers=2) as pool:rows=dict(pool.map(observe,plan['cases']))
counts={s:sum(r['status']==s for r in rows.values()) for s in {r['status'] for r in rows.values()}}
value=dict(utc=datetime.now(timezone.utc).isoformat(),counts=counts,cases=rows,component_accepted=False)
with (out/'summary.json').open('x') as f:json.dump(value,f,indent=2);f.write('\n')
print(json.dumps(counts))
