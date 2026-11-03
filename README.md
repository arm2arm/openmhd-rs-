# OpenMHD-RS

**Status: planning only — no solver implementation or validated numerical results yet.**

OpenMHD-RS is a proposed **publicly developed, MIT-licensed Rust research project** designed to independently implement and validate the moving-mesh vector-potential ideal-MHD method described by:

> V. Springel, A. C. Mayer & R. Pakmor (2026), *Divergence-free magnetohydrodynamics on a moving mesh*, [arXiv:2609.35989](https://arxiv.org/abs/2609.35989).

**This is not AREPO, a port of AREPO, or a claim that the paper's results have already been reproduced.** The physics implementation must be independently developed and quantitatively verified.

## Goals

1. Solve compressible ideal magnetohydrodynamics using conservative finite-volume fluxes on a moving, unstructured Voronoi mesh.
2. Evolve a **cell-centred magnetic vector potential**, using the paper's actual gauge, discretization, smoothing and stabilization, and reconstruct the physical field via a discrete curl (with mean-field handling where necessary).
3. Verify **Galilean invariance**, stability and magnetic-divergence diagnostics against analytical and published benchmarks.
4. Extend from a serial 2D reference to 3D adaptive moving meshes, local timesteps and optional self-gravity.
5. Support **MPI + Rayon** hybrid parallelism and reproducible Slurm/HPC scaling runs.

The paper uses finite differences for the magnetic vector potential and a finite-volume representation for the fluid variables. An arbitrary discrete divergence of an arbitrary reconstructed curl is **not** guaranteed to be zero to machine precision; the precise operators and their measured errors must be documented.

## Proposed stack

- **Rust 2024**, double precision (`f64`), Cargo workspaces, documented numerical invariants.
- **MPI** via `mpi` / rsmpi for decomposition and halo exchange.
- **Rayon** for thread-parallel cell/face computations instead of OpenMP.
- Evaluate Voronoi implementations, including `meshless_voronoi`, but verify moving topology, periodic boundaries, degeneracies and distributed compatibility.
- **HDF5** for snapshots/checkpoints; establish MPI-enabled I/O only after checking library/build support.
- **Slurm** for reproducible multi-node experiments.

## Milestones

| Stage | Deliverable | Acceptance gate |
| --- | --- | --- |
| **M0 — Specification** | Equation-by-equation reference design from the 2026 paper | Reviewed numerical specification and reproducible tests |
| **M1 — 2D reference** | Conservative MHD + paper-faithful vector potential | Smooth-wave convergence, shock tests and field-loop boost |
| **M2 — 3D moving mesh** | Dynamic Voronoi geometry and stabilized vector-potential evolution | 3D field advection, vortex/blast, conservation and Galilean tests |
| **M3 — MPI/Rayon** | Owned/ghost cells, halo exchange, race-free kernels | Multi-rank equivalence and scaling |
| **M4 — Adaptive physics** | Refinement/derefinement, local timesteps, optional gravity | Adaptive vs. global-timestep comparisons |
| **M5 — Scientific release** | Reproducible benchmark suite and HPC performance report | Published diagnostics, provenance and limitations |

## Planning documents

- [Detailed roadmap](docs/ROADMAP.md)
- [Numerical-method specification](docs/NUMERICS.md)
- [Code architecture](docs/ARCHITECTURE.md)
- [Scientific validation](docs/VALIDATION.md)
- [MPI/Rayon and Slurm design](docs/PARALLEL_HPC.md)
- [Prepared development issues](docs/ISSUE_BACKLOG.md)
- [Architecture decisions](docs/DECISIONS.md)
- [References](docs/REFERENCES.md)
- [Contributing](CONTRIBUTING.md)

## Proposed workspace (not yet implemented)

```text
crates/
  mhd-core/           # states, EOS, face flux
  mhd-vector-pot/     # A evolution, curl, gauge and cleaning
  moving-mesh/        # Voronoi geometry, moving faces, reconstruction
  time-integrator/    # RK stages, local timesteps
  parallel/           # MPI ownership, halos, Rayon kernels
  output/             # I/O, checkpoints and diagnostics
apps/
  openmhd/            # CLI driver
```

## Scientific standard

No scientific claim is accepted simply because a simulation finishes: every milestone must report convergence, conservation, magnetic-divergence diagnostics, Galilean-boost comparison and numerical provenance. In particular, do **not** advertise `∇·B = 0` to machine precision under arbitrary discrete operators.

## Visibility and license

The repository is **public** and already includes an [MIT License](LICENSE) chosen at repository initialization. The license applies to this repository's materials; verify compatibility before incorporating third-party code. The scientific solver itself remains **planning-only**, not a validated release.

## Primary reference

Springel, Mayer & Pakmor (2026), [arXiv:2609.35989](https://arxiv.org/abs/2609.35989). The precise numerical gauge, vector-potential update and cleaning algorithm are **to be extracted from the full paper in M0**, not guessed from its abstract.

## Continue in Codex on macOS

- [Codex agent instructions](AGENTS.md) — persistent project conventions.
- [ChatGPT-to-Codex context handoff](docs/CODEX_HANDOFF.md) — discussion decisions, technical scope and current status.
- [Mac Pro Codex setup](docs/MAC_CODEX_SETUP.md) — clone the GitHub repository and open it as a local Codex project.
- [First Codex task](codex/FIRST_TASK.md) — review the primary paper and complete scientific M0 before implementing code.

The local Codex project is established by cloning this repository and opening the local directory in Codex. The original ChatGPT conversation is **not automatically transferred** as a Codex chat history.
