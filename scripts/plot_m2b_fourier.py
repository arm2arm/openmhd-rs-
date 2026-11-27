"""Plot the measured Fourier field and mesh-refinement errors from an M2b output packet."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.ticker import ScalarFormatter
import numpy as np


INK = "#172e40"
SECONDARY = "#50667a"
MESH_COLORS = {"regular": "#1e5c87", "jitter": "#b94d25"}


def plot_field(path, case, destination):
    if hashlib.sha256(path.read_bytes()).hexdigest() != case["fields_sha256"]:
        raise ValueError("The supplied fields do not match the jitter-32-zero workflow")
    with np.load(path, allow_pickle=False) as fields:
        axis_indices = [3, 9, 16, 22, 28]
        chosen = np.ix_(axis_indices, axis_indices, axis_indices)
        positions = fields["centroids"].reshape(32, 32, 32, 3)[chosen].reshape(-1, 3)
        vectors = fields["quadratic"][:, :3].reshape(32, 32, 32, 3)[chosen].reshape(-1, 3)

    fig = plt.figure(figsize=(8.2, 6.5), facecolor="white")
    ax = fig.add_axes([0.04, 0.09, 0.77, 0.75], projection="3d", proj_type="ortho")
    ax.view_init(21, -53)
    ax.set_box_aspect((1, 1, 1))
    for name, axis in (("x", ax.xaxis), ("y", ax.yaxis), ("z", ax.zaxis)):
        axis.pane.set_facecolor((0.96, 0.97, 0.98, 0.6))
        axis._axinfo["grid"].update(color="#dae1e7", linewidth=0.6)
        getattr(ax, f"set_{name}lim")(0, 1)
        getattr(ax, f"set_{name}ticks")([0, 0.5, 1])
        getattr(ax, f"set_{name}label")(name, labelpad=3)
    ax.set_yticklabels(["", "0.5", "1.0"])

    scale = TwoSlopeNorm(vmin=-13, vcenter=0, vmax=13)
    palette = LinearSegmentedColormap.from_list(
        "signed_component", ["#214c9e", "#4f8dcc", "#73808b", "#e38b55", "#af292d"]
    )
    for position, direction, color in zip(positions, vectors, palette(scale(vectors[:, 2]))):
        ax.quiver(*position, *direction, length=0.073, pivot="middle", normalize=True,
                  color=color, linewidth=1.5, arrow_length_ratio=0.30)
    fig.text(0.075, 0.933, "Magnetic field on a jittered 3D Voronoi mesh", fontsize=18, weight="semibold", color=INK)
    fig.text(0.075, 0.879, "Periodic Fourier field recovered from its vector potential", fontsize=11, color=SECONDARY)
    cax = fig.add_axes([0.83, 0.27, 0.022, 0.37])
    fig.colorbar(plt.cm.ScalarMappable(norm=scale, cmap=palette), cax=cax, label=r"Recovered $B_z$")
    fig.text(0.075, 0.045, "125 sampled directions from 32,768 static cells. Arrow lengths are normalized.",
             fontsize=9, color=SECONDARY)
    fig.savefig(destination, dpi=175)
    plt.close(fig)


def plot_convergence(ladders, destination):
    fig, axes = plt.subplots(1, 3, figsize=(11.8, 4.8))
    fig.subplots_adjust(left=0.074, right=0.975, bottom=0.19, top=0.67, wspace=0.38)
    fig.suptitle("Convergence of the static 3D operators", x=0.07, y=0.96, ha="left",
                 fontsize=18, weight="semibold", color=INK)
    fig.text(0.07, 0.837, "Periodic Fourier field  ·  zero imposed mean", fontsize=11, color=SECONDARY)
    resolutions = [8, 16, 32]
    for ax in axes:
        ax.set_xscale("log", base=2)
        ax.set_xticks(resolutions)
        ax.xaxis.set_major_formatter(ScalarFormatter())
        ax.set_xlim(7, 37)
        ax.set_xlabel("Generators per axis, N")
        ax.grid(axis="y", alpha=0.23)
        ax.spines[["top", "right"]].set_visible(False)

    accuracy = axes[0]
    accuracy.set_yscale("log")
    accuracy.set_title("Quadratic curl accuracy", loc="left", fontsize=11)
    accuracy.set_ylabel("Volume-weighted relative error")
    for ax, mesh, name in zip(axes[1:], ("regular", "jitter"), ("Regular", "15% jitter")):
        subset = {row["fit"]: row for row in ladders if row["mesh"] == mesh and row["mean_b"] == [0.0, 0.0, 0.0]}
        curve = subset["quadratic"]
        color = MESH_COLORS[mesh]
        accuracy.plot(resolutions, curve["normalized_l1"], marker="o", color=color,
                      label=f"{name}, p = {curve['order']:.2f}")
        scale = 1e14 if mesh == "regular" else 1.0
        for fit, marker, style in (("quadratic", "o", "-"), ("linear", "s", "--")):
            ax.plot(resolutions, np.asarray(subset[fit]["face_mean_rms"]) * scale,
                    marker=marker, ls=style, color=color, mfc=color if fit == "quadratic" else "white",
                    label=fit.capitalize())
        ax.set_ylim(bottom=0)
        ax.set_title(f"{name} mesh divergence", loc="left", fontsize=11)
        ax.set_ylabel(r"Face-mean RMS ($10^{-14}$)" if mesh == "regular" else "Face-mean RMS")
    for ax in axes:
        ax.legend(frameon=False, fontsize=8.5)
    fig.savefig(destination, dpi=175)
    plt.close(fig)


def main(summary_path, field_path, destination):
    report = json.loads(summary_path.read_bytes())["o02"]
    case = next(row for row in report["cases"] if row["case"] == "jitter-32-zero")
    destination.mkdir(exist_ok=True, parents=True)
    plot_field(field_path, case, destination / "fourier_field.png")
    plot_convergence(report["ladders"], destination / "fourier_convergence.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ("summary", "fields", "destination"):
        parser.add_argument(argument, type=Path)
    args = parser.parse_args()
    main(args.summary, args.fields, args.destination)
