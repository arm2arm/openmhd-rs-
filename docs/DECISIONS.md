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
