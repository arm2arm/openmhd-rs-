"""Portable archive consistency checks, never independent execution or M1 acceptance.

Historical inventories close non-cache files; NEW evidence/outer boundaries close
every file including caches and forbid symlinks. Reviewers must pin the manifest.
"""
if not __debug__:
    raise RuntimeError("Optimized Python cannot verify M1 evidence")

import argparse
import ast
from datetime import datetime
import gzip
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import shlex
import sys

sys.dont_write_bytecode = True
REVISION = '2bdcea0d28340e7429e10053a641f92d51fcc696'
SNAPSHOT = 'b67ce03779a194099983b7ff07c0cafed23e9ea3a9051047492d072255e0160f'
BINARY = '18afcf0308338e2ea0ea7ef5e03dba46af9d7025f3ccf4a6a48ebbfe800d0725'
BOUNDED_BINARY = '090acac224588ff802f430290627f1f59ce764b0797e007c66708b0668c3a6ea'
IMAGE = 'gitlab-p4n.aip.de:5005/p4nreana/reana-env@sha256:aebd7911df9e1e97ad67d15f4c32ab23996000282183fad3bf7a480756522bd7'
COUNTS = dict(medium=48, mean=24, waves=112, physics=30)
PHASES = {'bounded_short','bounded_medium','mean','calibration_wave','calibration_vortex','physics','waves'}
# Frozen 2bdcea0 scripts/fanout_campaign_verdict.py:52-111,147-192;
# scripts/run_m1_campaign.py:59-90 and run_m1_bounded.py:104-109.
PLAN_CHECKS = {'same_snapshot','registered_cases','registered_options','terminal_without_errors',
    'every_planned_case_completed','same_binary','candidate_and_limiter_metadata'}
PHASE_CHECKS = {
    'bounded_short':{'workflow_completed','same_snapshot','gate_file_unchanged',
                     'four_short_stages_passed','blockers_closed','configuration'},
    'bounded_medium':PLAN_CHECKS|{'all_runs_completed','positive_and_conservative','boost_pairs_passed'},
    'mean':PLAN_CHECKS|{'all_completed','positive_and_conservative','boost_pairs',
                        'execution_configuration','mean_refinement_measured'},
    'calibration_wave':{'all_completed','positive_and_conservative','boost_pairs',
                        'execution_configuration','amplitude_error'},
    'calibration_vortex':{'complete','diagnostics','execution_configuration'},
    'physics':PLAN_CHECKS|{'physics_gates','complete_ladder'},
    'waves':PLAN_CHECKS|{'all_completed','positive_and_conservative','boost_pairs',
                        'execution_configuration','spatial_gates','temporal_measured'}}
CONFIGURATION = dict(profile='bulk-frame-heun-quadratic-v1', accelerated_projection=False,
    projection_screening=1., riemann_solver='hlld-pressure', potential_limiter='smooth-extrema',
    trial_step_fraction=None)
LABELS = ['prior_packet','verify_medium','verify_mean','verify_waves','verify_physics',
    'medium_norms','mean_norms','wave_inputs','wave_norms','physics_inputs','physics_norms',
    'shock_reference','vortex_reference']
TOOLS = {'prepare_final_evidence.py','collect_fresh_physics_reference_inputs.py',
    'verify_packet.py','verify_fresh_phase.py','prepare_inputs.py','reduce_waves.py',
    'reduce_boost_pairs.py','reduce_mean.py','reduce_shock.py','reduce_vortex.py'}
HISTORICAL = {
 'source_review_packet/archive_sha256.json':
 ('18e38519d43eac6c859c6bb2fd3788031c623cb4d7bb7eb2a2d357058531a7d4',69),
 'source_review_packet/review/review_sha256.json':
 ('ea0b252dda7ba1a850f629dfd28c9dc51f537de49c33a0a52bc30098059658fc',9),
 'historical_campaigns/archive_sha256.json':
 ('da6d8df237f2359ab69718bf73999b8e8ecb6dddd4eae3cde07087006602782b',94)}
REPORTS = {'medium_independent.json','mean_independent.json','waves_independent.json',
    'physics_boost_independent.json','shock/independent_reference.json','vortex/independent_reference.json'}
FIELDS = {'rho','p','vx','vy','vz','bx','by','bz','energy'}
BOUNDARY = 'original non-cache inventories; copied payload is non-cache; new evidence/outer closure includes every file including caches'
WAVE_FIELDS = {'bx','by','bz','vx','vy','vz','B','v'}
RESIDUAL_SCOPE = 'Residual-based log-log fit standard error, one degree of freedom; not a systematic discretization-error bound.'


class EvidenceError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def finite_number(value,nonnegative=False):
    return type(value) in (int,float) and math.isfinite(value) and (not nonnegative or value >= 0)


def roundoff_match(actual,expected,label,scale=None):
    """Scalar metadata consistency, NOT a scientific tolerance or uncertainty gate.

    Compare binary64 expressions evaluated by stdlib/libm and the frozen numpy
    reduction with |a-b| <= 256*epsilon*max(|a|,|b|,scale). With no scale this
    is a relative roundoff allowance (zero must equal zero). The three-point
    fit explicitly supplies its log-input/centering scale below, so near-zero
    residual cancellation has a small ABSOLUTE roundoff allowance. This fixed
    engineering allowance assumes normal finite log inputs and short sums; it
    is not a certified bound on every possible libm, raw arithmetic or physics.
    Its actual supported-runtime behavior remains a REANA metadata prerequisite.
    Physical inequalities are checked separately, without this allowance.
    """
    require(finite_number(actual) and finite_number(expected),'Nonfinite '+label)
    magnitude = max(abs(actual),abs(expected),0. if scale is None else scale)
    require(finite_number(magnitude,True) and
        abs(actual-expected) <= 256*sys.float_info.epsilon*magnitude,'Inconsistent '+label)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def loads(data):
    def pairs(items):
        result = {}
        for k,v in items:
            require(k not in result, 'Duplicate JSON key: '+k)
            result[k] = v
        return result
    def invalid(value):
        raise EvidenceError('Nonfinite JSON constant: '+value)
    def finite_float(value):
        result = float(value)
        require(math.isfinite(result),'Nonfinite JSON number: '+value)
        return result
    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid,parse_float=finite_float)


def fingerprint(value):
    return sha(json.dumps(value,sort_keys=True,allow_nan=False).encode())


def safe_name(name):
    require(isinstance(name,str),'Non-string path')
    p = PurePosixPath(name)
    require(bool(p.parts) and not p.is_absolute() and '..' not in p.parts
        and str(p) == name and '\\' not in name,'Unsafe path: '+name)
    return p


def safe_path(root,name):
    p,root = safe_name(name),Path(root).resolve()
    path = root.joinpath(*p.parts)
    require(path.resolve().is_relative_to(root),'Escaping path: '+name)
    for parent in [path,*path.parents]:
        if parent == root:
            break
        require(not parent.is_symlink(),'Evidence links forbidden: '+name)
    return path


def files(root,historical=False):
    root,result = Path(root).resolve(),{}
    for p in root.rglob('*'):
        rel = p.relative_to(root)
        if historical and '__pycache__' in rel.parts:
            continue
        require(not p.is_symlink(),'Closed boundary contains link: '+str(p))
        require(p.is_file() or p.is_dir(),'Closed boundary contains special file: '+str(p))
        if p.is_file():
            result[rel.as_posix()] = p
    return result


def verify_closed(root,manifest_name,children=None,historical=False,expected_count=None):
    root = Path(root).resolve()
    manifest = loads(safe_path(root,manifest_name).read_bytes())
    require(isinstance(manifest,dict),'Inventory must be object')
    actual = files(root,historical)
    require(manifest_name in actual,'Missing inventory')
    actual.pop(manifest_name)
    for directory,child in (children or {}).items():
        verify_closed(safe_path(root,directory),child,historical=historical)
        actual = {n:p for n,p in actual.items() if not n.startswith(directory+'/')
                  or n == directory+'/'+child}
    require(set(actual) == set(manifest),'Extra/missing inventory entries: '+str(root))
    require(expected_count is None or len(manifest) == expected_count,'Historical count')
    for name,digest in manifest.items():
        require(isinstance(digest,str) and re.fullmatch('[0-9a-f]{64}',digest),'Invalid digest')
        require(sha(safe_path(root,name).read_bytes()) == digest,'Inventory digest: '+name)
    return manifest


def decoded_file(root,name):
    data = safe_path(root,name).read_bytes()
    return gzip.decompress(data) if name.endswith('.gz') else data


def decode_artifact(root,row):
    data = safe_path(root,row['path']).read_bytes()
    require(row['encoding'] in {'gzip','identity'} and len(data) == row['stored_bytes']
        and sha(data) == row['stored_sha256'],'Stored identity')
    raw = gzip.decompress(data) if row['encoding'] == 'gzip' else data
    require(len(raw) == row['original_bytes'] and sha(raw) == row['original_sha256'],'Decoded identity')
    return raw


def read(root,name):
    return loads(decoded_file(root,name))


def named_specifications(rows):
    result = {}
    for row in rows:
        n = row['config']['name']
        require(n not in result and safe_name(n).parts == (n,),'Duplicate/unsafe case')
        result[n] = row
    return result


def plan_entries(plan):
    result = {}
    for row in plan['cases']:
        n = row['specification']['config']['name']
        require(n not in result,'Duplicate plan case')
        safe_name(row['directory'])
        result[n] = row
    require(len({r['workflow'] for r in result.values()}) == len(result),'Repeated workflow')
    require(len({r['directory'] for r in result.values()}) == len(result),'Repeated case directory')
    return result


def semantic_plan_match(plan,specs,old):
    # Fresh order must match its own exported registration, not A's ordering.
    require([r['specification'] for r in plan['cases']] == specs,'Fresh registration/order')
    expected = named_specifications(specs)
    require(expected == {n:r['specification'] for n,r in plan_entries(old).items()},
            'Historical A name-indexed specifications differ')
    return expected


def check_runtime(r):
    require(r['optimization'] == 0 and r['assertions_enabled'] is True,'Optimized recorded runtime')
    require(all(isinstance(r[k],str) and r[k] for k in
                ('executable','version','implementation','platform')),'Missing runtime identity')


def timestamp(value):
    t = datetime.fromisoformat(value)
    require(t.tzinfo is not None and t.utcoffset().total_seconds() == 0,'Timestamp not UTC')
    return t


def check_journal(rows,raw,required=None):
    require(isinstance(rows,list),'Journal must be list')
    require([r['attempt_id'] for r in rows] == list(range(1,len(rows)+1)),'Attempt ordering')
    if required is not None:
        require([r['label'] for r in rows] == required,'Exact successful command-label inventory')
    paths = set()
    for r in rows:
        require(r['logs_closed'] is True and r['external_evidence_required'] is False,
                'Unfinished writer/log cleanup requires external evidence')
        ownership = r['ownership']
        require(set(ownership) == {'schema','registry','node_id','parent_id','guardian_pid',
                'state','writers_stopped'} and ownership['schema'] == 'm1-command-ownership-v1'
                and ownership['writers_stopped'] is True,'Unclosed command ownership receipt')
        require(isinstance(r['argv'],list) and len(r['argv']) >= 2
                and all(isinstance(a,str) for a in r['argv']),'Invalid command argv')
        require(timestamp(r['finished_utc']) >= timestamp(r['started_utc']),'Command timestamps')
        require(math.isfinite(r['duration_seconds']) and r['duration_seconds'] >= 0
                and math.isfinite(r['timeout_seconds']) and r['timeout_seconds'] > 0,'Command duration/timeout')
        require(isinstance(r['cwd'],str) and PurePosixPath(r['cwd']).is_absolute(),'Command cwd')
        check_runtime(r['interpreter'])
        require(r['child_environment'] == dict(PYTHONOPTIMIZE='0',PYTHONDONTWRITEBYTECODE='1'),
                'Uncontrolled child interpreter')
        for stream in ('stdout','stderr'):
            log = r[stream]
            safe_name(log['path'])
            require(log['path'] not in paths,'Reused log')
            paths.add(log['path'])
            data = raw(log['path'])
            require(len(data) == log['bytes'] and sha(data) == log['sha256'],'Command log identity')
        require(r['outcome'] in {'success','nonzero','timeout','start_failure','interrupted'},
                'Unfinished/unknown attempt')
        require((r['outcome'] != 'success' or r['error_type'] is None)
            and (r['returncode'] is None or type(r['returncode']) is int),'Command error/returncode')
        if required is not None:
            require(r['outcome'] == 'success' and r['returncode'] == 0,'Failed complete command')
        else:
            require((r['outcome'] == 'success') == (r['returncode'] == 0),'Transport outcome')
    return paths


