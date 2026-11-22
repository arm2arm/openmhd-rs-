"""Collect actual complete M1 evidence without workflow control or acceptance.

Exit 2 is pending readiness before output creation. Private views contain only
captured metadata and links to actual staged/raw inputs; closed outputs contain
regular materialized files only. Historical adapters/reducers remain unchanged.
"""
if not __debug__:
    raise RuntimeError("M1 evidence tools require assertions: optimized Python is forbidden")

import argparse
import gzip
import json
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
from collect_fresh_physics_reference_inputs import (
    BINARY, SNAPSHOT, CaptureChanged, CommandJournal, MetadataCapture, case_metadata,
    copy_verified, digest, physics_files, read, relative_path, require,
    runtime_info, sha, verify_capture_copies, write_json,
)

COUNTS = dict(medium=48, mean=24, waves=112, physics=30)
REQUIRED_LABELS = [
    'prior_packet','verify_medium','verify_mean','verify_waves','verify_physics',
    'medium_norms','mean_norms','wave_inputs','wave_norms','physics_inputs',
    'physics_norms','shock_reference','vortex_reference',
]
CONFIGURATION = dict(profile='bulk-frame-heun-quadratic-v1', accelerated_projection=False,
                     projection_screening=1., riemann_solver='hlld-pressure',
                     potential_limiter='smooth-extrema', trial_step_fraction=None)


def original_name(repo, path):
    return str(path.relative_to(repo)) if path.is_relative_to(repo) else str(path)


def require_terminal(capture, phases, verdict_path):
    waiting = []
    for phase, directory in phases.items():
        checkpoint, runs = (capture.parsed(directory/n) for n in ('checkpoint.json','runs.json'))
        require(not checkpoint['verified_required_failure'] and not checkpoint['execution_failures'],
                'Required physical/execution failure blocks collection: '+phase)
        require(checkpoint['completed_cases'] == len(runs)
                and checkpoint['expected_cases'] == COUNTS[phase], 'Incoherent checkpoint: '+phase)
        if not checkpoint['all_terminal'] or len(runs) != COUNTS[phase]:
            waiting.append(dict(phase=phase,collected=len(runs),expected=COUNTS[phase]))
    if waiting or verdict_path not in capture.data:
        return dict(ready=False,pending_phases=waiting,
                    final_verdict_present=verdict_path in capture.data,full_m1_accepted=False)
    verdict = capture.parsed(verdict_path)
    require(verdict['snapshot_sha256'] == SNAPSHOT and verdict['binary_sha256'] == BINARY
            and verdict['all_registered_phase_checks_passed'] and not verdict['full_m1_accepted'],
            'Wrong/incomplete final verdict')
    require(set(verdict['phases']) == {'bounded_short','bounded_medium','mean','calibration_wave','calibration_vortex','physics','waves'},
            'Unexpected registered phase set')
    require(all(p['passed'] for p in verdict['phases'].values()), 'Failed registered phase')
    require(verdict['configuration'] == CONFIGURATION, 'Wrong final candidate configuration')
    return None


def create_phase_view(capture, original, view):
    """All metadata are immutable copies; all nonmetadata links are actual fresh inputs."""
    view.mkdir(parents=True)
    for path, data in capture.data.items():
        if path.is_relative_to(original):
            target = view / path.relative_to(original)
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(data)
    plan = capture.parsed(original/'plan.json')
    for entry in plan['cases']:
        directory = relative_path(entry['directory'])
        actual_case, case = original/directory, view/directory
        payload = capture.parsed(actual_case/'payload.json')
        for name in payload['input_sha256']:
            relative = relative_path(name)
            target = case/relative
            if not target.exists():
                target.parent.mkdir(parents=True,exist_ok=True)
                target.symlink_to((actual_case/relative).resolve(strict=True))
        name = entry['specification']['config']['name']
        require(relative_path(name).parts == (name,), 'Invalid raw case name')
        actual_final = original/'raw'/name/'final.csv'
        require(not actual_final.is_symlink()
                and actual_final.resolve(strict=True).is_relative_to(original.resolve()),
                'Fresh final origin must remain inside its actual phase, not an external cache')
        target = view/'raw'/name/'final.csv'
        target.parent.mkdir(parents=True,exist_ok=True)
        target.symlink_to(actual_final.resolve(strict=True))
        output = original/'download'/directory/'outputs'
        manifest = capture.parsed(output/'artifacts.sha256.json')
        for remote in manifest:
            relative = relative_path(remote)
            require(relative.parts[0] == 'outputs','Invalid remote artifact path')
            source = output.parent/relative
            target = view/'download'/directory/relative
            if source.exists() and not target.exists():
                target.parent.mkdir(parents=True,exist_ok=True)
                target.symlink_to(source.resolve(strict=True))


