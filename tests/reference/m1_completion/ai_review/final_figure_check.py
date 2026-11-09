#!/usr/bin/env python3
"""Independent AI artist/mapping and raw-vs-archive reproduction audit."""
import gzip,hashlib,json,math,platform,sys
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import matplotlib
ROOT=Path(__file__).resolve().parents[4];review=ROOT/'tests/reference/m1_completion/ai_review';figdir=ROOT/'docs/images/m1_completion';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
archive_root=ROOT/'tests/reference/m1_completion';raw_root=ROOT/'results/issue7_completion_20261106'
source_sha=sha(ROOT/'scripts/plot_m1_completion.py');index=json.loads((review/'archive_sha256.json').read_text())
for name in ['original_archive_report.json','candidate_archive_report.json']:
    assert sha(review/name)==index[name]
    report=json.loads((review/name).read_text());directory=archive_root/('original' if name.startswith('original') else 'candidate');assert sha(directory/'archive_sha256.json')==report['archive_index_sha256']
inputs={};summaries={}
for name in ['original','candidate','prescribed']:
    archive=archive_root/name;raw=raw_root/name;file_index=json.loads((archive/'archive_sha256.json').read_text())
    for path,digest in file_index.items():assert sha(archive/path)==digest
    compressed=(archive/'summary.json.gz').read_bytes();uncompressed=gzip.decompress(compressed);assert uncompressed==(raw/'summary.json').read_bytes()
    provenance=json.loads((raw/'measurement_provenance.json').read_text());assert hashlib.sha256(uncompressed).hexdigest()==provenance['summary_sha256']
    inputs[name]={'archive_index_sha256':sha(archive/'archive_sha256.json'),'compressed_summary_sha256':hashlib.sha256(compressed).hexdigest(),'summary_sha256':hashlib.sha256(uncompressed).hexdigest()}
    summaries[name]=json.loads(uncompressed)
assert [len(summaries[n]['runs']) for n in ['original','candidate','prescribed']]==[112,184,32]
sys.path.insert(0,str(ROOT/'scripts'));import plot_m1_completion as plot
capture=[];close=plot.plt.close
def capture_close(fig=None):
    if hasattr(fig,'axes'):capture.append(fig)
    else:close(fig)
plot.plt.close=capture_close
compact_out=Path('/tmp/openmhd-ai-review/final_figures_compact');raw_out=Path('/tmp/openmhd-ai-review/final_figures_raw')
sys.argv=['plot_m1_completion.py','--original',str(archive_root/'original'),'--candidate',str(archive_root/'candidate'),'--prescribed',str(archive_root/'prescribed'),'--output',str(compact_out)]
plot.main();assert len(capture)==4
spatial,boost,temporal,prescribed=capture
profiles=[(summaries['original'],'paper-global-v2','#bc5045'),(summaries['candidate'],'bulk-frame-signal-v1','#266ca0')]
def line_equal(line,x,y):
    assert np.array_equal(line.get_xdata(),x) and np.array_equal(line.get_ydata(),y)
def not_clipped(ax,x,y):
    assert min(ax.get_xlim())<min(x)<=max(x)<max(ax.get_xlim())
    assert min(ax.get_ylim())<min(y)<=max(y)<max(ax.get_ylim())
for row,jitter in enumerate([0.,.15]):
  for col,parallel in enumerate([0.,1.]):
    ax=spatial.axes[2*row+col];lines=ax.get_lines();assert len(lines)==5
    for pi,(summary,label,color) in enumerate(profiles):
      for mi,(motion,style) in enumerate([('fixed','-'),('comoving','--')]):
        matching=[s for s in summary['alfven_convergence'] if (s['jitter'],s['parallel'],s['motion'])==(jitter,parallel,motion)];assert len(matching)==1;s=matching[0]
        assert len(s['rows'])==4 and all(r['status']=='completed' for r in s['rows']);x=[r['n'] for r in s['rows']];y=[r['B_L1']/.1 for r in s['rows']]
        assert x==[32,64,128,256];line=lines[2*pi+mi];line_equal(line,x,y);assert line.get_label()==f'{label}, {motion}, p={s["finest_three_order"]:.2f}' and line.get_linestyle()==style and line.get_color()==color
        not_clipped(ax,x,y)
    line_equal(lines[-1],[0,1],[.02,.02]);assert lines[-1].get_label()=='N256 relative-error bound'
    assert ax.get_xscale()==ax.get_yscale()=='log' and ax.get_ylabel()=='Magnetic vector L1 / 0.1'
