#!/usr/bin/env python3
"""Reproduce M1 physical-study figures from raw or compressed archived packets."""
import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
INPUTS={}
def data(path):
    actual=path if path.exists() else path.with_suffix(path.suffix+'.gz')
    raw=actual.read_bytes();INPUTS[str(actual)]=hashlib.sha256(raw).hexdigest()
    text=gzip.decompress(raw).decode() if actual.suffix=='.gz' else raw.decode()
    return json.loads(text)
def reference(name):
    path=ROOT/'tests/reference/external_mhd'/name;INPUTS[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    with gzip.open(path,'rt') as f:return [{k:float(v) for k,v in row.items()} for row in csv.DictReader(f)]
def save(fig,out,name):fig.savefig(out/name);plt.close(fig)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--wave-dir',type=Path,required=True);p.add_argument('--remaining-dir',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);args=p.parse_args()
    out=args.output_dir;out.mkdir(parents=True,exist_ok=True);wave=data(args.wave_dir/'summary.json');rest=data(args.remaining_dir/'summary.json');rest_profile=rest['profile']
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':140,'savefig.dpi':160})
    profile=next(r['config']['profile'] for r in wave['runs'].values() if r['config']['case']=='alfven')
    fig,axes=plt.subplots(2,2,figsize=(11,8),layout='constrained')
    for item in wave['alfven_convergence']:
        ax=axes[int(item['parallel']),int(item['jitter']>0)];rows=[r for r in item['rows'] if r['status']=='completed']
        verdict='incomplete ladder' if item['gate'].startswith('unexecuted') else 'evolution failed' if item['gate'].startswith('fail: evolution') else item['gate'];label=item['motion']+'; '+verdict
        if 'finest_three_order' in item:label+=f" (order {item['finest_three_order']:.2f})"
        ax.loglog([r['n'] for r in rows],[r['B_L1']/.1 for r in rows],'o-' if item['motion']=='fixed' else 's--',label=label)
        initial=sorted([r for n,r in wave['runs'].items() if n.startswith('alfven_') and n.endswith('_base') and r['config']['parallel']==item['parallel'] and r['config']['jitter']==item['jitter'] and r['config']['motion_family']==item['motion'] and 'errors' in r],key=lambda r:r['config']['n'])
        if item['motion']=='fixed':ax.loglog([r['config']['n'] for r in initial],[r['errors']['initial']['B']['L1']/.1 for r in initial],':',color='grey',label='initial curl representation')
        ax.axhline(.02,color='grey',ls=':',lw=1);ax.set(title=('Travelling' if item['parallel']==0 else 'Standing')+(' · regular' if item['jitter']==0 else ' · jitter .15'),xlabel='N in each direction',ylabel='Vector B L1 / amplitude .1');ax.grid(alpha=.2);ax.legend(fontsize=7)
    fig.suptitle(f'Alfvén spatial convergence · {profile} · t=1\nRegistered finest-three order ≥1.8; finest relative error ≤.02',fontsize=12)
    save(fig,out,'alfven_convergence.png')

    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    for j in (0.,.15):
        for parallel in (0.,1.):
            rows=sorted([x for x in wave['pairs'] if x['case']=='alfven' and x['jitter']==j and x['parallel']==parallel and x['motion']=='fixed' and 'relative_L1' in x],key=lambda r:r['n'])
            axes[0].loglog([r['n'] for r in rows],[max(r['relative_L1']['wave_amplitude'].values()) for r in rows],'o-',label=f'v∥={parallel:g}, jitter={j:g}')
    axes[0].axhline(1e-8,color='grey',ls=':');axes[0].set(xlabel='N in each direction',ylabel='Largest normalized physical boost L1',title='Joint fluid/grid boost (2,−1,0) · fixed family');axes[0].legend(fontsize=8);axes[0].grid(alpha=.2)
    temporal=wave['temporal'] if isinstance(wave['temporal'],list) else []
    for ref in sorted({r['reference'] for r in temporal}):
        rows=sorted([r for r in temporal if r['reference']==ref and 'errors' in r],key=lambda r:r['dt'])
        if rows:axes[1].loglog([r['dt'] for r in rows],[r['errors']['B']['L1'] for r in rows],'o-',label=ref.split('_v')[-1].replace('_dt2.5e-05',''))
    axes[1].set(xlabel='dt cap',ylabel='Vector B L1 versus dt=0.000025',title='N64 temporal comparison; A/phi orders in packet');axes[1].grid(alpha=.2)
    if temporal:axes[1].legend(fontsize=8)
    else:axes[1].text(.5,.5,'Temporal ladder unexecuted',ha='center',transform=axes[1].transAxes)
    fig.suptitle(profile+' · physical boost and temporal diagnostics',fontsize=12);save(fig,out,'alfven_boost_temporal.png')

    fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained');ref=reference('brio_8192.csv.gz')
    for ax,key in zip(axes.flat,('rho','p','vx','by')):
        ax.plot([r['x'] for r in ref],[r[key] for r in ref],color='black',lw=1,label='Athena8192')
        for name,r in sorted(rest['runs'].items(),key=lambda item:item[1]['config']['n']):
            if r['config']['case']!='brio' or r['status']!='completed':continue
            rows=data(args.remaining_dir/name/'projection.json');group={}
            for row in rows:group.setdefault(row['x'],[]).append(row['candidate'][key])
            xs=sorted(group);ax.plot(xs,[sum(group[x])/len(group[x]) for x in xs],lw=1,label=f"Nx={r['config']['n']}; L1={r['reference_L1'][key]:.4g}")
        ax.set(xlabel='x',ylabel=key,xlim=(.5,1.5));ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('Brio–Wu · '+rest_profile+' · gamma=2 · t=.1\nCurves show row means; reported errors take absolute differences separately in each cell',fontsize=12);save(fig,out,'brio_profiles.png')

    fig,axes=plt.subplots(1,4,figsize=(14,4),layout='constrained');ref=reference('vortex_512.csv.gz');maps=[('Athena512 → 64²',np.array([r['rho'] for r in ref]).reshape(64,64),'completed')]
    for n in (64,128,256):
        name=f'vortex_n{n}_j0.0_b0';r=rest['runs'].get(name)
        rows=data(args.remaining_dir/name/'projection.json') if r and r['status']=='completed' else None
        maps.append((f'Rust N{n} → 64²',None if rows is None else np.array([x['rho'] for x in rows]).reshape(64,64),'No completed result' if r is None else r['status']))
    valid=[v for _,v,_ in maps if v is not None];vmin=min(v.min() for v in valid);vmax=max(v.max() for v in valid)
    for ax,(title,grid,status) in zip(axes,maps):
        if grid is None:ax.text(.5,.5,status,ha='center',transform=ax.transAxes)
        else:im=ax.imshow(grid,origin='lower',extent=(0,1,0,1),vmin=vmin,vmax=vmax,cmap='magma')
        ax.set(title=title,xlabel='x',ylabel='y',aspect='equal')
    fig.colorbar(im,ax=axes,label='Density',shrink=.7);fig.suptitle('Orszag–Tang · '+rest_profile+' · t=.5 · identical overlap bins and color scale',fontsize=12);save(fig,out,'vortex_density.png')

    fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
    for ax,key,limit in zip(axes.flat,('rho','p','bx','by'),(.06,.1,.1,.1)):
        for j in (0.,.15):
            rows=sorted([r for r in rest['runs'].values() if r['config']['case']=='vortex' and not r['config']['boost'] and r['config']['jitter']==j and 'scaled_reference_L1' in r],key=lambda r:r['config']['n'])
            ax.loglog([r['config']['n'] for r in rows],[r['scaled_reference_L1'][key] for r in rows],'o-',label=f'jitter={j:g}')
        ax.axhline(limit,color='grey',ls=':',label='finest-grid limit');ax.set(xlabel='N in each direction',ylabel=key+' scaled bin L1');ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('Orszag–Tang · '+rest_profile+' · reference errors at t=.5\nReference refinement uncertainty is reported separately in the numeric packet',fontsize=12);save(fig,out,'vortex_errors.png')

    fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    for j in (0.,.15):
        for moving in (False,True):
            rows=sorted([r for r in rest['runs'].values() if r['config']['case']=='passive' and r['config']['jitter']==j and r['config']['comoving']==moving and 'relative_A_L1' in r],key=lambda r:r['config']['n'])
            label=('comoving' if moving else 'fixed')+f', jitter={j:g}'
            axes[0].loglog([r['config']['n'] for r in rows],[r['relative_A_L1'] for r in rows],'o-',label=label)
            axes[1].semilogx([r['config']['n'] for r in rows],[r['magnetic_energy_initial_final'][1]/r['magnetic_energy_initial_final'][0] for r in rows],'o-',label=label)
    axes[0].axhline(.1,color='grey',ls=':');axes[0].set(xlabel='N in each direction',ylabel='A L1 / initial peak');axes[1].set(xlabel='N in each direction',ylabel='Magnetic energy / initial value')
    for ax in axes:ax.grid(alpha=.2);ax.legend(fontsize=8)
    operator=next((r['summary']['operator'] for r in rest['runs'].values() if r['config']['case']=='passive' and r['status']=='completed'),'unexecuted');fig.suptitle('Prescribed-flow loop · '+operator+' · t=1\nIsolated transport; no gas or cleaning evolution',fontsize=12);save(fig,out,'passive_loop.png')
    provenance={'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'matplotlib':matplotlib.__version__,'numpy':np.__version__,'input_sha256':INPUTS,'output_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('*.png'))}}
    (out/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
if __name__=='__main__':main()
