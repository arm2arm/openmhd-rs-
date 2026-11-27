"""Independent dense CF-MAP/MEAN reference on the native clipped polygons."""
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import subprocess

import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Stream:
    def __init__(self, path):
        self.reader = io.BytesIO(Path(path).read_bytes())

    def array(self, number, kind="<f8"):
        size = np.dtype(kind).itemsize * number
        values = self.reader.read(size)
        if len(values) != size:
            raise ValueError("truncated native output")
        return np.frombuffer(values, dtype=kind)

    def count(self):
        return int(self.array(1, "<u8")[0])

    def label(self):
        return self.reader.read(self.count()).decode()


def native(selection, data):
    for name, pin in selection["inputs"].items():
        if sha(name) != pin:
            raise ValueError("changed input "+name)
    Path("input.bin").write_bytes(data)
    exe = Path("field-operator")
    exe.chmod(0o700)
    run = subprocess.run([str(exe.resolve()), "input.bin", "native.bin", str(selection["threads"])],
                         capture_output=True, timeout=1690)
    Path("native.stderr").write_bytes(run.stderr)
    run.check_returncode()
    reader = Stream("native.bin")
    if (reader.label(),reader.label()) != ("periodic-shared-face-quadratic-curl-v1","a-point-b-cell-average-v1"):
        raise ValueError("unexpected sampling")
    return reader


def basis(x):
    a,b,c=x.T
    return np.column_stack((np.ones(len(x)),a,b,c,a*a/2,b*b/2,c*c/2,a*b,a*c,b*c))


def main():
    selection = json.loads(Path("selection.json").read_bytes())
    fixture = json.loads(Path("fixture.json").read_bytes())["generators"][selection["mesh"]]
    sites = np.array([[float.fromhex(t) for t in row] for row in fixture])
    n=len(sites)
    ids=np.arange(n)
    a=np.column_stack((((13*ids**2+3*ids+7)%31-15)/16,
                       ((5*ids**2+17*ids+3)%37-18)/16,((7*ids**2+11*ids+5)%41-20)/16))
    data=struct.pack("<8sQ",b"M2CFMAP1",n)+sites.astype("<f8").tobytes()+a.astype("<f8").tobytes()
    reader=native(selection,data)
    if reader.count()!=n:
        raise ValueError("wrong number of owners")
    nf=reader.count()
    vols=np.empty(n)
    centers=np.empty((n,3))
    # This is independently weighted SVD on the unnormalized physical
    # quadratic basis, including the fitted intercept and each periodic image.
    maps=[]
    for i in range(n):
        vols[i]=reader.array(1)[0]
        centers[i]=reader.array(3)
        count=reader.count()
        owners=[];d=[];images=[]
        for _ in range(count):
            owners.append(reader.count())
            d.append(reader.array(3))
            images.append(reader.array(3,"<i8"))
        if len(set(zip(owners,map(tuple,images))))!=count:
            raise ValueError("duplicate stencil key")
        d=np.array(d)
        sw=1/np.sqrt(np.linalg.norm(d,axis=1))
        targets=np.eye(n)[owners]
        h,_,rank,_=np.linalg.lstsq(sw[:,None]*basis(d),sw[:,None]*targets,rcond=None)
        if rank!=10:raise ValueError("rank of independent fit")
        maps.append((h,d,owners,images))

    expect=np.zeros((n,3,n,3)); closure=np.zeros((n,3)); surface=np.zeros(n)
    herror=0.; metric_error=0.
    for _ in range(nf):
        l,r=reader.count(),reader.count()
        image=reader.array(3,"<i8")
        area=reader.array(1)[0];normal=reader.array(3)
        verts=reader.array(3*reader.count()).reshape(-1,3)
        observed=reader.array(3)
        x=np.broadcast_to(verts[0],verts[1:-1].shape)
        y=verts[1:-1];z=verts[2:]
        cross=np.cross(y-x,z-x)
        triangle=np.linalg.norm(cross,axis=1)/2
        # Three symmetric barycentric points exactly integrate any quadratic.
        points=np.stack([(4*x+y+z)/6,(x+4*y+z)/6,(x+y+4*z)/6],axis=1)
        independent=cross.sum(axis=0)/2
        metric_error=max(metric_error,float(np.linalg.norm(independent-area*normal)/area))
        weight=np.zeros(n)
        for c,center in ((l,centers[l]),(r,centers[r]+image)):
            phi=basis((points-center).reshape(-1,3)).reshape(len(triangle),3,10).mean(axis=1)
            weight+=0.5*(triangle@phi/triangle.sum())@maps[c][0]
        herror=max(herror,float(np.max(abs(observed-weight@a))),float(abs(weight.sum()-1)))
        sx,sy,sz=independent
        block=np.array([[0.,-sz,sy],[sz,0.,-sx],[-sy,sx,0.]])[:,None,:]*weight[None,:,None]
        if l!=r:
            expect[l]+=block/vols[l];expect[r]-=block/vols[r]
        closure[l]+=independent;closure[r]-=independent;surface[l]+=area;surface[r]+=area
    flat=a.ravel()
    got=reader.array(3*n);trans=reader.array(3*n);diag=reader.array(3*n)
    matrix=reader.array((3*n)**2).reshape(3*n,3*n).T
    if reader.reader.read(1):raise ValueError("trailing output bytes")
    expect=expect.reshape(3*n,3*n)
    vol3=np.repeat(vols,3)
    def error(actual,wanted):
        return float(np.max(abs(actual-wanted))/max(1.,np.max(abs(wanted))))
    modes=np.tile(np.eye(3),(n,1))
    means=(matrix.reshape(n,3,3*n)*vols[:,None,None]).sum(axis=0)
    physical_mean=np.array([.3,-.2,.4])
    actual=got.reshape(n,3)+physical_mean
    delta=np.array([math.fsum(v*x for v,x in zip(vols,actual[:,k]))/math.fsum(vols)-physical_mean[k] for k in range(3)])
    singular=np.linalg.svd(np.sqrt(vol3)[:,None]*matrix,compute_uv=False)
    checks=dict(face_value=herror,polygon_area=metric_error,volume=abs(float(vols.sum()-1)),
                surface_closure=float(np.max(np.linalg.norm(closure,axis=1)/surface)),
                dense=error(matrix,expect), forward=error(got,expect@flat),adjoint=error(trans,expect.T@flat),
                diagonal=error(diag,(vol3[:,None]*expect**2).sum(axis=0)),
                constant=float(np.max(abs(matrix@modes))), all_column_mean=float(np.max(abs(means))))
    np.savez_compressed("observations.npz",candidate=matrix,independent=expect,volumes=vols,
                        field=actual,singular_values=singular,diagonal=diag,transpose=trans)
    result=dict(schema="openmhd.m2c.shared-face-map.v1",selection=selection,owner_count=n,
                face_count=nf,checks=checks,singular_values=singular.tolist(),mean_difference=delta.tolist(),
                max_error=max(checks.values()),passed=bool(max(checks.values())<=1e-12 and max(abs(delta))/math.tau<=1e-9),
                input_sha256=sha("input.bin"),native_sha256=sha("native.bin"),raw_sha256=sha("observations.npz"))
    Path("result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")


if __name__=="__main__":
    main()
