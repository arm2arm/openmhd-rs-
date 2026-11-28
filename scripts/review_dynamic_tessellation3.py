"""Replay the finite-step geometry decisions from the archived REANA outputs."""

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import tarfile


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_packet(path):
    with tarfile.open(path, "r:gz") as archive:
        files = {}
        for item in archive:
            require(item.isfile() and item.name not in files, "unexpected archive member")
            files[item.name] = archive.extractfile(item).read()
    inventory = json.loads(files.pop("sha256.json"))
    require({name: digest(buf) for name, buf in files.items()} == inventory, "archive body hashes")
    return files


def check_all_shared_faces(rows):
    """Compare the two directed boundaries in the common frame of the bounded CLI fixture."""
    by_face = {}
    for row in rows:
        key = (int(row["step"]), int(row["face"]))
        by_face.setdefault(key, {}).setdefault(int(row["sign"]), []).append(row)

    counts = {step: {"interior": 0, "wall": 0} for step in range(3)}
    max_separation = 0.0
    for (step, _), sides in by_face.items():
        left = sides[1]
        is_wall = left[0]["wall_patch"] != ""
        require(set(sides) == ({1} if is_wall else {1, -1}), "face incidence count")
        for loop in sides.values():
            require(
                len(loop) >= 3 and [int(row["vertex"]) for row in loop] == list(range(len(loop))),
                "directed polygon loop",
            )
            for field in ("owner", "neighbour", "wall_patch", "area", "nx", "ny", "nz"):
                require(all(row[field] == loop[0][field] for row in loop), "inconsistent face row")
        if is_wall:
            require(
                not left[0]["neighbour"] and 0 <= int(left[0]["wall_patch"]) < 6, "wall incidence"
            )
            counts[step]["wall"] += 1
            continue
        right = sides[-1]
        require(
            left[0]["owner"] == right[0]["neighbour"] and right[0]["owner"] == left[0]["neighbour"],
            "face owners",
        )
        require(float(left[0]["area"]) == float(right[0]["area"]) > 0, "shared positive area")
        require(
            all(float(left[0]["n" + a]) == -float(right[0]["n" + a]) for a in "xyz"),
            "opposite normals",
        )
        require(len(left) == len(right), "shared vertex count")
        for i, row in enumerate(left):
            other = right[-i % len(right)]
            p = tuple(float(row[a]) + float(row["d" + a]) for a in "xyz")
            q = tuple(float(other[a]) + float(other["d" + a]) for a in "xyz")
            separation = math.dist(p, q)
            require(separation < 1e-12, "opposite oriented common-frame edges")
            max_separation = max(max_separation, separation)
        counts[step]["interior"] += 1
    return {"faces_by_epoch": counts, "max_paired_vertex_separation": max_separation}


