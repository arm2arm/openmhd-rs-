from pathlib import Path
import concurrent.futures,datetime,hashlib,json,subprocess,time
root=Path('/Users/arm2arm/orca/workspaces/openmhd-rs-/M0');frozen=Path('/tmp/openmhd-m1-projected');out=root/'results/m1_projected_controls';out.mkdir();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();binary=frozen/'target/release/vector-potential'
revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=frozen,text=True).strip();assert revision=='0f2e5e295e55bc083690fc1450df9f4efe557932'
assert not subprocess.check_output(['git','status','--short'],cwd=frozen,text=True).strip()
paths=sorted({*frozen.glob('crates/*/src/**/*.rs'),frozen/'apps/openmhd/src/bin/vector-potential.rs',frozen/'docs/M1_COMPLETION_PLAN.md',frozen/'Cargo.toml',frozen/'Cargo.lock',frozen/'rust-toolchain.toml',*frozen.glob('crates/*/Cargo.toml'),*frozen.glob('apps/*/Cargo.toml')})
sources={str(p.relative_to(frozen)):sha(p) for p in paths}; origin={'revision':revision,'mesh_caches':{}}
configs={}
for n,dt in [(32,.0002),(64,.0001)]:
 for boosted in [False,True]:
  name=f'n{n}_'+('boost' if boosted else 'base');p=out/name;p.mkdir();cache=root/f'results/m1_mesh_cache/unit_{n}_0.0.mesh';cacheinfo=origin['mesh_caches'][f'n{n}_j0.0'] if f'n{n}_j0.0' in origin['mesh_caches'] else None
  cmd=[str(binary),'--profile','bulk-frame-hll-projected-v1','--case','alfven','--n',str(n),'--jitter','0','--time','1','--parallel-velocity','1','--motion','rigid','--mesh-x','2' if boosted else '0','--mesh-y','-1' if boosted else '0','--boost-x','2' if boosted else '0','--boost-y','-1' if boosted else '0','--boost-z','0','--dt',str(dt),'--checkpoint','.25','--mesh-cache',str(cache),'--output',str(p)]
  configs[name]={'n':n,'dt':dt,'boosted':boosted,'command':cmd,'mesh_cache':str(cache),'mesh_cache_sha256':sha(cache)}
prov={'scope':'Explicit fixed-cap diagnostic control, not replacement of failed registered adaptive runs or acceptance gate','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'revision':origin['revision'],'binary_sha256':sha(binary),'source_sha256':sources,'jobs':4,'script_sha256':sha(Path(__file__)),'original_execution_provenance_sha256':sha(root/'results/m1_compact_quick/provenance.json')};(out/'provenance.json').write_text(json.dumps(prov,indent=2)+'\n');(out/'manifest.json').write_text(json.dumps(configs,indent=2)+'\n');runs={}
def run(item):
 name,c=item;p=out/name;t=time.monotonic()
 with (p/'run.log').open('w') as f:result=subprocess.run(c['command'],cwd=frozen,stdout=f,stderr=subprocess.STDOUT)
 record={'config':c,'exit_code':result.returncode,'elapsed_seconds':time.monotonic()-t,'status':'completed' if result.returncode==0 else 'failed','sha256':{f.name:sha(f) for f in p.iterdir() if f.is_file()}}
 if (p/'summary.json').exists():record['summary']=json.loads((p/'summary.json').read_text())
 return name,record
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for future in concurrent.futures.as_completed([pool.submit(run,item) for item in configs.items()]):
  name,r=future.result();runs[name]=r;(out/'runs.json').write_text(json.dumps(runs,indent=2)+'\n');print(name,r['status'],r['elapsed_seconds'],{k:r.get('summary',{}).get(k) for k in ['steps','rejected_cfl','rejected_state','dt_min','dt_max']},flush=True)
prov['result_sha256']={n:sha(out/n) for n in ['manifest.json','runs.json']};(out/'provenance.json').write_text(json.dumps(prov,indent=2)+'\n')

assert sha(binary)==prov['binary_sha256']
assert sources=={str(p.relative_to(frozen)):sha(p) for p in paths}
assert all(sha(Path(c['mesh_cache']))==c['mesh_cache_sha256'] for c in configs.values())
