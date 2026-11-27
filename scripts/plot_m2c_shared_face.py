"""Plot measured initial magnetic means and cell-average spatial errors."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"docs/galaxy/results/m2c_moving"
COLORS=("#1b7181","#a14b1f","#73478b")
FAMILIES=("original","fresh-a","fresh-b")


def main(output, summary):
    previous=json.loads((DATA/"initial-mean.json").read_bytes())["workflows"]
    shared=json.loads(summary.read_bytes())["spatial_ladders"]
    fig,(left,right)=plt.subplots(1,2,figsize=(9.8,4.5),layout="constrained")
    x=[8,16,32]
    for ix,(fam,color) in enumerate(zip(FAMILIES,COLORS)):
        old=sorted((r["data"] for r in previous if r["data"]["case"][0]==fam and r["data"]["case"][2]=="mean"),key=lambda r:r["cells"])
        new,=[l for l in shared if (l["mesh"],l["mean"])==(fam,"mean")]
        left.plot(x,[r["scaled_max_component"] for r in old],"o--",color=color,ms=4,label="Point curl" if ix==0 else None)
        left.plot(x,[r["scaled_mean"] for r in new["levels"]],"o-",color=color,ms=4,label="Shared-face curl" if ix==0 else None)
    left.legend(frameon=False,loc="center right",fontsize=8)
    irregular=[r for r in shared if r["mesh"]!="regular" and r["mean"]=="mean"]
    regular,=[r for r in shared if (r["mesh"],r["mean"])==("regular","mean")]
    for j,r in enumerate(irregular):
        right.plot(x,[v["l1"] for v in r["levels"]],"o-",color="#1b7181",alpha=.8,ms=4,
                   label="Six jittered meshes" if j==0 else None)
    right.plot(x,[v["l1"] for v in regular["levels"]],"s--",color="#765387",ms=4,label="Regular mesh")
    left.axhline(1e-9,color="#4c555b",lw=.9)
    left.text(8.2,2.1e-9,"Mean limit",size=8,color="#4c555b")
    left.set(ylabel="Maximum component error / 2π",title="Periodic magnetic mean")
    right.set(ylabel="Volume-weighted relative L₁ error",title="Cell-average curl")
    right.legend(frameon=False,fontsize=8)
    for ax in (left,right):
        ax.set_xscale("log",base=2);ax.set_yscale("log")
        ax.set_xticks([8,16,32],["8³","16³","32³"]);ax.set_xlabel("Number of cells")
        ax.grid(axis="y",which="major",color="#dce3e4",lw=.7)
        ax.spines[["top","right"]].set_visible(False)
    fig.suptitle("Magnetic-field reconstruction on 3D Voronoi meshes",fontweight="semibold")
    fig.savefig(output,dpi=165,facecolor="white");plt.close(fig)


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("output",type=Path)
    parser.add_argument("--summary",type=Path,default=DATA/"shared-face/summary.json")
    args=parser.parse_args();main(args.output,args.summary)
