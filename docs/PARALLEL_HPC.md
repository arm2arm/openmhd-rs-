# MPI and Rayon execution

OpenMHD-RS can run a simulation on MPI ranks, with one Rayon thread pool per rank. The original Rust entry points default to one thread. Independent REANA workflows exercise separate cases. Each MPI case launches real ranks working on the **same** physical problem. [Measurement protocol](../reana/m3/mpi_matrix.py) · [REANA execution policy](REANA.md).

## Run a hybrid case

Build the MPI executable against the MPI implementation used by your launcher. The standalone Cargo manifest keeps the serial workspace usable on a machine without MPI. Building it requires a C toolchain, `mpicc`, the corresponding MPI library and libclang for the Rust bindings. The REANA build records Rust 1.85.1 and MPICH 4.3.2. [MPI package](../apps/openmhd-mpi/Cargo.toml) · [Build recipe](../reana/m3/mpi_build.py).

```bash
cargo build --release --locked --manifest-path apps/openmhd-mpi/Cargo.toml
exe=./apps/openmhd-mpi/target/release/openmhd-mpi
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

# Two MPI ranks and two Rayon threads per rank. The final two arguments are time increments.
mpiexec -n 2 "$exe" 2 mesh docs/galaxy/fixtures/m2c_tessellation_flip.txt mesh-output 0.5 0.5

# The registered iterative 2.5D profile. The two times are successive absolute targets.
mpiexec -n 2 "$exe" 2 mhd2 alfven 8 8 0 0.0078125,0.015625 wave-output
mpiexec -n 4 "$exe" 1 mhd2-restart wave-output/checkpoint.bin 0.03125 resumed-wave
```

Use the same executable when resuming a 2.5D MHD checkpoint. The checkpoint records hashes of the numerical build and the executable itself. The rank and thread counts may change at restart. [Checkpoint codec](../crates/mhd-vector-pot/src/checkpoint.rs).

Supply a new output directory for each run. Rank zero reads shared inputs, broadcasts the bytes and writes the scientific files. Every rank verifies the command arguments. The mesh example writes vertices, volumes, oriented face incidences and an ownership history. The MHD example writes the full numerical state and a versioned checkpoint. The Slurm example passes the requested CPUs per task to the Rayon team and reserves distinct cores for each rank. [Slurm script](../examples/slurm/hybrid.sbatch) · [Driver dispatch](../apps/openmhd-mpi/src/main.rs).

## Run with Rayon on one machine

The positional geometry and gravity examples accept a leading `--threads N`. The following command follows five generators through a 3D Voronoi face flip using four worker threads and writes the mesh at its initial and two later epochs.

```bash
cargo run --release --locked -p moving-mesh --example moving-voronoi3 -- \
    --threads 4 docs/galaxy/fixtures/m2c_tessellation_flip.txt 0.5 0.5 > mesh.csv
```

For the accepted 2.5D vector-potential profile, the ordinary `vector-potential` binary accepts its existing `--threads N` option. To distribute a single simulation between processes, use the MPI executable above. [Geometry example](../crates/moving-mesh/examples/moving-voronoi3.rs) · [Gravity example](../crates/gravity/examples/gravity-trajectory.rs).

## Where the work runs

| Path | Parallel work and ordering |
| --- | --- |
| Periodic 2D and bounded or periodic 3D Voronoi geometry | Ranks own generators in weighted Morton order. 3D owners compute exact clipping and send the supporting plane triples. Each rank reconstructs identical oriented polygons and validates shared faces. The next 3D rebuild uses measured clipping work, including the inner rebuilds of Lloyd prediction. |
| Geometry and motion | Independent per-face geometry, centroid and motion kernels use Rayon. Generator trajectories retain persistent IDs through position updates, periodic crossings and changes in adjacency. Euler and Heun swept-volume quadrature and face corrections have rank owners. Their small grounded graph solve retains the original Cholesky order. |
| Gas and vector potential in 2.5D | Owners exchange cell positions, conserved integrals, vector potential and cleaning scalar. One owner computes the Riemann solution for each shared face at each stage. The accepted solver updates both cells in the original face order and keeps its global timestep. The iterative projection distributes curl applications and their transposes. |
| 3D field and fluid operators | Shared-face reconstruction, curl, its transpose and Gram diagonal, moving-curl derivatives and ALE fluxes expose rank-aware entry points. Magnetic and fluid flux contributions retain their original signs and summation order. |
| Point-sampled 3D fields | Cell owners compute the linear, quadratic and curvature-corrected fields from the original M2b fits. Ranks share the independent divergence profiles and the six applications of the static and moving point operators. Each application retains the library's original accumulation order. |
| Collisionless gravity | Each unordered pair has one force evaluation. Bounded batches feed the original sorted compensated reductions. KDK retains particle IDs, complete force-cache identity and an atomic endpoint. A restart can use a different rank layout. |
| Planar comparators | Constrained transport, its admissibility-limited variant and planar MHD distribute face solves. Prescribed transport and passive-potential evolution distribute cell rates. The Cartesian kinematic and 1D Brio–Wu reference drivers also accept local Rayon threads. |

MPI calls run on the initializing thread with `MPI_THREAD_FUNNELED`. Worker threads produce owned records. Each rank gathers those records, checks owner coverage, then applies the serial ordering of scientific reductions. This keeps shared-face and particle-pair updates reproducible when there are empty owners or the decomposition changes. [MPI transport](../apps/openmhd-mpi/src/transport.rs) · [Ownership](../crates/mhd-parallel/src/partition.rs) · [3D geometry exchange](../crates/moving-mesh/src/three_d/oracle/distributed.rs).

Use `field3-tangent-points` to evaluate both magnetic representations at the same smooth periodic mesh epoch. Its arguments are the generator catalog, the field sample file, the adiabatic index, the three components of the mean magnetic field, and a new output directory. Each field row contains the persistent ID, density, three velocity components, pressure, three vector-potential components, cleaning scalar and local step size. The extra `point-operators.csv` contains the three point reconstructions, their independent divergences and the static and moving point operators. [Point-sampled driver](../apps/openmhd-mpi/src/point3.rs) · [Reproducible jittered example inputs](../reana/m3/mpi_case.py).

## Scope and performance

The 3D shared-face curl, ALE flux and conservative swept-mesh update route numerical rows to their consumer ranks by default. Use `--halo full` after the thread count for the complete-row comparison. The geometry catalogue, grounded mesh solve and several other operators still use replicated data. The REANA measurements use distinct MPICH processes in one Kubernetes pod. Inter-node scaling, distributed geometry and parallel HDF5 remain open. [Sparse exchange and timings](M3_SPARSE_HALOS.md) · [M2 and M3 roadmap](ROADMAP.md#m3--hybrid-mpi--rayon-36-weeks).

The registered comparisons record actual workflow identities, source and executable hashes, full numerical outputs, rank work, halo bytes, wall time and the available CPU affinity. Strong scaling holds the physical input fixed. Weak scaling increases the number of cells per job or, for direct gravity, keeps pair evaluations per rank nearly constant. The release also compares complete checkpoints across a change of layout. [Case runner](../reana/m3/mpi_case.py) · [REANA comparison and timing reduction](../reana/m3/mpi_reduce.py).

[Measured parallel results](M3_PARALLEL_RESULTS.md).

For a controlled threading comparison, the standalone direct-gravity benchmark runs OpenMP and Rayon against the same compiled force kernel. Both use MPICH to partition targets and gather the results. The reproduction instructions cover the pinned REANA build, input catalogues, CPU placement and individual rank/thread layouts. [Gravity benchmark](../benchmarks/m3/gravity-threading/README.md).
