"""Replay the three unequal-wave cube measurements and original workflow joins."""
import argparse
import io
import json
import math
from pathlib import Path

import numpy as np
from review_m2c_centroid import identity, read_packet, receipt, require


def review(packet):
    files=read_packet(packet)
    release=json.loads(files["release.json"])
    levels=[]
    for n in (8,16,32):
        prefix=str(n)
        uid,inputs,outputs,_=receipt(files,prefix,release["names"][prefix])
        get=lambda k:files[prefix+"/"+k]
        for k,v in outputs.items():require(identity(get(k))==v,prefix+" "+k)
        selection=json.loads(get("selection.json"))
        j=json.loads(get("result.json"))
        require(inputs["selection.json"]==identity(get("selection.json")) and selection==j["selection"] and
                selection["build_uuid"]==release["build_uuid"] and selection["inputs"]["field-operator"]==release["binary"] and
                selection["mesh"]=="regular" and selection["n"]==n and selection["mean"]=="zero",prefix+" selection")
        for k,v in selection["inputs"].items():
            require(inputs[k]["sha256"]==v and (k=="field-operator" or identity(files["source/"+k])==inputs[k]),prefix+" "+k)
        require(j["raw_sha256"]==outputs["observations.npz"]["sha256"],prefix+" raw")
        with np.load(io.BytesIO(get("observations.npz")),allow_pickle=False) as z:
            v=z["volumes"]; d=z["divergences"]
            require(len(v)==n**3 and (v>0).all() and abs(v.sum()-1)<=1e-12 and d.shape==(n**3,3),prefix+" dimensions")
            rms=np.sqrt(np.average(d*d,axis=0,weights=v))
            agree=float(np.max(abs(d[:,1]-z["independent"])))
            l1=float(np.average(np.linalg.norm(z["field"]-z["reference"],axis=1),weights=v)/np.average(np.linalg.norm(z["reference"],axis=1),weights=v))
        require(np.allclose(rms,[j["divergence"][k]["rms"] for k in ("cell_ls","face_mean","face_limited")],atol=1e-12,rtol=1e-12) and
                abs(agree-j["independent_face_difference"])<1e-12 and abs(l1-j["normalized_l1"])<1e-12,prefix+" recomputed norms")
        levels.append(dict(n=n,uuid=uid,rms=rms.tolist(),l1=l1,independent_max=agree,
                           roundoff_scale=128*np.finfo(float).eps*(math.tau*n+n*n)))
    require(len({r["uuid"] for r in levels})==3,"distinct workflows")
    d=np.array([r["rms"] for r in levels])
    passed=bool(np.all(np.diff(d[:,:2],axis=0)<0.) and np.all(d[:,:2]>np.array([r["roundoff_scale"] for r in levels])[:,None]))
    return dict(schema="openmhd.m2c.shared-face-mixed-cube-review.v1",levels=levels,passed=passed,**release)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("packet",type=Path);p.add_argument("output",type=Path)
    args=p.parse_args();args.output.write_text(json.dumps(review(args.packet),indent=2,allow_nan=False)+"\n")
