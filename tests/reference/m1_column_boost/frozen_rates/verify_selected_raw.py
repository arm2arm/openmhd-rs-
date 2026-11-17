from pathlib import Path
import json,hashlib
import numpy as np
root=Path('results/reana_remote_m1_column_rates_20261110/outputs/column_trace');old=Path('results/reana_remote_m1_column_trace_20261110/outputs/column_trace');selected=json.loads(Path('results/m1_column_trace_selected_snapshots.json').read_text());report=json.loads((root/'report.json').read_text());checks=[]
for name,row in selected.items():
 p=root/name/row['file'].replace('.csv','_rates.csv');digest=hashlib.sha256(p.read_bytes()).hexdigest();assert digest==report['runs'][name]['sha256'][p.name]
 states=np.genfromtxt(old/name/row['file'],names=True,delimiter=',');rates=np.genfromtxt(p,names=True,delimiter=',');assert np.array_equal(states['id'],rates['id']);assert np.array_equal(states['time'],rates['time'])
 data=json.loads((root/name/'row_modes.json').read_text());record=next(r for r in data if r['file']==row['file']);weights=states['volume'].reshape(4,1024).sum(axis=0)
 dft=lambda v:np.fft.rfft(v.reshape(4,1024),axis=0)[2].real/4
 v=dft(states['vx']);square=np.sum(weights*v*v);observed={}
 for group in ('fluid','fluid_x','fluid_y'):
  a=(rates[group+'_mx']-states['vx']*rates[group+'_rho'])/states['rho'];da=dft(a);g=float(np.sum(weights*v*da)/square);expected=record['frozen_rates']['growth']['vx']['rates'][group]['logarithmic_growth'];observed[group]=dict(independent_growth=g,recorded_growth=expected,absolute_difference=abs(g-expected))
 residual={field:float(np.max(abs(rates['fluid_'+field]-rates['fluid_x_'+field]-rates['fluid_y_'+field]))) for field in ('rho','mx','my','mz','energy')}
 assert max(residual.values())<1e-10
 checks.append(dict(name=name,file=p.name,sha256=digest,time=row['time'],independent_fft_growth=observed,max_local_face_group_sum_residual=residual))
result=dict(scope='Independent NumPy row DFT/acceleration reduction at four verified snapshots; no evolution',checks=checks,numpy=np.__version__)
Path('results/m1_column_rate_independent_fft.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(checks,indent=2))
