#!/usr/bin/env python3
"""Read-only localisation of the non-fundamental Alfven error in existing snapshots.

No evolution is launched and no production error routine is imported. Raw
final CSVs are checked against the retained 104-case run map before use.
"""
import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN_MAP = HERE.parent/'m1_pressure_campaign/standing_diagnosis/runs.json.gz'
WINDOW = 1/16  # half-width around each of the two reference positions


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def distance(x, centres):
    return min(abs((x-c+.5) % 1-.5) for c in centres)


def reduce(raw):
    runs = json.loads(gzip.decompress(RUN_MAP.read_bytes()))
    hashes = {}
    families = []
    for label, parallel in (('standing', 1.), ('travelling', 0.)):
        rows = []
        for n in (32, 64, 128, 256):
            name = f'alfven_bulk-frame-heun-quadratic-v1_v{parallel}_j0.0_fixed_n{n}_base'
            record = runs[name]
            path = raw/name/'final.csv'
            digest = sha(path)
            assert digest == record['sha256']['final.csv'], name
            c = record['config']
            assert record['status'] == 'completed' and record['positive_and_conservative']
            assert c['profile'] == 'bulk-frame-heun-quadratic-v1' and c['riemann_solver'] == 'hlld-pressure'
            assert c['n'] == n and c['target'] == 1. and c['parallel'] == parallel and c['jitter'] == 0.
            assert c['motion_family'] == 'fixed' and c['boost'] == [0., 0., 0.] and c['mesh_velocity'] == [0., 0.]
            assert record['summary']['projection_screening'] == 1. and record['summary']['limited'] is True
            with path.open() as stream:
                cells = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(stream)]
            assert len(cells) == n*n
            assert all(q['id'] == i and q['time'] == 1. and q['volume'] > 0 and q['rho'] > 0 and q['p'] > 0
                       and all(math.isfinite(v) for v in q.values()) for i, q in enumerate(cells))
            assert abs(math.fsum(q['volume'] for q in cells)-1.) < 1e-10
            hashes[name] = digest
            # At t=1 both families have the analytic phase 2 pi x (one full period).
            fields = {}
            for field, analytic, own_extrema, potential_extrema in (
                    ('by', math.sin, (.25, .75), (0., .5)),   # By=-dAz/dx: Az extrema at By zeros
                    ('bz', math.cos, (0., .5), (.25, .75))):  # Bz=+dAy/dx: Ay extrema at Bz zeros
                amplitudes = []
                fundamental = None
                for m in range(1, 10):
                    sine = 2*math.fsum(q['volume']*q[field]*math.sin(math.tau*m*q['x']) for q in cells)
                    cosine = 2*math.fsum(q['volume']*q[field]*math.cos(math.tau*m*q['x']) for q in cells)
                    if m == 1:
                        fundamental = (sine, cosine)
                        exact = (.1, 0.) if analytic is math.sin else (0., .1)
                        amplitudes.append(math.hypot(sine-exact[0], cosine-exact[1]))
                    else:
                        amplitudes.append(math.hypot(sine, cosine))
                mean = math.fsum(q['volume']*q[field] for q in cells)
                residual = [q[field]-mean-fundamental[0]*math.sin(math.tau*q['x'])
                            - fundamental[1]*math.cos(math.tau*q['x']) for q in cells]
                total = math.fsum(q['volume']*abs(r) for q, r in zip(cells, residual))
                near = {key: math.fsum(q['volume']*abs(r) for q, r in zip(cells, residual)
                                       if distance(q['x'], centres) <= WINDOW)/total
                        for key, centres in (('field_extrema', own_extrema), ('potential_extrema', potential_extrema))}
                peak = max(range(len(cells)), key=lambda i: abs(residual[i]))
                fields[field] = dict(error_harmonic_amplitudes_m1_to_m9=amplitudes,
                                     residual_L1_without_mean_and_fundamental=total,
                                     residual_max=abs(residual[peak]), residual_peak_x=cells[peak]['x'],
                                     residual_L1_fraction_within_one_sixteenth=near)
            rows.append(dict(n=n, B_L1=record['errors']['final']['B']['L1'], fields=fields))
        def order(values):
            return math.log(values[1]/values[3])/math.log(4.)
        families.append(dict(
            family=label, parallel_velocity=parallel, rows=rows,
            finest_three_two_point_orders=dict(
                B_L1=order([r['B_L1'] for r in rows]),
                **{f'{field}_{key}': order([r['fields'][field][source] if index is None
                                            else r['fields'][field][source][index] for r in rows])
                   for field in ('by', 'bz')
                   for key, source, index in (('fundamental_error', 'error_harmonic_amplitudes_m1_to_m9', 0),
                                              ('residual_L1', 'residual_L1_without_mean_and_fundamental', None))})))
    return dict(scope='Independent postprocessing of existing outputs; no evolution, changed gate or established cause.',
                window_half_width=WINDOW,
                uniform_reference_fraction=4*WINDOW,
                order_definition='log(value(N64)/value(N256))/log(4); a two-point slope, not the registered fit',
                script_sha256=sha(Path(__file__)), run_map_sha256=sha(RUN_MAP), raw_final_sha256=hashes,
                families=families, full_m1_accepted=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw_wave_directory', type=Path)
    parser.add_argument('output_json', type=Path)
    args = parser.parse_args()
    args.output_json.write_text(json.dumps(reduce(args.raw_wave_directory), indent=2, allow_nan=False)+'\n')
