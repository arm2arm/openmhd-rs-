# M1 final-review evidence (started 2026-11-21)

**M1 is not accepted by this packet yet.** The current-source REANA campaign
and its final output review are pending. The separate
[AI source/evidence review](../../../docs/M1_FINAL_AI_REVIEW.md) conditionally
approves the pinned reference and historical evidence. The owner authorized finishing
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

Preflight: `openmhd-m1-final-preflight-20261121.1` completed successfully.
`preflight/` preserves all eight command logs, execution/runtime metadata and
the original artifact manifest. All 12 remote artifact hashes verify,
including the binary, which remains in the retained remote/local outputs.
The eight commands pass: fmt, strict all-targets/all-features Clippy, 236
debug Rust tests, release build, 163 Python tests, 13 M0 algebra checks,
reference integrity and 245 release/all-target Rust tests. The exported
binary SHA256 is `18afcf0308338e2ea0ea7ef5e03dba46af9d7025f3ccf4a6a48ebbfe800d0725`.

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

The coordinator's `driver/wake_on_completion.py` reads only this driver's
local state and sends an Orca status notification to the existing coordinator
Run when the driver exits. It never consumes Orca mail, starts another
workflow, or accepts M1. This lets the coordinator continue on completion
or a stopped gate without requiring a new owner prompt.

2026-11-22 recovery: a host reboot terminated the detached host processes.
The same unfinished medium workflow was recovered after checking its inputs;
no duplicate case was created. `driver/run_service.py` now provides foreground
supervision through a task-specific login service so the immutable campaign
resumes after reboot. The login plist is removed after confirmed coordinator
notification. The notifier preserves its CLI receipt and leaves any failed
or unknown delivery for the prescribed Orca recovery procedure, without blind
automatic message retries. Earlier state is retained under
`results/m1_final_campaign_tools_20261121/recovery_20261122/`.

## Prescribed-flow applicability and remaining review

`prescribed_applicability_20261121.json` and its generating script verify all
12 historical archive hashes and identify current unchanged driver,
transport, diagnostic, transport-stencil and loop-reference code. Unlike
the 2026-11-10 record, the current gradients prefix has changed: the batched
implementation was reviewed together with the fresh REANA equality and
transport/geometry checks. The separate reviewer approves retaining the
historical prescribed-flow evidence within its kinematic scope. The
applicability JSON preserves the earlier provisional state; the later review
records the disposition. Neither asserts current-binary full-ladder identity.

The separate reviewer inspected the current code/source map, registered
gate coverage, pinned references, all provenance, prescribed-flow
applicability and the measured limiter tradeoff. It found no source blocker
within the declared scope. The reviewer also identified that the original
closed recursive inventory rejected newly added review files. That packaging
finding is resolved by a strict nested boundary: the parent manifest pins
`review/review_sha256.json`, which verifies the complete, separately hashed
review subpacket. `review_report_sha256.json` pins the report in `docs/`.
The independent review's original recorded observations remain unchanged.
Acceptance remains pending the fresh campaign and its final output review.
