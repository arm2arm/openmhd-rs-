"""Cell-integral Fourier reference and spatial checks for a periodic shared-face curl."""
import json
import math
from pathlib import Path
import struct

import numpy as np
from scipy.spatial import Voronoi

from m2b_o02 import analytical, norms, SCALE
from m2b_periodic_geometry import generators, cartesian, irregular
from m2c_shared_face_map import native, sha

# Each unordered axis pair has a sum and difference wave. Their cell averages
# determine all three components of curl(s_y s_z, s_z s_x, s_x s_y).
PAIRS = ((0,1),(1,2),(2,0))
WAVES = SCALE*np.array([np.eye(3)[i]+sign*np.eye(3)[j] for i,j in PAIRS for sign in (1,-1)])
MASK=(1<<64)-1


def positions(n,family):
    if family=="regular":
        return generators(n,False)
    historic={"original":20261122,"fresh-a":2026112701,"fresh-b":2026112702}
    if family in historic:
        return generators(n,True,historic[family])
    seed={"seed1":1,"seed2":2,"seed3":3}[family]
    points=[]
    for i,j,k in np.ndindex((n,n,n)):
        xyz=[]
        for axis,index in enumerate((i,j,k)):
            c=0x9e3779b97f4a7c15
            z=((seed^i^(j<<21)^(k<<42)^((axis*c)&MASK))+c)&MASK
            z=((z^(z>>30))*0xbf58476d1ce4e5b9)&MASK
            z=((z^(z>>27))*0x94d049bb133111eb)&MASK
            bits=(z^(z>>31))>>11
            xyz.append((index+0.5+0.3*(bits*2.**-53-0.5))/n)
        points.append(xyz)
    return np.asarray(points)


def polygons(n,mesh):
    indices=np.indices((n+4,)*3).reshape(3,-1).T-2
    ids=np.ravel_multi_index(tuple((indices%n).T),(n,n,n))
    shifts=indices//n
    vor=Voronoi(mesh["generators"][ids]+shifts,qhull_options="Qbb Qc Qz")
    u,v=vor.ridge_points.T
    lo=np.where(ids[u]<ids[v],u,v)
    hi=np.where(lo==u,v,u)
    use=np.flatnonzero(np.all(shifts[lo]==0,axis=1))
    keys=np.column_stack((ids[lo[use]],ids[hi[use]],shifts[hi[use]]))
    order=np.lexsort(keys.T[::-1]);use=use[order]
    expected=np.column_stack((mesh["left"],mesh["right"],mesh["image"]))
    if not np.array_equal(keys[order],expected):
        raise ValueError("full face/image keys disagree")
    groups={}
    for index,ridge in enumerate(use):
        vertices=vor.ridge_vertices[ridge]
        if -1 in vertices or len(vertices)<3:raise ValueError("unbounded ridge")
        groups.setdefault(len(vertices),[]).append((index,vertices))
    for group in groups.values():
        for start in range(0,len(group),384):
            sub=group[start:start+384]
            ix=np.array([i for i,_ in sub])
            vert=vor.vertices[np.array([vs for _,vs in sub])]
            center=mesh["face"][ix]
            rel=vert-center[:,None,:]
            normal=mesh["normal"][ix]
            e1=np.cross(normal,np.eye(3)[np.argmin(abs(normal),axis=1)])
            e2=np.cross(normal,e1)
            theta=np.arctan2(np.einsum("fvi,fi->fv",rel,e2),np.einsum("fvi,fi->fv",rel,e1))
            d=np.take_along_axis(rel,np.argsort(theta)[:,:,None],axis=1)
            yield ix,d,np.roll(d,-1,axis=1)


