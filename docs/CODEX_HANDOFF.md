# Handoff from ChatGPT conversation to Codex

*Prepared November 3, 2026. This is a curated, faithful project-context summary of the ChatGPT discussion, **not** a verbatim export of the ChatGPT conversation or a transferable Codex chat session.*

## Acceptance campaign checkpoint (2026-11-10)

Current branch: `arm2arm/m1-require-bounded-shock-wave-and-boost-regressi`.
M0 #1/#2 are accepted and closed; #7 and #19–#22 remain open. The owner
requests continuing through genuine acceptance on REANA, within 24 total
cores / 64 GB. Old execution holds below are historical, not current.

**Stopped after a verified required-gate failure at 01:16:53 UTC:**
`openmhd-m1-reporting-campaign-20261110.1`, UUID
`01947a14-a507-4384-a4ca-9533395d08e8`, started **2026-11-09 23:52:22 UTC**.
Frozen submission: `results/reana_submission_m1_reporting_campaign_20261110_v2`,
snapshot SHA256 `b102b766bc5b8e116811924f977e923e097c7ec3cf351647fae3bd2c8c46de04`.
All 391 uploads succeeded before start. This is an exact source snapshot over
`9ce5304`, including the reporting correction and resource allocation below.
It reruns workspace/M0 checks, 20 metadata-parity evolutions, then bounded,
mean-field, calibration and full gates. Do not mutate or restart that snapshot.
Monitor `outputs/execution.json`, `source/results/reana_projection-metadata/report.json`,
and `source/results/reana_m1-campaign/campaign.json` with per-phase run records.
The reporting correction is committed as `9e99b74`; resource allocation is
`cb70b85` (only a clarified help string differs from the executed runner).
Format, strict Clippy, **135 debug Rust / 143 release Rust / 66 Python tests**,
M0 algebra/reference checks and **20/20 reporting evolutions** pass. All ten
comparisons preserve scientific files and every remaining summary field.
All five bounded stages pass, including the 48-case medium wave/loop suite
(1061.49 s). The 24-run nonuniform mean-field suite also completes with all
12 boost pairs passing (56.9 s). **All N128 calibration checks pass**:
both wave frames pass at t=1 (1745.37 / 1915.21 s), with relative B L1
.003164125 and maximum normalized boost residual 2.69922e-14. The vortex
completes at t=.5 in 2574.25 s: normalized mean-B drift .000137274 and
limited-face divergence RMS .0361845 both pass, with positive states and
conserved budgets. Each case used eight threads. Wave peak process RSS is
667,623,424 bytes, vortex 665,624,576. All 24 raw files and exact source hashes verify;
see the [calibration archive](../tests/reference/m1_reana_calibration/README.md).
The matching N64→N128 order is 1.841645, a two-grid diagnostic that does not
replace the full N64/128/256 gate. The full 30-case physics matrix ran
from about **01:10:36 UTC**, with ten workers and two threads per case. The
8× N128 memory forecast and 8-GB reserve determine this allocation within
24 cores / 64 GB. It was stopped with 20/30 runs complete after the N1024
column-jitter Brio boost pair failed: maximum normalized L1 5.81839e-6 versus
1e-8. All 18 Brio runs and two N64 regular vortices completed with passing
state/diagnostic checks. Eight other Brio boost pairs and the completed vortex
pair pass; the regular and column Brio reference/refinement gates pass.
The 112-case wave/temporal matrix never started. Preserve the partial records;
forced-stop campaign JSON can still say running. See the
[new failure evidence](../tests/reference/m1_column_boost/README.md).

**Completed bounded reproduction:** `openmhd-m1-column-repro-20261110.1`, UUID
`1f6ce890-5340-4842-989c-049b780aaddb`, started 01:25:37 and finished
01:28:23 UTC. Frozen packet:
`results/reana_submission_m1_column_repro_20261110`, snapshot SHA256
`65c556d30ed5f171ed608c6fe22c7c26eb2edf1097c84231360e9bf2185ce800`.
All ten uploads succeeded. Four N1024 regular/column base/boost cases use
the exact original Linux binary, SHA256
`ac3e8e895624f80e02e25fb0794c69b1f2a1e2162b697db812b4d46128b8648c`,
two threads each, 8-GB job memory and 600-second case limits. It requires
scientific-file parity with the original cases and reproduces the known
pass/failure pattern. All four cases complete in 124.87–155.06 s; all 24
scientific-file comparisons match byte for byte. The regular pair passes
at 5.70035e-11; columns reproduce 5.81839e-6. A successful reproduction is
not physical acceptance. No compute workflow remains active at this checkpoint.
No solver change has been made for this failure yet. Alternating-row errors
are measured; the responsible operator and mechanism remain to be isolated.
Next: add bounded observation of transverse-mode growth without changing
timesteps, then isolate reconstruction/fluid-flux/curl/projection contributions.
Run all new tests and evolutions on REANA. Do not restart the full matrix
while this required boost regression fails.
[Verified bounded/mean archive](../tests/reference/m1_reana_bounded/README.md).
All 480 medium/mean raw files and their execution source hashes verify.
The medium wave coarse N32→N64 orders are 1.565–1.769; they do not satisfy
or replace the registered finest-three N64/128/256 gate. See the
[medium plot](images/m1_completion/medium_screened_gate.png).
Read-only [wave-mode postprocessing](../tests/reference/m1_reana_bounded/wave_modes/README.md)
checks all 96 medium wave snapshots. Phase supplies 65–84% of N64 fixed-mesh
final squared B error; this identifies a leading component, not its numerical
cause. The new analysis/plot scripts change no solver or acceptance threshold.
See [the immutable verification packet](../tests/reference/m1_projection_metadata/README.md).

