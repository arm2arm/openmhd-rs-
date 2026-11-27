"""Recompute the registered S-CENTROID rates and convergence from original REANA logs."""
import argparse
from fractions import Fraction as F
import hashlib
import io
from itertools import permutations
import json
import math
from pathlib import Path
import re
import tarfile
from uuid import UUID

AXES = tuple("".join(p) for p in permutations("xyz"))
DENOMINATORS = tuple(2 ** j for j in range(5, 12))
CONTROLS = {
    "periodic_self_image_rigid_translation",
    "periodic_two_owner_seam_uses_both_image_velocities",
    "fixed_walls_keep_centroid_stationary_while_generator_drifts",
    "rigid_bounded_translation_moves_every_centroid_with_the_walls",
    "a_joint_boost_shifts_centroid_velocity_on_the_deforming_box",
    "reject_incomplete_mismatched_and_nonfinite_velocity_fields",
    "reject_unrepresentable_integrated_face_flux",
    "reject_indices_from_a_different_geometry_epoch",
}
CATALOG = sorted(CONTROLS | {f"{p}::h{d}" for p in AXES for d in DENOMINATORS})
START = ((F(1, 4), F(7, 16), F(3, 8)), (F(3, 4), F(9, 16), F(5, 8)))
VEL = ((F(1, 8), F(3, 16), -F(1, 16)), (-F(1, 16), -F(1, 8), F(1, 16)))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def identity(data):
    return {"bytes": len(data), "sha256": sha(data)}


def reference(t, owner, axes):
    """Integrate columns of the unit cube and differentiate their moments exactly."""
    x = [tuple(a + t * v for a, v in zip(r, w)) for r, w in zip(START, VEL)]
    delta = [b - a for a, b in zip(*x)]
    slope = [b - a for a, b in zip(*VEL)]
    mid = [(a + b) / 2 for a, b in zip(*x)]
    mid_dot = [(a + b) / 2 for a, b in zip(*VEL)]
    p, q = [d / delta[0] for d in delta[1:]]
    dp, dq = [(v - s * slope[0]) / delta[0] for v, s in zip(slope[1:], (p, q))]
    u, v = (z - F(1, 2) for z in mid[1:])
    a = mid[0] + p * u + q * v
    da = mid_dot[0] + dp * u + p * mid_dot[1] + dq * v + q * mid_dot[2]
    require(all(0 < a - p * y - q * z < 1 for y in (-F(1, 2), F(1, 2))
                for z in (-F(1, 2), F(1, 2))), "bisector leaves the registered topology")
    first = ((a*a + (p*p + q*q)/12)/2, a/2 - p/12, a/2 - q/12)
    first_dot = (a*da + (p*dp + q*dq)/12, da/2 - dp/12, da/2 - dq/12)
    # The oriented normal flux times surface area is F_t dy dz in this chart.
    surface_moment = ((p*dp + q*dq)/12, -dp/12, -dq/12)
    if owner == 1:
        a, da = 1 - a, -da
        first = tuple(F(1, 2) - i for i in first)
        first_dot = tuple(-di for di in first_dot)
    c = tuple(i/a for i in first)
    dc = tuple((di - ci * da)/a for di, ci in zip(first_dot, c))
    index = ["xyz".index(k) for k in axes]
    return ((a, *(c[k] for k in index)), (da, *(dc[k] for k in index)),
            tuple(surface_moment[k] for k in index))