def tet_waves(origin,u,d,e):
    # Four barycentric coordinates of a uniform tetrahedron have Dirichlet
    # moments 6*prod(alpha!)/(sum(alpha)+3)!. Complete homogeneous
    # polynomials give the analytic Taylor integral without point quadrature.
    f=len(origin); nv=d.shape[1]
    vertex=np.stack([np.zeros((f,nv,3)),np.broadcast_to(u[:,None,:],(f,nv,3)),
                     u[:,None,:]+d,u[:,None,:]+e],axis=2)
    projected=vertex@WAVES.T
    center=projected.mean(axis=2)
    a,b,c,v=np.moveaxis(projected-center[:,:,None,:],2,0)
    e1=a+b+c+v
    e2=a*b+a*c+a*v+b*c+b*v+c*v
    e3=a*b*(c+v)+c*v*(a+b)
    e4=a*b*c*v
    prev=[0.,0.,0.,np.ones_like(center)]
    integral=np.ones_like(center,dtype=np.complex128)
    phase=np.exp(1j*(center+(origin@WAVES.T)[:,None,:]))
    estimate12=None
    for degree in range(1,17):
        h=e1*prev[3]-e2*prev[2]+e3*prev[1]-e4*prev[0]
        integral+=(1j**degree*6/math.factorial(degree+3))*h
        prev=[prev[1],prev[2],prev[3],h]
        if degree==12:estimate12=(phase*integral).imag
    radius=np.maximum.reduce([abs(a),abs(b),abs(c),abs(v)])
    return (phase*integral).imag,estimate12,float(np.max(radius)**17/math.factorial(17))


def curl_from_waves(waves):
    result=np.zeros((len(waves),3))
    for p,(i,j) in enumerate(PAIRS):
        plus,minus=waves[:,2*p:2*p+2].T
        result[:,i]+=0.5*SCALE*(plus+minus)
        result[:,j]-=0.5*SCALE*(plus-minus)
    return result


def volume_reference(mesh,n,family):
    nf=len(mesh["area"]); nc=len(mesh["vol"])
    if family=="regular":
        cov=(np.eye(3)[None,:,:]-mesh["normal"][:,:,None]*mesh["normal"][:,None,:])/(12*n*n)
        return cov, analytical(mesh["cell"])[1]*np.sinc(1/n)**2,0.,0.
    cov=np.zeros((nf,3,3)); volume=np.zeros(nc); high=np.zeros((nc,6)); low=high.copy()
    bound=0.
    for ix,d,e in polygons(n,mesh):
        normals=mesh["normal"][ix]
        w=np.einsum("fvi,fi->fv",np.cross(d,e),normals)/2
        area=w.sum(axis=1)
        if np.any(w<=0) or np.max(abs(area/mesh["area"][ix]-1))>2e-9:raise ValueError("ridge area reference")
        for term in (d,e,d+e):
            cov[ix]+=np.einsum("fv,fvi,fvj->fij",w,term,term)/(12*area[:,None,None])
        # Global binary64 Qhull vertices can lose a few ulps when translated
        # to an extremely small face. The physical surface covariance lives
        # in the bisector plane. Repeat its integral in that chart only when
        # the original moments fail the native tangency criterion.
        scale=np.max(abs(cov[ix]),axis=(1,2))
        scaled=cov[ix]/scale[:,None,None]
        leak=scaled[:,:,0]*normals[:,None,0]+scaled[:,:,1]*normals[:,None,1]+scaled[:,:,2]*normals[:,None,2]
        redo=np.max(abs(leak),axis=1)>1e-9
        if np.any(redo):
            plane=normals[redo]
            tangents=[]
            for edge in (d[redo],e[redo]):
                off=np.einsum("fvi,fi->fv",edge,plane)
                # The inputs lie in the primary box and its immediate images.
                if np.max(abs(off))>64*np.finfo(float).eps*3:
                    raise ValueError("polygon leaves its bisector beyond coordinate roundoff")
                tangents.append(edge-off[:,:,None]*plane[:,None,:])
            u,v=tangents
            target=ix[redo]
            cov[target]=0.
            for term in (u,v,u+v):
                cov[target]+=np.einsum("fv,fvi,fvj->fij",w[redo],term,term)/(12*area[redo,None,None])
        for owners,image,sign in [(mesh["left"][ix],0,1),(mesh["right"][ix],mesh["image"][ix],-1)]:
            origin=mesh["generators"][owners]+image
            u=mesh["face"][ix]-origin
            height=sign*np.einsum("fi,fi->f",u,normals)
            if np.any(height<=0):raise ValueError("tetrahedron orientation")
            vol=w*height[:,None]/3
            ha,la,eb=tet_waves(origin,u,d,e)
            np.add.at(volume,owners,vol.sum(axis=1))
            np.add.at(high,owners,np.einsum("fv,fvk->fk",vol,ha))
            np.add.at(low,owners,np.einsum("fv,fvk->fk",vol,la))
            bound=max(bound,eb)
    if np.max(abs(volume/mesh["vol"]-1))>1e-10:raise ValueError("independent cell volumes")
    high=curl_from_waves(high/volume[:,None]);low=curl_from_waves(low/volume[:,None])
    # Each normalized component is a signed sum of four half-amplitude modes.
    return cov,high,2*bound+2e-12,float(np.max(abs(high-low))/SCALE)


