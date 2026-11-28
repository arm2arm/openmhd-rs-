"""Plot the measured spatial field error and timestep differences for the coupled helix."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot(summary, destination):
    result = json.loads(summary.read_bytes())
    levels = result["levels"]
    n = [level["planes"] for level in levels]
    if n != [8,16,32]:
        raise ValueError("incomplete registered spatial ladder")
    fig,(spatial,time) = plt.subplots(1,2,figsize=(9.4,3.9),layout="constrained")
    initial = result["initial"]["errors"]
    final = result["final"]["errors"]
    fine = [level["runs"][1]["relative_l1"]["final"] for level in levels]
    spatial.loglog(n,initial,"s--",color="#967141",label="Initial field")
    spatial.loglog(n,final,"o-",color="#166b78",label="Evolved field")
    spatial.loglog(n,fine,"+",ms=11,color="#122e3a",label="Evolved, half timestep")
    spatial.set(xlabel="Generator planes per axis",ylabel="Relative L1 magnetic-field error",
                title="Spatial convergence")
    spatial.legend(frameon=False,fontsize=8)
    time.loglog(n,[level["timestep_field_rms"] for level in levels],"o-",color="#ad512e")
    time.set(xlabel="Generator planes per axis",ylabel="RMS difference in B (code units)",
             title="Effect of halving the timestep")
    for ax in (spatial,time):
        ax.set_xscale("log",base=2)
        ax.set_xticks(n,labels=[str(k) for k in n])
        ax.grid(axis="both",which="major",color="#dce2e2",lw=.7)
        ax.set_axisbelow(True)
        ax.spines[["top","right"]].set_visible(False)
    fig.savefig(destination,dpi=180,facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("summary",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    plot(args.summary,args.output)
