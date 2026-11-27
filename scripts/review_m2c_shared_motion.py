"""Reconstruct moving-face differences and topology masks from actual native workflow outputs."""
import argparse
import json
import math
import re
import struct
from pathlib import Path

import numpy as np
from review_m2c_centroid import identity, read_packet, receipt, require

GROUPS=("field","transported","area","center","cov0","cov1","cov2")
POWERS=range(7,14)
CONTROLS=("periodic_mean_adjoint_and_constants","rigid_self_faces_and_degenerate_nonrigid_vertex")


def observations(text, power):
    sides={k:[{}, {}, {}] for k in ("FACE","STENCIL")}
    arrays={k:{} for k in GROUPS}
    native={}
    branch=quality=transport=None
    for line in text.splitlines():
        line=line.split(" ... ")[-1]
        head,_,after=line.partition(" ")
        if head in sides:
            stage,i,words=after.split(" ",2);dest=sides[head][int(stage)]
            require(int(i) not in dest,"duplicate support")
            dest[int(i)]=words
        elif head=="BRANCH":
            exp,branch=after.split();require(int(exp)==power,"branch exponent")
        elif head=="ENDPOINT":
            key,i,k,lo,hi,rate=after.split();word=(int(i),int(k))
            require(word not in arrays[key],"duplicate endpoint")
            arrays[key][word]=tuple(map(float,(lo,hi,rate)))
        elif head=="DIFF":
            exp,key,err,spacing=after.split()
            require(int(exp)==power and key not in native,"difference exponent")
            native[key]=tuple(map(float,(err,spacing)))
        elif head=="QUALITY":quality=float(after)
        elif head=="TRANSPORT":transport=float(after)
    require(all(len(x)==27 for x in sides["STENCIL"]) and all(len(x)>0 for x in sides["FACE"]),"retained geometry")
    eligible=all(v[0]==v[1]==v[2] for v in sides.values())
    require(branch==("matched" if eligible else "switched"),"observed branch and retained supports")
    geometries=[]
    for catalog in sides["FACE"]:
        by_key={}
        for face in catalog.values():
            key,separator,vertices=face.partition(" [[")
            require(separator and key not in by_key,"canonical face key and vertex identities")
            by_key[key]=vertices
        geometries.append(by_key)
    center=geometries[1];changes=[]
    for i in (0,2):
        end=geometries[i]
        changes.append(dict(added_faces=len(end.keys()-center.keys()),lost_faces=len(center.keys()-end.keys()),
                            changed_vertex_supports=sum(end[k]!=center[k] for k in end.keys() & center.keys()),
                            changed_stencils=sum(row!=sides["STENCIL"][1][k] for k,row in sides["STENCIL"][i].items())))
    info=dict(denominator=2**power,matched=eligible,faces=[len(x) for x in sides["FACE"]],endpoint_changes=changes)
    if not eligible:
        require(not native and not any(arrays.values()),"difference across topology switch")
        return info,{}
    require(set(native)==set(GROUPS) and quality is not None and quality>1e-10 and transport is not None and transport>1e-3,"smooth geometry and sample sensitivity")
    derivatives={};stats={}
    for key in GROUPS:
        n=27 if key in ("field","transported") else info["faces"][1]
        require(arrays[key].keys()=={(i,k) for i in range(n) for k in range(3)},key+" complete endpoint words")
        rows=np.array([arrays[key][k] for k in sorted(arrays[key])])
        require(np.isfinite(rows).all(),key+" finite words")
        lo,hi,rate=rows.T
        derivative=(hi-lo)*2**(power-1)
        scale=max(1,float(np.max(abs(rate))))
        err=float(np.max(abs(derivative-rate)))/scale
        spacing=float(np.max(np.spacing(abs(lo))+np.spacing(abs(hi))))*2**(power-1)/scale
        require(np.allclose((err,spacing),native[key],rtol=1e-12,atol=1e-18),key+" independent difference")
        stats[key]=dict(error=err,endpoint_spacing=spacing,scale=scale,components=len(rate))
        derivatives[key]=derivative
    info.update(quantities=stats,min_vertex_determinant=quality,transported_sample_response=transport)
    return info,derivatives


