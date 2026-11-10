#!/usr/bin/env python3
"""Plot measured short-gate evidence; no new evolution or acceptance decision."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import NullLocator


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw',type=Path,help='Extracted bounded gate directory')
    parser.add_argument('output',type=Path)
    parser.add_argument('--title', default='Screened quadratic candidate: short checks only — full M1 remains open',
                        help='Figure label for an explicitly identified execution packet')
    args=parser.parse_args()
    load=lambda path:json.loads((args.raw/path).read_text())
    waves=load('waves_short/analysis.json')['waves']
    physics=load('physics_quick/runs.json')
    symmetry=load('shock_symmetry/runs.json')
    regular=load('waves_short/runs.json')['brio_k1.0_n256_regular']['bx']
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,2,figsize=(11,8),layout='constrained')
    for ax,field,label in ((axes[0,0],'B','Magnetic field'),(axes[0,1],'v','Velocity')):
        for row in waves:
            family=('regular' if row['jitter']==0 else 'jitter .15')+(' travelling' if row['parallel']==0 else ' standing')
            ax.loglog([8,16,32],row['errors'][field],'-o',label=f'{family}: {row["orders"][field]:.3f}')
        ax.set(title=label+' L1 error, t=.02',xlabel='Cells per direction N',ylabel='Volume-weighted L1')
        ax.set_xticks([8,16,32],labels=['8','16','32'])
        ax.xaxis.set_minor_locator(NullLocator())
        ax.legend(title='Fitted order (gate ≥1.8)',fontsize=8,title_fontsize=9)
        ax.grid(alpha=.2)
    ax=axes[1,0]
    for key,limit,label in (('mean_B_drift_over_Bscale_max',.001,'Mean-B drift / limit'),
                            ('limited_face_dimensionless_divB_RMS_max',.1,'Limited-face divergence RMS / limit')):
        values=[max(r['diagnostic_values'][key]/limit for r in physics.values()
                    if r['config']['case']=='orszag-tang' and r['config']['jitter']==.15 and r['config']['n']==n)
                for n in (16,32)]
        ax.plot([16,32],values,'-o',label=label)
    ax.axhline(1,color='black',ls='--',lw=1)
    ax.set(title='Jittered vortex diagnostics, t=.5',xlabel='N',ylabel='Diagnostic / registered limit',ylim=(0,3))
    ax.set_xticks([16,32],labels=['16 (fails; recorded)','32 (bounded gate)'])
    ax.legend(fontsize=8);ax.grid(alpha=.2)
    ax=axes[1,1]
    groups=[regular]
    for mode in ('columns','planar'):
        r=symmetry[mode+'_bulk-frame-heun-quadratic-v1_base']
        groups.append(dict(initial=r['initial_bx_error'],final=r['final_bx_error']))
    for stage,offset in (('initial',-.16),('final',.16)):
        ax.bar([x+offset for x in range(3)],[g[stage]['max'] for g in groups],width=.3,label=stage)
        for x,g in enumerate(groups):
            if g[stage]['max']==0:ax.text(x+offset,1.6e-16,'0',ha='center',fontsize=8)
    ax.plot([-.4,1.4],[1e-8,1e-8],'k--',lw=1,label='Gate on y-invariant meshes')
    ax.set_yscale('log')
    ax.set(title='Shock Bx departure, nx256 × ny4, t=.1',ylabel='max |Bx − .75|',ylim=(1e-16,1))
    ax.set_xticks([0,1,2],labels=['regular','columns','planar jitter\n(diagnostic only)'])
    ax.legend(fontsize=8);ax.grid(axis='y',alpha=.2)
    fig.suptitle(args.title,fontsize=14)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(args.output,dpi=160)


if __name__=='__main__':main()
