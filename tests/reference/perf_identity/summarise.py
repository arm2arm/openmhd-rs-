#!/usr/bin/env python3
"""Reduce downloaded REANA perf-compare outputs to the numbers this packet keeps.

Keeps byte-identity results, timings, profile phases, step counters and the
variant measurements. Drops commands, paths and anything else that names a
workspace. The snapshot is paired with the run by its SHA256, so a run is
never attributed to the wrong source revision.

  python3 tests/reference/perf_identity/summarise.py --label 2026-11-17 \\
      --outputs <downloaded outputs directory> --snapshot <submission>/snapshot.json
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
RESULTS = HERE/'results.json'
PHASES = ('mesh/build', 'step', 'stage', 'trial', 'stage/projection', 'projection/solve',
          'projection/setup/assemble', 'projection/setup/factorize', 'projection/curl',
          'projection/curl-transpose', 'projection/iterations', 'fluid/rate', 'fluid/rate/accumulate',
          'stage/primitive-gradients', 'fit/magnetic', 'stage/auxiliary', 'stage/potential-rate', 'bound',
          'endpoint', 'mesh/validate', 'recover')
TIMES = ('mesh_seconds', 'initialization_seconds', 'evolution_seconds', 'total_seconds')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_row(row):
    """The physical identity and the timings of one run, without its command."""
    timing = row['timing']
    phases = timing.get('phases', {})
    return dict(status=row['status'], steps=row['steps'], rejected_cfl=row['rejected_cfl'],
                physical_sha256=row['physical_sha256'],
                **{k: timing[k] for k in TIMES}, threads=timing['threads'],
                peak_rss_mib=round(row['peak_child_rss_kib']/1024) if 'peak_child_rss_kib' in row else None,
                phases={k: phases[k] for k in PHASES if k in phases},
                counters={k: v[1] for k, v in phases.items() if k.startswith(('trial/rejected', 'step/first'))})


def reduce(outputs, snapshot):
    report = json.loads((outputs/'perf-compare/report.json').read_text())
    runtime = json.loads((outputs/'runtime.json').read_text())
    execution = json.loads((outputs/'execution.json').read_text())
    if sha(snapshot) != runtime['snapshot_sha256'] or execution['snapshot_sha256'] != runtime['snapshot_sha256']:
        raise ValueError('Snapshot does not belong to this run')
    if report['status'] != 'completed':
        raise ValueError('Comparison did not complete: '+str(report.get('error')))
    source = json.loads(snapshot.read_text())
    cases = {}
    for key, comparison in report['comparisons'].items():
        cases[key] = dict(bit_identical=comparison['bit_identical'], files_compared=comparison['files_compared'],
                          different_files=comparison['different_files'],
                          baseline_source=comparison.get('baseline_timing', 'completed'),
                          evolution_speedup=comparison['evolution_speedup'], total_speedup=comparison['total_speedup'],
                          baseline=run_row(report['runs'][key+'_baseline']),
                          candidate=run_row(report['runs'][key+'_candidate']))
    variants = {}
    for variant, measured in report.get('variants', {}).items():
        variants[variant] = {}
        for name, v in measured.items():
            if v['status'] != 'completed':
                variants[variant][name] = dict(status=v['status'], error=v.get('error'))
                continue
            row = report['runs'].get(f'{name}_{variant}_candidate')
            variants[variant][name] = dict(
                status='completed', largest_physical_difference=v['largest_physical_difference'],
                largest_potential_difference=v['largest_potential_difference'], counters=v['counters'],
                evolution_seconds=v['evolution_seconds'], total_seconds=v['total_seconds'],
                peak_rss_mib=[round(x/1024) for x in v['peak_child_rss_kib']], projections=v['projections'],
                iterations=v['iterations'], run=run_row(row) if row else None)
    return dict(
        scope=report['scope'], source_revision=source['source_revision'], snapshot_sha256=runtime['snapshot_sha256'],
        image=runtime['image'], rustc=runtime['rustc'], platform=runtime['platform'],
        visible_cpus=report['visible_cpus'], threads=report['threads'], configuration=report['configuration'],
        started_utc=execution['started_utc'], ended_utc=execution['ended_utc'],
        baseline_binary_sha256=report['baseline_binary_sha256'],
        candidate_binary_sha256=report['candidate_binary_sha256'],
        all_bit_identical=report['all_bit_identical'], cases=cases, variants=variants)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--label', required=True)
    parser.add_argument('--outputs', type=Path, required=True, help='downloaded outputs/ of a perf-compare run')
    parser.add_argument('--snapshot', type=Path, required=True, help='snapshot.json of its submission')
    args = parser.parse_args()
    results = json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    results[args.label] = reduce(args.outputs, args.snapshot)
    text = json.dumps(results, indent=1, allow_nan=False)+'\n'
    # The image digest has an '@' too; refuse e-mail addresses, not digests.
    for marker in ('/Users/', '/var/reana', '/home/'):
        if marker in text:
            raise ValueError('Workspace path in the reduction: '+marker)
    if re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}', text):
        raise ValueError('Address in the reduction')
    RESULTS.write_text(text)
    row = results[args.label]
    print(args.label, row['source_revision'][:7], 'all identical', row['all_bit_identical'], 'cases', len(row['cases']))


if __name__ == '__main__':
    main()
