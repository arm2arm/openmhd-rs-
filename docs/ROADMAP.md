# OpenMHD-RS implementation roadmap

**All time ranges are tentative, not commitments.** Milestones are gated by scientific tests, not only feature completion.

**Owner goal, 2026-11-22:** a 3D moving-mesh galaxy merger with collisionless
dark matter/stars, self-gravitating gas and a published multiphase ISM/star
formation model. [The staged goal](GALAXY_MERGER_PLAN.md) extends this roadmap
with gravity/particle, ISM and equilibrium-galaxy gates. M1, M2a static geometry and M2b static spatial operators have scoped acceptance.
The next mesh milestone is M2c prescribed motion and geometric conservation.
Collisionless gravity has its own validation sequence.

## M0 — Paper-to-code numerical specification (1–2 weeks)

- [x] Read [arXiv:2609.35989v1](https://arxiv.org/abs/2609.35989v1) in full, including appendices and all test setups; [M0 extraction and outstanding review](PAPER_IMPLEMENTATION_SPEC.md).
- [x] Extract published governing equations, gauge, smooth velocity construction, cleaning, mean field, stencils and stage sequence, with explicit unresolved details.
- [x] Record periodic boundary scope, planar/2.5D embedding and deferred nonperiodic operators.
- [x] Document/test planar geometry, signs, reconstruction conditioning and conservative-energy closure as explicit reference choices.
- [x] Finish the general predictor, auxiliary-grid, endpoint reconstruction and cleaning/timestep decisions in the [engineering profile](M0_ENGINEERING_DECISIONS.md).
- [x] Register [reference configurations and gates](M0_BENCHMARK_PACKET.md) for the future general implementation; archive independent Athena shock/vortex data with refinement uncertainty and provenance.
- [x] Complete a separate, explicitly labelled [AI scientific review](M0_AI_REVIEW.md) of the equation/stencil map, units/EOS, initial conditions, engineering choices and source discrepancies.

M0 specification/reference acceptance is complete under the user-selected AI review process (2026-11-04). Human peer review and author confirmation have not occurred. The [isolated operator audit](M0_OPERATOR_CHECKS.md) includes eight Rust source/cleaning tests and the frozen-source gauge-mode finding. The [acceptance record](M0_REVIEW.md) distinguishes these deliverables from M1 implementation and physical validation.

**Gate:** reviewed, version-controlled equation-to-code map with all nontrivial operators traceable to publication equations.

## M1 — Serial numerical reference (3–5 weeks)

**Accepted checkpoint, 2026-11-22:** the [scoped acceptance record](../tests/reference/m1_final_acceptance/acceptance.json)
adopts the named iterative quadratic-Heun/smooth-extrema/hlld-pressure candidate
for periodic fixed/rigid 2.5D only. All 214 fresh cases and 58 registered checks,
the repaired 174-method REANA metadata suite, six actual new reductions, full
collection, packaging and relocated portable execution pass. The separate
[joint output/archive review](M1_FINAL_OUTPUT_ARCHIVE_REVIEW.md) supports this
scope; the actual copied outer consistency command also returned 0. The
[handoff](CODEX_HANDOFF.md) records exact identities and limitations. Historical
failures and binary defaults remain unchanged. M2 and galaxy components are
separately gated and have no physical acceptance yet.

- [x] Issue #3: compilable Rust 2024 workspace, pinned toolchain and build/format/Clippy/numerical-test CI. Separate integrator/parallel/output crates are explicitly [deferred](ARCHITECTURE.md#delivered-bootstrap-and-deferred-crate-boundaries). See the [Mac build instructions](MAC_CODEX_SETUP.md#5-build-and-check-the-serial-workspace).
- [x] EOS, conservative/primitive conversion and rejection of invalid states; no pressure floors or energy resets.
- [x] Serial reference 2D periodic Voronoi geometry, oriented faces, areas, centroids, free-intercept LS stencils and mesh validation (small well populated meshes).
- [x] Issue #5: [checked periodic geometry and shared reconstruction](MESH_VALIDATION.md), analytic nonuniform cells, explicit invalid/ill-conditioned-state rejection, direct limiter tests and archived regular/jittered gradient convergence. Cell insertion/removal and remapping remain deferred; persistent-cell endpoint motion is covered by issue #6.
- [x] Reconstructed finite-volume planar fluid solver with moving-face HLLD and counted HLL fallback; analytic flux fixtures pass. No general positivity guarantee.
- [x] Issue #4: [conservative states and face-flux validation](CORE_FLUX_VALIDATION.md), including independent Athena++ Brio–Wu profile agreement, refinement, periodic budgets and a joint fluid/grid boost. This is a 1D conservative-induction fixture, separate from the general A/gauge integrator.
- [x] Issue #6: globally synchronized paper endpoint stages, geometry rebuilds, old-data primitive predictor and frozen cleaning C1. Deforming uniform-state errors converge at second order in the declared fixture; the longitudinal gauge mode retains documented first-order error.
- [x] Issue #6: [general 2.5D cell-centred A/gauge/cleaning, bicubic auxiliary velocity and raw discrete curl](VECTOR_POTENTIAL_REFERENCE.md), with an explicit moving-origin engineering amendment and bounded operator/coupling checks.
- [x] Registered Alfvén wave, Brio–Wu, magnetic flux loop and 2D Orszag–Tang physical acceptance for the named fixed/rigid 2.5D candidate and exact scope above. Issue #7's earlier [continuation](M1_COMPLETION_RESULTS.md) retains its original N32/64/128/256 wave ladders, N64 temporal comparisons and prescribed-flow loops: only 3/8 wave spatial gates pass for those historical profiles, and that comparator's N256 fixed-grid standing-wave boost fails. The parallel `arm2arm/M0` line (2026-11-05, merged 2026-11-18) adds its own [case set and measurement tools](M1_IMPLEMENTATION.md) and six opt-in `bulk-frame-hll-*` profiles; their irregular wave ladders also fail the order gate.

The [coupled planar reference](COUPLED_2D.md) runs Brio–Wu and early-time Orszag–Tang, with budgets, divergence and a joint rigid-translation boost comparison. It uses method-of-lines Heun rather than the paper's endpoint predictor. The separate general-component implementation adds smooth gauge/cleaning and deforming endpoint geometry. The mean-field first-step discrepancy is isolated, and the named bulk-frame comparators pass their bounded mean-field ladders. Historical profiles retain their failed spatial gates. The accepted candidate does not establish general boost invariance, a positivity theorem or full 3D equivalence. Its twelve temporal comparisons remain observations without a retrospective order gate. Scoped M1 acceptance is recorded above. The earlier continuation retains coupled-loop completion and its separate prescribed-flow evidence.

Historical continuation (2026-11-10): the screened quadratic Heun candidate with
HLLD passed bounded/mean/calibration checks but failed the full N1024 column
shock boost gate. Global HLL removed that failure but failed the N32 regular
vortex normalized-divergence gate. The new explicitly selected `hlld-pressure`
blend passes eight focused shock/vortex cases and four boost pairs, with exact
reproduction of the historical controls. Its
[full REANA acceptance campaign](M1_FULL_VALIDATION_PLAN.md) passes workspace/M0, all five bounded stages and the mean-field ladder
within 24 total cores / 64 GB. A concurrent Cargo build failure interrupts
its first calibration attempt. The corrected binary-reuse campaign passes
all preflight, bounded, mean-field and N128 calibration checks; the full
30-case shock/vortex matrix is now running with 10 workers × 2 threads.
Full physical gates and final review remain required for this choice.
[Current status and provenance](CODEX_HANDOFF.md#active-binary-reuse-campaign-2026-11-10).
Historical default-profile failures remain; this does not yet complete M1.

**Gate:** smooth convergence and measured Galilean invariance; reproducible shock/field reference agreement.

The historical [projected-limiter experiment](M1_PROJECTED_CONTROLS.md) passes both small fixed-cap standing-wave controls and the 48-run boost subset following separate AI review. Its completed finest-three irregular-wave order is **1.641**, below 1.8; that failed control is preserved alongside the separately accepted candidate. [Serial full-state restart](CHECKPOINT_RESTART.md) is implemented independently of these scientific gates; the MPI-aware restart item below remains planned.

## M2 — Full 3D moving Voronoi mesh (4–8 weeks)

**November 26, 2026. M2a is accepted for the serial static 3D geometry
reference.** All 678 workspace selections, 252 analytic mesh comparisons
and 252 irregular and difficult mesh comparisons passed. All 84 inputs gave
byte-identical outputs at one, two and four declared threads. Of 240
reproducibility pairs, 231 passed the strict comparison and nine clustered
pairs had independently certified zero-area contacts. M2b covers spatial
operators on these meshes. M2c covers evolving mesh geometry.
[Acceptance decision](../tests/reference/m2a_static_geometry/acceptance.json) ·
[M2a gate results](galaxy/M2A_FINALIZATION_STATUS.md).

**November 27, 2026. M2b is accepted for the static 3D spatial operators, revision 2.**
The 87 polynomial and rank cases, 74 auxiliary controls and 27 revised Fourier
workflows support this decision. At both refinements all 24 required irregular-mesh
divergence sequences decreased. The original O02 criterion failed and is retained
with its results. [Scoped acceptance](../tests/reference/m2b_static_operators/acceptance.json) ·
[Measured convergence](galaxy/M2B_STATIC_OPERATORS.md).

- [x] M2a. Validate the static `HalfSpaceOracle3` reference on bounded and periodic fixtures up to 512 generators.
- [ ] Benchmark accelerated geometry backends, including `meshless_voronoi`, against the static reference.
- [x] M2c S-CENTROID. Implement prescribed face speeds, cell-volume rates and actual centroid velocities. All 50 independent REANA cases passed. [Measured convergence and raw records](galaxy/M2C_CENTROID_RATES.md#measured-reana-results).
- [ ] M2c S-CDOT. Differentiate the static curl on moving geometry and test it against independently rebuilt central differences.
- [ ] Dynamic 3D tessellation and mesh point motion; ensure oriented shared-face consistency.
- [x] Implement and condition static 3D least-squares gradients and curl for irregular cells.
- [x] M2b. Qualify the static curl and independent face-divergence measurements under the preregistered revision 2.
- [x] Validate the static 3D auxiliary interpolation, deposition and curl-adjoint controls.
- [x] Recover the static field with zero and nonzero periodic imposed mean.
- [ ] Validate the evolving advective gauge and preservation of the mean field on moving cells.
- [ ] Validate moving-face fluxes and mesh topology changes.

**Gate:** 3D field advection, blast and vortex; quantitative conservation and uniform-boost tests.

## M3 — Hybrid MPI + Rayon (3–6 weeks)

- [ ] Domain partition using Morton/Hilbert ordering and stable global cell IDs.
- [ ] Exchange geometry and state halos, A and gauge scalars, local-step metadata.
- [ ] Unique shared-face flux ownership and equal/opposite updates across rank boundaries.
- [ ] Rayon parallel face/cell kernels with no data races or oversubscription.
- [ ] MPI-aware logging, simple I/O and restart, domain rebalance.
- [ ] One-rank vs multi-rank scientific equivalence and preliminary strong/weak scaling.

**Gate:** physics reproducibility within floating-point tolerance under changed MPI/thread layouts.

## M4 — Mesh adaptation and physical extensions (4–8 weeks)

- [ ] Adaptive cell insertion/removal and conservative remapping.
- [ ] A transfer and mean-field consistency during topology changes.
- [ ] Hierarchical local timesteps and deferred flux accounting.
- [ ] Optional self-gravity only after core MHD validation.
- [ ] MRI and magnetic collapse cases with necessary boundary physics.

**Gate:** adaptive and global-step comparisons show controlled error and budget consistency.

## M5 — Scientific release-quality validation (3–5 weeks)

- [ ] Archived configs, reference curves, scripts and repeatable result tables.
- [ ] Automated small CI tests and scheduled large HPC tests.
- [ ] Time breakdowns, rank/thread scaling, memory/communication accounting.
- [ ] Document deviations from the paper and explicit limitations.
- [ ] Confirm compatibility with the existing MIT license, prepare citation metadata and refine the contribution policy for a scientific release.

**Gate:** scientific claims supported by public numerical evidence.

**Priority:** Do not optimize MPI or claim exact magnetic divergence before validating the paper-specific magnetic potential scheme.