def materialize_wave_inputs(destination, view, original, runs, phase_receipt):
    """Replace adapter links by verified fresh bytes, preserving origin/target receipts."""
    rows = read(destination/'input_receipts.json')
    require(len(rows) == len(runs) and {r['name'] for r in rows} == set(runs),
            'Wave adapter coverage mismatch')
    for row in rows:
        name, filename = row['name'],row['artifact']
        require(relative_path(name).parts == (name,), 'Invalid wave case name')
        require(filename == 'final.csv','Unexpected wave artifact')
        target = destination/name/filename
        require(target.parent.resolve().is_relative_to(destination.resolve()),
                'Wave materialization parent escaped the collection')
        actual = original/'raw'/name/filename
        require(not actual.is_symlink() and actual.resolve(strict=True).is_relative_to(original.resolve()),
                'Fresh wave origin must remain inside its actual phase')
        expected_source = view/'raw'/name/filename
        require(target.is_symlink() and target.resolve(strict=True) == expected_source.resolve(strict=True)
                == actual.resolve(strict=True), 'Wave adapter target is not actual fresh input')
        receipt = phase_receipt['receipts'][name]
        expected = runs[name]['sha256'][filename]
        require(row['workflow'] == receipt['workflow']
                and row['sha256'] == expected == receipt['final_csv_sha256']
                == receipt['artifacts']['outputs/raw/'+name+'/'+filename],
                'Wave materialization lacks fresh execution/manifest identity')
        identity = copy_verified(actual,target,expected)
        row.update(adapter_local_source=row['local_source'],local_source=str(actual),
                   source_realpath=str(actual.resolve(strict=True)),
                   copied_path=str(target.relative_to(destination)),materialized=True,
                   bytes=identity['bytes'],target_sha256=identity['sha256'],
                   remote_path='outputs/raw/'+name+'/'+filename,
                   artifact_manifest_sha256=receipt['artifact_manifest_sha256'])
    write_json(destination/'input_receipts.json',rows)


