"""Independently compare the acquired outputs of one scientific family across MPI layouts."""
import csv
import hashlib
import io
import json
import math
import statistics
import tarfile
from pathlib import Path

def require(condition, label):
    if not condition:
        raise ValueError(label)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def byteset(path):
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        require(all(p.isfile() and "/" not in p.name for p in members)
                and len({p.name for p in members})==len(members), "archive structure")
        return {p.name:archive.extractfile(p).read() for p in members}

def end_rows(body):
    rows = list(csv.reader(io.StringIO(body.decode())))
    return [rows[0], *[r for r in rows[1:] if r[0]==rows[-1][0]]]

def main():
    plan=json.loads(Path("comparison.json").read_bytes())
    rows=[]
    science={}
    require(len({k["uuid"] for k in plan["cases"]})==len(plan["cases"]), "unique REANA workflows")
    for i,item in enumerate(plan["cases"]):
        rp=Path(f"case-{i}.json")
        ap=Path(f"case-{i}.tar.gz")
        result=json.loads(rp.read_bytes())
        c=result["case"]
        require(item["result_sha256"]==sha(rp.read_bytes()) and
                item["archive_sha256"]==result["archive_sha256"]==sha(ap.read_bytes()),"acquired output identity")
        require(c["label"]==plan["label"] and c["source"]==plan["source"] and
                c["binary_sha256"]==plan["exe"] and c["parent"]==plan["parent"],"different numerical source")
        files=byteset(ap)
        require({p:sha(v) for p,v in files.items() if p!="ownership.csv"}==result["scientific"], "scientific files")
        science[item["uuid"]]=files
        rows.append(dict(uuid=item["uuid"],case=c,seconds=result["median_seconds"],
                         min_seconds=min(s["wall_seconds"] for s in result["samples"]),
                         max_seconds=max(s["wall_seconds"] for s in result["samples"]),
                         steps=len(result["samples"]),diagnostics=result["diagnostics"],
                         affinity=result["affinity"],cpu_max=result["cpu_max"],
                         median_rank_compute_wall=statistics.median(max(r["elapsed"] for r in s["ranks"]) for s in result["samples"]),
                         halo_bytes=sum(r["halo"] for r in result["samples"][0]["ranks"]),
                         work=[r["work"] for r in result["samples"][0]["ranks"]]))
    flavor=plan["kind"]
    ref=next(row for row in rows if row["case"]["reference"]) if flavor!="weak" else rows[0]
    expected=science[ref["uuid"]]
    for row in rows:
        c=row["case"]
        if flavor=="weak":
            require(c.get("scaling")=="weak" and c["threads"]==1 and c["ranks"] in (1,2,4), "weak scaling identity")
        elif flavor=="restart":
            actual=science[row["uuid"]]
            require(expected["checkpoint.bin"]==actual["checkpoint.bin"], "restart checkpoint byte mismatch")
            for name,body in expected.items():
                if name.endswith(".csv"):
                    require(end_rows(body)==end_rows(actual[name]) if c["family"]=="gravity"
                            else body==actual[name], "restart final state "+name)
        else:
            for name,body in expected.items():
                if name!="ownership.csv":
                    require(body==science[row["uuid"]][name], "layout mismatch "+name+" "+row["uuid"])
        row["speedup_vs_reference"]=ref["seconds"]/row["seconds"]
        base=next((r for r in rows if not r["case"]["reference"] and r["case"]["ranks"]==1
                   and r["case"]["threads"]==1),None)
        if base:
            row["relative_to_mpi_1x1"]=base["seconds"]/row["seconds"]
    out=dict(label=plan["label"],kind=flavor,source=plan["source"],parent=plan["parent"],binary_sha256=plan["exe"],
             cases=rows,reference_uuid=ref["uuid"],comparison_sha256=sha(Path("comparison.json").read_bytes()))
    Path("verified.json").write_text(json.dumps(out,indent=2,allow_nan=False)+"\n")

if __name__=="__main__":
    main()
