"""One approved normal-TLS, complete all-version scan for an original name."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

OPS = Path(__file__).resolve().parent
ROOT = OPS.parents[1]
workflow = sys.argv[1]
plan = json.loads((ROOT / 'results/branch_integration216_cases_20261124_attempt01/plan.json').read_bytes())
release = json.loads((OPS / 'method_release_20261124.json').read_bytes())
if (workflow not in {entry['workflow'] for entry in plan['cases']}
        or hashlib.sha256((ROOT / 'results/branch_integration216_cases_20261124_attempt01/plan.json').read_bytes()).hexdigest() != release['plan_sha256']):
    raise ValueError('Original released workflow plan')
adapter = ROOT / 'tools/galaxy_python_evidence/reana_metadata_readonly_adapter.py'
expected = '09a7f0cbaaa657eb6d84668dced7693c57c9784e78135adc86e72737ded79c4a'
if hashlib.sha256(adapter.read_bytes()).hexdigest() != expected:
    raise ValueError('Approved frozen GET source')
spec = importlib.util.spec_from_file_location('original216_get', adapter)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
try:
    client = module.Client(*module.settings_from_private())
    rows = client.scan(workflow[:-2])
    client.remaining()
    print(json.dumps(dict(workflow=workflow, rows=rows, source_sha256=expected,
        page_count=client.page_count, outcome='success', finished_utc=datetime.now(timezone.utc).isoformat())))
except module.AdapterError as error:
    print(json.dumps(dict(outcome='failure', code=error.code, http_status=error.http_status)), file=sys.stderr)
    raise SystemExit(1)

