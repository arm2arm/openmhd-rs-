# OpenMHD-RS — instructions for Codex and other coding agents

This is a **scientific numerical-methods project**. Read `README.md`, `docs/CODEX_HANDOFF.md`, `docs/ROADMAP.md`, `docs/NUMERICS.md` and `docs/VALIDATION.md` before changing code.

## Project mission
Independently implement and validate the vector-potential moving-Voronoi-mesh **ideal-MHD method** described by Springel, Mayer & Pakmor (2026), [arXiv:2609.35989](https://arxiv.org/abs/2609.35989), in **Rust 2024 + MPI + Rayon**. This is not an AREPO fork or a claim of paper-level numerical equivalence.

## Current state and priority
- The repository contains kinematic/planar pilots and the **general 2.5D endpoint reference** (`docs/VECTOR_POTENTIAL_REFERENCE.md`), with bounded operator/coupling tests. Nonuniform mean-field boost discrepancies remain unresolved. Do not claim full M1 physical validation, 3D equivalence or general Galilean invariance.
- M0 (#1/#2) is accepted under the labelled AI review process. Preserve its source map and historical v1 profile; v2's persistent auxiliary origin is an explicit engineering amendment. Follow the user's current issue; full physical validation and the nonuniform mean-field boost investigation belong to #7.
- Do not infer paper-specific algorithms, parameter values or successful results from high-level summaries. If full-text access is unavailable, explicitly flag unresolved equations and request the source PDF rather than making them up.
- Use `codex/FIRST_TASK.md` for the initial working prompt.

## Implementation practices
- Rust 2024 edition; `f64` for scientific states; modular Cargo workspace.
- MPI (rsmpi) for distributed ranks; Rayon for CPU parallelism. Avoid oversubscribing worker threads with any internally parallelized FFI dependencies.
- Start with a serial 2D reference implementation and globally synchronized timesteps. Extend to 3D moving Voronoi meshes, MPI/Rayon and local timesteps **only after validation gates pass**.
- Keep conservative finite-volume fluid updates and vector-potential magnetic evolution mathematically consistent.
- Every shared face must contribute equal-and-opposite conservative updates. Geometry changes must validate face orientation, volume and periodic boundaries.
- Report the exact discrete divergence operators used. `B = curl(A)` in the continuum does **not** imply machine-zero divergence for every independent numerical operator on an unstructured mesh.
- Record physical units, EOS, precision, mesh/stencil definitions and boundary conditions.

## Tests and evidence
- Every numerical change should include unit tests and, where appropriate, convergence data plus conservation, Galilean-invariance and independent magnetic-divergence diagnostics.
- Prefer small deterministic tests in CI; reserve large 3D/HPC simulations for Slurm.
- Once the workspace exists, run `cargo fmt --check`, `cargo clippy --all-targets --all-features` and `cargo test --workspace` when applicable, and report actual results. Do not imply these commands work before project scaffolding exists.
- Maintain configuration/provenance for each benchmark; no claim of AREPO-equivalent results without quantified validation.
- Prefer small reviewable commits and meaningful issue references. Check current Git status before editing; do not discard user modifications or force-push.

## Useful context
- Conversation handoff: `docs/CODEX_HANDOFF.md`
- Roadmap: `docs/ROADMAP.md`
- Numerical specification (draft): `docs/NUMERICS.md`
- Validation: `docs/VALIDATION.md`
- HPC: `docs/PARALLEL_HPC.md`
- Mac setup: `docs/MAC_CODEX_SETUP.md`
- Backlog: `docs/ISSUE_BACKLOG.md` and GitHub issues #1–#17
- License: MIT; verify license compatibility before importing outside code.

When a user starts the first session with no narrower request, **summarize your understanding and the M0 plan**, then tackle GitHub issue #1 and present which equations/stencils have and have not been verified. Do not start a full 3D solver based on an unverified method.
