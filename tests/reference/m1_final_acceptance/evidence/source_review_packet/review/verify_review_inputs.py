"""Independent reviewer: read-only source/provenance and existing-data arithmetic.

No compilation, tests, numerical evolution, submission, or production reducer
imports. Outputs only the requested JSON file, which must not already exist.
Run from the repository root; all execution artifacts were produced on REANA.
The original packet's closed manifest excludes this added review directory.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import tarfile


REVISION = '2bdcea0d28340e7429e10053a641f92d51fcc696'
SNAPSHOT = 'b67ce03779a194099983b7ff07c0cafed23e9ea3a9051047492d072255e0160f'
ROOT = Path.cwd()
PACKET = ROOT / 'tests/reference/m1_acceptance'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def raw(path):
    value = path.read_bytes()
    return gzip.decompress(value) if path.suffix == '.gz' else value


def read(path):
    return json.loads(raw(path))


def inventory(directory):
    manifest = read(directory / 'archive_sha256.json')
    for name, expected in manifest.items():
        assert sha((directory / name).read_bytes()) == expected, name
    return dict(files=len(manifest), manifest_sha256=sha((directory / 'archive_sha256.json').read_bytes()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    assert not args.output.exists(), 'Use a fresh output'
    result = dict(kind='Independent AI reviewer, existing-data analysis only',
                  reviewed_revision=REVISION,
                  current_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  analysis_source_sha256=sha(Path(__file__).read_bytes()),
                  provisional_packet=inventory(PACKET),
                  iterative_archive=inventory(ROOT / 'tests/reference/m1_iterative_step_campaigns'))
    snap_bytes = raw(PACKET / 'snapshot.json.gz')
    assert sha(snap_bytes) == SNAPSHOT
    frozen = json.loads(snap_bytes)
    scientific = {}
    for name, expected in frozen['source_sha256'].items():
        if name.startswith(('apps/', 'crates/', 'scripts/', 'benchmarks/', 'reana/')) or name in ('Cargo.toml', 'Cargo.lock'):
            content = (ROOT / name).read_bytes()
            assert sha(content) == expected, name
            versioned = subprocess.check_output(['git', 'show', REVISION + ':' + name])
            assert content == versioned, name
            scientific[name] = expected
    result['frozen_scientific_source_sha256'] = scientific
    result['snapshot_sha256'] = SNAPSHOT
    name = 'rust-toolchain.toml'
    assert sha((ROOT/name).read_bytes()) == frozen['source_sha256'][name]
    assert (ROOT/name).read_bytes() == subprocess.check_output(['git', 'show', REVISION+':'+name])
    result['rust_toolchain_sha256'] = frozen['source_sha256'][name]

    pre = ROOT / 'results/reana_remote_m1_final_preflight_20261121'
    preflight = read(pre / 'outputs/preflight.json')
    execution = read(pre / 'outputs/execution.json')
    artifacts = read(pre / 'outputs/artifacts.sha256.json')
    for name, expected in artifacts.items():
        assert sha((pre / name).read_bytes()) == expected, name
    assert execution['status'] == 'completed'
    assert preflight['snapshot_sha256'] == execution['snapshot_sha256'] == SNAPSHOT
    assert execution['commands'] == preflight['commands']
    for row in preflight['commands']:
        assert row['returncode'] == 0
        assert sha((pre / row['log']).read_bytes()) == row['log_sha256']
    assert sha((pre / 'outputs/vector-potential').read_bytes()) == preflight['binary_sha256']
    logs = [(pre / ('outputs/logs/%02d.log' % i)).read_text() for i in range(8)]
    passed = lambda text: sum(int(n) for n in re.findall(r'test result: ok\. (\d+) passed;', text))
    required = [
        'fused_gradients_and_limiters_repeat_the_scalar_ones_bit_for_bit',
        'fused_gradients_equal_the_component_path_bit_for_bit',
        'ordered_pruning_is_bit_identical_to_all_pairs_clipping',
        'incremental_polygon_repeats_the_reference_clip_bit_for_bit',
        'threaded_geometry_and_operators_match_serial_bits',
        'comoving_loop_preserves_discrete_a_b_on_irregular_cells',
        'fixed_transport_is_boost_covariant_and_converges_for_both_signs',
    ]
    for name in required:
        for index in (2, 7):
            assert re.search(r'test (?:\S*::)?' + name + r' \.\.\. ok', logs[index]), name
    assert 'Ran 163 tests' in logs[4] and '\nOK\n' in logs[4]
    result['fresh_preflight'] = dict(binary_sha256=preflight['binary_sha256'],
        artifacts=len(artifacts), artifact_manifest_sha256=sha((pre/'outputs/artifacts.sha256.json').read_bytes()),
        execution_sha256=sha((pre/'outputs/execution.json').read_bytes()),
        receipt_sha256=sha((pre/'outputs/preflight.json').read_bytes()),
        all_eight_commands_passed=True, commands=preflight['commands'],
        debug_rust_passes=passed(logs[2]), release_rust_passes=passed(logs[7]),
        python_passes=163, m0_algebra_passes=13, applicability_test_names=required,
        ended_utc=execution['ended_utc'])

    phase_results = {}
    for phase, count in [('medium', 48), ('mean', 24), ('physics', 30), ('waves', 112)]:
        directory = ROOT / ('results/followup_iter-' + phase + '_20261117')
        archive = ROOT / 'tests/reference/m1_iterative_step_campaigns/iter/plans'
        for filename in ('runs', 'plan', 'checkpoint'):
            assert (directory/(filename+'.json')).read_bytes() == raw(archive/('iter-'+phase+'_'+filename+'.json.gz'))
        runs = read(directory/'runs.json')
        plan = read(directory/'plan.json')
        entries = {r['specification']['config']['name']: r for r in plan['cases']}
        assert len(entries) == len(runs) == count and set(entries) == set(runs)
        input_hashes, counters = {}, {k: 0 for k in ('steps', 'rejected_geometry', 'rejected_state', 'rejected_cfl', 'hll_fallbacks')}
        maximum_budget = 0.
        diagnostic_maxima = {}
        for name, run in runs.items():
            entry = entries[name]
            assert entry['specification']['config'] == run['config']
            assert entry['specification']['options'] == dict(accelerated_projection=False, projection_screening=1., potential_limiter='smooth-extrema')
            assert entry['specification']['resources']['threads'] in (2, 4)
            assert run['status'] == 'completed' and run['returncode'] == 0
            summary = run['summary']
            assert summary['completed'] and summary['profile'] == 'bulk-frame-heun-quadratic-v1'
            assert summary['potential_limiter'] == 'smooth-extrema-v1'
            assert summary['riemann_solver'] == 'hlld-pressure-blend-v1'
            assert summary['projection_screening'] == 1.
            assert 'projection_solver' not in summary and 'trial_step_fraction' not in summary
            assert '--accelerated-projection' not in run['command'] and '--trial-step-fraction' not in run['command']
            receipt_path = directory/'download'/entry['directory']/'outputs/execution.json'
            receipt = read(receipt_path)
            assert receipt['status'] == 'completed' and receipt['single_case_gates_passed']
            assert receipt['snapshot_sha256'] == plan['snapshot_sha256']
            assert receipt['binary_sha256'] == '492b56e0b8f70519ac950f9f49c889dbaf462e97732eaf12e9be86f593ea8471'
            assert receipt['case'] == entry['specification']
            assert receipt['payload_sha256'] == entry['payload_sha256']
            record_path = receipt_path.parent/'record.json'
            assert receipt['record_sha256'] == sha(record_path.read_bytes())
            assert read(record_path) == run
            data_path = directory/'raw'/name/'final.csv'
            assert sha(data_path.read_bytes()) == run['sha256']['final.csv']
            input_hashes[name] = dict(final_csv=run['sha256']['final.csv'], execution_json=sha(receipt_path.read_bytes()))
            history = run['history']
            for record in history:
                d = record['diagnostics']
                assert d['rho_min'] > 0 and d['p_min'] > 0
                budget = max(abs(x) for x in d['normalized_budget'])
                assert math.isfinite(budget) and budget <= 1e-10
                maximum_budget = max(maximum_budget, budget)
            if phase == 'physics':
                assert run['state_and_diagnostic_gates'] and all(run['diagnostic_checks'].values())
                for key, value in run['diagnostic_values'].items():
                    if isinstance(value, (int, float)):
                        diagnostic_maxima[key] = max(diagnostic_maxima.get(key, 0.), value)
            for key in counters:
                counters[key] += summary[key]
        phase_results[phase] = dict(cases=count, input_sha256=input_hashes, counters=counters,
                                   maximum_recorded_budget=maximum_budget, diagnostic_maxima=diagnostic_maxima)
    result['campaign_a'] = phase_results

    wave = read(PACKET/'campaign_a_independent_waves.json.gz')
    fits = []
    for row in wave['spatial']:
        x = [math.log(1/n) for n in (64, 128, 256)]
        y = [math.log(e) for e in row['B_L1'][1:]]
        xm, ym = sum(x)/3, sum(y)/3
        xx = sum((v-xm)**2 for v in x)
        order = sum((a-xm)*(b-ym) for a, b in zip(x, y))/xx
        se = math.sqrt(sum((b-ym-order*(a-xm))**2 for a, b in zip(x, y))/xx)
        assert abs(order-row['finest_three_order']) < 1e-13
        assert abs(se-row['residual_based_order_standard_error']) < 1e-13
        assert order >= 1.8 and row['B_L1'][-1]/.1 <= .02
        fits.append(dict(jitter=row['jitter'], parallel=row['parallel'], motion=row['motion'],
                         order=order, residual_standard_error=se, finest_relative_B_L1=row['B_L1'][-1]/.1))
    result['independently_refitted_wave_ladders'] = fits
    result['temporal_observations'] = wave['temporal']

    prescribed = ROOT/'tests/reference/m1_completion/prescribed'
    result['prescribed_archive'] = inventory(prescribed)
    historical = read(prescribed/'summary.json.gz')
    assert len(historical['runs']) == 32 and all(r['status'] == 'completed' and r['returncode'] == 0 for r in historical['runs'].values())
    assert len(historical['pairs']) == 16 and all(r['status'] == 'pass' for r in historical['pairs'])
    comoving = [r for r in historical['runs'].values() if r['config']['motion'] == 'comoving']
    assert len(comoving) == 16 and all(r['comoving_gate'] == 'pass' for r in comoving)
    assert len(historical['fixed_convergence']) == 2
    for ladder in historical['fixed_convergence']:
        values = ladder['rows']
        assert ladder['gate'] == 'pass' and [r['n'] for r in values] == [32, 64, 128, 256]
        assert all(r['status'] == 'completed' for r in values)
        assert all(a['A_L1_over_peak'] > b['A_L1_over_peak'] for a, b in zip(values, values[1:]))
        assert values[-1]['A_L1_over_peak'] <= .1
    measured = dict(completed=32, boost_pairs_pass=16, comoving_pass=16, refinement_pass=2)
    assert measured == read(prescribed/'applicability_20261110.json')['historical_results']
    result['prescribed_historical_results'] = measured
    result['prescribed_fixed_convergence'] = historical['fixed_convergence']
    comparison = {}
    paths = ['apps/openmhd/src/bin/prescribed-loop.rs', 'crates/mhd-vector-pot/src/transport.rs',
             'crates/mhd-vector-pot/src/diagnostics.rs', 'crates/mhd-vector-pot/src/operators.rs',
             'crates/moving-mesh/src/lib.rs']
    with tarfile.open(prescribed/'execution_sources.tar.gz') as archive:
        for name in paths:
            old = archive.extractfile(name).read()
            new = (ROOT/name).read_bytes()
            if name in paths[:3]:
                assert old == new
            comparison[name] = dict(archived_sha256=sha(old), current_sha256=sha(new), unchanged=old == new)
        old = archive.extractfile(paths[3]).read().decode()
        new = (ROOT/paths[3]).read_text()
        def fragment(text, start, end):
            return text.split(start, 1)[1].split(end, 1)[0]
        assert fragment(old, 'pub(crate) struct TransportStencil', 'pub(crate) struct PotentialStage') == fragment(new, 'pub(crate) struct TransportStencil', 'pub(crate) struct PotentialStage')
        old = archive.extractfile(paths[4]).read().decode()
        new = (ROOT/paths[4]).read_text()
        assert fragment(old, 'fn fit_derivatives(', '#[cfg(test)]') == fragment(new, 'fn fit_derivatives(', '#[cfg(test)]')
        name = 'crates/mhd-vector-pot/src/benchmarks.rs'
        old = archive.extractfile(name).read().decode().split('#[cfg(test)]', 1)[0]
        new = (ROOT/name).read_text().split('/// M0 periodic Brio-Wu embedding', 1)[0]
        assert old == new
        result['prescribed_loop_reference_prefix_sha256'] = sha(old.encode())
    result['prescribed_source_comparison'] = comparison
    result['full_m1_accepted'] = False
    args.output.write_text(json.dumps(result, indent=1, allow_nan=False)+'\n')
    print(json.dumps(dict(frozen_scientific_files=len(scientific), fresh_preflight=result['fresh_preflight'],
                          campaign_a_cases=sum(r['cases'] for r in phase_results.values()),
                          archive_integrity=True, full_m1_accepted=False), indent=1))


if __name__ == '__main__':
    main()
