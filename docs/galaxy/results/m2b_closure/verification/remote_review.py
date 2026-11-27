"""Verify transported original archives and reduce all downloaded cell arrays on REANA."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile

def digest(data):
    return hashlib.sha256(data).hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def main():
    parts=json.loads(Path('parts.json').read_bytes())
    index=json.loads(Path('manifest.json').read_bytes())
    require(index['schema']=='openmhd.m2b.closure-archives.v2' and set(parts)==set(index['archives']),'archive inventory')
    root=Path('packet');root.mkdir()
    members=set()
    for archive,meta in index['archives'].items():
        require(len(PurePosixPath(archive).parts)==1 and archive.endswith('.tar.gz'),'archive filename')
        destination=Path(archive)
        with destination.open('xb') as out:
            for part in parts[archive]:
                data=Path(part['name']).read_bytes()
                require(len(data)==part['bytes'] and digest(data)==part['sha256'],'transfer part')
                out.write(data)
        require(destination.stat().st_size==meta['bytes'] and digest(destination.read_bytes())==meta['sha256'],'archive hash')
        with tarfile.open(destination,'r:gz') as tf:
            count=0
            for member in tf:
                name=PurePosixPath(member.name)
                require(member.isfile() and not name.is_absolute() and '..' not in name.parts and name.as_posix()==member.name and member.name not in members,'archive member')
                target=root/name
                target.parent.mkdir(parents=True,exist_ok=True)
                with tf.extractfile(member) as src, target.open('xb') as out:
                    data=src.read()
                    require(len(data)==member.size,'member size')
                    out.write(data)
                members.add(member.name);count+=1
            require(count==meta['members'],'archive member count')
    require(len(members)==index['files'],'full file coverage')
    require(Path('review.py').read_bytes()==(root/'prerequisites/reducer-control/review.py').read_bytes(),'identical tested reducer')
    argv=[sys.executable,'-B','review.py','verify','packet','summary.json']
    p=subprocess.run(argv,capture_output=True,check=False)
    Path('stdout').write_bytes(p.stdout);Path('stderr').write_bytes(p.stderr)
    if not Path('summary.json').is_file():
        sys.stderr.buffer.write(p.stderr)
        raise RuntimeError('no scientific summary, reducer return '+str(p.returncode))
    result=json.loads(Path('summary.json').read_bytes())
    ok=result['revised_comparisons_passed']
    require(type(ok) is bool and p.returncode==(0 if ok else 1),'measured decision and actual exit')
    record=dict(schema='openmhd.m2b.closure-verification.v2',argv=argv,returncode=p.returncode,
                full_per_cell_reduction=True,case_count=len(result['case_uuids']),extracted_members=len(members),
                archives=index['archives'],reducer_sha256=digest(Path('review.py').read_bytes()),
                stdout_sha256=digest(p.stdout),stderr_sha256=digest(p.stderr),summary_sha256=digest(Path('summary.json').read_bytes()))
    Path('review.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':
    main()
