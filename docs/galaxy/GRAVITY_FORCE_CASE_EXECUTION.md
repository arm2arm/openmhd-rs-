# Actual static gravity comparison execution

The one-case job `reana/galaxy_gravity_force_case.py` connects the compiled
`gravity-force-case` executable to the existing independent GP-2 reference
and exact-error reducer. This is an execution adapter, with no force, unit,
rounding, timestep or acceptance-threshold change. Source preparation is
complete; the new adapter's import prerequisite, 13 metadata controls and
actual scientific comparisons have not run yet.

The intended first inputs are the nine separately source-reviewed ASCII
catalogs retained in
`results/galaxy_g1_static_input_source_proposal_20261122/inputs/`: empty,
one body, axis pair, oblique pair, coincident distinct IDs, three bodies,
storage permutation, species relabel and the actual rounded 1e-6 mass ratio.
Their original bytes, review and failed or incomplete histories stay intact.
This small static slice supplies no gradient, N128, unit-rescaling, long-orbit,
boost/restart, gas coupling or merger acceptance.

Every scientific input receives its own workflow with one requested CPU,
2 GiB and a 300-second wait for each child process. Rust, Rayon and FFI
thread counts are one. The existing pinned REANA image is unchanged. Ready
cases may be submitted concurrently without an aggregate resource cap.

The job verifies all uploaded source/input/part hashes, the assembled
standalone-build binary and an explicit root release before launch. Six
separate prerequisite digests are mandatory: scoped M1 acceptance, original318
and later90 complete output reviews, native186 output review, standalone-build
output review, and this new wrapper's actual metadata output review. A digest
inside the job establishes a byte link; the coordinator must inspect the real
proof, source/compiler/binary identity and terminal workflow independently.
No internal flag claims to authenticate those external facts. Wrapper and
binary-build Git revisions are recorded separately, together with the exact
Rust source-inventory digest; a later Python wrapper is not relabeled as the
original compiled source generation.

There are two distinct supervised commands. The first runs the actual Rust
binary once. After its held leader and log writers close, the unchanged bridge
decodes the complete transcript and projects the exact exported words into
the reference input. The second command runs the independent exact reference
as a fresh Python process on those words. Its complete eight-body packet,
original source buffers and status/closure are retained. The unchanged reducer
then compares force, specific potential, independently summed pair energy,
and unrepaired raw net force/torque using its registered independent scales
and structural-zero policy. All per-particle and global gates must be present;
an unresolved certificate or gate remains nonpassing.

The standard eight-output GET capsule contains original Rust stdout/stderr,
both original stage journals and logs, the reference packet encoded losslessly
as base64, and the full comparison. Partial and unknown command closure remains
explicit and cannot authorize the next stage. A complete evidence body beyond
the GET protocol's limit fails rather than becoming a truncated passing packet.
The output review must check original UUID/version, source/build/input/runtime,
both command chains and raw buffers as well as numerical verdicts.

The current Python metadata runner selects only the new 13-method delta in
`scripts/test_galaxy_gravity_force_case.py`. This is a new immutable cohort,
not a replacement or relabeling of the closed original318/later90 catalogs.
All six reused sources are byte-identical to the actual original318 source
snapshot. Their prior methods and complete output proof remain mandatory;
unchanged catalogs are not rerun to validate this adapter. The metadata
fixtures are explicitly nonphysical and never execute a force kernel or
manufacture a successful physical reference packet.

The root agent authored and inspected this adapter. This is not a new
independently delegated source review. Independent source/manual-math reviews
of the unchanged [driver](GRAVITY_DRIVER_SOURCE_REVIEW.md),
[bridge](GRAVITY_BRIDGE_SOURCE_REVIEW.md), [reference](G1_REFERENCE_SOURCE_REVIEW.md)
and [comparison](GRAVITY_COMPARISON_SOURCE_REVIEW.md) retain their original
scope. Actual new control outputs and same-input scientific output review
are required before any static comparison claim. No module, metadata method,
reference arithmetic, Rust executable or scientific probe was executed locally.
