#!/usr/bin/env python3
"""Independent NumPy weighted least squares and incidence audit of the CT probe."""
import argparse
import csv
from pathlib import Path
import numpy as np
from run_m1_wave_loop import dump


def audit(path):
    result = {}
    for stage in ['initial', 'last']:
        with (path/(stage+'_cells.csv')).open() as stream:
            cells = [{k: float(v) for k,v in r.items()} for r in csv.DictReader(stream)]
        with (path/(stage+'_faces.csv')).open() as stream:
            faces = [{k: float(v) for k,v in r.items()} for r in csv.DictReader(stream)]
        stencils = [[] for _ in cells]
        incidence = [{} for _ in cells]
        div = np.zeros(len(cells))
        for f in faces:
            for side, sign in [('left',1),('right',-1)]:
                i=int(f[side]);prefix='dl' if side=='left' else 'dr'
                d=np.hypot(f[prefix+'x'],f[prefix+'y'])
                stencils[i].append(([f['nx']/d,f['ny']/d],f['flux']/f['length']/d))
                div[i]+=sign*f['flux']
                for key,orientation in [('minus',-1),('plus',1)]:
                    v=int(f[key]);incidence[i][v]=incidence[i].get(v,0)+sign*orientation
        if any(any(row.values()) for row in incidence):
            raise ValueError('non-telescoping integer cell boundary')
        error=0.
        for c,row in zip(cells,stencils):
            matrix,values=zip(*row)
            b=np.linalg.lstsq(matrix,values,rcond=None)[0]
            error=max(error,abs(b[0]-c['bx']),abs(b[1]-c['by']))
        if error>1e-11:
            raise ValueError('independent recovery mismatch')
        worst=min(cells,key=lambda c:c['p'])
        result[stage]=dict(recovery_max_error=error,integer_incidence_exact=True,
            div_ct_max=max(abs(d/c['volume']) for d,c in zip(div,cells)),
            minimum_pressure_cell=worst,cell253=cells[253])
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory',type=Path)
    args=p.parse_args()
    result=audit(args.directory)
    dump(args.directory/'independent_check.json',result)
    print(result)
