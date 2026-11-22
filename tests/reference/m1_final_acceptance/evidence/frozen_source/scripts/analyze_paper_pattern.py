#!/usr/bin/env python3
"""Verify repeated geometry/operators before interpreting the controlled shocks."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def groups(records):
    result = defaultdict(list)
    for row in records:
        result[int(row['id'])].append(row)
    return result


def coefficients(records):
    result = defaultdict(lambda: [0., 0.])
    # Preserve duplicate periodic images and the implementation's first-sample
    # subtraction before combining coefficients by the repeated base-cell ID.
    for row in records:
        j, first = int(row['neighbor_base']), int(row['baseline_neighbor']) % 1024
        for k, column in enumerate(['weight_x', 'weight_y']):
            result[j][k] += float(row[column])
            result[first][k] -= float(row[column])
    return result


def compare(root, reference, repeated, height):
    a = rows(root/reference/'geometry.csv')
    b = rows(root/repeated/'geometry.csv')
    ar = groups(rows(root/reference/'stencils.csv'))
    br = groups(rows(root/repeated/'stencils.csv'))
    ai = rows(root/reference/'initial.csv')
    bi = rows(root/repeated/'initial.csv')
    ae = rows(root/reference/'initial_rates.csv')
    be = rows(root/repeated/'initial_rates.csv')
    assert len(a) == 1024 and len(b) % len(a) == 0
    maxima = dict(centroid_absolute=0., volume_relative=0., face_geometry_absolute=0.,
                  operator_relative_L1=0., operator_absolute=0.,
                  initial_state_scaled=0., initial_rate_scaled=0.)
    for row in b:
        i, j, tile = int(row['id']), int(row['base_id']), int(row['tile'])
        expected = a[j]
        assert i == tile*1024+j and int(row['face_count']) == int(expected['face_count'])
        maxima['centroid_absolute'] = max(maxima['centroid_absolute'],
            abs(float(row['cx'])-float(expected['cx'])),
            abs(float(row['cy'])-tile*height-float(expected['cy'])))
        maxima['volume_relative'] = max(maxima['volume_relative'], abs(float(row['volume'])/float(expected['volume'])-1))
        candidates = list(br[i])
        for face in ar[j]:
            columns = ['dx', 'dy', 'area', 'nx', 'ny', 'face_dx', 'face_dy']
            choices = [(max(abs(float(face[k])-float(other[k])) for k in columns), n)
                       for n, other in enumerate(candidates) if face['neighbor_base'] == other['neighbor_base']]
            assert choices, (reference, repeated, i, face)
            error, n = min(choices)
            maxima['face_geometry_absolute'] = max(maxima['face_geometry_absolute'], error)
            candidates.pop(n)
        assert not candidates
        ca, cb = coefficients(ar[j]), coefficients(br[i])
        assert set(ca) == set(cb)
        absolute = [abs(ca[n][k]-cb[n][k]) for n in ca for k in range(2)]
        norm = sum(abs(v) for values in ca.values() for v in values)
        maxima['operator_absolute'] = max(maxima['operator_absolute'], max(absolute))
        maxima['operator_relative_L1'] = max(maxima['operator_relative_L1'], sum(absolute)/norm)
        for before, after, columns, key in [
                (ai[j], bi[i], ['rho', 'p', 'vx', 'vy', 'vz', 'bx', 'by', 'bz'], 'initial_state_scaled'),
                (ae[j], be[i], ['total_rate', 'magnetic_rate', 'magnetic_rate_fv', 'pressure_rate'], 'initial_rate_scaled')]:
            for k in columns:
                maxima[key] = max(maxima[key], abs(float(after[k])-float(before[k]))/(1+abs(float(before[k]))))
    checks = dict(centroids=maxima['centroid_absolute']<1e-12,
                  volumes=maxima['volume_relative']<1e-11,
                  faces=maxima['face_geometry_absolute']<1e-12,
                  operators=maxima['operator_relative_L1']<1e-10,
                  initial_states=maxima['initial_state_scaled']<1e-10,
                  initial_rates=maxima['initial_rate_scaled']<1e-9)
    return dict(reference=reference, repeated=repeated, maxima=maxima, checks=checks,
                passed=all(checks.values()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh analysis path')
    root = args.directory
    runs = json.loads((root/'runs.json').read_text())
    report = dict(scope='Pattern identity and geometric sensitivity; not full M1 acceptance.', cases={}, comparisons=[])
    for name, run in runs.items():
        for filename, expected in run['files_sha256'].items():
            assert hashlib.sha256((root/name/filename).read_bytes()).hexdigest() == expected, (name, filename)
        assert run.get('audit_returncode') == 0, (name, 'face audit incomplete')
        history = [{k: float(v) for k,v in r.items()} for r in rows(root/name/'history.csv')]
        assert all(math.isfinite(v) for r in history for v in r.values())
        assert all(b['time'] > a['time'] for a,b in zip(history, history[1:]))
        assert all(r['p_min'] > 0 and r['rho_min'] > 0 for r in history)
        initial_rates = rows(root/name/'initial_rates.csv')[253]
        cells = rows(root/name/'initial.csv')
        assert initial_rates['id'] == '253'
        stencil = groups(rows(root/name/'stencils.csv'))[253]
        report['cases'][name] = dict(status=run['status'], seconds=run['seconds'],
            initial=history[0], final=history[-1],
            history_p_min=min(r['p_min'] for r in history),
            history_budget_max=max(r['budget_max'] for r in history),
            target_initial_state=cells[253], target_initial_rates=initial_rates,
            target_neighbors=sorted(int(s['neighbor_base']) for s in stencil),
            target_faces=rows(root/name/'face_audit/j0.15_old_faces.csv'))
    for a,b,height in [('original','repeat2',.125), ('original','repeat4',.125),
                       ('compressed4','compressed4_repeat4',.03125)]:
        comparison = compare(root,a,b,height)
        report['comparisons'].append(comparison)
        print(a,b,comparison['passed'],comparison['maxima'])
    report['all_identity_checks_passed'] = all(c['passed'] for c in report['comparisons'])
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return 0 if report['all_identity_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