def check_command_links(rows,capture):
    """Recorded transient paths are strings, never reopened on the verifier host."""
    require(len(rows) == len(LABELS) and [r['label'] for r in rows] == LABELS,'Command link inventory')
    repo = PurePosixPath(capture['private_reference_context']['original_root'])
    reference = capture['private_reference_context']['path']
    require(repo.is_absolute() and PurePosixPath(reference).is_absolute(),'Capture context paths')
    require(set(capture['private_views']) == set(COUNTS),'Exact private phase views')
    views = {p:capture['private_views'][p]['path'] for p in COUNTS}
    for p,v in capture['private_views'].items():
        require(v['original_root'] == 'results/followup_iter-'+p+'_20261121'
            and PurePosixPath(v['path']).is_absolute(),'Fresh private view origin')
    require(len(set(views.values())|{reference}) == 5,'Distinct private views')
    out = PurePosixPath(rows[1]['argv'][-1]).parent
    require(out.is_absolute(),'Absolute collection command paths')
    t = out/'tools'
    expected = [('verify_packet.py',[],str(repo))]
    expected += [('verify_fresh_phase.py',[p,views[p],str(out/'observations'/p/'specifications.json'),
                  str(out/(p+'_provenance.json'))],reference) for p in COUNTS]
    expected += [
      ('reduce_boost_pairs.py',['medium',views['medium'],str(out/'medium_independent.json')],reference),
      ('reduce_mean.py',[views['mean'],str(out/'mean_independent.json')],reference),
      ('prepare_inputs.py',['waves',views['waves'],str(out/'wave_inputs')],reference),
      ('reduce_waves.py',[str(out/'wave_inputs'),str(out/'waves_independent.json')],reference)]
    physics = rows[9]['argv']
    require(len(physics) == 11 and physics[4] == '--client' and bool(shlex.split(physics[5])),
            'Physics transport client contract')
    expected += [
      ('collect_fresh_physics_reference_inputs.py',[views['physics'],str(out/'physics_inputs'),
       '--client',physics[5],'--require-complete','--original-root',
       str(repo/capture['private_views']['physics']['original_root']),'--reference-root',reference],str(repo)),
      ('reduce_boost_pairs.py',['physics',views['physics'],str(out/'physics_boost_independent.json')],reference),
      ('reduce_shock.py',[str(out/'physics_inputs'),str(out/'shock')],reference),
      ('reduce_vortex.py',[str(out/'physics_inputs'),str(out/'vortex')],reference)]
    for row,(script,args,cwd) in zip(rows,expected):
        path = repo/'tests/reference/m1_acceptance'/script if row['label'] == 'prior_packet' else t/script
        require(row['argv'] == [row['interpreter']['executable'],str(path),*args]
            and row['cwd'] == cwd,'Exact command source/arguments/context: '+row['label'])
        require(row['timeout_seconds'] == 7200,'Collector command timeout')
        for stream in ('stdout','stderr'):
            require(row[stream]['path'] == f"logs/{row['attempt_id']:03}-{row['label']}.{stream}",
                    'Command log-label association')
    return repo,out


def ownership_paths(names):
    """Classify retained REGULAR receipts, never follow a recorded registry path.

    The full preparer uses one OUTER inherited registry. Standalone collector
    receipts can be classified for explicit rejection, not silently dropped.
    Exact graph/row coverage below rejects unexpected/unreferenced nodes.
    """
    result = set()
    for name in names:
        for prefix in ('command_ownership/','physics_inputs/command_ownership/'):
            if name.startswith(prefix):
                tail = name[len(prefix):]
                require(tail == 'registry.lock' or re.fullmatch(r'[0-9a-f]{32}\.json',tail),
                        'Unclassified command ownership receipt: '+name)
                result.add(name)
    return result


def guardian_bootstrap(source):
    """Read one literal from captured reviewed SOURCE without importing it.

    collect_fresh_physics_reference_inputs.py at 3b2c6f7:30-52,365-373
    records exactly [-I,-S,-B,-c,GUARDIAN_BOOTSTRAP,source,--owned-command,node].
    The captured source identity is checked independently; this is not execution
    or proof of process closure after host death/daemon escape.
    """
    assignments = [n for n in ast.parse(source).body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id == 'GUARDIAN_BOOTSTRAP' for t in n.targets)]
    require(len(assignments) == 1 and isinstance(assignments[0].value,ast.Constant)
        and isinstance(assignments[0].value.value,str),'Literal captured guardian bootstrap')
    return assignments[0].value.value


def check_ownership(rows,transport,raw,names,repo,out,source):
    """Portable receipt consistency for the committed cooperative POSIX contract.

    Complete archives contain thirteen root nodes plus exactly the transport
    rows, all settled, successful and writer-closed. Nested nodes are children
    of physics_inputs (not a new nested registry). PID values are historical
    observations, never reopened/probed/signalled here. This cannot independently
    establish liveness, trustworthy runtime, containment of unregistered daemon
    escapes or cleanup after an uncatchable loss: those require external review.
    """
    receipt_paths = ownership_paths(names)
    require('command_ownership/registry.lock' in receipt_paths
        and not any(n.startswith('physics_inputs/command_ownership/') for n in receipt_paths),
        'Full preparer requires its one outer shared ownership registry')
    require(raw('command_ownership/registry.lock') == b'','Unexpected ownership lock bytes')
    registry = str(out/'command_ownership')
    bootstrap,digest = guardian_bootstrap(source),sha(source)
    nodes = {}
    for path in sorted(receipt_paths-{'command_ownership/registry.lock'}):
        node_id = PurePosixPath(path).stem
        node = loads(raw(path))
        require(set(node) == {'schema','node_id','parent_id','argv','cwd','guardian_pid','primary_pid',
                'primary_returncode','state','cancelled','writers_stopped','guardian_source','guardian_argv'},
                'Exact successful ownership node schema')
        require(node['schema'] == 'm1-command-ownership-v1' and node['node_id'] == node_id
            and node['state'] == 'settled' and node['cancelled'] is False
            and node['writers_stopped'] is True and type(node['primary_returncode']) is int
            and node['primary_returncode'] == 0,'Unsettled/failed ownership node')
        require(all(type(node[k]) is int and node[k] > 1 for k in ('guardian_pid','primary_pid'))
            and node['guardian_pid'] != node['primary_pid'],'Invalid historical private process identities')
        nodes[node_id] = node
    # Validate the entire graph BEFORE comparing expected parents: cycles and
    # missing ancestors are rejected even for a mutually consistent forged row.
    for node_id in nodes:
        seen,current = set(),node_id
        while current is not None:
            require(isinstance(current,str) and current in nodes and current not in seen,
                    'Ownership graph missing ancestor/cycle')
            seen.add(current)
            current = nodes[current]['parent_id']
    expected = {}
    require(len(rows) == len(LABELS) and [r['label'] for r in rows] == LABELS,
            'Ownership root command inventory')
    parent = rows[9]['ownership']['node_id']
    for r,nested in [*[(r,False) for r in rows],*[(r,True) for r in transport]]:
        receipt = r['ownership'];node_id = receipt['node_id']
        require(isinstance(node_id,str) and re.fullmatch('[0-9a-f]{32}',node_id)
            and node_id not in expected and node_id in nodes,'Missing/duplicate row ownership node')
        expected[node_id] = r
        node = nodes[node_id]
        require(receipt == dict(schema='m1-command-ownership-v1',registry=registry,node_id=node_id,
                parent_id=parent if nested else None,guardian_pid=node['guardian_pid'],
                state='settled',writers_stopped=True)
            and node['parent_id'] == receipt['parent_id'],'Row/node/registry/parent link')
        require(r['outcome'] == 'success' and r['returncode'] == node['primary_returncode'] == 0
            and r['error_type'] is None and r['logs_closed'] is True
            and r['external_evidence_required'] is False,'Successful node requires finalized successful row')
        require(node['argv'] == r['argv'] and node['cwd'] == r['cwd'],'Actual command argv/cwd ownership link')
        helper = str((out/'tools' if nested else repo/'tools/m1_evidence')/
                     'collect_fresh_physics_reference_inputs.py')
        require(node['guardian_source'] == dict(path=helper,sha256=digest)
            and node['guardian_argv'] == [r['interpreter']['executable'],'-I','-S','-B','-c',bootstrap,
                helper,'--owned-command',str(out/'command_ownership'/(node_id+'.json'))],
            'Captured guardian source/isolated launcher identity')
        if nested:
            require(timestamp(rows[9]['started_utc']) <= timestamp(r['started_utc'])
                <= timestamp(r['finished_utc']) <= timestamp(rows[9]['finished_utc']),
                'Nested transport outside parent command interval')
    require(set(nodes) == set(expected),'Unreferenced/unexpected ownership receipt')


def check_complete_status(status,label):
    require(isinstance(status,dict) and set(status) ==
        {'status','full_m1_accepted','final_ai_output_review_passed'} and status['status'] == 'complete'
        and status['full_m1_accepted'] is False and status['final_ai_output_review_passed'] is False,
            'Incomplete/failed '+label+' collection status')


def check_collection_lifecycle(json_read,raw,names):
    """Shared by source packager BEFORE mkdir and portable copied-byte verifier."""
    check_complete_status(json_read('collection_status.json'),'outer')
    check_complete_status(json_read('physics_inputs/collection_status.json'),'nested physics')
    rows,transport = json_read('commands.json'),json_read('physics_inputs/transport_commands.json')
    logs = check_journal(rows,raw,LABELS)
    nested_logs = check_journal(transport,lambda n:raw('physics_inputs/'+n))
    require({n for n in names if n.startswith('logs/')} == logs
        and {n[len('physics_inputs/'):] for n in names if n.startswith('physics_inputs/transport_logs/')}
            == nested_logs,'Unreferenced/missing lifecycle logs')
    repo,out = check_command_links(rows,json_read('metadata_capture.json'))
    source = raw('tools/collect_fresh_physics_reference_inputs.py')
    require(source == raw('physics_inputs/collector.py'),'Nested and original captured guardian sources differ')
    check_ownership(rows,transport,raw,names,repo,out,source)


def raw_input_names(runs):
    names = {p+'/'+n+'/final.csv' for p,rs in runs.items() for n in rs}
    for n,r in runs['physics'].items():
        c = r['config']
        shock = c['case'] == 'brio-wu' and ((c['jitter'] == 0 and c['jitter_mode'] == 'planar')
                  or (c['jitter'] == .15 and c['jitter_mode'] == 'columns'))
        vortex = c['case'] == 'orszag-tang' and c['jitter'] == 0
        if shock or vortex:
            names.add('physics/'+n+'/geometry.json')
        if vortex:
            names.add('physics/'+n+'/projected_bins.json')
    require(len(names) == 238,'Exact raw input count')
    return names


def omission_key(name):
    patterns = [
      (r'wave_inputs/([^/]+)/final.csv','waves',False),
      (r'physics_inputs/([^/]+)/(final.csv|geometry.json|projected_bins.json)','physics',False),
      (r'physics_inputs/download/[^/]+/outputs/raw/([^/]+)/(final.csv|geometry.json|projected_bins.json)','physics',False),
      (r'(shock|vortex)/snapshots/([^/]+)/(final.csv|geometry.json|projected_bins.json)\.gz','physics',True)]
    for pattern,phase,compressed in patterns:
        match = re.fullmatch(pattern,name)
        if match:
            g = match.groups()
            case,filename = ((g[0],'final.csv') if phase == 'waves' else
                             (g[1],g[2]) if compressed else g)
            return phase+'/'+case+'/'+filename,compressed
    return None


def export_selection(manifest,summary,capture):
    required = {'summary.json','registered_verdict.json','commands.json','metadata_capture.json',
      'collection_status.json','vortex/independent_bins.json.gz',*REPORTS,
      *[p+'_provenance.json' for p in COUNTS],
      *['wave_inputs/'+n for n in ('runs.json','manifest.json','provenance.json','input_receipts.json')],
      *['physics_inputs/'+n for n in ('runs.json','observed_run_map.json','plan.json','checkpoint.json',
       'provenance.json','input_receipts.json','collector.py','metadata_capture.json','transport_commands.json',
       'collection_status.json')],'command_ownership/registry.lock',
      *[r['copied_path'] for r in capture['files'].values()],*['tools/'+n for n in TOOLS],
      *[p+'/'+n for p in ('shock','vortex') for n in
        ('runs_checkpoint.json.gz','provenance_checkpoint.json','reduce_reference.py')]}
    selected,omitted = set(),{}
    ownership = ownership_paths(manifest)
    for name,digest in manifest.items():
        safe_name(name)
        key = omission_key(name)
        if key:
            input_key,compressed = key
            require(input_key in summary['raw_input_identities'],'Unregistered omitted input: '+name)
            omitted[name] = dict(sha256=digest,raw_input_key=input_key,
                encoding='gzip' if compressed else 'identity',
                decoded_sha256=summary['raw_input_identities'][input_key]['sha256'],
                decoded_bytes=summary['raw_input_identities'][input_key]['bytes'],
                reason='large actual raw input or reducer duplicate retained externally')
            if not compressed:
                require(digest == summary['raw_input_identities'][input_key]['sha256'],'Omitted raw digest')
            continue
        require(name in required or name in ownership or name.startswith(('observations/','logs/','physics_inputs/metadata/',
                'physics_inputs/download/','physics_inputs/transport_logs/')),'Unclassified collection file: '+name)
        selected.add(name)
    require(required <= selected,'Missing selected reports/tools/observations: '+str(required-selected))
    require({n[6:] for n in selected if n.startswith('tools/')} == TOOLS,'Exact tool inventory')
    return selected,omitted


