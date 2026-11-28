"""Exact DE presence oracle on the registered 69-generator S20 affine paths.

Only the DE face is queried. Rank, cone, domain and distance checks reject a
fixture outside this construction. All predicates use the retained input words.
"""
from fractions import Fraction as F
import hashlib
from itertools import product
import json
from math import isqrt
from pathlib import Path
import struct

D = range(3)
ZERO = (F(0),)*3


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def encode(x):
    return (json.dumps(x, sort_keys=True, indent=2) + "\n").encode()


def word(x):
    return struct.pack(">d", float(x)).hex()


def exact(w):
    return F.from_float(struct.unpack(">d", bytes.fromhex(w))[0])


def plus(a,b):
    return tuple(x+y for x,y in zip(a,b))


def minus(a,b):
    return tuple(x-y for x,y in zip(a,b))


def scale(a,k):
    return tuple(k*x for x in a)


def dot(a,b):
    return sum((x*y for x,y in zip(a,b)), F(0))


def det(m):
    a,b,c=m
    return sum(a[i]*(b[(i+1)%3]*c[(i+2)%3]-b[(i+2)%3]*c[(i+1)%3]) for i in D)


def solve(a,b):
    den=det(a)
    need(den!=0, "singular stationary core")
    return tuple(det([[b[j] if k==i else a[j][k] for k in D] for j in D])/den for i in D)


