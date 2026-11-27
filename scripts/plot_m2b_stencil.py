"""Plot the observed stencil and Rust curl of the bounded O01 Az=xy case."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.ticker import FormatStrFormatter
import numpy as np


def words(v):return np.array([struct.unpack(">d",bytes.fromhex(s))[0] for s in v])
def main(source,destination):
    origin=json.loads((source/"origin.json").read_bytes())
    for n,which in (("fixture.json","reference"),("comparison.json","candidate"),("native.stdout","candidate")):
        if hashlib.sha256((source/n).read_bytes()).hexdigest()!=origin[which]["outputs"][n]["sha256"]:
            raise ValueError("Figure input checksum "+n)
    ref=json.loads((source/"fixture.json").read_bytes())
    comparison=json.loads((source/"comparison.json").read_bytes())
    if not comparison["passed"] or ref["name"]!="bounded_interior__quadratic__xy__z":raise ValueError("Selection")
    reported={r[0]:words(r[1:]) for r in (line.split() for line in (source/"native.stdout").read_text().splitlines()) if r[0]!="fit"}
    center=words(ref["evaluation_position_bits"])
    delta=np.array([words(s["displacement_bits"]) for s in ref["samples"]]);pts=center+delta
    scalar=words([s["scalar_bits"] for s in ref["samples"]]);rings=np.array([s["adjacency_ring"] for s in ref["samples"]])
    fig=plt.figure(figsize=(9,6.2),facecolor="white")
    ax=fig.add_axes([.015,.075,.61,.80],projection="3d",proj_type="ortho")
    ax.view_init(elev=23,azim=-58);ax.set_box_aspect((1,1,1))
    for axis in (ax.xaxis,ax.yaxis,ax.zaxis):
        axis.pane.set_facecolor((.95,.97,.98,.55));axis.pane.set_edgecolor("#e3e8ed")
        axis._axinfo["grid"].update(color="#d8dfe5",linewidth=.5)
        axis.set_major_formatter(FormatStrFormatter("%.3g"))
    for k,label in enumerate("xyz"):
        getattr(ax,"set_"+label+"lim")(.07,1.18);getattr(ax,"set_"+label+"ticks")([.25,.625,1.]);getattr(ax,"set_"+label+"label")(label,labelpad=4)
    for p in pts[rings==1]:ax.plot(*zip(center,p),c="#728696",lw=1.1,zorder=1)
    for i,p in enumerate(pts):
        if rings[i]==2:
            for j,q in enumerate(pts):
                if rings[j]==1 and np.isclose(np.linalg.norm(p-q),.25):
                    ax.plot(*zip(p,q),c="#a2b8c6",alpha=.44,lw=.7,zorder=1)
    cmap=plt.get_cmap("viridis");norm=Normalize(0,scalar.max())
    for ring,size in [(2,48),(1,85)]:
        use=rings==ring;ax.scatter(*pts[use].T,c=scalar[use],s=size,cmap=cmap,norm=norm,depthshade=False,edgecolors="white",linewidths=.8)
    ax.scatter(*center,s=85,c="#202f46",edgecolors="white",depthshade=False)
    ax.quiver(*center,*reported["field"],length=.63,color="#ce4f34",linewidth=2.7,arrow_length_ratio=.22,normalize=False)
    fig.text(.055,.93,"Recovering a magnetic field on a 3D stencil",fontsize=19,weight="semibold",color="#162b40")
    fig.text(.055,.877,"M2b manufactured case   ·   bounded Cartesian Voronoi mesh",fontsize=11,color="#52677b")
    fig.text(.64,.715,r"$\mathbf{A}=(0,\,0,\,xy)$",fontsize=16,color="#182c40")
    fig.text(.64,.645,r"$\nabla\!\times\!\mathbf{A}=(x,\,-y,\,0)$",fontsize=16,color="#182c40")
    fig.text(.64,.53,"At the central centroid",fontsize=11,weight="semibold",color="#182c40")
    shown=",\\,".join(format(round(float(v),3),"g") if round(float(v),3)!=0 else "0" for v in reported["field"])
    fig.text(.64,.472,r"$\mathbf{B}_{\rm Rust}=("+shown+")$",fontsize=13,color="#b24128")
    fig.text(.64,.406,"Components rounded to three decimals.",fontsize=9,color="#52677b")
    fig.text(.64,.337,"Maximum component error",fontsize=10,color="#52677b")
    fig.text(.64,.28,f"{comparison['errors']['field']:.2e}",fontsize=16,weight="semibold",color="#182c40")
    cb=fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),cax=fig.add_axes([.64,.17,.29,.018]),orientation="horizontal")
    cb.set_label(r"Sampled potential $A_z$",fontsize=9);cb.ax.tick_params(labelsize=8);cb.outline.set_visible(False)
    fig.savefig(destination,dpi=175,facecolor="white");plt.close(fig)

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("source",type=Path);p.add_argument("destination",type=Path)
    a=p.parse_args();main(a.source,a.destination)
