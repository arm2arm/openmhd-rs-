# Handoff from ChatGPT conversation to Codex

*Prepared November 3, 2026. This is a curated, faithful project-context summary of the ChatGPT discussion, **not** a verbatim export of the ChatGPT conversation or a transferable Codex chat session.*

**Historical handoff:** subsequent local work added the [M0 source audit](PAPER_IMPLEMENTATION_SPEC.md), [kinematic pilot](KINEMATIC_2D.md) and [experimental coupled planar reference](COUPLED_2D.md). Issue #6 adds a separate [general 2.5D endpoint implementation](VECTOR_POTENTIAL_REFERENCE.md). Issue #7 now has [incremental wave/loop results](M1_WAVE_LOOP_RESULTS.md), with an explicit gauge comparator and unresolved physical gates. The [M1 implementation guide](M1_IMPLEMENTATION.md), [historical 31-case results](M1_HLL_RESULTS.md) and [failed wave diagnostics](M1_WAVE_DIAGNOSTICS.md) record subsequent completion work; the compact derivative remains experimental and M1 is open. Consult README/AGENTS for current implementation status; the planning-only descriptions below describe the original handoff.

## What the user wants

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
