#!/usr/bin/env python3
"""Recompute the failed HLL vortex diagnostic from preserved cell CSVs; no evolution."""
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import tarfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, Normalize
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'tests/reference/m1_hll_campaign/bounded_failure'
OUTPUT=ROOT/'docs/images/m1_completion/hll_vortex_diagnostic.png'


def main():
    records=json.loads((ARCHIVE/'selected_runs.json').read_text())
    hashes=json.loads((ARCHIVE/'raw_selected_sha256.json').read_text())
    arrays={};report={}
    with tarfile.open(ARCHIVE/'raw_selected.tar.gz') as tar:
        for name,digest in hashes.items():
            raw=tar.extractfile(name).read()
            if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('changed raw file '+name)
            if not name.endswith('final.csv'):continue
            key=name.removesuffix('/final.csv')
            if digest!=records[key]['sha256']['final.csv']:raise ValueError('run hash mismatch '+key)
            rows=list(csv.DictReader(io.StringIO(raw.decode())))
            a={k:np.array([float(r[k]) for r in rows]) for k in rows[0]}
            if len(rows)!=1024 or not np.array_equal(a['id'],np.arange(1024)):raise ValueError('wrong IDs/grid')
            b=np.hypot(np.hypot(a['bx'],a['by']),a['bz'])
            d=a['div_b_limited'];volume=math.fsum(a['volume'])
            scaled=np.sqrt(a['volume']/math.pi)*d/(b+1e-12/math.sqrt(4*math.pi))
            weights=a['volume']*scaled**2
            total=math.fsum(weights);rms=math.sqrt(total/volume)
            dimensional=math.sqrt(math.fsum(a['volume']*d*d)/volume)
            expected=records[key]['summary']['final']['div_B_limited']
            if abs(rms-expected['dimensionless']['rms'])>1e-12:raise ValueError('scaled reduction mismatch')
            if abs(dimensional-expected['dimensional']['rms'])>1e-12:raise ValueError('dimensional reduction mismatch')
            order=np.argsort(weights)[::-1]
            report[key]=dict(dimensionless_rms=rms,dimensional_rms=dimensional,
                gate_limit=.1,passed=rms<=.1,top_two_squared_norm_fraction=float(sum(weights[order[:2]])/total),
                top_cells=[dict(id=int(a['id'][i]),B=float(b[i]),divergence=float(d[i]),scaled=float(scaled[i])) for i in order[:4]])
            arrays[key]=(b,d,scaled,a)
    fig,axes=plt.subplots(2,3,figsize=(11,7.3),layout='constrained')
    titles=(r'$|B|$',r'$|\nabla\cdot B|$ (limited face)',r'$h\,|\nabla\cdot B|/(|B|+10^{-12}B_0)$')
    norms=(LogNorm(5e-4,.8),Normalize(0,1.6),LogNorm(1e-4,10))
    images=[]
    for row,solver in enumerate(('hlld','hll')):
        key=solver+'/orszag-tang_n32_j0.0_base';b,d,s,a=arrays[key]
        for col,values in enumerate((b,np.abs(d),np.abs(s))):
            # A positive plotting floor only affects log colours, never the reduction above.
            z=np.maximum(values,1e-15).reshape(32,32)
            im=axes[row,col].imshow(z,origin='lower',extent=(0,1,0,1),norm=norms[col],cmap='viridis')
            axes[row,col].set(xlabel='x',ylabel='y',xticks=[0,.5,1],yticks=[0,.5,1])
            if row==0:axes[row,col].set_title(titles[col],fontsize=11);images.append(im)
            if row==1:
                ids=[258,765]
                axes[row,col].scatter(a['x'][ids],a['y'][ids],facecolors='none',edgecolors='white',s=75,linewidths=1)
        r=report[key]
        axes[row,0].text(.02,.98,solver.upper(),transform=axes[row,0].transAxes,va='top',color='white',weight='bold')
        axes[row,2].text(.03,.98,f'RMS = {r["dimensionless_rms"]:.5f}\n{"PASS" if r["passed"] else "FAIL"} (limit 0.1)',
                         transform=axes[row,2].transAxes,va='top',color='white',fontsize=10)
    for col,im in enumerate(images):fig.colorbar(im,ax=axes[:,col],shrink=.9,pad=.02)
    fig.suptitle('Orszag–Tang, regular N32, t = 0.5: HLL fails the unchanged normalized divergence gate',fontsize=12)
    fig.supxlabel('White circles: two weak-field cells contribute 98.35% of HLL’s squared normalized error.',fontsize=10)
    OUTPUT.parent.mkdir(parents=True,exist_ok=True);fig.savefig(OUTPUT,dpi=170);plt.close(fig)
    (ARCHIVE/'independent_reduction.json').write_text(json.dumps(report,indent=2)+'\n')
    provenance=dict(inputs=hashes,plot_sha256=hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),numpy=np.__version__,matplotlib=matplotlib.__version__,
        scope='Hash-verified postprocessing of existing snapshots; no new numerical evolution or threshold change.')
    OUTPUT.with_suffix('.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
