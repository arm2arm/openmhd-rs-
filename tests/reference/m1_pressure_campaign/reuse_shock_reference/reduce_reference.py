"""Independent rectangular-cell Athena reference integrals; no evolution."""
from pathlib import Path
from decimal import Decimal, localcontext
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import shutil
import numpy as np


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    repo = Path.cwd()
    raw = args.raw
    out = args.output
    if out.exists():
        raise ValueError('Use a fresh archive directory')
    run_bytes = ((raw/'runs.json').read_bytes() if (raw/'runs.json').exists()
                 else gzip.decompress((raw/'runs_checkpoint.json.gz').read_bytes()))
    runs = json.loads(run_bytes)
    provenance_path = raw/'provenance.json'
    if not provenance_path.exists():
        provenance_path = raw/'provenance_checkpoint.json'
    provenance = json.loads(provenance_path.read_text())
    reference = repo/'tests/reference/external_mhd/brio_8192.csv.gz'
    pinned = json.loads((reference.parent/'provenance.json').read_text())
    assert digest(reference) == pinned['result_sha256'][reference.name]
    assert digest(reference) == provenance['reference_sha256'][reference.name]
    assert digest(repo/'benchmarks/m0/packet.json') == provenance['source_sha256']['benchmarks/m0/packet.json']
    ref = list(csv.DictReader(io.StringIO(gzip.decompress(reference.read_bytes()).decode())))
    count = len(ref)
    assert count == 8192
    assert all(float(row['x']) == .5+(i+.5)/count for i, row in enumerate(ref))
    fields = ('rho', 'p', 'vx', 'by')
    measured = {}
    inputs = {}
    retained = {}
    with localcontext() as context:
        context.prec = 50
        values = {field: [Decimal(row[field]) for row in ref] for field in fields}
        prefixes = {}
        for field in fields:
            prefix = [Decimal(0)]
            for value in values[field]:
                prefix.append(prefix[-1]+value)
            prefixes[field] = prefix

        def primitive(field, x):
            coordinate = (Decimal.from_float(x)-Decimal('.5'))*count
            assert 0 <= coordinate <= count
            index = int(coordinate)
            if index == count:
                return prefixes[field][-1]/count
            return (prefixes[field][index]
                    +(coordinate-index)*values[field][index])/count

        for family, jitter, mode in (('regular', 0., 'planar'), ('columns', .15, 'columns')):
            for resolution in (256, 512, 1024):
                for frame in ('base', 'boost'):
                    name = f'brio-wu_n{resolution}_j{jitter}'+('c' if mode == 'columns' else '')+'_'+frame
                    run = runs[name]
                    config = run['config']
                    assert run['status'] == 'completed'
                    assert config['case'] == 'brio-wu' and config['ny'] == 4
                    assert config['n'] == resolution and config['jitter'] == jitter
                    assert config['jitter_mode'] == mode and config['time'] == .1
                    assert config['riemann_solver'] == 'hlld-pressure'
                    assert config['profile'] == 'bulk-frame-heun-quadratic-v1'
                    assert run['summary']['projection_screening'] == 1.
                    for filename in ('final.csv', 'geometry.json'):
                        path = raw/name/filename
                        data_bytes = (path.read_bytes() if path.exists() else
                                      gzip.decompress((raw/'snapshots'/name/(filename+'.gz')).read_bytes()))
                        checksum = hashlib.sha256(data_bytes).hexdigest()
                        assert checksum == run['sha256'][filename]
                        inputs[name+'/'+filename] = checksum
                        retained[name+'/'+filename] = data_bytes
                    data = np.genfromtxt(io.BytesIO(retained[name+'/final.csv']), names=True, delimiter=',')
                    geometry = json.loads(retained[name+'/geometry.json'])
                    assert geometry['lengths'] == [2., .125] and geometry['time'] == .1
                    assert len(geometry['cells']) == len(data) == resolution*4
                    assert np.array_equal(data['id'], np.arange(len(data)))
                    assert all(np.isfinite(data[key]).all() for key in data.dtype.names)
                    assert (data['time'] == .1).all() and (data['volume'] > 0).all()
                    sums = {field: [] for field in fields}
                    squares = {field: [] for field in fields}
                    weights = []
                    max_rectangle_error = 0.
                    for cell, record in zip(data, geometry['cells']):
                        bounds = {}
                        assert record['id'] == int(cell['id'])
                        # Use the raw oriented face planes, not the production
                        # clipped polygons or their stored vertices.
                        for nx, ny, fx, fy in record['planes']:
                            if (nx, ny) == (1., 0.): key, value = 'right', fx
                            elif (nx, ny) == (-1., 0.): key, value = 'left', fx
                            elif (nx, ny) == (0., 1.): key, value = 'top', fy
                            elif (nx, ny) == (0., -1.): key, value = 'bottom', fy
                            else: raise ValueError('Nonrectangular primary cell')
                            assert key not in bounds
                            bounds[key] = value
                        assert len(bounds) == 4
                        height = bounds['top']-bounds['bottom']
                        width = bounds['right']-bounds['left']
                        assert height > 0 and width > 0
                        rectangle_error = abs(height*width/cell['volume']-1)
                        max_rectangle_error = max(max_rectangle_error, rectangle_error)
                        assert rectangle_error < 2e-11
                        shift = config['boost'][0]*config['time']
                        left, right = bounds['left']-shift, bounds['right']-shift
                        for image in (-2., 0., 2.):
                            a, b = max(.5, left+image), min(1.5, right+image)
                            if b <= a:
                                continue
                            weight = (b-a)*height
                            weights.append(weight)
                            for field in fields:
                                average = float((primitive(field, b)-primitive(field, a))
                                                /(Decimal.from_float(b)-Decimal.from_float(a)))
                                actual = cell[field]-(config['boost'][0] if field == 'vx' else 0.)
                                difference = actual-average
                                sums[field].append(weight*abs(difference))
                                squares[field].append(weight*difference*difference)
                    total = math.fsum(weights)
                    assert abs(total/.125-1) < 2e-11
                    errors = {field: dict(L1=math.fsum(sums[field])/total,
                                          L2=math.sqrt(math.fsum(squares[field])/total)) for field in fields}
                    discrepancy = max(abs(errors[field][norm]-run['reference_errors'][field][norm])
                                      for field in fields for norm in ('L1', 'L2'))
                    assert discrepancy < 2e-11, (name, discrepancy)
                    measured[name] = dict(family=family, resolution=resolution, frame=frame,
                                          reference_errors=errors, production_discrepancy=discrepancy,
                                          rectangle_volume_relative_error=max_rectangle_error,
                                          analysis_volume=total,
                                          final_Bx_max_error=float(max(abs(data['bx']-.75))))
    packet = json.loads((repo/'benchmarks/m0/packet.json').read_text())
    limits = packet['cases']['brio-wu']['gate']['finest_scaled_L1_max']
    gates = []
    for family in ('regular', 'columns'):
        for frame in ('base', 'boost'):
            ladder = sorted([row for row in measured.values()
                             if row['family'] == family and row['frame'] == frame], key=lambda row: row['resolution'])
            assert [row['resolution'] for row in ladder] == [256, 512, 1024]
            checks = {field: ladder[-1]['reference_errors'][field]['L1'] <= limit
                      and ladder[-1]['reference_errors'][field]['L1'] < ladder[0]['reference_errors'][field]['L1']
                      for field, limit in limits.items()}
            assert all(checks.values())
            gates.append(dict(family=family, frame=frame, checks=checks))
    out.mkdir(parents=True)
    (out/'runs_checkpoint.json.gz').write_bytes(gzip.compress(run_bytes, mtime=0))
    shutil.copyfile(provenance_path, out/'provenance_checkpoint.json')
    for name, data in retained.items():
        destination = out/'snapshots'/(name+'.gz')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(gzip.compress(data, mtime=0))
    shutil.copyfile(__file__, out/'reduce_reference.py')
    report = dict(scope='Independent 50-digit decimal prefix integrals of the pinned Athena samples over rectangular primary shock cells. No production polygon clipping or error routine is imported. This is a completed shock-reference subset; full physics and M1 remain pending.',
                  reference_sha256=digest(reference), packet_sha256=digest(repo/'benchmarks/m0/packet.json'),
                  run_map_sha256=hashlib.sha256(run_bytes).hexdigest(), input_sha256=inputs,
                  measured=measured, reference_gates=gates, all_reference_gates_passed=True,
                  decimal_precision=50, numpy=np.__version__, analysis_source_sha256=digest(out/'reduce_reference.py'))
    (out/'independent_reference.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Verified', len(measured), 'primary shock cases and', len(gates), 'reference ladders; maximum norm discrepancy',
          max(row['production_discrepancy'] for row in measured.values()))


if __name__ == '__main__':
    main()
