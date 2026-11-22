#!/usr/bin/env python3
"""Compare the registered diagnostics of two fan-out campaigns case by case (no execution, no gate).

For the 2026-11-17 follow-up of docs/M1_FULL_VALIDATION_PLAN.md: configuration A is
expected to reproduce the 2026-11-14 campaign to roundoff, and B measures the effect of
its changed step sequence. For every case present in both campaigns this reports the
largest relative difference over the numeric diagnostics of each registered section of
the run records and of the phase summaries, the step and rejection counts, and the
wall times. No threshold is defined here; the expectation stated in the plan is
reported next to the measurement.

  python3 scripts/compare_campaign_runs.py --reference-medium <dir> ... --candidate-medium <dir> ... --output <json>
"""
import argparse
import json
import math
from pathlib import Path

PHASES = ('medium', 'mean', 'physics', 'waves')
# Registered diagnostics of one run: wave errors at the final time, shock/vortex
# reference errors and the diagnostic values behind the physics gates.
RECORD_SECTIONS = {'final_errors': ('errors', 'final'), 'reference_errors': ('reference_errors',),
                   'diagnostic_values': ('diagnostic_values',)}
SUMMARY_SECTIONS = {'wave': ('alfven_convergence', 'pairs', 'temporal', 'mean_refinement'),
                    'physics': ('boost_pairs',)}
COUNTERS = ('steps', 'rejected_cfl', 'rejected_state', 'rejected_geometry', 'hll_fallbacks')
# Identity of the rows of summary lists. Their order follows the plan's case
# order, which may differ between campaigns, so rows are matched by identity.
ROW_KEYS = {
    'pairs': lambda r: '|'.join(r['names']),
    'boost_pairs': lambda r: '|'.join(r['names']),
    'alfven_convergence': lambda r: f"jitter={r['jitter']} parallel={r['parallel']} motion={r['motion']}",
    'temporal': lambda r: r['name'],
    'mean_refinement': lambda r: f"{r['profile']} jitter={r['jitter']} variable={r['variable']}",
}


def load(path):
    return json.loads(Path(path).read_text())


def leaves(value, prefix=''):
    """Finite numeric leaves of nested JSON, by path; booleans and strings are not measurements."""
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, (int, float)):
        if math.isfinite(value):
            yield prefix, float(value)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            yield from leaves(item, f'{prefix}.{key}' if prefix else str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from leaves(item, f'{prefix}[{index}]')


def section(record, path):
    for key in path:
        if not isinstance(record, dict) or key not in record:
            return None
        record = record[key]
    return record


def relative(a, b):
    scale = max(abs(a), abs(b))
    return 0. if scale == 0 else abs(a-b)/scale


def compare_values(reference, candidate):
    """The largest relative difference over the numeric leaves present in both, and where."""
    left, right = dict(leaves(reference)), dict(leaves(candidate))
    common = sorted(set(left) & set(right))
    worst, where = max(((relative(left[k], right[k]), k) for k in common), default=(0., None))
    return dict(compared=len(common), only_reference=len(set(left)-set(right)),
                only_candidate=len(set(right)-set(left)), largest_relative=worst, at=where)


def keyed(name, rows):
    """A summary list as rows keyed by identity; without identity fields, the list itself."""
    key = ROW_KEYS.get(name)
    if key is None or not isinstance(rows, list):
        return rows
    try:
        keys = [key(row) for row in rows]
    except (KeyError, TypeError):
        return rows
    if len(set(keys)) != len(keys):
        raise ValueError(f'duplicate rows in summary list {name}')
    return dict(zip(keys, rows))


def worst(rows):
    """The row with the largest relative difference, or None."""
    rows = [r for r in rows if r['compared']]
    return max(rows, key=lambda r: r['largest_relative'], default=None)


def compare_phase(reference, candidate):
    """One phase: per-case section differences, counters, wall times and summary sections."""
    ref_runs, new_runs = load(reference/'runs.json'), load(candidate/'runs.json')
    names = sorted(set(ref_runs) & set(new_runs))
    cases, sections = {}, {name: [] for name in RECORD_SECTIONS}
    same_counters = 0
    for name in names:
        a, b = ref_runs[name], new_runs[name]
        row = dict(status=[a.get('status'), b.get('status')], seconds=[a.get('seconds'), b.get('seconds')],
                   counters={k: [a.get('summary', {}).get(k), b.get('summary', {}).get(k)] for k in COUNTERS})
        same_counters += all(x == y for x, y in row['counters'].values())
        for label, path in RECORD_SECTIONS.items():
            left, right = section(a, path), section(b, path)
            if left is not None and right is not None:
                row[label] = compare_values(left, right)
                sections[label].append(dict(row[label], case=name))
        cases[name] = row
    kind = 'physics' if any(r.get('config', {}).get('case') in ('brio-wu', 'orszag-tang')
                            for r in ref_runs.values()) else 'wave'
    ref_summary = load(reference/'checkpoint.json')['summaries'].get(kind, {})
    new_summary = load(candidate/'checkpoint.json')['summaries'].get(kind, {})
    summary_sections = {key: compare_values(keyed(key, ref_summary[key]), keyed(key, new_summary[key]))
                        for key in SUMMARY_SECTIONS[kind] if key in ref_summary and key in new_summary}
    seconds = lambda runs: sum(r.get('seconds') or 0. for n, r in runs.items() if n in names)
    return dict(
        cases_compared=len(names), only_reference=sorted(set(ref_runs)-set(new_runs)),
        only_candidate=sorted(set(new_runs)-set(ref_runs)),
        cases_with_identical_counters=same_counters,
        largest_by_section={label: worst(rows) for label, rows in sections.items()},
        summary_sections=summary_sections,
        case_seconds=dict(reference=seconds(ref_runs), candidate=seconds(new_runs)),
        cases=cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for side in ('reference', 'candidate'):
        for phase in PHASES:
            parser.add_argument(f'--{side}-{phase}', type=Path, help=f'{side} plan directory of the {phase} phase')
    parser.add_argument('--expectation', default='', help='the expectation registered in the plan, reported verbatim')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output file')
    result = dict(scope='Case-by-case comparison of registered diagnostics; a measurement, not a gate.',
                  expectation=args.expectation, phases={})
    for phase in PHASES:
        reference, candidate = getattr(args, f'reference_{phase}'), getattr(args, f'candidate_{phase}')
        if reference is None or candidate is None:
            continue
        result['phases'][phase] = compare_phase(reference.resolve(), candidate.resolve())
    args.output.write_text(json.dumps(result, indent=1, allow_nan=False)+'\n')
    for phase, item in result['phases'].items():
        largest = {k: (f'{v["largest_relative"]:.2e} {v["case"]}' if v else '-')
                   for k, v in item['largest_by_section'].items()}
        summaries = {k: f'{v["largest_relative"]:.2e}' for k, v in item['summary_sections'].items()}
        print(f'{phase:8} cases {item["cases_compared"]:4} identical counters {item["cases_with_identical_counters"]:4} '
              f'| {largest} | summaries {summaries} | case seconds {item["case_seconds"]["reference"]:.0f} -> '
              f'{item["case_seconds"]["candidate"]:.0f}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
