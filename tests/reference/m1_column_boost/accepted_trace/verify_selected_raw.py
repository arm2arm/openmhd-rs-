from pathlib import Path
import csv,json,hashlib
import numpy as np
root=Path('results/reana_remote_m1_column_trace_20261110/outputs/column_trace')
selected=json.loads(Path('results/m1_column_trace_selected_snapshots.json').read_text()); report=json.loads((root/'report.json').read_text());checks=[]
for name, row in selected.items():
 p=root/name/row['file'];digest=hashlib.sha256(p.read_bytes()).hexdigest();assert digest==row['sha256']==report['runs'][name]['sha256'][row['file']]
 data=np.genfromtxt(p,delimiter=',',names=True)
 assert len(data)==4096 and np.array_equal(data['id'],np.arange(4096))
 errors={}
 for field, recorded in row['alternating'].items():
  coeff=np.fft.rfft(data[field].reshape(4,1024),axis=0)[2].real/4
  independent=float(np.max(abs(coeff)));error=abs(independent-recorded['max_abs']);assert error<1e-14*(1+float(np.max(abs(data[field]))))
  errors[field]=error
 checks.append(dict(name=name,file=row['file'],sha256=digest,time=row['time'],fft_coefficient_absolute_errors=errors))
Path('results/m1_column_trace_independent_fft.json').write_text(json.dumps(dict(scope='Independent NumPy row DFT reduction of four hash-verified intermediate snapshots; no evolution',numpy=np.__version__,checks=checks),indent=2)+'\n')
print('Verified four raw snapshots and 36 independent row Fourier coefficients')
