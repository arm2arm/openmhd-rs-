# Incremental independent wave/loop monitor

`reduce_checkpoint.py` analyzes completed snapshots while the frozen REANA
wave phase is still running. It imports no production measurement routine
and changes neither the simulator nor the acceptance runner. This supports
the existing instruction to stop unnecessary work when a required failure
is verified, without waiting for every case in a concurrent batch to finish.
It does not stop REANA itself or certify M1 acceptance.

The reducer checks final-file hashes, cell IDs, volumes, finite/positive
states and matching configurations. It independently recomputes analytic
Alfvén component/vector errors and both registered boost normalizations;
coupled loops retain the registered magnetic-amplitude normalization. It
also checks recorded history extrema/budgets, distinguishing these exported
diagnostics from an independent evolution. Full spatial gates are evaluated
only when all four resolutions of a family are present. Temporal B/A/phi
errors, successive orders, actual timesteps and rejection counters are
reported without inventing an order threshold. Missing files are observation
errors, distinct from recorded failed runs or measured gate failures.

Completed per-case and pair reductions are cached by the complete run-record
hash and analysis-script hash. Even on cache reuse, every final snapshot's
checksum is rechecked. This avoids repeatedly parsing and reducing the same
large CSVs on the laptop. Reports are mutable checkpoints; their explicitly
false `full_m1_accepted` field must not be used as an acceptance decision.

Measured against already completed, downloaded REANA data:

| Dataset | Runs / boost pairs | Largest analytic-error discrepancy | Largest normalized boost discrepancy |
| --- | ---: | ---: | ---: |
| Medium N32/N64 | 48 / 24 | 5.63785e-18 | 1.15805e-22 |
| N128 calibration | 2 / 1 | 1.78893e-18 | 1.67239e-28 |

All 50 run checks and 25 pairs pass. All eight incomplete spatial ladders
correctly remain pending. A second medium analysis reuses all 48 cases and
24 pairs after rechecking their file hashes. These are reductions of existing
physical data, not new evolutions or a new unit-test count. The full
current-candidate spatial and temporal report assembly awaits actual complete
wave data; this evidence does not claim it has already been measured.

A subsequent [historical temporal cross-check](historical_temporal/README.md)
re-reduces 32 retained snapshots from the two earlier profiles using the
unchanged temporal-pair routine. All 24 B/component/A/phi error comparisons
match their archived independent review exactly; adjacent orders differ by
at most 2.22045e-16. This validates that reduction path on existing data, not
the current candidate or its still-pending temporal packet.

The compressed reports and `verification.json` pin the exact run maps,
manifests and production summaries. Original execution evidence remains in
[`reuse_validation/medium`](../reuse_validation/medium/) and
[`reuse_calibration/wave`](../reuse_calibration/wave/). These medium/calibration
data come from
`openmhd-m1-pressure-reuse-20261110.1`, frozen numerical source parent
`4f491de`, binary SHA256
`90d40a752e357ed6a459e828d8a48cba51eed13549229271583f89fb7384a426`.

After downloading a phase's `manifest.json`, `runs.json` and each completed
case's checksum-matching `final.csv`, run from the repository root:

```sh
python3 tests/reference/m1_pressure_campaign/wave_monitor/reduce_checkpoint.py \
  results/reana_remote_m1_pressure_reuse_20261110/source/results/reana_m1-campaign/waves \
  results/reana_remote_m1_pressure_reuse_20261110/wave_checkpoint.json
```

For the measured medium/calibration datasets, substitute `bounded/waves_medium`
or `calibration_wave` as the input directory and use separate report paths.
Reusing a report path enables the validated cache path. Inspect any
`verified_required_failure` and its named raw evidence before stopping the
same workflow; a failed download is not a scientific result and must never
trigger a replacement run. Final source hashes, complete coverage, reference
applicability and scientific review remain separate acceptance requirements.
