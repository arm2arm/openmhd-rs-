"""Render the measured 100+100 trajectory, surface density and core separation."""
import argparse
import base64
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter
import numpy as np


BG, INK, MUTED, GRID = "#0c1422", "#edf3f7", "#b2c3d3", "#45576d"
COLORS = ("#67d8e8", "#ffac77")
WINDOW = np.array([4.8, 3.2, 3.2])


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_inputs(root):
    run = json.loads((root / "run.json").read_bytes())
    density = json.loads((root / "density.json").read_bytes())
    for file in ("trajectory.npz", "structure.csv"):
        if sha(root / file) != run["files"][file]:
            raise ValueError("trajectory or structure identity")
    if density["trajectory_sha256"] != run["files"]["trajectory.npz"] or density["levels_sha256"] != sha(root / "density.npz"):
        raise ValueError("density source")
    with np.load(root / "trajectory.npz") as data:
        t, x, labels, cores = (data[k] for k in ("time","position","population","core_centers"))
    with np.load(root / "density.npz") as d:
        if not np.array_equal(d["time"],t):
            raise ValueError("density time axis")
        levels, extent = d["levels"], d["extent"]
    history = np.genfromtxt(root / "structure.csv", names=True, delimiter=",")
    if x.shape != (len(t),200,3) or not np.array_equal(history["time"],t):
        raise ValueError("particle and diagnostic time axes")
    return run, density, t, x, labels, cores, levels, extent, history["core_separation"]


def cube(ax, labels=True):
    ax.computed_zorder = False
    ax.set_facecolor(BG)
    ax.set_proj_type("ortho")
    ax.view_init(elev=21,azim=-65)
    ax.set_box_aspect(2 * WINDOW, zoom=1.02)
    ax.set(xlim=(-WINDOW[0],WINDOW[0]), ylim=(-WINDOW[1],WINDOW[1]), zlim=(-WINDOW[2],WINDOW[2]))
    for i,(axis, ticks) in enumerate(zip((ax.xaxis,ax.yaxis,ax.zaxis), ([-4,0,4],[-2,0,2],[-2,0,2]))):
        axis.set_ticks(ticks if labels else [])
        axis.set_pane_color((.077,.12,.18,.64))
        axis._axinfo["grid"].update(color=(.28,.36,.45,.45),linewidth=.55)
        axis.line.set_color(GRID)
        if labels:
            axis.labelpad=-1
            axis.set_label_text("xyz"[i],color=MUTED)
    ax.tick_params(colors=MUTED, labelsize=8,pad=0)


def visible(p):
    return np.all(np.abs(p) <= WINDOW,axis=1)


def write_viewer(out, t, positions, cores):
    # Display-only quantization of every second measured endpoint, with both final cores.
    tracks = np.concatenate((positions[::2], cores[::2]), axis=1)
    unit = float(np.max(np.abs(tracks)) / 32760)
    words = np.rint(tracks / unit).astype("<i2")
    if not np.all(np.abs(words * unit - tracks) <= 0.500001 * unit):
        raise ValueError("display quantization")
    template = Path(__file__).with_name("nbody_merger_viewer.html.in").read_text()
    items = {"__LAST__": len(tracks) - 1, "__FRAMES__": len(tracks), "__STEP__": float(t[2] - t[0]),
             "__BOUND__": float(np.max(np.linalg.norm(tracks, axis=2))), "__UNIT__": unit,
             "__DATA__": base64.b64encode(words.tobytes()).decode("ascii")}
    for key, value in items.items():
        if key not in template:
            raise ValueError("missing viewer field " + key)
        template = template.replace(key, str(value))
    dest = out / "orbit.html"
    dest.write_text(template)
    if dest.stat().st_size >= 512000:
        raise ValueError("viewer size")
    return dict(viewer_sha256=sha(dest), viewer_frames=len(tracks), viewer_time_interval=float(t[2] - t[0]),
                viewer_max_coordinate_quantization_error=0.5 * unit)


