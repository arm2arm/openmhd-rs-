"""Plot the oblique S-CENTROID fixture and its measured REANA refinement curves."""
import argparse
from itertools import product
import json
from pathlib import Path
import tarfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from review_m2c_centroid import START, VEL


def render(packet, summary, output):
    blue, orange, ink = "#096a83", "#bd4c25", "#203845"
    with tarfile.open(packet) as archive:
        raw = archive.extractfile("cases/xyz-h32/stdout.txt").read().decode()
    centroids, speeds = {}, {}
    for line in raw.splitlines():
        if "M2C " not in line:
            continue
        fields = line.split("M2C ", 1)[1].split()
        if fields[0] in ("rate", "sample") and fields[2] == "0":
            values = speeds if fields[0] == "rate" else centroids
            values[int(fields[1])] = [float(v) for v in fields[4:]]
    fig = plt.figure(figsize=(10.3, 4.7))
    fig.subplots_adjust(left=.04, right=.976, top=.80, bottom=.18, wspace=.18)
    fig.text(.055, .942, "How fast does a Voronoi cell move?", fontsize=18,
             fontweight="semibold", color=ink)
    fig.text(.055, .882, "Prescribed generator velocities in a unit cube",
             fontsize=10.5, color="#49616d")
    mesh = fig.add_subplot(121, projection="3d", proj_type="ortho")
    for p in product((0, 1), repeat=3):
        for k in range(3):
            if p[k] == 0:
                q = list(p)
                q[k] = 1
                mesh.plot(*zip(p, q), color="#9aabb2", lw=.8)
    corners = [(0.5 - .25*(y-.5) - .5*(z-.5), y, z)
               for y, z in ((0,0), (1,0), (1,1), (0,1))]
    mesh.add_collection3d(Poly3DCollection([corners], facecolors="#9bcbd0",
                          edgecolors="#417d88", linewidths=1.05, alpha=.3))
    for i in range(2):
        for pos, vel, color, mark in [(list(map(float, START[i])), list(map(float, VEL[i])), blue, "o"),
                                       (centroids[i], speeds[i], orange, "D")]:
            mesh.scatter(*pos, c=color, marker=mark, s=27, depthshade=False)
            mesh.quiver(*pos, *vel, color=color, length=1.6, linewidth=1.85, arrow_length_ratio=.25)
    mesh.set_box_aspect((1, 1, 1), zoom=1.16)
    mesh.set_axis_off()
    mesh.view_init(elev=21, azim=-63)
    mesh.set_title("Generators and cell centroids", fontsize=11, color=ink)
    items = [Line2D([], [], color=c, marker=m, lw=1.5, label=l) for c, m, l in
             ((blue, "o", "Generator velocity"), (orange, "D", "Centroid velocity"))]
    mesh.legend(handles=items, loc="upper center", bbox_to_anchor=(.5, -.005),
                ncol=2, fontsize=8.5, handlelength=1.25, frameon=False)
    ax = fig.add_subplot(122)
    axes = summary["axis_ladders"]
    levels = axes["xyz"]
    x = [r["denominator"] for r in levels]
    for key, color, label, marker in [("volume_error", blue, "Volume derivative", "o"),
                                      ("centroid_error", orange, "Centroid velocity", "D")]:
        y = [max(series[i][key] for series in axes.values()) for i in range(len(x))]
        ax.plot(range(len(x)), y, color=color, marker=marker, lw=1.8, ms=5, label=label)
    ax.set_yscale("log")
    ax.set_xticks(range(len(x)), [f"1/{d}" for d in x], rotation=27, ha="right")
    ax.set_xlabel("Half-width of central difference, h", fontsize=9)
    ax.set_ylabel("Maximum absolute error (code units)", fontsize=9)
    ax.set_title("Worst error across six axis permutations", fontsize=11, color=ink)
    ax.legend(fontsize=8.5, frameon=False)
    for spine in ("right", "top"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(labelsize=8.5)
    ax.grid(axis="y", which="major", color="#d7e2e6", lw=.65)
    fig.text(.055, .027, "Arrows share one velocity scale. The shaded polygon is the shared face at the measurement time.",
             fontsize=8.4, color="#526975")
    fig.savefig(output, dpi=168, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("packet", "summary", "output"):
        p.add_argument(name, type=Path)
    args = p.parse_args()
    render(args.packet, json.loads(args.summary.read_bytes()), args.output)
