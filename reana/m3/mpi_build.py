import json,os,shutil,subprocess
from pathlib import Path
from remote import SOURCE,OUTPUT,RUNTIME,WORK,environment,extract,sha,verify_source
from mpi_runtime import environment as mpi_environment,WHEELS
snap=json.loads((WORK/'snapshot.json').read_bytes());verify_source(snap)
dest=RUNTIME/'mpivendor';dest.mkdir();extract(WORK/'vendor.tar.gz',dest,regular_only=True)
c=RUNTIME/'cargo';c.mkdir(exist_ok=True)
(c/'config.toml').write_text('[source.crates-io]\nreplace-with="vendored"\n[source.vendored]\ndirectory='+json.dumps(str(dest))+'\n')
out=OUTPUT/'hybrid';out.mkdir()
results=dict(source=snap['source_revision'],runtime=sha(OUTPUT/'runtime.json'),wheels=WHEELS,
   lock=sha(SOURCE/'apps/openmhd-mpi/Cargo.lock'),vendor=sha(WORK/'vendor.tar.gz'),commands=[])
def write():(out/'build.json').write_text(json.dumps(results,indent=2)+'\n')
write()
env=mpi_environment(RUNTIME/'mpienv',dict(environment(),CARGO_NET_OFFLINE='true',CARGO_BUILD_JOBS='4'),build=True)
manifest='apps/openmhd-mpi/Cargo.toml'
commands=[['mpicc','-show'],['mpiexec','--version'],['cargo','fmt','--manifest-path',manifest,'--all','--','--check'],
 ['cargo','clippy','--manifest-path',manifest,'--all-targets','--locked','--offline','--','-D','warnings'],
 ['cargo','build','--release','--manifest-path',manifest,'--locked','--offline','--message-format=json']]
for i,cmd in enumerate(commands):
    log=out/f'build-{i}.log'
    with log.open('xb') as f:r=subprocess.run(cmd,env=env,cwd=SOURCE,stdout=f,stderr=subprocess.STDOUT)
    results['commands'].append(dict(argv=cmd,returncode=r.returncode,log_sha256=sha(log)));write()
    if r.returncode:raise SystemExit(r.returncode)
messages=[json.loads(x) for x in log.read_text().splitlines() if x.startswith('{')]
one,=[m for m in messages if m.get('reason')=='compiler-artifact' and m['target']['name']=='openmhd-mpi' and m.get('executable')]
exe=Path(one['executable']);p=out/'openmhd-mpi'
subprocess.run(['strip','-o',str(p),str(exe)],check=True,env=env)
results['executables']={'openmhd-mpi':dict(sha256=sha(p),unstripped=sha(exe))}
results['linked']=subprocess.check_output(['ldd',str(p)],text=True,env=env)
if 'libmpi' not in results['linked'] or 'not found' in results['linked']:raise ValueError('MPI linkage')
verify_source(snap);write()
