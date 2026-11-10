"""Verify existing #21 evidence and unchanged derivative arithmetic; no new simulation/SVD."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def between(text, start, end):
    suffix = text[text.index(start):]
    return suffix[:suffix.index(end)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Use a fresh report path')
    archive = Path('tests/reference/m1_paper_audit')
    inputs = {}
    counts = {}
    for name, expected in json.loads((archive/'archive.json').read_text()).items():
        data = (archive/name).read_bytes()
        assert digest(data) == expected, name
        inputs[str(archive/name)] = expected
    for name, manifest, prefix in [('raw.tar.gz', 'raw_sha256.json', 'raw/'),
                                    ('retained_source.tar.gz', 'retained_source_sha256.json', '')]:
        expected = json.loads((archive/manifest).read_text())
        checked = {}
        with tarfile.open(archive/name) as bundle:
            for item in bundle:
                if item.isfile():
                    key = item.name.removeprefix(prefix)
                    checked[key] = digest(bundle.extractfile(item).read())
        assert checked == expected
        counts[name] = len(checked)
    with tarfile.open(archive/'raw.tar.gz') as bundle:
        original = json.load(bundle.extractfile('raw/rank.json'))
        rerun = json.load(bundle.extractfile('raw/rank_checked.json'))
    assert len(original['checks']) == len(rerun['checks']) == 24
    raw_hashes = json.loads((archive/'raw_sha256.json').read_text())
    rows = []
    for a, b in zip(original['checks'], rerun['checks']):
        assert all(a[key] == b[key] for key in
                   ('nx', 'ny', 'jitter', 'stencil', 'normal', 'rank', 'unknowns', 'input_sha256'))
        assert all(raw_hashes['matrices/'+name] == value for name, value in b['input_sha256'].items())
        if b['nx'] == 256 and b['jitter'] == .15 and b['normal'] == [1., 0.]:
            assert b['rank'] == b['unknowns'] == 1023
            keys = ('stencil', 'singular_min', 'rank_tolerance', 'backward_frobenius_residual',
                    'constant_annihilation_max', 'gauge_orthogonality_error',
                    'parallel_over_perpendicular_bound', 'maximum_parallel_RMS_if_normal_max_1e_8')
            row = {key: b[key] for key in keys}
            row['singular_min_over_tolerance'] = b['singular_min']/b['rank_tolerance']
            row['gain_relative_difference_between_reductions'] = abs(
                b['parallel_over_perpendicular_bound']/a['parallel_over_perpendicular_bound']-1)
            rows.append(row)
    assert len(rows) == 2
    with tarfile.open(archive/'retained_source.tar.gz') as bundle:
        unchanged = {}
        for name in ('scripts/check_symmetry_rank.py',
                     'crates/mhd-vector-pot/examples/symmetry-rank-probe.rs'):
            data = Path(name).read_bytes()
            assert data == bundle.extractfile(name).read()
            inputs[name] = digest(data)
            unchanged[name] = True
        name = 'crates/moving-mesh/src/lib.rs'
        old = bundle.extractfile(name).read().decode()
        new = Path(name).read_text()
        inputs[name] = digest(Path(name).read_bytes())
        for label, start, end in [('affine_fit', 'fn fit_derivatives(', '#[cfg(test)]'),
                                   ('effective_gradient', '    pub fn gradient(', '\n}\n')]:
            assert between(old, start, end) == between(new, start, end)
            unchanged[label] = True
        name = 'crates/moving-mesh/src/quadratic.rs'
        old = bundle.extractfile(name).read().decode()
        new = Path(name).read_text()
        inputs[name] = digest(Path(name).read_bytes())
        assert between(old, 'fn samples(', '\nfn basis(') == between(new, 'fn samples(', '\nfn basis(')
        assert between(old, '    let roots =', '    let result =') == between(new, '    let roots =', '    let gradient =')
        old_gradient = between(old, '    let result =', '    Ok((result, condition))').replace('let result =', 'let gradient =')
        assert old_gradient == between(new, '    let gradient =', '    let hessian =')
        unchanged['quadratic_samples_weighted_qr_and_gradient_coefficients'] = True
    primary = Path('tests/reference/m1_pressure_campaign/reuse_shock_reference/independent_reference.json')
    primary_report = json.loads(primary.read_text())
    assert primary_report['all_reference_gates_passed']
    assert len(primary_report['measured']) == 12 and len(primary_report['reference_gates']) == 4
    inputs[str(primary)] = digest(primary.read_bytes())
    bx = {name: row['final_Bx_max_error'] for name, row in primary_report['measured'].items()}
    assert all(value <= 1e-8 for value in bx.values())
    amendment = Path('benchmarks/m1/shock-bx-amendment.json')
    rule = json.loads(amendment.read_text())
    assert rule['bx_max_error'] == 1e-8 and rule['bx_gate_meshes'] == ['regular', 'columns']
    inputs[str(amendment)] = digest(amendment.read_bytes())
    packet = Path('benchmarks/m0/packet.json')
    inputs[str(packet)] = digest(packet.read_bytes())
    assert inputs[str(packet)] == primary_report['packet_sha256']
    retained_hashes = json.loads((archive/'retained_source_sha256.json').read_text())
    assert inputs[str(packet)] == retained_hashes[str(packet)]
    # Retained literal pressure failures are distinct from Bx disposition.
    short = Path('tests/reference/m1_pressure_campaign/reuse_short')
    report = dict(scope=__doc__, review_type='Implementing-assistant source/evidence review, not independent peer review.',
                  verification_script_sha256=digest(Path(__file__).read_bytes()),
                  input_sha256=inputs, archive_members_verified=counts,
                  matching_original_and_explicit_contraction_rank_records=24,
                  nx256_planar_x_normal=rows, unchanged_arithmetic=unchanged,
                  primary_shock_cases=12, primary_reference_ladders=4,
                  final_primary_Bx_errors=bx, maximum_primary_Bx_error=max(bx.values()),
                  approved_amendment_status=rule['status'],
                  paper_source='https://arxiv.org/html/2609.35989v1#S6.SS2',
                  pressure_failure_retained_in=str(short),
                  new_svd_or_evolution_executed=False, full_m1_accepted=False)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print('Verified archive members:', counts, '; matching rank records: 24; primary Bx cases: 12.')


if __name__ == '__main__':
    main()
