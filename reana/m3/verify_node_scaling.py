"""Replay the eight-core study from the downloaded REANA records and original M3 baselines."""
import argparse
import csv
import json
import math
import re
from pathlib import Path
from statistics import median
from uuid import UUID

from mpi_matrix import FAMILIES, fixed
from verify_evidence import require, scientific_files, sha

LAYOUTS = ((1, 2), (1, 8), (2, 4), (4, 2), (8, 1), (1, 16))
PARENT = "5b1b3206-86e3-4149-a0fe-2d897276f8d4"
RANK = re.compile(rb"openmhd-mpi rank=(\d+) ranks=(\d+) threads=(\d+) work_items=(\d+) halo_bytes_received=(\d+) exchange_seconds=([\d.]+) total_seconds=([\d.]+)")
MEASURE = ("scope", "family", "ranks", "threads", "reference", "uuid", "comparison_uuid",
           "seconds", "min_seconds", "max_seconds", "halo_bytes", "work_items", "affinity_cpus", "cpu_max")


def bundle(path):
    files = scientific_files(path.read_bytes())
    index = json.loads(files.pop("index.json"))
    hashes = {h for row in index for h in [*row["members"].values(), *row["outputs"].values()]}
    require(set(files) == hashes and all(sha(body) == h for h, body in files.items()), "bundle digest or inventory")
    require(len({str(UUID(row["uuid"])) for row in index}) == len(index), "duplicate workflow")
    return {row["uuid"]: row for row in index}, files


def load_case(index, files, uid):
    row = index[uid]
    member = {k: files[h] for k, h in row["members"].items()}
    receipt = json.loads(member["receipt"])
    terminal = json.loads(member["terminal"])
    require(terminal["status"] == "finished" and terminal["version"] == 1
            and terminal["workflow"] == receipt["workflow"] == terminal["name"] + ".1"
            and uid == receipt["uuid"] == terminal["id"] == json.loads(member["identity"])["uuid"],
            "terminal workflow " + uid)
    inputs = json.loads(member["inputs"])
    require(receipt["inputs"] == sha(member["inputs"]) and receipt["spec"] == sha(member["spec"])
            and inputs["uuid"] == uid and inputs["files"]["reana.yaml"]["sha256"] == receipt["spec"]
            and inputs["files"]["case.json"]["sha256"] == sha(member["case.json"]), "uploaded inputs " + uid)
    require(set(row["outputs"]) == set(receipt["outputs"]) == {"process.log", "result.json", "output.tar.gz"},
            "missing output " + uid)
    for k, h in row["outputs"].items():
        require(receipt["outputs"][k] == {"bytes": len(files[h]), "sha256": h}, "download " + uid)
    result = json.loads(files[row["outputs"]["result.json"]])
    require(result["case"] == json.loads(member["case.json"])
            and result["archive_sha256"] == row["outputs"]["output.tar.gz"]
            and result["stdout_stderr_sha256"] == row["outputs"]["process.log"], "case/output links " + uid)
    numerical = scientific_files(files[result["archive_sha256"]])
    numerical.pop("ownership.csv", None)
    require({k: sha(v) for k, v in numerical.items()} == result["scientific"], "scientific file hash " + uid)
    return result, numerical, inputs["files"], json.loads(member["spec"]), files[result["stdout_stderr_sha256"]]


def registered():
    cases = {}
    for family in FAMILIES:
        for ranks, threads in LAYOUTS:
            c = fixed(family, ranks, threads, repeats=3)
            if ranks == 8 and family in ("flip-mesh", "swept-flip"):
                c["empty_owner"] = True
            cases[f"strong-{family}-{ranks}x{threads}"] = c
    for label, sizes in (("alfven", {"ny": 64}), ("rigid-mesh", {"n": 3, "nz": 24}),
                         ("kdk", {"n": 361, "steps": 4, "stride": 4})):
        for ranks, serial in ((1, True), (8, False)):
            cases[f"weak-{label}-{'serial' if serial else '8x1'}"] = fixed(
                label, ranks, 1, serial, repeats=3, scaling="weak", **sizes)
    return cases


def rank_metrics(m, log):
    c = m["case"]
    ranks, threads = c["ranks"], c["threads"]
    records = RANK.findall(log)
    require(len(m["samples"]) == c["repeats"] == 3 and len(records) == 3 * ranks, "recorded repetitions")
    times = [sample["wall_seconds"] for sample in m["samples"]]
    for i, sample in enumerate(m["samples"]):
        reports = []
        for rank, n, t, work, halo, exchange, elapsed in records[i*ranks:(i+1)*ranks]:
            require((int(n), int(t)) == (ranks, threads), "launched rank/thread layout")
            reports.append(dict(rank=int(rank), work=int(work), halo=int(halo),
                                exchange=float(exchange), elapsed=float(elapsed)))
        reports.sort(key=lambda p: p["rank"])
        require(reports == sample["ranks"] and [p["rank"] for p in reports] == list(range(ranks)),
                "rank data disagree with child log")
    require(all(math.isfinite(t) and t > 0 for t in times) and median(times) == m["median_seconds"],
            "elapsed time")
    ranks0 = m["samples"][0]["ranks"]
    return dict(seconds=median(times), min_seconds=min(times), max_seconds=max(times),
                halo_bytes=sum(p["halo"] for p in ranks0), work_items=sum(p["work"] for p in ranks0),
                affinity_cpus=len(m["affinity"]), cpu_max=m["cpu_max"])