def measurements(output, selector):
    axes, spacing = selector.split("::h")
    denom = int(spacing)
    rows, diagnostic = {}, {}
    for tokens in (line.split("M2C ", 1)[1].split() for line in output.splitlines()
                   if "M2C " in line):
        tag = tokens[0]
        if tag in ("rate", "sample"):
            require(len(tokens) == 7, selector + " malformed measurement")
            key = (tag, int(tokens[1]), int(tokens[2]))
            require(key not in rows, selector + " duplicate measurement")
            rows[key] = tuple(map(float, tokens[3:]))
        else:
            require(tag in {"moment", "errors"} and tag not in diagnostic, selector + " diagnostic")
            diagnostic[tag] = tuple(map(float, tokens[1:]))
    expected = {(tag, i, t) for i in range(2) for tag, times in
                (("sample", (-1, 0, 1)), ("rate", (0,))) for t in times}
    require(rows.keys() == expected and diagnostic.keys() == {"moment", "errors"}, selector)
    require(len(diagnostic["moment"]) == 3 and len(diagnostic["errors"]) == 4, selector)
    require(all(math.isfinite(x) for row in (*rows.values(), *diagnostic.values()) for x in row),
            selector + " nonfinite record")
    analytic, moment_error, volume, centroid, gap, omitted = (0.0,) * 6
    for i in range(2):
        for tick in (-1, 0, 1):
            shape, rate, moment = reference(F(tick, denom), i, axes)
            raw = rows["sample", i, tick]
            analytic = max(analytic, *(abs(v - float(e)) for v, e in zip(raw, shape)))
            if tick == 0:
                current = rows["rate", i, 0]
                analytic = max(analytic, *(abs(v - float(e)) for v, e in zip(current, rate)))
                moment_error = max(moment_error, *(abs(v - float(e))
                                    for v, e in zip(diagnostic["moment"], moment)))
                gap = max(gap, *(abs(v - float(VEL[i]["xyz".index(k)]))
                                 for v, k in zip(current[1:], axes)))
                omitted = max(omitted, *(abs(m / raw[0]) for m in diagnostic["moment"]))
        minus, plus = rows["sample", i, -1], rows["sample", i, 1]
        errors = [abs((b - a) * (denom / 2) - rate)
                  for a, b, rate in zip(minus, plus, rows["rate", i, 0])]
        volume, centroid = max(volume, errors[0]), max(centroid, *errors[1:])
    require(rows["rate", 0, 0][0] == -rows["rate", 1, 0][0], selector + " shared flux")
    require(max(analytic, moment_error) <= 1e-10 and min(gap, omitted) > 1e-2,
            selector + " exact shape, rate, or sensitivity")
    require(all(abs(v - w) <= 1e-14 for v, w in
                zip((volume, centroid, gap, omitted), diagnostic["errors"])),
            selector + " raw/reduced error mismatch")
    return dict(denominator=denom, volume_error=volume, centroid_error=centroid,
                exact_error=analytic, face_moment_error=moment_error,
                centroid_generator_gap=gap, omitted_moment_gap=omitted)


def read_packet(path):
    files = {}
    with tarfile.open(path, "r:gz") as archive:
        for item in archive:
            require(item.isfile() and item.name not in files and not item.name.startswith("/")
                    and ".." not in Path(item.name).parts, "unexpected archive member")
            files[item.name] = archive.extractfile(item).read()
    return files


def receipt(files, prefix, name):
    def body(key):
        return files[f"{prefix}/{key}"]
    result, inputs, terminal = [json.loads(body(k)) for k in
                                ("download.json", "inputs.json", "terminal.json")]
    uuid = str(UUID(result["uuid"]))
    require(terminal == dict(id=uuid, name=name, status="finished", version=1, workflow=name+".1")
            and result["workflow"] == name+".1" and inputs["uuid"] == uuid, name + " workflow")
    require(result["inputs"] == sha(body("inputs.json")) and result["spec"] == sha(body("reana.yaml"))
            and inputs["files"]["reana.yaml"] == identity(body("reana.yaml")), name + " release")
    spec = json.loads(body("reana.yaml"))
    require(set(spec["inputs"]["files"]) | {"reana.yaml"} == inputs["files"].keys()
            and set(spec["outputs"]["files"]) == result["outputs"].keys(), name + " file inventory")
    return uuid, inputs["files"], result["outputs"], spec


