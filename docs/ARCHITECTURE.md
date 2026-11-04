# Proposed Rust software architecture

**Target architecture.** The Cargo workspace has the Cartesian `mhd-vector-pot`/`field-loop` pilot and a coupled `mhd-planar`/`openmhd` reference using `mhd-core` and `moving-mesh`. See [KINEMATIC_2D.md](KINEMATIC_2D.md) and [COUPLED_2D.md](COUPLED_2D.md). The latter is strictly planar with fixed/rigidly translating geometry; full 3D gauge, deforming mesh and parallel modules remain planned.

## Target Cargo workspace

```text
Cargo.toml                     # Rust 2024 workspace
crates/
  mhd-core/                    # EOS, primitive/conserved state, Riemann flux
  mhd-vector-pot/              # A evolution, gauge, reconstruction and cleaning
  moving-mesh/                 # Voronoi tessellation, faces, cell motion
  mhd-planar/                  # implemented experimental planar coupled reference
  time-integrator/             # RK stages, synchronization, local timesteps
  parallel/                    # domain decomposition, MPI ghosts, Rayon kernels
  output/                      # HDF5, checkpoints, diagnostics
apps/
  openmhd/                     # CLI and configuration
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
