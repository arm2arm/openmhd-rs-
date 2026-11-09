#!/usr/bin/env python3
"""Independent AI verification of completed signal-study execution/archive layers.

Reuse prior independent numerical reports only after their hashes and exact raw
inputs match. No simulation and no production measurement imports.
"""
import argparse,gzip,hashlib,json,math,tarfile
from datetime import datetime,timezone
from pathlib import Path

parser=argparse.ArgumentParser();parser.add_argument('archive',type=Path);parser.add_argument('raw',type=Path);parser.add_argument('checkout',type=Path);parser.add_argument('copy',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
review=Path(__file__).resolve().parent;repository=review.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();digest=lambda b:hashlib.sha256(b).hexdigest()
archive=args.archive;raw=args.raw;copied=args.copy;checkout=args.checkout
index=json.loads((archive/'archive_sha256.json').read_text());actual={str(p.relative_to(archive)) for p in archive.rglob('*') if p.is_file() and p.name!='archive_sha256.json'};assert set(index)==actual
for name,expected in index.items():assert sha(archive/name)==expected,name
print('Compact archive exact file inventory and hashes verified:',len(index),'files',flush=True)
bytes_by_name={name:gzip.decompress((archive/(name+'.gz')).read_bytes()) for name in ['manifest.json','runs.json','summary.json','execution_summary.json']}
execution_bytes=(archive/'execution_provenance.json').read_bytes();measurement_bytes=(archive/'measurement_provenance.json').read_bytes();execution=json.loads(execution_bytes);measurement=json.loads(measurement_bytes)
for name,expected in execution['result_sha256'].items():
    source='execution_summary.json' if name=='summary.json' else name
    assert digest(bytes_by_name[source])==expected and sha(raw/source)==expected and sha(copied/source)==expected,(name,'original result hash')
assert sha(raw/'execution_provenance.json')==sha(copied/'execution_provenance.json')==digest(execution_bytes)==measurement['execution_provenance_sha256']
assert sha(raw/'measurement_provenance.json')==sha(copied/'measurement_provenance.json')==digest(measurement_bytes)
assert digest(bytes_by_name['execution_summary.json'])==measurement['execution_summary_sha256']
assert digest(bytes_by_name['runs.json'])==measurement['raw_runs_sha256']
assert digest(bytes_by_name['summary.json'])==measurement['summary_sha256']==sha(raw/'summary.json')==sha(copied/'summary.json')
assert execution['revision']==measurement['execution_revision'] and execution['configuration']['quick_physical_subset'] is False
source_hashes={}
for filename,expected in [('execution_sources.tar.gz',execution['source_sha256']),('measurement_sources.tar.gz',measurement['measurement_source_sha256'])]:
    if isinstance(expected,str):expected={'scripts/run_m1_wave_loop.py':expected}
    with tarfile.open(archive/filename) as tar:
        entries=tar.getmembers();assert all(m.isfile() for m in entries) and len({m.name for m in entries})==len(entries)
        found={m.name:digest(tar.extractfile(m).read()) for m in entries};assert found==expected,(filename,'source map mismatch')
    for name,expected_sha in found.items():assert sha((checkout if filename.startswith('execution') else repository)/name)==expected_sha
    source_hashes[filename]=found
assert sha(checkout/'target/release/vector-potential')==execution['binary_sha256']
print('Execution and corrected measurement layers separately linked; original+measurement source bytes and frozen binary verified.',flush=True)
manifest=json.loads(bytes_by_name['manifest.json']);runs=json.loads(bytes_by_name['runs.json']);summary=json.loads(bytes_by_name['summary.json']);original_summary=json.loads(bytes_by_name['execution_summary.json'])
assert set(manifest)==set(runs)==set(summary['runs'])==set(original_summary['runs']) and len(runs)==184
assert sum(n.startswith('alfven_') for n in runs)==64 and sum(n.startswith('loop_') for n in runs)==32 and sum(n.startswith('temporal_') for n in runs)==16 and sum(n.startswith('mean_') for n in runs)==72
raw_count=0
for name,r in runs.items():
    assert r['config']==manifest[name] and r['status']=='completed' and r['returncode']==0 and r['summary']['completed'] and r['summary']['time']==r['config']['target']==(.02 if r['config']['case']=='smooth' else 1.)
    assert r==original_summary['runs'][name]
    for key in ['config','command','returncode','status','summary','history','positive_and_conservative','sha256']:assert r[key]==summary['runs'][name][key],(name,key,'measurement changed evolution')
    assert set(r['sha256'])==({'initial.csv','final.csv','summary.json','history.json','run.log'} if r['config']['case']=='smooth' else {'initial.csv','checkpoint_0.25000000.csv','final.csv','summary.json','history.json','run.log'})
    for filename,expected in r['sha256'].items():
        assert sha(raw/name/filename)==expected and sha(copied/name/filename)==expected,(name,filename)
        raw_count+=1
assert raw_count==1032
selected=[]
for path in sorted((archive/'snapshots').rglob('*.gz')):
    rel=path.relative_to(archive/'snapshots');name=rel.parts[0];filename=rel.parts[1][:-3]
    assert len(rel.parts)==2 and filename.endswith('.csv') and digest(gzip.decompress(path.read_bytes()))==runs[name]['sha256'][filename]
    selected.append(str(rel))
expected_names={'alfven_bulk-frame-signal-v1_v1.0_j0.0_fixed_n64_base','alfven_bulk-frame-signal-v1_v1.0_j0.0_fixed_n64_boost','loop_bulk-frame-signal-v1_v0.0_j0.0_fixed_n64_base','loop_bulk-frame-signal-v1_v0.0_j0.0_comoving_n64_base','alfven_bulk-frame-signal-v1_v1.0_j0.0_fixed_n256_base','alfven_bulk-frame-signal-v1_v1.0_j0.0_fixed_n256_boost'}
assert {x.split('/')[0] for x in selected}==expected_names and len(selected)==18
print('All 184 completed run records, all 1032 raw hashes in original and full-copy locations, and 18 selected snapshot hashes verified.',flush=True)
review_index=json.loads((review/'archive_sha256.json').read_text());report_names=['signal_wave_matrix_report.json','loop_matrix_report.json','temporal_matrix_report.json','mean_matrix_report.json'];independent={}
for name in report_names:
    assert sha(review/name)==review_index[name];independent[name]=json.loads((review/name).read_text())
wave=independent['signal_wave_matrix_report.json'];all_loops=independent['loop_matrix_report.json'];loop={**all_loops,'runs':{n:r for n,r in all_loops['runs'].items() if r['config']['profile']=='bulk-frame-signal-v1'},'pairs':[p for p in all_loops['pairs'] if p['profile']=='bulk-frame-signal-v1']};temporal=independent['temporal_matrix_report.json'];mean=independent['mean_matrix_report.json']
prior={**wave['runs'],**loop['runs'],**{n:r for n,r in temporal['runs'].items() if r['config']['profile']=='bulk-frame-signal-v1'},**mean['runs']};assert set(prior)==set(runs)
checked_numbers=0;max_absolute_difference=0.;maximum_difference_label=None
def close(a,b,label):
    global checked_numbers,max_absolute_difference,maximum_difference_label
    assert math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=5e-10,abs_tol=2e-17),(label,a,b)
    checked_numbers+=1
    if abs(a-b)>max_absolute_difference:max_absolute_difference=abs(a-b);maximum_difference_label=label
