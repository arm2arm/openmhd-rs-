#!/usr/bin/env python3
"""Tabulate the fan-out campaign of the smooth-extrema configuration (read-only).

Every gate status is the frozen production evaluation stored in each plan's
checkpoint.json; this script only collects those values next to the baseline
(the stopped pressure campaign: same configuration, default A-transport
limiter) and to the registered limits. Baseline ladder orders use the same
least-squares definition over N64/128/256. Missing or unfinished evidence is
reported as such and never as a pass. No evolution is launched.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
WAVE_BASELINE = HERE.parent/'m1_pressure_campaign/standing_diagnosis/runs.json.gz'
PROFILE = 'bulk-frame-heun-quadratic-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_plan(directory):
    plan = json.loads((directory/'plan.json').read_text())
    runs = json.loads((directory/'runs.json').read_text()) if (directory/'runs.json').exists() else {}
    checkpoint = json.loads((directory/'checkpoint.json').read_text()) if (directory/'checkpoint.json').exists() else {}
    states = checkpoint.get('workflow_states', {})
    status = dict(expected=len(plan['cases']), completed=sum(r['status'] == 'completed' for r in runs.values()),
                  not_completed=sorted(n for n, r in runs.items() if r['status'] != 'completed'),
                  all_terminal=checkpoint.get('all_terminal') is True,
                  running=sorted(e['specification']['config']['name'] for e in plan['cases']
                                 if states.get(e['workflow'], {}).get('status') not in ('finished', 'failed', 'stopped', 'deleted')),
                  verified_required_failure=checkpoint.get('verified_required_failure'),
                  execution_failures=checkpoint.get('execution_failures'),
                  workflow_prefix=plan['cases'][0]['workflow'].rsplit('-', 1)[0],
                  plan_sha256=sha(directory/'plan.json'), snapshot_sha256=plan['snapshot_sha256'])
    return runs, checkpoint.get('summaries', {}), status


def fitted_order(rows):
    """Least-squares log-log slope of B L1 against 1/N over the finest three registered grids."""
    chosen = {n: rows[n] for n in (64, 128, 256) if n in rows}
    if len(chosen) != 3:
        return None
    x = [math.log(1/n) for n in chosen]
    y = [math.log(v) for v in chosen.values()]
    xm, ym = sum(x)/3, sum(y)/3
    return sum((a-xm)*(b-ym) for a, b in zip(x, y))/sum((a-xm)**2 for a in x)


def ladders(summary, baseline):
    result = []
    for item in summary.get('alfven_convergence', []):
        theirs = {r['config']['n']: r['errors']['final']['B']['L1'] for n, r in baseline.items()
                  if n.startswith('alfven_') and n.endswith('_base') and r['status'] == 'completed'
                  and r['config']['jitter'] == item['jitter'] and r['config']['parallel'] == item['parallel']
                  and r['config']['motion_family'] == item['motion']}
        result.append(dict(jitter=item['jitter'], parallel=item['parallel'], motion=item['motion'], gate=item['gate'],
                           B_L1={str(r['n']): r['B_L1'] for r in item['rows']},
                           finest_three_order=item.get('finest_three_order'),
                           finest_relative_B_L1=item.get('finest_relative_B_L1'),
                           baseline_finest_three_order=fitted_order(theirs),
                           baseline_B_L1={str(n): v for n, v in sorted(theirs.items())}))
    return result


def wave_pairs(summary):
    groups = {}
    for pair in summary.get('pairs', []):
        key = pair['case']
        value = (pair['B_relative_L1'] if 'B_relative_L1' in pair else
                 max(max(v.values()) for v in pair['relative_L1'].values()) if 'relative_L1' in pair else
                 max(v['max'] for k, v in pair.get('errors', {}).items() if isinstance(v, dict) and 'max' in v) if pair.get('errors') else None)
        group = groups.setdefault(key, dict(pairs=0, passed=0, largest=None, statuses={}))
        group['pairs'] += 1
        group['passed'] += pair['status'].startswith('pass')
        group['statuses'][pair['status']] = group['statuses'].get(pair['status'], 0)+1
        if value is not None:
            group['largest'] = value if group['largest'] is None else max(group['largest'], value)
    limits = dict(alfven='1e-8 relative L1 under both normalisations', loop='1e-3 relative B L1', smooth='1e-9 largest field difference')
    return {k: dict(v, limit=limits.get(k)) for k, v in groups.items()}


def loops(runs, baseline):
    rows = []
    for name in sorted(n for n, r in runs.items() if r['config']['case'] == 'loop' and n.endswith('_base') and r['status'] == 'completed'):
        mine, theirs = runs[name], baseline.get(name)
        row = dict(name=name.replace(PROFILE+'_', ''), baseline_available=bool(theirs and theirs['status'] == 'completed'))
        for key in ('passive_B', 'passive_A'):
            row[key+'_L1'] = dict(candidate=mine['errors']['final'][key]['L1'])
            if row['baseline_available']:
                row[key+'_L1'].update(baseline=theirs['errors']['final'][key]['L1'],
                                      ratio=mine['errors']['final'][key]['L1']/theirs['errors']['final'][key]['L1'])
        kept = lambda r: r['summary']['final']['magnetic_energy']/r['summary']['initial']['magnetic_energy']
        row['magnetic_energy_retained'] = dict(candidate=kept(mine), **({'baseline': kept(theirs)} if row['baseline_available'] else {}))
        rows.append(row)
    return rows


def temporal(summary):
    """Differences from the dt=2.5e-5 run and their successive orders (reported, not gated)."""
    records = summary.get('temporal')
    if not isinstance(records, list):
        return records
    groups = {}
    for record in records:
        family, step = record['name'].rsplit('_dt', 1)
        groups.setdefault(family.replace('temporal_'+PROFILE+'_', ''), {})[float(step)] = (
            record['errors']['B']['L1'] if record['status'] == 'completed' else None)
    result = []
    for family, values in sorted(groups.items()):
        steps = sorted(values, reverse=True)
        orders = [math.log(values[a]/values[b])/math.log(a/b) if values[a] and values[b] else None
                  for a, b in zip(steps, steps[1:])]
        result.append(dict(family=family, B_L1_difference_from_finest_step={str(s): values[s] for s in steps},
                           successive_orders=orders))
    return result


def physics(runs, summary, baseline, packet):
    families = []
    for item in summary.get('profile_families', []):
        gate = packet['cases'][item['case']]['gate']
        limits = gate['finest_scaled_L1_max' if item['case'] == 'brio-wu' else 'finest_scaled_bin_L1_max']
        finest = item['names'][-1]
        row = dict(case=item['case'], jitter=item['jitter'], mesh=item['jitter_mode'], gated=item['primary_profile_gate'],
                   status=item['status'], finest_case=finest, fields={})
        if finest in runs and runs[finest]['status'] == 'completed':
            for field, limit in limits.items():
                mine = runs[finest]['reference_errors'][field]['L1']
                row['fields'][field] = dict(L1=mine, limit=limit, baseline=baseline[finest]['reference_errors'][field]['L1'],
                                            coarsest=runs[item['names'][0]]['reference_errors'][field]['L1']
                                            if item['names'][0] in runs and runs[item['names'][0]]['status'] == 'completed' else None)
        families.append(row)
    vortices = []
    for name in sorted(n for n, r in runs.items() if r['config']['case'] == 'orszag-tang' and n.endswith('_base')
                       and r['status'] == 'completed'):
        values = runs[name]['diagnostic_values']
        vortices.append(dict(name=name, state_and_diagnostic_gates=runs[name]['state_and_diagnostic_gates'],
                             **{k: dict(candidate=v, baseline=baseline[name]['diagnostic_values'][k],
                                        limit=packet['cases']['orszag-tang']['gate'][k]) for k, v in values.items()}))
    pairs = summary.get('boost_pairs', [])
    done = [p for p in pairs if 'relative_L1' in p]
    return dict(families=families, vortex_diagnostics=vortices,
                boost_pairs=dict(pairs=len(pairs), passed=sum(p['status'] == 'pass' for p in pairs),
                                 largest=max((max(p['relative_L1'].values()) for p in done), default=None),
                                 limit='1e-8 relative L1'),
                state_and_diagnostic_gates=dict(runs=len(runs), passed=sum(r.get('state_and_diagnostic_gates') is True for r in runs.values())),
                all_registered_physics_gates=summary.get('all_registered_physics_gates'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('medium', 'mean', 'physics', 'waves'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--baseline-physics', type=Path, required=True)
    parser.add_argument('--verdict', type=Path, help='output of scripts/fanout_campaign_verdict.py, when it exists')
    parser.add_argument('--packet', type=Path, default=HERE.parents[2]/'benchmarks/m0/packet.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    wave_baseline = json.loads(gzip.decompress(WAVE_BASELINE.read_bytes()))
    physics_baseline = json.loads(args.baseline_physics.read_text())
    packet = json.loads(args.packet.read_text())
    loaded = {name: load_plan(getattr(args, name)) for name in ('medium', 'mean', 'physics', 'waves')}
    wave_runs, wave_summaries, _ = loaded['waves']
    wave_summary = wave_summaries.get('wave', {})
    result = dict(
        scope='Collected production gate evaluations of one opt-in configuration; evidence for review, not acceptance.',
        configuration=f'{PROFILE} --accelerated-projection --projection-screening 1 --riemann hlld-pressure '
                      '--potential-limiter smooth-extrema',
        baseline='openmhd-m1-pressure-reuse-20261110.1 (default A-transport limiter); its N256 loops never completed',
        script_sha256=sha(Path(__file__)), baseline_wave_run_map_sha256=sha(WAVE_BASELINE),
        baseline_physics_run_map_sha256=sha(args.baseline_physics), packet_sha256=sha(args.packet),
        plans={name: status for name, (_, _, status) in loaded.items()},
        complete=all(status['all_terminal'] and status['completed'] == status['expected'] for _, _, status in loaded.values()),
        alfven_ladders=ladders(wave_summary, wave_baseline),
        boost_pairs=dict(waves=wave_pairs(wave_summary), medium=wave_pairs(loaded['medium'][1].get('wave', {})),
                         mean=wave_pairs(loaded['mean'][1].get('wave', {}))),
        loops=loops(wave_runs, wave_baseline), temporal=temporal(wave_summary),
        shock_vortex=physics(loaded['physics'][0], loaded['physics'][1].get('physics', {}), physics_baseline, packet),
        full_m1_accepted=False)
    if args.verdict is not None:
        verdict = json.loads(args.verdict.read_text())
        result['verdict'] = dict(sha256=sha(args.verdict), phases={n: p['passed'] for n, p in verdict['phases'].items()},
                                 failed_checks={n: [k for k, v in p['checks'].items() if v is not True] + ([p['error']] if 'error' in p else [])
                                                for n, p in verdict['phases'].items() if not p['passed']},
                                 all_registered_phase_checks_passed=verdict['all_registered_phase_checks_passed'])
    args.output.write_text(json.dumps(result, indent=1, allow_nan=False)+'\n')
    for name, status in result['plans'].items():
        print(f"{name:8} {status['completed']}/{status['expected']} completed, terminal {status['all_terminal']}, "
              f"running {len(status['running'])}, required failure {status['verified_required_failure']}")
    for item in result['alfven_ladders']:
        order, base = item['finest_three_order'], item['baseline_finest_three_order']
        print(f"ladder jitter {item['jitter']} parallel {item['parallel']} {item['motion']:8} {item['gate'][:12]:12} "
              f"{'%.4f' % order if order is not None else '   n/a'} baseline {'%.4f' % base if base is not None else 'n/a'}")
    for group, pairs in result['boost_pairs'].items():
        for case, p in pairs.items():
            print(f"pairs {group:6} {case:7} {p['passed']}/{p['pairs']} largest {p['largest']}")
    p = result['shock_vortex']
    print('physics pairs', p['boost_pairs']['passed'], '/', p['boost_pairs']['pairs'], 'state gates', p['state_and_diagnostic_gates'],
          'families', [(f['case'], f['jitter'], f['mesh'], f['status']) for f in p['families']])
    print('complete:', result['complete'], '| verdict:', result.get('verdict', {}).get('all_registered_phase_checks_passed', 'not run'))


if __name__ == '__main__':
    main()
