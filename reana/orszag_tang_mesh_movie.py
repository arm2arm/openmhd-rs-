"""Kinematic Figure 23 comparison on a common time-resolved planar MHD flow."""
import argparse
import csv
import hashlib
import json
import struct
from pathlib import Path

import numpy as np
import scipy
from scipy.spatial import Voronoi, cKDTree


PERIOD = 2.048
RADIUS = 0.2
DT = 0.004
STEPS = 512


def centers(time):
    angle = 2 * np.pi * time / PERIOD
    displacement = 0.25 * np.array([np.cos(angle), np.sin(angle)])
    return 0.5 - displacement, 0.5 + displacement  # fine, coarse


def target_areas(points, time):
    fine, coarse = centers(time)
    inside_fine = np.sum((points - fine)**2, axis=1) < RADIUS**2
    inside_coarse = np.sum((points - coarse)**2, axis=1) < RADIUS**2
    return np.where(inside_fine, 1 / 64**2, np.where(inside_coarse, 1 / 16**2, 1 / 32**2))


def initial_points():
    j, i = np.indices((18, 32))
    grid = np.column_stack([i.ravel(), j.ravel()])
    return np.vstack([(grid + offset) / [32, 18] for offset in (0.25, 0.75)])


def diagram(points, margin=0.16):
    copies = [points]
    owners = [np.arange(len(points))]
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            shifted = points + [dx, dy]
            mask = np.all((shifted >= -margin) & (shifted <= 1 + margin), axis=1)
            copies.append(shifted[mask])
            owners.append(np.flatnonzero(mask))
    return Voronoi(np.vstack(copies)), np.concatenate(owners)


def geometry(points, margin=0.16):
    vor, owners = diagram(points, margin)
    regions = [vor.regions[k] for k in vor.point_region[:len(points)]]
    if any(len(r) < 3 or -1 in r for r in regions):
        if margin < 1:
            return geometry(points, 1.0)
        raise ValueError("unbounded periodic cell")
    sizes = np.fromiter(map(len, regions), dtype=int, count=len(points))
    row = np.repeat(np.arange(len(points)), sizes)
    vertex = vor.vertices[np.concatenate(regions)]
    local = vertex - points[row]
    # Every omitted periodic image is at least margin from a central site.
    if margin < 1 and 2 * np.sqrt(np.max(np.sum(local**2, axis=1))) >= margin:
        return geometry(points, 1.0)
    starts = np.r_[0, np.cumsum(sizes)[:-1]]
    following = np.roll(local, -1, axis=0)
    following[starts + sizes - 1] = local[starts]
    cross = local[:, 0] * following[:, 1] - local[:, 1] * following[:, 0]
    twice_area = np.add.reduceat(cross, starts)
    areas = np.abs(twice_area) / 2
    if not np.all(areas > 0) or abs(areas.sum() - 1) > 2e-10:
        raise ValueError("periodic Voronoi areas do not close")
    delta = np.add.reduceat((local + following) * cross[:, None], starts, axis=0) / (3 * twice_area[:, None])
    return areas, delta, vor, owners


def read_flow(path):
    raw = path.read_bytes()
    if raw[:8] != b"OMVFLOW1":
        raise ValueError("unrecognized flow format")
    n, count = struct.unpack_from("<II", raw, 8)
    if n != 64 or count != 129 or len(raw) != 16 + count * (1 + 2*n*n) * 8:
        raise ValueError("incomplete flow")
    values = np.frombuffer(raw, dtype="<f8", offset=16).reshape(count, -1)
    times = values[:, 0].copy()
    if not np.array_equal(times, np.arange(count) * 0.016) or not np.isfinite(values).all():
        raise ValueError("flow times or velocities")
    flow = values[:, 1:].reshape(count, n, n, 2)
    yy, xx = np.meshgrid((np.arange(n) + 0.5) / n, (np.arange(n) + 0.5) / n, indexing="ij")
    initial = np.stack([-np.sin(2*np.pi*yy), np.sin(2*np.pi*xx)], axis=-1)
    if np.max(np.abs(flow[0] - initial)) > 1e-9 or np.max(np.abs(flow[-1] - flow[0])) < 0.01:
        raise ValueError("flow initial condition, indexing or evolution")
    return times, flow, hashlib.sha256(raw).hexdigest()


def velocity(points, time, times, flow):
    k = int(np.clip(np.searchsorted(times, time, side="right") - 1, 0, len(times) - 2))
    t = (time - times[k]) / (times[k+1] - times[k])
    n = flow.shape[1]
    coords = points * n - 0.5
    ij = np.floor(coords).astype(int)
    wx, wy = (coords - ij).T
    ix, iy = (ij % n).T
    right, up = (ix + 1) % n, (iy + 1) % n
    def spatial(field):
        lower = field[iy, ix] * (1-wx[:, None]) + field[iy, right] * wx[:, None]
        upper = field[up, ix] * (1-wx[:, None]) + field[up, right] * wx[:, None]
        return lower * (1-wy[:, None]) + upper * wy[:, None]
    return (1-t) * spatial(flow[k]) + t * spatial(flow[k+1])


