# Plan for the unchanged full M1 validation matrix (issue #22 → #7)

**Execution amendment, 2026-11-11:** the owner requests independent cases in
separate REANA workflows, submitted concurrently, with no aggregate
24-core/64-GB scheduling cap. Per-job resources and prerequisite checks remain
explicit. This supersedes the historical scheduling limits below, without
changing any numerical gate. The old monolithic runner must be adapted before
another full submission; see [the execution policy](REANA.md#current-execution-policy-2026-11-11).
The pressure-reuse campaign is stopped after two independently verified
standing-wave convergence failures; bounded diagnosis precedes new long runs.

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

## Explicit smooth-extrema continuation (2026-11-13, before execution)

Registered before any run of this sequence. It is a prospective declaration,
not a result, and it executes **only if** the candidate's two fixed-mesh
standing ladders, including N256 and both boost frames, meet the unchanged
gate of the [issue #26 plan](M1_STANDING_WAVE_PLAN.md). A failure there ends
this continuation before it starts.

**Configuration.** The stopped pressure campaign's configuration with one
added option: `bulk-frame-heun-quadratic-v1 --accelerated-projection
--projection-screening 1 --riemann hlld-pressure --potential-limiter
smooth-extrema`. The limiter of the `A` gradients used for face advection is
an engineering departure that admits curvature-confirmed extrema; its
definition and measured cost are in the issue #26 plan. The binary default
and the default limiter are unchanged. No Rust source changes after
`f60eaa8`, whose controls and screens are already measured; the runners now
propagate, record and validate the limiter choice. Candidate summaries must
carry `smooth-extrema-v1`; literal-paper symmetry controls keep HLLD and the
default limiter. Missing, mixed or wrong limiter metadata fails configuration
validation.

**Sequence, on one frozen source.** The phases of the registered campaign,
executed as separate REANA workflows under the 2026-11-11 policy:

| Phase | Workflows | Registered content | Checks |
| --- | --- | --- | --- |
| Preflight | 1 (`m1-fanout-preflight`) | format, strict Clippy, debug and release Rust tests, Python tests, M0 and reference checks; exports the binary | every command exits 0 |
| Bounded, short | 1 (`m1-limiter-bounded`) | the four short stages of `run_m1_bounded.py` (53 cases of at most 120 s, three workers) | each stage's unchanged verdict |
| Bounded, medium | 48 (`full-medium`) | Alfvén and loop N32/64, t=1, with every boost pair | all complete, positive, conservative; 24 pairs pass |
| Mean field | 24 (`full-mean`) | nonuniform mean-field boost ladder | `mean_checks` |
| Shock/vortex | 30 (`full-physics`) | Brio–Wu nx256/512/1024 on three meshes, Orszag–Tang N64/128/256, with boosts | all registered physics gates |
| Waves/loops | 112 (`full-waves`) | N32–256 ladders, 48 boost pairs, 16 temporal runs | `wave_checks`: 8 spatial gates, 48 pairs, temporal measured |

The short and medium bounded stages and the mean ladder are submitted
together once the preflight passes. The two long matrices are submitted
together only after those three pass; the historical order of physics before
waves was a consequence of the shared worker pool. Every per-case workflow
reuses the preflight binary.

The historical N128 calibration phase sized a shared 64-GB worker pool, which
the per-case policy removed: each case now declares its own memory. Its two
checks are retained and applied to the same registered cases inside the long
matrices (the N128 jittered travelling pair completes, passes its boost
comparison and has relative B L1 at most .02; the N128 jittered vortex
completes with its state and diagnostic gates). They no longer delay the
N256 cases; a verified failure stops the remaining workflows of its plan.

**Gates.** Exactly those of the table under
[Gates](#gates-all-unchanged-except-the-owner-approved-bx-amendment). No
threshold, grid, physical time, reference or mesh changes.
`scripts/fanout_campaign_verdict.py` applies the unchanged checks of
`run_m1_bounded.py` and `run_m1_campaign.py` to the workflow outputs and
additionally requires one snapshot, one binary and the limiter metadata in
every run. Its `full_m1_accepted` is always false.

**Execution budgets, not gates.**

| Case | Threads | Memory | Wall cap |
| --- | ---: | ---: | ---: |
| waves, loops, mean N8/16 | 2 | 4Gi | 1 h |
| waves, loops, mean N32 | 2 | 4Gi | 2 h |
| waves, loops, mean, temporal N64 | 2 | 4Gi | 8 h |
| waves, loops N128 | 4 | 8Gi | 24 h |
| waves, loops N256 | 4 | 16Gi | 6 d |
| Brio–Wu nx256/512 | 2 | 4Gi | 2 h |
| Brio–Wu nx1024 | 2 | 8Gi | 4 h |
| Orszag–Tang N64 / N128 / N256 | 2 / 4 / 4 | 4Gi / 8Gi / 16Gi | 8 h / 24 h / 6 d |

The caps are wide on purpose. On 2026-11-13 about 100 concurrent workflows
roughly doubled per-case wall times, pods see 24 CPUs with no enforced CPU
limit, and the N256 loops have no completed baseline (the stopped campaign
interrupted them). REANA stops any job after seven days. A timeout remains a
failure.

**Stop and reporting rules.** Those of
[Stop and reporting rules](#stop-and-reporting-rules). Candidate plans are
monitored with cancellation. The monitor is not a REANA service: it stops
siblings only while its client host runs, and only within its own plan, so a
verified failure in one long matrix is followed by stopping the other by
hand. Every gate is reported with its value, including failures.

**What a pass would and would not mean.** It would be the registered evidence
for proposing this configuration as the M1 validation profile under #7. It
would not decide whether an opt-in limiter that admits curvature-confirmed
extrema is acceptable there; that is the owner's decision, and independent
review is still required. It would not establish paper or AREPO equivalence,
3D behaviour or general Galilean invariance. No issue closes automatically.

**Known before running.** The candidate's bounded screens from `f60eaa8` pass
with no registered gate failing, but fixed-mesh field-loop passive diagnostics
are 3–10 % worse than with the default limiter and the potential undershoot
at the loop rim is 17–36 % larger; no registered gate measures either. The
N256 loop runtime is unknown. This is a prospective declaration, not a
passing result.

**Measured continuation (2026-11-13).** Appended after the declaration; the
text above is unchanged.

- *Condition met.* The candidate's standing ladders give finest-three orders
  1.9590 (regular) and 1.8834 (jitter .15) with all eight boost pairs
  passing. [Evidence](../tests/reference/m1_standing_limiter/README.md).
- *Frozen source and preflight.* Source `7fef6e2`, snapshot
  `e6f390efb2cd…`. `openmhd-limiter-campaign-preflight-20261113.1` passes all
  eight commands (160 debug and 169 release Rust tests, 112 Python tests);
  binary `7544a6ab44e4…`.
- *Short bounded stages pass.* `openmhd-limiter-bounded-20261113.1`
  (11:03–11:19 UTC): shock short, mesh symmetry, short waves and quick
  shock/vortex all pass their unchanged verdicts, including the limiter
  metadata of every candidate run; short-wave B orders are 1.918–1.952. The
  legacy gate script builds inside its own workflow, so these 53 cases ran a
  third binary (`4ae7fcb40364…`) of the same snapshot.
- *Mean ladder passes.* `openmhd-lim-full-mean-758d415bab22-*`: 24 of 24
  complete, 12 of 12 boost pairs pass, largest field difference 1.0e-14
  against 1e-9.
- *Medium stage passes.* `openmhd-lim-full-medium-18b64ff0fa7e-*`: 48 of 48
  complete, positive and conservative; 24 of 24 boost pairs pass (largest
  Alfvén relative L1 2.3e-12, largest loop relative B L1 4.1e-14).
- *Precondition met.* `fanout_campaign_verdict.py` reports `bounded_short`,
  `bounded_medium` and `mean` as passed with one snapshot, one per-case
  binary and matching limiter metadata
  ([record](../tests/reference/m1_standing_limiter/campaign/phase2_checks.json)).
- *Long matrices submitted 16:03–16:07 UTC:*
  `openmhd-lim-full-physics-b0835f299725-*` (30) and
  `openmhd-lim-full-waves-8eb6a53d6596-*` (112), all 142 accepted.

**Result (2026-11-14 17:35 UTC): every registered phase check passes.** All
214 per-case workflows and the short-stage workflow completed; none failed,
timed out or was stopped. `scripts/fanout_campaign_verdict.py` from the frozen source reports
all seven phases as passed, with one snapshot, one per-case binary and the
limiter metadata in every run.
[Verdict, summary and run records](../tests/reference/m1_standing_limiter/README.md#8-fan-out-campaign-from-the-campaign-snapshot-2026-11-13-to-14).

| Gate | Result | Baseline, default `A` limiter |
| --- | --- | --- |
| Alfvén finest-three B L1 order, 8 ladders (≥ 1.8) | 1.8834–1.9590, all pass | 1.6591 and 1.7705 fail, six pass |
| – standing, fixed mesh, regular / jitter .15 | **1.9590 / 1.8834** | **1.6591 / 1.7705** |
| – other six ladders | 1.9099–1.9362 | 1.9098–1.9362 |
| Finest relative B L1 (≤ .02) | 7.1e-4 to 1.1e-3 | |
| Alfvén boost pairs (≤ 1e-8) | 32/32, largest 9.3e-12 | |
| Loop boost pairs, relative B L1 (≤ 1e-3) | 16/16, largest 4.9e-9 | N256 never completed |
| Temporal runs | 12 measured, successive orders 1.98–2.08 | |
| Brio–Wu finest scaled L1, regular and column meshes | pass, 6–17 times below the limits | pass |
| Orszag–Tang finest binned L1 (ρ .06, p/Bx/By .1) | .0074 / .0159 / .0145 / .0125 | .0074 / .0159 / .0145 / .0125 |
| Vortex mean-B drift (≤ 1e-3), limited-face div B RMS (≤ .1) | ≤ 4.7e-4, ≤ .040 | ≤ 4.8e-4, ≤ .042 |
| Shock/vortex boost pairs (≤ 1e-8) | 15/15, largest 2.4e-11 | |
| Positivity and 1e-10 budgets | all 214 per-case runs | |
| Calibration checks on the N128 cases | pass | |

Wall time: the long matrices ran from 16:03 UTC on 13 November to 17:33 UTC
on 14 November. N256 loops took 11.5–15.2 hours each, N256 vortices
8.6–12.7 hours and N256 Alfvén waves 4.7–9.4 hours, on four threads with 23
N256 cases sharing the cluster.

This is the registered evidence for the opt-in configuration `--riemann
hlld-pressure --potential-limiter smooth-extrema`. It is **not** M1
acceptance: that needs the owner's decision on a limiter that admits
curvature-confirmed extrema, with its measured 3–10 % cost on fixed-mesh
loop diagnostics, and independent review. No default changed.

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

Measured focused result: `openmhd-m1-pressure-blend-20261110.2` completes all
24 evolutions with 96 byte-identical control files. All eight pressure-blend
cases and four boost pairs pass; column shock boost is 6.04941e-14 and regular/
jitter N32 vortex normalized divergence is .0684606/.0730138.
[Verified source/results and independent reductions](../tests/reference/m1_column_boost/pressure_blend/README.md).
All 169 executable/configuration sources match `144ac35`; its format, strict
Clippy, 163 release Rust tests, 80 Python tests and M0 checks pass on REANA.
Proceed with the registered pressure campaign, preserving the exact numerical
implementation and every gate below. This focused result is not full acceptance.

Execution correction after the first pressure campaign: all five bounded
stages and the mean ladder pass, but concurrent calibration Cargo builds
interfere with shared target artifacts. The workflow is stopped before full
matrices; see [the preserved evidence](../tests/reference/m1_pressure_campaign/README.md)
and [#25](https://github.com/arm2arm/openmhd-rs-/issues/25). The next fresh packet
uses explicitly hash-validated binary reuse in concurrent calibration, and
cancels sibling stages on failure. The complete preflight and unchanged
bounded/mean/calibration/full sequence must run; no physical gate or numerical
source is changed by this execution repair.

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