def check_csv(raw):
    owners = {}
    faces = {}
    all_rows = list(csv.DictReader(io.StringIO(raw.decode("ascii"))))
    for row in all_rows:
        step = int(row["step"])
        require(step in (0, 1, 2) and float(row["time"]) == step / 2, "CLI clock")
        owner = int(row["owner"], 16)
        require(owner >> 64 == 8 and owner % 2**64 < 5, "CLI owner")
        key = (step, owner)
        coordinate = tuple(float(row[a]) for a in "xyz")
        require(owners.setdefault(key, coordinate) == coordinate, "CLI site")
        if row["neighbour"]:
            neighbour = int(row["neighbour"], 16)
            if {owner, neighbour} == {8 * 2**64 + 3, 8 * 2**64 + 4}:
                faces.setdefault(key, []).append(row)
    require(len(owners) == 15 and len(faces) == 2, "CLI epochs and face birth")
    expected = [(-1 / 32, -1 / 16, -1 / 32), (-1 / 32, 1 / 16, -1 / 32), (5 / 96, 0, -1 / 32)]
    loops = {}
    signed_areas = []
    for owner, sign in ((3, 1), (4, -1)):
        rows = faces[(2, 8 * 2**64 + owner)]
        require([int(r["vertex"]) for r in rows] == [0, 1, 2], "triangle vertex indices")
        loop = []
        for row in rows:
            require(int(row["sign"]) == sign and float(row["nz"]) == sign, "triangle orientation")
            point = tuple(float(row[a]) + float(row["d" + a]) for a in "xyz")
            loop.append(point)
        require(
            all(any(math.dist(pt, q) < 1e-12 for pt in loop) for q in expected), "analytic vertices"
        )
        a, b, c = loop
        area = ((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / 2
        require(abs(area - sign / 192) < 1e-13, "signed analytic area")
        require(all(abs(float(row["area"]) - abs(area)) < 1e-13 for row in rows), "reported area")
        loops[sign] = loop
        signed_areas.append(area)
    require(
        all(math.dist(p, loops[-1][j]) < 1e-12 for p, j in zip(loops[1], (0, 2, 1))), "opposite fan"
    )
    return dict(
        times=[0, 0.5, 1],
        positive_face_times=[1],
        signed_areas=signed_areas,
        **check_all_shared_faces(all_rows),
    )


def replay(files):
    def obj(name):
        return json.loads(files[name])

    build = obj("build/build.json")
    origin = obj("build/downloads.json")
    terminal = obj("build/terminal.json")
    require(terminal["status"] == "finished" and origin["uuid"] == terminal["id"], "build identity")
    require(origin["spec"] == digest(files["build/reana.yaml"]), "build specification")
    require(build["runtime_sha256"] == digest(files["build/runtime.json"]), "build runtime")
    build_inputs = obj("build/inputs.json")
    require(
        origin["inputs"] == digest(files["build/inputs.json"])
        and build_inputs["uuid"] == origin["uuid"],
        "build inputs",
    )
    for name in ("reana.yaml", "geom_build.py", "snapshot.json"):
        require(
            build_inputs["files"][name]["sha256"] == digest(files["build/" + name]),
            "build input bytes",
        )
    require(
        set(build["selectors"]) == {"dynamic_tessellation3", "lloyd3"}, "registered Rust suites"
    )
    require(
        [c["argv"][1] for c in build["commands"]] == ["fmt", "clippy", "build", "test"],
        "build gates",
    )
    for remote_path, info in origin["outputs"].items():
        buf = files["build/" + Path(remote_path).name]
        require(digest(buf) == info["sha256"] and len(buf) == info["bytes"], "build download")
    for i, command in enumerate(build["commands"]):
        require(
            command["returncode"] == 0
            and digest(files[f"build/build-{i}.log"]) == command["sha256"],
            "build command",
        )
    snapshot = obj("build/snapshot.json")
    protocol = "docs/galaxy/DYNAMIC_TESSELLATION_3D.md"
    require(snapshot["source_revision"] == build["source_revision"], "source revision")
    require(snapshot["source_sha256"][protocol] == digest(files["protocol.md"]), "frozen protocol")
    expected = {name: binary for binary, names in build["selectors"].items() for name in names}
    expected["flip_cli"] = "moving-voronoi3"
    present = {n.split("/")[1] for n in files if n.startswith("cases/")}
    require(set(expected) == present, "whole campaign coverage")
    ids = {}
    errors = {"Bounded": {}, "Periodic": {}}
    rigid = {}
    for name, binary in sorted(expected.items()):
        pre = f"cases/{name}/"
        case, result = obj(pre + "case.json"), obj(pre + "result.json")
        downloads, end = obj(pre + "downloads.json"), obj(pre + "terminal.json")
        uid = end["id"]
        require(
            end["status"] == "finished" and uid == downloads["uuid"] and uid not in ids.values(),
            "distinct finished workflow",
        )
        ids[name] = uid
        require(digest(files[pre + "reana.yaml"]) == downloads["spec"], "leaf specification")
        spec = obj(pre + "reana.yaml")
        (resource,) = spec["workflow"]["specification"]["steps"]
        require(
            resource["kubernetes_cpu_request"] == resource["kubernetes_cpu_limit"] == "1"
            and resource["kubernetes_memory_limit"] == "4Gi",
            "case resources",
        )
        input_receipt = obj(pre + "inputs.json")
        require(
            downloads["inputs"] == digest(files[pre + "inputs.json"])
            and input_receipt["uuid"] == uid,
            "input receipt",
        )
        uploaded = {
            "case.json": files[pre + "case.json"],
            "reana.yaml": files[pre + "reana.yaml"],
            binary: files["build/" + binary],
            "run_case.py": files["run_case.py"],
        }
        if name == "flip_cli":
            uploaded["catalog.txt"] = files["catalog.txt"]
        require(
            input_receipt["files"]
            == {k: {"sha256": digest(v), "bytes": len(v)} for k, v in uploaded.items()},
            "original input files",
        )
        require(set(downloads["outputs"]) == set(spec["outputs"]["files"]), "output inventory")
        for member, info in downloads["outputs"].items():
            buf = files[pre + member]
            require(digest(buf) == info["sha256"] and len(buf) == info["bytes"], "case download")
        require(
            result["parent"] == case["parent"]
            and case["parent"]["uuid"] == origin["uuid"]
            and case["parent"]["build_sha256"] == digest(files["build/build.json"]),
            "parent links",
        )
        require(
            result["source_revision"]
            == case["parent"]["source_revision"]
            == build["source_revision"]
            and case["parent"]["protocol_sha256"] == digest(files["protocol.md"]),
            "release",
        )
        require(
            case["selector"] == result["selector"] == name
            and case["binary"] == result["binary"] == binary,
            "case selection",
        )
        require(
            case["sha256"]
            == result["binary_sha256"]
            == build["executables"][binary]["sha256"]
            == digest(files["build/" + binary]),
            "executable identity",
        )
        require(result["passed"] is True and result["returncode"] == 0, "native success")
        args = (
            ["catalog.txt", "0.5", "0.5"]
            if name == "flip_cli"
            else ["--exact", name, "--include-ignored", "--nocapture", "--test-threads=1"]
        )
        require(
            result["args"] == args and 0 < result["elapsed_seconds"] <= 600,
            "selected invocation and time budget",
        )
        raw = files[pre + "stdout.txt"]
        require(
            digest(raw) == result["stdout_sha256"]
            and digest(files[pre + "stderr.txt"]) == result["stderr_sha256"],
            "logs",
        )
        if name == "flip_cli":
            require(
                raw == files[pre + "mesh.csv"]
                and digest(files["catalog.txt"]) == case["catalog_sha256"],
                "demo data",
            )
            continue
        log = raw.decode()
        require(
            "running 1 test\n" in log
            and "test " + name + " ..." in log
            and "test result: ok. 1 passed; 0 failed;" in log,
            "one exact Rust leaf",
        )
        match = re.search(
            r"SMOOTH boundary=(\w+) inverse_h=(\d+) scaled_fd_error=(\S+) analytic=(\S+)", log
        )
        if match:
            boundary, den, actual, analytic = match.groups()
            den, actual = int(den), float(actual)
            require(
                name == boundary.lower() + "_h" + str(den)
                and abs(actual - float(analytic)) <= 2e-11,
                "analytic volume derivative",
            )
            errors[boundary][den] = actual
        match = re.search(r"RIGID n=(\d+) cells=(\d+) faces=(\d+) volume_closure=(\S+)", log)
        if match:
            n, cells, faces, closure = match.groups()
            n, cells, faces, closure = int(n), int(cells), int(faces), float(closure)
            require(
                name == f"rigid_{n}_cubed_multiple_wraps"
                and cells == n**3
                and faces == 3 * n**3
                and closure <= 1e-10,
                "periodic rigid counts and closure",
            )
            rigid[n] = dict(
                cells=cells,
                faces=faces,
                relative_volume_closure=closure,
                elapsed_seconds=result["elapsed_seconds"],
            )
    ladders = {}
    for boundary, data in errors.items():
        levels = sorted(data)
        require(levels == [128, 256, 512, 1024], "four step sizes")
        values = [data[level] for level in levels]
        orders = [math.log2(a / b) for a, b in zip(values, values[1:])]
        require(min(orders) >= 1.8 and values[-1] <= 1e-7, "finite-step convergence")
        ladders[boundary] = dict(inverse_h=levels, scaled_volume_rate_errors=values, orders=orders)
    require(set(rigid) == {4, 8}, "both rigid resolutions")
    return dict(
        source_revision=build["source_revision"],
        build_uuid=origin["uuid"],
        case_uuids=ids,
        passing_cases=len(ids),
        rigid_translation=rigid,
        smooth_motion=ladders,
        face_birth=check_csv(files["cases/flip_cli/mesh.csv"]),
    )


def plot_face(raw, output):
    """Draw intersections of the exported 3D polygons with the axial bisector."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    from matplotlib.patches import Polygon
    from collections import defaultdict

    rows = list(csv.DictReader(io.StringIO(raw.decode("ascii"))))
    fig, axes = plt.subplots(1, 3, figsize=(10.6, 4.3))
    fig.subplots_adjust(left=0.065, right=0.98, top=0.74, bottom=0.20, wspace=0.15)
    fig.text(
        0.065,
        0.92,
        "Birth of a shared Voronoi face",
        fontsize=20,
        weight="semibold",
        color="#183541",
    )
    fig.text(
        0.065,
        0.837,
        "Sections through the pole-to-pole bisector in a five-generator 3D mesh",
        fontsize=11,
        color="#425761",
    )
    for step, (ax, title) in enumerate(
        zip(axes, ("Separated", "Point contact", "Positive-area face"))
    ):
        epoch = [r for r in rows if int(r["step"]) == step]
        sites = {int(r["owner"], 16) % 2**64: float(r["z"]) for r in epoch}
        height = (sites[3] + sites[4]) / 2
        faces = defaultdict(list)
        for r in epoch:
            if int(r["sign"]) == 1:
                faces[(r["owner"], r["face"], r["neighbour"])].append(
                    tuple(float(r[a]) + float(r["d" + a]) for a in "xyz")
                )
        segments = []
        for (owner, _, neighbour), loop in faces.items():
            if not neighbour:
                continue
            if {int(owner, 16) % 2**64, int(neighbour, 16) % 2**64} == {3, 4}:
                ax.add_patch(
                    Polygon(
                        [p[:2] for p in loop],
                        closed=True,
                        facecolor="#99d4cb",
                        edgecolor="#0b6e6b",
                        lw=2.1,
                        zorder=3,
                    )
                )
                continue
            points = []
            for a, b in zip(loop, loop[1:] + loop[:1]):
                dz1, dz2 = a[2] - height, b[2] - height
                if abs(dz1) < 1e-13:
                    points.append(a[:2])
                if dz1 * dz2 < 0:
                    f = dz1 / (dz1 - dz2)
                    points.append(tuple(a[k] + f * (b[k] - a[k]) for k in (0, 1)))
            if len(points) > 1:
                edge = max(((a, b) for a in points for b in points), key=lambda ab: math.dist(*ab))
                if math.dist(*edge) > 1e-12:
                    segments.append(edge)
        ax.add_collection(LineCollection(segments, colors="#728791", linewidths=1.3))
        if step == 1:
            ax.scatter([0], [0], s=30, color="#ba6c34", zorder=5)
        ax.set_xlim(-0.08, 0.1)
        ax.set_ylim(-0.085, 0.085)
        ax.set_aspect("equal")
        ax.set_xticks([-0.05, 0, 0.05])
        ax.set_yticks([-0.05, 0, 0.05])
        ax.tick_params(colors="#526770", labelsize=9)
        for spine in ax.spines.values():
            spine.set_color("#a9b9be")
        ax.set_title(
            f"t = {step/2:g}    {title}",
            loc="left",
            fontsize=11,
            color="#183541",
            weight="semibold",
        )
        ax.set_xlabel("x")
        if step == 0:
            ax.set_ylabel("y")
        else:
            ax.tick_params(labelleft=False)
    fig.text(
        0.065,
        0.047,
        "The two pole cells share a triangle of area 1/192 at t = 1. Its two outward polygon loops wind in opposite directions.",
        fontsize=9,
        color="#425761",
    )
    fig.savefig(output, dpi=170, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("summary", type=Path)
    parser.add_argument("--figure", type=Path)
    args = parser.parse_args()
    files = read_packet(args.packet)
    result = replay(files)
    args.summary.write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n")
    if args.figure:
        plot_face(files["cases/flip_cli/mesh.csv"], args.figure)
    print(f"{result['passing_cases']} independent workflows verified")
