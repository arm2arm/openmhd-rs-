"""Inspect actual complete canary/Cargo/installer bytes; no local target execution."""
import base64
from datetime import datetime,timezone
import hashlib,io,json,re,tarfile
from pathlib import Path
OPS=Path(__file__).resolve().parent;ROOT=OPS.parents[1]
CASES=ROOT/'results/offline_workspace_canary_cases_released_20261124_attempt01'
checks=0

def need(ok,label):
 global checks
 checks+=1
 if not ok:raise ValueError(label)
def raw(p):
 need(p.is_file() and not p.is_symlink(),'Ordinary retained file')
 return p.read_bytes()
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(raw(p))
def pin(b):return dict(sha256=sha(b),bytes=len(b))
def save(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
release=load(OPS/'root_release.json');plan=load(CASES/'plan.json')
need(sha(raw(CASES/'plan.json'))==release['plan_sha256'],'Exact released plan')
plan['snapshot_sha256']=sha(raw(CASES/'0000/snapshot.json'))
inventory_path=OPS/'inventory_a01/summary.json';inventory=load(inventory_path)
need(inventory['counts']=={'finished':2},'Actual finished two-original-UUID inventory')
mapping={r['workflow']:r['uuid'] for r in inventory['cases'].values()}
need(len(mapping)==len(set(mapping.values()))==2,'Two unique original new canaries')
inputs=ROOT/'results/workspace_locked_dependencies_20261124_attempt01'
bundle=load(inputs/'bundle.json');manifest=load(inputs/'manifest.json')
need(sha(raw(inputs/'bundle.json'))=='5ad32dcda9f18064019f4111debeec8605039d8f07ff383e1abb44cc363b6d2f','Exact original dependency descriptor')
need(sha(raw(inputs/'manifest.json'))==bundle['manifest_sha256'],'Original eighty-package manifest')
wanted={}
for r in manifest['packages']:
 content=raw(inputs/r['path']);need(sha(content)==r['sha256'] and len(content)==r['bytes'],'Original locked crate archive bytes')
 with tarfile.open(fileobj=io.BytesIO(content),mode='r:gz') as archive:
  files={}
  for member in archive:
   if member.isfile():
    need(member.name.startswith(r['name']+'-'+r['version']+'/'),'Actual packaged crate root')
    files[member.name.split('/',1)[1]]=sha(archive.extractfile(member).read())
 wanted[(r['name'],r['version'])]=dict(package_sha256=r['sha256'],files=files)
need(len(wanted)==80 and sum(len(r['files']) for r in wanted.values())==3328,'Full actual archive inventory')
offline_records=[]
names = {'result.json', 'runtime.json', 'command.json', 'stdout.txt', 'stderr.txt', 'child_result.json', 'child_raw.bin', 'artifacts.sha256.json'}
reviews, failures, skipped = [], [], []
capture_paths = []
for entry in plan['cases']:
    index, workflow = entry['directory'], entry['workflow']
    folder = CASES / index
    need({p.relative_to(folder).as_posix(): pin(raw(p)) for p in folder.rglob('*') if p.is_file()} == entry['files'], 'Exact original staged inputs')
    complete = sorted((OPS / 'captures' / index).glob('attempt*/capture.json'))
    need(len(complete) == 1, 'One complete coherent new canary capsule')
    capture_path = complete[0].parent
    capture_paths.append((index, capture_path))
    capture = load(capture_path / 'capture.json')
    need(capture['workflow'] == workflow and capture['uuid'] == mapping[workflow] and capture['status'] == inventory['cases'][index]['status'] and capture['status'] in ('finished', 'failed'), 'Actual original terminal identity')
    origins = capture['artifacts'] + [capture['before'], capture['after']]
    for origin in origins:
        body = raw(OPS / origin['path'])
        need(pin(body) == dict(sha256=origin['sha256'], bytes=origin['bytes']) and origin['uuid'] == mapping[workflow], 'Held successful origin bytes and UUID')
        command = load(OPS / origin['command'])
        diagnostic = load((OPS / origin['command']).parent / 'stdout.txt')
        need(command['outcome'] == 'success' and command['returncode'] == 0 and command['finished_utc']
             and diagnostic['workflow_ids'] == [mapping[workflow]] and diagnostic['outcome'] == 'success'
             and diagnostic['code'] == 'completed' and diagnostic['workflow'] == workflow, 'Actual successful same-UUID GET receipt')
    for origin in (capture['before'], capture['after']):
        observed = load(OPS / origin['path'])
        need(observed['origin'] == 'server' and len(observed['matches']) == 1 and observed['matches'][0]['workflow'] == workflow
             and observed['matches'][0]['version'] == 1 and observed['matches'][0]['status'] == capture['status'], 'Original same-state terminal sandwich')
    artifacts = {Path(r['remote']).name: raw(OPS / r['path']) for r in capture['artifacts']}
    need(set(artifacts) == names and len(capture['artifacts']) == 8, 'Eight complete actual artifacts')
    need(json.loads(artifacts['artifacts.sha256.json']) == {'outputs/' + n: sha(v) for n, v in artifacts.items() if n != 'artifacts.sha256.json'}, 'Exact seven-body output manifest')
    result, runtime, child, commands = [json.loads(artifacts[n]) for n in ('result.json', 'runtime.json', 'child_result.json', 'command.json')]
    case, leaf = entry['specification'], entry['specification']['leaf']
    need(capture['status'] == 'finished' and result['status'] == 'passed', 'Actual finished and passed new canary')
    need(result['schema'] == 'openmhd.g00-source-leaf-result.v1' and result['status'] == 'passed'
         and result['test_leaves_executed'] == result['passing_leaves'] == 1 and result['component_accepted'] is False
         and result['case'] == case and result['payload_sha256'] == sha(raw(folder / 'payload.json'))
         and result['snapshot_sha256'] == plan['snapshot_sha256'], 'One actual passing exact input leaf')
    prepared_raw = base64.b64decode(child['prepared_runtime_base64'], validate=True)
    prepared = json.loads(prepared_raw)
    need(prepared['snapshot_sha256'] == plan['snapshot_sha256'] and prepared['image'] == runtime['image']
         and prepared['machine'] == runtime['machine'] and prepared['rustc'].startswith('rustc 1.85.1 ')
         and sha(prepared_raw) == runtime['prepared_runtime_sha256'], 'Original bootstrap/runtime compiler linkage')
    need(runtime['tool_pins'] == {'runtime/rust/bin/cargo': '87e9ff02f95ea17d877e7c4eeb0f365f50fe3827f5afec132131ff3b8031a57e',
         'runtime/rust/bin/rustc': 'f8d033fd72e878ec60493788c8bffec2e6c154dcab6f0cb4c145af8ada26a7ed'}
         and runtime['declared_resources'] == case['resources']
         and runtime['thread_environment'] == dict(CARGO_BUILD_JOBS='4', RUST_TEST_THREADS='1', RAYON_NUM_THREADS='1',
             OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1'), 'Actual pinned compiler/Cargo and explicit thread resources')
    stages = child['stages']
    need(commands == dict(schema='openmhd.g00-source-commands.v1', stages=stages)
         and [s['label'] for s in stages] == ['compiler', 'compile', 'list', 'ignored-list', 'leaf'], 'Five exact actual command stages')
    outputs = {}
    for stage in stages:
        command = stage['command']
        need(command['command'] == stage['argv'] and command['outcome'] == 'success' and command['returncode'] == 0
             and command['cleanup']['writers_settled'] is True and command['cleanup']['direct_child_reaped'] is True
             and command['cleanup']['leader_held_until_group_close'] is True and command['cleanup']['group_authority_lost'] is False,
             'Every actual command succeeded with held-leader writer closure')
        outputs[stage['label']] = (base64.b64decode(stage['stdout_base64'], validate=True), base64.b64decode(stage['stderr_base64'], validate=True))
    compiler = Path(stages[0]['argv'][0])
    work = compiler.parents[3]
    source = work / 'source'
    need(work.name == mapping[workflow] and stages[0]['argv'] == [str(compiler), '-Vv']
         and outputs['compiler'][0].decode() == prepared['rustc'] and runtime['compiler_stdout_sha256'] == sha(outputs['compiler'][0]), 'Actual original UUID compiler command and banner')
    build = stages[1]['argv']
    target = {'lib': ['--lib'], 'test': ['--test', leaf['target_name']], 'bin': ['--bin', leaf['target_name']], 'example': ['--example', leaf['target_name']]}[leaf['target_kind'][0]]
    prefix = [str(work / 'runtime/rust/bin/cargo'), 'test', '--manifest-path', str(source / leaf['manifest']), *target,
              '--all-features', '--locked', '--no-run', '--message-format=json', '--jobs', '4', '--target-dir', str(source / 'target')]
    need(build[:len(prefix)] == prefix and ('--release' in build) == (leaf['build_profile'] == 'release'), 'Correct actual selected Cargo target/profile build')
    messages = [json.loads(line) for line in outputs['compile'][0].splitlines() if line.startswith(b'{')]
    need([r['success'] for r in messages if r.get('reason') == 'build-finished'] == [True], 'Actual successful Cargo JSON build')
    executable_records = child['compiled_executables']
    restart = leaf['target_name'] == 'restart' and leaf['manifest'] == 'apps/openmhd/Cargo.toml'
    need(len(executable_records) == (2 if restart else 1), 'Actual libtest and required normal restart application')
    for number, record in enumerate(executable_records):
        artifact = record['artifact']
        executable = Path(artifact['executable'])
        need(artifact in messages and 0 < record['bytes'] <= 128 * 1024 * 1024 and re.fullmatch('[0-9a-f]{64}', record['sha256'])
             and executable.is_relative_to(source / 'target') and artifact['profile']['test'] is (number == 0), 'Actual Cargo executable provenance and held binary identity')
        identity = record['file_identity']
        need(set(identity) == {'st_dev','st_ino','st_nlink','st_size','st_mtime_ns','st_ctime_ns'}
             and all(type(value) is int for value in identity.values()) and identity['st_nlink'] >= 1
             and identity['st_size'] == record['bytes'] and identity['st_ino'] > 0, 'Actual held executable inode/link/size identity')
        expected = (leaf['manifest'], leaf['target_kind'], leaf['target_name'], leaf['source']) if number == 0 else (
            'apps/openmhd/Cargo.toml', ['bin'], 'vector-potential', 'apps/openmhd/src/bin/vector-potential.rs')
        need((str(Path(artifact['manifest_path']).relative_to(source)), artifact['target']['kind'], artifact['target']['name'],
             str(Path(artifact['target']['src_path']).relative_to(source))) == expected, 'Actual exact target/application identity')
    binary = executable_records[0]['artifact']['executable']
    parent = load(folder / 'parent/preflight.json')
    parent_binary = [b for b in parent['binaries'] if b['path'] == leaf['binary']]
    need(len(parent_binary) == 1 and leaf in parent['tests'], 'One exact original parent target and selector')
    selectors = parent_binary[0]['selectors']
    need(stages[2]['argv'] == [binary, '--list', '--format', 'terse']
         and outputs['list'][0].decode().splitlines() == [n + ': test' for n in selectors]
         and stages[3]['argv'] == [binary, '--list', '--ignored', '--format', 'terse'] and outputs['ignored-list'][0] == b'',
         'Original exact target catalog and no ignored substitution')
    need(stages[4]['argv'] == [binary, '--exact', leaf['selector'], '--test-threads', '1', '--color', 'never', '--show-output'], 'One exact native leaf invocation')
    stdout, stderr = outputs['leaf']
    text = stdout.decode()
    need(re.findall(r'^running ([0-9]+) tests?$', text, re.MULTILINE) == ['1']
         and len(re.findall(r'^test ' + re.escape(leaf['selector']) + r'(?: - should panic)? \.\.\. ok$', text, re.MULTILINE)) == 1
         and re.findall(r'^test result: ok\. ([0-9]+) passed; ([0-9]+) failed; ([0-9]+) ignored; ([0-9]+) measured; ([0-9]+) filtered out; finished in [^\n]+\n*\Z', text, re.MULTILINE)
             == [('1', '0', '0', '0', str(len(selectors) - 1))], 'Actual raw stdout proves exactly one clean nonignored leaf')
    need(child['witness'] == dict(schema='openmhd.galaxy-libtest-witness.v1', selector=leaf['selector'], passed=1, failed=0,
         ignored=0, measured=0, filtered_out=len(selectors) - 1, stdout_sha256=sha(stdout))
         and artifacts['child_raw.bin'] == artifacts['stdout.txt'] == stdout and artifacts['stderr.txt'] == stderr
         and child['component_accepted'] is False, 'Exact raw witness/body linkage and scope')
    auxiliary=capture['auxiliary'];auxroot=OPS/auxiliary['directory']
    need({p.relative_to(auxroot).as_posix():pin(raw(p)) for p in auxroot.rglob('*') if p.is_file()}==auxiliary['files'],'Exact auxiliary downloaded bodies')
    auxcmd=load(OPS/auxiliary['command'])
    need(auxcmd['outcome']=='success' and auxcmd['returncode']==0 and '--workflow' in auxcmd['argv'] and auxcmd['argv'][auxcmd['argv'].index('--workflow')+1]==mapping[workflow],'Actual same-UUID read-only auxiliary acquisition')
    config=raw(auxroot/'runtime/cargo/config.toml');installed_raw=raw(auxroot/'runtime/locked-dependencies/installed.json');installed=json.loads(installed_raw);status=load(auxroot/'runtime/locked-dependencies/status.json')
    info=prepared['offline_dependencies']
    expected_config=('[source.crates-io]\nreplace-with = "locked-inputs"\n[source.locked-inputs]\ndirectory = '+json.dumps(str(work/'runtime/locked-dependencies'))+'\n[net]\noffline = true\n').encode()
    need(config==expected_config and sha(config)==info['config_sha256']==installed['config_sha256']==status['config_sha256'],'Actual private Cargo directory-source and offline configuration')
    need(sha(installed_raw)==info['installed_sha256']==status['installed_sha256'] and info['bundle_sha256']==installed['bundle_sha256']==status['bundle_sha256']==sha(raw(inputs/'bundle.json')),'Actual installed ledger and original descriptor')
    need(info['packages']==status['package_count']==80 and info['source_replacement'] is True and info['network_offline'] is True and info['source_lock_sha256']==status['lock_sha256']==bundle['lock_sha256'],'Same eighty-package lock and offline source selection')
    need(info['installer_sha256']==entry['derivation']['installer_sha256']==sha(raw(CASES/index/'locked_dependencies.py')),'Exact actually tested installer source')
    need(status['status']=='complete' and status['target_executed'] is False and datetime.fromisoformat(status['finished_utc'])<datetime.fromisoformat(stages[0]['command']['started_utc']),'Completed installer before any Cargo/test stage')
    actual_packages={(r['name'],r['version']):r for r in installed['packages']}
    need(len(actual_packages)==len(installed['packages'])==80 and set(actual_packages)==set(wanted),'Exact installed package inventory')
    for key,r in actual_packages.items():
        need(r['package_sha256']==wanted[key]['package_sha256'] and r['files']==wanted[key]['files'],'Every installed original file hash and locked package')
    need(not any(n in outputs['compile'][1] for n in [b'Updating crates.io index',b'Downloading crates',b'Downloaded ']),'Actual canary Cargo log has no dependency fetch')
    offline_records.append(dict(directory=index,uuid=mapping[workflow],packages=80,files=3328,installed_sha256=sha(installed_raw),config_sha256=sha(config),compile_duration_seconds=stages[1]['command']['duration_seconds'],auxiliary=auxiliary))
    reviews.append(dict(directory=index, workflow=workflow, uuid=mapping[workflow], selector=leaf['selector'], restart=restart,
        result_sha256=sha(artifacts['result.json']), raw_stdout_sha256=sha(stdout), compiled_executables=[dict(
            sha256=r['sha256'], bytes=r['bytes'], path=r['artifact']['executable'], file_identity=r['file_identity']) for r in executable_records]))
need(len(reviews)==2 and len(offline_records)==2,'Both ordinary/restart strict actual canaries')
need(sorted(r['restart'] for r in reviews)==[False,True],'Actual ordinary and real CLI restart coverage')
report=dict(schema='openmhd.offline-canary-actual-output-root-review.v1',utc=datetime.now(timezone.utc).isoformat(),root_release_sha256=sha(raw(OPS/'root_release.json')),plan_sha256=release['plan_sha256'],source_snapshot_sha256=plan['snapshot_sha256'],strict_passing_canaries=2,canaries=reviews,offline_dependencies=offline_records,checks=checks,errors=[],offline_qualification_passed=True,original490_whole_catalog_passed=False,full_campaign_release=False,component_accepted=False,independent_reviewer_claimed=False,target_execution_by_inspector=False)
save(OPS/'actual_output_root_review.json',report)
print(json.dumps({k:v for k,v in report.items() if k not in ['canaries','offline_dependencies']},indent=2))