def sqrt_bounds(q):
    need(q>=0, "negative square root")
    unit=1<<384
    r=isqrt((q.numerator*unit**2)//q.denominator)
    lo=F(r,unit)
    if lo**2==q: return (lo,lo)
    hi=F(r+1,unit)
    need(lo**2<q<hi**2, "square root bounds")
    return lo,hi


def payload(e,shift,perm,periodic):
    sc=F(1,3)+F(shift,1024)
    step=F(1,10) if periodic else F(1)
    core=[(1,0,0),(-F(3,5),F(4,5),0),(-F(3,5),-F(4,5),0),(0,0,-1),(-F(3,2)*sc,0,1-F(1,2**e))]
    rows=[]
    def add(i,r,w):
        rows.append(dict(id=f'{1:016x}{i:016x}',position=[word(r[k]) for k in perm],
                         velocity=[word(w[k]) for k in perm],winding=[0,0,0]))
    for j,p in enumerate(core):
        add(j+1,[F(1,2)+F(x)/20 for x in p],(F(3,40)/step,0,0) if j==4 else ZERO)
    for k,j,i in product(range(4),repeat=3):
        add(100+i+4*j+16*k,[F(2*u+1,8) for u in (i,j,k)],ZERO)
    return dict(schema="s20-binary64-dyadic-path-v1",trajectory="linear-unwrapped",units="unit box; code time",
                epsilon_exponent=e,centre_shift_1024=shift,permutation=perm,periodic=periodic,
                t0=word(0),dt=word(step),anchor=[word(0)]*3,width=[word(1)]*3,sites=rows,
                field_parameters={k:word(v) for k,v in dict(gamma=F(5,3),p=1,
                    rho0=1,rho_x=F(1,10),rho_y=F(7,100),rho_z=F(3,100),potential_amplitude=F(1,1000),
                    vx=F(1,5),vy=F(-1,10),vz=F(1,20),bx=F(1,5),by=F(1,10),bz=F(-3,10),phi=0).items()})


def bounds_text(i):
    return [str(x) for x in i]


def oracle(p):
    # Use normalized time s in [0,1], with x(s)=r0_bits+s*(dt_bits*w_bits).
    sites=[tuple(map(exact,r['position'])) for r in p['sites']]
    velocities=[tuple(map(exact,r['velocity'])) for r in p['sites']]
    dt=exact(p['dt'])
    motion=[scale(w,dt) for w in velocities]
    need(len(sites)==69 and len(set(sites))==69 and all(v==ZERO for j,v in enumerate(motion) if j!=4),"stationary catalog")
    a,b,c,d,e=sites[:5];rows=[minus(x,d) for x in (a,b,c)]
    # G*(O-D)=|A_i-D|²/2. Use rows G_i=(A_i-D).
    centre=plus(d,solve(rows,[dot(g,g)/2 for g in rows]))
    radius_sq=dot(minus(centre,d),minus(centre,d))
    u=minus(e,centre);v=motion[4]
    qa=dot(v,v);qb=dot(v,u);qc=dot(u,u)-radius_sq
    need(qa>0,"nonzero crossing velocity")
    mid=-qb/qa;fmin=qc-qb*qb/qa
    need(0<mid<1 and fmin<0,"interior event")
    wl,wh=sqrt_bounds(-fmin/qa)
    root0=(mid-wh,mid-wl);root1=(mid+wl,mid+wh)
    need(0<root0[0]<=root0[1]<root1[0]<=root1[1]<1,"two separate roots")
    need(root0[1]-root0[0]<(root1[0]-root0[1])/1000,"event relative root width")

    # Exact dual cone. If h=X-O, admissibility against ABC is G*h <= 0.
    # On the DE bisector, 2*alpha.(G*h)=F(s), G^T*alpha=E(s)-D.
    basis=list(zip(*rows))
    alpha0=solve(basis,minus(e,d));adot=solve(basis,v)
    amin=[min(x,x+y) for x,y in zip(alpha0,adot)]
    need(min(amin)>0,"DE axis strictly spans the three facet constraints throughout the path")
    columns=[solve(rows,[F(int(i==j)) for i in D]) for j in D]
    # F<0 gives a triangle, exactly. At its k-th corner all but the k-th
    # entry of G*h vanish, and h=G^{-1}e_k F/(2*alpha_k). F=0 gives one
    # point and F>0 is infeasible. Bound all positive triangles at once.
    width=[max(abs(columns[k][j])*(-fmin)/(2*amin[k]) for k in D) for j in D]
    low=minus(centre,width);high=plus(centre,width)
    need(all(0<x<y<1 for x,y in zip(low,high)),"interior box enclosure")
    radius_bound=sum(max(abs(lo-x),abs(hi-x))**2 for lo,hi,x in zip(low,high,d))
    images=list(product((-1,0,1),repeat=3)) if p['periodic'] else [(0,0,0)]
    min_margin=None;tested=0
    for i,(site,dr) in enumerate(zip(sites,motion)):
        end=plus(site,dr)
        need(all(0<x<1 for x in site+end),"unit-box nearest image bound")
        for image in images:
            if i<5 and image==(0,0,0): continue
            dist2=F(0)
            for j in D:
                a0=min(site[j],end[j])+image[j];a1=max(site[j],end[j])+image[j]
                dist2+=max(F(0),low[j]-a1,a0-high[j])**2
            margin=dist2-radius_bound
            need(margin>0,"unresolved competing generator or periodic image")
            min_margin=margin if min_margin is None else min(margin,min_margin)
            tested+=1
    # For an interior unit-box query the nearest periodic copy of each
    # primary generator lies among {-1,0,1}^3. Every more distant copy is
    # dominated by a listed image. Domain walls are strict by the box bound.
    interiors=[]
    for k in [F(-1,2),F(0),F(1,2)]:
        times=tuple(sorted((mid+k*wl,mid+k*wh)))
        f=fmin*(1-k*k)  # exact at the algebraic quarter/mid/three-quarter
        vertices=[]
        for j,col in enumerate(columns):
            al=sorted(alpha0[j]+adot[j]*t for t in times)
            coeff=[f/(2*z) for z in al]
            bounds=[sorted(centre[n]+q*col[n] for q in coeff) for n in D]
            vertices.append([bounds_text(bd) for bd in bounds])
        # Triangle area = |F|² |E-D| / (8 |det G| alpha_A alpha_B alpha_C).
        # This follows by transforming the three coordinate-axis intercepts
        # in z=G*h space back into the physical plane.
        alphas=[sorted(alpha0[j]+adot[j]*t for t in times) for j in D]
        displacements=[sorted((e[j]-d[j]+v[j]*t for t in times)) for j in D]
        norm2lo=sum((min(abs(a),abs(b)) if a*b>0 else F(0))**2 for a,b in displacements)
        norm2hi=sum(max(abs(a),abs(b))**2 for a,b in displacements)
        prodlo=alphas[0][0]*alphas[1][0]*alphas[2][0];prodhi=alphas[0][1]*alphas[1][1]*alphas[2][1]
        factor=f*f/(8*abs(det(rows)))
        area=(factor*sqrt_bounds(norm2lo)[0]/prodhi,factor*sqrt_bounds(norm2hi)[1]/prodlo)
        need(0<area[0]<=area[1] and area[1]-area[0]<area[0]/1000,"positive resolved DE polygon")
        interiors.append(dict(fraction_of_event=str((k+1)/2),time_s=bounds_text(times),vertices=vertices,area=bounds_text(area)))
    return dict(schema="s20-de-face-presence-v1",payload_sha256=hashlib.sha256(encode(p)).hexdigest(),
                pair=[p['sites'][3]['id'],p['sites'][4]['id']],image=[0,0,0],root_s_bounds=[bounds_text(root0),bounds_text(root1)],
                quantile_polygons=interiors,competing_halfspaces_verified=tested,minimum_squared_distance_margin=str(min_margin),
                minimum_cone_coefficient=str(min(amin)),area_at_roots="0",absent_outside=True,
                predicate_coefficients=[str(qa),str(2*qb),str(qc)],cpu_threads=1)


def main():
    cfg=json.loads(Path("case.json").read_bytes())
    e,k,perm,periodic=cfg['epsilon_exponent'],cfg['centre_shift_1024'],cfg['permutation'],cfg['periodic']
    need(e in (9,16,28) and k in (-1,0,1) and sorted(perm)==[0,1,2] and type(periodic) is bool,"registered case")
    p=payload(e,k,perm,periodic)
    Path("literal.json").write_bytes(encode(p))
    result=oracle(p)
    Path("certificate.json").write_bytes(encode(result))


if __name__=="__main__":
    main()
