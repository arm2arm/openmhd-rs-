#!/usr/bin/env python3
"""Read-only independent AI review of the bounded N64 snapshot figures."""
import csv,gzip,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
figures=ROOT/'docs/images/m1_completion'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
provenance=json.loads((figures/'snapshot_provenance.json').read_text())
assert provenance['script_sha256']==sha(ROOT/'scripts/plot_m1_snapshots.py')
for name,digest in provenance['figure_sha256'].items(): assert sha(figures/name)==digest,name
for old_path,digest in provenance['archive_manifest_sha256'].items():
    directory=ROOT/'tests/reference/m1_completion'/Path(old_path).name
    assert sha(directory/'archive_sha256.json')==digest,directory
    for name,digest in json.loads((directory/'archive_sha256.json').read_text()).items():
        assert sha(directory/name)==digest,name
print('Figure/script/input archive hashes verified')

def snapshot(directory,name,stage,t):
    with gzip.open(directory/'snapshots'/name/(stage+'.csv.gz'),'rt') as f:
        rows=[{k:float(v) for k,v in row.items()} for row in csv.DictReader(f)]
    assert len(rows)==4096 and {r['id'] for r in rows}==set(range(4096))
    assert all(r['time']==t and r['volume']>0 and all(map(math.isfinite,r.values())) for r in rows)
    assert abs(math.fsum(r['volume'] for r in rows)-1)<1e-9
    keyed={}
    for r in rows:
        ij=tuple(round(64*r[k]-.5)%64 for k in ('x','y'))
        assert ij not in keyed
        assert max(abs((r[k]-(v+.5)/64+.5)%1-.5) for k,v in zip(('x','y'),ij))<1e-10
        keyed[ij]=r
    return keyed

def difference(a,b):
    return max(math.sqrt(sum((a[ij][k]-b[ij][k])**2 for k in ('bx','by','bz'))) for ij in a)

amplitude=.001/math.sqrt(4*math.pi)
for directory,prefix in [(ROOT/'tests/reference/m1_completion/prescribed','loop_j0.0'),
                         (ROOT/'tests/reference/m1_completion/signal_quick','loop_bulk-frame-signal-v1_v0.0_j0.0')]:
    data={}
    for motion,stage,t in [('fixed','initial',0.),('fixed','final',1.),('comoving','final',1.)]:
        name=f'{prefix}_{motion}_n64_base'
        rows=snapshot(directory,name,stage,t);data[(motion,stage)]=rows
        magnitudes=[math.sqrt(sum(r[k]**2 for k in ('bx','by','bz')))/amplitude for r in rows.values()]
        assert max(magnitudes)<1.2
        print(f'{directory.name} {motion} {stage}: |B|/B0 range=[{min(magnitudes):.17e}, {max(magnitudes):.17e}], former-1.1-overflow-cells={sum(x>1.1 for x in magnitudes)}')
    print(f'{directory.name} comoving versus initial max cellwise |delta B|={difference(data[("fixed","initial")],data[("comoving","final")]):.17e}')

candidate=ROOT/'tests/reference/m1_completion/signal_quick'
prefix='alfven_bulk-frame-signal-v1_v1.0_j0.0_fixed_n64'
base=snapshot(candidate,prefix+'_base','final',1.)
boost=snapshot(candidate,prefix+'_boost','final',1.)
summary=json.loads(gzip.decompress((candidate/'summary.json.gz').read_bytes()))
pair=next(p for p in summary['pairs'] if prefix+'_base' in p['names'])
assert pair['pairing_valid'] and pair['profile']=='bulk-frame-signal-v1' and pair['parallel']==1.
maximum=difference(base,boost)
assert math.isclose(maximum,pair['errors']['B']['max'],rel_tol=1e-14)
print(f'Standing-wave full-cell vector boost maximum={maximum:.17e} (matches archived paired maximum)')
for key,trig in [('by',math.sin),('bz',math.cos)]:
    means=[math.fsum(base[(i,j)][key] for j in range(64))/64 for i in range(64)]
    # parallel=1, no base boost: phase=2*pi*(x+(1-parallel)*t)=2*pi*x.
    exact=[.1*trig(2*math.pi*(i+.5)/64) for i in range(64)]
    residual=[a-b for a,b in zip(means,exact)]
    max_y_spread=max(abs(base[(i,j)][key]-means[i]) for i in range(64) for j in range(64))
    print(f'{key}: y-mean numerical-minus-analytic range=[{min(residual):.17e}, {max(residual):.17e}], maximum y deviation={max_y_spread:.17e}')
print('N64 geometry, normalization, analytic standing phase, full vector maximum and unclipped field ranges verified. Full spatial/temporal evidence remains pending.')
