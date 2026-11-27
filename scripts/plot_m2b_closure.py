"""Plot the zero-mean irregular-mesh ladders from the independent v2 reduction."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


def render(report, output):
    cases = {
        (r["family"], r["fit"]): r for r in report["ladders"]
        if r["field"] == "original" and r["mean"] == "zero"
    }
    families = (("original", "Original jitter"), ("fresh-a", "New jitter A"), ("fresh-b", "New jitter B"))
    series = (
        ("linear", "arithmetic_rms", "Raw linear · arithmetic", "#807b79", "--", "x"),
        ("quadratic", "arithmetic_rms", "Quadratic · arithmetic", "#126489", "-", "o"),
        ("quadratic", "skew_rms", "Quadratic · face centroid", "#126489", "--", "o"),
        ("corrected", "arithmetic_rms", "Corrected · arithmetic", "#ac4e22", "-", "D"),
        ("corrected", "skew_rms", "Corrected · face centroid", "#ac4e22", "--", "D"),
    )
    fig, axes = plt.subplots(1, 3, figsize=(10.3, 4.8), sharey=True)
    fig.subplots_adjust(left=.08, right=.98, top=.77, bottom=.30, wspace=.16)
    fig.text(.08, .94, "Magnetic divergence on irregular 3D meshes",
             ha="left", fontsize=17, weight="semibold", color="#172e40")
    fig.text(.08, .87, "Three independent jitter keys · periodic Fourier field · zero imposed mean",
             fontsize=10, color="#50667a")
    for ax, (family, title) in zip(axes, families):
        for fit, metric, _, color, style, marker in series:
            y = cases[family, fit][metric]
            ax.plot(range(3), y, color=color, ls=style, marker=marker, ms=5, lw=1.6,
                    markerfacecolor="white" if style == "--" else color)
        ax.set_title(title, fontsize=11, loc="left")
        ax.set_xticks(range(3), ["8³", "16³", "32³"])
        ax.set_xlabel("Cells")
        ax.set_ylim(bottom=0)
        ax.spines[["right", "top"]].set_visible(False)
        ax.grid(axis="y", linewidth=.55, color="#d8dfe4")
    axes[0].set_ylabel(r"Volume-weighted RMS of $\nabla\!\cdot B$")
    handles = [
        Line2D([], [], color=color, linestyle=style, marker=marker, markersize=5, label=label,
               markerfacecolor="white" if style == "--" else color)
        for _, _, label, color, style, marker in series
    ]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(.5,.026), ncol=3,
               frameon=False, fontsize=8.6, handlelength=2.3, columnspacing=1.5)
    fig.savefig(output, dpi=165, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    render(json.loads(args.summary.read_bytes()), args.output)
