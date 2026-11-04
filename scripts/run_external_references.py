#!/usr/bin/env python3
"""Build pinned Athena++ outside this repository and archive M0 reference data.

Requires Python's standard library, git, make and clang++. No Athena source is
imported into the Rust solver. Inputs and gates are in benchmarks/m0/packet.json.
"""
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
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("rho", "p", "vx", "vy", "vz", "bx", "by", "bz")
ATHENA_FIELDS = ("rho", "press", "vel1", "vel2", "vel3", "Bcc1", "Bcc2", "Bcc3")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(args, cwd=ROOT):
    return subprocess.check_output([str(a) for a in args], cwd=cwd, text=True)


def table(path, dimension, n, bins, expected_time):
    """Average native cell primitive values into aligned uniform comparison bins."""
    sums = [[0.0] * 8 for _ in range(bins ** dimension)]
    counts = [0] * len(sums)
    minimum = [math.inf, math.inf]
    with path.open() as stream:
        time_header = next(stream)
        actual_time = float(re.search(r"time=([^ ]+)", time_header).group(1))
        if abs(actual_time - expected_time) > 1e-12:
            raise ValueError(f"reference ended at unexpected time: {time_header}")
        headers = next(stream).lstrip("#").split()
        columns = [headers.index(name) for name in ATHENA_FIELDS]
        for line in stream:
            if not line.strip() or line.startswith("#"):
                continue
            values = list(map(float, line.split()))
            if not all(map(math.isfinite, values)):
                raise ValueError(f"nonfinite reference value in {path}")
            x = values[headers.index("x1v")] + 0.5
            i = min(bins - 1, int(x * bins))
            j = 0 if dimension == 1 else min(bins - 1, int((values[headers.index("x2v")] + 0.5) * bins))
            index = j * bins + i
            counts[index] += 1
            for q, column in enumerate(columns):
                sums[index][q] += values[column]
            minimum[0] = min(minimum[0], values[columns[0]])
            minimum[1] = min(minimum[1], values[columns[1]])
    expected = (n // bins) ** dimension
    if n % bins or any(count != expected for count in counts):
        raise ValueError(f"incomplete/unaligned reference grid: {path}")
    if min(minimum) <= 0:
        raise ValueError(f"nonpositive reference state: {path}")
    return [[value / counts[i] for value in row] for i, row in enumerate(sums)], minimum, time_header.strip()


def write_csv(path, rows, bins, dimension, x_shift):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(("x", "y") + FIELDS)
    for index, row in enumerate(rows):
        x = (index % bins + 0.5) / bins + x_shift
        y = 0.0 if dimension == 1 else (index // bins + 0.5) / bins
        writer.writerow([format(x, ".17e"), format(y, ".17e")] + [format(q, ".17e") for q in row])
    # Fixed gzip mtime avoids nondeterministic compressed bytes.
    path.write_bytes(gzip.compress(buffer.getvalue().encode(), mtime=0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=Path("/tmp/openmhd-athena-v24"))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/external_references")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--cxx", default="clang++")
    args = parser.parse_args()
    source, output = args.source_dir.resolve(), args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    archive = output / "archive"
    archive.mkdir(exist_ok=True)
    packet_path = ROOT / "benchmarks/m0/packet.json"
    packet = json.loads(packet_path.read_text())
    ref = packet["external_reference"]
    if not source.exists():
        subprocess.run(["git", "clone", "--depth", "1", "--branch", ref["tag"], ref["repository"], str(source)], check=True)
    if command(["git", "rev-parse", "HEAD"], source).strip() != ref["revision"]:
        raise ValueError("Athena checkout does not match pinned revision")
    if command(["git", "status", "--porcelain", "--untracked-files=no"], source):
        raise ValueError("Athena tracked source has local changes")
    if "BSD 3-Clause License" not in (source / "LICENSE").read_text():
        raise ValueError("unexpected external license")
    shutil.copyfile(source / "LICENSE", archive / "ATHENA_LICENSE.txt")
    provenance = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "openmhd_revision": command(["git", "rev-parse", "HEAD"]).strip(),
        "openmhd_dirty_status": command(["git", "status", "--short"]),
        "athena_revision": ref["revision"], "athena_repository": ref["repository"],
        "license_sha256": sha(source / "LICENSE"), "platform": platform.platform(),
        "compiler": command([args.cxx, "--version"]), "python": sys.version,
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in
                          [packet_path, Path(__file__).resolve(), ROOT / "benchmarks/m0/athinput.brio", ROOT / "benchmarks/m0/athinput.vortex"]},
        "runs": [], "reference_changes": {}, "gates": {},
        "scope": "independent implementation reference; finite resolution, not an exact solution or author dataset",
    }
    for case, problem, dimension, resolutions in (
        ("brio", "shock_tube", 1, ref["brio_resolutions"]),
        ("vortex", "orszag_tang", 2, ref["vortex_resolutions"]),
    ):
        build_commands = [[sys.executable, "configure.py", "--prob=" + problem,
                          "-b", "--flux=" + ref["flux"], "--cxx=" + args.cxx],
                          ["make", "clean"], ["make", "-j", str(args.jobs)]]
        with (output / (case + "_build.log")).open("w") as log:
            for invocation in build_commands:
                subprocess.run(invocation, cwd=source, stdout=log, stderr=subprocess.STDOUT, check=True)
        binary = output / ("athena_" + case)
        shutil.copyfile(source / "bin/athena", binary)
        binary.chmod(0o755)
        comparisons = []
        for n in resolutions:
            run_dir = output / f"{case}_{n}"
            run_dir.mkdir(exist_ok=True)
            # Athena appends history on repeat runs. This file is a generated
            # product of this runner; remove it before starting a fresh run.
            (run_dir / (case + ".hst")).unlink(missing_ok=True)
            invocation = [str(binary), "-i", str(ROOT / "benchmarks/m0" / ("athinput." + case)),
                          "mesh/nx1=" + str(n)]
            if dimension == 2:
                invocation.append("mesh/nx2=" + str(n))
            print(f"Running independent {case} reference at {n}" + (" squared" if dimension == 2 else ""), flush=True)
            with (run_dir / "run.log").open("w") as log:
                subprocess.run(invocation, cwd=run_dir, stdout=log, stderr=subprocess.STDOUT, check=True)
            snapshots = sorted(run_dir.glob("*.tab"))
            if len(snapshots) != 2:
                raise ValueError(f"expected initial/final tables, got {snapshots}")
            bins = n if dimension == 1 else ref["vortex_comparison_bins"]
            final_time = 0.1 if dimension == 1 else 0.5
            rows, minimum, header = table(snapshots[-1], dimension, n, bins, final_time)
            write_csv(archive / f"{case}_{n}.csv.gz", rows, bins, dimension, 0.5 if dimension == 1 else 0.0)
            # Compare both resolutions on identical bins (4096 shock or 64^2 vortex).
            comparison_bins = resolutions[0] if dimension == 1 else bins
            comparison, _, _ = table(snapshots[-1], dimension, n, comparison_bins, final_time)
            comparisons.append(comparison)
            history = run_dir / (case + ".hst")
            history_rows = [list(map(float, line.split())) for line in history.read_text().splitlines()
                            if line.strip() and not line.startswith("#")]
            initial_h, final_h = history_rows[0], history_rows[-1]
            if sum(row[0] == 0.0 for row in history_rows) != 1 or any(
                    b[0] <= a[0] for a, b in zip(history_rows, history_rows[1:])):
                raise ValueError("history contains repeated or nonmonotone run times")
            if abs(final_h[0] - final_time) > 1e-12:
                raise ValueError("history file lacks final time")
            # Outflow shock has analytic boundary stress input; vortex is periodic.
            boundary_rates = {2: 0.0, 3: 0.9 if dimension == 1 else 0.0,
                              4: -1.5 if dimension == 1 else 0.0, 5: 0.0, 9: 0.0}
            budget_error = max(abs(final_h[k] - initial_h[k] - rate * final_time)
                               for k, rate in boundary_rates.items())
            provenance["gates"][f"{case}_{n}_budget"] = budget_error <= packet["solver"]["budget_tolerance"]
            if dimension == 1:
                left, right = rows[0], rows[-1]
                expected_left = [1, 1, 0, 0, 0, 0.75, 1, 0]
                expected_right = [0.125, 0.1, 0, 0, 0, 0.75, -1, 0]
                provenance["gates"][f"{case}_{n}_boundary_states"] = max(
                    abs(a-b) for a, b in zip(left + right, expected_left + expected_right)) < 1e-12
            shutil.copyfile(history, archive / f"{case}_{n}.hst")
            provenance["runs"].append({"case": case, "n": n, "commands": build_commands + [invocation],
                "binary_sha256": sha(binary), "makefile_sha256": sha(source / "Makefile"),
                "defs_sha256": sha(source / "src/defs.hpp"), "table_sha256": {p.name: sha(p) for p in snapshots},
                "output_header": header, "min_rho": minimum[0], "min_p": minimum[1],
                "absolute_budget_error": budget_error})
        scales = {"rho": 1.0, "p": 1.0, "vx": 1.0, "by": 1.0} if dimension == 1 else {
            "rho": 25 / (36 * math.pi), "p": 5 / (12 * math.pi), "bx": 1 / math.sqrt(4 * math.pi), "by": 1 / math.sqrt(4 * math.pi)}
        for field, scale in scales.items():
            k = FIELDS.index(field)
            error = sum(abs(a[k] - b[k]) for a, b in zip(*comparisons)) / len(comparisons[0]) / scale
            key = case + "_" + field
            provenance["reference_changes"][key] = error
            provenance["gates"][key] = error <= ref["reference_change_limits"][key]
        print(json.dumps(provenance["reference_changes"], indent=2), flush=True)
    provenance["result_sha256"] = {p.name: sha(p) for p in sorted(archive.iterdir()) if p.name != "provenance.json"}
    (archive / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    if not all(provenance["gates"].values()):
        raise SystemExit("Reference resolution gate failed; do not certify it or tune the gate after seeing the result.")
    print("All preregistered reference resolution gates passed.")


if __name__ == "__main__":
    main()