def review(path):
    f=read_packet(path);release=json.loads(f["release.json"])
    source=release["source_revision"];build=json.loads(f["build/build.json"]);uid,pins,outs,_=receipt(f,"build",release["build_name"])
    for k,pin in outs.items():require(identity(f["build/"+k.rsplit("/",1)[-1]])==pin,k)
    binary=identity(f["build/face-motion-tests"])
    require(build["source_revision"]==source and release["build_uuid"]==uid and
            binary["sha256"]==build["executables"]["face-motion-tests"]["sha256"] and
            build["runtime_sha256"]==identity(f["build/runtime.json"])["sha256"],"linked native build")
    for i,step in enumerate(build["commands"]):
        require(step["returncode"]==0 and identity(f[f"build/build-{i}.log"])["sha256"]==step["sha256"],"build steps")
    require([c["argv"][1] for c in build["commands"]]==["fmt","clippy","build","test"],"build actions")
    snapshot=json.loads(f["build/snapshot.json"])
    require(identity(f["build/snapshot.json"])==pins["snapshot.json"] and snapshot["source_revision"]==source and
            all(pins[n]["sha256"]==v for n,v in snapshot["upload_sha256"].items()),"original snapshot")
    for k in (k for k in f if k.startswith("source/")):
        require(identity(f[k])["sha256"]==snapshot["source_sha256"][k.removeprefix("source/")],k)
    points=json.loads(f["source/docs/galaxy/fixtures/m2c_shared_face_static_v1.json"])["generators"]["jitter"]
    words=f["source/crates/mhd-vector-pot/tests/fixtures/m2c_shared_jitter.bits"].decode().splitlines()
    require(len(points)==27 and words==[" ".join(struct.pack(">d",float.fromhex(v)).hex() for v in xyz) for xyz in points],"all 81 fixture words")
    sels={f"h{2**p}" for p in POWERS}|set(CONTROLS)
    require(set(build["selectors"])==set(release["names"])==sels,"exact controls")
    levels=[];diffs=[];ids=set();controls={}
    for sel,name in sorted(release["names"].items()):
        prefix="cases/"+sel;get=lambda n:f[prefix+"/"+n]
        case_id,inputs,outputs,_=receipt(f,prefix,name)
        require(case_id not in ids and inputs["face-motion-tests"]==binary,"unique leaf and binary")
        ids.add(case_id)
        for n,pin in outputs.items():require(identity(get(n))==pin,sel+" "+n)
        spec=json.loads(get("case.json"));r=json.loads(get("result.json"))
        require(inputs["case.json"]==identity(get("case.json")) and inputs["run_fv_motion.py"]==identity(f["run_fv_motion.py"]) and
                r["passed"] and r["returncode"]==0 and r["selector"]==sel==spec["selector"] and r["sha256"]==binary["sha256"] and
                r["stdout_sha256"]==outputs["stdout.txt"]["sha256"] and r["stderr_sha256"]==outputs["stderr.txt"]["sha256"] and
                r["parent"]==spec["parent"] and r["parent"]["uuid"]==uid and r["parent"]["source_revision"]==source,"native test receipt")
        text=get("stdout.txt").decode()
        require("running 1 test\n" in text and "1 passed; 0 failed; 0 ignored; 0 measured; 8 filtered out" in text,"exact test")
        if sel in CONTROLS:
            controls[sel]=dict(uuid=case_id)
            if sel==CONTROLS[0]:
                triplet,=re.findall(r"IDENTITIES ([^\n]+)",text)
                adj,constant,mean=map(float,triplet.split())
                require(max(abs(adj),abs(constant),abs(mean))<=1e-12,"F9, gauge and transpose")
                controls[sel].update(adjoint=adj,constant=constant,mean_rate=mean)
        else:
            power=int(sel[1:]).bit_length()-1
            obs,d=observations(text,power);obs["uuid"]=case_id
            levels.append(obs);diffs.append((obs["denominator"],d))
    levels.sort(key=lambda r:r["denominator"]);diffs=dict(diffs)
    require([x["denominator"] for x in levels]==[2**p for p in POWERS] and len(ids)==9,"all half-steps")
    fine=[r for r in levels if r["matched"]];summary={}
    if len(fine)>=3:
        for k in GROUPS:
            order=[math.log2(a["quantities"][k]["error"]/b["quantities"][k]["error"])
                   for a,b in zip(fine,fine[1:]) if a["denominator"]*2==b["denominator"] and
                   min(a["quantities"][k]["error"], b["quantities"][k]["error"])>
                   max(a["quantities"][k]["endpoint_spacing"],b["quantities"][k]["endpoint_spacing"])]
            end=fine[-1];n=end["denominator"];z=end["quantities"][k];uncertainty=None
            if n//2 in diffs and n//4 in diffs and k in diffs[n//2] and k in diffs[n//4]:
                r1=(4*diffs[n][k]-diffs[n//2][k])/3
                r2=(4*diffs[n//2][k]-diffs[n//4][k])/3
                uncertainty=float(np.max(abs(r1-r2)))/z["scale"]+z["endpoint_spacing"]
            summary[k]=dict(orders=order,finest=z["error"],reference_disagreement=uncertainty,
                            passed=bool(n==8192 and len(order)>=2 and min(order)>=1.8 and z["error"]<=1e-7 and
                                        uncertainty is not None and uncertainty<=1e-9))
    return dict(schema="openmhd.m2c.shared-face-smooth-motion-review.v1",source_revision=source,build_uuid=uid,
                levels=levels,controls=controls,quantities=summary,
                smooth_case_passed=bool(len(summary)==len(GROUPS) and all(row["passed"] for row in summary.values())))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("packet",type=Path);p.add_argument("output",type=Path)
    args=p.parse_args();args.output.write_text(json.dumps(review(args.packet),indent=2,allow_nan=False)+"\n")
