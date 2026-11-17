"""Independent incremental reduction of frozen physical wave/loop results; no evolution."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(value):
    return sha(json.dumps(value, sort_keys=True, allow_nan=False).encode())


def load_cells(raw, name, run):
    path = raw/name/'final.csv'
    if not path.exists():
        raise ValueError('Missing observation: '+str(path))
    assert sha(path.read_bytes()) == run['sha256']['final.csv'], name
    data = np.genfromtxt(path, names=True, delimiter=',')
    config = run['config']
    assert len(data) == config['n']**2
    assert np.array_equal(data['id'], np.arange(len(data)))
    assert all(np.isfinite(data[field]).all() for field in data.dtype.names)
    assert (data['time'] == config['target']).all()
    assert all((data[field] > 0).all() for field in ('volume', 'rho', 'p'))
    assert abs(math.fsum(data['volume'])-1.) < 1e-10
    return data


def norms(data, delta):
    volume = math.fsum(data['volume'])
    return dict(L1=math.fsum(data['volume']*abs(delta))/volume,
                L2=math.sqrt(math.fsum(data['volume']*delta**2)/volume),
                max=float(max(abs(delta))))


def vector(data, fields):
    return np.array([data[field] for field in fields])


def state_check(run):
    summary, config, history = run['summary'], run['config'], run['history']
    assert summary['completed'] and summary['time'] == config['target'] == 1.
    assert config['profile'] == summary['profile'] == 'bulk-frame-heun-quadratic-v1'
    assert config['riemann_solver'] == 'hlld-pressure'
    assert summary['riemann_solver'] == 'hlld-pressure-blend-v1'
    assert summary['projection_screening'] == 1.
    assert history[0]['time'] == 0. and history[-1]['time'] == 1.
    assert all(a['time'] < b['time'] for a, b in zip(history, history[1:]))
    assert history[0]['diagnostics'] == summary['initial']
    assert history[-1]['diagnostics'] == summary['final']
    diagnostics = [row['diagnostics'] for row in history]
    assert all(len(row['normalized_budget']) == 5 and
               all(math.isfinite(value) for value in
                   (row['rho_min'], row['p_min'], *row['normalized_budget']))
               for row in diagnostics)
    rho, pressure = min(row['rho_min'] for row in diagnostics), min(row['p_min'] for row in diagnostics)
    budget = max(abs(value) for row in diagnostics for value in row['normalized_budget'])
    assert all(math.isfinite(x) for x in (rho, pressure, budget))
    passed = rho > 0 and pressure > 0 and budget <= 1e-10
    assert passed == run['positive_and_conservative']
    return dict(minimum_recorded_density=rho, minimum_recorded_pressure=pressure,
                maximum_recorded_budget=budget, passed=passed)


def analytic_wave(data, config):
    phase = math.tau*(data['x']+(1-config['parallel']-config['boost'][0])*config['target'])
    by, bz = .1*np.sin(phase), .1*np.cos(phase)
    expected = dict(bx=np.ones(len(data)), by=by, bz=bz,
                    vx=np.full(len(data), config['parallel']+config['boost'][0]),
                    vy=by+config['boost'][1], vz=bz+config['boost'][2])
    result = {field: norms(data, data[field]-value) for field, value in expected.items()}
    for label, fields in (('B', ('bx', 'by', 'bz')), ('v', ('vx', 'vy', 'vz'))):
        result[label] = norms(data, np.sqrt(sum((data[field]-expected[field])**2 for field in fields)))
    return result


def boost_pair(raw, names, runs):
    a, b = (runs[name] for name in names)
    config = a['config']
    assert config['boost'] == [0., 0., 0.] and b['config']['boost'] == [2., -1., 0.]
    for key in ('case', 'profile', 'n', 'jitter', 'parallel', 'motion_family', 'dt', 'target', 'riemann_solver'):
        assert config[key] == b['config'][key], key
    x, y = (load_cells(raw, name, runs[name]) for name in names)
    boost = np.array(b['config']['boost'])
    velocity = vector(y, ('vx', 'vy', 'vz'))-boost[:, None]
    energy = y['energy']-y['rho']*sum(y[field]*value for field, value in zip(('vx', 'vy', 'vz'), boost))+.5*y['rho']*sum(boost**2)
    errors = {field: norms(x, y[field]-x[field]) for field in ('rho', 'p')}
    errors['energy'] = norms(x, energy-x['energy'])
    errors['B'] = norms(x, np.sqrt(np.sum((vector(y, ('bx', 'by', 'bz'))-vector(x, ('bx', 'by', 'bz')))**2, axis=0)))
    errors['v'] = norms(x, np.sqrt(np.sum((velocity-vector(x, ('vx', 'vy', 'vz')))**2, axis=0)))
    position = max(float(max(abs((y[field]-x[field]-value*config['target']+.5) % 1-.5)))
                   for field, value in zip(('x', 'y'), boost))
    volume = float(max(abs(y['volume']/x['volume']-1)))
    if config['case'] == 'loop':
        conventions = {'loop_amplitude': {'B': .001/math.sqrt(4*math.pi)}}
        limit = .001
    else:
        common = dict(rho=1., p=.1, energy=.66+.5*config['parallel']**2)
        conventions = dict(wave_amplitude=dict(common, B=.1, v=.1),
                           mean_field_and_initial_speed=dict(common, B=1., v=max(math.sqrt(config['parallel']**2+.01), math.sqrt(1/6))))
        limit = 1e-8
    relative = {label: {field: errors[field]['L1']/scale for field, scale in scales.items()}
                for label, scales in conventions.items()}
    passed = (all(max(values.values()) <= limit for values in relative.values())
              and position <= 1e-11 and volume <= 1e-11
              and all(row['positive_and_conservative'] for row in (a, b)))
    return dict(names=names, case=config['case'], n=config['n'], relative_L1=relative,
                limit=limit, position_max=position, relative_volume_max=volume, passed=passed)


def temporal_pair(raw, name, reference, runs):
    run, ref = runs[name], runs[reference]
    for key in ('case', 'profile', 'n', 'jitter', 'parallel', 'motion_family',
                'mesh_velocity', 'boost', 'target', 'riemann_solver'):
        assert run['config'][key] == ref['config'][key], key
    assert run['config']['n'] == 64 and run['config']['dt'] in (.0004, .0002, .0001)
    assert ref['config']['dt'] == .000025
    a, b = load_cells(raw, name, run), load_cells(raw, reference, ref)
    errors = {field: norms(b, a[field]-b[field]) for field in ('bx', 'by', 'bz', 'ax', 'ay', 'az', 'phi')}
    errors['B'] = norms(b, np.sqrt(np.sum((vector(a, ('bx', 'by', 'bz'))-vector(b, ('bx', 'by', 'bz')))**2, axis=0)))
    assert max(float(max(abs(a[field]-b[field]))) for field in ('x', 'y', 'volume')) <= 1e-11
    summary, dt = run['summary'], run['config']['dt']
    return dict(name=name, reference=reference, dt=dt, errors=errors,
                actual_dt_max=summary['dt_max'], actual_dt_min=summary['dt_min'],
                cap_reached=math.isclose(summary['dt_max'], dt, rel_tol=1e-10, abs_tol=1e-15),
                steps=summary['steps'], rejected_state=summary['rejected_state'], rejected_cfl=summary['rejected_cfl'],
                reference_timesteps={key: ref['summary'][key] for key in
                                     ('dt_cap', 'dt_min', 'dt_max', 'steps', 'rejected_state', 'rejected_cfl')})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    run_bytes = (args.raw/'runs.json').read_bytes()
    manifest_bytes = (args.raw/'manifest.json').read_bytes()
    runs, manifest = json.loads(run_bytes), json.loads(manifest_bytes)
    assert set(runs) <= set(manifest)
    source_hash = sha(Path(__file__).read_bytes())
    cache = json.loads(args.output.read_text()) if args.output.exists() else {}
    if cache.get('analysis_source_sha256') != source_hash:
        cache = {}
    case_results, pair_results, temporal_results = {}, {}, {}
    failed_runs, failed_pairs, pending_pairs = [], [], []
    reused_cases = reused_pairs = 0
    for name, run in runs.items():
        assert run['config'] == manifest[name]
        if run['status'] != 'completed':
            failed_runs.append(dict(name=name, status=run['status'], error=run.get('error')))
            continue
        input_hash = fingerprint(run)
        path = args.raw/name/'final.csv'
        if not path.exists():
            raise ValueError('Missing observation: '+str(path))
        assert sha(path.read_bytes()) == run['sha256']['final.csv']
        cached = cache.get('cases', {}).get(name, {})
        if cached.get('run_record_sha256') == input_hash:
            result = cached
            reused_cases += 1
        else:
            state = state_check(run)
            result = dict(run_record_sha256=input_hash, state=state)
            if state['passed'] and run['config']['case'] == 'alfven':
                values = analytic_wave(load_cells(args.raw, name, run), run['config'])
                disagreement = max(abs(values[field][norm]-run['errors']['final'][field][norm])
                                   for field in values for norm in ('L1', 'L2', 'max'))
                assert disagreement < 2e-13, (name, disagreement)
                result.update(analytic_errors=values, maximum_production_error_difference=disagreement)
        case_results[name] = result
        if not result['state']['passed']:
            failed_runs.append(dict(name=name, status='failed state/budget gate', values=result['state']))
    for name in manifest:
        if not name.endswith('_base'):
            continue
        other = name.removesuffix('_base')+'_boost'
        names = [name, other]
        assert other in manifest
        if not all(n in case_results and case_results[n]['state']['passed'] for n in names):
            pending_pairs.append(names)
            continue
        inputs = [case_results[n]['run_record_sha256'] for n in names]
        cached = cache.get('pairs', {}).get(name, {})
        if cached.get('run_record_sha256') == inputs:
            result = cached
            reused_pairs += 1
        else:
            result = boost_pair(args.raw, names, runs)
            result['run_record_sha256'] = inputs
        pair_results[name] = result
        if not result['passed']:
            failed_pairs.append(name)
    spatial = []
    for jitter in (0., .15):
        for parallel in (0., 1.):
            for motion in ('fixed', 'comoving'):
                prefix = f'alfven_bulk-frame-heun-quadratic-v1_v{parallel}_j{jitter}_{motion}'
                names = [f'{prefix}_n{n}_base' for n in (32, 64, 128, 256)]
                row = dict(jitter=jitter, parallel=parallel, motion=motion, names=names, status='pending')
                if all(name in case_results and 'analytic_errors' in case_results[name] for name in names):
                    errors = [case_results[name]['analytic_errors']['B']['L1'] for name in names]
                    assert all(error > 0 and math.isfinite(error) for error in errors)
                    # For the three equally log-spaced resolutions, the least-
                    # squares slope equals this endpoint difference. The middle
                    # point contributes to the residual, not the fitted slope.
                    order = math.log(errors[1]/errors[3])/math.log(4)
                    x = np.log(np.array([1/64, 1/128, 1/256]))
                    y = np.log(np.array(errors[1:]))
                    residual = float(np.sum((y-y.mean()-order*(x-x.mean()))**2))
                    uncertainty = math.sqrt(residual/float(np.sum((x-x.mean())**2)))
                    relative = errors[-1]/.1
                    row.update(B_L1=errors, finest_three_order=order,
                               residual_based_order_standard_error=uncertainty,
                               finest_relative_B_L1=relative,
                               status='pass' if order >= 1.8 and relative <= .02 else 'fail')
                spatial.append(row)
    pending_temporal = []
    for name, config in manifest.items():
        if not name.startswith('temporal_') or config['dt'] == .000025:
            continue
        reference = name.rsplit('_dt', 1)[0]+'_dt2.5e-05'
        assert reference in manifest
        if not all(n in case_results and case_results[n]['state']['passed'] for n in (name, reference)):
            pending_temporal.append(name)
            continue
        inputs = [case_results[n]['run_record_sha256'] for n in (name, reference)]
        cached = cache.get('temporal', {}).get(name, {})
        if cached.get('run_record_sha256') == inputs:
            result = cached
        else:
            result = temporal_pair(args.raw, name, reference, runs)
            result['run_record_sha256'] = inputs
        temporal_results[name] = result
    for reference in {row['reference'] for row in temporal_results.values()}:
        group = sorted([row for row in temporal_results.values() if row['reference'] == reference],
                       key=lambda row: row['dt'], reverse=True)
        for left, right in zip(group, group[1:]):
            right['orders_from_previous_dt'] = {
                field: math.log(left['errors'][field]['L1']/right['errors'][field]['L1'])/math.log(left['dt']/right['dt'])
                if left['errors'][field]['L1'] > 0 and right['errors'][field]['L1'] > 0 else None
                for field in right['errors']}
    failed_spatial = [row for row in spatial if row['status'] == 'fail']
    report = dict(scope='Independent incremental raw-snapshot analysis. Missing observations raise separately from scientific failures; incomplete ladders remain pending. Recorded history extrema and budgets are checked, but the evolution/operators are not independently rerun. Temporal orders are observations with no invented threshold. This never certifies full M1.',
                  analysis_source_sha256=source_hash, numpy=np.__version__,
                  run_map_sha256=sha(run_bytes), manifest_sha256=sha(manifest_bytes),
                  recorded_runs=len(runs), manifest_runs=len(manifest),
                  cases=case_results, pairs=pair_results, spatial=spatial, temporal=temporal_results,
                  reused_cases=reused_cases, reused_pairs=reused_pairs,
                  pending_cases=sorted(set(manifest)-set(runs)), pending_pairs=pending_pairs,
                  pending_temporal=pending_temporal, failed_runs=failed_runs,
                  failed_pairs=failed_pairs, failed_spatial=failed_spatial,
                  verified_required_failure=bool(failed_runs or failed_pairs or failed_spatial), full_m1_accepted=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print('Recorded:', len(runs), '/', len(manifest), 'pairs:', len(pair_results),
          'spatial pass/pending:', sum(row['status'] == 'pass' for row in spatial), '/', sum(row['status'] == 'pending' for row in spatial),
          'temporal:', len(temporal_results), 'required failure:', report['verified_required_failure'],
          'reused cases/pairs:', reused_cases, '/', reused_pairs)
    if report['verified_required_failure']:
        print(json.dumps(dict(failed_runs=failed_runs, failed_pairs=failed_pairs, failed_spatial=failed_spatial), indent=2))


if __name__ == '__main__':
    main()
