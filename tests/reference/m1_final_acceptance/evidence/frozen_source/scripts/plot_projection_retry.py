#!/usr/bin/env python3
"""Scientific summary of the bounded projection retry and its remaining gate."""
import argparse
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('analysis',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();data=json.loads(args.analysis.read_text())
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import NullFormatter
    fig,axes=plt.subplots(2,2,figsize=(12,8.2),layout='constrained')
    colors=['#333333','#b34e29','#8172b3','#137fa2']
    ax=axes[0,0]
    for curve,color in zip(data['pressure_curves'],colors):
        h=curve['history'];ax.plot([r['time'] for r in h],[r['p_min'] for r in h],color=color,label=curve['label']+(' (fails)' if not curve['completed'] else ''))
        if not curve['completed']:ax.plot(h[-1]['time'],h[-1]['p_min'],'x',color=color,markersize=9)
    ax.set(title='Finer jittered shock: nx512 × ny4',xlabel='Simulation time',ylabel='Minimum accepted pressure',ylim=(-.005,.105))
    ax.axhline(0,color='.5',lw=.8);ax.grid(alpha=.2);ax.legend(fontsize=8,loc='upper right')
    ax=axes[0,1]
    for profile,label,color in [('bulk-frame-heun-projected-v1','Linear curl + projection',colors[2]),
                                ('bulk-frame-heun-quadratic-v1','Quadratic curl + projection',colors[3])]:
        row=next(r for r in data['accelerated_packet']['spatial'] if r['profile']==profile and r['jitter']==.15 and r['parallel']==1.)
        ax.loglog([8,16,32],[v/.1 for v in row['errors']['final']['v']],'-o',color=color,
                  label=f'{label}\norder {row["orders"]["final"]["v"]:.3f}')
    ax.set(title='Jittered standing Alfvén wave, t=0.02',xlabel='N (N × N cells)',ylabel='Velocity L1 error / wave amplitude',xticks=[8,16,32],xticklabels=['8','16','32'])
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.grid(which='both',alpha=.2);ax.legend(fontsize=8)
    ax=axes[1,0]
    rows={(r['study'],r['name']):r for r in data['records']}
    for i,v in enumerate([0.,1.]):
        name=f'bulk-frame-heun-quadratic-v1_j0.15_v{v}_n32'
        old,new=rows['controls',name]['seconds'],rows['accelerated',name]['seconds']
        ax.bar(i-.17,old,width=.32,color='.5',label='Original Jacobi CG' if i==0 else None)
        ax.bar(i+.17,new,width=.32,color=colors[3],label='Cached preconditioner' if i==0 else None)
        ax.text(i,old+.25,f'{old/new:.1f}× faster',ha='center',fontsize=10)
    ax.set(title='Same completed N32 wave cases',ylabel='Wall seconds (up to 3 concurrent runs)',xticks=[0,1],xticklabels=['Travelling','Standing'],ylim=(0,10.5))
    ax.legend(fontsize=8);ax.grid(axis='y',alpha=.2)
    ax=axes[1,1];bx=data['fine_quadratic_bx']
    ax.bar([0,1],[bx['initial'],bx['final']],color=['.5',colors[3]])
    for i,v in enumerate(bx.values()):ax.text(i,v*1.2,f'{v:.5f}',ha='center')
    ax.axhline(1e-8,color='black',ls='--',label='Original gate: 1e-8')
    ax.set(yscale='log',ylim=(1e-9,1),xticks=[0,1],xticklabels=['Initialization','t=0.02'],ylabel='Maximum |Bx - 0.75|',title='Remaining failure: finer-shock Bx gate')
    ax.legend(loc='lower right',fontsize=8);ax.grid(axis='y',alpha=.2)
    fig.suptitle('Working short-time candidate, faster projection solve\n'
                 'All 40 bounded runs complete; full M1 remains unaccepted',fontsize=15)
    args.output.parent.mkdir(parents=True,exist_ok=True);fig.savefig(args.output,dpi=180)


if __name__=='__main__':main()