def encode_fields(mesh,a,mean,cov):
    n=len(a);nf=len(cov)
    head=struct.pack("<8sQQ3d",b"M2CFFLD1",n,nf,*mean)
    cells=np.column_stack((mesh["vol"],mesh["cell"],a)).astype("<f8").tobytes()
    faces=np.empty(nf,dtype=[("lr","<u8",2),("image","<i4",3),("area","<f8"),("normal","<f8",3),
                            ("face","<f8",3),("cov","<f8",(3,3))])
    faces["lr"]=np.column_stack((mesh["left"],mesh["right"]))
    for key in ("image","area","normal","face"):faces[key]=mesh[key]
    faces["cov"]=cov
    return head+cells+faces.tobytes()


def main():
    p=json.loads(Path("selection.json").read_bytes())
    n=p["n"];fac=p["mesh"]
    if n not in (8,16,32):raise ValueError("resolution")
    pts=positions(n,fac)
    mesh=cartesian(n,pts) if fac=="regular" else irregular(n,pts)
    cov,exact,refbound,refgap=volume_reference(mesh,n,fac)
    mean={"zero":np.zeros(3),"mean":np.array([.3,-.2,.4])}[p["mean"]]
    reader=native(p,encode_fields(mesh,analytical(mesh["cell"])[0],mean,cov))
    if reader.count()!=len(pts):raise ValueError("native row count")
    rows=reader.array(len(pts)*6).reshape(-1,6)
    if reader.reader.read(1) or not np.isfinite(rows).all():raise ValueError("invalid fields")
    vol=mesh["vol"];error=np.linalg.norm(rows[:,:3]-(exact+mean),axis=1)
    rel=float(np.average(error,weights=vol)/np.average(np.linalg.norm(exact,axis=1),weights=vol))
    delta=np.array([math.fsum(v*x for v,x in zip(vol,rows[:,k]))/math.fsum(vol)-mean[k] for k in range(3)])
    div={label:norms(rows[:,k],vol) for k,label in enumerate(("cell_ls","face_mean","face_limited"),3)}
    np.savez_compressed("observations.npz",generators=pts,centroids=mesh["cell"],volumes=vol,
                        reference=exact+mean,field=rows[:,:3],divergences=rows[:,3:])
    j=dict(schema="openmhd.m2c.shared-face-spatial.v1",selection=p,cells=len(pts),faces=len(cov),
           normalized_l1=rel,scaled_mean=float(max(abs(delta))/SCALE),signed_mean_error=delta.tolist(),
           reference_bound=refbound,degree12_difference=refgap,divergence=div,
           passed=bool(refbound<=1e-5 and max(abs(delta))/SCALE<=1e-9 and
                       abs(div["face_mean"]["signed_mean"])/SCALE<=1e-12 and (n<32 or rel<=0.1)),
           input_sha256=sha("input.bin"),native_sha256=sha("native.bin"),raw_sha256=sha("observations.npz"))
    Path("result.json").write_text(json.dumps(j,indent=2,allow_nan=False)+"\n")


if __name__=="__main__":
    main()
