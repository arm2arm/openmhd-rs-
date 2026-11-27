"""Run one exact, discovered O03 Rust test and retain its reported metric."""
from pathlib import Path
import hashlib
import json
import math
import re
import subprocess


def main():
    cfg=json.loads(Path('selection.json').read_bytes())
    native=Path('operator')
    if hashlib.sha256(native.read_bytes()).hexdigest()!=cfg['binary_sha256']:
        raise ValueError('O03 binary identity')
    name=cfg['selector']
    if not re.fullmatch(r'[a-z][a-z_0-9]+',name):raise ValueError('O03 selector')
    native.chmod(0o700)
    cmd=[str(native.resolve()),'--exact',name,'--nocapture','--test-threads=1']
    result=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=270)
    Path('native.stdout').write_bytes(result.stdout)
    Path('native.stderr').write_bytes(result.stderr)
    out=result.stdout.decode()
    rows=re.findall(r'metric ([a-z_]+) ([^\s]+)',out)
    one=re.search(r'test result: ok\. 1 passed; 0 failed; 0 ignored; 0 measured; (\d+) filtered out',out)
    passed=(result.returncode==0 and len(rows)==1 and math.isfinite(float(rows[0][1]))
            and one is not None and int(one.group(1))==cfg['catalog_size']-1
            and ('test '+name+' ... ') in out)
    record=dict(selection=cfg,returncode=result.returncode,passed=passed,
                stdout_sha256=hashlib.sha256(result.stdout).hexdigest(),
                stderr_sha256=hashlib.sha256(result.stderr).hexdigest(),metrics=dict((k,float(v)) for k,v in rows))
    Path('comparison.json').write_text(json.dumps(record,indent=2,allow_nan=False)+'\n')
    if not passed:raise SystemExit(1)

if __name__=='__main__':main()
