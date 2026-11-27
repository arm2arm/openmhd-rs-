# OpenMHD-RS

**Vector-potential magnetohydrodynamics on Voronoi meshes, in Rust.**

An independent implementation of the ideal-MHD method described by
[Springel, Mayer & Pakmor (2026)](https://arxiv.org/abs/2609.35989),
with conservative gas dynamics and a magnetic field reconstructed from a
cell-centred vector potential. The project uses Rust 2024 and `f64`, with
Rayon kernels and a staged path toward MPI and magnetized galaxy mergers.
It is independently written, rather than an AREPO fork.

[Illustrated overview](docs/OVERVIEW.md) · [Results](#results-at-a-glance) · [The formalism](#the-formalism) ·
[Code and execution](#code-and-execution) · [Roadmap](docs/GALAXY_MERGER_PLAN.md) ·
[Development history](HISTORY.md)

![Animated cutaway of a three-dimensional Voronoi mesh with prescribed generator motion](docs/images/mesh_motion_3d_preview/moving_mesh_3d.gif)

*A 3D geometry teaser: 27 generators follow prescribed periodic paths, with
one cell highlighted. This independent kinematic illustration has no fluid
or magnetic evolution. [Static figure, renderer and provenance](docs/MESH_MOTION_3D_PREVIEW.md).*

## Results at a glance

**November 27, 2026. M2b is accepted for static 3D magnetic-field reconstruction.**
The quadratic curl reached 1.76% relative error on the regular 32³ grid and at most 3.81%
on three jittered 32³ grids. All 24 required irregular-mesh divergence sequences
decreased at both refinements under the preregistered revision. The exact-zero
cubic control stayed within its roundoff bound. [M2b decision](tests/reference/m2b_static_operators/acceptance.json) · [Convergence plots and historical O02 result](docs/galaxy/M2B_STATIC_OPERATORS.md).

![Magnetic field recovered on 32,768 jittered 3D Voronoi cells](docs/images/m2b_operators/fourier_field.png)

*Arrows show field directions at 125 sampled cell centroids in one static mesh.
Color gives the measured vertical field component.*

**November 26, 2026. M2a is accepted for the static 3D Voronoi reference.**
The Rust build passed 678 workspace regressions, 252 analytic mesh comparisons
and all eleven independent geometry checks on 252 irregular and difficult
mesh runs. The largest mesh had 512 cells and 4,063 shared faces. All 84
input arrays produced byte-identical meshes at one, two and four declared
threads. The named fixed/rigid 2.5D MHD reference holds its separate M1
acceptance.
[M2a decision](tests/reference/m2a_static_geometry/acceptance.json) ·
[Results and periodic contact analysis](docs/galaxy/M2A_FINALIZATION_STATUS.md).

| Result | Recorded evidence | Scope |
| --- | --- | --- |
| **214 fresh MHD cases, 58 checks passed** | [Accepted M1 packet and final review](tests/reference/m1_final_acceptance/README.md) | Periodic, single-process, fixed or rigidly translated 2.5D meshes |
| **99 boost pairs, 8 spatial ladders** | [Six independent reductions and exact configuration](tests/reference/m1_final_acceptance/acceptance.json) | Registered comparisons; temporal orders remain observations |
| **252 static 3D comparisons passed** | [Seven analytic families on the repaired build, 2,016 gate groups](docs/galaxy/results/m2a_general_20261125/repaired-analytic.json) | Volumes, centroids, faces, normals, moments and closure across scales and transforms |
| **240 geometry reproducibility comparisons** | [231 strict passes and nine exact zero-area contact cases](docs/galaxy/M2A_FINALIZATION_STATUS.md#reproducibility-results) | Reordered inputs, repeated runs, thread settings, translations and periodic crossings |

In 2.5D, fields depend on two spatial coordinates and retain all three vector
components. The accepted configuration is an explicitly named engineering
reference; the historical `paper-global-v2` binary default is unchanged.

### Waves, shocks and vortices

![Alfvén-wave magnetic-field errors decrease with resolution on regular and jittered meshes](docs/images/overview/alfven_ladders.png)

*Eight Alfvén ladders meet the registered order threshold of 1.8. This figure
shows the earlier iterative campaign A, with fitted orders 1.883–1.959.
[Campaign results](tests/reference/m1_iterative_step_campaigns/README.md) ·
[Figure inputs and hashes](docs/images/overview/provenance.json).*

![Brio–Wu density, pressure, velocity and magnetic-field profiles against the Athena++ reference](docs/images/overview/brio_wu.png)

*Brio–Wu shock structure from campaign A compared with the pinned Athena++
reference. The [benchmark packet](docs/M0_BENCHMARK_PACKET.md) records the
reference setup and comparison rules.*

![Orszag–Tang density from OpenMHD-RS beside the archived Athena++ reference](docs/images/overview/orszag_tang.png)

*Orszag–Tang density at time 0.5: campaign A on a 256² Voronoi mesh, beside a
512² Athena++ calculation retained as 64² bin averages. The displayed physics
figures precede the fresh accepted M1 rerun; their original provenance is
preserved. [Fresh output review](docs/M1_FRESH_SCIENTIFIC_OUTPUT_REVIEW.md).*

### A moving mesh in the Orszag–Tang vortex

[![Fixed-count and adaptive Voronoi meshes side by side at time 0.768; click to play](docs/images/orszag_tang_mesh/refinement-preview.jpg)](docs/images/orszag_tang_mesh/refinement-comparison.mp4)

**[Play the comparison movie](docs/images/orszag_tang_mesh/refinement-comparison.mp4).**
Both meshes start with 1,152 cells and follow the same time-resolved OpenMHD-RS
planar MHD flow. The left panel keeps its generators. In the right panel, the
blue circle requests finer cells and the red circle requests coarser cells as they
orbit. Refinement acts on the displayed mesh, with the gas evolved on a fixed grid.
[Methods, data and four snapshot times](docs/galaxy/ORSZAG_TANG_MESH_MOVIE.md) ·
[Springel, Mayer & Pakmor, Figure 23](https://arxiv.org/pdf/2609.35989#page=31).

### Actual Rust geometry in 3D

![Three camera views of the actual Rust-exported nonuniform periodic 64-cell Voronoi mesh](docs/images/geometry3_actual_20261123/case0156/mesh3d.png)

*Recorded polygon edges and generators from the Rust `geometry3-case`
executable, rendered from its actual output. These are three static camera
views, retaining periodic owner/image charts.
[More figures and rendering provenance](docs/galaxy/STATIC_GEOMETRY_VISUALIZATION.md) ·
[All 252 analytic comparisons](docs/galaxy/STATIC_GEOMETRY_COMPARISON_RESULTS.md).*

### A collisionless galaxy merger in 3D

[![One frame from the collisionless merger showing particle motion, projected density and the 3D Voronoi mesh](docs/images/nbody_merger_100/particles-density-voronoi.png)](docs/images/nbody_merger_100/particles-density-voronoi.mp4)

Two equal-mass galaxies merged under direct N-body gravity. At the final snapshot, the inner 100 particles contained 49 from one progenitor and 51 from the other. A second run with half the timestep reproduced sustained core overlap. [Watch particles, density and Voronoi cells evolve together (MP4)](docs/images/nbody_merger_100/particles-density-voronoi.mp4) · [Explore the 3D trajectory and measurements](docs/galaxy/NBODY_MERGER_100.md).

## The formalism

The continuum starting point is ideal MHD with magnetic permeability
$\mu_0=1$. A fixed periodic mean field is stored separately from the
periodic vector potential:

$$
\mathbf B=\overline{\mathbf B}+\nabla\times\mathbf A,
\qquad
E=\frac{p}{\gamma-1}
  +\frac{\rho\lvert\mathbf v\rvert^2}{2}
  +\frac{\lvert\mathbf B\rvert^2}{2}.
$$

The auxiliary velocity $\mathbf u$ selects the advective gauge, while
$\phi$ supplies gauge cleaning. With zero explicit resistivity, the
Eulerian vector-potential equation is

$$
\partial_t\mathbf A
=\mathbf v\times\mathbf B
-\nabla(\mathbf u\cdot\mathbf A)
+\nabla\phi.
$$

Gas mass, momentum and total energy are cell integrals. Oriented fluxes
through each shared moving face enter its two cells with opposite signs:

$$
\mathbf Q_i=V_i
\bigl(\rho_i,\rho_i\mathbf v_i,E_i\bigr)^{\mathsf T},
\qquad
\frac{d\mathbf Q_i}{dt}
=-\sum_{j\in\mathcal N(i)}a_{ij}\widehat{\mathbf F}_{ij},
\qquad
\widehat{\mathbf F}_{ji}=-\widehat{\mathbf F}_{ij}.
$$

The magnetic potential is evolved as a point value rather than a conserved
cell integral. Its fitted derivatives reconstruct the magnetic field.
The code reports distinct least-squares and face-based divergence diagnostics:
the continuum identity for the divergence of a curl does not make arbitrary
discrete operators vanish to machine precision.

The accepted M1 reference combines a bulk-frame gauge, quadratic fits,
reevaluated Heun stages, an iterative projected-rate solve, the `hlld-pressure`
flux blend and the `smooth-extrema` potential limiter. These engineering
choices and their measured tradeoffs are recorded separately from the paper's
endpoint formulation. See the [equation-to-code map](docs/PAPER_IMPLEMENTATION_SPEC.md),
[discrete reference contract](docs/VECTOR_POTENTIAL_REFERENCE.md) and
[scoped acceptance](tests/reference/m1_final_acceptance/acceptance.json).

## Code and execution

The toolchain is pinned to **Rust 1.85.1**. Start with the
[setup guide](docs/MAC_CODEX_SETUP.md) and [REANA execution guide](docs/REANA.md).
Project validation uses immutable source snapshots, required build/import
preflights and one independent benchmark case per REANA workflow.

The accepted M1 configuration is selected explicitly:

```text
--profile bulk-frame-heun-quadratic-v1
--projection-screening 1
--riemann hlld-pressure
--potential-limiter smooth-extrema
```

It uses the iterative projection, fixed/rigid periodic geometry and the
default trial-step fraction of 1. The cached `--accelerated-projection`
option is a separate choice. [Full configuration and campaign plan](docs/M1_FULL_VALIDATION_PLAN.md#configuration-under-test).

| Component | Code | Guide |
| --- | --- | --- |
| States, EOS and face fluxes | [`mhd-core`](crates/mhd-core) | [Conservative flux validation](docs/CORE_FLUX_VALIDATION.md) |
| Vector potential and 2.5D evolution | [`mhd-vector-pot`](crates/mhd-vector-pot) | [Method and discrete operators](docs/VECTOR_POTENTIAL_REFERENCE.md) |
| Voronoi geometry and reconstruction | [`moving-mesh`](crates/moving-mesh) | [Static 3D implementation](docs/galaxy/M2A_IMPLEMENTATION.md) · [Predictive Lloyd mesh motion](docs/galaxy/LLOYD_REGULARISATION.md) |
| Persistent entity identity | [`galaxy-types`](crates/galaxy-types) | [Identity implementation](docs/galaxy/IDENTITY_IMPLEMENTATION.md) |
| Direct gravity and collisionless KDK | [`gravity`](crates/gravity) | [Gravity implementation](docs/galaxy/G1_IMPLEMENTATION.md) · [Force–energy gradient results](docs/galaxy/G1_FORCE_GRADIENT.md#measured-reana-results) |
| Checkpoints and command-line drivers | [`mhd-io`](crates/mhd-io), [`openmhd`](apps/openmhd) | [Restart contract](docs/CHECKPOINT_RESTART.md) |

## What comes next

The [galaxy-merger plan](docs/GALAXY_MERGER_PLAN.md) separates static geometry,
moving geometry, gravity, gas/MHD, equilibrium components and published
ISM/star-formation/feedback physics into independent validation gates.
M2a closed the static geometry checks, and M2b closed the static spatial operators.
M2c now computes how quickly each cell's volume changes and how its centroid moves.
Both rates showed second-order convergence on a rotating 3D Voronoi face across six axis
permutations. The moving point-curl derivative also converged at second order. The point curl
failed the initial magnetic-mean test on jittered meshes. The experimental shared-face
candidate preserved that mean to 1.77×10⁻¹⁷ and gave orders 2.48–2.50 on six
irregular mesh families. Two regular-grid diagnostics used at most 0.527% of the cubic
roundoff budget in the separately validated revision. The coupled moving-MHD gates remain open.
[Measured fields, divergence and convergence plot](docs/galaxy/M2C_MOVING_CURL_RESULTS.md#cell-average-field-and-divergence).
[Centroid-motion figure and measured rates](docs/galaxy/M2C_CENTROID_RATES.md#measured-reana-results) ·
[M2a geometry results](docs/galaxy/M2A_FINALIZATION_STATUS.md) · [3D motion and validation plan](docs/galaxy/MESH_3D_SPEC.md).

The current results do not establish deforming 3D MHD, MPI equivalence,
adaptation/local timesteps, general Galilean invariance, a coupled
self-gravitating galaxy or a full-duration magnetized merger. M1 acceptance
also retains the measured 3–10% fixed passive-loop error increase and
17–36% rim-undershoot increase of its chosen limiter. Reviews are explicitly
labelled AI reviews; human peer review and author confirmation are not claimed.

[Roadmap](docs/ROADMAP.md) · [Validation requirements](docs/VALIDATION.md) ·
[Architecture](docs/ARCHITECTURE.md) · [Current handoff](docs/CODEX_HANDOFF.md) ·
[Earlier results and reproduction commands](HISTORY.md) ·
[Contributing](CONTRIBUTING.md) · [MIT license](LICENSE)
