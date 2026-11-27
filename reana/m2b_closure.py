"""One immutable REANA case for the M2b static-operator closure comparison."""
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess

import numpy as np

from m2b_o02 import SCALE, analytical, face_divergence, norms, sha, write_input
from m2b_periodic_geometry import compare_oracle, geometry


ORDERS = {"linear": 13, "quadratic": 14, "corrected": 7}
MEANS = {"zero": [0., 0., 0.], "mean": [.3, -.2, .4]}
SEEDS = {"regular": None, "original": 20261122, "fresh-a": 2026112701, "fresh-b": 2026112702}


def selections():
    for family in SEEDS:
        for n in (8, 16, 32):
            for mean in MEANS:
                yield family, n, mean, "original"
    for n in (8, 16, 32):
        yield "regular", n, "zero", "unequal"


def identifier(selection):
    family, n, mean, field = selection
    return f"{family}-{n:02}-{mean}-{field}"


def potential(kind, cells):
    if kind == "original":
        return analytical(cells)
    if kind != "unequal":
        raise ValueError(kind)
    x, y, _ = cells.T
    sx, cx = np.sin(math.tau*x), np.cos(math.tau*x)
    sy, cy = np.sin(2*math.tau*y), np.cos(2*math.tau*y)
    a = np.zeros_like(cells)
    a[:, 2] = sx*sy
    b = np.column_stack((2*math.tau*sx*cy, -math.tau*cx*sy, np.zeros_like(x)))
    return a, b


def independent_fluxes(g, fields):
    """Free-intercept area-weighted normal equations centered at each owner, using all its faces."""
    l, r, image = g["left"], g["right"], g["image"]
    width = np.cbrt(g["vol"])
    n = len(width)
    count = fields.shape[1]
    values = fields.reshape(n, 3*count)
    gram = np.zeros((n, 4, 4))
    rhs = np.zeros((n, 4, 3*count))
    separation = (g["cell"][r] - g["cell"][l]) + image
    for owner, neighbour, delta in ((l,r,separation),(r,l,-separation)):
        design = np.column_stack([np.ones(len(l)), delta/width[owner,None]])
        weighed = g["area"][:,None] * design
        np.add.at(gram,owner,weighed[:,:,None]*design[:,None,:])
        np.add.at(rhs,owner,weighed[:,:,None]*(values[neighbour]-values[owner])[:,None,:])
    # axis order is cell, derivative direction, field selector, vector component
    grad = (np.linalg.solve(gram,rhs)[:,1:,:]/width[:,None,None]).reshape(n,3,count,3)
    midpoint = 0.5 * (g["cell"][l] + (g["cell"][r] + image))
    delta_face = g["face"] - midpoint
    face = (fields[l]+fields[r])*0.5 + np.einsum("fakj,fa->fkj", (grad[l]+grad[r])*0.5,delta_face)
    flux = g["area"][:,None]*np.einsum("fkj,fj->fk",face,g["normal"])
    total = np.zeros((n,count))
    np.add.at(total,l,flux)
    np.add.at(total,r,-flux)
    return total/g["vol"][:,None]


def run():
    p = json.loads(Path("selection.json").read_bytes())
    if any(sha(name) != identity for name,identity in p["inputs"].items()):
        raise ValueError("closure input hash mismatch")
    case = tuple(p["case"])
    if case not in tuple(selections()):
        raise ValueError("unregistered mesh or field")
    family, n, mean_key, kind = case
    mean = np.array(MEANS[mean_key])
    g = geometry(n,family!="regular",SEEDS[family])
    oracle = None
    if family=="original" and n==8:
        with np.load("oracle.npz",allow_pickle=False) as kept:
            oracle = compare_oracle(g,kept)
    a, fluctuation = potential(kind,g["cell"])
    exact = fluctuation + mean
    metrics = Path("input.bin")
    write_input(metrics,g,a,mean)
    input_hash = sha(metrics)
    if p["original_input"] is not None and p["original_input"] != input_hash:
        raise ValueError("original released geometry or potential changed")
    exe = Path("operator")
    exe.chmod(0o700)
    output = Path("fields.bin")
    process = subprocess.run([str(exe.resolve()),str(metrics),str(output),"2","--closure-v2"],capture_output=True,timeout=1650)
    Path("native.stderr").write_bytes(process.stderr)
    process.check_returncode()
    cells = n**3
    arrays = {}
    with output.open("rb") as f:
        if struct.unpack("<8sI",f.read(12)) != (b"M2BR2v02",cells):
            raise ValueError("native format or cell count")
        for name,columns in ORDERS.items():
            arr = np.fromfile(f,dtype="<f8",count=cells*columns).reshape(cells,columns)
            if not np.isfinite(arr).all():
                raise ValueError("nonfinite native output")
            arrays[name] = arr
        if f.read(1):
            raise ValueError("trailing native output")
    legacy = hashlib.sha256(struct.pack("<8sI",b"M2BR2v01",cells))
    for name in ("linear","quadratic"):
        legacy.update(arrays[name][:,:-1].tobytes(order="C"))
    if p["original_native"] is not None and p["original_native"] != legacy.hexdigest():
        raise ValueError("legacy Rust fields differ from archived binary output")
    fields = np.stack([*(arr[:,:3] for arr in arrays.values()),exact],axis=1)
    skew = independent_fluxes(g,fields)
    vol = g["vol"]
    reference_mean = face_divergence(g,exact)
    np.savez_compressed("geometry.npz",centroids=g["cell"],volumes=vol,exact=exact,
                        reference_mean=reference_mean,reference_skew=skew[:,-1])
    measured = {}
    uncertainty = 128*np.finfo(float).eps*((SCALE+np.linalg.norm(mean))*n+n*n)
    for index,(name,arr) in enumerate(arrays.items()):
        np.savez_compressed(name+".npz",rows=arr)
        k = 4 if name=="corrected" else 5
        independent_mean = face_divergence(g,arr[:,:3])
        err_mean = float(np.max(abs(independent_mean-arr[:,k])))
        err_skew = float(np.max(abs(skew[:,index]-arr[:,-1])))
        if not (err_mean <= 4*uncertainty and err_skew <= 4*uncertainty):
            raise ValueError(f"independent reconstruction discrepancy {name}: {err_mean}, {err_skew}")
        rel = np.average(np.linalg.norm(arr[:,:3]-exact,axis=1),weights=vol)/np.average(np.linalg.norm(fluctuation,axis=1),weights=vol)
        measured[name] = dict(relative_curl_l1=float(rel),arithmetic=norms(arr[:,k],vol),
                              skew=norms(arr[:,-1],vol),cell_ls=norms(arr[:,k-1],vol),
                              limited=norms(arr[:,k+1],vol),max_arithmetic_difference=err_mean,
                              max_skew_difference=err_skew)
    report = dict(schema="openmhd.m2b.closure-case.v2",selection=p,input_sha256=input_hash,
                  native_output_sha256=sha(output),legacy_output_sha256=legacy.hexdigest(),
                  dimensions=n,cells=cells,faces=len(g["area"]),oracle=oracle,profiles=measured,
                  cubic_roundoff_budget=uncertainty,reference_arithmetic=norms(reference_mean,vol),
                  reference_skew=norms(skew[:,-1],vol),
                  output_sha256={f:sha(f) for f in ["geometry.npz","linear.npz","quadratic.npz","corrected.npz","native.stderr"]})
    Path("metrics.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")


if __name__=="__main__":
    run()