def render(root, out, fps=20):
    run, den, t, x, labels, cores, levels, extent, gap = read_inputs(root)
    out.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({"font.family":"DejaVu Sans","text.color":INK,"axes.labelcolor":MUTED,
                         "xtick.color":MUTED,"ytick.color":MUTED,"axes.edgecolor":GRID,
                         "figure.facecolor":BG,"axes.facecolor":BG,"font.size":10})
    fig = plt.figure(figsize=(12.8,7.2),dpi=100)
    fig.text(.035,.925,"Two 100-particle galaxies",fontsize=27,weight="bold")
    fig.text(.037,.881,"Isolated 3D collisionless gravity   ·   Equal masses   ·   Fixed Plummer softening",fontsize=12,color=MUTED)
    clock = fig.text(.953,.93,"",fontsize=16,ha="right",fontfamily="DejaVu Sans Mono")
    ax = fig.add_axes([.016,.14,.55,.68],projection="3d")
    cube(ax)
    fig.text(.04,.81,"Particle positions",fontsize=15,weight="bold")
    dot = ax.scatter([],[],[],s=18,depthshade=False,edgecolors="none",zorder=2)
    traces = [ax.plot([],[],[],color=color,lw=1.25,alpha=.83,zorder=3)[0] for color in COLORS]
    marks = [ax.plot([],[],[],marker="x",markersize=8,markeredgewidth=1.65,ls="",color=color,zorder=5)[0] for color in COLORS]
    fig.text(.048,.113,"●  Galaxy A",color=COLORS[0],fontsize=12)
    fig.text(.178,.113,"●  Galaxy B",color=COLORS[1],fontsize=12)
    fig.text(.309,.113,"×  Tagged core",color=MUTED,fontsize=12)
    count = fig.text(.048,.066,"",fontsize=10,color=MUTED)

    dx = fig.add_axes([.608,.487,.298,.314])
    img = dx.imshow(levels[0],origin="lower",extent=extent,cmap="magma",vmin=0,vmax=255,interpolation="bilinear")
    dx.set(xlabel="x",ylabel="y",xticks=[-4,-2,0,2,4],yticks=[-2,0,2])
    dx.tick_params(labelsize=8)
    fig.text(.608,.81,"Projected mass density",fontsize=15,weight="bold")
    cax = fig.add_axes([.923,.529,.009,.21])
    bar = fig.colorbar(img,cax=cax)
    bar.set_ticks([0,85,170,255],labels=[f"{den['floor']*10**k:.2g}" for k in range(4)])
    bar.ax.tick_params(labelsize=8)
    bar.ax.set_title("M/L²",fontsize=8,color=MUTED)

    diag = fig.add_axes([.61,.113,.319,.212])
    diag.spines[["top","right"]].set_visible(False)
    diag.grid(axis="y",color=GRID,lw=.55,alpha=.55)
    diag.plot(t,gap,color="#576a83",lw=1)
    diag.axhline(run["initial_half_mass_radius"],color="#c1d1db",ls=(0,(2,3)),lw=.8)
    past = diag.plot([],[],color="#a2e6d5",lw=1.8)[0]
    head = diag.plot([],[],color=INK,marker="o",markersize=4,ls="")[0]
    diag.set(xlim=(t[0],t[-1]),ylim=(0,max(gap)*1.11),xlabel="Time (code units)",ylabel="Distance",xticks=[0,10,20,30,40])
    diag.tick_params(labelsize=8)
    fig.text(.61,.357,"Core separation",fontsize=14,weight="bold")
    fig.text(.933,.357,"Initial half-mass radius · dotted",fontsize=8,color=MUTED,ha="right")
    palette=np.array(COLORS)

    def draw(i):
        mask=visible(x[i]); points=x[i,mask]
        dot._offsets3d=tuple(points.T)
        dot.set_facecolors(palette[labels[mask]])
        for j in range(2):
            traces[j].set_data_3d(*cores[max(0,i-22):i+1,j].T)
            marks[j].set_data_3d(*cores[i:i+1,j].T)
        img.set_data(levels[i])
        past.set_data(t[:i+1],gap[:i+1]);head.set_data(t[i:i+1],gap[i:i+1])
        clock.set_text(f"t = {t[i]:05.2f} / {t[-1]:.0f}")
        count.set_text(f"{int(mask.sum())} / 200 particles inside the fixed 3D viewing box")
    writer=FFMpegWriter(fps=fps,codec="libx264",extra_args=["-preset","fast","-crf","20","-pix_fmt","yuv420p","-movflags","+faststart"])
    movie=out/"merger.mp4"
    with writer.saving(fig,str(movie),dpi=100):
        for i in range(len(t)):
            draw(i)
            writer.grab_frame()
    plt.close(fig)

    first=run["core_overlap"]["first_overlap_time"]
    center=int(np.argmin(abs(t-first))) if first is not None else int(np.argmin(gap))
    panels=[0,center,len(t)-1]
    fig=plt.figure(figsize=(11.6,4.45),dpi=140)
    fig.text(.028,.91,"A collisionless galaxy merger in 3D",fontsize=21,weight="bold")
    fig.text(.03,.837,"200 live particles, coloured by progenitor",fontsize=11,color=MUTED)
    for col,(i,title) in enumerate(zip(panels,["Approach","Core overlap" if first is not None else "Closest cores","Final state"])):
        ax=fig.add_axes([.012+col*.33,.075,.325,.66],projection="3d")
        cube(ax,False)
        mask=visible(x[i])
        ax.scatter(*x[i,mask].T,c=palette[labels[mask]],s=13,alpha=.95,edgecolors="none",depthshade=False,zorder=2)
        for k,color in enumerate(COLORS):
            ax.plot(*cores[i:i+1,k].T,marker="x",markeredgewidth=1.2,ms=6,ls="",color=color,zorder=5)
        fig.text(.169+col*.33,.728,f"{title}   ·   t = {t[i]:.2f}",fontsize=12,ha="center")
    fig.text(.035,.04,"●  Galaxy A",color=COLORS[0],fontsize=10)
    fig.text(.15,.04,"●  Galaxy B",color=COLORS[1],fontsize=10)
    fig.text(.267,.04,"×  Core of each progenitor",color=MUTED,fontsize=10)
    fig.text(.964,.04,"Identical camera and physical scale in each panel",color=MUTED,fontsize=10,ha="right")
    fig.savefig(out/"evolution.png",facecolor=BG);plt.close(fig)
    record=dict(frames=len(t),fps=fps,video_seconds=len(t)/fps,source_sha256=run["files"]["trajectory.npz"],
                projection_sha256=den["levels_sha256"],camera_elevation=21,camera_azimuth=-65,
                viewing_box_half_widths=WINDOW.tolist(),poster_frames=panels,mp4_sha256=sha(movie),poster_sha256=sha(out/"evolution.png"))
    record.update(write_viewer(out,t,x,cores))
    (out/"media.json").write_text(json.dumps(record,indent=2)+"\n")


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("input",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    render(args.input,args.output)
