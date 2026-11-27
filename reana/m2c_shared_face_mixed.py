"""Regular-cube unequal-wave diagnostic for the shared-face magnetic field."""
import json
import math
from pathlib import Path

import numpy as np
from m2b_o02 import face_divergence, norms
from m2b_periodic_geometry import cartesian
from m2c_shared_face_map import native, sha
from m2c_shared_face_spatial import encode_fields, positions, volume_reference


def main():
    selection=json.loads(Path("selection.json").read_bytes())
    n=selection["n"]
    if n not in (8,16,32) or selection["mean"]!="zero":
        raise ValueError("unregistered cube")
    mesh=cartesian(n,positions(n,"regular"))
    covariance,_,_,_=volume_reference(mesh,n,"regular")
    x,y,_=mesh["cell"].T
    sx,cx=np.sin(math.tau*x),np.cos(math.tau*x)
    sy,cy=np.sin(2*math.tau*y),np.cos(2*math.tau*y)
    a=np.zeros_like(mesh["cell"]);a[:,2]=sx*sy
    exact=np.column_stack((2*math.tau*sx*cy,-math.tau*cx*sy,np.zeros_like(x)))*np.sinc(1/n)*np.sinc(2/n)
    reader=native(selection,encode_fields(mesh,a,np.zeros(3),covariance))
    if reader.count()!=n**3:raise ValueError("owner count")
    rows=reader.array(6*n**3).reshape(-1,6)
    if reader.reader.read(1) or not np.isfinite(rows).all():raise ValueError("invalid field")
    vol=mesh["vol"]
    reconstructed=face_divergence(mesh,rows[:,:3])
    agreement=float(np.max(abs(reconstructed-rows[:,4])))
    if agreement>1024*np.finfo(float).eps*n*2*math.tau:raise ValueError("independent face flux discrepancy")
    np.savez_compressed("observations.npz",volumes=vol,field=rows[:,:3],reference=exact,divergences=rows[:,3:],independent=reconstructed)
    report=dict(schema="openmhd.m2c.shared-face-mixed-cube.v1",selection=selection,
                divergence={k:norms(rows[:,j],vol) for j,k in enumerate(("cell_ls","face_mean","face_limited"),3)},
                normalized_l1=float(np.average(np.linalg.norm(rows[:,:3]-exact,axis=1),weights=vol)/np.average(np.linalg.norm(exact,axis=1),weights=vol)),
                independent_face_difference=agreement,input_sha256=sha("input.bin"),native_sha256=sha("native.bin"),
                raw_sha256=sha("observations.npz"))
    Path("result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")


if __name__=="__main__":
    main()
