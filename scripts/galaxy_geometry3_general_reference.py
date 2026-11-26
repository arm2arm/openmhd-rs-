"""Independent general-polytope reference; execute only on REANA.

Qhull proposes supporting-plane intersections. Exact integer/rational checks
certify every vertex against every retained halfspace, planar convex faces,
a connected closed oriented two-manifold and Euler characteristic two. No
candidate polygon, metric, predicate or topology is used as reference input.
"""
from collections import Counter, defaultdict
from fractions import Fraction as Q
from functools import reduce
from itertools import combinations, product
from math import gcd, isqrt
import hashlib
import json

import galaxy_geometry3_general_bridge as bridge
import galaxy_geometry3_reference as ieee


def need(condition, message):
    if not condition:
        raise ValueError(message)


def dot(a, b):
    return sum((x*y for x, y in zip(a, b)), 0)


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def det(rows):
    return dot(rows[0], cross(rows[1], rows[2]))


def intersection(planes, indices):
    rows = [planes[k]['n'] for k in indices]
    d = det(rows)
    if d == 0:
        return None
    n = [det([tuple(planes[indices[k]]['h'] if axis == a else rows[k][axis]
                    for axis in range(3)) for k in range(3)]) for a in range(3)]
    if d < 0:
        d, n = -d, [-v for v in n]
    common = reduce(gcd, [d, *n])
    return tuple(v // common for v in n), d // common


def plane_key(owner, other, image, winding):
    trajectory = tuple(image[a] + winding[owner][a] - winding[other][a] for a in range(3))
    forward = owner < other or owner == other and next((x for x in trajectory if x), 0) > 0
    return ((owner, other, trajectory), 1) if forward else ((other, owner, tuple(-x for x in trajectory)), -1)


def constraints(owner, points, widths, winding):
    planes = []
    def add(other, image, n, h):
        key, sign = plane_key(owner, other, image, winding)
        planes.append(dict(n=tuple(n), h=h, key=key, sign=sign, other=other, image=image))
    for axis in range(3):
        for sign in (-1, 1):
            n = [0, 0, 0]; n[axis] = 2*sign
            image = [0, 0, 0]; image[axis] = sign
            add(owner, tuple(image), n, widths[axis])
    for other, p in sorted(points.items()):
        for image in product((-1, 0, 1), repeat=3):
            if owner == other and sum(x != 0 for x in image) <= 1:
                continue
            d = tuple(p[a] + image[a]*widths[a] - points[owner][a] for a in range(3))
            h = dot(d, d)
            need(h > 0, 'Coincident reference generators')
            # Exact redundancy certificate on the owner's self-image box.
            if h >= sum(abs(d[a])*widths[a] for a in range(3)):
                continue
            add(other, image, tuple(2*x for x in d), h)
    return planes


def polygon(indices, vertices, n):
    axis = max(range(3), key=lambda a: abs(n[a])); axes = [a for a in range(3) if a != axis]
    def xy(k):
        return tuple(vertices[k][a] for a in axes)
    ordered = sorted(set(indices), key=xy)
    def orientation(a, b, c):
        u, v, w = xy(a), xy(b), xy(c)
        return (v[0]-u[0])*(w[1]-u[1])-(v[1]-u[1])*(w[0]-u[0])
    lower, upper = [], []
    for chain, sequence in ((lower, ordered), (upper, reversed(ordered))):
        for k in sequence:
            while len(chain) >= 2 and orientation(chain[-2], chain[-1], k) <= 0:
                chain.pop()
            chain.append(k)
    loop = lower[:-1] + upper[:-1]
    if len(loop) < 3:
        return []
    a, b, c = (vertices[k] for k in loop[:3])
    if dot(cross(sub(b, a), sub(c, a)), n) < 0:
        loop.reverse()
    return loop


def active_supports(planes, point):
    numerator, denominator = point
    active = []
    for k, plane in enumerate(planes):
        slack = plane['h'] * denominator - dot(plane['n'], numerator)
        need(slack >= 0, 'Proposed reference vertex violates an exact input halfspace')
        if slack == 0:
            active.append(k)
    return active


def support_basis(planes, active):
    basis = []
    for k in active:
        normal = planes[k]['n']
        if not basis or (len(basis) == 1 and any(cross(planes[basis[0]]['n'], normal))):
            basis.append(k)
        elif len(basis) == 2 and dot(cross(planes[basis[0]]['n'], planes[basis[1]]['n']), normal):
            return (*basis, k)
    return tuple(basis)


def edge_endpoint(planes, point, direction):
    """Next exact support from a feasible point along a feasible, nonzero direction."""
    numerator, denominator = point
    best = None
    for plane in planes:
        slope = dot(plane['n'], direction)
        if slope <= 0:
            continue
        slack = plane['h'] * denominator - dot(plane['n'], numerator)
        need(slack > 0, 'Edge direction leaves an active halfspace')
        if best is None or slack * best[1] < best[0] * slope:
            best = (slack, slope)
    need(best is not None, 'Bounded reference cell has a forward endpoint')
    slack, slope = best
    new_denominator = denominator * slope
    new_numerator = tuple(x * slope + v * slack for x, v in zip(numerator, direction))
    common = reduce(gcd, new_numerator, new_denominator)
    return tuple(x // common for x in new_numerator), new_denominator // common


def exact_vertices(planes):
    """Walk every edge using integer halfspaces and reduced homogeneous vertices."""
    # From the strictly interior generator, each step tangent to all current
    # supports adds an independent support. Three steps suffice in 3D.
    point = ((0, 0, 0), 1)
    for _ in range(3):
        basis = support_basis(planes, active_supports(planes, point))
        if len(basis) == 3:
            break
        if len(basis) == 0:
            direction = (1, 0, 0)
        elif len(basis) == 1:
            normal = planes[basis[0]]['n']
            axis = (1, 0, 0) if normal[1] or normal[2] else (0, 1, 0)
            direction = cross(normal, axis)
        else:
            direction = cross(planes[basis[0]]['n'], planes[basis[1]]['n'])
        point = edge_endpoint(planes, point, direction)

    pending = [point]
    seen = {point}
    while pending:
        point = pending.pop()
        active = active_supports(planes, point)
        basis = support_basis(planes, active)
        need(len(basis) == 3 and intersection(planes, basis) == point, 'Exact rank-three vertex certificate')
        yield point, basis
        # Every edge through a vertex lies on two independent supporting
        # planes. All additional active planes constrain its permitted sign.
        directions = set()
        for i, j in combinations(active, 2):
            v = cross(planes[i]['n'], planes[j]['n'])
            divisor = reduce(gcd, v, 0)
            if not divisor:
                continue
            v = tuple(x // divisor for x in v)
            directions.update((v, tuple(-x for x in v)))
        for v in sorted(directions):
            if any(dot(planes[i]['n'], v) > 0 for i in active):
                continue
            neighbour = edge_endpoint(planes, point, v)
            if neighbour not in seen:
                seen.add(neighbour)
                # Euler's identity and degree >= 3 imply V <= 2F - 4.
                need(len(seen) <= 2 * len(planes) - 4, 'Convex polyhedron vertex bound')
                pending.append(neighbour)


def proposed_vertices(planes, denominator):
    import numpy as np
    from scipy.spatial import HalfspaceIntersection
    # Local physical coordinate x = integer-coordinate / denominator; origin is strictly interior.
    halfspaces = np.asarray([[float(Q(n*denominator, p['h'])) for n in p['n']] + [-1.0] for p in planes])
    proposed = HalfspaceIntersection(halfspaces, np.zeros(3))
    for facet in proposed.dual_facets:
        point = None
        for indices in combinations(sorted(facet), 3):
            point = intersection(planes, indices)
            if point is not None:
                break
        need(point is not None, 'Independent dual facet has no rank-three intersection')
        yield point, indices


def certified_surface(planes, denominator, candidates):
    vertices, supports, certificates = [], [], []
    seen = set()
    for point, indices in candidates:
        if point in seen:
            continue
        seen.add(point); n, d = point
        active = active_supports(planes, point)
        need(set(indices) <= set(active), 'Proposed support is exact')
        vertices.append(tuple(Q(x, d*denominator) for x in n))
        supports.append(active); certificates.append(list(indices))
    need(len(vertices) >= 4, 'Full-dimensional reference cell')
    faces = []
    for k, p in enumerate(planes):
        loop = polygon([i for i, active in enumerate(supports) if k in active], vertices, p['n'])
        if loop:
            faces.append((p, loop))
    edges = Counter((loop[i], loop[(i+1) % len(loop)]) for _, loop in faces for i in range(len(loop)))
    need(all(count == 1 and edges[(v, u)] == 1 for (u, v), count in edges.items()), 'Exact closed oriented reference surface')
    used = {u for edge in edges for u in edge}
    need(used == set(range(len(vertices))) and len(vertices)-len(edges)//2+len(faces) == 2, 'Reference sphere Euler certificate')
    adjacency = defaultdict(set)
    for u, v in edges:
        adjacency[u].add(v)
    reached, pending = set(), [0]
    while pending:
        k = pending.pop()
        if k not in reached:
            reached.add(k); pending.extend(adjacency[k]-reached)
    need(reached == used, 'Connected reference boundary')
    for vertex in used:
        link = defaultdict(set)
        for _, loop in faces:
            if vertex in loop:
                at = loop.index(vertex)
                before, after = loop[at-1], loop[(at+1) % len(loop)]
                link[before].add(after); link[after].add(before)
        need(link and all(len(neighbours) == 2 for neighbours in link.values()),
             'Every reference vertex has a manifold cycle link')
        visited, queue = set(), [next(iter(link))]
        while queue:
            k = queue.pop()
            if k not in visited:
                visited.add(k); queue.extend(link[k]-visited)
        need(visited == set(link), 'Connected reference vertex link')
    return vertices, faces, dict(vertex_support_triples=certificates, vertices=len(vertices),
        faces=len(faces), edges=len(edges)//2, exact_halfspaces=len(planes), closed_oriented_surface=True)


def certify_cell(planes, denominator):
    from scipy.spatial import QhullError
    try:
        vertices, faces, certificate = certified_surface(planes, denominator, proposed_vertices(planes, denominator))
        certificate['vertex_enumeration'] = 'certified-dual-proposal'
    except (ValueError, QhullError) as exc:
        vertices, faces, certificate = certified_surface(planes, denominator, exact_vertices(planes))
        certificate['vertex_enumeration'] = 'exact-edge-walk'
        certificate['proposal_rejection'] = type(exc).__name__
    return vertices, faces, certificate


def enclosure(value, bits=160):
    """Outward exact dyadic enclosure; never infer uncertainty from candidate agreement."""
    value = Q(value); scale = 1 << bits
    lo = (value.numerator*scale)//value.denominator
    hi = -((-value.numerator*scale)//value.denominator)
    return [str(Q(lo, scale)), str(Q(hi, scale))]


def sqrt_enclosure(value, bits=160):
    value = Q(value);need(value >= 0, 'Nonnegative reference radical')
    scale = 1 << bits
    lo = isqrt((value.numerator*scale*scale)//value.denominator)
    hi = lo if Q(lo*lo, scale*scale) == value else lo+1
    return [str(Q(lo, scale)), str(Q(hi, scale))]


def integrate(vertices, faces):
    volume = Q(0); first = [Q(0)]*3; raw = [[Q(0)]*3 for _ in range(3)]; records = []
    for p, loop in faces:
        pts = [vertices[i] for i in loop]
        area_vector = tuple(sum((cross(a, b)[k] for a, b in zip(pts, pts[1:]+pts[:1])), Q(0))/2 for k in range(3))
        need(dot(area_vector, p['n']) > 0, 'Outward exact face orientation')
        axis = max(range(3), key=lambda a: abs(p['n'][a])); projected = Q(0)
        face_first = [Q(0)]*3; face_raw = [[Q(0)]*3 for _ in range(3)]
        for k in range(1, len(pts)-1):
            tri = (pts[0], pts[k], pts[k+1]); s = [sum((a[j] for a in tri), Q(0)) for j in range(3)]
            v = det(tri)/6
            need(v > 0, 'Positive exact tetrahedron from strict interior origin')
            volume += v
            weight = cross(sub(tri[1], tri[0]), sub(tri[2], tri[0]))[axis] / area_vector[axis]
            need(weight > 0, 'Positive exact face triangulation')
            projected += weight
            for a in range(3):
                first[a] += v*s[a]/4;face_first[a] += weight*s[a]/3
                for b in range(3):
                    diagonal = sum((x[a]*x[b] for x in tri), Q(0))
                    raw[a][b] += v*(diagonal+s[a]*s[b])/20
                    face_raw[a][b] += weight*(diagonal+s[a]*s[b])/12
        centroid = [v/projected for v in face_first]
        covariance = [[face_raw[a][b]/projected-centroid[a]*centroid[b] for b in range(3)] for a in range(3)]
        records.append(dict(plane=p, area_squared=dot(area_vector, area_vector), area_vector=area_vector,
            centroid=centroid, covariance=covariance))
    need(volume > 0, 'Positive reference volume')
    centroid = [x/volume for x in first]
    central = [[raw[a][b]-volume*centroid[a]*centroid[b] for b in range(3)] for a in range(3)]
    return volume, centroid, central, records


def evaluate(input_bytes):
    import numpy, scipy
    value = bridge.parse_input(input_bytes)
    need(value['domain']['boundary'] == 'periodic', 'Registered general reference is periodic')
    decode = lambda s: ieee.exact_binary64(int(s, 16))
    coordinates = {g['id']:tuple(decode(x) for x in g['position_bits']) for g in value['generators']}
    widths = tuple(decode(x) for x in value['domain']['width_bits'])
    denominator = max(x.denominator for p in coordinates.values() for x in p)
    denominator = max(denominator, *(x.denominator for x in widths))
    points = {k:tuple(int(x*denominator) for x in v) for k,v in coordinates.items()}
    integer_widths = tuple(int(x*denominator) for x in widths)
    winding = {g['id']:g['winding'] for g in value['generators']}
    cells, shared, uses = [], {}, Counter()
    total = Q(0)
    for owner in sorted(points):
        planes = constraints(owner, points, integer_widths, winding)
        vertices, faces, certificate = certify_cell(planes, denominator)
        volume, centroid, central, face_records = integrate(vertices, faces)
        total += volume
        cells.append(dict(id=owner, volume=enclosure(volume), centroid=[enclosure(v) for v in centroid],
            central_moment=[[enclosure(v) for v in row] for row in central], certificate=certificate))
        for r in face_records:
            p=r['plane'];key=p['key'];uses[key]+=1
            if p['sign'] == 1:
                need(key not in shared, 'Unique canonical reference face')
                shared[key] = dict(key=[key[0],key[1],list(key[2])], area=sqrt_enclosure(r['area_squared']),
                    centroid=[enclosure(v) for v in r['centroid']],
                    covariance=[[enclosure(v) for v in row] for row in r['covariance']],
                    area_vector=[enclosure(v) for v in r['area_vector']])
    need(all(n == 2 for n in uses.values()) and set(shared) == set(uses), 'Independent periodic reciprocal face coverage')
    need(total == widths[0]*widths[1]*widths[2], 'Exact independently integrated domain volume')
    return dict(schema='openmhd.geometry3.certified-general-reference.v1', input_sha256=hashlib.sha256(input_bytes).hexdigest(),
        method='certified-dual-or-exact-edge-walk-rational-tetrahedra-v2', numpy=numpy.__version__, scipy=scipy.__version__,
        cells=cells, faces=[shared[k] for k in sorted(shared)], exact_volume_closure=True, component_accepted=False)
