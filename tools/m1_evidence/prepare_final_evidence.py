"""Read-only final M1 evidence collection after all registered workflows finish.

No workflow submission, numerical evolution, Cargo command or acceptance action.
Run from repository root with a fresh --output directory. Exit 2 means pending
inputs before creating output. A later failure preserves all partial evidence.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

SNAPSHOT = 'b67ce03779a194099983b7ff07c0cafed23e9ea3a9051047492d072255e0160f'
BINARY = '18afcf0308338e2ea0ea7ef5e03dba46af9d7025f3ccf4a6a48ebbfe800d0725'
COUNTS = dict(medium=48, mean=24, waves=112, physics=30)


def read(path):
    return json.loads(path.read_text())


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--client', default='python3 results/limiter_campaign_tools_20261113/reana-command.py')
    args = parser.parse_args()
    repo = Path.cwd()
    tools = repo / 'tests/reference/m1_acceptance'
    assert tools.is_dir(), 'Run from the repository root'
    phases = {p: repo / ('results/followup_iter-' + p + '_20261121') for p in COUNTS}
    registered = repo / 'results/m1_final_campaign_cases_20261121'
    verdict_path = repo / 'results/followup_iter_verdict_20261121.json'
    waiting = []
    inputs = {}
    for phase, directory in phases.items():
        checkpoint, runs = read(directory / 'checkpoint.json'), read(directory / 'runs.json')
        assert not checkpoint['verified_required_failure'] and not checkpoint['execution_failures']
        if not checkpoint['all_terminal'] or len(runs) != COUNTS[phase]:
            waiting.append(dict(phase=phase, collected=len(runs), expected=COUNTS[phase]))
        for name in ('plan.json', 'runs.json', 'checkpoint.json'):
            path = directory / name
            inputs[str(path.relative_to(repo))] = sha(path)
        specification = registered / ('iter-' + phase + '.json')
        inputs[str(specification.relative_to(repo))] = sha(specification)
    if waiting or not verdict_path.exists():
        print(json.dumps(dict(ready=False, pending_phases=waiting,
                              final_verdict_present=verdict_path.exists(), full_m1_accepted=False)))
        return 2
    verdict = read(verdict_path)
    assert verdict['snapshot_sha256'] == SNAPSHOT and verdict['binary_sha256'] == BINARY
    assert verdict['all_registered_phase_checks_passed'] and not verdict['full_m1_accepted']
    assert len(verdict['phases']) == 7 and all(p['passed'] for p in verdict['phases'].values())
    assert verdict['configuration'] == dict(profile='bulk-frame-heun-quadratic-v1',
        accelerated_projection=False, projection_screening=1., riemann_solver='hlld-pressure',
        potential_limiter='smooth-extrema', trial_step_fraction=None)
    inputs[str(verdict_path.relative_to(repo))] = sha(verdict_path)
    out = args.output.resolve()
    if out.exists():
        raise FileExistsError('Use a new output directory, preserving old observations')
    out.mkdir(parents=True)
    (out / 'logs').mkdir()
    (out / 'tools').mkdir()
    collector = Path(__file__).resolve().with_name('collect_fresh_physics_reference_inputs.py')
    sources = [Path(__file__).resolve(), collector, *[tools / name for name in (
        'verify_packet.py', 'verify_fresh_phase.py', 'prepare_inputs.py', 'reduce_waves.py',
        'reduce_boost_pairs.py', 'reduce_mean.py', 'reduce_shock.py', 'reduce_vortex.py')]]
    source_hashes = {str(p.relative_to(repo)): sha(p) for p in sources}
    for source in sources:
        shutil.copyfile(source, out / 'tools' / source.name)
    commands = []

    def run(label, script, *arguments):
        argv = [sys.executable, str(script), *map(str, arguments)]
        started = datetime.now(timezone.utc).isoformat()
        with (out / 'logs' / (label + '.stdout')).open('w') as stdout, \
                (out / 'logs' / (label + '.stderr')).open('w') as stderr:
            result = subprocess.run(argv, cwd=repo, stdout=stdout, stderr=stderr, timeout=7200)
        commands.append(dict(label=label, argv=argv, started_utc=started,
                             finished_utc=datetime.now(timezone.utc).isoformat(), returncode=result.returncode))
        (out / 'commands.json').write_text(json.dumps(commands, indent=1) + '\n')
        assert result.returncode == 0, 'Preserved failed evidence command: ' + label
        print(label + ': completed', flush=True)

    run('prior_packet', tools / 'verify_packet.py')
    for phase, directory in phases.items():
        run('verify_' + phase, tools / 'verify_fresh_phase.py', phase, directory,
            registered / ('iter-' + phase + '.json'), out / (phase + '_provenance.json'))
        destination = out / 'observations' / phase
        destination.mkdir(parents=True)
        for name in ('plan.json', 'runs.json', 'checkpoint.json'):
            shutil.copyfile(directory / name, destination / name)
        shutil.copyfile(registered / ('iter-' + phase + '.json'), destination / 'specifications.json')
    run('medium_norms', tools / 'reduce_boost_pairs.py', 'medium', phases['medium'], out / 'medium_independent.json')
    run('mean_norms', tools / 'reduce_mean.py', phases['mean'], out / 'mean_independent.json')
    run('wave_inputs', tools / 'prepare_inputs.py', 'waves', phases['waves'], out / 'wave_inputs')
    run('wave_norms', tools / 'reduce_waves.py', out / 'wave_inputs', out / 'waves_independent.json')
    run('physics_inputs', collector, phases['physics'], out / 'physics_inputs', '--client', args.client)
    run('physics_norms', tools / 'reduce_boost_pairs.py', 'physics', phases['physics'], out / 'physics_boost_independent.json')
    run('shock_reference', tools / 'reduce_shock.py', out / 'physics_inputs', out / 'shock')
    run('vortex_reference', tools / 'reduce_vortex.py', out / 'physics_inputs', out / 'vortex')

    # Every consumed raw input is read again; historical identity is reported,
    # not required to replace the fresh independent calculations above.
    identity_rows = {}
    for phase, directory in phases.items():
        runs = read(directory / 'runs.json')
        old_path = repo / ('tests/reference/m1_iterative_step_campaigns/iter/plans/iter-' + phase + '_runs.json.gz')
        old = json.loads(gzip.decompress(old_path.read_bytes()))
        inputs[str(old_path.relative_to(repo))] = sha(old_path)
        receipt = read(out / 'physics_inputs/input_receipts.json') if phase == 'physics' else None
        required = ({row['name']: row['verified'] for row in receipt['observations']} if receipt else
                    {name: {'final.csv': run['sha256']['final.csv']} for name, run in runs.items()})
        for name, filenames in required.items():
            for filename, digest in filenames.items():
                path = (out / 'physics_inputs' / name / filename if phase == 'physics'
                        else directory / 'raw' / name / filename)
                assert sha(path) == digest == runs[name]['sha256'][filename]
                identity_rows[phase + '/' + name + '/' + filename] = dict(
                    sha256=digest, byte_identical_to_a=digest == old[name]['sha256'][filename])
    assert len(identity_rows) == 238  # 214 finals + 18 primary geometries + six projected-bin files
    wave = read(out / 'waves_independent.json')
    assert wave['recorded_runs'] == wave['manifest_runs'] == 112
    assert len(wave['pairs']) == 48 and all(p['passed'] for p in wave['pairs'].values())
    assert len(wave['spatial']) == 8 and all(p['status'] == 'pass' for p in wave['spatial'])
    assert len(wave['temporal']) == 12 and not wave['verified_required_failure']
    assert wave['reused_cases'] == wave['reused_pairs'] == 0
    for key in ('pending_cases', 'pending_pairs', 'pending_temporal', 'failed_runs', 'failed_pairs', 'failed_spatial'):
        assert not wave[key], key
    for label, count in (('medium', 24), ('mean', 12), ('physics_boost', 15)):
        report = read(out / (label + '_independent.json'))
        assert len(report['pairs']) == count and report['all_passed']
    shock, vortex = read(out / 'shock/independent_reference.json'), read(out / 'vortex/independent_reference.json')
    assert len(shock['measured']) == 12 and len(shock['reference_gates']) == 4 and shock['all_reference_gates_passed']
    assert len(vortex['measured']) == 6 and len(vortex['primary_reference_ladders']) == 2
    assert not vortex['missing_primary_cases'] and all(p['status'] == 'pass' for p in vortex['primary_reference_ladders'])
    assert all(sha(repo / name) == digest for name, digest in inputs.items()), 'Input changed during collection'
    assert all(sha(repo / name) == digest for name, digest in source_hashes.items()), 'Reducer source changed'
    shutil.copyfile(verdict_path, out / 'registered_verdict.json')
    summary = dict(scope='Full fresh independent arithmetic and provenance collection; separate final review and final archive closure remain required.',
        snapshot_sha256=SNAPSHOT, binary_sha256=BINARY, verified_matrix_cases=214,
        independently_reduced_boost_pairs=99, spatial_ladders=8, temporal_ladders=12,
        primary_shock_cases=12, primary_vortex_cases=6, actual_raw_inputs=len(identity_rows),
        matched_a_inputs=sum(row['byte_identical_to_a'] for row in identity_rows.values()),
        raw_input_identities=identity_rows, source_sha256=source_hashes, observation_sha256=inputs,
        all_independent_checks_passed=True, final_ai_output_review_passed=False, full_m1_accepted=False)
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, allow_nan=False) + '\n')
    manifest = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*'))
                if p.is_file() and '__pycache__' not in p.parts}
    (out / 'sha256.json').write_text(json.dumps(manifest, indent=1) + '\n')
    print('Collected complete fresh evidence; final review/archive/acceptance remain pending', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
