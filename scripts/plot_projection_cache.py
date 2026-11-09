#!/usr/bin/env python3
"""Plot measured REANA cache/threading timings; no ideal-scaling extrapolation."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    d=json.loads(args.report.read_text())
    if d['status']!='completed' or len(d['runs'])!=11 or len(d['comparisons'])!=7 or not all(c['bit_identical'] for c in d['comparisons']):
        raise ValueError('Requires the complete verified cache/threading benchmark')
    runs=d['runs'];cases=('wave64_k0','wave128_k1','shock512','vortex32')
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(1,3,figsize=(14,4.8),layout='constrained')
    x=np.arange(4);width=.36
    for suffix,offset,color,label in (('_baseline',-width/2,'#8795a1','Before cache'),('_cached',width/2,'#087f8c','Cached diagonal')):
        values=[runs[c+suffix]['timing']['evolution_seconds'] for c in cases]
        bars=ax[0].bar(x+offset,values,width,color=color,label=label)
        ax[0].bar_label(bars,fmt='%.1f',fontsize=8,padding=3)
    ax[0].set(xticks=x,xticklabels=['Wave N64\nκ=0, t=.02','Wave N128\nκ=1, t=.02','Shock nx512\nκ=1, t=.02','Vortex N32\nκ=1, t=.5'],
              ylabel='Evolution time (seconds)',title='Cache change: one thread')
    ax[0].set_ylim(0,118);ax[0].legend(frameon=False,fontsize=9)
    threads=(1,4,12,24)
    rows=[runs['wave128_k1_cached'],*[runs[f'wave128_k1_threads{n}'] for n in threads[1:]]]
    for field,label,color in (('wall_seconds','Total wall time','#855aa5'),('evolution_seconds','Evolution only','#087f8c')):
        values=[r[field] if field=='wall_seconds' else r['timing'][field] for r in rows]
        speed=[values[0]/v for v in values]
        ax[1].plot(x,speed,'o-',color=color,label=label)
        for i,value in enumerate(speed[1:],1):ax[1].annotate(f'{value:.2f}×',(i,value),xytext=(0,7),textcoords='offset points',ha='center',fontsize=9)
    ax[1].axhline(1,color='0.7',ls=':',lw=1)
    ax[1].set(xticks=x,xticklabels=threads,xlabel='Threads per simulation',ylabel='Speedup relative to one thread',
              ylim=(.9,2.25),title='N128 standing wave, κ=1')
    ax[1].legend(frameon=False,fontsize=9,loc='upper left')
    ax[2].bar(x-width/2,threads,width,label='Thread limit',color='#c8d0d7')
    cores=[r['cpu_seconds']/r['wall_seconds'] for r in rows]
    bars=ax[2].bar(x+width/2,cores,width,label='Average cores used',color='#087f8c')
    ax[2].bar_label(bars,fmt='%.2f',fontsize=9,padding=3)
    ax[2].set(xticks=x,xticklabels=threads,xlabel='Threads per simulation',ylabel='CPU cores',ylim=(0,27),title='CPU time / wall time')
    ax[2].legend(frameon=False,fontsize=9,loc='upper left')
    fig.suptitle('REANA projection performance — identical scientific outputs in all 7 comparisons',fontsize=14)
    fig.supxlabel('One timing sample per configuration on a shared node; 11 completed evolutions. No full M1 acceptance is implied.',fontsize=9)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(args.output,dpi=160);plt.close(fig)


if __name__=='__main__':main()
