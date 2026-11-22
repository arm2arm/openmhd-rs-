#!/usr/bin/env python3
"""Plot outputs of run_kinematic_2d.py. Optional dependency: matplotlib 3.9.4."""

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def cells(path):
    with path.open() as stream:
        rows = list(csv.DictReader(line for line in stream if not line.startswith("#")))
    n = int(len(rows) ** 0.5)
    if n * n != len(rows):
        raise ValueError(f"{path}: expected a square cell grid")
    energy = [0.5 * (float(row["bx"]) ** 2 + float(row["by"]) ** 2) for row in rows]
    return [energy[j*n:(j+1)*n] for j in range(n)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, nargs="?", default=Path("results/kinematic_2d"))
    args = parser.parse_args()
    maps = [cells(args.directory / name) for name in
            ("loop_initial.csv", "loop_fixed.csv", "loop_comoving.csv")]
    maximum = max(max(row) for row in maps[0])
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.8), layout="constrained")
    for axis, data, title in zip(axes, maps,
                                 ("Initial", "Fixed grid: t = 1", "Comoving grid: t = 1")):
        image = axis.imshow(data, origin="lower", extent=(0, 1, 0, 1), cmap="magma",
                            vmin=0, vmax=maximum, interpolation="nearest")
        axis.set(title=title, xlabel="x", ylabel="y", aspect="equal")
    fig.colorbar(image, ax=axes, label="Magnetic energy density |B|²/2", shrink=0.85)
    fig.suptitle("Prescribed 2D field-loop transport, 64 × 64 cells, v = (2, 1)\n"
                 "Kinematic Cartesian test; no fluid-force feedback", fontsize=12)
    fig.savefig(args.directory / "loop_comparison.png", dpi=160)
    plt.close(fig)

    with (args.directory / "convergence.csv").open() as stream:
        rows = [row for row in csv.DictReader(stream) if row["case"] == "smooth"]
    n = [int(row["n"]) for row in rows]
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.8), layout="constrained")
    for axis, field, title in zip(axes, ("az_l1", "b_l1"), ("Vector potential Az", "Magnetic field B")):
        error = [float(row[field]) for row in rows]
        axis.loglog(n, error, "o-", label="Measured L1 error")
        axis.loglog(n, [error[-1] * (n[-1]/value)**2 for value in n], "--", color="0.5", label="N⁻²")
        axis.set(title=title, xlabel="Cells per side N", ylabel="Absolute L1 error")
        axis.set_xticks(n, labels=[str(value) for value in n])
        axis.tick_params(axis="x", which="minor", labelbottom=False)
        axis.grid(True, which="both", alpha=0.2)
        axis.legend(fontsize=8)
    fig.suptitle("Smooth kinematic transport, fixed Cartesian grid, t = 1", fontsize=12)
    fig.savefig(args.directory / "smooth_convergence.png", dpi=160)
    plt.close(fig)
    print(args.directory / "loop_comparison.png")
    print(args.directory / "smooth_convergence.png")


if __name__ == "__main__":
    main()
