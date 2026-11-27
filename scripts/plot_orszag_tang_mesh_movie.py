"""Render the acquired REANA point histories as a comparison movie and four snapshots."""
import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as effects
import numpy as np
from PIL import Image
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Circle

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "reana"))
from orszag_tang_mesh_movie import PERIOD, RADIUS, centers, geometry


INK = "#192b35"
MUTED = "#48616c"
EDGES = "#384952"
FINE = "#1764ad"
COARSE = "#b13c22"
PAPER = "#faf9f5"


class Frames:
    def __init__(self, folder, mode):
        self.record = json.loads((folder/"mesh.json").read_text())
        for name in ["frames.npz", "metrics.csv"]:
            if hashlib.sha256((folder/name).read_bytes()).hexdigest() != self.record["files"][name]:
                raise ValueError(f"changed {mode} artifact {name}")
        with np.load(folder/"frames.npz", allow_pickle=False) as data:
            self.times = data["times"]
            self.offsets = data["offsets"]
            self.points = data["points"]
        with (folder/"metrics.csv").open() as f:
            self.metrics = list(csv.DictReader(f))
        if (self.record["mode"] != mode or len(self.times) != self.record["frames"]
                or len(self.metrics) != len(self.times) or self.offsets[-1] != len(self.points)
                or np.any(np.diff(self.offsets) != [int(r["cells"]) for r in self.metrics])):
            raise ValueError(f"incomplete {mode} trajectory")

    def at(self, k):
        return self.points[self.offsets[k]:self.offsets[k+1]]


def segments(points):
    _, _, vor, owners = geometry(points)
    a, b = vor.ridge_points.T
    # Give each periodic face to its lower-indexed central generator, then
    # draw every copy intersecting the visible square, including corner pieces.
    owned = ((a < len(points)) & (owners[a] < owners[b])) | ((b < len(points)) & (owners[b] < owners[a]))
    vertices = np.asarray(vor.ridge_vertices)[owned]
    if np.any(vertices < 0):
        raise ValueError("unbounded central face")
    edges = vor.vertices[vertices]
    visible = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            lines = edges + [dx, dy]
            keep = ((lines.max(axis=1) >= 0) & (lines.min(axis=1) <= 1)).all(axis=1)
            visible.append(lines[keep])
    return np.concatenate(visible)


def panel(fig, box, linewidth):
    ax = fig.add_axes(box, facecolor="white", aspect="equal")
    ax.set(xlim=(0,1), ylim=(0,1), xticks=[], yticks=[])
    for side in ax.spines.values():
        side.set(linewidth=0.8, color="#8d9b9c")
    lines = LineCollection([], colors=EDGES, linewidths=linewidth, capstyle="round")
    ax.add_collection(lines)
    rings = []
    for color in [FINE, COARSE]:
        circle = Circle((0,0), RADIUS, fill=False, edgecolor=color, linewidth=1.55,
                        linestyle=(0,(3.8,2.4)), zorder=3)
        circle.set_path_effects([effects.Stroke(linewidth=2.6,foreground="white"), effects.Normal()])
        ax.add_patch(circle)
        rings.append(circle)
    return lines, rings


def draw_panel(artists, archive, k):
    lines, rings = artists
    lines.set_segments(segments(archive.at(k)))
    for ring, center in zip(rings, centers(archive.times[k])):
        ring.center = center


def label(fig, x, y, value, size, color=INK, **opts):
    return fig.text(x,y,value,fontsize=size,color=color,va="center",**opts)


def legend(fig, x, y, width, color, text):
    fig.add_artist(Line2D([x,x+width], [y,y], transform=fig.transFigure,
                          color=color, lw=1.8, ls=(0,(3.8,2.4))))
    label(fig,x+width+0.009,y,text,10.0,color)


