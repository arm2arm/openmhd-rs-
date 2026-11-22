"""Metadata-only archive regressions, intended for independent REANA workflows.

Nothing here evolves a state, invokes a reducer, builds Rust or fabricates a
successful complete campaign. Historical objects are READ from the two closed
packets and copied before mutation. Tiny synthetic byte/journal/schema controls
are explicitly not physical-campaign evidence. Each test_* is independently
runnable with unittest and needs only tools/ plus the two historical packets.
"""
if not __debug__:
    raise RuntimeError("Metadata tests require an unoptimized interpreter")

import copy
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parents[1]
REPO = TOOLS.parents[1]
PREVIOUS = REPO/'tests/reference/m1_acceptance'
HISTORICAL = REPO/'tests/reference/m1_iterative_step_campaigns'


def verifier():
    spec = importlib.util.spec_from_file_location('portable_metadata_test_subject',
                                                 TOOLS/'verify_final_review_evidence.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value,indent=1,allow_nan=False)+'\n').encode()


def historical_json(root,name):
    data = (root/name).read_bytes()
    return json.loads(gzip.decompress(data) if name.endswith('.gz') else data)


def put(root,name,data):
    path = root/name
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(data)


def close(root,name='sha256.json',child=None):
    """Tiny metadata-only closure, deliberately not an M1 evidence packet."""
    rows = {}
    for path in root.rglob('*'):
        if not path.is_file() or path == root/name:
            continue
        relative = path.relative_to(root).as_posix()
        if child and relative.startswith(child[0]+'/') and relative != '/'.join(child):
            continue
        rows[relative] = digest(path.read_bytes())
    put(root,name,json_bytes(rows))


def fresh_control(root):
    """One nonphysical JSON observation and its connected export provenance."""
    raw = json_bytes(dict(fixture='metadata-only',full_m1_accepted=False))
    manifest = json_bytes({'observation.json':digest(raw)})
    manifest_digest = digest(manifest)
    stored = gzip.compress(raw,mtime=0)
    put(root,'fresh/observation.json.gz',stored)
    put(root,'fresh/original_collection_sha256.json',manifest)
    def row(path,data,original,origin,encoding):
        return dict(path=path,origin=origin,encoding=encoding,stored_bytes=len(data),
                    stored_sha256=digest(data),original_bytes=len(original),
                    original_sha256=digest(original))
    index = dict(input_collection_manifest_sha256=manifest_digest,artifacts=[
        row('fresh/observation.json.gz',stored,raw,
            dict(kind='complete_fresh_collection',path='observation.json',
                 manifest_sha256=manifest_digest),'gzip'),
        row('fresh/original_collection_sha256.json',manifest,manifest,
            dict(kind='full_original_collection_manifest',manifest_sha256=manifest_digest,
                 raw_inputs_retained_outside_this_packet=True),'identity')])
    return index,raw


def verdict_schema_control():
    """SYNTHETIC helper-only schema control, NEVER a fresh campaign verdict.

    No historical verdict is rewritten or relabelled. These literal check-name
    inventories follow frozen 2bdcea0 fanout_campaign_verdict.py:31,52-111,
    147-201, run_m1_campaign.py:59-90 and run_m1_bounded.py:102-104; the
    independent retained historical schema is compared in the verdict test.
    Identity tokens come from the closed source-review snapshot/preflight,
    not the verifier's own constants. True flags below are INVENTED inputs to
    check_verdict ONLY; they assert no observed phase, state or physical result.
    There are no reports, runs, receipts, artifact index or collection manifest;
    this object cannot supply a complete Fresh/verify_evidence packet. It is
    never serialized as registered_verdict.json or passed to those entrypoints.
    """
    plan_checks = ('same_snapshot','registered_cases','registered_options',
        'terminal_without_errors','every_planned_case_completed','same_binary',
        'candidate_and_limiter_metadata')
    registered = {
        'bounded_short':('workflow_completed','same_snapshot','gate_file_unchanged',
            'four_short_stages_passed','blockers_closed','configuration'),
        'bounded_medium':plan_checks+('all_runs_completed','positive_and_conservative',
            'boost_pairs_passed'),
        'mean':plan_checks+('all_completed','positive_and_conservative','boost_pairs',
            'execution_configuration','mean_refinement_measured'),
        'calibration_wave':('all_completed','positive_and_conservative','boost_pairs',
            'execution_configuration','amplitude_error'),
        'calibration_vortex':('complete','diagnostics','execution_configuration'),
        'physics':plan_checks+('physics_gates','complete_ladder'),
        'waves':plan_checks+('all_completed','positive_and_conservative','boost_pairs',
            'execution_configuration','spatial_gates','temporal_measured')}
    return dict(scope='SYNTHETIC metadata-only verdict helper schema; no physical observations',
        fixture_kind='nonphysical-verdict-schema-control',
        snapshot_sha256=digest(gzip.decompress((PREVIOUS/'snapshot.json.gz').read_bytes())),
        binary_sha256=historical_json(PREVIOUS,'preflight/preflight.json')['binary_sha256'],
        configuration=dict(profile='bulk-frame-heun-quadratic-v1',accelerated_projection=False,
            projection_screening=1.,riemann_solver='hlld-pressure',
            potential_limiter='smooth-extrema',trial_step_fraction=None),
        phases={name:dict(checks=dict.fromkeys(checks,True),passed=True)
                for name,checks in registered.items()},
        all_registered_phase_checks_passed=True,full_m1_accepted=False,
        final_ai_output_review_passed=False)


def receipt_control():
    """Actual closed fresh-medium receipt; never substituted for new evidence."""
    plan = historical_json(PREVIOUS,'fresh/medium_plan.json.gz')
    runs = historical_json(PREVIOUS,'fresh/medium_runs.json.gz')
    provenance = historical_json(PREVIOUS,'fresh/medium_provenance.json.gz')
    name = next(iter(provenance['receipts']))
    receipt = copy.deepcopy(provenance['receipts'][name])
    entry = copy.deepcopy(next(e for e in plan['cases']
                               if e['specification']['config']['name'] == name))
    hashes = {'execution.json':receipt['execution_sha256'],
              'record.json':receipt['execution']['record_sha256'],
              'artifacts.sha256.json':receipt['artifact_manifest_sha256']}
    return dict(receipt=receipt,entry=entry,spec=copy.deepcopy(entry['specification']),
                execution=copy.deepcopy(receipt['execution']),run=copy.deepcopy(runs[name]),
                record=copy.deepcopy(runs[name]),artifacts=copy.deepcopy(receipt['artifacts']),
                hashes=hashes,preflight_digest=receipt['execution']['preflight_sha256'])


def journal_control():
    """Synthetic process metadata, not a command execution or campaign result."""
    logs = {'logs/001-metadata.stdout':b'nonphysical metadata control\n',
            'logs/001-metadata.stderr':b''}
    runtime = dict(executable='/usr/bin/python3',version='metadata-control',
                   implementation='CPython',optimization=0,assertions_enabled=True,
                   pythonoptimize='',platform='metadata-control')
    row = dict(attempt_id=1,label='metadata',argv=['/usr/bin/python3','metadata.py'],
               cwd='/metadata-only',started_utc='2026-11-22T00:00:00+00:00',
               finished_utc='2026-11-22T00:00:01+00:00',duration_seconds=1.,
               timeout_seconds=10.,outcome='success',returncode=0,error_type=None,
               interpreter=runtime,child_environment=dict(PYTHONOPTIMIZE='0',PYTHONDONTWRITEBYTECODE='1'),
               logs_closed=True,external_evidence_required=False,
               ownership=dict(schema='m1-command-ownership-v1',registry='/metadata-only/command_ownership',
                   node_id='0'*31+'1',parent_id=None,guardian_pid=101,state='settled',writers_stopped=True))
    for stream in ('stdout','stderr'):
        path = 'logs/001-metadata.'+stream
        row[stream] = dict(path=path,sha256=digest(logs[path]),bytes=len(logs[path]))
    return [row],logs


def physics_gate_controls():
    """Small SOURCE-SCHEMA controls, not a witnessed packet or numerical result.

    Literal existing bounds from frozen benchmarks/m0/packet.json and
    benchmarks/m1/shock-bx-amendment.json. Real complete-path verification reads
    those hash-verified frozen files; these unit controls add no external fixture
    dependency to the two closed packets supplied by the metadata runner.
    """
    packet = dict(solver=dict(budget_tolerance=1e-10),cases={
        'brio-wu':dict(gate=dict(seam_max_signal_travel=.45)),
        'orszag-tang':dict(gate=dict(mean_B_drift_over_Bscale_max=.001,
                                   limited_face_dimensionless_divB_RMS_max=.1))})
    amendment = dict(bx_max_error=1e-8,bx_gate_meshes=['regular','columns'])
    return packet,amendment


def spatial_control():
    """Copied CLOSED real scalar metadata; never promoted to fresh physical data."""
    runs = historical_json(HISTORICAL,'iter/plans/iter-waves_runs.json.gz')
    checkpoint = historical_json(HISTORICAL,'iter/plans/iter-waves_checkpoint.json.gz')
    report = historical_json(PREVIOUS,'campaign_a_independent_waves.json.gz')
    row = copy.deepcopy(report['spatial'][0])
    production = copy.deepcopy(next(r for r in checkpoint['summaries']['wave']['alfven_convergence']
        if (r['jitter'],r['parallel'],r['motion']) == (row['jitter'],row['parallel'],row['motion'])))
    return row,production,runs,report['cases']


def ownership_control(v):
    """Synthetic PROCESS GRAPH only; no command is launched and no physical
    state, report, workflow, full archive or campaign success is constructed.
    Thirteen labels exercise the real graph schema, not physical evidence.
    """
    source = (TOOLS/'collect_fresh_physics_reference_inputs.py').read_bytes()
    repo,out = v.PurePosixPath('/metadata-repo'),v.PurePosixPath('/metadata-collection')
    rows,transport,raw = [],[],{'command_ownership/registry.lock':b''}
    prototype = journal_control()[0][0]
    for index,label in enumerate([*v.LABELS,'download-metadata-only'],1):
        nested = index > len(v.LABELS)
        node_id = format(index,'032x')
        parent = format(10,'032x') if nested else None
        row = copy.deepcopy(prototype)
        row.update(attempt_id=1 if nested else index,label=label,
                   argv=['/usr/bin/python3','metadata-only.py',label])
        if nested:
            row.update(started_utc='2026-11-22T00:00:00.1+00:00',
                       finished_utc='2026-11-22T00:00:00.9+00:00')
        row['ownership'] = dict(schema='m1-command-ownership-v1',
            registry=str(out/'command_ownership'),node_id=node_id,parent_id=parent,
            guardian_pid=100+2*index,state='settled',writers_stopped=True)
        helper = str((out/'tools' if nested else repo/'tools/m1_evidence')/
                     'collect_fresh_physics_reference_inputs.py')
        node = dict(schema='m1-command-ownership-v1',node_id=node_id,parent_id=parent,
            argv=row['argv'],cwd=row['cwd'],guardian_pid=100+2*index,primary_pid=101+2*index,
            primary_returncode=0,state='settled',cancelled=False,writers_stopped=True,
            guardian_source=dict(path=helper,sha256=digest(source)),
            guardian_argv=['/usr/bin/python3','-I','-S','-B','-c',v.guardian_bootstrap(source),
                helper,'--owned-command',str(out/'command_ownership'/(node_id+'.json'))])
        raw['command_ownership/'+node_id+'.json'] = json_bytes(node)
        (transport if nested else rows).append(row)
    return rows,transport,raw,repo,out,source


def export_schema_control(v):
    """Invented path/digest DICTIONARY solely for the selection schema. No bytes,
    reports or artificial passing physical packet are supplied to Fresh/verify.
    """
    names = {'summary.json','registered_verdict.json','commands.json','metadata_capture.json',
        'collection_status.json','vortex/independent_bins.json.gz',*v.REPORTS,
        *[p+'_provenance.json' for p in v.COUNTS],*['tools/'+n for n in v.TOOLS],
        *['wave_inputs/'+n for n in ('runs.json','manifest.json','provenance.json','input_receipts.json')],
        *['physics_inputs/'+n for n in ('runs.json','observed_run_map.json','plan.json','checkpoint.json',
            'provenance.json','input_receipts.json','collector.py','metadata_capture.json',
            'transport_commands.json','collection_status.json')],
        *[p+'/'+n for p in ('shock','vortex') for n in
            ('runs_checkpoint.json.gz','provenance_checkpoint.json','reduce_reference.py')],
        'command_ownership/registry.lock','command_ownership/'+format(1,'032x')+'.json'}
    return {n:'0'*64 for n in names},dict(raw_input_identities={}),dict(files={})


class ArchiveMetadataTests(unittest.TestCase):
    def setUp(self):
        self.v = verifier()

    def test_connected_manifest_bytes_control(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index,raw = fresh_control(root)
            self.assertEqual(self.v.Fresh(root,index).raw('observation.json'),raw)

    def test_disconnected_original_manifest_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index,_ = fresh_control(root)
            put(root,'fresh/original_collection_sha256.json',json_bytes({'other':'0'*64}))
            with self.assertRaises(self.v.EvidenceError):
                self.v.Fresh(root,index)

    def test_disconnected_origin_path_or_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original,_ = fresh_control(root)
            for field,value in (('path','other.json'),('manifest_sha256','0'*64)):
                index = copy.deepcopy(original)
                index['artifacts'][0]['origin'][field] = value
                with self.subTest(field=field),self.assertRaises(self.v.EvidenceError):
                    self.v.Fresh(root,index)

    def test_original_decoded_digest_and_manifest_artifact_origin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original,_ = fresh_control(root)
            index = copy.deepcopy(original)
            index['artifacts'][0]['original_sha256'] = '0'*64
            with self.assertRaises(self.v.EvidenceError):
                self.v.Fresh(root,index)
            index = copy.deepcopy(original)
            index['artifacts'][1]['origin']['manifest_sha256'] = '0'*64
            with self.assertRaises(self.v.EvidenceError):
                self.v.Fresh(root,index)

    def test_stored_and_decoded_length_hash_mutations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index,raw = fresh_control(root)
            original = index['artifacts'][0]
            self.assertEqual(self.v.decode_artifact(root,original),raw)
            for field,value in (('stored_bytes',1),('stored_sha256','0'*64),
                                ('original_bytes',1),('original_sha256','0'*64)):
                row = copy.deepcopy(original)
                row[field] = value
                with self.subTest(field=field),self.assertRaises(self.v.EvidenceError):
                    self.v.decode_artifact(root,row)

    def test_unsafe_and_symlink_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('../escape','/absolute','a/../b','a\\b','a//b','.'):
                with self.subTest(name=name),self.assertRaises(self.v.EvidenceError):
                    self.v.safe_path(root,name)
            put(root,'real',b'nonphysical bytes')
            (root/'link').symlink_to(root/'real')
            with self.assertRaises(self.v.EvidenceError):
                self.v.safe_path(root,'link')
            with self.assertRaises(self.v.EvidenceError):
                self.v.files(root)

    def test_nested_missing_and_extra_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            put(root,'review/report.txt',b'nonphysical review control')
            close(root/'review','review_sha256.json')
            close(root,'archive_sha256.json',('review','review_sha256.json'))
            self.v.verify_closed(root,'archive_sha256.json',{'review':'review_sha256.json'})
            (root/'review/report.txt').unlink()
            with self.assertRaises(self.v.EvidenceError):
                self.v.verify_closed(root,'archive_sha256.json',{'review':'review_sha256.json'})
            put(root,'review/report.txt',b'nonphysical review control')
            put(root,'review/unlisted.txt',b'extra')
            with self.assertRaises(self.v.EvidenceError):
                self.v.verify_closed(root,'archive_sha256.json',{'review':'review_sha256.json'})

    def test_new_cache_not_exempt_historical_boundary_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            put(root,'payload',b'metadata')
            close(root)
            put(root,'__pycache__/unlisted.pyc',b'metadata-only cache bytes')
            with self.assertRaises(self.v.EvidenceError):
                self.v.verify_closed(root,'sha256.json')
            self.v.verify_closed(root,'sha256.json',historical=True)

    def test_exact_copied_historical_closures(self):
        # Read-only validation of copied metadata, not a relocated historical script.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for source,label in ((PREVIOUS,'source_review_packet'),(HISTORICAL,'historical_campaigns')):
                shutil.copytree(source,root/label,ignore=shutil.ignore_patterns('__pycache__'))
            for name,(expected,count) in self.v.HISTORICAL.items():
                self.assertEqual(digest((root/name).read_bytes()),expected)
                parent,filename = name.rsplit('/',1)
                self.v.verify_closed(root/parent,filename,
                    {'review':'review_sha256.json'} if parent == 'source_review_packet' else None,
                    historical=True,expected_count=count)
            (root/'source_review_packet/review/rerun_mean.json').unlink()
            with self.assertRaises(self.v.EvidenceError):
                self.v.verify_closed(root/'source_review_packet','archive_sha256.json',
                                     {'review':'review_sha256.json'},historical=True,expected_count=69)

    def test_semantic_historical_plan_order(self):
        for phase in ('waves','physics'):
            old = historical_json(HISTORICAL,'iter/plans/iter-'+phase+'_plan.json.gz')
            new = copy.deepcopy(old)
            new['cases'].reverse()
            specs = [row['specification'] for row in new['cases']]
            with self.subTest(phase=phase):
                self.assertEqual(len(self.v.semantic_plan_match(new,specs,old)),self.v.COUNTS[phase])

    def test_a_identity_flags_derived_from_closed_run_maps(self):
        runs = historical_json(HISTORICAL,'iter/plans/iter-physics_runs.json.gz')
        old = next(iter(runs.values()))
        row = dict(sha256=old['sha256']['final.csv'],byte_identical_to_a=True)
        self.assertTrue(self.v.check_a_identity(row,old,'final.csv'))
        row['byte_identical_to_a'] = False
        with self.assertRaises(self.v.EvidenceError):
            self.v.check_a_identity(row,old,'final.csv')
        row = dict(sha256='0'*64,byte_identical_to_a=False)
        self.assertFalse(self.v.check_a_identity(row,old,'final.csv'))
        row['byte_identical_to_a'] = True
        with self.assertRaises(self.v.EvidenceError):
            self.v.check_a_identity(row,old,'final.csv')

    def test_semantic_case_or_resource_mutation_rejected(self):
        old = historical_json(HISTORICAL,'iter/plans/iter-waves_plan.json.gz')
        for field,value in (('n',257),('memory','999Gi')):
            new = copy.deepcopy(old)
            section = 'config' if field == 'n' else 'resources'
            new['cases'][0]['specification'][section][field] = value
            specs = [r['specification'] for r in new['cases']]
            with self.subTest(field=field),self.assertRaises(self.v.EvidenceError):
                self.v.semantic_plan_match(new,specs,old)

    def test_exact_phase_names_and_receipt_coverage(self):
        old = historical_json(HISTORICAL,'iter/plans/iter-mean_plan.json.gz')
        runs = historical_json(HISTORICAL,'iter/plans/iter-mean_runs.json.gz')
        entries = self.v.plan_entries(old)
        specs = self.v.named_specifications([r['specification'] for r in old['cases']])
        # Membership-only controls are not claimed to be execution receipts.
        receipts = dict.fromkeys(runs,None)
        self.v.check_phase_coverage(entries,runs,specs,receipts,24)
        for target in ('runs','receipts','specs'):
            mappings = dict(entries=entries,runs=copy.deepcopy(runs),
                            registered=copy.deepcopy(specs),receipts=copy.deepcopy(receipts),count=24)
            key = 'registered' if target == 'specs' else target
            mappings[key].pop(next(iter(mappings[key])))
            with self.subTest(target=target),self.assertRaises(self.v.EvidenceError):
                self.v.check_phase_coverage(**mappings)

    def test_candidate_command_defaults_and_flags(self):
        for phase in ('mean','waves','physics'):
            plan = historical_json(HISTORICAL,'iter/plans/iter-'+phase+'_plan.json.gz')
            runs = historical_json(HISTORICAL,'iter/plans/iter-'+phase+'_runs.json.gz')
            for entry in plan['cases']:
                spec = entry['specification']
                self.v.check_case_command(runs[spec['config']['name']],spec)
        plan = historical_json(HISTORICAL,'iter/plans/iter-mean_plan.json.gz')
        runs = historical_json(HISTORICAL,'iter/plans/iter-mean_runs.json.gz')
        spec = plan['cases'][0]['specification']
        original = runs[spec['config']['name']]
        for tail in (['--accelerated-projection'],['--trial-step-fraction','0.95'],
                     ['--projection-screening','2']):
            run = copy.deepcopy(original)
            run['command'] += tail
            with self.subTest(tail=tail),self.assertRaises(self.v.EvidenceError):
                self.v.check_case_command(run,spec)

    def test_exact_registered_verdict_names_configuration_and_checks(self):
        control = verdict_schema_control()
        # A positive helper-only schema control must precede negative mutations.
        self.v.check_verdict(control)
        historical = historical_json(HISTORICAL,'iter/verdict.json')
        self.assertEqual(digest((HISTORICAL/'iter/verdict.json').read_bytes()),
            'bcb442c207029dc98cf14d6250ac7b3f333b08f6428bedd01daf9e7556465f97')
        self.assertEqual(historical['configuration'],control['configuration'])
        self.assertEqual(historical['phases'],control['phases'])
        self.assertEqual(historical['all_registered_phase_checks_passed'],
                         control['all_registered_phase_checks_passed'])
        self.assertIs(historical['full_m1_accepted'],False)
        # Historical results remain historical: both identities differ, and the
        # FRESH-only helper must reject the ORIGINAL bytes, even with true flags.
        for field in ('snapshot_sha256','binary_sha256'):
            self.assertNotEqual(historical[field],control[field])
        with self.assertRaisesRegex(self.v.EvidenceError,
                '^Exact registered phases/candidate verdict$'):
            self.v.check_verdict(historical)
        mutations = []
        for field in ('snapshot_sha256','binary_sha256'):
            wrong = copy.deepcopy(control)
            wrong[field] = historical[field]
            mutations.append((field,wrong))
        for field,value in (('profile','paper-global-v2'),('accelerated_projection',True),
                ('projection_screening',2.),('riemann_solver','hlld'),
                ('potential_limiter','fixed-cap'),('trial_step_fraction',.95)):
            wrong = copy.deepcopy(control)
            wrong['configuration'][field] = value
            mutations.append(('configuration.'+field,wrong))
        for mutation in ('missing','extra','renamed'):
            wrong = copy.deepcopy(control)
            if mutation == 'missing':
                wrong['phases'].pop('waves')
            elif mutation == 'extra':
                wrong['phases']['unregistered'] = copy.deepcopy(wrong['phases']['waves'])
            else:
                wrong['phases']['unregistered'] = wrong['phases'].pop('waves')
            mutations.append(('phase.'+mutation,wrong))
        for field,value in (('all_registered_phase_checks_passed',False),
                            ('full_m1_accepted',True)):
            wrong = copy.deepcopy(control)
            wrong[field] = value
            mutations.append((field,wrong))
        for label,wrong in mutations:
            with self.subTest(mutation=label),self.assertRaisesRegex(self.v.EvidenceError,
                    '^Exact registered phases/candidate verdict$'):
                self.v.check_verdict(wrong)
        wrong = copy.deepcopy(control)
        wrong['phases']['waves']['checks']['spatial_gates'] = False
        with self.assertRaisesRegex(self.v.EvidenceError,
                '^Exact registered checks/no failed or error phase: waves$'):
            self.v.check_verdict(wrong)

    def test_every_phase_exact_check_inventory_and_error_rejection(self):
        control = verdict_schema_control()
        # Without this positive path, an unrelated identity rejection masks all
        # later mutations. Assert the PHASE rejection branch as well as its type.
        self.v.check_verdict(control)
        for phase in control['phases']:
            for mutation in ('missing','extra','renamed','substitute','error','failed','false_check'):
                wrong = copy.deepcopy(control)
                row = wrong['phases'][phase]
                name = next(iter(row['checks']))
                if mutation == 'missing':
                    row['checks'].pop(name)
                elif mutation == 'extra':
                    row['checks']['unregistered_check'] = True
                elif mutation == 'renamed':
                    row['checks']['renamed_'+name] = row['checks'].pop(name)
                elif mutation == 'substitute':
                    row['checks'] = {'metadata_control':True}
                elif mutation == 'error':
                    row['error'] = 'metadata mutation, not a physical error'
                elif mutation == 'failed':
                    row['passed'] = False
                else:
                    row['checks'][name] = False
                with self.subTest(phase=phase,mutation=mutation),self.assertRaisesRegex(
                        self.v.EvidenceError,
                        '^Exact registered checks/no failed or error phase: '+phase+'$'):
                    self.v.check_verdict(wrong)

    def test_real_mean_refinement_missing_row_coordinates_and_order_lengths(self):
        checkpoint = historical_json(HISTORICAL,'iter/plans/iter-mean_checkpoint.json.gz')
        runs = historical_json(HISTORICAL,'iter/plans/iter-mean_runs.json.gz')
        summary = checkpoint['summaries']['wave']
        self.v.check_mean_refinement(summary,runs)
        verdict = verdict_schema_control()
        self.v.check_verdict(verdict)  # schema-only true flags, not physical evidence
        for mutation in ('missing','duplicate','coordinate','negative','nonfinite','orders'):
            wrong = copy.deepcopy(summary)
            i = next(i for i,r in enumerate(wrong['mean_refinement'])
                     if r['profile'] == self.v.CONFIGURATION['profile'])
            row = wrong['mean_refinement'][i]
            if mutation == 'missing':
                wrong['mean_refinement'].pop(i)
            elif mutation == 'duplicate':
                wrong['mean_refinement'].append(copy.deepcopy(row))
            elif mutation == 'coordinate':
                row['values'][0][0] = 7
            elif mutation == 'negative':
                row['values'][0][1] = -1.
            elif mutation == 'nonfinite':
                row['values'][0][1] = float('inf')
            else:
                row['successive_B_L1_orders'].pop()
            # Invented schema-only true flags remain true; the real connected
            # observations must independently reject these metadata mutations.
            self.v.check_verdict(verdict)
            with self.subTest(mutation=mutation),self.assertRaises(self.v.EvidenceError):
                self.v.check_mean_refinement(wrong,runs)

    def test_mean_refinement_values_bound_to_captured_pairs(self):
        checkpoint = historical_json(HISTORICAL,'iter/plans/iter-mean_checkpoint.json.gz')
        runs = historical_json(HISTORICAL,'iter/plans/iter-mean_runs.json.gz')
        wrong = copy.deepcopy(checkpoint['summaries']['wave'])
        row = next(r for r in wrong['mean_refinement'] if r['profile'] == self.v.CONFIGURATION['profile'])
        row['values'][0][1] = .125  # finite/nonnegative, but not this captured pair's observation
        with self.assertRaises(self.v.EvidenceError):
            self.v.check_mean_refinement(wrong,runs)
        wrong = copy.deepcopy(checkpoint['summaries']['wave'])
        wrong['pairs'][0]['n'] += 1
        with self.assertRaises(self.v.EvidenceError):
            self.v.check_mean_refinement(wrong,runs)

    def test_exact_calibration_wave_selection_and_amplitude_bound(self):
        runs = historical_json(HISTORICAL,'iter/plans/iter-waves_runs.json.gz')
        chosen = self.v.check_calibration_wave(runs)
        self.assertEqual(len(chosen),2)
        verdict = verdict_schema_control()
        self.v.check_verdict(verdict)  # schema-only true flags, not physical evidence
        for name in chosen:
            wrong = copy.deepcopy(runs)
            wrong[name]['errors']['final']['B']['L1'] = .0021
            self.v.check_verdict(verdict)
            with self.subTest(name=name),self.assertRaises(self.v.EvidenceError):
                self.v.check_calibration_wave(wrong)
        other = next(n for n,r in runs.items() if r['config']['case'] == 'alfven' and r['config']['n'] == 64)
        wrong = copy.deepcopy(runs)
        wrong[other]['errors']['final']['B']['L1'] = 1.
        # Only this helper's calibration selection is exercised, not full spatial
        # acceptance of the deliberately modified N64 record.
        self.assertEqual(self.v.check_calibration_wave(wrong),chosen)

    def test_regular_and_column_shock_exact_diagnostic_flags(self):
        runs = historical_json(HISTORICAL,'iter/plans/iter-physics_runs.json.gz')
        packet,amendment = physics_gate_controls()
        for family in ('regular','columns'):
            run = next(r for r in runs.values() if r['config']['case'] == 'brio-wu' and
                       (r['config']['jitter'] == 0. if family == 'regular'
                        else r['config']['jitter_mode'] == 'columns'))
            self.v.check_physics_diagnostics(run,packet,amendment)
            for mutation in ('missing','flag','bx_applicability','bx_duplicate'):
                wrong = copy.deepcopy(run)
                if mutation == 'missing':
                    wrong['diagnostic_checks'].pop('bx_preserved')
                elif mutation == 'flag':
                    wrong['diagnostic_gates'] = False
                elif mutation == 'bx_applicability':
                    wrong['diagnostic_values']['bx']['gate_applies'] = False
                else:
                    wrong['diagnostic_values']['bx_max_error'] = 1e-7
                with self.subTest(family=family,mutation=mutation),self.assertRaises(self.v.EvidenceError):
                    self.v.check_physics_diagnostics(wrong,packet,amendment)

    def test_planar_jitter_shock_remains_diagnostic_only(self):
        runs = historical_json(HISTORICAL,'iter/plans/iter-physics_runs.json.gz')
        packet,amendment = physics_gate_controls()
        run = next(r for r in runs.values() if r['config']['case'] == 'brio-wu'
                   and r['config']['jitter'] == .15 and r['config']['jitter_mode'] == 'planar')
        self.assertIsNone(run['diagnostic_values']['bx']['passed'])
        self.assertGreater(run['diagnostic_values']['bx']['final']['max'],amendment['bx_max_error'])
        self.v.check_physics_diagnostics(run,packet,amendment)
        for mutation in ('false_pass','gate_applies','extra_flag'):
            wrong = copy.deepcopy(run)
            if mutation == 'false_pass':
                wrong['diagnostic_values']['bx']['passed'] = True
            elif mutation == 'gate_applies':
                wrong['diagnostic_values']['bx']['gate_applies'] = True
            else:
                wrong['diagnostic_checks']['bx_preserved'] = True
            with self.subTest(mutation=mutation),self.assertRaises(self.v.EvidenceError):
                self.v.check_physics_diagnostics(wrong,packet,amendment)

    def test_shock_tracking_travel_seam_and_independent_bx_receipt(self):
        runs = historical_json(HISTORICAL,'iter/plans/iter-physics_runs.json.gz')
        report = historical_json(PREVIOUS,'campaign_a_independent_shock.json.gz')
        packet,amendment = physics_gate_controls()
        name = next(iter(report['measured']))
        run = runs[name]
        self.v.check_primary_shock_bx(report['measured'][name],run,amendment)
        for mutation in ('tracking','travel_duplicate','seam','missing_flag'):
            wrong = copy.deepcopy(run)
            if mutation == 'tracking':
                wrong['physics']['signal_tracking'] = False
            elif mutation == 'travel_duplicate':
                wrong['diagnostic_values']['signal_travel_x'] = .123
            elif mutation == 'seam':
                wrong['physics']['signal_travel_x'] = .45
                wrong['diagnostic_values']['signal_travel_x'] = .45
            else:
                wrong['diagnostic_checks'].pop('signal_tracking')
            with self.subTest(mutation=mutation),self.assertRaises(self.v.EvidenceError):
                self.v.check_physics_diagnostics(wrong,packet,amendment)
        wrong = copy.deepcopy(report['measured'][name])
        wrong['final_Bx_max_error'] = 1e-7
        with self.assertRaises(self.v.EvidenceError):
            self.v.check_primary_shock_bx(wrong,run,amendment)

    def test_jittered_vortex_named_history_maxima_and_normalization(self):
        runs = historical_json(HISTORICAL,'iter/plans/iter-physics_runs.json.gz')
        packet,amendment = physics_gate_controls()
        run = next(r for r in runs.values() if r['config']['case'] == 'orszag-tang' and r['config']['jitter'] == .15)
        self.v.check_physics_diagnostics(run,packet,amendment)
        for mutation in ('missing_flag','normalization','history','different_operator'):
            wrong = copy.deepcopy(run)
            if mutation == 'missing_flag':
                wrong['diagnostic_checks'].pop('mean_B_drift_over_Bscale_max')
            elif mutation == 'normalization':
                wrong['diagnostic_values']['mean_B_drift_over_Bscale_max'] *= 2
            elif mutation == 'history':
                for h in wrong['history']:
                    h['diagnostics']['div_B_limited']['dimensionless']['rms'] *= 2
                wrong['summary']['initial'] = copy.deepcopy(wrong['history'][0]['diagnostics'])
                wrong['summary']['final'] = copy.deepcopy(wrong['history'][-1]['diagnostics'])
            else:
                wrong['diagnostic_values']['limited_face_dimensionless_divB_RMS_max'] = max(
                    h['diagnostics']['div_B_ls']['dimensionless']['rms'] for h in wrong['history'])
                # Make a distinct, finite scalar even if two archived operators
                # happen to have identical maxima on this case.
                wrong['diagnostic_values']['limited_face_dimensionless_divB_RMS_max'] += .001
            with self.subTest(mutation=mutation),self.assertRaises(self.v.EvidenceError):
                self.v.check_physics_diagnostics(wrong,packet,amendment)

    def test_real_spatial_fit_order_uncertainty_and_production_links(self):
        row,production,runs,cases = spatial_control()
        self.v.check_spatial_ladder(row,production,runs,cases)
        for mutation in ('order','production_order','missing_uncertainty','negative_uncertainty','production_input'):
            a,b = copy.deepcopy(row),copy.deepcopy(production)
            if mutation == 'order':
                a['finest_three_order'] += .01
            elif mutation == 'production_order':
                b['finest_three_order'] += .01
            elif mutation == 'missing_uncertainty':
                a.pop('residual_based_order_standard_error')
            elif mutation == 'negative_uncertainty':
                a['residual_based_order_standard_error'] = -1.
            else:
                b['rows'][1]['B_L1'] *= 1.01
            with self.subTest(mutation=mutation),self.assertRaises(self.v.EvidenceError):
                self.v.check_spatial_ladder(a,b,runs,cases)

    def test_middle_spatial_error_changes_residual_not_endpoint_slope(self):
        row,production,runs,cases = spatial_control()
        name = row['names'][2]  # N128 is the middle of the N64/128/256 fit.
        error = row['B_L1'][2]*1.25
        row['B_L1'][2] = production['rows'][2]['B_L1'] = error
        cases[name]['analytic_errors']['B']['L1'] = runs[name]['errors']['final']['B']['L1'] = error
        cases[name]['maximum_production_error_difference'] = max(
            abs(cases[name]['analytic_errors'][f][n]-runs[name]['errors']['final'][f][n])
            for f in cases[name]['analytic_errors'] for n in ('L1','L2','max'))
        # Endpoints/order are untouched. Both retained uncertainties are stale.
        with self.assertRaises(self.v.EvidenceError):
            self.v.check_spatial_ladder(row,production,runs,cases)

    def test_analytic_agreement_scalar_matches_retained_norms(self):
        row,production,runs,cases = spatial_control()
        name = row['names'][0]
        self.v.check_wave_error_agreement(cases[name],runs[name])
        wrong = copy.deepcopy(cases[name])
        wrong['maximum_production_error_difference'] = 1e-14
        # Deliberately below the existing 2e-13 bound, but not the computed
        # retained norm difference: an all-true/under-limit flag is insufficient.
        with self.assertRaises(self.v.EvidenceError):
            self.v.check_wave_error_agreement(wrong,runs[name])

    def test_spatial_positive_inputs_and_residual_scope(self):
        row,production,runs,cases = spatial_control()
        for value in (0.,-1.,float('inf'),float('nan')):
            with self.subTest(error=value),self.assertRaises(self.v.EvidenceError):
                self.v.spatial_fit_metadata([.01,value,.001],True)
        for mutation in ('missing','negative','scope'):
            wrong = copy.deepcopy(production)
            if mutation == 'missing':
                wrong.pop('finest_three_order_standard_error')
            elif mutation == 'negative':
                wrong['finest_three_order_standard_error'] = -1.
            else:
                wrong['uncertainty_scope'] = 'synthetic mutation: systematic guarantee'
            with self.subTest(mutation=mutation),self.assertRaises(self.v.EvidenceError):
                self.v.check_spatial_ladder(row,wrong,runs,cases)

    def test_actual_execution_receipt_metadata_links(self):
        values = receipt_control()
        self.v.check_execution_receipt(**values)
        for field,value in (('workflow','wrong-workflow'),('payload_sha256','0'*64),
                            ('artifact_manifest_sha256','0'*64),('final_csv_sha256','0'*64)):
            wrong = copy.deepcopy(values)
            wrong['receipt'][field] = value
            with self.subTest(field=field),self.assertRaises(self.v.EvidenceError):
                self.v.check_execution_receipt(**wrong)

    def test_execution_configuration_preflight_and_record_mutations(self):
        values = receipt_control()
        for field in ('binary_sha256','preflight_sha256','record_sha256'):
            wrong = copy.deepcopy(values)
            wrong['execution'][field] = '0'*64
            wrong['receipt']['execution'] = copy.deepcopy(wrong['execution'])
            with self.subTest(field=field),self.assertRaises(self.v.EvidenceError):
                self.v.check_execution_receipt(**wrong)
        wrong = copy.deepcopy(values)
        wrong['record']['config']['n'] += 1
        with self.assertRaises(self.v.EvidenceError):
            self.v.check_execution_receipt(**wrong)

    def test_execution_download_partition_not_only_counts(self):
        values = receipt_control()
        wrong = copy.deepcopy(values)
        wrong['receipt']['checked_downloads'][0] = 'outputs/not-registered'
        with self.assertRaises(self.v.EvidenceError):
            self.v.check_execution_receipt(**wrong)
        wrong = copy.deepcopy(values)
        wrong['artifacts']['outputs/raw/not-this-case/final.csv'] = '0'*64
        wrong['receipt']['artifacts'] = copy.deepcopy(wrong['artifacts'])
        with self.assertRaises(self.v.EvidenceError):
            self.v.check_execution_receipt(**wrong)

    def test_submission_metadata_resources_parts_and_workflow(self):
        # This is ONLY a submission-schema control; no binary/archive parts exist
        # or are claimed verified, and it cannot close a full evidence packet.
        snapshot = historical_json(PREVIOUS,'snapshot.json.gz')
        spec = receipt_control()['spec']
        preflight = {n:digest((PREVIOUS/'preflight'/n).read_bytes()) for n in
                     ('preflight.json','execution.json','runtime.json','artifacts.sha256.json')}
        source_parts = snapshot['archives']['source.tar.gz']['parts']
        inputs = {'case.json':'0'*64,'case.py':'0'*64,'snapshot.json':self.v.SNAPSHOT,
                  **{'preflight/'+n:d for n,d in preflight.items()},
                  **{n:snapshot['upload_sha256'][n] for n in source_parts},
                  'vector-potential.part000':'0'*64}
        payload = dict(input_sha256=inputs,parts={'source.tar.gz':source_parts,
                                                'vector-potential':['vector-potential.part000']})
        resources = spec['resources']
        step = dict(name='one-case',environment=self.v.IMAGE,compute_backend='kubernetes',
            kubernetes_memory_limit=resources['memory'],kubernetes_cpu_request=str(resources['threads']),
            kubernetes_cpu_limit=str(resources['threads']),commands=['python3 case.py'])
        workflow = dict(version='0.9.0',inputs=dict(files=[*inputs,'payload.json']),
            workflow=dict(type='serial',specification=dict(steps=[step])),
            outputs=dict(files=['outputs/execution.json','outputs/record.json','outputs/artifacts.sha256.json']))
        self.v.check_submission(workflow,payload,spec,snapshot,preflight)
        for mutation in ('memory','command','part_order','preflight'):
            w,p = copy.deepcopy(workflow),copy.deepcopy(payload)
            if mutation == 'memory':
                w['workflow']['specification']['steps'][0]['kubernetes_memory_limit'] = '999Gi'
            elif mutation == 'command':
                w['workflow']['specification']['steps'][0]['commands'] = ['python3 other.py']
            elif mutation == 'part_order':
                p['parts']['source.tar.gz'].reverse()
            else:
                p['input_sha256']['preflight/preflight.json'] = '0'*64
            with self.subTest(mutation=mutation),self.assertRaises(self.v.EvidenceError):
                self.v.check_submission(w,p,spec,snapshot,preflight)

    def test_preflight_and_bounded_retained_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(PREVIOUS,root/'source_review_packet',ignore=shutil.ignore_patterns('__pycache__'))
            snapshot = historical_json(PREVIOUS,'snapshot.json.gz')
            self.assertEqual(self.v.check_preflight(root,snapshot),
                             digest((PREVIOUS/'preflight/preflight.json').read_bytes()))
            path = root/'source_review_packet/preflight/logs/00.log'
            path.write_bytes(path.read_bytes()+b'not the recorded log')
            with self.assertRaises(self.v.EvidenceError):
                self.v.check_preflight(root,snapshot)

    def test_command_source_arguments_context_and_logs(self):
        # Deliberately invented transient DIRECTORY STRINGS; no workflow, case
        # state, report, command execution, acceptance or complete archive.
        repo,out,reference = '/metadata-repo','/metadata-collection','/private/reference_context'
        views = {p:'/private/'+p for p in self.v.COUNTS}
        capture = dict(private_reference_context=dict(original_root=repo,path=reference),
            private_views={p:dict(path=views[p],original_root='results/followup_iter-'+p+'_20261121')
                           for p in self.v.COUNTS})
        commands = [([repo+'/tests/reference/m1_acceptance/verify_packet.py'],repo)]
        commands += [([out+'/tools/verify_fresh_phase.py',p,views[p],
            out+'/observations/'+p+'/specifications.json',out+'/'+p+'_provenance.json'],reference)
            for p in self.v.COUNTS]
        commands += [
            ([out+'/tools/reduce_boost_pairs.py','medium',views['medium'],out+'/medium_independent.json'],reference),
            ([out+'/tools/reduce_mean.py',views['mean'],out+'/mean_independent.json'],reference),
            ([out+'/tools/prepare_inputs.py','waves',views['waves'],out+'/wave_inputs'],reference),
            ([out+'/tools/reduce_waves.py',out+'/wave_inputs',out+'/waves_independent.json'],reference),
            ([out+'/tools/collect_fresh_physics_reference_inputs.py',views['physics'],out+'/physics_inputs',
             '--client','python3 transport-control.py','--require-complete','--original-root',
             repo+'/results/followup_iter-physics_20261121','--reference-root',reference],repo),
            ([out+'/tools/reduce_boost_pairs.py','physics',views['physics'],out+'/physics_boost_independent.json'],reference),
            ([out+'/tools/reduce_shock.py',out+'/physics_inputs',out+'/shock'],reference),
            ([out+'/tools/reduce_vortex.py',out+'/physics_inputs',out+'/vortex'],reference)]
        rows = []
        for i,((argv,cwd),label) in enumerate(zip(commands,self.v.LABELS),1):
            row = dict(attempt_id=i,label=label,argv=['/usr/bin/python3',*argv],cwd=cwd,
                       interpreter={'executable':'/usr/bin/python3'},timeout_seconds=7200)
            for stream in ('stdout','stderr'):
                row[stream] = {'path':f'logs/{i:03}-{label}.{stream}'}
            rows.append(row)
        self.assertEqual(self.v.check_command_links(rows,capture),
                         (self.v.PurePosixPath(repo),self.v.PurePosixPath(out)))
        for mutation in ('script','input','cwd','log'):
            wrong = copy.deepcopy(rows)
            if mutation == 'script':
                wrong[12]['argv'][1] = out+'/tools/reduce_shock.py'
            elif mutation == 'input':
                wrong[6]['argv'][2] = '/not-the-captured-mean'
            elif mutation == 'cwd':
                wrong[1]['cwd'] = repo
            else:
                wrong[0]['stdout']['path'] = 'logs/other.stdout'
            with self.subTest(mutation=mutation),self.assertRaises(self.v.EvidenceError):
                self.v.check_command_links(wrong,capture)

    def test_boost_partition_and_mean_input_digest(self):
        runs = historical_json(HISTORICAL,'iter/plans/iter-mean_runs.json.gz')
        report = historical_json(PREVIOUS,'campaign_a_independent_mean.json')
        self.v.check_pair_partition(report['pairs'],runs,report['pairs'])
        for row in report['pairs']:
            self.v.check_mean_pair(row,runs)
        wrong = copy.deepcopy(report['pairs'])
        wrong[0]['names'][1] = wrong[1]['names'][1]
        with self.assertRaises(self.v.EvidenceError):
            self.v.check_pair_partition(wrong,runs,report['pairs'])
        wrong = copy.deepcopy(report['pairs'][0])
        wrong['input_sha256'][wrong['names'][0]] = '0'*64
        with self.assertRaises(self.v.EvidenceError):
            self.v.check_mean_pair(wrong,runs)

    def test_primary_exact_names_and_input_key_digest_sets(self):
        runs = historical_json(HISTORICAL,'iter/plans/iter-physics_runs.json.gz')
        for label,filenames in (('shock',('final.csv','geometry.json')),
                ('vortex',('final.csv','geometry.json','projected_bins.json'))):
            report = historical_json(PREVIOUS,'campaign_a_independent_'+label+'.json.gz')
            names = set(report['measured'])
            self.assertEqual(len(names),12 if label == 'shock' else 6)
            self.assertEqual(len(report['input_sha256']),24 if label == 'shock' else 18)
            self.v.check_primary_input_coverage(report,names,filenames,runs)
            wrong = copy.deepcopy(report)
            wrong['input_sha256'].pop(next(iter(wrong['input_sha256'])))
            with self.subTest(label=label),self.assertRaises(self.v.EvidenceError):
                self.v.check_primary_input_coverage(wrong,names,filenames,runs)
            wrong = copy.deepcopy(report)
            wrong['measured']['not-registered'] = wrong['measured'].pop(next(iter(names)))
            with self.subTest(label=label),self.assertRaises(self.v.EvidenceError):
                self.v.check_primary_input_coverage(wrong,names,filenames,runs)

    def test_independent_bin_entries_fields_and_shapes(self):
        bins = historical_json(PREVIOUS,'campaign_a_independent_vortex_bins.json.gz')
        names = set(bins)
        self.assertEqual(len(names),6)
        self.v.check_bin_payload(bins,names)
        name = next(iter(names))
        for mutation in ('missing_case','field','shape','nonfinite'):
            wrong = copy.deepcopy(bins)
            if mutation == 'missing_case':
                wrong.pop(name)
            elif mutation == 'field':
                wrong[name]['not-bx'] = wrong[name].pop('bx')
            elif mutation == 'shape':
                wrong[name]['rho'].pop()
            else:
                wrong[name]['rho'][0] = float('nan')
            with self.subTest(mutation=mutation),self.assertRaises(self.v.EvidenceError):
                self.v.check_bin_payload(wrong,names)

    def test_command_journal_labels_logs_runtime_and_failures(self):
        rows,logs = journal_control()
        self.v.check_journal(rows,logs.__getitem__,['metadata'])
        for mutation in ('label','log','runtime','returncode','time','environment'):
            wrong = copy.deepcopy(rows)
            if mutation == 'label':
                wrong[0]['label'] = 'other'
            elif mutation == 'log':
                wrong[0]['stdout']['sha256'] = '0'*64
            elif mutation == 'runtime':
                wrong[0]['interpreter']['optimization'] = 1
            elif mutation == 'returncode':
                wrong[0]['returncode'] = 1
            elif mutation == 'time':
                wrong[0]['finished_utc'] = '2026-11-21T23:59:59+00:00'
            else:
                wrong[0]['child_environment']['PYTHONOPTIMIZE'] = '1'
            with self.subTest(mutation=mutation),self.assertRaises(self.v.EvidenceError):
                self.v.check_journal(wrong,logs.__getitem__,['metadata'])
        failed = copy.deepcopy(rows)
        failed[0].update(outcome='timeout',returncode=-9)
        # Failure receipts are interpretable; a COMPLETE success inventory rejects them.
        self.v.check_journal(failed,logs.__getitem__)
        with self.assertRaises(self.v.EvidenceError):
            self.v.check_journal(failed,logs.__getitem__,['metadata'])

    def test_ownership_nodes_lock_and_nested_status_are_exported(self):
        manifest,summary,capture = export_schema_control(self.v)
        selected,omitted = self.v.export_selection(manifest,summary,capture)
        self.assertFalse(omitted)
        self.assertEqual(selected,set(manifest))
        self.assertIn('physics_inputs/collection_status.json',selected)
        for name in ('command_ownership/not-a-node.json','command_ownership/registry.lock/extra',
                     'command_ownership/'+format(1,'032x')+'.json/extra'):
            wrong = dict(manifest)
            wrong[name] = '0'*64
            with self.subTest(path=name),self.assertRaises(self.v.EvidenceError):
                self.v.export_selection(wrong,summary,capture)
        wrong = dict(manifest)
        wrong.pop('physics_inputs/collection_status.json')
        with self.assertRaises(self.v.EvidenceError):
            self.v.export_selection(wrong,summary,capture)

    def test_ownership_real_source_launcher_and_exact_node_links(self):
        rows,transport,raw,repo,out,source = ownership_control(self.v)
        self.v.check_ownership(rows,transport,raw.__getitem__,set(raw),repo,out,source)
        for mutation in ('registry','node_id','parent','argv','cwd','guardian_pid'):
            wrong = copy.deepcopy(rows)
            if mutation == 'registry':
                wrong[0]['ownership']['registry'] = '/some-other-registry'
            elif mutation == 'node_id':
                wrong[0]['ownership']['node_id'] = 'f'*32
            elif mutation == 'parent':
                wrong[0]['ownership']['parent_id'] = rows[1]['ownership']['node_id']
            elif mutation == 'argv':
                wrong[0]['argv'].append('not-the-requested-command')
            elif mutation == 'cwd':
                wrong[0]['cwd'] = '/different-context'
            else:
                wrong[0]['ownership']['guardian_pid'] += 1
            with self.subTest(mutation=mutation),self.assertRaises(self.v.EvidenceError):
                self.v.check_ownership(wrong,transport,raw.__getitem__,set(raw),repo,out,source)

    def test_ownership_missing_extra_cycle_and_unlisted_receipts(self):
        rows,transport,raw,repo,out,source = ownership_control(self.v)
        path = 'command_ownership/'+rows[0]['ownership']['node_id']+'.json'
        for mutation in ('missing','extra','cycle','node_name','unlisted'):
            wrong = copy.deepcopy(raw)
            names = set(wrong)
            if mutation == 'missing':
                wrong.pop(path);names.remove(path)
            elif mutation == 'extra':
                extra = json.loads(wrong[path]);extra['node_id'] = 'f'*32
                wrong['command_ownership/'+'f'*32+'.json'] = json_bytes(extra)
                names = set(wrong)
            elif mutation == 'cycle':
                node = json.loads(wrong[path]);node['parent_id'] = node['node_id']
                wrong[path] = json_bytes(node)
            elif mutation == 'node_name':
                node = json.loads(wrong[path]);node['node_id'] = 'f'*32
                wrong[path] = json_bytes(node)
            else:
                # Node bytes exist, but a manifest/export omitted the receipt.
                names.remove(path)
            with self.subTest(mutation=mutation),self.assertRaises(self.v.EvidenceError):
                self.v.check_ownership(rows,transport,wrong.__getitem__,names,repo,out,source)

    def test_ownership_captured_guardian_hash_and_isolated_bootstrap(self):
        rows,transport,raw,repo,out,source = ownership_control(self.v)
        path = 'command_ownership/'+rows[0]['ownership']['node_id']+'.json'
        for mutation in ('hash','source_path','isolation','bootstrap','command_path'):
            wrong = copy.deepcopy(raw)
            node = json.loads(wrong[path])
            if mutation == 'hash':
                node['guardian_source']['sha256'] = '0'*64
            elif mutation == 'source_path':
                node['guardian_source']['path'] = '/not-captured/collector.py'
            elif mutation == 'isolation':
                node['guardian_argv'][1] = '-O'
            elif mutation == 'bootstrap':
                node['guardian_argv'][5] = 'print("not the captured bootstrap")'
            else:
                node['guardian_argv'][-1] = '/outside/command_ownership/'+path.rsplit('/',1)[1]
            wrong[path] = json_bytes(node)
            with self.subTest(mutation=mutation),self.assertRaises(self.v.EvidenceError):
                self.v.check_ownership(rows,transport,wrong.__getitem__,set(wrong),repo,out,source)
        with self.assertRaises(self.v.EvidenceError):
            self.v.guardian_bootstrap(b'GUARDIAN_BOOTSTRAP = make_dynamic_code()\n')

    def test_ownership_writer_cleanup_and_log_finalization_fail_closed(self):
        rows,logs = journal_control()
        for mutation in ('logs','external','writers','unfinished'):
            wrong = copy.deepcopy(rows)
            if mutation == 'logs':
                wrong[0]['logs_closed'] = False
            elif mutation == 'external':
                wrong[0]['external_evidence_required'] = True
            elif mutation == 'writers':
                wrong[0]['ownership']['writers_stopped'] = False
            else:
                wrong[0].update(outcome='running',finished_utc=None,logs_closed=False,
                                external_evidence_required=True)
                wrong[0]['stdout']['sha256'] = None
            with self.subTest(mutation=mutation),self.assertRaises(self.v.EvidenceError):
                self.v.check_journal(wrong,logs.__getitem__,['metadata'])
        rows,transport,raw,repo,out,source = ownership_control(self.v)
        path = 'command_ownership/'+rows[0]['ownership']['node_id']+'.json'
        for mutation in ('active','cancelled','writers','result','error'):
            wrong = copy.deepcopy(raw);node = json.loads(wrong[path])
            if mutation == 'active':
                node['state'] = 'active'
            elif mutation == 'cancelled':
                node['cancelled'] = True
            elif mutation == 'writers':
                node['writers_stopped'] = False
            elif mutation == 'result':
                node['primary_returncode'] = 1
            else:
                node['error_type'] = 'SyntheticStartFailure'
            wrong[path] = json_bytes(node)
            with self.subTest(mutation=mutation),self.assertRaises(self.v.EvidenceError):
                self.v.check_ownership(rows,transport,wrong.__getitem__,set(wrong),repo,out,source)

    def test_nested_transport_uses_parent_outer_registry_and_interval(self):
        rows,transport,raw,repo,out,source = ownership_control(self.v)
        for mutation in ('registry','parent','interval','nested_registry'):
            wrong,receipts = copy.deepcopy(transport),copy.deepcopy(raw)
            if mutation == 'registry':
                wrong[0]['ownership']['registry'] = str(out/'physics_inputs/command_ownership')
            elif mutation == 'parent':
                wrong[0]['ownership']['parent_id'] = rows[0]['ownership']['node_id']
            elif mutation == 'interval':
                wrong[0]['finished_utc'] = '2026-11-22T00:00:02+00:00'
            else:
                receipts['physics_inputs/command_ownership/registry.lock'] = b''
            with self.subTest(mutation=mutation),self.assertRaises(self.v.EvidenceError):
                self.v.check_ownership(rows,wrong,receipts.__getitem__,set(receipts),repo,out,source)

    def test_outer_and_nested_collection_status_are_exact_and_nonaccepting(self):
        control = dict(status='complete',full_m1_accepted=False,final_ai_output_review_passed=False)
        for label in ('outer','nested physics'):
            self.v.check_complete_status(control,label)
            for mutation in ('collecting','failed','acceptance','numeric_false','extra'):
                wrong = dict(control)
                if mutation in ('collecting','failed'):
                    wrong['status'] = mutation
                elif mutation == 'acceptance':
                    wrong['full_m1_accepted'] = True
                elif mutation == 'numeric_false':
                    wrong['full_m1_accepted'] = 0
                else:
                    wrong['external_evidence_required'] = True
                with self.subTest(label=label,mutation=mutation),self.assertRaises(self.v.EvidenceError):
                    self.v.check_complete_status(wrong,label)

    def test_nested_status_rejects_before_any_successful_lifecycle_claim(self):
        # Only two tiny statuses are supplied; this is deliberately NOT a full
        # collection. Invalid nested status must fail before commands are read.
        for state in ('collecting','failed'):
            statuses = {'collection_status.json':dict(status='complete',full_m1_accepted=False,
                    final_ai_output_review_passed=False),
                'physics_inputs/collection_status.json':dict(status=state,full_m1_accepted=False,
                    final_ai_output_review_passed=False)}
            def status_only(name):
                self.assertIn(name,statuses)
                return statuses[name]
            with self.subTest(state=state),self.assertRaises(self.v.EvidenceError):
                self.v.check_collection_lifecycle(status_only,lambda _:b'',set(statuses))

    def test_strict_json_duplicate_nonfinite_and_traversal_keys(self):
        for raw in (b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":Infinity}',b'{"a":1e999}'):
            with self.subTest(raw=raw),self.assertRaises(self.v.EvidenceError):
                self.v.loads(raw)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            put(root,'sha256.json',json_bytes({'../outside':'0'*64}))
            with self.assertRaises(self.v.EvidenceError):
                self.v.verify_closed(root,'sha256.json')

    def test_optimized_cli_rejection_before_argument_processing(self):
        environment = dict(os.environ,PYTHONOPTIMIZE='0',PYTHONDONTWRITEBYTECODE='1')
        for name in ('pack_final_review_evidence.py','verify_final_review_evidence.py'):
            result = subprocess.run([sys.executable,'-B','-O',str(TOOLS/name),'--help'],
                cwd=TOOLS,capture_output=True,text=True,env=environment,timeout=30)
            with self.subTest(name=name):
                self.assertNotEqual(result.returncode,0)
                self.assertIn('Optimized Python',result.stderr)
                self.assertNotIn('evidence_integrity_passed',result.stdout)

    def test_pythonoptimize_environment_rejection(self):
        environment = dict(os.environ,PYTHONOPTIMIZE='1',PYTHONDONTWRITEBYTECODE='1')
        for name in ('pack_final_review_evidence.py','verify_final_review_evidence.py'):
            result = subprocess.run([sys.executable,'-B',str(TOOLS/name),'--help'],
                cwd=TOOLS,capture_output=True,text=True,env=environment,timeout=30)
            with self.subTest(name=name):
                self.assertNotEqual(result.returncode,0)
                self.assertIn('Optimized Python',result.stderr)
                self.assertNotIn('evidence_integrity_passed',result.stdout)


if __name__ == '__main__':
    unittest.main()
