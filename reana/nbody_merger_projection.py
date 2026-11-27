"""Project the measured 200-particle trajectory using its softened mass kernel."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project(trajectory, run, out):
    source = json.loads(run.read_bytes())
    if source["mode"] != "merger" or source["particle_count"] != 200 or sha(trajectory) != source["files"]["trajectory.npz"]:
        raise ValueError("merger trajectory identity")
    with np.load(trajectory, allow_pickle=False) as data:
        times, positions, masses = (data[k] for k in ("time", "position", "mass"))
    ny, nx = 112, 176
    extent = [-4.4, 4.4, -2.8, 2.8]
    dx = (extent[1] - extent[0]) / nx
    dy = (extent[3] - extent[2]) / ny
    gx = extent[0] + (np.arange(nx) + 0.5) * dx
    gy = extent[2] + (np.arange(ny) + 0.5) * dy
    eps2 = source["epsilon"] ** 2
    values = np.empty((len(times), ny, nx), dtype=np.float32)
    for i, p in enumerate(positions):
        field = np.zeros((ny, nx))
        for (x, y, _), mass in zip(p, masses):
            s2 = (gx[None, :] - x) ** 2 + (gy[:, None] - y) ** 2 + eps2
            field += mass * eps2 / (np.pi * s2 ** 2)
        if not np.isfinite(field).all() or np.min(field) <= 0:
            raise ValueError("positive finite projected surface density")
        values[i] = field
    peak = float(values.max())
    floor = peak / 1000
    # Store display levels compactly; both timing and the global log scale are fixed.
    levels = np.rint(255 * np.clip(np.log(values / floor) / np.log(peak / floor), 0, 1)).astype("u1")
    out.mkdir()
    np.savez_compressed(out / "density.npz", levels=levels, time=times, extent=extent,
                        floor=floor, peak=peak)
    report = dict(method="line-of-sight integral of the Plummer mass kernel along z",
                  units="code mass per square code length", trajectory_sha256=sha(trajectory),
                  levels_sha256=sha(out / "density.npz"), frames=len(times), grid_yx=[ny,nx],
                  extent_xy=extent, pixel_centres=True, softening=source["epsilon"],
                  peak=peak, floor=floor, encoding="uint8, 0..255 spans three decades, logarithmic")
    (out / "density.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("trajectory", "run", "out"):
        p.add_argument(name, type=Path)
    args = p.parse_args()
    project(args.trajectory, args.run, args.out)
