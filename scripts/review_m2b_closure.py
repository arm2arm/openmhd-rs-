"""Independently reduce the M2b closure packet, including all archived per-cell fields."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


FAMILIES = ("regular", "original", "fresh-a", "fresh-b")
ORDERS = ("linear", "quadratic", "corrected")
MEAN = {"zero": (0., 0., 0.), "mean": (.3, -.2, .4)}
CONTROLS = {
    "corrected_linear_recovers_quadratic_potential_on_asymmetric_stencil",
    "shared_skew_face_reproduces_affine_field_across_periodic_chart",
    "linear_curl_transpose", "quadratic_curl_transpose", "linear_gauge_constant", "quadratic_gauge_constant",
}


def load(path):
    return json.loads(path.read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory():
    for family in FAMILIES:
        for n in (8, 16, 32):
            for mean in MEAN:
                yield family, n, mean, "original"
    for n in (8, 16, 32):
        yield "regular", n, "zero", "unequal"


def key(c):
    return f"{c[0]}-{c[1]:02}-{c[2]}-{c[3]}"


def close(a, b):
    if not np.allclose(a,b,rtol=4e-12,atol=2e-14):
        raise ValueError(f"independent reduction differs: {a}, {b}")


def zero_budget(n, mean):
    return 128*np.finfo(float).eps*((math.tau+np.linalg.norm(mean))*n+n*n)


def rms(y, v):
    return float(np.sqrt(np.dot(y*y,v)/v.sum()))


def raw_case(path, c, parent, full):
    row = load(path/"metrics.json")
    receipt, terminal, pin = (load(path/p) for p in ("result.json","terminal.json","selection.json"))
    if (row["schema"]!="openmhd.m2b.closure-case.v2" or row["selection"]!=pin or tuple(pin["case"])!=c
            or pin["parent"]!=parent or terminal["status"]!="finished" or terminal["id"]!=receipt["uuid"]
            or terminal["workflow"]!=receipt["workflow"] or digest(path/"metrics.json")!=receipt["outputs"]["metrics.json"]["sha256"]
            or digest(path/"inputs.json")!=receipt["inputs"] or digest(path/"reana.yaml")!=receipt["spec"]):
        raise ValueError("case or transport identity "+key(c))
    if pin["original_native"] is not None and row["legacy_output_sha256"]!=pin["original_native"]:
        raise ValueError("original field words "+key(c))
    if pin["original_input"] is not None and row["input_sha256"]!=pin["original_input"]:
        raise ValueError("original input words "+key(c))
    if set(row["profiles"])!=set(ORDERS) or row["cells"]!=c[1]**3:
        raise ValueError("fit inventory or cell count")
    required = {"geometry.npz","linear.npz","quadratic.npz","corrected.npz","native.stderr"}
    if set(row["output_sha256"])!=required or set(receipt["outputs"])!=required|{"metrics.json"}:
        raise ValueError("output inventory")
    for name,h in row["output_sha256"].items():
        if receipt["outputs"][name]["sha256"]!=h or (full and (digest(path/name)!=h or (path/name).stat().st_size!=receipt["outputs"][name]["bytes"])):
            raise ValueError("field file identity "+name)
    close(row["cubic_roundoff_budget"],zero_budget(c[1],MEAN[c[2]]))
    if full:
        with np.load(path/"geometry.npz",allow_pickle=False) as g:
            v, exact, points = (g[k] for k in ("volumes","exact","centroids"))
            if v.shape!=(c[1]**3,) or exact.shape!=(len(v),3) or points.shape!=exact.shape or np.any(v<=0):
                raise ValueError("cell geometry")
            close(v.sum(),1.)
            # An independent cosine/sine derivative, with explicit component order.
            sin,cos=np.sin(math.tau*points),np.cos(math.tau*points)
            if c[3]=="original":
                ref=np.column_stack((sin[:,0]*(cos[:,1]-cos[:,2]),sin[:,1]*(cos[:,2]-cos[:,0]),sin[:,2]*(cos[:,0]-cos[:,1])))*math.tau
            else:
                x,y,_=points.T
                ref=np.column_stack((2*math.tau*np.sin(math.tau*x)*np.cos(2*math.tau*y),
                                     -math.tau*np.cos(math.tau*x)*np.sin(2*math.tau*y),np.zeros(len(v))))
            close(exact,ref+MEAN[c[2]])
            close(row["reference_arithmetic"]["rms"],rms(g["reference_mean"],v))
            close(row["reference_skew"]["rms"],rms(g["reference_skew"],v))
        for name in ORDERS:
            with np.load(path/(name+".npz"),allow_pickle=False) as f:
                a=f["rows"]
            if a.shape!=(len(v),{"linear":13,"quadratic":14,"corrected":7}[name]) or not np.isfinite(a).all():
                raise ValueError("finite complete Rust rows")
            index=4 if name=="corrected" else 5
            p=row["profiles"][name]
            close(p["relative_curl_l1"], np.dot(v,np.linalg.norm(a[:,:3]-exact,axis=1))/np.dot(v,np.linalg.norm(ref,axis=1)))
            for label,i in (("arithmetic",index),("skew",-1),("limited",index+1),("cell_ls",index-1)):
                close(p[label]["rms"],rms(a[:,i],v))
                close(p[label]["signed_mean"],np.dot(v,a[:,i])/v.sum())
    return row,receipt["uuid"]


def ladder(family, mean, field, fit, rows):
    p=[r["profiles"][fit] for r in rows]
    error=[r["relative_curl_l1"] for r in p]
    order=math.log2(error[0]/error[-1])/2
    presumed_null=family=="regular" and (field=="original" or fit in ("linear","corrected"))
    checks={}
    if field=="original" and fit!="linear":
        checks.update(curl_order=order>=1.8,finest_curl_error=error[-1]<=.1)
    measurements={}
    for label in ("arithmetic","skew"):
        values=[r[label]["rms"] for r in p]
        measurements[label]=values
        if presumed_null:
            checks[label+"_cubic_budget"]=all(x<=zero_budget(n,MEAN[mean]) for x,n in zip(values,(8,16,32)))
        else:
            checks[label+"_strict_decrease"]=all(a>b for a,b in zip(values,values[1:]))
        checks[label+"_signed_flux"]=all(abs(r[label]["signed_mean"])/math.tau<=1e-12 for r in p)
    return dict(family=family,mean=mean,field=field,fit=fit,curl_relative_l1=error,curl_order=order,
                arithmetic_rms=measurements["arithmetic"],skew_rms=measurements["skew"],
                numerical_checks={k:bool(v) for k,v in checks.items()},passed=all(checks.values()))


def reduce(root, full):
    parent=load(root/"parent.json")
    if set(parent["controls"])!=CONTROLS or parent["original_o01"]["passed"] is not True or parent["original_o03_passed"] is not True:
        raise ValueError("prerequisite inventory")
    expected={key(c) for c in inventory()}
    if {p.name for p in (root/"cases").iterdir() if p.is_dir()}!=expected:
        raise ValueError("incomplete or extra case directories")
    cases={}; ids={}
    for c in inventory():
        row,uid=raw_case(root/"cases"/key(c),c,parent,full)
        cases[c]=row;ids[key(c)]=uid
    if len(set(ids.values()))!=27:
        raise ValueError("duplicated case UUID")
    ladders=[]
    for f,mean,field in sorted({(c[0],c[2],c[3]) for c in cases}):
        rows=[cases[f,n,mean,field] for n in (8,16,32)]
        for name in ORDERS:
            ladders.append(ladder(f,mean,field,name,rows))
    references=[]
    for c,r in cases.items():
        if c[0]!="regular" and c[1]==32 and c[3]=="original":
            ar,sk=r["reference_arithmetic"]["rms"],r["reference_skew"]["rms"]
            references.append(dict(case=key(c),arithmetic=ar,skew=sk,passed=sk<ar))
    required=[row for row in ladders if row["fit"]!="linear"]
    raw_linear=[row for row in ladders if row["fit"]=="linear"]
    # The raw linear model is retained as its own historical/control profile.
    return dict(schema="openmhd.m2b.closure-reduction.v2",case_uuids=ids,prerequisites=parent,ladders=ladders,
                finest_analytic_face_comparisons=references,legacy_registered_o02_passed=False,
                raw_linear_comparator_failed=[r["family"]+"/"+r["mean"]+"/"+r["field"] for r in raw_linear if not r["passed"]],
                revised_comparisons_passed=all(r["passed"] for r in required+references),
                failed_required=[{k:r[k] for k in ("family","mean","field","fit","numerical_checks")} for r in required if not r["passed"]])


def control():
    def measured(x):
        return {"profiles":{"quadratic":{"relative_curl_l1":x,"arithmetic":{"rms":x,"signed_mean":0},
                                        "skew":{"rms":x,"signed_mean":0}}}}
    tiny=[measured(x) for x in (4e-14,5e-14,6e-14)]
    # Isolate the flux decision from the separately enforced curl convergence.
    for i,r in enumerate(tiny):
        r["profiles"]["quadratic"]["relative_curl_l1"]=[.08,.02,.005][i]
    if not ladder("regular","zero","original","quadratic",tiny)["passed"]:
        raise ValueError("analytic-null control rejected")
    for family,field in (("fresh-a","original"),("original","original"),("regular","unequal")):
        if ladder(family,"zero",field,"quadratic",tiny)["passed"]:
            raise ValueError("roundoff exception escaped the registered null family")
    tiny[-1]["profiles"]["quadratic"]["skew"]["rms"]=1e-3
    if ladder("regular","zero","original","quadratic",tiny)["passed"]:
        raise ValueError("large cubic residual passed roundoff limit")
    print("passed closure decision controls")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest="mode",required=True)
    commands.add_parser("control")
    verify=commands.add_parser("verify")
    verify.add_argument("packet",type=Path)
    verify.add_argument("output",type=Path)
    verify.add_argument("--reports-only",action="store_true",help="Check compact reports and workflow provenance; omit per-cell re-reduction.")
    args=parser.parse_args()
    if args.mode=="control":
        control()
    else:
        result=reduce(args.packet,not args.reports_only)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
        print("Revised comparisons passed:",result["revised_comparisons_passed"])
        raise SystemExit(0 if result["revised_comparisons_passed"] else 1)