**Completed performance study:** the cache code in **`9ce5304`** exactly
matches the tested numerical sources. Format, strict Clippy, 133 debug and
141 release Rust tests, 64 Python tests and M0 checks pass. All 11 performance
evolutions complete and seven comparisons match scientific files byte for
byte. All 52 downloaded scientific-file hashes verify. Evolution speedups
are 1.068–1.106 for four serial baseline/cache pairs; N128 threading at
4/12/24 gives 1.367/1.479/1.382. These are single shared-node samples.
See [the archived evidence](../tests/reference/m1_projection_cache/README.md)
and [the performance plot](images/m1_completion/projection_cache.png).

The parent cache workflow `openmhd-m1-cache-campaign-20261110.1`, UUID
`9122c09e-93da-4bda-9f57-a534713cf4d3`, is **stopped** (23:51:52 UTC), before
the replacement started; there was no compute overlap. Its four short
numerical stages pass. 42/48 medium cases completed with positive states and
conserved budgets; six cases and final boost comparisons remain incomplete.
This is not a medium-stage pass. Raw remote and local partial records remain.
Its original snapshot SHA256 is
`c559771dac2006da0bc84f176b2146a80e890e2dfe03753f32c3bceacb2f9939`.
Force-stop can leave local execution/campaign JSON labelled running; use
REANA's authoritative workflow status when interpreting those partial files.

**Reporting defect:** screened summaries falsely label the factor shift as
1e-8, although the matrix uses κ=1 and `projection_screening` correctly
records it. The verified correction stores/reports the actual factor coefficient and
add solver/CLI tests plus `run_projection_metadata_check.py` (20 small matched
evolutions; only that field may change). Keep old outputs immutable and
annotated. The correction changes metadata, not the executed equations.

The measured cached N128 **standing** wave costs 91.60 evolution seconds to
t=.02, suggesting about 76 minutes to t=1 before setup. Calibration instead
uses a travelling wave, so this is a cost warning, not its measured runtime.
The replacement prospectively uses two-hour calibration/24-hour full-case
caps, with worker-count-aware stage caps. Calibration uses three cases with
eight threads each; full matrices use memory-bounded workers and remaining
threads within 24 cores total. Physical targets and thresholds stay unchanged.

The [candidate audit](M1_CANDIDATE_AUDIT.md) separates every engineering
departure from the source formalism; it is an assistant implementation audit,
not an independent review. The archived prescribed-flow packet's 12 file
hashes, 32 completed evolutions, 16 boosts, 16 comoving gates and two refinement
gates verify. A source-dependency review finds the serial transport arithmetic unchanged;
see the audit and `tests/reference/m1_completion/prescribed/applicability_20261110.json`.
This retains historical evidence, not a new full-ladder binary reproduction.

`openmhd-m1-campaign-20261109.1` **failed at numerical launch** at 22:57 UTC:
the pinned image lacks `/usr/bin/time`. Format, strict Clippy, 133 debug Rust
tests, 141 release Rust tests, 61 Python tests and M0 checks passed first.
See [its preserved preflight evidence](../tests/reference/m1_reana_preflight/README.md).
The Linux `wait4` resource wrapper replaces that dependency and passes
success/failure/memory tests in the cache campaign. Its RSS is the maximum
individual process, not the concurrent-worker sum. Memory scheduling reserves
8 GB and forecasts eight times the largest N128 peak per N256 worker.

## Verified follow-up reporting correction (2026-11-10)

A source audit found that `evaluate()` only emits mean-field refinement rows
for the three historical `PROFILES`, even when `--candidate-mean` evolves the
new quadratic profile. Per-run and pair errors are still computed; this is
an omitted-summary-row defect, not a numerical evolution change. Commit `c6cda9d`
derives additional smooth profiles from measured pairs, preserve
historical rows, and require the candidate's four registered spatial/time
observation series in the campaign reducer. No new physical-order target is
introduced for roundoff-sensitive boost residuals.

