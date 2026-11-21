# Fresh integrated-source precondition evidence

Checkpoint, 2026-11-22: medium 48/48 and mean-field 24/24 cases completed on
REANA. The separate bounded-short workflow also passed. These are the three
required precondition phases; the 112-wave and 30-physics phases and final
output review remain pending. **M1 is not accepted.**

Each phase retains its immutable registered specifications, exact plan,
run map and terminal checkpoint, plus independent provenance and arithmetic
reports. All JSON files use deterministic gzip compression. Provenance
records preserve every execution receipt and remote artifact manifest.

`bounded/` retains the separate completed legacy bounded workflow's gate,
execution/runtime metadata, eight logs and original artifact manifest.
All 12 downloaded artifact hashes were verified, including its large raw
archive (retained on REANA and locally, outside Git). The packet verifier
checks the 11 retained artifacts after decompression. All four registered
stages pass; the symmetry stage intentionally includes a failing historical
control and records return code 1, while its candidate-specific checks pass.
The top-level bounded runner returns 0. Its own freshly built binary is
`090acac224588ff802f430290627f1f59ce764b0797e007c66708b0668c3a6ea`,
distinct from the reused preflight binary in the 214-case matrix. Its source
map matches the same frozen submission; no binary identity is inferred
between these separately built workflows.

`../verify_fresh_phase.py` reads every staged input part, reconstructs the
frozen source archive and binary hashes, checks each command/configuration,
resource declarations, preflight identity, record and downloaded final CSV,
and examines the recorded positive-state/conservative histories. Absent raw
outputs are explicitly listed as **not byte verified**; pinning their remote
manifest does not assert those files were downloaded. The report records
actual cgroup observations separately from Kubernetes resource declarations.

| Phase | Fresh cases / boost pairs | Maximum recorded normalized budget | Accepted steps / CFL retries / HLL fallbacks |
| --- | --- | --- | --- |
| Medium | 48 / 24 | 5.131e-14 | 105462 / 69618 / 924 |
| Mean | 24 / 12 | 2.699e-14 | 1520 / 0 / 0 |

All 72 final CSVs are byte-identical to their campaign A counterparts,
although this campaign uses the fresh integrated-source preflight binary.
The two original independent reducers were nevertheless rerun on the fresh
snapshots. All 36 pairs pass; their largest norm disagreements with recorded
production measurements are 8.49e-27 (medium) and zero (mean). No new
evolution or local executable test was run for these reductions.

Reproduce from the retained original observations, using fresh output paths:

```sh
python3 tests/reference/m1_acceptance/verify_fresh_phase.py medium results/followup_iter-medium_20261121 results/m1_final_campaign_cases_20261121/iter-medium.json results/fresh_medium_receipts.json
python3 tests/reference/m1_acceptance/verify_fresh_phase.py mean results/followup_iter-mean_20261121 results/m1_final_campaign_cases_20261121/iter-mean.json results/fresh_mean_receipts.json
python3 tests/reference/m1_acceptance/reduce_boost_pairs.py medium results/followup_iter-medium_20261121 results/fresh_medium_norms.json
python3 tests/reference/m1_acceptance/reduce_mean.py results/followup_iter-mean_20261121 results/fresh_mean_norms.json
```

Large raw CSVs, binary and source upload parts remain in the original REANA
workflows and ignored local `results/` directories. The parent packet's
closed manifest hashes this complete checkpoint, independently of the
separately bounded reviewer subpacket.
