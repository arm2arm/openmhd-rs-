"""Plot only recorded Fourier fields and their independently reduced errors."""
import argparse
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.ticker import ScalarFormatter
import numpy as np

def main(summary_path,field_path,dest):
    summary=json.loads(summary_path.read_bytes())
    case=next(c for c in summary["o02"]["cases"] if c["case"]=="jitter-32-zero")
    if hashlib.sha256(field_path.read_bytes()).hexdigest()!=case["fields_sha256"]:raise ValueError("Field data identity")
    dest.mkdir(exist_ok=True,parents=True)
    color={"regular":"#1e5c87","jitter":"#b94d25"}
    with np.load(field_path,allow_pickle=False) as d:
        xyz=d["centroids"].reshape(32,32,32,3)[3::7,3::7,3::7].reshape(-1,3)
        b=d["quadratic"][:,:3].reshape(32,32,32,3)[3::7,3::7,3::7].reshape(-1,3)
    fig=plt.figure(figsize=(8.2,6.5),facecolor="white")
    ax=fig.add_axes([.04,.09,.77,.75],projection="3d",proj_type="ortho")
    ax.view_init(21,-53);ax.set_box_aspect((1,1,1))
    for a in (ax.xaxis,ax.yaxis,ax.zaxis):
        a.pane.set_facecolor((.96,.97,.98,.6));a._axinfo["grid"].update(color="#dae1e7",linewidth=.6)
    for k in "xyz":
        getattr(ax,"set_"+k+"lim")(0,1);getattr(ax,"set_"+k+"ticks")([0,.5,1]);getattr(ax,"set_"+k+"label")(k,labelpad=3)
    norm=TwoSlopeNorm(vmin=-13,vcenter=0,vmax=13);cmap=plt.get_cmap("coolwarm")
    rgba=cmap(norm(b[:,2]))
    # The 3D quiver artist orders all shafts before both arrowhead segments.
    ax.quiver(*xyz.T,*b.T,length=.064,normalize=True,colors=np.concatenate([rgba,np.repeat(rgba,2,axis=0)]),linewidth=1.35,arrow_length_ratio=.27)
    fig.text(.075,.933,"Magnetic field on a jittered 3D Voronoi mesh",fontsize=18,weight="semibold",color="#172e40")
    fig.text(.075,.879,"Periodic Fourier field recovered from its vector potential",fontsize=11,color="#50667a")
    cax=fig.add_axes([.83,.27,.022,.37]);fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),cax=cax,label=r"Recovered $B_z$")
    fig.text(.075,.045,"125 sampled directions from 32,768 static cells. Arrow lengths are normalized.",fontsize=9,color="#50667a")
    fig.savefig(dest/"fourier_field.png",dpi=175);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(10,4.8))
    fig.subplots_adjust(left=.095,right=.965,bottom=.17,top=.73,wspace=.30)
    fig.suptitle("Convergence of the static 3D operators",x=.07,y=.96,ha="left",fontsize=18,weight="semibold",color="#172e40")
    fig.text(.07,.835,"Periodic Fourier field  ·  quadratic fit  ·  zero imposed mean",fontsize=10.5,color="#50667a")
    for ax in axs:
        ax.set_xscale("log",base=2);ax.set_xticks([8,16,32]);ax.xaxis.set_major_formatter(ScalarFormatter())
        ax.set_yscale("log");ax.set_xlabel("Generators per axis, N");ax.grid(axis="y",alpha=.23);ax.spines[["top","right"]].set_visible(False)
    for mesh,label in (("regular","Regular"),("jitter","15% jitter")):
        curve=next(x for x in summary["o02"]["ladders"] if x["mesh"]==mesh and x["fit"]=="quadratic" and x["mean_b"]==[0.,0.,0.])
        axs[0].plot([8,16,32],curve["normalized_l1"],marker="o",color=color[mesh],label=f"{label}, p = {curve['order']:.2f}")
        axs[1].plot([8,16,32],curve["face_mean_rms"],marker="o",color=color[mesh],label=label)
    axs[0].set_ylabel("Volume-weighted relative curl error");axs[1].set_ylabel(r"RMS of face-mean $\nabla\cdot\mathbf{B}$")
    axs[0].legend(frameon=False,fontsize=9);axs[1].legend(frameon=False,fontsize=9)
    fig.savefig(dest/"fourier_convergence.png",dpi=175);plt.close(fig)

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("summary","fields","destination"):p.add_argument(k,type=Path)
    args=p.parse_args();main(args.summary,args.fields,args.destination)
