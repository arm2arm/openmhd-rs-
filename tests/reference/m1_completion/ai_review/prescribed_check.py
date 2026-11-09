#!/usr/bin/env python3
"""Independent read-only review of the full prescribed-flow packet; stdlib only."""
import csv,gzip,hashlib,json,math,sys,tarfile
from pathlib import Path
archive=Path(sys.argv[1]);raw=Path(sys.argv[2])
sha=lambda b:hashlib.sha256(b).hexdigest()
read=lambda name:json.loads(gzip.decompress((archive/(name+'.json.gz')).read_bytes()))
check=lambda x: (_ for _ in ()).throw(AssertionError()) if not x else None
for name,digest in json.loads((archive/'archive_sha256.json').read_text()).items():
    assert sha((archive/name).read_bytes())==digest,name
print('Archive file hashes verified')
execution=json.loads((archive/'execution_provenance.json').read_text())
measured=json.loads((archive/'measurement_provenance.json').read_text())
for name,digest in execution['result_sha256'].items():
    actual=gzip.decompress((archive/('execution_summary.json.gz' if name=='summary.json' else name+'.gz')).read_bytes())
    assert sha(actual)==digest,name
assert sha((archive/'execution_provenance.json').read_bytes())==measured['execution_provenance_sha256']
assert sha(gzip.decompress((archive/'execution_summary.json.gz').read_bytes()))==measured['execution_summary_sha256']
assert sha(gzip.decompress((archive/'summary.json.gz').read_bytes()))==measured['summary_sha256']
for filename,hashes in [('execution_sources.tar.gz',execution['source_sha256']),('measurement_sources.tar.gz',measured['measurement_source_sha256'])]:
    with tarfile.open(archive/filename) as tar:
        members={m.name:sha(tar.extractfile(m).read()) for m in tar.getmembers()}
    assert members==hashes,filename
print('Execution/measurement provenance and exact archived source bytes verified')
manifest=read('manifest');runs=read('runs');summary=read('summary')
assert len(manifest)==len(runs)==len(summary['runs'])==32
assert set(manifest)==set(runs)==set(summary['runs'])
assert execution['config']['quick'] is False
amplitude=.001/math.sqrt(4*math.pi)
def snapshot(path,n,t):
    with path.open() as f: rows=[{k:float(v) for k,v in r.items()} for r in csv.DictReader(f)]
    assert len(rows)==n*n
    assert all(row['id']==i and row['time']==t and row['volume']>0 and all(map(math.isfinite,row.values())) for i,row in enumerate(rows))
    assert abs(math.fsum(r['volume'] for r in rows)-1)<1e-9
    return rows
def norm(errors,rows):
    v=math.fsum(r['volume'] for r in rows)
    return {'L1':math.fsum(abs(e)*r['volume'] for e,r in zip(errors,rows))/v,
            'L2':math.sqrt(math.fsum(e*e*r['volume'] for e,r in zip(errors,rows))/v),'max':max(map(abs,errors))}
def compare(a,b):
    for k in a: assert math.isclose(a[k],b[k],rel_tol=2e-12,abs_tol=1e-18),(k,a[k],b[k])
all_norms={};comoving=0
for name,record in runs.items():
    c=manifest[name]
    assert c==record['config'] and record['status']=='completed' and record['returncode']==0
    for filename,digest in record['sha256'].items(): assert sha((raw/name/filename).read_bytes())==digest,(name,filename)
    initial=snapshot(raw/name/'initial.csv',c['n'],0.)
    final=snapshot(raw/name/'final.csv',c['n'],1.)
    r=summary['runs'][name]
    assert r['status']=='completed' and r['summary']['completed'] and r['summary']['time']==1.
    ea=[];eb=[];brows=[]
    for row in final:
        dx=(row['x']-c['velocity'][0]-.5+.5)%1-.5
        dy=(row['y']-c['velocity'][1]-.5+.5)%1-.5
        radius=math.hypot(dx,dy)
        ea.append(row['az']-amplitude*max(.3-radius,0.))
        if radius>1e-12 and abs(radius-.3)>1e-12:
            b=(-amplitude*dy/radius,amplitude*dx/radius,0.) if radius<.3 else (0.,0.,0.)
            eb.append(math.sqrt(sum((row[k]-v)**2 for k,v in zip(('bx','by','bz'),b))))
            brows.append(row)
    an=norm(ea,final);bn=norm(eb,brows)
    compare(an,r['errors']['passive_A']);compare(bn,r['errors']['passive_B'])
    assert r['errors']['passive_B_excluded_cells']==len(final)-len(brows)
    for label,rows in [('initial',initial),('final',final)]:
        independent={'magnetic_energy':math.fsum(.5*row['volume']*sum(row[k]**2 for k in ('bx','by','bz')) for row in rows),
                     'A_integral':math.fsum(row['volume']*row['az'] for row in rows),'A_min':min(row['az'] for row in rows),'A_max':max(row['az'] for row in rows)}
        compare(independent,r['diagnostics'][label])
    if c['motion']=='comoving':
        assert r['comoving_gate']=='pass'
        assert all(a[k]==b[k] for a,b in zip(initial,final) for k in ('az','bx','by','bz'))
        assert all(v==0 for metric in r['discrete_drift'].values() for v in metric.values())
        comoving+=1
    all_norms[name]=an['L1']/(.3*amplitude)
print(f'All 32 raw-file hashes, complete initial/final snapshots, analytic A/B norms and energy/A-integral/extrema verified; {comoving} comoving runs bit-identical in A/B')
for pair in summary['pairs']:
    assert pair['status']=='pass' and pair['pairing_valid']
    a,b=(snapshot(raw/name/'final.csv',manifest[name]['n'],1.) for name in pair['names'])
    assert all(x[k]==y[k] for x,y in zip(a,b) for k in ('az','bx','by','bz','volume'))
    assert all(v==0 for metric in pair['errors'].values() for v in metric.values())
    assert max(abs((y[k]-x[k]-shift+.5)%1-.5) for x,y in zip(a,b) for k,shift in [('x',2.),('y',-1.)])<1e-11
assert len(summary['pairs'])==16
print('All 16 paired final A/B/volume arrays bit-identical; periodic boost position correspondence verified')
for ladder in summary['fixed_convergence']:
    values=[all_norms[f"loop_j{ladder['jitter']}_fixed_n{n}_base"] for n in [32,64,128,256]]
    assert all(a>b for a,b in zip(values,values[1:])) and values[-1]<.1
    assert ladder['gate']=='pass'
    assert all(math.isclose(v,r['A_L1_over_peak'],rel_tol=2e-12,abs_tol=1e-18) for v,r in zip(values,ladder['rows']))
    orders=[math.log2(a/b) for a,b in zip(values,values[1:])]
    print(f"Fixed jitter={ladder['jitter']} normalized_A_L1={values}; adjacent_orders={orders}")
print('Independent AI review: prescribed-flow packet is internally verified; this is not coupled-MHD or paper-level acceptance.')
