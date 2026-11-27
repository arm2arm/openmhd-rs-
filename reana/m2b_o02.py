"""Run and measure one periodic O02 resolution, mesh, and prescribed mean."""
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import time
import numpy as np
import scipy
from m2b_periodic_geometry import geometry,compare_oracle

SCALE=2*math.pi
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def analytical(x):
    s=np.sin(2*np.pi*x);c=np.cos(2*np.pi*x)
    a=np.column_stack([s[:,(k+1)%3]*s[:,(k+2)%3] for k in range(3)])
    curl=2*np.pi*np.column_stack([s[:,k]*(c[:,(k+1)%3]-c[:,(k+2)%3]) for k in range(3)])
    return a,curl

def write_input(path,g,a,mean):
    with path.open("xb") as out:
        out.write(struct.pack("<8sII3d",b"M2BO2v01",len(a),len(g["area"]),*mean))
        np.column_stack((g["vol"],g["cell"],a)).astype("<f8").tofile(out)
        fs=np.empty(len(g["area"]),dtype=[("lr","<u4",2),("image","<i4",3),("area","<f8"),("normal","<f8",3),("face","<f8",3)])
        fs["lr"]=np.column_stack((g["left"],g["right"]));fs["image"]=g["image"];fs["area"]=g["area"];fs["normal"]=g["normal"];fs["face"]=g["face"];fs.tofile(out)

def norms(v,vol):
    return dict(signed_mean=float(np.average(v,weights=vol)),l1=float(np.average(np.abs(v),weights=vol)),
                rms=float(np.sqrt(np.average(v*v,weights=vol))),maximum=float(np.max(np.abs(v))))

def main():
    pin=json.loads(Path("selection.json").read_bytes())
    if any(sha(n)!=h for n,h in pin["sha256"].items()):raise ValueError("Frozen case input")
    n=pin["n"];jitter=pin["mesh"]=="jitter";mean=np.array(pin["mean_b"])
    if n not in (8,16,32) or pin["mesh"] not in ("jitter","regular"):raise ValueError("O02 inventory")
    start=time.monotonic();g=geometry(n,jitter)
    oracle=compare_oracle(g,np.load("m2a-jitter8.npz")) if n==8 and jitter else None
    cell,vol=g["cell"],g["vol"];a,fluct=analytical(cell);exact=mean+fluct
    src=Path("metrics.bin");out=Path("outputs.bin")
    write_input(src,g,a,mean);t1=time.monotonic()
    native=Path("operator");native.chmod(0o700)
    p=subprocess.run([str(native.resolve()),str(src),str(out),"2"],capture_output=True,timeout=1650)
    Path("native.stderr").write_bytes(p.stderr);p.check_returncode()
    t2=time.monotonic()
    with out.open("rb") as stream:
        if struct.unpack("<8sI",stream.read(12))!=(b"M2BR2v01",n**3):raise ValueError("Native dimensions")
        profiles={s:np.fromfile(stream,dtype="<f8",count=n**3*w).reshape(n**3,w) for s,w in (("linear",12),("quadratic",13))}
        if stream.read(1):raise ValueError("Trailing native output")
    raw=dict(centroids=cell,volumes=vol,exact=exact,**profiles)
    if not all(np.isfinite(v).all() for v in raw.values()):raise ValueError("Nonfinite output")
    np.savez_compressed("fields.npz",**raw)
    report=dict(schema="openmhd.m2b.o02.v1",selection=pin,dimensions=n,mesh=pin["mesh"],mean=mean.tolist(),
                cells=len(cell),faces=len(g["area"]),numpy=np.__version__,scipy=scipy.__version__,B_scale=SCALE,
                geometry_seconds=t1-start,native_seconds=t2-t1,geometry_input_sha256=sha(src),
                native_output_sha256=sha(out),retained_fields_sha256=sha("fields.npz"),m2a_metric_differences=oracle,profiles={})
    for name,v in profiles.items():
        field=v[:,:3];mag=np.linalg.norm(field,axis=1)
        err=np.linalg.norm(field-exact,axis=1)
        reff=(3*vol/(4*np.pi))**(1/3);weak=int(np.argmin(mag))
        labels=["div_a","cell_ls","face_mean","face_limited"];indices=[3,4,5,6]
        if name=="quadratic":labels+=["same_fit"];indices+=[12]
        divergences={}
        for label,col in zip(labels,indices):
            values=v[:,col]
            s=norms(values,vol)
            if label!="div_a":
                s["cell_scaled_abs"]=norms(reff*abs(values)/(mag+1e-12*SCALE),vol)
            divergences[label]=s
        report["profiles"][name]=dict(curl_l1=float(np.average(err,weights=vol)),
              normalized_curl_l1=float(np.average(err,weights=vol)/np.average(np.linalg.norm(fluct,axis=1),weights=vol)),
              curl_l1_over_fixed_scale=float(np.average(err,weights=vol)/SCALE),mean_error=(np.average(field,weights=vol,axis=0)-mean).tolist(),
              weakest_field=dict(cell=weak,coordinates=cell[weak].tolist(),magnitude=float(mag[weak])),
              divergences=divergences,normalized_signed_face_sum=float(abs(np.dot(vol,v[:,5]))/SCALE),
              max_condition=float(v[:,7].max()),minimum_certified_pivot_ratio=float(v[:,8].min()),
              sample_range=[int(v[:,9].min()),int(v[:,9].max())],ring_range=[int(v[:,10].min()),int(v[:,10].max())])
    Path("metrics.json").write_text(json.dumps(report,allow_nan=False,indent=2)+"\n")

if __name__=="__main__":main()
