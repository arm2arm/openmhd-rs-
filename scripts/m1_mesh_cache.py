"""Exact initial mesh cache and hash-checked reuse of completed evolutions."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def prepare(binary,configs,directory,jobs):
    directory=directory.resolve();directory.mkdir(parents=True,exist_ok=True)
    keys={(c['case']=='brio',c['n'],c['jitter']) for c in configs.values()}
    def one(key):
        brio,n,j=key;path=directory/f"{'brio' if brio else 'unit'}_{n}_{j}.mesh"
        cmd=[str(binary),'--case','brio' if brio else 'uniform','--n',str(n),'--ny',str(4 if brio else n),'--jitter',str(j),'--mesh-cache',str(path),'--mesh-only']
        subprocess.run(cmd,check=True)
        return key,{'path':str(path),'sha256':sha(path),'validation_command':cmd}
    with ThreadPoolExecutor(max_workers=jobs) as pool: entries=dict(pool.map(one,sorted(keys)))
    return {name:entries[(c['case']=='brio',c['n'],c['jitter'])] for name,c in configs.items()}

def reuse_runs(source,output,configs):
    """Reuse only completed, exact-config records whose raw files match all hashes.

    The source may be an explicitly interrupted study. Snapshot its partial ledger
    and original provenance; per-run origins remain visible in the combined packet.
    """
    source=source.resolve();records=json.loads((source/'runs.json').read_text());manifest=json.loads((source/'manifest.json').read_text());provenance=json.loads((source/'provenance.json').read_text())
    origin={'directory':str(source),'revision':provenance['revision'],'binary_sha256':provenance['binary_sha256'],'provenance_sha256':sha(source/'provenance.json'),'runs_sha256':sha(source/'runs.json'),'manifest_sha256':sha(source/'manifest.json')}
    (output/'reuse_origin.json').write_text(json.dumps({'origin':origin,'provenance':provenance,'runs':records,'manifest':manifest},indent=2)+'\n')
    reused={}
    for name,c in configs.items():
        r=records.get(name)
        if r is None or r['status']!='completed':continue
        if r['config']!=c or manifest[name]!=c:raise ValueError('reuse configuration mismatch')
        for file,digest in r.get('sha256',r.get('artifacts_sha256',{})).items():
            if sha(source/name/file)!=digest:raise ValueError(f'changed reuse input {name}/{file}')
        if not r.get('sha256',r.get('artifacts_sha256',{})):raise ValueError('reuse record lacks artifact hashes')
        shutil.copytree(source/name,output/name)
        reused[name]={**r,'execution_origin':origin}
    return reused
