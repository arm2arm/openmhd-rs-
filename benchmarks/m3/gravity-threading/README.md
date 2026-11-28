# MPI/OpenMP and MPI/Rayon direct-gravity benchmark

The two backends schedule the same compiled C force function on the same MPI
partitions and the same disjoint logical CPUs. This isolates thread scheduling
and MPI gathering on a fixed workload. The scientific gravity crate continues
to use Rust, Rayon and its symmetric pair accumulation.

## Workload and correctness

G is one, boundaries are isolated, and every particle uses the same Plummer
softening. For target i and source j, with d = x_j − x_i and
s² = d·d + ε², the force on i is G m_i m_j d/s³ and its specific potential
contribution is −G m_j/s. Each target visits all other sources in ID order
with compensated summation. It owns one acceleration and specific potential
output. A complete evaluation visits N(N−1) directed interactions. The
production code instead processes N(N−1)/2 unordered pairs, applies both
reactions and also produces diagnostic scales. Wall times from the production
KDK evolutions measure different work.

The analytic two-particle fixture uses masses 2 and 3, separation 3 and
softening 4. At 256 and 2,048 particles, the test reads the actual masses,
positions, reference accelerations and potential energy from the first saved
step of the [published Rust measurements](../../../tests/reference/m3_parallel).
The force and energy criteria are fixed before timing. Every per-particle
acceleration must match within 5×10⁻¹³ of its reference norm, using a lower
normalization bound of 10⁻¹² times the largest acceleration. The relative
total potential-energy error and net-force norm divided by the sum of the
particle force norms must each be at most 5×10⁻¹³. Both analytic specific
potentials are also checked. All layouts and both backends must produce
byte-identical force files for each catalogue.

## Timing protocol

There is one REANA workflow per backend, catalogue and rank/thread layout.
For each scientific size, the single-rank thread sweep is 1, 2, 4, 8 and 16.
Two-rank layouts use 1, 2 and 4 threads, four-rank layouts use 1 and 2,
and the eight-rank layout uses one thread. The two-body control uses 1×1
and 2×2. A separate build workflow records Rust and C compiler versions,
MPICH and the OpenMP runtime linkage. Jobs request one CPU per rank thread.
All ranks occupy one node. Each rank sets a disjoint Linux CPU mask before
starting its team. The executable checks the actual team sizes. The inputs
and the output paths are the same for both scheduling choices.

One force evaluation warms the runtime. There are seven timed samples. Each
sample averages 16 evaluations at N=256 and two at N=2,048. Two-body controls
use one. The **stage time** includes the force calls and MPI gather, and uses
the slowest rank. The **kernel time** records only the force calls, likewise
using the slowest rank. MPI startup, team initialization, catalogue broadcast
and file output are outside both timers. The original timing CSVs preserve
every sample. The code checks the final force bytes against the warm-up after
each sample. Shared-host timings have no required speedup.

## Source entry points

- [The MPI driver and shared force kernel](gravity_kernel.c) and [Rayon dispatcher](src/lib.rs)
- [Pinned build](build.py), [original fixture extraction](fixtures.py) and [single-layout runner](case.py)

## Reproduction

From the repository root, use Python 3.11+ to stage the build in a new folder.
Cargo vendors only the six locked dependencies. The staged build runs formatting,
strict Clippy, the optimized compilation and a check of both runtime libraries.

~~~sh
bench=benchmarks/m3/gravity-threading
cargo vendor --locked --manifest-path "$bench/Cargo.toml" /tmp/gravity-vendor
python3 "$bench/prepare.py" build /tmp/gravity-vendor /tmp/gravity-build
(cd /tmp/gravity-build && reana-client run -w gravity-comparison-build)
~~~

After the build finishes, download its declared outputs, including the build
log, to a fresh directory and record its actual UUID. Pass that directory and
UUID to the case preparer. The registration gives all 48 case keys. Each
ready case uses its own workflow. The analytic controls precede the two larger
catalogues.

~~~sh
python3 "$bench/prepare.py" case n2-openmp-2x2 \
  tests/reference/m3_gravity_threading/registration.json \
  "$acquired_build" "$build_uuid" /tmp/gravity-pair-control
(cd /tmp/gravity-pair-control && reana-client run -w gravity-pair-control)
~~~

The independent [output replay](report.py) takes the packed service records,
the registration and the original M3 evidence directory. It verifies the
scientific files, placements, reference origins and resource declarations
before writing the timing table and figure.
