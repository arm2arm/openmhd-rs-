#!/usr/bin/env python3
"""Split a planar-jitter Brio snapshot's Az into an x-only part and a remainder.

Least-squares periodic cubic B-spline f(x) with M knots on [0,2]; writes
PREFIX_xonly.csv and PREFIX_remainder.csv (x,y,az per cell, same order) for
`cargo run --release -p mhd-vector-pot --example bx-floor -- --cells ...`.
Diagnostic only. Usage: split_shock_potential.py SNAPSHOT_CSV M PREFIX
"""
import csv,sys,math
def bspl(t):  # cubic B-spline weights for fractional t in [0,1)
    return ((1-t)**3/6,(3*t**3-6*t**2+4)/6,(-3*t**3+3*t**2+3*t+1)/6,t**3/6)
def split(path,M,out):
    rows=[{k:float(v) for k,v in r.items()} for r in csv.DictReader(open(path))]
    L=2.;h=L/M
    A=[]  # per point: (indices, weights)
    for r in rows:
        s=(r['x']%L)/h;i=math.floor(s);w=bspl(s-i)
        A.append(([(i-1+k)%M for k in range(4)],w))
    b=[r['az'] for r in rows]
    def Ax(c):return [sum(w*c[j] for j,w in zip(idx,ws)) for idx,ws in A]
    def ATy(y):
        g=[0.]*M
        for (idx,ws),v in zip(A,y):
            for j,w in zip(idx,ws):g[j]+=w*v
        return g
    c=[0.]*M;r_=ATy(b);p=r_[:];rs=sum(x*x for x in r_);r0=rs
    for it in range(5000):
        q=ATy(Ax(p));a=rs/sum(x*y for x,y in zip(p,q))
        c=[x+a*y for x,y in zip(c,p)];r_=[x-a*y for x,y in zip(r_,q)]
        rn=sum(x*x for x in r_)
        if rn<1e-26*r0:break
        p=[x+rn/rs*y for x,y in zip(r_,p)];rs=rn
    f=Ax(c)
    for name,vals in (('xonly',f),('remainder',[x-y for x,y in zip(b,f)])):
        with open(f'{out}_{name}.csv','w') as s:
            s.write('x,y,az\n')
            for r,v in zip(rows,vals):s.write(f"{r['x']!r},{r['y']!r},{v!r}\n")
    print(path.split('/')[-1],'M',M,'iters',it,'rms remainder',math.sqrt(sum((x-y)**2 for x,y in zip(b,f))/len(b)))

if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit(__doc__)
    split(sys.argv[1],int(sys.argv[2]),sys.argv[3])
