"""Piecewise-constant primitive projection by convex polygon/bin overlap.

No point sampling or nearest-cell interpolation. Every periodic image contributes
once to its bin; coverage and volume integrals are checked independently.
"""
import csv
import math
from pathlib import Path

FIELDS = ('rho', 'p', 'vx', 'vy', 'vz', 'bx', 'by', 'bz')


def area(poly):
    if len(poly) < 3:
        return 0.
    # Shift origin to avoid cancellation for tiny slivers at large coordinates.
    x, y = poly[0]
    return abs(sum((a[0]-x)*(b[1]-y)-(a[1]-y)*(b[0]-x)
                   for a,b in zip(poly,poly[1:]+poly[:1])))*.5


def clip(poly, axis, edge, lower):
    result=[]
    if not poly:
        return result
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=a[axis]-edge; db=b[axis]-edge
        ia=da>=0 if lower else da<=0
        ib=db>=0 if lower else db<=0
        if ia != ib:
            t=da/(da-db)
            result.append(tuple(a[k]+t*(b[k]-a[k]) for k in range(2)))
        if ib:
            result.append(b)
    return result


def overlap(poly, bounds):
    for axis in range(2):
        poly=clip(poly,axis,bounds[axis][0],True)
        poly=clip(poly,axis,bounds[axis][1],False)
    return area(poly)


def polygons(path):
    result={}
    with Path(path).open() as f:
        for r in csv.DictReader(f):
            i=int(r['id']); vertices=result.setdefault(i,[])
            if int(r['vertex']) != len(vertices):
                raise ValueError('nonsequential polygon vertices')
            vertices.append((float(r['x']),float(r['y'])))
    return result


def project(cells, polys, lengths, shape):
    nx,ny=shape; lx,ly=lengths; dx,dy=lx/nx,ly/ny
    sums=[[0.]*len(FIELDS) for _ in range(nx*ny)]; coverage=[0.]*(nx*ny)
    if set(polys) != set(range(len(cells))):
        raise ValueError('polygon IDs do not cover cells exactly')
    for i,c in enumerate(cells):
        p=polys[i]
        if len(p)<3 or any(not math.isfinite(x) for v in p for x in v):
            raise ValueError('invalid polygon')
        shift=[math.floor(sum(v[k] for v in p)/len(p)/lengths[k])*lengths[k] for k in range(2)]
        p=[tuple(v[k]-shift[k] for k in range(2)) for v in p]
        if abs(area(p)/c['volume']-1)>1e-9:
            raise ValueError('polygon/cell area disagreement')
        received=0.
        for jy in range(math.floor(min(v[1] for v in p)/dy),math.floor(max(v[1] for v in p)/dy)+1):
            for ix in range(math.floor(min(v[0] for v in p)/dx),math.floor(max(v[0] for v in p)/dx)+1):
                a=overlap(p,((ix*dx,(ix+1)*dx),(jy*dy,(jy+1)*dy)))
                k=(jy%ny)*nx+ix%nx; coverage[k]+=a; received+=a
                for f,name in enumerate(FIELDS):
                    sums[k][f]+=a*c[name]
        if abs(received/c['volume']-1)>2e-9:
            raise ValueError('cell overlap volume lost')
    coverage_error=max(abs(v/(dx*dy)-1) for v in coverage)
    if coverage_error>2e-8:
        raise ValueError(f'incomplete/overlapping bin coverage: {coverage_error}')
    projected=[{name:s[f]/(dx*dy) for f,name in enumerate(FIELDS)} for s in sums]
    residual={name:sum(s[f] for s in sums)-sum(c['volume']*c[name] for c in cells) for f,name in enumerate(FIELDS)}
    for name,value in residual.items():
        scale=sum(c['volume']*abs(c[name]) for c in cells)
        if abs(value)>1e-10*(1+scale):
            raise ValueError('projection lost integral')
    return projected, {'coverage_relative_max':coverage_error,'integral_residual':residual}
