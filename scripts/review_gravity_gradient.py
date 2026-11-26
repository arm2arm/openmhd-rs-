"""Verify a published G-GRAD packet and reconstruct its force errors from recorded words."""
import argparse
import base64
from fractions import Fraction
import gzip
from hashlib import sha256
import json
from pathlib import Path
import struct
import tarfile
from uuid import UUID

# Independently bind the original registration rather than import the measured reducer.
FD_LIMIT = Fraction(1, 10**7)
ALGEBRA_LIMIT = Fraction(5, 10**13)
HALVINGS = 60
RATIOS = {"r0": "0", "r001": "0.01", "r01": "0.1", "r1": "1", "r10": "10", "r100": "100"}


def check(value, label):
    if not value:
        raise ValueError(label)


def checksum(data):
    return sha256(data).hexdigest()


def number(bits):
    return Fraction.from_float(struct.unpack(">d", bytes.fromhex(bits))[0])


def rational(entry):
    return Fraction(int(entry["numerator_hex"], 16), int(entry["denominator_hex"], 16))


def load_archive(path):
    bodies = {}
    with tarfile.open(path, "r:gz") as archive:
        for member in archive:
            check(member.isfile() and member.name not in bodies
                  and len(bodies) < 100 and member.size <= 4*1024**2, "Unique bounded packet members")
            bodies[member.name] = archive.extractfile(member).read()
    inventory = json.loads(bodies.pop("manifest.json"))
    check(inventory == {name: {"sha256": checksum(raw), "bytes": len(raw)} for name, raw in bodies.items()},
          "Every retained body matches the file manifest")
    return bodies


def read_workflow(bodies, key, mode, source):
    files = {name: bodies[key+"/"+name] for name in ("before.json","after.json","result.json","evidence.json.gz","reana.yaml")}
    before, after = [json.loads(files[n+".json"]) for n in ("before","after")]
    r = json.loads(files["result.json"])
    check(len(before)==1 and before==after and before[0]["status"]=="finished" and before[0]["version"]==1
          and before[0]["id"]==str(UUID(r["uuid"]))==r["uuid"], "Original finished version for "+key)
    check(r["mode"]==mode and r["status"]=="passed" and r["source_sha256"]==checksum(source)
          and r["revision"]==json.loads(source)["revision"] and r["full_g1_accepted"] is False,
          "Exact source and scope for "+key)
    check(r["evidence"]==dict(bytes=len(files["evidence.json.gz"]),sha256=checksum(files["evidence.json.gz"])),
          "Remote output capsule for "+key)
    steps=json.loads(files["reana.yaml"])["workflow"]["specification"]["steps"]
    check(len(steps)==1 and steps[0]["kubernetes_cpu_request"]==steps[0]["kubernetes_cpu_limit"]=="1"
          and steps[0]["kubernetes_memory_limit"]=="1Gi", "Declared per-case resources")
    return r, json.loads(gzip.decompress(files["evidence.json.gz"]))


def coordinate_review(row, certificate, force, h0):
    ref = certificate["enclosure"]
    lo, hi = rational(ref["lower"]), rational(ref["upper"])
    levels = row["levels"]
    check(row["passed"] and row["rust_force_word"]==force and len(levels)==HALVINGS+1,
          "Rust word and complete coordinate ladder")
    zero = certificate["structural_zero"]
    check(zero==row["structural_zero"], "Independent structural-zero classification")
    f = number(force)
    if zero:
        check(f==lo==hi==0 and row["coarse_energy_changes"] and row["exact_even"], "Exact zero derivative")
    else:
        check(lo*hi>0, "Independent nonzero component")
        floor, ceiling = sorted((abs(lo),abs(hi)))
        algebra = max(abs(f-lo),abs(f-hi)) / floor
        check(algebra < ALGEBRA_LIMIT, "Strict Rust–algebra derivative limit")
    errors = []
    for k, level in enumerate(levels):
        h = h0 / (1<<k)
        check(level["k"]==k and number(level["h_word"])==h, "Ordered matching spacings")
        fd = (number(level["U_minus"]) - number(level["U_plus"])) / (2*h)
        check(float(fd)==level["force_fd"], "Central difference from original rounded energies")
        if zero:
            check(level["U_plus"]==level["U_minus"] and fd==0, "Every structural-zero difference")
            continue
        lower = max(lo-fd,fd-hi,0)/ceiling
        upper = max(abs(fd-lo),abs(fd-hi))/floor
        rust = abs(fd-f)/floor
        published = level["fd_vs_algebra"]
        check(Fraction(published[0])<=lower<=upper<=Fraction(published[1]) and
              Fraction(level["fd_vs_rust_upper"])>=rust, "Published force error encloses the measured words")
        errors.append((lower,upper,rust))
    if zero:
        return dict(zero=True)
    w = row["witness"]
    trunc, plateau, fine = (w[n] for n in ("truncation_start","plateau_start","roundoff"))
    check(0<=trunc<=trunc+2<=plateau<plateau+3<=fine<=HALVINGS, "Ordered numerical witnesses")
    for i in (trunc,trunc+1):
        check(errors[i+1][0]>0 and errors[i][0]>=Fraction(5,2)*errors[i+1][1]
              and errors[i][1]<=6*errors[i+1][0], "Measured quadratic truncation range")
    ref_tail=levels[fine]["exact_secant_vs_algebra"]
    check(errors[fine][0]>FD_LIMIT and Fraction(ref_tail[1])<FD_LIMIT, "Measured roundoff with resolved unrounded secant")
    plateau_max=max(max(v[1],v[2]) for v in errors[plateau:plateau+3])
    check(plateau_max<FD_LIMIT, "Three consecutive passing differences")
    return dict(zero=False,algebra=float(algebra),plateau_max=float(plateau_max),
                plateau_start=plateau,roundoff_start=fine)