class Fresh:
    def __init__(self,root,index):
        self.root,self.index,self.rows = root,index,{}
        self.manifest_bytes = safe_path(root,'fresh/original_collection_sha256.json').read_bytes()
        self.manifest_digest = sha(self.manifest_bytes)
        require(self.manifest_digest == index['input_collection_manifest_sha256'],'Disconnected original manifest')
        self.manifest = loads(self.manifest_bytes)
        require(isinstance(self.manifest,dict),'Original manifest must be object')
        for n,d in self.manifest.items():
            safe_name(n)
            require(isinstance(d,str) and re.fullmatch('[0-9a-f]{64}',d),'Invalid original digest')
        manifests = [r for r in index['artifacts'] if r['path'] == 'fresh/original_collection_sha256.json']
        require(len(manifests) == 1 and manifests[0]['encoding'] == 'identity'
            and manifests[0]['original_sha256'] == self.manifest_digest
            and manifests[0]['origin'] == dict(kind='full_original_collection_manifest',
                manifest_sha256=self.manifest_digest,raw_inputs_retained_outside_this_packet=True),
            'Disconnected manifest artifact origin')
        for row in index['artifacts']:
            origin = row['origin']
            if origin['kind'] == 'complete_fresh_collection':
                name = origin['path']
                require(name not in self.rows,'Duplicate fresh origin')
                safe_name(name)
                require(origin['manifest_sha256'] == self.manifest_digest,'Disconnected origin manifest')
                require(name in self.manifest and row['original_sha256'] == self.manifest[name],
                        'Disconnected origin path/digest: '+name)
                require(row['path'] == 'fresh/'+name+('.gz' if row['encoding'] == 'gzip' else ''),
                        'Incorrect fresh export path')
                self.rows[name] = row

    def raw(self,name):
        require(name in self.rows,'Unexported fresh metadata: '+name)
        return decode_artifact(self.root,self.rows[name])

    def json(self,name):
        data = self.raw(name)
        return loads(gzip.decompress(data) if name.endswith('.gz') else data)

    def digest(self,name):
        return sha(self.raw(name))


def check_capture(fresh):
    c,s = fresh.json('metadata_capture.json'),fresh.json('summary.json')
    require(c['schema'] == 'm1-metadata-capture-v1','Capture schema')
    require(s['capture_manifest_sha256'] == fresh.digest('metadata_capture.json'),'Capture hash')
    check_runtime(c['runtime']);check_runtime(s['runtime'])
    require(c['final_unchanged_check']['passed'] is True
            and c['final_unchanged_check']['files'] == len(c['files']),'Unclosed capture')
    require(timestamp(c['final_unchanged_check']['checked_utc']) >= timestamp(c['captured_utc']),
            'Capture closure timestamps')
    require(c['attempts'] and c['attempts'][-1]['outcome'] == 'stable','No stable capture')
    reverse = {}
    for original,row in c['files'].items():
        copied = row['copied_path']
        require(copied not in reverse,'Ambiguous copied observation')
        reverse[copied] = original
        data = fresh.raw(copied)
        require(sha(data) == row['sha256'] and len(data) == row['bytes'],'Captured exact bytes')
    require(s['observation_sha256'] == {n:r['sha256'] for n,r in c['files'].items()},
            'Disconnected observation map')
    require({n for n in fresh.rows if n.startswith('observations/')} <= set(reverse),
            'Uncaptured observations')
    require(set(reverse) == {n for n in fresh.rows if n.startswith('observations/')}|
        {'registered_verdict.json',*['tools/'+n for n in TOOLS]},'Exact captured metadata roles')
    for name,digest in s['source_sha256'].items():
        copied = 'tools/'+PurePosixPath(name).name
        require(name in c['files'] and c['files'][name]['copied_path'] == copied
                and fresh.digest(copied) == digest,'Source/capture identity')
    expected_sources = {('tools/m1_evidence/' if n in
        {'prepare_final_evidence.py','collect_fresh_physics_reference_inputs.py'} else
        'tests/reference/m1_acceptance/')+n for n in TOOLS}
    require(set(s['source_sha256']) == expected_sources,'Exact source inventory')
    require({n for n in fresh.rows if n.startswith('observations/historical_a/')} ==
        {'observations/historical_a/iter-'+p+'_runs.json.gz' for p in COUNTS},'Exact captured A map inventory')
    for copied,original in reverse.items():
        if copied.startswith('observations/'):
            parts = PurePosixPath(copied).parts
            if parts[1] in COUNTS:
                phase = parts[1]
                if parts[2:] == ('specifications.json',):
                    expected = 'results/m1_final_campaign_cases_20261121/iter-'+phase+'.json'
                else:
                    tail = parts[3:] if parts[2] == 'cases' else parts[2:]
                    expected = str(PurePosixPath('results/followup_iter-'+phase+'_20261121').joinpath(*tail))
            elif parts[1] == 'historical_a':
                expected = 'tests/reference/m1_iterative_step_campaigns/iter/plans/'+parts[-1]
            else:
                require(parts[1] == 'reference_inputs','Unrecognized observation origin')
                expected = str(PurePosixPath(*parts[2:]))
            require(original == expected,'Observation original-to-copy path: '+copied)
    require(reverse.get('registered_verdict.json') == 'results/followup_iter_verdict_20261121.json',
            'Uncaptured registered verdict origin')
    return c,reverse


def check_source_context(fresh,root,frozen):
    """Pin immutable imported reducers; the two repaired hosts have their own capture identity."""
    host = {'prepare_final_evidence.py','collect_fresh_physics_reference_inputs.py'}
    for name in TOOLS-host:
        require(fresh.raw('tools/'+name) == safe_path(root,'source_review_packet/'+name).read_bytes(),
                'Changed frozen analysis source: '+name)
    refs = ['benchmarks/m0/packet.json',*['tests/reference/external_mhd/'+n for n in
            ('provenance.json','brio_8192.csv.gz','vortex_512.csv.gz')]]
    expected = {'observations/reference_inputs/'+n for n in refs}
    optional = {'observations/reference_inputs/results/followup_iter-'+p+'_20261117/runs.json' for p in COUNTS}
    require({n for n in fresh.rows if n.startswith('observations/reference_inputs/')} <= expected|optional
        and expected <= set(fresh.rows),'Exact captured reference context')
    for n in refs:
        require(fresh.raw('observations/reference_inputs/'+n) == safe_path(frozen,n).read_bytes(),
                'Reducer cwd reference bytes differ: '+n)


def check_case_command(run,spec):
    command,c = run['command'],spec['config']
    require(PurePosixPath(command[0]).name == 'vector-potential' and len(command[1:])%2 == 0,
            'Candidate binary/flag syntax')
    flags = dict(zip(command[1::2],command[2::2]))
    require(len(flags)*2 == len(command)-1,'Duplicate candidate flag')
    expected = {'--case':c['case'],'--profile':c['profile'],'--n':str(c['n']),
      '--jitter':str(c['jitter']),'--time':str(c.get('target',c.get('time'))),'--motion':'rigid',
      '--boost-x':str(c['boost'][0]),'--boost-y':str(c['boost'][1]),'--boost-z':str(c['boost'][2]),
      '--threads':str(spec['resources']['threads']),'--riemann':'hlld-pressure',
      '--potential-limiter':'smooth-extrema','--projection-screening':'1.0'}
    if spec['kind'] == 'wave':
        expected.update({'--parallel-velocity':str(c['parallel']),
          '--mesh-x':str(c['mesh_velocity'][0]),'--mesh-y':str(c['mesh_velocity'][1])})
        if c['case'] == 'smooth':
            expected.update({'--mean-bx':'.3','--mean-by':'.2','--mean-bz':'.1'})
        else:
            expected['--checkpoint'] = '.25'
        if c['dt'] is not None:
            expected['--dt'] = str(c['dt'])
    else:
        expected.update({'--mesh-x':str(c['boost'][0]),'--mesh-y':str(c['boost'][1])})
        if c['jitter_mode'] == 'columns':
            expected['--jitter-mode'] = 'columns'
    require(PurePosixPath(flags.pop('--output','')).parts[-3:] == ('outputs','raw',c['name']),
            'Wrong output command path')
    require(flags == expected,'Changed candidate flags/fraction/projection defaults')


def check_phase_coverage(entries,runs,registered,receipts,count):
    require(len(entries) == len(runs) == count
        and set(entries) == set(runs) == set(registered) == set(receipts),'Exact phase name/receipt coverage')


def check_submission(workflow,payload,spec,snapshot,preflight_hashes):
    """Portable metadata links; assembled part BYTES were witnessed by the strict verifier."""
    resources = spec['resources']
    require(set(payload['parts']) == {'source.tar.gz','vector-potential'},'Assembled payload set')
    parts = payload['parts']
    require(parts['source.tar.gz'] == snapshot['archives']['source.tar.gz']['parts'],'Source part order')
    for filename,names in parts.items():
        require(names == [f'{filename}.part{i:03}' for i in range(len(names))] and names,'Contiguous payload parts')
    base = {'case.json','case.py','snapshot.json',*['preflight/'+n for n in preflight_hashes]}
    require(set(payload['input_sha256']) == base|set(parts['source.tar.gz'])|set(parts['vector-potential']),
            'Exact staged metadata/parts inventory')
    for n,d in preflight_hashes.items():
        require(payload['input_sha256']['preflight/'+n] == d,'Staged preflight file identity')
    require(all(payload['input_sha256'][n] == snapshot['upload_sha256'][n]
                for n in parts['source.tar.gz']),'Source upload-part identity')
    expected_step = dict(name='one-case',environment=IMAGE,compute_backend='kubernetes',
        kubernetes_memory_limit=resources['memory'],kubernetes_cpu_request=str(resources['threads']),
        kubernetes_cpu_limit=str(resources['threads']),commands=['python3 case.py'])
    require(workflow == dict(version='0.9.0',inputs=dict(files=[*payload['input_sha256'],'payload.json']),
        workflow=dict(type='serial',specification=dict(steps=[expected_step])),
        outputs=dict(files=['outputs/execution.json','outputs/record.json','outputs/artifacts.sha256.json'])),
        'Exact single-case workflow/resources/staged input order')
    require(resources['threads'] in (2,4) and math.isfinite(resources['timeout_seconds'])
        and resources['timeout_seconds'] > 0,'Exact case resources')


def check_execution_receipt(receipt,entry,spec,execution,run,record,artifacts,hashes,preflight_digest):
    require(receipt['specification'] == spec and receipt['workflow'] == entry['workflow']
        and receipt['payload_sha256'] == entry['payload_sha256']
        and receipt['workflow_sha256'] == entry['workflow_sha256'],'Receipt submission link')
    require(receipt['execution'] == execution and record == run,'Record/execution semantics')
    require(receipt['execution_sha256'] == hashes['execution.json'] == artifacts['outputs/execution.json']
        and execution['record_sha256'] == hashes['record.json'] == artifacts['outputs/record.json'],
        'Execution/record artifact digests')
    require(receipt['artifact_manifest_sha256'] == hashes['artifacts.sha256.json']
        and receipt['artifacts'] == artifacts,'Artifact manifest receipt')
    require(execution['status'] == 'completed' and execution['single_case_gates_passed'] is True
        and execution['case'] == spec and execution['snapshot_sha256'] == SNAPSHOT
        and execution['binary_sha256'] == BINARY and execution['payload_sha256'] == entry['payload_sha256']
        and execution['preflight_sha256'] == preflight_digest,'Execution source/candidate identity')
    require(timestamp(execution['ended_utc']) >= timestamp(execution['started_utc'])
        and execution['machine'] and execution['visible_cpus'] > 0
        and isinstance(execution['cgroup'],dict),'Execution runtime')
    require(all(safe_name(n).parts[0] == 'outputs' for n in artifacts),'Unsafe remote artifact')
    checked,absent = receipt['checked_downloads'],receipt['not_downloaded_not_byte_verified']
    require(len(checked) == len(set(checked)) and len(absent) == len(set(absent))
        and not set(checked)&set(absent) and set(checked)|set(absent) == set(artifacts),'Download receipt partition')
    name = spec['config']['name']
    require(receipt['final_csv_sha256'] == run['sha256']['final.csv'] == artifacts['outputs/raw/'+name+'/final.csv'],
            'Final CSV linkage')