def adapt(points, ids, next_id, time, geom):
    areas, _, vor, owners = geom
    targets = target_areas(points, time)
    small = np.flatnonzero(areas < 0.5 * targets)
    neighbours = {i: set() for i in small}
    for a, b in owners[vor.ridge_points]:
        if a in neighbours and b in neighbours and a != b:
            neighbours[a].add(b)
            neighbours[b].add(a)
    removed = set()
    for i in sorted(small, key=lambda j: (areas[j] / targets[j], ids[j])):
        if removed.isdisjoint(neighbours[i]):
            removed.add(i)
    split = np.flatnonzero(areas > 2 * targets)
    if not removed and not len(split):
        return points, ids, next_id, 0, 0
    survivors = np.ones(len(ids), dtype=bool)
    if removed:
        survivors[list(removed)] = False
    if len(split):
        angle = 2*np.pi * np.mod(ids[split] * 0.6180339887498949, 1.0)
        nearest = cKDTree(points, boxsize=1.0).query(points[split], k=2)[0][:, 1]
        offset = np.column_stack([np.cos(angle), np.sin(angle)]) * (0.23 * nearest[:, None])
        children = (points[split] + offset) % 1
        points[split] = (points[split] - offset) % 1
        points = np.vstack([points[survivors], children])
        ids = np.r_[ids[survivors], np.arange(next_id, next_id + len(split))]
    else:
        points, ids = points[survivors], ids[survivors]
    return points, ids, next_id + len(split), len(split), len(removed)


def run(flow_path, mode, destination):
    times, flow, flow_hash = read_flow(flow_path)
    destination.mkdir()
    points = initial_points()
    ids = np.arange(len(points))
    next_id = len(ids)
    frames, particle_ids, rows = [], [], []
    total_split = total_removed = 0
    for step in range(STEPS + 1):
        time = step * DT
        geom = geometry(points)
        if mode == "adaptive" and step > 0 and step % 2 == 0:
            points, ids, next_id, added, removed = adapt(points, ids, next_id, time, geom)
            total_split += added
            total_removed += removed
            if added or removed:
                geom = geometry(points)
        areas, delta, _, _ = geom
        target = target_areas(points, time)
        if len(points) != 1152 + total_split - total_removed or len(np.unique(ids)) != len(points):
            raise ValueError("generator identity/count ledger")
        fine = areas[target == 1/64**2]
        coarse = areas[target == 1/16**2]
        if not len(fine) or not len(coarse):
            raise ValueError("empty sampling circle")
        rows.append((time, len(ids), total_split, total_removed, abs(areas.sum()-1),
                     len(fine), len(coarse), np.median(fine), np.median(coarse)))
        frames.append(points.copy())
        particle_ids.append(ids.copy())
        if step < STEPS:
            u0 = velocity(points, time, times, flow)
            u1 = velocity((points + DT * u0) % 1, (step+1)*DT, times, flow)
            # Lag the Voronoi centroid with a common relaxation time of 1/8.
            points = (points + 0.5 * DT * (u0 + u1) - np.expm1(-8*DT) * delta) % 1
    if mode == "adaptive" and (total_split == 0 or total_removed == 0):
        raise ValueError("both adaptive operations must occur")
    offsets = np.r_[0, np.cumsum([len(frame) for frame in frames])]
    np.savez_compressed(destination / "frames.npz", times=np.arange(STEPS+1)*DT, offsets=offsets,
                        points=np.vstack(frames), ids=np.concatenate(particle_ids))
    with (destination / "metrics.csv").open("w", newline="") as f:
        out = csv.writer(f)
        out.writerow(["time","cells","splits","removals","area_closure","fine_cells","coarse_cells",
                      "median_fine_area","median_coarse_area"])
        out.writerows(rows)
    record = dict(mode=mode, period=PERIOD, step=DT, frames=len(rows), splits=total_split, removals=total_removed,
                  first_cells=rows[0][1], last_cells=rows[-1][1], min_cells=min(r[1] for r in rows),
                  max_cells=max(r[1] for r in rows), max_area_defect=max(r[4] for r in rows),
                  numpy=np.__version__, scipy=scipy.__version__, flow_sha256=flow_hash,
                  code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  files={name: hashlib.sha256((destination / name).read_bytes()).hexdigest()
                         for name in ["frames.npz","metrics.csv"]})
    (destination / "mesh.json").write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("flow", type=Path)
    parser.add_argument("mode", choices=["fixed-count","adaptive"])
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    run(args.flow, args.mode, args.destination)
