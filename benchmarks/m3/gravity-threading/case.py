"""Run one backend/layout and check its real team, placements, force vectors and potential energy."""
import csv
import math
import os
import re
import subprocess
import time
from pathlib import Path
from statistics import median
import json

from fixtures import encoded, need, sha


def matrix():
    layouts=((1,1),(1,2),(1,4),(1,8),(1,16),(2,1),(2,2),(2,4),(4,1),(4,2),(8,1))
    return {f"n{n}-{backend}-{r}x{t}":dict(n=n,backend=backend,ranks=r,threads=t,
                batch={2:1,256:16,2048:2}[n])
            for n in (2,256,2048) for backend in ("openmp","rayon")
            for r,t in (((1,1),(2,2)) if n==2 else layouts)}


def read_forces(text, catalogue, ref):
    rows=list(csv.DictReader(text.splitlines()))
    n=ref["n"]
    need([int(r["id"]) for r in rows]==list(range(n)) and len(ref["acceleration"])==n,"force catalogue")
    masses=[float(line.split()[1]) for line in catalogue.decode().splitlines()[1:]]
    need(sha(catalogue)==ref["catalogue_sha256"] and len(masses)==n,"same input catalogue")
    a=[[float(row[k]) for k in ("ax","ay","az")] for row in rows]
    phi=[float(row["phi"]) for row in rows]
    need(all(math.isfinite(x) for vals in a for x in vals) and all(math.isfinite(x) for x in phi),"nonfinite force")
    scale=max(math.hypot(*v) for v in ref["acceleration"])
    accel_error=max(math.dist(v,expected)/max(math.hypot(*expected),1e-12*scale)
                    for v,expected in zip(a,ref["acceleration"]))
    energy=.5*math.fsum(m*p for m,p in zip(masses,phi))
    energy_error=abs((energy-ref["energy"])/ref["energy"])
    residual=math.hypot(*(math.fsum(m*v[k] for m,v in zip(masses,a)) for k in range(3)))
    net=residual/math.fsum(m*math.hypot(*v) for m,v in zip(masses,a))
    need(accel_error<=5e-13,"per-particle acceleration gate")
    need(energy_error<=5e-13,"total potential energy gate")
    need(net<=5e-13,"net force gate")
    if "phi" in ref:
        need(all(abs((x-y)/y)<=5e-13 for x,y in zip(phi,ref["phi"])),"analytic per-particle potential")
    return dict(max_scaled_acceleration_error=accel_error,relative_energy_error=energy_error,
                scaled_net_force=net,potential_energy=energy)


def timings(text):
    rows=list(csv.DictReader(text.splitlines()))
    need([int(r["sample"]) for r in rows]==list(range(7)),"seven force samples")
    for r in rows:
        need(0 < float(r["kernel_seconds"]) <= float(r["stage_seconds"]) < 600,"finite kernel/stage times")
    return {k:median(float(r[k]) for r in rows) for k in ("kernel_seconds","stage_seconds")}


def placements(log, case):
    matches=re.findall(r"^placement rank=(\d+) cpus=([0-9,]+)$",log,re.M)
    ranks,threads=case["ranks"],case["threads"]
    need(len(matches)==ranks and sorted(int(r) for r,cpus in matches)==list(range(ranks)),"rank evidence")
    cpus={int(r):list(map(int,ids.split(","))) for r,ids in matches}
    need(all(len(ids)==len(set(ids))==threads for ids in cpus.values())
         and len(set().union(*map(set,cpus.values())))==ranks*threads,"disjoint rank CPU sets")
    summary=re.findall(r"^runtime=(openmp|rayon) ranks=(\d+) threads=(\d+) openmp_macro=(\d+) particles=(\d+) batch=(\d+)$",log,re.M)
    need(len(summary)==1,"runtime witness")
    backend,r,t,macro,n,batch=summary[0]
    need(backend==case["backend"] and (int(r),int(t),int(n),int(batch))==(ranks,threads,case["n"],case["batch"])
         and int(macro)>=200805,"requested MPI and thread runtime")
    return cpus


def main():
    from mpi_runtime import environment
    c=json.loads(Path("case.json").read_bytes())
    exe=Path("gravity-kernel").resolve()
    binary_hash=sha(exe.read_bytes())
    need(binary_hash==c["executable"],"preflight binary")
    exe.chmod(0o755)
    cat=Path("catalogue.txt").read_bytes()
    ref_bytes=Path("reference.json").read_bytes()
    ref=json.loads(ref_bytes)
    need(c["reference"]==sha(ref_bytes) and c["catalogue"]==sha(cat) and c["n"]==ref["n"],"input release")
    need(int(os.environ["RAYON_NUM_THREADS"])==c["ranks"]*c["threads"],"declared CPU request")
    # Only the chosen backend creates workers; MPI calls stay on the main thread.
    env=environment("mpi",dict(os.environ,
        OMP_NUM_THREADS=str(c["threads"]) if c["backend"]=="openmp" else "1",
        RAYON_NUM_THREADS=str(c["threads"]) if c["backend"]=="rayon" else "1",
        OMP_DYNAMIC="false",OMP_PROC_BIND="false",OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1"))
    cmd=["mpiexec","-launcher","fork","-bind-to","none","-n",str(c["ranks"]),str(exe),c["backend"],
         str(c["threads"]),"catalogue.txt",str(ref["epsilon"]),str(c["batch"])]
    begin=time.monotonic()
    p=subprocess.run(cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=420)
    wall=time.monotonic()-begin
    Path("process.log").write_bytes(p.stdout)
    need(p.returncode==0,"driver exit "+str(p.returncode)+": "+p.stdout[-800:].decode(errors="replace"))
    masks=placements(p.stdout.decode(),c)
    force=Path("forces.csv").read_bytes()
    physics=read_forces(force.decode(),cat,ref)
    timing=Path("timings.csv").read_bytes()
    medians=timings(timing.decode())
    cpu_model=next((line.split(":",1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                    if line.startswith("model name")),"unknown")
    Path("result.json").write_bytes(encoded(dict(case=c,physics=physics,medians=medians,placement=masks,
        forces_sha256=sha(force),timings_sha256=sha(timing),log_sha256=sha(p.stdout),wall_seconds=wall,
        cpu=cpu_model,cpu_max=Path("/sys/fs/cgroup/cpu.max").read_text().strip(),child_argv=cmd[1:],
        environment={k:env[k] for k in ("OMP_NUM_THREADS","OMP_DYNAMIC","OMP_PROC_BIND","RAYON_NUM_THREADS")})))

if __name__=="__main__":
    main()