assert 'target p ≥ 1.8' in spatial._suptitle.get_text() and 'failures retained' in spatial._suptitle.get_text()
print('Spatial: all 16 curves, resolution/profile/motion/jitter mapping, B/.1 normalization, fitted orders and labelled .02 N256 bound verified; no clipping.')
boost_points=0;floor_count=0
for ax,case in zip(boost.axes,['alfven','loop']):
    collections=iter(ax.collections);count=0
    for data,label,color in profiles:
      for jitter in [0.,.15]:
        for n in [32,64,128,256]:
            rows=[p for p in data['pairs'] if p['case']==case and p['n']==n and p['jitter']==jitter];assert len(rows)==(4 if case=='alfven' else 2)
            scale=.1 if case=='alfven' else .001/math.sqrt(4*math.pi);raw=[p['errors']['B']['L1']/scale for p in rows];x=[n]*len(rows);y=[max(v,1e-17) for v in raw]
            collection=next(collections);assert np.array_equal(collection.get_offsets(),np.column_stack([x,y]));not_clipped(ax,x,y);count+=1;boost_points+=len(rows);floor_count+=sum(v<1e-17 for v in raw)
            assert np.allclose(collection.get_facecolors()[0,:3],matplotlib.colors.to_rgb(color),rtol=0,atol=0)
    assert count==16 and len(ax.collections)==16;line=ax.get_lines()[0];gate=1e-8 if case=='alfven' else .001;line_equal(line,[0,1],[gate,gate]);assert line.get_label()=='B relative-L1 gate'
    assert ax.get_xscale()==ax.get_yscale()=='log'
assert boost_points==96 and 'Magnetic part only' in boost._suptitle.get_text() and 'log-display floor 1e−17' in boost._suptitle.get_text()
print('Boost: all 96 magnetic-only scatter values, profile/jitter/N grouping, amplitude scales and separate wave/loop gates verified; floor-active points:',floor_count)
line_index=0;phi_floor_count=0
for data,label,color in profiles:
  for parallel,marker in [(0.,'o'),(1.,'s')]:
    for jitter,style in [(0.,'-'),(.15,'--')]:
      rows=sorted([r for r in data['temporal'] if f'_v{parallel}_j{jitter}_' in r['name']],key=lambda r:r['dt']);assert len(rows)==3 and all(r['status']=='completed' for r in rows)
      x=[r['dt'] for r in rows];assert x==[.0001,.0002,.0004]
      for ai,key in enumerate(['B','phi']):
        y=[r['errors'][key]['L1'] if key=='B' else max(r['errors'][key]['L1'],1e-30) for r in rows];line=temporal.axes[ai].get_lines()[line_index]
        line_equal(line,x,y);not_clipped(temporal.axes[ai],x,y);assert line.get_color()==color and line.get_marker()==marker and line.get_linestyle()==style
      assert temporal.axes[0].get_lines()[line_index].get_label()==f'{label}, v∥={parallel}, j={jitter}'
      phi_floor_count+=sum(r['errors']['phi']['L1']<1e-30 for r in rows);line_index+=1
