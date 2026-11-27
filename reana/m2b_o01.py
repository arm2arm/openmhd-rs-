"""Compare one Rust evaluation with one independent, immutable O01 fixture."""
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys


def number(word):
    return struct.unpack(">d", bytes.fromhex(word))[0]


def flat(values):
    if isinstance(values, str):
        return [number(values)]
    return [x for row in values for x in flat(row)]


def wire(packet):
    axis = "xyz".index(packet["A_component"] or "x")
    lines = [" ".join(("M2B1", packet["fit"], str(axis), packet["cell_volume_bits"], *packet["mean_B_bits"]))]
    for s in packet["samples"]:
        lines.append(" ".join((s["id"], *map(str, s["image"]), *s["displacement_bits"],
                               s.get("face_area_weight_bits", "-"), s["scalar_bits"])))
    return ("\n".join(lines) + "\n").encode()


def spectrum(data):
    # Independent LAPACK diagnostic. The production decision uses its own QR.
    import numpy as np
    h = number(data["cell_volume_bits"]) ** (1 / 3)
    rows = []
    for s in data["samples"]:
        d = list(map(number, s["displacement_bits"]))
        x, y, z = (t / h for t in d)
        row = [1., x, y, z]
        if data["fit"] == "quadratic":
            row += [x*x/2, y*y/2, z*z/2, x*y, x*z, y*z]
            weight = 1 / math.sqrt(sum(t*t for t in d))
        else:
            weight = number(s["face_area_weight_bits"])
        rows.append([a*math.sqrt(weight) for a in row])
    a = np.array(rows)
    scale = np.linalg.norm(a, axis=0)
    return np.linalg.svd(a / np.where(scale > 0, scale, 1.), compute_uv=False).tolist()


def main():
    native, source = Path("operator"), Path("fixture.json")
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (native, source)}
    pin = json.loads(Path("selection.json").read_bytes())
    if hashes != pin["sha256"]:
        raise ValueError("Case input identity")
    d = json.loads(source.read_bytes())
    if d["name"] != pin["case"] or d["gate"] != "O01":
        raise ValueError("Selection identity")
    native.chmod(0o700)
    run = subprocess.run([str(native.resolve())], input=wire(d), capture_output=True, timeout=180)
    Path("native.stdout").write_bytes(run.stdout)
    Path("native.stderr").write_bytes(run.stderr)
    run.check_returncode()
    rows = [line.split() for line in run.stdout.decode().splitlines()]
    e = d["expected"]
    result = dict(case=d["name"], sha256=hashes, source_revision=pin["revision"],
                  native_stdout_sha256=hashlib.sha256(run.stdout).hexdigest(),
                  exact_rank=e["exact_design_rank"], singular_values=spectrum(d))
    if e["expected_fit"] == "reject_rank_deficient":
        result.update(rejection=rows[0][1] if len(rows)==1 and len(rows[0])==2 else None,
                      passed=len(rows)==1 and rows[0]==["reject","RankDeficient"])
    else:
        head = rows[0]
        if head[0] != "fit" or len(head) != 6 or int(head[1]) != e["rows"] or int(head[2]) != e["exact_design_rank"]:
            raise ValueError("Expected a full-rank fit")
        k, low, high = map(float, head[3:])
        observed = {label: list(map(number, words)) for label,*words in rows[1:]}
        names = dict(value="value_bits",gradient="gradient_bits",field="curl_A_bits",div_a="div_A_bits")
        if d["fit"] == "quadratic":
            names.update(hessian="hessian_bits",curl_jacobian="curl_jacobian_bits",div_b_same_fit="div_B_same_fit_bits")
        if len(observed)!=len(rows)-1 or set(observed)!=set(names)|{"residual"}:
            raise ValueError("Candidate report shape")
        errors = {}
        scales = {}
        for name, target in names.items():
            expected = flat(e[target])
            actual = observed[name]
            if len(actual)!=len(expected) or not all(map(math.isfinite,actual)):
                raise ValueError("Nonfinite or mismatched output " + name)
            errors[name]=max(abs(x-y) for x,y in zip(actual,expected))
            scales[name]=max(1., *map(abs,expected))
        tol=max(1e-10,64*sys.float_info.epsilon*k)
        result.update(kappa1_r=k, kappa1_bounds=[low,high], tolerance=tol, errors=errors,
                      derivative_scales=scales, weighted_rms_residual=observed["residual"][0],
                      passed=low<=k<=high<=1e8 and all(v<=tol*scales[n] for n,v in errors.items()))
    Path("comparison.json").write_text(json.dumps(result,allow_nan=False,indent=2)+"\n")
    return 0 if result["passed"] else 1

if __name__=="__main__":
    sys.exit(main())
