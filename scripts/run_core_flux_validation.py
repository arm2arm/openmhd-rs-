#!/usr/bin/env python3
"""Issue #4: compare the 1D conservative-induction driver with pinned Athena data."""
import argparse
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("rho", "p", "vx", "by")
LIMITS = dict(zip(FIELDS, (.03, .04, .03, .04)))
LADDER = (512, 1024, 2048)


def command(args):
    return subprocess.check_output(args, cwd=ROOT, text=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_cells(stream):
    rows = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(stream)]
    if not rows or any(not math.isfinite(v) for r in rows for v in r.values()):
        raise ValueError("empty/nonfinite profile")
    if any(r["rho"] <= 0 or r["p"] <= 0 for r in rows):
        raise ValueError("nonpositive profile")
    return rows


def profile_errors(cells, reference):
    """Volume-average reference primitives over aligned central candidate cells."""
    n = len(cells)
    if n % 4 or len(reference) % (n // 2):
        raise ValueError("grids do not nest on the central unit interval")
    for i, cell in enumerate(cells):
        if abs(cell["x_comoving"] - (i + .5) * 2 / n) > 1e-12:
            raise ValueError("candidate cells are not ordered on the declared grid")
    for j, cell in enumerate(reference):
        if abs(cell["x"] - (.5 + (j + .5) / len(reference))) > 1e-12:
            raise ValueError("reference coordinates do not cover [.5,1.5]")
    ratio = len(reference) // (n // 2)
    differences = {k: [] for k in FIELDS}
    for j, cell in enumerate(cells[n // 4:3 * n // 4]):
        fine = reference[j * ratio:(j + 1) * ratio]
        for k in FIELDS:
            expected = math.fsum(r[k] for r in fine) / ratio
            differences[k].append(cell[k] - expected)
    # Fixed characteristic scales are one in these nondimensional units.
    return {f"{k}_{norm}": (math.fsum(abs(v) for v in d) / len(d) if norm == "l1"
                              else math.sqrt(math.fsum(v * v for v in d) / len(d)))
            for k, d in differences.items() for norm in ("l1", "l2")}


def boost_errors(base, boosted, boost, time):
    if len(base) != len(boosted):
        raise ValueError("boost profiles have different cell counts")
    errors = dict.fromkeys(("rho", "p", "bx", "by", "vx", "vy", "energy", "x"), 0.0)
    for a, b in zip(base, boosted):
        if a["x_comoving"] != b["x_comoving"]:
            raise ValueError("boost profiles do not share persistent cell coordinates")
        for k in errors:
            expected = a[k]
            if k == "vx":
                expected += boost
            elif k == "energy":
                expected += boost * a["rho"] * a["vx"] + .5 * a["rho"] * boost**2
            elif k == "x":
                expected = (a["x"] + boost * time) % 2
            error = abs(b[k] - expected)
            if k == "x":
                error = min(error, 2 - error)
            errors[k] = max(errors[k], error)
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/core_flux")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    archive = output / "archive"
    archive.mkdir(exist_ok=True)
    source_paths = ["Cargo.toml", "Cargo.lock", "rust-toolchain.toml",
                    "crates/mhd-core/Cargo.toml", "crates/mhd-core/src/lib.rs",
                    "crates/mhd-core/tests/flux.rs", "apps/openmhd/Cargo.toml",
                    "apps/openmhd/src/bin/brio-reference.rs",
                    "scripts/run_core_flux_validation.py", "docs/CORE_FLUX_VALIDATION.md"]
    source_hashes = {p: sha(ROOT / p) for p in source_paths}
    ref_dir = ROOT / "tests/reference/external_mhd"
    provenance = json.loads((ref_dir / "provenance.json").read_text())
    ref_path = ref_dir / "brio_8192.csv.gz"
    if sha(ref_path) != provenance["result_sha256"][ref_path.name]:
        raise ValueError("independent reference checksum mismatch")
    with gzip.open(ref_path, "rt") as stream:
        reference = read_cells(stream)
    if len(reference) != 8192:
        raise ValueError("expected the pinned 8192-cell reference")

    cargo = shutil.which("cargo") or str(Path.home() / ".cargo/bin/cargo")
    build = [cargo, "build", "--release", "--locked", "-p", "openmhd", "--bin", "brio-reference"]
    subprocess.run(build, cwd=ROOT, check=True)
    metadata = json.loads(command([cargo, "metadata", "--no-deps", "--format-version", "1"]))
    binary = Path(metadata["target_directory"]) / "release/brio-reference"
    commands, rows, profiles = [], [], {}
    for n, boost in [(n, 0) for n in LADDER] + [(LADDER[0], 2)]:
        label = f"brio_{n}_boost{boost}"
        snapshot = output / f"{label}.csv"
        invocation = [str(binary), str(n), ".1", str(snapshot), str(boost)]
        commands.append(invocation)
        diagnostics = list(csv.DictReader(io.StringIO(command(invocation))))
        if len(diagnostics) != 1:
            raise ValueError("expected one diagnostic row")
        row = {k: float(v) for k, v in diagnostics[0].items()}
        if any(not math.isfinite(v) for v in row.values()):
            raise ValueError("nonfinite diagnostic")
        if row["n"] != n or row["time"] != .1 or row["boost"] != boost:
            raise ValueError("run configuration mismatch")
        with snapshot.open() as stream:
            cells = read_cells(stream)
        if len(cells) != n:
            raise ValueError("incorrect snapshot row count")
        profiles[(n, boost)] = cells
        row["label"] = label
        row["bx_max_error"] = max(abs(r["bx"] - .75) for r in cells)
        row.update(profile_errors(cells, reference) if boost == 0
                   else {f"{k}_{norm}": "" for k in FIELDS for norm in ("l1", "l2")})
        rows.append(row)
        (archive / f"{label}.csv.gz").write_bytes(gzip.compress(snapshot.read_bytes(), mtime=0))
        print(f"{label}: steps={int(row['steps'])}, budget={row['budget_error']:.3e}, "
              f"min p={row['min_p']:.3e}, rejected={int(row['rejected_steps'])}", flush=True)
    boost_error = boost_errors(profiles[(LADDER[0], 0)], profiles[(LADDER[0], 2)], 2, .1)
    gates = {
        "positive_accepted_stages": all(r["min_rho"] > 0 and r["min_p"] > 0 for r in rows),
        "periodic_budgets": all(r["budget_error"] <= 1e-10 for r in rows),
        "unchanged_bx": all(r["bx_max_error"] == 0 for r in rows),
        "isolated_central_interval": all(r["signal_distance"] < .45 for r in rows),
        "joint_boost": all(e <= 1e-10 for e in boost_error.values()),
    }
    for k in FIELDS:
        gates[f"{k}_finest_l1"] = rows[2][f"{k}_l1"] < LIMITS[k]
        gates[f"{k}_refinement"] = rows[2][f"{k}_l1"] < rows[0][f"{k}_l1"]
    with (archive / "summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    if source_hashes != {p: sha(ROOT / p) for p in source_paths}:
        raise RuntimeError("source files changed during study")
    record = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "revision": command(["git", "rev-parse", "HEAD"]).strip(),
        "dirty_status": command(["git", "status", "--short"]),
        "source_sha256": source_hashes,
        "platform": platform.platform(), "machine": platform.machine(),
        "rustc": command([str(Path(cargo).with_name("rustc")), "-Vv"]),
        "execution": {"ranks": 1, "threads": 1, "profile": "release", "precision": "f64",
                      "gamma": 2, "mu0": 1, "domain": [0, 2], "boundary": "periodic",
                      "analysis_interval": [.5, 1.5], "time": .1, "cfl": .3,
                      "space": "piecewise constant", "time_integrator": "Heun, endpoint CFL/retries",
                      "bx": .75, "bz": 0, "mean_field_divergence_cell_and_face": 0,
                      "density_pressure_floors": False, "energy_resets": False},
        "build_command": build, "commands": commands, "binary_sha256": sha(binary),
        "reference": {"path": str(ref_path.relative_to(ROOT)), "sha256": sha(ref_path),
                      "athena_revision": provenance["athena_revision"],
                      "provenance_sha256": sha(ref_dir / "provenance.json"),
                      "refinement_l1_4096_to_8192": {
                          k: provenance["reference_changes"][f"brio_{k}"] for k in FIELDS}},
        "finest_l1_limits": LIMITS, "boost_max_absolute_errors": boost_error, "gates": gates,
        "result_sha256": {p.name: sha(p) for p in sorted(archive.iterdir()) if p.name != "provenance.json"},
        "scope": "conservative-induction flux validation; no A/curl, general mesh or paper-global-v1 claim",
    }
    (archive / "provenance.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"gates": gates, "boost_errors": boost_error}, indent=2))
    if not all(gates.values()):
        raise SystemExit("Predeclared gates failed; inspect the archived results.")


if __name__ == "__main__":
    main()
