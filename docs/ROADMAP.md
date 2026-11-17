# OpenMHD-RS implementation roadmap

**All time ranges are tentative, not commitments.** Milestones are gated by scientific tests, not only feature completion.

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

- [x] Issue #3: compilable Rust 2024 workspace, pinned toolchain and build/format/Clippy/numerical-test CI. Separate integrator/parallel/output crates are explicitly [deferred](ARCHITECTURE.md#delivered-bootstrap-and-deferred-crate-boundaries). See the [Mac build instructions](MAC_CODEX_SETUP.md#5-build-and-check-the-serial-workspace).
- [x] EOS, conservative/primitive conversion and rejection of invalid states; no pressure floors or energy resets.
- [x] Serial reference 2D periodic Voronoi geometry, oriented faces, areas, centroids, free-intercept LS stencils and mesh validation (small well populated meshes).
- [x] Issue #5: [checked periodic geometry and shared reconstruction](MESH_VALIDATION.md), analytic nonuniform cells, explicit invalid/ill-conditioned-state rejection, direct limiter tests and archived regular/jittered gradient convergence. Cell insertion/removal and remapping remain deferred; persistent-cell endpoint motion is covered by issue #6.
- [x] Reconstructed finite-volume planar fluid solver with moving-face HLLD and counted HLL fallback; analytic flux fixtures pass. No general positivity guarantee.
- [x] Issue #4: [conservative states and face-flux validation](CORE_FLUX_VALIDATION.md), including independent Athena++ Brio–Wu profile agreement, refinement, periodic budgets and a joint fluid/grid boost. This is a 1D conservative-induction fixture, separate from the general A/gauge integrator.
- [x] Issue #6: globally synchronized paper endpoint stages, geometry rebuilds, old-data primitive predictor and frozen cleaning C1. Deforming uniform-state errors converge at second order in the declared fixture; the longitudinal gauge mode retains documented first-order error.
- [x] Issue #6: [general 2.5D cell-centred A/gauge/cleaning, bicubic auxiliary velocity and raw discrete curl](VECTOR_POTENTIAL_REFERENCE.md), with an explicit moving-origin engineering amendment and bounded operator/coupling checks.
- [ ] Alfvén wave, Brio–Wu, magnetic flux loop and 2D Orszag–Tang physical acceptance. Issue #7's [continuation](M1_COMPLETION_RESULTS.md) measures the full N32/64/128/256 wave ladders, N64 temporal comparisons and prescribed-flow loops. Only 3/8 wave spatial gates pass per profile, and the new comparator's N256 fixed-grid standing-wave boost still fails. Execution and scientific acceptance remain separate.

The [coupled planar reference](COUPLED_2D.md) runs Brio–Wu and early-time Orszag–Tang, with budgets, divergence and a joint rigid-translation boost comparison. It uses method-of-lines Heun rather than the paper's endpoint predictor. The separate general-component implementation adds smooth gauge/cleaning and deforming endpoint geometry. The mean-field first-step discrepancy is isolated, and the named bulk-frame comparators pass their bounded mean-field ladders. Wave spatial gates still fail; second-order physical time accuracy, general boost invariance and published-profile vortex/shock agreement are not established. M1 has not passed its full gate. The continuation reports coupled-loop completion and its separate prescribed-flow evidence.

Current continuation (2026-11-10): the screened quadratic Heun candidate with
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

## M2 — Full 3D moving Voronoi mesh (4–8 weeks)

- [ ] Benchmark candidate geometry crates (including `meshless_voronoi`); evaluate periodicity, topology changes and numerical degeneracies.
- [ ] Dynamic 3D tessellation and mesh point motion; ensure oriented shared-face consistency.
- [ ] Implement and condition least-squares gradients and curl for irregular cells.
- [ ] Reproduce smooth auxiliary velocity and advective gauge in 3D.
- [ ] Consistent nonzero periodic background field.
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
