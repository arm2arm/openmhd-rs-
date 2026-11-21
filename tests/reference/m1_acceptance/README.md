# M1 final-review evidence (started 2026-11-21)

**M1 is not accepted by this packet yet.** The current-source REANA campaign
and the separate final AI review are pending. The owner authorized finishing
M1 and making the necessary routine decisions on 2026-11-21; see the
[acceptance sequence](../../../docs/M1_FINAL_ACCEPTANCE_PLAN.md).

## Named configuration

Campaign A: `bulk-frame-heun-quadratic-v1 --projection-screening 1 --riemann
hlld-pressure --potential-limiter smooth-extrema`, iterative projection,
trial fraction 1. This is a single-process, f64, periodic fixed/rigid 2.5D
engineering reference with synchronized timesteps and explicit per-case
Rayon pools. Binary defaults and historical failed controls are unchanged.
No paper/AREPO equivalence, general invariance, TVD or positivity theorem is
claimed. The selected limiter's documented loop-error/extremum tradeoff is
retained, not hidden by a changed gate.

## Independent reductions of completed campaign A

These read existing observations; they run no new evolution and import no
production measurement functions. They were run locally under the REANA
execution policy's read-only-reduction exception. The complete original
execution maps, registered configurations and phase verdicts are in the
[A archive](../m1_iterative_step_campaigns/README.md). Reports pin their raw
input and analysis hashes. Large original CSVs remain on REANA and in the
ignored local results directories.

| Evidence | Inputs / independently recomputed results |
| --- | --- |
| `campaign_a_independent_waves.json.gz` | 112 cases, 48 boost pairs, eight finest-three-point spatial fits, 12 temporal comparisons; all required checks pass. Maximum disagreement with recorded analytic norms: 6.94e-18. |
| `campaign_a_independent_medium.json.gz` | 48 cases / 24 boost pairs, both Alfvén normalizations and the coupled-loop normalization; all pass. |
| `campaign_a_independent_mean.json` | 24 cases / 12 mean-field boost pairs; direct field maxima, transformed energy, positions, volumes and recorded conservative histories; all pass. |
| `campaign_a_independent_physics_boost.json.gz` | All 30 physics cases / 15 pairs, including planar jittered shocks and jittered vortices; all pass. Physical scales are rebuilt from the definitions and recorded initial budget scales. |
| `campaign_a_independent_shock.json.gz` | Twelve primary regular/column Brio cases and four reference ladders; independent 50-digit decimal prefix integrals of the pinned 8192-cell Athena reference over rectangular cells. All pass; maximum norm disagreement 3.82e-16. |
| `campaign_a_independent_vortex.json.gz` | Six primary regular vortex cases and two ladders; independently recover rectangles from raw shared faces and integrate conserved/recovered quantities into 64 bins before comparison to the pinned Athena reference. All pass; maximum norm disagreement 1.11e-16. |

Thus every one of the 99 registered boost pairs across the four phases has
an independent snapshot norm reduction. The wave report also records the
actual temporal dt ranges/cap attainment, rejections, convergence orders and
spatial-fit residual standard errors. Temporal orders remain observations;
no retrospective order gate is added. Eight spatial orders range from
1.8833871 to 1.9589917; their residual standard errors range from .0156 to
.0393. These are fit diagnostics, not statistical confidence intervals.

`campaign_a_independent_summary.json` gives compact results.
`campaign_a_physics_runs_checkpoint.json.gz` and
`campaign_a_physics_provenance_checkpoint.json.gz` preserve the exact adapters
used for the primary reference reductions. The provenance adapter keeps the
historical pinned reference/packet hashes and explicitly adds the actual A
run-map identity; it is not represented as original A execution provenance.
`campaign_a_independent_vortex_bins.json.gz` retains the independently
integrated bins. The shock/vortex reports record every input artifact hash,
including the geometry and projected bins downloaded from the actual A
workflows where older hashes did not match.

