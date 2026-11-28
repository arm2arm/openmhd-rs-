"""Verify the complete raw benchmark packet and plot matched gravity-stage timings."""
import argparse
import csv
import io
import json
from pathlib import Path
import tarfile
from uuid import UUID

from case import matrix, placements, read_forces, timings
from fixtures import encoded, fixture, need, sha

VALUES = ("n","backend","ranks","threads","uuid","stage_ms","kernel_ms","min_stage_ms","max_stage_ms",
          "max_scaled_acceleration_error","relative_energy_error","scaled_net_force","forces_sha256","cpu")


def read_packet(path):
    with tarfile.open(path) as archive:
        bodies={}
        for entry in archive.getmembers():
            need(entry.isfile() and "/" not in entry.name and entry.name not in bodies, "packet members")
            bodies[entry.name]=archive.extractfile(entry).read()
    index=json.loads(bodies.pop("index.json"))
    used={h for files in index.values() for h in files.values()}
    need(used==set(bodies) and all(sha(b)==h for h,b in bodies.items()),"complete content-addressed packet")
    return {k:{name:bodies[h] for name,h in row.items()} for k,row in index.items()}


def workflow(files):
    terminal=json.loads(files["terminal"])
    receipt=json.loads(files["receipt"])
    inputs=json.loads(files["inputs"])
    spec=json.loads(files["spec"])
    uid=str(UUID(terminal["id"]))
    need(terminal["status"]=="finished" and receipt["uuid"]==inputs["uuid"]==uid
         and terminal["workflow"]==receipt["workflow"]==terminal["name"]+".1"
         and terminal["version"]==1,"workflow identity")
    need(sha(files["spec"])==receipt["spec"]==inputs["files"]["reana.yaml"]["sha256"]
         and sha(files["inputs"])==receipt["inputs"],"uploaded workflow specification and inputs")
    for name,body in files.items():
        if name in receipt["outputs"]:
            need(receipt["outputs"][name]==dict(bytes=len(body),sha256=sha(body)),"original download "+name)
    return uid,receipt,inputs["files"],spec


def review(packet, registration, rust_packets):
    families=matrix()
    references={n:fixture(n,rust_packets) for n in (2,256,2048)}
    plan=json.loads(registration)
    need(plan["schema"]=="openmhd.m3.openmp-rayon-gravity.v1" and families==plan["cases"]
         and plan["relative_acceleration_energy_netforce_bound"]==5e-13 and plan["samples"]==7
         and plan["complete_force_csv_must_match"] is True,"registration")
    files_by_key=read_packet(packet)
    need(set(files_by_key)==set(families)|{"build"},"complete 48-case cohort plus its build")
    b=files_by_key.pop("build")
    parent,build_receipt,build_inputs,_=workflow(b)
    build=json.loads(b["build.json"])
    executable=build["executable"]
    need(build["schema"]=="openmhd.m3.threading-benchmark-build.v1"
         and executable==build_receipt["outputs"]["gravity-kernel"]["sha256"]
         and set(build_receipt["outputs"])=={"build.json","build.log","gravity-kernel"}
         and build["log_sha256"]==sha(b["build.log"]) and "libgomp.so" in build["linked"]
         and "libmpi.so" in build["linked"] and "not found" not in build["linked"],"linked and captured executable")
    build_names=("Cargo.toml","Cargo.lock","src/lib.rs","gravity_kernel.c","build.py")
    need(all(build_inputs[k]["sha256"]==build["sources"]["files"][k]==plan["source"][k] for k in build_names)
         and all(c["returncode"]==0 for c in build["commands"])
         and any(c["argv"][0:2]==["cargo","fmt"] for c in build["commands"])
         and any(c["argv"][0:2]==["cargo","clippy"] for c in build["commands"])
         and any(c["argv"][0]=="mpicc" and "-fopenmp" in c["argv"] and "-ffp-contract=off" in c["argv"]
                 for c in build["commands"]), "compiler, source and preflight")
    science={}
    uuids={parent}
    measures=[]
    for key,params in sorted(families.items()):
        f=files_by_key[key]
        uid,receipt,inputs,spec=workflow(f)
        need(uid not in uuids,"unique independent workflow")
        uuids.add(uid)
        n=params["n"]
        catalogue,ref=references[n]
        ref_hash=sha(encoded(ref))
        need(plan["references"][str(n)]==dict(catalogue=sha(catalogue),reference=ref_hash),"reference origin")
        case=json.loads(f["case.json"])
        expected=dict(params,source=plan["revision"],parent=parent,build=sha(b["build.json"]),
                      executable=executable,reference=ref_hash,catalogue=sha(catalogue),study=sha(registration))
        need(case==expected and inputs["case.json"]["sha256"]==sha(f["case.json"])
             and inputs["catalogue.txt"]["sha256"]==sha(catalogue) and inputs["reference.json"]["sha256"]==ref_hash
             and inputs["gravity-kernel"]["sha256"]==executable and inputs["case.py"]["sha256"]==plan["source"]["case.py"]
             and inputs["fixtures.py"]["sha256"]==plan["source"]["fixtures.py"]
             and inputs["mpi_runtime.py"]["sha256"]==build_inputs["mpi_runtime.py"]["sha256"],"original job inputs "+key)
        need(set(receipt["outputs"])=={"result.json","process.log","forces.csv","timings.csv"}
             and set(receipt["outputs"]).issubset(f),"original outputs")
        step,=spec["workflow"]["specification"]["steps"]
        cpus=case["ranks"]*case["threads"]
        need(step["kubernetes_cpu_request"]==step["kubernetes_cpu_limit"]==str(cpus)
             and step["kubernetes_memory_limit"]=="2Gi" and step["commands"]==[
             f"env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 RAYON_NUM_THREADS={cpus} timeout 540 python3 -B case.py"],
             "declared resource and runner")
        measured=json.loads(f["result.json"])
        ph=read_forces(f["forces.csv"].decode(),catalogue,ref)
        ts=timings(f["timings.csv"].decode())
        cpumask=placements(f["process.log"].decode(),case)
        need(measured["case"]==case and measured["forces_sha256"]==sha(f["forces.csv"])
             and measured["timings_sha256"]==sha(f["timings.csv"]) and measured["log_sha256"]==sha(f["process.log"])
             and measured["medians"]==ts and measured["placement"]=={str(r):v for r,v in cpumask.items()}
             and measured["environment"]["OMP_NUM_THREADS"]==str(case["threads"] if case["backend"]=="openmp" else 1)
             and measured["environment"]["RAYON_NUM_THREADS"]==str(case["threads"] if case["backend"]=="rayon" else 1),
             "actual threads, timings and output checksums")
        need(ph==measured["physics"],"replayed physical gates "+key)
        if n in science:need(science[n]==f["forces.csv"],"mixed backend or layout force output "+key)
        science[n]=f["forces.csv"]
        raw=[float(x["stage_seconds"]) for x in csv.DictReader(f["timings.csv"].decode().splitlines())]
        measures.append(dict(n=n,backend=case["backend"],ranks=case["ranks"],threads=case["threads"],uuid=uid,
            kernel_ms=1000*ts["kernel_seconds"],stage_ms=1000*ts["stage_seconds"],
            min_stage_ms=1000*min(raw),max_stage_ms=1000*max(raw),forces_sha256=sha(science[n]),cpu=measured["cpu"],
            **{k:ph[k] for k in ("max_scaled_acceleration_error","relative_energy_error","scaled_net_force")}))
    # Exercise the acceleration oracle on a modified copy of the analytic output.
    lines=science[2].decode().splitlines()
    fields=lines[1].split(",")
    fields[1]=str(float(fields[1])+1.)
    lines[1]=",".join(fields)
    try:
        read_forces("\n".join(lines),*references[2])
    except ValueError as error:
        need(str(error)=="per-particle acceleration gate","expected acceleration sensitivity")
    else:
        raise ValueError("modified acceleration accepted")
    checks=dict(independent_cases=len(measures),analytic_controls=sum(r["n"]==2 for r in measures),
        measured_cases=sum(r["n"]!=2 for r in measures),samples_per_case=7,
        max_scaled_acceleration_error=max(r["max_scaled_acceleration_error"] for r in measures),
        max_relative_energy_error=max(r["relative_energy_error"] for r in measures),
        max_scaled_net_force=max(r["scaled_net_force"] for r in measures),altered_acceleration_rejected=True,
        build_uuid=parent,executable_sha256=executable,registration_sha256=sha(registration),packet_sha256=sha(packet.read_bytes()),
        force_file_sha256={str(n):sha(raw) for n,raw in science.items()})
    return measures,checks


