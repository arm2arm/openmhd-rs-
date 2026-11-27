"""Reduce original REANA fields and Rust test outputs without invoking candidate code."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct
from uuid import UUID

import numpy as np


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(observed, recorded):
    if not math.isclose(observed, recorded, rel_tol=5e-12, abs_tol=5e-14):
        raise ValueError(f"Independent reduction differs: {observed!r}, {recorded!r}")


def actual_outputs(directory, expected_files):
    seen = set()
    for name, receipt in read(directory / "results.json").items():
        if "failed" in receipt:
            raise ValueError(f"Unsuccessful original workflow {name}")
        case = directory / "workflow" / name
        if read(case / "result.json") != receipt or receipt["workflow"] != name + ".1":
            raise ValueError(f"Workflow receipt mismatch for {name}")
        uuid = UUID(receipt["uuid"])
        if uuid in seen or set(receipt["outputs"]) != set(expected_files):
            raise ValueError(f"Duplicate workflow or unexpected output inventory for {name}")
        seen.add(uuid)
        for filename, identity in receipt["outputs"].items():
            path = case / "outputs" / filename
            if path.stat().st_size != identity["bytes"] or sha(path) != identity["sha256"]:
                raise ValueError(f"Changed downloaded output {path}")
        yield case / "outputs", receipt


def scalar_statistics(values, volumes):
    return {
        "signed_mean": float(np.average(values, weights=volumes)),
        "l1": float(np.average(abs(values), weights=volumes)),
        "rms": float(np.sqrt(np.average(values**2, weights=volumes))),
        "maximum": float(np.max(abs(values))),
    }


def binary64_values(tree):
    if isinstance(tree, str):
        return [struct.unpack(">d", bytes.fromhex(tree))[0]]
    return [word for child in tree for word in binary64_values(child)]


def verify_polynomials(gate, directory):
    """Replay each original Rust stdout against the independently generated reference words."""
    by_name = {row["case"]: row for row in gate["cases"]}
    references = read(directory / "reference" / "results.json")
    if len(by_name) != 87 or set(by_name) != set(references):
        raise ValueError("Polynomial reference inventory")
    seen = set()
    maxima = {}
    rejected = 0
    for root, receipt in actual_outputs(directory / "O01", ("comparison.json", "native.stdout", "native.stderr")):
        report = read(root / "comparison.json")
        name = report["case"]
        entry = by_name[name]
        ref_receipt = references[name]
        ref_root = directory / "reference" / name
        ref_path = ref_root / "outputs" / "fixture.json"
        fixture = read(ref_path)
        expected = fixture["expected"]
        ref_hash = sha(ref_path)
        if (name in seen or name != fixture["name"] or receipt["uuid"] != entry["uuid"]
                or ref_receipt != read(ref_root / "result.json") or ref_receipt["uuid"] != entry["reference_uuid"]
                or ref_hash != ref_receipt["outputs"]["fixture.json"]["sha256"] or ref_hash != entry["reference_sha256"]
                or ref_hash != report["sha256"]["fixture.json"] or sha(root / "comparison.json") != entry["output_sha256"]
                or sha(root / "native.stdout") != entry["binary_stdout_sha256"] or report["passed"] is not True):
            raise ValueError(f"Polynomial provenance {name}")
        seen.add(name)
        lines = [line.split() for line in (root / "native.stdout").read_text().splitlines()]
        if expected["expected_fit"] == "reject_rank_deficient":
            if lines != [["reject", "RankDeficient"]] or report["exact_rank"] != expected["exact_design_rank"]:
                raise ValueError(f"Rank rejection {name}")
            rejected += 1
            continue
        header = lines[0]
        if (header[:3] != ["fit", str(expected["rows"]), str(expected["exact_design_rank"])]
                or len(header) != 6 or expected["expected_fit"] != "reproduce"):
            raise ValueError(f"Fit shape or rank {name}")
        condition, low, high = map(float, header[3:])
        if not 0 < low <= condition <= high <= 1e8:
            raise ValueError(f"Fit condition {name}")
        tolerance = max(1e-10, 64 * math.ulp(1.0) * condition)
        keys = dict(value="value_bits", gradient="gradient_bits", field="curl_A_bits", div_a="div_A_bits")
        if fixture["fit"] == "quadratic":
            keys.update(hessian="hessian_bits", curl_jacobian="curl_jacobian_bits", div_b_same_fit="div_B_same_fit_bits")
        observed = {label: binary64_values(words) for label, *words in lines[1:]}
        if set(observed) != set(keys) | {"residual"} or len(observed) != len(lines) - 1:
            raise ValueError(f"Polynomial output rows {name}")
        for label, expected_key in keys.items():
            target = binary64_values(expected[expected_key])
            values = observed[label]
            if len(target) != len(values) or not all(map(math.isfinite, values)):
                raise ValueError(f"Polynomial output dimensions {name} {label}")
            error = max(abs(x - y) for x, y in zip(values, target))
            if error > tolerance * max(1.0, *map(abs, target)) or error != report["errors"][label]:
                raise ValueError(f"Polynomial derivative {name} {label}")
            maxima[label] = max(maxima.get(label, 0.0), error)
    if seen != set(by_name) or rejected != 3 or maxima != gate["maximum_absolute_errors"]:
        raise ValueError("Polynomial gate replay differs from the original verdict")


def fourier(root, receipt, gate_hash):
    report = read(root / "metrics.json")
    case = report["selection"]
    n, mesh, mean = report["dimensions"], report["mesh"], report["mean"]
    field_hash = sha(root / "fields.npz")
    if (case["o01_gate_sha256"] != gate_hash or n != case["n"] or mesh != case["mesh"]
            or mean != case["mean_b"] or report["cells"] != n**3
            or field_hash != report["retained_fields_sha256"]):
        raise ValueError(f"Fourier packet linkage {root}")
    profiles = {}
    with np.load(root / "fields.npz", allow_pickle=False) as data:
        volumes, centres = data["volumes"], data["centroids"]
        if centres.shape != (n**3, 3) or volumes.shape != (n**3,) or not (volumes > 0).all():
            raise ValueError("Cell positions, positive volumes and resolution must agree")
        close(float(volumes.sum()), 1.0)
        phase = math.tau * centres
        target = np.empty_like(centres)
        for a in range(3):
            b, c = (a + 1) % 3, (a + 2) % 3
            target[:, a] = mean[a] + math.tau * np.sin(phase[:, a]) * (np.cos(phase[:, b]) - np.cos(phase[:, c]))
        close(float(np.max(abs(target - data["exact"]))), 0.0)
        wave_scale = np.average(np.linalg.norm(target - mean, axis=1), weights=volumes)
        exact_div = data["div_face_from_exact"]
        exact_rms = scalar_statistics(exact_div, volumes)["rms"]
        close(exact_rms, report["exact_field_face_mean"]["rms"])
        for fit, width in (("linear", 12), ("quadratic", 13)):
            observed = data[fit]
            if observed.shape != (n**3, width) or not np.isfinite(observed).all():
                raise ValueError("Nonfinite field or unexpected native columns")
            stored = report["profiles"][fit]
            field = observed[:, :3]
            curl_l1 = float(np.average(np.linalg.norm(field - target, axis=1), weights=volumes))
            relative = float(curl_l1 / wave_scale)
            close(curl_l1, stored["curl_l1"])
            close(relative, stored["normalized_curl_l1"])
            columns = {"div_a": 3, "cell_ls": 4, "face_mean": 5, "face_limited": 6}
            if fit == "quadratic":
                columns["same_fit"] = 12
            divergences = {}
            for label, column in columns.items():
                values = observed[:, column]
                stats = scalar_statistics(values, volumes)
                for key, value in stats.items():
                    close(value, stored["divergences"][label][key])
                if label != "div_a":
                    radius = np.cbrt(3 * volumes / (4 * math.pi))
                    scaled = radius * abs(values) / (np.linalg.norm(field, axis=1) + 1e-12 * math.tau)
                    stats["locally_scaled_rms"] = scalar_statistics(scaled, volumes)["rms"]
                    close(stats["locally_scaled_rms"], stored["divergences"][label]["cell_scaled_abs"]["rms"])
                divergences[label] = stats
            signed = abs(divergences["face_mean"]["signed_mean"]) / math.tau
            close(signed, stored["normalized_signed_face_sum"])
            mean_error = (np.average(field, weights=volumes, axis=0) - mean).tolist()
            for value, original in zip(mean_error, stored["mean_error"]):
                close(value, original)
            error_rms = scalar_statistics(observed[:, 5] - exact_div, volumes)["rms"]
            # Independent Python and native shared-face sums can differ by roundoff.
            if abs(error_rms - stored["face_mean_from_curl_error"]["rms"]) > stored["independent_face_difference"] + 5e-14:
                raise ValueError("Independent curl-error contribution to the face RMS")
            profiles[fit] = dict(
                normalized_curl_l1=relative, curl_l1=curl_l1, divergences=divergences,
                mean_error=mean_error, signed_face_sum=signed, max_condition=stored["max_condition"],
                sample_range=stored["sample_range"], ring_range=stored["ring_range"],
                face_mean_from_curl_error_rms=error_rms,
            )
    return dict(
        case=case["case"], mesh=mesh, n=n, mean_b=mean, uuid=receipt["uuid"], workflow=receipt["workflow"],
        source_revision=case["rust_revision"], build_uuid=case["build_uuid"], report_sha256=sha(root / "metrics.json"),
        fields_sha256=field_hash, cell_count=n**3, faces=report["faces"], profiles=profiles,
        m2a_metric_differences=report["m2a_metric_differences"], exact_field_face_mean_rms=exact_rms,
    )


def fourier_summary(directory, gate_hash):
    rows = [fourier(root, receipt, gate_hash) for root, receipt in
            actual_outputs(directory, ("metrics.json", "fields.npz", "native.stderr"))]
    by_key = {(row["mesh"], row["n"], tuple(row["mean_b"])): row for row in rows}
    if len(rows) != 12 or len(by_key) != 12:
        raise ValueError("Expected all twelve distinct Fourier runs")
    ladders = []
    for mesh in ("regular", "jitter"):
        for mean in ((0.0, 0.0, 0.0), (0.3, -0.2, 0.4)):
            cases = [by_key[mesh, n, mean] for n in (8, 16, 32)]
            for fit in ("linear", "quadratic"):
                profiles = [case["profiles"][fit] for case in cases]
                errors = [profile["normalized_curl_l1"] for profile in profiles]
                pair_orders = [math.log2(a / b) for a, b in zip(errors, errors[1:])]
                order = math.log(errors[0] / errors[2]) / math.log(4.0)
                rms = [profile["divergences"]["face_mean"]["rms"] for profile in profiles]
                gates = dict(
                    face_mean_rms_decreases=all(a > b for a, b in zip(rms, rms[1:])),
                    global_signed_face_sum=max(p["signed_face_sum"] for p in profiles) <= 1e-12,
                )
                if fit == "quadratic":
                    gates.update(curl_order=order >= 1.8, finest_normalized_l1=errors[-1] <= 0.1)
                ladders.append(dict(mesh=mesh, mean_b=mean, fit=fit, normalized_l1=errors, pair_orders=pair_orders,
                                    order=order, face_mean_rms=rms, gates=gates, passed=all(gates.values())))
    return dict(passed=all(row["passed"] for row in ladders), ladders=ladders, cases=sorted(rows, key=lambda r: r["case"]))


def auxiliary_summary(directory, gate_hash):
    expected = {
        f"tricubic_{i}{j}{k}": ("polynomial_max_scaled", 1e-10)
        for i in range(4) for j in range(4) for k in range(4)
    }
    expected.update({f"tricubic_all_faces_and_seams_{a}": ("shared_face_max_absolute", 1e-12) for a in "xyz"})
    for fit in ("linear", "quadratic"):
        expected[f"{fit}_curl_transpose"] = ("adjoint_relative", 1e-12)
        expected[f"{fit}_gauge_constant"] = ("constant_curl_max", 0.0)
    expected.update({
        "deposition_aliases_and_empty_root": ("alias_mass_error", 1e-15),
        "one_root_volume_weighted_mean": ("volume_mean_max", 1e-12),
        "deposition_order_and_translated_origin": ("translated_jet_difference", 0.0),
    })
    rows = []
    for root, receipt in actual_outputs(directory, ("comparison.json", "native.stdout", "native.stderr")):
        result = read(root / "comparison.json")
        selection = result["selection"]
        selector = selection["selector"]
        metric, limit = expected[selector]
        stdout = (root / "native.stdout").read_text()
        extracted = re.findall(r"metric ([a-z_]+) (\S+)", stdout)
        if len(extracted) != 1 or extracted[0][0] != metric:
            raise ValueError(f"Missing the declared native metric for {selector}")
        value = float(extracted[0][1])
        if (result["passed"] is not True or result["returncode"] != 0 or not 0 <= value <= limit
                or result["metrics"] != {metric: value} or selection["o01_gate_sha256"] != gate_hash
                or selection["catalog_size"] != len(expected) or "test " + selector + " ... " not in stdout
                or f"1 passed; 0 failed; 0 ignored; 0 measured; {len(expected)-1} filtered out" not in stdout
                or result["stdout_sha256"] != sha(root / "native.stdout")
                or result["stderr_sha256"] != sha(root / "native.stderr")):
            raise ValueError(f"Native test result disagrees with the original selection {selector}")
        rows.append(dict(selector=selector, uuid=receipt["uuid"], workflow=receipt["workflow"], metrics=result["metrics"],
                         stdout_sha256=result["stdout_sha256"], result_sha256=sha(root / "comparison.json"),
                         build_uuid=selection["build_uuid"]))
    if len(rows) != len(expected) or {row["selector"] for row in rows} != set(expected):
        raise ValueError("Incomplete auxiliary-control matrix")
    return dict(passed=True, cases=sorted(rows, key=lambda row: row["selector"]))


def summarize(o01_path, o02_path, o03_path):
    original = read(o01_path)
    if original["passed"] is not True or len(original["cases"]) != 87:
        raise ValueError("Missing O01 evidence")
    gate_hash = sha(o01_path)
    o01 = {key: original[key] for key in ("passed", "reproduced", "rejected_deficient", "maximum_absolute_errors")}
    o02 = fourier_summary(o02_path, gate_hash)
    o03 = auxiliary_summary(o03_path, gate_hash)
    return dict(schema="openmhd.static-3d-operators.summary.v1", o01_gate_sha256=gate_hash,
                o01=o01, o02=o02, o03=o03, all_registered_gates_passed=all(g["passed"] for g in (o01, o02, o03)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("o01_gate", "o02", "o03", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--polynomial-outputs", type=Path, help="Parent directory containing O01 and reference")
    args = parser.parse_args()
    if args.polynomial_outputs is not None:
        verify_polynomials(read(args.o01_gate), args.polynomial_outputs)
    summary = summarize(args.o01_gate, args.o02, args.o03)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print("All registered gates passed:", summary["all_registered_gates_passed"])
