"""Compare three spatial resolutions and their paired, half-timestep solutions."""
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path


def need(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_bytes())


def digest(path):
    with path.open("rb") as stream:
        h = hashlib.sha256()
        for block in iter(lambda: stream.read(1024*1024), b""):
            h.update(block)
        return h.hexdigest()


def final_cells(path):
    with gzip.open(path,"rb") as stream:
        for line in stream:
            if line.startswith(b"FINAL "):
                words = line.split()
                yield int(float(words[1])), [float(v) for v in words[2:6]], [float(v) for v in words[15:18]]


def measure(path):
    plan = read(path/"ladder.json")
    need(set(plan["cases"])=={f"n{n}-s{s}" for n in (8,16,32) for s in (2*n,4*n)},
         "three registered resolutions and both step counts")
    seen = set()
    levels = []
    for n in (8,16,32):
        runs = []
        for steps in (2*n,4*n):
            key = f"n{n}-s{steps}"
            folder = path/key
            files = plan["cases"][key]
            for name in ("metrics.json","native.json","stdout.gz"):
                need(digest(folder/name)==files[name], key+" artifact "+name)
            m, native = read(folder/"metrics.json"), read(folder/"native.json")
            case = native["case"]
            need(case==m["input"]["case"] and case["source"]==plan["source"] and case["build"]==plan["build"]
                 and case["args"]==["advection","deforming",str(steps),"0",str(n),"2"]
                 and m["input"]["native_sha256"]==files["native.json"] and m["checks_pass"]
                 and native["returncode"]==0 and not native["timed_out"], "solved and verified "+key)
            uid = m["input"]["uuid"]
            need(uid not in seen, "duplicate original workflow")
            seen.add(uid)
            metrics=m["metrics"]
            runs.append(dict(steps=steps, uuid=uid, elapsed_seconds=native["seconds"], peak_rss_kib=native["peak_rss_kib"],
                             relative_l1=metrics["relative_l1"], relative_rms=metrics["analytic_agreement"]["final"]["relative_rms"],
                             alignment=metrics["analytic_agreement"]["final"]["alignment_cosine"]))
        from itertools import zip_longest
        pair=[final_cells(path/f"n{n}-s{s}"/"stdout.gz") for s in (2*n,4*n)]
        errors=[]; volumes=[]
        for i,(a,b) in enumerate(zip_longest(*pair)):
            need(a is not None and b is not None and a[0]==i==b[0], "paired persistent owner")
            va, vb = a[1], b[1]
            need(va[0]>0 and abs(va[0]/vb[0]-1)<=1e-12 and
                 all(abs(x-y)<=2e-13 for x,y in zip(va[1:],vb[1:])), "paired final chart and volume")
            errors.append(va[0]*sum((x-y)**2 for x,y in zip(a[2],b[2])))
            volumes.append(va[0])
        need(len(errors)==n**3 and abs(math.fsum(volumes)-1.)<=1e-12, "paired volume closure")
        levels.append(dict(planes=n, cells=n**3, runs=runs, timestep_field_rms=math.sqrt(math.fsum(errors))))
    def ladder(column):
        errors = [level["runs"][0]["relative_l1"][column] for level in levels]
        need(all(math.isfinite(x) and x>0 for x in errors), "spatial field errors")
        adjacent = [math.log2(a/b) for a,b in zip(errors,errors[1:])]
        # Three equally spaced log resolutions. Their least-squares log-log
        # slope is the mean of the two measured adjacent slopes.
        return dict(errors=errors, adjacent_orders=adjacent, order=math.fsum(adjacent)/2)
    initial, final = ladder("initial"), ladder("final")
    return dict(source=plan["source"], build=plan["build"], levels=levels, initial=initial, final=final,
                final_field_spatial_gate_pass=final["order"]>=1.8 and final["errors"][-1]<=0.1)


if __name__ == "__main__":
    root, output = map(Path, sys.argv[1:])
    output.write_text(json.dumps(measure(root),sort_keys=True,indent=2,allow_nan=False)+"\n")
