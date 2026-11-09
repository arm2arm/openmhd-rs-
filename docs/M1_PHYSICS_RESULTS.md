# General shock/vortex measurement status

The [prospective contract](M1_PHYSICS_PLAN.md) applies the unchanged M0 packet
to `bulk-frame-heun-spline-v1`. This is the general vector-potential/gauge
driver, separate from the older planar and conservative-induction pilots.

## Small execution probes, 2026-11-08

`python3 scripts/run_m1_physics.py --quick --jobs 4 --output-dir
results/physics_quick_20261108` completed all 16 small cases: Brio nx64/128
with four rows, vortex N16/32, regular/jittered, base/boost, at the full
packet times .1/.5. Each evolution took .5–6.1 seconds locally. This checks
execution and measurement; none of these resolutions satisfies the full
registered profile ladder. Source, binary and independent-reference hashes,
raw cells, recovered polygon vertices and diagnostics are retained there.

All eight joint fluid/grid boost pairs pass 1e-8, with maximum per-field
scaled L1 below 1e-14. All runs have positive sampled states and normalized
conservative residuals <=1e-10. Polygon area and bin-coverage checks pass.

Regular Brio signal travel is .38144/.38322, below .45; Bx maximum departure
is <=3.56e-15. Its scaled L1 errors decrease from nx64 to nx128:

| Field | nx64 | nx128 |
| --- | ---: | ---: |
| rho | .017391 | .011142 |
| p | .025463 | .015284 |
| vx | .035094 | .026122 |
| By | .034801 | .022936 |

Jittered Brio fails the Bx diagnostic: maximum departures are .039943 and
.066458 at nx64/128, against the unchanged 1e-8 limit. These are physical
field errors despite the passing boost comparison. They remain failures.
The initial discrete field already has maximum Bx departures .066861 and
.153424 respectively. This locates a problem in the spatial representation
before timestepping; it does not by itself quantify the later evolution error.
Jittered N16 vortex also fails the normalized limited-face divergence RMS
bound (.10735 versus .1); N32 gives .07473. Regular vortex gives .06766/.03660.
The full resolution study must measure whether these trends persist.

The passive signal diagnostic agrees with the analytic uniform x-characteristic
travel and leaves physical states unchanged in fixed/rigid boosted checks.
Projection tests independently check diagonal clipping, periodic coverage,
primitive averaging before absolute shock error, and rejection of incomplete
or nonfinite evidence. These checks do not substitute for physical validation.

M1 is not accepted, and no merge is justified by these probes.

After adding per-diagnostic measured values to the runner, the 16-case check
was repeated in `results/physics_quick_v2_20261108`. Every physical CSV,
history and summary matches the first probe byte for byte. The
[immutable probe archive](../tests/reference/m1_physics_probe/README.md)
retains all raw data, exact measurement/source files, manifests and the
known failures; its source is verified against the full REANA submission.

## Full REANA study

`openmhd-physics-20261108.1` started at `2026-11-08T17:13:14Z`, with 24
independent serial workers and a 64G memory limit. Snapshot SHA-256 is
`2a7cb3dcec2d418d1034746805bdf0e3b05ace3a461221189d915dc9b8ec614f`.
It runs checks before the 24 registered evolutions; submission is not a pass.
The known small-mesh failures remain explicit and no thresholds changed.

Before submission, format, Clippy, the workspace suite, all 36 Python tests,
M0 algebra and independent-reference checks passed locally. A separate build
of the frozen full-wave study source was compared with the diagnostic-enabled
code on ten small jittered boosted wave/loop runs across all five profiles.
Every initial/final CSV, history and summary is byte-identical. Exact source
archive/binary/output hashes and commands are retained in
`results/physics_legacy_parity_20261108/comparison.json`. The new observable
does not change these physical evolutions; full scientific gates remain open.

### Partial remote results at 17:55 UTC

All seven preliminary check commands passed on REANA. Of 24 registered
evolutions, ten completed, six failed, and eight vortex cases remained.
This is a partial observation, not a completed acceptance report.

All six regular Brio evolutions reached t=.1 with positive sampled states,
acceptable budgets, Bx departure <=4.98e-14 and signal travel <.385. Base
nx1024 profile L1 errors are rho=.002268, p=.002553, vx=.004888 and
By=.003499; each lies below its packet limit and decreases across nx256/512/1024.
The four N64 vortex cases completed with state/budget/diagnostic checks passing.
Their finer-resolution comparisons are still outstanding.

All six jittered Brio cases aborted after repeated primitive-state validity
rejections. Base/boost pairs stopped at approximately t=.0034298 (nx256),
.00068839 (nx512), and .00086874 (nx1024), far short of .1. Last accepted
minimum pressures are about 6.2e-8 to 1.1e-7; state-rejection counts are
93, 54 and 84 respectively. No geometry rejections occurred. Logs report
`primitive state requires finite values, positive density and pressure`.
The solver stopped rather than applying floors or resetting energy.
These are numerical failures, not REANA execution delays. Their precise
mechanism remains to be diagnosed; the initial Bx representation error is
already documented above and is not by itself a complete causal explanation.

Partial run records, execution records and failure logs are preserved in
`results/reana_remote_20261108/status_1755/`, with a SHA-256 manifest; the
remote source-snapshot identity matches the registered submission. These
failures block M1 acceptance and the conditional merge to main.

The subsequent [shock investigation](M1_SHOCK_INVESTIGATION.md) traces the
failure to a discrete fluid/curl energy mismatch, rules out timestep
refinement as a fix, and preserves two unsuccessful reconstruction trials.
Only passive diagnostics and clearer failure reports are retained in the
solver; its historical numerical profiles remain unchanged.
