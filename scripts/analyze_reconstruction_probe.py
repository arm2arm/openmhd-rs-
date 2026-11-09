#!/usr/bin/env python3
"""Independent kink-residual and frozen-rate checks; never accepts a solver."""
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


def kink(records):
    # In these three cells the local affine branch is Az=x-2. Periodic
    # neighbors beyond x=2 sample the opposite branch, creating a residual.
    residual = [float(r['neighbor_Az'])-(float(r['cx'])+float(r['dx'])-2.) for r in records]
    correction = [math.fsum(float(r[k])*(a-residual[0]) for r,a in zip(records,residual))
                  for k in ['weight_x','weight_y']]
    predicted = [.75+correction[1], -1.-correction[0]]
    actual = [float(records[0]['bx']),float(records[0]['by'])]
    # Independent free-intercept weighted normal equations, without using
    # the exported derivative coefficients.
    total = math.fsum(float(r['area']) for r in records)
    data = [(float(r['dx']),float(r['dy']),float(r['neighbor_Az']),float(r['area'])/total) for r in records]
    means = [math.fsum(row[k]*row[3] for row in data) for k in range(3)]
    xx,xy,yy = [math.fsum(w*(row[a]-means[a])*(row[b]-means[b]) for row in data for w in [row[3]])
                for a,b in [(0,0),(0,1),(1,1)]]
    ax,ay = [math.fsum(w*(row[k]-means[k])*(row[2]-means[2]) for row in data for w in [row[3]]) for k in [0,1]]
    det = xx*yy-xy*xy
    assert det>0
    independent = [.75+(xx*ay-xy*ax)/det, -(yy*ax-xy*ay)/det]
    assert max(abs(a-b) for a,b in zip(predicted,actual))<1e-11
    assert max(abs(a-b) for a,b in zip(independent,actual))<1e-11
    samples = [dict(neighbor=int(r['neighbor']), unwrapped_x=float(r['cx'])+float(r['dx']),
                    kink_residual=a, delta_Bx=float(r['weight_y'])*(a-residual[0]),
                    delta_By=-float(r['weight_x'])*(a-residual[0])) for r,a in zip(records,residual)]
    return dict(magnetic=actual,kink_reconstruction=predicted,independent_fit=independent,
                error=max(abs(a-b) for a,b in zip(predicted,actual)),samples=samples)


def analyze(root):
    provenance = json.loads((root/'provenance.json').read_text())
    assert provenance['completed'] and provenance['unchanged'] and not provenance['evolved']
    for name,digest in provenance['files_sha256'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest, name
    data=root/'data'
    rates=rows(data/'rates.csv')
    assert len(rates)==80 and len({(r['height'],r['jitter'],r['variant'],r['stage']) for r in rates})==80
    max_rate_error=0.
    for row in rates:
        for key in ['total_rate','magnetic_rate','pressure_rate','minimum_pressure_rate','budget_residual']:
            assert math.isfinite(float(row[key]))
        prefix=f'h{row["height"]}_j{row["jitter"]}_{row["variant"]}_{row["stage"]}'
        cells=rows(data/(prefix+'_cells.csv'))
        assert len(cells)==1024
        target=cells[253]
        for key in ['total_rate','magnetic_rate','pressure_rate']:
            assert float(target[key])==float(row[key])
        assert float(row['minimum_pressure_rate'])==min(float(c['pressure_rate']) for c in cells)
        for c in cells:
            error=abs(float(c['total_rate'])-float(c['magnetic_rate'])-float(c['pressure_rate']))
            max_rate_error=max(max_rate_error,error)
            assert error<1e-11
        assert float(row['budget_residual'])<1e-13
    decomposition={}
    for path in sorted(data.glob('*_kink_samples.csv')):
        grouped=defaultdict(list)
        for row in rows(path):grouped[int(row['id'])].append(row)
        assert set(grouped)=={253,254,255}
        decomposition[path.stem]={i:kink(samples) for i,samples in grouped.items()}
    assert len(decomposition)==4
    return dict(scope='Frozen diagnostic substitutions, no consistent evolved state or M1 acceptance.',
                cases=rates,kink_decomposition=decomposition,maximum_pressure_rate_identity_error=max_rate_error,
                all_checks_passed=True,seconds=provenance['seconds'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Use a fresh analysis path')
    report=analyze(args.directory)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print('80 frozen rates, 12 kink decompositions and archive hashes verified.')


if __name__=='__main__':main()