def assert_closed_files(out):
    files = {}
    for path in sorted(out.rglob('*')):
        require(not path.is_symlink(),'External or internal links forbidden in closed collection')
        require('__pycache__' not in path.relative_to(out).parts,'Cache files forbidden in new collection')
        require(path.is_file() or path.is_dir(),'Special files forbidden in closed collection')
        if path.is_file():
            files[str(path.relative_to(out))] = sha(path)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--client',default='python3 results/limiter_campaign_tools_20261113/reana-command.py')
    args = parser.parse_args()
    repo = Path.cwd().resolve()
    tools = repo/'tests/reference/m1_acceptance'
    require(tools.is_dir(),'Run from repository root')
    phases = {p:repo/('results/followup_iter-'+p+'_20261121') for p in COUNTS}
    registered = repo/'results/m1_final_campaign_cases_20261121'
    verdict_path = repo/'results/followup_iter_verdict_20261121.json'
    # This stable readiness observation is the only path allowed to return 2.
    readiness_paths = [d/n for d in phases.values() for n in ('plan.json','runs.json','checkpoint.json')]
    if verdict_path.exists():
        readiness_paths.append(verdict_path)
    def coherent(data):
        for directory in phases.values():
            runs = json.loads(data[directory/'runs.json'])
            checkpoint = json.loads(data[directory/'checkpoint.json'])
            if checkpoint['completed_cases'] != len(runs):
                raise CaptureChanged('Observer checkpoint/run generation is incoherent')
    ready_capture = MetadataCapture.take(readiness_paths,validate=coherent)
    pending = require_terminal(ready_capture,phases,verdict_path)
    if pending:
        print(json.dumps(pending))
        return 2

    collector = Path(__file__).resolve().with_name('collect_fresh_physics_reference_inputs.py')
    sources = [Path(__file__).resolve(),collector,*[tools/name for name in (
        'verify_packet.py','verify_fresh_phase.py','prepare_inputs.py','reduce_waves.py',
        'reduce_boost_pairs.py','reduce_mean.py','reduce_shock.py','reduce_vortex.py')]]
    historical = {p:repo/('tests/reference/m1_iterative_step_campaigns/iter/plans/iter-'+p+'_runs.json.gz')
                  for p in COUNTS}
    references = [repo/'benchmarks/m0/packet.json',*[repo/'tests/reference/external_mhd'/n
                  for n in ('provenance.json','brio_8192.csv.gz','vortex_512.csv.gz')]]
    old_live = [repo/('results/followup_iter-'+p+'_20261117/runs.json') for p in COUNTS]
    old_live = [p for p in old_live if p.exists()]
    base = [*readiness_paths,*sources,*historical.values(),
            *references,*old_live,
            *[registered/('iter-'+p+'.json') for p in COUNTS]]
    def expand(data):
        return [path for directory in phases.values()
                for path in case_metadata(directory,json.loads(data[directory/'plan.json']))]
    capture = MetadataCapture.take(base,expand,validate=coherent)
    require(require_terminal(capture,phases,verdict_path) is None,'Terminal metadata changed; retry later')
    # Coherence is by case name; historical A ordering is deliberately irrelevant.
    for phase,directory in phases.items():
        plan,runs = (capture.parsed(directory/n) for n in ('plan.json','runs.json'))
        entries = {e['specification']['config']['name']:e for e in plan['cases']}
        specs = capture.parsed(registered/('iter-'+phase+'.json'))
        require(len(entries) == len(runs) == len(specs) == COUNTS[phase]
                and set(entries) == set(runs),'Terminal case coverage mismatch: '+phase)
        require({s['config']['name']:s for s in specs} ==
                {n:e['specification'] for n,e in entries.items()},'Registered case mismatch: '+phase)
        # The frozen strict verifier also checks the actual plan/spec list order.
        require([e['specification'] for e in plan['cases']] == specs,
                'Fresh plan differs from its own registered specification order')

    out = args.output.resolve()
    require(not out.exists(),'Use a new output directory, preserving partial failures')
    require(not any(out.is_relative_to(d) or d.is_relative_to(out) for d in phases.values()),
            'Output must be separate from live phase directories')
    for packet in ('m1_acceptance','m1_iterative_step_campaigns'):
        require(not out.is_relative_to(repo/'tests/reference'/packet),
                'Historical reference packets are closed')
    out.mkdir(parents=True)
    destinations = {}
    for path in capture.data:
        if path in sources:
            destinations[path] = 'tools/'+path.name
        elif path in historical.values():
            destinations[path] = 'observations/historical_a/'+path.name
        elif path in references or path in old_live:
            destinations[path] = 'observations/reference_inputs/'+str(path.relative_to(repo))
        elif path == verdict_path:
            destinations[path] = 'registered_verdict.json'
        elif path.parent == registered:
            phase = path.stem.removeprefix('iter-')
            destinations[path] = 'observations/'+phase+'/specifications.json'
        else:
            phase = next(p for p,d in phases.items() if path.is_relative_to(d))
            relative = path.relative_to(phases[phase]).as_posix()
            if relative in ('plan.json','runs.json','checkpoint.json') or relative.startswith('download/'):
                destinations[path] = 'observations/'+phase+'/'+relative
            else:
                destinations[path] = 'observations/'+phase+'/cases/'+relative
    capture_record = capture.export(out,destinations,lambda p:original_name(repo,p))
    write_json(out/'metadata_capture.json',capture_record)
    source_hashes = {original_name(repo,p):digest(capture.data[p]) for p in sources}
    write_json(out/'collection_status.json',dict(status='collecting',full_m1_accepted=False))
    journal = CommandJournal(out)
    try:
        # Ephemeral view is outside the closed collection. Its metadata are
        # regular captured copies; staged parts/raw links still verify ACTUAL
        # immutable submission files, not an invented reduced staging packet.
        with tempfile.TemporaryDirectory(prefix='openmhd-m1-capture-',dir=out.parent) as temporary:
            reference_view = Path(temporary)/'reference_context'
            for path in [*references,*old_live]:
                target = reference_view/path.relative_to(repo)
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(capture.data[path])
            views = {}
            for phase,directory in phases.items():
                views[phase] = Path(temporary)/phase
                create_phase_view(capture,directory,views[phase])
            capture_record['private_views'] = {
                phase:dict(path=str(views[phase]),original_root=original_name(repo,directory),
                           metadata='Exact captured copies; see files original-to-copy map',
                           other_inputs='Links to actual original staged inputs and fresh raw outputs')
                for phase,directory in phases.items()}
            capture_record['private_reference_context'] = dict(
                path=str(reference_view),original_root=str(repo),
                inputs='Captured references/packet and optional comparison-only previous live-A run maps')
            write_json(out/'metadata_capture.json',capture_record)
            def run(label,script,*arguments,command_cwd=None):
                journal.run(label,[sys.executable,str(script),*map(str,arguments)],
                            cwd=command_cwd or reference_view)
                print(label+': completed',flush=True)
            frozen_tools = out/'tools'
            run('prior_packet',tools/'verify_packet.py',command_cwd=repo)
            for phase in phases:
                run('verify_'+phase,frozen_tools/'verify_fresh_phase.py',phase,views[phase],
                    out/'observations'/phase/'specifications.json',out/(phase+'_provenance.json'))
            run('medium_norms',frozen_tools/'reduce_boost_pairs.py','medium',views['medium'],out/'medium_independent.json')
            run('mean_norms',frozen_tools/'reduce_mean.py',views['mean'],out/'mean_independent.json')
            run('wave_inputs',frozen_tools/'prepare_inputs.py','waves',views['waves'],out/'wave_inputs')
            materialize_wave_inputs(out/'wave_inputs',views['waves'],phases['waves'],
                capture.parsed(phases['waves']/'runs.json'),read(out/'waves_provenance.json'))
            run('wave_norms',frozen_tools/'reduce_waves.py',out/'wave_inputs',out/'waves_independent.json')
            run('physics_inputs',frozen_tools/collector.name,views['physics'],out/'physics_inputs',
                '--client',args.client,'--require-complete','--original-root',phases['physics'],
                '--reference-root',reference_view,command_cwd=repo)
            run('physics_norms',frozen_tools/'reduce_boost_pairs.py','physics',views['physics'],out/'physics_boost_independent.json')
            run('shock_reference',frozen_tools/'reduce_shock.py',out/'physics_inputs',out/'shock')
            run('vortex_reference',frozen_tools/'reduce_vortex.py',out/'physics_inputs',out/'vortex')

        identity_rows = {}
        for phase,directory in phases.items():
            runs = capture.parsed(directory/'runs.json')
            old = json.loads(gzip.decompress(capture.data[historical[phase]]))
            phase_receipt = read(out/(phase+'_provenance.json'))
            required = {name:physics_files(run['config']) if phase == 'physics' else ['final.csv']
                        for name,run in runs.items()}
            for name,filenames in required.items():
                for filename in filenames:
                    copied = (out/'physics_inputs'/name/filename if phase == 'physics' else
                              out/'wave_inputs'/name/filename if phase == 'waves' else None)
                    path = copied if copied else directory/'raw'/name/filename
                    value = sha(path)
                    receipt = phase_receipt['receipts'][name]
                    remote = 'outputs/raw/'+name+'/'+filename
                    require(value == runs[name]['sha256'][filename] == receipt['artifacts'][remote],
                            'Consumed raw identity mismatch')
                    if phase != 'physics':
                        require(sha(directory/'raw'/name/filename) == value,'Fresh final changed')
                    identity_rows[phase+'/'+name+'/'+filename] = dict(
                        sha256=value,bytes=path.stat().st_size,
                        byte_identical_to_a=value == old[name]['sha256'][filename],
                        workflow=receipt['workflow'],remote_path=remote,
                        artifact_manifest_sha256=receipt['artifact_manifest_sha256'],
                        copied_path=str(copied.relative_to(out)) if copied else None,
                        local_source=str(directory/'raw'/name/filename) if phase != 'physics'
                                     else str(copied))
        require(len(identity_rows) == 238,'Expected exact 214 finals/18 geometry/6 bin identities')
        wave = read(out/'waves_independent.json')
        require(wave['recorded_runs'] == wave['manifest_runs'] == len(wave['cases']) == 112,
                'Incomplete wave report')
        require(all(r['state']['passed'] for r in wave['cases'].values()),'Wave state failed')
        require(len(wave['pairs']) == 48 and all(p['passed'] for p in wave['pairs'].values())
                and len(wave['spatial']) == 8 and all(p['status'] == 'pass' for p in wave['spatial'])
                and len(wave['temporal']) == 12 and not wave['verified_required_failure']
                and wave['reused_cases'] == wave['reused_pairs'] == 0,'Wave reduction failed')
        for key in ('pending_cases','pending_pairs','pending_temporal','failed_runs','failed_pairs','failed_spatial'):
            require(not wave[key],'Wave pending/failure: '+key)
        for label,count in (('medium',24),('mean',12),('physics_boost',15)):
            report = read(out/(label+'_independent.json'))
            require(len(report['pairs']) == count and report['all_passed']
                    and all(r['passed'] for r in report['pairs']) and not report['full_m1_accepted'],
                    'Independent boost failure: '+label)
        shock,vortex = read(out/'shock/independent_reference.json'),read(out/'vortex/independent_reference.json')
        require(len(shock['measured']) == 12 and len(shock['reference_gates']) == 4
                and shock['all_reference_gates_passed'],'Shock reference failed')
        require(len(vortex['measured']) == 6 and len(vortex['primary_reference_ladders']) == 2
                and not vortex['missing_primary_cases']
                and all(p['status'] == 'pass' for p in vortex['primary_reference_ladders']),
                'Vortex reference failed')
        require([row['label'] for row in journal.rows] == REQUIRED_LABELS
                and all(row['outcome'] == 'success' and row['returncode'] == 0 for row in journal.rows),
                'Missing/failed command attempt')
        capture_record['final_unchanged_check'] = capture.unchanged()
        verify_capture_copies(out,capture_record)
        write_json(out/'metadata_capture.json',capture_record)
        observations = {name:row['sha256'] for name,row in capture_record['files'].items()}
        summary = dict(
            scope='Full fresh independent arithmetic/provenance collection; separate final review and outer closure required.',
            snapshot_sha256=SNAPSHOT,binary_sha256=BINARY,verified_matrix_cases=214,
            independently_reduced_boost_pairs=99,spatial_ladders=8,temporal_ladders=12,
            primary_shock_cases=12,primary_vortex_cases=6,actual_raw_inputs=len(identity_rows),
            matched_a_inputs=sum(r['byte_identical_to_a'] for r in identity_rows.values()),
            raw_input_identities=identity_rows,source_sha256=source_hashes,observation_sha256=observations,
            capture_manifest_sha256=sha(out/'metadata_capture.json'),runtime=runtime_info(),
            required_successful_command_labels=REQUIRED_LABELS,all_independent_checks_passed=True,
            final_ai_output_review_passed=False,full_m1_accepted=False)
        write_json(out/'summary.json',summary)
        write_json(out/'collection_status.json',dict(status='complete',full_m1_accepted=False,
                                                   final_ai_output_review_passed=False))
        manifest = assert_closed_files(out)
        write_json(out/'sha256.json',manifest)
    except BaseException as exc:
        write_json(out/'collection_status.json',dict(status='failed',error_type=type(exc).__name__,
                                                   full_m1_accepted=False))
        raise
    print('Collected complete fresh evidence; final review/archive/acceptance remain pending',flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
