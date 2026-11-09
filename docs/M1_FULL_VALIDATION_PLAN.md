# Plan for the unchanged full M1 validation matrix (issue #22 → #7)

Registered 2026-11-09, before any full-matrix run of this configuration. This
is a plan, not a result. **No long job has been started and none is started by
anything in this document.** Full M1 acceptance is not evaluated.

## Configuration under test

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

1. **Calibration (local, bounded).** One N128 jittered Alfvén pair and one
   N128 jittered Orszag–Tang run. Record wall time and peak memory. Stop if a
   single case would exceed 64 GB / 24 at N256 by the measured scaling, or if
   any gate already fails at N128; report instead of escalating.
2. **Physics matrix.** `python3 scripts/run_m1_physics.py --profile bulk-frame-heun-quadratic-v1 --accelerated-projection --projection-screening 1 --jobs 24 --output-dir <fresh>`.
3. **Wave/loop matrix.** `python3 scripts/run_m1_wave_loop.py --suite physical --temporal --profile bulk-frame-heun-quadratic-v1 --accelerated-projection --projection-screening 1 --jobs 24 --output-dir <fresh>`.

Steps 2–3 need the owner's explicit go-ahead and new REANA study entries in
`reana/remote.py` (the existing `physics` and `spline-full` studies run other
profiles and must not be reused or restarted). Limits: at most 24 cores and
64 GB in total, one thread per case, no nested worker pools.

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
