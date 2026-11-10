# OpenMHD-RS

Latest [candidate checkpoint](docs/CODEX_HANDOFF.md#active-full-pressure-blend-campaign-2026-11-10):
the explicitly selected `hlld-pressure` blend passes its eight focused shock
and vortex cases, including all four boost pairs. The column-shock boost error
is 6.05e-14 against the unchanged 1e-8 limit; regular/jittered N32 vortex
normalized divergence is .06846/.07301 against .1. All 96 historical HLLD/HLL
scientific files reproduce byte for byte. See the
[verified comparison and plot](tests/reference/m1_column_boost/pressure_blend/README.md).
The full REANA campaign is active within 24 aggregate cores / 64 GB. Its eight
preflight commands pass, including 163 release/all-target Rust tests, 80 Python
tests and M0 checks. Its [four short stages pass](tests/reference/m1_pressure_campaign/short/README.md),
with 51 completed evolutions and two historical pressure-failure controls
retained. The medium wave/loop stage is active; the full physical gates remain pending.
This is a separately named engineering extension, with the historical default
and failed controls preserved. HLLD's column-shock boost failure and global
HLL's vortex-divergence failure remain recorded in
[#24](https://github.com/arm2arm/openmhd-rs-/issues/24). Full M1 remains unaccepted.

The user has authorized merging this development checkpoint into main;
[that merge is separate from full M1 acceptance](docs/M1_MERGE_PLAN.md#updated-merge-instruction--2026-11-09).
Open validation issues and historical failed-run evidence are preserved.

**Status: serial 2.5D vector-potential implementation with operator/coupling tests, alongside the planar and kinematic pilots. The full M1 physical benchmark matrix and 3D paper method are not validated.**

M0's specification and initial benchmark packet are accepted following a separate, explicitly labelled [AI scientific review](docs/M0_AI_REVIEW.md). See the [acceptance boundary and M1 work remaining](docs/M0_REVIEW.md).

OpenMHD-RS is a proposed **publicly developed, MIT-licensed Rust research project** designed to independently implement and validate the moving-mesh vector-potential ideal-MHD method described by:

> V. Springel, A. C. Mayer & R. Pakmor (2026), *Divergence-free magnetohydrodynamics on a moving mesh*, [arXiv:2609.35989](https://arxiv.org/abs/2609.35989).

**This is not AREPO, a port of AREPO, or a claim that the paper's results have already been reproduced.** The physics implementation must be independently developed and quantitatively verified.

## Run the general-component 2.5D reference

For remote execution, the [REANA workflow](docs/REANA.md) packages the exact
working source and runs checks and benchmark studies on the AIP Kubernetes
backend. Large study outputs stay in the remote workflow workspace; local
development does not require repeating the full matrix on the laptop.

For the user-requested 24-core experiment, `vector-potential --threads 24`
parallelizes independent cell/face work within **one** simulation. The default
remains one thread. See the [threading contract](docs/THREADING_PLAN.md);
the [measured scaling results](docs/THREADING_RESULTS.md) retain exact numerical
agreement and show that the best thread count depends on workload. The
`threading` REANA study must use `-p jobs=1` to avoid multiplying 24 threads
by 24 simultaneous simulations. This does not claim full M1 or MPI validation.

Issue #6 adds three-component A/v/B on periodic 2D Voronoi geometry, smooth auxiliary velocity, gauge/cleaning, the old-data endpoint predictor, and fixed/rigid/deforming mesh motion. The explicit [paper-global-v2 contract](docs/VECTOR_POTENTIAL_REFERENCE.md) records the moving auxiliary-origin amendment and all test gates.

```sh
cargo run --release --locked -p openmhd --bin vector-potential -- --case smooth --n 8 --time 0.02 --output results/smooth
cargo run --release --locked -p openmhd --bin vector-potential -- --case deform --n 6 --motion prescribed --dt 0.002 --time 0.04 --output results/deform
python3 scripts/run_vector_potential.py
```

The driver writes initial/final cell CSVs and JSON diagnostics. The study checks curl convergence, uniform mean fields, gauge damping, mean-zero boosts and deforming-mesh convergence. **Nonuniform flows with nonzero mean B show a boost discrepancy in additional review probes; general Galilean invariance is not established.** See the [illustrated results, plot reproduction commands and AI review](docs/VECTOR_POTENTIAL_RESULTS.md). Full Alfvén/loop/shock/vortex validation remains issue #7.

## Wave/loop development (issue #7)

The [continuation and plots](docs/M1_COMPLETION_RESULTS.md) add the separately
named `bulk-frame-signal-v1` face completion and a regular/irregular Voronoi
prescribed-flow loop driver. The complete wave matrix passes **3/8 spatial
gates per profile**; boost comparisons pass **13/32 for the original profile
and 31/32 for the new comparator**. The new N256 regular fixed-grid standing
wave still fails its boost gate. The full prescribed-flow packet passes its
registered gates; temporal measurements do not establish second-order physical
time accuracy. See the [separate AI review](docs/M1_COMPLETION_AI_REVIEW.md).
All registered executions are complete; both profiles pass all 16 coupled-loop
boost pairs. The default and all historical failed gates are preserved;
full M1 validation has not passed.

Current development investigates time coupling with the separately named
`bulk-frame-heun-v1` integrator, restricted to fixed/rigid meshes. Its small
smooth time-order, boost and conservation checks pass. The 40-run REANA time
comparison reduces magnetic time errors but retains sub-second-order behavior
for the jittered standing wave. See the [contract](docs/M1_HEUN_INVESTIGATION.md)
and [current results](docs/M1_HEUN_RESULTS.md).
This is an engineering comparator; the default paper endpoint method is unchanged.

The next [auxiliary-projection investigation](docs/M1_AUXILIARY_RESULTS.md)
adds `bulk-frame-heun-spline-v1`, a separate engineering comparator using
continuous cubic deposition into the auxiliary velocity grid. It tests whether
discontinuous bin membership contributes to the remaining temporal errors,
with a controlled limiting-on/off REANA comparison. All 80 runs complete;
the limited jittered standing-wave time slopes improve to 2.000/2.011,
while the unlimited magnetic slopes remain below second order.

The long REANA matrices are stopped at the user's request while development
uses a [four-case short shock screen](docs/M1_SHOCK_INVESTIGATION.md), measured
at .87 seconds for the baseline. The experimental `bulk-frame-heun-projected-v1`
now completes all four short cases in 2.62 seconds with positive pressure,
conservation and boost checks passing. Its jittered Bx diagnostic still fails;
this is a partial stability improvement, not M1 acceptance. The new
[general shock/vortex comparison](docs/M1_PHYSICS_RESULTS.md) implements the
unchanged M0 reference packet with exact polygon-overlap measurements and a
shock signal-travel diagnostic. Small execution probes pass their boost and
budget checks, but jittered shock Bx and coarse-vortex divergence diagnostics
fail. Partial full-resolution results and failures are preserved; M1 acceptance and
the requested merge remain conditional on passing all gates.

The bounded [shock reconstruction trial](docs/M1_SHOCK_INVESTIGATION.md)
retains `bulk-frame-heun-quadratic-v1`. It completes the short cases and a
t=.02 extension, reducing jittered Bx error from .1075 to .0604 at t=.02
while keeping positive pressure, conservation and boost agreement. The
unchanged 1e-8 field gate still fails. Wider stencils improve smooth
convergence order but increase some absolute errors and runtime; the results
are an experimental improvement, not full M1 acceptance.

The current direction returns to the published endpoint formalism. The new
`paper-state-emf-v1` comparison uses the literal Eq. (69) Riemann-state source.
Its regular short shocks pass, but its jittered shocks still lose positive
pressure at t=.003343. It is not a fix or a new default. The
[paper/source and symmetry audit](docs/M1_SHOCK_INVESTIGATION.md#paper-source-comparison-measured-result)
records this failure and separates published terms from engineering choices.
Long jobs remain stopped and the M1 merge remains blocked by numerical gates.

The [2026-11-09 coupling audit](docs/M1_SHOCK_INVESTIGATION.md#resumed-paper-audit-and-prospective-mixed-stencil-trial-2026-11-09)
localizes most initial energy loss in the failing cell to two faces. A
paper-based mixed-Hessian trial fails earlier and is removed. Increasing the
transverse resolution to 8/16 rows stabilizes the short nx256 control while
retaining large Bx errors; the registered 4-row case is still unresolved.
The accumulated implementation and evidence are now committed and published
on the development branch. This is diagnostic progress, not M1 acceptance.

The subsequent [exact-pattern controls and plot](docs/M1_SHOCK_INVESTIGATION.md#measured-repeated-pattern-result)
show that repeating the original stretched mesh in taller boxes retains the
pressure failure. Compressing the same perturbations changes local Voronoi
connectivity and stabilizes t=.01, while Bx still fails. This narrows the
investigation to reconstruction/curl coupling near the magnetic discontinuity;
the original solver and M1 gates remain unchanged and unresolved.

The [frozen reconstruction audit](docs/M1_SHOCK_INVESTIGATION.md#measured-reconstruction-input-result)
rules out the paper's optional central-value primitive fit as an improvement
to the initial pressure deficit. Diagnostic substitutions identify broadened
neighboring By values as its dominant driver; removing Bx error alone is
insufficient. These substitutions are never evolved and are not a solver fix.
The next correction must resolve conservative energy/curl coupling while
passing the original benchmark; no new evolution profile is introduced.

The [historical 144-run increment](docs/M1_WAVE_LOOP_RESULTS.md) covers mean-field boost refinement and N32/64 Alfvén/loop subsets. Its separately named `bulk-frame-v1` gauge passes the mean-field ladder and improves Alfvén boost comparisons from 7/16 to 15/16 passing pairs. That increment left one N64 standing-wave boost failure and the full resolution/temporal packet open. The continuation preserves those results; `paper-global-v2` remains the default.

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
