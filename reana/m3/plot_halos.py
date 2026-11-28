"""Plot the eight-rank fixed-input measurements after the offline verifier passes."""
import csv
import hashlib
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot(packet, destination):
    verdict = json.loads((packet / "verification.json").read_bytes())
    raw = (packet / "measurements.csv").read_bytes()
    if not verdict["passed"] or hashlib.sha256(raw).hexdigest() != verdict["measurements_sha256"]:
        raise ValueError("measurements differ from verified replay")
    rows = {r["case"]: r for r in csv.DictReader(raw.decode().splitlines())}
    cases = [("curl-flux3", "Magnetic curl + ALE flux"), ("moving-curl3", "Moving-field operators"),
             ("swept-jitter", "Jittered mesh sweeps"), ("swept-flip", "Mesh sweeps through a flip"),
             ("periodic-self", "Periodic self-images")]
    fig, (traffic, wall) = plt.subplots(1, 2, figsize=(10.2, 3.9), sharey=True,
                                          gridspec_kw={"width_ratios": [1.12, 1]})
    for i,(key, _) in enumerate(cases):
        sparse, full = [rows[f"{key}-{mode}-8x1"] for mode in ("sparse","full")]
        fraction = 100 * (1 - int(sparse["payload_bytes"]) / int(full["payload_bytes"]))
        traffic.barh(i, fraction, color="#176a73", height=0.49)
        traffic.text(fraction+1.5,i,f"{fraction:.1f}%",va="center", fontsize=9)
        a,b = [float(r["median_wall_s"]) for r in (full,sparse)]
        wall.plot([a,b],[i,i],color="#99a4ad",lw=1.5,zorder=1)
        wall.scatter(a,i,color="#e49a4d",s=54,label="Full gather" if i==0 else None,zorder=2)
        wall.scatter(b,i,facecolor="white",edgecolor="#176a73",lw=1.8,s=39,label="Sparse" if i==0 else None,zorder=3)
    traffic.set_yticks(range(len(cases)), labels=[name for _,name in cases])
    traffic.invert_yaxis()
    traffic.set_xlim(0,116)
    traffic.set_xticks([0,25,50,75,100])
    traffic.set_xlabel("Remote stage payload saved (%)")
    wall.set_xlabel("Median end-to-end wall time (s)")
    wall.set_xlim(left=0)
    wall.legend(loc="upper center",bbox_to_anchor=(.5,-.24),ncols=2,frameon=False)
    for ax in (traffic,wall):
        ax.grid(axis="x",color="#e2e6e9",lw=.7)
        ax.set_axisbelow(True)
        ax.spines[["top","right","left"]].set_visible(False)
        ax.tick_params(axis="y",length=0)
    fig.suptitle("Eight MPI ranks on one REANA node", x=.24, ha="left", fontsize=15, fontweight="semibold")
    fig.subplots_adjust(left=.25,right=.98,bottom=.29,top=.82,wspace=.18)
    destination.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(destination,dpi=175,bbox_inches="tight",facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    plot(Path(sys.argv[1]),Path(sys.argv[2]))