def check_phases(fresh,historical,snapshot,preflight_digest,preflight_hashes):
    all_runs,all_plans,all_prov = {},{},{}
    capture,reverse = check_capture(fresh)
    for phase,count in COUNTS.items():
        prefix = 'observations/'+phase+'/'
        plan,runs,checkpoint,specs = (fresh.json(prefix+n+'.json') for n in
                                      ('plan','runs','checkpoint','specifications'))
        old = read(historical,'iter/plans/iter-'+phase+'_plan.json.gz')
        registered = semantic_plan_match(plan,specs,old)
        entries = plan_entries(plan)
        require(plan['schema'] == 1 and plan['snapshot_sha256'] == SNAPSHOT,'Phase snapshot/schema')
        require(plan['analysis_sha256'] == {n:d for n,d in snapshot['source_sha256'].items()
                if n.startswith(('scripts/','benchmarks/'))},'Exact plan analysis sources')
        require(checkpoint['all_terminal'] is True
                and checkpoint['completed_cases'] == checkpoint['expected_cases'] == count,
                'Nonterminal phase')
        require(not any(checkpoint[k] for k in ('verified_required_failure','failures',
                'execution_failures','observation_errors','full_m1_accepted')),'Failed checkpoint')
        workflows = {r['workflow'] for r in entries.values()}
        require(set(checkpoint['workflow_states']) == workflows,'Checkpoint workflow coverage')
        require(all(s['status'] == 'finished' and s['name']+'.'+str(s['run_number']) == w
                    and s['command'] == 'python3 case.py'
                    for w,s in checkpoint['workflow_states'].items()),'Checkpoint workflow execution links')
        pr = fresh.json(phase+'_provenance.json')
        check_phase_coverage(entries,runs,registered,pr['receipts'],count)
        require(pr['phase'] == phase and pr['cases'] == count and pr['all_verified'] is True
                and pr['full_m1_accepted'] is False and set(pr['receipts']) == set(entries),'Strict phase result')
        require(pr['snapshot_sha256'] == SNAPSHOT and pr['binary_sha256'] == BINARY
                and pr['analysis_source_sha256'] == fresh.digest('tools/verify_fresh_phase.py'),
                'Strict verifier identities')
        for label,key in (('plan','plan_sha256'),('runs','run_map_sha256'),
                          ('checkpoint','checkpoint_sha256'),('specifications','registered_specifications_sha256')):
            require(fresh.digest(prefix+label+'.json') == pr[key] and prefix+label+'.json' in reverse,
                    'Phase observation/capture link')
        expected_metadata = {prefix+n+'.json' for n in ('plan','runs','checkpoint','specifications')}
        for name,run in runs.items():
            entry,spec = entries[name],registered[name]
            c,resources = spec['config'],spec['resources']
            require(c['profile'] == CONFIGURATION['profile'] and c['riemann_solver'] == 'hlld-pressure'
                and spec['options'] == dict(accelerated_projection=False,projection_screening=1.,
                                          potential_limiter='smooth-extrema'),'Candidate options')
            require(run['config'] == c and run['status'] == 'completed' and run['returncode'] == 0,'Run config/status')
            case = prefix+'cases/'+entry['directory']+'/'
            output = prefix+'download/'+entry['directory']+'/outputs/'
            names = [case+n for n in ('case.json','payload.json','reana.yaml','snapshot.json','preflight/preflight.json')]
            names += [output+n for n in ('execution.json','record.json','artifacts.sha256.json')]
            if output+'runtime.json' in fresh.rows:
                names.append(output+'runtime.json')
            expected_metadata.update(names)
            payload,workflow = fresh.json(case+'payload.json'),fresh.json(case+'reana.yaml')
            require(fresh.json(case+'case.json') == spec and fresh.digest(case+'snapshot.json') == SNAPSHOT
                and fresh.digest(case+'preflight/preflight.json') == preflight_digest,'Case spec/snapshot/preflight')
            require(fresh.digest(case+'payload.json') == entry['payload_sha256']
                and fresh.digest(case+'reana.yaml') == entry['workflow_sha256'],'Payload/workflow links')
            for filename,digest in [('case.json',fresh.digest(case+'case.json')),('snapshot.json',SNAPSHOT),
                ('preflight/preflight.json',preflight_digest),('case.py',snapshot['source_sha256']['reana/case.py'])]:
                require(payload['input_sha256'][filename] == digest,'Payload metadata/source digest')
            check_submission(workflow,payload,spec,snapshot,preflight_hashes)
            receipt = pr['receipts'][name]
            execution,record,artifacts = (fresh.json(output+n) for n in
                                         ('execution.json','record.json','artifacts.sha256.json'))
            check_execution_receipt(receipt,entry,spec,execution,run,record,artifacts,
                {n:fresh.digest(output+n) for n in ('execution.json','record.json','artifacts.sha256.json')},
                preflight_digest)
            if output+'runtime.json' in fresh.rows:
                require(artifacts['outputs/runtime.json'] == fresh.digest(output+'runtime.json'),
                        'Optional runtime artifact link')
            require(receipt['staged_input_files_verified'] == len(payload['input_sha256']),'Strict staged count')
            require(receipt['final_csv_sha256'] == run['sha256']['final.csv'] == artifacts['outputs/raw/'+name+'/final.csv'],
                    'Final CSV linkage')
            check_case_command(run,spec)
            s,h = run['summary'],run['history']
            target = c.get('time',c.get('target'))
            require(s['completed'] is True and s['time'] == target and s['profile'] == c['profile']
                and s['potential_limiter'] == 'smooth-extrema-v1' and s['riemann_solver'] == 'hlld-pressure-blend-v1'
                and s['projection_screening'] == 1. and 'projection_solver' not in s
                and 'trial_step_fraction' not in s,'Run candidate defaults')
            require(h[0]['time'] == 0 and h[-1]['time'] == target
                and all(a['time'] < b['time'] for a,b in zip(h,h[1:]))
                and h[0]['diagnostics'] == s['initial'] and h[-1]['diagnostics'] == s['final'],'History endpoints/times')
            for row in h:
                d = row['diagnostics']
                require(len(d['normalized_budget']) == 5 and d['rho_min'] > 0 and d['p_min'] > 0
                    and all(math.isfinite(v) for v in (d['rho_min'],d['p_min'],*d['normalized_budget']))
                    and max(map(abs,d['normalized_budget'])) <= 1e-10,'Recorded positive/conservative history')
            require(run['positive_and_conservative'] is True,'State gate')
            if phase == 'physics':
                require(run['state_and_diagnostic_gates'] is True and run['diagnostic_checks']
                    and all(v is True for v in run['diagnostic_checks'].values()),'Physics diagnostics')
        require({n for n in fresh.rows if n.startswith(prefix)} == expected_metadata,'Exact phase metadata inventory')
        require(pr['counters'] == {k:sum(r['summary'][k] for r in runs.values()) for k in
                ('steps','rejected_geometry','rejected_state','rejected_cfl','hll_fallbacks')}
            and pr['maximum_recorded_budget'] == max(abs(v) for r in runs.values()
                for h in r['history'] for v in h['diagnostics']['normalized_budget']),'Strict aggregate receipt consistency')
        previous = 'observations/reference_inputs/results/followup_iter-'+phase+'_20261117/runs.json'
        old_live = fresh.json(previous) if previous in fresh.rows else {}
        require(pr['final_csv_byte_identical_to_campaign_a'] == sum(
            old_live.get(n,{}).get('sha256',{}).get('final.csv') == r['sha256']['final.csv']
            for n,r in runs.items()),'Strict comparison-only live-A count')
        all_runs[phase],all_plans[phase],all_prov[phase] = runs,plan,pr
    return all_runs,all_plans,all_prov,capture


def check_a_identity(row,old,filename):
    actual = row['sha256'] == old['sha256'][filename]
    require(row['byte_identical_to_a'] is actual,'Unproven A identity flag')
    return actual


def check_raw_identities(fresh,runs,provenance,historical):
    summary = fresh.json('summary.json')
    capture = fresh.json('metadata_capture.json')
    repo,out = check_command_links(fresh.json('commands.json'),capture)
    rows = summary['raw_input_identities']
    require(set(rows) == raw_input_names(runs),'Exact238 raw input coverage')
    matched = 0
    for phase in COUNTS:
        old_bytes = decoded_file(historical,'iter/plans/iter-'+phase+'_runs.json.gz')
        require(gzip.decompress(fresh.raw('observations/historical_a/iter-'+phase+'_runs.json.gz')) == old_bytes,
                'Disconnected captured A run map')
        old = loads(old_bytes)
        require(set(old) == set(runs[phase]),'Historical A name coverage')
        for key,row in rows.items():
            p,name,filename = key.split('/')
            if p != phase:
                continue
            receipt = provenance[p]['receipts'][name]
            remote = 'outputs/raw/'+name+'/'+filename
            require(row['sha256'] == runs[p][name]['sha256'][filename] == receipt['artifacts'][remote]
                and row['workflow'] == receipt['workflow'] and row['remote_path'] == remote
                and row['artifact_manifest_sha256'] == receipt['artifact_manifest_sha256'],'Raw workflow/path/hash')
            require(type(row['bytes']) is int and row['bytes'] > 0,'Actual raw byte length')
            expected_copy = (p+'_inputs/'+name+'/'+filename) if p in ('waves','physics') else None
            # The wave adapter directory is singular by its frozen schema.
            if p == 'waves':
                expected_copy = 'wave_inputs/'+name+'/'+filename
            require(row['copied_path'] == expected_copy,'Raw materialized-copy identity')
            expected_source = (out/'physics_inputs'/name/filename if p == 'physics' else
                repo/capture['private_views'][p]['original_root']/'raw'/name/filename)
            require(row['local_source'] == str(expected_source),'Actual consumed source path')
            matched += check_a_identity(row,old[name],filename)
    require(summary['matched_a_inputs'] == matched,'Derived A match count')


def check_state_row(row,run):
    ds = [r['diagnostics'] for r in run['history']]
    require(row == dict(minimum_recorded_density=min(d['rho_min'] for d in ds),
        minimum_recorded_pressure=min(d['p_min'] for d in ds),
        maximum_recorded_budget=max(abs(v) for d in ds for v in d['normalized_budget']),passed=True),
        'Independent state/history receipt')


def check_pair_partition(rows,runs,expected):
    names = [n for row in rows for n in row['names']]
    require(len(names) == len(set(names)) and set(names) == set(runs),'Pair name partition')
    require({tuple(r['names']) for r in rows} == {tuple(r['names']) for r in expected},'Wrong checkpoint pairs')
    for r in rows:
        a,b = r['names']
        require(r['passed'] is True and runs[a]['config']['boost'] == [0.,0.,0.]
            and runs[b]['config']['boost'] == [2.,-1.,0.],'Pair frames/pass')


def check_wave_pair(row,run):
    loop = run['config']['case'] == 'loop'
    conventions = {'loop_amplitude':{'B'}} if loop else {
        'wave_amplitude':{'rho','p','energy','B','v'},
        'mean_field_and_initial_speed':{'rho','p','energy','B','v'}}
    require(set(row['relative_L1']) == set(conventions) and row['limit'] == (.001 if loop else 1e-8),
            'Wave normalizations/limit')
    for convention,fields in conventions.items():
        values = row['relative_L1'][convention]
        require(set(values) == fields and all(math.isfinite(x) and 0 <= x <= row['limit']
                for x in values.values()),'Wave boost norms')
    require(0 <= row['position_max'] <= 1e-11 and 0 <= row['relative_volume_max'] <= 1e-11
        and row['case'] == run['config']['case'] and row['n'] == run['config']['n'],'Wave pair fields')


def check_mean_pair(row,runs):
    require(row['input_sha256'] == {n:runs[n]['sha256']['final.csv'] for n in row['names']},
            'Mean pair input hashes')
    require(set(row['maximum_errors']) == FIELDS and all(0 <= x <= 1e-9 for x in row['maximum_errors'].values())
        and 0 <= row['position_max'] <= 1e-11 and 0 <= row['volume_relative_max'] <= 1e-11
        and row['matching_auxiliary_roots'] is True and 0 <= row['maximum_recorded_budget'] <= 1e-10,'Mean gates')


