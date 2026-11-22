#!/usr/bin/env python3
"""Reproduce issue #6's predeclared 2.5D operator/coupling gates (standard library only)."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TAU = 2 * math.pi


def command(args):
    return subprocess.check_output(args, cwd=ROOT, text=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_cells(path):
    with path.open() as stream:
        rows = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(stream)]
    if not rows or any(not math.isfinite(v) for r in rows for v in r.values()):
        raise ValueError(f"nonfinite/empty snapshot {path}")
    if [r["id"] for r in rows] != list(range(len(rows))):
        raise ValueError("persistent cell IDs lost")
    return rows


def orders(values):
    return [math.log2(a / b) for a, b in zip(values, values[1:])]


def weighted(values, cells):
    volume = sum(c["volume"] for c in cells)
    return [sum(c["volume"] * abs(e) for c, e in zip(cells, values)) / volume,
            math.sqrt(sum(c["volume"] * e * e for c, e in zip(cells, values)) / volume)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/vector_potential")
    output = parser.parse_args().output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    cargo = shutil.which("cargo") or str(Path.home() / ".cargo/bin/cargo")
    source_paths = ["Cargo.toml", "Cargo.lock", "rust-toolchain.toml", "scripts/run_vector_potential.py",
                    "docs/VECTOR_POTENTIAL_REFERENCE.md", "benchmarks/m1/packet-v2.json",
                    "apps/openmhd/Cargo.toml", "apps/openmhd/src/bin/vector-potential.rs"]
    for crate in ("mhd-vector-pot", "mhd-core", "moving-mesh"):
        source_paths += [str(p.relative_to(ROOT)) for p in sorted((ROOT / "crates" / crate).rglob("*.rs"))]
        source_paths.append(f"crates/{crate}/Cargo.toml")
    sources = {p: sha(ROOT / p) for p in source_paths}
    revision = command(["git", "rev-parse", "HEAD"]).strip()
    dirty = command(["git", "status", "--short"])
    command([cargo, "build", "--release", "--locked", "-p", "openmhd", "--bin", "vector-potential"])
    binary = ROOT / "target/release/vector-potential"
    runs, commands, hashes = {}, [], {}
    cells = {}

    def run(name, case, n, jitter, time, *extra):
        dest = output / name
        args = [str(binary), "--case", case, "--n", str(n), "--jitter", str(jitter), "--time", str(time),
                "--output", str(dest), *map(str, extra)]
        print(command(args), end="", flush=True)
        commands.append(args)
        record = json.loads((dest / "summary.json").read_text())
        runs[name] = record
        cells[name] = [read_cells(dest / f"{stage}.csv") for stage in ("initial", "final")]
        for stage in ("initial", "final"):
            hashes[f"{name}/{stage}.csv"] = sha(dest / f"{stage}.csv")
        d = record["final"]
        assert d["rho_min"] > 0 and d["p_min"] > 0, name
        assert max(map(abs, d["normalized_budget"])) <= 1e-10, name
        return record, cells[name]

    result = {"profile": "paper-global-v2", "scope": "issue #6 operator/coupling gates; not the full M1 physical benchmark matrix"}
    curl = []
    uniform = []
    boosts = []
    for jitter in (0., .15):
        series = []
        for n in (8, 16, 32):
            _, (_, final) = run(f"curl_n{n}_j{jitter}", "curl", n, jitter, 0)
            error = []
            for c in final:
                x, y = TAU * c["x"], TAU * c["y"]
                exact = [.001 * TAU * math.sin(x) * math.cos(y), -.001 * TAU * math.cos(x) * math.sin(y),
                         -.001 * TAU * (math.sin(x) + math.cos(y))]
                error.append(math.sqrt(sum((c[k] - e)**2 for k, e in zip(("bx", "by", "bz"), exact))))
            l1, l2 = weighted(error, final)
            series.append([l1, l2])
            curl.append({"jitter": jitter, "n": n, "L1": l1, "L2": l2})
        for k in (0, 1):
            assert min(orders([e[k] for e in series])) > (1.8 if jitter == 0 else .7)
        for motion in ("fixed", "rigid"):
            name = f"uniform_{motion}_j{jitter}"
            _, (initial, final) = run(name, "uniform", 6, jitter, .05, "--motion", motion, "--mesh-x", .7, "--mesh-y", -.8)
            physical = max(abs(b[k] - a[k]) for a, b in zip(initial, final) for k in ("rho", "p", "vx", "vy", "vz", "bx", "by", "bz"))
            source = [-.08, .05, .14]  # (.4,-.2,.3) cross (.3,.2,.1)
            potential = max(abs(b[k] - a[k] - .05 * s) for a, b in zip(initial, final) for k, s in zip(("ax", "ay", "az"), source))
            assert max(physical, potential) <= 1e-10
            uniform.append({"run": name, "physical_max": physical, "potential_drift_max": potential})
        aname, bname = f"smooth_j{jitter}", f"boost_j{jitter}"
        ar, (_, ac) = run(aname, "smooth", 8, jitter, .02)
        br, (_, bc) = run(bname, "smooth", 8, jitter, .02, "--boost-x", 2, "--boost-y", -1,
                            "--motion", "rigid", "--mesh-x", 2, "--mesh-y", -1)
        error = {k: max(abs(a[k] - b[k] + {"vx": 2, "vy": -1}.get(k, 0)) for a, b in zip(ac, bc))
                 for k in ("rho", "p", "vx", "vy", "vz", "bx", "by", "bz")}
        error["energy"] = max(abs(a["energy"] - (b["energy"] - b["rho"]*(2*b["vx"]-b["vy"]) + 2.5*b["rho"])) for a, b in zip(ac, bc))
        error["origin"] = max(abs((b-a-v*.02+.5) % 1-.5) for a, b, v in zip(ar["auxiliary_origin"], br["auxiliary_origin"], (2, -1)))
        assert max(error.values()) <= 1e-9
        assert ar["auxiliary_roots"] == br["auxiliary_roots"] and ar["steps"] > 2
        boosts.append({"jitter": jitter, "max_errors": error})
    result.update(curl=curl, uniform=uniform, boost=boosts)

    gauge = []
    damping = .15 * 16 * math.sqrt(math.pi)
    k = math.sin(TAU / 16) * 16
    omega = math.sqrt(k*k - damping*damping/4)
    exact_a = .001 * math.exp(-damping*.05/2) * (math.cos(omega*.05) + damping/(2*omega)*math.sin(omega*.05))
    exact_phi = -.001 * k/omega * math.exp(-damping*.05/2) * math.sin(omega*.05)
    for limited in (True, False):
        series = []
        for dt in (.001, .0005, .00025):
            name = f"gauge_dt{dt}_limited{limited}"
            extra = [] if limited else ["--unlimited"]
            _, (_, final) = run(name, "gauge", 16, 0, .05, "--dt", dt, *extra)
            ea = weighted([c["ax"]-exact_a*math.cos(TAU*c["x"]) for c in final], final)[1]
            ep = weighted([c["phi"]-exact_phi*math.sin(TAU*c["x"]) for c in final], final)[1]
            bmax = max(math.sqrt(sum(c[k]**2 for k in ("bx", "by", "bz"))) for c in final)
            assert bmax <= 1e-10
            gauge.append({"run": name, "limited": limited, "dt": dt, "A_L2": ea, "phi_L2": ep, "B_max": bmax})
            series.append([ea, ep])
        for k in (0, 1):
            assert .8 <= orders([e[k] for e in series])[-1] <= 1.2
    _, (initial, final) = run("gauge_jitter", "gauge", 16, .15, .05, "--dt", .0005)
    b_initial = max(math.sqrt(sum(c[k]**2 for k in ("bx", "by", "bz"))) for c in initial)
    b_change = max(math.sqrt(sum((b[k]-a[k])**2 for k in ("bx", "by", "bz"))) for a, b in zip(initial, final))
    amplitude = max(max(math.sqrt(sum(c[k]**2 for k in ("ax", "ay", "az"))), abs(c["phi"])/math.sqrt(5/3*c["p"]/c["rho"])) for c in final)
    assert amplitude <= .002
    result.update(gauge=gauge, irregular_gauge={"initial_B_max": b_initial, "B_change_max": b_change, "gauge_amplitude_max": amplitude,
                  "interpretation": "coupled cleaning run; initial discrete curl and subsequent magnetic change are not zero"})

    deform = []
    for limited in (True, False):
        series = []
        for dt in (.004, .002, .001):
            extra = [] if limited else ["--unlimited"]
            record, (_, final) = run(f"deform_dt{dt}_limited{limited}", "deform", 6, 0, .04,
                                    "--dt", dt, "--motion", "prescribed", *extra)
            exact = {"rho": 1, "p": .01, "vx": 0, "vy": 0, "vz": 0, "bx": .3, "by": .2, "bz": .1}
            errors = {k: max(abs(c[k]-v) for c in final) for k, v in exact.items()}
            error = max(errors.values())
            series.append(error)
            deform.append({"limited": limited, "dt": dt, "physical_max": error, "errors": errors,
                           "step_GCL_max": record["geometric_conservation_max"]})
        assert series[-1] < series[0]
    result["deform"] = deform
    # Observational extension suggested by the independent AI review, AFTER the
    # original gates were evaluated. No new success threshold is inferred here.
    mean_options = ["--mean-bx", .3, "--mean-by", .2, "--mean-bz", .1]
    ar, (_, ac) = run("mean_smooth", "smooth", 8, .15, .02, *mean_options)
    br, (_, bc) = run("mean_boost", "smooth", 8, .15, .02, *mean_options,
                        "--boost-x", 2, "--boost-y", -1, "--motion", "rigid", "--mesh-x", 2, "--mesh-y", -1)
    result["nonuniform_mean_boost_observation"] = {
        "origin": "extra diagnostic requested by AI review after the predeclared gates; not an acceptance test",
        "max_errors": {k: max(abs(a[k]-b[k]+{"vx": 2, "vy": -1}.get(k, 0)) for a, b in zip(ac, bc))
                       for k in ("rho", "p", "vx", "vy", "vz", "bx", "by", "bz")},
        "baseline_steps": ar["steps"], "boosted_steps": br["steps"],
        "limitation": "nonuniform flow with nonzero mean B does not establish general Galilean invariance; investigate under #7"
    }
    result["runs"] = runs
    result["all_study_gates_passed"] = True
    (output / "summary.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if sources != {p: sha(ROOT / p) for p in source_paths}:
        raise ValueError("study sources changed during execution")
    record = {"created_utc": datetime.now(timezone.utc).isoformat(), "revision": revision, "dirty_status": dirty,
              "source_sha256": sources, "platform": platform.platform(), "machine": platform.machine(),
              "rustc": command([str(Path(cargo).with_name("rustc")), "-Vv"]), "commands": commands,
              "configuration": {"profile": "paper-global-v2", "precision": "f64", "lengths": [1, 1], "boundary": "periodic",
                                "units": "dimensionless mu0=1", "gamma": 5/3, "ranks": 1, "threads": 1,
                                "seed": "deterministic trigonometric jitter; no RNG", "build": "release --locked"},
              "result_sha256": {"summary.json": sha(output / "summary.json"), **hashes}}
    (output / "provenance.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"All predeclared study gates passed ({len(runs)} runs). Results: {output}")


if __name__ == "__main__":
    main()