Both added regressions pass within **68 Python tests on REANA**.
The original completed mean summary confirms zero candidate refinement rows.
Its 24 runs and 12 pair measurements are preserved in `m1_reana_bounded/mean`.
The original report remains unchanged. A verified copy restores only its
`mean_refinement` field; all other fields are identical and the four candidate
spatial/time observations are present. No MHD evolution was repeated.

The supplemental workflow **finished successfully at 01:17:44 UTC**:
`openmhd-m1-mean-report-audit-20261110.1`, UUID
`9fb39416-290c-4028-b199-8aa0e0248d18`. Frozen input directory:
`results/reana_submission_m1_mean_report_audit_20261110`; snapshot SHA256
`becbff01b4671d52de3e597093ded7d7f3bcc5d862d241318961ce5e61874dc5`.
All six uploads succeeded. It ran Python regressions and restored only the
missing refinement observations from the original hash-verified summary.
No MHD evolutions; 2 GiB limit. Its private export Git commit exists only
for unit-test provenance fixtures; the actual source revision `c6cda9d` and
all 80 source/config hashes are pinned separately. It started after the main
compute job was authoritatively stopped; no resource overlap occurred.
[Verified supplemental archive](../tests/reference/m1_reana_bounded/mean_reporting_audit/README.md).

## Earlier campaign submission (2026-11-09, 22:45 UTC)

Current branch: `arm2arm/m1-require-bounded-shock-wave-and-boost-regressi`.
The owner explicitly requests continuing until M0/M1 gates pass, using
REANA for tests and long runs. M0 #1/#2 remain accepted and closed; M1 and
#19–#22 remain open. No numerical solver changes accompanied this earlier snapshot.

The local four-stage gate passes in 71.1 seconds: 51 evolutions complete,
two literal planar controls reproduce the pressure failure. Exact source,
raw measurements and hashes are archived under `tests/reference/m1_bounded_gate`;
see the [plot](images/m1_completion/bounded_screened_gate.png).

`openmhd-m1-bounded-20261109.1` passed format, strict Clippy, 133 workspace
Rust tests, 57 Python tests, release build and M0 algebra/reference checks.
Its 30-second local-case budget was too small on REANA: nx512 × ny8 shock
and both N32 jittered vortices timed out. The workflow was stopped with raw
workspace retained; 16 N32 medium wave records also completed before stopping.
They took 20–49 seconds, around 2.5–3 times local costs. No timeout is a pass.

`openmhd-m1-campaign-20261109.1` started at **22:45:55 UTC** from the frozen
`results/reana_submission_m1_campaign_20261109_v5` packet, snapshot SHA256
`29e467e6a0af19cc2afd59701c7132e9f813d71bdaae704bef13bdccafcd828d`.
It reruns all checks (also release/all-target Rust tests), then short/medium
gates, candidate mean-field boosts, N128 memory/time calibration, the full
30-case physics matrix and 112-case physical/temporal wave/loop matrix.
New remote budgets: short cases 120 s, medium cases 1800 s; local defaults
stay 30/600 s. A failed short stage now prevents medium execution.
At most 24 serial simulations and 64G memory; calibration may reduce workers.

Monitor `outputs/execution.json` and, once present,
`source/results/reana_m1-campaign/campaign.json`, then each phase's `runs.json`.
The campaign must not be called accepted merely because its workflow finishes.
The plan, historical prescribed-loop evidence and paper/code audit remain
part of final M1 review. Preserve failed records and physical thresholds.
The snapshot contains the current uncommitted runner changes over `3cbd1d5`;
commit them after the new remote checks, then publish verified result links.

## Updated merge instruction (2026-11-09)

