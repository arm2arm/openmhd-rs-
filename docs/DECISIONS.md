# Architecture decision records (provisional)

## ADR-001 — Rust 2024, f64

**Proposal:** Rust 2024 with double precision in scientific kernels. Report floating-point nondeterminism across rank/thread reduction orders.

## ADR-002 — MPI + Rayon

**Proposal:** rsmpi for inter-node communication and Rayon for shared-memory parallelism; MPI calls initially on a single thread. Native libraries using OpenMP internally must not oversubscribe cores.

## ADR-003 — Geometry abstraction

**Proposal:** internal mesh geometry interface; benchmark candidate Voronoi implementations for moving topology, periodic domains, degeneracies and distributed halo handling before selecting one.

## ADR-004 — Global timesteps first

**Proposal:** validate synchronized second-order integration before adaptive individual timesteps.

## ADR-005 — Public repository; license undecided

**Decision:** the GitHub repository is **public by owner choice**. A software license has **not yet been selected**. Public visibility does not by itself grant redistribution or modification rights. Compare Apache-2.0, MIT and GPL-3.0 alongside dependency requirements; commit an appropriate LICENSE before claiming an open-source software release.

## ADR-006 — Physics correctness before optimization

**Proposal:** derive exact paper-specific vector-potential update before performance tuning. Reject solver versions whose physics diagnostics fail even if scaling improves.
