"""Read-only integrity/consistency check of the provisional M1 review packet."""
import gzip
import hashlib
import json
from pathlib import Path
import re


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    data = path.read_bytes()
    return gzip.decompress(data) if path.suffix == '.gz' else data


def main():
    root = Path(__file__).resolve().parent
    manifest = json.loads((root/'archive_sha256.json').read_text())
    files = {str(path.relative_to(root)) for path in root.rglob('*')
             if path.is_file() and '__pycache__' not in path.parts
             and path != root/'archive_sha256.json'
             and ('review' not in path.relative_to(root).parts
                  or path == root/'review/review_sha256.json')}
    assert set(manifest) == files
    for name, digest in manifest.items():
        assert sha((root/name).read_bytes()) == digest, name
    # The separate review is an explicitly bounded subpacket. Its manifest
    # is pinned by the parent, and closes the inventory of every reviewer file.
    review = root/'review'
    review_manifest = json.loads((review/'review_sha256.json').read_text())
    review_files = {str(path.relative_to(review)) for path in review.rglob('*')
                    if path.is_file() and '__pycache__' not in path.parts
                    and path != review/'review_sha256.json'}
    assert set(review_manifest) == review_files
    for name, digest in review_manifest.items():
        assert sha((review/name).read_bytes()) == digest, name
    archive = root.parent/'m1_iterative_step_campaigns/iter/plans'
    reports = {}
    for label, phase, reducer in [
        ('waves', 'waves', 'reduce_waves.py'), ('medium', 'medium', 'reduce_boost_pairs.py'),
        ('mean', 'mean', 'reduce_mean.py'), ('physics_boost', 'physics', 'reduce_boost_pairs.py'),
        ('shock', 'physics', 'reduce_shock.py'), ('vortex', 'physics', 'reduce_vortex.py'),
    ]:
        path = root/f'campaign_a_independent_{label}.json'
        if not path.exists():
            path = path.with_suffix('.json.gz')
        report = json.loads(read(path))
        assert report['analysis_source_sha256'] == sha((root/reducer).read_bytes()), label
        assert report['run_map_sha256'] == sha(read(archive/f'iter-{phase}_runs.json.gz')), label
        reports[label] = report
    waves = reports['waves']
    assert len(waves['cases']) == waves['recorded_runs'] == waves['manifest_runs'] == 112
    assert all(row['state']['passed'] for row in waves['cases'].values())
    assert len(waves['pairs']) == 48 and all(row['passed'] for row in waves['pairs'].values())
    assert len(waves['spatial']) == 8 and all(row['status'] == 'pass' for row in waves['spatial'])
    assert len(waves['temporal']) == 12
    for key in ('pending_cases', 'pending_pairs', 'pending_temporal', 'failed_runs',
                'failed_pairs', 'failed_spatial'):
        assert not waves[key], key
    assert not waves['verified_required_failure'] and not waves['full_m1_accepted']
    for label, count in [('medium', 24), ('mean', 12), ('physics_boost', 15)]:
        report = reports[label]
        assert len(report['pairs']) == count and report['all_passed']
        assert all(row['passed'] for row in report['pairs']) and not report['full_m1_accepted']
    shock, vortex = reports['shock'], reports['vortex']
    assert len(shock['measured']) == 12 and len(shock['reference_gates']) == 4
    assert shock['all_reference_gates_passed']
    assert len(vortex['measured']) == 6 and len(vortex['primary_reference_ladders']) == 2
    assert all(row['status'] == 'pass' for row in vortex['primary_reference_ladders'])
    assert not vortex['missing_primary_cases']
    for label in ('medium', 'physics_boost'):
        assert reports[label]['wave_reducer_sha256'] == sha((root/'reduce_waves.py').read_bytes())
    applicable = json.loads((root/'prescribed_applicability_20261121.json').read_text())
    assert applicable['analysis_source_sha256'] == sha((root/'verify_prescribed_applicability.py').read_bytes())
    assert len(applicable['verified_archive_files']) == 12 and not applicable['full_m1_accepted']
    snapshot = read(root/'snapshot.json.gz')
    assert sha(snapshot) == 'b67ce03779a194099983b7ff07c0cafed23e9ea3a9051047492d072255e0160f'
    # Later prose and analysis changes may differ; the scientific source under
    # current-source REANA validation must retain the frozen file identities.
    frozen = json.loads(snapshot)
    repository = root.parents[2]
    count = 0
    for name, digest in frozen['source_sha256'].items():
        if name.startswith(('apps/', 'crates/', 'scripts/', 'benchmarks/', 'reana/')) or name in ('Cargo.toml', 'Cargo.lock'):
            assert sha((repository/name).read_bytes()) == digest, name
            count += 1
    report_record = json.loads((root/'review_report_sha256.json').read_text())
    assert sha((repository/'docs/M1_FINAL_AI_REVIEW.md').read_bytes()) == report_record['docs/M1_FINAL_AI_REVIEW.md']
    pre = root/'preflight'
    preflight = json.loads((pre/'preflight.json').read_text())
    execution = json.loads((pre/'execution.json').read_text())
    artifacts = json.loads((pre/'artifacts.sha256.json').read_text())
    assert execution['status'] == 'completed'
    assert preflight['snapshot_sha256'] == execution['snapshot_sha256'] == sha(snapshot)
    assert len(execution['commands']) == 8 and preflight['commands'] == execution['commands']
    assert all(row['returncode'] == 0 for row in execution['commands'])
    for name, digest in artifacts.items():
        assert name.startswith('outputs/')
        relative = name.removeprefix('outputs/')
        if relative == 'vector-potential':
            assert digest == preflight['binary_sha256']
        else:
            assert sha((pre/relative).read_bytes()) == digest, name
    for row in execution['commands']:
        assert sha((pre/row['log'].removeprefix('outputs/')).read_bytes()) == row['log_sha256']
    passes = lambda path: sum(int(value) for value in re.findall(
        r'test result: ok\. (\d+) passed;', path.read_text()))
    rust_counts = dict(debug=passes(pre/'logs/02.log'), release=passes(pre/'logs/07.log'))
    assert rust_counts == dict(debug=236, release=245)
    assert 'Ran 163 tests' in (pre/'logs/04.log').read_text()
    bounded = root/'fresh/bounded'
    bounded_read = lambda name: json.loads(read(bounded/(name+'.gz')))
    bounded_execution = bounded_read('execution.json')
    bounded_artifacts = bounded_read('artifacts.sha256.json')
    for name, digest in bounded_artifacts.items():
        assert name.startswith('outputs/')
        relative = name.removeprefix('outputs/')
        if relative == 'm1-iterative-bounded-raw.tar.gz':
            continue  # Original large raw archive retained remotely/locally.
        assert sha(read(bounded/(relative+'.gz'))) == digest, name
    assert bounded_execution['status'] == 'completed'
    assert bounded_execution['snapshot_sha256'] == sha(snapshot)
    assert len(bounded_execution['commands']) == 8
    assert all(row['returncode'] == 0 for row in bounded_execution['commands'])
    bounded_gate = bounded_read('m1-iterative-bounded/gate.json')
    assert bounded_gate['bounded_blockers_closed'] and bounded_gate['iterative_projection']
    assert bounded_gate['source_and_binary_unchanged'] and not bounded_gate['full_m1_accepted']
    assert [row['name'] for row in bounded_gate['stages']] == bounded_gate['stages_expected']
    assert len(bounded_gate['stages']) == 4
    assert all(row['status'] == 'pass' and all(row['checks'].values()) for row in bounded_gate['stages'])
    for name, digest in bounded_gate['provenance']['source_sha256'].items():
        assert frozen['source_sha256'][name] == digest, name
    fresh_cases = fresh_pairs = 0
    for phase, cases, pairs, reducer in (
        ('medium', 48, 24, 'reduce_boost_pairs.py'),
        ('mean', 24, 12, 'reduce_mean.py'),
    ):
        directory = root/'fresh'
        phase_read = lambda label: json.loads(read(directory/f'{phase}_{label}.json.gz'))
        provenance, independent = phase_read('provenance'), phase_read('independent')
        plan, runs, checkpoint = (phase_read(label) for label in ('plan', 'runs', 'checkpoint'))
        for label, key in (('plan', 'plan_sha256'), ('runs', 'run_map_sha256'),
                           ('checkpoint', 'checkpoint_sha256'),
                           ('specifications', 'registered_specifications_sha256')):
            assert provenance[key] == sha(read(directory/f'{phase}_{label}.json.gz'))
        assert provenance['analysis_source_sha256'] == sha((root/'verify_fresh_phase.py').read_bytes())
        assert provenance['all_verified'] and provenance['cases'] == len(runs) == cases
        assert provenance['snapshot_sha256'] == sha(snapshot)
        assert provenance['binary_sha256'] == preflight['binary_sha256']
        assert provenance['final_csv_byte_identical_to_campaign_a'] == cases
        assert [entry['specification'] for entry in plan['cases']] == phase_read('specifications')
        assert set(provenance['receipts']) == set(runs)
        assert checkpoint['all_terminal'] and not checkpoint['verified_required_failure']
        assert checkpoint['completed_cases'] == checkpoint['expected_cases'] == cases
        assert independent['analysis_source_sha256'] == sha((root/reducer).read_bytes())
        assert independent['run_map_sha256'] == provenance['run_map_sha256']
        assert independent['all_passed'] and len(independent['pairs']) == pairs
        assert all(row['passed'] for row in independent['pairs'])
        assert not independent['full_m1_accepted'] and not provenance['full_m1_accepted']
        fresh_cases += cases
        fresh_pairs += pairs
    print(json.dumps(dict(archived_files=len(manifest), independent_boost_pairs=99,
                          independent_wave_cases=112, primary_reference_cases=18,
                          reviewer_files=len(review_manifest), fresh_preflight_passed=True,
                          fresh_rust_test_counts=rust_counts, fresh_python_tests=163,
                          unchanged_frozen_scientific_files=count,
                          fresh_verified_cases=fresh_cases,
                          fresh_independent_boost_pairs=fresh_pairs,
                          fresh_bounded_stages=4,
                          packet_integrity_passed=True, full_m1_accepted=False), indent=1))


if __name__ == '__main__':
    main()
