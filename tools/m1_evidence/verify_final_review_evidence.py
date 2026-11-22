"""Portable read-only identity/coverage check; never an M1 acceptance action."""
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(root, name):
    data = (root / name).read_bytes()
    return json.loads(gzip.decompress(data) if name.endswith('.gz') else data)


def main():
    root = Path(__file__).resolve().parent
    manifest = read(root, 'sha256.json')
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p != root / 'sha256.json'}
    assert actual == set(manifest)
    for name, digest in manifest.items():
        path = PurePosixPath(name)
        assert not path.is_absolute() and '..' not in path.parts and str(path) == name
        assert (root / name).resolve().is_relative_to(root)
        assert sha((root / name).read_bytes()) == digest, name
    index = read(root, 'artifact_index.json')
    assert index['schema'] == 'openmhd.m1-final-review-evidence.v1'
    assert not index['full_m1_accepted'] and not index['final_ai_output_review_passed']
    assert {row['path'] for row in index['artifacts']} == actual - {'artifact_index.json'}
    assert len(index['artifacts']) == len(actual) - 1
    for row in index['artifacts']:
        data = (root / row['path']).read_bytes()
        assert len(data) == row['stored_bytes'] and sha(data) == row['stored_sha256']
        assert row['encoding'] in ('gzip', 'identity')
        raw = gzip.decompress(data) if row['encoding'] == 'gzip' else data
        assert len(raw) == row['original_bytes'] and sha(raw) == row['original_sha256']
    snapshot_path = root / 'source_review_packet/snapshot.json.gz'
    snapshot_bytes = gzip.decompress(snapshot_path.read_bytes())
    assert sha(snapshot_bytes) == index['snapshot_sha256'] == 'b67ce03779a194099983b7ff07c0cafed23e9ea3a9051047492d072255e0160f'
    frozen = read(root, 'frozen_source_catalog.json')
    assert frozen['revision'] == index['source_revision'] == '2bdcea0d28340e7429e10053a641f92d51fcc696'
    snapshot = json.loads(snapshot_bytes)
    source_review = read(root, 'source_review_packet/review_report_sha256.json')
    assert sha((root/'documents/M1_FINAL_AI_REVIEW.md').read_bytes()) == source_review['docs/M1_FINAL_AI_REVIEW.md']
    preflight = read(root, 'source_review_packet/preflight/preflight.json')
    assert preflight['snapshot_sha256'] == index['snapshot_sha256']
    assert preflight['binary_sha256'] == index['binary_sha256']
    required = {n: d for n,d in snapshot['source_sha256'].items()
                if n.startswith(('apps/', 'crates/', 'scripts/', 'benchmarks/', 'reana/',
                                 'tests/reference/external_mhd/')) or
                n in ('Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml')}
    assert frozen['sha256'] == required
    assert len([n for n in required if not n.startswith('tests/reference/')
                and n != 'rust-toolchain.toml']) == frozen['scientific_files'] == 226
    for name, digest in required.items():
        assert sha((root / 'frozen_source' / name).read_bytes()) == digest, name
    summary = read(root, 'fresh/summary.json')
    assert summary['snapshot_sha256'] == index['snapshot_sha256']
    assert summary['binary_sha256'] == index['binary_sha256'] == '18afcf0308338e2ea0ea7ef5e03dba46af9d7025f3ccf4a6a48ebbfe800d0725'
    for key, expected in dict(verified_matrix_cases=214, independently_reduced_boost_pairs=99,
            spatial_ladders=8, temporal_ladders=12, primary_shock_cases=12,
            primary_vortex_cases=6, actual_raw_inputs=238).items():
        assert summary[key] == expected, key
    assert summary['all_independent_checks_passed'] and not summary['full_m1_accepted']
    assert not summary['final_ai_output_review_passed']
    assert len(summary['raw_input_identities']) == 238
    assert summary['matched_a_inputs'] == sum(row['byte_identical_to_a'] for row in summary['raw_input_identities'].values())
    for name, digest in summary['source_sha256'].items():
        assert sha((root / 'fresh/tools' / Path(name).name).read_bytes()) == digest, name
    phase_runs = {}
    for phase, count in (('medium',48), ('mean',24), ('waves',112), ('physics',30)):
        prefix = 'fresh/observations/' + phase + '/'
        plan, runs, checkpoint, specs = (read(root, prefix+n+'.json.gz')
                                        for n in ('plan','runs','checkpoint','specifications'))
        provenance = read(root, 'fresh/' + phase + '_provenance.json.gz')
        assert len(runs) == provenance['cases'] == len(plan['cases']) == count
        assert [e['specification'] for e in plan['cases']] == specs
        assert checkpoint['all_terminal'] and not checkpoint['verified_required_failure']
        assert checkpoint['completed_cases'] == checkpoint['expected_cases'] == count
        assert not checkpoint['failures'] and not checkpoint['execution_failures']
        assert provenance['all_verified'] and provenance['snapshot_sha256'] == index['snapshot_sha256']
        assert provenance['binary_sha256'] == index['binary_sha256']
        assert provenance['analysis_source_sha256'] == sha((root/'fresh/tools/verify_fresh_phase.py').read_bytes())
        phase_runs[phase] = runs
        for label, key in (('plan','plan_sha256'), ('runs','run_map_sha256'),
                           ('checkpoint','checkpoint_sha256'), ('specifications','registered_specifications_sha256')):
            assert sha(gzip.decompress((root/(prefix+label+'.json.gz')).read_bytes())) == provenance[key]
    expected_inputs = {phase+'/'+name+'/final.csv'
                       for phase,runs in phase_runs.items() for name in runs}
    for name, run in phase_runs['physics'].items():
        config = run['config']
        shock_primary = (config['case'] == 'brio-wu' and
            ((config['jitter'] == 0 and config['jitter_mode'] == 'planar') or
             (config['jitter'] == .15 and config['jitter_mode'] == 'columns')))
        vortex_primary = config['case'] == 'orszag-tang' and config['jitter'] == 0
        if shock_primary or vortex_primary:
            expected_inputs.add('physics/'+name+'/geometry.json')
        if vortex_primary:
            expected_inputs.add('physics/'+name+'/projected_bins.json')
    assert set(summary['raw_input_identities']) == expected_inputs
    for key, row in summary['raw_input_identities'].items():
        phase, name, filename = key.split('/')
        assert row['sha256'] == phase_runs[phase][name]['sha256'][filename], key
    verdict = read(root, 'fresh/registered_verdict.json.gz')
    assert verdict['snapshot_sha256'] == index['snapshot_sha256'] and verdict['binary_sha256'] == index['binary_sha256']
    assert verdict['all_registered_phase_checks_passed'] and not verdict['full_m1_accepted']
    assert len(verdict['phases']) == 7 and all(row['passed'] for row in verdict['phases'].values())
    wave = read(root, 'fresh/waves_independent.json.gz')
    wave_run_bytes = gzip.decompress((root/'fresh/wave_inputs/runs.json.gz').read_bytes())
    wave_manifest_bytes = gzip.decompress((root/'fresh/wave_inputs/manifest.json.gz').read_bytes())
    assert json.loads(wave_run_bytes) == phase_runs['waves']
    assert wave['run_map_sha256'] == sha(wave_run_bytes)
    assert wave['manifest_sha256'] == sha(wave_manifest_bytes)
    assert wave['recorded_runs'] == wave['manifest_runs'] == 112
    assert len(wave['pairs']) == 48 and all(p['passed'] for p in wave['pairs'].values())
    assert len(wave['spatial']) == 8 and all(p['status'] == 'pass' for p in wave['spatial'])
    assert len(wave['temporal']) == 12 and wave['reused_cases'] == wave['reused_pairs'] == 0
    for name in ('pending_cases','pending_pairs','pending_temporal','failed_runs','failed_pairs','failed_spatial'):
        assert not wave[name], name
    assert not wave['verified_required_failure']
    assert wave['analysis_source_sha256'] == sha((root/'fresh/tools/reduce_waves.py').read_bytes())
    for name, count in (('medium',24), ('mean',12), ('physics_boost',15)):
        report = read(root, 'fresh/' + name + '_independent.json.gz')
        assert len(report['pairs']) == count and report['all_passed']
        assert all(p['passed'] for p in report['pairs']) and not report['full_m1_accepted']
        phase = 'physics' if name == 'physics_boost' else name
        run_bytes = gzip.decompress((root/('fresh/observations/'+phase+'/runs.json.gz')).read_bytes())
        assert report['run_map_sha256'] == sha(run_bytes)
        script = 'reduce_mean.py' if name == 'mean' else 'reduce_boost_pairs.py'
        assert report['analysis_source_sha256'] == sha((root/'fresh/tools'/script).read_bytes())
    shock = read(root, 'fresh/shock/independent_reference.json.gz')
    vortex = read(root, 'fresh/vortex/independent_reference.json.gz')
    assert len(shock['measured']) == 12 and len(shock['reference_gates']) == 4 and shock['all_reference_gates_passed']
    assert len(vortex['measured']) == 6 and len(vortex['primary_reference_ladders']) == 2
    assert not vortex['missing_primary_cases'] and all(p['status']=='pass' for p in vortex['primary_reference_ladders'])
    primary_run_bytes = gzip.decompress((root/'fresh/physics_inputs/runs.json.gz').read_bytes())
    assert json.loads(primary_run_bytes) == phase_runs['physics']
    observed_bytes = gzip.decompress((root/'fresh/physics_inputs/observed_run_map.json.gz').read_bytes())
    assert json.loads(observed_bytes) == phase_runs['physics']
    for report, script, reference in ((shock,'reduce_shock.py','brio_8192.csv.gz'),
                                      (vortex,'reduce_vortex.py','vortex_512.csv.gz')):
        assert report['run_map_sha256'] == sha(primary_run_bytes)
        assert report['analysis_source_sha256'] == sha((root/'fresh/tools'/script).read_bytes())
        assert report['reference_sha256'] == sha((root/'frozen_source/tests/reference/external_mhd'/reference).read_bytes())
        assert report['packet_sha256'] == sha((root/'frozen_source/benchmarks/m0/packet.json').read_bytes())
        for key, digest in report['input_sha256'].items():
            assert summary['raw_input_identities']['physics/'+key]['sha256'] == digest
    print(json.dumps(dict(evidence_inventory_files=len(manifest), frozen_scientific_files=226,
        matrix_cases=214, independently_reduced_boost_pairs=99, raw_input_identities=238,
        evidence_integrity_passed=True, separate_final_review_required=True, full_m1_accepted=False), indent=1))


if __name__ == '__main__':
    main()
