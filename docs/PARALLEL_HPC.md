# MPI + Rayon / Slurm execution plan

## Parallelism model

- **MPI:** spatial decomposition of moving Voronoi cells, with stable global IDs and owned/ghost cells.
- **Rayon:** CPU data-parallelism within each rank for reconstruction, independent face fluxes, potential updates and diagnostics.
- Initially invoke MPI only from the controlling thread and select MPI thread support appropriately; do not assume `MPI_THREAD_MULTIPLE` is required.

## Decomposition and communication

1. Partition points with a Morton/Hilbert space-filling curve; update load assignments after motion.
2. Maintain ghost layers covering geometry and reconstruction stencils.
3. Exchange position, velocity, gas state, vector potential, cleaning fields, local timesteps and periodic image metadata.
4. Assign each shared face a single flux owner, then apply matching opposite conservative cell updates across ranks.
5. Rebalance based on measured workload (not only raw cell count).
6. Validate ghost geometry and neighbor stencils at MPI boundaries after re-tessellation.

## Thread safety

- Compute independent face-flux arrays; accumulate cell updates with reductions, graph coloring or conflict-free ownership.
- No unsynchronized mutable writes to adjacent cell records in Rayon loops.
- Use packed/contiguous buffers and avoid per-face heap allocations.
- Compare numerical outputs across 1, 2, 4, 8 and 16 threads as applicable.

## I/O and restart

Start with serial or per-rank files for small tests. Parallel HDF5/MPI-IO is a later milestone requiring verified MPI-enabled HDF5 linkage. Store mesh topology, global cell IDs, numerical state, integrator state and provenance in restart data.

## Profiling

Track wall time, Voronoi tessellation, gradient/curl kernels, HLLD fluxes, MPI communication volume/wait, rank imbalance, output, memory high-water mark and steps/cell updates per second. Avoid unnecessary global synchronizations.

## Slurm example

See [examples/slurm/hybrid.sbatch](../examples/slurm/hybrid.sbatch). At 4 nodes x 48 cores/node, 6 ranks/node x 8 Rayon threads/rank uses 192 cores; **this is illustrative only** and must be benchmarked for each cluster.

## Strong and weak scaling

- Thread count vs time at fixed rank and problem.
- MPI ranks per node vs time and communication.
- Fixed global cells (strong scaling) across nodes.
- Fixed local cells/core (weak scaling) across nodes.
- Repeat physics acceptance tests for every scaling configuration.
