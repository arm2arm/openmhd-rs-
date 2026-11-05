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
        sidecar=path.with_suffix('.provenance.json'); existed=path.exists()
        if existed:
            if sidecar.exists(): creation=json.loads(sidecar.read_text())
            else:
                global_record=json.loads((directory/'generation_provenance.json').read_text())
                record=next((r for r in global_record['configs'] if r['file']==path.name and r['sha256']==sha(path)),None)
                if record is None:raise ValueError('cache creation provenance missing')
                creation={**global_record,'file':record}
            recorded=creation.get('mesh_sha256',creation.get('file',{}).get('sha256'))
            if recorded!=sha(path):raise ValueError('cache changed since creation')
        subprocess.run(cmd,check=True)
        if not existed:
            root=Path(__file__).resolve().parents[1]
            creation={'mesh_sha256':sha(path),'command':cmd,'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'dirty_status':subprocess.check_output(['git','status','--short'],cwd=root,text=True).strip(),'binary_sha256':sha(binary),'geometry_source_sha256':{str(f.relative_to(root)):sha(f) for f in (root/'crates/moving-mesh/src').glob('*.rs')}}
            sidecar.write_text(json.dumps(creation,indent=2)+'\n')
        return key,{'path':str(path),'sha256':sha(path),'validation_command':cmd,'creation':creation}
    with ThreadPoolExecutor(max_workers=jobs) as pool: entries=dict(pool.map(one,sorted(keys)))
    return {name:entries[(c['case']=='brio',c['n'],c['jitter'])] for name,c in configs.items()}

def reuse_runs(source,output,configs):
    """Reuse only completed, exact-config records whose raw files match all hashes.

    The source may be an explicitly interrupted study. Snapshot its partial ledger
    and original provenance; per-run origins remain visible in the combined packet.
    """
    source=source.resolve();captured={name:(source/name).read_bytes() for name in ('runs.json','manifest.json','provenance.json')};records=json.loads(captured['runs.json']);manifest=json.loads(captured['manifest.json']);provenance=json.loads(captured['provenance.json'])
    origin={'directory':str(source),'revision':provenance['revision'],'binary_sha256':provenance['binary_sha256'],'provenance_sha256':hashlib.sha256(captured['provenance.json']).hexdigest(),'runs_sha256':hashlib.sha256(captured['runs.json']).hexdigest(),'manifest_sha256':hashlib.sha256(captured['manifest.json']).hexdigest()}
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
        reused[name]={**r,'execution_origin':r.get('execution_origin',origin),'reused_via':origin}
    return reused
