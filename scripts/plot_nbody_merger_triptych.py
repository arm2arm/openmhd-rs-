"""Render the synchronized particles, projected mass density and true 3D Voronoi cutaway."""
import argparse
import itertools
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter
from matplotlib.collections import LineCollection
from matplotlib.colors import to_rgba
from matplotlib.lines import Line2D
import numpy as np

from plot_nbody_merger_100 import BG, COLORS, INK, MUTED, read_inputs, sha


FPS = 20
AZIMUTH, ELEVATION = -72, 38
WIRE, SECTION = "#718eb6", "#9ae0c6"


def camera_basis():
    az, el = np.radians([AZIMUTH, ELEVATION])
    right = [-np.sin(az), np.cos(az), 0]
    toward = [np.cos(el)*np.cos(az), np.cos(el)*np.sin(az), np.sin(el)]
    return np.column_stack([right, np.cross(toward, right), toward])


CAMERA = camera_basis()


def project(points):
    return points @ CAMERA[:, :2]


def box_edges(half, bottom, top):
    edges = []
    for z in (bottom, top):
        corners = np.array([[-half[0],-half[1],z], [half[0],-half[1],z],
                            [half[0],half[1],z], [-half[0],half[1],z]])
        edges.extend(np.stack([corners, np.roll(corners, -1, axis=0)], axis=1))
    for x, y in itertools.product([-half[0], half[0]], [-half[1], half[1]]):
        edges.append([[x,y,bottom], [x,y,top]])
    return np.asarray(edges)


def add_lines(ax, xyz, color, width, alpha, zorder):
    lines = LineCollection(project(xyz), colors=color, linewidths=width, alpha=alpha,
                           capstyle="round", zorder=zorder)
    ax.add_collection(lines)
    return lines


def frame_axes(fig, bounds, half):
    ax = fig.add_axes(bounds)
    ax.set_aspect("equal")
    ax.set_axis_off()
    corners = project(box_edges(half, -half[2], half[2]).reshape(-1,3))
    limits = np.max(np.abs(corners), axis=0) + .1
    ax.set(xlim=(-limits[0],limits[0]), ylim=(-limits[1],limits[1]))
    return ax


def triad(ax):
    origin = np.array([-.90*ax.get_xlim()[1], -.88*ax.get_ylim()[1]])
    for i, label in enumerate("xyz"):
        tip = origin + .85*project(np.eye(3))[i]
        ax.plot(*np.stack([origin,tip]).T, color=MUTED, lw=.85)
        ax.text(*(origin + 1.29*(tip-origin)), label, ha="center", va="center",
                fontsize=8, color=MUTED)


def dots(ax):
    return ax.scatter([], [], edgecolors=BG, linewidths=.28, zorder=5)


def set_dots(artist, points, labels, size):
    depth = points @ CAMERA[:, 2]
    order = np.argsort(depth)
    artist.set_offsets(project(points[order]))
    artist.set_facecolors(np.asarray(COLORS)[labels[order]])
    artist.set_sizes(size * np.clip(1.0 + .08*depth[order], .68, 1.4))


def legend(fig, x, y, text, color, line=False):
    if line:
        fig.add_artist(Line2D([x, x+.012], [y+.002,y+.002], transform=fig.transFigure,
                              color=color, lw=1.5))
    else:
        fig.add_artist(Line2D([x+.005], [y+.002], transform=fig.transFigure,
                              ls="", marker="o", ms=5.5, mfc=color, mec="none"))
    fig.text(x+.016, y, text, color=MUTED, fontsize=10, va="center")


