# Handoff from ChatGPT conversation to Codex

*Prepared November 3, 2026. This is a curated, faithful project-context summary of the ChatGPT discussion, **not** a verbatim export of the ChatGPT conversation or a transferable Codex chat session.*

## Final M1 continuation (2026-11-21, in progress)

2026-11-22 recovery: a host reboot terminated the detached driver and notifier.
The retained checkpoint had 24/24 mean and 47/48 medium cases, with no required
physical failure; medium workflow `openmhd-fu-iter-medium-1e2aacc98313-0014.1`
was still `created`. After validating all 62 expected input sizes, the same
workflow was started and finished successfully. Fresh medium 48/48 and mean
24/24 cases now pass, as does the short bounded stage. All 72 final CSVs are
byte-identical to A; fresh independent reductions pass all 36 boost pairs.
The [fresh checkpoint](../tests/reference/m1_acceptance/fresh/README.md)
retains their verified input/execution identities and exact phase records.
The full 112-wave and 30-physics plans have completed their upload/start
transport stages, and the supervisor is collecting both. Supervision uses the task-specific
login service `org.openmhd.m1-final-20261121`, which resumes the existing
immutable plans after reboot and removes its plist after confirmed coordinator
notification. No numerical sources or case thresholds changed. Live logs and
the previous state are retained under the existing tools directory, including
`recovery_20261122/` and `service_installation.json`.

Full-wave submission hit the legacy client's 300-second `run` timeout.
`driver/transport_plan.py` now resumes the same planned workflows through
authoritative status/listing checks, missing-input uploads and same-workflow
starts. It changes host transport only, preserves input hashes and keeps
eight HTTP clients without capping concurrent remote cases. The old submit
clients were stopped before the replacement service resumed; checkpoint and
host source copies are retained in `transport_recovery_20261122/`. Inspect
each plan's `transport.jsonl` and `submission.json`; do not create replacement
workflow identities for uncertain uploads.

The owner also set the [3D galaxy-merger goal](GALAXY_MERGER_PLAN.md) and
authorized parallel agents. Source/specification work for geometry, gravity/
particles and multiphase ISM proceeds independently while M1 finishes. Coupled
3D implementation remains behind its scientific prerequisite.

The geometry and gravity design/source contracts are now recorded in
`docs/galaxy/MESH_3D_SPEC.md` and `docs/galaxy/GRAVITY_PARTICLES_SPEC.md`, with
hashed primary-source inventories. The
[shared integration contract](galaxy/INTEGRATION_CONTRACT.md) reconciles their
IDs, units, force epochs, source ledgers and endpoint birth activation.
These are unimplemented designs. The candidate geometry library requires
periodic-face/normal-sign fixtures and a complete locked license audit;
moving GCL/projection and bounded magnetic boundaries need separate review.
The ISM/cooling source contracts now include the published SH03 finite-phase
equations, a complete primordial coefficient map with an explicit proposed
dielectronic-sign correction, and the exact author FG20 external-input
identity. Historical SH03 UV identity and permission for raw FG20 data
redistribution were not established. The independent review below does not
supply rate/threshold/ISM numerical evidence, which remains pending.

2026-11-22 source/design review continuation: the independent
[ISM/cooling review](galaxy/ISM_COOLING_DESIGN_REVIEW.md) supports the
transcribed source algebra but found inconsistent subcycled birth metadata.
The shared/gravity interface now preserves each actual source subinterval,
with `formation_end <= activated_at`; all packets activate atomically at
the accepted global endpoint, including their mutual potential-energy terms.
The four ISM/cooling contracts still require the review's root, domain,
tracer and private-input policies before coupled use. The
[direct-gravity source check](galaxy/G1_DIRECT_GRAVITY_REVIEW.md) supports
only units, common fixed-Plummer forces and collisionless KDK equations;
its G1 numerical/reference gates remain unexecuted and M1-dependent.

The independent [M2 design review](galaxy/MESH_3D_DESIGN_REVIEW.md) found six
blocking moving-stage issues: target-frame reduction, explicit corrector/
projection composition, centroid order, transient topology control,
magnetic/thermal and mean-flux accounting, and raw auxiliary/gauge formulas.
They require author revision before moving-MHD implementation. The first
bounded physical reference is now the
[conducting slip box](galaxy/BOUNDARY_MHD_SPEC.md), with unbounded particles
and isolated gravity; the shared/gravity contracts defer general outflow.
Its constrained boundary operators and global reflection fixture remain
unaccepted, with independent findings below. The [analytic geometry packet](galaxy/fixtures/README.md)
and [backend metadata audit](galaxy/dependency_audit/README.md) contain design
inputs/source-byte evidence only. No geometry implementation or dependency
adoption is implied; full locked distribution/license closure remains open.

The author has now replaced the old finite-endpoint moving projection in
[the revised moving-stage proposal](galaxy/MOVING_MHD_STAGE_SPEC.md), after
a manual second-order counterexample. The new covariant-rate increment
scheme requires fresh independent review, Cdot/topology/mean compatibility
evidence and the existing numerical gates; it is not an accepted algorithm.
The independent [bounded-MHD/fixture review](galaxy/BOUNDARY_MHD_DESIGN_REVIEW.md)
supports the seven analytic geometry expectation sets, but requires wall
pressure, constrained-map/adjoint consistency and a globally compatible
reflection packet to be revised. The dependency audit now retains complete
candidate grant/notice texts as well as metadata, without adopting the library.

The latest independently reduced partial wave checkpoint has 88/112 fresh
snapshots and 34 passing boost pairs, with no verified required failure;
all 88 snapshots are byte-identical to A. Three of eight spatial ladders are
complete and pass: regular speed-1 comoving (finest-three order 1.93624),
jittered standing comoving (1.90986), and jittered speed-1 fixed (1.88339).
Nine temporal comparisons are available. The other ladders remain pending.
The input/receipt-checked staging and report are retained under
`results/independent_fresh_waves_checkpoint_20261122_0008*` and are deliberately
not full-phase/M1 acceptance evidence. All 112 wave workflows have now passed
their upload/start transport stage, as have all 30 physics workflows. The
same supervisor is collecting both plans; do not duplicate their identities.
Twenty-nine physics cases have 53 actual fresh byte-verified inputs: 29 final
snapshots, 18 geometry files and six projected-bin files, all identical to A.
Fourteen independently reduced boost pairs pass, including the fresh N256
regular vortex pair. The latest isolated input/identity checkpoint is
`results/independent_fresh_physics_checkpoint_20261122_0009/`; the boost
report is at
`results/independent_fresh_physics_boost_checkpoint_20261122_0007/`. Exact
collector/wrapper source bytes are retained with those observations. The
strict 30-case phase and boost verifiers are unchanged; partial reports cannot
satisfy that requirement. Missing later cases remain pending.

All twelve primary fresh shock cases are now independently reduced over
their actual rectangular geometry, using the unchanged 50-digit reference
integrator. All four reference ladders pass; the maximum norm discrepancy
with recorded measurements is `3.8163916471489756e-16`. The actual snapshots,
geometry, input hashes and reducer are retained in
`results/independent_fresh_shock_checkpoint_20261122_0001/`. Vortex ladders and
the remaining matrix still gate M1.
The latest independent vortex checkpoint, `results/independent_fresh_vortex_checkpoint_20261122_0005/`,
now reduces all six primary cases, including both fresh N256 regular cases.
Its largest norm discrepancy is `1.1102230246251565e-16`; both complete
64/128/256 ladders pass all four field checks. The jittered N256 boosted
vortex remains pending, so physics-phase completion and its fifteenth boost
pair remain unaccepted. Earlier immutable partial observations are retained.

The read-only host utility
`tools/m1_evidence/prepare_final_evidence.py` is now
prepared for the final completion event. It checks terminal phase counts and
the seven-phase verdict before creating a new output directory, then calls
the unchanged strict phase verifiers and all six independent reducers. It
will read all 238 consumed raw inputs (214 final CSVs, eighteen primary
geometry files and six projected-bin files), report exact A identities,
preserve command/source/observation hashes and close its own inventory.
The new utility's readiness guard read the actual pending plans, returned
exit 2 and created no output; its complete-input execution remains pending.
Its source was syntax-parsed and inspected. It submits no workflows, changes
no production source and cannot accept M1. Invoke with a fresh `--output`
path after the existing service produces the final registered verdict; do
not replace the live supervisor with it. Final separate review and parent/
reviewer archive closure still follow its successful execution. The new
[archive boundary plan](M1_FINAL_ARCHIVE_PLAN.md) and tracked
[host tools](../tools/m1_evidence/README.md) prepare an immutable evidence
subpacket, a separate later reviewer boundary and final outer closure.
The packager preserves historical source bytes rather than requiring later
3D development files to stay frozen. Its complete-input/portable execution
is unperformed; no final numerical-output review, gate or M1 acceptance is inferred.

The [independent archive design review](M1_FINAL_ARCHIVE_DESIGN_REVIEW.md),
committed in `b402753`, identifies four high and four medium host-workflow
findings. The complete path must be repaired before use: wave-stage symlinks
currently leave the collection, and portable manifest/provenance/coverage
checks are incomplete. Coherent observation, transport/timeout receipts and
optimized-execution guards also need correction. These are source/metadata
findings, not M1 scientific failures; the live campaign is unchanged.
Two parallel authors are repairing the collector and packager/verifier.
The separate metadata REANA runner is source-prepared with one workflow per
unittest after an actual source/import preflight, pinned committed sources,
per-job resources and no scientific evolution. Its execution remains pending
until the repaired tools and tests are ready; it grants no physical acceptance.