def norm_equal(a,b,label):
    for k in ['L1','L2','max']:close(a[k],b[k],(label,k))
for name,prior_r in prior.items():
    r=runs[name];assert prior_r['input_sha256']==r['sha256'] and prior_r['config']==r['config'] and prior_r['command']==r['command'] and prior_r['positive_and_conservative']==r['positive_and_conservative']
    for key,value in prior_r['summary'].items():assert r['summary'][key]==value,(name,key)
    for stage,m in prior_r['measurements'].items():
        measured=m.get('norms',m.get('physical_errors',m.get('passive_errors')))
        for key,values in (measured or {}).items():
            if isinstance(values,dict):norm_equal(values,summary['runs'][name]['errors'][stage][key],(name,stage,key))
for reviewed in [wave,loop,mean]:
    for pair in reviewed['pairs']:
        found=[p for p in summary['pairs'] if p['names']==pair['names']];assert len(found)==1;measured=found[0]
        assert pair['status']==measured['status'] and pair['pairing_valid']==measured['pairing_valid'] and pair['positive_and_conservative']==measured['positive_and_conservative'] and pair['matching_auxiliary_roots']==measured['matching_auxiliary_roots']
        final=pair['times']['final']
        for key,value in final['errors'].items():norm_equal(value,measured['errors'][key],(pair['names'][0],key))
        geometry=final.get('geometry',final)
        for key in ['position_max','relative_volume_max']:close(geometry[key],measured['errors'][key],(pair['names'][0],key))
        if 'B_relative_L1' in pair:close(pair['B_relative_L1'],measured['B_relative_L1'],(pair['names'][0],'B_relative_L1'))
        if 'normalization_verdicts' in pair:
            assert pair['normalization_verdicts']==measured['normalization_verdicts']
            if 'normalization_scales' in pair:assert pair['normalization_scales']==measured['normalization_scales']
            for convention,values in pair['relative_L1'].items():
                for key,value in values.items():close(value,measured['relative_L1'][convention][key],(pair['names'][0],convention,key))
