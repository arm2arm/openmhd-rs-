# Deterministic threading experiment — 2026-11-08

The user explicitly requested trying 24 cores inside the complex tests before
M1 physical acceptance. This authorizes this bounded CPU-threading experiment
ahead of the original milestone order. It does not advance the MPI/3D milestone
or change any physical acceptance threshold.

`vector-potential --threads N` uses one explicitly sized local Rayon pool,
1–24 threads, default 1. An independent cell's Voronoi clipping retains its
original plane order and arithmetic. Cell results are collected by persistent
ID and assembled into the original ordered edge map. Independent face Riemann
solutions, cell curl/limiter/potential calculations and timestep bounds may run
concurrently. Face fluxes still accumulate serially in the original face order,
with the same shared equal-and-opposite exchanges. All floating-point sums
within a cell and all global physical reductions retain their original order.
Failed maps resolve the first error in index order; attempted fallback counts
retain their serial-prefix semantics. Invalid states still reject without floors.
No global Rayon pool or automatic all-core default is introduced.

Rayon 1.10.0 is pinned; all six new dependencies offer MIT OR Apache-2.0 and
support the pinned Rust 1.85.1 compiler (verified from downloaded package
metadata/licenses). Use the MIT alternative, compatible with the project.
Sources: [Rayon pool API](https://docs.rs/rayon/1.10.0/rayon/struct.ThreadPoolBuilder.html)
and the dependency licenses distributed in the Cargo registry packages.

## Prospective correctness and performance checks

* Compare serial with 1/2/4/24-thread geometry, operators, full coupled states,
  budgets, independent divergence diagnostics and counters bit for bit. Cover
  regular/jittered/permuted geometry, fixed/deforming/rigid motion, nonzero mean
  field and all four profiles. Check deterministic first errors and thread limits.
* Compare initial/final snapshots with the pre-threading frozen signal binary
  on a small standing-wave boost fixture, so parity with the modified serial
  path alone is insufficient.
* Run all workspace format/Clippy/tests and Python/M0 checks locally and on REANA.
* Measure identical N64 regular and N128 jittered standing-wave cases to t=.02
  at 1/4/12/24 threads, cap dt=.0002, in sequence in one REANA job. Require
  byte-identical initial/final CSVs, summary and history across thread counts,
  complete positive states and conservative budgets <=1e-10. Record failures.
  Timings are separate from scientific outputs, including mesh, initialization,
  evolution, end-to-end wall time and process CPU seconds. No speedup is assumed.
* Then run the complex N256 regular travelling wave at 24 threads to t=1,
  checkpoints .01/.1/.25/.5/.75, using the original paper profile. Compare its
  common checkpoints with the already-running frozen serial study when available.
  This is one simulation using 24 threads, not 24 concurrent 24-thread cases.

The old workflows remain untouched. Benchmarks share the cluster with them;
timings are observed throughput, not isolated-machine scaling guarantees.
Individual thread pools cap concurrency but do not reserve Kubernetes CPUs
on this REANA 0.9.4 deployment. The test pod requests a 64 GB memory limit.
