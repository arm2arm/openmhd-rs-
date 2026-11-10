"""Re-reduce retained temporal snapshots; no new test/evolution execution."""
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path.cwd()
SOURCE = ROOT / 'tests/reference/m1_pressure_campaign/wave_monitor/reduce_checkpoint.py'
REVIEW = ROOT / 'tests/reference/m1_completion/ai_review/temporal_matrix_report.json'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
spec = importlib.util.spec_from_file_location('wave_checkpoint_reducer', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
review_archive = json.loads((REVIEW.parent / 'archive_sha256.json').read_text())
for name in ('temporal_matrix_report.json', 'temporal_matrix_check.py',
             'temporal_matrix_review_provenance.json'):
    assert sha(REVIEW.parent / name) == review_archive[name]
review = json.loads(REVIEW.read_text())
results = []
inputs = {}
for label, profile in (('original', 'paper-global-v2'),
                       ('candidate', 'bulk-frame-signal-v1')):
    archive = ROOT / 'tests/reference/m1_completion' / label / 'runs.json.gz'
    archived = json.loads(gzip.decompress(archive.read_bytes()))
    raw = ROOT / 'results/issue7_completion_20261106' / label
    live = json.loads((raw / 'runs.json').read_text())
    names = [name for name in archived if name.startswith('temporal_')]
    assert len(names) == 16
    records = {}
    hashes = {}
    for name in names:
        original = archived[name]
        assert original == live[name], name
        assert original['status'] == 'completed'
        assert original['config']['profile'] == profile
        assert 'riemann_solver' not in original['config']
        final = raw / name / 'final.csv'
        assert sha(final) == original['sha256']['final.csv']
        hashes[name] = sha(final)
        # Schema-only view: explicitly unspecified legacy metadata, not a
        # substituted current-candidate flux or changed scientific record.
        # The current candidate state_check is deliberately not invoked.
        records[name] = deepcopy(original)
        records[name]['config']['riemann_solver'] = None
    inputs[label] = dict(profile=profile, archived_run_map=str(archive.relative_to(ROOT)),
                         archived_run_map_sha256=sha(archive),
                         raw_run_map_sha256=sha(raw / 'runs.json'),
                         unchanged_archived_records=len(names), final_sha256=hashes)
    for ladder in review['ladders']:
        if ladder['profile'] != profile:
            continue
        comparisons = []
        for expected in ladder['comparisons']:
            actual = module.temporal_pair(raw, expected['name'], expected['reference'], records)
            old = expected['times']['final']['errors']
            difference = max(abs(actual['errors'][field][norm] - old[field][norm])
                             for field in actual['errors'] for norm in ('L1', 'L2', 'max'))
            assert difference < 2e-13, (expected['name'], difference)
            summary = records[expected['name']]['summary']
            assert actual['actual_dt_max'] == summary['dt_max']
            assert actual['actual_dt_min'] == summary['dt_min']
            assert actual['steps'] == summary['steps']
            assert actual['rejected_state'] == summary['rejected_state']
            assert actual['rejected_cfl'] == summary['rejected_cfl']
            actual['maximum_archived_norm_disagreement'] = difference
            comparisons.append(actual)
        orders = {field: [math.log(left['errors'][field]['L1']/right['errors'][field]['L1']) /
                          math.log(left['dt']/right['dt'])
                          if left['errors'][field]['L1'] > 0 and right['errors'][field]['L1'] > 0 else None
                          for left, right in zip(comparisons, comparisons[1:])]
                  for field in comparisons[0]['errors']}
        order_difference = 0.
        for field, values in orders.items():
            old = ladder['adjacent_cap_ratio_L1_orders']['final'][field]
            for value, reference in zip(values, old):
                if value is None or reference is None:
                    assert value is reference
                else:
                    order_difference = max(order_difference, abs(value-reference))
        assert order_difference < 2e-13
        results.append(dict(profile=profile, parallel=ladder['parallel'], jitter=ladder['jitter'],
                            comparisons=comparisons, adjacent_orders=orders,
                            maximum_archived_order_disagreement=order_difference))
report = dict(created_utc=datetime.now(timezone.utc).isoformat(),
              scope='Read-only re-reduction of 32 retained historical runs / 24 temporal comparisons. Verifies unchanged raw-snapshot temporal formulas and timestep metadata; does not exercise current-candidate state/configuration acceptance, the full main-loop assembly, or certify the running candidate. No simulations or unit-test suites were run.',
              metadata_adapter='Each in-memory legacy configuration receives riemann_solver=None to represent its absent field. Existing profile, values and raw files remain unchanged. No current-candidate metadata is substituted.',
              reducer=str(SOURCE.relative_to(ROOT)), reducer_sha256=sha(SOURCE),
              analysis_script_sha256=sha(Path(__file__)),
              archived_independent_report=str(REVIEW.relative_to(ROOT)),
              archived_independent_report_sha256=sha(REVIEW), inputs=inputs, ladders=results,
              full_m1_accepted=False)
output = ROOT / 'results/reana_remote_m1_pressure_reuse_20261110/historical_temporal_reduction.json'
output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
print('Historical snapshots:', sum(v['unchanged_archived_records'] for v in inputs.values()))
print('Temporal comparisons:', sum(len(row['comparisons']) for row in results))
print('Maximum norm difference:', max(c['maximum_archived_norm_disagreement'] for r in results for c in r['comparisons']))
print('Maximum order difference:', max(r['maximum_archived_order_disagreement'] for r in results))
print('Current candidate temporal gates remain pending.')
