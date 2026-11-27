"""Measure the M2c initial mean on original M2b quadratic field words."""
import argparse
from fractions import Fraction
import hashlib
import io
import json
import math
from pathlib import Path
from uuid import UUID

import numpy as np


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def measure(case, volumes, field, configured):
    if volumes.shape != (case[1]**3,) or field.shape != (len(volumes), 3):
        raise ValueError("incomplete volume or field array")
    if (volumes.dtype != np.float64 or field.dtype != np.float64 or
            not np.isfinite(volumes).all() or not np.isfinite(field).all() or min(volumes) <= 0):
        raise ValueError("invalid binary64 geometry or field")
    total = math.fsum(volumes)
    if abs(total-1) > 1e-10:
        raise ValueError("periodic box volume")
    exact_volumes = [Fraction.from_float(float(v)) for v in volumes]
    exact_total = sum(exact_volumes)
    means, delta, reverse_errors, roundoff = [], [], [], []
    for col, target in zip(field.T, configured):
        exact = sum(v*Fraction.from_float(float(b)) for v,b in zip(exact_volumes, col))/exact_total
        direct = math.fsum(float(v)*float(b) for v,b in zip(volumes,col))/total
        reverse = math.fsum(float(v)*float(b) for v,b in zip(volumes[::-1],col[::-1]))/total
        means.append(float(exact))
        delta.append(float(exact - Fraction.from_float(target)))
        reverse_errors.append(abs(direct-reverse))
        roundoff.append(abs(float(exact-Fraction.from_float(direct))))
    scale = math.tau
    component = max(map(abs,delta))
    return dict(configured=configured, exact_rounded_mean=means, signed_difference=delta,
                absolute_max_component=component, euclidean_error=math.dist(delta,(0,0,0)),
                field_scale=scale, scaled_max_component=component/scale, threshold=1e-9,
                scaled_using_analytic_upper_bound=component/(2*math.sqrt(3)*scale+math.hypot(*configured)),
                compensated_vs_exact=max(roundoff), forward_vs_reverse=max(reverse_errors),
                volume=total, cells=len(volumes), passed=component/scale<=1e-9)


def evaluate(path):
    def read(name):
        return (path/name).read_bytes()
    metadata=json.loads(read("case.json"))
    records={name:json.loads(read(name)) for name in ("result.json","terminal.json","selection.json","metrics.json")}
    receipt,terminal,selection,metrics=[records[name] for name in ("result.json","terminal.json","selection.json","metrics.json")]
    family,n,mean,field=case=selection["case"]
    if family not in ("regular","original","fresh-a","fresh-b") or n not in (8,16,32) or field!="original":
        raise ValueError("unregistered field or mesh")
    configured={"zero":[0.,0.,0.],"mean":[.3,-.2,.4]}[mean]
    if (case!=metadata["selection"] or metrics["selection"]!=selection or
        metrics["schema"]!="openmhd.m2b.closure-case.v2" or str(UUID(receipt["uuid"]))!=terminal["id"]
        or terminal["status"]!="finished" or terminal["workflow"]!=receipt["workflow"] or terminal["version"]!=1
        or sha(read("metrics.json"))!=receipt["outputs"]["metrics.json"]["sha256"] or sha(read("inputs.json"))!=receipt["inputs"]
        or sha(read("original-reana.yaml"))!=receipt["spec"]):
        raise ValueError("original execution or source mismatch")
    def array(name,key):
        raw=b"".join(read(p) for p in metadata["parts"][name])
        if (receipt["outputs"][name]!={"sha256":sha(raw),"bytes":len(raw)} or
            metrics["output_sha256"][name]!=sha(raw)):
            raise ValueError("changed original "+name)
        with np.load(io.BytesIO(raw),allow_pickle=False) as data:
            return data[key]
    v=array("geometry.npz","volumes")
    b=array("quadratic.npz","rows")
    if b.shape!=(n**3,14):
        raise ValueError("quadratic candidate rows")
    result=measure(case,v,b[:,:3],configured)
    result.update(schema="openmhd.m2c.initial-mean.v1", case=case, original_uuid=terminal["id"],
                  original_archive_sha256=metadata["archive_sha256"],
                  original_volumes_file=metrics["output_sha256"]["geometry.npz"],
                  original_field_file=metrics["output_sha256"]["quadratic.npz"])
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("case_directory",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    args.output.write_text(json.dumps(evaluate(args.case_directory),indent=2,sort_keys=True,allow_nan=False)+"\n")
