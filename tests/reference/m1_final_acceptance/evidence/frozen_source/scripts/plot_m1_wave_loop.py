#!/usr/bin/env python3
"""Plot measured issue #7 results, preserving incomplete and failed gate labels."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter, NullFormatter
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    if path.exists():
        return json.loads(path.read_text())
    return json.loads(gzip.decompress(path.with_suffix(path.suffix+'.gz').read_bytes()))


def cells(path):
    if path.exists():
        stream = path.open()
    else:
        stream = gzip.open(path.with_suffix(path.suffix+'.gz'), 'rt')
    with stream:
        return [{k:float(v) for k,v in row.items()} for row in csv.DictReader(stream)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, default=ROOT/'tests/reference/m1_wave_loop')
    parser.add_argument('--comparison-dir', type=Path, help='Optional bulk-frame physical packet; defaults to INPUT/bulk')
    parser.add_argument('--output-dir', type=Path, default=ROOT/'docs/images/m1_wave_loop')
    args = parser.parse_args()
    source = args.input_dir.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    data = load(source/'summary.json')
    plt.rcParams.update({'font.size':10, 'axes.spines.top':False, 'axes.spines.right':False,
                         'figure.dpi':140, 'savefig.dpi':160})
    comparison_path=args.comparison_dir.resolve() if args.comparison_dir else source/'bulk'
    comparison=load(comparison_path/'summary.json') if ((comparison_path/'summary.json').exists() or (comparison_path/'summary.json.gz').exists()) else None
    colors = {'paper-global-v2':'#c34b30','bulk-frame-v1':'#167185'}
    fig,axes = plt.subplots(1,2,figsize=(11,4.6),layout='constrained')
    for series in data['mean_refinement']:
        if not series['values']:
            continue
        ax=axes[0 if series['variable']=='n' else 1]
        measured=[row for row in series['values'] if row[1] is not None]
        if not measured:
            continue
        x,y=zip(*measured)
        label=series['profile']+(' · regular' if series['jitter']==0 else ' · jitter .15')
        ax.loglog(x,np.maximum(y,1e-18),marker='o' if series['jitter']==0 else 's',
                  linestyle='-' if series['jitter']==0 else '--',color=colors[series['profile']],label=label)
    axes[0].set(xlabel='N in each direction',ylabel='Volume-weighted vector B boost error (L1)',title='Spatial ladder · dt cap = 0.00025')
    axes[1].set(xlabel='dt cap',title='Time-step ladder · N = 16')
    for ax in axes:
        ax.grid(True,which='both',alpha=.2)
    axes[0].set_xticks([8,16,32,64]);axes[0].xaxis.set_major_formatter(ScalarFormatter());axes[0].xaxis.set_minor_formatter(NullFormatter())
    axes[1].set_xticks([.00025,.0005,.001]);axes[1].xaxis.set_major_formatter(ScalarFormatter());axes[1].xaxis.set_minor_formatter(NullFormatter())
    axes[0].legend(fontsize=8)
    fig.suptitle('Nonuniform flow with mean B = (0.3, 0.2, 0.1) · t = 0.02\nJoint fluid/grid boost (2, −1, 0); the original v2 discrepancy is retained',fontsize=12)
    fig.savefig(output/'mean_field_boost.png');plt.close(fig)

    fig,axes=plt.subplots(2,2,figsize=(10,7),layout='constrained',sharex=True,sharey=True)
    for item in data['alfven_convergence']:
        ax=axes[int(item['parallel'])][int(item['jitter']>0)]
        rows=[r for r in item['rows'] if r['status']=='completed']
        ax.loglog([r['n'] for r in rows],[r['B_L1']/.1 for r in rows],'o-' if item['motion']=='fixed' else 's--',label=item['motion'])
        ax.set_title(('Travelling' if item['parallel']==0 else 'Standing')+(' · regular' if item['jitter']==0 else ' · jitter .15'))
        ax.set_xticks([r['n'] for r in rows]);ax.xaxis.set_major_formatter(ScalarFormatter());ax.xaxis.set_minor_formatter(NullFormatter())
        ax.set_xlabel('N in each direction');ax.set_ylabel('Vector B L1 / amplitude 0.1');ax.grid(True,which='both',alpha=.2);ax.legend(fontsize=8)
    complete=all(i['gate'] in ('pass','fail') for i in data['alfven_convergence'])
    fig.suptitle('Alfvén wave · paper-global-v2 · t = 1\n'+('Full ladder measured; see numeric gate statuses' if complete else 'N32/64 subset only — finest-three order and N256 gates unexecuted'),fontsize=12)
    fig.savefig(output/'alfven_subset.png');plt.close(fig)

    # Fixed archived selection makes plots reproducible without storing all full snapshots.
    names={motion:f'loop_paper-global-v2_v0.0_j0.0_{motion}_n64_base' for motion in ('fixed','comoving')}
    snapshots=[]
    snapshot_inputs=[]
    for title,motion,stage in [('Initial','fixed','initial'),('Fixed mesh · t=1','fixed','final'),('Comoving mesh · t=1','comoving','final')]:
        path=source/names[motion]/f'{stage}.csv'
        if not path.exists() and not path.with_suffix('.csv.gz').exists():
            path=source/'snapshots'/names[motion]/f'{stage}.csv'
        snapshot_inputs.append(path if path.exists() else path.with_suffix('.csv.gz'))
        snapshots.append((title,cells(path)))
    vmax=max(c['az'] for _,rows in snapshots for c in rows)
    fig,axes=plt.subplots(1,3,figsize=(11,4.3),layout='constrained',sharex=True,sharey=True)
    for ax,(title,rows) in zip(axes,snapshots):
        n=64
        # Rigid comoving loop translates by whole boxes by t=1; sort coordinates for a physical map.
        x=sorted(set(round(c['x'],10) for c in rows));y=sorted(set(round(c['y'],10) for c in rows))
        if len(x)!=n or len(y)!=n:
            raise ValueError('loop map requires regular 64x64 sampling')
        index_x={v:i for i,v in enumerate(x)};index_y={v:i for i,v in enumerate(y)}
        grid=np.empty((n,n))
        for c in rows:
            grid[index_y[round(c['y'],10)],index_x[round(c['x'],10)]]=c['az']
        im=ax.imshow(grid,origin='lower',extent=(0,1,0,1),cmap='magma',vmin=0,vmax=vmax)
        ax.set(title=title,xlabel='x');ax.set_aspect('equal')
    axes[0].set_ylabel('y');fig.colorbar(im,ax=axes,label='Az',shrink=.75)
    fig.suptitle('Weak field loop · coupled MHD · N64 regular · paper-global-v2\nPassive translation is a diagnostic reference, not an exact coupled solution',fontsize=12)
    fig.savefig(output/'loop_subset.png');plt.close(fig)

    fig,axes=plt.subplots(1,3,figsize=(14,4.6),layout='constrained')
    for motion,name in names.items():
        run=data['runs'][name]
        h=run['history'];energy0=h[0]['diagnostics']['magnetic_energy']
        axes[0].plot([r['time'] for r in h],[r['diagnostics']['magnetic_energy']/energy0 for r in h],'o-' if motion=='fixed' else 's--',label=motion)
        d=run['summary']['final']
        for ax,unit in zip(axes[1:],('dimensional','dimensionless')):
            ax.plot(range(3),[d[key][unit]['rms'] for key in ('div_B_ls','div_B_face','div_B_limited')], 'o-' if motion=='fixed' else 's--',label=motion)
    axes[0].set(xlabel='Time',ylabel='Magnetic energy / initial value',title='Measured output samples; lines guide the eye')
    for ax,unit in zip(axes[1:],('Dimensional','Dimensionless')):
        ax.set(xticks=range(3),xticklabels=['LS','Arithmetic','Limited'],ylabel=unit+' RMS div B',title='Distinct operators at t=1')
        ax.set_yscale('log')
    for ax in axes:
        ax.grid(True,alpha=.2);ax.legend()
    fig.suptitle('N64 regular coupled loop · energy and independent divergence diagnostics',fontsize=12)
    fig.savefig(output/'loop_diagnostics.png');plt.close(fig)
    if comparison:
        fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained',sharey=True)
        for ax,jitter in zip(axes,(0.,.15)):
            keys=[(motion,parallel,n) for motion in ('fixed','comoving') for parallel in (0.,1.) for n in (32,64)]
            for packet,profile in [(data,'paper-global-v2'),(comparison,'bulk-frame-v1')]:
                pairs={(p['motion'],p['parallel'],p['n']):p for p in packet['pairs'] if p['case']=='alfven' and p['jitter']==jitter}
                ax.semilogy(range(len(keys)),[pairs[k]['errors']['B']['L1']/.1 for k in keys],
                    'o-' if profile=='paper-global-v2' else 's--',color=colors[profile],label=profile)
            ax.axhline(1e-8,color='grey',linestyle=':',label='1e-8 threshold')
            ax.set_xticks(range(len(keys)),[f'{m}\nv∥={int(v)}, N{n}' for m,v,n in keys],rotation=35,ha='right',fontsize=8)
            ax.set_title('Regular' if jitter==0 else 'Jitter .15');ax.grid(True,which='both',alpha=.2);ax.legend(fontsize=8)
        axes[0].set_ylabel('Boosted vector B L1 / wave amplitude .1')
        fig.suptitle('Alfvén boost comparison · t=1 · N32/64 subset\nMagnetic part only; complete density/pressure/velocity/energy classifications are in the numeric packet',fontsize=12)
        fig.savefig(output/'alfven_boost_profiles.png');plt.close(fig)
    inputs=[source/'summary.json',source/'summary.json.gz']
    inputs=[p for p in inputs if p.exists()]+snapshot_inputs
    comparison_inputs=[p for p in [comparison_path/'summary.json',comparison_path/'summary.json.gz'] if p.exists()] if comparison else []
    provenance={'comparison_input_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in comparison_inputs},'matplotlib':matplotlib.__version__,'numpy':np.__version__,
                'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'input_sha256':{str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
                'output_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.glob('*.png'))}}
    (output/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')


if __name__=='__main__':
    main()