def verify(plan_path, evidence, original):
    plan_bytes = plan_path.read_bytes()
    plan = json.loads(plan_bytes)
    require(plan["schema"] == "openmhd.m3.single-node-layout-extension.v1" and plan["parent"] == PARENT
            and plan["cases"] == registered() and set(plan["original_benchmarks"]) == set(FAMILIES),
            "registered study scope")
    parent_fields = {k:plan[k] for k in ("source","protocol","parent","build_sha256","binary_sha256")}
    original_index, original_files = bundle(original)
    anchors = {}
    for label, anchor in plan["original_benchmarks"].items():
        uid = anchor["uuid"]
        row = original_index[uid]
        require(anchor["result_sha256"] == row["outputs"]["result.json"]
                and anchor["archive_sha256"] == row["outputs"]["output.tar.gz"], "published baseline " + label)
        m, raw, _, _, _ = load_case(original_index, original_files, uid)
        require(m["case"]["label"] == label and m["case"]["source"] == plan["source"]
                and m["case"]["parent"] == PARENT and m["case"]["binary_sha256"] == plan["binary_sha256"],
                "published binary or problem " + label)
        anchors[label] = (uid, m, raw)
    index, blobs = bundle(evidence)
    keys = {w.get("key"): u for u,w in index.items()}
    require(len(set(index) & set(original_index)) == 0 and len(keys) == len(index)
            and set(keys) == set(plan["cases"]), "all new original workflow IDs and study cases")
    measurements = []
    weak = {}
    for key in sorted(keys):
        uid = keys[key]
        m, raw, inputs, spec, log = load_case(index, blobs, uid)
        c = m["case"]
        require(c == dict(plan["cases"][key], **parent_fields, study_plan_sha256=sha(plan_bytes)), key+" inputs")
        steps = spec["workflow"]["specification"]["steps"]
        require(len(steps)==1 and set(spec["inputs"]["files"])|{"reana.yaml"}==set(inputs), "workflow input inventory")
        extra = ({"flip.txt"} if c["problem"] == "flip" else set()) | ({"jitter.bits"} if c.get("tangent") else set())
        expected = {"mpi_case.py", "mpi_runtime.py", "openmhd-mpi.gz"} | extra
        require(set(inputs)==expected | {"case.json","reana.yaml"}
                and all(inputs[p]["sha256"]==plan["shared_inputs"][p] for p in expected), "pinned executable and runner")
        cpus = c["ranks"]*c["threads"]
        step = steps[0]
        require(step["kubernetes_cpu_request"] == step["kubernetes_cpu_limit"] == str(cpus)
                and step["kubernetes_memory_limit"] == "4Gi"
                and step["commands"] == [f"env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 RAYON_NUM_THREADS={cpus} timeout {110+3*c['timeout']} sh -ec 'gzip -dc openmhd-mpi.gz > openmhd-mpi && python3 -B mpi_case.py'"], "CPU, memory and threading")
        scope = key.split("-", 1)[0]
        label = c["label"]
        if scope == "strong":
            anchor_uuid, prior, prior_raw = anchors[label]
            require(m["inputs"] == prior["inputs"] and raw == prior_raw and m["diagnostics"] == prior["diagnostics"],
                    "fixed-input science "+key)
        else:
            anchor_uuid = keys["weak-"+label+"-serial"]
            weak[key] = (m["inputs"], raw, m["diagnostics"])
        measurements.append(dict(scope=scope,family=label,ranks=c["ranks"],threads=c["threads"],
                                 reference=c["reference"],uuid=uid,comparison_uuid=anchor_uuid,**rank_metrics(m,log)))
    for family in ("rigid-mesh", "alfven", "kdk"):
        require(weak["weak-"+family+"-serial"] == weak["weak-"+family+"-8x1"], "weak same-size science "+family)
    return measurements


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plan", type=Path)
    p.add_argument("evidence", type=Path)
    p.add_argument("original", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    rows = verify(a.plan, a.evidence, a.original)
    a.output.mkdir(parents=True,exist_ok=True)
    with (a.output/"measurements.csv").open("w",newline="") as f:
        w = csv.DictWriter(f,fieldnames=MEASURE,lineterminator="\n"); w.writeheader(); w.writerows(rows)
    verdict = dict(families=len(FAMILIES),independent_workflows=len(rows),timed_executions=3*len(rows),
                   fixed_input_comparisons=sum(r["scope"]=="strong" for r in rows),
                   weak_same_size_comparisons=3,OMP_NUM_THREADS=1,
                   plan_sha256=sha(a.plan.read_bytes()),evidence_sha256=sha(a.evidence.read_bytes()),
                   original_sha256=sha(a.original.read_bytes()),
                   measurements_sha256=sha((a.output/"measurements.csv").read_bytes()))
    (a.output/"verification.json").write_text(json.dumps(verdict,sort_keys=True,indent=2)+"\n")
    print(json.dumps(verdict))

if __name__ == "__main__":
    main()
