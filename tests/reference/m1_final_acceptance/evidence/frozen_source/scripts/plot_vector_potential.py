#!/usr/bin/env python3
"""Plot archived issue #6 measurements; no solver rerun or new acceptance thresholds."""
import argparse
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
import numpy as np
import PIL

ROOT = Path(__file__).resolve().parents[1]
BLUE, ORANGE, TEAL, INK = "#2166ac", "#c96520", "#16847b", "#283544"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def near(a, b, description):
    if not math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-14):
        raise ValueError(f"{description}: {a} differs from archived {b}")


class Packet:
    def __init__(self, folder):
        self.folder = folder
        self.inputs = {}
        self.provenance = json.loads(self.read("provenance.json"))
        raw = self.read("summary.json")
        if sha(raw) != self.provenance["result_sha256"]["summary.json"]:
            raise ValueError("summary does not match simulation provenance")
        self.summary = json.loads(raw)
        if self.summary["profile"] != "paper-global-v2":
            raise ValueError("unsupported simulation profile")

    def read(self, relative):
        raw = (self.folder / relative).read_bytes()
        self.inputs[str(relative)] = sha(raw)
        return raw

    def cells(self, name, stage):
        key = f"{name}/{stage}.csv"
        archive = Path("snapshots") / f"{key}.gz"
        raw = gzip.decompress(self.read(archive)) if (self.folder / archive).exists() else self.read(key)
        if sha(raw) != self.provenance["result_sha256"][key]:
            raise ValueError(f"snapshot hash mismatch: {key}")
        rows = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(io.StringIO(raw.decode()))]
        expected = self.summary["runs"][name]["n"] ** 2
        ids = [r["id"] for r in rows]
        if len(rows) != expected or len(set(ids)) != expected or sorted(ids) != list(range(expected)):
            raise ValueError(f"incorrect cell IDs/count: {key}")
        if any(not math.isfinite(v) for r in rows for v in r.values()):
            raise ValueError(f"nonfinite snapshot: {key}")
        rows.sort(key=lambda r: r["id"])
        time = 0 if stage == "initial" else self.summary["runs"][name]["time"]
        for row in rows:
            near(row["time"], time, f"snapshot time: {key}")
        return rows


def order(y):
    return [math.log2(a / b) for a, b in zip(y, y[1:])]


def log_axes(ax, ticks, labels):
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xticks(ticks, labels)
    ax.grid(True, which="major", color="#d9dee5", linewidth=.7)
    ax.spines[["top", "right"]].set_visible(False)


def guide(ax, x, y, power, label):
    # Visually offset slope guide, anchored to the finest measured point;
    # its coefficient is arbitrary and it is never fitted to the data.
    anchor = int(np.argmin(x)) if power > 0 else int(np.argmax(x))
    values = .55 * y[anchor] * (np.array(x) / x[anchor]) ** power
    ax.plot(x, values, ":", color="#78838e", linewidth=1.3, label=label)


def map_points(ax, cells, values, bound, title):
    n = math.sqrt(len(cells))
    points = ax.scatter([c["x"] for c in cells], [c["y"] for c in cells], c=values,
                        s=(128/n)**2, cmap="RdBu_r", vmin=-bound, vmax=bound,
                        linewidths=.25, edgecolors="#59616a")
    ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="x", ylabel="y", title=title)
    ax.set_aspect("equal")
    return points


