#!/usr/bin/env python3
"""Build and archive the predeclared serial 2D kinematic resolution study.

Only Python's standard library and the pinned Rust toolchain are required.
See docs/KINEMATIC_2D.md. No full-MHD validation claim follows from this study.
"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
RESOLUTIONS = [16, 32, 64, 128]


def command(args):
    return subprocess.check_output(args, cwd=ROOT, text=True)


def source_hashes():
    paths = [ROOT / name for name in ("Cargo.toml", "Cargo.lock", "rust-toolchain.toml")]
    paths += sorted((ROOT / "crates").rglob("*.rs"))
    paths += sorted((ROOT / "apps").rglob("*.rs"))
    paths += sorted((ROOT / "crates").rglob("Cargo.toml"))
    paths += sorted((ROOT / "apps").rglob("Cargo.toml"))
    paths += [Path(__file__).resolve()]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/kinematic_2d")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    cargo = shutil.which("cargo") or str(Path.home() / ".cargo/bin/cargo")
    rustc = shutil.which("rustc") or str(Path(cargo).with_name("rustc"))
    subprocess.run([cargo, "build", "--release", "--locked", "-p", "field-loop"], cwd=ROOT, check=True)
    # Ask Cargo about target-dir rather than assume a particular user config.
    metadata = json.loads(command([cargo, "metadata", "--no-deps", "--format-version", "1"]))
    binary = str(Path(metadata["target_directory"]) / "release" / ("field-loop.exe" if os.name == "nt" else "field-loop"))
    commands = []

    def simulate(case, n, mesh, time="1", cells=None):
        invocation = [binary, "--case", case, "--n", str(n), "--mesh", mesh,
                      "--vx", "2", "--vy", "1", "--time", time, "--cfl", "0.4"]
        if cells is not None:
            invocation += ["--output", str(cells)]
        commands.append(["field-loop"] + invocation[1:])
        result = list(csv.DictReader(io.StringIO(command(invocation))))
        if len(result) != 1:
            raise RuntimeError("driver must return exactly one diagnostics row")
        row = result[0]
        for key, value in row.items():
            if key not in ("case", "mesh", "limiter") and not math.isfinite(float(value)):
                raise RuntimeError(f"non-finite metric {key}: {value}")
        return row

    rows = []
    failures = []
    for case in ("smooth", "loop"):
        previous = None
        for n in RESOLUTIONS:
            row = simulate(case, n, "fixed")
            row.update(az_order="", b_order="")
            if previous is not None:
                for quantity in ("az", "b"):
                    order = math.log2(float(previous[f"{quantity}_l1"]) / float(row[f"{quantity}_l1"]))
                    row[f"{quantity}_order"] = f"{order:.8f}"
                    if case == "smooth" and n in (64, 128) and order < 1.8:
                        failures.append(f"smooth {quantity}, N={n}: order {order} < 1.8")
            if case == "loop":
                initial = simulate(case, n, "fixed", time="0")
                scale = float(initial["az_max"])
                if float(row["az_min"]) < -1e-12 * scale or float(row["az_max"]) > scale * (1 + 1e-12):
                    failures.append(f"loop N={n}: new extrema")
                if abs(float(row["az_integral_relative_drift"])) > 1e-11:
                    failures.append(f"loop N={n}: integral drift")
            rows.append(row)
            previous = row
            print(f"{case:6} N={n:3}: Az L1={float(row['az_l1']):.6e}, B L1={float(row['b_l1']):.6e}, "
                  f"orders=({row['az_order']},{row['b_order']})", flush=True)

    comoving = simulate("loop", 64, "comoving", cells=output / "loop_comoving.csv")
    comoving.update(az_order="", b_order="")
    rows.append(comoving)
    if float(comoving["az_l1"]) > 1e-10 * (0.001 / math.sqrt(4 * math.pi)):
        failures.append("comoving loop: normalized Az drift")
    if float(comoving["magnetic_energy_ratio"]) != 1.0:
        failures.append("comoving loop: changed discrete magnetic energy")
    simulate("loop", 64, "fixed", cells=output / "loop_fixed.csv")
    simulate("loop", 64, "fixed", time="0", cells=output / "loop_initial.csv")

    with (output / "convergence.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    provenance = {
        "model": "kinematic_cartesian_2d_not_coupled_mhd",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_git_commit": command(["git", "rev-parse", "HEAD"]).strip(),
        "source_worktree_dirty": bool(command(["git", "status", "--porcelain"])),
        "source_sha256": source_hashes(),
        "rustc": command([rustc, "-Vv"]).strip(),
        "cargo": command([cargo, "--version"]).strip(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "rustflags": os.environ.get("RUSTFLAGS", ""),
        "ranks": 1,
        "worker_threads": 1,
        "random_seed": None,
        "config": {"domain": [1, 1], "boundary": "periodic", "precision": "f64",
                   "units": "nondimensional", "mean_B": [0, 0], "phi": 0,
                   "resistivity": 0, "gas_evolution": False, "EOS": "not_used",
                   "fluid_velocity": [2, 1], "fixed_grid_velocity": [0, 0],
                   "comoving_grid_velocity": [2, 1], "final_time": 1, "CFL": 0.4,
                   "smooth_reconstruction": "unlimited", "loop_reconstruction": "mc",
                   "resolutions": RESOLUTIONS},
        "commands": commands,
        "gates": {"smooth_min_order_finest_two_doublings": 1.8,
                  "loop_relative_integral_drift_max": 1e-11,
                  "loop_extrema_tolerance_relative_initial_max": 1e-12,
                  "comoving_relative_Az_error_max": 1e-10},
        "gate_failures": failures,
        "convergence_csv_sha256": hashlib.sha256((output / "convergence.csv").read_bytes()).hexdigest(),
    }
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"PASS: predeclared gates; outputs: {output}")


if __name__ == "__main__":
    main()
