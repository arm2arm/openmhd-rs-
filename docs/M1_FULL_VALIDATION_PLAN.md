# Plan for the unchanged full M1 validation matrix (issue #22 → #7)

Registered 2026-11-09, before any full-matrix run of this configuration. This
is a preregistration, not a result. No long job had been started when it was
registered. The authorized REANA campaign executed the sequence
below; see [the current checkpoint](CODEX_HANDOFF.md#acceptance-campaign-checkpoint-2026-11-10).
Full M1 acceptance remains pending.

Update: the owner authorized new REANA tests and long runs on 2026-11-09,
with the instruction to continue through M0/M1 acceptance. The short gate
now passes ([results](M1_SHOCK_INVESTIGATION.md#bounded-m1-gate-for-the-screened-candidate-2026-11-09-issue-22)).
Run the medium gate and calibration on REANA before escalating to full
matrices. This authorization supersedes the go-ahead requirement below;
it does not waive a scientific gate or change the resource limits.

Measured update (2026-11-10): all five bounded stages and the 24-run candidate
mean-field boost ladder and N128 calibration pass. The N32→N64
wave orders are only 1.565–1.769, so full fine-grid convergence remains
unproven. See [the source and measured evidence](../tests/reference/m1_reana_bounded/README.md).
A separate reporting correction restores omitted candidate mean-refinement
rows without changing evolutions; its separate REANA audit passes all 68
Python tests and all mean-report checks.
The [N128 travelling-wave calibration pair](../tests/reference/m1_reana_calibration/README.md)
now completes and passes its accuracy/state/boost checks. The matching
N64→N128 B L1 order is 1.841645; this two-grid observation is not the full
registered convergence fit. Vortex calibration also completes and passes:
normalized mean-B drift .000137274 and limited-face divergence RMS .0361845.
The full physics matrix used ten workers and two threads each, selected from
measured peak process RSS and the preregistered reserve. It was stopped at
01:16:53 UTC after a verified N1024 column-jitter Brio boost failure (maximum
normalized L1 5.81839e-6, limit 1e-8). Twenty of thirty runs completed; the
full wave matrix did not start. See the [failure record](../tests/reference/m1_column_boost/README.md).
Bounded reproduction and a tested correction are required before escalation.

The first REANA preflight passed format, strict Clippy, 133 workspace Rust
tests, 57 Python tests and both M0 checks, but the laptop's 30-second case
limit interrupted the nx512 × ny8 short shock and both N32 jittered vortices.
The workflow was stopped with its failed and partial records preserved.
Completed N32 full-time waves took 20–49 seconds, roughly 2.5–3 times the
local cost basis. The remote campaign therefore declares 120-second short
case limits and 1800-second medium case limits before rerunning. Local
defaults remain 30/600 seconds. These are execution budgets, not changes to
physical time, grids or acceptance thresholds; previous timeouts stay failures.
The runner now stops immediately at the first failed stage.

## Explicit HLL continuation (2026-11-10, before campaign execution)

The bounded nx1024 comparison in `8d53b79` retains all 24 original HLLD
scientific files and passes both HLL boost pairs, state/diagnostic and
finest-grid reference checks. It does not establish full M1 acceptance.
[Evidence](../tests/reference/m1_column_boost/hll_comparator/README.md).

The next immutable REANA campaign uses the same quadratic profile, accelerated
projection and screening 1, with **explicit `--riemann hll`**. Its Riemann fan
is an additional engineering departure from the paper's HLLD. Defaults remain
HLLD. No Rust numerical source changes after the passing comparison are
needed for this campaign; the runners now propagate, record and validate the
flux choice. Candidate manifests carry `riemann_solver=hll`; binary summaries
must carry `hll-comparator-v1`. Literal-paper symmetry controls retain HLLD.
Missing, mixed or wrong flux metadata fails configuration validation.

Execute `run_m1_campaign.py --riemann hll --jobs 24` on REANA via the new
`m1-hll-campaign` study: full workspace/M0 checks, the unchanged five bounded
stages, 24-run mean-field ladder, N128 wave/vortex calibration, 30-run full
physics ladder, then the 112-run wave/loop/temporal matrix. Every preceding
phase must pass; a failed or missing phase stops escalation. The original
reference data, grids, physical times and numerical acceptance thresholds
below all apply without alteration. HLL's accuracy cost remains unmeasured
outside the finest shock comparison. No M1 issue closes automatically.

Resource/case limits stay as registered below: at most 24 aggregate cores and
64 GB, short-case caps 120 s, medium caps 1800 s, calibration caps 7200 s,
full-case caps 86400 s, and memory-based worker allocation with an 8-GB reserve.
This is a prospective execution declaration, not a passing result.

Measured continuation: the HLL campaign passes all workspace/M0 checks and
the first three short stages, then fails the regular N32 vortex normalized
limited-face divergence gate (.385293, limit .1). It stops before medium or
larger execution. [Raw failure and independent norm reduction](../tests/reference/m1_hll_campaign/bounded_failure/README.md).
The [next bounded shock-sensor trial](M1_SHOCK_SENSOR_PLAN.md) is separate;
none of these observations changes the full gates below.

## Configuration under test

Prospective pressure-blend continuation (2026-11-10): **only if** the
[24-case focused trial](M1_PRESSURE_BLEND_PLAN.md) passes, execute the same
sequence via `m1-pressure-campaign` / `--riemann hlld-pressure`. Candidate
summaries must carry `hlld-pressure-blend-v1`; literal-paper controls remain
HLLD. All five bounded stages, mean ladder, calibration, full physics and full
wave/loop/temporal phases retain the grids, times, gates and resource limits
below. No numerical change after a passing focused comparison is implied by
this runner option. At registration the focused comparison is still in
preflight; no pressure-blend physical pass is claimed and no full campaign
has started. The wrapper's new routing will receive its checks on REANA.

| Item | Value |
| --- | --- |
| Profile | `bulk-frame-heun-quadratic-v1` (engineering comparator, not the paper endpoint method) |
| Projection | `--accelerated-projection --projection-screening 1` |
| Units / EOS | dimensionless, mu0=1, f64; gamma 5/3 (waves, loop, vortex), 2 (Brio) |
| Boundaries / motion | periodic; fixed or rigid mesh, global timesteps, CFL .3 |
| Excluded | floors, energy resets, resistivity, entropy closure |

The binary default stays `paper-global-v2`. Screening 1 is part of the tested
configuration because the unscreened candidate fails the jittered vortex
mean-field drift gate at N32 (.0037 against .001) and screening 1 passes it
(.00061); see [the bounded results](M1_SHOCK_INVESTIGATION.md#bounded-m1-gate-for-the-screened-candidate-2026-11-09-issue-22).
Screening 3 lost positivity on one hard shock mesh, so the margin is narrow
and this value is a development choice, not a validated constant.

## Precondition

`python3 scripts/run_m1_bounded.py --medium --output-dir <fresh>` must report
`bounded_blockers_closed: true` for the exact source revision that is
submitted. A failed, timed-out or missing stage blocks submission.

## Gates (all unchanged except the owner-approved Bx amendment)

| Family | Runner | Registered runs | Gate |
| --- | --- | --- | --- |
| Alfvén waves | `run_m1_wave_loop.py --suite physical --temporal` | N32/64/128/256, t=1, regular and jitter .15, travelling and standing, fixed and comoving, each with joint boost | finest-three B order >=1.8, finest relative B L1 <=.02, positivity, 1e-10 budgets, boost 1e-8 under both normalizations |
| Field loop | same | N32/64/128/256, t=1, regular and jitter, fixed and comoving, with boost | boost-relative B L1 <=1e-3, positivity, budgets |
| Temporal | same | N64, dt caps 4e-4, 2e-4, 1e-4 against 2.5e-5 | reported successive orders |
| Brio–Wu | `run_m1_physics.py` | nx256/512/1024 x ny4, t=.1; regular, planar jitter, column jitter; with boost | finest scaled L1 limits (rho .03, p .04, vx .03, By .04) and finest below coarsest on regular and column meshes; Bx 1e-8 on regular and column meshes; seam isolation; boost 1e-8; positivity; budgets |
| Orszag–Tang | same | N64/128/256, t=.5, regular and jitter, with boost | finest binned L1 limits, mean-B drift <=1e-3, limited-face div B RMS <=.1, boost, positivity, budgets |

Planar-jitter Brio profile errors and Bx are diagnostics
(`benchmarks/m0/packet.json`, `benchmarks/m1/shock-bx-amendment.json`). The
prescribed kinematic loop packet (`run_prescribed_loop.py`) is independent of
the evolution profile and is not rerun.

## Measured cost basis

One thread per case, three concurrent cases, this Mac (18 cores), unscreened
candidate, 2026-11-09. Wall time per run grows by a factor 9–10 per resolution
doubling (measured N32→N64 exponent 3.2–3.4).

| Case, t=1 | N32 | N64 | N128 (extrapolated) | N256 (extrapolated) |
| --- | ---: | ---: | ---: | ---: |
| Alfvén regular / jitter | 8 / 14 s | 80 / 132 s | 13 / 22 min | 2.2 / 3.7 h |
| Loop regular / jitter | 19 / 28 s | 192 / 280 s | 32 / 47 min | 5.3 / 7.8 h |

Orszag–Tang N32 jitter to t=.5 takes 11 s, extrapolating to about 3 h at N256.
Brio nx128 takes about 2 s; nx1024 x ny4 is minutes. The extrapolated total is
roughly 150 core-hours, dominated by 24 N256 wave/loop runs and the four
N64 temporal references. The longest single case (jittered loop N256) is
about 8 hours and sets the minimum wall time. Extrapolations are estimates,
not measurements; memory of the cached factorization at N128/N256 is unmeasured.

## Execution sequence

The new `m1-campaign` REANA study automates this sequence on one frozen source:
workspace/M0 checks, the medium bounded gate, the candidate's 24-run
nonuniform mean-field ladder, N128 calibration, the 30-run physics matrix,
then the 112-run physical/temporal wave-and-loop matrix. Each phase must pass
before the next one starts. The historical mean-field comparison remains
unchanged; `--candidate-mean` selects the candidate explicitly.

Calibration runs at most three simulations together: the two N128
jittered travelling-wave frames and one N128 jittered vortex. With 24 requested
cores, each uses eight threads. Full matrices prioritize independent cases;
if memory reduces the worker count, the remaining core budget is distributed
as `floor(requested_cores/workers)` threads per case. Every runner rejects
`jobs*threads > 24`. The Linux
`measure_process.py` wrapper records `wait4` peak process resident memory
(the maximum individual process, not the sum across concurrent workers).
The first campaign stopped before numerical execution because the pinned
image lacks GNU `time`; the wrapper removes that external dependency.
Before seeing those measurements, reserve
8 GB for orchestration and estimate each N256 case at eight times the
largest N128 peak (four times the cell count plus sparse-factor growth and
safety allowance). Use at most `min(24, floor(56 GB / estimate))` workers;
stop if even one case will not fit. This estimate is conservative scheduling,
not a measured N256 memory bound; the Kubernetes 64G limit remains enforced.
The first cache benchmark measured N128 jittered **standing-wave** evolution
(parallel velocity 1, while calibration uses travelling velocity 0)
to t=.02 at 98.16 seconds before and 91.60 seconds after diagonal caching,
with bit-identical physical files. Linear extrapolation of the latter is
76 minutes for t=1 before setup cost; it is an estimate, not a completion
measurement. It does not predict the different calibration family exactly;
the original one-hour budget offers limited headroom for this measured cost.
The corrected-reporting campaign prospectively uses **two-hour calibration
and 24-hour full-case caps**. Full-phase caps account for the number of worker
batches, including any memory-driven reduction in workers. Timeouts remain
failures; none changes a physical target, grid or acceptance threshold.

1. **Calibration (REANA, bounded).** One N128 jittered Alfvén pair and one
   N128 jittered Orszag–Tang run. Record wall time and peak memory. Stop if a
   single case would exceed the available memory even at one worker, or if
   any gate already fails at N128; report instead of escalating.
2. **Physics matrix.** `python3 scripts/run_m1_physics.py --profile bulk-frame-heun-quadratic-v1 --accelerated-projection --projection-screening 1 --jobs 24 --output-dir <fresh>`.
3. **Wave/loop matrix.** `python3 scripts/run_m1_wave_loop.py --suite physical --temporal --profile bulk-frame-heun-quadratic-v1 --accelerated-projection --projection-screening 1 --jobs 24 --output-dir <fresh>`.

Steps 2–3 need the owner's explicit go-ahead and new REANA study entries in
`reana/remote.py` (the existing `physics` and `spline-full` studies run other
profiles and must not be reused or restarted). Limits: at most 24 cores and
64 GB in total, explicit case/thread allocation, no nested FFI worker pools.

The go-ahead has been given and the `m1-campaign` entry is now implemented.
Its final report separates new-candidate numerical gates from full M1
acceptance: the existing prescribed-flow evidence and paper/code audit must
also be reviewed before closing the milestone. Full raw snapshots stay in
the REANA workspace; compact diagnostics, logs and checksums are exported.

## Stop and reporting rules

- A failed or timed-out evolution is a failed gate, never an omitted row.
- No threshold, initial condition, reference or mesh is changed after seeing
  results. Any further amendment needs the owner's decision first.
- Report every gate with its measured value, including failures, and keep raw
  outputs with hashes as in the existing archives.
- A complete pass would support adopting this configuration as the M1
  validation profile under #7. It would not establish paper equivalence, 3D
  behaviour or general Galilean invariance.

## Known risks before running

- The literal `paper-global-v2` profile still loses pressure on planar-jittered
  Brio meshes (#20). This plan validates the engineering candidate instead.
- The 2026-11 record lists a failing N256 standing-wave boost case and failing
  spatial gates for earlier profiles. Bounded N32/64 pairs pass for this
  candidate; N128/256 are untested.
- Two-point N32→N64 orders at t=1 are 1.75–1.97 for B. The gate uses the
  finest three resolutions and is not predicted by this.
