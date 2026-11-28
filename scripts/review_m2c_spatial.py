"""Measure one completed coupled helix case from the captured native output."""
import gzip
import json
import math
from pathlib import Path
from review_m2c_smooth_step import cell_oracle, decode, norm, require, sha


def weighted_error(raw, args, tag):
    size = int(args[4])
    t = 0.0 if tag == b"INITIAL" else 1/32
    error, scale = [], []
    for line in raw.splitlines():
        if not line.startswith(tag + b" "):
            continue
        words = line.split()
        i = len(error)
        require(float(words[1]) == i, "cell ordering")
        ref = cell_oracle(args, size, i, t)
        volume = float(words[2])
        b = map(float, words[15:18])
        error.append(volume * norm([a-r for a,r in zip(b,ref["b"])]))
        scale.append(volume * norm(ref["b"]))
    require(len(error) == size**3 and math.fsum(scale) > 0., "field normalization")
    return math.fsum(error)/math.fsum(scale)


def compare(raw, previous):
    """Maximum absolute differences of the emitted quantities in code units."""
    before, after = previous.splitlines(), raw.splitlines()
    require(len(after) == len(before), "comparison row inventory")
    peaks = {}
    for x,y in zip(before, after):
        tag, *left = x.split()
        name, *right = y.split()
        require(name == tag and len(right) == len(left), "comparison schema")
        diffs = [abs(float(a)-float(b)) for k,(a,b) in enumerate(zip(left,right))
                 if not (tag == b"STAGE" and k == 5)]
        require(all(math.isfinite(v) for v in diffs), "finite comparison")
        key = tag.decode("ascii")
        peaks[key] = max(peaks.get(key, 0.), max(diffs))
    return peaks


def main():
    plan = json.loads(Path("analysis.json").read_bytes())
    result = json.loads(Path("native.json").read_bytes())
    require(sha(Path("native.json").read_bytes()) == plan["native_sha256"], "native receipt")
    require(result["case"] == plan["case"] and result["returncode"] == 0 and not result["timed_out"],
            "successful native child")
    require(plan["case"]["args"][0:2] == ["advection","deforming"], "field and motion")
    pieces = []
    for i,(name,witness) in enumerate(sorted(result["parts"].items())):
        require(name == f"stdout.part{i:04d}", "part ordering")
        data = Path(name).read_bytes()
        require(len(data)==witness["bytes"] and sha(data)==witness["sha256"], "part contents")
        pieces.append(data)
    raw = gzip.decompress(b"".join(pieces))
    require(sha(raw) == result["stdout_sha256"] and len(raw)==result["native_stdout_bytes"], "original output")
    metrics,_ = decode(result["case"],raw)
    args = result["case"]["args"]
    metrics["relative_l1"] = {tag.decode().lower():weighted_error(raw,args,tag) for tag in [b"INITIAL",b"FINAL"]}
    overlap = None
    if plan.get("reference"):
        original = Path("reference.gz").read_bytes()
        require(sha(original)==plan["reference"]["sha256"], "original comparison")
        overlap = compare(raw,gzip.decompress(original))
    report = dict(input=plan, metrics=metrics, overlap_max_abs=overlap,
                  checks_pass=metrics["checks_pass"] and (overlap is None or max(overlap.values())<=5e-10))
    Path("metrics.json").write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")


if __name__ == "__main__":
    main()
