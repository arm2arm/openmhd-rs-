"""Predeclared MPI/Rayon comparisons. Each entry is one independent REANA workflow."""
LAYOUTS = [(1, 1), (1, 4), (2, 1), (2, 2), (4, 1)]
DEFAULTS = dict(n=4, repeats=1, timeout=420, times=["0.125"], reference=False)
FAMILIES = {
    "rigid-mesh": dict(family="mesh", problem="rigid", repeats=3, times=["0.125","0.25"]),
    "jitter-mesh": dict(family="mesh", problem="jitter", n=3, times=["0.03125"]),
    "flip-mesh": dict(family="mesh", problem="flip", n=5, times=["0.5","0.5"]),
    "periodic-self": dict(family="mesh", problem="rigid", n=1, empty_owner=True, times=["8"]),
    "lloyd": dict(family="lloyd", problem="jitter", n=3, times=["0.0625"]),
    "moving-curl3": dict(family="field3", problem="deformation", n=3, tangent=True),
    "curl-flux3": dict(family="field3", problem="jitter", n=4),
    "kdk": dict(family="gravity", problem="counterstream", n=256, steps=8, stride=4, repeats=3),
    "alfven": dict(family="mhd2", problem="alfven", n=8, ny=8, jitter=0., times=["0.0078125","0.015625"], boost=["0","0","0"]),
    "boosted-loop": dict(family="mhd2", problem="loop", n=8, ny=8, jitter=0.125, times=["0.0078125","0.015625"], boost=["0.5","-0.25","0.125"]),
    "deforming-alfven": dict(family="mhd2",problem="alfven",deform=True,n=8,ny=8,jitter=0.125,times=["0.0005","0.001"],boost=["0","0","0"]),
    **{problem:dict(family="compare2",problem=problem,n=8,jitter=0.125,times=["0.015625"])
       for problem in ("ct","ct-limited","planar","passive","prescribed")},
    "vortex": dict(family="mhd2", problem="vortex", n=8, ny=8, jitter=0.125, times=["0.01"], boost=["0","0","0"]),
    "brio": dict(family="mhd2", problem="brio", n=16, ny=4, jitter=0., times=["0.001"], boost=["0","0","0"]),
}

def fixed(label, ranks, threads, reference=False, **overrides):
    c = {**DEFAULTS, **FAMILIES[label], **overrides}
    c.update(label=label, ranks=ranks, threads=threads, reference=reference)
    return c

def strong():
    out=[]
    for name in FAMILIES:
        out.append(fixed(name,1,1,True))
        for r,t in LAYOUTS:
            out.append(fixed(name,r,t))
    out.extend(fixed(name,2,2,reverse=True) for name in ("jitter-mesh","lloyd","curl-flux3","kdk"))
    return out

def weak():
    out=[]
    for r in (1,2,4):
        out.append(fixed("alfven",r,1,ny=8*r,repeats=3,scaling="weak"))
        out.append(fixed("rigid-mesh",r,1,n=3,nz=3*r,repeats=3,scaling="weak"))
        # Direct gravity work is N(N-1)/2. Choose the nearest N giving constant pairs/rank.
        n=round((1+(1+4*r*128*127)**0.5)/2)
        out.append(fixed("kdk",r,1,n=n,steps=4,stride=4,scaling="weak"))
    return out


def sweep_cases():
    """The M2 swept-volume closure added after the original hybrid campaign."""
    for label, base in (("swept-flip","flip-mesh"), ("swept-jitter","jitter-mesh")):
        for ranks, threads, reference in [(1,1,True), *((r,t,False) for r,t in LAYOUTS)]:
            yield dict(fixed(base,ranks,threads,reference,sweeps=True),label=label)
