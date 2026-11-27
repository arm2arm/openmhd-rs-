"""Measure cubic Fourier nulls, non-null controls and the independent detection floor."""
import json
import math
from pathlib import Path

import numpy as np
from m2b_o02 import analytical, face_divergence
from m2b_periodic_geometry import cartesian
from m2c_shared_face_map import native, sha
from m2c_shared_face_spatial import encode_fields, positions, volume_reference

RULE="m2c-shared-face-cubic-divergence-v2"


def potential_and_reference(centers,n,family):
    if family in ("equal","shifted"):
        x=centers if family=="equal" else centers+np.array([1/11,2/13,3/17])
        a,b=analytical(x)
        return a,b*np.sinc(1/n)**2
    if family!="mixed":
        raise ValueError("unregistered field")
    x,y,_=centers.T
    sx,cx=np.sin(math.tau*x),np.cos(math.tau*x)
    sy,cy=np.sin(2*math.tau*y),np.cos(2*math.tau*y)
    a=np.zeros_like(centers)
    a[:,2]=sx*sy
    b=np.column_stack((2*math.tau*sx*cy,-math.tau*cx*sy,np.zeros_like(x)))
    return a,b*np.sinc(1/n)*np.sinc(2/n)


def centered_divergence(field,n):
    grid=field.reshape((n,n,n,3))
    trace=np.zeros((n,n,n))
    for axis in range(3):
        component=grid[...,axis]
        trace+=(n/2)*(np.roll(component,-1,axis)-np.roll(component,1,axis))
    return trace.ravel()


def main():
    p=json.loads(Path("selection.json").read_bytes())
    n=p["n"];family=p["mesh"]
    if n not in (8,16,32) or p["rule"]!=RULE:
        raise ValueError("unregistered selection")
    background=np.array({"zero":[0.,0.,0.],"mean":[.3,-.2,.4]}[p["mean"]])
    g=cartesian(n,positions(n,"regular"))
    covariance=volume_reference(g,n,"regular")[0]
    a,exact=potential_and_reference(g["cell"],n,family)
    stream=native(p,encode_fields(g,a,background,covariance))
    if stream.count()!=n**3:raise ValueError("owner count")
    rows=stream.array(6*n**3).reshape(-1,6)
    if stream.reader.read(1) or not np.isfinite(rows).all():raise ValueError("invalid native field")
    field=rows[:,:3]; div=rows[:,3:]
    direct=centered_divergence(field,n)
    face=face_divergence(g,field)
    probe=field.copy()
    probe[:,0]+=2.**-30*np.sin(math.tau*g["cell"][:,0])
    injected=centered_divergence(probe,n)
    vol=g["vol"]
    rms=np.sqrt(np.average(div*div,weights=vol,axis=0))
    bound=128*np.finfo(float).eps*((math.tau+np.linalg.norm(background))*n+n*n)
    delta=[math.fsum(float(v*x) for v,x in zip(vol,col))/math.fsum(vol)-b for col,b in zip(field.T,background)]
    l1=np.average(np.linalg.norm(field-(exact+background),axis=1),weights=vol)/np.average(np.linalg.norm(exact,axis=1),weights=vol)
    np.savez_compressed("observations.npz",centers=g["cell"],volumes=vol,reference=exact+background,
                        field=field,divergences=div,centered=direct,arithmetic=face,injected_centered=injected)
    report=dict(rule=RULE,selection=p,normalized_l1=float(l1),rms=rms.tolist(),
                budget=float(bound),scaled_mean=max(abs(x) for x in delta)/math.tau,
                scaled_face_sum=abs(math.fsum(float(v*x) for v,x in zip(vol,div[:,1]))/math.fsum(vol))/math.tau,
                independent_max=[float(np.max(abs(direct-div[:,0]))),float(np.max(abs(face-div[:,1])))],
                perturbed_rms=float(np.sqrt(np.average(injected*injected,weights=vol))),
                input_sha256=sha("input.bin"),native_sha256=sha("native.bin"),raw_sha256=sha("observations.npz"))
    Path("result.json").write_text(json.dumps(report,allow_nan=False,indent=2)+"\n")


if __name__=="__main__":
    main()
