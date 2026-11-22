"""Conservative polygon-overlap comparisons for the unchanged M0 packet."""
import math


def area(polygon):
    if len(polygon) < 3:
        return 0.
    x, y = polygon[0]
    return abs(math.fsum((a[0]-x)*(b[1]-y)-(a[1]-y)*(b[0]-x)
                        for a, b in zip(polygon[1:], polygon[2:])))*.5


def clip(polygon, normal, bound):
    """Intersect a convex polygon with normal dot x <= bound."""
    if not polygon:
        return []
    result = []
    previous = polygon[-1]
    a = math.fsum(n*x for n, x in zip(normal, previous))-bound
    for point in polygon:
        b = math.fsum(n*x for n, x in zip(normal, point))-bound
        if (a <= 0.) != (b <= 0.):
            f = a/(a-b)
            result.append(tuple(x+f*(y-x) for x, y in zip(previous, point)))
        if b <= 0.:
            result.append(point)
        previous, a = point, b
    return result


def rectangle(polygon, bounds):
    for normal, bound in (((-1., 0.), -bounds[0]), ((1., 0.), bounds[1]),
                          ((0., -1.), -bounds[2]), ((0., 1.), bounds[3])):
        polygon = clip(polygon, normal, bound)
    return polygon


def polygons(geometry, cells, shift=(0., 0.)):
    """Return cell polygons as pieces within the unboosted periodic domain."""
    lengths = geometry['lengths']
    if len(lengths) != 2 or not all(math.isfinite(l) and l > 0 for l in lengths):
        raise ValueError('invalid geometry domain')
    if len(geometry['cells']) != len(cells) or not cells:
        raise ValueError('incomplete geometry')
    if not math.isfinite(geometry['time']) or len(shift) != 2 or not all(map(math.isfinite, shift)):
        raise ValueError('nonfinite geometry time/shift')
    result = []
    for i, (g, c) in enumerate(zip(geometry['cells'], cells)):
        if (len(g['centroid']) != 2 or len(g['generator']) != 2
            or not all(map(math.isfinite, [g['volume'], c['volume'], c['time'], c['x'], c['y'], *g['centroid'], *g['generator']]))
            or g['volume'] <= 0 or c['volume'] <= 0 or len(g['planes']) < 3):
            raise ValueError('invalid geometry cell')
        if g['id'] != i or c['id'] != i or abs(c['time']-geometry['time']) > 1e-12:
            raise ValueError('geometry ID/time mismatch')
        if abs(g['volume']/c['volume']-1) > 1e-10:
            raise ValueError('geometry volume mismatch')
        if any(abs((g['centroid'][k]-c[key]+lengths[k]/2)%lengths[k]-lengths[k]/2)>1e-10
               for k, key in enumerate(('x', 'y'))):
            raise ValueError('geometry position mismatch')
        x, y = g['generator']; lx, ly = lengths
        p = [(x-lx,y-ly),(x+lx,y-ly),(x+lx,y+ly),(x-lx,y+ly)]
        for nx, ny, fx, fy in g['planes']:
            if not all(map(math.isfinite, (nx,ny,fx,fy))) or abs(math.hypot(nx,ny)-1)>1e-10:
                raise ValueError('invalid oriented face')
            p = clip(p, (nx, ny), nx*fx+ny*fy)
        if not p or abs(area(p)/c['volume']-1)>1e-8:
            raise ValueError('polygon does not recover the recorded cell area')
        g['vertices'] = p  # Retain exact unwrapped vertices in the measured geometry artifact.
        p = [(x-shift[0],y-shift[1]) for x,y in p]
        ranges = [range(-math.ceil(max(v[k] for v in p)/lengths[k]),
                        -math.floor(min(v[k] for v in p)/lengths[k])+1) for k in range(2)]
        pieces = []
        for ix in ranges[0]:
            for iy in ranges[1]:
                piece = rectangle([(x+ix*lx,y+iy*ly) for x,y in p], (0.,lx,0.,ly))
                if area(piece)>0: pieces.append(piece)
        if abs(math.fsum(map(area,pieces))/c['volume']-1)>1e-8:
            raise ValueError('periodic projection loses cell area')
        result.append(pieces)
    if abs(math.fsum(c['volume'] for c in cells)/(lengths[0]*lengths[1])-1)>1e-9:
        raise ValueError('incomplete domain volume')
    return result


def shock_errors(cells, pieces, reference):
    """Average fine primitive samples over each clipped cell BEFORE L1/L2."""
    fields = ('rho','p','vx','by')
    n = len(reference)
    if n == 0 or any(abs(r['x']-(.5+(i+.5)/n))>1e-12 for i,r in enumerate(reference)):
        raise ValueError('invalid shock reference coordinates')
    sums = {f:[] for f in fields}; squares = {f:[] for f in fields}; volumes=[]
    for c, parts in zip(cells, pieces):
        integrals = dict.fromkeys(fields,0.); volume=0.
        for polygon in parts:
            p = rectangle(polygon,(.5,1.5,0.,.125))
            if area(p)==0.: continue
            lo=max(0,math.floor((min(x for x,y in p)-.5)*n))
            hi=min(n-1,math.floor((max(x for x,y in p)-.5)*n))
            for j in range(lo,hi+1):
                a=area(rectangle(p,(.5+j/n,.5+(j+1)/n,0.,.125)))
                volume+=a
                for f in fields:integrals[f]+=a*reference[j][f]
        if volume>0:
            volumes.append(volume)
            for f in fields:
                d=c[f]-integrals[f]/volume
                sums[f].append(volume*abs(d));squares[f].append(volume*d*d)
    total=math.fsum(volumes)
    if abs(total/.125-1)>1e-8:raise ValueError('incomplete central shock interval')
    return {f:{'L1':math.fsum(sums[f])/total,'L2':math.sqrt(math.fsum(squares[f])/total)} for f in fields}


def vortex_bins(cells, pieces, bins=64):
    fields=('rho','p','bx','by')
    values=[dict.fromkeys(fields,0.) for _ in range(bins*bins)];volumes=[0.]*(bins*bins)
    for c,parts in zip(cells,pieces):
        for p in parts:
            ranges=[range(max(0,math.floor(min(v[k] for v in p)*bins)),
                          min(bins-1,math.floor(max(v[k] for v in p)*bins))+1) for k in range(2)]
            for j in ranges[1]:
                for i in ranges[0]:
                    a=area(rectangle(p,(i/bins,(i+1)/bins,j/bins,(j+1)/bins)))
                    index=i+bins*j;volumes[index]+=a
                    for f in fields:values[index][f]+=a*c[f]
    if any(abs(v*bins*bins-1)>1e-8 for v in volumes):raise ValueError('incomplete vortex bin coverage')
    return [{f:r[f]/v for f in fields} for r,v in zip(values,volumes)]