The new independent [moving-stage review](galaxy/MOVING_MHD_STAGE_DESIGN_REVIEW.md)
supports the revised conditional smooth prescribed-path ODE order, while
requiring sharper transient-event coverage/exchange/reference semantics and
all numerical gates. It does not establish spatial/mean compatibility,
state-dependent motion, bounded operators or moving-MHD acceptance. The
[author follow-up](galaxy/CURL_3D_MEAN_SPEC.md), committed in `3b9719c`, now
separates mandatory event coverage, noncancelling transient exchange and
surface/time versus centroid-rule references, with event-width-relative root
uncertainty. It also derives a separately named periodic shared-face curl
comparator and its moving mean identity. This changes B sampling to a
cell-average approximation; the raw point-LS reference remains available.
The independent [curl/event review](galaxy/CURL_EVENT_DESIGN_REVIEW.md),
committed in `5cdf51d`, supports F1–F9 algebra and E1–E5 design semantics
under their stated assumptions. It requires literal rounded-input/oracle
identities, distinct surface and centroid-rule reducer definitions, and a
stage point-versus-cell-average wording correction before those packets.
The author clarification `23b7770` now specifies the actual dyadic-input
oracle target, separate exposure reducers, sampling IDs and deterministic
periodic CPQR/kappa1 policy; new independent review and literal fixtures
remain required. F1–F9 and S1–S19 equations are unchanged.
The comparator and smooth metric-support comparison remain unadopted;
spatial, conditioning, Cdot, switching, energy/partition and physical
evidence remain pending. Mean cancellation alone proves none of those gates
or bounded/state-dependent moving MHD. The
[softened spherical-equilibrium source note](galaxy/SPHERICAL_EQUILIBRIUM_SOURCE_NOTE.md)
now supplies primary inversion references and manual center/edge derivations
for a concrete proposed G-EQUIL-SOURCE target. The independent
[equilibrium/sampling review](galaxy/EQUILIBRIUM_SAMPLING_DESIGN_REVIEW.md),
committed in `d1059b8`, supports its source algebra but requires separating
the fixed-taper Newtonian limit from the untapered Plummer control and
defining virial kinetic energy in the center-of-mass frame. Explicit DF
domains and independently frozen DF/CDF error budgets also remain required.
Numerical DF positivity/reconstruction/sampling/live evidence is pending;
no equilibrium or disk/merger result is claimed.
The author correction `d3d156d` now makes the two Newtonian controls and
DF domain explicit and uses COM-relative internal kinetic energy in the
unchanged 2% virial gate, retaining laboratory energy and actual sampled
P/L. Independent review of the new bytes and DF/CDF budgets/evidence remain
pending.

The new [axisymmetric Jeans source note](galaxy/AXISYMMETRIC_JEANS_SOURCE_NOTE.md)
records an unreviewed manual radial mixed-moment derivative discrepancy in
the retained Y14 Eq.24, a reduced tilt/axis formula, and a conditional
negative-moment edge result for an untilted constant-anisotropy closure with
the proposed separable radial-only taper. It changes no selected density
or scientific gate. Independent review and a compatible complete rotating
galaxy density/stress prescription are required; no stellar or gas/MHD
equilibrium is accepted.

The separate [state-dependent motion proposal](galaxy/STATE_DEPENDENT_MESH_MOTION_SPEC.md)
defines an explicit fluid/centroid-regularized velocity law, a separate
wall-relative taper and augmented Heun stages with distinct old, predicted
and corrected geometries. The corrector uses the predicted tangent metric;
GCL uses the actual corrected volume. Its manual smooth-ODE order argument
includes the velocity law's state dependence. It is unimplemented,
unexecuted and unreviewed, and does not replace the selected prescribed-path
profile. A predictor-only face can differ from the proposed continuous
trajectory's actual face: path-aware accepted exchange/controller design
remains an explicit blocker, alongside all spatial, bounded, gravity/source
and full merger evidence. No 3D numerical acceptance is inferred.

The proposed [IC random-address and sampling contract](galaxy/RANDOM_SAMPLING_SPEC.md)
selects a separate SHA-256/open52 stream using the existing pinned hash
primitive, explicit typed-ID/seed/purpose bytes and inverse-CDF spherical
sampling. It preserves the existing half-open SF stream. Complete official
hash/vector sources and context identities are pinned without executing
vectors or draws. The same independent review supports its address/open52
algebra within scope. Accepted DF/CDF inputs and all new REANA
hash/address/endpoint/scheduling/sampling cases remain pending; this is not
an accepted RNG or equilibrium generator.

The revised ISM/cooling policy contracts (`6d8f634`) now define finite root
and event policies, actual-subinterval atomic births and new-new GP2 terms,
passive-metal bounds and prospective private-UV handling. The revised bounded
contract (`bed56a4`) supplies physical wall shock/rarefaction pressure and
explicit vacuum rejection, fixed-geometry operator maps and a global
reflection reference. The separate
[policy review](galaxy/ISM_COOLING_POLICY_REVIEW.md) identified an entry-event
unit mismatch and an incompatible manufactured timestep ladder. The narrow
author correction `a7ef086` uses specific-energy and mass guard scales,
explicit unit/parcel representations, a shared finer ladder and an additional
heating-only level 5. The failed level-4 history bound is retained, all norms
and gates are unchanged, and discrete BE and continuum references are distinct.
This correction still needs independent review and numerical evidence.
Owner authorization for project REANA tests already exists; actual private
FG20 input/restart/artifact visibility and retention remain unverified.

The independent [bounded revision review](galaxy/BOUNDARY_MHD_REVISION_REVIEW.md),
committed in `59bc5c8`, supports W1–W5 wall-pressure algebra but finds a blocking
signed-cubic O7 kernel error: its inner cubic must use the absolute value.
Literal column scaling/conditioning and reflection-response/aperture/lag
definitions must also be frozen before the corresponding fixture packets.
The author revision `f3fa362` corrects the even O7a kernel and specifies a
QR/Frobenius convention and unit-response reflection estimator. These new
bytes require separate review; no numerical evidence was executed.
U1–U4, all numerical gates and coupled physics remain unaccepted. The mesh
author's narrow ISM provenance cleanup in `3b9719c` now distinguishes the
unretained historical working copy from reproducible committed `6d8f634`.

The [independent dependency review](galaxy/MESH_DEPENDENCY_REVIEW.md) supports
the isolated candidate's license elections but found missing additive MIT
notices in glam's `ATTRIBUTION.md`. The exact attribution is now retained in
a [readable notice candidate](galaxy/dependency_audit/release_notice_candidate/THIRD_PARTY.md)
with all 33 audited packages' materials and selected source notices. Its
91 files reproduce byte-for-byte from checked archives and retained texts.
The earlier audit observations remain unchanged. The independent
[notice-repair review](galaxy/MESH_NOTICE_REVISION_REVIEW.md), committed in
`59bc5c8`, closes the missing-attribution finding and supports this intended
91-file layout. The actual integrated graph, feature unification and final
source/binary/container artifact inspection remain open; the dependency has
not been adopted.

The owner authorized continuing until M1 is finished, without asking for
routine decisions. [The final sequence](M1_FINAL_ACCEPTANCE_PLAN.md) retains
campaign A, including the measured smooth-extrema limiter tradeoff and
historical trial fraction 1. B's .95 fraction remains optional; no binary
default changes. Full M1 acceptance is still pending, not inferred from the
owner's authorization.

The [provisional final-review packet](../tests/reference/m1_acceptance/README.md)
now independently reduces A's 112 wave snapshots, all 99 registered boost
pairs, twelve primary shock cases and six primary vortex cases. All checked
norms/gates pass, with rounding-level agreement with production measurements.
It records current prescribed-flow source dependencies without asserting a
fresh full-ladder reproduction. The current source audit now distinguishes
the integrated iterative/smooth-extrema configuration from historical
cached-solve/default-limiter choices.

A fresh registered campaign is running from development source `2bdcea0`:
`openmhd-m1-final-preflight-20261121.1`, immutable snapshot SHA256
`b67ce03779a194099983b7ff07c0cafed23e9ea3a9051047492d072255e0160f`.
The preflight passes all eight commands: fmt, strict all-feature Clippy,
236 debug Rust tests, release build, 163 Python tests, 13 M0 algebra checks,
reference integrity and 245 release/all-target Rust tests. The
detached driver in `results/m1_final_campaign_tools_20261121/` waits for its
actual result before short bounded, medium + mean, precondition and full
waves + physics. It survives chat sessions, preserves same-workflow recovery
and cancels unnecessary active siblings only on a verified required failure.
Do not launch duplicate campaigns. Its source record and the submission
snapshot are retained in the provisional packet. The
[separate AI review](M1_FINAL_AI_REVIEW.md) conditionally approves the source,
historical reductions and prescribed-flow applicability, with no scientific
source blocker in the declared scope. Actual fresh physical outputs, their
independent reductions/complete input identity checks, and a final output
review remain required before acceptance. A completion notifier reads only
the existing driver's local state and wakes this coordinator Run when the
driver ends; it never duplicates workflows or accepts M1.

## Candidate solve decision (2026-11-19)

The owner made the iterative projection the candidate's standard solve. The
M1 validation candidate is now `bulk-frame-heun-quadratic-v1
--projection-screening 1 --riemann hlld-pressure --potential-limiter
smooth-extrema` without `--accelerated-projection`.

