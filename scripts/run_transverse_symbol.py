#!/usr/bin/env python3
"""Bounded REANA-only uniform-state response study for #24; no evolution/gate change."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

FIELDS = ('rho', 'vx', 'vy', 'p', 'scaled_az', 'by_curl', 'by_fv',
          'scaled_az_raw', 'p_raw', 'by_raw', 'vx_faces_x', 'vx_faces_y')
INPUTS = FIELDS[:5]
LENGTH = 0.125


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False)+'\n')


def matrices(rows):
    values = {}
    for row in rows:
        key = (row['input'], int(row['input_phase']), row['output'], int(row['output_phase']))
        if key in values or key[0] not in INPUTS or key[2] not in FIELDS or key[1] not in (0,1) or key[3] not in (0,1):
            raise ValueError('Unexpected/duplicate response coefficient')
        values[key] = float(row['derivative'])
    expected = {(a,p,b,q) for a in INPUTS for p in (0,1) for b in FIELDS for q in (0,1)}
    if set(values) != expected or not np.isfinite(list(values.values())).all():
        raise ValueError('Incomplete/nonfinite response matrix')
    result = {}
    for label, outputs in [('projected', INPUTS),
                           ('unprojected', ('rho','vx','vy','p_raw','scaled_az_raw'))]:
        matrix = np.array([[values[(a,p,b,q)] for a in INPUTS for p in (0,1)]
                           for b in outputs for q in (0,1)])
        eig = np.linalg.eigvals(matrix)
        # Each input/output basis function has volume-weighted norm L/sqrt(2).
        residual2 = sum(float(r['leakage_l2'])**2 for r in rows
                        if r['output'] in outputs and int(r['output_phase']) == 0)
        matrix_norm = float(np.linalg.norm(matrix))
        result[label] = dict(matrix=matrix.tolist(), matrix_frobenius=matrix_norm,
                             eigenvalues=[[float(e.real),float(e.imag)] for e in eig],
                             max_real_eigenvalue=float(max(eig.real)),
                             leakage_relative=(residual2**0.5)/(LENGTH/2**0.5*matrix_norm)
                             if matrix_norm else None)
    return result


def configurations():
    result = []
    for nx, waves in [(16,[1,2,4,7]), (32,[1,2,4,8,12,15]), (64,[1,2,4,8,12,16,24,31])]:
        for wave in waves:
            for transverse in (0,2):
                for epsilon in (1e-6,1e-7):
                    result.append((nx,wave,transverse,epsilon,'downstream'))
    for background in ('rest','hydro'):
        for wave in (4,16,31):
            for transverse in (0,2):
                for epsilon in (1e-6,1e-7):
                    result.append((64,wave,transverse,epsilon,background))
    return result


def main():
    if sys.platform != 'linux':
        raise ValueError('Run probes on the REANA Linux backend')
    root = Path(__file__).resolve().parents[1]
    out = root/'results/transverse_symbol'
    out.mkdir(parents=True, exist_ok=False)
    binary = root/'target/release/examples/transverse-symbol'
    report = dict(status='running', scientific_acceptance=False,
                  started_utc=datetime.now(timezone.utc).isoformat(),
                  scope='Uniform regular-mesh unlimited semidiscrete Fourier response; no shock evolution or production correction',
                  source_sha256=sha(Path(__file__)), binary_sha256=sha(binary),
                  numpy=np.__version__, geometry=dict(lengths=[LENGTH,LENGTH],ny=4),
                  config=dict(profile='bulk-frame-heun-quadratic-v1',screening=1,
                              accelerated=True,limited=False,gamma=2,threads_per_case=1),
                  backgrounds={
                      'downstream':dict(rho=.235,p=.512,velocity=[.592,-1.579,0],mean_B=[.75,-.535,0],scope='rounded manufactured positive state, not an exact Brio reference'),
                      'rest':dict(rho=.235,p=.512,velocity=[0,0,0],mean_B=[.75,-.535,0]),
                      'hydro':dict(rho=1,p=1,velocity=[.592,-1.579,0],mean_B=[0,0,0])},
                  runs={}, amplitude_comparisons=[],max_workers=8)
    env = dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',RAYON_NUM_THREADS='1')
    def run(config):
        nx,wave,transverse,epsilon,background = config
        name = f'{background}_n{nx}_kx{wave}_ky{transverse}_e{epsilon:g}'
        path = out/(name+'.csv')
        command = [str(binary),*map(str,config)]
        row = dict(status='running',configuration=list(config),command=command,timeout_seconds=120)
        start = time.monotonic()
        try:
            with path.open('w') as stream, (out/(name+'.log')).open('w') as log:
                done = subprocess.run(command,env=env,cwd=root,stdout=stream,stderr=log,timeout=120)
            if done.returncode:
                raise ValueError('Probe failed with code '+str(done.returncode))
            with path.open() as stream:
                data = list(csv.DictReader(stream))
            for r in data:
                if [int(r['nx']),int(r['x_mode']),int(r['y_mode']),float(r['epsilon']),r['background']] != list(config):
                    raise ValueError('Configuration mismatch')
            response = matrices(data)
            row.update(status='completed',responses=response,sha256=sha(path),
                       reference_rate_max=max(float(r['reference_rate_max']) for r in data))
        except Exception as error:
            row.update(status='failed',error=f'{type(error).__name__}: {error}')
        row['seconds']=time.monotonic()-start
        return name,row
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            for future in as_completed([pool.submit(run,c) for c in configurations()]):
                name,row = future.result();report['runs'][name]=row
                dump(out/'report.json',report)
                print(name,row['status'],f"{row['seconds']:.3f}s",flush=True)
        if len(report['runs']) != len(configurations()) or any(r['status']!='completed' for r in report['runs'].values()):
            raise ValueError('Incomplete/failed probe matrix')
        for name,run in sorted(report['runs'].items()):
            if run['configuration'][3] != 1e-6:continue
            small = report['runs'][name.replace('_e1e-06','_e1e-07')]
            comparisons={}
            for label in ('projected','unprojected'):
                a=np.array(run['responses'][label]['matrix']);b=np.array(small['responses'][label]['matrix'])
                comparisons[label]=dict(relative_matrix_difference=float(np.linalg.norm(a-b)/max(np.linalg.norm(a),1e-300)),
                    max_real_difference=abs(run['responses'][label]['max_real_eigenvalue']-small['responses'][label]['max_real_eigenvalue']))
            report['amplitude_comparisons'].append(dict(name=name,comparisons=comparisons))
        report['status']='completed'
    except Exception as error:
        report.update(status='failed',error=f'{type(error).__name__}: {error}')
    finally:
        report['ended_utc']=datetime.now(timezone.utc).isoformat();dump(out/'report.json',report)
        dump(out/'sha256.json',{p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()})
    return 0 if report['status']=='completed' else 1


if __name__=='__main__':
    raise SystemExit(main())
