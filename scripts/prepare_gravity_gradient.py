"""Stage G-GRAD from committed source and the previously exported gravity executable."""
import argparse
import ast
import json
from pathlib import Path
import re
import subprocess
from uuid import UUID

from prepare_general_geometry_jobs import digest, stage

REPO = Path(__file__).resolve().parents[1]
HISTORICAL = "docs/galaxy/results/gravity_static9_20261123"
RUNNER = "reana/galaxy_gravity_gradient_case.py"
BUILD = "58fe532f642e17f4961ce1ce7497882a88cbf069"


def checked(condition, why):
    if not condition:
        raise ValueError(why)


def encode(data):
    return (json.dumps(data, sort_keys=True, indent=2, allow_nan=False)+"\n").encode("ascii")


def committed(revision, path):
    return subprocess.check_output(["git","show",revision+":"+path],cwd=REPO)


def stage_campaign(binary, destination, mode, parent=None, controls=None, revision="HEAD"):
    rev = subprocess.check_output(["git","rev-parse","--verify",revision+"^{commit}"],cwd=REPO,text=True).strip()
    release_raw = committed(rev,HISTORICAL+"/case_0002/root-release.json")
    prior = json.loads(release_raw)
    native = binary.read_bytes()
    checked(prior["build_source_revision"] == BUILD and prior["binary"] == dict(bytes=len(native),sha256=digest(native)),
            "Executable must match the original reviewed standalone build")
    # All scientific Rust sources, target, lock file and dependency features match the compiled release.
    subprocess.run(["git","diff","--quiet",BUILD,rev,"--","Cargo.toml","Cargo.lock","rust-toolchain.toml",
                    "crates/gravity/Cargo.toml","crates/gravity/src","crates/gravity/examples/gravity-force-case.rs",
                    "crates/galaxy-types/Cargo.toml","crates/galaxy-types/src"],cwd=REPO,check=True)
    syntax = ast.parse(committed(rev,RUNNER))
    members, = [ast.literal_eval(s.value) for s in syntax.body if isinstance(s,ast.Assign)
                 and any(isinstance(t,ast.Name) and t.id == "HELPER_FILES" for t in s.targets)]
    files = {path:committed(rev,path) for path in members}
    checked(all(raw == (REPO/p).read_bytes() for p,raw in files.items()),"Selected working files match immutable Git source")
    source = encode(dict(revision=rev, files={p:digest(b) for p,b in files.items()},
                         binary_revision=BUILD,binary_sha256=digest(native),
                         prior_root_release_sha256=digest(release_raw),
                         prior_actual_output_review_sha256=digest(committed(rev,HISTORICAL+"/actual_output_review.json"))))
    files.update({"source.json":source,"gravity.part0000":native})
    plan = dict(revision=rev, source_sha256=digest(source), mode=mode, jobs={})
    selections = ["preflight"]
    if mode != "preflight":
        raw = parent.read_bytes()
        info = json.loads(raw)
        checked(info["source_sha256"] == digest(source) and info["status"] == "passed" and
                info["mode"] == "preflight" and info["tests_run"] == 0 and str(UUID(info["uuid"])) == info["uuid"],
                "Terminal import and fixture parent for this exact revision")
        files["parent.json"] = raw
        selections = info["selectors"] if mode == "control" else list(info["fixtures"])
        checked(len(selections)==len(set(selections)) and all(re.fullmatch(r"[a-z0-9_-]+", n) for n in selections),
                "Distinct bounded case names")
        if mode == "case":
            raw = controls.read_bytes()
            passed = json.loads(raw)
            checked(passed["parent_uuid"]==info["uuid"] and passed["source_sha256"]==digest(source)
                    and set(passed["methods"])==set(info["selectors"])
                    and all(x["passed"] is True and x["tests_run"]==1 for x in passed["methods"].values()),
                    "All preflight-selected controls passed on the original source")
            files["controls.json"] = raw
    destination.mkdir(parents=True,exist_ok=False)
    for name in selections:
        inputs=dict(files)
        if mode=="case":
            inputs["input.txt"] = info["fixtures"][name].encode("ascii")
        command=RUNNER+" "+mode+(" "+name if mode != "preflight" else "")
        plan["jobs"][name]=stage(destination/name,inputs,command,["result.json","evidence.json.gz"],
                                 1,"1Gi",240,"gravity-gradient-"+mode)
    (destination/"plan.json").write_bytes(encode(plan))
    return plan


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("preflight","control","case"))
    parser.add_argument("binary",type=Path)
    parser.add_argument("destination",type=Path)
    parser.add_argument("--revision",default="HEAD")
    parser.add_argument("--parent",type=Path)
    parser.add_argument("--controls",type=Path)
    args=parser.parse_args()
    if args.mode != "preflight" and args.parent is None or args.mode == "case" and args.controls is None:
        parser.error("Dependent stages require --parent and scientific cases also require --controls")
    stage_campaign(args.binary,args.destination,args.mode,args.parent,args.controls,args.revision)
