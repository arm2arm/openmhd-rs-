#!/usr/bin/env python3
"""Offline integrity/shape checks for the small independent M0 reference archive."""
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    packet = json.loads((ROOT / "benchmarks/m0/packet.json").read_text())
    archive = ROOT / "tests/reference/external_mhd"
    provenance = json.loads((archive / "provenance.json").read_text())
    assert provenance["athena_revision"] == packet["external_reference"]["revision"]
    assert all(provenance["gates"].values()), "a recorded reference gate failed"
    for name, digest in provenance["result_sha256"].items():
        assert hashlib.sha256((archive / name).read_bytes()).hexdigest() == digest, name
    for path in archive.glob("*.csv.gz"):
        case, resolution = path.name.removesuffix(".csv.gz").split("_")
        n = int(resolution)
        bins = n if case == "brio" else packet["external_reference"]["vortex_comparison_bins"]
        dimension = 1 if case == "brio" else 2
        rows = list(csv.DictReader(io.StringIO(gzip.decompress(path.read_bytes()).decode())))
        assert len(rows) == bins ** dimension, path.name
        for index, row in enumerate(rows):
            values = {key: float(value) for key, value in row.items()}
            assert all(map(math.isfinite, values.values())), path.name
            assert values["rho"] > 0 and values["p"] > 0, path.name
            x = (index % bins + 0.5) / bins + (0.5 if dimension == 1 else 0)
            y = 0.0 if dimension == 1 else (index // bins + 0.5) / bins
            assert abs(values["x"] - x) < 1e-14 and abs(values["y"] - y) < 1e-14, path.name
    for path in archive.glob("*.hst"):
        times = [float(line.split()[0]) for line in path.read_text().splitlines()
                 if line.strip() and not line.startswith("#")]
        assert times[0] == 0 and all(b > a for a, b in zip(times, times[1:])), path.name
        assert abs(times[-1] - (0.1 if path.name.startswith("brio") else 0.5)) < 1e-12, path.name
    print("M0 independent reference hashes, grids, positive states and history times verified.")


if __name__ == "__main__":
    main()
