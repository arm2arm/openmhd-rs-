#!/usr/bin/env python3
"""Plot a complete medium packet, distinguishing its gate from fine-grid acceptance."""
import argparse
import gzip
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import NullLocator


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('summary',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    raw=args.summary.read_bytes()
    data=json.loads(gzip.decompress(raw) if args.summary.suffix=='.gz' else raw)
    runs=data['runs'];pairs=data['pairs']
    if (len(runs)!=48 or len(pairs)!=24 or
        any(r['status']!='completed' or not r['positive_and_conservative'] for r in runs.values()) or
        any(p['status'] not in ('pass','pass under both reported normalizations') for p in pairs)):
        raise ValueError('Requires the complete passing 48-run medium packet')
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,3,figsize=(14,5.3),layout='constrained',width_ratios=(1.2,1.2,1))
    colors=['#087f8c','#855aa5','#d0802b','#b34755'];orders=[]
    for index,(jitter,parallel) in enumerate((j,p) for j in (0.,.15) for p in (0.,1.)):
        label=('Regular' if jitter==0 else 'Jittered')+(' travelling' if parallel==0 else ' standing')
        for motion in ('fixed','comoving'):
            selected=sorted([r for n,r in runs.items() if n.startswith('alfven_') and n.endswith('_base')
                             and r['config']['jitter']==jitter and r['config']['parallel']==parallel
                             and r['config']['motion_family']==motion],key=lambda r:r['config']['n'])
            if [r['config']['n'] for r in selected]!=[32,64]:raise ValueError('Wrong spatial subset')
            errors=[r['errors']['final']['B']['L1']/.1 for r in selected]
            orders.append((label+'\n'+motion,math.log(errors[0]/errors[1],2),colors[index]))
            if motion=='fixed':axes[0].loglog([32,64],errors,'o-',label=label,color=colors[index])
    axes[0].set(title='Fixed meshes: physical B error',xlabel='Cells per direction N',ylabel='Volume-weighted B L1 / amplitude 0.1')
    axes[0].set_xticks([32,64],labels=['32','64']);axes[0].xaxis.set_minor_locator(NullLocator())
    axes[0].legend(fontsize=8,frameon=False);axes[0].grid(alpha=.2,which='both')
    for i,(_,order,color) in enumerate(orders):
        axes[1].plot(order,i,'o',color=color)
        axes[1].annotate(f'{order:.3f}',(order,i),xytext=(-6,0),textcoords='offset points',ha='right',va='center',fontsize=8)
    axes[1].axvline(1.8,color='0.4',ls='--',lw=1,label='Target on N64/128/256')
    axes[1].set(title='Coarse order: N32 → N64',xlabel='Two-point order (diagnostic only)',xlim=(1.48,2.02),
                yticks=range(len(orders)),yticklabels=[label for label,_,_ in orders])
    axes[1].invert_yaxis();axes[1].tick_params(axis='y',labelsize=8);axes[1].legend(fontsize=8,frameon=False,loc='lower right')
    wave=[p for p in pairs if p['case']=='alfven'];loop=[p for p in pairs if p['case']=='loop']
    if len(wave)!=16 or len(loop)!=8:raise ValueError('Wrong boost subset')
    ratios=[max(max(values.values()) for p in wave for values in p['relative_L1'].values())/1e-8,
            max(p['B_relative_L1'] for p in loop)/.001]
    axes[2].bar([0,1],[max(x,1e-16) for x in ratios],color=['#087f8c','#855aa5'],width=.5)
    for i,x in enumerate(ratios):axes[2].text(i,max(x,1e-16)*1.8,f'{x:.2e}',ha='center',fontsize=9)
    axes[2].axhline(1,color='0.4',ls='--',lw=1,label='Registered boost limit')
    axes[2].set(yscale='log',ylim=(min(max(min(ratios)/10,1e-16),1e-5),10),title='Largest boost residual / limit',
                ylabel='Ratio (passes at ≤1)',xticks=[0,1],xticklabels=['Alfvén\n16 pairs pass','Loop\n8 pairs pass'])
    axes[2].legend(fontsize=8,frameon=False,loc='upper right');axes[2].grid(axis='y',alpha=.2)
    fig.suptitle('Screened quadratic candidate (κ=1): all 48 medium evolutions complete at t=1',fontsize=14)
    fig.supxlabel('Medium execution, positivity, budgets and boost checks pass. N128/256 convergence and full shock/vortex reference gates remain open.',fontsize=9)
    args.output.parent.mkdir(parents=True,exist_ok=True);fig.savefig(args.output,dpi=160);plt.close(fig)


if __name__=='__main__':main()
