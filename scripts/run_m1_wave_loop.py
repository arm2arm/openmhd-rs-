#!/usr/bin/env python3
"""Issue #7 preregistered mean-field and physical benchmark studies (stdlib only)."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ('paper-global-v2', 'bulk-frame-v1', 'bulk-frame-signal-v1')
PHYSICAL_PROFILES = PROFILES + ('bulk-frame-heun-v1', 'bulk-frame-heun-spline-v1',
                                'bulk-frame-heun-projected-v1', 'bulk-frame-heun-quadratic-v1')
PROJECTED_PROFILES = PHYSICAL_PROFILES[-2:]
BOOST = (2., -1., 0.)
FIELDS = ('rho', 'p', 'vx', 'vy', 'vz', 'bx', 'by', 'bz', 'energy')



RIEMANN_SOLVERS = ('hlld', 'hll', 'hlld-shock', 'hlld-pressure')
RIEMANN_METADATA = {'hlld':'hlld','hll':'hll-comparator-v1','hlld-shock':'hlld-shock-sensor-v1','hlld-pressure':'hlld-pressure-blend-v1'}
HLL_PROFILE = 'bulk-frame-heun-quadratic-v1'


def with_riemann(configs, solver):
    """Explicit execution configuration; historical default manifests stay intact."""
    if solver not in RIEMANN_SOLVERS:
        raise ValueError('Unknown Riemann solver')
    if solver == 'hlld':
        return configs
    if any(c['profile'] != HLL_PROFILE for c in configs.values()):
        raise ValueError('Explicit flux comparator requires the quadratic candidate')
    return {n: dict(c, riemann_solver=solver) for n, c in configs.items()}


def riemann_arguments(config):
    solver = config.get('riemann_solver', 'hlld')
    with_riemann({'run': config}, solver)  # Validate the allowed profile/choice.
    return ['--riemann', solver] if solver != 'hlld' else []


def riemann_matches(config, summary):
    try:
        riemann_arguments(config)
    except (ValueError, KeyError):
        return False
    expected = RIEMANN_METADATA[config.get('riemann_solver','hlld')]
    return summary.get('riemann_solver', 'hlld') == expected


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def read_cells(path):
    with path.open() as stream:
        cells = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(stream)]
    if not cells or any(not math.isfinite(v) for r in cells for v in r.values()):
        raise ValueError(f'empty/nonfinite cells: {path}')
    if [r['id'] for r in cells] != list(range(len(cells))):
        raise ValueError('persistent IDs lost')
    if any(r['volume'] <= 0 for r in cells):
        raise ValueError('nonpositive cell volume')
    return cells


def read_snapshot(path, n, time):
    """Validate the complete unit-square snapshot against execution configuration."""
    cells = read_cells(path)
    if len(cells) != n*n:
        raise ValueError(f'snapshot cell count {len(cells)} != {n*n}: {path}')
    if abs(math.fsum(c['volume'] for c in cells)-1.) > 1e-9:
        raise ValueError(f'snapshot domain volume != 1: {path}')
    if any(c['time'] != time for c in cells):
        raise ValueError(f'snapshot time != {time}: {path}')
    return cells


def norms(values, cells):
    if not cells or len(values) != len(cells):
        raise ValueError('norm requires one value per cell')
    if any(c['volume'] <= 0 or not math.isfinite(c['volume']) for c in cells) or any(not math.isfinite(v) for v in values):
        raise ValueError('norm requires finite values and positive volumes')
    volume = sum(c['volume'] for c in cells)
    return {'L1': sum(c['volume']*abs(e) for c, e in zip(cells, values))/volume,
            'L2': math.sqrt(sum(c['volume']*e*e for c, e in zip(cells, values))/volume),
            'max': max(map(abs, values))}


def physical_errors(cells, t, case, parallel, boost):
    """Alfven is exact coupled physics; loop transport is a passive comparison only."""
    errors = {k: [] for k in ('B', 'v', 'bx', 'by', 'bz', 'vx', 'vy', 'vz')} if case == 'alfven' else {'passive_A': [], 'passive_B': []}
    b_cells = []
    for c in cells:
        if case == 'alfven':
            phase = math.tau*(c['x']+(1-parallel-boost[0])*t)
            transverse = [.1*math.sin(phase), .1*math.cos(phase)]
            b = [1., *transverse]
            v = [parallel+boost[0], transverse[0]+boost[1], transverse[1]+boost[2]]
            errors['B'].append(math.sqrt(sum((c[k]-e)**2 for k, e in zip(('bx', 'by', 'bz'), b))))
            errors['v'].append(math.sqrt(sum((c[k]-e)**2 for k, e in zip(('vx', 'vy', 'vz'), v))))
            for k,e in zip(('bx','by','bz','vx','vy','vz'), b+v):
                errors[k].append(c[k]-e)
        else:
            dx = (c['x']-(2+boost[0])*t) % 1 - .5
            dy = (c['y']-(1+boost[1])*t) % 1 - .5
            radius = math.hypot(dx, dy)
            amplitude = .001/math.sqrt(4*math.pi)
            errors['passive_A'].append(c['az']-amplitude*max(0., .3-radius))
            # Derivative undefined at the cusp/edge: exclude, don't use a zero placeholder.
            if radius > 1e-12 and abs(radius-.3) > 1e-12:
                b = [-amplitude*dy/radius, amplitude*dx/radius, 0.] if radius < .3 else [0.]*3
                errors['passive_B'].append(math.sqrt(sum((c[k]-e)**2 for k, e in zip(('bx', 'by', 'bz'), b))))
                b_cells.append(c)
    result = {k: norms(v, b_cells if k == 'passive_B' else cells) for k, v in errors.items()}
    if case == 'loop':
        result['passive_B_excluded_cells'] = len(cells)-len(b_cells)
        result['reference_scope'] = 'passive diagnostic, not an exact coupled-MHD solution'
    return result


def boost_error(base, boosted, t):
    if len(base) != len(boosted):
        raise ValueError('boost pair cell count mismatch')
    transformed = []
    positions = []
    for a, b in zip(base, boosted):
        row = dict(b)
        for k, shift in zip(('vx', 'vy', 'vz'), BOOST):
            row[k] -= shift
        row['energy'] = b['energy']-b['rho']*sum(b[k]*shift for k, shift in zip(('vx', 'vy', 'vz'), BOOST)) + .5*b['rho']*sum(x*x for x in BOOST)
        transformed.append(row)
        positions.append(max(abs((b[k]-a[k]-shift*t+.5) % 1-.5) for k, shift in zip(('x', 'y'), BOOST)))
    result = {k: norms([b[k]-a[k] for a, b in zip(base, transformed)], base) for k in FIELDS}
    for label, keys in [('B', ('bx', 'by', 'bz')), ('v', ('vx', 'vy', 'vz'))]:
        result[label] = norms([math.sqrt(sum((b[k]-a[k])**2 for k in keys)) for a, b in zip(base, transformed)], base)
    result['position_max'] = max(positions)
    result['volume_max'] = max(abs(a['volume']-b['volume']) for a, b in zip(base, boosted))
    result['relative_volume_max'] = max(abs(a['volume']-b['volume'])/a['volume'] for a,b in zip(base,boosted))
    return result


def refinement_orders(coordinates, values, increasing_resolution):
    result=[]
    for xa,xb,ea,eb in zip(coordinates,coordinates[1:],values,values[1:]):
        ratio=xb/xa if increasing_resolution else xa/xb
        result.append(math.log(ea/eb)/math.log(ratio) if ea and eb else None)
    return result


def fitted_order(resolutions, errors):
    """Log-log slope and residual-based standard error; not a systematic-error bound."""
    if len(resolutions)!=len(errors) or len(errors)<3 or any(e<=0 or not math.isfinite(e) for e in errors):
        raise ValueError('order fit requires at least three positive finite errors')
    x=[math.log(1/n) for n in resolutions];y=list(map(math.log,errors))
    xm=sum(x)/len(x);ym=sum(y)/len(y)
    variance=sum((a-xm)**2 for a in x)
    if variance==0: raise ValueError('order fit needs distinct resolutions')
    slope=sum((a-xm)*(b-ym) for a,b in zip(x,y))/variance
    residual=sum((b-ym-slope*(a-xm))**2 for a,b in zip(x,y))
    return slope,math.sqrt(residual/(len(x)-2)/variance)


def mean_refinement_series(pairs):
    """Retain historical rows and include every measured smooth-flow profile."""
    series = []
    profiles = (*PROFILES, *sorted({p['profile'] for p in pairs if p['case']=='smooth'}-set(PROFILES)))
    for profile in profiles:
        for jitter in (0., .15):
            for variable, fixed in [('n', .00025), ('dt', 16)]:
                selection = [p for p in pairs if p['case']=='smooth' and p['profile']==profile and p['jitter']==jitter
                             and (p['dt']==fixed if variable=='n' else p['n']==fixed)]
                selection.sort(key=lambda p: p[variable], reverse=variable=='dt')
                values = [p.get('errors',{}).get('B',{}).get('L1') for p in selection]
                orders = refinement_orders([p[variable] for p in selection],values,variable=='n')
                series.append({'profile': profile, 'jitter': jitter, 'variable': variable,
                    'values': [[p[variable], value] for p, value in zip(selection, values)],
                    'successive_B_L1_orders': orders})
    return series


def evaluate(output, runs, pairs, physical_profile, temporal_enabled):
    for pair in pairs:
        a, b = (runs[n] for n in pair['names'])
        if any(r['status'] != 'completed' for r in (a, b)):
            pair['status'] = 'failed evolution'
            continue
        ca, cb = (read_snapshot(output/n/'final.csv',runs[n]['config']['n'],pair['time']) for n in pair['names'])
        pair['errors'] = boost_error(ca, cb, pair['time'])
        pair['pairing_valid'] = (a['summary']['time'] == b['summary']['time'] == pair['time']
            and all(c['time']==pair['time'] for c in ca+cb)
            and pair['errors']['position_max'] <= 1e-11 and pair['errors']['relative_volume_max'] <= 1e-11)
        pair['matching_auxiliary_roots'] = a['summary']['auxiliary_roots'] == b['summary']['auxiliary_roots']
        pair['positive_and_conservative'] = all(r['positive_and_conservative'] for r in (a,b))
        if not pair['pairing_valid']:
            pair['status'] = 'fail: paired time/geometry mismatch'
        elif pair['case'] == 'smooth' and pair['profile'] == 'paper-global-v2':
            pair['status'] = 'diagnostic observation; no retrospective boost gate'
        elif pair['case'] == 'loop':
            scale = .001/math.sqrt(4*math.pi)
            pair['B_relative_L1'] = pair['errors']['B']['L1']/scale
            pair['status'] = 'pass' if pair['B_relative_L1'] <= .001 and pair['positive_and_conservative'] else 'fail'
        elif pair['case'] == 'smooth':
            pair['status'] = 'pass' if (max(pair['errors'][k]['max'] for k in FIELDS) <= 1e-9
                and pair['matching_auxiliary_roots'] and pair['positive_and_conservative']) else 'fail'
        else:
            energy = .66 + .5*pair['parallel']**2
            velocity_scale = max(math.sqrt(pair['parallel']**2+.01), math.sqrt(1/6))
            shared = {'rho':1.,'p':.1,'energy':energy}
            conventions = {'wave_amplitude':{**shared,'B':.1,'v':.1},
                           'mean_field_and_initial_speed':{**shared,'B':1.,'v':velocity_scale}}
            pair['relative_L1'] = {name:{k:pair['errors'][k]['L1']/scale for k,scale in scales.items()}
                                   for name,scales in conventions.items()}
            pair['normalization_scales'] = conventions
            pair['normalization_note'] = 'Wave-amplitude scale is prospective for the continuation; both conventions and unchanged thresholds are retained. Historical runs use the documented post-run clarification.'
            verdicts = {name:max(values.values()) <= 1e-8 and pair['positive_and_conservative']
                        for name,values in pair['relative_L1'].items()}
            pair['normalization_verdicts'] = verdicts
            pair['status'] = ('pass under both reported normalizations' if all(verdicts.values()) else
                              'fail under both reported normalizations' if not any(verdicts.values()) else
                              'normalization clarification pending')
    series = mean_refinement_series(pairs)
    convergence = []
    for jitter in (0., .15):
        for parallel in (0., 1.):
            for motion in ('fixed', 'comoving'):
                chosen = sorted([r for n,r in runs.items() if n.startswith('alfven_') and n.endswith('_base') and r['config']['jitter']==jitter
                                 and r['config']['parallel']==parallel and r['config']['motion_family']==motion], key=lambda r:r['config']['n'])
                if not chosen:
                    continue
                rows = [{'n':r['config']['n'], 'B_L1':r.get('errors',{}).get('final',{}).get('B',{}).get('L1'), 'status':r['status']} for r in chosen]
                for row in rows:
                    if row['status']=='completed' and (row['B_L1'] is None or not math.isfinite(row['B_L1']) or row['B_L1']<=0):
                        row['status']='failed: missing/invalid convergence error'
                item = {'jitter':jitter,'parallel':parallel,'motion':motion,'rows':rows,'gate':'unexecuted: requires complete N32/64/128/256 ladder'}
                if any(r['status']!='completed' for r in rows):
                    item['gate']='fail: evolution failed; missing resolutions also remain unexecuted'
                elif [r['n'] for r in rows]==[32,64,128,256]:
                    order,uncertainty=fitted_order([r['n'] for r in rows[-3:]],[r['B_L1'] for r in rows[-3:]])
                    item.update(finest_three_order=order, finest_relative_B_L1=rows[-1]['B_L1']/.1,
                                finest_three_order_standard_error=uncertainty,
                                uncertainty_scope='Residual-based log-log fit standard error, one degree of freedom; not a systematic discretization-error bound.',
                                gate='pass' if order>=1.8 and rows[-1]['B_L1']/.1<=.02 and all(r['positive_and_conservative'] for r in chosen) else 'fail')
                convergence.append(item)
    temporal=[]
    if temporal_enabled:
        for parallel in (0.,1.):
            for jitter in (0.,.15):
                reference=f'temporal_{physical_profile}_v{parallel}_j{jitter}_dt2.5e-05'
                if runs[reference]['status']!='completed':
                    temporal.append({'reference':reference,'status':'failed reference'}); continue
                ref=read_snapshot(output/reference/'final.csv',runs[reference]['config']['n'],runs[reference]['config']['target'])
                for dt in (.0004,.0002,.0001):
                    name=f'temporal_{physical_profile}_v{parallel}_j{jitter}_dt{dt}'
                    record={'name':name,'reference':reference,'status':runs[name]['status']}
                    if record['status']=='completed':
                        cells=read_snapshot(output/name/'final.csv',runs[name]['config']['n'],runs[name]['config']['target'])
                        record['errors']={k:norms([a[k]-b[k] for a,b in zip(cells,ref)],ref) for k in ('bx','by','bz','ax','ay','az','phi')}
                        record['dt']=dt
                        record['dt_max_actual']=runs[name]['summary']['dt_max']
                        record['cap_reached']=math.isclose(record['dt_max_actual'],dt,rel_tol=1e-10,abs_tol=1e-15)
                        record['timestep_note']='Orders use dt-cap ratios; inspect actual dt_min/max and rejection counters before interpreting temporal order.'
                        record['errors']['B']=norms([math.sqrt(sum((a[k]-b[k])**2 for k in ('bx','by','bz'))) for a,b in zip(cells,ref)],ref)
                    temporal.append(record)
    for reference in {r['reference'] for r in temporal}:
        group=sorted([r for r in temporal if r['reference']==reference and 'errors' in r],key=lambda r:r['dt'],reverse=True)
        for left,right in zip(group,group[1:]):
            right['orders_from_previous_dt']={k:math.log(left['errors'][k]['L1']/right['errors'][k]['L1'])/math.log(left['dt']/right['dt'])
                if left['errors'][k]['L1']>0 and right['errors'][k]['L1']>0 else None for k in right['errors']}
    result={'scope':'issue #7; failed and unexecuted gates remain open', 'pairs':pairs,'mean_refinement':series,
            'alfven_convergence':convergence,'temporal':temporal or 'unexecuted',
            'kinematic_loop':'unexecuted by this coupled-MHD runner; separate prescribed-flow packet remains required',
            'runs':runs}
    return result


def reanalyze(output):
    original = output/'execution_provenance.json'
    if not original.exists():
        shutil.copyfile(output/'provenance.json',original)
    execution = json.loads(original.read_text())
    for filename in ('manifest.json','runs.json'):
        if sha(output/filename) != execution['result_sha256'][filename]:
            raise ValueError(f'changed execution input {filename}')
    immutable = output/'execution_summary.json'
    if not immutable.exists():
        if sha(output/'summary.json') != execution['result_sha256']['summary.json']:
            raise ValueError('Original execution summary is missing; refusing mutable metadata')
        shutil.copyfile(output/'summary.json',immutable)
    if sha(immutable) != execution['result_sha256']['summary.json']:
        raise ValueError('Changed immutable execution summary')
    runs = json.loads((output/'runs.json').read_text())
    old = json.loads(immutable.read_text())
    pair_keys=('names','case','profile','n','jitter','parallel','motion','dt','time')
    pairs=[{k:p[k] for k in pair_keys} | ({'riemann_solver':p['riemann_solver']} if 'riemann_solver' in p else {})
           for p in old['pairs']]
    for name,record in runs.items():
        for filename,digest in record['sha256'].items():
            if sha(output/name/filename) != digest:
                raise ValueError(f'changed raw input {name}/{filename}')
        c=record['config']
        if 'summary' in record:
            if not riemann_matches(c,record['summary']):
                raise ValueError('Riemann configuration mismatch: '+name)
            for stage,t in [('initial',0.),('final',record['summary']['time'])]:
                read_snapshot(output/name/f'{stage}.csv',c['n'],t)
            if record['summary']['time'] != c['target'] or not record['summary']['completed']:
                record['status']='failed evolution'
        if 'summary' in record and c['case']!='smooth':
            record['errors']={stage:physical_errors(read_snapshot(output/name/f'{stage}.csv',c['n'],t),t,c['case'],c['parallel'],c['boost'])
                              for stage,t in [('initial',0.),('final',record['summary']['time'])]}
            checkpoint=output/name/'checkpoint_0.25000000.csv'
            if record['summary']['time'] >= .25 and not checkpoint.exists():
                raise ValueError(f'missing requested checkpoint: {name}')
            if checkpoint.exists():
                record['errors']['t0.25']=physical_errors(read_snapshot(checkpoint,c['n'],.25),.25,c['case'],c['parallel'],c['boost'])
    physical_profiles={r['config']['profile'] for r in runs.values() if r['config']['case']!='smooth'}
    profile=next(iter(physical_profiles),PROFILES[0])
    result=evaluate(output,runs,pairs,profile,any(n.startswith('temporal_') for n in runs))
    dump(output/'summary.json',result)
    provenance={'execution_provenance_sha256':sha(original),'execution_revision':execution['revision'],
                'measurement_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                'measurement_dirty_status':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True).strip(),
                'measurement_source_sha256':sha(Path(__file__)),
                'execution_summary_sha256':sha(immutable),'raw_runs_sha256':sha(output/'runs.json'),'summary_sha256':sha(output/'summary.json'),
                'note':'No evolution rerun; raw inputs validated against original execution hashes.'}
    dump(output/'measurement_provenance.json',provenance)
    print(f'Remeasured validated raw snapshots: {output}')


def validate_parallelism(jobs, threads):
    if not 1 <= jobs <= 24 or not 1 <= threads <= 24 or jobs*threads > 24:
        raise ValueError('jobs and threads must be 1..24 with jobs*threads <= 24')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analyze-only', action='store_true', help='Remeasure existing raw snapshots with separate analysis provenance')
    parser.add_argument('--suite', choices=('mean', 'physical', 'all'), default='all')
    parser.add_argument('--quick', action='store_true', help='Physical N32/64 subset; full-resolution/temporal gates stay unexecuted')
    parser.add_argument('--calibration', action='store_true', help='Only the N128 jittered travelling fixed-grid wave pair; no full acceptance')
    parser.add_argument('--candidate-mean', action='store_true', help='Run the registered mean-field ladder for --profile only; historical default comparison is preserved')
    parser.add_argument('--temporal', action='store_true', help='Also run registered N64 fixed-grid temporal comparisons')
    parser.add_argument('--profile', choices=PHYSICAL_PROFILES, default=PROFILES[0], help='Physical studies; historical mean-field suite is unchanged')
    parser.add_argument('--accelerated-projection', action='store_true', help='Cached projection solve; projected-rate profiles only')
    parser.add_argument('--projection-screening', type=float, default=0., help='Opt-in damping kappa of the projected-rate correction; 0 is the exact projection')
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--threads', type=int, default=1, help='Threads per evolution; jobs*threads <= 24')
    parser.add_argument('--timeout', type=float, help='Wall seconds per evolution; a timeout fails the run')
    parser.add_argument('--output-dir', type=Path, default=ROOT/'results/m1_wave_loop')
    parser.add_argument('--riemann', choices=RIEMANN_SOLVERS, default='hlld', help='Explicit candidate flux; historical default remains HLLD')
    args = parser.parse_args()
    try: validate_parallelism(args.jobs,args.threads)
    except ValueError as error: parser.error(str(error))
    if args.timeout is not None and (not math.isfinite(args.timeout) or args.timeout <= 0):
        parser.error('timeout must be finite and positive')
    candidate_suite = args.suite == 'physical' or (args.suite == 'mean' and args.candidate_mean)
    if args.riemann != 'hlld' and (not candidate_suite or args.profile != HLL_PROFILE):
        parser.error('Explicit flux comparator requires the quadratic physical or candidate-mean suite')
    if args.candidate_mean and args.suite != 'mean':
        parser.error('--candidate-mean requires --suite mean')
    if args.accelerated_projection and (args.profile not in PROJECTED_PROFILES or not candidate_suite):
        parser.error('--accelerated-projection requires a projected-rate profile with physical or candidate-mean suite')
    if not math.isfinite(args.projection_screening) or args.projection_screening < 0 or (
            args.projection_screening and (args.profile not in PROJECTED_PROFILES or not candidate_suite)):
        parser.error('--projection-screening must be >= 0 with a projected-rate profile and physical or candidate-mean suite')
    if args.temporal and args.suite == 'mean':
        parser.error('--temporal requires the physical or all suite')
    if args.calibration and (args.quick or args.temporal or args.suite != 'physical'):
        parser.error('calibration requires --suite physical without quick/temporal')
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if args.analyze_only:
        reanalyze(output)
        return
    if (output/'manifest.json').exists():
        raise SystemExit('Choose a fresh output directory to preserve the previous run and provenance.')
    cargo = shutil.which('cargo') or str(Path.home()/'.cargo/bin/cargo')
    command = lambda c: subprocess.check_output(c, cwd=ROOT, text=True).strip()
    source_paths = sorted({*ROOT.glob('crates/*/src/**/*.rs'), *ROOT.glob('crates/*/tests/**/*.rs'),
                           *ROOT.glob('apps/*/src/**/*.rs'), Path(__file__).resolve(),
                           ROOT/'Cargo.toml', ROOT/'Cargo.lock', ROOT/'rust-toolchain.toml',
                           ROOT/'docs/M1_WAVE_LOOP_PLAN.md', ROOT/'docs/M1_COMPLETION_PLAN.md', ROOT/'docs/M1_MERGE_PLAN.md',
                           ROOT/'docs/M1_AUXILIARY_INVESTIGATION.md', ROOT/'benchmarks/m1/packet-v2.json'})
    source_paths += sorted(ROOT.glob('crates/*/Cargo.toml')) + sorted(ROOT.glob('apps/*/Cargo.toml'))
    sources = {str(p.relative_to(ROOT)): sha(p) for p in source_paths}
    provenance = {'created_utc': datetime.now(timezone.utc).isoformat(),
                  'revision': command(['git', 'rev-parse', 'HEAD']), 'dirty_status': command(['git', 'status', '--short']),
                  'source_sha256': sources, 'platform': platform.platform(), 'machine': platform.machine(),
                  'timeout_seconds': args.timeout,
                  'calibration': args.calibration,
                  'candidate_mean': args.candidate_mean,
                  'rustc': command([str(Path(cargo).with_name('rustc')), '-Vv']), 'jobs': args.jobs,
                  'configuration': {'units': 'dimensionless, mu0=1', 'gamma': 5/3, 'precision': 'f64',
                                    'boundary': 'periodic unit square', 'per_run_ranks': 1, 'per_run_threads': args.threads,
                                    'geometry': 'ordered clipped Voronoi; deterministic trigonometric jitter',
                                    'build': 'release --locked', 'quick_physical_subset': args.quick,
                                    'accelerated_projection': args.accelerated_projection,
                                    'projection_screening': args.projection_screening}}
    subprocess.run([cargo, 'build', '--release', '--locked', '-p', 'openmhd', '--bin', 'vector-potential'], cwd=ROOT, check=True)
    binary = ROOT/'target/release/vector-potential'
    provenance['binary_sha256'] = sha(binary)
    configs = {}
    pairs = []

    def add_pair(prefix, case, profile, n, jitter, parallel=0., motion='fixed', dt=None, final=1.):
        names = []
        mesh_base = [0., 0.] if motion == 'fixed' else ([parallel, 0.] if case == 'alfven' else [2., 1.])
        for boosted in (False, True):
            name = prefix+('_boost' if boosted else '_base')
            boost = list(BOOST if boosted else (0., 0., 0.))
            w = [mesh_base[k]+boost[k] for k in range(2)]
            configs[name] = {'name': name, 'case': case, 'profile': profile, 'n': n, 'jitter': jitter,
                             'parallel': parallel, 'motion_family': motion, 'mesh_velocity': w,
                             'boost': boost, 'dt': dt, 'target': final}
            names.append(name)
        pairs.append({'names': names, 'case': case, 'profile': profile, 'n': n, 'jitter': jitter,
                      'parallel': parallel, 'motion': motion, 'dt': dt, 'time': final})

    if args.suite in ('mean', 'all'):
        for profile in ((args.profile,) if args.candidate_mean else PROFILES):
            for jitter in (0., .15):
                for n in (8, 16, 32, 64):
                    add_pair(f'mean_{profile}_n{n}_j{jitter}_dt0.00025', 'smooth', profile, n, jitter, dt=.00025, final=.02)
                for dt in (.001, .0005):
                    add_pair(f'mean_{profile}_n16_j{jitter}_dt{dt}', 'smooth', profile, 16, jitter, dt=dt, final=.02)
    if args.suite in ('physical', 'all'):
        for case in ('alfven', 'loop'):
            for parallel in ((0., 1.) if case == 'alfven' else (0.,)):
                for jitter in (0., .15):
                    for motion in ('fixed', 'comoving'):
                        for n in ((32, 64) if args.quick else (32, 64, 128, 256)):
                            add_pair(f'{case}_{args.profile}_v{parallel}_j{jitter}_{motion}_n{n}', case, args.profile, n, jitter, parallel, motion)
        if args.temporal:
            for parallel in (0., 1.):
                for jitter in (0., .15):
                    for dt in (.0004, .0002, .0001, .000025):
                        name = f'temporal_{args.profile}_v{parallel}_j{jitter}_dt{dt}'
                        configs[name] = {'name': name, 'case': 'alfven', 'profile': args.profile, 'n': 64,
                                         'jitter': jitter, 'parallel': parallel, 'motion_family': 'fixed',
                                         'mesh_velocity': [0., 0.], 'boost': [0., 0., 0.], 'dt': dt, 'target': 1.}
    if args.calibration:
        configs = {n:c for n,c in configs.items() if c['case']=='alfven' and c['n']==128
                   and c['jitter']==.15 and c['parallel']==0. and c['motion_family']=='fixed'}
        pairs = [p for p in pairs if all(n in configs for n in p['names'])]
    configs = with_riemann(configs,args.riemann)
    if args.riemann != 'hlld':
        provenance['configuration']['riemann_solver'] = args.riemann
        for pair in pairs: pair['riemann_solver'] = args.riemann
    dump(output/'manifest.json', configs)
    dump(output/'provenance.json', provenance)
    runs = {}

    def run(config):
        name = config['name']
        dest = output/name
        dest.mkdir(exist_ok=True)
        command = [str(binary), '--case', config['case'], '--profile', config['profile'], '--n', str(config['n']),
                   '--jitter', str(config['jitter']), '--time', str(config['target']), '--parallel-velocity', str(config['parallel']),
                   '--motion', 'rigid', '--mesh-x', str(config['mesh_velocity'][0]), '--mesh-y', str(config['mesh_velocity'][1]),
                   '--boost-x', str(config['boost'][0]), '--boost-y', str(config['boost'][1]), '--boost-z', str(config['boost'][2]),
                   '--output', str(dest), '--threads', str(args.threads)]
        command += riemann_arguments(config)
        if config['case'] == 'smooth':
            command += ['--mean-bx', '.3', '--mean-by', '.2', '--mean-bz', '.1']
        else:
            command += ['--checkpoint', '.25']
        if config['dt'] is not None:
            command += ['--dt', str(config['dt'])]
        if args.accelerated_projection:
            command += ['--accelerated-projection']
        if args.projection_screening:
            command += ['--projection-screening', str(args.projection_screening)]
        start = time.monotonic()
        record = {'config': config, 'command': command, 'status': 'failed'}
        try:
            with (dest/'run.log').open('w') as log:
                completed = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout)
            record.update(returncode=completed.returncode,
                          status='completed' if completed.returncode == 0 else 'failed')
            if (dest/'summary.json').exists():
                record['summary'] = json.loads((dest/'summary.json').read_text())
                if (record['summary']['profile'] != config['profile'] or
                        record['summary'].get('projection_screening', 0.) != args.projection_screening or
                        not riemann_matches(config,record['summary'])):
                    raise ValueError('profile/screening configuration mismatch')
                record['history'] = json.loads((dest/'history.json').read_text())
                record['positive_and_conservative'] = all(h['diagnostics']['rho_min'] > 0 and h['diagnostics']['p_min'] > 0
                    and max(map(abs, h['diagnostics']['normalized_budget'])) <= 1e-10 for h in record['history'])
                for stage,t in [('initial',0.),('final',record['summary']['time'])]:
                    read_snapshot(dest/f'{stage}.csv',config['n'],t)
                if record['summary']['time'] != config['target'] or not record['summary']['completed']:
                    record['status'] = 'failed evolution'
                if config['case'] != 'smooth':
                    record['errors'] = {'initial': physical_errors(read_snapshot(dest/'initial.csv',config['n'],0.), 0., config['case'], config['parallel'], config['boost']),
                        'final': physical_errors(read_snapshot(dest/'final.csv',config['n'],record['summary']['time']), record['summary']['time'], config['case'], config['parallel'], config['boost'])}
                    checkpoint = dest/'checkpoint_0.25000000.csv'
                    if record['summary']['time'] >= .25 and not checkpoint.exists():
                        raise ValueError('missing requested checkpoint')
                    if checkpoint.exists():
                        record['errors']['t0.25'] = physical_errors(read_snapshot(checkpoint,config['n'],.25), .25, config['case'], config['parallel'], config['boost'])
            else:
                raise ValueError('missing run summary')
        except subprocess.TimeoutExpired:
            record.update(status='timeout', validation_error='Wall-time cap reached; incomplete execution')
        except (ValueError, KeyError, OSError) as error:
            record['status'] = 'failed snapshot validation'
            record['validation_error'] = str(error)
        record['seconds'] = time.monotonic()-start
        record['sha256'] = {p.name: sha(p) for p in sorted(dest.iterdir()) if p.is_file()}
        return name, record

    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = {executor.submit(run, config): name for name, config in configs.items()}
        for future in as_completed(futures):
            name, record = future.result()
            runs[name] = record
            dump(output/'runs.json', runs)
            print(f'{name}: {record["status"]}, {record["seconds"]:.2f} s', flush=True)
    result = evaluate(output, runs, pairs, args.profile, args.temporal)
    if args.riemann != 'hlld':result['riemann_solver']=args.riemann
    dump(output/'summary.json',result)
    if sources != {str(p.relative_to(ROOT)):sha(p) for p in source_paths}:
        raise ValueError('study sources changed during execution')
    provenance['result_sha256']={name:sha(output/name) for name in ('summary.json','manifest.json','runs.json')}
    dump(output/'provenance.json',provenance)
    print(f'Results: {output}; no full-M1 acceptance implied.',flush=True)


if __name__ == '__main__':
    main()