Latest instruction: continue until M0/M1 acceptance gates pass and close
their issues only with measured evidence. Use REANA for tests and long runs,
within 24 total cores and 64 GB. Work on
`arm2arm/m1-require-bounded-shock-wave-and-boost-regressi`. M0 issues #1/#2
are already closed under their documented AI review. The screened quadratic
candidate passes the combined **short-only** gate; the medium and full
matrices remain required. See [results](M1_SHOCK_INVESTIGATION.md#bounded-m1-gate-for-the-screened-candidate-2026-11-09-issue-22)
and [the plan](M1_FULL_VALIDATION_PLAN.md). New REANA validation is authorized;
the older execution hold below applies to the archived stopped workflows.

The user explicitly requests merging this development branch into main after
being informed of the remaining Bx failure. Merge the tested implementation
and evidence as a development checkpoint; full M1 acceptance remains pending.
This supersedes earlier "do not merge" instructions in this historical handoff,
not the physical gates. Keep #7/#19–#22 open and long REANA jobs stopped.
See the [updated merge contract](M1_MERGE_PLAN.md).

## Latest bounded candidate result (2026-11-09)

The new opt-in `--accelerated-projection` caches a sparse Cholesky
preconditioner for the existing projected-rate profiles. It changes neither
the projection objective nor its original residual tolerances. The quadratic
profile completes both nx512 jittered Brio base/boost cases to t=.02 in
7.64/7.92 seconds, minimum accepted pressure .0467862, budgets <3.74e-15,
zero state rejections, passing boost agreement. All 40 bounded controls now
complete. Its four N8/16/32 t=.02 wave families have B/velocity orders
1.909–1.953; the linear-curl comparator still fails two velocity screens.
Matched N32 jittered waves are about 10 times faster. Across 38 completed
old/new pairs, physical states agree within 2.8e-13, A within 2.33e-10.
Serial and 1/2/4/24-thread states/diagnostics/counters agree bitwise.

This is a working short-time **engineering candidate**, not the literal paper
algorithm or full M1 acceptance. The fine shock Bx error is .0457136 initially
and .0549856 finally, versus the unchanged 1e-8 gate. Do not merge main or close
#7/#19–#22. Next investigate the transverse curl representation (#21), using
this faster comparator for bounded controls, then the original full physical
gates. Long REANA jobs remain stopped. Preserve all failures and thresholds.

A positive, quadratic-consistent Laplacian was also implemented independently
and passed standalone moment/maximum-principle/Fourier checks, but its coupled
nx512 shock failed at .00113439. That evolution profile is removed; only its
measurement API/probe remains. No retained evolution uses this dissipation.
See [measured results](M1_SHOCK_INVESTIGATION.md#measured-projection-retry-2026-11-09)
and the [exact source/data archive](../tests/reference/m1_projection_retry/README.md).
Checks pass: 138 release Rust, 43 Python and 13 M0 tests, strict Clippy, format
and reference integrity. faer 0.22.6 is pinned, MIT, Rust 1.84 minimum;
its Rayon feature is disabled. Default solver behavior remains unchanged.

## Previous rejected dissipation result (2026-11-09)

The user requests a deeper solution and completion. Optional paper Eq. (77)
was implemented in two separately named trial profiles: successive raw-LS and
direct quadratic Hessian trace, alpha=.2 primary, .1/.3 short sensitivities.
37 local evolutions take <=3.52 seconds each; no long job is resumed. Both
variants stabilize nx256 to t=.02, but both fail nx512 before .000824, base
and boost. The unchanged Bx gate still fails. A new regular-mesh Fourier proof
shows that the quadratic trace amplifies high-frequency modes despite passing
polynomial/smooth tests. Both evolution profiles are rejected and removed.
Do not propose either archived profile as a validated repair.

Retained changes: tested second-derivative measurement API and Fourier-sign
regression, accepted-step diagnostic CSVs, reproducible analysis and plot,
complete failed source/data archive. 134 Rust/42 Python/13 M0 tests, format,
strict Clippy and reference integrity pass. Original jittered baseline CSVs
are byte-identical. See [full findings and next decision](M1_SHOCK_INVESTIGATION.md#measured-dissipation-result-both-candidates-rejected-2026-11-09)
and [archive reproduction](../tests/reference/m1_paper_dissipation/README.md).
Next work must establish the discrete magnetic-energy damping property before
another diffusion evolution. Pressure, initial Bx representation, and full
wave/mean-field boost gates remain distinct problems. #19–#22 remain open;
M1 is not ready to merge. No pressure floor, energy reset or relaxed gate.

## Resumed session (2026-11-09)

The user requested bug reports on 2026-11-08 and explicitly resumed development
with "continue" on 2026-11-09 (Europe/Berlin). The pause is lifted for local
development. Preserve the short-test constraint and paper formalism; all long
REANA workflows remain stopped.

The next-session order under [#7](https://github.com/arm2arm/openmhd-rs-/issues/7) is:

1. [#18: checkpoint current source and evidence](https://github.com/arm2arm/openmhd-rs-/issues/18).
2. [#19: audit the paper-to-code interfaces](https://github.com/arm2arm/openmhd-rs-/issues/19).
3. [#20: isolate cell 253's pressure failure](https://github.com/arm2arm/openmhd-rs-/issues/20).
4. [#21: resolve the jittered Bx representation/gate conflict](https://github.com/arm2arm/openmhd-rs-/issues/21), separately from pressure stability.
5. [#22: pass bounded regressions before longer validation](https://github.com/arm2arm/openmhd-rs-/issues/22).

The accumulated code is now checkpointed in `4c5341a` (Riemann completion),
`76470eb` (mesh derivatives/threading), `b5bea83` (M1 solver profiles/tests)
and `5175240` (measurement/REANA tooling). A fresh local check passes 127 Rust,
41 Python and 13 M0 tests plus format, strict Clippy and reference integrity.
The retained paper-audit source is byte-identical apart from this handoff.
All 126 files named by study archive manifests verify. The reports embed
measured failures, reproduction commands and archive hashes; their initial
uncommitted status is historical. The paper-source comparison
still fails both jittered short shocks at t=.00334288704. All long REANA jobs
remain stopped; full M1 acceptance and merge remain blocked by numerical gates.

Checkpoint issue #18 is closed: `e17cf9b` publishes the source/evidence with
the preceding four component commits. New face-assembly and geometry probes
retain the original solver. The stationary first-step reconstruction matches
the production Q/A update bit for bit. Faces 1050 and 1051 explain 99.4% of
cell 253's initial energy loss; both use HLLD and agree between state/flux EMFs.
The optional mixed-Hessian paper trial fails earlier (t=.00295085417) and is
removed; its exact source/data remain archived. Seven of eight short geometry
controls complete. At fixed nx256, increasing ny4 to ny8/16 permits t=.01
completion, but Bx errors remain .110146/.0821556. Original ny4 still fails.
See [the new measured interpretation and plot](M1_SHOCK_INVESTIGATION.md).
The subsequent exact-pattern controls separate local geometry from row count:
repeating the original stretched four-row pattern in taller boxes still fails
at t=.00334, while compressing the same perturbation pattern reaches t=.01.
Repeated effective derivative rows agree within 3.87e-14 relative L1.
Compression removes the 253/255 face and changes neighboring magnetic
reconstruction; cell 253's initial dp changes from -35.3551 to +3.34461.
This localizes sensitivity to shape/topology at the magnetic discontinuity;
it does not isolate aspect ratio alone or fix the original benchmark.
The original physical CSVs reproduce byte for byte; no library solver changes.
All six configurations plus face audits take 3.16–11.27 seconds each, no
timeouts. Final checks pass 129 Rust, 42 Python and 13 M0 tests, strict
Clippy/format/reference integrity. See the [pattern evidence](../tests/reference/m1_pattern_controls/README.md)
and [plot/interpretation](M1_SHOCK_INVESTIGATION.md#measured-repeated-pattern-result).
Next focus on discontinuity reconstruction and conservative energy/curl
coupling under the verified source formalism. Keep the original ny4 benchmark
and Bx gate; #19–#22 remain open, and no long workflow is restarted.

The next frozen audit tests the paper's optional primitive fit through the
central value. It passes operator tests but changes cell 253's initial dp from
-35.3551 to -35.4438; zero magnetic face slopes worsen it to -61.9306. No new
evolution profile is added. Counterfactual Riemann inputs isolate the neighboring
cell values: analytic Bx at cells 254/255 leaves dp=-30.6001, analytic By gives
-.0320103, both give +5.89480. These inputs are inconsistent with stored A and
never evolved; they diagnose, rather than repair, the coupling. Independent
kink-residual/normal-equation calculations reproduce the neighboring initial B
to about 1e-14. The broadened By jump dominates this initial energy drain;
Bx-only correction would be insufficient. Source-supported broadening itself
is not a coding error. Robust conservative energy/curl coupling on the original
geometry remains the problem. See [results and plot](M1_SHOCK_INVESTIGATION.md#measured-reconstruction-input-result)
and [reproducible archive](../tests/reference/m1_reconstruction_inputs/README.md).
The final 80 frozen evaluations take 5.43 seconds; 131 Rust/42 Python/13 M0
checks plus strict Clippy/format/reference integrity pass. Production solver,
all gates and stopped long workflows are unchanged.

**Historical handoff:** subsequent local work added the [M0 source audit](PAPER_IMPLEMENTATION_SPEC.md), [kinematic pilot](KINEMATIC_2D.md) and [experimental coupled planar reference](COUPLED_2D.md). Issue #6 adds a separate [general 2.5D endpoint implementation](VECTOR_POTENTIAL_REFERENCE.md). Issue #7 has [historical incremental results](M1_WAVE_LOOP_RESULTS.md) and a [continuation with full wave spatial/temporal measurements and prescribed-flow loops](M1_COMPLETION_RESULTS.md). The named signal-completion comparator improves boost agreement but still fails the N256 fixed-grid standing-wave pair; spatial and temporal limitations remain explicit. Consult README/AGENTS and the continuation's labelled AI review for current status; the planning-only descriptions below describe the original handoff.

Current continuation (2026-11-08): the separately named `bulk-frame-heun-v1`
adds fully reevaluated stages for fixed/rigid meshes. See [its contract](M1_HEUN_INVESTIGATION.md)
and [measured status](M1_HEUN_RESULTS.md). New REANA submissions use up to 24
serial cases concurrently and a 64 GB test-job memory limit. Existing frozen
full matrices retain their original resource settings.

At the user's request, a bounded within-simulation threading experiment now
adds `vector-potential --threads 1..24`, default 1. The REANA N64/N128 scaling
runs have byte-identical physical outputs across 1/4/12/24 threads; N128 wall
time is 72.7/25.3/15.2/16.7 seconds. Twelve threads are fastest overall in these
measurements. The N256 24-thread full-wave demonstration completed in 49.1
minutes (earlier serial: 148.0 minutes, different checkpoint clocks), with
positive sampled states and budget residual <=1.171e-12. Its initial CSV
matches the frozen serial reference. See
[threading results and evidence](THREADING_RESULTS.md). This user-authorized
experiment does not imply M1 acceptance or completion of the MPI/3D milestone.

The subsequent [auxiliary-projection study](M1_AUXILIARY_RESULTS.md) adds
`bulk-frame-heun-spline-v1`. All 80 REANA cases and 16 boost pairs complete;
limited jittered standing-wave time slopes improve from 1.729/1.598 to
2.000/2.011. Unlimited magnetic slopes remain 1.704/1.668, and the full
physical/spatial gates remain open. All 102 Rust/29 Python checks pass;
the original profiles are unchanged. Raw outputs and source are archived.

## What the user wants

Latest execution constraint (2026-11-08): the user requested short tests for
development and stopping unnecessary long studies. All four long REANA
workflows are stopped: original 28/112 completed, candidate 100/184,
spline-full 64/112, physics 14 completed + 6 failed of 24. Partial records/logs
are saved locally and raw remote workspaces retained. Use
`scripts/run_shock_repro.py` (four cases, measured .87 seconds) and targeted
unit tests while developing the coupling fix. Hold new long submissions;
passing this short screen does not satisfy M1 or authorize a merge. Report
the candidate's measured short-test results before considering long validation.

The current user request is to pass M1 gates and then merge to main; see
[the merge contract](M1_MERGE_PLAN.md). The 112-case spline wave/loop study
was stopped after 64 completed cases. A [general shock/vortex driver and measurement contract](M1_PHYSICS_PLAN.md)
now implement the M0 Athena comparison packet, including periodic polygon
overlap and a passive shock characteristic-travel diagnostic. Sixteen small
execution probes complete and all eight boost pairs pass, but jittered Brio
Bx diagnostics fail. These probes are not the registered resolution ladder,
and do not establish M1 acceptance. Preserve all failures and historical
profiles; merging is still conditional on the full gates.

The full remote physics study subsequently failed all six jittered Brio
cases before t=.004. See [the diagnostic investigation](M1_SHOCK_INVESTIGATION.md):
smaller dt converges to the same failure, and two tested reconstruction
comparators failed and were removed after archiving. The retained
`--trace-energy`/accepted-state observer and cell/stage error context do not
change physical outputs. The fluid/curl energy mismatch remains unresolved;
do not describe either rejected comparator as a fix or relax the M1 packet.

A subsequent shared-vertex face-normal comparator also fails the short shock
screen (t=.00333372, .85 seconds for four cases), despite eliminating the
initial Riemann face-sum divergence to roundoff and passing seven bounded
operator/Heun checks. It too is archived and removed. See
[the probe evidence](../tests/reference/m1_face_normal_probe/README.md).
The energy-transfer mismatch persists; no accepted M1 fix or merge is ready.

The next initial-state least-squares probe shows that the historical curl
cannot exactly represent the FV induction rate on these jittered meshes:
nx256 retains a .4718 relative rate residual after a converged normal solve.
A separate `bulk-frame-heun-projected-v1` candidate projects each stage's
comoving FV rate onto that curl range. It completes all four short shocks
to t=.01 in 2.62 seconds with positive pressure, conservative budgets and
both boost pairs passing. The jittered Bx error remains .112966 versus the
unchanged 1e-8 gate: the overall short screen still fails. Retain this as a
partial stability improvement only; long jobs stay stopped. See the
[contract and results](M1_SHOCK_INVESTIGATION.md) and
[exact experiment archive](../tests/reference/m1_projected_rate/README.md).

The subsequent initial-curl audit isolates the remaining Bx error. Independent
70-digit free-intercept fits reproduce the Rust gradients. Jittered Brio
initial max Bx errors at nx256/512/1024 are .160355/.149907/.284451; errors
outside stencils spanning an Az slope change are <=3.34e-16. A smooth 1D
control also has nonzero transverse error. This implicates the chosen spatial
reconstruction rather than roundoff; it does not prove the entire code correct.
All 12 probes take 2.29 seconds. No production algorithm or gates change;
see [the audit evidence](../tests/reference/m1_curl_audit/README.md).

The [deeper interpretation](M1_SHOCK_INVESTIGATION.md#root-cause-interpretation-two-separate-errors)
separates the worst initial-field cell 640 from the first pressure-failure
cell 253, which starts with the correct B. Cell 640's fit matrix has condition
number 1.46; inventing a transverse slope reduces the least-squares objective
by 49.25%. The exact neighbour contributions explain its Bx error. A new
figure and reproducible analysis script use only preserved measurements.
The paper cross-check supports the selected affine-fit formula but does not
establish machine-precision Bx for our jitter family. No numerical changes,
gate changes or new evolutions accompany this explanation.

The subsequent bounded development adds `bulk-frame-heun-quadratic-v1`: a
quadratic double-neighbour A/phi derivative coupled to the existing projected
rate. Eight short trials and six t=.02 extensions complete. At t=.02 on the
jittered nx256 shock, the retained candidate reduces max Bx error from .107515
to .0604426 and has minimum p=.0493331, with zero state rejections and passing
budgets/boosts. A concurrent-Hessian face-slope variant is rejected and removed
after giving Bx error .0701692. The 1e-8 gate still fails; this is partial
progress, not a fixed/accepted solver. The wider quadratic fit improves smooth
convergence order but has larger absolute 2D errors on the small ladder and
costs more per run. See [the measured tradeoffs](M1_SHOCK_INVESTIGATION.md) and
[all source/data versions](../tests/reference/m1_quadratic_curl/README.md).
126 Rust, 41 Python and 13 M0 algebra tests pass; strict Clippy/format/reference
checks pass, and ten historical cases retain byte-identical physical outputs.
All long jobs remain stopped. No commit or merge is made by this continuation.

The user's latest steering explicitly requests the Springel–Mayer–Pakmor
formalism. The independent face-integral prototype was removed and archived.
A matrix-rank audit finds a severe numerical representability constraint for
the current jittered Bx gate; it does not authorize changing that gate or
replacing the paper method. See the
[paper-source comparison](M1_SHOCK_INVESTIGATION.md#paper-source-comparison-measured-result).
`paper-state-emf-v1` isolates the literal Eq. (69) state product in both
historical endpoint stages, with linear cell curl and original gauge. Its
unit/uniform tests pass. Both regular short shocks complete, but both jittered
shocks fail at t=.00334288704 (matched default: .00336336379), still at cell
253. The pressure mismatch is unresolved. Do not continue independent
projection/face-integral method development under the paper's name.
127 Rust tests, strict Clippy and formatting pass; ten historical wave/loop
cases remain byte-identical. Exact source and raw observations are in
[m1_paper_audit](../tests/reference/m1_paper_audit/README.md). The latest work
is uncommitted; no full acceptance or merge is claimed.

Develop a new **Rust** scientific HPC code implementing the new **moving-mesh magnetic vector-potential ideal-MHD** method presented in **Springel, Mayer & Pakmor (2026), arXiv:2609.35989**. The target is an independently developed, scientifically validated, **hybrid MPI/Rayon** code runnable on the user's **Mac Pro** for local development and later on Slurm clusters for multi-node scaling. The initial discussion also considered C++ with MPI/OpenMP; the user explicitly preferred the additional **Rust implementation** and asked to preserve the plan in GitHub for future coding.

User repository: **https://github.com/arm2arm/openmhd-rs-**. The trailing hyphen in `openmhd-rs-` is intentional and part of the actual repository name. It is **public**, with an existing **MIT** license; the user explicitly wants public visibility.

## Conversation decisions in chronological order

1. Asked for the main findings of arXiv:2609.35989. Discussion centered on a new vector-potential, moving-Voronoi mesh approach to ideal MHD, aiming for stable magnetic-field evolution and Galilean invariance.
2. Asked whether we could implement the physical method using MPI/OpenMP. Initial engineering proposal used C++20, finite-volume ideal MHD (HLLD as candidate), moving Voronoi meshes, second-order integration, 3D, MPI/OpenMP, refinement and local timesteps, with quantitative validation and Slurm benchmarks.
3. Asked whether it could be written in Rust. Agreed target: Rust 2024 + `mpi`/rsmpi + Rayon, `f64` scientific precision, HDF5/Slurm, 2D serial validation first and MPI/3D later. Rayon replaces OpenMP for native Rust loops; MPI provides multi-node scaling.
4. Asked to create a GitHub project and save the plans. The repository `arm2arm/openmhd-rs-` was created by the user; the assistant published planning documentation and 17 GitHub issues to `main`.
5. Confirmed project should be **public**, not private. README and docs describe the planning-only state; existing MIT LICENSE was detected and preserved.
6. On Nov 3, 2026, asked to move this ChatGPT discussion to **Codex on the user's Mac Pro**. This file and root `AGENTS.md` enable an effective **project handoff** through Git; they do not migrate the actual conversation thread, Codex session history, or the Mac's local filesystem.

## Current GitHub state at handoff

- Repository: `arm2arm/openmhd-rs-`, default branch `main`, public.
- Planning docs: `README.md`, `docs/ROADMAP.md`, `docs/NUMERICS.md`, `docs/ARCHITECTURE.md`, `docs/VALIDATION.md`, `docs/PARALLEL_HPC.md`, `docs/REFERENCES.md`, `docs/DECISIONS.md`, `docs/ISSUE_BACKLOG.md`.
- Contribution policy in `CONTRIBUTING.md`; example Slurm script in `examples/slurm/hybrid.sbatch`; GitHub issue templates.
- Issues #1–#17 cover M0 numerical-method extraction, M1 serial solver, M2 3D moving mesh, M3 MPI/Rayon, M4 adaptivity/physics, M5 scientific release, and governance.
- **No validated or compilable MHD solver has been implemented.** The Slurm script is illustrative, not runnable at this stage.

## Scientific requirements that must not be simplified away

- The equation `B = B_mean + curl(A)` identifies the strategy, **not an entire implementation**.
- M0 must extract the **exact published discrete equations**, including gauge choice, smooth auxiliary velocity, terms/signs, cleaning, mesh/timestep coupling, treatment of periodic mean magnetic flux and any positivity/energy subtleties. Existing planning docs are not authoritative transcriptions.
- Verify and document the exact relation between vector potential, the solver's discrete curl, independent `div(B)` diagnostics, and conservation. Avoid an unjustified blanket assertion of machine-zero `div(B)`.
- The numerical scheme must pass **Alfvén wave, magnetic flux-loop advection, Brio–Wu shock tube, Orszag–Tang, 3D field advection/blast, MRI and magnetized-collapse** tests as the relevant physics modules become available.
- Numerical targets should be declared in advance, assessed via resolution studies and compared with the paper where possible. Reproducibility includes configs, code revision, hardware/compiler/MPI/runtime and plotted error data.
- MPI domain decomposition, cross-boundary face flux conservation, Rayon race-free face reductions, geometry rebuilds after mesh movement, per-cell timesteps and adaptive remapping are separate milestones, not trivial add-ons.
- Avoid reusing/copying AREPO source without checking licensing, provenance and whether the user's requested independent method warrants it.

## Proposed order of work

**M0 — scientific specification (#1 and #2):** Read the full primary paper; produce a detailed equation-by-equation, stencil-by-stencil, and stage-by-stage implementation plan. Resolve 2D embedding, boundary conditions and mean field. Predeclare benchmark reference curves/tolerances.

**M1 — serial Rust baseline (#3–#7):** Introduce a Cargo workspace, EOS/conservative states, robust HLLD-style moving-face fluxes, 2D Voronoi mesh, paper-specific A evolution and diagnostics, with analytic/small benchmarks.

**M2 — 3D moving mesh (#8–#9):** Real 3D dynamic Voronoi geometry, smooth velocity/gauge, full moving-face operations, 3D published cases.

**M3 — hybrid HPC (#10–#12):** rsmpi ranks, ghost halos and geometry, consistent face owners, Rayon kernels and Slurm strong/weak scaling with correctness checks.

**M4 — advanced physics (#13–#15):** Mesh refinement/derefinement, local timesteps and optional gravity/magnetic collapse.

**M5 — scientific release (#16):** Documented numerical tests, open reproducibility data, performance report and deviations from the paper.

## First Codex session

Open this repository locally on Mac Pro and give Codex the prompt in `codex/FIRST_TASK.md`. Start at M0, GitHub issue #1. Treat the full paper as authoritative for numerical claims. Do **not** invent code or claim the solver already exists.

## Open questions for a later design decision

- Which Rust Voronoi geometry implementation survives 3D periodic moving-topology robustness tests?
- Should M1 use 2D unstructured Voronoi from the start or a temporary, strictly labeled structured-mesh verification kernel?
- Exact face flux method and fallback, reconstruction and limiting choices compatible with the paper.
- Gravity and cosmological coordinate extensions: optional and out of initial M0/M1 scope.
- Mac Pro architecture (Intel or Apple Silicon), macOS version, local compiler/MPI availability; obtain from the machine rather than guessing.
