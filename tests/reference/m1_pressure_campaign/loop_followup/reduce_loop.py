"""Inspect a passed loop pair's boost residual and counters; no evolution."""
from pathlib import Path
import gzip,hashlib,io,json,math,tarfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
NAME='loop_bulk-frame-heun-quadratic-v1_v0.0_j0.15_fixed_n64'
FILES=('initial.csv','checkpoint_0.25000000.csv','final.csv')
COUNTERS=('steps','dt_min','dt_max','rejected_state','rejected_cfl','hll_fallbacks','hll_fallbacks_attempted')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    records={};inputs={};output={};snapshots={}
    for label,relative in (('pressure','tests/reference/m1_pressure_campaign/medium'),
                           ('historical_hlld','tests/reference/m1_reana_bounded/medium')):
        p=ROOT/relative;manifest=json.loads((p/'archive_sha256.json').read_text())
        assert sha(p/'runs.json.gz')==manifest['runs.json.gz']
        records[label]=json.loads(gzip.decompress((p/'runs.json.gz').read_bytes()))
        inputs[relative+'/runs.json.gz']=manifest['runs.json.gz']
    members=json.loads((OUT/'historical_members_sha256.json').read_text())
    with tarfile.open(OUT/'historical_hlld.tar.gz') as tar:
        historical={m.name:tar.extractfile(m).read() for m in tar if m.isfile()}
    assert set(historical)==set(members)
    assert all(hashlib.sha256(historical[n]).hexdigest()==h for n,h in members.items())
    for label,runs in records.items():
        output[label]={'counters':{},'snapshots':[]}
        for frame in ('base','boost'):
            output[label]['counters'][frame]={k:runs[NAME+'_'+frame]['summary'][k] for k in COUNTERS}
        for filename in FILES:
            arrays=[]
            for frame in ('base','boost'):
                name=NAME+'_'+frame
                if label=='pressure':
                    p=ROOT/'tests/reference/m1_pressure_campaign/medium/snapshots'/name/(filename+'.gz')
                    raw=gzip.decompress(p.read_bytes())
                else:raw=historical[name+'/'+filename]
                digest=hashlib.sha256(raw).hexdigest();assert digest==runs[name]['sha256'][filename]
                inputs[label+'/'+name+'/'+filename]=digest
                d=np.genfromtxt(io.BytesIO(raw),names=True,delimiter=',')
                assert np.array_equal(d['id'],np.arange(4096)) and (d['volume']>0).all()
                assert all(np.isfinite(d[k]).all() for k in d.dtype.names)
                arrays.append(d)
            x,y=arrays;assert np.array_equal(x['time'],y['time'])
            delta=np.sqrt(sum((x[k]-y[k])**2 for k in ('bx','by','bz')))
            error=float(np.dot(x['volume'],delta)/sum(x['volume']))/(.001/math.sqrt(4*math.pi))
            worst=int(np.argmax(delta))
            output[label]['snapshots'].append(dict(time=float(x['time'][0]),B_relative_L1=error,
                B_absolute_max=float(delta.max()),worst_cell=worst,pressure_max_difference=float(max(abs(y['p']-x['p'])))))
            if label=='pressure' and filename=='final.csv':snapshots['final']=(x,delta)
    fig,axes=plt.subplots(1,2,figsize=(11,4.9),layout='constrained')
    for label,color in (('historical_hlld','#2178a8'),('pressure','#b16d18')):
        rows=output[label]['snapshots'][1:]
        axes[0].semilogy([r['time'] for r in rows],[r['B_relative_L1'] for r in rows],'-o',color=color,
                         label='Historical HLLD' if label=='historical_hlld' else 'Pressure blend')
    axes[0].axhline(.001,color='black',ls='--',lw=1,label='Registered loop gate')
    axes[0].set(xlabel='Physical time',ylabel='Volume-weighted boost B L1 / Bscale',ylim=(1e-16,.01),
                xticks=[.25,1.],title='N64 jittered fixed-mesh loop')
    axes[0].legend(fontsize=9);axes[0].grid(alpha=.2)
    x,delta=snapshots['final']
    # This positive floor affects log colours only; all reductions use the raw values.
    im=axes[1].scatter(x['x'],x['y'],c=np.maximum(delta,1e-18),s=5,norm=LogNorm(1e-18,1e-10),cmap='viridis')
    axes[1].set(xlabel='Base-frame x',ylabel='Base-frame y',xlim=(0,1),ylim=(0,1),aspect='equal',title='Final magnetic difference at cell centres')
    fig.colorbar(im,ax=axes[1],label='Absolute |Bboost − Bbase|')
    fig.suptitle('Loop boost comparison passes; accepted timestep counts differ')
    fig.supxlabel('Pressure blend: 5481 / 5482 steps, 3538 / 3540 CFL retries. Timesteps are a hypothesis, not a proven cause.',fontsize=9)
    image=ROOT/'docs/images/m1_completion/pressure_loop_followup.png';fig.savefig(image,dpi=170);plt.close(fig)
    report=dict(scope='Hash-verified postprocessing of existing snapshots/counters. Historical HLLD uses an older frozen source. No matched-timestep experiment, new evolution or causal proof.',
                inputs=inputs,observations=output,plot_sha256=sha(image),script_sha256=sha(Path(__file__)),numpy=np.__version__,matplotlib=matplotlib.__version__)
    (OUT/'observation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(output,indent=2))


if __name__=='__main__':main()
