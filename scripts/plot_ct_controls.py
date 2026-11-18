#!/usr/bin/env python3
"""Scientific figure for the bounded CT comparator, including retained failures."""
import argparse
import csv
import json
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.ticker import NullLocator


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory',type=Path)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    a=json.loads((args.directory/'analysis.json').read_text())
    fig,axes=plt.subplots(1,3,figsize=(14,4.2),layout='constrained')
    colors={256:'#b64b31',512:'#176c91'}
    for n in [256,512]:
        name=f'brio_n{n}_j0.15_t0.02_base'
        with (args.directory/name/'accepted_diagnostics.csv').open() as stream:
            rows=list(csv.DictReader(stream))
        time=[float(r['time']) for r in rows]
        pressure=[float(r['min_pressure']) for r in rows]
        axes[0].semilogy(time,pressure,color=colors[n],label=f'nx{n}')
        if a['runs'][name]['status']=='failed':
            axes[0].plot(time[-1],pressure[-1],'x',color=colors[n],markersize=8)
            axes[0].annotate('pressure failure',xy=(time[-1],pressure[-1]),xytext=(.003,2e-6),
                             arrowprops=dict(arrowstyle='->',color=colors[n]),fontsize=9)
    axes[0].set(xlabel='Time',ylabel='Minimum accepted pressure',title='Jittered Brio: stability')
    axes[0].set_xticks([0.,.005,.01,.015,.02],['0','.005','.010','.015','.020'])
    axes[0].legend()
    for i,n in enumerate([256,512]):
        r=a['runs'][f'brio_n{n}_j0.15_t0.02_base']
        axes[1].bar([i-.18,i+.18],[r['initial_bx_error'],r['final_bx_error']],width=.32,
                    color=[colors[n],colors[n]],alpha=.8)
    axes[1].axhline(1e-8,color='black',linestyle='--',label='Unchanged gate: 1e-8')
    axes[1].set(yscale='log',ylim=(3e-9,1.),ylabel='max |Bx - 0.75|',title='CT does not fix cell Bx')
    axes[1].set_xticks([0,1],['nx256\ninitial / last accepted','nx512\ninitial / final'])
    axes[1].legend(fontsize=8,loc='center')
    for v,color in [(0.,'#176c91'),(1.,'#b64b31')]:
        for field,style in [('B','o-'),('v','s--')]:
            names=[f'wave_j0.15_v{v}_n{n}_base' for n in [8,16,32]]
            errors=[a['runs'][n]['final_errors'][field]['L1'] for n in names]
            order=next(r['orders'][field] for r in a['spatial'] if r['jitter']==.15 and r['parallel']==v)
            axes[2].loglog([8,16,32],errors,style,color=color,
                label=f'{"travelling" if v==0 else "standing"} {field}: {order:.2f}')
    axes[2].set(xlabel='Resolution N',ylabel='Volume-weighted L1 error',title='Jittered waves: target order ≥ 1.8')
    axes[2].set_xticks([8,16,32],['8','16','32']);axes[2].legend(fontsize=8)
    axes[2].xaxis.set_minor_locator(NullLocator())
    for ax in axes: ax.grid(alpha=.18)
    fig.suptitle('Full Voronoi CT comparator — diagnostic result, not an accepted M1 fix',fontsize=13)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(args.output,dpi=160)


if __name__=='__main__':
    main()
