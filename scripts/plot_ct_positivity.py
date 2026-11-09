#!/usr/bin/env python3
"""Plot the conservative pressure guard's improvement and remaining limitation."""
import argparse
import csv
import json
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.ticker import NullLocator


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['analysis','extended','baseline','output']:
        p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    analysis=json.loads(args.analysis.read_text())
    fig,axes=plt.subplots(1,3,figsize=(14,4.2),layout='constrained')
    cases=[(args.baseline,'brio_n256_j0.15_t0.02_base','Original CT','#b64b31'),
           (args.extended,'brio_n256_j0.15_t0.04_base','Coupled limiter','#176c91')]
    for directory,name,label,color in cases:
        with (directory/name/'accepted_diagnostics.csv').open() as stream:
            rows=list(csv.DictReader(stream))
        t=[float(r['time']) for r in rows];p=[float(r['min_pressure']) for r in rows]
        axes[0].semilogy(t,p,color=color,label=label)
        if label=='Original CT':
            axes[0].plot(t[-1],p[-1],'x',color=color,markersize=8)
    axes[0].set(xlabel='Time',ylabel='Minimum accepted pressure',title='nx256 jittered Brio survives to t=.04')
    axes[0].set_xticks([0,.01,.02,.03,.04],['0','.01','.02','.03','.04']);axes[0].legend(fontsize=9)
    rates=analysis['frozen_cell645_rates']
    keys=['ReconstructedHlld','CellHlld','CellRusanov']
    values=[rates[k]['dp'] for k in keys]
    axes[1].bar(range(3),values,color=['#b64b31','#d99461','#176c91'])
    axes[1].axhline(0,color='black',linewidth=.7)
    axes[1].set_xticks(range(3),['Reconstructed\nHLLD','Cell-constant\nHLLD','Cell-constant\nRusanov'])
    axes[1].set(ylabel='Frozen pressure derivative',title='Lower-order update restores admissibility')
    for i,v in enumerate(values):axes[1].text(i,v+(1.5 if v>0 else -1.5),f'{v:.2f}',ha='center',va='bottom' if v>0 else 'top')
    axes[1].set_ylim(-22,68)
    rows=analysis['time_step_sensitivity']
    dt=[r['dt'] for r in rows];pressure=[r['min_pressure'] for r in rows]
    axes[2].loglog(dt,pressure,'o-',color='#176c91')
    axes[2].set_xticks(dt,['1e-4','5e-5','2.5e-5']);axes[2].xaxis.set_minor_locator(NullLocator())
    axes[2].set(xlabel='Timestep cap',ylabel='Minimum accepted pressure',title='Smaller dt still approaches p = 0')
    for ax in axes:ax.grid(alpha=.18)
    fig.suptitle('Coupled conservative limiter — improved robustness, physical accuracy still unpassed',fontsize=13)
    args.output.parent.mkdir(parents=True,exist_ok=True);fig.savefig(args.output,dpi=160)


if __name__=='__main__':main()
