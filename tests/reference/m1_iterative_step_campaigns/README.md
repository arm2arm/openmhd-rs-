# Iterative-projection and step-fraction campaigns (2026-11-17–19, issue #26)

Both campaigns were declared before execution in
[M1_FULL_VALIDATION_PLAN.md](../../../docs/M1_FULL_VALIDATION_PLAN.md#iterative-projection-and-trial-step-fraction-2026-11-17-before-execution),
at the owner's request of 2026-11-17 to validate options 1 and 2 of the
[speed-up review](../perf_identity/README.md). They start from the
configuration that passed the complete registered matrix on 2026-11-14,
`bulk-frame-heun-quadratic-v1 --projection-screening 1 --riemann
hlld-pressure --potential-limiter smooth-extrema`, and change only how it is
solved:

- **A (`iter`):** without `--accelerated-projection`. The same screened
  projected-rate equations and residual tolerances, solved by
  Jacobi-preconditioned CG instead of CG preconditioned with a cached sparse
  Cholesky factor. Archived here: **every registered phase check passes.**
- **B (`step`):** A with `--trial-step-fraction 0.95`. Resumed on 2026-11-19
  after a failed result download; **every registered phase check passes.**
  See section 5, completed in this archive on 2026-11-21.

On 2026-11-19 the owner made A's iterative solve the candidate's standard.
B's step fraction is not adopted and no binary default changed. This is not
M1 acceptance; independent review and the limiter decision remain open.

## 1. What ran

One frozen source, `11d149f` (Rust sources of `e8d228b`), snapshot
`results/reana_submission_followup_20261117`, SHA256 `f1fee181…`
(`snapshot.json`). The shared preflight `openmhd-fu-preflight-20261117`
passed all eight commands on REANA on 2026-11-17 17:33–17:44 UTC:
`cargo fmt --check`, strict Clippy, 175 debug Rust tests, release build,
133 Python tests, 13 M0 checks, the reference-packet check and 184 release
all-target Rust tests (`preflight/`). Every per-case run used its binary
`492b56e0…`.

A detached driver (`driver/driver.py`, log `driver/driver.log.gz`, final
`driver/state.json`) ran the declared sequence. For A:

| Phase | Workflows | Submitted (UTC) | Result |
| --- | --- | --- | --- |
| Short bounded stages | `openmhd-fu-bounded-iter-20261117` | 11-17 17:47 | all four stages pass (`iter/bounded/gate.json`) |
| Medium bounded stage | `openmhd-fu-iter-medium-d3956c4b6924-*` (48) | 11-17 18:37 | pass |
| Mean-field ladder | `openmhd-fu-iter-mean-ad3399344f60-*` (24) | 11-17 20:28 | pass |
| Wave/loop/temporal matrix | `openmhd-fu-iter-waves-d19962efc205-*` (112) | 11-17 21:23 | pass |
| Shock/vortex matrix | `openmhd-fu-iter-physics-15bfbd1c637e-*` (30) | 11-17 21:39 | pass |

The verdict (`iter/verdict.json`, frozen `scripts/fanout_campaign_verdict.py
--iterative-projection`) was written on 2026-11-18 at 10:03 UTC. All seven
phase checks pass: bounded short, bounded medium, mean, wave calibration,
vortex calibration, physics and waves. As registered, every run records the
iterative solve and no cached factorization. `full_m1_accepted` is false.
The driver's precondition check at 20:31 UTC covers only the first three
phases; its "FAIL" lines for the later phases mean "no plan yet".

The 2026-11-17 evening sleep of the uploading Mac interrupted some uploads.
The driver recovered every affected workflow into the same workflow (see the
`recovery:` lines of the log). No case was resubmitted under a new name.

## 2. A: every registered phase check passes

`iter/summary.json` is the output of `summarise_campaign.py`, the summariser of
the 2026-11-14 campaign with its configuration label as an argument. It
collects the production gate evaluations next to the same baseline (the
stopped pressure campaign, default A-transport limiter).

Alfvén ladders, finest-three B L1 order (required: at least 1.8):

| Mesh | Wave | Motion | Order, A | Order, 2026-11-14 | Finest relative B L1 |
| --- | --- | --- | ---: | ---: | ---: |
| regular | travelling | fixed | 1.9362 | 1.9362 | 7.1e-4 |
| regular | travelling | comoving | 1.9362 | 1.9362 | 7.1e-4 |
| regular | standing | fixed | 1.9590 | 1.9590 | 9.3e-4 |
| regular | standing | comoving | 1.9362 | 1.9362 | 7.1e-4 |
| jitter .15 | travelling | fixed | 1.9099 | 1.9099 | 8.0e-4 |
| jitter .15 | travelling | comoving | 1.9099 | 1.9099 | 8.0e-4 |
| jitter .15 | standing | fixed | 1.8834 | 1.8834 | 1.1e-3 |
| jitter .15 | standing | comoving | 1.9099 | 1.9099 | 8.0e-4 |

Boost pairs, all passing:

| Matrix | Kind | Pairs | Largest value | Limit |
| --- | --- | ---: | ---: | ---: |
| waves | Alfvén | 32 | 1.3e-11 | 1e-8 |
| waves | loop | 16 | 1.9e-9 | 1e-3 |
| medium | Alfvén | 16 | 2.9e-12 | 1e-8 |
| medium | loop | 8 | 4.4e-14 | 1e-3 |
| mean | smooth | 12 | 9.3e-15 | 1e-8 |
| physics | shock/vortex | 15 | 7.4e-11 | 1e-8 |

The temporal differences converge at orders 1.98–2.08.

Shock/vortex, finest grid of each family (finest L1, A):

| Family | Gated | ρ | p | vx or Bx | By | Limits |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Brio–Wu regular, nx1024 | yes | .00221 | .00236 | vx .00477 | .00327 | .03, .04, .03, .04 |
| Brio–Wu column jitter | yes | .00236 | .00248 | vx .00505 | .00333 | same |
| Brio–Wu planar jitter | diagnostic | .00677 | .00752 | vx .01215 | .00950 | same |
| Orszag–Tang regular, N256 | yes | .00739 | .01593 | Bx .01447 | .01247 | .06, .1, .1, .1 |
| Orszag–Tang jitter .15 | diagnostic | .00867 | .01850 | Bx .01648 | .01402 | same |

All 30 shock/vortex runs pass their state and diagnostic gates.

## 3. A: reproduction of the 2026-11-14 campaign

**Registered measurement, not a gate.** For every case, the registered
diagnostics of A are compared with the same case on 2026-11-14. The plan
expected roundoff-level agreement, at most 1e-10 relative, and requires a
larger difference to be reported and investigated.

**Result: A reproduces 2026-11-14 to the tolerance of the projection solve,
not to roundoff.** The largest relative differences of the quantities the
plan names are below, from `iter/reproduction_magnitudes.json`:

| Quantity | Values | Largest relative difference | Where |
| --- | ---: | ---: | --- |
| final B, v L1 errors, medium stage | 64 | 7.6e-11 | Alfvén N64 regular fixed boost, v |
| final B, v L1 errors, wave/loop matrix | 160 | **1.6e-9** | Alfvén N128 regular travelling fixed, v (2.587150016e-4 vs 2.587150012e-4) |
| finest-three ladder orders | 8 | 1.4e-10 | regular standing comoving |
| shock/vortex reference L1 errors, 28 cases | 112 | 2.3e-12 | Brio–Wu N256 jitter boost, vx |
| shock/vortex reference L1 errors, 2 cases below | 8 | **1.8e-9** | Orszag–Tang N256 jitter boost, ρ |
| boost-pair statuses | 99 | identical | |

Every gate outcome is the same. The differences exceed the expected 1e-10 by
up to 18 times, and they are explained by the solver:

- **The two solvers stop at different iterates.** Both stop the projection
  solve at a relative residual below 1e-11 (`projected_rate.rs`), so their
  solutions agree only to that tolerance. In the case with the largest error
  difference, the final states of 3,007 Heun steps differ by at most 2.8e-11,
  in vz and bz, against a wave amplitude of 0.1, with identical step and
  rejection counts. The expectation came from six short excerpts on
  2026-11-17, whose final states agreed within 2e-14 (8e-13 in the Brio
  shock).
- **In 4 of 214 cases this flips a discrete decision.**
  - In the two jittered N256 Orszag–Tang cases, 5 and 21 of about 420,000
    HLL fallbacks differ, which gives the 1.8e-9 above.
  - In the two jittered comoving N256 loops, one trial is rejected twice more
    and the run takes one more step out of 19,168. Their final states differ
    by at most 1.3e-13, and their final error values by at most 2.4e-9.

**About the tool.** `scripts/compare_campaign_runs.py` first compared the
summary lists by position. A's driver uploaded the N256 cases first, so its
wave and shock/vortex boost-pair lists are in a different order, and that run
compared different pairs. It is kept, labelled, as
`iter/reproduction_unaligned.json`. The script now matches rows by identity
(pair names, ladder, temporal row, mean-refinement series), with a regression
test. `iter/reproduction.json` is its output.

**Why the generic maximum is misleading.** The registered maximum over every
numeric value also reaches 0.7–1.2. These values are at roundoff level
themselves, so their ratio is of order one by construction:

- Bx errors of a wave whose Bx is the constant mean field (1e-17 to 1e-12);
- the mean-field ladder at machine zero, whose "orders" are ratios of
  1e-17 values;
- boost-pair differences, which are base-versus-boosted roundoff and swing
  between 1e-17 and 5e-9 from one campaign to the other. The 2026-11-14
  largest loop pair, 4.9e-9, is 2e-14 in A, and A's largest is 1.9e-9.

`analyse_reproduction.py`, a post-hoc analysis that is not registered,
separates resolved values (at least 1e-12, with an order resolved only when
its errors are) from roundoff-level ones, family by family. It also records
the cut-off used.

## 4. Wall time (not registered for A)

| Matrix | Case-seconds 2026-11-14 | Case-seconds A |
| --- | ---: | ---: |
| medium | 8,856 | 8,183 |
| mean | 68 | 61 |
| shock/vortex | 175,412 | 84,371 |
| wave/loop | 935,847 | 633,953 |

From the first submission to the verdict, A took 16.3 hours; 2026-11-14 took
25.5. These are not a measurement of the solver alone: A's binary also has
the result-preserving speed-ups of [perf_identity](../perf_identity/README.md),
which the 2026-11-14 binary did not, and the cluster load differed.

## 5. B: resumed and every registered phase check passes

B's precondition was evaluated on 2026-11-17 at 20:44 UTC. The result download
of medium case 0034 had just failed ("REANA download failed"), 13 minutes
after the case had been counted as complete. Every physical check of that
phase passed; only `terminal_without_errors` and
`every_planned_case_completed` failed (`driver/state.json`). The workflow
`openmhd-fu-step-medium-f35cbd4b94b8-0034` finished on REANA at 18:54 UTC
with all its outputs. B's physics and wave plans had not yet been submitted.
This was an observation failure, not a physical one. The failed precondition
is preserved as `step/precondition_download_failure.json`.

At the owner's request, `driver/resume_b.py` resumed B alone at 07:58 UTC on
2026-11-19, using the same frozen source, binary, cases and options. After
the missing result was downloaded, its bounded/medium/mean precondition
passed at 07:59 UTC (`step/precondition.json`). The later-phase "FAIL" lines
there mean "no plan yet", as for A's precondition. The resumed driver skips
completed work and recovers interrupted uploads within their existing
workflow identities.

| Phase | Workflow or prefix | Cases | Result |
| --- | --- | ---: | --- |
| Short bounded stages | `openmhd-fu-bounded-step-20261117` | four stages | pass |
| Medium | `openmhd-fu-step-medium-f35cbd4b94b8-*` | 48 | pass |
| Mean | `openmhd-fu-step-mean-af4c52cb6d3b-*` | 24 | pass |
| Shock/vortex | `openmhd-fu-step-physics-22e28b75daa9-*` | 30 | pass |
| Wave/loop/temporal | `openmhd-fu-step-waves-5e95af9d0b54-*` | 112 | pass |

The driver finished at **16:32:32 UTC on 2026-11-19**. All seven phase
checks pass in `step/verdict.json`; all 214 per-case workflows are terminal,
with no execution failure or remaining observation error. The eight Alfvén
orders are 1.8834–1.9590, above 1.8. All 99 boost-pair evaluations pass:
24 medium, 12 mean, 15 physics and 48 wave/loop. The wave-matrix maxima are
8.34e-12 for Alfvén and 4.51e-11 for loops; physics reaches 2.24e-11.
All 30 shock/vortex state and diagnostic checks pass. These are collected
production evaluations, not an independent scientific review.

**Changed step sequence, measured against A.**
`step/comparison_to_iter.json` applies the registered comparison, and
`step/comparison_to_iter_magnitudes.json` separates named quantities from
component roundoff. `step/reproduction*.json` records the same measurements
against 2026-11-14. Every comparison matches all planned cases and summary
rows by identity.

| Named quantity | Largest relative difference, B versus A |
| --- | ---: |
| Final B/v L1 errors, medium Alfvén cases (64 values) | 6.13e-4 (0.0613%) |
| Final B/v L1 errors, Alfvén/temporal cases (160 values) | 6.60e-4 (0.0660%) |
| Loop passive B L1 diagnostic, medium (16 values) | 2.60e-4 (0.0260%) |
| Loop passive B L1 diagnostic, full matrix (32 values) | 3.41e-4 (0.0341%) |
| Finest-three Alfvén orders (8) | 7.54e-5 |
| Shock/vortex reference L1 errors (120 values) | 1.45e-3 (0.145%) |
| Boost-pair statuses (99) | identical |

The largest shock/vortex difference is Brio–Wu N512 regular boost vx:
.008740437509 in A versus .008753167575 in B. The largest wave/loop
difference is the jittered N128 travelling fixed-mesh v error:
.000293764305 versus .000293570512. No registered gate outcome changes.
Generic maxima still include ratios of tiny constant-Bx or boost residuals;
they do not mean order-one changes in the physical wave errors.
The loop's `passive_A`/`passive_B` errors are recorded separately as
`loop_passive_L1` in the magnitude analysis: the passively transported
reference is a diagnostic, not an exact solution of coupled MHD.

All 24 mean-field and 16 fixed-step temporal final CSVs are byte-identical
to A. The temporal runs are limited by their prescribed dt caps, so they do
not measure the effect of the changed CFL trial fraction. Their reported
time orders remain 1.98–2.08.

| Matrix | Accepted steps A → B | CFL rejections A → B | Case-seconds A → B | Ratio A/B |
| --- | ---: | ---: | ---: | ---: |
| Medium | 105,462 → 74,382 | 69,618 → 0 | 8,183 → 5,510 | 1.49 |
| Mean | 1,520 → 1,520 | 0 → 0 | 61 → 58 | 1.05 |
| Shock/vortex | 104,144 → 72,952 | 69,676 → 0 | 84,371 → 49,260 | 1.71 |
| Wave/loop/temporal | 745,880 → 602,660 | 323,726 → 0 | 633,953 → 395,030 | 1.60 |

B has no CFL, state or geometry rejection across these matrices. Summed
case time is 449,857 seconds versus A's 726,567 (ratio 1.62). These are
observations on shared cluster nodes at different times, with the same
binary and per-case resources, not a controlled measurement of speed-up.
The 8.6-hour resumed interval excludes B's earlier bounded/medium/mean work
and the intervening pause; it must not be compared directly with A's full
16.3-hour campaign interval.

**Archive verification on 2026-11-21.** The frozen verdict reducer and the
summary reproduce the archived JSON exactly. Each of 214 execution receipts,
run records and final CSVs matches its downloaded REANA artifact manifest
(642 file checks); receipts and manifests are retained in
`step/case_receipts.json.gz`. `step/verification.json` records this check and
the 40 identical final snapshots above. The prior driver state is preserved
as `driver/state_before_resume.json`; the resumed log retains the original
log as its exact prefix. No tests or evolutions were launched in this
postprocessing session. B remains unadopted; `full_m1_accepted` stays false.

## 6. Files and reproduction

- `preflight/`: the shared preflight.
- `snapshot.json`: the frozen source.
- `driver/`: the driver, its resume wrapper, combined log, pre-resume state
  (A complete, B's failed download) and final state of the B-only resume.
- `iter/verdict.json`, `iter/precondition.json`: the frozen verdict of A and
  its precondition check.
- `iter/bounded/`: the short bounded stages.
- `iter/plans/`: per phase, the case specifications and workflow identities
  (`*_plan.json.gz`), the submission record, the monitor's final checkpoint
  with the phase summaries, and the run records (`*_runs.json.gz`).
- `iter/summary.json`: section 2.
- `iter/reproduction.json`, `iter/reproduction_unaligned.json`,
  `iter/reproduction_magnitudes.json`: section 3.
- `step/`: B's bounded outputs, plans, summary, preconditions, verdict,
  comparisons, execution receipts and verification described in section 5.
  Its eight bounded command logs are in `bounded/logs/`. This archive's
  `.gitignore` retains those logs and the existing preflight/A logs despite
  the repository-wide exclusion of runtime log directories.
- `archive_sha256.json`: covers the other archived files in this directory.

Raw snapshots are local under `results/followup_{iter,step}-*_20261117` and
remain in each REANA workspace. From the repository root:

```sh
B=results/reana_remote_m1_pressure_reuse_20261110/source/results/reana_m1-campaign/physics/runs.json
python3 tests/reference/m1_iterative_step_campaigns/summarise_campaign.py \
  --medium results/followup_iter-medium_20261117 --mean results/followup_iter-mean_20261117 \
  --physics results/followup_iter-physics_20261117 --waves results/followup_iter-waves_20261117 \
  --baseline-physics $B --verdict results/followup_iter_verdict_20261117.json \
  --configuration "<as recorded in iter/summary.json>" --output /tmp/summary.json
args=(); for p in medium mean physics waves; do
  args+=(--reference-$p results/limiter_campaign_full-${p}_20261113 --candidate-$p results/followup_iter-${p}_20261117)
done
python3 scripts/compare_campaign_runs.py "${args[@]}" --expectation "..." --output /tmp/reproduction.json
# From the archived records alone; the final-state comparison needs the raw snapshots.
python3 tests/reference/m1_iterative_step_campaigns/analyse_reproduction.py \
  --raw-reference results/limiter_campaign_full-waves_20261113 --raw-candidate results/followup_iter-waves_20261117 \
  --final-state-case alfven_bulk-frame-heun-quadratic-v1_v0.0_j0.0_fixed_n128_base \
  --final-state-case loop_bulk-frame-heun-quadratic-v1_v0.0_j0.15_comoving_n256_base \
  --output /tmp/reproduction_magnitudes.json
# B versus A, from archived records alone (fresh output required).
python3 tests/reference/m1_iterative_step_campaigns/analyse_reproduction.py \
  --reference iter --candidate step --output /tmp/step_vs_iter_magnitudes.json
# B versus A, the comparison of registered diagnostics from the local plans.
args=(); for p in medium mean physics waves; do
  args+=(--reference-$p results/followup_iter-${p}_20261117 --candidate-$p results/followup_step-${p}_20261117)
done
python3 scripts/compare_campaign_runs.py "${args[@]}" \
  --expectation "B measures the effect of the changed step sequence, together with the wall times of both; a measurement, not a gate." \
  --output /tmp/step_vs_iter.json
# For B versus 2026-11-14, use the original reference directories above and
# --reference 2026-11-14 --candidate step for the archived magnitude analysis.
```
