#!/usr/bin/env python3
"""Optional matplotlib plots of archived coupled runs, not a validation oracle."""
import argparse
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    with path.open() as stream:
        return [{k: float(v) for k, v in row.items()} for row in csv.DictReader(stream)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=ROOT / "results/coupled_2d")
    args = parser.parse_args()
    folder = args.input_dir
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), layout="constrained")
    reference = [r for r in read(folder / "brio_reference_2048.csv") if .5 < r["x"] < 1.5]
    for ax, key, label in zip(axes.flat, ("rho", "vx", "p", "by"),
                              ("Density", "Velocity x", "Gas pressure", "Magnetic By")):
        ax.plot([r["x"] - 1 for r in reference], [r[key] for r in reference],
                color="black", linewidth=1.1, label="1D induction, N=2048")
        for n, color in ((32, "#e09a26"), (64, "#377eb8"), (128, "#c13852")):
            cells = [r for r in read(folder / f"brio-wu_{n}.csv")[:n] if .5 < r["x"] < 1.5]
            ax.plot([r["x"] - 1 for r in cells], [r[key] for r in cells], ".-",
                    color=color, markersize=3, linewidth=.8, label=f"2D Az, nx={n}")
        ax.set(xlabel="x − interface", ylabel=label)
        ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Brio–Wu periodic adaptation, t=0.1\nShared Riemann kernel; separate induction and Az evolution")
    fig.savefig(folder / "brio_comparison.png", dpi=170)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(12, 4), layout="constrained")
    for ax, n in zip(axes, (12, 24, 48)):
        cells = read(folder / f"orszag-tang_{n}.csv")
        field = [[cells[i + n*j]["rho"] for i in range(n)] for j in range(n)]
        image = ax.imshow(field, origin="lower", extent=[0, 1, 0, 1], cmap="viridis",
                          vmin=.14, vmax=.4, interpolation="nearest")
        ax.set(title=f"N={n}", xlabel="x", ylabel="y")
    fig.colorbar(image, ax=list(axes), label="Density")
    fig.suptitle("Orszag–Tang density at t=0.1 — experimental planar reference\nStability/resolution inspection; no published-profile equivalence claim")
    fig.savefig(folder / "vortex_density.png", dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    main()