def review(path):
    files = read_packet(path)
    build = json.loads(files["build/build.json"])
    ref = build["source_revision"]
    require(re.fullmatch("[0-9a-f]{40}", ref) and sorted(build["selectors"]) == CATALOG,
            "frozen source and discovered exact catalog")
    uid, pins, outputs, _ = receipt(files, "build", "openmhd-m2c-centroid-build-"+ref[:10])
    snap = json.loads(files["build/snapshot.json"])
    protocol = "docs/galaxy/M2C_CENTROID_PROTOCOL.md"
    require(ref == snap["source_revision"] and pins["snapshot.json"] == identity(files["build/snapshot.json"])
            and pins["centroid_build.py"] == identity(files["build/centroid_build.py"])
            and build["runtime_sha256"] == sha(files["build/runtime.json"]), "build source or runtime")
    for n, expected in snap["upload_sha256"].items():
        require(pins[n]["sha256"] == expected, "snapshot upload "+n)
    archive = snap["archives"]["source.tar.gz"]
    parts = []
    for name in archive["parts"]:
        data = files["build/"+name]
        require(identity(data) == pins[name], "source archive part")
        parts.append(data)
    source = b"".join(parts)
    require(sha(source) == archive["sha256"], "frozen source archive")
    source_ids = {}
    with tarfile.open(fileobj=io.BytesIO(source), mode="r:gz") as tar:
        for item in tar:
            require(item.isfile() and item.name not in source_ids, "source member")
            source_ids[item.name] = sha(tar.extractfile(item).read())
    require(source_ids == snap["source_sha256"] and protocol in source_ids, "complete build source")
    for key, record in outputs.items():
        require(record == identity(files["build/"+key.split("/")[-1]]), key)
    binary = identity(files["build/centroid-tests"])
    require(binary["sha256"] == build["executables"]["centroid-tests"]["sha256"], "native executable")
    require([row["argv"][1] for row in build["commands"]] == ["fmt", "clippy", "build", "test"]
            and "--no-run" in build["commands"][-1]["argv"], "build stages")
    for i, row in enumerate(build["commands"]):
        require(row["returncode"] == 0 and row["sha256"] == sha(files[f"build/build-{i}.log"]),
                "build stage "+str(i))
    parent = dict(source_revision=ref, uuid=uid, report_sha256=sha(files["build/build.json"]),
                  protocol_sha256=snap["source_sha256"][protocol])
    cohorts, ids = {axes: [] for axes in AXES}, {uid}
    for index, selector in enumerate(CATALOG, 1):
        prefix = "cases/"+selector.replace("::", "-")
        name = f"openmhd-m2c-centroid-{ref[:10]}-{index:02}"
        uuid, pins, outputs, spec = receipt(files, prefix, name)
        require(uuid not in ids, selector + " reused workflow")
        ids.add(uuid)
        stage = spec["workflow"]["specification"]["steps"]
        require(len(stage) == 1 and stage[0]["kubernetes_cpu_limit"] == "1" and
                stage[0]["kubernetes_memory_limit"] == "4Gi" and
                "timeout 900 python3 -B run_leaf.py" in stage[0]["commands"][0], selector+" resources")
        case_bytes = files[prefix+"/case.json"]
        args = ["--exact", selector, "--nocapture", "--test-threads=1"]
        require(json.loads(case_bytes) == dict(selector=selector, binary="centroid-tests",
                sha256=binary["sha256"], parent=parent, args=args), selector + " selected native leaf")
        require(pins["case.json"] == identity(case_bytes) and pins["centroid-tests"] == binary and
                pins["run_leaf.py"] == identity(files["run_leaf.py"]), selector+" released inputs")
        for key, record in outputs.items():
            require(identity(files[prefix+"/"+key]) == record, selector+" "+key)
        observed = json.loads(files[prefix+"/result.json"])
        require(observed == dict(selector=selector, parent=parent, sha256=binary["sha256"], argv=args,
                returncode=0, passed=True, stdout_sha256=outputs["stdout.txt"]["sha256"],
                stderr_sha256=outputs["stderr.txt"]["sha256"]), selector+" original exit")
        log = files[prefix+"/stdout.txt"].decode()
        require("running 1 test\n" in log and f"test {selector} ..." in log and
                "test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 49 filtered out;" in log,
                selector+" native result")
        if selector not in CONTROLS:
            cohorts[selector.split("::")[0]].append(measurements(log, selector))
    orders = {"volume": [], "centroid": []}
    finest = {}
    for axes, levels in cohorts.items():
        levels.sort(key=lambda row: row["denominator"])
        require(tuple(row["denominator"] for row in levels) == DENOMINATORS, axes + " spacing")
        for quantity in orders:
            key = quantity+"_error"
            for coarse, fine in zip(levels, levels[1:]):
                require(0 < fine[key] < coarse[key], axes+" "+quantity+" decrease")
                order = math.log2(coarse[key] / fine[key])
                require(order >= 1.8, axes+" "+quantity+" order")
                orders[quantity].append(order)
            require(levels[-1][key] <= 1e-7, axes+" "+quantity+" finest error")
            finest[quantity] = max(finest.get(quantity, 0), levels[-1][key])
    all_levels = [row for levels in cohorts.values() for row in levels]
    return dict(gate="M2c S-CENTROID", source_revision=ref, build_uuid=uid,
                binary_sha256=binary["sha256"], protocol_sha256=parent["protocol_sha256"],
                case_count=len(CATALOG), controls=sorted(CONTROLS), oblique_cases=len(all_levels),
                passed=True, minimum_observed_order={k:min(vals) for k,vals in orders.items()},
                maximum_finest_error=finest, maximum_analytic_error=max(r["exact_error"] for r in all_levels),
                maximum_face_moment_error=max(r["face_moment_error"] for r in all_levels),
                minimum_centroid_generator_gap=min(r["centroid_generator_gap"] for r in all_levels),
                minimum_omitted_moment_gap=min(r["omitted_moment_gap"] for r in all_levels),
                axis_ladders=cohorts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    summary = review(args.packet)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False)+"\n")
    print(f'{summary["gate"]} passed for {summary["case_count"]} workflows')
