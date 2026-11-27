"""Periodic O02 benchmark metrics, independently constructed with SciPy/Qhull.
Cell indices are the row-major (ix, iy, iz) generator indices. Every interior
ridge is retained once in its lower owner's chart; no Qhull joggle is used.
"""
from fractions import Fraction
from itertools import product
import hashlib
import numpy as np
from scipy.spatial import Voronoi


def generators(n, jitter, seed=20261122):
    if not jitter:
        return (np.indices((n,n,n)).reshape(3,-1).T + 0.5) / n
    points=[]
    for index in product(range(n), repeat=3):
        p=[]
        for a,i in enumerate(index):
            key=f"openmhd-m2a-jitter-sha256-v1/{seed}/"+"/".join(map(str,(n,*index,a)))
            word=int.from_bytes(hashlib.sha256(key.encode("ascii")).digest()[:8],"big")
            p.append(float((Fraction(2*i+1,2)+Fraction(3,20)*(Fraction(word,2**63)-1))/n))
        points.append(p)
    return np.array(points)


def cartesian(n, points):
    owners=np.arange(n**3)
    left=np.tile(owners,3)
    right=[];images=[];normals=[]
    indices=np.array(np.unravel_index(owners,(n,)*3)).T
    for a in range(3):
        j=indices.copy();j[:,a]+=1
        right.append(np.ravel_multi_index(tuple((j%n).T),(n,)*3));images.append(j//n)
        v=np.zeros((len(j),3));v[:,a]=1.;normals.append(v)
    right=np.concatenate(right);images=np.concatenate(images);normals=np.concatenate(normals)
    area=np.full(len(left),1./n**2)
    return dict(generators=points,cell=points.copy(),vol=np.full(len(points),1./n**3),left=left,right=right,
                image=images,normal=normals,area=area,face=points[left]+0.5*normals/n)


def irregular(n,points):
    # Every point of the cube lies within sqrt(3)*(.5+.15)/n of a generator.
    # A bisector farther than twice that distance cannot cut a cell. An index
    # offset of three already separates generators by at least 2.7/n.
    grid=np.indices((n+4,)*3).reshape(3,-1).T-2
    owner=np.ravel_multi_index(tuple((grid%n).T),(n,)*3)
    images=grid//n
    vor=Voronoi(points[owner]+images,qhull_options="Qbb Qc Qz")
    ca,cb=vor.ridge_points.T
    a=np.where(owner[ca]<owner[cb],ca,cb)
    b=np.where(a==ca,cb,ca)
    chosen=np.flatnonzero((images[a]==0).all(axis=1))
    left,right,shift=owner[a[chosen]],owner[b[chosen]],images[b[chosen]]
    keep=np.lexsort((shift[:,2],shift[:,1],shift[:,0],right,left))
    chosen=chosen[keep];left=left[keep];right=right[keep];shift=shift[keep]
    if np.any(left==right) or len(np.unique(np.column_stack((left,right,shift)),axis=0))!=len(left):
        raise ValueError("Expected unique real-owner/image faces")
    delta=points[right]+shift-points[left]
    normal=delta/np.linalg.norm(delta,axis=1)[:,None]
    area=np.empty(len(left));face=np.empty((len(left),3));groups={}
    for j,ri in enumerate(chosen):
        polygon=vor.ridge_vertices[ri]
        if len(polygon)<3 or -1 in polygon:raise ValueError("Unbounded primary ridge")
        groups.setdefault(len(polygon),[]).append((j,polygon))
    for group in groups.values():
        ix=np.array([j for j,_ in group]); verts=vor.vertices[np.array([p for _,p in group])]
        c=verts.mean(axis=1);d=verts-c[:,None,:]
        ortho=np.eye(3)[np.argmin(np.abs(normal[ix]),axis=1)]
        u=np.cross(normal[ix],ortho);v=np.cross(normal[ix],u)
        angle=np.arctan2(np.einsum("fvi,fi->fv",d,v),np.einsum("fvi,fi->fv",d,u))
        d=np.take_along_axis(d,np.argsort(angle,axis=1)[:,:,None],axis=1);e=np.roll(d,-1,axis=1)
        weights=0.5*np.einsum("fvi,fi->fv",np.cross(d,e),normal[ix])
        if (weights<=0).any():raise ValueError("Invalid outward ridge triangle")
        area[ix]=weights.sum(axis=1)
        face[ix]=c+np.einsum("fv,fvi->fi",weights,d+e)/(3*area[ix,None])
    vol=np.zeros(len(points));moment=np.zeros_like(points)
    for owners,dx,no in ((left,face-points[left],normal),(right,face-shift-points[right],-normal)):
        pyramid=area*np.einsum("fi,fi->f",no,dx)/3
        if not (pyramid>0).all():raise ValueError("Nonpositive pyramid")
        np.add.at(vol,owners,pyramid);np.add.at(moment,owners,.75*pyramid[:,None]*dx)
    if not np.isfinite(moment).all() or abs(vol.sum()-1)>1e-11:raise ValueError("Metric partition")
    return dict(generators=points,cell=points+moment/vol[:,None],vol=vol,left=left,right=right,image=shift,
                area=area,normal=normal,face=face)


def geometry(n,jitter,seed=20261122):
    points=generators(n,jitter,seed)
    return irregular(n,points) if jitter else cartesian(n,points)


def compare_oracle(mesh, keeper):
    """Use actual candidate metrics from the accepted M2a jitter8 workflow."""
    if not np.array_equal(mesh["generators"],keeper["generators"]):raise ValueError("G02 generator words differ")
    keys=np.column_stack((mesh["left"],mesh["right"],mesh["image"])).astype(np.int64)
    if not np.array_equal(keys,keeper["keys"]):raise ValueError("G02 full face-image topology")
    worst={}
    for label,scale in (("cell",1.),("vol",keeper["vol"]),("face",1.),("area",1.),("normal",1.)):
        worst[label]=float(np.max(np.abs(mesh[label]-keeper[label])/scale))
    if max(worst.values())>1e-9:raise ValueError("G02 metric discrepancy "+str(worst))
    return worst