def check_mean_refinement(summary,runs):
    """Finding 1: frozen run_m1_campaign.py:76-90 / wave_loop.py:226-241.

    Preserve historical empty profile rows. The four CANDIDATE rows must be
    real observations of their captured production pairs, not merely four
    plausible coordinates. No accuracy/order bound applies to these roundoff-
    sensitive boost residuals; successive orders retain only their source gate
    (array length), including negative orders and nulls for zero errors.
    """
    expected = {(j,v):coords for j in (0.,.15) for v,coords in
                (('n',[8,16,32,64]),('dt',[.001,.0005,.00025]))}
    rows = [r for r in summary['mean_refinement'] if r['profile'] == CONFIGURATION['profile']]
    keys = [(r['jitter'],r['variable']) for r in rows]
    require(len(rows) == 4 and len(set(keys)) == 4 and set(keys) == set(expected),
            'Exact four candidate mean-refinement observations')
    pairs = summary['pairs']
    require(len(pairs) == 12,'Mean refinement production pair inventory')
    for pair in pairs:
        require(len(pair['names']) == 2 and all(n in runs for n in pair['names']),
                'Mean observation pair owners')
        c = runs[pair['names'][0]]['config']
        metadata = dict(case=c['case'],profile=c['profile'],n=c['n'],jitter=c['jitter'],
                        parallel=c['parallel'],motion=c['motion_family'],dt=c['dt'],time=c['target'])
        require(all(pair[k] == v for k,v in metadata.items()),'Mean pair coordinate/config identity')
        require(finite_number(pair['errors']['B']['L1'],True),'Invalid recorded mean B residual')
    for row in rows:
        key = row['jitter'],row['variable']
        values = row['values']
        require(isinstance(values,list) and all(isinstance(v,list) and len(v) == 2 for v in values)
            and [v[0] for v in values] == expected[key]
            and all(finite_number(v[1],True) for v in values),'Mean refinement coordinates/measurements')
        variable = row['variable']
        chosen = [p for p in pairs if p['case'] == 'smooth' and p['profile'] == CONFIGURATION['profile']
                  and p['jitter'] == row['jitter'] and
                  (p['dt'] == .00025 if variable == 'n' else p['n'] == 16)]
        chosen.sort(key=lambda p:p[variable],reverse=variable == 'dt')
        require(values == [[p[variable],p['errors']['B']['L1']] for p in chosen],
                'Mean refinement disconnected from captured production pairs')
        require(isinstance(row['successive_B_L1_orders'],list)
            and len(row['successive_B_L1_orders']) == len(values)-1,'Mean observation order-array length')


def check_calibration_wave(runs):
    """Frozen fanout_campaign_verdict.py:156-166: exactly both named frames."""
    names = {n for n,r in runs.items() if r['config']['case'] == 'alfven' and r['config']['n'] == 128
        and r['config']['jitter'] == .15 and r['config']['parallel'] == 0.
        and r['config']['motion_family'] == 'fixed' and r['config']['dt'] is None}
    prefix = 'alfven_bulk-frame-heun-quadratic-v1_v0.0_j0.15_fixed_n128_'
    require(names == {prefix+'base',prefix+'boost'},'Exact two N128 calibration cases')
    for n in names:
        r = runs[n];error = r['errors']['final']['B']['L1']
        require(r['status'] == 'completed' and r['positive_and_conservative'] is True
            and finite_number(error,True) and error/.1 <= .02,'N128 calibration amplitude error')
    return names


def check_registered_observations(fresh,runs):
    """Source gates join already hash-bound observations, not fresh true flags.

    Plan/config/state/short-stage links are checked by check_phases/preflight;
    pair/reference/spatial links by check_reports; per-case physics by
    check_physics_diagnostics. Here close the formerly absent mean/calibration
    observations and production summary links. No mean or temporal order gate.
    """
    checkpoints = {p:fresh.json('observations/'+p+'/checkpoint.json') for p in COUNTS}
    check_mean_refinement(checkpoints['mean']['summaries']['wave'],runs['mean'])
    chosen = check_calibration_wave(runs['waves'])
    for p,count in (('medium',24),('mean',12),('waves',48)):
        pairs = checkpoints[p]['summaries']['wave']['pairs']
        require(len(pairs) == count and all(x['status'] in ('pass','pass under both reported normalizations')
            for x in pairs),'Captured production pair gate: '+p)
    require(len([p for p in checkpoints['waves']['summaries']['wave']['pairs'] if set(p['names']) == chosen]) == 1,
            'Calibration pair must be a captured production observation')
    wave = checkpoints['waves']['summaries']['wave']
    temporal = wave['temporal']
    require(isinstance(temporal,list) and len(temporal) == 12 and all(
        t['status'] == 'completed' and finite_number(t['errors']['B']['L1']) for t in temporal),
        'Captured temporal measurements (no order gate)')
    summary = checkpoints['physics']['summaries']['physics']
    require(summary['all_registered_physics_gates'] is True and summary['state_and_diagnostic_gates'] is True
        and summary['complete'] is True and summary['registered_configuration'] is True
        and summary['quick'] is False and summary['completed_evolutions'] == summary['expected_evolutions'] == 30,
        'Captured complete physics ladder')
    selected = [r for r in runs['physics'].values() if r['config']['case'] == 'orszag-tang'
        and r['config']['n'] == 128 and r['config']['jitter'] == .15 and not any(r['config']['boost'])]
    require(len(selected) == 1 and selected[0]['status'] == 'completed'
        and selected[0]['state_and_diagnostic_gates'] is True,'Captured calibration vortex')


def check_physics_diagnostics(run,packet,amendment):
    """Finding 2: frozen run_m1_physics.py:29-47,75-77,233-248.

    These are archived scalar/history checks, NOT a raw-operator calculation.
    Shock travel is a retained accepted-stage counter: its duplicate and source
    tracking configuration can be checked, but the history does not retain all
    reconstructed-stage characteristic speeds needed to reintegrate it.
    Apps vector-potential.rs:609,1053-1056 tracks only Brio; general.rs:1735-1749
    accumulates the accepted dt*stage-max travel. Do not invent a speed history.
    Vortex divergence is specifically div_B_limited.dimensionless.rms, never
    div_B_ls, div_B_face or a replacement operator.
    """
    c,p,values,checks = (run[k] for k in ('config','physics','diagnostic_values','diagnostic_checks'))
    require(c['case'] in {'brio-wu','orszag-tang'},'Unknown registered physics case')
    shock = c['case'] == 'brio-wu'
    require(p['nx'] == c['n'] and p['ny'] == c['ny']
        and p['lengths'] == ([2.,.125] if shock else [1.,1.])
        and p['signal_tracking'] is shock and finite_number(p['signal_travel_x'],True),
        'Physics configuration/tracking/travel identity')
    require(shock or p['signal_travel_x'] == 0.,'Untracked vortex travel must stay zero')
    history = run['history']
    require(history and history[0]['time'] == 0. and history[-1]['time'] == c['time']
        and history[0]['diagnostics'] == run['summary']['initial']
        and history[-1]['diagnostics'] == run['summary']['final'],'Physics diagnostic history endpoints')
    positive = True
    for h in history:
        d = h['diagnostics']
        require(finite_number(d['rho_min']) and finite_number(d['p_min'])
            and len(d['normalized_budget']) == 5
            and all(finite_number(v) for v in d['normalized_budget']),'Invalid physics state history')
        positive = positive and d['rho_min'] > 0 and d['p_min'] > 0 and all(
            abs(v) <= packet['solver']['budget_tolerance'] for v in d['normalized_budget'])
    gate = packet['cases'][c['case']]['gate']
    if shock:
        require(set(values) == {'bx_max_error','bx','signal_travel_x'},'Exact shock diagnostic values')
        require(values['signal_travel_x'] == p['signal_travel_x'],'Duplicated shock travel')
        bx = values['bx']
        require(set(bx) == {'initial','final','gate_applies','passed'},'Exact shock Bx receipt')
        for stage in ('initial','final'):
            require(set(bx[stage]) == {'max','L1'} and all(finite_number(v,True)
                    for v in bx[stage].values()),'Shock initial/final Bx diagnostic norms')
        require(values['bx_max_error'] == bx['final']['max'],'Duplicated final Bx maximum')
        family = 'regular' if c['jitter'] == 0. else c['jitter_mode']
        applies = family in amendment['bx_gate_meshes']
        require(bx['gate_applies'] is applies,'Bx mesh-family applicability')
        passed = bx['final']['max'] <= amendment['bx_max_error'] if applies else None
        require(bx['passed'] is passed,'Bx preservation/planar diagnostic-only disposition')
        expected = dict(signal_tracking=p['signal_tracking'],
                        seam_isolated=0 <= p['signal_travel_x'] < gate['seam_max_signal_travel'])
        if applies:
            expected['bx_preserved'] = passed
    else:
        expected_keys = {'mean_B_drift_over_Bscale_max','limited_face_dimensionless_divB_RMS_max'}
        require(set(values) == expected_keys,'Exact vortex diagnostic values')
        drift,rms = [],[]
        for h in history:
            d = h['diagnostics']
            require(isinstance(d['mean_B_drift'],list) and len(d['mean_B_drift']) == 3
                and all(finite_number(x) for x in d['mean_B_drift'])
                and finite_number(d['div_B_limited']['dimensionless']['rms'],True),
                'Named vortex vector/divergence history')
            drift.append(math.sqrt(sum(x*x for x in d['mean_B_drift']))/(1/math.sqrt(4*math.pi)))
            rms.append(d['div_B_limited']['dimensionless']['rms'])
        measured = dict(mean_B_drift_over_Bscale_max=max(drift),
                        limited_face_dimensionless_divB_RMS_max=max(rms))
        for k in expected_keys:
            require(finite_number(values[k],True),'Invalid vortex diagnostic value')
            roundoff_match(values[k],measured[k],'vortex history maximum: '+k)
        # Preserve BOTH actual source bounds; roundoff consistency never relaxes them.
        expected = {k:values[k] <= gate[k] and measured[k] <= gate[k] for k in expected_keys}
    require(set(checks) == set(expected) and all(type(v) is bool for v in checks.values())
        and checks == expected,'Exact physics diagnostic flags/values')
    diagnostic = all(expected.values())
    require(run['positive_and_conservative'] is positive and run['diagnostic_gates'] is diagnostic
        and run['state_and_diagnostic_gates'] is (positive and diagnostic)
        and positive and diagnostic,'Physics state/diagnostic gate consistency')


def check_primary_shock_bx(row,run,amendment):
    """Same final CSV f64 abs(Bx-.75) maximum, independently retained in reduce_shock.py:146.

    This copied scalar uses the same binary64 subtraction/max, not a fit with a
    solve uncertainty. Require exact scalar equality, plus the unchanged Bx gate
    on these primary regular/column cases; do not pretend to reread omitted CSVs.
    """
    value = row['final_Bx_max_error']
    bx = run['diagnostic_values']['bx']
    require(finite_number(value,True) and value == bx['final']['max']
        == run['diagnostic_values']['bx_max_error'],'Independent primary shock Bx receipt')
    require(bx['gate_applies'] is True and bx['passed'] is True
        and value <= amendment['bx_max_error'],'Primary shock Bx preservation gate')


def check_wave_error_agreement(row,run):
    """Frozen reduce_waves.py:164-168, no raw analytic-wave evaluation here."""
    independent,production = row['analytic_errors'],run['errors']['final']
    require(set(independent) == set(production) == WAVE_FIELDS,'Exact analytic wave norm fields')
    for norms in (*independent.values(),*production.values()):
        require(set(norms) == {'L1','L2','max'} and all(finite_number(v,True) for v in norms.values()),
                'Analytic wave norm shape/values')
    disagreement = max(abs(independent[f][n]-production[f][n])
        for f in WAVE_FIELDS for n in ('L1','L2','max'))
    # Same retained binary64 values and subtraction/max: no fit/solve tolerance.
    require(row['maximum_production_error_difference'] == disagreement and disagreement < 2e-13,
            'Analytic independent/production input agreement')


def spatial_fit_metadata(errors,endpoint):
    """Finding 3, manual scalar audit of frozen fits; never a snapshot reduction.

    reduce_waves.py:203-221 uses p=ln(e64/e256)/ln(4). Production
    run_m1_wave_loop.py:213-223,293-305 uses the centered three-point LS slope.
    With x=ln(1/N), y=ln(e), N=(64,128,256), Sxx=sum((x-xbar)^2),
    both are mathematically the same slope. One residual degree of freedom
    gives sigma_p=sqrt(sum((y-ybar-p*(x-xbar))^2)/Sxx); the middle error affects
    sigma_p but not the exact endpoint slope. Compute each source's own variant
    on its own retained errors. Do not require identical production/independent
    fits when their norm inputs differ within the original 2e-13 agreement gate.
    The explicit log-centering scale is for roundoff_match only: no physical
    order, accuracy, systematic uncertainty or temporal gate is added/relaxed.
    """
    require(len(errors) == 3 and all(finite_number(e) and e > 0 for e in errors),
            'Spatial fit needs three positive finite scalar errors')
    x = [math.log(1/n) for n in (64,128,256)]
    y = [math.log(e) for e in errors]
    xm,ym = sum(x)/3,sum(y)/3
    variance = sum((a-xm)**2 for a in x)
    if endpoint:
        ratio = errors[0]/errors[2]
        require(finite_number(ratio) and ratio > 0,'Unresolved spatial endpoint ratio')
        order = math.log(ratio)/math.log(4)
    else:
        order = sum((a-xm)*(b-ym) for a,b in zip(x,y))/variance
    residual = sum((b-ym-order*(a-xm))**2 for a,b in zip(x,y))
    uncertainty = math.sqrt(residual/variance)
    scale = max(1.,*map(abs,x),*map(abs,y))*(1+abs(order))/math.sqrt(variance)
    require(all(finite_number(v,True) for v in (uncertainty,scale)) and finite_number(order),
            'Nonfinite spatial fit arithmetic')
    return order,uncertainty,scale


