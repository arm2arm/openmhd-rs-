"""Registered G02/G04 metrics on actual words and independent enclosures; REANA only."""
from fractions import Fraction as Q
import hashlib

import galaxy_geometry3_general_bridge as bridge
import galaxy_geometry3_reference as ieee


def scalar(word):
    return ieee.exact_binary64(int(bridge.finite_word(word), 16))


def interval(value):
    bridge.require(type(value) is list and len(value) == 2, 'Two independent enclosure endpoints')
    a, b = map(Q, value)
    bridge.require(a <= b, 'Ordered independent enclosure')
    return a, b


def error(value, target):
    lo, hi = interval(target)
    return max(abs(value-lo), abs(value-hi))


def key(face):
    k = face['key']
    bridge.require(k['kind'] == 'interior', 'Periodic general mesh')
    return k['lo'], k['hi'], tuple(k['hi_image'])


def compare(input_bytes, transcript_bytes, reference):
    decoded = bridge.parse_transcript(transcript_bytes, input_bytes)
    bridge.require(reference['schema'] == 'openmhd.geometry3.certified-general-reference.v1'
        and reference['input_sha256'] == hashlib.sha256(input_bytes).hexdigest()
        and reference['exact_volume_closure'] is True, 'Exact independent reference/input')
    inputs = bridge.parse_input(input_bytes)
    width = list(map(scalar, inputs['domain']['width_bits'])); length = max(width)
    expected = {r['id']:r for r in reference['cells']}
    faces = {key(f):f for f in decoded['faces']}
    ref_faces = {(r['key'][0], r['key'][1], tuple(r['key'][2])):r for r in reference['faces']}
    bridge.require(set(faces) == set(ref_faces) and set(expected) == {c['id'] for c in decoded['cells']}, 'Exact independent cell/face/image topology')
    metrics = {n:Q(0) for n in ('volume_relative', 'centroid_over_L', 'cell_moment_over_VL2',
        'face_area_relative', 'face_centroid_over_L', 'face_covariance_over_L2', 'normal_component',
        'normal_closure_over_surface', 'affine_identity_over_V', 'centroid_identity_over_VL', 'total_volume_relative')}
    def maximum(name, value):
        metrics[name] = max(metrics[name], value)
    for c in decoded['cells']:
        r = expected[c['id']]; v = scalar(c['volume_bits']);vlo,_ = interval(r['volume'])
        bridge.require(vlo > 0 and v > 0, 'Independent and candidate positive cells')
        maximum('volume_relative', error(v, r['volume'])/vlo)
        centroid = list(map(scalar,c['centroid_offset_bits']))
        for a in range(3):
            maximum('centroid_over_L', error(centroid[a],r['centroid'][a])/length)
            for b in range(3):
                maximum('cell_moment_over_VL2',error(scalar(c['central_second_moment_bits'][a][b]),r['central_moment'][a][b])/(vlo*length*length))
        normal_sum = [Q(0)]*3;surface = Q(0);affine = [[Q(0)]*3 for _ in range(3)];first = [Q(0)]*3
        for incidence in c['incidences']:
            f = decoded['faces'][incidence['face']];area = scalar(f['area_bits']);surface += area
            n = [incidence['sign']*scalar(w) for w in f['normal_bits']]
            y = [scalar(f['centroid_offset_bits'][a])+scalar(incidence['chart_translation_bits'][a]) for a in range(3)]
            for a in range(3):
                normal_sum[a] += area*n[a]
                first[a] += area*sum((y[b]*n[b] for b in range(3)),Q(0))*y[a]
                for b in range(3):
                    affine[a][b] += area*y[a]*n[b]
        # Retain squared Euclidean closure; compare with the squared registered limit.
        maximum('normal_closure_over_surface', sum((x*x for x in normal_sum),Q(0))/(surface*surface))
        for a in range(3):
            maximum('centroid_identity_over_VL',abs(first[a]-4*v*centroid[a])/(v*length))
            for b in range(3):
                maximum('affine_identity_over_V',abs(affine[a][b]-(v if a==b else 0))/v)
    for k,f in faces.items():
        r=ref_faces[k];alo,ahi=interval(r['area']);bridge.require(alo > 0,'Positive independent face area')
        maximum('face_area_relative',error(scalar(f['area_bits']),r['area'])/alo)
        for a in range(3):
            maximum('face_centroid_over_L',error(scalar(f['centroid_offset_bits'][a]),r['centroid'][a])/length)
            lo,hi=interval(r['area_vector'][a]);quotients=[x/y for x in (lo,hi) for y in (alo,ahi)]
            maximum('normal_component',max(abs(scalar(f['normal_bits'][a])-v) for v in quotients))
            for b in range(3):
                maximum('face_covariance_over_L2',error(scalar(f['covariance_bits'][a][b]),r['covariance'][a][b])/(length*length))
    volume=width[0]*width[1]*width[2]
    maximum('total_volume_relative',abs(sum((scalar(c['volume_bits']) for c in decoded['cells']),Q(0))-volume)/volume)
    limits={n:(Q(1,10**20) if n=='normal_closure_over_surface' else Q(1,10**10) if n=='total_volume_relative' else Q(1,10**9)) for n in metrics}
    return dict(schema='openmhd.geometry3.general-comparison.v1', input_sha256=hashlib.sha256(input_bytes).hexdigest(),
        transcript_sha256=hashlib.sha256(transcript_bytes).hexdigest(),
        metrics={n:dict(upper=str(v),limit=str(limits[n]),passed=v<=limits[n],squared=n=='normal_closure_over_surface') for n,v in metrics.items()},
        topology_identical=True, passed=all(v<=limits[n] for n,v in metrics.items()), component_accepted=False)


def reproducibility(left_input, left_output, right_input, right_output):
    a=bridge.parse_transcript(left_output,left_input);b=bridge.parse_transcript(right_output,right_input)
    bridge.require([c['id'] for c in a['cells']]==[c['id'] for c in b['cells']], 'Same persistent cell IDs')
    bridge.require([key(f) for f in a['faces']]==[key(f) for f in b['faces']], 'Exact canonical trajectory keys across transforms')
    length=max(map(scalar,a['domain']['width_bits']));maximum=Q(0);bitwise=True
    def assess(x,y,scale):
        nonlocal maximum,bitwise
        maximum=max(maximum,abs(scalar(x)-scalar(y))/scale);bitwise=bitwise and x==y
    for x,y in zip(a['cells'],b['cells']):
        v=scalar(x['volume_bits']);assess(x['volume_bits'],y['volume_bits'],v)
        for i in range(3):
            assess(x['centroid_offset_bits'][i],y['centroid_offset_bits'][i],length)
            for j in range(3):assess(x['central_second_moment_bits'][i][j],y['central_second_moment_bits'][i][j],v*length*length)
    for x,y in zip(a['faces'],b['faces']):
        assess(x['area_bits'],y['area_bits'],scalar(x['area_bits']))
        for i in range(3):
            assess(x['normal_bits'][i],y['normal_bits'][i],Q(1))
            assess(x['centroid_offset_bits'][i],y['centroid_offset_bits'][i],length)
            for j in range(3):assess(x['covariance_bits'][i][j],y['covariance_bits'][i][j],length*length)
    return dict(schema='openmhd.geometry3.reproducibility.v1',canonical_keys_identical=True,maximum_normalized_difference=str(maximum),limit='1/10000000000',passed=maximum<=Q(1,10**10),metric_bits_identical=bitwise,component_accepted=False)
