"""Apply the separately registered cubic rule and replay unchanged irregular ladders."""
import argparse
import io
import json
import math
from pathlib import Path

import numpy as np
from review_m2c_centroid import identity, read_packet, receipt, require
from review_m2c_shared_face import review as original_review
from review_m2c_shared_face_mixed import review as original_mixed

RULE="m2c-shared-face-cubic-divergence-v2"
FAMILIES=("equal","shifted","mixed")
MEANS=("zero","mean")
LEVELS=(8,16,32)


def measure(data, family, mean, n):
    with np.load(io.BytesIO(data),allow_pickle=False) as z:
        c=z["centers"];vol=z["volumes"];b=z["field"];reference=z["reference"];div=z["divergences"]
        require(b.shape==div.shape==reference.shape==c.shape==(n**3,3) and
                np.array_equal(c,(np.indices((n,n,n)).reshape(3,-1).T+.5)/n) and np.all(vol==1/n**3),"cubic geometry")
        bg=np.array([0.,0.,0.] if mean=="zero" else [.3,-.2,.4])
        k=math.tau
        if family=="mixed":
            x,y,_=c.T
            exact=np.column_stack((2*k*np.sin(k*x)*np.cos(2*k*y),-k*np.cos(k*x)*np.sin(2*k*y),np.zeros_like(x)))*np.sinc(1/n)*np.sinc(2/n)
        else:
            phase=np.array([1/11,2/13,3/17]) if family=="shifted" else np.zeros(3)
            sine=np.sin(k*(c+phase));cosine=np.cos(k*(c+phase))
            exact=k*sine*(np.roll(cosine,-1,axis=1)-np.roll(cosine,-2,axis=1))*np.sinc(1/n)**2
        require(np.allclose(exact+bg,reference,atol=2e-13,rtol=1e-13),"analytic cell averages")
        grid=b.reshape(n,n,n,3)
        trace=np.zeros((n,n,n))
        for axis in range(3):
            v=grid[...,axis]
            trace+=n*.5*(np.roll(v,-1,axis)-np.roll(v,1,axis))
        trace=trace.ravel()
        q=2.**-30*np.sin(k*c[:,0]).reshape(n,n,n)
        # Adding the perturbation to stored B rounds once before differencing.
        # Compute its face response from the two perturbed neighbouring values.
        bx=grid[...,0];changed=(bx+q)-bx
        response=n*.5*(np.roll(changed,-1,axis=0)-np.roll(changed,1,axis=0))
        injected=trace+response.ravel()
        bound=float(128*np.finfo(float).eps*((k+math.sqrt(sum(x*x for x in bg)))*n+n*n))
        within=lambda x,y:np.max(abs(x-y))<=bound
        require(within(trace,z["centered"]) and within(trace,z["arithmetic"]) and within(injected,z["injected_centered"]),"independent cubic measurements")
        rms=np.sqrt(np.average(div*div,axis=0,weights=vol))
        delta=[math.fsum(float(v*x) for v,x in zip(vol,col))/math.fsum(vol)-b0 for col,b0 in zip(b.T,bg)]
        l1=np.average(np.linalg.norm(b-reference,axis=1),weights=vol)/np.average(np.linalg.norm(reference-bg,axis=1),weights=vol)
        independent=[float(np.max(abs(z["centered"]-div[:,0]))),float(np.max(abs(z["arithmetic"]-div[:,1])))]
        injected_rms=float(np.sqrt(np.average(z["injected_centered"]**2,weights=vol)))
        require(within(trace,div[:,0]) and within(trace,div[:,1]),"native cell-fit and arithmetic-face rows")
        return dict(n=n,budget=bound,rms=rms.tolist(),normalized_l1=float(l1),scaled_mean=max(abs(x) for x in delta)/k,
                    scaled_face_sum=abs(math.fsum(float(v*x) for v,x in zip(vol,div[:,1]))/math.fsum(vol))/k,
                    independent_max=independent,perturbed_rms=injected_rms)


