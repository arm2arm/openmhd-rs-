"""Plot measured end-to-end speedups from the published REANA M3 evidence."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter


COLORS = ("#007a77", "#bd5b24", "#655bae")
CASES = (("rigid-mesh", "Regular 3D mesh"), ("jitter-mesh", "Jittered 3D mesh"),
         ("alfven", "2.5D Alfvén wave"), ("kdk", "Direct gravity · 256 particles"))


def local_panel(ax, data, baseline, large):
    series = [
        (data[baseline], "geometry", "64-cell 3D mesh"),
        (data[baseline], "gravity", "256 particles"),
        (data[large], "gravity", "2,048 particles"),
    ]
    for (group, kind, label), color, marker in zip(series, COLORS, ("o", "s", "^")):
        rows = {r["case"]["threads"]: r["median_seconds"] for r in group["rows"] if r["case"]["kind"] == kind}
        if group["errors"] or sorted(rows) != [1, 2, 4, 8, 16]:
            raise ValueError("incomplete local scaling series for " + label)
        counts = sorted(rows)
        ax.plot(counts, [rows[1] / rows[n] for n in counts], label=label,
                color=color, marker=marker, lw=2.2, markersize=6)
    ax.set_xscale("log", base=2)
    ax.set_xticks([1, 2, 4, 8, 16])
    ax.xaxis.set_major_formatter(ScalarFormatter())
    ax.set_xlabel("Rayon threads")
    ax.set_ylabel("Speedup over one thread")
    ax.axhline(1, color="#536675", lw=0.9, ls="--", zorder=0)
    ax.set_ylim(bottom=0)
    ax.grid(axis="y")
    ax.legend(loc="upper left")


def rank_panel(ax, group):
    if group["errors"]:
        raise ValueError("incomplete MPI scaling series")
    layouts = ((1, 4), (2, 2), (4, 1))
    positions = list(range(len(CASES)))
    for k, ((ranks, threads), color) in enumerate(zip(layouts, COLORS)):
        speedup = []
        for key, _ in CASES:
            cases = group["comparisons"]["strong-" + key]["cases"]
            times = {(r["ranks"], r["threads"]): r["seconds"] for r in cases if not r["reference"] and not r["reverse"]}
            speedup.append(times[1, 1] / times[ranks, threads])
        ax.barh([p + (k-1)*0.23 for p in positions], speedup, height=0.20,
                color=color, label=f"{ranks} × {threads}", zorder=2)
    ax.set_yticks(positions, [label for _, label in CASES])
    ax.set_ylim(len(CASES)-0.50, -0.55)
    ax.set_xlabel("Speedup over 1 rank × 1 thread")
    ax.axvline(1, color="#536675", lw=1, ls="--", zorder=4)
    ax.grid(axis="x")
    ax.legend(ncols=3, loc="lower left", bbox_to_anchor=(0.0, 1.0),
              handlelength=0.9, columnspacing=1.1, borderaxespad=0.0)


def weak_scaling(group, output):
    figures = (("rigid-mesh", "3D Voronoi mesh"), ("alfven", "2.5D Alfvén wave"), ("kdk", "Direct gravity"))
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.9))
    fig.subplots_adjust(left=.075, right=.975, bottom=.23, top=.73, wspace=.30)
    for ax, (key, title), color in zip(axes, figures, COLORS):
        rows = sorted(group["comparisons"]["weak-" + key]["cases"], key=lambda row: row["ranks"])
        if [r["ranks"] for r in rows] != [1, 2, 4] or any(r["threads"] != 1 for r in rows):
            raise ValueError("missing weak scaling layout for " + title)
        ranks = [row["ranks"] for row in rows]
        seconds = [row["seconds"] for row in rows]
        labels = []
        for row in rows:
            size = row["problem_size"]
            if key == "kdk":
                population = f'{size["n"]} particles'
            else:
                cells = size["n"] * (size["ny"] if key == "alfven" else size["n"] * size["nz"])
                population = f"{cells} cells"
            labels.append(f'{row["ranks"]}\n{population}')
        ax.axhline(seconds[0], ls="--", lw=1, color="#707d86")
        ax.plot(ranks, seconds, color=color, marker="o", lw=2.2, markersize=6)
        for rank, value in zip(ranks, seconds):
            ax.annotate(f"{value:.2f}", (rank, value), xytext=(0, 7),
                        textcoords="offset points", ha="center", color=color)
        ax.set_xscale("log", base=2)
        ax.set_xticks(ranks, labels)
        ax.set_xlim(.86, 4.65)
        ax.set_ylim(0, max(seconds) * 1.35)
        ax.set_title(title, loc="left", fontsize=13, weight="bold", pad=10)
        ax.set_xlabel("MPI ranks", labelpad=8)
        ax.grid(axis="y")
    axes[0].set_ylabel("Elapsed seconds")
    fig.suptitle("MPI weak scaling on REANA", x=.075, y=.96, ha="left", fontsize=18, weight="bold")
    fig.savefig(output, dpi=190, bbox_inches="tight", pad_inches=.18, facecolor="white")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--weak-output", type=Path, help="also plot wall time for the three weak-scaling series")
    parser.add_argument("--local", default="cases-bc82f7421f")
    parser.add_argument("--large", default="large-kdk-512c762ebb-131cbfc7")
    parser.add_argument("--hybrid", default="hybrid-26750efba-26750efba")
    args = parser.parse_args()
    local = json.loads((args.evidence / "rayon-measurements.json").read_bytes())
    hybrid = json.loads((args.evidence / "hybrid-measurements.json").read_bytes())
    plt.rcParams.update({
        "font.family":"DejaVu Sans", "font.size":10, "text.color":"#203444",
        "axes.labelcolor":"#203444", "axes.edgecolor":"#a1acaf", "axes.spines.top":False,
        "axes.spines.right":False, "axes.grid":False, "axes.axisbelow":True,
        "grid.color":"#dfe6e7", "grid.linewidth":0.7, "legend.frameon":False,
        "xtick.color":"#3d5262", "ytick.color":"#3d5262",
    })
    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.8))
    fig.subplots_adjust(left=.076, bottom=.17, right=.975, wspace=.63, top=.77)
    local_panel(left, local, args.local, args.large)
    rank_panel(right, hybrid[args.hybrid])
    left.set_title("Rayon strong scaling", loc="left", pad=28, weight="bold", fontsize=14)
    right.set_title("Four CPU slots · ranks × threads", loc="left", pad=28, weight="bold", fontsize=14)
    fig.suptitle("OpenMHD-RS parallel scaling on REANA", x=.075, y=.975, ha="left", fontsize=18, weight="bold")
    fig.savefig(args.output, dpi=190, bbox_inches="tight", pad_inches=.18, facecolor="white")
    plt.close(fig)
    if args.weak_output is not None:
        weak_scaling(hybrid[args.hybrid], args.weak_output)


if __name__ == "__main__":
    main()
