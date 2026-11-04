#!/usr/bin/env python3
"""Archive the predeclared manufactured gauge/cleaning temporal-order audit."""
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/m0_operators")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    cargo = shutil.which("cargo") or str(Path.home() / ".cargo/bin/cargo")
    rustc = str(Path(cargo).with_name("rustc"))
    build = [cargo, "build", "--release", "--locked", "-p", "mhd-vector-pot",
             "--example", "gauge-cleaning"]
    subprocess.run(build, cwd=ROOT, check=True)
    metadata = json.loads(command([cargo, "metadata", "--no-deps", "--format-version", "1"]))
    binary = Path(metadata["target_directory"]) / "release/examples/gauge-cleaning"
    result = command([str(binary)])
    rows = list(csv.DictReader(io.StringIO(result)))
    if len(rows) != 8:
        raise RuntimeError("expected two methods with four resolutions each")
    for row in rows:
        for key, value in row.items():
            if key != "method" and value and not math.isfinite(float(value)):
                raise RuntimeError(f"nonfinite {key}")
    methods = ("paper_frozen_source", "reevaluated_heun_comparator")
    errors = {}
    orders = {}
    for method in methods:
        subset = [row for row in rows if row["method"] == method]
        if [int(row["n"]) for row in subset] != [40, 80, 160, 320]:
            raise RuntimeError(f"unexpected resolution ladder for {method}")
        errors[method] = [float(row["relative_error"]) for row in subset]
        orders[method] = [math.log2(a / b) for a, b in zip(errors[method], errors[method][1:])]
    gates = {
        "errors_decrease": all(all(a > b > 0 for a, b in zip(values, values[1:]))
                               for values in errors.values()),
        "frozen_source_first_order": 0.8 <= orders[methods[0]][-1] <= 1.2,
        "reevaluated_heun_second_order": orders[methods[1]][-1] >= 1.8,
    }
    # LF bytes keep the archived hash stable across Git newline normalization.
    csv_path = output / "cleaning.csv"
    csv_path.write_bytes(result.replace("\r\n", "\n").encode())
    sources = [ROOT / name for name in (
        "Cargo.toml", "Cargo.lock", "rust-toolchain.toml", "crates/mhd-vector-pot/Cargo.toml",
        "crates/mhd-vector-pot/src/lib.rs", "crates/mhd-vector-pot/src/gauge.rs",
        "crates/mhd-vector-pot/tests/gauge.rs", "crates/mhd-vector-pot/examples/gauge-cleaning.rs",
        "docs/M0_OPERATOR_CHECKS.md", "scripts/run_m0_operators.py",
    )]
    provenance = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "revision": command(["git", "rev-parse", "HEAD"]).strip(),
        "dirty_status": command(["git", "status", "--short"]),
        "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sources},
        "platform": platform.platform(), "machine": platform.machine(),
        "rustc": command([rustc, "-Vv"]), "cargo": command([cargo, "-V"]),
        "execution": {"ranks": 1, "threads": 1, "profile": "release", "spatial_derivatives": "analytic"},
        "commands": [build, [str(binary)]], "gates": gates, "orders": orders,
        "result_sha256": {csv_path.name: hashlib.sha256(csv_path.read_bytes()).hexdigest()},
        "scope": "isolated longitudinal gauge mode; not full-solver temporal convergence",
    }
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(json.dumps({"gates": gates, "orders": orders}, indent=2))
    if not all(gates.values()):
        raise SystemExit("A predeclared operator gate failed; see the archived output.")


if __name__ == "__main__":
    main()
