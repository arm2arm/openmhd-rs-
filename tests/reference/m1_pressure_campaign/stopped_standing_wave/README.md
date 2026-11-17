# Stopped pressure campaign: standing-wave convergence failure

Workflow `openmhd-m1-pressure-reuse-20261110.1`, UUID
`7a615758-c141-4903-a2ea-8da3094ddd58`, was stopped at the owner's request on
2026-11-11 at **11:53:34 UTC**, after 109,072 seconds. `workflow_status.json`
records the authoritative terminal state. No new numerical test was run to
create this archive.

The terminal wave run map contains **104/112 completed** cases: all 64 Alfvén
cases, all 16 temporal cases and 24/32 loops. The eight N256 loops were
interrupted. The physics summary reports all registered gates passing for
30/30 completed cases; that production report is not a new independent review
of the full physics matrix.

The independent read-only check used the preceding **103-case** checkpoint,
retained separately with its exact manifest and script hashes. Eight raw final
snapshots verify against their run records and the independent analytic B
norms agree with production to less than 4e-18. Both standing, fixed-mesh
base-frame ladders fail the unchanged finest-three convergence gate:

| Mesh | B L1 order, N64/128/256 | Required | Finest B L1 / 0.1 | Allowed |
| --- | ---: | ---: | ---: | ---: |
| Regular | 1.659066006399202 | ≥ 1.8 | 0.0014996894081165492 | ≤ 0.02 |
| Jitter 0.15 | 1.7704518931031932 | ≥ 1.8 | 0.0012823230817238323 | ≤ 0.02 |

Passing amplitude, positivity or conservation checks does not override the
failed convergence orders. M1 remains unaccepted. This observation does not
establish the numerical cause; bounded diagnosis is still required.

## Evidence and reproduction boundary

- `standing_wave_gate_check.json` records the independently measured norms,
  orders, execution times, all eight raw final hashes and the observation's
  exact input/script hashes.
- `wave_runs_103.json.gz` and `wave_manifest.json.gz` preserve those original
  inputs. `wave_runs_terminal.json.gz` is the later 104-case checkpoint; do
  not substitute it when checking the original report's run-map hash.
- `check_standing_wave_gates.py` is the original read-only downloader/reducer.
  It imports no production error routine. Its credential-handling CLI adapter
  lives outside the repository at `/tmp/openmhd-reana-command.py`; credentials
  are neither required nor included for reviewing the archived measurements.
- The raw CSVs remain in the stopped REANA workspace under
  `source/results/reana_m1-campaign/waves/<case-name>/final.csv`, and in the
  local download at `results/reana_remote_m1_pressure_reuse_20261110/` under
  the same path. Their hashes were rechecked when archiving this evidence.
  They are not duplicated here, so this compact archive is not a self-contained
  raw-data reproduction package. A rerun of the original script requires those
  inputs (or authorized download access) and writes a new observation.
- The campaign/provenance JSON files are last-written checkpoints. Any
  `running` label or missing final manifest in them does not override the
  authoritative stopped status.

`archive_sha256.json` hashes every other file in this directory. This is an
implementing-assistant evidence check, not an independent scientific review.

## Execution follow-up

`run_m1_wave_loop.py` evaluates combined gates only after every future finishes.
Consequently the long loops continued after these ladders had completed.
Future execution must evaluate completed pairs/ladders promptly and cancel
unnecessary siblings on verified required failure. The owner's new policy is
one concurrent REANA workflow per independent case, without the old aggregate
24-core/64-GB cap; see [the execution policy](../../../../docs/REANA.md#current-execution-policy-2026-11-11).
The legacy monolithic runner has not yet been converted.
