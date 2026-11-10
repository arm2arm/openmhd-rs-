"""Supplemental Python regression and mean-report audit; no MHD evolutions."""
import copy
from datetime import datetime, timezone
import hashlib
import gzip
import json
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import sys
import tarfile

ROOT=Path.cwd()
OUT=ROOT/'outputs'
OUT.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def dump(path,data):path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
metadata=json.loads((ROOT/'snapshot.json').read_text())
report=dict(status='failed',started_utc=datetime.now(timezone.utc).isoformat(),
            source_revision=metadata['source_revision'],snapshot_sha256=sha(ROOT/'snapshot.json'),
            scope='Python regressions and correction of omitted refinement observations only; no MHD evolution or full M1 acceptance',
            commands=[],python=sys.version,platform=platform.platform())
for name in ('cpu.max','memory.max'):
    path=Path('/sys/fs/cgroup')/name
    if path.exists():report.setdefault('cgroup',{})[name]=path.read_text().strip()
try:
    for name,digest in metadata['input_sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Input changed: '+name)
    source=ROOT/'source';source.mkdir()
    seen=set()
    with tarfile.open(ROOT/'source.tar.gz') as archive:
        for item in archive.getmembers():
            name=PurePosixPath(item.name)
            if not item.isfile() or name.is_absolute() or '..' in name.parts or item.name not in metadata['source_sha256']:
                raise ValueError('Unexpected source archive member')
            if item.name in seen:raise ValueError('Duplicate source member')
            data=archive.extractfile(item).read()
            if hashlib.sha256(data).hexdigest()!=metadata['source_sha256'][item.name]:raise ValueError('Source hash mismatch')
            dest=source/item.name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);seen.add(item.name)
    if seen!=set(metadata['source_sha256']):raise ValueError('Incomplete source export')
    # A private export commit supports unit-test provenance calls. The actual
    # repository revision and all source hashes are separately pinned above.
    with (OUT/'export.log').open('w') as log:
        for command in (['git','init'],['git','add','.'],
                        ['git','-c','user.name=REANA source export','-c','user.email=export@localhost','commit','-m','Verified analysis source export']):
            subprocess.run(command,cwd=source,stdout=log,stderr=subprocess.STDOUT,check=True)
    report['fixture_export_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','RAYON_NUM_THREADS'):
        os.environ[name]='1'
    command=[sys.executable,'-m','unittest','discover','-s','scripts','-p','test_*.py']
    with (OUT/'python-tests.log').open('w') as log:
        completed=subprocess.run(command,cwd=source,stdout=log,stderr=subprocess.STDOUT,timeout=600)
    report['commands'].append(dict(command=command,returncode=completed.returncode,log_sha256=sha(OUT/'python-tests.log')))
    if completed.returncode:raise ValueError('Python regressions failed')
    sys.path.insert(0,str(source/'scripts'))
    from run_m1_wave_loop import mean_refinement_series
    from run_m1_campaign import mean_checks
    provenance=json.loads((ROOT/'mean-provenance.json').read_text())
    original_bytes=gzip.decompress((ROOT/'mean-summary.json.gz').read_bytes())
    original_sha=hashlib.sha256(original_bytes).hexdigest()
    if original_sha!=provenance['result_sha256']['summary.json']:
        raise ValueError('Original mean summary differs from execution provenance')
    original=json.loads(original_bytes)
    corrected=copy.deepcopy(original)
    corrected['mean_refinement']=mean_refinement_series(original['pairs'])
    unchanged=[key for key in original if key!='mean_refinement']
    if any(corrected[key]!=original[key] for key in unchanged):raise ValueError('Non-refinement measurement changed')
    checks=mean_checks(corrected)
    if not all(checks.values()):raise ValueError('Candidate mean evidence incomplete or failed: '+str(checks))
    dump(OUT/'corrected-mean-summary.json',corrected)
    report.update(status='completed',mean_checks=checks,
                  original_summary_sha256=original_sha,
                  original_provenance_sha256=sha(ROOT/'mean-provenance.json'),
                  corrected_summary_sha256=sha(OUT/'corrected-mean-summary.json'),
                  changed_fields=['mean_refinement'],unchanged_fields=unchanged,
                  added_candidate_rows=[r for r in corrected['mean_refinement'] if r['profile']=='bulk-frame-heun-quadratic-v1'])
    if any(sha(source/name)!=digest for name,digest in metadata['source_sha256'].items()):raise ValueError('Source changed')
except Exception as error:
    report.update(status='failed',error=f'{type(error).__name__}: {error}')
finally:
    report['ended_utc']=datetime.now(timezone.utc).isoformat()
    dump(OUT/'report.json',report)
    dump(OUT/'sha256.json',{str(p.relative_to(OUT)):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file()})
raise SystemExit(0 if report['status']=='completed' else 1)
