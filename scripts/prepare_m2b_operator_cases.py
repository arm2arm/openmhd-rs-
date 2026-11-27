"""Stage the independent Rust comparisons for a static M2b operator gate."""
import argparse
import hashlib
import json
from pathlib import Path
from uuid import UUID
from prepare_general_geometry_jobs import ROOT, stage, write_json

def encoded(value):
    return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()

def digest(blob):
    return hashlib.sha256(blob).hexdigest()

def prepare(args):
    if args.phase!="O01":
        if args.o01_gate is None:raise ValueError("A measured O01 gate is required")
        o01=json.loads(args.o01_gate.read_bytes())
        if o01.get("gate")!="O01" or o01.get("passed") is not True or o01.get("reproduced")!=84 or o01.get("rejected_deficient")!=3:
            raise ValueError("A complete O01 output comparison is required")
    parent=json.loads(args.build.read_bytes())
    if not parent["commands"] or any(r["returncode"]!=0 for r in parent["commands"]):
        raise ValueError("Successful compile preflight required")
    name={"O01":"m2b-o01","O02":"m2b-o02","O03":"m2b_operators"}[args.phase]
    binary=(args.build.parent/name).read_bytes()
    if digest(binary)!=parent["binaries"][name]["sha256"] or not binary.startswith(b"\x7fELF"):
        raise ValueError("Actual executable pin")
    uuid=str(UUID(args.build_uuid)); rev=parent["source_revision"]
    catalog={}
    common=dict(rust_revision=rev,build_uuid=uuid,build_sha256=digest(args.build.read_bytes()))
    if args.phase!="O01":common["o01_gate_sha256"]=digest(args.o01_gate.read_bytes())
    args.destination.mkdir()
    if args.phase=="O01":
        if args.references is None:raise ValueError("Original REANA references directory required")
        from geometry3_operator_fixtures import catalog as selections
        # Only enumerate names here. The analytic fixtures come from measured workflows.
        runner=(ROOT/"reana/m2b_o01.py").read_bytes()
        for case in selections():
            folder=args.references/case;ref=json.loads((folder/"result.json").read_bytes())
            data=(folder/"outputs/fixture.json").read_bytes()
            if digest(data)!=ref["outputs"]["fixture.json"]["sha256"] or json.loads(data)["name"]!=case:
                raise ValueError("Original reference bytes for "+case)
            pin=dict(case=case,revision=rev,build_uuid=uuid,reference_uuid=str(UUID(ref["uuid"])),
                     sha256={"fixture.json":digest(data),"operator":digest(binary)})
            files={"runner.py":runner,"fixture.json":data,"operator":binary,"selection.json":encoded(pin)}
            catalog[case]=stage(args.destination/case,files,"runner.py",["comparison.json","native.stdout","native.stderr"],
                                1,"2Gi",300,"manufactured-curl",output_prefix="")
    elif args.phase=="O02":
        if args.oracle is None or args.oracle_provenance is None:raise ValueError("M2a jitter8 metrics and origin required")
        witness=json.loads(args.oracle_provenance.read_bytes()); keep=args.oracle.read_bytes()
        original=json.loads((ROOT/"docs/galaxy/results/m2a_general_20261125/repaired-base-results.json").read_bytes())
        ref=next(r["native"] for r in original["cases"] if r["name"]=="jitter8__base__t1")
        if witness["native"]!=ref or witness["extracted_npz"]!=digest(keep):raise ValueError("Accepted original G02 output identity")
        base={"operator":binary,"m2b_o02.py":(ROOT/"reana/m2b_o02.py").read_bytes(),
              "m2b_periodic_geometry.py":(ROOT/"reana/m2b_periodic_geometry.py").read_bytes()}
        if args.metric_qualification is None:raise ValueError("Prior jitter8 cross-check required")
        mq=json.loads(args.metric_qualification.read_bytes())
        measured=mq["checks"]
        if (measured["cells"]!=512 or measured["faces"]!=4063 or measured["reference"]!=witness
                or measured["geometry_source_sha256"]!=digest(base["m2b_periodic_geometry.py"])
                or set(measured["max_errors"])!={"vol","cell","area","normal","face"}
                or not all(0.<=v<=1e-9 for v in measured["max_errors"].values())):
            raise ValueError("Independent small-mesh cross-check")
        common["metric_preflight_uuid"]=str(UUID(mq["result"]["uuid"]))
        for mesh in ("regular","jitter"):
            for n in (8,16,32):
                for mean_id,mean in (("zero",[0.,0.,0.]),("imposed",[.3,-.2,.4])):
                    case=f"{mesh}-{n}-{mean_id}";files=dict(base)
                    if n==8 and mesh=="jitter":files["m2a-jitter8.npz"]=keep
                    pin=dict(common,case=case,n=n,mesh=mesh,mean_b=mean,oracle_uuid=ref["uuid"],sha256={k:digest(v) for k,v in files.items()})
                    files["selection.json"]=encoded(pin)
                    catalog[case]=stage(args.destination/case,files,"m2b_o02.py",["metrics.json","fields.npz","native.stderr"],2,"8Gi",1800,"fourier-point-curl",output_prefix="")
    else:
        catalog_names=[]
        for row in parent["test_listing"]:
            if not row.endswith(": test"):raise ValueError("Unexpected discovery line")
            catalog_names.append(row[:-6])
        if len(catalog_names)!=len(set(catalog_names)) or not catalog_names:raise ValueError("Empty or duplicate test selection")
        runner=(ROOT/"reana/m2b_o03.py").read_bytes()
        for case in catalog_names:
            pin=dict(common,selector=case,catalog_size=len(catalog_names),binary_sha256=digest(binary))
            catalog[case]=stage(args.destination/case,{"operator":binary,"selection.json":encoded(pin),"m2b_o03.py":runner},
                                "m2b_o03.py",["comparison.json","native.stdout","native.stderr"],1,"2Gi",300,"tricubic-and-curl",output_prefix="")
    write_json(args.destination/"plan.json",dict(gate=args.phase,build_uuid=uuid,source_revision=rev,jobs=catalog))

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("O01","O02","O03"))
    parser.add_argument("destination",type=Path)
    parser.add_argument("--build",type=Path,required=True)
    parser.add_argument("--build-uuid",required=True)
    parser.add_argument("--o01-gate",type=Path)
    parser.add_argument("--references",type=Path)
    parser.add_argument("--oracle",type=Path)
    parser.add_argument("--oracle-provenance",type=Path)
    parser.add_argument("--metric-qualification",type=Path)
    prepare(parser.parse_args())