def review(prior,packet):
    old=original_review(prior);positive=original_mixed(prior/"mixed-cube.tar.gz")
    original_files=read_packet(prior/"regular.tar.gz")
    positive_files=read_packet(prior/"mixed-cube.tar.gz")
    require(not old["divergence_decreased_on_all"] and old["spatial_mean_passed"] and old["spatial_field_passed"] and positive["passed"],"original verdicts")
    files=read_packet(packet);release=json.loads(files["release.json"])
    tags={f"{fam}-{n}-{mean}" for fam in FAMILIES for n in LEVELS for mean in MEANS}
    require(set(release["names"])==tags and release["build_uuid"]==old["build_uuid"] and
            release["binary"]==positive["binary"] and release["rule"]==RULE and
            identity((prior/"manifest.json").read_bytes())==release["original_manifest"],"plan and original released build")
    values={};ids=set();overlaps=0
    for tag in sorted(tags):
        family,nstr,mean=tag.split("-");n=int(nstr);prefix="cases/"+tag
        case,inputs,outputs,spec=receipt(files,prefix,release["names"][tag])
        ids.add(case);get=lambda name:files[prefix+"/"+name]
        for name,pin in outputs.items(): require(identity(get(name))==pin,tag+" "+name)
        p=json.loads(get("selection.json"));j=json.loads(get("result.json"))
        require(p==j["selection"] and j["rule"]==p["rule"]==RULE and p["source_revision"]==old["source_revision"] and p["build_uuid"]==old["build_uuid"]
                and p["reference_revision"]==release["measurement_revision"] and identity(get("selection.json"))==inputs["selection.json"] and
                (p["mesh"],p["mean"],p["n"])==(family,mean,n),"identity "+tag)
        require(p["inputs"]["field-operator"]==inputs["field-operator"]["sha256"]==release["binary"] and j["raw_sha256"]==outputs["observations.npz"]["sha256"],tag+" native output")
        for name,digest in p["inputs"].items():
            require(inputs[name]["sha256"]==digest and (name=="field-operator" or identity(files["source/"+name])==inputs[name]),tag+" input")
        step,=spec["workflow"]["specification"]["steps"]
        require(step["kubernetes_cpu_limit"]=="2" and step["kubernetes_memory_limit"]=="8Gi",tag+" declared resources")
        row=measure(get("observations.npz"),family,mean,n)
        for k,v in row.items():
            if k!="n":require(np.allclose(j[k],v,rtol=1e-12,atol=1e-14),tag+" "+k)
        row["uuid"]=case
        origin=None
        if family=="equal":origin=json.loads(original_files[f"cases/space/regular-{n}-{mean}/result.json"])
        if family=="mixed" and mean=="zero":origin=json.loads(positive_files[f"{n}/result.json"])
        if origin is not None:
            require(all(j[k]==origin[k] for k in ("input_sha256","native_sha256")),tag+" original native input/output words")
            overlaps+=1
        values[family,mean,n]=row
    require(len(ids)==18 and overlaps==9,"fresh unique workflows and original overlaps")
    ladders=[]
    for family in FAMILIES:
        for mean in MEANS:
            rows=[values[family,mean,n] for n in LEVELS]
            rms=np.array([r["rms"] for r in rows]);budget=np.array([r["budget"] for r in rows])
            ratios=rms[:,:2]/budget[:,None]
            strict=np.all(np.diff(rms,axis=0)<0,axis=0)
            order=math.log2(rows[0]["normalized_l1"]/rows[-1]["normalized_l1"])/2
            if family=="mixed":
                field_gate=True
                divergence_gate=bool(np.all(rms>budget[:,None]) and np.all(strict))
            else:
                field_gate=order>=1.8 and rows[-1]["normalized_l1"]<=.1
                divergence_gate=bool(np.all(ratios<=1) and strict[2] and all(r["perturbed_rms"]>r["budget"] for r in rows))
            passed=all(r["scaled_mean"]<=1e-9 and r["scaled_face_sum"]<=1e-12 and max(r["independent_max"])<=r["budget"] for r in rows)
            ladders.append(dict(field=family,background=mean,levels=rows,max_null_budget_fraction=float(np.max(ratios)) if family!="mixed" else None,
                                strict_decreases=strict.tolist(),spatial_order=order,passed=bool(passed and field_gate and divergence_gate)))
    irregular=[r for r in old["spatial_ladders"] if r["mesh"]!="regular"]
    require(len(irregular)==12 and all(r["mean_passed"] and r["field_passed"] and all(r["rms_decreases"]) for r in irregular),"strict original irregular ladders")
    return dict(rule=RULE,scientific_scope="periodic adjacency-stencil Fourier divergence",
                original_strict_decrease_passed=old["divergence_decreased_on_all"],rechecked_irregular_ladders=len(irregular),
                original_irregular_workflows=[v["uuid"] for r in irregular for v in r["levels"]],
                new_workflows=len(ids),original_native_results_reproduced=overlaps,build_uuid=old["build_uuid"],
                protocol_sha256=identity(files["source/protocol.md"])["sha256"],ladders=ladders,passed=all(r["passed"] for r in ladders))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("prior",type=Path);p.add_argument("packet",type=Path);p.add_argument("output",type=Path)
    args=p.parse_args();args.output.write_text(json.dumps(review(args.prior,args.packet),indent=2,allow_nan=False)+"\n")
