"""Verify a published M3 packet and replay its byte comparisons without running a solver."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(body):
    return hashlib.sha256(body).hexdigest()


def scientific_files(body):
    with tarfile.open(fileobj=io.BytesIO(body), mode="r:gz") as archive:
        output = {}
        for item in archive.getmembers():
            require(item.isfile() and "/" not in item.name and item.name not in output, "invalid scientific archive")
            output[item.name] = archive.extractfile(item).read()
        return output


def final_rows(body):
    lines = body.splitlines()
    last_step = lines[-1].split(b",", 1)[0]
    return [lines[0], *[line for line in lines[1:] if line.split(b",", 1)[0] == last_step]]


def verify(directory):
    manifest = json.loads((directory / "manifest.json").read_bytes())
    require(manifest["schema"] == "openmhd.m3-evidence.v1", "packet version")
    expected = set(manifest["files"])
    require(expected == {p.name for p in directory.iterdir()} - {"manifest.json"}, "packet members")
    for name, rec in manifest["files"].items():
        raw = (directory / name).read_bytes()
        require(len(raw) == rec["bytes"] and sha(raw) == rec["sha256"], "changed packet file " + name)
    summary = json.loads((directory / "summary.json").read_bytes())
    builds = {}
    case_records = {}
    thread_data = {}
    all_ids = {}
    outcomes = {}
    comparisons = []
    for bundle in sorted(directory.glob("*.tar.gz")):
        with tarfile.open(bundle, mode="r:gz") as archive:
            members = {}
            for item in archive.getmembers():
                require(item.isfile() and item.name not in members, "duplicate evidence member")
                members[item.name] = archive.extractfile(item).read()
        index = json.loads(members.pop("index.json"))
        require(all(sha(body) == digest for digest, body in members.items()), "content-addressed body")
        used = set()
        def get(digest):
            used.add(digest)
            return members[digest]
        require(len(index) == summary["bundles"][bundle.name[:-7]], "published workflow count")
        for w in index:
            uid = w["uuid"]
            require(uid not in all_ids, "duplicate workflow UUID")
            files = {name: get(h) for name, h in w["members"].items()}
            service = json.loads(files["receipt"])
            terminal = json.loads(files["terminal"])
            require(uid == service["uuid"] == terminal["id"] == json.loads(files["identity"])["uuid"]
                    and service["workflow"] == terminal["workflow"] and terminal["status"] == "finished",
                    "workflow identity/status")
            require(sha(files["spec"]) == service["spec"] and sha(files["inputs"]) == service["inputs"],
                    "workflow configuration")
            inputs = json.loads(files["inputs"])
            require(inputs["uuid"] == uid, "uploaded input origin")
            for name in ("case.json","comparison.json","snapshot.json"):
                if name in files:
                    require(sha(files[name]) == inputs["files"][name]["sha256"], "input bytes")
            require(set(service["outputs"]) == set(w["outputs"]) | set(w["build_binaries"]), "output inventory")
            for name, digest in w["outputs"].items():
                body = get(digest)
                require(service["outputs"][name] == {"sha256": digest, "bytes": len(body)}, "acquired output")
            for name in w["build_binaries"]:
                require(name.startswith(("outputs/hybrid/", "outputs/parallel/")) and
                        name.rsplit("/",1)[-1] in {"openmhd-mpi", "gravity-trajectory","moving-voronoi3",
                                                    "parallel_gravity","parallel_geometry3"}, "build binary list")
            for name, digest in w["outputs"].items():
                if name in ("outputs/hybrid/build.json", "outputs/parallel/build.json", "outputs/regression/catalog.json"):
                    build = json.loads(get(digest))
                    require(build["commands"] and all(row["returncode"] == 0 for row in build["commands"]), "parent build outcome")
                    builds[uid] = (build, digest, service)
            all_ids[uid] = service
            if "case.json" in files:
                c = json.loads(files["case.json"]); m = json.loads(get(w["outputs"]["result.json"]))
                require(m["case"] == c, "wrong case in output")
                case_records[uid] = (c, m)
                if "scientific" in m:
                    archive_bytes = get(w["outputs"]["output.tar.gz"])
                    science = {k:sha(v) for k,v in scientific_files(archive_bytes).items() if k != "ownership.csv"}
                    require(science == m["scientific"] and sha(archive_bytes) == m["archive_sha256"]
                            and m["stdout_stderr_sha256"] == w["outputs"]["process.log"], "hybrid result")
                    outcomes[uid] = (c, science, archive_bytes)
                elif "observations_sha256" in m:
                    require(sha(gzip.decompress(get(w["outputs"]["observations.gz"]))) == m["observations_sha256"],
                            "thread comparison")
                    if c["kind"] != "test":
                        group = (c["source"], c.get("protocol"), c["selector"])
                        thread_data.setdefault(group, []).append((c["threads"], m["observations_sha256"]))
                else:
                    require(m["passed"] is True and m["returncode"] == 0 and m["stdout_sha256"] == w["outputs"]["stdout.txt"]
                            and m["stderr_sha256"] == w["outputs"]["stderr.txt"], "libtest outcome")
            if "comparison.json" in files:
                plan = json.loads(files["comparison.json"])
                m = json.loads(get(w["outputs"]["verified.json"]))
                require(sha(files["comparison.json"]) == m["comparison_sha256"] and
                        [c["uuid"] for c in plan["cases"]] == [c["uuid"] for c in m["cases"]], "reducer identity")
                comparisons.append((plan, m))
        require(used == set(members), "unlisted evidence body")
    require(len(all_ids) == summary["workflows"] and builds and case_records, "published workflow inventory")
    for values in thread_data.values():
        require(sorted(n for n, _ in values) == [1, 2, 4, 8, 16] and len({h for _, h in values}) == 1,
                "thread layouts and byte equivalence")
    for uid, (c, row) in case_records.items():
        parent, parent_sha, service = builds[c["parent"]]
        require(parent["source"] == c["source"], "different parent source")
        if "catalog_sha256" in c:
            require(c["catalog_sha256"] == parent_sha and
                    parent["binaries"][c["binary"]]["sha256"] == row["binary_sha256"], "workspace executable")
        else:
            binary = c.get("binary", "openmhd-mpi")
            require(c["build_sha256"] == parent_sha and c["binary_sha256"] == parent["executables"][binary]["sha256"],
                    "compiled program identity")
        if "restart_parent" in c:
            prior_case, prior_hashes, _ = outcomes[c["restart_parent"]]
            require(prior_case["source"] == c["source"] and prior_hashes["checkpoint.bin"] == c["restart_sha256"]
                    and prior_case["ranks"] != c["ranks"], "original changed-layout checkpoint")
    for plan, m in comparisons:
        rank_threads = sorted((outcomes[x["uuid"]][0]["ranks"], outcomes[x["uuid"]][0]["threads"])
                              for x in plan["cases"] if not outcomes[x["uuid"]][0]["reference"])
        if plan["kind"] == "strong":
            require({(1,1),(1,4),(2,1),(2,2),(4,1)} <= set(rank_threads) and
                    outcomes[m["reference_uuid"]][0]["reference"], "strong layout inventory")
        if plan["kind"] == "weak":
            require(rank_threads == [(1,1),(2,1),(4,1)], "weak layout inventory")
            configs = [outcomes[item["uuid"]][0] for item in plan["cases"]]
            def weak_work(c):
                if c["family"] == "gravity":
                    return c["n"]*(c["n"]-1)/2/c["ranks"]
                return (c["n"]**2*c["nz"] if c["family"] == "mesh" else c["n"]*c["ny"])/c["ranks"]
            base_work = weak_work(configs[0])
            require(all(abs(weak_work(c)/base_work-1) < 0.015 for c in configs), "work per rank")

        baseline = outcomes[m["reference_uuid"]]
        for item in plan["cases"]:
            uid = item["uuid"]
            c, hashes, body = outcomes[uid]
            require(c["source"] == plan["source"] and c["parent"] == plan["parent"] and
                    c["parent"] in all_ids and c["binary_sha256"] == plan["exe"] and
                    all_ids[uid]["outputs"]["result.json"]["sha256"] == item["result_sha256"] and
                    sha(body) == item["archive_sha256"], "comparison input")
            if plan["kind"] == "strong":
                require(hashes == baseline[1], "strong-scaling output changed")
            elif plan["kind"] == "restart":
                require(hashes["checkpoint.bin"] == baseline[1]["checkpoint.bin"], "restart checkpoint")
                original = scientific_files(baseline[2])
                for name, data in scientific_files(body).items():
                    if name.endswith(".csv"):
                        require(final_rows(data) == final_rows(original[name]) if c["family"] == "gravity"
                                else data == original[name], "restart endpoint")
            else:
                require(plan["kind"] == "weak" and c.get("scaling") == "weak", "weak-scaling plan")
    return {"workflows": len(all_ids), "hybrid_cases": len(outcomes), "comparisons": len(comparisons),
            "manifest_sha256": sha((directory / "manifest.json").read_bytes())}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("directory", type=Path)
    print(json.dumps(verify(p.parse_args().directory), sort_keys=True))
