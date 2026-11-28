import json,shutil,subprocess
from pathlib import Path
from remote import WORK,SOURCE,OUTPUT,RUNTIME,environment,extract,sha,verify_source
snap=json.loads((WORK/'snapshot.json').read_bytes());verify_source(snap)
dest=RUNTIME/'vendor';dest.mkdir();extract(WORK/'vendor.tar.gz',dest,regular_only=True)
c=RUNTIME/'cargo';c.mkdir(exist_ok=True)
(c/'config.toml').write_text('[source.crates-io]\nreplace-with="vendored"\n[source.vendored]\ndirectory='+json.dumps(str(dest))+'\n')
env=dict(environment(),CARGO_NET_OFFLINE='true',CARGO_BUILD_JOBS='4')
out=OUTPUT/'parallel';out.mkdir()
commands=[['cargo','fmt','--all','--','--check'],['cargo','clippy','--workspace','--all-targets','--all-features','--locked','--offline','--','-D','warnings'],
 ['cargo','build','--release','--locked','--offline','--all-features','-p','moving-mesh','-p','gravity','--example','moving-voronoi3','--example','gravity-trajectory','--message-format=json'],
 ['cargo','test','--no-run','--release','--locked','--offline','--all-features','-p','moving-mesh','-p','gravity','--test','parallel_geometry3','--test','parallel_gravity','--message-format=json']]
results=dict(source=snap['source_revision'],runtime=sha(OUTPUT/'runtime.json'),lock=sha(SOURCE/'Cargo.lock'),vendor=sha(WORK/'vendor.tar.gz'),commands=[],executables={},selectors={})
def write():(out/'build.json').write_text(json.dumps(results,indent=2)+'\n')
for i,cmd in enumerate(commands):
    log=out/f'build-{i}.log'
    with log.open('xb') as f:r=subprocess.run(cmd,env=env,cwd=SOURCE,stdout=f,stderr=subprocess.STDOUT)
    results['commands'].append(dict(argv=cmd,returncode=r.returncode,log_sha256=sha(log)));write()
    if r.returncode:raise SystemExit(r.returncode)
    if i<2:continue
    messages=[json.loads(x) for x in log.read_text().splitlines() if x.startswith('{')]
    for name in (['gravity-trajectory','moving-voronoi3'] if i==2 else ['parallel_geometry3','parallel_gravity']):
        one,=[m for m in messages if m.get('reason')=='compiler-artifact' and m['target']['name']==name and m.get('executable')]
        exe=Path(one['executable']);p=out/name
        subprocess.run(['strip','-o',str(p),str(exe)],check=True)
        results['executables'][name]=dict(sha256=sha(p),unstripped=sha(exe))
        if i==3:results['selectors'][name]=[v[:-6] for v in subprocess.check_output([str(p),'--list','--format','terse'],text=True).splitlines() if v.endswith(': test')]
        write()
verify_source(snap)
