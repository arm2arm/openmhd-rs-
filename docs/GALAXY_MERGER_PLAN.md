# Three-dimensional galaxy-merger implementation goal

Owner instruction, 2026-11-22: implement a 3D moving mesh for galaxy mergers
with dark matter, gas and stars, and an AREPO-like multiphase interstellar
medium with star formation. The owner authorized parallel agents and routine
engineering decisions. This document defines the staged deliverable; it is
not a record of implemented 3D/gravity/star-formation physics.

## Starting boundary

M1 scoped acceptance is complete at commit `309ae41` (2026-11-22). The named
iterative quadratic-Heun/smooth-extrema/hlld-pressure candidate is accepted
for periodic, single-process fixed/rigid **2.5D** only. The
[acceptance archive](../tests/reference/m1_final_acceptance/README.md) retains
214 fresh scientific cases, 58 registered checks, 238 input identities, six
actual independent reductions and separate source/output/archive AI reviews.
The repaired 174-method metadata suite passes independent REANA workflows;
actual collection, packaging, relocated portable verification and copied outer
consistency execution also pass. Default-profile failures, the original failed
metadata suite and measured limiter tradeoffs remain preserved.

M2a accepted the static serial geometry reference on November 26. M2b accepted the
static 3D spatial operators under revision 2 on November 27. M2c is the next mesh
milestone and starts with prescribed motion and geometric conservation. The gravity
and galaxy-component campaigns proceed under their own criteria. [M2a decision](../tests/reference/m2a_static_geometry/acceptance.json) · [M2b decision](../tests/reference/m2b_static_operators/acceptance.json) · [3D motion plan](galaxy/MESH_3D_SPEC.md).

## Intended components and model choices

| Component | Initial implementation boundary |
| --- | --- |
| Gas | Three-dimensional moving Voronoi finite volumes with conservative mass, momentum and total-energy exchange, ideal MHD, synchronized steps, explicit mesh regularity/topology checks and recorded independent divergence operators. |
| Dark matter | Collisionless gravitating particles, stable IDs, positive masses, three positions/velocities and explicit fixed softening. |
| Stars | Collisionless gravitating particles with stable birth IDs, formation time, birth mass/current mass and metallicity metadata; existing stars and newly formed stars share one force/integration path. |
| Gravity | Isolated self-gravity first. Symmetric softened direct summation is the small-system force oracle; a tree implementation follows force and orbit validation. Gas and both collisionless species contribute consistently. |
| Thermal/ISM physics | Published Springel–Hernquist two-phase effective model: cold clouds and hot ambient medium, radiative terms, star formation and supernova-driven heating/evaporation. Exact equations, conventions, parameters and applicability must be transcribed from full text before implementation. |
| Coupling | Explicit gas-to-star mass, momentum, metals and energy accounting, with separate radiation/feedback source ledgers. Unresolved feedback represented by the effective EOS must not also be injected as a second copy of the same energy. |
| Galaxy setup | Reproducible equilibrium dark-matter halo, stellar structure and gaseous disk; relax and validate each isolated galaxy before merging a pair. Orbital, spin, mass-ratio and seed parameters belong in the run configuration. |
| Output | Restartable snapshots, component catalogues, force/mesh counters, mass/momentum/energy/angular-momentum ledgers, star-formation histories and projected maps with complete provenance. |

