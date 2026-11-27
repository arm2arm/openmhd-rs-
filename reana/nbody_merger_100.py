"""Reproduce the isolated control or 100+100 collisionless merger with gravity-trajectory."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np


N = 100
SCALE = 0.55
CUTOFF = 4 * SCALE
EPS = 0.25
DT = 1 / 256
STEPS = 10240
STRIDE = 32
CORE = 20
SEEDS = (20261127, 20261128)
BULK_X = np.array([[-2.5, 0, 0], [2.5, 0, 0]])
BULK_V = np.array([[0.12, 0.14, 0.05], [-0.12, -0.14, -0.05]])


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    with path.open("rb") as stream:
        h = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def directions(rng, n):
    vec = rng.normal(size=(n, 3))
    return vec / np.linalg.norm(vec, axis=1)[:, None]


def pair_fields(x, mass):
    """An independent array pair sum, excluding self from the potential."""
    delta = x[None, :, :] - x[:, None, :]
    distance2 = np.einsum("ijk,ijk->ij", delta, delta)
    inv = 1 / np.sqrt(distance2 + EPS ** 2)
    np.fill_diagonal(inv, 0)
    coeff = inv ** 3 * mass[None, :]
    pair = delta * coeff[:, :, None]
    phi = -(inv @ mass)
    virial = -0.5 * (mass @ np.sum(coeff * distance2, axis=1))
    return pair.sum(axis=1), phi, virial, np.linalg.norm(pair, axis=2).sum(axis=1)


def progenitor(seed):
    # Stratified enclosed-mass fractions, with antipodal pairs for a quiet start.
    rng = np.random.Generator(np.random.PCG64(seed))
    n = N // 2
    fmax = (CUTOFF / np.hypot(CUTOFF, SCALE)) ** 3
    fraction = fmax * (np.arange(n) + 0.5) / n
    radius = SCALE / np.sqrt(fraction ** (-2 / 3) - 1)
    p = directions(rng, n) * radius[:, None]
    escape = np.sqrt(2 / np.hypot(radius, SCALE))
    speed = escape * np.sqrt(rng.beta(1.5, 4.5, size=n))
    v = directions(rng, n) * speed[:, None]
    x = np.concatenate((p, -p))
    v = np.concatenate((v, -v))
    m = np.full(N, 1 / N)
    _, phi, w, _ = pair_fields(x, m)
    scale = np.sqrt(-w / np.sum(m[:, None] * v ** 2))
    v *= scale
    require(abs(np.sum(m[:, None] * v ** 2) / -w - 1) < 1e-13, "initial softened virial ratio")
    binding = 0.5 * np.sum(v * v, axis=1) + phi
    core = np.argsort(binding, kind="stable")[:CORE]
    return x, v, m, core, float(scale)


def setup(merger):
    x, v, m, groups, cores, scales, half = [], [], [], [], [], [], []
    for k in range(2 if merger else 1):
        p, u, mass, core, scale = progenitor(SEEDS[k])
        half.append(float(np.median(np.linalg.norm(p, axis=1))))
        x.append(p + (BULK_X[k] if merger else 0))
        v.append(u + (BULK_V[k] if merger else 0))
        m.append(mass)
        groups.append(np.full(N, k))
        cores.append(core + N * k)
        scales.append(scale)
    return (np.concatenate(x), np.concatenate(v), np.concatenate(m), np.concatenate(groups),
            np.array(cores), scales, float(np.mean(half)))


def run(mode, binary, output):
    merger = mode != "isolated"
    refinement = 2 if mode == "merger-half-dt" else 1
    dt, steps, stride = DT / refinement, STEPS * refinement, STRIDE * refinement
    x0, v0, mass, labels, cores, velocity_scales, initial_half_mass = setup(merger)
    count = (2 if merger else 1) * N
    ids = np.arange(1, count + 1)
    output.mkdir(parents=True, exist_ok=False)
    initial = output / "initial.txt"
    np.savetxt(initial, np.column_stack((ids, labels, mass, x0, v0)),
               fmt=["%d", "%d"] + ["%.17g"] * 7, header="id population mass x y z vx vy vz")
    raw = output / "raw"
    command = [str(binary.resolve()), str(initial), str(EPS), str(dt), str(steps), str(stride), str(raw)]
    subprocess.run(command, check=True, timeout=2400)

    frame_steps = np.arange(0, steps + 1, stride)
    state = np.loadtxt(raw / "particles.csv", delimiter=",", skiprows=1)
    require(state.shape == (len(frame_steps) * count, 14), "particle output shape")
    data = state.reshape(len(frame_steps), count, 14)
    ledger = np.loadtxt(raw / "conservation.csv", delimiter=",", skiprows=1)
    times = frame_steps * dt
    require(ledger.shape == (len(times), 12) and np.isfinite(ledger).all() and np.isfinite(data).all(), "finite endpoints")
    require(np.all(data[:, :, 0] == frame_steps[:, None]) and np.all(data[:, :, 1] == times[:, None])
            and np.array_equal(ledger[:, 0], frame_steps) and np.array_equal(ledger[:, 1], times), "identical clocks")
    require(np.all(data[:, :, 2] == ids) and np.all(data[:, :, 3] == labels)
            and np.all(data[:, :, 4] == mass) and np.array_equal(np.bincount(labels), [N] * len(cores)), "population, IDs, masses")
    x, v, a = data[:, :, 5:8], data[:, :, 8:11], data[:, :, 11:14]
    require(np.array_equal(x[0], x0) and np.allclose(v[0], v0, rtol=3e-16, atol=1e-16), "initial conditions")

    # These tracers keep their initial identities throughout mixing and ejection.
    centers = np.stack([np.median(x[:, idx, :], axis=1) for idx in cores], axis=1)
    gap = np.linalg.norm(centers[:, 0] - centers[:, -1], axis=1)
    force_error, ledger_error, com_error = 0.0, 0.0, 0.0
    profiles = []
    for frame, (p, u, acceleration) in enumerate(zip(x, v, a)):
        reference, phi, _, force_scale = pair_fields(p, mass)
        force_error = max(force_error, float(np.max(np.linalg.norm(reference - acceleration, axis=1) / force_scale)))
        kinetic = 0.5 * np.sum(mass[:, None] * u ** 2)
        potential = 0.5 * (mass @ phi)
        sums = np.r_[mass.sum(), kinetic, potential, kinetic + potential, mass @ u, mass @ np.cross(p, u)]
        ledger_error = max(ledger_error, float(np.max(abs(sums - ledger[frame, 2:]) / np.maximum(1, abs(sums)))))
        center_of_mass = mass @ p / mass.sum()
        center_velocity = mass @ u / mass.sum()
        com_error = max(com_error, float(np.linalg.norm(center_of_mass)))
        radius = np.linalg.norm(p - np.median(p, axis=0), axis=1)
        inner = np.argsort(radius, kind="stable")[:count // 2]
        bound = 0.5 * np.sum((u - center_velocity) ** 2, axis=1) + phi < 0
        profiles.append((times[frame], gap[frame], np.median(radius), np.mean(labels[inner] == 0),
                         np.count_nonzero(bound)))
    profiles = np.asarray(profiles)
    np.savetxt(output / "structure.csv", profiles, delimiter=",", comments="",
               header="time,core_separation,half_mass_radius,inner_half_fraction_A,instantaneously_bound_count",
               fmt=["%.17g"] * 4 + ["%d"])
    energy_drift = float(np.max(abs(ledger[:, 5] - ledger[0, 5])) / abs(ledger[0, 5]))
    p_drift = float(np.max(np.linalg.norm(ledger[:, 6:9] - ledger[0, 6:9], axis=1)))
    l_drift = float(np.max(np.linalg.norm(ledger[:, 9:12] - ledger[0, 9:12], axis=1)))
    require(force_error < 1e-12 and ledger_error < 1e-11 and com_error < 1e-10, "independent force/ledger/barycentre")
    require(energy_drift < 5e-4 and p_drift < 1e-11 and l_drift < 1e-10, "conservation")

    trajectory = output / "trajectory.npz"
    np.savez_compressed(trajectory, time=times, step=frame_steps, particle_id=ids, population=labels,
                        mass=mass, position=x, velocity=v, acceleration=a, core_ids=ids[cores], core_centers=centers)
    report = dict(mode=mode, units="dimensionless; G=1, mass per galaxy=1", boundary="isolated",
                  integrator="serial direct pair sum; fixed-Plummer kick-drift-kick", particle_count=count,
                  particles_per_progenitor=[N]*len(cores), initial_model="truncated, antipodally paired Plummer",
                  initial_scale=SCALE, truncation_radius=CUTOFF, epsilon=EPS, dt=dt, steps=steps, stride=stride,
                  frames=len(times), end_time=float(times[-1]), initial_half_mass_radius=initial_half_mass,
                  rng="numpy.random.PCG64", seeds=list(SEEDS[:len(cores)]), initial_virial_velocity_scales=velocity_scales,
                  final_instantaneously_bound_count=int(profiles[-1, 4]), final_half_mass_radius=float(profiles[-1, 2]),
                  max_relative_energy_drift=energy_drift, max_momentum_drift=p_drift, max_angular_momentum_drift=l_drift,
                  max_scaled_force_discrepancy=force_error, max_scaled_ledger_discrepancy=ledger_error,
                  max_barycentre_offset=com_error, binary_sha256=digest(binary), driver_sha256=digest(Path(__file__)),
                  numpy=np.__version__, core_ids=ids[cores].tolist())
    if merger:
        tail = times >= 32
        p90 = float(np.quantile(gap[tail], 0.9))
        fractions = profiles[tail, 3]
        first_overlap = np.flatnonzero(gap < initial_half_mass)
        above = np.flatnonzero(gap >= initial_half_mass)
        report["core_overlap"] = dict(
            initial_separation=float(gap[0]), final_separation=float(gap[-1]),
            minimum_separation=float(gap.min()), time_of_minimum=float(times[np.argmin(gap)]),
            first_overlap_time=float(times[first_overlap[0]]) if len(first_overlap) else None,
            last_time_above_initial_half_mass_radius=float(times[above[-1]]) if len(above) else None,
            late_interval=[32, 40], late_separation_p90=p90, late_separation_max=float(np.max(gap[tail])),
            min_late_inner_fraction_A=float(fractions.min()), max_late_inner_fraction_A=float(fractions.max()),
            sustained_mixed_remnant=bool(p90 < initial_half_mass and gap[-1] < initial_half_mass
                                         and fractions.min() >= 0.25 and fractions.max() <= 0.75
                                         and profiles[-1, 4] >= 0.9 * count))
    report["files"] = {str(p.relative_to(output)): digest(p) for p in
                       (initial, trajectory, output / "structure.csv", raw / "conservation.csv")}
    (output / "run.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=["isolated", "merger", "merger-half-dt"])
    parser.add_argument("binary", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.case, args.binary, args.output)
