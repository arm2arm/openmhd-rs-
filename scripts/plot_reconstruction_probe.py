#!/usr/bin/env python3
"""Plot frozen reconstruction diagnostics, explicitly separated from a solver fix."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('analysis',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    data=json.loads(args.analysis.read_text())
    assert data['all_checks_passed']
    fig,(left,right)=plt.subplots(1,2,figsize=(12,5),constrained_layout=True,
                                  gridspec_kw={'width_ratios':[1,1.5]})
    for shift,key,label,color in [(-.18,'h0.125_j0.15_kink_samples','Original stretched mesh','#bd433e'),
                                   (.18,'h0.03125_j0.15_kink_samples','Same pattern, compressed 1/4','#34815b')]:
        values=[data['kink_decomposition'][key][str(i)]['magnetic'][1] for i in [253,254,255]]
        bars=left.bar([k+shift for k in range(3)],values,width=.34,label=label,color=color)
        left.bar_label(bars,fmt='%.3f',padding=3,fontsize=9)
    left.axhline(-1,color='black',ls=':',label='Analytic By = −1')
    left.set(xticks=[0,1,2],xticklabels=['253','254','255'],xlabel='Cell ID',ylabel='Initial cell-centred By',
             ylim=(-1.45,.05),title='The curl broadens the magnetic jump')
    left.legend(loc='lower left',fontsize=8)
    cases={r['variant']:float(r['pressure_rate']) for r in data['cases']
           if r['height']=='0.125' and r['jitter']=='0.15' and r['stage']=='old'}
    names=['baseline','centered_all','zero_magnetic','riemann_Bx_254_255','riemann_By_254_255','riemann_B_254_255']
    labels=['Original reconstruction','Fit through central value','Zero magnetic slopes',
            'Analytic Bx inputs at 254/255','Analytic By inputs at 254/255','Analytic Bx + By at 254/255']
    colors=['#bd433e','#c88c36','#c88c36','#497ba2','#497ba2','#497ba2']
    bars=right.barh(range(len(names)),[cases[k] for k in names],color=colors)
    right.bar_label(bars,labels=[f'{cases[k]:+.3f}' for k in names],padding=3,fontsize=9)
    right.axvline(0,color='black',lw=.8)
    right.set(yticks=range(len(names)),yticklabels=labels,xlim=(-72,18),
              xlabel='Initial pressure rate in cell 253',title='Frozen inputs isolate the pressure deficit')
    right.invert_yaxis()
    right.grid(axis='x',alpha=.2)
    fig.suptitle('Smeared neighboring By drives most of the initial pressure deficit\nBlue bars are counterfactual Riemann inputs: no field overwrite, evolution or M1 acceptance',fontsize=12)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(args.output,dpi=170)
    plt.close(fig)


if __name__=='__main__':main()
