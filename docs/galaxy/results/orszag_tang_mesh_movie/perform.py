import gzip, hashlib, json, os, subprocess, sys
from pathlib import Path
m=json.loads(Path('input.json').read_bytes())
raw=b''.join(Path(p).read_bytes() for p in m['parts'])
if hashlib.sha256(raw).hexdigest()!=m['parts_sha256']:raise ValueError('input archive')
payload=gzip.decompress(raw)
if hashlib.sha256(payload).hexdigest()!=m['sha256']:raise ValueError('uncompressed input')
dest=Path(m['destination'])
dest.write_bytes(payload)
if m['mode']=='flow':
    dest.chmod(0o700)
    with Path('flow.log').open('wb') as log:
        subprocess.run(['./'+dest.name,'flow'],stdout=log,stderr=subprocess.STDOUT,check=True)
    p=Path('flow/velocity.bin')
    with Path('velocity.bin.gz').open('wb') as f:
        with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0,compresslevel=3) as z:z.write(p.read_bytes())
    Path('flow-report.json').write_text(json.dumps({'solver_sha256':m['sha256'],'flow_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'build':m['parent'],'source':m['source']},indent=2)+'\n')
else:
    subprocess.run([sys.executable,'-B','mesh.py',str(dest),m['mode'],'mesh'],check=True)
