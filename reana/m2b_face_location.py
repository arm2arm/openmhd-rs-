"""Separate face sampling and flux quadrature on an original jittered O02 mesh."""
import hashlib
import json
from pathlib import Path

import numpy as np

from m2b_o02 import SCALE, analytical, norms, write_input
from m2b_periodic_geometry import geometry


def exact_jacobian(points):
    """Rows differentiate components of B, columns are spatial coordinates."""
    sine = np.sin(SCALE * points)
    cosine = np.cos(SCALE * points)
    jacobian = np.empty((len(points), 3, 3))
    for a in range(3):
        b, c = (a + 1) % 3, (a + 2) % 3
        jacobian[:, a, a] = cosine[:, a] * (cosine[:, b] - cosine[:, c])
        jacobian[:, a, b] = -sine[:, a] * sine[:, b]
        jacobian[:, a, c] = sine[:, a] * sine[:, c]
    return SCALE**2 * jacobian


def divergence(mesh, field_on_faces):
    volume = mesh["vol"]
    flux = mesh["area"] * np.einsum("fi,fi->f", mesh["normal"], field_on_faces)
    net_flux = np.zeros_like(volume)
    np.add.at(net_flux, mesh["left"], flux)
    np.add.at(net_flux, mesh["right"], -flux)
    return net_flux / volume


def main():
    selection = json.loads(Path("selection.json").read_bytes())
    for path, digest in selection["inputs"].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Changed diagnostic input {path}")
    original = json.loads(Path("original.json").read_bytes())
    n = selection["n"]
    if original["selection"]["case"] != f"jitter-{n}-zero":
        raise ValueError("Expected the original zero-mean jittered case")
    mesh = geometry(n, True)
    cells, faces = mesh["cell"], mesh["face"]
    potential, field = analytical(cells)
    original_input = Path("original-metrics.bin")
    write_input(original_input, mesh, potential, (0.0, 0.0, 0.0))
    if hashlib.sha256(original_input.read_bytes()).hexdigest() != original["geometry_input_sha256"]:
        raise ValueError("Reconstructed mesh and potential differ from the original native input")

    left, right = mesh["left"], mesh["right"]
    midpoint = (cells[left] + (cells[right] + mesh["image"])) * 0.5
    offset = midpoint - faces
    exact_on_faces = analytical(faces)[1]
    from_centres = divergence(mesh, (field[left] + field[right]) * 0.5)
    from_faces = divergence(mesh, exact_on_faces)
    sampling_error = from_centres - from_faces
    # Taylor expansion of the two exact samples about the shared face centroid.
    linear_bias = np.einsum("fij,fj->fi", exact_jacobian(faces), offset)
    prediction = divergence(mesh, linear_bias)
    volume = mesh["vol"]
    measured = norms(from_centres, volume)
    if not np.isclose(measured["rms"], original["exact_field_face_mean"]["rms"], rtol=1e-12, atol=1e-13):
        raise ValueError("Failed to reproduce original independent face-mean RMS")
    correlation = np.average(sampling_error * prediction, weights=volume) / (
        norms(sampling_error, volume)["rms"] * norms(prediction, volume)["rms"]
    )
    report = {
        "selection": selection,
        "native_input_sha256": original["geometry_input_sha256"],
        "cells": len(cells),
        "faces": len(faces),
        "centroid_midpoint_offset_rms_in_spacings": float(
            n * np.sqrt(np.average((offset**2).sum(axis=1), weights=mesh["area"]))
        ),
        "exact_cell_samples_face_mean": measured,
        "exact_face_centroid_samples": norms(from_faces, volume),
        "difference": norms(sampling_error, volume),
        "first_order_offset_term": norms(prediction, volume),
        "remainder": norms(sampling_error - prediction, volume),
        "offset_term_correlation": float(correlation),
    }
    Path("diagnostic.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
