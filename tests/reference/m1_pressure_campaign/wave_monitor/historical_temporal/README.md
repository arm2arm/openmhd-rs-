# Temporal reduction cross-check on retained historical data

The unchanged wave monitor's `temporal_pair` routine re-reduces all **32
historical temporal snapshots**, giving **24 comparisons in eight ladders**
for `paper-global-v2` and `bulk-frame-signal-v1`. Every raw final-file hash
matches its archived run record, and all 32 complete records match the
retained local data. The previous independent review's report, source and
provenance also match their archive manifest.

All B/component/A/phi L1, L2 and maximum errors match that archived review
exactly. The largest difference in adjacent cap-ratio orders is
**2.220446049250313e-16**. Actual timestep extrema, step counts and rejection
metadata are preserved. Negative or roundoff-sensitive orders stay in the
report; no temporal-order acceptance threshold is introduced.

This is an implementing-assistant re-analysis of existing data, not a new
independent scientific review, unit-test suite or evolution. It verifies the
snapshot reduction and timestep reporting used by the monitor. It does not
exercise the current-candidate state/configuration check or full report
assembly, and does not replace any pending pressure-candidate temporal run.
The monitor's numerical source is unchanged.

The historical configuration schema has no `riemann_solver` field. The
analysis uses a copy with that absent value represented explicitly as `None`
for within-profile pair matching. It never substitutes pressure-blend metadata,
changes the recorded profile, or edits historical data. The strict current
candidate acceptance check is deliberately not invoked on these old profiles.

`reduction.json.gz` retains the complete measurements, raw hashes, archived
run-map/report hashes and reducer/source hashes. `archive_sha256.json` covers
this directory except itself. This compact archive is not self-contained raw
data: the existing full snapshots remain in the historical download cache
documented by [`m1_completion`](../../../m1_completion/README.md).

From the repository root, with those unchanged raw directories available:

```sh
python3 tests/reference/m1_pressure_campaign/wave_monitor/historical_temporal/reduce.py
```

The command writes a fresh timestamped reduction to
`results/reana_remote_m1_pressure_reuse_20261110/historical_temporal_reduction.json`.
The committed report remains immutable. All new tests and evolutions remain
on REANA; this command only reads and reduces existing snapshots.
