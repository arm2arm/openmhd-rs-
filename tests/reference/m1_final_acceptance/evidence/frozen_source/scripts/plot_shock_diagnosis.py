#!/usr/bin/env python3
"""Plot preserved failing-cell energy traces; no acceptance gates are inferred."""
import argparse
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def read(path, cell):
    with path.open() as stream:
        return [{k: float(v) for k, v in r.items()} for r in csv.DictReader(stream) if int(r['id']) == cell]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory',type=Path)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    curves=[('traced','Spline baseline'),('centered_j0.15_b0','Anchored derivative trial'),
            ('facefit_j0.15_b0','Affine face-source trial')]
    fig,axes=plt.subplots(1,2,figsize=(10,3.9),layout='constrained')
    for name,label in curves:
        rows=read(args.directory/name/'energy_trace.csv',253)
        axes[0].plot([r['time'] for r in rows],[r['thermal'] for r in rows],label=label)
    axes[0].axhline(0,color='black',lw=.8)
    axes[0].set(title='All three trials exhaust thermal energy',ylabel='Thermal energy density')
    rows=read(args.directory/'traced/energy_trace.csv',253)
    for key,label in [('total_rate','Total-energy rate'),('magnetic_rate','Curl magnetic-energy rate'),
                      ('magnetic_rate_fv','FV induction comparison')]:
        axes[1].plot([r['time'] for r in rows],[r[key] for r in rows],label=label)
    axes[1].set(title='Baseline: fluid and curl rates disagree',ylabel='Energy density per unit time')
    for ax in axes:
        ax.set_xlabel('Simulation time');ax.grid(alpha=.2);ax.legend(fontsize=8)
        ax.ticklabel_format(axis='x',style='sci',scilimits=(0,0))
    fig.suptitle('Jittered Brio–Wu, 256 × 4 cells: cell 253 near the periodic seam',fontsize=12)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(args.output,dpi=170)


if __name__=='__main__':main()
