#!/usr/bin/env python3
"""Verify and reduce archived REANA results, then plot; no evolution."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();root=args.archive
    manifest=json.loads((root/'shock_sensor_artifacts.sha256.json').read_text())
    metadata=json.loads((root/'snapshot.json').read_text())
    sources=0
    with tarfile.open(root/'sources.tar.gz') as tar:
        for item in tar.getmembers():
            data=tar.extractfile(item).read()
            if hashlib.sha256(data).hexdigest()!=metadata['source_sha256'][item.name]:raise ValueError(item.name)
            sources+=1
    records={}
    with tarfile.open(root/'science.tar.gz') as tar:
        for item in tar.getmembers():
            data=tar.extractfile(item).read()
            if hashlib.sha256(data).hexdigest()!=manifest['source/results/shock_sensor_probe/'+item.name]:raise ValueError(item.name)
            records[item.name]=data
    report=json.loads(records['report.json'])
    def cells(name,file='final.csv'):
        return np.genfromtxt(io.BytesIO(records[name+'/'+file]),names=True,delimiter=',',dtype=None,encoding='utf8')
    pairs=[]
    for pair in report['pairs']:
        a,b=pair['names'];x,y=cells(a),cells(b)
        if not np.array_equal(x['id'],y['id']):raise ValueError('ID mismatch')
        config=report['runs'][b]['config'];boost=config['boost'];values={}
        for field,scale in pair['scales'].items():
            expected=x[field].copy()
            if field in ('vx','vy','vz'):expected+=boost[('vx','vy','vz').index(field)]
            if field=='energy':expected+=x['rho']*(sum(x[k]*v for k,v in zip(('vx','vy','vz'),boost))+.5*sum(v*v for v in boost))
            values[field]=float(np.sum(x['volume']*abs(y[field]-expected)/scale)/np.sum(x['volume']))
        discrepancy=max(abs(values[k]-pair['relative_L1'][k]) for k in values)
        if discrepancy>1e-15:raise ValueError('Independent boost reduction disagrees')
        pairs.append(dict(names=[a,b],relative_L1=values,maximum_discrepancy=discrepancy))
    rows={};sensors={};divergence={}
    fig,axes=plt.subplots(2,2,figsize=(12,8.5))
    colors={'hlld':'#c23c39','hll':'#2374ab','hlld-shock':'#a16a14'}
    for name,run in report['runs'].items():
        data=cells(name);config=run['config'];solver=run['solver'];boosted=bool(any(config['boost']))
        if config['case']=='brio-wu':
            vx=data['vx'].reshape(4,1024);spread=np.ptp(vx,axis=0)
            rows[name]=float(spread.max())
            if abs(rows[name]-run['final_row_variation']['vx'])>1e-15:raise ValueError('Row reduction disagrees')
            if config['jitter'] and not boosted:
                ax=axes[0,0];ax.plot(data['x'][:1024],np.maximum(spread,1e-16),color=colors[solver],label=solver)
                for row in range(4):axes[1,0].plot(data['x'][row*1024:(row+1)*1024],vx[row],color=colors[solver],alpha=.7,lw=.9,label=solver if row==0 else None)
            if solver=='hlld-shock':
                face=cells(name,'final_shock_faces.csv')
                # The first remote report used an absolute-x window. Correct
                # that observational window here for both translating frames.
                x=(face['x']-config['boost'][0]*config['time'])%2.
                window=(x>=1.05)&(x<=1.25)
                for direction in ('x','y'):
                    orientation=abs(face['nx'])>=abs(face['ny'])
                    mask=window&(orientation if direction=='x' else ~orientation)
                    sensors[name+'_'+direction]=dict(faces=int(mask.sum()),active=int((face['method'][mask]=='HlldShock').sum()),
                        theta_min=float(face['theta'][mask].min()),max_mass_flux_change=float(abs(face['mass_new'][mask]-face['mass_hlld'][mask]).max()))
        else:
            norm=np.sqrt(data['volume']/np.pi)*data['div_b_limited']/(np.sqrt(data['bx']**2+data['by']**2+data['bz']**2)+1e-12/np.sqrt(4*np.pi))
            rms=float(np.sqrt(np.sum(data['volume']*norm**2)/sum(data['volume'])))
            final=run['history'][-1]['diagnostics']['div_B_limited']['dimensionless']['rms']
            if abs(rms-final)>1e-12:raise ValueError('Independent divergence reduction disagrees')
            divergence[name]=rms
    for index,jitter in enumerate(('0.0','0.15')):
        values=[report['runs'][s+'_orszag-tang_n32_j'+jitter+'_base']['diagnostic_values']['limited_face_dimensionless_divB_RMS_max'] for s in colors]
        axes[0,1].bar(np.arange(3)+index*4,values,color=list(colors.values()))
    axes[0,1].set_xticks([1,5],['Regular vortex','Jittered vortex']);axes[0,1].axhline(.1,color='black',ls='--',label='gate 0.1')
    axes[0,1].set(ylabel='Maximum normalized limited-face div B RMS',title='N32 vortex, t=0.5');axes[0,1].legend()
    names=[s+'_brio-wu_n1024_j0.15c_base' for s in colors]
    vals=[max(p['relative_L1'].values()) for p in report['pairs'] if p['names'][0] in names]
    axes[1,1].bar(list(colors),vals,color=list(colors.values()));axes[1,1].axhline(1e-8,color='black',ls='--',label='gate 1e-8')
    axes[1,1].set(yscale='log',ylabel='Maximum normalized boost L1',title='Column shock, nx1024 × ny4, t=0.1');axes[1,1].legend()
    axes[0,0].set(xlim=(1.05,1.25),yscale='log',xlabel='Rest-frame x',ylabel='Row-to-row vx range',title='Column shock: transverse differences');axes[0,0].legend()
    axes[1,0].set(xlim=(1.10,1.18),ylim=(-.25,.65),xlabel='Rest-frame x',ylabel='vx',title='Column shock: four row profiles');axes[1,0].legend()
    for ax in axes.flat:ax.grid(alpha=.2)
    fig.suptitle('HLLD shock-only correction: vortex passes; column shock boost still fails')
    fig.tight_layout();args.output.mkdir(exist_ok=True,parents=True)
    image=args.output/'shock_sensor_comparison.png';fig.savefig(image,dpi=180);plt.close(fig)
    result=dict(scope='Independent raw-state NumPy reductions; div B itself is the stored operator output, not independently reconstructed; no new evolution or full M1 acceptance',
        source_files_verified=sources,scientific_artifacts_verified=len(records),pairs=pairs,row_ranges=rows,rest_frame_slow_shock_faces=sensors,
        final_normalized_divergence=divergence,plot_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),numpy=np.__version__,matplotlib=matplotlib.__version__)
    (root/'independent_reduction.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Verified',sources,'sources,',len(records),'scientific files,',len(pairs),'boost pairs;',image)


if __name__=='__main__':main()