def check_spatial_ladder(row,production,runs,cases):
    """Complete captured independent AND production scalar fits, with original gates."""
    key = row['jitter'],row['parallel'],row['motion']
    require((production['jitter'],production['parallel'],production['motion']) == key,
            'Production/independent spatial ladder identity')
    prefix = f"alfven_bulk-frame-heun-quadratic-v1_v{row['parallel']}_j{row['jitter']}_{row['motion']}"
    names = [f'{prefix}_n{n}_base' for n in (32,64,128,256)]
    require(row['names'] == names and row['B_L1'] ==
        [cases[n]['analytic_errors']['B']['L1'] for n in names],'Spatial independent case inputs')
    require(all(finite_number(e) and e > 0 for e in row['B_L1']),'Positive spatial error inputs')
    require(production['rows'] == [dict(n=n,B_L1=runs[name]['errors']['final']['B']['L1'],
            status=runs[name]['status']) for n,name in zip((32,64,128,256),names)],
            'Production convergence disconnected from captured run errors')
    require(all(r['status'] == 'completed' and finite_number(r['B_L1']) and r['B_L1'] > 0
                for r in production['rows']),'Positive completed production fit inputs')
    for name in names:
        check_wave_error_agreement(cases[name],runs[name])
    for data,errors,endpoint,uncertainty_key,status_key in (
        (row,row['B_L1'],True,'residual_based_order_standard_error','status'),
        (production,[r['B_L1'] for r in production['rows']],False,'finest_three_order_standard_error','gate')):
        require(uncertainty_key in data and finite_number(data[uncertainty_key],True),
                'Missing/negative/nonfinite spatial residual standard error')
        order,uncertainty,scale = spatial_fit_metadata(errors[-3:],endpoint)
        roundoff_match(data['finest_three_order'],order,'spatial fitted order',scale)
        roundoff_match(data[uncertainty_key],uncertainty,'spatial residual standard error',scale)
        require(data[status_key] == 'pass' and data['finest_three_order'] >= 1.8 and order >= 1.8
            and data['finest_relative_B_L1'] == errors[-1]/.1 <= .02,'Unchanged spatial physical gates')
    require(production['uncertainty_scope'] == RESIDUAL_SCOPE,'Residual-only spatial uncertainty scope')


def check_reports(fresh,runs,provenance,frozen):
    wave,rs = fresh.json('waves_independent.json'),runs['waves']
    require(fresh.json('wave_inputs/runs.json') == rs,'Wave adapter runs')
    require(fresh.json('wave_inputs/manifest.json') == {n:r['config'] for n,r in rs.items()},
            'Wave manifest configs')
    require(wave['analysis_source_sha256'] == fresh.digest('tools/reduce_waves.py')
        and wave['run_map_sha256'] == fresh.digest('wave_inputs/runs.json')
        and wave['manifest_sha256'] == fresh.digest('wave_inputs/manifest.json'),'Wave reducer inputs/source')
    require(wave['recorded_runs'] == wave['manifest_runs'] == 112 and set(wave['cases']) == set(rs),
            'Wave case coverage')
    require(wave['reused_cases'] == wave['reused_pairs'] == 0
        and wave['verified_required_failure'] is False and wave['full_m1_accepted'] is False,'Wave cache/status')
    for k in ('pending_cases','pending_pairs','pending_temporal','failed_runs','failed_pairs','failed_spatial'):
        require(not wave[k],'Pending/failed wave channel: '+k)
    for name,row in wave['cases'].items():
        require(row['run_record_sha256'] == fingerprint(rs[name]),'Wave record fingerprint')
        check_state_row(row['state'],rs[name])
        if rs[name]['config']['case'] == 'alfven':
            check_wave_error_agreement(row,rs[name])
    expected_pairs = [dict(names=[n,n[:-5]+'_boost']) for n in rs if n.endswith('_base')]
    require(len(expected_pairs) == 48 and set(wave['pairs']) == {r['names'][0] for r in expected_pairs},
            'Exact48 wave pair keys')
    check_pair_partition(list(wave['pairs'].values()),
                         {n:r for n,r in rs.items() if not n.startswith('temporal_')},expected_pairs)
    for name,row in wave['pairs'].items():
        require(row['names'][0] == name and row['run_record_sha256'] ==
                [fingerprint(rs[n]) for n in row['names']],'Wave pair record inputs')
        check_wave_pair(row,rs[name])
    expected_spatial = {(j,p,m) for j in (0.,.15) for p in (0.,1.) for m in ('fixed','comoving')}
    require(len(wave['spatial']) == 8 and {(r['jitter'],r['parallel'],r['motion']) for r in wave['spatial']}
            == expected_spatial,'Exact8 spatial ladder identities')
    production_spatial = fresh.json('observations/waves/checkpoint.json')['summaries']['wave']['alfven_convergence']
    production_keys = [(r['jitter'],r['parallel'],r['motion']) for r in production_spatial]
    require(len(production_spatial) == 8 and len(set(production_keys)) == 8
        and set(production_keys) == expected_spatial,'Exact eight captured production spatial fits')
    production_spatial = dict(zip(production_keys,production_spatial))
    for row in wave['spatial']:
        check_spatial_ladder(row,production_spatial[row['jitter'],row['parallel'],row['motion']],rs,wave['cases'])
    temporal = {n for n,r in rs.items() if n.startswith('temporal_') and r['config']['dt'] != .000025}
    require(len(temporal) == 12 and set(wave['temporal']) == temporal,'Exact12 temporal comparisons')
    for name,row in wave['temporal'].items():
        ref = name.rsplit('_dt',1)[0]+'_dt2.5e-05'
        require(row['name'] == name and row['reference'] == ref and row['dt'] == rs[name]['config']['dt']
            and row['run_record_sha256'] == [fingerprint(rs[n]) for n in (name,ref)],'Temporal input linkage')
        require(set(row['errors']) == {'bx','by','bz','ax','ay','az','phi','B'},'Temporal fields')
        for k,s in (('actual_dt_max','dt_max'),('actual_dt_min','dt_min'),('steps','steps'),
                    ('rejected_state','rejected_state'),('rejected_cfl','rejected_cfl')):
            require(row[k] == rs[name]['summary'][s],'Temporal timestep receipt')
        require(row['reference_timesteps'] == {k:rs[ref]['summary'][k] for k in
                ('dt_cap','dt_min','dt_max','steps','rejected_state','rejected_cfl')},'Temporal reference metadata')
        # Orders and cap_reached remain observational: no invented gate.
    for label,phase,count in (('medium','medium',24),('mean','mean',12),('physics_boost','physics',15)):
        report = fresh.json(label+'_independent.json')
        script = 'reduce_mean.py' if label == 'mean' else 'reduce_boost_pairs.py'
        require(report['analysis_source_sha256'] == fresh.digest('tools/'+script)
            and report['run_map_sha256'] == provenance[phase]['run_map_sha256']
            and report['all_passed'] is True and report['full_m1_accepted'] is False,'Boost report identity/result')
        cp = fresh.json('observations/'+phase+'/checkpoint.json')
        pairs = cp['summaries']['physics' if phase == 'physics' else 'wave'][
                      'boost_pairs' if phase == 'physics' else 'pairs']
        require(len(report['pairs']) == count,'Boost pair count')
        check_pair_partition(report['pairs'],runs[phase],pairs)
        if label != 'mean':
            require(report['phase'] == phase and report['checkpoint_sha256'] == provenance[phase]['checkpoint_sha256']
                and report['wave_reducer_sha256'] == fresh.digest('tools/reduce_waves.py')
                and report['snapshot_sha256'] == {n:r['sha256']['final.csv'] for n,r in runs[phase].items()},
                'Boost checkpoint/import/snapshot identity')
        if phase == 'medium':
            require(set(report['states']) == set(runs[phase]),'Medium state coverage')
            for n,r in report['states'].items():
                check_state_row(r,runs[phase][n])
        for row in report['pairs']:
            require(row['maximum_production_disagreement'] < 1e-13,'Boost independent agreement receipt')
            if label == 'mean':
                check_mean_pair(row,runs[phase])
            elif phase == 'medium':
                check_wave_pair(row,runs[phase][row['names'][0]])
            else:
                require(set(row['relative_L1']) == set(row['scales']) == FIELDS
                    and all(0 <= x <= 1e-8 for x in row['relative_L1'].values())
                    and all(x > 0 for x in row['scales'].values()) and 0 <= row['position_max'] <= 1e-9
                    and 0 <= row['volume_relative_max'] <= 1e-9 and 0 <= row['maximum_recorded_budget'] <= 1e-10,'Physics boost gates')
    check_primary_reports(fresh,runs['physics'],frozen)


def check_primary_input_coverage(report,names,filenames,runs):
    require(set(report['measured']) == names and report['input_sha256'] ==
        {n+'/'+f:runs[n]['sha256'][f] for n in names for f in filenames},'Exact primary12/6 cases and24/18 inputs')


def check_bin_payload(bins,names):
    require(set(bins) == names,'Six independent bin entries')
    for row in bins.values():
        require(set(row) == {'rho','p','bx','by'},'Independent bin fields')
        require(all(isinstance(v,list) and len(v) == 4096 and all(type(x) in (int,float)
            and math.isfinite(x) for x in v) for v in row.values()),'Independent bin shape/finite data')


def check_primary_reports(fresh,runs,frozen):
    shock_names = {f'brio-wu_n{n}_j{j}'+('c' if family == 'columns' else '')+'_'+frame
        for family,j in (('regular',0.),('columns',.15)) for n in (256,512,1024) for frame in ('base','boost')}
    vortex_names = {f'orszag-tang_n{n}_j0.0_{frame}' for n in (64,128,256) for frame in ('base','boost')}
    packet = read(frozen,'benchmarks/m0/packet.json')
    amendment = read(frozen,'benchmarks/m1/shock-bx-amendment.json')
    for label,names,filenames,reference,fields in (
      ('shock',shock_names,('final.csv','geometry.json'),'brio_8192.csv.gz',{'rho','p','vx','by'}),
      ('vortex',vortex_names,('final.csv','geometry.json','projected_bins.json'),'vortex_512.csv.gz',{'rho','p','bx','by'})):
        r = fresh.json(label+'/independent_reference.json')
        require(r['analysis_source_sha256'] == fresh.digest('tools/reduce_'+label+'.py')
            == fresh.digest(label+'/reduce_reference.py'),'Primary analysis source')
        require(r['reference_sha256'] == sha(safe_path(frozen,'tests/reference/external_mhd/'+reference).read_bytes())
            and r['packet_sha256'] == sha(safe_path(frozen,'benchmarks/m0/packet.json').read_bytes()),'Primary reference source')
        require(r['run_map_sha256'] == fresh.digest('physics_inputs/runs.json')
            and gzip.decompress(fresh.raw(label+'/runs_checkpoint.json.gz')) == fresh.raw('physics_inputs/runs.json')
            and fresh.raw(label+'/provenance_checkpoint.json') == fresh.raw('physics_inputs/provenance.json'),
            'Primary adapter/checkpoint provenance')
        check_primary_input_coverage(r,names,filenames,runs)
        for name,row in r['measured'].items():
            c = runs[name]['config']
            require(row['resolution'] == c['n'] and row['frame'] == name.rsplit('_',1)[1]
                and set(row['reference_errors']) == fields,'Primary measured identities/fields')
            require(all(set(v) == {'L1','L2'} and all(math.isfinite(x) and x >= 0 for x in v.values())
                        for v in row['reference_errors'].values()),'Primary norm shape')
            if label == 'shock':
                require(row['family'] == ('columns' if c['jitter_mode'] == 'columns' else 'regular')
                    and row['production_discrepancy'] < 2e-11
                    and row['rectangle_volume_relative_error'] < 2e-11,'Shock norm/geometry receipts')
                check_primary_shock_bx(row,runs[name],amendment)
            else:
                require(all(row[k] < 2e-11 for k in ('maximum_rectangle_area_relative_error',
                  'maximum_bin_coverage_relative_error','maximum_production_bin_difference',
                  'maximum_production_norm_difference')),'Vortex bin/norm receipts')
        gates = r['reference_gates'] if label == 'shock' else r['primary_reference_ladders']
        expected = {(f,frame) for f in ('regular','columns') for frame in ('base','boost')} if label == 'shock' else {('base',),('boost',)}
        keys = [(x['family'],x['frame']) if label == 'shock' else (x['frame'],) for x in gates]
        require(len(keys) == len(expected) and set(keys) == expected,'Exact reference family/frame gates')
        if label == 'shock':
            require(r['all_reference_gates_passed'] is True and r['decimal_precision'] == 50,'Shock completed reference')
        else:
            require(not r['missing_primary_cases'],'Missing vortex primary')
        limits = packet['cases']['brio-wu' if label == 'shock' else 'orszag-tang']['gate'][
                   'finest_scaled_L1_max' if label == 'shock' else 'finest_scaled_bin_L1_max']
        require(set(limits) == fields,'Primary packet fields')
        for gate in gates:
            require(set(gate['checks']) == fields and all(v is True for v in gate['checks'].values()),'Reference checks')
            if label == 'vortex':
                require(gate['complete'] is True and gate['status'] == 'pass','Complete vortex ladder')
            ladder = sorted([v for v in r['measured'].values() if v['frame'] == gate['frame']
                 and (label == 'vortex' or v['family'] == gate['family'])],key=lambda v:v['resolution'])
            require([v['resolution'] for v in ladder] == ([256,512,1024] if label == 'shock' else [64,128,256]),'Reference ladder resolutions')
            for f,limit in limits.items():
                require(ladder[-1]['reference_errors'][f]['L1'] <= limit
                    and ladder[-1]['reference_errors'][f]['L1'] < ladder[0]['reference_errors'][f]['L1'],'Reference gate consistency')
    check_bin_payload(fresh.json('vortex/independent_bins.json.gz'),vortex_names)