def read_mesh(root, run, time):
    record = json.loads((root/"voronoi.json").read_bytes())
    if record["trajectory_sha256"] != run["files"]["trajectory.npz"] or record["geometry_sha256"] != sha(root/"voronoi.npz"):
        raise ValueError("geometry/trajectory identity mismatch")
    with np.load(root/"trajectory.npz", allow_pickle=False) as source, np.load(root/"voronoi.npz", allow_pickle=False) as data:
        if not np.array_equal(source["particle_id"], data["particle_id"]) or not np.array_equal(data["time"], time):
            raise ValueError("generator IDs or frame times differ")
        half, bottom, scale = data["half_box"], float(data["slab_bottom"]), int(data["scale"])
        layers = []
        for name in ("wire", "cut"):
            edges, offsets = data[name], data[name+"_offsets"]
            if (edges.shape[1:] != (2,3) or offsets.shape != (len(time)+1,) or offsets[0] != 0
                    or offsets[-1] != len(edges) or np.any(np.diff(offsets) <= 0)):
                raise ValueError("incomplete mesh frame spans")
            layers.append((edges, offsets))
    return record, half, bottom, scale, layers


def render(root, out):
    run, den, time, positions, labels, _, levels, extent, _ = read_inputs(root)
    mesh_record, half, bottom, scale, layers = read_mesh(root, run, time)
    out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family":"DejaVu Sans", "text.color":INK, "axes.labelcolor":MUTED,
                         "xtick.color":MUTED, "ytick.color":MUTED, "axes.edgecolor":"#53647b",
                         "axes.facecolor":BG, "figure.facecolor":BG, "font.size":10})
    fig = plt.figure(figsize=(17.6, 6.8), dpi=100)
    fig.text(.029,.919,"Collisionless galaxy merger",fontsize=28,weight="bold",va="center")
    fig.text(.030,.856,"3D direct gravity   ·   100 equal-mass particles per galaxy   ·   Time in code units",fontsize=13,color=MUTED)
    clock = fig.text(.969,.92,"",ha="right",va="center",fontsize=17,fontfamily="DejaVu Sans Mono")
    bar_left, bar_right = .806,.968
    fig.add_artist(Line2D([bar_left,bar_right],[.863,.863],transform=fig.transFigure,color="#354559",lw=2.0))
    progress = Line2D([],[],transform=fig.transFigure,color=SECTION,lw=2.0)
    fig.add_artist(progress)
    for x, title, sub in [(.030,"Particles","3D positions and recent paths"),
                          (.369,"Projected density","Mass integrated along the z axis"),
                          (.692,"Points and Voronoi mesh","All 200 sites generate the 3D cells")]:
        fig.text(x,.742,title,fontsize=18,weight="bold")
        fig.text(x,.692,sub,fontsize=11.5,color=MUTED)
    for x in (.339,.664):
        fig.add_artist(Line2D([x,x],[.112,.773],transform=fig.transFigure,color="#2c3b50",lw=.8))
    fig.add_artist(Line2D([.030,.969],[.815,.815],transform=fig.transFigure,color="#354559",lw=.8))

    left = frame_axes(fig,[.013,.164,.315,.490],half)
    add_lines(left, box_edges(half,-half[2],half[2]), "#657a91", .70, .53, 1)
    for y in (-1.4,0,1.4):
        add_lines(left,np.array([[[-half[0],y,-half[2]],[half[0],y,-half[2]]]]),"#506076",.50,.35,1)
    triad(left)
    tracks = LineCollection([], linewidths=.72, capstyle="round", zorder=3)
    left.add_collection(tracks)
    stars = dots(left)
    legend(fig,.031,.118,"Galaxy A",COLORS[0])
    legend(fig,.125,.118,"Galaxy B",COLORS[1])
    left_count = fig.text(.031,.054,"",color=MUTED,fontsize=10)

    center = fig.add_axes([.371,.227,.267,.423])
    img = center.imshow(levels[0],origin="lower",extent=extent,cmap="magma",
                        vmin=0,vmax=255,interpolation="bilinear")
    center.set(xticks=[-4,-2,0,2,4], yticks=[-2,0,2], xlabel="x  [L]", ylabel="y  [L]")
    center.tick_params(length=3, width=.7, labelsize=9, pad=3)
    center.xaxis.labelpad=2
    center.yaxis.labelpad=1
    cax = fig.add_axes([.397,.130,.216,.012])
    cax.imshow(np.arange(256)[None,:], cmap="magma", aspect="auto", extent=(0,255,0,1),
               origin="lower", vmin=0,vmax=255)
    ticks = np.array([.002,.01,.1,1.])
    cax.set_xticks(255*np.log(ticks/den["floor"])/np.log(den["peak"]/den["floor"]),
                   labels=["0.002","0.01","0.1","1"])
    cax.set_yticks([])
    cax.tick_params(length=2, pad=2, labelsize=8)
    fig.text(.505,.045,"Surface mass density  [M/L²]",fontsize=10,color=MUTED,ha="center")

    right = frame_axes(fig,[.674,.164,.315,.490],half)
    slab = box_edges(half,bottom,0)
    # Frame the thinner cutaway at a larger fixed magnification using the same 3D camera.
    slab_height = project(slab.reshape(-1,3))[:,1]
    right.set_ylim(slab_height.min()-.22, slab_height.max()+.22)
    add_lines(right, slab[:4], WIRE,.7,.5,1)
    add_lines(right, slab[4:8], SECTION,.9,.7,3)
    add_lines(right, slab[8:], WIRE,.7,.5,1)
    wire_artist = add_lines(right,np.empty((0,2,3)),WIRE,.68,.52,2)
    cut_artist = add_lines(right,np.empty((0,2,3)),SECTION,1.08,.91,4)
    seeds = dots(right)
    legend(fig,.693,.118,"3D edges",WIRE,True)
    legend(fig,.791,.118,"z = 0 section",SECTION,True)
    right_count = fig.text(.693,.054,"",color=MUTED,fontsize=10)
    rgba = np.array([to_rgba(c) for c in COLORS])

    def update(i):
        p = positions[i]
        view = np.all(np.abs(p) <= half, axis=1)
        in_slab = view & (p[:,2] >= bottom) & (p[:,2] <= 0)
        set_dots(stars,p[view],labels[view],19)
        set_dots(seeds,p[in_slab],labels[in_slab],14)
        # Connect persistent IDs across the last five saved intervals using their actual 3D endpoints.
        recent = positions[max(0,i-5):i+1]
        seg = np.stack([recent[:-1],recent[1:]],axis=2)
        inside = np.all(np.abs(seg) <= half,axis=(2,3))
        tracks.set_segments(project(seg[inside]))
        trail_colors = np.broadcast_to(rgba[labels], (*inside.shape,4)).copy()
        trail_colors[:,:,3] = np.linspace(.08,.50,5)[5-len(inside):,None]
        tracks.set_color(trail_colors[inside])
        img.set_data(levels[i])
        for (edges,offsets),artist in zip(layers,(wire_artist,cut_artist)):
            artist.set_segments(project(edges[offsets[i]:offsets[i+1]]/scale))
        clock.set_text(f"t = {time[i]:06.3f} / {time[-1]:.0f}")
        progress.set_data([bar_left,bar_left+(bar_right-bar_left)*time[i]/time[-1]],[.863,.863])
        left_count.set_text(f"{view.sum()} of 200 particles in the viewing box")
        right_count.set_text(f"{in_slab.sum()} sites in slab   ·   {bottom:g} ≤ z ≤ 0")
    movie = out/"particles-density-voronoi.mp4"
    poster = out/"particles-density-voronoi.png"
    poster_index = int(np.flatnonzero(time==2.5)[0])
    update(poster_index)
    fig.savefig(poster,dpi=100,facecolor=BG)
    writer=FFMpegWriter(fps=FPS,codec="libx264",extra_args=["-preset","fast","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart"])
    with writer.saving(fig,str(movie),dpi=100):
        for i in range(len(time)):
            update(i)
            writer.grab_frame()
    plt.close(fig)
    report=dict(trajectory_sha256=run["files"]["trajectory.npz"], density_sha256=den["levels_sha256"],
                geometry_sha256=mesh_record["geometry_sha256"], movie_sha256=sha(movie), poster_sha256=sha(poster),
                frames=len(time), fps=FPS, run_time=[float(time[0]),float(time[-1])], poster_time=float(time[poster_index]),
                frame_size=[1760,680], azimuth=AZIMUTH, elevation=ELEVATION, display_half_box=half.tolist(),
                displayed_z=[bottom,0], seed_display="all sites inside the cutaway slab")
    (out/"triptych.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("input",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    render(args.input,args.output)
