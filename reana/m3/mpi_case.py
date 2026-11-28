"""Run one immutable hybrid layout on REANA and retain its original numerical outputs."""
import csv
import gzip
import hashlib
import io
import json
import math
import os
import re
import statistics
import struct
import subprocess
import tarfile
import time
from pathlib import Path

from mpi_runtime import environment


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(body):
    return hashlib.sha256(body).hexdigest()


def table(path):
    return list(csv.DictReader(io.StringIO(path.read_text())))


def make_inputs(c):
    n = c["n"]
    family = c["family"]
    if family == "gravity":
        rows = []
        for i in range(n):
            side = i % 2
            j = i // 2
            pos = ((2 * side - 1) * 0.75 + ((j % 8) - 3.5) / 32,
                   ((j // 8 % 8) - 3.5) / 32, ((j // 64) - 1.5) / 32)
            rows.append(f"{i} {side} {1/n:.17g} " + " ".join(map(str, pos))
                        + f" 0 {(1-2*side)/16} 0")
        if c.get("reverse"):
            rows.reverse()
        Path("input.txt").write_text("\n".join(rows) + "\n")
    elif family in ("field3", "mesh", "lloyd") and c["problem"] != "flip":
        points, fields = [], []
        exact = []
        if c.get("tangent"):
            exact = [[struct.unpack(">d", bytes.fromhex(word))[0] for word in line.split()]
                     for line in Path("jitter.bits").read_text().splitlines()]
            require(len(exact) == n**3, "registered smooth deformation inputs")
        dimensions = (n, n, c.get("nz", n))
        for i in range(math.prod(dimensions)):
            # Fixed, deterministic dyadic jitter in units of the local spacing.
            ijk = (i % n, (i // n) % n, i // n ** 2)
            pos = [(j + 0.5 + (0 if c["problem"] == "rigid" else
                    ((i * (19+axis*12) + axis*17) % 31 - 15) / 256)) / dimensions[axis]
                   for axis, j in enumerate(ijk)]
            velocity = [0.125, -0.0625, 0.25]
            if exact:
                pos = exact[i]
                velocity = [((7*i+3)%13-6)/128, ((5*i+1)%11-5)/128, ((3*i+2)%17-8)/128]
            name = f"{i+1:032x}"
            points.append(f"cell {name} " + " ".join(format(x, ".17g") for x in pos)
                          + " 0 0 0 " + " ".join(map(str,velocity)) + " 1")
            phase = 2 * math.pi * (pos[0] + pos[1])
            fields.append(f"{name} {1+0.05*math.cos(phase):.17g} 0.125 -0.0625 0.25 1 "
                          + f"0 {0.0125*math.sin(phase):.17g} {0.025*math.cos(phase):.17g} 0 0.001")
        if c.get("reverse"):
            points.reverse()
            fields.reverse()
        Path("input.txt").write_text("domain periodic 0 0 0 1 1 1\n" + "\n".join(points) + "\n")
        Path("fields.txt").write_text("\n".join(fields) + "\n")


def scientific_checks(c, directory):
    family, n = c["family"], c["n"]
    if family in ("mesh", "lloyd"):
        rows = table(directory / "mesh.csv")
        epochs, faces = {}, {}
        for row in rows:
            st, ix = int(row["step"]), int(row["face"])
            owner, sign = row["owner"], int(row["sign"])
            epoch = epochs.setdefault(st, {})
            v = float(row["volume"])
            require(v > 0 and math.isfinite(v), "nonpositive mesh volume")
            if owner in epoch:
                require(v == epoch[owner], "inconsistent volume among faces")
            epoch[owner] = v
            if int(row["vertex"]) == 0:
                key = st, ix
                normals = tuple(float(row[k]) for k in ("nx","ny","nz"))
                faces.setdefault(key, []).append((sign, row["neighbour"], float(row["area"]), normals))
        expected_n = 5 if c["problem"] == "flip" else n * n * c.get("nz", n)
        vol = 8 if c["problem"] == "flip" else 1
        require(len(epochs) == len(c["times"]) + 1, "missing mesh epoch")
        for cells in epochs.values():
            require(len(cells) == expected_n and abs(math.fsum(cells.values())-vol) < 2e-11 * vol,
                    "mesh owner count/volume closure")
        interior = 0
        for incidences in faces.values():
            if len(incidences) == 1 and not incidences[0][1]:
                continue
            require(len(incidences) == 2, "shared polygon has no reciprocal incidence")
            a, b = incidences
            require(a[0] == -b[0] and a[2] == b[2]
                    and all(x == -y for x,y in zip(a[3], b[3])), "face metric/orientation mismatch")
            interior += 1
        require(interior > 0, "no shared polygons")
        result = dict(epochs=len(epochs), cells=expected_n, reciprocal_faces=interior,
                      max_volume_residual=max(abs(math.fsum(x.values())-vol) for x in epochs.values()))
        if c.get("sweeps"):
            cells=table(directory/"sweep-cells.csv")
            fluxes=table(directory/"sweep-faces.csv")
            endpoints={(str(i),rule) for i in range(1,len(epochs)) for rule in ("euler","heun")}
            require({(r["step"],r["rule"]) for r in cells}==endpoints and
                    len({(r["step"],r["rule"],r["id"]) for r in cells})==len(cells)==len(endpoints)*expected_n,
                    "incomplete swept cell catalog")
            require({(r["step"],r["rule"]) for r in fluxes}==endpoints and
                    len({(r["step"],r["rule"],r["key"]) for r in fluxes})==len(fluxes),"duplicate or missing shared sweep")
            defects=[abs(float(r["uniform_increment"])-(float(r["new_volume"])-float(r["old_volume"])))
                     / max(float(r["new_volume"]),float(r["old_volume"])) for r in cells]
            require(all(math.isfinite(x) and x<=1e-12 for x in defects) and
                    all(0<=float(r["max_relative_defect"])<=1e-12 for r in cells), "uniform cell swept-volume mismatch")
            require(all(float(r["exchange"]) == -(float(r["raw"])+float(r["correction"])) for r in fluxes),
                    "signed constant-state face exchange")
            result.update(max_uniform_sweep_relative=max(defects),swept_faces=len(fluxes),rules=["euler","heun"])
        return result
    if family == "gravity":
        particles, ledger = table(directory / "particles.csv"), table(directory / "conservation.csv")
        require(len(ledger) >= 2 and len(particles) == n*len(ledger), "missing gravity samples")
        for j in range(len(ledger)):
            require([int(p["id"]) for p in particles[j*n:(j+1)*n]] == list(range(n)), "particle IDs")
        scale = max(1., abs(float(ledger[0]["energy"])))
        drift = max(abs(float(row["energy"]) - float(ledger[0]["energy"])) for row in ledger)
        momentum = max(abs(float(row[k]) - float(ledger[0][k])) for row in ledger for k in ("px","py","pz"))
        require(drift < 1e-5 * scale and momentum < 2e-12 and all(
            abs(float(row["mass"])-1.) < 1e-13 for row in ledger), "gravity conservation")
        return dict(particles=n, samples=len(ledger), energy_drift=drift, momentum_drift=momentum)
    if family == "field3":
        rows = table(directory/"rates.csv")
        require(len({row["id"] for row in rows}) == len(rows) == n*n*c.get("nz",n), "missing field cell")
        rates = {k: math.fsum(float(row[k]) for row in rows) for k in ("dm","dpx","dpy","dpz","de")}
        mean = [math.fsum(float(row["volume"])*float(row[k]) for row in rows) for k in ("bx","by","bz")]
        require(all(abs(v)<2e-12 for v in rates.values()) and
                max(abs(x-y) for x,y in zip(mean,(0.5,-0.25,0.125))) < 2e-12, "periodic flux or mean-field residual")
        operator_rows = table(directory / "field-operators.csv")
        require([r["id"] for r in operator_rows] == [r["id"] for r in rows], "operator owner identities")
        def dot_rows(left, right):
            return math.fsum(float(row[left+k])*float(row[right+k]) for row in operator_rows for k in "xyz")
        def dual_residual(direct, transposed):
            left, right = dot_rows(direct,"u"), dot_rows("a",transposed)
            error = abs(left-right) / max(1.,abs(left),abs(right))
            require(error < 2e-11, "discrete operator-adjoint pairing")
            return error
        diagnostics=dict(cells=len(rows),intensive_mean=mean,global_extensive_rates=rates,
                         adjoint_residual=dual_residual("ca","ctu"))
        require(all(float(r["g"+k]) >= 0 for r in operator_rows for k in "xyz"), "negative Gram diagonal")
        require(all(math.isfinite(float(v)) for r in operator_rows for k,v in r.items() if k!="id"),"nonfinite operator")
        if c.get("tangent"):
            diagnostics["derivative_adjoint_residual"] = dual_residual("cda","cdtu")
            diagnostics["mean_derivative"] = [math.fsum(float(r["volume"])*float(r["cda"+k])
                    +float(r["vdot"])*float(r["ca"+k]) for r in operator_rows) for k in "xyz"]
            require(max(map(abs,diagnostics["mean_derivative"])) < 2e-11, "moving volume-weighted mean")
            require(any(abs(float(r["cdax"]))>1e-10 for r in operator_rows), "unexercised derivative")
        return diagnostics
    if family == "compare2":
        rows = table(directory / "cells.csv")
        require([int(r["cell"]) for r in rows] == list(range(n*n)) and
                all(math.isfinite(float(v)) for r in rows for v in r.values()), "comparator cells")
        volume = math.fsum(float(r["volume"]) for r in rows)
        require(abs(volume-1.) < 2e-12 and min(float(r["volume"]) for r in rows)>0, "comparator volume")
        record = table(directory / "steps.csv")
        require(len(record)==1 and int(record[0]["steps"])>0 and
                float(record[0]["time"])==float(c["times"][-1]), "comparator advance")
        d = dict(volume=volume,steps=int(record[0]["steps"]),cells=len(rows))
        if "mass" in rows[0]:
            require(all(float(r["density"])>0 and float(r["pressure"])>0 for r in rows),"gas admissibility")
            d["conserved"]={k:math.fsum(float(r[k]) for r in rows) for k in ("mass","px","py","pz","energy")}
        if "div_ct" in rows[0]:
            d["max_ct_divergence"]=max(abs(float(r["div_ct"])) for r in rows)
            face=table(directory/"faces.csv")
            require(len(face)>n*n and d["max_ct_divergence"]<2e-11 and all(math.isfinite(float(f["oriented_flux"])) for f in face), "CT face closure")
        if "az" in rows[0]:
            require(max(float(r["az"]) for r in rows)>min(float(r["az"]) for r in rows), "constant potential fixture")
        return d
    require(family == "mhd2", "unknown family")
    rows = table(directory/"cells.csv")
    require([int(row["cell"]) for row in rows] == list(range(n*c["ny"])), "missing MHD cell")
    require(all(float(row["mass"])>0 and float(row["volume"])>0 and
                all(math.isfinite(float(x)) for x in row.values()) for row in rows), "invalid MHD state")
    volume = math.fsum(float(row["volume"]) for row in rows)
    require(abs(volume-(0.25 if c["problem"]=="brio" else 1.)) < 2e-12, "2D volume closure")
    return dict(cells=len(rows), volume=volume, conserved={k: math.fsum(float(row[k]) for row in rows)
                for k in ("mass","px","py","pz","energy")})


def arguments(c, out):
    mode = c["family"] + ("-tangent" if c.get("tangent") else "-deform" if c.get("deform") else "-sweeps" if c.get("sweeps") else "") + ("-reference" if c["reference"] else "")
    if c.get("restart_sha256"):
        require(sha(Path("restart.bin").read_bytes()) == c["restart_sha256"], "restart origin")
        if c["family"]=="mhd2":
            return ["mhd2-restart","restart.bin",c["times"][-1],out]
        return ["gravity-restart","restart.bin","0.125","0.0001",str(c["steps"]),str(c["stride"]),out]
    if c["family"] in ("mesh","lloyd"):
        return [mode, "flip.txt" if c["problem"]=="flip" else "input.txt", out, *c["times"]]
    if c["family"]=="compare2":
        return [mode,c["problem"],str(c["n"]),str(c["jitter"]),c["times"][-1],out]
    if c["family"]=="field3":
        return [mode,"input.txt","fields.txt","1.6666666666666667","0.5","-0.25","0.125",out]
    if c["family"]=="gravity":
        return [mode,"input.txt","0.125","0.0001",str(c["steps"]),str(c["stride"]),out]
    return [mode,c["problem"],str(c["n"]),str(c["ny"]),str(c["jitter"]),
            ",".join(c["times"]),out,*c["boost"]]


def archive(directory):
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf,mode="wb",mtime=0,filename="") as compressed:
        with tarfile.open(fileobj=compressed,mode="w") as tar:
            for path in sorted(directory.iterdir()):
                body = path.read_bytes()
                info = tarfile.TarInfo(path.name)
                info.size = len(body)
                tar.addfile(info,io.BytesIO(body))
    return buf.getvalue()


def main():
    c = json.loads(Path("case.json").read_bytes())
    exe = Path("openmhd-mpi").resolve()
    require(sha(exe.read_bytes()) == c["binary_sha256"], "executable identity")
    exe.chmod(0o755)
    require(int(os.environ["RAYON_NUM_THREADS"]) == c["ranks"]*c["threads"], "declared CPU allocation")
    env = environment("mpi", dict(os.environ, RAYON_NUM_THREADS=str(c["threads"]),
                      OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1"))
    make_inputs(c)
    inputs = {p:sha(Path(p).read_bytes()) for p in ("input.txt","fields.txt","flip.txt","jitter.bits","restart.bin") if Path(p).exists()}
    samples, repetitions = [], []
    for rep in range(c["repeats"]):
        out = "epoch-"+str(rep)
        args = ["mpiexec","-launcher","fork","-n",str(c["ranks"]),str(exe),str(c["threads"]),*arguments(c,out)]
        begin=time.monotonic()
        run=subprocess.run(args,env=env,capture_output=True,timeout=c["timeout"])
        sec=time.monotonic()-begin
        with Path("process.log").open("ab") as log:
            log.write(run.stdout+run.stderr)
        require(run.returncode==0,"driver exited "+str(run.returncode)+" "+run.stderr[-1200:].decode(errors="replace"))
        stats = []
        for match in re.finditer(r"openmhd-mpi rank=(\d+) ranks=(\d+) threads=(\d+) work_items=(\d+) halo_bytes_received=(\d+) exchange_seconds=([\d.]+) total_seconds=([\d.]+)",run.stderr.decode()):
            idx,r,t,work,halo,exchange,elapsed=match.groups()
            require((int(r),int(t))==(c["ranks"],c["threads"]),"MPI layout report")
            stats.append(dict(rank=int(idx),work=int(work),halo=int(halo),exchange=float(exchange),elapsed=float(elapsed)))
        require(sorted(row["rank"] for row in stats)==list(range(c["ranks"])),"missing actual MPI rank")
        if c["ranks"]>1:
            require(all(row["halo"]>0 for row in stats), "rank received no halo")
            if c.get("empty_owner"):
                owners = table(Path(out) / "ownership.csv")
                require(owners and len({row["owner"] for row in owners}) < c["ranks"],
                        "empty cell ownership not exercised")
            else:
                require(all(row["work"]>0 for row in stats),"rank did no owned work")
        directory=Path(out)
        diagnostics=scientific_checks(c,directory)
        hashes={p.name:sha(p.read_bytes()) for p in directory.iterdir() if p.name!="ownership.csv"}
        repetitions.append(hashes)
        if rep==0:
            Path("output.tar.gz").write_bytes(archive(directory))
        samples.append(dict(wall_seconds=sec,ranks=sorted(stats,key=lambda x:x["rank"])))
    require(all(h==repetitions[0] for h in repetitions), "nondeterministic repeated scientific output")
    result=dict(case=c,inputs=inputs,scientific=repetitions[0],diagnostics=diagnostics,samples=samples,
                median_seconds=statistics.median(s["wall_seconds"] for s in samples),
                archive_sha256=sha(Path("output.tar.gz").read_bytes()),stdout_stderr_sha256=sha(Path("process.log").read_bytes()),
                affinity=sorted(os.sched_getaffinity(0)),cpu_max=Path("/sys/fs/cgroup/cpu.max").read_text().strip())
    Path("result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")


if __name__ == "__main__":
    main()
