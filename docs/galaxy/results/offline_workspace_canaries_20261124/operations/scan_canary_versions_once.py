"""Approved GET-only complete all-version lookup for one released canary."""
from datetime import datetime,timezone
import hashlib,importlib.util,json
from pathlib import Path
import sys
OPS=Path(__file__).resolve().parent;ROOT=OPS.parents[1]
planpath=ROOT/'results/offline_workspace_canary_cases_released_20261124_attempt01/plan.json'
release=json.loads((OPS/'root_release.json').read_bytes());workflow=sys.argv[1]
if hashlib.sha256(planpath.read_bytes()).hexdigest()!=release['plan_sha256'] or workflow not in release['released_workflows']:raise ValueError('Released canary only')
p=ROOT/'tools/galaxy_python_evidence/reana_metadata_readonly_adapter.py'
if hashlib.sha256(p.read_bytes()).hexdigest()!='09a7f0cbaaa657eb6d84668dced7693c57c9784e78135adc86e72737ded79c4a':raise ValueError('Approved adapter')
spec=importlib.util.spec_from_file_location('canary_read_only',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
try:
 c=m.Client(*m.settings_from_private());rows=c.scan(workflow[:-2]);c.remaining()
 print(json.dumps(dict(workflow=workflow,rows=rows,page_count=c.page_count,outcome='success',utc=datetime.now(timezone.utc).isoformat())))
except m.AdapterError as e:
 print(json.dumps(dict(outcome='failure',code=e.code,http_status=e.http_status)),file=sys.stderr);raise SystemExit(1)
