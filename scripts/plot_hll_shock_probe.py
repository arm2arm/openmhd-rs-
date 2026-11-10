#!/usr/bin/env python3
"""Plot hash-verified REANA flux-comparison artifacts; never run an evolution."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('download_root',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args();root=args.download_root
    manifest_path=root/'outputs/hll_artifacts.sha256.json'
    manifest=json.loads(manifest_path.read_text());used={}
    def verified(name):
        path=root/name;digest=sha(path)
        if digest!=manifest[name]:raise ValueError('Changed artifact: '+name)
        used[name]=digest;return path
    directory='source/results/hll_shock_probe'
    report=json.loads(verified(directory+'/report.json').read_text())
    if report['status']!='completed' or len(report['runs'])!=8:raise ValueError('Incomplete comparison report')
    colors={'hlld':'#c23c39','hll':'#2374ab'}
    fig,axes=plt.subplots(2,2,figsize=(11.5,8.2))
    completed=[]
    for name,run in sorted(report['runs'].items()):
        if run['status']!='completed':continue
        completed.append(name);solver=run['solver'];boost=bool(any(run['config']['boost']))
        column=run['config']['jitter']!=0
        mode_path=verified(f'{directory}/{name}/row_modes.json')
        modes=json.loads(mode_path.read_text())
        ax=axes[0,int(column)]
        ax.plot([r['time'] for r in modes],[max(r['vx_alternating_max'],1e-18) for r in modes],
                color=colors[solver],linestyle='--' if boost else '-',linewidth=1.4,
                label=solver.upper()+(' boost' if boost else ' base'))
        if column and not boost:
            path=verified(f'{directory}/{name}/final.csv')
            data=np.genfromtxt(path,names=True,delimiter=',')
            for ax,field in zip(axes[1],('vx','by')):
                for row in range(4):
                    subset=data[row*1024:(row+1)*1024]
                    ax.plot(subset['x'],subset[field],color=colors[solver],lw=.9,alpha=.7,
                            label=solver.upper() if row==0 else None)
    repo=Path(__file__).resolve().parents[1]
    reference=repo/'tests/reference/external_mhd/brio_8192.csv.gz'
    # The remote comparison records the pinned reference digest it actually used.
    if sha(reference)!=report['reference_sha256']:raise ValueError('Reference hash differs')
    with gzip.open(reference,'rt') as stream:ref=np.genfromtxt(stream,names=True,delimiter=',')
    for ax,field,label in zip(axes[1],('vx','by'),('vx','By')):
        ax.plot(ref['x'],ref[field],color='#222222',ls=':',lw=1.2,label='pinned 1D reference')
        ax.set(xlim=(1.05,1.19),ylim=(-.28,.67) if field=='vx' else (-.97,-.45),
               xlabel='x',ylabel=label,title=f'Column base frame, t=0.1: {label}')
        ax.grid(alpha=.2);ax.legend(fontsize=8)
    for ax,title in zip(axes[0],('Regular mesh','Column jitter 0.15')):
        ax.set(yscale='log',xlabel='simulation time',ylabel='max |alternating-row vx coefficient|',title=title)
        ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('Controlled HLLD / HLL shock comparison — nx1024 × ny4',fontsize=14)
    fig.text(.5,.015,f'{len(completed)}/8 evolutions completed; HLL bounded pass: {report["hll_bounded_pass"]}. '
             'This diagnostic does not establish full M1 acceptance.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.95));args.output.mkdir(parents=True,exist_ok=True)
    image=args.output/'hll_shock_comparison.png';fig.savefig(image,dpi=180);plt.close(fig)
    provenance=dict(scope='Hash-verified plotting only; no evolution',python=sys.version,
                    numpy=np.__version__,matplotlib=matplotlib.__version__,plot_sha256=sha(image),
                    source_sha256=sha(Path(__file__)),reference_sha256=sha(reference),
                    manifest_sha256=sha(manifest_path),inputs=used,completed_runs=completed,
                    scientific_acceptance=False)
    (args.output/'hll_shock_plot_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(image,sha(image))


if __name__=='__main__':main()
