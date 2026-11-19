#!/usr/bin/env python3
"""Separate resolved from roundoff-level values in a campaign reproduction (read-only).

Post-hoc analysis, not part of the registered measurement. The registered
measurement of docs/M1_FULL_VALIDATION_PLAN.md (scripts/compare_campaign_runs.py)
reports the largest relative difference of each family. Where both values are
themselves at roundoff level, for instance the Bx error of a wave whose Bx is
the constant mean field, that ratio is of order one by construction. This script
repeats the comparison from the archived run records with the same leaves and
sections, and reports for each family:

- the registered largest relative difference, which must equal the registered
  measurement;
- the largest relative difference over resolved values, max(|a|, |b|) >= FLOOR,
  where an order counts as resolved only if the errors it is computed from are;
- the largest magnitude among the unresolved values;
- the same over the cases whose step, rejection and fallback counts are equal,
  and separately for the cases where they differ;
- the quantities the plan names: final B and v L1 errors of waves and loops
  (the passive loop-transport errors are not among them),
  the finest-three ladder orders, the shock and vortex reference L1 errors and
  the boost-pair statuses;
- with --raw-reference/--raw-candidate (local raw plan directories, not
  archived), the largest final-state difference of selected cases.

No threshold or gate is defined here.
"""
import argparse
import csv
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from compare_campaign_runs import (COUNTERS, PHASES, RECORD_SECTIONS, ROW_KEYS,  # noqa: E402
                                   SUMMARY_SECTIONS, keyed, leaves, relative, section)

FLOOR = 1e-12
REFERENCE = ROOT/'tests/reference/m1_standing_limiter/campaign/plans/full-{phase}_{kind}.json.gz'
CANDIDATE = HERE/'iter/plans/iter-{phase}_{kind}.json.gz'


def load(template, phase, kind):
    path = Path(str(template).format(phase=phase, kind=kind))
    return json.loads(gzip.decompress(path.read_bytes())), hashlib.sha256(path.read_bytes()).hexdigest()


def error_leaf(name, path):
    """Magnitude that decides whether a derived order is resolved, or None for a plain value.

    Rows are matched by identity, as in the registered comparison; an order from
    the previous step size uses the previous row of the same campaign's list."""
    temporal = re.fullmatch(r'(.+)\.orders_from_previous_dt\.(\w+)', path) if name == 'temporal' else None
    if temporal:
        row, field = temporal.group(1), temporal.group(2)
        def scale(rows):
            i = next(i for i, r in enumerate(rows) if ROW_KEYS[name](r) == row)
            return min(abs(rows[i]['errors'][field]['L1']), abs(rows[i-1]['errors'][field]['L1']))
        return scale
    refinement = re.fullmatch(r'(.+)\.successive_B_L1_orders\[(\d+)\]', path) if name == 'mean_refinement' else None
    if refinement:
        row, k = refinement.group(1), int(refinement.group(2))
        def scale(rows):
            r = next(r for r in rows if ROW_KEYS[name](r) == row)
            return min(abs(r['values'][k][1]), abs(r['values'][k+1][1]))
        return scale
    return None


def family(pairs):
    """pairs: (case, path, a, b, scale) with scale deciding resolution."""
    registered = max(((relative(a, b), case, path, a, b) for case, path, a, b, _ in pairs), default=None)
    resolved = [(relative(a, b), case, path, a, b) for case, path, a, b, scale in pairs if scale >= FLOOR]
    unresolved = [max(abs(a), abs(b)) for case, path, a, b, scale in pairs if scale < FLOOR and path]
    row = lambda r: None if r is None else dict(relative=r[0], case=r[1], at=r[2], reference=r[3], candidate=r[4])
    return dict(values=len(pairs), registered_largest=row(registered), resolved=len(resolved),
                resolved_largest=row(max(resolved, default=None)), unresolved=len(unresolved),
                unresolved_largest_magnitude=max(unresolved, default=None))


