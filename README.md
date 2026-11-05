# OpenMHD-RS

**Status: serial 2.5D vector-potential implementation with operator/coupling tests, alongside the planar and kinematic pilots. The full M1 physical benchmark matrix and 3D paper method are not validated.**

M0's specification and initial benchmark packet are accepted following a separate, explicitly labelled [AI scientific review](docs/M0_AI_REVIEW.md). See the [acceptance boundary and M1 work remaining](docs/M0_REVIEW.md).

OpenMHD-RS is a proposed **publicly developed, MIT-licensed Rust research project** designed to independently implement and validate the moving-mesh vector-potential ideal-MHD method described by:

> V. Springel, A. C. Mayer & R. Pakmor (2026), *Divergence-free magnetohydrodynamics on a moving mesh*, [arXiv:2609.35989](https://arxiv.org/abs/2609.35989).

**This is not AREPO, a port of AREPO, or a claim that the paper's results have already been reproduced.** The physics implementation must be independently developed and quantitatively verified.

## Run the general-component 2.5D reference

Issue #6 adds three-component A/v/B on periodic 2D Voronoi geometry, smooth auxiliary velocity, gauge/cleaning, the old-data endpoint predictor, and fixed/rigid/deforming mesh motion. The explicit [paper-global-v2 contract](docs/VECTOR_POTENTIAL_REFERENCE.md) records the moving auxiliary-origin amendment and all test gates.

```sh
cargo run --release --locked -p openmhd --bin vector-potential -- --case smooth --n 8 --time 0.02 --output results/smooth
cargo run --release --locked -p openmhd --bin vector-potential -- --case deform --n 6 --motion prescribed --dt 0.002 --time 0.04 --output results/deform
python3 scripts/run_vector_potential.py
```

The driver writes initial/final cell CSVs and JSON diagnostics. The study checks curl convergence, uniform mean fields, gauge damping, mean-zero boosts and deforming-mesh convergence. **Nonuniform flows with nonzero mean B show a boost discrepancy in additional review probes; general Galilean invariance is not established.** See the [illustrated results, plot reproduction commands and AI review](docs/VECTOR_POTENTIAL_RESULTS.md). Full Alfvén/loop/shock/vortex validation remains issue #7.

See [moving Voronoi cells and hypothetical particles](docs/MESH_MOTION_VISUALIZATION.md) for an animation, time-sequence plots and reproduction commands showing mesh translation and deformation during integration.

## M1 physical cases (issue #7)

The [M1 implementation guide](docs/M1_IMPLEMENTATION.md) adds the full Brio–Wu and Orszag–Tang cases, prescribed-flow Voronoi loop transport, exact overlap measurements and reusable mesh caches. The explicit `bulk-frame-hll-v1` face completion resolves the previously failing N64 standing-wave boost fixture; full M1 acceptance still depends on the complete registered physical packet and separate AI review.

The [historical HLL completion study](docs/M1_HLL_RESULTS.md) now includes all 31 prescribed-loop/shock/vortex runs and six reproducible figures. Those gates pass, but the irregular Alfvén ladder fails the required order (1.18 versus 1.8), so that profile does not close M1. The separately registered matched-derivative candidate is undergoing its full validation matrix.

The [earlier illustrated results](docs/M1_WAVE_LOOP_RESULTS.md) cover 144 evolutions: mean-field boost refinement and N32/64 Alfvén/loop subsets. The separately named `bulk-frame-v1` gauge passes its mean-field ladder and improves Alfvén boost comparisons from 7/16 to 15/16 passing pairs. **That historical profile still fails one regular standing-wave boost case; its archived result remains unchanged.** The original `paper-global-v2` stays the default and its failures remain archived.

```sh
cargo run --release --locked -p openmhd --bin vector-potential -- --case alfven --profile bulk-frame-v1 --n 32 --jitter 0.15 --time 1 --checkpoint 0.25 --output results/alfven_example
python3 scripts/run_m1_wave_loop.py --quick --jobs 4 --output-dir results/m1_wave_loop_quick
```

The study records component/vector errors, energy histories, three divergence operators, positive states, conservative budgets and failed/unexecuted gates. See the [separate AI review](docs/M1_WAVE_LOOP_AI_REVIEW.md) and the [unresolved degenerate-face observation](docs/DEGENERATE_FACE_FOLLOWUP.md).

## Run the coupled 2D cases

The [coupled planar reference](docs/COUPLED_2D.md) implements ideal-gas states, HLLD/HLL face fluxes, periodic 2D Voronoi cells, cell-centred Az and magnetic force feedback. Geometry can be fixed or translate rigidly. Its Az-only method-of-lines integrator is separate from the general-component endpoint implementation above.

```sh
cargo run --release -p openmhd -- --case orszag-tang --nx 24 --time 0.1 --output vortex.csv
cargo run --release -p openmhd -- --case brio-wu --nx 128 --time 0.1 --output shock.csv
python3 scripts/run_coupled_2d.py
```

The study writes snapshots, quantitative comparisons and provenance under `results/coupled_2d/`. Small measured results are archived in [tests/reference/coupled_2d](tests/reference/coupled_2d). Brio–Wu uses a doubled periodic domain and a separate 1D conservative-induction comparison. The vortex runs are early-time stability checks, not published-profile agreement. See [scope, methods and measured limitations](docs/COUPLED_2D.md).

See the [illustrated Mac run guide and test results](docs/COUPLED_2D_RESULTS.md) for the shock profiles, vortex density maps, exact commands and plot regeneration steps.

Issue #4's conservative state/face-flux kernels also pass an [independent Athena++ Brio–Wu comparison](docs/CORE_FLUX_VALIDATION.md), with refinement, positivity, periodic conservation and joint fluid/grid boost checks. Reproduce it with `python3 scripts/run_core_flux_validation.py`. This separate 1D conservative-induction fixture does not validate the general vector-potential integrator.

Issue #5's [periodic 2D geometry and reconstruction packet](docs/MESH_VALIDATION.md) adds checked connectivity/centroid identities, a shared limiter, analytic geometry fixtures and measured regular/jittered gradient convergence. Run `python3 scripts/run_mesh_validation.py` to reproduce the study.

## Run the kinematic 2D pilot

The [Cartesian kinematic pilot](docs/KINEMATIC_2D.md) separately transports a magnetic field loop with prescribed velocity and reconstructs B from Az. It includes fixed/comoving grids, a smooth convergence case, two divergence diagnostics and CSV output.

With the Rust toolchain installed (`source "$HOME/.cargo/env"` if needed):

```sh
cargo run --release -p field-loop -- --case loop --n 64 --mesh fixed
cargo run --release -p field-loop -- --case loop --n 64 --mesh comoving
python3 scripts/run_kinematic_2d.py
```

The last command runs the resolution study and writes diagnostics, cell snapshots and provenance under `results/kinematic_2d/`. See the [numerical setup and measured results](docs/KINEMATIC_2D.md) for scope, checks and optional plots.

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
- [M0 paper extraction and equation map](docs/PAPER_IMPLEMENTATION_SPEC.md)
- [M0 completion checklist and remaining decisions](docs/M0_REVIEW.md)
- [M0 engineering profile](docs/M0_ENGINEERING_DECISIONS.md)
- [M0 benchmark packet and independent references](docs/M0_BENCHMARK_PACKET.md)
- [Independent AI review and scope](docs/M0_AI_REVIEW.md)
- [Isolated gauge/cleaning kernels and temporal-order audit](docs/M0_OPERATOR_CHECKS.md)
- [Code architecture](docs/ARCHITECTURE.md)
- [Scientific validation](docs/VALIDATION.md)
- [MPI/Rayon and Slurm design](docs/PARALLEL_HPC.md)
- [Prepared development issues](docs/ISSUE_BACKLOG.md)
- [Architecture decisions](docs/DECISIONS.md)
- [References](docs/REFERENCES.md)
- [Contributing](CONTRIBUTING.md)

## Workspace direction

The Cargo workspace contains three reference drivers and four serial crates. The general-component integrator lives in `mhd-vector-pot`; separate parallel, shared time-integrator and checkpoint/output modules remain planned.

```text
crates/
  mhd-core/           # implemented states, EOS, HLLD/HLL face flux
  mhd-vector-pot/     # kinematic pilot, source audit and general 2.5D endpoint solver
  moving-mesh/        # implemented periodic 2D clipping and LS stencils
  mhd-planar/         # experimental coupled planar solver, rigid translation
  time-integrator/    # RK stages, local timesteps
  parallel/           # MPI ownership, halos, Rayon kernels
  output/             # I/O, checkpoints and diagnostics
apps/
  field-loop/        # runnable Cartesian kinematic reference
  openmhd/            # coupled CLI and separate 1D shock reference
```

## Scientific standard

No scientific claim is accepted simply because a simulation finishes: every milestone must report convergence, conservation, magnetic-divergence diagnostics, Galilean-boost comparison and numerical provenance. In particular, do **not** advertise `∇·B = 0` to machine precision under arbitrary discrete operators.

## Visibility and license

The repository is **public** and already includes an [MIT License](LICENSE) chosen at repository initialization. The license applies to this repository's materials; verify compatibility before incorporating third-party code. The experimental references are not a validated scientific release.

## Primary reference

Springel, Mayer & Pakmor (2026), [arXiv:2609.35989](https://arxiv.org/abs/2609.35989). The [M0 specification](docs/PAPER_IMPLEMENTATION_SPEC.md) extracts the v1 gauge, vector-potential update, cleaning, stencils and stage sequence, and attributes apparent inconsistencies. Explicit engineering choices and independent AI review are recorded separately. General-method implementation and physical validation remain M1 work; author confirmation and human peer review are not claimed.

## Continue in Codex on macOS

- [Codex agent instructions](AGENTS.md) — persistent project conventions.
- [ChatGPT-to-Codex context handoff](docs/CODEX_HANDOFF.md) — discussion decisions, technical scope and current status.
- [Mac Pro Codex setup](docs/MAC_CODEX_SETUP.md) — clone the GitHub repository and open it as a local Codex project.
- [First Codex task](codex/FIRST_TASK.md) — review the primary paper and complete scientific M0 before implementing code.

The local Codex project is established by cloning this repository and opening the local directory in Codex. The original ChatGPT conversation is **not automatically transferred** as a Codex chat history.
