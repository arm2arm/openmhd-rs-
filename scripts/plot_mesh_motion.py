#!/usr/bin/env python3
"""Plot checked moving-mesh geometry and hypothetical uniform-flow tracers.

By default read the archived solver outputs. --run executes two small existing
solver cases first; use --input-dir results/mesh_motion for new measurements.
No tracer evolution or changes to the numerical solver are introduced.
"""
import argparse
import csv
import gzip
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
TIMES = np.linspace(0.0, 0.6, 25)
N, JITTER = 8, 0.15
BLUE, ORANGE = "#156b9c", "#e26024"
CASES = {
    "rigid": ["--case", "uniform", "--motion", "rigid", "--mesh-x", "0.4", "--mesh-y", "-0.2"],
    "deform": ["--case", "deform", "--motion", "prescribed"],
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def command(args):
    return subprocess.check_output(args, cwd=ROOT, text=True)


def source_hashes():
    paths = [ROOT / p for p in ("Cargo.toml", "Cargo.lock", "rust-toolchain.toml",
                              "apps/openmhd/Cargo.toml", "apps/openmhd/src/bin/vector-potential.rs")]
    for name in ("mhd-core", "mhd-vector-pot", "moving-mesh", "mhd-planar"):
        folder = ROOT / "crates" / name
        paths += [folder / "Cargo.toml", *sorted(folder.glob("src/**/*.rs"))]
    return {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in paths}


def run_solver(folder):
    if folder.exists() and any(folder.iterdir()):
        raise ValueError("--run requires an empty --input-dir; preserve earlier measurements")
    folder.mkdir(parents=True, exist_ok=True)
    cargo = shutil.which("cargo") or str(Path.home() / ".cargo/bin/cargo")
    sources = source_hashes()
    build_dir = ROOT / "results/mesh_motion_build"
    build = [cargo, "build", "--release", "--locked", "-p", "openmhd", "--bin",
             "vector-potential", "--target-dir", str(build_dir)]
    revision = command(["git", "rev-parse", "HEAD"]).strip()
    status = command(["git", "status", "--short"])
    command(build)
    binary = build_dir / "release/vector-potential"
    commands = []
    for name, extra in CASES.items():
        args = [str(binary), "--profile", "paper-global-v2", "--n", str(N),
                "--jitter", str(JITTER), "--dt", "0.002", "--time", "0.6",
                "--output", str(folder / name), *extra]
        for time in TIMES[1:-1]:
            args += ["--checkpoint", f"{time:.8f}"]
        print(command(args), end="", flush=True)
        commands.append(args)
    if sources != source_hashes():
        raise ValueError("solver sources changed during the run; rerun in a fresh directory")
    # Small lossless archive, including every animation frame and full diagnostics.
    for path in sorted(folder.glob("*/*.csv")):
        path.with_suffix(".csv.gz").write_bytes(gzip.compress(path.read_bytes(), mtime=0))
        path.unlink()
    manifest = {
        "scope": "Mesh-motion illustration, not an M1 acceptance/convergence study",
        "revision": revision, "working_tree_before_run": status,
        "source_sha256": sources, "binary_sha256": sha(binary.read_bytes()),
        "build_command": build, "commands": commands,
        "rustc": command([str(Path(cargo).with_name("rustc")), "--version"]).strip(),
        "platform": platform.platform(), "times": TIMES.tolist(),
        "n": N, "jitter": JITTER,
        "file_sha256": {str(p.relative_to(folder)): sha(p.read_bytes())
                        for p in sorted(folder.glob("*/*")) if p.is_file()},
    }
    (folder / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n")


def generators(time, case):
    # Same deterministic lattice and persistent-ID velocities as the Rust driver.
    points = np.array([[(i + 0.5 + JITTER * math.sin(1.7 * (i + N*j) + 0.3))/N,
                        (j + 0.5 + JITTER * math.cos(2.3 * (i + N*j) + 0.7))/N]
                       for j in range(N) for i in range(N)])
    velocity = (np.tile([0.4, -0.2], (N*N, 1)) if case == "rigid" else
                np.array([[0.1*math.sin(math.tau*y), 0.1*math.cos(math.tau*x)] for x, y in points]))
    return (points + time * velocity) % 1.0


def tracers(time, case):
    points = np.array(list(itertools.product([0.15, 0.38, 0.61, 0.84], repeat=2)))
    return (points + time * (np.array([0.4, -0.2]) if case == "rigid" else 0.0)) % 1.0


def polygon(points, index):
    """Independent periodic half-plane construction for display, not solver code."""
    centre = points[index]
    vertices = np.array([[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]])
    images = np.concatenate([points + shift - centre for shift in itertools.product((-1, 0, 1), repeat=2)])
    distances = np.sum(images**2, axis=1)
    for k in np.argsort(distances):
        delta, distance = images[k], distances[k]
        if distance < 1e-28:
            continue
        if distance > 4.0 * np.max(np.sum(vertices**2, axis=1)) * (1.0 + 1e-13):
            break
        residual = vertices @ delta - 0.5 * distance
        clipped = []
        for a, b, da, db in zip(vertices, np.roll(vertices, -1, axis=0), residual, np.roll(residual, -1)):
            if (da <= 0) != (db <= 0):
                clipped.append(a + da / (da - db) * (b - a))
            if db <= 0:
                clipped.append(b)
        vertices = np.array(clipped)
    other = np.roll(vertices, -1, axis=0)
    cross = vertices[:, 0]*other[:, 1] - vertices[:, 1]*other[:, 0]
    area = 0.5 * np.sum(cross)
    centroid = centre + np.sum((vertices + other)*cross[:, None], axis=0)/(6*area)
    return vertices + centre, area, centroid % 1.0


def read_packet(folder):
    manifest = json.loads((folder / "provenance.json").read_text())
    for relative, expected in manifest["file_sha256"].items():
        if sha((folder / relative).read_bytes()) != expected:
            raise ValueError(f"archive checksum mismatch: {relative}")
    if manifest["n"] != N or manifest["jitter"] != JITTER or not np.allclose(manifest["times"], TIMES):
        raise ValueError("archive parameters differ from this illustration")
    data, checks = {}, {}
    for case in CASES:
        summary = json.loads((folder / case / "summary.json").read_text())
        if not summary["completed"] or summary["profile"] != "paper-global-v2":
            raise ValueError(f"incomplete or unexpected solver profile: {case}")
        expected = {"n": N, "jitter": JITTER, "time": 0.6, "dt_cap": 0.002,
                    "case": "uniform" if case == "rigid" else "deform",
                    "motion": "rigid" if case == "rigid" else "prescribed",
                    "mean_B": [0.3, 0.2, 0.1], "boost": [0.0, 0.0, 0.0]}
        if any(summary[key] != value for key, value in expected.items()):
            raise ValueError(f"unexpected solver configuration: {case}")
        history = json.loads((folder / case / "history.json").read_text())
        budget = max(abs(v) for h in history for v in h["diagnostics"]["normalized_budget"])
        if budget > 1e-10:
            raise ValueError("periodic conservative budget check failed")
        frames, area_error, centre_error, tile_error = [], 0.0, 0.0, 0.0
        for frame, time in enumerate(TIMES):
            stage = "initial" if frame == 0 else "final" if frame == len(TIMES)-1 else f"checkpoint_{time:.8f}"
            raw = gzip.decompress((folder / case / f"{stage}.csv.gz").read_bytes())
            rows = [{key: float(value) for key, value in row.items()}
                    for row in csv.DictReader(io.StringIO(raw.decode()))]
            if len(rows) != N*N or [r["id"] for r in rows] != list(range(N*N)):
                raise ValueError("persistent cell count/IDs changed")
            if any(not math.isfinite(v) for r in rows for v in r.values()):
                raise ValueError("nonfinite snapshot")
            if any(abs(r["time"] - time) > 1e-12 or r["rho"] <= 0 or r["p"] <= 0 for r in rows):
                raise ValueError("invalid snapshot time or physical state")
            points = generators(time, case)
            polygons, areas, centroids = zip(*(polygon(points, i) for i in range(N*N)))
            areas, centroids = np.array(areas), np.array(centroids)
            area_error = max(area_error, float(np.max(np.abs(areas - [r["volume"] for r in rows]))))
            delta = centroids - np.array([[r["x"], r["y"]] for r in rows])
            centre_error = max(centre_error, float(np.max(np.abs((delta + 0.5) % 1.0 - 0.5))))
            tile_error = max(tile_error, abs(float(np.sum(areas))-1.0))
            frames.append((points, polygons, areas, rows))
        if max(area_error, centre_error, tile_error) > 1e-10:
            raise ValueError("display geometry does not match solver cells")
        checks[case] = {"snapshots_checked": len(frames), "max_area_difference": area_error,
                        "max_periodic_centroid_difference": centre_error, "max_tiling_error": tile_error,
                        "max_normalized_budget_over_outputs": budget,
                        "max_fluid_speed_error_over_outputs": max(
                            math.sqrt(sum((r[k]-v)**2 for k, v in zip(("vx", "vy", "vz"),
                                          (0.4, -0.2, 0.3) if case == "rigid" else (0.0, 0.0, 0.0))))
                            for f in frames for r in f[3]),
                        "area_ratio_range": [float(fn(np.concatenate([f[2]/frames[0][2] for f in frames])))
                                             for fn in (np.min, np.max)]}
        data[case] = frames
    return data, checks, manifest


def draw(ax, frames, frame, case, norm):
    time = TIMES[frame]
    points, polygons, areas, _ = frames[frame]
    visible, ratios = [], []
    for shape, ratio in zip(polygons, areas/frames[0][2]):
        for shift in itertools.product((-1, 0, 1), repeat=2):
            shifted = shape + shift
            if np.all(shifted.max(axis=0) >= 0) and np.all(shifted.min(axis=0) <= 1):
                visible.append(shifted)
                ratios.append(ratio)
    collection = PolyCollection(visible, array=np.array(ratios), cmap="PuOr_r", norm=norm,
                                edgecolors="#78868e", linewidths=0.6)
    ax.add_collection(collection)
    # Three persistent generator IDs and three illustrative tracer paths.
    for kind, ids, color, style in ((generators, (10, 30, 52), BLUE, "-"),
                                  (tracers, (0, 6, 15), ORANGE, "--")):
        history = np.array([kind(t, case) for t in TIMES[:frame+1]])
        for index in ids:
            path = history[:, index].copy()
            # Split at periodic seams, never draw a spurious line across the box.
            jumps = np.r_[False, np.any(np.abs(np.diff(path, axis=0)) > 0.5, axis=1)]
            path[jumps] = np.nan
            ax.plot(path[:, 0], path[:, 1], style, color=color, lw=1.5, zorder=3)
    ax.scatter(*points.T, s=12, color=BLUE, zorder=4)
    ax.scatter(*tracers(time, case).T, s=39, marker="^", color=ORANGE,
               edgecolors="white", linewidths=0.6, zorder=5)
    ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="x / box length", title=f"t = {time:.3f}",
           xticks=(0, 0.5, 1), yticks=(0, 0.5, 1))
    ax.set_aspect("equal")
    return collection


def decorate(fig, axes, image, title):
    fig.suptitle(title, fontsize=14, y=0.98)
    axes[0].set_ylabel("y / box length")
    fig.legend(handles=[Line2D([], [], color=BLUE, marker="o", ms=4, label="Mesh generators; selected paths solid"),
                        Line2D([], [], color=ORANGE, marker="^", ls="--", label="Hypothetical tracers; selected paths dashed")],
               loc="lower center", ncol=2, frameon=False, fontsize=9)
    fig.colorbar(image, ax=axes, label="Cell area / its initial area", shrink=0.65, pad=0.02)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--input-dir", type=Path, default=ROOT / "tests/reference/mesh_motion")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/images/mesh_motion")
    args = parser.parse_args()
    folder, output = args.input_dir.resolve(), args.output_dir.resolve()
    if args.run:
        run_solver(folder)
    data, checks, manifest = read_packet(folder)
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 10, "figure.facecolor": "white", "savefig.facecolor": "white"})
    norm = Normalize(0.5, 1.5)
    if any(c["area_ratio_range"][0] < norm.vmin or c["area_ratio_range"][1] > norm.vmax for c in checks.values()):
        raise ValueError("colour scale would hide area changes")
    titles = {"rigid": "Rigid translation · mesh and reference fluid travel together",
              "deform": "Deforming Voronoi mesh · reference fluid and hypothetical tracers stay at rest"}
    for case in CASES:
        fig, axes = plt.subplots(1, 4, figsize=(14, 4.2), sharey=True)
        fig.subplots_adjust(left=0.045, right=0.93, top=0.84, bottom=0.19, wspace=0.12)
        for ax, frame in zip(axes, (0, 8, 16, 24)):
            im = draw(ax, data[case], frame, case, norm)
        decorate(fig, axes, im, titles[case])
        fig.savefig(output / f"{case}_sequence.png", dpi=160)
        plt.close(fig)
    images = []
    for frame in range(len(TIMES)):
        fig, axes = plt.subplots(1, 2, figsize=(10, 5.7), dpi=100)
        fig.subplots_adjust(left=0.065, right=0.88, top=0.80, bottom=0.17, wspace=0.18)
        for ax, case in zip(axes, CASES):
            im = draw(ax, data[case], frame, case, norm)
            ax.set_title(("Rigid / comoving" if case == "rigid" else "Deforming / fluid at rest") + f"\nt = {TIMES[frame]:.3f}")
        decorate(fig, axes, im, "Moving mesh and hypothetical particles · periodic unit square")
        fig.canvas.draw()
        images.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba()).copy()).convert("RGB"))
        plt.close(fig)
    images[0].save(output / "mesh_motion.gif", save_all=True, append_images=images[1:],
                   duration=[140]*24 + [1000], loop=0)
    provenance = {"simulation_revision": manifest["revision"], "geometry_checks": checks,
                  "tracers": "16 illustrative massless markers; exact uniform-flow positions, no solver feedback",
                  "source_manifest_sha256": sha((folder / "provenance.json").read_bytes()),
                  "script_sha256": sha(Path(__file__).read_bytes()),
                  "python": platform.python_version(), "numpy": np.__version__,
                  "matplotlib": matplotlib.__version__, "pillow": Image.__version__,
                  "output_sha256": {p.name: sha(p.read_bytes()) for p in sorted(output.iterdir())
                                    if p.suffix in (".png", ".gif")}}
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