def largest(rows):
    """rows: (relative, case, quantity, reference, candidate)."""
    w = max(rows, default=None)
    return None if w is None else dict(values=len(rows), relative=w[0], case=w[1], quantity=w[2],
                                       reference=w[3], candidate=w[4])


def registered(phase, ref_runs, new_runs, ref_summary, new_summary, changed):
    """The quantities that the plan names, split by whether the counters changed."""
    names = sorted(set(ref_runs) & set(new_runs))
    out = {}
    for group, selected in (('equal_counters', [n for n in names if n not in changed]),
                            ('changed_counters', [n for n in names if n in changed])):
        if phase == 'physics':
            rows = [(relative(ref_runs[n]['reference_errors'][f]['L1'], new_runs[n]['reference_errors'][f]['L1']),
                     n, f+'.L1', ref_runs[n]['reference_errors'][f]['L1'], new_runs[n]['reference_errors'][f]['L1'])
                    for n in selected for f in ref_runs[n].get('reference_errors', {})]
            out['reference_error_L1_'+group] = largest(rows)
        else:
            rows = []
            for n in selected:
                a, b = section(ref_runs[n], ('errors', 'final')), section(new_runs[n], ('errors', 'final'))
                for f in ('B', 'v'):
                    if a and b and f in a and f in b:
                        rows.append((relative(a[f]['L1'], b[f]['L1']), n, f+'.L1', a[f]['L1'], b[f]['L1']))
            out['final_L1_'+group] = largest(rows)
    if phase == 'physics':
        a, b = keyed('boost_pairs', ref_summary['boost_pairs']), keyed('boost_pairs', new_summary['boost_pairs'])
        out['boost_pairs'] = dict(pairs=len(a), same_status=sum(a[k]['status'] == b[k]['status'] for k in a if k in b),
                                  largest_relative_L1=[max(max(p['relative_L1'].values()) for p in x.values()) for x in (a, b)])
    else:
        ladders = [keyed('alfven_convergence', x.get('alfven_convergence', [])) for x in (ref_summary, new_summary)]
        rows = [(relative(ladders[0][k]['finest_three_order'], ladders[1][k]['finest_three_order']), 'ladder', k,
                 ladders[0][k]['finest_three_order'], ladders[1][k]['finest_three_order'])
                for k in ladders[0] if k in ladders[1] and ladders[0][k].get('finest_three_order') is not None
                and ladders[1][k].get('finest_three_order') is not None]
        if rows:
            out['ladder_orders'] = largest(rows)
            out['ladder_gates_equal'] = all(ladders[0][k]['gate'] == ladders[1][k]['gate'] for k in ladders[0])
        a, b = keyed('pairs', ref_summary.get('pairs', [])), keyed('pairs', new_summary.get('pairs', []))
        out['boost_pairs'] = dict(pairs=len(a), same_status=sum(a[k].get('status') == b[k].get('status') for k in a if k in b))
    return out