assert len(summary['pairs'])==84
for ladder in wave['ladders']:
    found=[x for x in summary['alfven_convergence'] if (x['parallel'],x['jitter'],x['motion'])==(ladder['parallel'],ladder['jitter'],ladder['motion'])];assert len(found)==1;m=found[0]
    assert m['gate']==('pass' if ladder['gate'] else 'fail') and [row['n'] for row in m['rows']]==ladder['n']
    for a,b in zip(ladder['B_L1'],[row['B_L1'] for row in m['rows']]):close(a,b,'spatial errors')
    close(ladder['finest_three']['order'],m['finest_three_order'],'spatial fitted slope');close(ladder['finest_three']['residual_slope_SE'],m['finest_three_order_standard_error'],'spatial fit SE');close(ladder['finest_B_L1_over_amplitude'],m['finest_relative_B_L1'],'spatial relative B')
assert len(summary['alfven_convergence'])==8
for ladder in temporal['ladders']:
    if ladder['profile']!='bulk-frame-signal-v1':continue
    for i,row in enumerate(ladder['comparisons']):
        found=[x for x in summary['temporal'] if x['name']==row['name']];assert len(found)==1;m=found[0]
        assert m['reference']==row['reference'] and m['status']=='completed' and m['dt']==row['dt_cap'] and m['dt_max_actual']==row['dt_cap'] and m['cap_reached']
        for key,values in m['errors'].items():norm_equal(row['times']['final']['errors'][key],values,(row['name'],key))
        if i:
            for key,value in m['orders_from_previous_dt'].items():
                expected=ladder['adjacent_cap_ratio_L1_orders']['final'][key][i-1]
                if value is None:assert expected is None
                else:close(value,expected,(row['name'],key,'temporal slope'))
assert len(summary['temporal'])==12
for series in mean['refinement_observations']:
    variable='dt' if series['variable']=='dt_cap' else 'n'
    found=[x for x in summary['mean_refinement'] if (x['profile'],x['jitter'],x['variable'])==(series['profile'],series['jitter'],variable)];assert len(found)==1;m=found[0]
    assert [x[0] for x in m['values']]==series['coordinates']
    for a,b in zip([x[1] for x in m['values']],series['B_boost_L1']):close(a,b,'mean refinement B residual')
    assert len(m['successive_B_L1_orders'])==len(series['successive_orders'])
    for a,b in zip(m['successive_B_L1_orders'],series['successive_orders']):
        if a is None:assert b is None
        else:close(a,b,'mean residual slope')
assert len(summary['mean_refinement'])==12
for source in [wave['source_inputs'],all_loops['source_inputs']['bulk-frame-signal-v1'],temporal['source_inputs']['bulk-frame-signal-v1'],mean['source_inputs']]:
    assert source['source_sha256']==execution['source_sha256'] and source['binary_sha256']==execution['binary_sha256']