`reduce_waves.py`, `reduce_shock.py` and `reduce_vortex.py` are byte-for-byte
copies of the existing independent reducers under
`m1_pressure_campaign/{wave_monitor,reuse_shock_reference,reuse_vortex_reference}`.
`reduce_mean.py` and `reduce_boost_pairs.py` add the same read-only arithmetic
checks for the remaining phase pairs. Conservative histories are inspected
as recorded; these reductions do not rerun the face-flux or divergence
operators. The exact three discrete B-divergence operators are documented
in the [current source audit](../../../docs/M1_CANDIDATE_AUDIT.md).

## Reproduction from retained observations

From the repository root, after obtaining the original phase directories:

```sh
python3 tests/reference/m1_acceptance/prepare_inputs.py waves results/followup_iter-waves_20261117 results/independent_a_waves
python3 tests/reference/m1_acceptance/reduce_waves.py results/independent_a_waves results/independent_a_waves.json
python3 tests/reference/m1_acceptance/prepare_inputs.py physics results/followup_iter-physics_20261117 results/independent_a_physics --client results/limiter_campaign_tools_20261113/reana-command.py
python3 tests/reference/m1_acceptance/reduce_shock.py results/independent_a_physics results/independent_a_shock
python3 tests/reference/m1_acceptance/reduce_vortex.py results/independent_a_physics results/independent_a_vortex
python3 tests/reference/m1_acceptance/reduce_mean.py results/followup_iter-mean_20261117 results/independent_a_mean.json
python3 tests/reference/m1_acceptance/reduce_boost_pairs.py medium results/followup_iter-medium_20261117 results/independent_a_medium.json
python3 tests/reference/m1_acceptance/reduce_boost_pairs.py physics results/followup_iter-physics_20261117 results/independent_a_physics_boost.json
```

Use fresh output paths. `prepare_inputs.py` validates the registered plan and
all artifact hashes, stages only primary reference families for the physics
reducers, and can reuse a `--cache DIRECTORY` only after exact hash matching.
It downloads observations only, never submits or evolves a benchmark.

## Current integrated source and execution

Development source `2bdcea0d28340e7429e10053a641f92d51fcc696` is frozen in
`snapshot.json.gz` (uncompressed SHA256
`b67ce03779a194099983b7ff07c0cafed23e9ea3a9051047492d072255e0160f`).
The one-commit export-fixture revision differs intentionally; the snapshot's
`source_revision` and per-file hashes identify development sources.

Preflight: `openmhd-m1-final-preflight-20261121.1`. Source upload and toolchain
preparation completed; the check/build job was still running at packet
creation. Do not infer passing checks from its running state.

The detached `driver/start_final.py` reuses the archived proven A/B driver,
selects A alone and changes only orchestration paths and failure monitoring.
It waits for the preflight, then executes bounded short, medium + mean,
precondition, and full waves + physics. A verified required failure cancels
unnecessary active siblings across the current concurrent plans. Observation
errors alone never cause cancellation or completion. Client timeouts recover
the original workflows rather than submitting duplicates. The frozen
scientific runners/cases are unchanged. This archive is a source record;
launching the script from the archive location is not a supported resume.

Live state remains under `results/m1_final_campaign_tools_20261121/`;
phase plans will be `results/followup_iter-{medium,mean,waves,physics}_20261121`.
The driver was launched as PID 62987 with a host sleep inhibitor and requires
no chat session to continue. The final packet must archive actual receipts,
logs, source/binary hashes and verdicts. Fresh independent reductions must
then pass, or every reused raw input must be shown byte-identical to the
independently reduced A input. No automatic phase runner accepts M1 itself.

## Prescribed-flow applicability and remaining review

`prescribed_applicability_20261121.json` and its generating script verify all
12 historical archive hashes and identify current unchanged driver,
transport, diagnostic, transport-stencil and loop-reference code. Unlike
the 2026-11-10 record, the current gradients prefix has changed: the batched
implementation must be reviewed together with the fresh REANA equality and
transport/geometry checks. The report explicitly leaves applicability for
the final reviewer. It does not assert current-binary full-ladder identity.

The separate reviewer must assess the current code/source map, registered
gate coverage, pinned references, all provenance, prescribed-flow
applicability and the measured limiter tradeoff. Acceptance remains pending
until that review and the fresh campaign are complete.
