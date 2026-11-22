#!/usr/bin/env python3
"""Render full issue #7 continuation from verified raw or compact archived packets."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]


def load(directory):
    hashes=directory/'archive_sha256.json'
    plain=directory/'summary.json'
    selected=plain if plain.exists() else directory/'summary.json.gz'
    if hashes.exists():
        manifest=json.loads(hashes.read_text())
        if selected.name not in manifest: raise ValueError('unverified summary shadows archive')
        for name,digest in manifest.items():
            if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=digest: raise ValueError(f'changed archive {directory/name}')
    else:
        provenance=directory/'measurement_provenance.json'
        if provenance.exists(): expected=json.loads(provenance.read_text())['summary_sha256']
        else: expected=json.loads((directory/'provenance.json').read_text())['result_sha256']['summary.json']
        if hashlib.sha256(selected.read_bytes()).hexdigest()!=expected: raise ValueError('changed raw summary')
    return json.loads(plain.read_text()) if plain.exists() else json.loads(gzip.decompress((directory/'summary.json.gz').read_bytes()))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    default=ROOT/'tests/reference/m1_completion'
    parser.add_argument('--original',type=Path,default=default/'original')
    parser.add_argument('--candidate',type=Path,default=default/'candidate')
    parser.add_argument('--prescribed',type=Path,default=default/'prescribed')
    parser.add_argument('--output',type=Path,default=ROOT/'docs/images/m1_completion')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    original,candidate,prescribed=map(load,(args.original,args.candidate,args.prescribed))
    plt.rcParams.update({'figure.dpi':150,'font.size':9,'axes.grid':True,'grid.alpha':.25,'savefig.bbox':'tight'})
    profiles=[(original,'paper-global-v2','#bc5045'),(candidate,'bulk-frame-signal-v1','#266ca0')]
    measured_n=sorted({p['n'] for data,_,_ in profiles for p in data['pairs'] if p['case'] in ('alfven','loop') and 'errors' in p})
    resolution_label='N='+','.join(map(str,measured_n))
    if measured_n != [32,64,128,256]: resolution_label+=' · partial spatial packet'
    fig,axes=plt.subplots(2,2,figsize=(11,8),sharex=True,sharey=True)
    for row,jitter in enumerate((0.,.15)):
        for col,parallel in enumerate((0.,1.)):
            ax=axes[row,col]
            for data,label,color in profiles:
                for motion,style in [('fixed','-'),('comoving','--')]:
                    series=[s for s in data['alfven_convergence'] if s['jitter']==jitter and s['parallel']==parallel and s['motion']==motion][0]
                    rows=[r for r in series['rows'] if r['status']=='completed' and r['B_L1'] is not None]
                    order=series.get('finest_three_order')
                    suffix=f', p={order:.2f}' if order is not None else ', incomplete'
                    ax.loglog([r['n'] for r in rows],[r['B_L1']/.1 for r in rows],marker='o',linestyle=style,color=color,label=f'{label}, {motion}{suffix}')
                    missing=sorted({32,64,128,256}-{r['n'] for r in rows})
                    if missing: ax.plot([],[],color=color,label=f'{label} {motion}: failed/missing N={missing}')
            ax.axhline(.02,color='black',linewidth=.8,linestyle=':',label='N256 relative-error bound')
            ax.set_title(f'{"Travelling" if parallel==0 else "Standing"}, jitter={jitter}')
            ax.set_xticks([32,64,128,256],[32,64,128,256]);ax.legend(fontsize=6)
            ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
            ax.set_xlabel('N per direction');ax.set_ylabel('Magnetic vector L1 / 0.1')
    fig.suptitle('Alfvén spatial packet, t=1 · 2.5D periodic Voronoi\nReported order fits N64/128/256; target p ≥ 1.8; failures retained')
    fig.tight_layout();fig.savefig(args.output/'alfven_convergence.png');plt.close(fig)

    fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    for ax,case in zip(axes,('alfven','loop')):
        for data,label,color in profiles:
            pairs=[p for p in data['pairs'] if p['case']==case and 'errors' in p]
            for jitter,marker in [(0.,'o'),(.15,'s')]:
                for n in (32,64,128,256):
                    rows=[p for p in pairs if p['n']==n and p['jitter']==jitter]
                    if not rows: continue
                    scale=.1 if case=='alfven' else .001/(4*3.141592653589793)**.5
                    ax.scatter([n]*len(rows),[max(p['errors']['B']['L1']/scale,1e-17) for p in rows],marker=marker,color=color,alpha=.7,label=f'{label}, jitter={jitter}' if n==32 else None)
        ax.axhline(1e-8 if case=='alfven' else .001,color='black',linestyle=':',label='B relative-L1 gate')
        ax.set_xscale('log',base=2);ax.set_yscale('log');ax.set_xticks([32,64,128,256],[32,64,128,256])
        ax.set_xlabel('N per direction');ax.set_ylabel('Magnetic boost L1 / field amplitude');ax.set_title(case);ax.legend(fontsize=7)
    fig.suptitle(f'Joint fluid/grid boost (2, −1, 0), t=1 · {resolution_label}\nMagnetic part only; log-display floor 1e−17; complete classifications in numeric packet')
    fig.tight_layout();fig.savefig(args.output/'boost_comparison.png');plt.close(fig)

    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for data,label,color in profiles:
        for parallel,marker in [(0.,'o'),(1.,'s')]:
            for jitter,style in [(0.,'-'),(.15,'--')]:
                rows=[r for r in data['temporal'] if 'errors' in r and f'_v{parallel}_j{jitter}_' in r['name']] if isinstance(data['temporal'],list) else []
                rows.sort(key=lambda r:r['dt'])
                if not rows:continue
                axes[0].loglog([r['dt'] for r in rows],[r['errors']['B']['L1'] for r in rows],color=color,marker=marker,linestyle=style,label=f'{label}, v∥={parallel}, j={jitter}')
                axes[1].loglog([r['dt'] for r in rows],[max(r['errors']['phi']['L1'],1e-30) for r in rows],color=color,marker=marker,linestyle=style)
    for ax in axes:ax.set_xlabel('dt cap');ax.set_ylabel('L1 vs same-grid dt=0.000025')
    axes[0].set_title('Physical B');axes[1].set_title('Cleaning scalar phi (floor at 1e−30 for display)');axes[0].legend(fontsize=6)
    fig.suptitle('N64 fixed-grid temporal packet, t=1 · frozen-C1 prescription retained')
    fig.tight_layout();fig.savefig(args.output/'temporal.png');plt.close(fig)

    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for s in prescribed['fixed_convergence']:
        rows=[r for r in s['rows'] if r['A_L1_over_peak'] is not None]
        axes[0].loglog([r['n'] for r in rows],[r['A_L1_over_peak'] for r in rows],'o-',label=f'jitter={s["jitter"]}, {s["gate"]}')
    axes[0].axhline(.1,color='black',linestyle=':',label='N256 bound');axes[0].legend();axes[0].set_ylabel('Fixed-grid A L1 / initial analytic peak')
    for jitter,style in [(0.,'-'),(.15,'--')]:
        for motion in ('fixed','comoving'):
            rows=sorted([r for n,r in prescribed['runs'].items() if n.endswith('_base') and r['config']['motion']==motion and r['config']['jitter']==jitter and r['status']=='completed'],key=lambda r:r['config']['n'])
            axes[1].plot([r['config']['n'] for r in rows],[r['diagnostics']['final']['magnetic_energy']/r['diagnostics']['initial']['magnetic_energy'] for r in rows],marker='o',linestyle=style,label=f'{motion}, jitter={jitter}')
    axes[1].set_ylabel('Final / initial discrete magnetic energy');axes[1].legend(fontsize=8)
    for ax in axes:ax.set_xscale('log',base=2);ax.set_xticks([32,64,128,256],[32,64,128,256]);ax.set_xlabel('N per direction')
    fig.suptitle('Prescribed-flow loop, t=1 · separate from coupled MHD\nNo fluid energy budget; comoving A/B drift and three divergence operators in numeric packet')
    fig.tight_layout();fig.savefig(args.output/'prescribed_loop.png');plt.close(fig)


if __name__=='__main__': main()