The model starting point is the original
[Springel & Hernquist multiphase paper](https://arxiv.org/abs/astro-ph/0206393),
whose published model includes cold/hot exchange, star formation and feedback.
[Springel's moving-mesh paper](https://arxiv.org/abs/0901.4107) supplies a
separate hydrodynamic/geometry reference. These are sources for independently
implemented numerical contracts; no AREPO implementation equivalence is
assumed. Additional physics must have its own declared model and tests.

The initial merger target uses isolated, non-expanding physical coordinates.
Dimensionless fixtures use G=1; galaxy configurations declare physical length,
mass and velocity units and pinned conversions. The first bounded reference
uses [a conducting slip box](galaxy/BOUNDARY_MHD_SPEC.md), zero normal magnetic
flux and a nonzero compact-support interior field. Its discrete boundary
operators remain unaccepted; ambient-medium and domain-size controls are
required. A periodic gas test mesh does not silently imply periodic gravity.

## Dependency order and acceptance

| Stage | Concrete deliverable | Evidence required before escalation |
| --- | --- | --- |
| M1 final | Accept the exact current 2.5D fixed/rigid reference | Existing unchanged registered gates, complete provenance, independent reductions and final separate AI review. |
| M2a geometry | 3D cells/faces, periodic images, oriented connectivity and deterministic rebuilds | Analytic Cartesian/nonuniform fixtures, volume closure, reciprocal faces, translation/permutation/thread checks, degeneracy handling and independent geometric comparison. |
| M2b operators | Conditioned 3D derivatives, full-vector curl, gauge/cleaning and background field | Polynomial reproduction, manufactured refinement, explicitly different divergence operators and mean-flux tests. |
| M2c motion | Coupled 3D moving-mesh fluid/MHD evolution | Uniform-state geometric conservation, equal/opposite face exchange, topology-change fixtures, smooth-wave order, field advection, blast/vortex and joint boosts. The current fixed/rigid Heun guard cannot simply be removed. |
| M2d physical boundary | Bounded/nonperiodic gas and magnetic/gauge boundary path for isolated galaxies | Explicit source/engineering derivation, boundary flux/energy and manufactured magnetic/gauge checks, ambient-medium and domain-size controls. Periodic gas geometry plus isolated gravity does not satisfy this stage. |
| G1 particles | Component state, direct softened gravity and globally stepped collisionless integration | Two-body/orbit convergence, center-of-mass and momentum conservation, potential/force consistency, mixed-species equality and isolated equilibrium stability. |
| G2 gravity coupling | Accelerated gravity and consistent gas/particle kicks | Force-error comparison with the direct oracle, timestep/softening convergence, gas hydrostatic/collapse tests, momentum symmetry and an explicit energy-work diagnostic. |
| G3 ISM/SF | Cooling/heating, multiphase closure, star formation, recycling and feedback bookkeeping | Source-mapped one-zone solutions, equilibrium/threshold continuity, limiting cases, mass/metals/momentum accounting, energy-source ledger and seeded stochastic expectation/convergence checks. |
| G4 isolated galaxies | Stable equilibrium multicomponent galaxy initial conditions | Density/rotation/dispersion profiles, equilibrium drift, star-formation history and resolution/domain/softening/timestep controls before a pair is combined. |
| G5 merger | A reproducible dark-matter/gas/star merger demonstration | Completed configured orbit, component histories, accounting residuals, field and mesh diagnostics, paired resolution controls, restart parity, visualization and a separate scientific review. |

MPI decomposition, local timesteps and refinement remain separate extensions
with their existing reproducibility requirements. The first validated small
merger may be single-process. Performance features cannot replace missing
geometry, dynamics or source-term acceptance evidence.

All new executable tests/evolutions run on REANA. Independent ready cases get
separate concurrent workflows, each declaring threads and memory; no aggregate
CPU cap. Required preflight/build and physical dependencies remain gates.
Failure thresholds are registered before execution and retained on failure.

## Parallel work and integration

The three preparatory streams have delivered source/specification and validation
contracts with separate AI reviews. Their current implementation slices follow
scoped M1 acceptance and retain all component-specific validation dependencies:

1. `docs/galaxy/MESH_3D_SPEC.md`: geometry representation, candidate dependency
   license/API audit, moving-face/topology contract, 3D operator requirements
   and prospective REANA fixtures.
2. `docs/galaxy/GRAVITY_PARTICLES_SPEC.md`: collisionless species, units,
   softening, force oracle/tree, integration, gas coupling and equilibrium ICs.
3. `docs/galaxy/ISM_STAR_FORMATION_SPEC.md`: full-text equation/parameter map,
   thermal closure, stochastic spawning, recycling/feedback/metals accounting
   and one-zone/disk validation.

Each stream owns separate files. The coordinator owns M1 supervision, shared
architecture/status files, integration decisions and milestone acceptance.
The exact frozen M1 scientific files remained unchanged throughout its campaign
and remain retained in the accepted archive as new modules are developed.
Source/specification findings and unresolved equations must be explicit.

The [shared integration contract](galaxy/INTEGRATION_CONTRACT.md) reconciles
persistent IDs, SI/cgs conversions, gas-centroid gravity, accepted-endpoint
births, source/representation-energy ledgers and the additional physical
boundary prerequisite. These are design decisions pending implementation
and their declared validation, not scientific acceptance.

The [independent M2 design review](galaxy/MESH_3D_DESIGN_REVIEW.md) requires
six moving-stage revisions before coupled implementation. Static geometry
and operator slices remain separately gated after M1 acceptance. The
[analytic fixture packet](galaxy/fixtures/README.md) and
[candidate dependency metadata inventory](galaxy/dependency_audit/README.md)
are source/design preparation, with no executed geometry evidence or
dependency adoption. The [cooling contract](galaxy/COOLING_RATES_SPEC.md) and
[finite-phase star-formation contract](galaxy/ISM_STAR_FORMATION_SPEC.md)
likewise require independent equation/input review and REANA validation.
