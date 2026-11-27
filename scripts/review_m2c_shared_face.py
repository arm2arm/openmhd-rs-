"""Verify each measured map and spatial ladder against its original REANA downloads."""
import argparse
import io
import json
import math
from pathlib import Path

import numpy as np
from review_m2c_centroid import identity, read_packet, receipt, require

FAMILIES=("regular","seed1","seed2","seed3","original","fresh-a","fresh-b")
STEPS=(8,16,32)
MEANS=("zero","mean")


def review(path):
    manifest=json.loads((path/"manifest.json").read_bytes())
    f={}
    for name,pin in manifest["archives"].items():
        require(Path(name).name==name and name.endswith(".tar.gz"),"archive name")
        part=path/name
        require(identity(part.read_bytes())==pin,"archive digest "+name)
        chunk=read_packet(part)
        require(not (chunk.keys() & f.keys()),"duplicate packet member")
        f.update(chunk)
    release=json.loads(f["release.json"])
    build=json.loads(f["build/build.json"])
    uid,pins,outputs,_=receipt(f,"build",release["build_name"])
    require(uid==release["build_uuid"] and build["source_revision"]==release["source_revision"],"build source and workflow")
    for k,pin in outputs.items():require(identity(f["build/"+k.split("/")[-1]])==pin,k)
    require([c["argv"][1] for c in build["commands"]]==["fmt","clippy","build"] and
            all(c["returncode"]==0 and c["sha256"]==identity(f[f"build/build-{i}.log"])["sha256"]
                for i,c in enumerate(build["commands"])),"native build")
    binary=identity(f["build/shared-face"])
    require(pins["snapshot.json"]==identity(f["build/snapshot.json"]) and
            binary["sha256"]==build["executables"]["shared-face"]["sha256"],"compiled executable")
    snap=json.loads(f["build/snapshot.json"])
    require(snap["source_revision"]==build["source_revision"] and
            identity(f["build/runtime.json"])["sha256"]==build["runtime_sha256"] and
            all(pins[n]["sha256"]==h for n,h in snap["upload_sha256"].items()) and
            pins["face_build.py"]==identity(f["build/face_build.py"]), "build source and runtime")
    maps={};spatial={};ids=set()
    wanted={"map/"+m for m in ("single","cube","jitter")}|{f"space/{m}-{n}-{b}" for m in FAMILIES for n in STEPS for b in MEANS}
    require(set(release["cases"])==wanted,"registered case inventory")
    for tag,name in release["cases"].items():
        prefix="cases/"+tag
        get=lambda n:f[prefix+"/"+n]
        uuid,inputs,outputs,spec=receipt(f,prefix,name)
        require(uuid not in ids and uuid!=uid and inputs["field-operator"]==binary,"unique workflow and frozen executable")
        ids.add(uuid)
        for k,pin in outputs.items(): require(identity(get(k))==pin,k)
        j=json.loads(get("result.json")); p=j["selection"]
        require(identity(get("selection.json"))==inputs["selection.json"] and json.loads(get("selection.json"))==p and
                p["build_uuid"]==uid and p["source_revision"]==build["source_revision"],tag+" selection")
        for k,pin in p["inputs"].items():
            require(pin==inputs[k]["sha256"],tag+" staged "+k)
            if k!="field-operator":require(identity(f["source/"+pin+"/"+k])==inputs[k],tag+" source "+k)
        step,=spec["workflow"]["specification"]["steps"]
        require(step["kubernetes_cpu_limit"]==str(p["threads"]) and step["kubernetes_memory_limit"]==("4Gi" if tag.startswith("map/") else "8Gi"),tag+" resources")
        require(j["raw_sha256"]==outputs["observations.npz"]["sha256"],tag+" original fields")
        with np.load(io.BytesIO(get("observations.npz")),allow_pickle=False) as z:
            if tag.startswith("map/"):
                c=z["candidate"];expected=z["independent"];sing=z["singular_values"]
                require(np.isfinite(c).all() and np.allclose(c,expected,atol=1e-12,rtol=1e-12) and
                        max(j["checks"].values())<=1e-12 and j["passed"],tag+" dense map, transpose and diagonal")
                require(tag=="map/"+p["mesh"],tag+" mesh tag")
                maps[p["mesh"]]=dict(workflow=uuid,cells=j["owner_count"],faces=j["face_count"],
                    max_error=j["max_error"],singular_values=sing.tolist(),mean_error=j["mean_difference"])
                continue
            n,mean=p["n"],p["mean"]
            require(tag==f"space/{p['mesh']}-{n}-{mean}",tag+" mesh tag")
            vol=z["volumes"]; b=z["field"]; exact=z["reference"];div=z["divergences"]
            imposed=np.array([0.,0.,0.] if mean=="zero" else [.3,-.2,.4])
            require(b.shape==exact.shape==div.shape==(n**3,3) and (vol>0).all() and abs(vol.sum()-1)<1e-10,tag+" cell words")
            l1=np.average(np.linalg.norm(b-exact,axis=1),weights=vol)/np.average(np.linalg.norm(exact-imposed,axis=1),weights=vol)
            delta=np.array([math.fsum(v*x for v,x in zip(vol,b[:,k]))/math.fsum(vol)-imposed[k] for k in range(3)])
            require(abs(l1-j["normalized_l1"])<=1e-13 and
                    max(abs(delta-np.array(j["signed_mean_error"])))<=1e-14,tag+" reduced fields")
            rms=np.sqrt(np.sum(vol[:,None]*div**2,axis=0)/vol.sum())
            require(np.allclose(rms,[j["divergence"][k]["rms"] for k in ("cell_ls","face_mean","face_limited")],
                                rtol=1e-12,atol=1e-12),tag+" independent divergence")
            mean_flux=math.fsum(float(v*x) for v,x in zip(vol,div[:,1]))/math.fsum(vol)
            passed=bool(j["reference_bound"]<=1e-5 and max(abs(delta))/math.tau<=1e-9 and
                        abs(mean_flux)/math.tau<=1e-12 and (n<32 or l1<=.1))
            require(passed==j["passed"],tag+" per-case verdict")
            spatial[(p["mesh"],mean,n)]=dict(uuid=uuid,l1=float(l1),scaled_mean=float(max(abs(delta))/math.tau),
                reference_bound=j["reference_bound"],reference_difference=j["degree12_difference"],
                flux_signed_mean=j["divergence"]["face_mean"]["signed_mean"],rms_divergence=rms.tolist(),
                per_case_passed=j["passed"])
    superseded = {}
    for tag in release.get("superseded", []):
        require(tag in wanted and tag.startswith("space/"), "old selection")
        old="history/"+tag+"/"
        orig=json.loads(f[old+"selection.json"]);new=json.loads(f["cases/"+tag+"/selection.json"])
        oldid=json.loads(f[old+"id.json"]);term=json.loads(f[old+"terminal.json"])
        require(oldid["uuid"]==term["id"] and term["version"]==1 and term["status"]=="failed" and
                oldid["uuid"] not in ids and oldid["name"]!=release["cases"][tag],tag+" failed original workflow")
        require(f[old+"native-failure.txt"].decode().strip()=="Error: InvalidSample",tag+" original native rejection")
        oldinputs=json.loads(f[old+"inputs.json"])
        require(oldinputs["uuid"]==oldid["uuid"] and oldinputs["files"]["selection.json"]==identity(f[old+"selection.json"]) and
                all(orig[k]==new[k] for k in ("mesh","n","mean","threads","build_uuid","source_revision")),tag+" repair scope")
        for k,pin in orig["inputs"].items():
            require(oldinputs["files"][k]["sha256"]==pin and
                    (k=="m2c_shared_face_spatial.py" or pin==new["inputs"][k]),tag+" original exporter inputs")
            if k!="field-operator":require(identity(f["source/"+pin+"/"+k])==oldinputs["files"][k],k)
        superseded[tag]=dict(uuid=oldid["uuid"],status=term["status"],prior_exporter=orig["reference_revision"],revised_exporter=new["reference_revision"])
    ladders=[]
    for family in FAMILIES:
        for mean in MEANS:
            levels=[spatial[(family,mean,n)] for n in STEPS]
            order=math.log(levels[0]["l1"]/levels[-1]["l1"])/math.log(4)
            # Record every sequence, including small positive roundoff values;
            # selecting a fitted floor after measurement cannot give a pass.
            rms=np.array([v["rms_divergence"] for v in levels])
            decreases=[bool(np.all(np.diff(v)<0)) if np.any(v!=0.) else True for v in rms.T]
            ladders.append(dict(mesh=family,mean=mean,levels=levels,spatial_order=order,rms_decreases=decreases,
                mean_passed=all(v["scaled_mean"]<=1e-9 for v in levels),
                field_passed=order>=1.8 and levels[-1]["l1"]<=0.1 and all(v["per_case_passed"] for v in levels),
                divergence_passed=all(decreases)))
    return dict(schema="openmhd.m2c.shared-face-review.v1",build_uuid=uid,source_revision=build["source_revision"],
                map_cases=maps,superseded_workflows=superseded,spatial_ladders=ladders,workflow_count=len(ids),
                spatial_mean_passed=all(v["mean_passed"] for v in ladders),
                spatial_field_passed=all(v["field_passed"] for v in ladders),
                divergence_decreased_on_all=all(v["divergence_passed"] for v in ladders))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("packet",type=Path);p.add_argument("output",type=Path)
    args=p.parse_args();args.output.write_text(json.dumps(review(args.packet),indent=2,allow_nan=False)+"\n")
