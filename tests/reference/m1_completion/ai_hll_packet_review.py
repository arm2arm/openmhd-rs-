from pathlib import Path
import json,gzip,hashlib,sys,csv,math,tempfile,subprocess
root=Path('/Users/arm2arm/orca/workspaces/openmhd-rs-/M0');sha=lambda b:hashlib.sha256(b).hexdigest()
readgz=lambda p:json.loads(gzip.decompress(p.read_bytes()))
remaining=root/'tests/reference/m1_completion/hll_remaining';meta=json.loads((remaining/'archive_provenance.json').read_text())
for name,digest in meta['archive_sha256'].items():assert sha((remaining/name).read_bytes())==digest
for name,digest in meta['uncompressed_sha256'].items():assert sha(gzip.decompress((remaining/name).read_bytes()))==digest
p=remaining/'remaining';s=readgz(p/'summary.json.gz');runs=readgz(p/'runs.json.gz');manifest=readgz(p/'manifest.json.gz');assert set(s['runs'])==set(runs)==set(manifest) and len(runs)==31
for name,r in s['runs'].items():
 if r['config']['case'] in ('brio','vortex'):
  raw=gzip.decompress((p/name/'projection.json.gz').read_bytes());assert sha(raw)==r['projection_sha256']
  rows=json.loads(raw)
  if r['config']['case']=='brio':
   norm=sum(x['volume'] for x in rows)
   err={k:sum(x['volume']*abs(x['candidate'][k]-x['reference'][k]) for x in rows)/norm for k in ['rho','p','vx','by']}
   assert all(abs(err[k]-r['reference_L1'][k])<1e-14 for k in err)
  else:
   with gzip.open(root/'tests/reference/external_mhd/vortex_512.csv.gz','rt') as f:ref=list(csv.DictReader(f))
   err={k:sum(abs(x[k]-float(y[k])) for x,y in zip(rows,ref))/len(ref) for k in ['rho','p','bx','by']}
   assert len(rows)==len(ref)==4096
   assert all(abs(err[k]-r['reference_L1'][k])<1e-14 for k in err)
assert len(s['gates'])==9 and all(g['status']=='pass' for g in s['gates'])
assert len(s['vortex_boost_pairs'])==6 and all(g['status']=='pass' for g in s['vortex_boost_pairs'])
print('Remaining archive: all22 compressed/uncompressed hashes and15 projection seals valid; all15 reference norms recomputed')
print('Vortex maximum boost relative L1',max(max(r['relative_L1'].values()) for r in s['vortex_boost_pairs']))
print('Maximum conservative budget',max(max(abs(v) for v in r['summary']['final']['normalized_budget']) for r in s['runs'].values() if r['config']['case']!='passive'))
p=root/'tests/reference/m1_completion/hll_wave_interrupted';meta=json.loads((p/'partial_archive_provenance.json').read_text())
for name,digest in meta['archive_sha256'].items():assert sha((p/name).read_bytes())==digest
for name,digest in meta['uncompressed_sha256'].items():assert sha(gzip.decompress((p/(name+'.gz')).read_bytes()))==digest
manifest=readgz(p/'manifest.json.gz');runs=readgz(p/'runs.json.gz');s=readgz(p/'summary.json.gz');interrupt=readgz(p/'interruption.json.gz')
for name,digest in interrupt['captured_metadata_sha256'].items():assert sha(gzip.decompress((p/(name+'.gz')).read_bytes()))==digest
completed=set(runs);stopped=set(s['externally_stopped_unfinished']);unexecuted=set(s['unexecuted']);assert not completed&stopped and not completed&unexecuted and not stopped&unexecuted and completed|stopped|unexecuted==set(manifest)
assert all(r['status']=='completed' and r['returncode']==0 for r in runs.values())
raw_count=0
for name,r in runs.items():
 assert r['config']==manifest[name]
 for filename,digest in r['sha256'].items():assert sha((root/'results/m1_completion_full'/name/filename).read_bytes())==digest;raw_count+=1
assert (len(completed),len(stopped),len(unexecuted),len(manifest))==(119,8,57,184)
failed=[g for g in s['alfven_convergence'] if g['parallel']==0 and g['jitter']==.15 and g['motion']=='fixed'][0];assert failed['gate']=='fail' and failed['finest_three_order']<1.8
print('Interrupted archive: all5 compressed/uncompressed hashes;',raw_count,'raw artifact hashes; disjoint counts119/8/57 of184; order gate remainsFAIL')
with tempfile.TemporaryDirectory(prefix='openmhd-one-study-') as tmp:
 out=Path(tmp)/'remaining';cmd=[sys.executable,str(root/'scripts/archive_m1_completion.py'),'--remaining-dir',str(root/'results/m1_completion_remaining'),'--output-dir',str(out)]
 q=subprocess.run(cmd,text=True,capture_output=True,check=True);print(q.stdout.strip())
 for name,digest in json.loads((remaining/'archive_provenance.json').read_text())['archive_sha256'].items():assert sha((out/name).read_bytes())==digest
 empty=Path(tmp)/'no-input';q=subprocess.run([sys.executable,str(root/'scripts/archive_m1_completion.py'),'--output-dir',str(empty)],text=True,capture_output=True);assert q.returncode!=0 and not empty.exists()
 print('One-study CLI recreated all22 archived file hashes; zero-study CLI rejected without output')
