#!/usr/bin/env python3
"""Run issue #5's preregistered geometry/reconstruction study and archive provenance."""
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


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/mesh_validation")
    output = parser.parse_args().output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    paths = ["Cargo.toml", "Cargo.lock", "rust-toolchain.toml", "crates/moving-mesh/Cargo.toml",
             "crates/moving-mesh/src/lib.rs", "crates/moving-mesh/tests/geometry.rs",
             "crates/moving-mesh/examples/reconstruction-study.rs", "crates/mhd-planar/src/lib.rs",
             "scripts/run_mesh_validation.py", "docs/MESH_VALIDATION.md"]
    sources = {p: sha(ROOT / p) for p in paths}
    cargo = shutil.which("cargo") or str(Path.home() / ".cargo/bin/cargo")
    invocation = [cargo, "run", "--release", "--locked", "-p", "moving-mesh", "--example", "reconstruction-study"]
    summary = command(invocation)  # The Rust study enforces the predeclared gates.
    rows = list(csv.DictReader(io.StringIO(summary)))
    if len(rows) != 18 or any(not math.isfinite(float(v)) for r in rows for k, v in r.items() if k != "operator"):
        raise ValueError("invalid study table")
    orders = []
    for jitter in (0., .15):
        for operator in ("neighbour_raw", "neighbour_limited", "face_raw"):
            series = [r for r in rows if float(r["jitter"]) == jitter and r["operator"] == operator]
            if [int(r["n"]) for r in series] != [8, 16, 32]:
                raise ValueError("incorrect resolution ladder")
            for a, b in zip(series, series[1:]):
                orders.append({"jitter": jitter, "operator": operator, "from_n": int(a["n"]),
                               "to_n": int(b["n"]), **{f"{norm}_order": math.log2(float(a[norm]) / float(b[norm])) for norm in ("l1", "l2")}})
    (output / "summary.csv").write_text(summary)
    if sources != {p: sha(ROOT / p) for p in paths}:
        raise ValueError("study sources changed during execution")
    record = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "revision": command(["git", "rev-parse", "HEAD"]).strip(),
        "dirty_status": command(["git", "status", "--short"]), "source_sha256": sources,
        "platform": platform.platform(), "machine": platform.machine(),
        "rustc": command([str(Path(cargo).with_name("rustc")), "-Vv"]), "command": invocation,
        "configuration": {"lengths": [1, 1], "boundary": "periodic", "precision": "f64",
                          "ranks": 1, "threads": 1, "profile": "release", "field": "sin(2pi*x)sin(2pi*y)",
                          "jitter": "deterministic trigonometric generator perturbation; no RNG"},
        "refinement_orders": orders, "study_gates_passed": True,
        "result_sha256": {"summary.csv": sha(output / "summary.csv")},
        "scope": "geometry and manufactured scalar-gradient/planar-curl errors; no fluid evolution or div(curl) claim",
    }
    (output / "provenance.json").write_text(json.dumps(record, indent=2) + "\n")
    print(summary, end="")
    print("All predeclared study gates passed.")


if __name__ == "__main__":
    main()