def check_adapters(fresh,runs,plans,provenance,frozen):
    capture = fresh.json('metadata_capture.json')
    repo,out = check_command_links(fresh.json('commands.json'),capture)
    wp = fresh.json('wave_inputs/provenance.json')
    require(wp['original_run_map_sha256'] == provenance['waves']['run_map_sha256']
        and wp['plan_sha256'] == provenance['waves']['plan_sha256'] and wp['snapshot_sha256'] == SNAPSHOT,
        'Wave adapter provenance')
    refs = read(frozen,'tests/reference/external_mhd/provenance.json')['result_sha256']
    packet_digest = sha(safe_path(frozen,'benchmarks/m0/packet.json').read_bytes())
    require(wp['reference_sha256'] == refs and wp['source_sha256'] ==
            {'benchmarks/m0/packet.json':packet_digest},'Wave source/reference identities')
    rows = fresh.json('wave_inputs/input_receipts.json')
    require(len(rows) == 112 and {r['name'] for r in rows} == set(runs['waves']),'Exact wave acquisition receipts')
    for r in rows:
        n = r['name'];pr = provenance['waves']['receipts'][n]
        require(r['artifact'] == 'final.csv' and r['sha256'] == r['target_sha256'] == runs['waves'][n]['sha256']['final.csv']
            and r['workflow'] == pr['workflow'] and r['remote_path'] == 'outputs/raw/'+n+'/final.csv'
            and r['artifact_manifest_sha256'] == pr['artifact_manifest_sha256']
            and r['materialized'] is True and r['copied_path'] == n+'/final.csv' and r['downloaded'] is False,
            'Wave materialization/source receipt')
        identity = fresh.json('summary.json')['raw_input_identities']['waves/'+n+'/final.csv']
        require(r['bytes'] == identity['bytes'] and r['local_source'] == identity['local_source'],
                'Wave actual input byte/path identity')
        actual = str(repo/capture['private_views']['waves']['original_root']/'raw'/n/'final.csv')
        require(r['local_source'] == r['source_realpath'] == actual
            and r['adapter_local_source'] == str(PurePosixPath(capture['private_views']['waves']['path'])/'raw'/n/'final.csv'),
            'Wave adapter actual versus private-view path')
    require(fresh.json('physics_inputs/runs.json') == fresh.json('physics_inputs/observed_run_map.json')
        == runs['physics'],'Physics maps must be semantically equal, not byte-identical')
    require(fresh.json('physics_inputs/plan.json') == plans['physics']
        and fresh.json('physics_inputs/checkpoint.json') == fresh.json('observations/physics/checkpoint.json'),
        'Physics adapter plan/checkpoint')
    p = fresh.json('physics_inputs/provenance.json')
    require(p['snapshot_sha256'] == SNAPSHOT and p['binary_sha256'] == BINARY
        and p['observed_run_map_sha256'] == fresh.digest('physics_inputs/observed_run_map.json')
        and p['observer_checkpoint_sha256'] == fresh.digest('physics_inputs/checkpoint.json')
        and p['plan_sha256'] == fresh.digest('physics_inputs/plan.json')
        and p['collector_sha256'] == fresh.digest('physics_inputs/collector.py')
        == fresh.digest('tools/collect_fresh_physics_reference_inputs.py'),'Physics collector identities')
    check_runtime(p['runtime'])
    require(p['source_sha256'] == {'benchmarks/m0/packet.json':packet_digest}
        and p['reference_sha256'] == {n:refs[n] for n in ('brio_8192.csv.gz','vortex_512.csv.gz')},
        'Physics reference/source context')
    receipt = fresh.json('physics_inputs/input_receipts.json')
    require(receipt['completed'] == receipt['expected'] == 30 and receipt['full_m1_accepted'] is False
        and receipt['transport_journal'] == 'transport_commands.json'
        and receipt['capture_manifest_sha256'] == fresh.digest('physics_inputs/metadata_capture.json'),
        'Complete physics acquisition contract')
    rows = receipt['observations']
    require(len(rows) == 30 and {r['name'] for r in rows} == set(runs['physics']),'Exact physics acquisition cases')
    transport = fresh.json('physics_inputs/transport_commands.json')
    logs = check_journal(transport,lambda n:fresh.raw('physics_inputs/'+n))
    require({n[len('physics_inputs/'):] for n in fresh.rows if n.startswith('physics_inputs/transport_logs/')}
        == logs,'Unreferenced/missing transport log')
    attempts = {r['attempt_id']:r for r in transport}
    requested = set()
    entries = plan_entries(plans['physics'])
    for r in transport:
        require(r['outcome'] == 'success' and r['returncode'] == 0,'Failed transport cannot close full collection')
        require(r['workflow'] in {e['workflow'] for e in entries.values()} and r['requested_paths'],
                'Transport registered workflow/path inventory')
        argv = r['argv']
        n = next(n for n,e in entries.items() if e['workflow'] == r['workflow'])
        command = shlex.split(fresh.json('commands.json')[9]['argv'][5])
        require(argv == [*command,'download','-w',r['workflow'],'-o',
                str(out/'physics_inputs'/'download'/entries[n]['directory']),*r['requested_paths']]
            and r['cwd'] == str(repo) and r['label'] == 'download-'+n and r['timeout_seconds'] == 1800,
            'Transport exact client/workflow/destination/requested argv paths')
        for stream in ('stdout','stderr'):
            require(r[stream]['path'] == f"transport_logs/{r['attempt_id']:03}-{r['label']}.{stream}",
                    'Transport log-label association')
        for remote in r['requested_paths']:
            require(safe_name(remote).parts[0:2] == ('outputs','raw'),'Transport artifact containment')
            require((r['workflow'],remote) not in requested,'Repeated transport request')
            requested.add((r['workflow'],remote))
    expected_inputs = {k for k in raw_input_names(runs) if k.startswith('physics/')}
    acquired,used_requests = set(),set()
    for r in rows:
        n = r['name'];pr = provenance['physics']['receipts'][n]
        require(r['workflow'] == pr['workflow'] and r['execution_sha256'] == pr['execution_sha256']
            and r['manifest_sha256'] == pr['artifact_manifest_sha256'],'Acquisition execution linkage')
        fs = {a['artifact']:a for a in r['artifacts']}
        expected = {k.rsplit('/',1)[1] for k in expected_inputs if k.split('/')[1] == n}
        require(len(fs) == len(r['artifacts']) and set(fs) == expected
            and r['verified'] == {f:runs['physics'][n]['sha256'][f] for f in expected},'Exact physics files')
        for filename,a in fs.items():
            key = 'physics/'+n+'/'+filename;acquired.add(key)
            remote = 'outputs/raw/'+n+'/'+filename
            require(a['remote_path'] == remote and a['sha256'] == runs['physics'][n]['sha256'][filename]
                and a['bytes'] == fresh.json('summary.json')['raw_input_identities'][key]['bytes']
                and a['copied_path'] == n+'/'+filename,'Actual acquisition artifact/path/hash/size')
            if a['acquisition'] == 'fresh_workflow_download':
                attempt = attempts[a['transport_attempt_id']]
                require(attempt['workflow'] == r['workflow'] and remote in attempt['requested_paths'],
                        'Downloaded artifact lacks exact transport receipt')
                actual = out/'physics_inputs'/'download'/entries[n]['directory']/remote
                used_requests.add((r['workflow'],remote))
            else:
                require(a['acquisition'] == 'already_downloaded_fresh' and a['transport_attempt_id'] is None,
                        'Unrecognized acquisition/historical substitution')
                actual = repo/capture['private_views']['physics']['original_root']/'download'/entries[n]['directory']/remote
            require(a['local_source'] == str(actual),'Wrong fresh acquisition local path')
            require(fresh.json('summary.json')['raw_input_identities'][key]['local_source'] ==
                    str(out/'physics_inputs'/n/filename),'Wrong consumed physics source path')
    require(acquired == expected_inputs and used_requests == requested,'Exact54 physics acquisition/transport links')
    nested = fresh.json('physics_inputs/metadata_capture.json')
    require(nested['schema'] == 'm1-metadata-capture-v1' and nested['final_unchanged_check']['passed'] is True
        and nested['final_unchanged_check']['files'] == len(nested['files']),'Nested physics capture closure')
    check_runtime(nested['runtime'])
    require(nested['attempts'] and nested['attempts'][-1]['outcome'] == 'stable'
        and timestamp(nested['final_unchanged_check']['checked_utc']) >= timestamp(nested['captured_utc']),
        'Nested capture stability/timestamps')
    nested_copies = set()
    outer = fresh.json('metadata_capture.json')['files']
    original_root = capture['private_views']['physics']['original_root']+'/'
    reference_sources = {'benchmarks/m0/packet.json',*['tests/reference/external_mhd/'+n for n in
                         ('provenance.json','brio_8192.csv.gz','vortex_512.csv.gz')]}
    require(set(nested['files']) == {n for n in outer if n.startswith(original_root)}|reference_sources,
            'Exact nested metadata original sources')
    for original,r in nested['files'].items():
        if original in reference_sources:
            expected = 'metadata/reference_inputs/'+original
        else:
            tail = original.removeprefix(original_root)
            expected = ('observed_run_map.json' if tail == 'runs.json' else tail
                        if tail in {'plan.json','checkpoint.json'} or tail.startswith('download/') else 'metadata/'+tail)
        require(r['copied_path'] == expected,'Nested original-to-copy path')
        path = 'physics_inputs/'+r['copied_path'];nested_copies.add(path)
        data = fresh.raw(path)
        require(sha(data) == r['sha256'] and len(data) == r['bytes'],'Physics exact captured bytes')
        require(original in outer and outer[original]['sha256'] == r['sha256']
            and outer[original]['bytes'] == r['bytes'],'Physics capture disconnected from complete capture')
    require(len(nested_copies) == len(nested['files']),'Duplicate nested capture destination')
    allowed = nested_copies|{'physics_inputs/'+n for n in
        ('collector.py','metadata_capture.json','transport_commands.json','provenance.json','runs.json',
         'input_receipts.json','collection_status.json')}
    allowed |= {'physics_inputs/'+n for n in logs}
    require({n for n in fresh.rows if n.startswith('physics_inputs/')} == allowed,
            'Exact nested physics metadata/log inventory')