def final_state(reference, candidate, case):
    """Largest absolute difference of each field of final.csv, and relative to the field's largest value."""
    def cells(root):
        with open(root/'raw'/case/'final.csv') as stream:
            return list(csv.DictReader(stream))
    a, b = cells(reference), cells(candidate)
    if len(a) != len(b) or any(x['id'] != y['id'] for x, y in zip(a, b)):
        raise ValueError(f'{case}: final snapshots do not match cell by cell')
    out = {}
    for field in ('rho', 'p', 'vx', 'vy', 'vz', 'bx', 'by', 'bz', 'ax', 'ay', 'az', 'phi'):
        d = max(abs(float(x[field])-float(y[field])) for x, y in zip(a, b))
        scale = max(abs(float(x[field])) for x in a)
        out[field] = dict(absolute=d, field_max=scale, relative_to_field_max=d/scale if scale else None)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--raw-reference', type=Path, help='local waves plan directory of the reference campaign')
    parser.add_argument('--raw-candidate', type=Path, help='local waves plan directory of the candidate campaign')
    parser.add_argument('--final-state-case', action='append', default=[], help='case whose final states are compared')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output file')
    result = dict(scope='Post-hoc separation of resolved and roundoff-level values; not a registered measurement, no gate.',
                  floor=FLOOR, inputs={}, phases={})
    for phase in PHASES:
        (ref_runs, h1), (new_runs, h2) = load(REFERENCE, phase, 'runs'), load(CANDIDATE, phase, 'runs')
        (ref_ckpt, h3), (new_ckpt, h4) = load(REFERENCE, phase, 'checkpoint'), load(CANDIDATE, phase, 'checkpoint')
        result['inputs'][phase] = dict(reference_runs=h1, candidate_runs=h2, reference_checkpoint=h3, candidate_checkpoint=h4)
        names = sorted(set(ref_runs) & set(new_runs))
        changed = {n: {k: [ref_runs[n]['summary'].get(k), new_runs[n]['summary'].get(k)] for k in COUNTERS
                       if ref_runs[n]['summary'].get(k) != new_runs[n]['summary'].get(k)} for n in names}
        changed = {n: c for n, c in changed.items() if c}
        families = {}
        for label, path in RECORD_SECTIONS.items():
            pairs = []
            for n in names:
                left, right = section(ref_runs[n], path), section(new_runs[n], path)
                if left is None or right is None:
                    continue
                a, b = dict(leaves(left)), dict(leaves(right))
                pairs += [(n, k, a[k], b[k], max(abs(a[k]), abs(b[k]))) for k in sorted(set(a) & set(b))]
            if pairs:
                families[label] = dict(all_cases=family(pairs),
                                       equal_counters=family([p for p in pairs if p[0] not in changed]),
                                       changed_counters=family([p for p in pairs if p[0] in changed]))
        kind = 'physics' if phase == 'physics' else 'wave'
        ref_summary, new_summary = ref_ckpt['summaries'].get(kind, {}), new_ckpt['summaries'].get(kind, {})
        for key in SUMMARY_SECTIONS[kind]:
            if key not in ref_summary or key not in new_summary:
                continue
            a = dict(leaves(keyed(key, ref_summary[key])))
            b = dict(leaves(keyed(key, new_summary[key])))
            pairs = []
            for k in sorted(set(a) & set(b)):
                derived = error_leaf(key, k)
                scale = (min(derived(ref_summary[key]), derived(new_summary[key])) if derived
                         else max(abs(a[k]), abs(b[k])))
                pairs.append(('summary', k, a[k], b[k], scale))
            families['summary.'+key] = dict(all_cases=family(pairs))
        result['phases'][phase] = dict(cases=len(names), changed_counters=changed, families=families,
                                       registered=registered(phase, ref_runs, new_runs, ref_summary, new_summary, changed))
    if args.final_state_case:
        if args.raw_reference is None or args.raw_candidate is None:
            parser.error('--final-state-case requires --raw-reference and --raw-candidate')
        result['final_states'] = {case: final_state(args.raw_reference, args.raw_candidate, case)
                                  for case in args.final_state_case}
    args.output.write_text(json.dumps(result, indent=1, allow_nan=False)+'\n')
    for phase, item in result['phases'].items():
        print(f'{phase}: {item["cases"]} cases, counters differ in {len(item["changed_counters"])}: {item["changed_counters"]}')
        for label, groups in item['families'].items():
            for group, f in groups.items():
                reg, res = f['registered_largest'], f['resolved_largest']
                print(f'  {label:28} {group:16} values {f["values"]:6} registered {reg["relative"] if reg else 0:.2e} '
                      f'| resolved {f["resolved"]:6} largest {res["relative"] if res else 0:.2e} '
                      f'| unresolved {f["unresolved"]:5} up to {f["unresolved_largest_magnitude"] or 0:.1e}')
        for label, value in item['registered'].items():
            print(f'  registered {label}: {value}')
    for case, fields in result.get('final_states', {}).items():
        print(f'final state {case}: largest absolute difference {max(v["absolute"] for v in fields.values()):.2e}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
