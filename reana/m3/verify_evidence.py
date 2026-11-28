"""Verify a published M3 packet and replay its byte comparisons without running a solver."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

import checkpoint_identity


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


def exact_leaf(output, selector):
    lines = output.decode().splitlines()
    return ("running 1 test" in lines and f"test {selector} ... ok" in lines
            and any(line.startswith("test result: ok. 1 passed; 0 failed; 0 ignored;") for line in lines))


def workspace_inventory(catalog):
    ordinary = set()
    ignored = []
    for target in catalog["targets"]:
        name = (target["manifest"], target["name"], tuple(target["kind"]))
        for selector in target["selectors"]:
            if selector in target["ignored"]:
                ignored.append((name[0], name[1], selector))
            else:
                identity = (*name, selector)
                require(identity not in ordinary, "duplicate selector in parent discovery")
                ordinary.add(identity)
    return ordinary, sorted(ignored)


def verify_dispatch(files, uid, terminal, inputs):
    if "dispatch/original-create-recovery/intent.json" in files:
        intent = json.loads(files["dispatch/original-create-recovery/intent.json"])
        origin = json.loads(files["dispatch/create.json"])
        observed = json.loads(files["dispatch/original-create-recovery/observed.json"])
        require(intent["original_create"] == origin and origin["http"] not in (200, 201, 202, 204)
                and intent["source_intent_sha256"] == sha(files["dispatch/intent.json"])
                and intent["original_inputs"] == {k: v["sha256"] for k, v in inputs["files"].items()}
                and intent["family"] == {} and intent["all_versions"] == [],
                "original creation and absence observations")
        require(observed["id"] == uid and observed["name"] == intent["name"] and
                observed["workflow"] == terminal["workflow"] and observed["version"] == 1,
                "first version after transport recovery")
    if "dispatch/same-uuid-start/intent.json" in files:
        intent = json.loads(files["dispatch/same-uuid-start/intent.json"])
        require(intent["uuid"] == uid and intent["inputs"] == inputs["files"] and
                intent["original_start"] == json.loads(files["dispatch/start.json"]),
                "original start and uploaded inputs")
        for key in ("before", "after"):
            observation = intent[key]
            require(observation["workflow"]["id"] == uid and observation["workflow"]["status"] == "created"
                    and observation["progress"]["run_started_at"] is None
                    and observation["progress"]["total"] == {"job_ids": [], "total": 0},
                    "start recovery must preserve the original unstarted workflow")


def verify_rebuilt_states(pairs, outcomes, jobs, rule):
    require(rule["schema"] == "openmhd.m3-build-bound-checkpoint.v1", "cross-build comparison rule")
    require(sha(Path(checkpoint_identity.__file__).read_bytes()) == rule["validator_sha256"], "checkpoint validator source")
    changed = {}
    expected_jobs = {}
    for pair in pairs:
        old, old_hashes, old_archive = outcomes[pair["original"]]
        new, new_hashes, new_archive = outcomes[pair["current"]]
        label = pair["label"]
        require(old_hashes.keys() == new_hashes.keys(), "cross-build scientific inventory")
        differences = {name for name in old_hashes if old_hashes[name] != new_hashes[name]}
        if old["family"] != "mhd2":
            require(not differences, "different numerical output after rebuild")
            continue
        require(differences == {"checkpoint.bin"}, "unexpected MHD cross-build difference")
        original = scientific_files(old_archive)["checkpoint.bin"]
        current = scientific_files(new_archive)["checkpoint.bin"]
        changed[label] = {"original_sha256": sha(original), "current_sha256": sha(current)}
        variants = {"observed": rule["cases"][label]}
        if label == "alfven":
            variants.update(rule["controls"])
        for control, uid in variants.items():
            require(uid not in expected_jobs, "reused checkpoint workflow")
            expected_jobs[uid] = label
            request, result, inputs, module_digest = jobs[uid]
            require(request == dict(schema=rule["schema"], label=label, control=control,
                    original_case=pair["original"], current_case=pair["current"],
                    original_executable=old["binary_sha256"], current_executable=new["binary_sha256"],
                    validator_source=rule["validator_source"], **changed[label]), "checkpoint workflow origins")
            require(inputs["original.bin"] == {"bytes": len(original), "sha256": sha(original)}
                    and inputs["current.bin"] == {"bytes": len(current), "sha256": sha(current)}
                    and inputs["checkpoint_identity.py"]["sha256"] == rule["validator_sha256"] == module_digest,
                    "checkpoint workflow inputs")
            require(checkpoint_identity.run(request, original, current) == result, "checkpoint workflow replay")
    failure = rule["original_failure"]
    require(set(jobs) == set(expected_jobs) and set(changed) == set(rule["cases"])
            == {"alfven", "boosted-loop", "brio", "deforming-alfven", "vortex"}
            and set(rule["controls"]) == set(checkpoint_identity.CONTROL_ERRORS), "checkpoint proof inventory")
    require(failure["first_error"] == "ValueError: original mode changed alfven"
            and failure["identical_complete_families"] == len(pairs) - len(changed)
            and failure["original_checkpoint_hashes"] == changed, "original whole-file mismatch")
    return len(changed)


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
    build_snapshots = {}
    case_records = {}
    thread_data = {}
    all_ids = {}
    outcomes = {}
    comparisons = {}
    checkpoint_jobs = {}
    workspace_rows = {}
    release_scale_rows = {}
    workspace_uploads = {}
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
            verify_dispatch(files, uid, terminal, inputs)
            for name in ("case.json","comparison.json","snapshot.json","request.json","checkpoint_identity.py"):
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
                    log_directory = name.rsplit("/", 1)[0]
                    for i, command in enumerate(build["commands"]):
                        log = service["outputs"][f"{log_directory}/build-{i}.log"]
                        require(command.get("log_sha256", command.get("sha256")) == log["sha256"], "build log")
                    require(build["runtime"] == service["outputs"]["outputs/runtime.json"]["sha256"], "build runtime")
                    builds[uid] = (build, digest, service)
                    if "snapshot.json" in files:
                        build_snapshots[uid] = json.loads(files["snapshot.json"])
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
                    if c["kind"] == "test":
                        require(exact_leaf(gzip.decompress(get(w["outputs"]["observations.gz"])), c["selector"]),
                                "wrong kernel test in libtest output")
                    else:
                        group = (c["source"], c.get("protocol"), c["selector"])
                        thread_data.setdefault(group, []).append((c["threads"], m["observations_sha256"]))
                else:
                    require(m["passed"] is True and m["returncode"] == 0 and m["stdout_sha256"] == w["outputs"]["stdout.txt"]
                            and m["stderr_sha256"] == w["outputs"]["stderr.txt"]
                            and exact_leaf(get(w["outputs"]["stdout.txt"]), c["selector"]), "libtest outcome")
                    name = (c["manifest"], c["name"], tuple(c["kind"]), c["selector"])
                    selection = c.get("selection", "ordinary")
                    require(selection in ("ordinary", "ignored"), "undeclared libtest selection")
                    rows = release_scale_rows if selection == "ignored" else workspace_rows
                    leaves = rows.setdefault(c["parent"], set())
                    require(name not in leaves, "duplicate workspace case")
                    leaves.add(name)
                    workspace_uploads[uid] = inputs["files"]
            if "request.json" in files:
                request = json.loads(files["request.json"])
                result = json.loads(get(w["outputs"]["comparison-result.json"]))
                checkpoint_jobs[uid] = (request, result, inputs["files"], sha(files["checkpoint_identity.py"]))
            if "comparison.json" in files:
                plan = json.loads(files["comparison.json"])
                m = json.loads(get(w["outputs"]["verified.json"]))
                require(sha(files["comparison.json"]) == m["comparison_sha256"] and
                        [c["uuid"] for c in plan["cases"]] == [c["uuid"] for c in m["cases"]], "reducer identity")
                comparisons[uid] = (plan, m)
        require(used == set(members), "unlisted evidence body")
    require(len(all_ids) == summary["workflows"] and builds and case_records, "published workflow inventory")
    suites = {name: summary[name] for name in ("workspace", "examples") if name in summary}
    require(set(workspace_rows) == {suite["parent"] for suite in suites.values()}, "declared test parents")
    for name, suite in suites.items():
        parent = suite["parent"]
        catalog = builds[parent][0]
        require(not suite["errors"] and catalog.get("selection", "workspace") == name, "test target selection")
        expected_cases, ignored = workspace_inventory(catalog)
        require(workspace_rows[parent] == expected_cases and
                len(expected_cases) == suite["ordinary"] == suite["passed"] and
                sorted(map(tuple, suite["ignored"])) == ignored, "complete discovered " + name)
    if "release_scale" in summary:
        release = summary["release_scale"]
        parent = release["parent"]
        require(parent == suites["workspace"]["parent"] and set(release_scale_rows) == {parent}
                and not release["errors"], "release-scale parent")
        catalog = builds[parent][0]
        ignored_cases = {(t["manifest"], t["name"], tuple(t["kind"]), n)
                         for t in catalog["targets"] for n in t["ignored"]}
        require(release_scale_rows[parent] == ignored_cases and
                len(ignored_cases) == release["passed"] == release["selected"],
                "one exact execution per ignored test")
    else:
        require(not release_scale_rows, "unexpected release-scale cases")
    for values in thread_data.values():
        require(sorted(n for n, _ in values) == [1, 2, 4, 8, 16] and len({h for _, h in values}) == 1,
                "thread layouts and byte equivalence")
    common_sources = {}
    checkpoint_count = 0
    extension = summary.get("point_extension")
    if extension is not None:
        pairs = extension["pairs"]
        original_labels = {plan["label"] for plan, _ in comparisons.values()
                           if plan["kind"] == "strong" and plan["source"] == extension["original_source"]}
        require(len(pairs) == len(original_labels) == 20 and {p["label"] for p in pairs} == original_labels,
                "original MPI family inventory")
        build_fields = {"parent", "source", "protocol", "build_sha256", "binary_sha256"}
        for p in pairs:
            old = outcomes[p["original"]][0]
            new = outcomes[p["current"]][0]
            require(old["source"] == extension["original_source"] and new["source"] == extension["source"]
                    and old["label"] == new["label"] == p["label"] and (new["ranks"], new["threads"]) == (2, 1)
                    and {k: v for k, v in old.items() if k not in build_fields}
                    == {k: v for k, v in new.items() if k not in build_fields}, "recompiled original MPI mode")
        checkpoint_count = verify_rebuilt_states(pairs, outcomes, checkpoint_jobs, extension["checkpoint_rule"])
        before, previous, _ = outcomes[extension["shared_original"]]
        after, expanded, _ = outcomes[extension["shared_extension"]]
        require(before["label"] == "moving-curl3" and before["source"] == extension["original_source"]
                and after["label"] == "point-curl3" and after["source"] == extension["source"]
                and set(expanded) == set(previous) | {"point-operators.csv"}
                and all(expanded[k] == v for k, v in previous.items()), "pre-existing magnetic and flux fields")
        # The workspace tests and two MPI binaries were compiled in separate workflows.
        roots = {"Cargo.toml", "Cargo.lock", "rust-toolchain.toml", "docs/galaxy/fixtures/m2c_tessellation_flip.txt"}
        for parent in (suites["workspace"]["parent"], suites["examples"]["parent"], before["parent"], after["parent"]):
            snapshot = build_snapshots[parent]
            require(snapshot["source_revision"] == builds[parent][0]["source"], "build source revision")
            sources = {k: v for k, v in snapshot["source_sha256"].items() if k in roots or k.startswith("crates/")
                       or (k.startswith("apps/") and not k.startswith("apps/openmhd-mpi/"))}
            require(roots <= sources.keys() and "crates/mhd-parallel/src/lib.rs" in sources
                    and (not common_sources or common_sources == sources), "workspace and MPI source files")
            common_sources = sources
        plan, _ = comparisons[extension["comparison"]]
        shared = next(pair for pair in pairs if pair["label"] == "moving-curl3")
        require(plan["label"] == "point-curl3" and plan["source"] == extension["source"]
                and plan["kind"] == "strong" and len(plan["cases"]) == extension["layout_cases"] == 7
                and extension["shared_original"] == shared["original"]
                and extension["shared_extension"] in {row["uuid"] for row in plan["cases"]}
                and (after["ranks"], after["threads"]) == (2, 1), "additional point-operator comparison")
    else:
        require(not checkpoint_jobs, "checkpoint checks without declared MPI rebuild")
    for uid, (c, row) in case_records.items():
        parent, parent_sha, service = builds[c["parent"]]
        require(parent["source"] == c["source"], "different parent source")
        if "catalog_sha256" in c:
            uploaded = workspace_uploads[uid]
            require(c["catalog_sha256"] == parent_sha == uploaded["catalog.json"]["sha256"] and
                    parent["binaries"][c["binary"]]["sha256"] == row["binary_sha256"], "workspace executable")
            programs = {"program.gz": c["binary"]}
            if (c["manifest"], c["name"]) == ("apps/openmhd/Cargo.toml", "restart"):
                programs["application.gz"] = parent["restart_application"]
            for path, key in programs.items():
                program = parent["binaries"][key]
                require(uploaded[path] == {"sha256": program["compressed_sha256"], "bytes": program["compressed_bytes"]},
                        "uploaded binary differs from its parent build")
        else:
            binary = c.get("binary", "openmhd-mpi")
            require(c["build_sha256"] == parent_sha and c["binary_sha256"] == parent["executables"][binary]["sha256"],
                    "compiled program identity")
        if "restart_parent" in c:
            prior_case, prior_hashes, _ = outcomes[c["restart_parent"]]
            require(prior_case["source"] == c["source"] and prior_hashes["checkpoint.bin"] == c["restart_sha256"]
                    and prior_case["ranks"] != c["ranks"], "original changed-layout checkpoint")
    prior_path = directory / "superseded-pilots.json"
    historical_failures = set()
    if prior_path.exists():
        for prior in json.loads(prior_path.read_bytes()).values():
            seen = set()
            require(prior["parent"] in builds, "superseded build")
            for entry in prior["originals"]:
                uid = entry["uuid"]
                require(uid not in seen, "duplicate original pilot")
                seen.add(uid)
                if entry["status"] == "finished":
                    require(all_ids[uid]["outputs"]["result.json"]["sha256"] == entry["result_sha256"]
                            and outcomes[uid][1] == entry["science"], "superseded successful result")
                    continue
                records = entry["records"]
                case = json.loads(records["case"])
                terminal = json.loads(records["terminal"])
                inputs = json.loads(records["inputs"])
                require(entry["status"] == terminal["status"] == "failed" and uid == terminal["id"] == inputs["uuid"]
                        and json.loads(records["identity"])["uuid"] == uid and uid not in all_ids,
                        "superseded failed workflow")
                require(case == entry["case"] and case["source"] == prior["source"] and case["parent"] == prior["parent"]
                        and inputs["files"]["case.json"]["sha256"] == sha(records["case"].encode())
                        and sha(records["spec"].encode()) == entry["spec_sha256"]
                        and sha(records["inputs"].encode()) == entry["inputs_sha256"], "failed original release")
                body = entry["process_log"].encode()
                require(entry["original_outputs"]["process.log"] == {"bytes": len(body), "sha256": sha(body)},
                        "failed process output")
                historical_failures.add(uid)

    for plan, m in comparisons.values():
        rank_threads = sorted((outcomes[x["uuid"]][0]["ranks"], outcomes[x["uuid"]][0]["threads"])
                              for x in plan["cases"] if not outcomes[x["uuid"]][0]["reference"])
        if plan["kind"] == "strong":
            require({(1,1),(1,4),(2,1),(2,2),(4,1)} <= set(rank_threads) and
                    outcomes[m["reference_uuid"]][0]["reference"], "strong layout inventory")
        if plan["kind"] == "pilot":
            require(rank_threads == [(2,1)] and outcomes[m["reference_uuid"]][0]["reference"], "pilot layout inventory")
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
            if plan["kind"] in ("strong","pilot"):
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
            "workspace_leaves": suites.get("workspace", {}).get("passed", 0),
            "example_leaves": suites.get("examples", {}).get("passed", 0),
            "release_scale_leaves": summary.get("release_scale", {}).get("passed", 0),
            "recompiled_original_families": len(extension["pairs"]) if extension else 0,
            "common_workspace_source_files": len(common_sources),
            "recompiled_mhd_checkpoints": checkpoint_count, "checkpoint_workflows": len(checkpoint_jobs),
            "superseded_failed_pilots": len(historical_failures),
            "manifest_sha256": sha((directory / "manifest.json").read_bytes())}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("directory", type=Path)
    print(json.dumps(verify(p.parse_args().directory), sort_keys=True))
