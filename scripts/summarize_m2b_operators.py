"""Independently reduce downloaded M2b outputs. No candidate code is invoked."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np


def read(p):
    return json.loads(p.read_bytes())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def close(x,y):
    if not math.isclose(x,y,rel_tol=5e-12,abs_tol=5e-14):
        raise ValueError(f"Independent reduction differs: {x!r}, {y!r}")


def actual_outputs(directory):
    seen=set()
    for name,receipt in read(directory/"results.json").items():
        if 'failed' in receipt:raise ValueError("Unsuccessful original "+name)
        root=directory/"workflow"/name/"outputs"
        for k,v in receipt["outputs"].items():
            if sha(root/k)!=v["sha256"]:raise ValueError("Changed downloaded "+str(root/k))
        if receipt["uuid"] in seen:raise ValueError("Repeated workflow identity")
        seen.add(receipt["uuid"])
        yield root,receipt


def fourier(root,receipt):
    meta=read(root/"metrics.json"); n=meta["dimensions"]
    mesh=meta["mesh"];mean=meta["mean"];pin=meta["selection"]
    if n!=pin["n"] or mean!=pin["mean_b"] or mesh!=pin["mesh"] or meta['cells']!=n**3 or sha(root/"fields.npz")!=meta["retained_fields_sha256"]:
        raise ValueError("Fourier packet linkage")
    checks={}
    with np.load(root/"fields.npz",allow_pickle=False) as data:
        v=data["volumes"];cell=data["centroids"];exact=data["exact"]
        if len(v)!=n**3 or np.any(v<=0) or cell.shape!=(n**3,3):raise ValueError("Original volume and position inventory")
        close(float(sum(v)),1.)
        # Independent component-by-component analytic reconstruction.
        phase=cell*math.tau
        target=np.empty_like(cell)
        for a in range(3):
            b,c=(a+1)%3,(a+2)%3
            target[:,a]=mean[a]+math.tau*np.sin(phase[:,a])*(np.cos(phase[:,b])-np.cos(phase[:,c]))
        close(float(np.max(np.abs(target-exact))),0.)
        reference_rms=float(np.sqrt(np.average(data["div_face_from_exact"]**2,weights=v)))
        close(reference_rms,meta["exact_field_face_mean"]["rms"])
        wave_scale=np.average(np.sqrt(np.sum((target-mean)**2,axis=1)),weights=v)
        for key,width in (("linear",12),("quadratic",13)):
            a=data[key]
            if a.shape!=(len(v),width) or not np.isfinite(a).all():raise ValueError("Native finite fields and measures")
            b=a[:,:3];l1=float(np.average(np.sqrt(np.sum((b-target)**2,axis=1)),weights=v))
            local=l1/wave_scale;g=meta["profiles"][key];close(l1,g["curl_l1"]);close(local,g["normalized_curl_l1"])
            divergence={}
            for label,i in [('div_a',3),('cell_ls',4),('face_mean',5),('face_limited',6)]+([('same_fit',12)] if key=='quadratic' else []):
                x=a[:,i];stats=dict(signed_mean=float(np.average(x,weights=v)),l1=float(np.average(abs(x),weights=v)),
                                    rms=float(np.sqrt(np.average(x*x,weights=v))),maximum=float(abs(x).max()))
                for k,val in stats.items():close(val,g["divergences"][label][k])
                if label!='div_a':
                    z=np.cbrt(3*v/(4*math.pi))*abs(x)/(np.sqrt(np.sum(b*b,axis=1))+1e-12*math.tau)
                    close(float(np.sqrt(np.average(z*z,weights=v))),g["divergences"][label]["cell_scaled_abs"]["rms"])
                    stats["locally_scaled_rms"]=g["divergences"][label]["cell_scaled_abs"]["rms"]
                divergence[label]=stats
            signed=abs(divergence['face_mean']['signed_mean'])/math.tau
            close(signed,g["normalized_signed_face_sum"])
            mean_error=(np.average(b,weights=v,axis=0)-mean).tolist()
            for m,old in zip(mean_error,g["mean_error"]):close(m,old)
            checks[key]=dict(normalized_curl_l1=float(local),curl_l1=l1,divergences=divergence,
                             mean_error=mean_error,signed_face_sum=signed,max_condition=g["max_condition"],
                             sample_range=g["sample_range"],ring_range=g["ring_range"])
    return dict(case=pin["case"],mesh=mesh,n=n,mean_b=mean,uuid=receipt["uuid"],workflow=receipt["workflow"],
                source_revision=pin["rust_revision"],build_uuid=pin["build_uuid"],report_sha256=sha(root/"metrics.json"),
                fields_sha256=sha(root/"fields.npz"),cell_count=n**3,faces=meta["faces"],profiles=checks,
                m2a_metric_differences=meta["m2a_metric_differences"],exact_field_face_mean_rms=reference_rms)


def summarize(o01_path,o02_path,o03_path):
    o01=read(o01_path); rows=[fourier(r,rec) for r,rec in actual_outputs(o02_path)]
    if o01["passed"] is not True or len(o01["cases"])!=87:raise ValueError("Missing O01 evidence")
    by_key={(r["mesh"],r["n"],tuple(r["mean_b"])):r for r in rows}
    if len(rows)!=12 or len(by_key)!=12:raise ValueError("Expected all 12 Fourier runs")
    ladders=[]
    for mesh in ("regular","jitter"):
        for mean in ((0.,0.,0.),(.3,-.2,.4)):
            cases=[by_key[mesh,n,mean] for n in (8,16,32)]
            for p in ("linear","quadratic"):
                values=[r["profiles"][p] for r in cases]; errs=[r["normalized_curl_l1"] for r in values]
                orders=[math.log(a/b,2) for a,b in zip(errs,errs[1:])]
                order=math.log(errs[0]/errs[2])/math.log(4.)
                rms=[r["divergences"]["face_mean"]["rms"] for r in values]
                gates=dict(face_mean_rms_decreases=all(a>b for a,b in zip(rms,rms[1:])),
                           global_signed_face_sum=max(r["signed_face_sum"] for r in values)<=1e-12)
                if p=="quadratic":gates.update(curl_order=order>=1.8,finest_normalized_l1=errs[-1]<=.1)
                ladders.append(dict(mesh=mesh,mean_b=mean,fit=p,normalized_l1=errs,pair_orders=orders,order=order,
                                    face_mean_rms=rms,gates=gates,passed=all(gates.values())))
    aux=[]
    for r,rec in actual_outputs(o03_path):
        m=read(r/"comparison.json");key=m["selection"]["selector"]
        if m["passed"] is not True or m["returncode"]!=0 or m["stdout_sha256"]!=sha(r/"native.stdout") or m["stderr_sha256"]!=sha(r/"native.stderr"):
            raise ValueError("O03 selector "+key)
        aux.append(dict(selector=key,uuid=rec["uuid"],workflow=rec["workflow"],metrics=m["metrics"],stdout_sha256=m["stdout_sha256"],result_sha256=sha(r/"comparison.json")))
    expected={f"tricubic_{i}{j}{k}" for i in range(4) for j in range(4) for k in range(4)}
    expected|={f"tricubic_all_faces_and_seams_{a}" for a in "xyz"}
    expected|={"linear_curl_transpose","quadratic_curl_transpose","linear_gauge_constant","quadratic_gauge_constant",
               "deposition_aliases_and_empty_root","one_root_volume_weighted_mean","deposition_order_and_translated_origin"}
    if len(aux)!=len(expected) or {x["selector"] for x in aux}!=expected:raise ValueError("Incomplete O03 matrix")
    return dict(schema="openmhd.static-3d-operators.summary.v1",o01_gate_sha256=sha(o01_path),
                o01=dict(passed=True,reproduced=o01["reproduced"],rejected_deficient=o01["rejected_deficient"],maximum_absolute_errors=o01["maximum_absolute_errors"]),
                o02=dict(passed=all(r["passed"] for r in ladders),ladders=ladders,cases=sorted(rows,key=lambda r:r["case"])),
                o03=dict(passed=True,cases=sorted(aux,key=lambda r:r["selector"])),all_registered_gates_passed=all(r["passed"] for r in ladders))

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("o01_gate",type=Path);p.add_argument("o02",type=Path);p.add_argument("o03",type=Path);p.add_argument("output",type=Path)
    a=p.parse_args();summary=summarize(a.o01_gate,a.o02,a.o03)
    a.output.write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print("All registered gates passed:",summary["all_registered_gates_passed"])
