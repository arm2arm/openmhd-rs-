"""Independently integrate rectangular vortex cells into the M0 bins; no evolution."""
import argparse
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import shutil

import numpy as np


def sha(data):
    return hashlib.sha256(data).hexdigest()


def axis_overlaps(lo, hi, shift, bins):
    """Lengths in periodic bins, using interval intersections only."""
    lo -= shift
    hi -= shift
    if not 0 < hi-lo < 1:
        raise ValueError('Invalid cell width')
    result = []
    for image in range(-math.floor(hi), -math.floor(lo)+1):
        left, right = max(0., lo+image), min(1., hi+image)
        if right <= left:
            continue
        for index in range(max(0, math.floor(left*bins)),
                           min(bins-1, math.floor(right*bins))+1):
            length = min(right, (index+1)/bins)-max(left, index/bins)
            if length > 0:
                result.append((index, length))
    if abs(math.fsum(length for _, length in result)/(hi-lo)-1) > 2e-11:
        raise ValueError('Periodic interval lost length')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    raw, out = args.raw, args.output
    if out.exists():
        raise ValueError('Use a fresh output directory')
    run_path = raw/'runs.json'
    run_bytes = (run_path.read_bytes() if run_path.exists() else
                 gzip.decompress((raw/'runs_checkpoint.json.gz').read_bytes()))
    runs = json.loads(run_bytes)
    provenance_path = raw/'provenance.json'
    if not provenance_path.exists():
        provenance_path = raw/'provenance_checkpoint.json'
    provenance = json.loads(provenance_path.read_text())
    repo = Path.cwd()
    reference_path = repo/'tests/reference/external_mhd/vortex_512.csv.gz'
    reference_bytes = reference_path.read_bytes()
    pinned = json.loads((reference_path.parent/'provenance.json').read_text())
    assert sha(reference_bytes) == pinned['result_sha256'][reference_path.name]
    assert sha(reference_bytes) == provenance['reference_sha256'][reference_path.name]
    packet_path = repo/'benchmarks/m0/packet.json'
    assert sha(packet_path.read_bytes()) == provenance['source_sha256']['benchmarks/m0/packet.json']
    reference = np.genfromtxt(io.BytesIO(gzip.decompress(reference_bytes)), names=True, delimiter=',')
    bins = 64
    assert len(reference) == bins*bins
    assert np.array_equal(reference['x'], (np.arange(bins*bins) % bins+.5)/bins)
    assert np.array_equal(reference['y'], (np.arange(bins*bins) // bins+.5)/bins)
    fields = ('rho', 'p', 'bx', 'by')
    scales = dict(rho=25/(36*math.pi), p=5/(12*math.pi),
                  bx=1/math.sqrt(4*math.pi), by=1/math.sqrt(4*math.pi))
    expected = [f'orszag-tang_n{n}_j0.0_{frame}'
                for n in (64, 128, 256) for frame in ('base', 'boost')]
    retained, inputs, measured, projected = {}, {}, {}, {}
    for name in expected:
        if name not in runs:
            continue
        run = runs[name]
        assert run['status'] == 'completed', (name, run['status'])
        config = run['config']
        assert config['case'] == 'orszag-tang' and config['jitter'] == 0.
        assert config['time'] == .5 and config['ny'] == config['n']
        assert config['riemann_solver'] == 'hlld-pressure'
        assert config['profile'] == 'bulk-frame-heun-quadratic-v1'
        assert run['summary']['projection_screening'] == 1.
        frame = name.rsplit('_', 1)[1]
        assert config['boost'] == ([0., 0., 0.] if frame == 'base' else [2., -1., 0.])
        loaded = {}
        for filename in ('final.csv', 'geometry.json', 'projected_bins.json'):
            path = raw/name/filename
            data = (path.read_bytes() if path.exists() else
                    gzip.decompress((raw/'snapshots'/name/(filename+'.gz')).read_bytes()))
            assert sha(data) == run['sha256'][filename]
            inputs[name+'/'+filename] = sha(data)
            retained[name+'/'+filename] = data
            loaded[filename] = data
        cells = np.genfromtxt(io.BytesIO(loaded['final.csv']), names=True, delimiter=',')
        geometry = json.loads(loaded['geometry.json'])
        assert geometry['lengths'] == [1., 1.] and geometry['time'] == .5
        assert len(cells) == len(geometry['cells']) == config['n']**2
        assert np.array_equal(cells['id'], np.arange(len(cells)))
        assert (cells['time'] == .5).all() and (cells['volume'] > 0).all()
        assert all(np.isfinite(cells[key]).all() for key in cells.dtype.names)
        assert abs(math.fsum(cells['volume'])-1) < 2e-11
        volumes = [[] for _ in range(bins*bins)]
        weighted = {field: [[] for _ in range(bins*bins)] for field in fields}
        maximum_area_error = 0.
        shift = [value*.5 for value in config['boost'][:2]]
        for cell, record in zip(cells, geometry['cells']):
            assert record['id'] == int(cell['id'])
            assert abs(record['volume']/cell['volume']-1) < 2e-11
            assert all(abs((record['centroid'][k]-cell[field]+.5) % 1-.5) < 2e-11
                       for k, field in enumerate(('x', 'y')))
            bounds = {}
            # Recover rectangles directly from raw face planes. Do not import
            # the production polygon clipper or use its saved vertices.
            for nx, ny, fx, fy in record['planes']:
                if (nx, ny) == (1., 0.): key, value = 'right', fx
                elif (nx, ny) == (-1., 0.): key, value = 'left', fx
                elif (nx, ny) == (0., 1.): key, value = 'top', fy
                elif (nx, ny) == (0., -1.): key, value = 'bottom', fy
                else: raise ValueError('Nonrectangular primary cell')
                assert key not in bounds and math.isfinite(value)
                bounds[key] = value
            assert len(bounds) == 4
            area = (bounds['right']-bounds['left'])*(bounds['top']-bounds['bottom'])
            error = abs(area/cell['volume']-1)
            assert error < 2e-11
            maximum_area_error = max(maximum_area_error, error)
            xx = axis_overlaps(bounds['left'], bounds['right'], shift[0], bins)
            yy = axis_overlaps(bounds['bottom'], bounds['top'], shift[1], bins)
            for x, width in xx:
                for y, height in yy:
                    index, area = x+bins*y, width*height
                    volumes[index].append(area)
                    for field in fields:
                        weighted[field][index].append(area*float(cell[field]))
        areas = np.array([math.fsum(parts) for parts in volumes])
        coverage_error = float(max(abs(areas*bins*bins-1)))
        assert coverage_error < 2e-11
        values = {field: np.array([math.fsum(parts) for parts in weighted[field]])/areas
                  for field in fields}
        production = json.loads(loaded['projected_bins.json'])
        assert len(production) == bins*bins
        bin_difference = max(float(max(abs(values[field]-np.array([row[field] for row in production]))))
                             for field in fields)
        assert bin_difference < 2e-11
        errors = {}
        for field in fields:
            delta = (values[field]-reference[field])/scales[field]
            errors[field] = dict(L1=math.fsum(abs(x) for x in delta)/len(delta),
                                 L2=math.sqrt(math.fsum(x*x for x in delta)/len(delta)))
        norm_difference = max(abs(errors[field][norm]-run['reference_errors'][field][norm])
                              for field in fields for norm in ('L1', 'L2'))
        assert norm_difference < 2e-11
        measured[name] = dict(resolution=config['n'], frame=frame, reference_errors=errors,
                              maximum_rectangle_area_relative_error=maximum_area_error,
                              maximum_bin_coverage_relative_error=coverage_error,
                              maximum_production_bin_difference=bin_difference,
                              maximum_production_norm_difference=norm_difference)
        projected[name] = {field: values[field].tolist() for field in fields}
    assert measured, 'No completed regular vortex records'
    limits = json.loads(packet_path.read_text())['cases']['orszag-tang']['gate']['finest_scaled_bin_L1_max']
    ladders = []
    for frame in ('base', 'boost'):
        rows = sorted([row for row in measured.values() if row['frame'] == frame], key=lambda row: row['resolution'])
        complete = [row['resolution'] for row in rows] == [64, 128, 256]
        checks = ({field: rows[-1]['reference_errors'][field]['L1'] <= limit
                   and rows[-1]['reference_errors'][field]['L1'] < rows[0]['reference_errors'][field]['L1']
                   for field, limit in limits.items()} if complete else None)
        ladders.append(dict(frame=frame, complete=complete, checks=checks,
                            status=('pass' if all(checks.values()) else 'fail') if complete else 'pending'))
    out.mkdir(parents=True)
    (out/'runs_checkpoint.json.gz').write_bytes(gzip.compress(run_bytes, mtime=0))
    shutil.copyfile(provenance_path, out/'provenance_checkpoint.json')
    shutil.copyfile(__file__, out/'reduce_reference.py')
    for name, data in retained.items():
        path = out/'snapshots'/(name+'.gz')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(gzip.compress(data, mtime=0))
    (out/'independent_bins.json.gz').write_bytes(gzip.compress(json.dumps(projected).encode(), mtime=0))
    report = dict(scope='Independent raw-face rectangle/64-bin intersections and reference norms. No production polygon or error code is imported. Only completed regular-mesh cases are reduced; partial ladders remain pending, not passed. No evolution or full M1 acceptance.',
                  reference_sha256=sha(reference_bytes), packet_sha256=sha(packet_path.read_bytes()),
                  run_map_sha256=sha(run_bytes), input_sha256=inputs, measured=measured,
                  primary_reference_ladders=ladders,
                  missing_primary_cases=[name for name in expected if name not in measured],
                  numpy=np.__version__, analysis_source_sha256=sha((out/'reduce_reference.py').read_bytes()))
    (out/'independent_reference.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Reduced', len(measured), 'primary vortex cases. Ladders:',
          [row['status'] for row in ladders], 'Maximum norm discrepancy:',
          max(row['maximum_production_norm_difference'] for row in measured.values()))


if __name__ == '__main__':
    main()
