"""Render synchronized movies from the published REANA arrays. Requires ffmpeg."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import NamedTuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.colors import LogNorm, to_rgba
from matplotlib.cm import ScalarMappable
from matplotlib.ticker import FixedLocator
import numpy as np


BACKGROUND = "#0a111e"
PLOT = "#0d1827"
TEXT = "#f1f5f7"
MUTED = "#b0bfd0"
FAINT = "#62778d"
LINES = "#2b4054"
GROUPS = ("#61e2d2", "#ffae77")
ACC_COLOR = "#eaf4ff"
FPS = 12
NAMES = ("gravity", "density", "grid")
TITLES = ("Gravitational acceleration", "Mass density", "Moving Voronoi grid")
DESCRIPTIONS = ("Particle accelerations and recent paths in 3D",
                "Softened volume density on the fixed z = 0 plane",
                "3D cell edges, a midplane section and two tracked cells")


class MeshFrame(NamedTuple):
    section: np.ndarray
    level: np.ndarray
    cages: list
    face_count: int
    wire: np.ndarray


def load(path):
    with np.load(path, allow_pickle=False) as arrays:
        return {k: arrays[k] for k in arrays.files}


def read_data(root):
    primary = load(root / "encounter/trajectory.npz")
    density = load(root / "density/density.npz")
    if not np.array_equal(primary["time"], density["time"]):
        raise ValueError("Density and trajectory clocks differ")
    meshes = {}
    for path in sorted(root.glob("mesh-*/mesh.npz")):
        m = load(path)
        quality = json.loads((path.parent / "report.json").read_bytes())["checks"]
        for slot, f in enumerate(m["frames"]):
            f = int(f)
            if f in meshes or m["time"][slot] != primary["time"][f] or quality[slot]["frame"] != f:
                raise ValueError("Mismatched or duplicated mesh frame")
            lines = m["line_frame"] == f
            faces = []
            for i in np.flatnonzero(m["face_frame"] == f):
                a, b = m["face_offset"][i:i+2]
                faces.append((int(m["face_id"][i]), m["face_vertex"][a:b]))
            meshes[f] = MeshFrame(m["line"][lines], m["line_level"][lines], faces, quality[slot]["faces"],
                                  m["wire"][m["wire_frame"] == f])
    if sorted(meshes) != list(range(len(primary["time"]))):
        raise ValueError("Incomplete mesh history")
    return primary, density, meshes


def projection():
    azimuth, elevation = np.radians([-15, 40])
    u = np.array([np.cos(azimuth), np.sin(azimuth), 0.0])
    v = np.array([-np.sin(azimuth)*np.sin(elevation), np.cos(azimuth)*np.sin(elevation), np.cos(elevation)])
    return np.stack((u, v)), np.cross(u, v)


UV, DEPTH = projection()


def project(points):
    return np.einsum("...j,ij->...i", points, UV)


def camera_depth(points):
    return np.einsum("...j,j->...", points, DEPTH)


def stroke(ax, segments, color, width, alpha=1.0, zorder=2):
    ax.add_collection(LineCollection(segments, colors=color, linewidths=width,
                                    alpha=alpha, capstyle="round", zorder=zorder))


def axis_box(ax, physical=False):
    ax.set_facecolor(PLOT)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-2.12, 2.12)
    ax.set_ylim(-1.31, 1.31)
    if physical:
        ax.set_xticks([-2, -1, 0, 1, 2], labels=["−2", "−1", "0", "1", "2"])
        ax.set_yticks([-1, 0, 1], labels=["−1", "0", "1"])
        ax.tick_params(labelsize=9, colors=MUTED, length=2, width=0.5, pad=3)
        ax.text(0.995, 0.014, "x  [L]", transform=ax.transAxes, ha="right", va="bottom", fontsize=9, color=MUTED)
        ax.set_ylabel("y  [L]", loc="top", fontsize=9, color=MUTED, labelpad=0, rotation=0)
    else:
        ax.set_xticks([])
        ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color(LINES)
        spine.set_linewidth(0.8)


def floor(ax):
    seq = []
    for tick in np.arange(-3, 3.01, 0.5):
        seq.append([[tick,-2.5,-0.55],[tick,2.5,-0.55]])
        seq.append([[-3,tick,-0.55],[3,tick,-0.55]])
    stroke(ax,project(np.asarray(seq)),LINES,0.45,0.48,zorder=0)


def triad(ax):
    base = np.array([-1.90,-1.09])
    for direction, name in zip(np.eye(3), "xyz"):
        tip = base + 0.32 * project(direction)
        ax.plot(*np.stack((base,tip)).T, color=MUTED, linewidth=0.85, zorder=9)
        offset = {"x":(0.055,-0.043),"y":(-0.060,0.032),"z":(0.035,0.045)}[name]
        ax.text(*(tip+offset), name, color=MUTED, fontsize=9, ha="center",va="center", zorder=9)


def groups_key(fig, suffix=""):
    x0 = 0.080
    for j,label in enumerate(("Group A", "Group B")):
        x=x0+j*0.158
        fig.text(x,0.237,"●",color=GROUPS[j],fontsize=12,va="center")
        fig.text(x+0.026,0.237,label,color=MUTED,fontsize=10,va="center")
    fig.text(0.925,0.237,suffix,color=MUTED,fontsize=10,ha="right",va="center")


def clock(fig, time):
    fig.text(0.925,0.947,f"t = {time:.2f}",color=TEXT,fontsize=16,ha="right",va="center",
             family="DejaVu Sans Mono")


def timeline(fig, t, values, i, label, units, color, digits):
    fig.text(0.078,0.163,label,color=MUTED,fontsize=12,va="center")
    fig.text(0.923,0.164,f"{values[i]:.{digits}f}{units}",ha="right",va="center",
             color=TEXT,fontsize=15,family="DejaVu Sans Mono")
    ax=fig.add_axes([0.081,0.070,0.84,0.064],facecolor=BACKGROUND)
    lo,hi=np.min(values),np.max(values)
    pad=max((hi-lo)*0.15,0.001)
    ax.set_xlim(t[0],t[-1])
    ax.set_ylim(lo-pad,hi+pad)
    ax.plot(t,values,color=LINES,linewidth=1.9)
    ax.plot(t[:i+1],values[:i+1],color=color,linewidth=1.8)
    ax.scatter(t[i],values[i],color=color,s=26,edgecolor=BACKGROUND,linewidth=0.8,zorder=3,clip_on=False)
    ax.axis("off")
    fig.text(0.078,0.038,"0",color=FAINT,fontsize=9)
    fig.text(0.50,0.038,"Time [T]",ha="center",color=MUTED,fontsize=10)
    fig.text(0.924,0.038,f"{t[-1]:g}",ha="right",color=FAINT,fontsize=9)


def gravity_scene(ax, fig, state, i, centroids):
    pos=state["position"]; pop=state["population"]; t=state["time"]
    floor(ax)
    # Every trail contains at most the last 16 saved intervals.
    uv=project(pos[max(0,i-16):i+1])
    if len(uv)>1:
        segments=np.stack((uv[:-1],uv[1:]),axis=2).reshape(-1,2,2)
        colors=[to_rgba(GROUPS[group],a) for a in np.linspace(0.07,0.5,len(uv)-1) for group in pop]
        ax.add_collection(LineCollection(segments,colors=colors,linewidths=1.3))
    current=uv[-1]
    order=np.argsort(camera_depth(pos[i]))
    c=np.array(GROUPS)[pop[order]]
    ax.scatter(*current[order].T,s=48,color=c,alpha=0.12,edgecolors="none",zorder=3)
    ax.scatter(*current[order].T,s=15,color=c,edgecolors=BACKGROUND,linewidth=0.35,zorder=5)
    arrows=0.16*project(state["acceleration"][i])
    ax.quiver(*current.T,*arrows.T,angles="xy",scale_units="xy",scale=1,
              width=0.0021,headwidth=3.6,headlength=4.2,minlength=0,color=ACC_COLOR,alpha=0.85,zorder=4)
    triad(ax)
    ax.quiver(1.48,-1.12,0.16,0,angles="xy",scale_units="xy",scale=1,
              width=0.0025,color=ACC_COLOR,zorder=9)
    ax.text(1.7,-1.12,"1 L/T²",color=MUTED,fontsize=9,va="center")
    groups_key(fig,"White arrows show acceleration")
    timeline(fig,t,np.linalg.norm(centroids[0]-centroids[1],axis=1),i,"Group-centre separation"," L",GROUPS[0],2)


def density_scene(ax, fig, d, i, centroids):
    extent=float(d["extent"]);low,high=float(d["low"]),float(d["high"])
    lo,hi=0.001,3.2
    raw_bounds=255*np.log(np.array([lo,hi])/low)/np.log(high/low)
    ax.imshow(d["image"][i],origin="lower",extent=(-extent,extent,-extent,extent),
              cmap="magma",vmin=raw_bounds[0],vmax=raw_bounds[1],interpolation="bilinear",zorder=0)
    levels = 255 * np.log(np.array([0.03, 0.1, 0.3, 1.0, 2.0]) / low) / np.log(high / low)
    ax.contour(d["axes"], d["axes"], d["image"][i], levels=levels, colors="#ffedcb",
               linewidths=0.65, alpha=0.48, zorder=1)
    # Ring marks the centre of mass of each original group, projected into x-y.
    for k,color in enumerate(GROUPS):
        x,y=centroids[k,i,:2]
        ax.scatter(x,y,marker="o",s=62,facecolor="none",edgecolor=BACKGROUND,linewidth=2.6,zorder=3)
        ax.scatter(x,y,marker="o",s=62,facecolor="none",edgecolor=color,linewidth=1.2,zorder=4)
    fig.text(0.078,0.232,"ρ  [M/L³]",fontsize=12,color=TEXT,va="center")
    cbax=fig.add_axes([0.255,0.244,0.66,0.013])
    ticks=[0.001,0.01,0.1,1,3]
    bar=fig.colorbar(ScalarMappable(norm=LogNorm(lo,hi),cmap="magma"),cax=cbax,
                     orientation="horizontal",ticks=ticks)
    bar.ax.xaxis.set_major_locator(FixedLocator(ticks))
    bar.ax.set_xticklabels(["0.001","0.01","0.1","1","3"])
    bar.ax.minorticks_off()
    bar.ax.tick_params(colors=MUTED,length=2,labelsize=9,pad=2)
    bar.outline.set_edgecolor(LINES)
    timeline(fig,d["time"],d["peak"],i,"Peak midplane density"," M/L³","#ffac7d",2)


def cutaway(wire):
    """Clip exported line segments in space and remove the front of the grid."""
    start, end = wire[:,0], wire[:,1]
    start4 = np.column_stack((start, camera_depth(start)))
    delta4 = np.column_stack((end, camera_depth(end))) - start4
    enter, leave = np.zeros(len(wire)), np.ones(len(wire))
    visible = np.ones(len(wire), dtype=bool)
    for j,(lo,hi) in enumerate(((-2.18,2.18),(-1.39,1.39),(-0.57,0.57),(-1.4,0.08))):
        a, delta = start4[:,j], delta4[:,j]
        parallel = abs(delta) < 1e-12
        visible &= ~(parallel & ((a < lo) | (a > hi)))
        safe = np.where(parallel, 1.0, delta)
        b, c = (lo-a)/safe, (hi-a)/safe
        enter = np.maximum(enter,np.where(parallel,-np.inf,np.minimum(b,c)))
        leave = np.minimum(leave,np.where(parallel,np.inf,np.maximum(b,c)))
    visible &= enter < leave
    delta = end[visible] - start[visible]
    return np.stack((start[visible]+enter[visible,None]*delta, start[visible]+leave[visible,None]*delta),axis=1)


def grid_scene(ax,fig,state,meshes,i):
    m=meshes[i]
    stroke(ax,project(cutaway(m.wire)),"#7899b2",0.85,0.46,zorder=0)
    stroke(ax,project(m.section[m.level==1]),"#8cbfd2",1.05,0.91,zorder=1)
    palette={3:GROUPS[0],35:GROUPS[1]}
    view_order=sorted(m.cages,key=lambda item:float(np.mean(camera_depth(item[1]))))
    patches=[project(p) for _,p in view_order]
    ax.add_collection(PolyCollection(patches,facecolors=[to_rgba(palette[k],0.10) for k,_ in view_order],
                                      edgecolors=[to_rgba(palette[k],0.92) for k,_ in view_order],
                                      linewidths=1.25,zorder=4))
    pts=project(state["position"][i])
    for k,color in palette.items():
        point=pts[state["ids"]==k][0]
        ax.scatter(*point,s=31,facecolor=color,edgecolor=BACKGROUND,linewidth=0.7,zorder=5)
    triad(ax)
    fig.text(0.078,0.237,"●",color=GROUPS[0],fontsize=12,va="center")
    fig.text(0.104,0.237,"Cell 3",color=MUTED,fontsize=10,va="center")
    fig.text(0.226,0.237,"●",color=GROUPS[1],fontsize=12,va="center")
    fig.text(0.252,0.237,"Cell 35",color=MUTED,fontsize=10,va="center")
    fig.text(0.925,0.237,"64 moving generators",color=MUTED,fontsize=10,ha="right",va="center")
    timeline(fig,state["time"],np.array([meshes[f].face_count for f in range(len(meshes))]),i,
             "Faces in the full grid","",GROUPS[0],0)


def frame(kind, state, density, meshes, centroids, i):
    fig=plt.figure(figsize=(8,7.2),dpi=100,facecolor=BACKGROUND)
    idx=NAMES.index(kind)
    fig.text(0.073,0.946,TITLES[idx],fontsize=25,weight="semibold",color=TEXT,va="center")
    fig.text(0.076,0.887,DESCRIPTIONS[idx],fontsize=12,color=MUTED,va="center")
    clock(fig,state["time"][i])
    ax=fig.add_axes([0.073,0.292,0.852,0.55])
    axis_box(ax,physical=kind=="density")
    if kind=="gravity":
        gravity_scene(ax,fig,state,i,centroids)
    elif kind=="density":
        density_scene(ax,fig,density,i,centroids)
    else:
        grid_scene(ax,fig,state,meshes,i)
    return fig


def ffmpeg(args):
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",*map(str,args)],check=True)


def render(root, dest, preview):
    state,density,meshes=read_data(root)
    pos,pop=state["position"],state["population"]
    centres=np.stack([np.average(pos[:,pop==k],axis=1,weights=state["mass"][pop==k]) for k in (0,1)])
    dest.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({"font.family":"DejaVu Sans","axes.unicode_minus":True,"savefig.dpi":100})
    if preview is not None:
        for kind in NAMES:
            fig=frame(kind,state,density,meshes,centres,preview)
            fig.savefig(dest/f"{kind}-{preview:03}.png",facecolor=BACKGROUND)
            plt.close(fig)
        return
    for kind in NAMES:
        target=dest/f"{kind}.mp4"
        cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-f","rawvideo","-pix_fmt","rgba",
             "-s","800x720","-r",str(FPS),"-i","pipe:0","-an","-c:v","libx264","-crf","18",
             "-pix_fmt","yuv420p","-movflags","+faststart",str(target)]
        with subprocess.Popen(cmd,stdin=subprocess.PIPE) as encoder:
            for i in range(len(state["time"])):
                fig=frame(kind,state,density,meshes,centres,i)
                try:
                    fig.canvas.draw()
                    encoder.stdin.write(fig.canvas.buffer_rgba())
                finally:
                    plt.close(fig)
            encoder.stdin.close()
            if encoder.wait():
                raise RuntimeError(f"Encoding {target.name} failed")
    inputs=[arg for kind in NAMES for arg in ["-i",dest/f"{kind}.mp4"]]
    combined=dest/"synchronized.mp4"
    ffmpeg([*inputs,"-filter_complex","hstack=inputs=3","-an","-c:v","libx264","-crf","19",
            "-pix_fmt","yuv420p","-movflags","+faststart",combined])
    palette="fps=8,scale=1080:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=160[p];[b][p]paletteuse=dither=bayer:bayer_scale=4"
    ffmpeg(["-i",combined,"-filter_complex",palette,"-loop","0",dest/"preview.gif"])
    ffmpeg(["-ss",str(49/FPS),"-i",combined,"-frames:v","1","-vf","scale=1440:-2",dest/"encounter.png"])
    media=sorted([*dest.glob("*.mp4"),dest/"preview.gif",dest/"encounter.png"])
    report=dict(frames=len(state["time"]),fps=FPS,trajectory_sha256=hashlib.sha256((root/"encounter/trajectory.npz").read_bytes()).hexdigest(),
                files={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in media})
    (dest/"media.json").write_text(json.dumps(report,indent=2)+"\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--preview-frame",type=int)
    a=parser.parse_args()
    render(a.data,a.output,a.preview_frame)
