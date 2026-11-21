# Three-dimensional galaxy-merger implementation goal

Owner instruction, 2026-11-22: implement a 3D moving mesh for galaxy mergers
with dark matter, gas and stars, and an AREPO-like multiphase interstellar
medium with star formation. The owner authorized parallel agents and routine
engineering decisions. This document defines the staged deliverable; it is
not a record of implemented 3D/gravity/star-formation physics.

## Starting boundary

M1 is not accepted yet. The selected fixed/rigid 2.5D engineering candidate
has complete passing historical A/B campaigns and a conditional independent
AI source review. Its integrated-source preflight and short bounded stages
pass. At recovery the fresh matrix had 24/24 mean-field and 47/48 medium
cases complete; no required physical failure was recorded. One incomplete
upload/start left a workflow in `created`; that same workflow was started
successfully, without duplication. A host reboot had also terminated the
detached supervisor and completion notifier.

Supervision now runs as a task-specific foreground login service, resuming
the existing immutable plans after reboot. It removes its login plist after
confirmed coordinator notification. It changes no scientific source, gate,
benchmark or workflow identity. The 112-wave/30-physics phases remain behind
the registered medium/mean precondition. Complete the fresh results,
independent reductions or complete input identity checks, final output
review, and scoped M1 acceptance before extending the coupled solver to 3D.

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
mass and velocity units and pinned conversions. A hydrodynamic boundary/ambient
medium prescription must be chosen explicitly and checked for domain-size
effects. A periodic gas test mesh does not silently imply periodic gravity.

## Dependency order and acceptance

| Stage | Concrete deliverable | Evidence required before escalation |
| --- | --- | --- |
| M1 final | Accept the exact current 2.5D fixed/rigid reference | Existing unchanged registered gates, complete provenance, independent reductions and final separate AI review. |
| M2a geometry | 3D cells/faces, periodic images, oriented connectivity and deterministic rebuilds | Analytic Cartesian/nonuniform fixtures, volume closure, reciprocal faces, translation/permutation/thread checks, degeneracy handling and independent geometric comparison. |
| M2b operators | Conditioned 3D derivatives, full-vector curl, gauge/cleaning and background field | Polynomial reproduction, manufactured refinement, explicitly different divergence operators and mean-flux tests. |
| M2c motion | Coupled 3D moving-mesh fluid/MHD evolution | Uniform-state geometric conservation, equal/opposite face exchange, topology-change fixtures, smooth-wave order, field advection, blast/vortex and joint boosts. The current fixed/rigid Heun guard cannot simply be removed. |
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

Three independent preparatory streams can proceed while the pinned M1 source
runs. Their first deliverables are source/specification and validation contracts,
not unvalidated numerical implementation:

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
The exact frozen M1 scientific files remain unchanged throughout its campaign.
Source/specification findings and unresolved equations must be explicit.
