#!/usr/bin/env python3
"""Run the predeclared experimental planar MHD gates; archive results/provenance."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def command(args):
    return subprocess.check_output(args, cwd=ROOT, text=True)


def hashes():
    paths = [ROOT / n for n in ("Cargo.toml", "Cargo.lock", "rust-toolchain.toml")]
    for folder in ("crates", "apps"):
        paths += sorted((ROOT / folder).rglob("*.rs"))
        paths += sorted((ROOT / folder).rglob("Cargo.toml"))
    paths += [Path(__file__).resolve(), ROOT / "docs/COUPLED_2D.md"]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/coupled_2d")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    cargo = shutil.which("cargo") or str(Path.home() / ".cargo/bin/cargo")
    rustc = str(Path(cargo).with_name("rustc"))
    subprocess.run([cargo, "build", "--release", "--locked", "-p", "openmhd", "--bins"], cwd=ROOT, check=True)
    metadata = json.loads(command([cargo, "metadata", "--no-deps", "--format-version", "1"]))
    binaries = Path(metadata["target_directory"]) / "release"
    commands = []
    rows = []

    def run(case, nx, ny=None, extra=None):
        label = f"{case}_{nx}" + ("_" + "_".join(extra).replace("--", "") if extra else "")
        snapshot = output / f"{label}.csv"
        invocation = [str(binaries / "openmhd"), "--case", case, "--nx", str(nx),
                      "--time", "0.2" if case == "smooth" else "0.1", "--output", str(snapshot)]
        if ny is not None:
            invocation += ["--ny", str(ny)]
        invocation += extra or []
        commands.append(["openmhd"] + invocation[1:])
        result = list(csv.DictReader(io.StringIO(command(invocation))))
        if len(result) != 1:
            raise RuntimeError("expected one diagnostic row")
        row = result[0]
        for key, value in row.items():
            if key != "case" and not math.isfinite(float(value)):
                raise RuntimeError(f"nonfinite diagnostic {key}")
        row["label"] = label
        row["brio_rho_l1"] = row["brio_by_l1"] = ""
        rows.append(row)
        print(f"{label}: steps={row['steps']}, budget={float(row['budget_error']):.3e}, "
              f"min p={float(row['min_p']):.3e}", flush=True)
        with snapshot.open() as stream:
            cells = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(stream)]
        return row, cells

    for n in (8, 16, 32):
        run("smooth", n)
    reference_path = output / "brio_reference_2048.csv"
    invocation = [str(binaries / "brio-reference"), "2048", "0.1", str(reference_path)]
    commands.append(["brio-reference"] + invocation[1:])
    reference_diagnostics = list(csv.DictReader(io.StringIO(command(invocation))))[0]
    with reference_path.open() as stream:
        reference = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(stream)]
    for n in (32, 64, 128):
        row, cells = run("brio-wu", n)
        ratio = 2048 // n
        for key in ("rho", "by"):
            error = norm = 0.0
            # One transverse row suffices on this exact regular tube geometry.
            for i in range(n // 4, 3 * n // 4):
                expected = sum(reference[j][key] for j in range(i * ratio, (i + 1) * ratio)) / ratio
                error += abs(cells[i][key] - expected)
                norm += abs(expected)
            row[f"brio_{key}_l1"] = error / norm
    base_cells = boost_cells = None
    for n in (12, 24, 48):
        _, cells = run("orszag-tang", n)
        if n == 12:
            base_cells = cells
    _, boost_cells = run("orszag-tang", 12, extra=["--boost-x", "2", "--boost-y", "-1",
                                                 "--mesh-vx", "2", "--mesh-vy", "-1"])
    run("orszag-tang", 12, extra=["--jitter", "0.15"])
    for jitter in ("0", "0.15"):
        run("uniform", 8, extra=["--jitter", jitter, "--mesh-vx", "0.7", "--mesh-vy", "-0.8"])

    boost_error = max(abs(a[key] - b[key]) for a, b in zip(base_cells, boost_cells)
                      for key in ("rho", "p", "bx", "by"))
    smooth = [float(r["smooth_l1"]) for r in rows if r["case"] == "smooth"]
    brio = [r for r in rows if r["case"] == "brio-wu"]
    gates = {
        "all_budgets": all(float(r["budget_error"]) <= 1e-10 for r in rows),
        "all_positive": all(float(r["min_rho"]) > 0 and float(r["min_p"]) > 0 for r in rows),
        "smooth_decreasing": all(a > b for a, b in zip(smooth, smooth[1:])),
        "brio_rho": float(brio[-1]["brio_rho_l1"]) < min(.15, float(brio[0]["brio_rho_l1"])),
        "brio_by": float(brio[-1]["brio_by_l1"]) < min(.15, float(brio[0]["brio_by_l1"])),
        "vortex_joint_boost": boost_error < 1e-9,
    }
    with (output / "summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    provenance = {
        "created_utc": datetime.now(timezone.utc).isoformat(), "revision": command(["git", "rev-parse", "HEAD"]).strip(),
        "dirty_status": command(["git", "status", "--short"]), "source_sha256": hashes(),
        "platform": platform.platform(), "machine": platform.machine(),
        "rustc": command([rustc, "-Vv"]), "cargo": command([cargo, "-V"]),
        "execution": {"ranks": 1, "threads": 1, "profile": "release", "dependencies": "local crates only"},
        "commands": commands, "gates": gates, "max_boost_error": boost_error,
        "smooth_orders": [math.log2(a / b) for a, b in zip(smooth, smooth[1:])],
        "reference_diagnostics": reference_diagnostics,
        "result_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(output.glob("*.csv"))},
        "scope": "experimental planar reference; no full-paper or published-profile equivalence claim",
    }
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(json.dumps({"gates": gates, "boost_error": boost_error,
                      "smooth_orders": provenance["smooth_orders"]}, indent=2))
    if not all(gates.values()):
        raise SystemExit("Some predeclared gates failed; see archived diagnostics.")


if __name__ == "__main__":
    main()
