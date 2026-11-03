# OpenMHD-RS development issue backlog

Use the [GitHub Issues tab](../../issues) to track tasks. This file is a version-controlled map of milestone dependencies and proposed acceptance criteria.

## M0: numerical specification

1. **[M0] Extract exact vector-potential algorithm from arXiv:2609.35989**
   - Document gauge, A evolution, smooth velocity, cleaning, mean field, discrete curl, exact RK stages with page/equation references.
   - Done: implementation-ready, reviewed equation-to-code traceability matrix.
2. **[M0] Define benchmark reference data and acceptance thresholds**
   - Define reference cases, resolutions, norms, conservation/error budgets and Galilean boosts.
   - Done: reproducible, preregistered acceptance conditions.

## M1: serial baseline

3. **[M1] Bootstrap Rust workspace and CI**
   - Create Cargo workspace, toolchain configuration, fmt/clippy/test workflow and a real tested utility.
   - Done: CI executes reproducible tests.
4. **[M1] Implement conservative ideal-MHD states and face flux**
   - EOS, primitives/conserved, face-frame HLLD, positivity guards and robust fallback.
   - Done: standard Riemann fixtures match references.
5. **[M1] Implement 2D Voronoi geometry and reconstruction**
   - Cell/face geometry, periodicity, orientation, gradients and degeneracy checks.
   - Done: geometric identities and convergence pass.
6. **[M1] Implement vector-potential update and diagnostics**
   - Paper-faithful A update, gauge/cleaning, discrete curl and independent div(B) diagnostics.
   - Done: analytic potential tests and gauge stability pass.
7. **[M1] Run Alfvén-wave and field-loop benchmarks**
   - Quantify convergence and bulk-velocity invariance.
   - Done: scripts generate checked-in error tables and plots.

## M2: 3D moving mesh

8. **[M2] Evaluate and implement dynamic 3D Voronoi mesh**
   - Compare candidate libraries and implement periodic moving geometry.
   - Done: 3D topology-change and geometry regressions pass.
9. **[M2] Match 3D published MHD benchmarks**
   - 3D Orszag–Tang, blast and magnetic field advection.
   - Done: quantitative paper/reference comparison.

## M3: hybrid HPC

10. **[M3] Implement MPI ownership and halo exchange**
    - Space-filling decomposition, global IDs, geometry/state/A/gauge ghost updates.
    - Done: boundary consistency and MPI-rank invariance.
11. **[M3] Implement race-free Rayon parallel kernels**
    - Independent face flux buffering and reductions, parallel gradients and cleaning.
    - Done: 1-thread vs N-thread physical diagnostics agree.
12. **[M3] Establish Slurm strong/weak scaling campaign**
    - Profile geometry/physics/communication and record environment.
    - Done: automated scaling figures with scientific correctness checks.

## M4/M5: advanced features and release

13. **[M4] Implement cell refinement/derefinement and A transfer**
    - Conservative remapping and stable potential reconstruction.
    - Done: adaptive regressions and conservative budgets.
14. **[M4] Implement hierarchical local timesteps**
    - Timestep scheduler, deferred flux and stage/mesh consistency.
    - Done: agreement with global-step reference.
15. **[M4] Implement optional self-gravity and collapse benchmark**
    - Add optional gravity, then reference collapse test with assumptions recorded.
    - Done: reproducible comparison.
16. **[M5] Publish scientific validation and architecture release report**
    - Archive configs, reference metrics, numerical limitations and HPC performance.
    - Done: tagged, reproducible scientific artifact.

## Administrative work before a licensed software release

- Review compatibility of the existing MIT `LICENSE` with dependencies and any imported code.
- Define contribution/review policy and acknowledge source-code dependencies.
- Add CITATION.cff and release metadata when code/reproducible results exist.
