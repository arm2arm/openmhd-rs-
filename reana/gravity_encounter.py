"""Run an isolated orbit control or a low-N encounter using the Rust KDK binary."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess

import numpy as np

EPS = 0.25
STRIDE = 20


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binary_orbit():
    radius = 0.7
    omega = math.sqrt(2 / ((2 * radius) ** 2 + EPS ** 2) ** 1.5)
    x = np.array([[-radius, 0, 0], [radius, 0, 0]])
    v = np.array([[0, -radius * omega, 0], [0, radius * omega, 0]])
    return x, v, np.arange(2), np.ones(2), 2 * math.pi / omega / 4096, 4096, 32


def encounter():
    # Two cold, mutually inclined particle groups. Break regular ring symmetry
    # deterministically and subtract each group's mean before adding its drift.
    positions, velocities = [], []
    for group in range(2):
        p, v = [], []
        for i in range(32):
            ring, slot = divmod(i, 8)
            phi = 2 * math.pi * slot / 8 + 0.31 * ring + 0.19 * group + 0.073 * math.sin(1.7 * i + group)
            r = (0.18 + 0.165 * ring) * (1 + 0.073 * math.cos(i * 2.3 + group))
            height = 0.050 * math.sin(i * 2.71 + 0.8 + group)
            enclosed = (ring + 0.7) / 4
            speed = 0.88 * math.sqrt(enclosed * r**2 / (r*r + EPS*EPS)**1.5)
            p.append([r * math.cos(phi), r * math.sin(phi), height])
            v.append([-speed * math.sin(phi), speed * math.cos(phi), 0.036 * math.cos(i * 1.93)])
        tilt = (0.43, -0.74)[group]
        azimuth = (-0.18, 0.58)[group]
        c, s = math.cos(tilt), math.sin(tilt)
        u, w = math.cos(azimuth), math.sin(azimuth)
        rotation = np.array([[u, -w*c, w*s], [w, u*c, -u*s], [0, s, c]])
        sign = (1, -1)[group]
        positions.extend((p - np.mean(p, axis=0)) @ rotation.T + sign * np.array([-1.05, -0.20, 0]))
        velocities.extend((v - np.mean(v, axis=0)) @ rotation.T + sign * np.array([0.36, -0.26, 0.045]))
    return np.array(positions), np.array(velocities), np.repeat([0, 1], 32), np.full(64, 1/32), 1/512, 2560, STRIDE


def run(case, binary, output):
    x0, v0, groups, masses, dt, steps, stride = binary_orbit() if case == "binary" else encounter()
    ids = np.arange(1, len(masses) + 1)
    output.mkdir()
    initial = output / "initial.txt"
    np.savetxt(initial, np.column_stack((ids, groups, masses, x0, v0)),
               fmt=["%d", "%d"] + ["%.17g"] * 7,
               header="id population mass x y z vx vy vz")
    raw = output / "raw"
    subprocess.run([str(binary.resolve()), str(initial), str(EPS), str(dt), str(steps),
                    str(stride), str(raw)], check=True, timeout=600)
    data = np.loadtxt(raw / "particles.csv", delimiter=",", skiprows=1).reshape(-1, len(masses), 14)
    ledger = np.loadtxt(raw / "conservation.csv", delimiter=",", skiprows=1)
    step = np.arange(0, steps+1, stride)
    t = data[:, 0, 1]
    require(np.isfinite(data).all() and np.isfinite(ledger).all(), "finite trajectory and ledger")
    require(np.array_equal(data[:, :, 0], np.broadcast_to(step[:, None], data.shape[:2]))
            and np.all(data[:, :, 1] == t[:, None]) and np.array_equal(ledger[:, 1], t)
            and np.array_equal(ledger[:, 0], step) and np.max(abs(t-step*dt)) < 1e-11, "common clock")
    require(np.all(data[:, :, 2] == ids) and np.all(data[:, :, 3] == groups)
            and np.all(data[:, :, 4] == masses), "persistent particle identities and masses")
    x, v, a = data[:, :, 5:8], data[:, :, 8:11], data[:, :, 11:14]
    require(np.array_equal(x[0], x0) and np.allclose(v[0], v0, atol=0, rtol=2e-15), "initial state")
    # Independent double-precision evaluation on every recorded endpoint.
    err = 0.0
    for p, acceleration in zip(x, a):
        delta = p[None, :, :] - p[:, None, :]
        pair = masses[None, :, None] * delta / (np.sum(delta**2, axis=2) + EPS**2)[:, :, None]**1.5
        scale = np.linalg.norm(pair, axis=2).sum(axis=1)
        err = max(err, float(np.max(np.linalg.norm(pair.sum(axis=1) - acceleration, axis=1) / scale)))
    eerr = float(np.max(abs(ledger[:, 5] - ledger[0, 5])) / abs(ledger[0, 5]))
    perr = float(np.linalg.norm(ledger[:, 6:9] - ledger[0, 6:9], axis=1).max())
    lerr = float(np.linalg.norm(ledger[:, 9:12] - ledger[0, 9:12], axis=1).max())
    require(np.all(ledger[:, 2] == sum(masses)) and err < 1e-12 and eerr < 5e-4
            and perr < 1e-12 and lerr < 1e-10, "force or conservation cross-check")
    report = dict(case=case, g=1, epsilon=EPS, units="dimensionless", boundary="isolated",
                  binary_sha256=sha(binary), initial_sha256=sha(initial), particles=len(ids),
                  steps=steps, dt=dt, stride=stride, frames=len(t), end_time=float(t[-1]),
                  maximum_relative_energy_drift=eerr, maximum_momentum_drift=perr,
                  maximum_angular_momentum_drift=lerr, maximum_scaled_force_error=err)
    if case == "binary":
        omega = math.sqrt(2 / (1.4**2 + EPS**2)**1.5)
        analytic = np.column_stack((np.cos(t*omega), np.sin(t*omega), np.zeros_like(t)))
        deviation = np.linalg.norm(x - x0[None, :, :1] * analytic[:, None, :], axis=2).max()/0.7
        require(deviation < 2e-5, "one-period softened binary orbit")
        report["max_position_error_over_orbit_radius"] = float(deviation)
    if case == "encounter":
        com = np.stack([np.average(x[:, groups == k, :], weights=masses[groups == k], axis=1) for k in (0, 1)])
        gap = np.linalg.norm(com[0] - com[1], axis=-1)
        report["centroid_separation"] = dict(initial=float(gap[0]), minimum=float(gap.min()),
                                              time_of_minimum=float(t[gap.argmin()]), final=float(gap[-1]))
    arrays = output / "trajectory.npz"
    np.savez_compressed(arrays, step=step, time=t, ids=ids, population=groups, mass=masses,
                        position=x, velocity=v, acceleration=a, epsilon=EPS, g=1.0)
    report["trajectory_sha256"] = sha(arrays)
    report["conservation_sha256"] = sha(raw / "conservation.csv")
    (output / "run.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=("binary", "encounter"))
    parser.add_argument("binary", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.case, args.binary, args.output)
