# OpenMHD-RS — instructions for Codex and other coding agents

This is a **scientific numerical-methods project**. Read `README.md`, `docs/CODEX_HANDOFF.md`, `docs/ROADMAP.md`, `docs/NUMERICS.md` and `docs/VALIDATION.md` before changing code.

## Project mission
Independently implement and validate the vector-potential moving-Voronoi-mesh **ideal-MHD method** described by Springel, Mayer & Pakmor (2026), [arXiv:2609.35989](https://arxiv.org/abs/2609.35989), in **Rust 2024 + MPI + Rayon**. This is not an AREPO fork or a claim of paper-level numerical equivalence.

## Current state and priority
- 2026-11-22 (scoped acceptance): the named iterative `bulk-frame-heun-quadratic-v1 --projection-screening 1 --riemann hlld-pressure --potential-limiter smooth-extrema` candidate is accepted for the registered periodic, single-process fixed/rigid 2.5D reference. See `tests/reference/m1_final_acceptance/acceptance.json` and `docs/M1_FINAL_OUTPUT_ARCHIVE_REVIEW.md`: all 214 fresh cases, 58 checks, repaired 174-method REANA metadata suite, actual collection/six reductions/package/relocated verifier, independent final joint review and actual copied outer consistency command pass. Defaults and historical failures below remain unchanged. Proceed to independently gated static 3D geometry and direct gravity; full deforming 3D, MPI, gravity/ISM and the galaxy merger remain unaccepted. The dated entries below are historical checkpoints.
- The repository contains kinematic/planar pilots, the **general 2.5D endpoint reference** (`docs/VECTOR_POTENTIAL_REFERENCE.md`) and issue #7 continuation evidence (`docs/M1_COMPLETION_RESULTS.md`). The historical default retains its mean-field boost discrepancy. Named comparators pass bounded mean-field tests, but the new N256 standing-wave boost case and five of eight spatial gates still fail. Do not claim full M1 physical validation, 3D equivalence or general Galilean invariance.
- 2026-11-14 (#26): the opt-in configuration, then with the cached solve, `bulk-frame-heun-quadratic-v1 --accelerated-projection --projection-screening 1 --riemann hlld-pressure --potential-limiter smooth-extrema` passes every registered M1 phase check on REANA; see `docs/CODEX_HANDOFF.md`. It is unreviewed and not adopted, its limiter admits curvature-confirmed extrema, and defaults are unchanged. This is not M1 acceptance.
- 2026-11-18/19 (#26): the iterative projection (campaign A, without `--accelerated-projection`) passes every registered phase check and reproduces 2026-11-14 to the projection solve's 1e-11 tolerance (largest named differences 1.6e-9 and 1.8e-9; no gate outcome changes). Campaign B (`--trial-step-fraction 0.95`) resumed after a failed download and finished on 2026-11-19 with all seven phase checks passing; its archive/comparison was completed on 2026-11-21. B's largest named reference-error change versus A is 0.145%; its step fraction is not adopted. See `tests/reference/m1_iterative_step_campaigns/`.
- 2026-11-19 (owner decision): the M1 validation candidate is `bulk-frame-heun-quadratic-v1 --projection-screening 1 --riemann hlld-pressure --potential-limiter smooth-extrema` with the iterative projection (no `--accelerated-projection`). Run its registered campaigns with the `iter-*` plans and `--iterative-projection`; see `docs/M1_FULL_VALIDATION_PLAN.md#configuration-under-test`. The cached solve stays available; binary defaults are unchanged. The candidate is still unreviewed and fixed/rigid-mesh only, and this is not M1 acceptance.
- 2026-11-21 (continuation): owner delegated decisions to finish M1. Retain campaign A, including its measured smooth-extrema tradeoff and trial fraction 1; B's .95 fraction stays optional. The separate `docs/M1_FINAL_AI_REVIEW.md` conditionally approves frozen source `2bdcea0` and historical evidence. Fresh integrated-source preflight passes; its physical campaign and final output review remain pending. See `docs/M1_FINAL_ACCEPTANCE_PLAN.md`; this is not M1 acceptance.
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
- Owner execution policy (2026-11-11): run all new tests/evolutions on REANA. Give each independent benchmark case its own workflow and submit ready cases concurrently. Treat aggregate CPU time/resources as unconstrained for scheduling; the historical shared 24-core/64-GB cap no longer applies. Declare CPU threads and memory per job, avoid nested oversubscription, and preserve required preflight/build dependencies. Do not launch long validation while a required gate is known to fail. See `docs/REANA.md` for the policy and legacy-runner limitation.
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
