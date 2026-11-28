"""Replay the sparse-halo comparison from the original REANA receipts and scientific files."""
import argparse
import csv
import hashlib
import io
import json
import math
import re
import statistics
import tarfile
from collections import defaultdict
from pathlib import Path


def require(ok, context):
    if not ok:
        raise ValueError(context)


def sha(body):
    return hashlib.sha256(body).hexdigest()


def unpack(source):
    with tarfile.open(fileobj=io.BytesIO(source), mode="r:gz") as archive:
        result = {}
        for m in archive:
            require(m.isfile() and m.name not in result, "invalid archive member")
            result[m.name] = archive.extractfile(m).read()
        return result


def records(body):
    return list(csv.DictReader(io.StringIO(body.decode())))


def write_table(path, rows):
    with path.open("w", newline="") as f:
        out = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        out.writeheader()
        out.writerows(rows)


PATTERN = re.compile(r"openmhd-halo rank=(\d+) stage=([\w-]+) mode=(full|sparse) calls=(\d+) "
                     r"payload_bytes=(\d+) full_bytes=(\d+) payload_seconds=([\d.]+)")
FIELD = {"curl-samples", "curl-jets", "curl-faces", "ale-states", "ale-fluxes"}
SWEEP = {"sweep-old", "sweep-predicted", "sweep-faces", "sweep-output-cells", "sweep-output-faces"}


def stage_traffic(c, log):
    stages = FIELD if c["family"] == "field3" else SWEEP
    stats = defaultdict(list)
    for rank, stage, mode, calls, received, full, seconds in PATTERN.findall(log.decode()):
        require(mode == c["halo"] and stage in stages, "unexpected halo stage")
        r, count, size, dense = map(int, (rank, calls, received, full))
        require(count > 0 and 0 <= size <= dense and (mode == "sparse" or size == dense)
                and math.isfinite(float(seconds)), "halo counter")
        stats[stage, r].append((count, size, dense, float(seconds)))
    require(set(stats) == {(stage, r) for stage in stages for r in range(c["ranks"])}, "missing rank/stage")
    totals = {}
    for stage in sorted(stages):
        ranks = [stats[stage, r] for r in range(c["ranks"])]
        require(all(len(rows) == c["repeats"] and len({x[:3] for x in rows}) == 1 for rows in ranks),
                "repetition bytes or count changed")
        require(len({rows[0][0] for rows in ranks}) == 1, "collective call count")
        totals[stage] = (sum(rows[0][1] for rows in ranks), sum(rows[0][2] for rows in ranks))
    return totals


def verify_tracer(c, files):
    tracer = records(files["sweep-tracer.csv"])
    faces = records(files["sweep-faces.csv"])
    cells = records(files["sweep-cells.csv"])
    expected = defaultdict(list)
    for kind, rows in [("cell", cells), ("face", faces)]:
        for row in rows:
            expected[row["step"], row["rule"], kind].append(row)
    actual = defaultdict(list)
    for row in tracer:
        actual[row["step"], row["rule"], row["kind"]].append((int(row["ordinal"]), float(row["value"])))
    require(set(actual) == set(expected), "tracer step/rule/quantity inventory")
    sensitive = False
    for key, rows in actual.items():
        require([j for j, _ in rows] == list(range(len(expected[key]))) and all(math.isfinite(x) for _, x in rows),
                "tracer coverage")
        if key[2] == "cell":
            vals = [x for _, x in rows]
            require(abs(math.fsum(vals)) <= 2e-12 * max(1.0, math.fsum(map(abs, vals))), "closed tracer budget")
        else:
            sensitive |= any(x != float(y["exchange"]) for (_, x), y in zip(rows, expected[key]))
    if c["problem"] == "flip":
        require(sensitive, "nonuniform tracer insensitive through a flip")


