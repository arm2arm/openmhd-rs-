# OpenMHD-RS implementation roadmap

**All time ranges are tentative, not commitments.** Milestones are gated by scientific tests, not only feature completion.

## M0 — Paper-to-code numerical specification (1–2 weeks)

- [ ] Read [arXiv:2609.35989](https://arxiv.org/abs/2609.35989) in full, including appendices and all test setups.
- [ ] Extract governing equations, vector-potential gauge, smooth velocity field, cleaning, mean-field correction, finite-difference stencils and stage sequencing.
- [ ] Clarify 2D embedding of the 3D vector potential and all boundary conditions.
- [ ] Specify mesh geometry operators, sign conventions, reconstruction conditioning and magnetic/total-energy synchronization.
- [ ] Select reference initial conditions, resolution sequences, tolerances and diagnostics **before** observing implementation results.
- [ ] Agree on numerical units, equation of state, precision and initial target problems.

**Gate:** reviewed, version-controlled equation-to-code map with all nontrivial operators traceable to publication equations.

## M1 — Serial numerical reference (3–5 weeks)

- [ ] Rust/Cargo workspace and CI (`fmt`, `clippy`, tests).
- [ ] EOS, conservative/primitive conversion and robust positivity checks.
- [ ] 2D periodic Voronoi geometry, oriented faces, volumes, centroids and mesh validation.
- [ ] Reconstructed finite-volume fluid solver with face-frame HLLD and robust fallbacks.
- [ ] Second-order globally synchronized integration; correct geometry rebuild/stage order.
- [ ] Implement cell-centred A, its exact paper gauge, cleaning, smoothed auxiliary velocity and discrete curl.
- [ ] Alfvén wave, Brio–Wu, magnetic flux loop and 2D Orszag–Tang benchmarks with diagnostics.

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
- [ ] Choose software license, citation metadata and contribution policy for a licensed release.

**Gate:** scientific claims supported by public numerical evidence.

**Priority:** Do not optimize MPI or claim exact magnetic divergence before validating the paper-specific magnetic potential scheme.
