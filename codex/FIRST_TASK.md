# First task to give Codex: M0 paper-to-code numerical specification

> Historical initial-session prompt. The repository now includes an M0 review draft and serial reference implementations; consult README and AGENTS for current status and follow the user's active task. The original prompt below records the initial scope, not a claim that the repository is still planning-only.

Copy the following prompt into a **new Codex chat** in the local `openmhd-rs-` repository, or ask Codex to execute this file as a task.

---

You are working in the public GitHub repository `arm2arm/openmhd-rs-` on my Mac Pro. Read `AGENTS.md`, `README.md`, `docs/CODEX_HANDOFF.md`, `docs/ROADMAP.md`, `docs/NUMERICS.md`, and `docs/VALIDATION.md` first.

We want to build a **new Rust 2024 + MPI + Rayon** implementation of the moving-mesh magnetic-vector-potential ideal-MHD method in Springel, Mayer & Pakmor (2026), arXiv:2609.35989. The repository is currently **planning only**.

Your **first task** is **M0 / GitHub issue #1**, *not* to generate a large unverified MHD codebase:

1. Locate and read the **full primary paper**, including appendices; record the version of the text consulted. If it is inaccessible, clearly state which details you cannot verify and do not invent paper-specific equations.
2. Derive an implementation-focused numerical specification for the fluid variables, vector potential `A`, gauge/cleaning scalar, curl reconstruction, smooth auxiliary velocity, moving-face fluxes, periodic mean magnetic field and all time-integration stages. Cite paper equation numbers and pages for each nontrivial term and distinguish *paper-specified* from *our engineering choice*.
3. Identify the exact discretization and ordering dependencies, especially where the new solver differs from generic induction-equation MHD and common constrained transport/cleaning methods.
4. Write `docs/PAPER_IMPLEMENTATION_SPEC.md` with pseudocode and an equation-to-code mapping. Propose Rust traits/data types and separate physics kernels from mesh, I/O and parallel implementation.
5. Extend or correct `docs/VALIDATION.md` only where full-text evidence supports it; identify analytical initial conditions and predeclared acceptance metrics for the first 2D test suite.
6. If a mismatch with existing planning docs is detected, explain it and propose a correction rather than silently perpetuating a wrong assumption.
7. Perform applicable documentation checks and report what was actually verified. Do not claim numerical tests pass or `cargo` builds before code exists.

Output a clear scientific review: verified equations, unknowns, risks, files changed, suggested first compilable Rust milestone, and test strategy. Keep changes narrow and reviewable. **Do not implement the full solver, MPI domain decomposition or 3D moving Voronoi mesh in this first task.**

After finishing, I will review the M0 specification before proceeding to issue #3 (Cargo workspace) and issues #4–#7 (M1 serial baseline).

---
