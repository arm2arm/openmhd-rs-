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
               interpreter=runtime,child_environment=dict(PYTHONOPTIMIZE='0',PYTHONDONTWRITEBYTECODE='1'))
    for stream in ('stdout','stderr'):
        path = 'logs/001-metadata.'+stream
        row[stream] = dict(path=path,sha256=digest(logs[path]),bytes=len(logs[path]))
    return [row],logs


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
        # Schema-only control: not a witnessed verdict or complete campaign.
        control = dict(snapshot_sha256=self.v.SNAPSHOT,binary_sha256=self.v.BINARY,
            configuration=copy.deepcopy(self.v.CONFIGURATION),all_registered_phase_checks_passed=True,
            full_m1_accepted=False,phases={p:dict(passed=True,checks={'metadata_control':True})
                                          for p in self.v.PHASES})
        self.v.check_verdict(control)
        mutations = []
        wrong = copy.deepcopy(control)
        wrong['phases']['unregistered'] = wrong['phases'].pop('waves')
        mutations.append(wrong)
        wrong = copy.deepcopy(control)
        wrong['configuration']['accelerated_projection'] = True
        mutations.append(wrong)
        wrong = copy.deepcopy(control)
        wrong['phases']['waves']['checks']['metadata_control'] = False
        mutations.append(wrong)
        for wrong in mutations:
            with self.assertRaises(self.v.EvidenceError):
                self.v.check_verdict(wrong)

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
