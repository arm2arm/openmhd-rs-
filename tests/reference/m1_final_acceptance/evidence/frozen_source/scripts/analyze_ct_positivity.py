#!/usr/bin/env python3
"""Combine bounded admissibility controls, frozen rates and baseline parity."""
import argparse
import csv
import json
from pathlib import Path
from run_m1_wave_loop import dump


def analyze(primary, extended, frozen, baseline, old_frozen):
    packets=[json.loads((p/'analysis.json').read_text()) for p in [primary,extended]]
    runs=[r for a in packets for r in a['runs'].values()]
    pairs=[r for a in packets for r in a['boost_pairs']]
    waves={name:all((primary/name/file).read_bytes()==(baseline/name/file).read_bytes()
                   for file in ['initial.csv','final.csv','accepted_diagnostics.csv'])
           for name in packets[0]['runs'] if name.startswith('wave_')}
    frozen_files=['initial_cells.csv','initial_faces.csv','last_cells.csv','last_faces.csv','failure.json']
    parity={file:(frozen/file).read_bytes()==(old_frozen/file).read_bytes() for file in frozen_files}
    with (frozen/'last_rate_comparison.csv').open() as stream:
        rates={r['scheme']:{k:float(v) for k,v in r.items() if k not in ['scheme','id']}
               for r in csv.DictReader(stream) if r['id']=='645'}
    sensitivity=[]
    for name,r in packets[1]['runs'].items():
        if '_dt' in name and name.endswith('_base'):
            sensitivity.append(dict(dt=r['summary']['max_dt'],min_pressure=r['accepted']['min_pressure'],
                                    final_min_pressure=r['summary']['min_pressure_final'],
                                    limited_stages=r['summary']['limited_stages'],minimum_theta=r['summary']['minimum_theta']))
    sensitivity.sort(key=lambda r:r['dt'],reverse=True)
    return dict(completed=sum(r['status']=='completed' for r in runs),count=len(runs),
        boost_pairs_passed=sum(r['passed'] for r in pairs),boost_pairs=len(pairs),
        max_boost_absolute=max(max(r['component_max_absolute'].values()) for r in pairs),
        max_budget=max(r['accepted']['max_budget'] for r in runs),
        max_ct_divergence=max(r['accepted']['max_ct_divergence'] for r in runs),
        low_order_rejections=sum(r['summary']['low_order_rejections'] for r in runs),
        high_order_rate_failures=sum(r['summary']['high_order_rate_failures'] for r in runs),
        minimum_theta=min(r['summary']['minimum_theta'] for r in runs),
        wave_physical_bytes_unchanged=waves,original_frozen_bytes_unchanged=parity,
        frozen_cell645_rates=rates,time_step_sensitivity=sensitivity,
        wave_spatial=packets[0]['spatial'],full_m1_accepted=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['primary','extended','frozen','baseline','old-frozen','output']:
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    result=analyze(a.primary,a.extended,a.frozen,a.baseline,a.old_frozen)
    dump(a.output,result)
    print(json.dumps({k:result[k] for k in ['completed','count','boost_pairs_passed','max_budget','max_boost_absolute']},indent=2))
