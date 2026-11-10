"""Independent NumPy reduction of archived raw CSVs; no simulation or gate change."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import numpy as np

root=Path(__file__).resolve().parent
manifest=json.loads((root/'hll_artifacts.sha256.json').read_text())
report=json.loads((root/'report.json').read_text())
source=json.loads((root/'snapshot.json').read_text())['source_sha256']
with tarfile.open(root/'sources.tar.gz') as archive:
    source_names=[]
    for member in archive.getmembers():
        data=archive.extractfile(member).read()
        if hashlib.sha256(data).hexdigest()!=source[member.name]:raise ValueError('Changed source '+member.name)
        source_names.append(member.name)
with tarfile.open(root/'science.tar.gz') as archive:
    records={}
    for member in archive.getmembers():
        data=archive.extractfile(member).read()
        if hashlib.sha256(data).hexdigest()!=manifest['source/results/hll_shock_probe/'+member.name]:
            raise ValueError('Changed scientific artifact '+member.name)
        records[member.name]=data

def cells(name):return np.genfromtxt(io.BytesIO(records[name+'/final.csv']),names=True,delimiter=',')

checks=[]
for pair in report['pairs']:
    a=pair['solver']+'_brio-wu_n1024_j'+pair['mesh']+'_base';b=a.removesuffix('base')+'boost'
    x=cells(a);y=cells(b)
    if not np.array_equal(x['id'],y['id']) or not np.all(x['time']==.1) or not np.all(y['time']==.1):
        raise ValueError('Unexpected ID/time')
    volume=x['volume'].sum();values={}
    for field,scale in pair['scales'].items():
        expected=x[field].copy()
        if field in ('vx','vy','vz'):expected+=dict(vx=2.,vy=-1.,vz=0.)[field]
        if field=='energy':expected+=x['rho']*(2.*x['vx']-x['vy']+2.5)
        values[field]=float(np.sum(x['volume']*np.abs(y[field]-expected)/scale)/volume)
    discrepancy=max(abs(values[k]-pair['relative_L1'][k]) for k in values)
    if discrepancy>1e-15:raise ValueError('Independent boost reduction disagrees')
    mode={}
    for name,data in ((a,x),(b,y)):
        observed=float(np.max(np.abs(np.fft.rfft(data['vx'].reshape(4,1024),axis=0)[2].real/4)))
        recorded=json.loads(records[name+'/row_modes.json'])[-1]['vx_alternating_max']
        mode[name]=dict(independent_DFT=observed,recorded=recorded,absolute_difference=abs(observed-recorded))
        if abs(observed-recorded)>1e-15:raise ValueError('Independent mode reduction disagrees')
    checks.append(dict(solver=pair['solver'],mesh=pair['mesh'],relative_L1=values,
                       max_absolute_difference=discrepancy,final_modes=mode))
result=dict(scope='Independent weighted NumPy boost and row-DFT reduction; not an independent scientific review',
            numpy=np.__version__,source_files_verified=len(source_names),scientific_artifacts_verified=len(records),checks=checks)
(root/'independent_reduction.json').write_text(json.dumps(result,indent=2)+'\n')
print('Verified',len(source_names),'source files,',len(records),'scientific artifacts and',len(checks),'independent pair reductions')