- **Evidence.** It passed every registered phase check as campaign A, and it
  reproduces the cached-solve campaign of 2026-11-14 to the solve's 1e-11
  tolerance ([evidence](../tests/reference/m1_iterative_step_campaigns/README.md)).
- **Measured cost.** In the speed-up review it was 1.05–1.28 times faster at
  N128 and N256, used 4–6 times less memory, and was two times slower in the
  small 512×4 Brio–Wu case.
- **Running it.** Use the `iter-*` plans, `run_m1_bounded.py
  --iterative-projection` and `fanout_campaign_verdict.py
  --iterative-projection` ([plan](M1_FULL_VALIDATION_PLAN.md#configuration-under-test)).
- **Unchanged.** `--accelerated-projection` and every binary default.

At that checkpoint still open: independent review, the owner's decision on the opt-in limiter,
deforming meshes (Heun is fixed/rigid only), and adoption of B's step
fraction. B's execution is complete; see its result below. Not M1 acceptance.

## Branch integration (2026-11-18)

On 2026-11-18 the owner asked to merge every unmerged branch into `main`.
Branch `arm2arm/merge-all-developments` brings in, as a development
checkpoint:

- the five `arm2arm/m1-iterative-step-campaign` commits (the iterative and
  step-fraction campaign options, declaration and comparison script); see
  [their outcome](#iterative-projection-and-step-fraction-campaigns-2026-11-1718);
- the three 2026-11-09 commits left on
  `arm2arm/m1-run-alfv-n-wave-and-field-loop-benchmarks` after #23: the
  fixed/rigid Voronoi [CT comparator](M1_CT_COMPARATOR.md), the coupled
  [CT admissibility limiter](M1_CT_POSITIVITY.md) and their evidence. Its
  Rusanov comparator flux joins main's Riemann selection as a separate flag;
  every existing caller passes `false` and is unchanged;
- the [mesh-motion visualisation](MESH_MOTION_VISUALIZATION.md) of
  `arm2arm/M0`, cherry-picked from `d059fb4`.

Those three parts merged as #28. Branch `arm2arm/merge-m0` then merges the
other 42 `arm2arm/M0` commits (2026-11-05). They are an earlier, independent
implementation of the same #7 work; main later built files with the same
names differently, and 24 files conflicted. The rule for every resolution:
main's profiles, options and output bytes stay as they were, and the
`arm2arm/M0` features are added beside them, selected only by their own
names.

- **Solver:** the six opt-in `bulk-frame-hll-*` profiles. The symmetric-fan
  A-face completion is a third `FaceCompletion` variant (`M0`'s
  `RiemannState` is main's `Intermediate`). `M0`'s quadratic module is now
  `moving_mesh::quadratic_jet`, beside main's `quadratic`. Its quadratic,
  compact, matched and projected fits are `MagneticFit::with_projection` and
  `Geometry::jet_fit`, and its centred face weights and curvature-corrected
  transport apply only to those fits; every other profile calls main's
  unchanged fit. Its signal-travel counters are computed for its profiles
  only. Its stoppable observer, `advance_with_observer`, now drives main's
  `advance_to_observed`.
- **Checkpoint/restart** with the `mhd-io` crate (`sha2`, MIT/Apache-2.0),
  the exact mesh cache and polygon output. Restart covers the eight `M0`
  profiles with default options and refuses everything else; see
  [CHECKPOINT_RESTART.md](CHECKPOINT_RESTART.md).
- **CLI:** `--checkpoint-steps`, `--restart-out`, `--resume`,
  `--stop-after-steps`, `--mesh-cache`, `--mesh-only` and `--nx` (= `--n`).
  The `M0` case names `brio` and `vortex` run the same setups as `brio-wu`
  and `orszag-tang` with `M0`'s defaults and outputs (`polygons.csv` and its
  summary fields). Restart runs use `M0`'s output loop; all other runs use
  main's.
- **Scripts:** `M0`'s versions of three add/add tools are
  `archive_m1_hll_completion.py`, `plot_m1_hll_completion.py` and
  `test_m1_hll_archive.py`, and its wave driver is `run_m1_hll_wave_loop.py`.
  Main's `run_m1_wave_loop.py` is unchanged. Main's REANA runner already
  fails a pair that passes only the alternate normalization, so `M0`'s
  relabelling of such pairs stays in `M0`'s driver.
- **Docs:** `M0`'s plan and AI review are
  [M1_HLL_COMPLETION_PLAN.md](M1_HLL_COMPLETION_PLAN.md) and
  [M1_HLL_COMPLETION_AI_REVIEW.md](M1_HLL_COMPLETION_AI_REVIEW.md). Its
  results are in [M1_IMPLEMENTATION.md](M1_IMPLEMENTATION.md),
  [M1_HLL_RESULTS.md](M1_HLL_RESULTS.md),
  [M1_MATCHED_RESULTS.md](M1_MATCHED_RESULTS.md),
  [M1_COMPACT_RESULTS.md](M1_COMPACT_RESULTS.md),
  [M1_PROJECTED_CONTROLS.md](M1_PROJECTED_CONTROLS.md) and
  [M1_WAVE_DIAGNOSTICS.md](M1_WAVE_DIAGNOSTICS.md). Its evidence is under
  `tests/reference/m1_completion` and `checkpoint_restart`. Archived review
  scripts and provenance records keep the `M0` paths. All irregular Alfvén
  ladders of those studies fail the 1.8 order gate (best 1.64).

The ported `M0` code is not the code that produced `M0`'s archived numbers;
those come from the `M0` commits, which are ancestors after this merge. No
default, profile or threshold changed. Not M1 acceptance.

**Verification on REANA (2026-11-18).** The baseline is the binary
`fc49c442…` that the #28 preflight built from main's pre-merge code.

- `openmhd-m0fix-preflight-20261118` on `d0f74e5`: all eight commands
  pass. 236 debug and 245 release Rust tests and 162 Python tests, none
  failing.
- `perf-compare-historical` on `f99683c` and again on `d0f74e5`: all seven
  historical-profile cases are bit-identical to the baseline.
- `perf-compare` on `f99683c`: all 12 campaign-configuration comparisons
  are bit-identical. They include N256, Brio-Wu and Orszag-Tang with their
  physics, geometry and shock-face files, and the iterative projection.
  `d0f74e5` changes only a test file.
- The first preflight, on `f99683c`, failed in one restart test that
  expected `polygons.csv` from a default-profile run; `d0f74e5` fixes the
  test. Records are under `results/reana_remote_m0*_20261118`.

## Standing-wave limiter controls (2026-11-13, issue #26)

Nothing below is reviewed or accepted. No gate, threshold, grid, reference or
default changed, and M1 remains unaccepted. The work was paused by the owner
on 2026-11-12 and resumed on 2026-11-13.

**Cause.** The registered controls support hypothesis H1 of the
[plan](M1_STANDING_WAVE_PLAN.md): the neighbour-extrema limiter applied to
the `A` gradients of the `b · grad(A)` transport clips smooth extrema of `A`
where fluid moves through a fixed mesh. Switching off only that limiter
(`--potential-limiter none`) raises the regular N64→N128 B L1 order from
1.643 to 1.932 and both standing ladders to **1.9590** and **1.8834** (gate
1.8; baseline 1.6591 and 1.7705). Unlimiting the primitives instead leaves
the order at 1.635 and the distortion at the potential extrema.
[Numbers, reducers and run records](../tests/reference/m1_standing_limiter/README.md).

**Candidate.** `--potential-limiter smooth-extrema` (opt-in, engineering
choice, defined in the plan) keeps the limiter and widens its bounds by a
curvature that two cells confirm.

- **Standing ladders pass the unchanged gate:** finest-three orders 1.9590
  (regular) and 1.8834 (jitter .15), all eight boost pairs pass. It
  reproduces `none` (byte-identical on the regular mesh at every resolution).
- Screens (98 workflows, all completed, no registered gate fails): 24/24
  wave and loop boost pairs at N32/64, 12/12 mean-field pairs, and the
  26-case shock/vortex screen with reference errors within .9984–1.0021 of
  the baseline.
- Measured cost: fixed-mesh loop passive errors are 3–10 % larger than the
  baseline's and the potential undershoot at the loop rim is 17–36 % larger.
  No registered gate measures this.

**Full registered sequence for this configuration: every registered phase
check passes (2026-11-14 17:35 UTC).** It was declared before execution in
[M1_FULL_VALIDATION_PLAN.md](M1_FULL_VALIDATION_PLAN.md#explicit-smooth-extrema-continuation-2026-11-13-before-execution),
which also holds the result table.

- Frozen source `7fef6e2`, snapshot SHA256 `e6f390ef…`, per-case binary
  `7544a6ab…`. 214 per-case workflows and one short-stage workflow, none
  failed or timed out.
- All eight Alfvén ladders pass (orders 1.8834–1.9590; the two that failed
  with the default limiter give 1.9590 and 1.8834). 48/48 wave and loop boost
  pairs, 12/12 mean-field pairs, 15/15 shock/vortex pairs and every
  shock/vortex gate pass. The N256 loops completed for the first time.
- Verdict, summary and run records:
  [tests/reference/m1_standing_limiter](../tests/reference/m1_standing_limiter/README.md#8-fan-out-campaign-from-the-campaign-snapshot-2026-11-13-to-14).
  Raw snapshots stay in the REANA workspaces and, locally, under
  `results/limiter_campaign_*_20261113`.
- The 162 cases shared with the earlier screens, which used another build of
  the same Rust sources, are byte-identical.
- It took 25.5 hours; N256 loops need 11.5–15.2 hours each. For the
  speed-ups that followed, see the next section.

**Open, and not the implementing assistant's to decide:** whether an opt-in
limiter that admits curvature-confirmed extrema, with its measured 3–10 %
cost on fixed-mesh loop diagnostics, becomes the M1 configuration; and
independent review. No default changed and M1 remains unaccepted. Issue #26
has not been updated. On 2026-11-17 the owner asked to push and merge these
commits, with the speed-ups below, into `main` as a development checkpoint;
that is not M1 acceptance.

How the sequence was run, for the next one: a detached driver
(`results/limiter_campaign_tools_20261113/driver_long.sh`) submitted the long
plans, finished uploads that stopped midway, checked both plans every ten
minutes from an export of the snapshot's scripts and wrote the verdict. The
check refuses to run if a `scripts/` or `benchmarks/` file differs from the
plan, so always run it from such an export
(`git archive <revision> scripts benchmarks reana | tar -x -C <dir>`). If
`/tmp/openmhd-reana-command.py` is gone, recreate the client adapter (it
reads `~/.config/openmhd/reana-p4n.json` and must redact the token).

## Result-preserving solver speed-ups (2026-11-16/17, issue #26)

The owner asked on 2026-11-15 for a review and speed-up because the N256
tests did not finish in reasonable time. Branch `arm2arm/perf-solver-speedup`
on top of `32155bc`, merged into `main` at the owner's request on 2026-11-17;
not reviewed.

- **What changed:** each geometry validated once, CFL-rejected trials stopped
  before the projection, accepted closures reused, a faster Voronoi clipping
  kernel, a flat parallel curl and transpose, per-cell pressure-blend ratios
  and parallel vector updates in the iterative projection. Every change keeps
  the floating-point operations and their order. Commits, tests and numbers:
  [tests/reference/perf_identity](../tests/reference/perf_identity/README.md).
- **How it was checked:** the REANA study `perf-compare` runs six short
  excerpts of the campaign configuration with the campaign binary `7544a6ab…`
  and with the new build; all physical outputs were byte-identical. The
  `m1-fanout-preflight` study runs the tests on the same snapshot.
- **What remains:** the cached-Cholesky solve is two thirds of the stepping
  time in the campaign configuration, and the mesh build stays superlinear
  in its fixed clip order. Neither can go faster without changing results.
- **Open, for the owner:** the iterative projection instead of the cached
  factorization (roundoff-level change), the opt-in `--trial-step-fraction`
  (every rejected trial missed the bound by less than one per cent and was
  halved), and a different mesh build order. None is adopted and each would
  need the registered matrix again.

## Iterative-projection and step-fraction campaigns (2026-11-17/18)

**Status (updated 2026-11-21).** A finished on 2026-11-18 at 10:03 UTC;
B's resumed driver finished on 2026-11-19 at 16:32 UTC. The evidence is in
[tests/reference/m1_iterative_step_campaigns](../tests/reference/m1_iterative_step_campaigns/README.md),
with A archived on 2026-11-19 and B's archive/comparison completed on
2026-11-21. Both pass all seven registered phase checks.

- **A (`iter`):** every registered phase check passes, and the eight ladder
  orders equal those of 2026-11-14. The registered reproduction measurement
  finds agreement to the projection solve's 1e-11 residual tolerance, not to
  roundoff. The largest relative differences in the named quantities are
  1.6e-9 and 1.8e-9, against the expected 1e-10. In 4 of 214 cases a
  discrete decision flips: a few HLL fallbacks, or one CFL rejection. No gate
  outcome changes. The comparison tool first matched summary lists by
  position, and A's reordered upload put its boost pairs out of order; it now
  matches rows by identity. On 2026-11-19 the owner selected A as the
  candidate's standard solve (see the decision above).
- **B (`step`):** initially stopped at 20:44 UTC on 2026-11-17, before its long
  phases. At its precondition check the result download of medium case
  0034 had failed ("REANA download failed"); 13 minutes earlier that case
  had been counted as complete. Every physical check of the phase passed;
  only `terminal_without_errors` and `every_planned_case_completed` failed.
  This is an observation failure, not a physical one. The case's workflow
  finished at 18:54 UTC with all outputs. At the owner's request B resumed
  alone at 07:58 UTC on 2026-11-19, after the result was recovered. Its
  precondition passed, and all 214 per-case workflows completed, including
  30 physics and 112 wave/loop/temporal cases. All eight Alfvén ladders pass
  (1.8834–1.9590); all 99 boost-pair evaluations pass. Against A, the
  largest named B/v L1 error change is 0.0660%, and the largest shock/vortex
  reference L1 change is 0.145%. CFL rejections fall from 463,020 to zero;
  accepted steps fall from 957,006 to 751,514. Summed case time is
  449,857 s versus A's 726,567 s, a shared-cluster observation rather than a
  controlled speed-up measurement. The 24 mean and 16 prescribed-dt temporal
  final snapshots are byte-identical to A. No registered outcome changes.
  The frozen verdict and summary reproduce exactly, and 642 files (execution
  receipt, run record and final snapshot for each case) verify against the
  downloaded artifact manifests. B's step fraction is not adopted.

The owner asked to validate options 1 and 2 of the speed-up review. Both run
through the unchanged registered phases, declared before execution in
[M1_FULL_VALIDATION_PLAN.md](M1_FULL_VALIDATION_PLAN.md#iterative-projection-and-trial-step-fraction-2026-11-17-before-execution):

- **A (`iter`):** the 2026-11-14 configuration without
  `--accelerated-projection`, so the same equations are solved by Jacobi-PCG.
  It is expected to reproduce 2026-11-14 to roundoff.
- **B (`step`):** A with `--trial-step-fraction 0.95`. This changes the step
  sequence.

Branch `arm2arm/m1-iterative-step-campaign`, frozen source `11d149f`,
snapshot `results/reana_submission_followup_20261117` (`f1fee181…`).

- A detached driver (`results/followup_campaign_tools_20261117/driver.py`)
  does three things:
  - waits for the shared preflight `openmhd-fu-preflight-20261117`;
  - runs each configuration through its short bounded stages, then the
    medium and mean plans and the precondition verdict, then the physics and
    waves plans and the final verdict;
  - writes `driver.log` and `state.json` next to itself.
- A and B stop independently. Plans are `results/followup_{iter,step}-{medium,mean,physics,waves}_20261117`
  (workflow prefix `openmhd-fu-…`). Verdicts are written to
  `results/followup_{iter,step}_{precondition,verdict}_20261117.json`.
- `driver/resume_b.py` restricted the existing driver to B. The completed
  A/B workflows need no restart. `driver/state_before_resume.json` preserves
  A's completed state and B's original failed precondition; `driver/state.json`
  is the final B-only state. The combined log retains both executions.
- It runs the case runner from the frozen export
  `results/followup_campaign_tools_20261117/frozen`, as plan hashes require.
- `scripts/compare_campaign_runs.py` measurements are archived for A and B
  against the 2026-11-13 plans `results/limiter_campaign_full-*_20261113`,
  and additionally for B against A. The post-hoc magnitude analysis separates
  named physical errors from ratios of roundoff-level component residuals.

A's iterative solve is the candidate's standard; B's trial fraction is
unadopted. Binary defaults are unchanged and this is not M1 acceptance.

## Independent REANA case execution (2026-11-11)

`scripts/reana_cases.py` now implements the owner's separate-workflow policy
for independent wave/mean/loop and shock/vortex cases. It shares the existing
case execution/measurement functions; all 66 workspace Rust/Cargo/toolchain
files remain unchanged. It verifies a matching preflight, reuses its binary,
submits cases concurrently and evaluates available pairs/ladders while other
cases run. A required failure saves its evidence before stopping unnecessary
siblings. Missing observations are not classified as physical failures.

The new `m1-fanout-preflight` passes all eight commands on REANA: format,
strict Clippy, 154 debug Rust tests, release build, 94 Python tests, M0 and
reference checks, and 163 release/all-target Rust tests. Six separate real
workflows then pass all case checks and three boost comparisons. All six final
CSVs exactly reproduce the corresponding pressure-reuse campaign outputs.
Submissions are concurrent; the backend staggers starts and up to three
workflow executions overlap. CPU hints are declared, but the observed CPU
quota remains unlimited; dedicated CPU reservation is not established.
[Frozen sources, receipts, logs, parity and resource evidence](../tests/reference/m1_pressure_campaign/fanout_execution/README.md).
An additional real timeout control verifies the stop path: the monitor saves
the triggering failure and automatically stops the running sibling after
54 seconds, before its 90-second cap. These are intentional execution-control
outcomes, not new physical failures. All submitted validation/control workflows
are terminal; no numerical job remains running from this increment.

Use `prepare_reana.py --minimal --compact-history` for new snapshots. The
private one-commit export reduced the Git bundle from 538.9 MB to 20.6 MB;
metadata retains the actual source parent, dirty status and exact file hashes.
Do not mistake the export fixture's revision for a development commit.

The monitor must remain running on an available client host for automatic
cancellation. It is not an always-on REANA service. No full matrix has been
restarted. New independent postprocessing verifies 12 existing snapshots:
at N64, reducing dt by 16 changes B by only 0.001–0.0015% of the analytic error;
the regular-mesh distortion beyond the fundamental converges at order 1.4423.
[Reproducible localisation and scope](../tests/reference/m1_pressure_campaign/standing_diagnosis/README.md).
Next numerical work should isolate limiting/spatial fluid–A reconstruction
with bounded controls. The cause is not yet established, and M1 remains open.

## Stopped pressure campaign and execution policy (2026-11-11)

The owner authorized stopping unnecessary long runs after the read-only check
found two required convergence failures. REANA confirms
`openmhd-m1-pressure-reuse-20261110.1`, UUID
`7a615758-c141-4903-a2ea-8da3094ddd58`, **stopped at 11:53:34 UTC** after
109,072 seconds. Do not restart this frozen workflow. Its raw remote workspace
is retained. Earlier instructions below to keep this workflow running are
historical.

The physics runner completed **30/30** cases and reports all its registered
gates passing; final independent review is still separate. The wave phase
completed **104/112** cases: all 64 Alfvén and 16 temporal cases, plus 24/32
loops. Eight N256 loop cases were interrupted. Two fixed-mesh standing-wave
base ladders fail the unchanged finest-three B L1 order target of 1.8:
**1.6590660064** on the regular mesh and **1.7704518931** at jitter .15.
Independent raw-CSV reduction verifies both failures; finest-grid amplitude
errors pass, which does not repair the failed orders. Full M1 remains open;
M0 retains its accepted scope.

The runner evaluates combined gates only after all futures finish, explaining
why expensive loops continued after the standing-wave ladders completed.
The next work is bounded diagnosis of the standing-wave error and execution
changes that evaluate complete pairs/ladders promptly. Do not infer the
numerical cause from the failed order alone or weaken the gate.

[Stopped status, immutable checkpoints and independent failure report](../tests/reference/m1_pressure_campaign/stopped_standing_wave/README.md)
are retained with checksums. The eight supporting local raw snapshots were
hash-verified again when archiving; the full raw workspace remains on REANA.

The owner's new scheduling instruction is **one separate REANA workflow per
independent test case, all ready cases submitted concurrently**, assuming no
aggregate CPU/resource constraint. It supersedes every older shared
24-core/64-GB limit below. Keep explicit per-job resources and prerequisite
checks; all new numerical execution stays on REANA. The existing monolithic
campaign runner has not yet been converted. See [the policy and implementation
boundary](REANA.md#current-execution-policy-2026-11-11).

## Active binary-reuse campaign (2026-11-10)

`openmhd-m1-pressure-reuse-20261110.1`, UUID
`7a615758-c141-4903-a2ea-8da3094ddd58`, starts **05:35:42 UTC** after all
26 inputs upload. Packet/export:
`results/reana_{submission,export}_m1_pressure_reuse_20261110`.
Snapshot SHA256
`00d823cc61e3ebfca3c79645625e528bf45f59e0a94967f532d74cd52b56390b`,
323 sources, actual parent **4f491de**, clean at freezing; private export
revision is only a fixture. All 70 Rust/Cargo input hashes match the previous
passing pressure candidate. The only implementation change is the execution
correction below; previous numerical failures and thresholds remain intact.

The same `m1-pressure-campaign` study runs full preflight, all five bounded
stages, mean, calibration and full matrices in a fresh workspace. The five
new Python regressions must pass before any evolution. At this checkpoint
all eight preflight commands pass: formatting, strict Clippy, 154 debug Rust
tests, release build, 85 Python tests, 13 M0 algebra checks, independent
reference verification and 163 release/all-target Rust tests. The scientific
campaign starts **05:47:05 UTC**. All five bounded stages pass in 1308.14 s,
including the 48-run medium stage in 1096.51 s. The 24-run mean ladder also
passes in 14.87 s. [Verified preflight archive](../tests/reference/m1_pressure_campaign/reuse_preflight/README.md).
All 471 short-stage raw artifacts were downloaded and verified; all 365
scientific files reproduce the preceding campaign exactly. The 106 changed
runtime/log files and new provenance are retained in the
[short-stage parity archive](../tests/reference/m1_pressure_campaign/reuse_short/README.md).
All 384 medium and 168 mean raw artifacts are also downloaded and verified;
their 288/120 scientific files exactly reproduce the preceding campaign.
Independent reductions pass all 24 medium and 12 mean pairs. The complete
bounded/mean total is 1023 verified raw artifacts and 773 identical scientific
files. [Verified bounded/mean archive](../tests/reference/m1_pressure_campaign/reuse_validation/README.md).

Both N128 calibration drivers start **06:09:08 UTC** and record
`prebuilt_binary_sha256=90d40a752e357ed6a459e828d8a48cba51eed13549229271583f89fb7384a426`,
matching the campaign binary. Neither calibration log contains a Cargo build.
The wave pair now completes and passes in 1896.65 s: relative B L1 .00316421,
independently reduced maximum normalized boost L1 2.74699e-14, peak process
RSS 667,435,008 bytes. All 16 raw files verify; the N64→N128 order is 1.841711,
an observation rather than the required finest-three fit.
[Verified wave-calibration archive](../tests/reference/m1_pressure_campaign/reuse_calibration/README.md).
The vortex also completes and passes in 2547.03 s: normalized mean-B drift
9.41954e-5 and limited-face divergence RMS .0257406. All 27 calibration raw
files verify; independent reductions and inspected gas/magnetic reference
figures are retained in that archive. Both real drivers reuse the verified
binary without invoking Cargo. Their peaks are 667,435,008 / 666,353,664 bytes.
The checked resource rule selects **10 workers × 2 threads**, with an 8-GB
reserve under the 64-GB cap. The full 30-case physics matrix starts
**06:51:35 UTC**. Monitor completed pairs, especially the N1024 column shock,
and stop on a verified required failure. Full wave/loop/temporal and final
review remain pending; M1 is still open.

Execution issue [#25 is closed](https://github.com/arm2arm/openmhd-rs-/issues/25#issuecomment-6761181555)
after its REANA regression and real concurrent-calibration requirements pass.
This is a scoped execution review by the implementing assistant, not M1
acceptance. The earlier archived full physics checkpoint has **22/30 completed**:
all 18 shocks and four N64 vortices. All state/diagnostic gates and all 11
independently reduced boost pairs pass. In particular, the formerly failing
N1024 column pair is **6.04941e-14**, against 1e-8.
[Immutable partial run map, reductions and retained finest pair](../tests/reference/m1_pressure_campaign/reuse_physics_checkpoint/README.md).
At that checkpoint eight N128/N256 vortices remain running/pending. Monitor with
`/tmp/monitor_reuse_physics.py` after downloading the latest physics run map;
it downloads completed final snapshots and checks all currently complete pairs.
Its `results/reana_remote_m1_pressure_reuse_20261110/physics_pair_checkpoint.json`
is a mutable monitoring report, distinct from the committed partial archive.

While the finer vortices run, the completed primary shock-reference subset
is independently verified using 50-digit decimal prefix integrals over
rectangles derived from raw face planes, without importing production
polygon clipping or error routines. All 12 regular/column cases and four
base/boost reference ladders pass; maximum L1/L2 disagreement with production
is **4.30212e-16**. The self-contained archive reproduces every observation
and retains an inspected profile/refinement figure.
[Independent primary shock-reference evidence](../tests/reference/m1_pressure_campaign/reuse_shock_reference/README.md).
All 224 per-run raw artifacts for the first 22 physics cases are downloaded
and hash verified locally. This still does not accept the incomplete full
physics stage or M1. Keep the same REANA workflow running unless a required
failure is verified; no numerical source changed during this postprocessing.
The old `openmhd-m1-pressure-campaign-20261110.1` remains stopped. Only this
new compute workflow is active, within 24 aggregate worker cores / 64 GB.

The next checkpoint has **23/30 completed**: the N128 regular rest-frame vortex
finishes in 2192.08 s and passes its state/diagnostic checks. All 235 raw files
for those 23 cases verify. An independent raw-face rectangle/interval reduction
checks the N64 base/boost and N128 base vortex reference bins and norms; maximum
L1/L2 disagreement with production is **2.77556e-17**. The N64→N128 base errors
fall from .05626/.11460/.09506/.08505 to .02247/.04761/.04098/.03426 for
rho/p/Bx/By. Both primary refinement ladders remain pending because the finest
N256 cases are absent. The self-contained archive reproduces every measurement,
and its gas/magnetic figures have been inspected.
[Independent partial vortex-reference evidence and plots](../tests/reference/m1_pressure_campaign/reuse_vortex_reference/README.md).
Seven finer vortex cases and the full wave/loop/temporal phase remain pending.
No required failure has been observed; keep the same workflow running.

The next live checkpoint reaches **24/30**: N128 regular boost completes in
2440.86 s and independently passes its pair at **1.51895e-14**. All 12 completed
pairs and 24 state/diagnostic records pass. Six finer vortex cases remain.
The committed vortex-reference archive above deliberately retains its earlier
23-record checkpoint; do not overwrite its immutable run map.

The [#21 disposition review](../tests/reference/m1_mesh_symmetry/disposition_review/README.md)
is complete: historical operator/rank archives verify, the bound/gauge/source
interpretation is reviewed and the existing owner-approved Bx amendment has
passing full primary shock evidence. This supports scoped issue closure,
not full M1 acceptance. [#21 is closed](https://github.com/arm2arm/openmhd-rs-/issues/21#issuecomment-6761865379)
at 07:42:20 UTC after that review is committed/pushed. The review is by the
implementing assistant; #20's default planar pressure failure remains visible
and unresolved.

The live physics map then reaches **25/30**: N128 planar-jitter base completes
in 3276.70 s, with normalized mean-B drift 9.41954e-5 and limited-face divergence
RMS .0257406, both passing. Its boost sibling and the four N256 vortices remain
pending. The complete wave phase has not started.

For that later phase, the [incremental independent wave monitor](../tests/reference/m1_pressure_campaign/wave_monitor/README.md)
is prepared and measured against the actual 48 medium and two calibration
snapshots. It checks analytic errors, both boost normalizations, recorded
history gates and file hashes without importing production reducers. All
25 existing pairs agree; incomplete spatial ladders remain pending. Cached
case/pair reductions recheck snapshot hashes and avoid repeated CSV work.
Full spatial/temporal branches still await the complete physical wave data.
After downloading its run map, manifest and completed final CSVs, invoke the
documented command; investigate a verified required failure and stop the same
workflow, without interpreting missing observations as execution failures.

The **complete N128 checkpoint reaches 26/30** and all 13 independently
reduced boost pairs pass. N128 jitter boost takes 3566.52 s; its pair is
1.40549e-14. All four N128 final-state reductions and all four regular N64/N128
reference cases verify. All 268 raw files and 73 phase source dependencies
verify. The two-thread N128 jittered base case reproduces all nine scientific
files from its eight-thread calibration exactly; timing/log differences are
retained. A compensated-sum postprocessing check resolves a dot-product
roundoff discrepancy without any solver or threshold change.
[Immutable complete N128 checkpoint and reproduction](../tests/reference/m1_pressure_campaign/reuse_n128_physics/README.md).
Only four N256 vortices remain in physics; full wave/loop/temporal still waits
for the entire physics gate. Keep the same live workflow running. This is
not full physics or M1 acceptance.

Download root `results/reana_remote_m1_pressure_reuse_20261110`. Monitor
`outputs/execution.json`, `outputs/logs/00.log`–`08.log` and
`source/results/reana_m1-campaign/campaign.json`. In Python test logs, the new
mocked calibration-failure test intentionally emits failed/cancelled phase
messages; distinguish that regression from the actual scientific campaign.
No gate or issue is closed until the required evidence passes. Keep the
active M0/M1 goal intact.

## Calibration execution correction (2026-11-10, issue #25)

[Issue #25](https://github.com/arm2arm/openmhd-rs-/issues/25) records the
shared-target calibration build failure below. The correction introduces
`--reuse-binary-sha256` in the wave/physics drivers. When explicitly supplied,
the existing preflight executable must exist and match that digest; Cargo
is not invoked. Standalone default builds keep the original command. The
campaign supplies the frozen binary digest to mean, both calibration drivers
and full physics/waves; provenance records the reuse choice.

Calibration futures are inspected as they finish. A failed return, missing
measurement or failed scientific check cancels the sibling process group,
including descendants. Both failed/cancelled outcomes remain in the campaign
record. The default bounded stage timeout behaviour is retained.

Five new Python regressions cover correct/missing/wrong/malformed reuse,
standalone build compatibility, campaign failure propagation/provenance and
real Linux descendant-process cancellation. At implementation time these
were unexecuted; all tests must run on REANA. Static inspection confirms unchanged Rust/Cargo
inputs and unchanged measurement/configuration/nested evolution-worker
functions. This is an orchestration correction, not a new numerical method.
The fresh campaign above subsequently passes all five new regressions as
part of its 85-test Python suite. Actual concurrent calibration remains pending.

The fresh `m1-pressure-campaign` packet above now runs the unchanged
acceptance sequence on REANA. Keep the old workflow stopped;
do not reuse an incomplete calibration as a pass or silently omit gates.

## Pressure-blend campaign checkpoint (2026-11-10)

`openmhd-m1-pressure-campaign-20261110.1`, UUID
`b04502aa-c906-4efa-9333-7f2649a28757`, started **04:39:05 UTC** after all
26 inputs uploaded. Packet/export:
`results/reana_{submission,export}_m1_pressure_campaign_20261110`.
Snapshot SHA256
`de65afe4f1920ec3a6db0535f904d48112227ce1fc57324fe604b3fbaf8b5c95`,
321 source files, actual parent `d1127f2`; private export revision is a fixture.
The only dirty file at freezing is `scripts/prepare_reana.py`, adding the new
campaign evidence directory to future minimal-export omissions. Relative to
the passing focused snapshot, only docs, the plotting script and that packaging
list differ. **Every Rust source and Cargo input is unchanged.**

The focused comparison below passes and its verified archive is committed.
This campaign runs full workspace/M0 checks, five bounded stages, the 24-run
mean ladder, N128 wave/vortex calibration, 30 full physics cases and the 112-run
wave/loop/temporal matrix. It uses explicit `hlld-pressure` throughout the
candidate; historical literal controls stay HLLD. Every phase must pass before
escalation. All thresholds, grids, times and caps remain as preregistered.
At most 24 aggregate worker cores / 64 GB; calibration determines the full
worker count from measured memory. Stop unnecessary long work at a verified
required-gate failure. No other compute workflow is active.

Monitor authoritative REANA status, `outputs/execution.json`,
`outputs/logs/00.log` through `08.log`, and
`source/results/reana_m1-campaign/campaign.json` with per-stage results.
Download root `results/reana_remote_m1_pressure_campaign_20261110`.
Final `outputs/artifacts.sha256.json` and the compact
`outputs/m1-pressure-campaign-measurements.tar.gz` appear on wrapper exit.
Do not restart or mutate the frozen packet. All eight preflight commands pass:
format, strict Clippy, 154 debug Rust tests, release build, 80 Python tests,
13 M0 algebra checks, independent reference verification and 163 release/all-target
Rust tests. [Verified preflight archive](../tests/reference/m1_pressure_campaign/preflight/README.md).
The scientific campaign starts at **04:51:22 UTC**. All four short stages
pass: 51 completed evolutions (49 candidate and two literal column controls),
with two literal planar pressure failures retained. All 471 raw artifacts
are hash verified; the [short-stage archive and plot](../tests/reference/m1_pressure_campaign/short/README.md)
include independent wave, vortex-norm, boost and final-budget reductions.
Short magnetic/velocity orders range 1.918–1.952 / 1.907–2.038. N32 vortex
diagnostics pass; N16 jittered mean-field drift .0016708 remains a failed
coarse diagnostic under the registered finest-quick-grid rule.
The 48-case N32/64 t=1 medium stage passes all 24 boost pairs, state and
budget checks in 1073.24 seconds. The complete five-stage bounded gate passes:
99 completed evolutions plus two expected literal planar failures. The
24-run mean-field ladder also passes all 12 pairs and four candidate refinement
rows, with maximum transformed component error 1.04361e-14.
[Verified medium/mean results and independent reductions](../tests/reference/m1_pressure_campaign/README.md).

**Stopped at 05:22:00 UTC:** the wave-calibration Cargo build exits 101 while
removing missing faer-traits/gemm rlibs during concurrent shared-target builds.
No calibration waves run. The vortex build succeeds with the same binary but
its evolution is interrupted by the stop. Its partial result is not accepted.
The campaign waits for both futures before checking failure, so it could not
advance and was stopped explicitly. No full physics or full wave matrix starts.
The [failure archive](../tests/reference/m1_pressure_campaign/calibration_build_failure/)
retains logs, failed memory record, partial vortex provenance and terminal status.
Running JSON checkpoints are historical, not authoritative workflow status.

Next fix hash-validated binary reuse in concurrent drivers and calibration
sibling cancellation, then test on REANA before a fresh complete campaign.
No Rust numerical change or threshold change is warranted by this build error.
M0 remains accepted; M1/#7/#19–#22/#24 remain open. No compute workflow remains
active after this stop.

## Passing focused pressure-blend comparison (2026-11-10)

`openmhd-m1-pressure-blend-20261110.2`, UUID
`976c4360-a91b-4a5c-842a-01c997ff82c5`, finished **04:31:45 UTC** after
741 seconds. Snapshot
`85cbaf2025f591ee989c59a33c4c5db5b3a212ef7fe6dd5c95feb5649760ad89`;
321 sources, actual parent `c0265ee`, private export revision is a fixture.
All 224 artifacts and 28 uploads verify. All 169 archived executable/config
files match published commit **144ac35** exactly. Format, strict Clippy,
163 release/all-target Rust tests, 80 Python tests and M0 checks pass.
All tests/evolutions ran on REANA, at most 16 worker cores / 16 GB.

All 24 evolutions finish; **all 96 historical HLLD/HLL files match**.
The eight `hlld-pressure-blend-v1` candidates and four boost pairs pass.
Column shock boost maximum L1 is **6.049405107e-14**, limit 1e-8;
regular shock is **5.619539122e-14**. Regular/jitter N32 vortex normalized
limited-face divergence maxima are **.06846058 / .07301384**, limit .1.
All positivity, budgets, mean-field, shock reference/Bx/seam checks pass.
Column base/boost vx row ranges are 1.87642e-12 / 8.42881e-13.
The original HLLD column failure and global-HLL vortex failure stay visible.
[Verified exact source/results, independent reductions and inspected plot](../tests/reference/m1_column_boost/pressure_blend/README.md).
The earlier strict-Clippy-only failure is preserved separately below.

Next run the unchanged complete sequence with `m1-pressure-campaign`:
workspace/M0 checks, five bounded stages, mean-field ladder, N128 calibration,
full 30-run physics ladder, then 112-run wave/loop/temporal matrix. Each phase
must pass before escalation. Use at most 24 aggregate cores / 64 GB, with
registered case caps and memory-based workers. Numerical source is unchanged
since the focused pass. At this checkpoint no workflow is active; the new
campaign is being prepared. Do not close M1 or claim general invariance yet.

## Pressure-blend implementation and failed preflight (2026-11-10)

The [registered pressure-weighted HLLD/HLL blend](M1_PRESSURE_BLEND_PLAN.md)
is implemented as `hlld-pressure-blend-v1`, with seven new Rust tests and two
Python tests. It blends the complete fluid/induction vector using the fixed
cubed neighbouring gas-pressure ratio; no shock-only theta correction is
combined with it. The earlier numerical paths remain separate. All numerical
tests/evolutions must run only on REANA.

First workflow `openmhd-m1-pressure-blend-20261110.1`, UUID
`e6315eaf-fc64-4a78-9d0f-2c7b84c3c33d`, ran **04:11:35–04:15:40 UTC**.
Snapshot `beda7bd90d04dfef8e004bf06030c173c18ffd75bdebb69a95a1569e35d64daa`,
321 sources, actual parent `c0265ee`. Formatting passed; strict Clippy failed
on `needless_range_loop` in the new covariance test. **No simulations ran.**
[Verified failed preflight](../tests/reference/m1_column_boost/pressure_blend_preflight/README.md).
The test-only loop is corrected using `enumerate`, without numerical changes.
A fresh v2 packet is being prepared; never restart the failed immutable packet.

The current source also prepares conditional `m1-pressure-campaign` routing
for the unchanged full sequence. It is not submitted unless all focused gates
pass. Require the 24-case shock/vortex comparison to preserve all 96 HLLD/HLL
control hashes and pass every candidate gate. Eight two-thread workers,
16 GB, 600 seconds per case. New observations use rest-frame shock windows
and `omega` metadata; the original shock-only archive remains untouched.
This failed-preflight record and the test-loop correction are retained together
with the implementation; the newer run .2 is described above.

## Completed failed shock-only HLLD trial (2026-11-10)

`openmhd-m1-shock-sensor-20261110.1`, UUID
`443effc9-4179-46ba-97d0-e27ca17e21c2`, finished **04:00:01 UTC**, 756 s.
Snapshot `2a8cadb08e98a2368ab48414a3e80ab780920f60b25bbaba0c63af33c374e969`,
315 source files, actual parent `8f48a08`; private export revision is a fixture.
All 28 inputs and 224 output artifacts verify. Format, strict Clippy,
156 release/all-target Rust tests, 78 Python tests and M0 checks pass.
All 24 focused evolutions finish; **all 96 historical HLLD/HLL files match**.
All tests/evolutions ran on REANA, at most 16 worker cores / 16 GB.

The new `hlld-shock-sensor-v1` passes both vortex diagnostics but fails the
column shock boost at **7.503948931e-6**, limit 1e-8. It is active but does not
remove the row instability. No long campaign was started. The workflow's
finished status is not scientific acceptance. [Exact source/results archive,
independent reductions and inspected plot](../tests/reference/m1_column_boost/shock_sensor/README.md).
The first remote face-window report used absolute x for boosted states;
archived independent reductions correct only that observation to rest-frame x.
No gate depends on this reporting error.

The next hypothesis is the [registered pressure-weighted HLLD/HLL blend](M1_PRESSURE_BLEND_PLAN.md).
This is an explicitly new MHD engineering extension, using the published
pressure ratio exponent three without tuning. Implement/test it separately;
require historical controls and both shock/vortex gates before escalation.
No workflow is active at this checkpoint. M0 remains accepted, M1/#24 open.

## HLL campaign failure checkpoint (2026-11-10)

`openmhd-m1-hll-campaign-20261110.1` started **03:06:16 UTC**, UUID
`f32fda39-1696-4fe2-8950-54e4ec10fd55`. Frozen packet
`results/reana_submission_m1_hll_campaign_20261110`, snapshot SHA256
`cf55c78de31a305bb06f0059e7a347cfe5c6563bcfcf64bba023b64932a067b4`;
307 source files, all 26 remote input names/sizes verified before start.
Preparation independently verifies input hashes. Actual source parent
`8d53b79`; the private export revision is a build/provenance fixture.
The Rust numerical source is unchanged from the passing HLL shock comparison.
Runner changes propagate and validate the explicit HLL choice, including four
new configuration/provenance tests. No new tests or evolutions run locally.

Preflight completes at approximately **03:19:16 UTC**: format, strict Clippy,
139 debug Rust tests, 148 release/all-target Rust tests, 76 Python tests,
13 M0 algebra tests and independent M0 reference checks pass.
[Verified preflight archive](../tests/reference/m1_hll_campaign/preflight/README.md)
retains all eight logs, the full snapshot manifest and 163 exact source/config
files; all 307 frozen source files and upload hashes verify. The first bounded
short-shock, symmetry and short-wave stages pass in 61.45 / 40.40 / 70.66
seconds. The coarse physics stage fails after 78.85 seconds: regular N32
vortex normalized limited-face divergence is .385293086709, limit .1.
All 20 physics evolutions finish with passing positivity, budgets and boost
pairs. The medium and every later phase never start. REANA ends **failed at
03:23:35 UTC** (1039 seconds). No workflow remained active at that checkpoint.
[Preserved failure, independent reduction and plot](../tests/reference/m1_hll_campaign/bounded_failure/README.md).
Two weak-field cells account for 98.35% of the squared normalized error;
dimensional divergence RMS is actually lower than HLLD. This is not permission
to change the diagnostic or claim a pass. Global HLL is not adopted.

Next implement and test the [prospective HLLD shock-sensor comparison](M1_SHOCK_SENSOR_PLAN.md).
It uses Minoshima–Miyoshi's published transverse-compression pressure-jump
correction with an explicitly documented Voronoi extension, not global HLL
or a relaxed divergence denominator. At this historical checkpoint the plan had not been implemented or executed;
see the newer failed-trial record above. Preserve existing numerical paths and require
exact historical HLLD/HLL controls plus both shock and vortex gates.

The `m1-hll-campaign` study executes workspace/M0 checks, all five bounded
stages, the 24-run mean-field ladder, N128 wave/vortex calibration, the 30-run
full physics ladder and the 112-run wave/loop/temporal matrix. Each phase must
pass before escalation. All numerical thresholds, grids, physical times and
resource/case limits remain as [registered](M1_FULL_VALIDATION_PLAN.md#explicit-hll-continuation-2026-11-10-before-campaign-execution).
At most 24 aggregate worker cores / 64 GB were permitted.

Monitor authoritative workflow status, `outputs/execution.json`,
`outputs/logs/00.log` through `08.log`, and
`source/results/reana_m1-campaign/campaign.json` with per-stage records.
Download root: `results/reana_remote_m1_hll_campaign_20261110`.
The wrapper exports compact results and an artifact hash manifest on exit;
all 13 final output artifacts now verify.
Do not mutate or restart the frozen packet. Stop unnecessary long work at a
verified required-gate failure. M0 remains accepted; M1 and #24 remain open.

## Completed HLL shock comparator (2026-11-10, #24)

`openmhd-m1-hll-shock-20261110.1` started **02:34:02 UTC**, UUID
`b689d692-63c5-40cb-9026-b338872346b2`. Frozen packet
`results/reana_submission_m1_hll_shock_20261110`, SHA256
`20c103fef9facca21884aed961dd7349997555492ebac9607f88e059daf4ff9c`;
305 source files, all 28 uploads successful. Actual parent `cac0088`.
At most eight two-thread simulations (16 worker cores), 16-GB job memory,
600-second case limits and 900-second per-command limits. The workflow finished **02:43:56 UTC** (594 s). No workflow remained active at that checkpoint.
All tests/evolutions ran on REANA.

Opt-in `--riemann hll` selects the existing two-wave formula explicitly with
separate `hll-comparator-v1` metadata and no fallback-count conflation. Default
HLLD and historical wrapper APIs retain their arithmetic. The comparison has
four original nx1024 regular/column base/boost HLLD controls requiring 24
byte-identical scientific files, plus four matching HLL trials. It measures
positivity, budgets, Bx/seam, original reference errors and 1e-8 boost gates,
with accepted-step row-mode observations. Success is not full M1 acceptance.
New algebra/covariance and derivative-symbol tests run in the full preflight.

Monitor `outputs/hll_execution.json`, `outputs/check_07.log`,
`source/results/hll_shock_probe/report.json` and authoritative workflow status.
The final `outputs/hll_artifacts.sha256.json` covers all artifacts. Download
root: `results/reana_remote_m1_hll_shock_20261110`. The wrapper's opening
"no-evolution" wording is a copied docstring typo in the immutable packet;
this study explicitly executes eight bounded shock evolutions. The working
wrapper corrects only that comment; its frozen bytes remain in the archive.

All eight complete in 131.92–172.59 s. Format, strict Clippy, 148 release/all-target
Rust tests, 72 Python tests and M0 checks pass. **All 24 HLLD control files are
byte-identical** to the original failure; the HLLD column boost still fails at
5.818394374e-6. The explicit HLL column pair passes at **9.589525564e-14**;
regular HLL passes at **6.836139727e-13**. All four HLL cases pass positivity,
conservation, Bx/seam and original finest-grid reference limits. Final column
row-to-row vx ranges are 1.27701e-12 / 7.46736e-13 (base/boost), compared with
.001680084 / .002194238 for HLLD. This is a strong bounded remedy, not full
M1 acceptance or proof that one HLLD term alone causes the instability.
Next promote the explicitly labelled HLL configuration into the unchanged
bounded wave/loop/shock/vortex suite, then calibration and full gates only
if it passes. HLL's accuracy cost must be measured. Keep the HLLD/default
profiles and failed evidence intact; do not close M1 or #24 yet.

## Uniform response checkpoint (2026-11-10, #24)

`openmhd-m1-transverse-symbol-20261110.1` finished at 02:24:18 UTC (425 s),
UUID `8e21b7ea-c053-41a6-9461-25286b170419`. Frozen packet
`results/reana_submission_m1_transverse_symbol_20261110`, snapshot SHA256
`6a70c0c542ae41773d9d49adc53460b9238119972a727df8a33cfe08335e373c`.
All 96 no-evolution uniform/unlimited probes complete; format, strict Clippy,
146 release Rust tests, 72 Python tests and M0 checks pass. All 204 artifacts
and 303 frozen source files verify. No resolved positive screened eigenmode
in the sampled states/wavelengths; this does not explain or repair the limited
nonlinear shock. The unprojected stationary short-mode control grows.
[Full data/source archive](../tests/reference/m1_column_boost/uniform_symbol/README.md).
The next bounded comparator is explicit two-wave HLL versus unchanged HLLD,
using the original four nx1024 shock cases and unchanged gates. It is not
adopted as a fix. M0 remains accepted; M1/#24 remain open.

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

### Active bounded row-mode diagnosis (2026-11-10, #24)

The original failure/reproduction packet is committed and pushed as `411d917`.
New bug [#24](https://github.com/arm2arm/openmhd-rs-/issues/24) and a parent
[#7 update](https://github.com/arm2arm/openmhd-rs-/issues/7#issuecomment-6756435422)
record the failed gate. No numerical correction has been claimed.

Two immutable diagnostic workflows were submitted and both are now finished. Their
overlap used at most 16 worker threads / 32 GB. Each has four original nx1024 regular/column
base/boost cases, two threads per case, 600-second case limits, and requires
all 24 original scientific files to remain byte-identical. Their instrumented
sources are separately hash pinned; private source-export commits are only
build/provenance fixtures, not the repository's real revision (`411d917`).

- Snapshot-only: `openmhd-m1-column-trace-20261110.1`, UUID
  `c4ad247d-9fb4-438f-8387-92bcf7edd1bc`, started **01:41:19 UTC**.
  Packet `results/reana_submission_m1_column_trace_20261110`, SHA256
  `4ecb1c27d91d6ba285b208cd47de8bd8b4ff5fb3a353073402f38c1f4a0d1308`;
  all 35 uploads succeeded. Format, strict Clippy, release/all-target workspace
  Rust tests, Python tests, M0 algebra/reference and invalid stride parsing
  pass (143 Rust / 68 Python tests). Four evolutions started at approximately
  **01:48:49 UTC** and the workflow finished **01:51:42 UTC**. All four
  complete in 135.63–165.12 seconds, and all 24 scientific-file comparisons
  match exactly. All 152 snapshot mode records are retained; four intermediate
  raw snapshots are downloaded/hash checked and their 36 coefficients independently
  reproduced with a NumPy row DFT. See the
  [trace archive](../tests/reference/m1_column_boost/accepted_trace/README.md)
  and [inspected plot](images/m1_completion/column_mode_growth.png).
- Frozen-rate decomposition: `openmhd-m1-column-rates-20261110.1`, UUID
  `658b9f65-b318-474c-a81a-71e2ef2da244`, started **01:48:39 UTC**.
  Packet `results/reana_submission_m1_column_rates_20261110`, SHA256
  `488774a9fc2f50764cdce1826ceb881bc2cc0127e194443e4b5eee3897601b9d`;
  all 35 uploads succeeded. Finished **01:59:08 UTC**. Format, strict Clippy,
  145 release/all-target Rust tests, 70 Python tests, release build and M0
  checks pass. All four evolutions complete in 143.11–174.09 seconds; all 24
  original scientific files and all 152 earlier snapshot records match exactly.
  The six current instrumentation sources match the frozen input hashes.
  [Raw rate/source archive](../tests/reference/m1_column_boost/frozen_rates/README.md).

Instrumentation adds `--snapshot-stride 64`: step 1 and each 64th accepted
step, with no new landing times. `--trace-frozen-rates` additionally samples
the immutable production RHS. It groups fluid face exchanges by normal
orientation and measures curl(projected A-rate), curl(unprojected A-rate),
and the same comoving FV-induction target as production. No evolved operator
is changed. Files are under `outputs/column_trace`; `row_modes.json` is reduced
only after each evolution completes. Monitor `outputs/trace_execution.json`,
`outputs/column_trace/report.json`, and authoritative workflow status.
Local download directories use matching `results/reana_remote_m1_column_*` names.

`scripts/plot_column_modes.py` is subsequent local postprocessing, not in
either frozen input. It verifies report/snapshot provenance before plotting.
Both plots pass visual inspection and reproduce byte for byte.
Measured column-mode envelope slopes over t=.04–.09 are approximately 260
per simulation-time unit, versus 100–103 on the regular mesh. The column mode
reaches about 1e-3 by t=.1 and tracks the right-moving slow-shock region.
Investigate the signs of the x/y fluid
contributions before changing fluxes or curl/projection. Positive instantaneous
mode growth on a nonlinear shock is not itself a linear eigenvalue or a proof
of numerical instability. A uniform-state finite-amplitude/linearized mode
probe is a possible next discriminator if the frozen shock rates are ambiguous.
Primary-source hypotheses and links are in `M1_SHOCK_INVESTIGATION.md`.

The rate decomposition finds **negative y-normal-face contributions in all
77 observations** with max |vx mode| >= 1e-10 (range -100.330 to -83.335 per
time unit). The x-normal contribution varies between about -1341 and +1233.
This does not support direct transverse-face anti-diffusion as the source.
The magnetic projected/unprojected/FV rates differ substantially and change
phase as the shock moves; their differences alone do not prove a bad term.
Four raw rate snapshots are hash verified and their acceleration mode rates
independently reduced with NumPy DFTs. Maximum relative-growth discrepancy
is .000339 for the tiny regular modes and 1.80e-8 for columns; local fluid
face-group sums differ from production by at most 1.34e-13.

**No compute job is active after this checkpoint.** Next investigate the
shock-propagation-direction fluid/magnetic feedback with bounded REANA
operator probes. A regular uniform-state Fourier response at the same
aspect ratio (dy/dx=16) can test whether the coupling has an intrinsic growing
short-wave mode before changing any Riemann or projection term. Distinguish
unlimited linear-symbol analysis from the production limited nonlinear shock;
the limiter at a uniform state is not automatically differentiable. Test
perturbation amplitude dependence and retain the unchanged shock control.
Do not insert a transverse shock detector merely from the visual row pattern,
or hide the growth by enforcing symmetry or changing the boost threshold.

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

The [coupled CT admissibility guard](M1_CT_POSITIVITY.md) now provides an
opt-in `voronoi-ct-admissible-v1` comparator. A frozen Rusanov Euler update
is positive at the old CT failure, unlike first-order HLLD. One global
convex coefficient limits fluid integrals, face fluxes and Bz together on
both SSP Heun legs; no energy reset or fixed pressure floor. All 42 short
controls complete, 17 boost pairs pass, budgets <=1.50e-14, each <=4.12s.
Nx256 jitter survives to .04; at .02 it uses 59 limited legs, theta>=.834377.
However, smaller dt drives minimum p toward zero (~dt²), and all jittered
Bx/wave-order failures remain. This is a conservative robustness guard,
not a physical fix or the Springel A method. All 16 waves stay unmodified
byte for byte. A repeat of the original CT frozen failure is also identical.
146 release Rust, 138 debug, 45 Python and 13 M0 tests pass. Preserve default
profiles, open physical gates and stopped long jobs. Next address magnetic
reconstruction/spatial accuracy, not simply more pressure limiting.

Subsequent [Athena/public-AREPO literature and source review](M1_SHOCK_INVESTIGATION.md#athena-and-arepo-source-comparison-2026-11-09)
confirms the distinction between full CT coupling, direct-B Powell evolution,
and the paper's A method. The recommended experiment was a separately
named complete fixed/rigid-mesh CT comparator, including face evolution and
cell-field recovery; the rejected face-normal-only patch was not that test.
This comparator has now been implemented and measured, with failures; see
the [bounded CT results](M1_CT_COMPARATOR.md). It is a separately named
fixed/rigid 2.5D face-flux/edge-EMF method using Mocz et al. (2014) equations
25–32 and the existing moving-face HLLD/ALE kernels. It is not a replacement
for the Springel (2026) A formalism. Thirty of 32 short runs complete; nx256
jittered base/boost fail at .01406918923 in cell 645, despite CT flux divergence
<=7.5e-13 there. That cell's frozen dp is -11.04467 as p tends to zero. The
original cell253 initial drain is removed. All jittered Bx gates and two
jittered wave-order screens still fail. Eleven complete boost pairs pass;
no new long job. Independent SVD recovery agrees within 1.45e-15; failed
retry immutability is checked. Preserve this diagnostic comparator separately;
do not promote it over the projected quadratic candidate. Further work needs
coupled positivity/reconstruction, not another divergence-only patch.
Keep the paper profiles and original gates. Optional entropy/floor safeguards in external methods
are not evidence of their activation in the published shock or authorization
to reset our energy. The original source review ran no evolutions; the CT
continuation runs 32 controls plus one frozen failure-audit repetition.

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