def review(path):
    bodies=load_archive(path)
    source=bodies["source.json"]
    compiled = json.loads(bodies["historical-build-release.json"])
    frozen = json.loads(source)
    check(checksum(bodies["historical-build-release.json"])==frozen["prior_root_release_sha256"]
          and compiled["binary"]["sha256"]==frozen["binary_sha256"]=="b7185b92b1c5052f5fc315e2fa8720eae54cb26742ed4b028127449d938f0196"
          and compiled["build_source_revision"]==frozen["binary_revision"]=="58fe532f642e17f4961ce1ce7497882a88cbf069",
          "Original gravity build and executable")
    parent,_=read_workflow(bodies,"preflight","preflight",source)
    check(parent["tests_run"]==0 and len(parent["selectors"])==len(set(parent["selectors"]))==6
          and set(parent["fixtures"])==set(RATIOS)|{"three-body"}, "Import, controls and physical registry")
    release=json.loads(bodies["controls.json"])
    check(release["parent_uuid"]==parent["uuid"] and release["source_sha256"]==checksum(source)
          and set(release["methods"])==set(parent["selectors"]), "Original control release")
    uuids={parent["uuid"]}
    for selector in parent["selectors"]:
        key="control/"+selector
        r, evidence=read_workflow(bodies,key,"control",source)
        check(r["uuid"] not in uuids and r["name"]==selector and r["parent_uuid"]==parent["uuid"] and r["tests_run"]==1
              and r["failures"]==r["errors"]==r["skips"]==0 and evidence["unittest"].rstrip().endswith("OK")
              and release["methods"][selector]==dict(passed=True,tests_run=1,uuid=r["uuid"],
                        result_sha256=checksum(bodies[key+"/result.json"]), evidence_sha256=r["evidence"]["sha256"]),
              "One clean control with authentic output")
        uuids.add(r["uuid"])
    cases = {}
    examples = {}
    for name, literal in parent["fixtures"].items():
        r, evidence=read_workflow(bodies,"case/"+name,"case",source)
        check(r["uuid"] not in uuids and r["name"]==name and r["parent_uuid"]==parent["uuid"]
              and r["parent_sha256"]==checksum(bodies["preflight/result.json"]) and r["links"]["controls_sha256"]==checksum(bodies["controls.json"])
              and r["links"]["input_sha256"]==checksum(literal.encode("ascii")) and evidence["input_ascii"]==literal,
              "Original frozen physics input and tested control cohort")
        uuids.add(r["uuid"])
        command=json.loads(base64.b64decode(evidence["native/command.json"],validate=True))
        stdout=base64.b64decode(evidence["native/stdout.txt"],validate=True)
        stderr=base64.b64decode(evidence["native/stderr.txt"],validate=True)
        join=evidence["projection"]
        check(command["returncode"]==0 and command["outcome"]=="success" and command["links"]==r["links"]
              and command["cleanup"]["direct_child_reaped"] and command["cleanup"]["writers_settled"]
              and not command["cleanup"]["group_authority_lost"] and command["cleanup"]["leader_held_until_group_close"]
              and join["stdout_sha256"]==checksum(stdout) and join["stderr_sha256"]==checksum(stderr)
              and r["links"]["binary_sha256"]==r["binary_sha256"]==json.loads(source)["binary_sha256"],
              "Original native binary, process and output")
        samples={}
        for line in stdout.decode("ascii").splitlines():
            fields=line.split()
            if fields and fields[0]=="sample":
                check(len(fields)==8 and fields[1] not in samples, "One force sample per original particle")
                samples[fields[1]]=fields[2:5]
        analytic=evidence["algebra"]
        check(analytic["input"]["original_sha256"]==join["raw_reference_input_sha256"] and set(analytic["samples_by_particle_id"])==set(samples),
              "Derivative certificates for the actual source words and particle IDs")
        report=evidence["gradient"]
        check(report["passed"] and report["case"]==name and report["fd_limit"]==str(FD_LIMIT)
              and report["algebra_limit"]==str(ALGEBRA_LIMIT), "Original registered decision")
        coords=report["coordinates"]
        check(len(coords)==len(samples)*3 and {(c["id"],c["axis"]) for c in coords}=={(p,a) for p in samples for a in "xyz"},
              "All particle coordinates")
        checks=[]
        for c in coords:
            i="xyz".index(c["axis"])
            cert=analytic["samples_by_particle_id"][c["id"]]["force"][i]
            checks.append(coordinate_review(c,cert,samples[c["id"]][i],max(Fraction(1),Fraction(RATIOS.get(name,"1")))))
            if c["id"]==min(samples) and c["axis"]=="x" and not c["structural_zero"]:
                examples[name]=c
        measured=[v for v in checks if not v["zero"]]
        cases[name]=dict(uuid=r["uuid"],input_sha256=r["links"]["input_sha256"],coordinates=len(checks),
                         exact_zero_axes=len(checks)-len(measured),native_stdout_sha256=checksum(stdout),
                         worst_algebra=max((v["algebra"] for v in measured),default=None),
                         worst_plateau=max((v["plateau_max"] for v in measured),default=None),
                         plateau_starts=[v["plateau_start"] for v in measured],roundoff_starts=[v["roundoff_start"] for v in measured])
    check(len(uuids)==14 and sum(r["coordinates"] for r in cases.values())==45, "Complete 14-workflow campaign")
    return dict(schema="openmhd.gravity-gradient-review.v1",revision=parent["revision"],import_uuid=parent["uuid"],
                original_binary_sha256=parent["binary_sha256"],independent_controls=len(parent["selectors"]),
                cases=cases,passed=True,full_g1_accepted=False,archive_sha256=checksum(path.read_bytes())),examples