def figure(rows, target):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,panels=plt.subplots(1,2,figsize=(9.8,4.4))
    for ax,n in zip(panels,(256,2048)):
        for backend,color,marker in (("openmp","#00695c","o"),("rayon","#a94b23","s")):
            data=sorted((r for r in rows if r["backend"]==backend and r["n"]==n and r["ranks"]==1),
                        key=lambda r:r["threads"])
            x=[r["threads"] for r in data]
            mid=[r["stage_ms"] for r in data]
            ax.fill_between(x,[r["min_stage_ms"] for r in data],[r["max_stage_ms"] for r in data],color=color,alpha=.12)
            ax.plot(x,mid,color=color,marker=marker,label=backend.capitalize() if backend=="rayon" else "OpenMP",lw=2)
        ax.set_title(f"{n:,} particles")
        ax.set_xscale("log",base=2);ax.set_xticks([1,2,4,8,16],["1","2","4","8","16"])
        ax.set_yscale("log");ax.set_xlabel("Threads on one MPI rank")
        ax.grid(axis="y",alpha=.23,which="both")
        ax.spines[["top","right"]].set_visible(False)
    panels[0].set_ylabel("Force stage, milliseconds")
    panels[1].legend(frameon=False)
    fig.suptitle("One gravity kernel, two thread runtimes",x=.09,ha="left",fontsize=16,fontweight="bold")
    fig.subplots_adjust(left=.09,right=.98,top=.77,bottom=.20,wspace=.26)
    fig.text(.09,.055,"Lines show seven-sample medians; shading spans the measured range. MPI startup and disk I/O are excluded.",fontsize=9)
    fig.savefig(target,dpi=180,facecolor="white")
    plt.close(fig)


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("records",type=Path)
    cli.add_argument("registration",type=Path)
    cli.add_argument("published_m3",type=Path)
    cli.add_argument("output",type=Path)
    args=cli.parse_args()
    rows,checks=review(args.records,args.registration.read_bytes(),args.published_m3)
    args.output.mkdir(exist_ok=True,parents=True)
    with (args.output/"gravity-timings.csv").open("w",newline="") as of:
        writer=csv.DictWriter(of,fieldnames=VALUES,lineterminator="\n")
        writer.writeheader();writer.writerows(rows)
    checks["timing_table_sha256"]=sha((args.output/"gravity-timings.csv").read_bytes())
    (args.output/"gravity-verification.json").write_bytes(encoded(checks))
    figure(rows,args.output/"gravity-threading.png")
    print(json.dumps(checks))

if __name__=="__main__":
    main()
