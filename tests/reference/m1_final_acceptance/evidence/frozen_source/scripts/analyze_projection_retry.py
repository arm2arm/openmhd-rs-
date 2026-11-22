#!/usr/bin/env python3
"""Reverify the bounded projection retry, preserving failures and capped runs."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import tarfile
from run_m1_wave_loop import read_cells
from run_projected_controls import analyze

STUDIES = ('positive_primary','positive_extended','projected_refinement','controls','accelerated','baseline')


def load(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def histories(path):
    with path.open() as stream:
        rows = list(csv.DictReader(stream))
    complete = []
    for i, row in enumerate(rows):
        if any(v is None or v == '' for v in row.values()):
            if i != len(rows)-1:
                raise ValueError('Truncated nonfinal diagnostic row')
            break  # a killed process can leave an incomplete final CSV line
        parsed = {k: float(v) for k,v in row.items()}
        if any(not math.isfinite(v) for v in parsed.values()):
            raise ValueError('Nonfinite diagnostic history')
        complete.append(parsed)
    if not complete or complete[0]['time'] != 0 or any(b['time']<=a['time'] for a,b in zip(complete,complete[1:])):
        raise ValueError('Invalid diagnostic time sequence')
    return complete


def measure(root):
    source_count = 0; rows = []; studies = {}
    for study in STUDIES:
        directory = root/study; runs = load(directory/'runs.json'); studies[study] = runs
        provenance = load(directory/'provenance.json')
        if digest(directory/'source.tar.gz') != provenance['source_archive_sha256']:
            raise ValueError('Changed source archive: '+study)
        with tarfile.open(directory/'source.tar.gz') as archive:
            for name, expected in provenance['source_sha256'].items():
                if hashlib.sha256(archive.extractfile(name).read()).hexdigest() != expected:
                    raise ValueError('Changed run source: '+name)
                source_count += 1
        for name, run in runs.items():
            for filename, expected in run['files_sha256'].items():
                if digest(directory/name/filename) != expected:
                    raise ValueError(f'Changed run file: {study}/{name}/{filename}')
            summary = run.get('summary',{})
            completed = run.get('status', 'completed' if summary.get('completed') else 'failed') == 'completed'
            row = dict(study=study, name=name, completed=completed,
                       status=run.get('status', 'completed' if completed else 'failed'), seconds=run['seconds'])
            path = directory/name/'accepted_diagnostics.csv'
            if path.exists():
                h = histories(path)
                if summary and (len(h)!=summary['steps']+1 or h[-1]['time']!=summary['time']):
                    raise ValueError(f'History/summary mismatch: {study}/{name}')
                row.update(last_recorded_time=h[-1]['time'],p_min=min(a['p_min'] for a in h),
                           rho_min=min(a['rho_min'] for a in h),budget_max=max(a['budget_max'] for a in h))
            rows.append(row)
    comparison = {}
    old,new = root/'controls',root/'accelerated'
    fields = ['rho','p','vx','vy','vz','bx','by','bz','energy','ax','ay','az','phi']
    for name,run in studies['controls'].items():
        if run['status'] != 'completed':continue
        a,b = read_cells(old/name/'final.csv'),read_cells(new/name/'final.csv')
        if len(a)!=len(b) or any(abs(x[k]-y[k])>1e-12 for x,y in zip(a,b) for k in ['id','time','x','y','volume']):
            raise ValueError('Projection parity geometry mismatch')
        differences = {k:max(abs(x[k]-y[k]) for x,y in zip(a,b)) for k in fields}
        if max(differences.values())>1e-8:raise ValueError('Projection parity failure')
        comparison[name] = dict(max_errors=differences,wall_speedup=run['seconds']/studies['accelerated'][name]['seconds'])
    prefixes = {}
    for label in ['base','boost']:
        name='quadratic_brio_'+label
        a,b=histories(old/name/'accepted_diagnostics.csv'),histories(new/name/'accepted_diagnostics.csv')
        paired=list(zip(a,b));errors={k:max(abs(x[k]-y[k]) for x,y in paired) for k in a[0]}
        if errors['time']>1e-10 or errors['p_min']>1e-8 or errors['magnetic_energy']>1e-8:
            raise ValueError('Projection shock-prefix parity failure')
        prefixes[label]=dict(rows=len(paired),last_old_time=a[-1]['time'],errors=errors)
    curves=[]
    for study,name,label in [('baseline','n512_j0.15_base','Original paper source'),
                            ('positive_extended','n512_j0.15_base','Positive dissipation (rejected)'),
                            ('projected_refinement','n512_base','Linear curl + projection'),
                            ('accelerated','quadratic_brio_base','Quadratic curl + projection')]:
        run=studies[study][name]
        curves.append(dict(label=label,completed=run['summary']['completed'],
                           history=histories(root/study/name/'accepted_diagnostics.csv')))
    configs=load(new/'manifest.json')
    packet=analyze(new,configs,studies['accelerated'])
    fine='quadratic_brio_base'
    bx={stage:max(abs(c['bx']-.75) for c in read_cells(new/fine/f'{stage}.csv')) for stage in ['initial','final']}
    return dict(records=rows,verified_source_members=source_count,parity=comparison,shock_prefixes=prefixes,
                pressure_curves=curves,accelerated_packet=packet,fine_quadratic_bx=bx,
                full_m1_accepted=False,scope='96 new bounded evolutions plus 3 reused baseline records; two original runs timed out.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=measure(args.raw)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(f'Verified {len(result["records"])} records and {result["verified_source_members"]} source members; '
          f'{len(result["parity"])} completed parity pairs; full M1 remains unaccepted.')


if __name__=='__main__':main()