def colorbar(fig, points, axes, label):
    bar = fig.colorbar(points, ax=axes, shrink=.85, pad=.025)
    bar.set_label(label)
    fmt = ScalarFormatter(useMathText=True)
    fmt.set_powerlimits((-2, 2))
    bar.formatter = fmt
    bar.update_ticks()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=ROOT / "tests/reference/vector_potential")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/images/vector_potential")
    args = parser.parse_args()
    packet = Packet(args.input_dir.resolve())
    summary = packet.summary
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.labelcolor": INK, "text.color": INK,
                         "axes.titleweight": "semibold", "axes.titlesize": 11,
                         "legend.fontsize": 9, "figure.facecolor": "white"})
    images, measurements = {}, {}

    def save(fig, filename, title, note):
        fig.suptitle(title, fontsize=14, fontweight="semibold")
        fig.supxlabel(note, fontsize=9, color="#52606e")
        path = output / filename
        fig.savefig(path, dpi=180, metadata={"Software": f"Matplotlib {matplotlib.__version__}",
                    "Description": "OpenMHD-RS issue #6; simulation " + packet.provenance["revision"]})
        plt.close(fig)
        images[filename] = sha(path.read_bytes())

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4), layout="constrained")
    curl_orders = {}
    for ax, norm in zip(axes, ("L1", "L2")):
        for jitter, color, marker in ((0., BLUE, "o"), (.15, ORANGE, "s")):
            rows = sorted((r for r in summary["curl"] if r["jitter"] == jitter), key=lambda r: r["n"])
            x, y = [r["n"] for r in rows], [r[norm] for r in rows]
            ax.plot(x, y, marker=marker, color=color, linewidth=1.8, markersize=6,
                    label="Regular mesh" if jitter == 0 else "Jitter = 0.15")
            curl_orders[f"jitter={jitter}/{norm}"] = order(y)
            if jitter == 0:
                guide(ax, x, y, -2, r"$N^{-2}$ slope guide")
        log_axes(ax, [8, 16, 32], ["8", "16", "32"])
        ax.set(xlabel=r"Resolution $N$ ($N\times N$ cells)", ylabel=f"Volume-weighted vector {norm} error",
               title=f"Initial discrete curl: {norm}")
        ax.legend()
    measurements["curl_orders"] = curl_orders
    save(fig, "curl_convergence.png", "Three-component curl convergence",
         "Analytic curl reference at t = 0  •  periodic unit square  •  dotted lines are slope guides, not fits")

    initial = packet.cells("gauge_jitter", "initial")
    final = packet.cells("gauge_jitter", "final")
    for a, b in zip(initial, final):
        for key in ("x", "y"):
            near(a[key], b[key], "fixed gauge mesh position")
    b0 = [c["bz"] for c in initial]
    delta_b = [b["bz"]-a["bz"] for a, b in zip(initial, final)]
    b0_vector_max = max(math.sqrt(sum(c[k]**2 for k in ("bx", "by", "bz"))) for c in initial)
    change_vector_max = max(math.sqrt(sum((b[k]-a[k])**2 for k in ("bx", "by", "bz"))) for a, b in zip(initial, final))
    near(b0_vector_max, summary["irregular_gauge"]["initial_B_max"], "initial gauge magnetic norm")
    near(change_vector_max, summary["irregular_gauge"]["B_change_max"], "gauge magnetic change")
    fig, axes = plt.subplots(2, 2, figsize=(11, 8.6), layout="constrained")
    ax = axes[0, 0]
    gauge_orders = {}
    for key, color, label in (("A_L2", BLUE, r"$A_x$"), ("phi_L2", TEAL, r"$\phi$")):
        for limited, style, marker in ((True, "-", "o"), (False, "--", "s")):
            rows = sorted((r for r in summary["gauge"] if r["limited"] == limited), key=lambda r: -r["dt"])
            x, y = [r["dt"] for r in rows], [r[key] for r in rows]
            ax.plot(x, y, linestyle=style, marker=marker, color=color,
                    markerfacecolor=color if limited else "none", markersize=5 if limited else 8,
                    label=label + (", limited" if limited else ", unlimited"))
            gauge_orders[f"{key}/limited={limited}"] = order(y)
            if key == "A_L2" and limited:
                guide(ax, x, y, 1, r"$\Delta t$ slope guide")
    log_axes(ax, [.00025, .0005, .001], ["0.00025", "0.0005", "0.001"])
    ax.set(xlabel="Timestep cap", ylabel="Volume-weighted L2 error",
           title="Regular N16: exact same-grid mode, t = 0.05")
    ax.legend(loc="lower right", fontsize=8)
    ax = axes[0, 1]
    for cells, color, marker, label in ((initial, "#89939e", "o", "Initial: t = 0"),
                                       (final, BLUE, "+", "Final: t = 0.05")):
        ax.scatter([c["x"] for c in cells], [c["ax"] for c in cells], s=17,
                   c=color, marker=marker, linewidths=.7, label=label)
    ax.set(xlabel="x", ylabel=r"$A_x$", title="Jittered N16: gauge component snapshots")
    ax.ticklabel_format(axis="y", style="sci", scilimits=(-2, 2), useMathText=True)
    ax.grid(alpha=.2)
    ax.legend()
    for ax, values, title in ((axes[1, 0], b0, r"Jittered mesh: initial discrete $B_z$"),
                               (axes[1, 1], delta_b, r"Jittered mesh: $B_z(0.05)-B_z(0)$")):
        points = map_points(ax, initial, values, max(map(abs, values)), title)
        colorbar(fig, points, ax, r"$B_z$" if ax is axes[1, 0] else r"$\Delta B_z$")
    measurements["gauge_orders"] = gauge_orders
    measurements["gauge_initial_B_max"] = b0_vector_max
    measurements["gauge_B_change_max"] = change_vector_max
    save(fig, "gauge_cleaning.png", "Gauge cleaning: first-order error and irregular-mesh magnetic response",
         "Bottom panels: centroid samples, separate colour scales, no interpolation  •  B change is from the coupled run")

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4), layout="constrained")
    deform_orders = {}
    for ax, key, title, ylabel, power in zip(axes, ("physical_max", "step_GCL_max"),
            ("Accumulated physical-state error", "Single-step geometric-conservation residual"),
            (r"Max absolute error over $\rho,p,\mathbf{v},\mathbf{B}$", r"Max $|V_1-V_0-\frac{\Delta t}{2}(\dot V_0+\dot V_1)|/V_0$"), (2, 3)):
        for limited, color, marker in ((True, BLUE, "o"), (False, ORANGE, "s")):
            rows = sorted((r for r in summary["deform"] if r["limited"] == limited), key=lambda r: -r["dt"])
            x, y = [r["dt"] for r in rows], [r[key] for r in rows]
            ax.plot(x, y, color=color, marker=marker, linestyle="-" if limited else "--",
                    markersize=5 if limited else 8, markerfacecolor=color if limited else "none",
                    label="Limited reconstruction" if limited else "Unlimited reconstruction")
            deform_orders[f"{key}/limited={limited}"] = order(y)
            if limited:
                guide(ax, x, y, power, rf"$\Delta t^{power}$ slope guide")
        log_axes(ax, [.001, .002, .004], ["0.001", "0.002", "0.004"])
        ax.set(xlabel="Timestep cap", ylabel=ylabel, title=title)
        ax.legend(fontsize=8)
    measurements["deform_orders"] = deform_orders
    save(fig, "deforming_convergence.png", "Deforming Voronoi mesh: temporal refinement",
         "N6, t = 0.04  •  prescribed nonuniform generator motion  •  geometric residual is per step, not accumulated")

    baseline = packet.cells("mean_smooth", "final")
    boosted = packet.cells("mean_boost", "final")
    run = summary["runs"]["mean_boost"]
    physical_time = run["time"]
    near(physical_time, summary["runs"]["mean_smooth"]["time"], "matched boost time")
    for a, b in zip(baseline, boosted):
        for k, key in enumerate(("x", "y")):
            residual = (b[key] - run["boost"][k]*physical_time - a[key] + .5) % 1 - .5
            near(residual, 0., "boosted coordinates after periodic translation")
        near(a["volume"], b["volume"], "paired cell volumes")
    bz_a, bz_b = [c["bz"] for c in baseline], [c["bz"] for c in boosted]
    delta = [b-a for a, b in zip(bz_a, bz_b)]
    maximum = max(map(abs, delta))
    near(maximum, summary["nonuniform_mean_boost_observation"]["max_errors"]["bz"], "mean-field boost residual")
    measurements["mean_boost_Bz_max"] = maximum
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5), layout="constrained")
    common_min, common_max = min(bz_a+bz_b), max(bz_a+bz_b)
    for ax, values, title in zip(axes[:2], (bz_a, bz_b), ("Baseline: fixed mesh", "Boosted: translation removed")):
        # Display both physical fields at the matched baseline centroids.
        points = ax.scatter([c["x"] for c in baseline], [c["y"] for c in baseline], c=values,
                            s=256, cmap="viridis", vmin=common_min, vmax=common_max,
                            linewidths=.3, edgecolors="#59616a")
        ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="x (baseline frame)", ylabel="y", title=title)
        ax.set_aspect("equal")
    colorbar(fig, points, list(axes[:2]), r"$B_z$ (shared scale)")
    residual = map_points(axes[2], baseline, delta, maximum, rf"Boosted $-$ baseline; max = {maximum:.2e}")
    axes[2].set_xlabel("x (baseline frame)")
    colorbar(fig, residual, axes[2], r"$\Delta B_z$")
    save(fig, "mean_field_boost.png", "Observed mean-field boost discrepancy — not a passed invariance test",
         "N8, jitter 0.15, t = 0.02  •  mean B = (0.3, 0.2, 0.1), boost = (2, −1, 0)  •  centroid samples, no interpolation")

    # Provenance describes plotting only; the original simulation packet is immutable.
    script = Path(__file__).resolve()
    provenance = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "simulation_revision": packet.provenance["revision"],
        "simulation_run_utc": packet.provenance["created_utc"],
        "profile": summary["profile"], "new_simulations_run": False,
        "plot_script": {"path": str(script.relative_to(ROOT)), "sha256": sha(script.read_bytes())},
        "plot_command": [sys.executable, *sys.argv],
        "input_directory": str(packet.folder), "input_sha256": packet.inputs,
        "environment": {"python": sys.version, "matplotlib": matplotlib.__version__,
                        "numpy": np.__version__, "pillow": PIL.__version__, "platform": platform.platform()},
        "display_checks": measurements, "image_sha256": images,
        "notes": "Plots use archived measurements. Slope guides are not fits. Spatial maps show centroid samples without interpolation. Boosted cells match by persistent ID after removing b*t modulo the unit box. The nonzero-mean boost residual is an observed limitation, not a passed gate.",
    }
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2, allow_nan=False) + "\n")
    print(f"Wrote {len(images)} checked figures and plot provenance to {output}")


if __name__ == "__main__":
    main()