assert line_index==8 and all(len(ax.get_lines())==8 and ax.get_xscale()==ax.get_yscale()=='log' for ax in temporal.axes)
assert all(ax.get_xlabel()=='dt cap' and ax.get_ylabel()=='L1 vs same-grid dt=0.000025' for ax in temporal.axes)
assert 'frozen-C1' in temporal._suptitle.get_text() and 'floor at 1e−30' in temporal.axes[1].get_title()
print('Temporal: all 16 B/phi curves and cap/reference labels verified; nonmonotone original standing B retained; phi floor-active values:',phi_floor_count)
pres=summaries['prescribed'];left,right=prescribed.axes;assert len(left.get_lines())==3 and len(right.get_lines())==4
for i,jitter in enumerate([0.,.15]):
    s=next(x for x in pres['fixed_convergence'] if x['jitter']==jitter);assert s['gate']=='pass';x=[r['n'] for r in s['rows']];y=[r['A_L1_over_peak'] for r in s['rows']];line_equal(left.get_lines()[i],x,y);not_clipped(left,x,y);assert left.get_lines()[i].get_label()==f'jitter={jitter}, pass'
line_equal(left.get_lines()[-1],[0,1],[.1,.1]);assert left.get_lines()[-1].get_label()=='N256 bound'
i=0
for jitter,style in [(0.,'-'),(.15,'--')]:
    for motion in ['fixed','comoving']:
        rows=sorted([r for n,r in pres['runs'].items() if n.endswith('_base') and r['config']['motion']==motion and r['config']['jitter']==jitter],key=lambda r:r['config']['n']);assert len(rows)==4 and all(r['status']=='completed' for r in rows)
        x=[r['config']['n'] for r in rows];y=[r['diagnostics']['final']['magnetic_energy']/r['diagnostics']['initial']['magnetic_energy'] for r in rows];line=right.get_lines()[i];line_equal(line,x,y);not_clipped(right,x,y);assert line.get_label()==f'{motion}, jitter={jitter}' and line.get_linestyle()==style;i+=1
assert 'separate from coupled MHD' in prescribed._suptitle.get_text() and 'No fluid energy budget' in prescribed._suptitle.get_text()
print('Prescribed: both fixed-A ladders/labels/bound and all four discrete magnetic-energy ratios verified; constant-flow/coupled-MHD distinction explicit.')
for fig in capture:close(fig)
plot.plt.close=close
sys.argv=['plot_m1_completion.py','--original',str(raw_root/'original'),'--candidate',str(raw_root/'candidate'),'--prescribed',str(raw_root/'prescribed'),'--output',str(raw_out)];plot.main()
assert sha(ROOT/'scripts/plot_m1_completion.py')==source_sha
figures={}
for name in ['alfven_convergence.png','boost_comparison.png','temporal.png','prescribed_loop.png']:
    assert (compact_out/name).read_bytes()==(raw_out/name).read_bytes()==(figdir/name).read_bytes(),name;figures[name]=sha(figdir/name);print('Byte-identical raw/compact/checked-in figure:',name,figures[name])
report={'created_utc':datetime.now(timezone.utc).isoformat(),'reviewer':'Independent AI review; not scientific acceptance','scope':'Final combined numerical figures only, using verified completed original/candidate/prescribed summaries. No simulations or solver changes.',
 'plot_source_sha256':source_sha,'python':platform.python_version(),'numpy':np.__version__,'matplotlib':matplotlib.__version__,'input_provenance':inputs,'figure_sha256':figures,'raw_output':str(raw_out),'compact_output':str(compact_out),
 'artist_checks':{'spatial_curves':16,'boost_scatter_points':boost_points,'temporal_curves':16,'prescribed_curves':6,'boost_display_floor':1e-17,'boost_floor_active_points':floor_count,'phi_display_floor':1e-30,'phi_floor_active_values':phi_floor_count,'unlabelled_or_clipped_values':False},
 'byte_identical_all_three_locations':True,'figures_visually_inspected':True,'scientific_scope':'B-only boost figure is not the complete field gate; temporal figure shows finite-reference cap differences, not a new pass/fail or second-order claim. Prescribed energy/transport remains distinct from coupled MHD.'}
(review/'final_figure_report.json').write_text(json.dumps(report,indent=2)+'\n')