def plot(examples, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import LogLocator
    fig, ax=plt.subplots(figsize=(9.2,5.6),layout="constrained")
    colors=("#276f83","#6654a1","#bd4c2e","#57843a","#a06f24")
    for (name,label),color in zip([(k,v) for k,v in RATIOS.items() if k!="r0"],colors):
        case=examples[name]
        x=[r["k"] for r in case["levels"]]
        y=[r["fd_vs_algebra"][1] for r in case["levels"]]
        ax.plot(x,y,lw=1.8,color=color,label=label)
        i=case["witness"]["plateau_start"]
        ax.scatter(x[i:i+3],y[i:i+3],s=19,color=color,zorder=3)
    ax.axhline(1e-7,color="#454b54",linestyle="--",linewidth=1.1)
    ax.text(0.4,1.6e-7,"Registered limit",color="#454b54",fontsize=9)
    ax.set(xlim=(0,60),ylim=(1e-16,6),yscale="log",xlabel="Successive halvings of the displacement",
           ylabel="Relative force error")
    ax.set_title("Gravity from the change in potential energy",loc="left",fontsize=16,pad=13)
    ax.yaxis.set_major_locator(LogLocator(base=10,numticks=9))
    ax.grid(axis="y",alpha=.2)
    ax.spines[["top","right"]].set_visible(False)
    ax.legend(title="Separation / softening",ncol=5,loc="lower right",fontsize=9,frameon=False)
    fig.savefig(output,dpi=165)
    plt.close(fig)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet",type=Path)
    parser.add_argument("--plot",type=Path)
    parser.add_argument("--output",type=Path,help="Write the reviewed case summary as JSON")
    args=parser.parse_args()
    summary,examples=review(args.packet)
    if args.plot:
        args.plot.parent.mkdir(parents=True,exist_ok=True)
        plot(examples,args.plot)
    raw = json.dumps(summary,allow_nan=False,sort_keys=True,indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(raw)
    else:
        print(raw,end="")