def check_preflight(root,snapshot):
    previous = root/'source_review_packet'
    pre = previous/'preflight'
    p,e,artifacts = (read(pre,n) for n in ('preflight.json','execution.json','artifacts.sha256.json'))
    require(p['snapshot_sha256'] == e['snapshot_sha256'] == SNAPSHOT and p['binary_sha256'] == BINARY
        and e['status'] == 'completed' and e['study'] == 'm1-fanout-preflight','Preflight binary/source identity')
    runtime = read(pre,'runtime.json')
    require(p['image'] == runtime['image'] == IMAGE and p['machine'] == runtime['machine'],
            'Preflight image/machine identity')
    expected = [['cargo','fmt','--check'],
      ['cargo','clippy','--all-targets','--all-features','--locked','--','-D','warnings'],
      ['cargo','test','--workspace','--locked'],['cargo','build','--release','--workspace','--locked'],
      ['python','-m','unittest','discover','-s','scripts','-p','test_*.py'],
      ['python','scripts/check_m0_spec.py'],['python','scripts/check_reference_packet.py'],
      ['cargo','test','--release','--workspace','--all-targets','--locked']]
    require(p['commands'] == e['commands'],'Preflight command equality')
    def commands(execution,directory,compressed,wants):
        require(execution['status'] == 'completed' and len(execution['commands']) == len(wants),'Eight command receipts')
        require(timestamp(execution['ended_utc']) >= timestamp(execution['started_utc']),'Preflight execution timestamps')
        for i,(r,want) in enumerate(zip(execution['commands'],wants)):
            command = list(r['command'])
            if want[0] == 'python':
                require(PurePosixPath(command[0]).name in {'python','python3'},'Preflight interpreter')
                command[0] = 'python'
            require(command == want and r['returncode'] == 0 and math.isfinite(r['seconds']) and r['seconds'] >= 0
                and r['log'] == f'outputs/logs/{i:02}.log','Exact successful command/log receipt')
            data = decoded_file(directory,f'logs/{i:02}.log'+('.gz' if compressed else ''))
            require(sha(data) == r['log_sha256'],'Preflight retained log hash')
    commands(e,pre,False,expected)
    require(p['runtime_sha256'] == e['runtime_sha256'] == sha((pre/'runtime.json').read_bytes()),'Preflight runtime')
    for n,d in artifacts.items():
        require(safe_name(n).parts[0] == 'outputs','Preflight artifact path')
        require((BINARY if n == 'outputs/vector-potential' else sha(safe_path(pre,n.removeprefix('outputs/')).read_bytes())) == d,
                'Preflight artifact hash')
    def passes(label):
        return sum(map(int,re.findall(r'test result: ok\. (\d+) passed;',(pre/f'logs/{label}.log').read_text())))
    require(passes('02') == 236 and passes('07') == 245 and 'Ran 163 tests' in (pre/'logs/04.log').read_text(),
            'Actual retained preflight test receipts')
    bounded = previous/'fresh/bounded'
    be,ba = read(bounded,'execution.json.gz'),read(bounded,'artifacts.sha256.json.gz')
    bc = expected[:7]+[['python','scripts/run_m1_bounded.py','--riemann','hlld-pressure',
      '--potential-limiter','smooth-extrema','--case-timeout','120','--iterative-projection',
      '--output-dir','results/reana_m1-bounded']]
    commands(be,bounded,True,bc)
    require(be['snapshot_sha256'] == SNAPSHOT and be['runtime_sha256'] ==
            sha(decoded_file(bounded,'runtime.json.gz')),'Bounded source/runtime')
    for n,d in ba.items():
        require(safe_name(n).parts[0] == 'outputs','Bounded artifact path')
        if n == 'outputs/m1-iterative-bounded-raw.tar.gz':
            continue  # Explicit historical raw omission, not a NEW boundary exemption.
        require(sha(decoded_file(bounded,n.removeprefix('outputs/')+'.gz')) == d,'Bounded retained artifact hash')
    gate = read(bounded,'m1-iterative-bounded/gate.json.gz')
    stages = ['shock_short','shock_symmetry','waves_short','physics_quick']
    require(gate['stages_expected'] == [r['name'] for r in gate['stages']] == stages
        and gate['bounded_blockers_closed'] is True and gate['source_and_binary_unchanged'] is True
        and gate['iterative_projection'] is True and gate['full_m1_accepted'] is False,'Four bounded stage receipts')
    gp = gate['provenance']
    require(gp['binary_sha256'] == BOUNDED_BINARY != BINARY and gp['profile'] == CONFIGURATION['profile']
        and gp['projection_screening'] == 1. and gp['accelerated_projection'] is False
        and gate['potential_limiter'] == gp['potential_limiter'] == 'smooth-extrema'
        and gate['riemann_solver'] == gp['riemann_solver'] == 'hlld-pressure','Separate historical bounded binary/config')
    for row in gate['stages']:
        require(row['status'] == 'pass' and row['checks'] and all(v is True for v in row['checks'].values())
            and row['returncode'] == (1 if row['name'] == 'shock_symmetry' else 0)
            and re.fullmatch('[0-9a-f]{64}',row['summary_sha256'])
            and re.fullmatch('[0-9a-f]{64}',row['runs_sha256']),'Bounded stage checks/retained receipt')
    require(all(snapshot['source_sha256'][n] == d for n,d in gp['source_sha256'].items()),'Bounded frozen source')
    return sha((pre/'preflight.json').read_bytes())


def check_export_inventory(root,index,frozen):
    """Every export role has an exact path and provenance policy, not a suffix whitelist."""
    expected = {'fresh/original_collection_sha256.json':dict(kind='full_original_collection_manifest',
        manifest_sha256=index['input_collection_manifest_sha256'],raw_inputs_retained_outside_this_packet=True),
        'frozen_source_catalog.json':dict(kind='verified_frozen_git_catalog'),
        'host_tools/pack_final_review_evidence.py':dict(kind='packager_source'),
        'verify_final_review_evidence.py':dict(kind='portable_read_only_verifier')}
    for directory,repo_path in (('source_review_packet','tests/reference/m1_acceptance'),
                                ('historical_campaigns','tests/reference/m1_iterative_step_campaigns')):
        for n in files(root/directory,historical=True):
            expected[directory+'/'+n] = dict(kind='retained_prior_packet',repository_path=repo_path+'/'+n)
    for n in frozen['sha256']:
        expected['frozen_source/'+n] = dict(kind='frozen_git_blob',revision=REVISION,path=n)
    for n in ('M1_FINAL_AI_REVIEW.md','M1_CANDIDATE_AUDIT.md','M1_FINAL_ACCEPTANCE_PLAN.md',
              'M1_FULL_VALIDATION_PLAN.md','M1_FINAL_ARCHIVE_PLAN.md'):
        expected['documents/'+n] = dict(kind='current_review_context',repository_path='docs/'+n)
    nonfresh = {r['path']:r['origin'] for r in index['artifacts']
                if r['origin']['kind'] != 'complete_fresh_collection'}
    require(nonfresh == expected,'Exact historical/source/context/host export inventory')


def check_verdict(verdict):
    require(verdict['snapshot_sha256'] == SNAPSHOT and verdict['binary_sha256'] == BINARY
        and verdict['configuration'] == CONFIGURATION and set(verdict['phases']) == PHASES
        and verdict['all_registered_phase_checks_passed'] is True and verdict['full_m1_accepted'] is False,
        'Exact registered phases/candidate verdict')
    for name,r in verdict['phases'].items():
        require(set(r) == {'checks','passed'} and r['passed'] is True
            and set(r['checks']) == PHASE_CHECKS[name] and all(v is True for v in r['checks'].values()),
            'Exact registered checks/no failed or error phase: '+name)


def verify_evidence(root):
    root = Path(root).resolve()
    manifest = verify_closed(root,'sha256.json')
    index = read(root,'artifact_index.json')
    require(index['schema'] == 'openmhd.m1-final-review-evidence.v2'
        and index['source_revision'] == REVISION and index['snapshot_sha256'] == SNAPSHOT
        and index['binary_sha256'] == BINARY and index['full_m1_accepted'] is False
        and index['final_ai_output_review_passed'] is False,'Archive schema/identity/review boundary')
    rows = index['artifacts']
    require(len(rows) == len({r['path'] for r in rows})
        and {r['path'] for r in rows} == set(manifest)-{'artifact_index.json'},'Exact indexed inventory')
    for r in rows:
        decode_artifact(root,r)
        if r['path'].startswith('fresh/'):
            require(r['origin']['kind'] == ('full_original_collection_manifest' if
                r['path'] == 'fresh/original_collection_sha256.json' else 'complete_fresh_collection'),
                'Fresh artifact has disconnected origin type')
    for name,(digest,count) in HISTORICAL.items():
        require(sha(safe_path(root,name).read_bytes()) == digest,'Pinned historical manifest')
        parent,filename = name.rsplit('/',1)
        verify_closed(root/parent,filename,{'review':'review_sha256.json'} if parent == 'source_review_packet' else None,
                      historical=True,expected_count=count)
    snapshot_bytes = decoded_file(root,'source_review_packet/snapshot.json.gz')
    require(sha(snapshot_bytes) == SNAPSHOT,'Snapshot hash')
    snapshot = loads(snapshot_bytes)
    frozen = read(root,'frozen_source_catalog.json')
    required = {n:d for n,d in snapshot['source_sha256'].items() if
        n.startswith(('apps/','crates/','scripts/','benchmarks/','reana/','tests/reference/external_mhd/'))
        or n in ('Cargo.toml','Cargo.lock','rust-toolchain.toml')}
    require(frozen['revision'] == REVISION and frozen['sha256'] == required
        and frozen['scientific_files'] == len([n for n in required if not n.startswith('tests/reference/')
             and n != 'rust-toolchain.toml']) == 226,'Frozen source catalog')
    for n,d in required.items():
        require(sha(safe_path(root,'frozen_source/'+n).read_bytes()) == d,'Historical Git blob')
    check_export_inventory(root,index,frozen)
    source_review = read(root,'source_review_packet/review_report_sha256.json')
    require(sha(safe_path(root,'documents/M1_FINAL_AI_REVIEW.md').read_bytes()) ==
            source_review['docs/M1_FINAL_AI_REVIEW.md'],'Source-review report identity')
    preflight_digest = check_preflight(root,snapshot)
    fresh = Fresh(root,index)
    s = fresh.json('summary.json')
    require(s['snapshot_sha256'] == SNAPSHOT and s['binary_sha256'] == BINARY
        and s['all_independent_checks_passed'] is True and s['full_m1_accepted'] is False
        and s['final_ai_output_review_passed'] is False,'Fresh summary identity/status')
    for k,v in dict(verified_matrix_cases=214,independently_reduced_boost_pairs=99,spatial_ladders=8,
          temporal_ladders=12,primary_shock_cases=12,primary_vortex_cases=6,actual_raw_inputs=238).items():
        require(s[k] == v,'Summary coverage: '+k)
    check_collection_lifecycle(fresh.json,fresh.raw,set(fresh.rows))
    selected,omitted = export_selection(fresh.manifest,s,fresh.json('metadata_capture.json'))
    require(set(fresh.rows) == selected and index['fresh_export']['selected_paths'] == sorted(selected)
        and index['fresh_export']['omitted_large_inputs'] == omitted,'Exact export/omission partition')
    require(index['historical_boundary'] == BOUNDARY,'Undeclared historical non-cache boundary')
    require(s['required_successful_command_labels'] == LABELS,'Required command contract')
    check_source_context(fresh,root,root/'frozen_source')
    preflight_hashes = {n:sha(safe_path(root,'source_review_packet/preflight/'+n).read_bytes())
        for n in ('preflight.json','execution.json','runtime.json','artifacts.sha256.json')}
    runs,plans,provenance,capture = check_phases(fresh,root/'historical_campaigns',snapshot,
                                               preflight_digest,preflight_hashes)
    check_raw_identities(fresh,runs,provenance,root/'historical_campaigns')
    check_verdict(fresh.json('registered_verdict.json'))
    check_registered_observations(fresh,runs)
    packet = read(root/'frozen_source','benchmarks/m0/packet.json')
    amendment = read(root/'frozen_source','benchmarks/m1/shock-bx-amendment.json')
    for run in runs['physics'].values():
        check_physics_diagnostics(run,packet,amendment)
    check_reports(fresh,runs,provenance,root/'frozen_source')
    check_adapters(fresh,runs,plans,provenance,root/'frozen_source')
    return dict(evidence_inventory_files=len(manifest),frozen_scientific_files=226,matrix_cases=214,
        independently_reduced_boost_pairs=99,raw_input_identities=238,evidence_integrity_passed=True,
        separate_final_review_required=True,full_m1_accepted=False)


def verify_outer(root):
    """Future sibling closure: consistency only, no acceptance decision inferred."""
    root = Path(root).resolve()
    verify_closed(root,'archive_sha256.json',{'evidence':'sha256.json','review':'review_sha256.json'})
    result = verify_evidence(root/'evidence')
    acceptance = read(root,'acceptance.json')
    require(acceptance['evidence_manifest_sha256'] == sha((root/'evidence/sha256.json').read_bytes())
        and acceptance['review_manifest_sha256'] == sha((root/'review/review_sha256.json').read_bytes()),
        'Outer record/nested manifest links')
    require(acceptance['source_revision'] == REVISION and acceptance['snapshot_sha256'] == SNAPSHOT
        and acceptance['binary_sha256'] == BINARY and acceptance['configuration'] == CONFIGURATION,
        'Outer acceptance-record identities')
    result.update(outer_closure_consistent=True,acceptance_record_present=True,
                  scope='Consistency only; this utility makes no acceptance decision')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outer',type=Path,help='Future sibling evidence/review/acceptance boundary')
    args = parser.parse_args()
    result = verify_outer(args.outer) if args.outer else verify_evidence(Path(__file__).resolve().parent)
    print(json.dumps(result,indent=1,allow_nan=False))


if __name__ == '__main__':
    main()
