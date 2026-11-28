"""Plot the measured 3D helix and fixed-mesh-size timestep refinement."""
import argparse
import gzip
import json
import tarfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA = Path(__file__).resolve().parents[1] / "docs/galaxy/results/m2c_smooth_step"


def plot(output, packet, summary):
    measured = json.loads(summary.read_bytes())
    fig, (field, time) = plt.subplots(1, 2, figsize=(9, 4.1), layout="constrained")
    with tarfile.open(packet, "r:gz") as archive:
        for n, color, marker in [(3, "#1b7181", "o"), (4, "#b65629", "^")]:
            key = f"advection-deforming-n{n}-s16-b0-t2/stdout.gz"
            lines = gzip.decompress(archive.extractfile(key).read()).decode("ascii").splitlines()
            rows = [list(map(float, line.split()[1:])) for line in lines if line.startswith("FINAL ")]
            analytic = [v for row in rows for v in row[24:27]]
            computed = [v for row in rows for v in row[14:17]]
            field.scatter(analytic, computed, s=17, color=color, marker=marker,
                          alpha=.68, linewidths=0, label=f"{n**3} cells")
    field.plot([-.04, .04], [-.04, .04], "--", lw=1, color="#555f65",
               label="Exact agreement", zorder=0)
    field.set(xlabel="Analytic cell-average B component", ylabel="Computed B component",
              title="Advected magnetic helix", aspect="equal")
    field.legend(frameon=False, fontsize=8, loc="upper left")
    differences = measured["field_step_halving_rms"]
    steps = sorted(map(int, differences))
    rms = [differences[str(n)] for n in steps]
    time.loglog(steps, rms, "o-", color="#1b7181", lw=1.8, label="Measured, 27 cells")
    reference = [1.8*rms[-1]*(steps[-1]/n)**2 for n in steps]
    time.loglog(steps, reference, "--", color="#555f65", lw=1, label="Second-order slope")
    time.set_xscale("log", base=2)
    time.set_xticks(steps, [str(n) for n in steps])
    time.set(xlabel="Steps over the same time interval", ylabel="RMS field difference, N vs. 2N steps",
             title="Timestep refinement")
    time.legend(frameon=False, fontsize=8)
    for ax in (field, time):
        ax.grid(axis="both", which="major", color="#dce3e4", lw=.7)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(output, dpi=170, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--packet", type=Path, default=DATA / "measurements.tar.gz")
    parser.add_argument("--summary", type=Path, default=DATA / "summary.json")
    args = parser.parse_args()
    plot(args.output, args.packet, args.summary)
