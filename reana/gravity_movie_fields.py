"""Derive a physical midplane density and real 3D Voronoi sections from Rust endpoints."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import struct
import subprocess

import numpy as np


def check(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def half_extent(position):
    # One axis-aligned box encloses every particle at every saved time.
    return np.ceil(4 * (np.abs(position).max(axis=(0, 1)) + 0.25)) / 4


def fields(data, out):
    x, masses, eps = data["position"], data["mass"], float(data["epsilon"])
    half = float(max(half_extent(x)[:2]))
    n = 240
    axes = (np.arange(n) + 0.5) * (2 * half / n) - half
    xx, yy = np.meshgrid(axes, axes)
    low, high = 1e-4, 32.0
    images, peaks, ranges = [], [], []
    # -div(g)/(4 pi G) for the same 3D Plummer force used by the Rust run.
    # Evaluate at z=0. Each particle's 3D density kernel integrates to its mass.
    prefactor = 3 * eps**2 / (4 * np.pi)
    for p in x:
        rho = np.zeros_like(xx)
        for m, (px, py, pz) in zip(masses, p):
            rho += prefactor * m / ((xx-px)**2 + (yy-py)**2 + pz*pz + eps*eps)**2.5
        check(np.isfinite(rho).all() and np.all(rho > 0), "positive finite density")
        ranges.append([rho.min(), rho.max()])
        peaks.append(float(rho.max()))
        normalized = np.clip(np.log(rho/low) / np.log(high/low), 0, 1)
        images.append(np.rint(normalized * 255).astype(np.uint8))
    np.savez_compressed(out / "density.npz", image=images, extent=half, axes=axes,
                        low=low, high=high, time=data["time"], peak=peaks)
    return dict(grid=n, plane_z=0, kernel="3 m epsilon^2 / (4 pi (r^2 + epsilon^2)^(5/2))",
                density_units="mass / length^3", extent=half, display_bounds=[low,high],
                min_density=float(np.min(ranges)), max_density=float(np.max(ranges)),
                density_sha256=sha(out / "density.npz"))


def word(x):
    return struct.pack(">d", x).hex()


def number(bits):
    return struct.unpack(">d", bytes.fromhex(bits))[0]


def sections(polygon, heights):
    result = []
    after = np.roll(polygon, -1, axis=0)
    for level, z in enumerate(heights):
        a, b = polygon[:, 2] - z, after[:, 2] - z
        crossing = ((a <= 0) & (b > 0)) | ((a > 0) & (b <= 0))
        if not np.any(crossing):
            continue
        t = -a[crossing] / (b[crossing] - a[crossing])
        points = polygon[crossing] + t[:, None] * (after[crossing] - polygon[crossing])
        if len(points) >= 2:
            distances = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=2)
            i, j = np.unravel_index(np.argmax(distances), distances.shape)
            if distances[i, j] > 1e-12:
                result.append((level, points[[i, j]]))
    return result


def mesh_frame(frame, pos, ids, half, tracked, levels, binary, out):
    rect = lambda v: " ".join(word(x) for x in v)
    rows = ["openmhd-geometry3-input-v1", f"case encounter_{frame:04}", "boundary bounded",
            "anchor "+rect(-half), "width "+rect(2*half), f"count {len(ids)}"]
    owner_keys = [f"{1:016x}{int(i):016x}" for i in ids]
    for key, p in zip(owner_keys, pos):
        rows.append(f"generator {key} {rect(p)} 0 0 0")
    initial = out / f"geometry-{frame:04}.in"
    initial.write_text("\n".join([*rows, "end", ""]))
    job = subprocess.run([str(binary.resolve()), str(initial)], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, timeout=180)
    if job.returncode:
        raise RuntimeError(f"geometry frame {frame} returned {job.returncode}: {job.stderr.decode()[:1600]}")
    text = job.stdout.decode().splitlines()
    check(text[0] == "openmhd-geometry3-candidate-v1" and "status complete" in text
          and text[-1] == "end" and f"case encounter_{frame:04}" in text, "complete mesh transcript")
    tokens = [line.split() for line in text]
    check([r[1:] for r in tokens if r[0]=="input_generator"] ==
          [line.split()[1:] for line in rows if line.startswith("generator ")], "mesh generator words")
    cells = [r for r in tokens if r[0]=="cell"]
    check([r[1] for r in cells] == owner_keys, "sorted persistent mesh sites")
    volumes = np.array([number(r[2]) for r in cells])
    box_volume = np.prod(2*half)
    closure = abs(volumes.sum()-box_volume)/box_volume
    check(np.all(volumes>0) and closure<1e-9, "positive complete Voronoi partition")
    counts = next(r for r in tokens if r[0]=="counts")
    faces = [r for r in tokens if r[0]=="face"]
    check([int(counts[1]), int(counts[2])] == [len(ids), len(faces)], "face inventory")
    vertices = iter(r for r in tokens if r[0]=="vertex")
    lines, cages, face_edges, max_plane = [], [], [], 0.0
    for k, face in enumerate(faces):
        left = int(face[2])
        right = int(face[4]) if face[3]=="some" else None
        check(int(face[1])==k, "ordered faces")
        verts = [next(vertices) for _ in range(int(face[-1]))]
        check(all(int(row[1])==k and int(row[2])==j for j,row in enumerate(verts)), "polygon offsets")
        poly = pos[left] + np.array([[number(w) for w in row[3:6]] for row in verts])
        check(np.isfinite(poly).all() and np.all(np.abs(poly)<=half+1e-9), "bounded polygon")
        if right is not None:
            a = np.sum((poly-pos[left])**2,axis=1)
            b = np.sum((poly-pos[right])**2,axis=1)
            max_plane = max(max_plane, float(np.max(abs(a-b))))
        lines.extend(sections(poly,levels))
        face_edges.append(np.stack((poly, np.roll(poly, -1, axis=0)), axis=1))
        for idx in (left,right):
            if idx is not None and int(ids[idx]) in tracked:
                cages.append((int(ids[idx]),poly))
    check(next(vertices,None) is None and max_plane<1e-8*float(max(half))**2, "true 3D bisectors")
    check(set(i for i,_ in cages)==set(tracked), "complete tracked cells")
    # A shared edge belongs to several faces. Index its unordered endpoints
    # once at display precision, after all double-precision polygon checks.
    endpoints = np.concatenate(face_edges).reshape(-1, 3).astype("float32")
    points, inverse = np.unique(endpoints, axis=0, return_inverse=True)
    pairs = np.unique(np.sort(inverse.reshape(-1, 2), axis=1), axis=0)
    wire = points[pairs]
    return lines, cages, wire, volumes, dict(frame=frame, faces=len(faces), relative_volume_closure=float(closure),
            max_squared_bisector_residual=max_plane, input_sha256=sha(initial),
            transcript_sha256=hashlib.sha256(job.stdout).hexdigest())


def mesh(data, out, begin, end, binary):
    pos, ids = data["position"], data["ids"]
    check(0<=begin<end<=len(pos), "snapshot interval")
    bounds = half_extent(pos)
    levels = np.array([-0.24, 0.0, 0.24])
    tracked = [3, 35]
    def one(index):
        return mesh_frame(index, pos[index], ids, bounds, tracked, levels, binary, out)
    li, li_frame, li_level = [], [], []
    vertices, offsets, owner, face_frame = [], [0], [], []
    volumes, metrics, wires, wire_frames = [], [], [], []
    with ThreadPoolExecutor(max_workers=2) as pool:
        for frame,(sections_, cages, wire, volume, checks) in zip(range(begin,end), pool.map(one,range(begin,end))):
            wires.append(wire)
            wire_frames.append(np.full(len(wire), frame, dtype="int16"))
            for level, segment in sections_:
                li.append(segment); li_frame.append(frame); li_level.append(level)
            for tracked_id, polygon in cages:
                vertices.extend(polygon); offsets.append(len(vertices)); owner.append(tracked_id); face_frame.append(frame)
            volumes.append(volume); metrics.append(checks)
    # Convert coordinates to binary32 only for display after checking the binary64 export.
    np.savez_compressed(out/"mesh.npz", line=np.array(li,dtype="float32"), line_frame=np.array(li_frame,dtype="int16"),
            line_level=np.array(li_level,dtype="int8"), face_vertex=np.array(vertices,dtype="float32"),
            face_offset=offsets, face_frame=face_frame, face_id=owner, volumes=volumes, tracked=tracked,
            levels=levels, half=bounds, wire=np.concatenate(wires), wire_frame=np.concatenate(wire_frames),
            time=data["time"][begin:end], frames=np.arange(begin,end))
    return dict(begin=begin, end=end, geometry_binary_sha256=sha(binary), mesh_sha256=sha(out/"mesh.npz"),
                domain_halfwidth=bounds.tolist(), tracked_ids=tracked, section_heights=levels.tolist(), checks=metrics)


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=["fields","mesh"])
    p.add_argument("trajectory",type=Path)
    p.add_argument("output",type=Path)
    p.add_argument("--binary",type=Path)
    p.add_argument("--interval",nargs=2,type=int)
    a=p.parse_args()
    a.output.mkdir()
    with np.load(a.trajectory,allow_pickle=False) as data:
        if a.mode=="fields":
            report=fields(data,a.output)
        else:
            report=mesh(data,a.output,*a.interval,a.binary)
    report["trajectory_sha256"]=sha(a.trajectory)
    (a.output/"report.json").write_text(json.dumps(report,indent=2)+"\n")
