# Proposed Rust software architecture

**Target architecture.** The Cargo workspace has the Cartesian `mhd-vector-pot`/`field-loop` pilot and a coupled `mhd-planar`/`openmhd` reference using `mhd-core` and `moving-mesh`. See [KINEMATIC_2D.md](KINEMATIC_2D.md) and [COUPLED_2D.md](COUPLED_2D.md). The latter is strictly planar with fixed/rigidly translating geometry; full 3D gauge, deforming mesh and parallel modules remain planned.

## Delivered bootstrap and deferred crate boundaries

[Issue #3](https://github.com/arm2arm/openmhd-rs-/issues/3) delivers the compilable serial workspace: four libraries (`mhd-core`, `mhd-vector-pot`, `moving-mesh`, `mhd-planar`) and two applications (`field-loop`, `openmhd`). Numerical utilities include periodic Voronoi geometry validation and conditioned least-squares derivatives, tested for affine reproduction, periodic crossings and smooth-curl convergence.

The user approved recording the following deferrals when closing the bootstrap issue. These are planned library boundaries, not missing dependencies of the runnable serial programs:

| Planned crate | Current location / capability | Extraction or implementation trigger |
| --- | --- | --- |
| `time-integrator` | Each serial solver owns its synchronized stepping; isolated cleaning stages are in `mhd-vector-pot::gauge` | Extract shared stage interfaces during the general M1 integrator work; hierarchical local steps remain issue #14 |
| `parallel` | Serial execution; no MPI/Rayon runtime is required | Introduce with M3 ownership/halo and threaded-kernel work, issues #10 and #11 |
| `output` | Application drivers write CSV; study scripts record configuration/provenance | Extract when a shared snapshot/restart API is implemented; HDF5/checkpoint support remains future I/O work |

See [ADR-007](DECISIONS.md#adr-007--serial-workspace-bootstrap-and-deferred-crates). Completing this bootstrap does not complete M1's general algorithm or physical-validation gates.

## Target Cargo workspace

```text
Cargo.toml                     # Rust 2024 workspace
crates/
  mhd-core/                    # EOS, primitive/conserved state, Riemann flux
  mhd-vector-pot/              # A evolution, gauge, reconstruction and cleaning
  moving-mesh/                 # Voronoi tessellation, faces, cell motion
  mhd-planar/                  # implemented experimental planar coupled reference
  time-integrator/             # planned: shared stages, synchronization, local timesteps
  parallel/                    # planned: MPI ownership/ghosts and Rayon kernels
  output/                      # planned: shared I/O, HDF5 and checkpoints
apps/
  field-loop/                  # implemented kinematic reference CLI
  openmhd/                     # implemented coupled CLI and 1D shock reference
tests/
  reference/                   # analytic and paper-based checks
  integration/                 # physics regressions
benches/                       # measurable computational kernels
```

## Essential data structures

- `CellId`: stable global identifier, not a local array index.
- `CellState`: conservative variables, primitives, `A`, gauge scalars, local timestep state.
- `MeshPoint`: position, prescribed mesh velocity, stable ID and owner rank.
- `Face`: oriented neighboring IDs, normal, area, centroid, moving-face velocity.
- `Geometry`: volume, centroid, neighbor/face indices and periodic transforms.
- `Domain`: MPI rank, owned cells, ghost layer, communication map.
- `Simulation`: physics, geometry, integrator, diagnostics, checkpoint context.

Prefer clear ownership of read-only ghosts and independent face-flux buffers. Determine structure-of-arrays versus array-of-structures using measured memory/cache performance, not ideology.

## Conceptual Rust interfaces

```rust
// Design pseudocode only; not compilable source.
trait MeshGeometry {
    fn rebuild(&mut self) -> Result<(), MeshError>;
    fn validate(&self) -> Result<(), MeshError>;
}
trait FluxOperator {
    fn face_flux(&self, /* left, right, face */) -> Flux;
}
trait VectorPotentialOperator {
    fn reconstruct_b(&self, /* A and geometry */) -> MagneticField;
    fn advance(&self, /* A, gauge, velocity, mesh, dt */) -> Result<(), PhysicsError>;
}
```

## Enforced invariants

1. Each shared face has a unique flux computation owner or exactly consistent duplicated evaluation.
2. Opposite conservative cell updates represent the same intercell face flux.
3. Ghost-cell data are read-only during kernels; owners apply final updates.
4. Mesh geometry must pass closure, orientation and degeneracy checks after topology changes.
5. Magnetic reconstruction and conservative fluid updates have explicit synchronization points.
6. Every snapshot records code revision, units, physical/numerical setup, MPI/thread layout and compiler options.

## Engineering process

- Independent unit tests first, small physics runs next, 3D and HPC testing later.
- The M0 equation-to-operator specification is a prerequisite for numerical implementation.
- All scientific changes require convergence, conservation and divergence-diagnostic comparisons.
- Rust FFI (MPI, HDF5 or geometry) requires pinned build dependencies and clearly audited unsafe boundaries.
