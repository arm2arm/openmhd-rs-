#!/usr/bin/env python3
"""Read-only, independent Fourier/time-step analysis of existing wave snapshots."""
import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reduce(raw):
    runs = json.loads(gzip.decompress((HERE/'runs.json.gz').read_bytes()))
    hashes = {}
    def read(name, n):
        path = raw/name/'final.csv'
        record = runs[name]
        digest = sha(path)
        assert digest == record['sha256']['final.csv']
        assert record['status'] == 'completed' and record['positive_and_conservative']
        c = record['config']
        assert c['profile'] == 'bulk-frame-heun-quadratic-v1' and c['riemann_solver'] == 'hlld-pressure'
        assert c['n'] == n and c['target'] == 1. and c['parallel'] == 1. and c['motion_family'] == 'fixed'
        assert c['boost'] == [0., 0., 0.] and record['summary']['projection_screening'] == 1.
        with path.open() as stream:
            cells = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(stream)]
        assert len(cells) == n*n
        assert all(c['id'] == i and c['time'] == 1. and c['volume'] > 0
                   and c['rho'] > 0 and c['p'] > 0 and all(math.isfinite(v) for v in c.values()) for i, c in enumerate(cells))
        assert abs(math.fsum(c['volume'] for c in cells)-1.) < 1e-10
        hashes[name] = digest
        return cells, record
    temporal = []
    for jitter in (0., .15):
        data = {dt: read(f'temporal_bulk-frame-heun-quadratic-v1_v1.0_j{jitter}_dt{dt}', 64)
                for dt in (.0004, .0002, .0001, .000025)}
        ref = data[.000025][0]
        rows = []
        for dt, (cells, record) in data.items():
            assert max(max(abs(c[k]-b[k]) for k in ('x', 'y', 'volume')) for c, b in zip(cells, ref)) < 1e-14
            error = math.fsum(c['volume']*math.sqrt((c['bx']-1.)**2 + (c['by']-.1*math.sin(math.tau*c['x']))**2
                                                   + (c['bz']-.1*math.cos(math.tau*c['x']))**2) for c in cells)
            assert abs(error-record['errors']['final']['B']['L1']) < 2e-13
            differences = {label: math.fsum(b['volume']*math.sqrt(math.fsum((c[k]-b[k])**2 for k in fields))
                                           for c, b in zip(cells, ref))
                           for label, fields in [('B', ('bx', 'by', 'bz')), ('A', ('ax', 'ay', 'az')), ('phi', ('phi',))]}
            rows.append(dict(dt_cap=dt, dt_max_actual=record['summary']['dt_max'], analytic_B_L1=error,
                             L1_difference_from_finest_dt=differences, temporal_to_spatial_error_ratio=differences['B']/error))
        temporal.append(dict(jitter=jitter, rows=rows))
    modes = []
    for n in (32, 64, 128, 256):
        cells, record = read(f'alfven_bulk-frame-heun-quadratic-v1_v1.0_j0.0_fixed_n{n}_base', n)
        coefficient = {field: [[2*math.fsum(c['volume']*c[field]*f(math.tau*m*c['x']) for c in cells)
                               for f in (math.sin, math.cos)] for m in range(1, 10)]
                       for field in ('by', 'bz', 'vy', 'vz')}
        def residual(c, field):
            sine, cosine = coefficient[field][0]
            return c[field]-sine*math.sin(math.tau*c['x'])-cosine*math.cos(math.tau*c['x'])
        remaining = math.fsum(c['volume']*math.hypot(residual(c, 'by'), residual(c, 'bz')) for c in cells)
        modes.append(dict(n=n, coefficients_sine_cosine=coefficient,
                          residual_transverse_B_L1_without_fundamental=remaining,
                          rms_transverse_v_minus_B=math.sqrt(math.fsum(c['volume']*((c['vy']-c['by'])**2
                                                                  +(c['vz']-c['bz'])**2) for c in cells))))
    order = math.log(modes[1]['residual_transverse_B_L1_without_fundamental']
                    /modes[3]['residual_transverse_B_L1_without_fundamental'])/math.log(4.)
    return dict(scope='Independent postprocessing only; no numerical evolution, changed gate or established root cause.',
                script_sha256=sha(Path(__file__)), run_map_sha256=sha(HERE/'runs.json.gz'), raw_final_sha256=hashes,
                temporal=temporal, regular_fixed_standing_modes=modes, residual_finest_three_order=order,
                full_m1_accepted=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw_wave_directory', type=Path)
    parser.add_argument('output_json', type=Path)
    args = parser.parse_args()
    args.output_json.write_text(json.dumps(reduce(args.raw_wave_directory), indent=2, allow_nan=False)+'\n')
