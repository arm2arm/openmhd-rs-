# Architecture decision records (provisional)

## ADR-001 — Rust 2024, f64

**Proposal:** Rust 2024 with double precision in scientific kernels. Report floating-point nondeterminism across rank/thread reduction orders.

## ADR-002 — MPI + Rayon

**Proposal:** rsmpi for inter-node communication and Rayon for shared-memory parallelism; MPI calls initially on a single thread. Native libraries using OpenMP internally must not oversubscribe cores.

## ADR-003 — Geometry abstraction

**Proposal:** internal mesh geometry interface; benchmark candidate Voronoi implementations for moving topology, periodic domains, degeneracies and distributed halo handling before selecting one.

## ADR-004 — Global timesteps first

**Proposal:** validate synchronized second-order integration before adaptive individual timesteps.

## ADR-005 — Public repository with MIT license

**Decision:** the repository is **public** and includes an [MIT License](../LICENSE) created with the repository, with copyright notice for 2026 Arman. The license must be respected when reusing material; any imported code and numerical dependencies must be checked for license compatibility. Contribution policies remain to be refined.

## ADR-006 — Physics correctness before optimization

**Proposal:** derive exact paper-specific vector-potential update before performance tuning. Reject solver versions whose physics diagnostics fail even if scaling improves.

## ADR-007 — Serial workspace bootstrap and deferred crates

**Decision, 2026-11-04 (issue #3):** accept the delivered four-library/two-application serial workspace. Keep stepping with its solver and CSV writing with its driver until shared APIs warrant extraction. Introduce `parallel` with M3. The separately named `time-integrator`, `parallel` and `output` crates remain explicit architectural targets, as detailed in [ARCHITECTURE.md](ARCHITECTURE.md#delivered-bootstrap-and-deferred-crate-boundaries). The user approved these deferrals for bootstrap closure; they do not certify later solver or HPC functionality.

**Toolchain and dependency policy:** Rust 2024, declared minimum Rust 1.85, tested/pinned Rust 1.85.1 with rustfmt and Clippy in `rust-toolchain.toml`. Physics states and numerical geometry use `f64`. Commit `Cargo.lock`; builds and tests use `--locked`. Current Cargo dependencies are local workspace crates only, so serial builds need no MPI, HDF5 or other numerical FFI library. Before adding an external dependency, record its purpose/license compatibility and update the lockfile intentionally; FFI and parallel runtimes require their own documented build and validation setup. Toolchain changes must update the pin and CI together and rerun the workspace checks.
