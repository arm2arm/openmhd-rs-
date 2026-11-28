"""Compare the original geometry words and oriented polygons of the single-threaded jobs."""
from collections import Counter
from fractions import Fraction
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct


def sha(x):
    return hashlib.sha256(x).hexdigest()


def vec_sub(a, b):
    return tuple(x-y for x, y in zip(a,b))


def dot(a, b):
    return math.fsum(x*y for x,y in zip(a,b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def length(a):
    return math.hypot(*a)


def v_sum(a, b, t):
    return tuple(x+t*y for x,y in zip(a,b))


def polygon(vs, normal):
    if len(vs)<3:
        return None
    fan=[cross(vec_sub(a,vs[0]),vec_sub(b,vs[0])) for a,b in zip(vs[1:],vs[2:])]
    av=tuple(0.5*math.fsum(v[d] for v in fan) for d in range(3))
    signed=dot(av,normal)
    scale=max(length(vec_sub(x,vs[0])) for x in vs)
    if abs(signed)<=1e-14*scale**2:
        # The smallness threshold only triggers an exact affine-rank check.
        # Positive-area contacts are never discarded by an epsilon rule.
        q=[tuple(map(Fraction,x)) for x in vs]
        d=next((vec_sub(x,q[0]) for x in q[1:] if x!=q[0]),None)
        if d is None or all(not any(cross(d,vec_sub(x,q[0]))) for x in q[1:]):
            return None
    if signed==0 or abs(abs(signed)-length(av))>1e-10*length(av):
        raise ValueError("nonplanar or unmeasurable positive face")
    tri=[0.5*dot(t,normal) for t in fan]
    ctr=tuple(math.fsum(a*(vs[0][d]+p[d]+q[d])/3 for a,p,q in zip(tri,vs[1:],vs[2:]))/signed for d in range(3))
    return abs(signed),ctr,signed<0


def to_segments(point, vs):
    def distance(a,b):
        d=vec_sub(b,a)
        ap=vec_sub(point,a)
        d2=dot(d,d)
        t=0.0 if d2==0 else min(1.0,max(0.0,dot(ap,d)/d2))
        return length(vec_sub(point,v_sum(a,d,t)))
    return min(distance(a,b) for a,b in zip(vs,vs[1:]+vs[:1]))


def read_geometry(buf, selected):
    points, cells, faces, zero = {}, {}, {}, []
    timing=None
    reversed_loops=0
    for line in buf.decode('ascii').splitlines():
        kind,*w=line.split()
        if kind=='T':
            if timing is not None or w[:2]!=selected:
                raise ValueError('timing identity')
            timing=list(map(float,w[2:]))
            continue
        owner=int(w[0])
        if kind=='P':
            if owner in points or len(w)!=7: raise ValueError('point')
            points[owner]=(tuple(w[1:4]),tuple(map(int,w[4:])))
        elif kind=='C':
            row=list(map(float,w[1:]))
            if len(row)!=4 or not all(map(math.isfinite,row)) or row[0]<=0 or owner in cells:
                raise ValueError('invalid cell')
            cells[owner]=(row[0],tuple(row[1:]))
        elif kind=='F':
            interior=w[1]=='I'
            if not interior and w[1]!='W':raise ValueError('face type')
            stop=6 if interior else 3
            key=(owner,w[1],*map(int,w[2:stop]))
            nums=list(map(float,w[stop:]))
            if len(nums)<3 or len(nums)%3 or not all(map(math.isfinite,nums)):raise ValueError('face components')
            normal=tuple(nums[:3])
            if abs(length(normal)-1)>1e-10:raise ValueError('normal magnitude')
            vertices=[tuple(nums[i:i+3]) for i in range(3,len(nums),3)]
            m=polygon(vertices,normal)
            if m is None:
                zero.append(key)
                continue
            area,ctr,rev=m
            reversed_loops+=int(rev)
            if key in faces:raise ValueError('duplicate positive-area face')
            faces[key]=(area,ctr,normal,vertices)
        else:
            raise ValueError('row type')
    if timing is None or len(timing)!=2 or not points or points.keys()!=cells.keys(): raise ValueError('incomplete geometry')
    xyz={i:tuple(struct.unpack('>d',bytes.fromhex(x))[0] for x in a) for i,(a,w) in points.items()}
    flux={i:[] for i in cells}
    plane_error=0.0
    for key,(a,c,n,vs) in faces.items():
        i=key[0];h=cells[i][0]**(1/3)
        if key[1]=='I':
            j=key[2]
            relative=tuple(k-p+q for k,p,q in zip(key[3:],points[i][1],points[j][1]))
            d=v_sum(vec_sub(xyz[j],xyz[i]),relative,1.0)
            dn=length(d)
            if dn==0:raise ValueError('coincident images')
            n0=tuple(v/dn for v in d); offset=dn/2
            other=(j,'I',i,*[-x for x in key[3:]])
            if other not in faces:raise ValueError('missing opposite positive incidence')
        else:
            axis,side=divmod(key[2],2); sign=2*side-1
            n0=tuple(sign if k==axis else 0 for k in range(3))
            offset=sign*(side-xyz[i][axis])
        plane_error=max(plane_error,length(vec_sub(n,n0)),*(abs(dot(p,n0)-offset)/h for p in vs))
        flux[i].append((a,n,c))
    closure=max(length(tuple(math.fsum(a*n[k] for a,n,c in entries) for k in range(3)))/math.fsum(t[0] for t in entries) for entries in flux.values())
    divergence_volume=max(abs(math.fsum(a*dot(c,n)/3 for a,n,c in entries)/cells[i][0]-1) for i,entries in flux.items())
    summary=dict(cells=len(cells),directed_faces=len(faces),zero_contacts=len(zero),reversed_loops=reversed_loops,construction_seconds=timing[0],including_row_preparation_seconds=timing[1],
                 relative_volume_sum=abs(math.fsum(v for v,c in cells.values())-1.0),max_area_closure=closure,max_plane_error=plane_error,
                 max_independent_volume_error=divergence_volume)
    return points,cells,faces,summary


def compare(a,b,check_words=True):
    ap,ac,af,_=a;bp,bc,bf,_=b
    if (check_words and bp!=ap) or ac.keys()!=bc.keys():raise ValueError('generator words or cell IDs differ')
    diffs=Counter()
    def peak(s,x):diffs[s]=max(diffs[s],x)
    for i,(v,c) in ac.items():
        vv,cc=bc[i];h=v**(1/3)
        peak('volume',abs(vv-v)/v);peak('cell_centroid',length(vec_sub(cc,c))/h)
    missing=af.keys()-bf.keys();extra=bf.keys()-af.keys()
    for k in af.keys() & bf.keys():
        a0,c,n,vs=af[k];a1,c1,n1,vs1=bf[k];h=ac[k[0]][0]**(1/3)
        peak('area',abs(a1-a0)/(h*h));peak('face_centroid',length(vec_sub(c1,c))/h);peak('normal',length(vec_sub(n,n1)))
        peak('polygon',max(max(to_segments(v,vs1) for v in vs),max(to_segments(v,vs) for v in vs1))/h)
    return dict(maximum=dict(diffs),missing_faces=len(missing),extra_faces=len(extra),missing_examples=sorted(missing)[:6],extra_examples=sorted(extra)[:6],
                passed=not(missing or extra) and max(diffs.values(),default=0)<=1e-9)


def main():
    packet=json.loads(Path('cases.json').read_bytes())
    results={}; clouds={}
    for name,case in packet.items():
        blob=Path(name+'.gz').read_bytes(); raw=gzip.decompress(blob)
        if sha(raw)!=case['stdout_sha256']: raise ValueError('raw output identity '+name)
        if case['backend']=='rates':continue
        item=dict(uuid=case['uuid'],exit_code=case['exit_code'],timeout=case['timed_out'])
        if case['exit_code']==0:
            try:
                obtained=read_geometry(raw,[case['backend'],case['fixture']])
                clouds[name]=obtained
                m=obtained[3]
                item.update(m)
                item['intrinsic_passed']=max(m['relative_volume_sum'],m['max_area_closure'])<=1e-10 and max(m['max_plane_error'],m['max_independent_volume_error'])<=1e-9
            except (ValueError,KeyError,ZeroDivisionError,OverflowError) as err:
                item['geometry_error']=str(err)
        results[name]=item
    for name,case in packet.items():
        f=case['fixture']; backend=case['backend']
        if backend=='rates':continue
        ref=f+'-'+('motion' if f=='cube8' else 'oracle')
        if name in clouds and ref in clouds:
            results[name]['comparison']=compare(clouds[ref],clouds[name])
        results[name]['passed']=bool(results[name].get('intrinsic_passed') and results[name].get('comparison',{}).get('passed') and results[ref].get('intrinsic_passed'))
    seams={}
    for b in ['oracle','motion','meshless']:
        before=clouds.get('seam-before-'+b);after=clouds.get('seam-after-'+b)
        if before and after:seams[b]=compare(before,after,check_words=False)
    Path('comparison.json').write_text(json.dumps(dict(cases=results,rigid_periodic_seam=seams),sort_keys=True,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    main()
