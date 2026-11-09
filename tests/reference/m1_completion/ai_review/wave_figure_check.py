#!/usr/bin/env python3
"""Bounded AI figure audit: verify plotted artists against immutable wave reports."""
import hashlib,json,math,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[4];review=ROOT/'tests/reference/m1_completion/ai_review';figdir=ROOT/'docs/images/m1_completion'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
provenance=json.loads((figdir/'wave_review_plot_provenance.json').read_text())
assert provenance['script_sha256']==sha(ROOT/'scripts/plot_m1_wave_review.py')
archive=json.loads((review/'archive_sha256.json').read_text())
reports=[]
for name in ['original_wave_matrix_report.json','signal_wave_matrix_report.json']:
    assert sha(review/name)==provenance['input_report_sha256'][name]==archive[name]
    r=json.loads((review/name).read_text());assert len(r['runs'])==64 and len(r['pairs'])==32 and len(r['ladders'])==8;reports.append(r)
for name,digest in provenance['figure_sha256'].items():assert sha(figdir/name)==digest
print('Plot/source/report hashes verified; inputs are the reviewed 128-run wave matrix only.')
sys.path.insert(0,str(ROOT/'scripts'));import plot_m1_wave_review as plot
captured=[];original_close=plot.plt.close
def capture(fig=None):
    if hasattr(fig,'axes'):captured.append(fig)
    else:original_close(fig)
plot.plt.close=capture
repeated=Path('/tmp/openmhd-ai-review/reviewed_wave_reproduction')
sys.argv=['plot_m1_wave_review.py','--review',str(review),'--output',str(repeated)]
plot.main();plot.plt.close=original_close
assert len(captured)==2
spatial,boost=captured
assert len(spatial.axes)==4 and len(boost.axes)==3
labels=['Original','Signal completion']
for row,jitter in enumerate([0.,.15]):
    for column,parallel in enumerate([0.,1.]):
        ax=spatial.axes[2*row+column];lines=ax.get_lines();assert len(lines)==5
        for rp,(report,label) in enumerate(zip(reports,labels)):
            for mi,motion in enumerate(['fixed','comoving']):
                matches=[s for s in report['ladders'] if (s['parallel'],s['jitter'],s['motion'])==(parallel,jitter,motion)];assert len(matches)==1;s=matches[0]
                line=lines[2*rp+mi];expected=np.array(s['B_L1'])/.1
                assert np.array_equal(line.get_xdata(),[32,64,128,256]) and np.array_equal(line.get_ydata(),expected)
                verdict=s['finest_three']['order']>=1.8 and expected[-1]<=.02 and all(report['runs'][f"alfven_{report['profile']}_v{parallel}_j{jitter}_{motion}_n{n}_base"]['positive_and_conservative'] for n in [32,64,128,256])
                assert bool(verdict)==s['gate']
                assert line.get_label()==f"{label}, {motion}: p={s['finest_three']['order']:.2f}, {'PASS' if verdict else 'FAIL'}"
                assert line.get_linestyle()==('-' if motion=='fixed' else '--')
                assert ax.get_ylim()[0]<float(min(expected)) and ax.get_ylim()[1]>float(max(expected))
        assert np.array_equal(lines[-1].get_ydata(),[.02,.02])
        assert ax.get_xscale()==ax.get_yscale()=='log'
print('All 16 spatial curves map to correct profile/wave/jitter/motion; N and /0.1 normalization, labels, fitted-order and magnitude gates verified; no curve clipping.')
configs=[(v,j,m) for v in [0.,1.] for j in [0.,.15] for m in ['fixed','comoving']]
row_labels=[f"{'Travelling' if v==0 else 'Standing'}, {'regular' if j==0 else 'jittered'}, {m}" for v,j,m in configs]
red_counts=[];ranges=[]
for ax,report,label in zip(boost.axes[:2],reports,labels):
    assert len(ax.images)==1
    matrix=np.empty((8,4))
    for i,(v,j,m) in enumerate(configs):
        for col,n in enumerate([32,64,128,256]):
            p=[p for p in report['pairs'] if (p['parallel'],p['jitter'],p['motion'],p['n'])==(v,j,m,n)];assert len(p)==1
            matrix[i,col]=p[0]['times']['final']['errors']['B']['L1']/.1
    image=ax.images[0];assert np.array_equal(np.asarray(image.get_array()),np.maximum(matrix,1e-16))
    assert image.norm.vmin==1e-16 and float(np.max(matrix))<=image.norm.vmax
    assert image.norm.vmax==max(1e-7,10**math.ceil(math.log10(max(p['times']['final']['errors']['B']['L1']/.1 for r in reports for p in r['pairs']))))
    texts={tuple(t.get_position()):t.get_text() for t in ax.texts};assert len(texts)==32
    for (i,j),v in np.ndenumerate(matrix):assert texts[(j,i)]==f'{v:.1e}'
    rectangles={(round(p.get_x()+.48),round(p.get_y()+.48)) for p in ax.patches}
    expected={(j,i) for (i,j),v in np.ndenumerate(matrix) if v>1e-8};assert rectangles==expected
    passed=sum(all(p['normalization_verdicts'].values()) for p in report['pairs']);assert passed==report['review_summary']['boost_pass_both']
    assert ax.get_title()==f'{label}\n{passed}/32 full-field pairs pass both scales'
    assert [t.get_text() for t in ax.get_xticklabels()]==['32','64','128','256']
    ranges.append((float(matrix.min()),float(matrix.max()),image.norm.vmin,image.norm.vmax));red_counts.append(len(rectangles))
assert [t.get_text() for t in boost.axes[0].get_yticklabels()]==row_labels
print('Both 8x4 heat maps match exact configurations and magnetic vector L1/0.1; annotations and red magnetic-only threshold boxes verified.')
print('Magnetic red-box counts:',red_counts,'(full-field title counts independently 13/32 and 31/32); raw/color ranges:',ranges)
for name in ['reviewed_wave_convergence.png','reviewed_wave_boost.png','wave_review_plot_provenance.json']:
    assert (figdir/name).read_bytes()==(repeated/name).read_bytes(),name
    print('Byte-identical fresh reproduction:',name,sha(figdir/name))
for fig in captured:original_close(fig)
print('Bounded figure audit complete; loop/temporal/global archive review remains pending.')
