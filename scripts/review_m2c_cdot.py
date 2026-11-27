"""Replay the periodic point-curl derivative ladder from original native REANA output."""
import argparse
import io
import json
import math
from pathlib import Path
import tarfile

from review_m2c_centroid import read_packet, receipt, identity, sha, require

CONTROLS=("coalesced_transpose_diagonal_and_constants","moving_polynomial_chain_rule","rigid_and_stale_motion")
STEPS=tuple(2**p for p in range(4,11))


def ladder(stdout,denominator):
    rows={}
    for line in stdout.splitlines():
        if "CDOT " in line:
            power,i,k,lo,hi,d=line.split("CDOT ",1)[1].split()
            key=int(i),int(k)
            require(2**int(power)==denominator and key not in rows,"duplicate or wrong raw observation")
            rows[key]=tuple(map(float,(lo,hi,d)))
    require(set(rows)=={(i,k) for i in range(27) for k in range(3)}
            and all(math.isfinite(v) for row in rows.values() for v in row),"raw finite-difference data")
    quality,=[list(map(float,line.split()[1:])) for line in stdout.splitlines() if line.startswith("QUALITY ")]
    require(len(quality)==2 and all(math.isfinite(x) and x>0 for x in quality),"QR measurements")
    scale=max(1,max(abs(d) for _,_,d in rows.values()))
    error=max(abs((hi-lo)*denominator/2-d) for lo,hi,d in rows.values())/scale
    return dict(denominator=denominator,scaled_error=error,max_qr_condition=quality[0],max_inverse_r_norm=quality[1])


def review(path):
    files=read_packet(path)
    build=json.loads(files["build/build.json"])
    ref=build["source_revision"]
    catalog=sorted([*CONTROLS,*["h"+str(d) for d in STEPS]])
    require(sorted(build["selectors"])==catalog,"exact selector set")
    uid,pins,outputs,_=receipt(files,"build","openmhd-m2c-cdot-build-"+ref[:10])
    snap=json.loads(files["build/snapshot.json"])
    require(snap["source_revision"]==ref and pins["snapshot.json"]==identity(files["build/snapshot.json"])
            and pins["cdot_build.py"]==identity(files["build/cdot_build.py"]),"build pins")
    archive=snap["archives"]["source.tar.gz"]
    parts=[files["build/"+n] for n in archive["parts"]]
    require(all(identity(b)==pins[n] for n,b in zip(archive["parts"],parts)),"source parts")
    raw=b"".join(parts)
    require(sha(raw)==archive["sha256"],"source archive")
    with tarfile.open(fileobj=io.BytesIO(raw),mode="r:gz") as t:
        source={m.name:sha(t.extractfile(m).read()) for m in t if m.isfile()}
    require(source==snap["source_sha256"],"all source members")
    binary=identity(files["build/cdot-tests"])
    for key,record in outputs.items():require(record==identity(files["build/"+key.split("/")[-1]]),key)
    require([c["argv"][1] for c in build["commands"]]==["fmt","clippy","build","test"] and
            all(c["returncode"]==0 and c["sha256"]==sha(files[f"build/build-{i}.log"])
                for i,c in enumerate(build["commands"])) and "--no-run" in build["commands"][-1]["argv"] and
            binary["sha256"]==build["executables"]["cdot-tests"]["sha256"],"remote build")
    parent=dict(source_revision=ref,uuid=uid,report_sha256=sha(files["build/build.json"]),
                protocol_sha256=source["docs/galaxy/M2C_VALIDATION_PROTOCOL.md"])
    ids={}; observations=[]
    for index,sel in enumerate(catalog,1):
        prefix="cases/"+sel
        case_uuid,inputs,outputs,spec=receipt(files,prefix,f"openmhd-m2c-cdot-{ref[:10]}-{index:02}")
        ids[sel]=case_uuid
        args=["--exact",sel,"--nocapture","--test-threads=1"]
        case=files[prefix+"/case.json"]
        require(json.loads(case)==dict(selector=sel,binary="cdot-tests",sha256=binary["sha256"],parent=parent,args=args)
                and inputs["case.json"]==identity(case) and inputs["cdot-tests"]==binary and
                inputs["run_leaf.py"]==identity(files["run_leaf.py"]),sel+" submitted case")
        step,=spec["workflow"]["specification"]["steps"]
        require(step["kubernetes_cpu_limit"]=="1" and step["kubernetes_memory_limit"]=="4Gi" and
                "timeout 1800" in step["commands"][0],sel+" resources")
        for n,pin in outputs.items():require(pin==identity(files[prefix+"/"+n]),sel+" "+n)
        log=files[prefix+"/stdout.txt"].decode()
        actual=json.loads(files[prefix+"/result.json"])
        require(actual==dict(selector=sel,parent=parent,sha256=binary["sha256"],argv=args,returncode=0,
                stdout_sha256=outputs["stdout.txt"]["sha256"],stderr_sha256=outputs["stderr.txt"]["sha256"],passed=True)
                and f"test {sel} ..." in log and "1 passed; 0 failed; 0 ignored; 0 measured; 9 filtered out;" in log,sel)
        if sel not in CONTROLS:observations.append(ladder(log,int(sel[1:])))
    require(len({uid,*ids.values()})==len(catalog)+1,"unique native leaves")
    observations.sort(key=lambda x:x["denominator"])
    errors=[o["scaled_error"] for o in observations]
    orders=[math.log2(a/b) for a,b in zip(errors,errors[1:]) if max(a,b)>1e-11]
    passed=all(v>=1.8 for v in orders) and errors[-1]<=1e-7
    return dict(schema="openmhd.m2c.point-cdot.v1",parent=parent,case_count=len(catalog),workflows=ids,
                observations=observations,orders=orders,finest_scaled_error=errors[-1],passed=passed)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet",type=Path);parser.add_argument("output",type=Path)
    args=parser.parse_args()
    args.output.write_text(json.dumps(review(args.packet),sort_keys=True,indent=2,allow_nan=False)+"\n")