def replay(folder, baseline_archive, output):
    plan_bytes = (folder / "plan.json").read_bytes()
    plan = json.loads(plan_bytes)
    builds_raw = (folder / "builds.tar.gz").read_bytes()
    builds = unpack(builds_raw)
    parent = plan["parent"] + "/"
    build = json.loads(builds[parent+"build.json"])
    build_receipt = json.loads(builds[parent+"result.json"])
    require(json.loads(builds[parent+"terminal.json"])["status"] == "finished" and
            build_receipt["uuid"] == plan["parent"] and sha(builds[parent+"build.json"]) == plan["build_sha256"]
            and build["source"] == plan["source"] and len(build["commands"]) == 5
            and sha(builds[parent+"runtime.json"]) == build["runtime"] == build_receipt["outputs"]["outputs/runtime.json"]["sha256"],
            "original build")
    for j,cmd in enumerate(build["commands"]):
        n = f"build-{j}.log"
        require(cmd["returncode"] == 0 and cmd["log_sha256"] == sha(builds[parent+n])
                == build_receipt["outputs"]["outputs/hybrid/"+n]["sha256"], n)
    for exe,h in plan["binaries"].items():
        require(build["executables"][exe]["sha256"] == h == build_receipt["outputs"]["outputs/hybrid/"+exe]["sha256"],
                "original compiled binary " + exe)
    raw = (folder / "workflows.tar.gz").read_bytes()
    blobs = unpack(raw)
    index = json.loads(blobs.pop("index.json"))
    targets = {h for mapping in index.values() for h in mapping.values()}
    require(set(blobs) == targets and all(sha(b) == h for h, b in blobs.items()), "packet byte closure")
    require(set(index) == set(plan["cases"]), "exact case inventory")
    legacy = unpack(baseline_archive.read_bytes())
    prior = {}
    for row in json.loads(legacy["index.json"]):
        if row["key"].startswith("strong-") and row["key"].endswith("-4x2"):
            h = row["outputs"]["result.json"]
            require(sha(legacy[h]) == h, "published baseline digest")
            old = json.loads(legacy[h])
            prior[old["case"]["label"]] = old
    results, uuids, measurements, details = {}, set(), [], []
    expected_outputs = {"result.json", "process.log"}
    for key, members in sorted(index.items()):
        get = lambda name: blobs[members[name]]
        c = json.loads(get("case.json"))
        receipt, term, identity = [json.loads(get(p)) for p in ("receipt", "terminal", "identity")]
        spec = json.loads(get("spec"))
        require(sha(get("spec")) == receipt["spec"] and sha(get("inputs")) == receipt["inputs"], key+" receipts")
        require(term["status"] == "finished" and term["version"] == 1
                and term["id"] == receipt["uuid"] == identity["uuid"] and term["workflow"] == receipt["workflow"]
                and term["name"] == identity["name"] and term["id"] not in uuids, key+" workflow")
        uuids.add(term["id"])
        step, = spec["workflow"]["specification"]["steps"]
        require(int(step["kubernetes_cpu_request"]) == c["threads"]*c["ranks"] == int(step["kubernetes_cpu_limit"])
                and step["kubernetes_memory_limit"] == "4Gi", key+" allocation")
        result = json.loads(get("result.json"))
        contract = c["family"] == "contract"
        exe = "halo_contract" if contract else "openmhd-mpi"
        require(c == {**plan["cases"][key], "source":plan["source"], "parent":plan["parent"],
                      "binary_sha256":plan["binaries"][exe], "plan_sha256":sha(plan_bytes)} and result["case"] == c,
                key+" source, parent, executable, release")
        pins = json.loads(get("inputs"))
        require(pins["uuid"] == term["id"], key+" input receipt UUID")
        # The launcher verified every uploaded file against these digests before starting the workflow.
        require(pins["files"]["case.json"]["sha256"] == sha(get("case.json")) and
                all(pins["files"][name]["sha256"] == h for name, h in plan["protocol_hashes"].items()
                    if name != "halo_contract.py" or contract), key+" inputs")
        additional = [exe + ".gz"]
        if c.get("tangent"):
            additional.append("jitter.bits")
        if c.get("problem") == "flip":
            additional.append("flip.txt")
        require(all(pins["files"][n]["sha256"] == plan["upload_hashes"][n] for n in additional), key+" uploaded bytes")
        wanted = expected_outputs if contract else expected_outputs | {"output.tar.gz"}
        require(set(receipt["outputs"]) == set(spec["outputs"]["files"]) == wanted, key+" outputs")
        for name in wanted:
            require(receipt["outputs"][name] == {"bytes":len(get(name)), "sha256":sha(get(name))}, key+" "+name)
        log = get("process.log")
        if contract:
            require(result["process_sha256"] == sha(log) and result["ranks"] == c["ranks"]
                    and sorted(re.findall(r"^verified ([^\n]+)$", log.decode(), re.M)) ==
                    sorted(f"{c['selector']} {c['halo']} rank={i}" for i in range(c["ranks"])), key+" verdicts")
            transfers = PATTERN.findall(log.decode())
            if c["selector"] == "routing":
                dense = (32,48,48,64)
                actual = (16,0,32,16) if c["halo"] == "sparse" else dense
                expected = {(rank,stage,1,actual[rank] if stage == "contract" else 0,
                             dense[rank] if stage == "contract" else 0) for rank in range(4) for stage in ("contract","empty")}
                require(len(transfers) == len(expected) and
                        {(int(r),stage,int(count),int(size),int(full)) for r,stage,mode,count,size,full,_ in transfers
                         if mode == c["halo"]} == expected, key+" exact directed payloads")
            else:
                require(not transfers, key+" rejected plan/error reached numerical payload")
            continue
        require(result["stdout_stderr_sha256"] == sha(log) and result["archive_sha256"] == sha(get("output.tar.gz")),
                key+" archive and log")
        files = unpack(get("output.tar.gz"))
        science = {n:sha(b) for n,b in files.items() if n != "ownership.csv"}
        require(science == result["scientific"], key+" original scientific files")
        if c.get("tracer"):
            verify_tracer(c, files)
        samples = result["samples"]
        require(len(samples) == c["repeats"] and all(sorted(r["rank"] for r in s["ranks"]) == list(range(c["ranks"]))
                for s in samples), key+" rank receipts")
        seconds = statistics.median(s["wall_seconds"] for s in samples)
        require(seconds == result["median_seconds"] and seconds > 0, key+" elapsed")
        if c["reference"]:
            totals = {}
        else:
            totals = stage_traffic(c, log)
            for stage, (size,dense) in totals.items():
                details.append(dict(case=key, stage=stage, payload_bytes=size, full_bytes=dense))
        size = sum(row[0] for row in totals.values())
        dense = sum(row[1] for row in totals.values())
        neighbour = [v for stage,v in totals.items() if not stage.startswith("sweep-output-")]
        measurements.append(dict(case=key, ranks=c["ranks"], threads=c["threads"], mode=c.get("halo","serial"),
                                 median_wall_s=seconds, payload_bytes=size, full_bytes=dense,
                                 neighbour_payload_bytes=sum(v[0] for v in neighbour),
                                 neighbour_full_bytes=sum(v[1] for v in neighbour),
                                 all_recorded_bytes=sum(r["halo"] for r in samples[0]["ranks"])))
        results[key] = (c,result,totals)
    pairs = 0
    for key,(c,result,totals) in results.items():
        serial = results[c["label"]+"-serial-1x1"][1]
        require(result["scientific"] == serial["scientific"] and result["diagnostics"] == serial["diagnostics"],
                key+" serial equivalence")
        if not c.get("reverse"):
            require(result["inputs"] == serial["inputs"], key+" input equivalence")
        old = prior[c["label"]]
        require(all(result["scientific"].get(n) == h for n,h in old["scientific"].items()), key+" published baseline")
        if c.get("halo") == "sparse":
            peer = results[key.replace("-sparse","-full")][1:]
            require(result["inputs"] == peer[0]["inputs"] and set(totals) == set(peer[1]) and
                    all(dense == peer[1][stage][0] for stage,(_,dense) in totals.items()), key+" full controls")
            if c["ranks"] >= 4 and c["label"] != "periodic-self":
                require(sum(a for a,b in totals.values()) < sum(b for a,b in totals.values()), key+" strict payload savings")
            pairs += 1
    output.mkdir(parents=True,exist_ok=True)
    write_table(output/"measurements.csv",measurements)
    write_table(output/"stage-traffic.csv",details)
    verdict = dict(workflows=len(index), contract_controls=len(index)-len(results), serial_controls=sum(c["reference"] for c,_,_ in results.values()),
                   science_workflows=len(results), science_invocations=sum(c["repeats"] for c,_,_ in results.values()),
                   full_sparse_pairs=pairs, builds_sha256=sha(builds_raw), plan_sha256=sha(plan_bytes), evidence_sha256=sha(raw),
                   legacy_archive_sha256=sha(baseline_archive.read_bytes()), measurements_sha256=sha((output/"measurements.csv").read_bytes()),
                   stages_sha256=sha((output/"stage-traffic.csv").read_bytes()), passed=True)
    (output/"verification.json").write_text(json.dumps(verdict,sort_keys=True,indent=2)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument("legacy_archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    replay(args.packet, args.legacy_archive, args.output)
