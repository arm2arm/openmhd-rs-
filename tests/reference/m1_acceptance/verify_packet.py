"""Read-only integrity/consistency check of the provisional M1 review packet."""
import gzip
import hashlib
import json
from pathlib import Path


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
             and path.name != 'archive_sha256.json'}
    assert set(manifest) == files
    for name, digest in manifest.items():
        assert sha((root/name).read_bytes()) == digest, name
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
    print(json.dumps(dict(archived_files=len(manifest), independent_boost_pairs=99,
                          independent_wave_cases=112, primary_reference_cases=18,
                          unchanged_frozen_scientific_files=count,
                          packet_integrity_passed=True, full_m1_accepted=False), indent=1))


if __name__ == '__main__':
    main()