print('Reanalysis agrees with independent reviews for all 184 runs, 84 boost pairs, 8 spatial ladders, 12 temporal comparisons and 12 mean refinement observations; failures and diagnostic-only scope preserved.',flush=True)
changes=[]
def diff(a,b,path=''):
    if type(a)!=type(b):changes.append({'path':path,'kind':'type','old':str(type(a)),'new':str(type(b))});return
    if isinstance(a,dict):
        for key in sorted(a.keys()|b.keys()):
            if key not in a:changes.append({'path':path+'/'+key,'kind':'added','value':b[key]})
            elif key not in b:changes.append({'path':path+'/'+key,'kind':'removed','value':a[key]})
            else:diff(a[key],b[key],path+'/'+key)
    elif isinstance(a,list):
        for i in range(max(len(a),len(b))):
            if i>=len(a):changes.append({'path':path+'/'+str(i),'kind':'added','value':b[i]})
            elif i>=len(b):changes.append({'path':path+'/'+str(i),'kind':'removed','value':a[i]})
            else:diff(a[i],b[i],path+'/'+str(i))
    elif a!=b:changes.append({'path':path,'kind':'changed','old':a,'new':b})
diff(original_summary,summary)
expected_paths={f'/alfven_convergence/{i}/{key}' for i in range(8) for key in ['finest_three_order_standard_error','uncertainty_scope']}

expected_paths|={f'/pairs/{i}/normalization_note' for i in range(36,68)}
expected_paths|={f'/temporal/{i}/{key}' for i in range(12) for key in ['cap_reached','dt_max_actual','timestep_note']}
assert {c['path'] for c in changes}<=expected_paths
assert all(c['kind']=='added' or c['path'].endswith('/normalization_note') and c['kind']=='changed' and isinstance(c['old'],str) and isinstance(c['new'],str) for c in changes)

report={'created_utc':datetime.now(timezone.utc).isoformat(),'scope':'Independent AI audit of completed 184-run signal-study execution/measurement/compact archive and full raw copy only. Final figure/document assessment is separate; no full M1 acceptance.',
 'locations':{'archive':str(archive),'raw':str(raw),'checkout':str(checkout),'full_raw_copy':str(copied)},
 'archive_index_sha256':sha(archive/'archive_sha256.json'),'archive_file_sha256':index,'execution_provenance_sha256':digest(execution_bytes),'measurement_provenance_sha256':digest(measurement_bytes),
 'execution_source_sha256':execution['source_sha256'],'measurement_source_sha256':source_hashes['measurement_sources.tar.gz'],'binary_sha256':execution['binary_sha256'],
 'original_result_sha256':execution['result_sha256'],'corrected_summary_sha256':measurement['summary_sha256'],'reused_independent_report_sha256':{n:sha(review/n) for n in report_names},
 'review_summary':{'runs':184,'raw_files_verified_at_each_location':raw_count,'selected_snapshots':len(selected),'complete_signal_loop_runs':32,'loop_boost_passes':16,'mean_diagnostic_pairs':sum(p['case']=='smooth' and p['status'].startswith('diagnostic') for p in summary['pairs']),'mean_comparator_passes':sum(p['case']=='smooth' and p['status']=='pass' for p in summary['pairs']),'wave_spatial_passes':sum(x['gate']=='pass' for x in summary['alfven_convergence']),
  'wave_boost_passes_both':sum(x['case']=='alfven' and x['status']=='pass under both reported normalizations' for x in summary['pairs']),'wave_boost_failures_both':sum(x['case']=='alfven' and x['status']=='fail under both reported normalizations' for x in summary['pairs']),
  'numeric_values_cross_checked':checked_numbers,'maximum_absolute_numeric_difference':max_absolute_difference,'maximum_difference_label':maximum_difference_label,'execution_to_measurement_changes':len(changes),'existing_numeric_results_and_gate_labels_unchanged':True},
 'execution_to_measurement_diff':changes,'pending':'Combined final figures/document review and bounded overall assessment.'}
args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print('SUMMARY',json.dumps(report['review_summary']),flush=True);print('Layer differences',[(x['path'],x['kind']) for x in changes],flush=True)
