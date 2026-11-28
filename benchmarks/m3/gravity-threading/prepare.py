"""Stage a standalone REANA build or one gravity layout from an acquired build."""
import argparse
import gzip
import io
import json
from pathlib import Path
import tarfile
import tomllib
from uuid import UUID

from case import matrix
from fixtures import encoded, fixture, need, sha

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
IMAGE = "gitlab-p4n.aip.de:5005/p4nreana/reana-env@sha256:aebd7911df9e1e97ad67d15f4c32ab23996000282183fad3bf7a480756522bd7"


def stage(path, inputs, command, outputs, cpus, memory, timeout):
    path.mkdir(parents=True, exist_ok=False)
    for name,body in inputs.items():
        target=path/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(body)
    # The shared project launcher uses this step name in the recorded REANA specifications.
    step=dict(name="m2b",environment=IMAGE,compute_backend="kubernetes",kubernetes_cpu_request=str(cpus),
              kubernetes_cpu_limit=str(cpus),kubernetes_memory_limit=memory,commands=[
              f"env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 RAYON_NUM_THREADS={cpus} timeout {timeout} {command}"])
    (path/"reana.yaml").write_bytes(encoded(dict(version="0.9.0",inputs=dict(files=sorted(inputs)),
            workflow=dict(type="serial",specification=dict(steps=[step])),outputs=dict(files=outputs))))


def vendor_archive(vendor, lock):
    result=io.BytesIO()
    pins={}
    with gzip.GzipFile(fileobj=result,mode="wb",mtime=0,filename="") as gz:
        with tarfile.open(fileobj=gz,mode="w") as archive:
            for crate in sorted((c for c in lock["package"] if "checksum" in c),key=lambda c:c["name"]):
                name=crate["name"]
                base=vendor/name
                if not base.is_dir():
                    base=vendor/(name+"-"+crate["version"])
                manifest=json.loads((base/".cargo-checksum.json").read_bytes())
                need(manifest["package"]==crate["checksum"],"vendored package "+name)
                pins[name]=crate["checksum"]
                for f in sorted([*manifest["files"],".cargo-checksum.json"]):
                    member=base/f
                    need(member.resolve().is_relative_to(base.resolve()),"vendored member path")
                    raw=member.read_bytes()
                    if f in manifest["files"]:
                        need(sha(raw)==manifest["files"][f],"vendored file "+f)
                    info=tarfile.TarInfo(name+"/"+f);info.size=len(raw);archive.addfile(info,io.BytesIO(raw))
    return result.getvalue(),pins


def build(args):
    files={p:(HERE/p).read_bytes() for p in ("Cargo.toml","Cargo.lock","src/lib.rs","gravity_kernel.c","build.py")}
    files["remote.py"]=(ROOT/"reana/remote.py").read_bytes()
    files["mpi_runtime.py"]=(ROOT/"reana/m3/mpi_runtime.py").read_bytes()
    files["vendor.tar.gz"],pins=vendor_archive(args.vendor,tomllib.loads(files["Cargo.lock"].decode()))
    files["build-inputs.json"]=encoded(dict(files={k:sha(v) for k,v in files.items()},packages=pins,project="openmhd-rs-"))
    stage(args.destination,files,"python3 -B build.py",["gravity-kernel","build.json","build.log"],2,"4Gi",900)


def case(args):
    registration=args.registration.read_bytes()
    plan=json.loads(registration)
    need(plan["cases"]==matrix(),"registered case set")
    params=plan["cases"][args.key]
    build_raw=(args.acquired_build/"build.json").read_bytes()
    b=json.loads(build_raw)
    exe=(args.acquired_build/"gravity-kernel").read_bytes()
    need(sha(exe)==b["executable"] and all(r["returncode"]==0 for r in b["commands"])
         and sha((args.acquired_build/"build.log").read_bytes())==b["log_sha256"],"acquired build")
    for k in ("Cargo.toml","Cargo.lock","src/lib.rs","gravity_kernel.c","build.py"):
        need(b["sources"]["files"][k]==plan["source"][k],"registered build source "+k)
    catalog,ref=fixture(params["n"],ROOT/"tests/reference/m3_parallel")
    reference=encoded(ref)
    case_config=dict(params,source=plan["revision"],parent=str(UUID(args.build_uuid)),build=sha(build_raw),
                     executable=sha(exe),reference=sha(reference),catalogue=sha(catalog),study=sha(registration))
    files={"gravity-kernel":exe,"catalogue.txt":catalog,"reference.json":reference,"case.json":encoded(case_config),
           "mpi_runtime.py":(ROOT/"reana/m3/mpi_runtime.py").read_bytes()}
    for k in ("case.py","fixtures.py"):
        files[k]=(HERE/k).read_bytes()
        need(sha(files[k])==plan["source"][k],"registered runner "+k)
    need(plan["references"][str(params["n"])]=={"reference":sha(reference),"catalogue":sha(catalog)}
         and sha(files["mpi_runtime.py"])==b["sources"]["files"]["mpi_runtime.py"],"stage source and reference")
    stage(args.destination,files,"python3 -B case.py",["result.json","forces.csv","timings.csv","process.log"],
          params["ranks"]*params["threads"],"2Gi",540)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    subs=parser.add_subparsers(dest="mode",required=True)
    b=subs.add_parser("build");b.add_argument("vendor",type=Path);b.add_argument("destination",type=Path)
    c=subs.add_parser("case")
    c.add_argument("key",choices=sorted(matrix()));c.add_argument("registration",type=Path)
    c.add_argument("acquired_build",type=Path);c.add_argument("build_uuid");c.add_argument("destination",type=Path)
    opts=parser.parse_args()
    (build if opts.mode=="build" else case)(opts)