def movie(fixed, adaptive, path):
    fig = plt.figure(figsize=(12.8,8),dpi=112.5,facecolor=PAPER)
    label(fig,.047,.938,"Orszag–Tang vortex",29,family="DejaVu Serif")
    label(fig,.048,.885,"Two moving Voronoi meshes in the same 2D MHD velocity field",12,MUTED)
    stamp = label(fig,.953,.933,"",20,ha="right",family="DejaVu Sans Mono")
    label(fig,.953,.885,"one orbit  ·  T = 2.048",10,MUTED,ha="right")
    boxes = [(.047,.145,.431,.6896),(.522,.145,.431,.6896)]
    panels = [panel(fig,box,.43) for box in boxes]
    for box, title in zip(boxes,["Fixed cell count","Local refinement and derefinement"]):
        label(fig,box[0],.855,title,12.2,weight="bold")
    counts = [label(fig,box[0],.116,"",11,weight="bold") for box in boxes]
    ledger = label(fig,.953,.116,"",9.5,MUTED,ha="right")
    legend(fig,.047,.063,.028,FINE,"Finer target   1/64²")
    legend(fig,.290,.063,.028,COARSE,"Coarser target   1/16²")
    label(fig,.953,.063,"Periodic unit square   ·   default target 1/32²",10,MUTED,ha="right")
    progress = Line2D([.047,.047],[.022,.022],transform=fig.transFigure,lw=1.8,color=FINE)
    fig.add_artist(Line2D([.047,.953],[.022,.022],transform=fig.transFigure,lw=1,color="#c6d1d1"))
    fig.add_artist(progress)
    fig.canvas.draw()
    width,height=fig.canvas.get_width_height()
    command=["ffmpeg","-nostdin","-v","error","-y","-f","rawvideo","-pix_fmt","rgba",
             "-s",f"{width}x{height}","-r","30","-i","pipe:0","-an","-c:v","libx264",
             "-preset","medium","-crf","21","-maxrate","11M","-bufsize","22M",
             "-pix_fmt","yuv420p","-movflags","+faststart","-metadata","title=Orszag-Tang moving-mesh comparison",str(path)]
    try:
        with subprocess.Popen(command,stdin=subprocess.PIPE) as encoder:
            for k,time in enumerate(fixed.times):
                for artists, data, count in zip(panels,[fixed,adaptive],counts):
                    draw_panel(artists,data,k)
                    count.set_text(f"{int(data.metrics[k]['cells']):,} cells")
                row=adaptive.metrics[k]
                ledger.set_text(f"{int(row['splits']):,} splits   ·   {int(row['removals']):,} removals")
                stamp.set_text(f"t = {time:.3f}")
                progress.set_xdata([.047,.047+.906*time/PERIOD])
                fig.canvas.draw()
                frame = np.asarray(fig.canvas.buffer_rgba())
                if frame.shape != (height, width, 4):
                    raise ValueError("canvas dimensions changed during encoding")
                if abs(time - 0.768) < 1e-12:
                    Image.fromarray(frame[:, :, :3]).save(path.with_name("refinement-preview.jpg"), quality=92)
                repeat=16 if k==0 else 30 if k==len(fixed.times)-1 else 1
                for _ in range(repeat):
                    encoder.stdin.write(frame)
            encoder.stdin.close()
            if encoder.wait():
                raise RuntimeError("FFmpeg failed to encode the time series")
    finally:
        plt.close(fig)


def poster(data, path):
    fig = plt.figure(figsize=(10.8,12.0),dpi=150,facecolor=PAPER)
    label(fig,.060,.955,"One orbit of local mesh refinement",25,family="DejaVu Serif")
    label(fig,.061,.914,"Orszag–Tang vortex   ·   four snapshots at the times in Figure 23",11.2,MUTED)
    positions=[(.061,.512),(.527,.512),(.061,.100),(.527,.100)]
    for time,(x,y) in zip([.128,.256,.768,1.572],positions):
        k, = np.flatnonzero(np.isclose(data.times,time,rtol=0,atol=2e-15))
        box=(x,y,.413,.3717)
        draw_panel(panel(fig,box,.41),data,k)
        label(fig,x,y-.018,f"t = {time:.3f}",11.5,weight="bold")
        label(fig,x+.413,y-.018,f"{int(data.metrics[k]['cells']):,} cells",10,MUTED,ha="right")
    legend(fig,.061,.039,.028,FINE,"Finer target")
    legend(fig,.309,.039,.028,COARSE,"Coarser target")
    label(fig,.940,.039,"OpenMHD-RS planar flow   ·   passive mesh replay",9.5,MUTED,ha="right")
    fig.savefig(path,dpi=150,facecolor=fig.get_facecolor())
    plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("data",type=Path)
    p.add_argument("destination",type=Path)
    args=p.parse_args()
    fixed,adaptive=[Frames(args.data/mode,mode) for mode in ["fixed-count","adaptive"]]
    if (fixed.record["flow_sha256"]!=adaptive.record["flow_sha256"] or not np.array_equal(fixed.times,adaptive.times)
            or not np.array_equal(fixed.at(0),adaptive.at(0)) or len(fixed.times)!=513):
        raise ValueError("the two histories must share an initial mesh, actual flow and clock")
    args.destination.mkdir(parents=True,exist_ok=True)
    poster(adaptive,args.destination/"refinement-snapshots.png")
    movie(fixed,adaptive,args.destination/"refinement-comparison.mp4")


if __name__ == "__main__":
    main()
