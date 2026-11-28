"""Plot measured same-input speedups at a fixed eight-CPU request."""
import argparse
import csv
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize

LABELS = {
    "rigid-mesh":"Regular 3D mesh", "jitter-mesh":"Jittered 3D mesh",
    "flip-mesh":"Face flip", "periodic-self":"Periodic self-neighbours",
    "lloyd":"Lloyd regularisation", "swept-flip":"Swept volume · flip", "swept-jitter":"Swept volume · jitter",
    "moving-curl3":"Moving shared-face curl", "point-curl3":"Point and shared-face curl",
    "curl-flux3":"3D curl and HLLD flux", "kdk":"Direct gravity · 256 particles",
    "alfven":"Alfvén wave", "boosted-loop":"Boosted field loop", "brio":"Brio–Wu shock",
    "vortex":"Orszag–Tang vortex", "deforming-alfven":"Deforming Alfvén wave", "planar":"Planar gas",
    "ct":"Constrained transport", "ct-limited":"Limited constrained transport",
    "passive":"Passive potential", "prescribed":"Prescribed advection",
}

def plot(source, target):
    with source.open(newline="") as inp:
        rows = {(row["family"],int(row["ranks"]),int(row["threads"])):float(row["seconds"])
                for row in csv.DictReader(inp) if row["scope"]=="strong"}
    layouts = [(2,4),(4,2),(8,1)]
    order = list(LABELS)
    speed = [[rows[name,1,8]/rows[name,r,t] for r,t in layouts] for name in order]
    scale = max(1, max(abs(math.log2(x)) for row in speed for x in row))
    palette = LinearSegmentedColormap.from_list("speed",["#a34918","#f3dcc1","#f6f7f6","#b4dacf","#006960"])
    fig, ax = plt.subplots(figsize=(7.4,8.3),facecolor="white")
    fig.subplots_adjust(left=.43,right=.975,top=.845,bottom=.105)
    ax.imshow([[math.log2(x) for x in row] for row in speed],aspect="auto",cmap=palette,norm=Normalize(-scale,scale))
    for y,row in enumerate(speed):
        for x,value in enumerate(row):
            ax.text(x,y,f"{value:.2f}×",ha="center",va="center",fontsize=9,
                    color="white" if abs(math.log2(value))>.81*scale else "#16343c")
    ax.set_yticks(range(len(order)),[f"{LABELS[n]}   {rows[n,1,8]:.2f} s" for n in order],fontsize=8.5)
    ax.set_xticks(range(len(layouts)),[f"{r} × {t}" for r,t in layouts],fontsize=10,fontweight="bold")
    ax.xaxis.tick_top()
    ax.tick_params(axis="both",length=0,pad=6)
    for y in (6.5,9.5,10.5,15.5):
        ax.axhline(y,color="white",lw=2)
    for spine in ax.spines.values(): spine.set_visible(False)
    fig.text(.04,.96,"Eight CPUs on one REANA node",fontsize=19,weight="bold",color="#173940")
    fig.text(.04,.924,"Speed relative to one MPI rank with eight Rayon threads",fontsize=11,color="#39545a")
    fig.text(.411,.876,"Reference time",ha="right",fontsize=9,color="#39545a")
    fig.text(.703,.876,"MPI ranks × threads per rank",ha="center",fontsize=9,color="#39545a")
    fig.text(.04,.054,"Each value compares the same numerical input. Values above 1× are faster.",fontsize=9,color="#39545a")
    fig.text(.04,.031,"Times are medians of three complete launches, including MPI startup and file output.",fontsize=9,color="#39545a")
    fig.savefig(target,dpi=180,facecolor="white")
    plt.close(fig)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("measurements",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    plot(args.measurements,args.output)
