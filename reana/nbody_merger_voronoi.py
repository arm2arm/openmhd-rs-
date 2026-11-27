"""Reconstruct the 3D Voronoi diagram at the saved collisionless merger times."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import scipy
from scipy.spatial import Voronoi, cKDTree


HALF = np.array([4.4, 2.8, 2.8])
SLAB_BOTTOM = -1.1
SCALE = 4096
OPTIONS = "Qbb Qc Qz"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clip_segments(lines):
    """Intersect segments with the display slab. Parallel, exterior lines are discarded."""
    start = lines[:, 0]
    delta = lines[:, 1] - start
    lower, upper = np.zeros(len(lines)), np.ones(len(lines))
    keep = np.ones(len(lines), dtype=bool)
    for axis, lo, hi in zip(range(3), [-HALF[0], -HALF[1], SLAB_BOTTOM], [HALF[0], HALF[1], 0.0]):
        origin, direction = start[:, axis], delta[:, axis]
        moving = direction != 0.0
        keep &= moving | ((origin >= lo) & (origin <= hi))
        a = np.divide(lo - origin, direction, out=np.zeros_like(origin), where=moving)
        b = np.divide(hi - origin, direction, out=np.zeros_like(origin), where=moving)
        lower = np.where(moving, np.maximum(lower, np.minimum(a, b)), lower)
        upper = np.where(moving, np.minimum(upper, np.maximum(a, b)), upper)
    keep &= upper > lower
    trimmed = start[keep, None, :] + np.stack([lower[keep], upper[keep]], axis=1)[:, :, None] * delta[keep, None, :]
    return trimmed[np.linalg.norm(trimmed[:, 1] - trimmed[:, 0], axis=1) > 1e-10]


def face_edges(diagram, sites):
    """Order each real-real face in its own plane, returning directed vertex pairs and face IDs."""
    take = np.flatnonzero(np.all(diagram.ridge_points < len(sites), axis=1))
    pairs = diagram.ridge_points[take]
    polygons = [diagram.ridge_vertices[i] for i in take]
    counts = np.array([len(poly) for poly in polygons])
    vertices = np.concatenate(polygons)
    if counts.min() < 3 or vertices.min() < 0:
        raise ValueError("unbounded or invalid real face")
    starts = np.r_[0, np.cumsum(counts)[:-1]]
    faces = np.repeat(np.arange(len(pairs)), counts)
    coords = diagram.vertices[vertices]
    centers = np.add.reduceat(coords, starts) / counts[:, None]
    normal = sites[pairs[:, 1]] - sites[pairs[:, 0]]
    normal /= np.linalg.norm(normal, axis=1)[:, None]
    first = np.cross(normal, np.eye(3)[np.argmin(np.abs(normal), axis=1)])
    second = np.cross(normal, first)
    local = coords - centers[faces]
    angle = np.arctan2(np.sum(local * second[faces], axis=1), np.sum(local * first[faces], axis=1))
    ordered = vertices[np.lexsort((angle, faces))]
    following = np.roll(ordered, -1)
    following[starts + counts - 1] = ordered[starts]
    return np.column_stack([ordered, following]), faces, normal


def plane_sections(vertices, edges, faces, normals):
    """Intersect convex Voronoi faces with z=0, including contacts on existing vertices."""
    a, b = vertices[edges[:, 0]], vertices[edges[:, 1]]
    za, zb = a[:, 2], b[:, 2]
    cross = ((za < 0) & (zb > 0)) | ((za > 0) & (zb < 0))
    t = za[cross] / (za[cross] - zb[cross])
    points = np.vstack([a[cross] + t[:, None] * (b[cross] - a[cross]), a[za == 0]])
    owners = np.r_[faces[cross], faces[za == 0]]
    points[:, 2] = 0.0
    tangent = np.column_stack([-normals[:, 1], normals[:, 0]])
    # A face lying in the cutting plane has its outline supplied by its incident faces.
    keep = np.any(tangent[owners] != 0, axis=1)
    points, owners = points[keep], owners[keep]
    if not len(owners):
        return np.empty((0, 2, 3))
    direction = np.sum(points[:, :2] * tangent[owners], axis=1)
    order = np.lexsort((direction, owners))
    owners, points = owners[order], points[order]
    first = np.r_[0, np.flatnonzero(np.diff(owners)) + 1]
    last = np.r_[first[1:] - 1, len(points) - 1]
    return clip_segments(np.stack([points[first], points[last]], axis=1))


def mesh(sites):
    """Distant guards close unbounded hull cells and provably cannot win in the visible box."""
    if not np.isfinite(sites).all() or len(np.unique(sites, axis=0)) != len(sites):
        raise ValueError("nonfinite or coincident generator")
    radius = 4.0 * max(float(np.abs(sites).max()), float(HALF.max()))
    guards = radius * np.array(list(itertools.product([-1, 1], repeat=3)))
    guard_distance = np.linalg.norm(np.abs(guards[0]) - HALF)
    real_upper_bound = np.linalg.norm(HALF) + np.linalg.norm(sites, axis=1).min()
    if guard_distance <= real_upper_bound:
        raise ValueError("external guards could influence the displayed geometry")
    diagram = Voronoi(np.vstack([sites, guards]), qhull_options=OPTIONS)
    for region_id in diagram.point_region[:len(sites)]:
        if region_id < 0 or not diagram.regions[region_id] or -1 in diagram.regions[region_id]:
            raise ValueError("real generator lacks a bounded region in the auxiliary diagram")
    edges, faces, normals = face_edges(diagram, sites)
    undirected = np.unique(np.sort(edges, axis=1), axis=0)
    wire = clip_segments(diagram.vertices[undirected])
    cut = plane_sections(diagram.vertices, edges, faces, normals)
    return wire, cut


def nearest_gap(sites_tree, segments, multiplicity):
    # Check both interior quarter points and the midpoint against an independent nearest-site query.
    if len(segments) == 0:
        raise ValueError("empty displayed geometry")
    a, b = segments[:, 0], segments[:, 1]
    samples = np.vstack([(3*a+b)/4, (a+b)/2, (a+3*b)/4])
    distances, _ = sites_tree.query(samples, k=multiplicity)
    gap = float(np.max((distances[:, -1] - distances[:, 0]) / np.maximum(1, distances[:, 0])))
    if not np.isfinite(gap) or gap > 2e-8:
        raise ValueError(f"nearest-site tie failure ({multiplicity} sites, gap {gap:g})")
    return gap


def tetrahedron_control():
    # Four sites of identical radius have the two coordinate axes as their z=0 boundaries.
    tetra = np.array([[1,1,1], [1,-1,-1], [-1,1,-1], [-1,-1,1]], dtype=float)
    wire, cut = mesh(tetra)
    if not np.all(np.min(np.max(np.abs(cut[:, :, :2]), axis=1), axis=1) < 1e-9):
        raise ValueError("tetrahedron cut does not follow the coordinate axes")
    expected_tips = np.array([[HALF[0],0], [-HALF[0],0], [0,HALF[1]], [0,-HALF[1]]])
    tips = cut[:, :, :2].reshape(-1, 2)
    length = np.linalg.norm(cut[:, 1] - cut[:, 0], axis=1).sum()
    if not np.all(cKDTree(tips).query(expected_tips)[0] < 1e-9) or abs(length-2*HALF[:2].sum()) > 1e-9:
        raise ValueError("tetrahedron section endpoint or length")
    nearest_gap(cKDTree(tetra), wire, 3)
    nearest_gap(cKDTree(tetra), cut, 2)


def offset_control():
    # Equal squared *3D* distances put the cut at x=1/4, displaced from the projected bisector.
    _, offset = mesh(np.array([[-1,0,0], [1,0,1]], dtype=float))
    if len(offset) != 1 or not np.allclose(offset[:, :, 0], 0.25, atol=1e-10, rtol=0) or not np.allclose(
            np.sort(offset[0, :, 1]), [-HALF[1], HALF[1]], atol=1e-10, rtol=0):
        raise ValueError("unequal-height two-site plane section")


def frame_offsets(frames):
    return np.r_[0, np.cumsum([len(frame) for frame in frames])]


def reconstruct(trajectory, run, out):
    source = json.loads(run.read_bytes())
    if (source["mode"] != "merger" or source["particle_count"] != 200
            or source["files"]["trajectory.npz"] != digest(trajectory)):
        raise ValueError("trajectory/parent identity")
    with np.load(trajectory, allow_pickle=False) as data:
        time, pos, ids, population = (data[k] for k in ("time", "position", "particle_id", "population"))
    if (pos.shape != (321, 200, 3) or not np.array_equal(time, np.arange(321)*0.125)
            or len(np.unique(ids)) != 200 or not np.array_equal(np.bincount(population), [100,100])):
        raise ValueError("source frame, clock or population")
    wireframes, sections = [], []
    max_gap = np.zeros(2)
    for sites in pos:
        wire, cut = mesh(sites)
        tree = cKDTree(sites)
        checks = [nearest_gap(tree, wire, 3), nearest_gap(tree, cut, 2)]
        max_gap = np.maximum(max_gap, checks)
        wireframes.append(np.rint(wire*SCALE).astype("<i2"))
        sections.append(np.rint(cut*SCALE).astype("<i2"))
    out.mkdir()
    archive = out / "voronoi.npz"
    np.savez_compressed(archive, time=time, particle_id=ids, scale=SCALE, half_box=HALF,
                        slab_bottom=SLAB_BOTTOM, wire=np.concatenate(wireframes), wire_offsets=frame_offsets(wireframes),
                        cut=np.concatenate(sections), cut_offsets=frame_offsets(sections))
    report = dict(trajectory_sha256=digest(trajectory), geometry_sha256=digest(archive),
                  driver_sha256=digest(Path(__file__)), frames=len(time), sites_per_frame=len(ids),
                  scipy=scipy.__version__, numpy=np.__version__, qhull_options=OPTIONS,
                  bounds_xyz_half=HALF.tolist(), displayed_z=[SLAB_BOTTOM,0], section_z=0,
                  max_scaled_nearest_site_gap=dict(edge=max_gap[0], section=max_gap[1]),
                  samples_per_segment=3, coordinate_quantum=1/SCALE,
                  wire_segments=sum(map(len,wireframes)), section_segments=sum(map(len,sections)))
    (out / "voronoi.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    tasks = parser.add_subparsers(dest="task", required=True)
    check = tasks.add_parser("control")
    check.add_argument("fixture", choices=("tetrahedron", "offset"))
    movie = tasks.add_parser("reconstruct")
    for name in ("trajectory", "run", "out"):
        movie.add_argument(name, type=Path)
    args = parser.parse_args()
    if args.task == "control":
        {"tetrahedron": tetrahedron_control, "offset": offset_control}[args.fixture]()
        print("Passed", args.fixture)
    else:
        reconstruct(args.trajectory, args.run, args.out)
