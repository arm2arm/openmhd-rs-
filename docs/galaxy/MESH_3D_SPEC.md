# 3D moving-Voronoi geometry and operator contract

Design/source review: 2026-11-22. Status: **proposed, unimplemented and
unexecuted**. This is the geometry worker's implementation contract for the
[galaxy-merger goal](../GALAXY_MERGER_PLAN.md), not independent acceptance of a
new numerical method. No Rust, Cargo, benchmark, script or M1 evidence file was
changed, and no test, geometry probe or evolution was run for this document.
Only reading, downloads, PDF extraction/rendering and document integrity checks
were performed locally. Sources and archive hashes are recorded in
[mesh_3d_sources.json](mesh_3d_sources.json).

The frozen M1 scientific source is `2bdcea0d28340e7429e10053a641f92d51fcc696`.
Its historical matrix passes and its [separate AI source review](../M1_FINAL_AI_REVIEW.md)
conditionally approves the named iterative, screened, quadratic, pressure-blended,
smooth-extrema candidate. Fresh physical acceptance remains pending under the
[final acceptance plan](../M1_FINAL_ACCEPTANCE_PLAN.md). The result, if accepted,
is single-process periodic **2.5D fixed/rigid** MHD. It supplies neither deforming
mesh nor full-3D physical acceptance. Coupled 3D implementation starts only after
that acceptance; this design work does not wait for the long campaign.

## 1. Decisions and publication boundary

Use `f64`, physical non-expanding Cartesian coordinates, globally synchronized
steps and persistent generators. All internal code units derive from the
coordinator's single SI-based `UnitSystem`, with `mu0_code=1`; the cooling
interface has an explicit cgs adapter, not a second independent unit convention.
Dimensionless geometry/MHD fixtures record their unit mapping separately. First implement
an independent small clipped-polyhedron oracle and checked static 3D geometry.
Keep the current 2D APIs and arithmetic intact. Evaluate `meshless_voronoi`
behind an optional adapter only after the oracle fixtures pass; do not add the
dependency as part of this task. Generator insertion/removal, MPI, local steps,
mesh refinement, nonideal MHD and cosmology are later contracts.

Labels below distinguish **P26** (verified 2026 publication), **P09** (verified
older geometry publication), **D** (derivation here), **E** (our proposed
engineering policy), and **U** (an unresolved or deliberately deferred item).
Everything without a publication label is E. Published equations do not supply
our ID layout, solver tolerances, boundary implementations or acceptance bounds.

| Verified source anchor | What it establishes for this contract |
| --- | --- |
| [P26 §4.1, p.8](https://arxiv.org/html/2609.35989v1#S4.SS1) | Conserved fluid integrals and generator coordinates; A is located at the geometric cell centroid. |
| [P26 §4.2.1, pp.8–9, Eqs.51–61](https://arxiv.org/html/2609.35989v1#S4.SS2.SSS1) | Free-intercept neighbour fit, face-area weights, full curl; separate raw and limited derivatives. |
| [P26 §4.2.2, pp.9–10, Eqs.62–66](https://arxiv.org/html/2609.35989v1#S4.SS2.SSS2) | Optional ten-coefficient quadratic fit on neighbours and their neighbours, inverse-distance weights and symmetric Hessians. |
| [P26 §4.3, pp.10–12, Eq.68](https://arxiv.org/html/2609.35989v1#S4.SS3) | Adaptive tricubic auxiliary velocity with shared corner jets and C1 continuity. |
| [P26 §§4.4–4.5, pp.12–13, Eqs.69–76](https://arxiv.org/html/2609.35989v1#S4.SS4) | Face-state induction, distortion, upwind A transport, cleaning and separate mean B. |
| [P26 §5.1, pp.14–16, steps i–xvii, Eqs.80–92](https://arxiv.org/html/2609.35989v1#S5.SS1) | Old/new geometry, endpoint reconstruction, measured centroid-motion correction, frozen second-stage cleaning source. |
| [P09 §3.3, p.17, Eqs.32–34](https://arxiv.org/pdf/0901.4107) | Normal speed of a Voronoi face from generator velocities and face centroid; volume derivative. |

Both complete PDFs were accessible. P26's downloaded SHA256 matches the M0
source map; key operator/stage pages and P09 p.17 were rendered and inspected.
There is **no full-text access gap for these anchors**. The paper does not
specify our dependency adapter, full degeneracy policy or nonperiodic A/gauge
boundary algorithm. Those cannot be inferred as AREPO algorithms. The existing
[M0 discrepancy register](../PAPER_IMPLEMENTATION_SPEC.md#discrepancies-and-implementation-decisions),
including the Alfvén-potential inconsistency, remains in force. This review
imports no AREPO source and verifies no unpublished coefficients.

## 2. Exact identity and coordinate contracts

### 2.1 Types, ownership and epochs

Proposed distinct types, never interchangeable integer aliases:

```rust
struct EntityId { namespace: u64, counter: u64 } // persistent 128-bit payload
struct CellId(EntityId);           // distinct checked real-gas-cell identity
struct ParticleId(EntityId);       // distinct checked collisionless identity
struct EventId(EntityId);          // distinct checked source/event identity
struct LocalCell(u32);             // index into this immutable geometry only
struct GeometryEpoch(u64);         // checked monotone increment per rebuild
struct BoundaryId(u32);            // named physical geometric patch
struct Image([i64; 3]);            // checked integer arithmetic
struct LiftedPoint { wrapped: [f64; 3], winding: Image }
enum FaceKey {
    Interior { lo: CellId, hi: CellId, hi_image: Image },
    Boundary { cell: CellId, patch: BoundaryId },
}
struct FaceRef { epoch: GeometryEpoch, index: u32 }
```

`EntityId` serializes as 32 hexadecimal digits, namespace first then counter,
with 16 zero-padded digits for each u64. Dataset namespaces and the serial
overflow-checked monotone allocator are checkpointed; IDs are never recycled.
The checked wrappers preserve the real entity's kind; an image/ghost has only
its owner's ID plus an image/halo role, never a newly allocated EntityId.
Sort IDs lexicographically by namespace/counter for deterministic local order.
Future MPI allocation uses a separately specified disjoint ID allocator, never
a rank/local index pair whose meaning changes on migration. A gas-cell ID is
not implicitly a newly spawned star ID; transfer uses its recorded EventId.
These shared identity decisions come from coordinator integration on 2026-11-22.
A face has a
canonical key and an epoch-local index, **not a persistent material identity**.
Topology birth/death invalidates indices. Hashes accelerate lookup but never
replace full-key equality. Report owner rank separately from physical identity.

`Geometry3` is immutable and contains a sorted `CellId -> LocalCell` map, cells,
canonical faces, incidence CSR arrays, domain metadata, quality report, source
backend/version/features and epoch. `ValidatedGeometry3` can be constructed
only by the validator; operators/flux plans borrow it. A cache key includes
epoch, complete coordinate/domain/ID digest, stencil policy and operator version.
A new shape invalidates fits, curl/transpose plans, projection diagonals,
preconditioners and boundary samples. Rigid-translation reuse needs an explicit
metric-equivalence certificate; equal cell counts are insufficient.

### 2.2 Wrapped, lifted and cell-local coordinates

First supported domains are orthorhombic `anchor a`, positive finite lengths
`L`, either all-periodic or all-bounded. Per-axis mixed periodicity is represented
in the domain type but returns `UnsupportedBoundaryMix` in the first backend.
For a periodic generator, `x_i` lies in the half-open box `[a,a+L)` and its
trajectory lift is `r_i=x_i+L*k_i`. Advance the lift, then wrap; never infer a
trajectory from a minimum-image difference. Store the cell centroid as the
small offset `dc_i=c_i-r_i`, and vertices/face centroids in a local chart. Avoid
subtracting enormous reconstructed unwrapped positions after many windings.

For a face as seen from cell i, the neighbouring wrapped image is `x_j+L*s`.
Its **trajectory-image** label is `m=s+k_i-k_j`, so the same neighbour in i's
lift is `r_j+L*m`; reverse incidence uses `-m`. This distinguishes a true
neighbour-image change from a generator merely crossing a box seam. Integer
conversion, addition and subtraction are checked for overflow. Cell j's
centroid in i's chart is the corresponding generator image plus `dc_j`.
Stored stencil samples are `(CellId, Image)`, not `CellId` alone. Two images of
one cell are distinct observations even though a periodic field has equal
stored values at them. Path sums compose image labels before deduplication.

Canonicalize an interior face by choosing the lexicographically smaller of
`(i,j,m)` and `(j,i,-m)`. For a self-image face `i=j`, select the sign whose
first nonzero image component is positive. The zero self-image is invalid.
The canonical left chart is attached to the selected left generator. This
permits one-cell/tiny periodic fixtures instead of inheriting 2D's current
no-self-face restriction. Reject unsupported cases explicitly until implemented.

## 3. Geometry records and oriented shared faces

Each `CellGeometry3` stores ID, generator, volume `V>0`, centroid offset,
oriented face incidences, bounding radius, minimum generator-face distance,
surface area, aspect/centroid-offset measures and diagnostic second moments.
Physical gas state lives separately, keyed by persistent ID: integrated
`Q=(mass,px,py,pz,total_energy)`, point-sampled periodic A, cleaning phi and
any explicitly named gauge offset. Geometry does not own or reset energy.

Each `SharedFace3` stores:

- Full `FaceKey`, left owner and optional right owner/image, geometric boundary
  tag when right is absent, positive area and unit normal **from left to right**
  (outward from left for a physical boundary).
- Centroid offset from the left generator, plane offset, an ordered convex
  polygon loop in that chart, and a deterministic fan triangulation. Viewed
  from outside the left cell, the loop is counterclockwise, equivalently each
  triangle's cross product points along the stored outward normal.
- Area-weighted first and second moments, quality flags and source-side
  comparison residuals. Vertices have epoch-local identity; a defining-plane
  set can label them for comparison, but is not a promise of identity through
  a degenerate event.

An interior face has **one record, two incidences**: left `+1`, right `-1`.
Right incidence translates the polygon/centroid into the right cell's chart
and reverses the normal and loop. Self-image faces still have two incidences
on the same cell, in different charts. A boundary face has one incidence and
one boundary ledger entry. Never recompute a second numerical flux from the
other side. On future MPI boundaries, the canonical owner computes one flux
and transmits the same bit pattern and key to the partner; missing/duplicate
exchange acknowledgements reject the stage. MPI implementation is deferred.

For an interior face let `d=r_R+L*m-r_L`, `n=d/|d|` and
`f=face centroid` in the left chart. Require positive projected separation,
`d·(f-(r_L+r_R+L*m)/2)=0` within normalized geometry tolerance, and all face
vertices on that same bisector. Polygon winding and `n·d>0` decide orientation;
backend normal documentation alone never does. Shared areas/centroids from
independent constructions must agree before choosing one canonical record.
Do not average incompatible polygons or silently discard a small positive face.
Only certified zero-area contacts are omitted as non-faces.

### 3.1 Robust volumes and centroids

Work in coordinates relative to the generator, scaled by a positive local
length, and use compensated sums in canonical face/triangle order. For an
outward triangle `(a,b,c)` and interior pivot `o` (the generator for a valid
unweighted Voronoi cell), the signed tetrahedron volume and centroid are

```text
v_t = det(a-o, b-o, c-o)/6
c_t = (o+a+b+c)/4
V = sum_t v_t;       c_cell = sum_t(v_t*c_t)/V.
```

An outward-oriented face fan gives positive tetrahedra; materially negative
tetrahedra indicate a winding/convexity/pivot defect. Do not take absolute
values to conceal cancellation. Compute face area/centroid from oriented
triangle moments, with a fan centre inside the convex planar polygon. Store
central second moments by analytic tetrahedron integration (or exact-degree
quadrature); they are needed for diagnostics and future cell-average fits.

Independently check these divergence-theorem identities, with local centroid
origin `y=f-c_cell` and outward normals:

```text
sum_f A_f*n_f = 0
sum_f A_f*y_f[a]*n_f[b] = V*delta[a,b]
V = (1/3)*sum_f A_f*(f-o)·n_f
sum_f A_f*(y_f·n_f)*y_f = 0.       // div(y_a*y)=4*y_a in 3D
```

Face-centroid quadrature is exact for the last identity because `y·n` is
constant on each planar face. Check centroid containment in every face plane,
edge-manifold incidence and convexity as well as global volume. Small positive
cells are flagged by dimensionless quality, not deleted or floored. Empty,
nonfinite, inverted, open or multiply connected polyhedra are errors.

### 3.2 Boundary semantics

Periodic geometry covers the torus exactly once; boundary crossings are
interior image exchanges, with no external fluid source. Cell polyhedra may
cross the displayed box. Clipping every cell to the displayed primary box
would incorrectly truncate seam cells. Background `B_mean` is separate from
periodic a; adding a nonperiodic linear A across a seam is prohibited.

Bounded geometry initially clips to a **fixed closed cuboid**, six unique
patch IDs and outward planes. Generators stay strictly inside; a generator
leaving the domain rejects the trial. A clipping plane is geometry, not a
reflecting gas boundary. An explicit boundary provider supplies face states
and signed mass/momentum/energy/induction ledgers. Stationary impermeable
hydrodynamic walls use zero normal mass flux, wall pressure force and its
energy-work term; outflow/inflow require specified external states and flux
accounting. Gas conservation then includes those ledgers. Moving walls and
arbitrary curved/nonconvex domains are unsupported initially.

**U: bounded vector-potential MHD is not authorized by the periodic P26 map.**
A conducting wall must specify compatible B-normal, tangential electric
field, gauge and phi conditions; copying gas ghost primitives does not define
these. Do not implement or advertise general outflow A/cleaning boundaries
without a separate derivation and REANA tests. Periodic gas/MHD geometry remains
a useful verification domain, but it cannot stand in for the owner's merger
boundary requirement. **The merger demonstration requires independently
accepted bounded/nonperiodic gas/MHD boundary physics as well as isolated
gravity.** Do not silently combine a periodic gas mesh with isolated gravity
for that demonstration. Bounded geometry/hydro can be built and reviewed
before this magnetic boundary extension; the missing extension remains a
blocking dependency for the merger, rather than an assumed ambient-box remedy.

## 4. Candidate dependency audit: meshless_voronoi 0.7.2

Reviewed the published crate archive, normalized/original manifests and source,
not merely the latest documentation summary. Archive SHA256 is
`5fdae7b98518f55142d22a609d634942e99ef7a7a493eb0534bdc8e8c4ebb794`;
`.cargo_vcs_info.json` pins upstream
`3120dc9e75f12e1a1dc73bfde3797fbdce2459ed`. Exact source URLs and per-file hashes
are in the JSON manifest. No build, feature resolution or performance claim was
tested here. Upstream's timing table is not a project benchmark.

### 4.1 Features and licensing

[Published Cargo.toml](https://docs.rs/crate/meshless_voronoi/0.7.2/source/Cargo.toml)
declares Rust edition 2021, defaults `ibig,rayon`; backend features are mutually
exclusive, with a [compile-time conflict check](https://docs.rs/crate/meshless_voronoi/0.7.2/source/src/lib.rs).
Disabling defaults requires explicitly selecting one backend. The metadata
license string is the broad `MIT OR Apache-2.0 OR LGPL-3.0-only OR LGPL-3.0+`;
the upstream README conditions the permissive option on the selected backend.
That string is not permission to redistribute LGPL dependencies as MIT.

| Feature | Actual backend path checked in published manifests | License/feature consequence |
| --- | --- | --- |
| `ibig` | `ibig ^0.3`, defaults **off**; inspected 0.3.6 | MIT OR Apache-2.0. Only mandatory `cfg-if` and `static_assertions` beneath this backend; its optional rand/serde/num-traits defaults are not activated by meshless_voronoi. |
| `dashu` | `dashu ^0.4`, defaults **on**; inspected 0.4.4 | MIT OR Apache-2.0 metadata; pulls dashu-base/int/float/ratio/macros and rustversion, plus default std/num-order paths, even though only Integer is wanted. This is broader than an integer-only dashu-int dependency. |
| `num_bigint` | `num-bigint ^0.4`, defaults on; inspected 0.4.8 | MIT OR Apache-2.0; std enables num-integer/num-traits std. No GMP path in this backend's manifest. |
| `malachite` | `malachite-base ^0.4` AND `malachite-nz ^0.4`; inspected 0.4.22 each | Both declare LGPL-3.0-only. These versions' normal enabled paths are Rust; nz's optional rug/pyo3/test paths are not enabled by this meshless feature. Pure Rust does not imply a permissive license. |
| `rug` | `rug ^1.24`, defaults **off**, `integer` on; inspected 1.24.1 | LGPL-3.0+; integer enables gmp-mpfr-sys with its defaults off. Inspected gmp-mpfr-sys 1.6.8 has LGPL-3.0+ bindings and bundled GMP; MPFR/MPC are not enabled by this integer-only route. C/native build requirements remain. |
| `rayon` | optional `rayon ^1`, on by default | Parallel cell construction. Use the project pool, or disable it; never multiply an outer simulation pool by an independent unbounded pool. |
| `hdf5` | optional `hdf5 ^0.8`, off by default | Adds a native HDF5 discovery/link/license path. Geometry evaluation needs neither this exporter nor that dependency; retain project-owned output. |

Primary backend manifests: [ibig 0.3.6](https://docs.rs/crate/ibig/0.3.6/source/Cargo.toml),
[dashu 0.4.4](https://docs.rs/crate/dashu/0.4.4/source/Cargo.toml),
[num-bigint 0.4.8](https://docs.rs/crate/num-bigint/0.4.8/source/Cargo.toml),
[malachite-base 0.4.22](https://docs.rs/crate/malachite-base/0.4.22/source/Cargo.toml),
[malachite-nz 0.4.22](https://docs.rs/crate/malachite-nz/0.4.22/source/Cargo.toml),
[rug 1.24.1](https://docs.rs/crate/rug/1.24.1/source/Cargo.toml),
[gmp-mpfr-sys 1.6.8](https://docs.rs/crate/gmp-mpfr-sys/1.6.8/source/Cargo.toml).
Their archive checksums and declared direct feature edges are retained in JSON.
These are inspected versions satisfying the declared ranges, **not a computed
Cargo resolution**. In particular `rug ^1.24` can resolve a later 1.x release.
The crate supplies no Cargo.lock. Adoption requires a locked complete normal,
build and target-specific dependency inventory, actual license texts and
feature-unification check. No full-transitive SPDX closure is claimed here.

Mandatory non-backend dependencies are ahash ^0.8, document-features ^0.2,
glam ^0.27, num_enum ^0.7.2 (defaults off) and rstar ^0.12. Their actual resolved
versions/licenses and transitives must enter that adoption inventory. The 0.7.2
archive **and pinned upstream Git tree contain no LICENSE/COPYING file**;
README and Cargo metadata give the grant, but notices/text packaging must be
resolved before redistribution. The inspected ibig and num-bigint archives do
include MIT/Apache texts; rug/sys include LGPL/GPL texts. Do not import code
from this crate into the independent oracle.

Recommended future experiment declaration, never added in this task:

```toml
meshless_voronoi = { version = "=0.7.2", default-features = false, features = ["ibig"] }
```

This isolates a permissive backend and serial geometry first. `--all-features`
on a direct dependency would enable incompatible backends; the project must
expose at most its selected adapter feature, not forward every backend as a
simultaneous all-feature set. Later Rayon is an explicit single-pool experiment.
Neither malachite nor rug is recommended for this MIT project's first slice.

### 4.2 Geometry, connectivity and hazards

[Voronoi::build](https://docs.rs/meshless_voronoi/0.7.2/meshless_voronoi/struct.Voronoi.html)
takes DVec3 generators, anchor, width, dimensionality and **one periodic bool**;
it is a snapshot rebuild, not incremental mesh motion or MPI distribution.
`build_partial` constructs masked cells; it does not establish a complete
distributed halo or reciprocal ownership contract. Rectangular bounds and
periodic copies are supported. The periodic R-tree iterator enumerates the
3x3x3 neighbouring box shifts.

The compact representation exposes cell volume/centroid and face area,
centroid, left/right generator indices, normal and optional right-image
translation. It lacks ordered polygons, common edge/vertex topology, central
moments, face velocities, swept volumes, stage correspondence, persistent
global IDs and physical boundary conditions. `VoronoiIntegrator::build(...)
.with_faces()` exposes per-cell `ConvexCell` vertices and face-vertex lists,
neighbour/shift and clipping plane; custom integrals are available. Use this
route for audited polygon extraction; do not assert the compact API makes
polygon geometry impossible. Local vertices are not a globally shared complex.
[ConvexCell API](https://docs.rs/meshless_voronoi/0.7.2/meshless_voronoi/struct.ConvexCell.html).

Three source-level adapter requirements are mandatory:

1. [voronoi_cell.rs](https://docs.rs/crate/meshless_voronoi/0.7.2/source/src/voronoi/voronoi_cell.rs)
   deduplicates ordinary internal faces, but emits periodic faces per side;
   `Voronoi::finalize` links a periodic record only to its left cell.
   `neighbour_ids()` explicitly skips periodic faces. Traverse raw faces with
   right/image metadata, pair `(i,j,s)` with `(j,i,-s)` after chart transforms,
   verify both, then create this project's one shared record.
2. [convex_cell.rs](https://docs.rs/crate/meshless_voronoi/0.7.2/source/src/voronoi/convex_cell.rs)
   computes `n=(left-right_image)/distance`, retains positive halfspaces and
   describes clipping normals as inward.
   [voronoi_face.rs](https://docs.rs/crate/meshless_voronoi/0.7.2/source/src/voronoi/voronoi_face.rs)
   copies that normal, while its public `normal()` comment says away from the
   left generator. `FaceIntegrator::init` retains the same left ID. **Static
   source inspection therefore finds a sign discrepancy with the API comment.**
   Derive outward normals from generator separation/boundary planes, test the
   sign of returned normals and reverse loops as necessary. A dedicated
   two-generator REANA fixture must confirm this before coupling. No runtime
   reproduction or upstream bug report was made in this task.
3. [geometry.rs](https://docs.rs/crate/meshless_voronoi/0.7.2/source/src/geometry.rs)
   has integer in-sphere fallback. Boundary coordinates are rescaled into a
   mantissa-based integer representation; exactness concerns that represented
   predicate, not exact f64 volumes/intersections. Coincident generators assert;
   triple-plane intersection and several topology invariants can panic.
   Prevalidate domain/duplicates/nonfinite values, isolate backend failure as a
   geometry error, and never continue with partial geometry. An unwind guard
   does not recover abort/OOM or prove memory safety of backend unsafe paths.

[R-tree ordering](https://docs.rs/crate/meshless_voronoi/0.7.2/source/src/rtree_nn.rs)
compares equal-distance heap entries by distance, without an ID tie-break.
Indexed Rayon collection alone does not prove permutation, thread or
cross-platform determinism. Exact regular/co-spherical seeds, nearly duplicate
seeds, slivers and clustered/tiny cells need explicit fixtures. Keep a
canonical input order and canonical output keys/loops; test geometry invariants
and toleranced equality after permutation, rather than asserting bitwise
identity from upstream marketing. No random jitter may silently resolve a
degeneracy. Record a deliberate perturbation as a different input if ever used.

### 4.3 Independent all-pairs oracle

Write a small Rust `HalfSpaceOracle3` independently, with no candidate source
copied and no spatial search or safety-radius pruning. In generator-relative
coordinates `y`, clip by every plane

```text
d_ijs · y <= |d_ijs|^2/2,  d_ijs = x_j+L*s-x_i.
```

For periodic cells start from `[-Lx/2,Lx/2] × ...` about the generator, whose
planes are its nearest self images. Include all other generators' shifts
`s in {-1,0,1}^3` relative to wrapped coordinates; convert s to the trajectory
image m when forming persistent keys. These are sufficient for an
orthorhombic torus because the self-image box bounds the possible nearest
image in each coordinate; this argument does not cover skew/shearing boxes.
For bounded cells start from the physical cuboid and clip every other real
generator. Tag every clipping plane with full neighbour/image or boundary ID.

Clip each existing polygon, create the cap from intersection points, order
it in a deterministic in-plane basis and remove only certified duplicate or
collinear vertices. Rebuild adjacency and integrate moments. Use normalized
predicate error bounds; if a side/intersection cannot be resolved, return a
diagnostic `AmbiguousPredicate` with planes/cell/scale. Analytic rational
Cartesian fixtures provide a stronger reference than two f64 backends agreeing.
This oracle is an independent algorithmic comparator, **not an exact-arithmetic
proof for arbitrary degeneracies**. Exact/near-degenerate expected-rejection
fixtures must distinguish unsupported ambiguity from a wrong accepted mesh.

Use it for <=512 cells initially, with a measured cost report before enlarging
the bound. The accelerated backend must match accepted oracle geometry,
analytic fixtures and topology away from zero-area contacts. Near a certified
zero-area event compare physical faces/volume, not arbitrary triangulation
diagonals. Common mistakes in both implementations remain possible; global
closure, analytic cases and local plane identities are independent safeguards.

## 5. Full-3D derivative, curl and divergence contracts

Let `G[q][a]=partial_a q` for a scalar, and `J_A[k][a]=partial_a A_k` for a
vector; component is the first index, coordinate the second. Never infer a
transpose from a 2D type alias. A centre stencil uses neighbours' **geometric
centroids in consistent image charts**, not generator positions. A face stencil
uses face centroids in the receiving cell's chart. Each has separate metadata.

### 5.1 Conditioned linear and quadratic fits

The primary linear P26 fit minimizes `sum_j A_ij*(q_j-X_j·b)^2`, with
`X=[1,dx,dy,dz]` and a free intercept, excluding the central value as an
observation. Face-centre fits use the same free-intercept construction with
face-area weights. For the optional quadratic path, use the P26 basis

```text
X=[1,x,y,z,x²/2,y²/2,z²/2,xy,xz,yz].
```

Use one- and two-ring adjacency with composed image labels, unique by full
`(ID,image)` and excluding only `(i,zero)`; `w=1/|d|` is the quadratic objective
weight, so the design row is multiplied by `sqrt(w)`. This extends the current
selected quadratic path; it does not mean P26 uses that path for every field.
Samples with zero displacement are invalid. Face advection retains its own
linear face-centre stencil. Boundary ghost observations require a boundary
contract and are tagged as such, never mistaken for physical cells.

Scale displacements by `h=cbrt(V)`, normalize columns and factor the weighted
rectangular design with column-pivoted Householder QR; use a rank-revealing SVD
as the prospective small-fixture diagnostic. Do not solve normal equations
for derivative coefficients. Store the permutation, coefficient weights,
rank, residual, `kappa_1(R)` estimate, maximum coefficient amplification,
sample count, h and image labels. Subtract an actual sample's scalar baseline
before applying derivative rows; constants must annihilate without cancellation
of a large arbitrary gauge offset. Return intercept offsets separately.

Proposed rank rule after column normalization: a pivot below `1e-10` times
the largest QR pivot, or `kappa_1(R)>1e8`, rejects the stencil. These extend
the **engineering** current quadratic rejection policy; they are not a spectral
condition number or a published tolerance. Require at least 4/10 independent
rows and overdetermination for accepted production fits. A Cartesian one-ring
stencil can be rank deficient for a free-intercept quadratic: sample count is
not rank. A deterministic next-ring expansion (sorted full keys, maximum
three rings and 256 samples initially) may rescue rank/conditioning; record
it and repeat convergence tests. Exhaustion rejects the geometry/trial.
Never replace a failed derivative with zero, a through-centre fit or a lower
order stencil without a separately named reviewed policy.

For fluid finite volumes, cell averages equal centroid point values only
through affine order. Initial reconstruction remains piecewise linear around
the **stored cell average** for density, pressure, velocity and B, with its
separate limiter. Do not apply the point-sampled quadratic A fit to Q/V as
though it were an exact quadratic cell-average fit. A later average-aware
quadratic fluid fit must incorporate the stored second moments.

### 5.2 Magnetic recovery and diagnostics

Raw, unlimited curl (P26 Eq.61) is

```text
B = B_mean + (J_A[z][y]-J_A[y][z],
              J_A[x][z]-J_A[z][x],
              J_A[y][x]-J_A[x][y]).
div_A = J_A[x][x]+J_A[y][y]+J_A[z][z].
```

Retain symmetric Hessians `H_A[k][a][b]` for the quadratic path. Derive
`J_B[k][a]` by differentiating the above curl, using those *same* Hessians
(P26 Eq.66). Its trace cancels algebraically; label it `div_B_same_fit`.
This cancellation is neither a diagnostic on neighbouring recovered B nor a
finite-volume identity. Limited B gradients lose this cancellation in general.

Every output reports all of the following independently:

1. `div_B_cell_ls`: trace of a separate unlimited linear LS fit to recovered
   neighbouring B, including z derivatives.
2. `div_B_face_mean`: `(1/V_i) sum_f sign_if*A_f*n_f·((B_L+B_R)/2)` with a
   single shared value and explicit physical boundary states.
3. `div_B_face_limited`: independently limited linear B reconstructions to
   faces, averaged once into a shared normal value, then the same face sum.
4. `div_B_same_fit` if available, `div_A`, phi norms and projection residuals;
   none replaces items 1–3.

Report signed volume mean, volume-weighted L1/RMS, absolute maximum and
`r_eff*abs(div_B)/(|B|+1e-12*B_scale)` with
`r_eff=(3V/(4pi))^(1/3)` and a recorded fixed initial `B_scale>0`. Also retain
dimensional values and weak-field locations. Global cancellation of the shared
face diagnostic follows incidence pairing, not local divergence-free fields.
Do not substitute its global sum for cellwise error. Report
`sum V*B/sum V-B_mean` explicitly: a general LS curl is not guaranteed to
preserve the prescribed discrete volume mean exactly on a changed geometry.

Limit raw A gradients only in a separate face-advection copy. Keep the current
neighbour-extrema and smooth-extrema policies named separately; curvature
confirmation in 3D uses the same two-sided displacement residuals and needs
new discontinuity/extremum tests. Admission of an extremum is not a smoothness
proof. All raw curl/cleaning derivatives remain unlimited. Phi controls
`div(A)`, not a direct B-divergence cleaning equation.

### 5.3 Auxiliary velocity

Provide `sample(point, stage) -> {u:[f64;3], jacobian:[[f64;3];3]}` with the
same component/coordinate convention and analytic polynomial derivatives.
The first 3D implementation is a **uniform periodic tensor-Hermite grid**,
64 coefficients per velocity component per cube, eight corner jets
`[u,ux,uy,uz,uxy,uxz,uyz,uxyz]`, shared across adjacent cubes. Use the current
continuous cubic deposition idea generalized to xyz, volume weighting and a
persistent translated auxiliary origin; this is an engineering extension of
M1, not P26's adaptive deposition algorithm. Specify empty-bin handling and
4/2/1 root fallback as configuration; report root changes per stage. Test
C1 seam continuity and polynomial derivatives before any evolution. Adaptive
tricubic refinement with inherited boundary jets (P26 §4.3) is a later slice.

## 6. Motion, topology and geometric conservation

### 6.1 First supported motion plan

Use `LinearMotion3`: generator velocities fixed over one attempted synchronized
step, lifted paths `r_i(t)=r_i(0)+t*wtilde_i`, no creation/removal and no
physical-domain change. Fixed/rigid and externally prescribed deformation are
separate case names. A fluid-following proposal may choose the initial gas
velocity for wtilde, but a second-order trajectory/regularization policy and
its error study are prerequisites to calling it a validated Lagrangian path.
Regularization is a recorded velocity component, not an unlogged point shift.

Rebuild complete geometry at every stage position; validate it before deriving
primitives, auxiliary bins, fits or fluxes. Compare old/new face keys and record
births/deaths, minimum areas, neighbour/ring changes and centroid displacement.
Persistent Q/A/phi are matched by **cell ID**, never by face or vector position.
A neighbour change among existing cells is not insertion/deletion and does
not by itself authorize an overlap remap of Q or interpolation of A.

For actual face position f in the common image chart, use (P09 Eqs.32–33)

```text
d = r_R_image-r_L; m=(r_L+r_R_image)/2
w_f = (wtilde_L+wtilde_R)/2
      + d * (((wtilde_L-wtilde_R)·(f-m))/(d·d)).
```

Its **normal component** is the bisector's local speed. This vector is a
convenient face frame, not generally the time derivative of the polygon
centroid's full tangential position. Do not finite-difference centroids of
unmatched face records. For fixed physical walls w_normal is zero. Compute
`W_i=sum sign*A_f*(w_f·n_f)` and compare it with an independent finite-difference
of rebuilt volume; P09 Eq.34 is the instantaneous volume identity.

The A sampling point moves at the **cell centroid** speed, not wtilde and not
w_f. Measure its full lifted displacement
`delta_c=dt*wtilde_i+dc_i(end)-dc_i(start)`. If the two-stage endpoint
advection uses wtilde first, use `what=2*delta_c/dt-wtilde` second (P26 Eq.89).
All three components and multi-box crossings are required. This geometric
relation alone does not make the rest of the M1 integrator deforming-safe.

### 6.2 Discrete GCL and a concrete reference policy

Required accepted behavior: constant fluid states remain constant while cells
deform; gas integrals follow actual geometric volume, and total conserved
integrals change only by accounted sources/boundaries. Keep geometric endpoint
volumes authoritative. Merely evolving a second RK volume variable, then using
it in place of the tessellated volume, hides a metric mismatch.

The endpoint trapezoid has an explicit defect

```text
R_i = V1_i - V0_i - dt/2*(W0_i+W1_i).
```

Across smooth topology this is generally truncation error, not roundoff;
topology events may change its order. Reporting finite R without bounding it
is insufficient. The existing Heun path only rejects a nonfinite GCL error.
First implement the following **new proposed engineering reference**,
`gcl-shared-sweep-v1`, for prescribed-motion gas/MHD development:

1. On the union of start/end canonical faces set absent stage area/flux to
   zero. Let B be the cell-face incidence matrix with +1 at left, -1 at right;
   physical boundary sweeps are prescribed separately (zero for the fixed
   cuboid). Let `S_H[f]=dt/2*(A0*w_n0+A1*w_n1)`.
2. Solve `B*delta_S=V1-V0-B*S_H` by the minimum weighted-norm graph solve
   `delta_S=W*B^T*lambda`, `B*W*B^T*lambda=R`, one pinned multiplier per connected
   component, with positive edge weights `W_f=(A0+A1)/2` normalized by a fixed
   area scale. Self loops have zero incidence and zero correction. Require
   component volume compatibility; a non-roundoff global volume defect is a
   geometry failure, never a silently subtracted mean. New correction edges
   with zero area at both endpoints are not invented.
3. Correct the **one shared integrated ALE exchange** by
   `E_Q[f] <- E_Q_H[f] - Ubar_f*delta_S[f]`, then apply -E to left and +E to
   right. Here `Ubar_f` is the arithmetic mean of the two owners' conserved
   densities at both endpoints (four samples); target cells exist even if
   the face is absent at one endpoint. For constant U this makes `Q1=U*V1`
   to the graph-solve tolerance. Correct the diagnostic induction exchange
   with `-Bbar_f*delta_S` using the same averaging rule. These are ledgered
   geometric transport terms, not an energy floor or independent cell repair.
4. The Euler predictor also uses a GCL correction, replacing S_H with
   `dt*A0*w_n0` and Ubar with the two old owner values, so its closure sees a
   uniform state on V1. Stage-two face solves then use that predictor's Q/V1.
   The final corrector uses the endpoint trapezoid and its own correction,
   not an accidental second application of the predictor correction.
5. Require small corrections with observed `O(dt^2)` predictor and `O(dt^3)`
   corrector scaling on smooth paths, positive stage/final gas closures and
   the gate table below. Retry from immutable old data on failure. If a face
   appears/disappears entirely inside a step, endpoint sampling may miss its
   physical exchange. Limit motion and substep; require event-bracketing
   fixtures and convergence against finer rebuilds before accepting such
   steps. A passed algebraic GCL solve cannot certify this physical exchange.

This graph correction is D/E, **absent from P26 and current code**. It must get
numerical review and REANA evidence before adoption. It supplies a concrete
small reference path; a space-time swept-face method may replace it only as a
separately named, reviewed choice. At topology events do not claim second
order from an unchanged face list. Monitor both the raw defect and correction;
do not relax thresholds to make a failing motion campaign complete.

## 7. Coupling interfaces and stage obligations

### 7.1 MHD face contract and moving curl

`mhd-core` already accepts a full 3-vector unit normal and full face velocity,
rotates into a face frame, enforces a common normal B at preserved gas
pressure, computes HLLD/HLL/pressure blend and transforms momentum/energy back.
Its `FaceFlux.fluid` is the **ALE** conservative flux per unit area/time;
do not subtract `U*w_n` again. `FaceFlux.induction` is likewise the lab-frame
ALE induction flux after its `-Bn*w_f` transform. Reuse these kernels and
fallback labels, with genuinely oblique 3D covariance fixtures. B is recovered
from A, not evolved as an independently accepted FV state.

Every face request carries geometry epoch, FaceKey, stage time, polygon
centroid, normal, area, w_f, both reconstructed states, frame/gauge metadata,
boundary provider and selected Riemann/limiter configuration. Every response
returns one shared gas exchange, induction target exchange, returned states,
signal speeds, method/fallback counters and source ledger. Deterministic
per-face calculation can be threaded; accumulate sorted results once into
both owners. Corrections must have exactly the same exchange ownership.

For moving geometry, writing `B=B_mean+C(g)*a` gives (D)

```text
dB/dt = C(g)*da/dt + (dC(g)/dt)*a,
dB_target/dt = (d(V*B)/dt - B*dV/dt)/V.
```

The current fixed/rigid projection need not include the geometry derivative
because its metric operator is invariant there. It cannot be copied into
deforming 3D and called complete. Stage volume changes, centroid motion and
changing curl rows all matter; topology switches can make the derivative
nonsmooth.

A concrete proposed extension is **endpoint-increment projection**. For each
predictor/corrector let `a_trial=a0+delta_a_raw`, recover `B0` with C0, build
`M_B_target=V0*B0-B*E_B` from the shared integrated induction target, and set
`B_target=M_B_target/V1`. Use C1 and V1 to solve

```text
(C1^T V1 C1 + kappa*D1)*z
    = C1^T V1 * (B_target-B_mean-C1*a_trial),
D1=diag(C1^T V1 C1),    a_next=a_trial+z.
```

This includes the finite geometry change `C1*a0-C0*a0` without differentiating
topology. The transpose is exactly the stored 3D curl's weighted adjoint;
verify the dot-product identity, including baseline subtraction and repeated
image samples. Keep `kappa=1` initially as the candidate's screened objective,
with its 1e-11 iterative relative target and 1e-9 true-residual check. These
are inherited solver criteria, not physical B error guarantees. Zero diagonal
modes need explicit null-space handling and may not be silently regularized.

For joint-boost tests use one **constant full-3D reference frame** Vref,
transformed by the boost, and target face flux
`F_B_target=FaceFlux.induction+Bn*Vref`, with Bn from the same returned face
state. This is a proposed bulk-frame engineering completion, not P26 Eq.69.
It is distinct from the current xy rigid-generator/z gauge completion. Record
the target, raw curl-rate mismatch and final screened residual separately.
For each accepted geometry report mean-B drift; screening does not force exact
target representation or a magnetic-energy identity. This target and the
increment formulation require a separate source/design review and fixed/rigid
reduction check before moving MHD execution. No equivalence is asserted here.

### 7.2 Required stage sequence

The new named 3D profile must state these operations in executable order:

| Stage | Geometry and physical obligations |
| --- | --- |
| Begin/retry snapshot | Freeze accepted IDs, lifted positions, Q/a/phi, mean B, gauge offset, auxiliary origin, RNG/source ledgers and time. Construct the linear motion plan and dt bound without mutating them. |
| Old stage | Validate g0; build C0/face/primitive fits; recover B and positive primitives from Q/V0 and conserved energy; build raw/limited copies and 3D auxiliary u/gradient; evaluate one old-stage face exchange and raw A/phi rates. |
| Endpoint/predictor | Move generators on the declared lift; rebuild/validate g1 and topology report; build all g1 fits/plans. Apply Euler integrated gas/induction exchanges with predictor GCL correction. Predict A/phi/origin/offset, including the full centroid-path transport convention; perform the C1 endpoint-increment projection. |
| Reevaluate | Recover Q*/V1 and curl(a*) together; reject invalid pressure/density without floors. Refresh primitive/A limits, auxiliary deposits/jets, cleaning sources, face velocities, pressure blend, signal/CFL bounds and endpoint face solves on g1. Use the same frozen generator trajectory; its endpoint normal speeds do not use unrelated freshly selected next-step velocities. |
| Corrector | Form old/endpoint trapezoidal exchanges with one shared correction and endpoint-volume closure. Average raw A/phi rates with the stated centroid correction, then the final endpoint-increment projection. Integrate auxiliary origin and gauge offset with their declared stage rules. |
| Accept | Recover final B/primitives from final Q, a and g1; enforce finite/positive state, GCL, solve and timestep bounds. Record independent divergences, budgets, geometry/condition/topology/correction/retry/fallback counters. Atomically replace accepted state. |

The reevaluated cleaning and auxiliary stages are the M1 engineering family,
**not P26's frozen second-stage source**. A literal paper endpoint profile,
if later implemented, must instead follow Eqs.80–92 and retain its different
predictor semantics under a separate name. Failed trials restore all state,
including geometry epoch/cache handles, origin, gauge offset and ledgers;
attempt counters may advance, accepted counters do not. Timestep halving
rebuilds every dt-dependent object. No partially exchanged face contribution
survives a rejected trial.

### 7.3 Gravity and source interface

Geometry exports `{cell_id, centroid_lift, generator_lift, volume, second_moment,
quality, epoch, unit_system_id}`. Gravity consumes gas mass from the conservative
state and collisionless masses from their own catalog. The initial gas gravity
source is its **volume-centroid monopole**; a distributed-cell quadrature is a
separate future extension, and the generator is not its mass position.
Gravity returns `{entity_id, force, specific_potential, source_epoch,
source_hash, evaluation_time, unit_system_id}` and a signed force/work ledger.
At checked application derive acceleration `force/mass` using the matching
positive target mass and source identity/epoch; a stale mass snapshot requires
an explicit re-evaluation or source-coupling policy. Never reinterpret force
as acceleration or specific potential as potential energy. Source increments to Q are
separate from shared face exchanges. Generator motion, cell-centroid motion
and physical gas velocity remain distinct even if a motion policy relates
them. Match force interpolation and kicks to the gravity worker's contract.

A gravity kick cannot move a mesh cell's geometry in place without a new
motion plan/rebuild. Gas-to-star transfer changes gas mass/momentum/energy
through an explicit source transaction; it does not implicitly delete its
generator. Deletion/remap and A transfer require later adaptation review.
For gravity-on runs report gas/particle/source momentum, force work,
gravitational energy and angular momentum separately. Pairwise gas fluxes
conserve linear momentum/total energy; they do not guarantee exact angular
momentum on noncentral stress/mass exchange. Do not claim the latter from
face antisymmetry.

### 7.4 Why removing the Heun guard is insufficient

The current `Simulation::new` rejects nonrigid Heun motion, but `trial_heun`
also calls `endpoint(..., true)`, reuses metric stencils and assumes unchanged
volumes. Its projection target takes one rigid xy generator velocity and a
special z reference; its mesh, face velocity, fits, auxiliary grid, paths,
radius and divergence normalizations are all intrinsically 2D. Removing one
guard leaves these assumptions active. Required changes are full polyhedra,
fresh stage curl/transpose/projection plans, authoritative stage volumes,
GCL transport, centroid sampling paths, topology-aware exchanges, 3D auxiliary
jets and true z derivatives, plus new energy/boost/field acceptance evidence.

## 8. Proposed Rust layout and reuse boundary

Create new modules beside the existing 2D path, after M1 acceptance. Do not
change Cargo dependencies until the adapter/license decision is reviewed.

```text
moving-mesh/src/three_d/
  mod.rs                 public Geometry3/ValidatedGeometry3 and facade
  ids.rs                 CellId, Image, FaceKey, lifted/local charts
  domain.rs              cuboid/periodic geometry, boundary tags
  polyhedron.rs          oriented polygons, clipping, tetrahedron moments
  oracle.rs              independent all-pairs HalfSpaceOracle3
  validate.rs            topology/plane/moment/global invariants, error context
  backend.rs             GeometryBackend3 trait, canonicalization adapter
  meshless_072.rs         optional isolated dependency adapter, later
  stencil.rs             image-aware rings, QR fits, conditioning report
  differential.rs        gradient/curl/Hessian/adjoint/independent divergence
  motion.rs              LinearMotion3, face normal speed, centroid paths
  gcl.rs                 shared sweeps and correction graph, later
  checkpoint.rs          versioned ID/chart/epoch geometry payload, later
mhd-vector-pot/src/three_d/
  geometry.rs            stage plans, state/geometry epoch validation
  auxiliary.rs           tensor-Hermite 3D jets and periodic deposition
  operators.rs           raw/limited A, gauge/cleaning, full-3D recovery
  projected_increment.rs moving endpoint-increment proposal, later
  integrator.rs          separately named 3D stages, immutable retry
```

Illustrative API contract (proposed signatures, not compilable code yet):

```rust
trait GeometryBackend3 {
    fn build(&self, input: &MeshInput3, epoch: GeometryEpoch)
        -> Result<RawGeometry3, GeometryError3>;
}
fn validate(raw: RawGeometry3, tolerances: &GeometryTolerances3)
    -> Result<ValidatedGeometry3, GeometryError3>;
fn build_operators(g: &ValidatedGeometry3, policy: &FitPolicy3)
    -> Result<Operators3, StencilError3>;
fn rebuild_endpoint(g0: &ValidatedGeometry3, p: &LinearMotion3, dt: f64,
                    backend: &dyn GeometryBackend3)
    -> Result<(ValidatedGeometry3, MotionReport3), GeometryError3>;
fn shared_exchange(g: &ValidatedGeometry3, states: &StageStates3,
                   motion: &LinearMotion3, boundary: &dyn BoundaryProvider3)
    -> Result<FaceExchangePlan3, StageError3>;
```

Errors carry stage, epoch, cell/face key, image, local scale, offending plane,
rank/condition and retryability. Input errors are not endlessly dt-retried.
Checkpoint serialization preserves IDs, image conventions, gauge/origin and
method version; unsupported schema/configuration is rejected. Backend outputs
are never deserialized directly into a validated type.

| Existing code | Reuse or generalization |
| --- | --- |
| `mhd-core/src/lib.rs`: Primitive, IdealGas, vector algebra, face-frame Riemann/ALE kernels | Reuse interfaces/kernels; add oblique 3D flux/covariance evidence. Pressure blend remains a named engineering choice. |
| `moving-mesh/src/lib.rs`: ValidMesh, oriented accumulation, error and baseline patterns | Reuse design patterns. Vec2 polygons, 2D moment identities and conditioning indicator are not 3D implementations. |
| `moving-mesh/src/quadratic.rs` | Reuse basis/weight/QR and image-dedup concepts; extend six to ten coefficients, full xyz, explicit rank-revealing factorization and metadata. Preserve the M1 module. |
| `mhd-vector-pot/src/operators.rs`: face_velocity, curl, material/source derivatives | Generalize all spatial indices and test transposes/signs; do not append a zero z row. |
| `mhd-vector-pot/src/projected_rate.rs` | Reuse matrix-free solve and deterministic-adjoint concepts; new moving target/increment contract and epoch invalidation. Cached fixed geometry is not reusable by identity alone. |
| `mhd-vector-pot/src/auxiliary.rs` | Generalize bicubic jets/deposition/origin to tricubic; existing 2D interpolation cannot serve a full-3D mesh. |
| `mhd-vector-pot/src/general.rs` | Reuse ownership/retry/positive-closure patterns; new 3D stage implementation, GCL and motion obligations. Keep old profiles and guard. |
| `moving-mesh/src/parallel.rs`, timing; `mhd-io` codec/checksum/atomic writes | Reuse ordered parallel collection and generic IO primitives where types permit; create explicit 3D schema. MPI remains deferred. |
| Existing geometry/M1 tests and reference evidence | Preserve as scoped 2D regression evidence. None counts as an executed 3D gate. |

## 9. Prospective REANA fixtures, gates and dependencies

**Every entry below is proposed and unexecuted.** Freeze exact fixture arrays,
configs, seeds, thresholds, source/dependency lock and independent reducer
before a run. This table registers a design target; executable case manifests
are a subsequent implementation deliverable. It changes no M1 gate. M1's
existing budget `1e-10`, wave order `>=1.8`, wave/shock boost `1e-8`, loop
boost `.001`, mean-field `1e-9`, vortex divergence `.1` and every scoped
reference condition remain unchanged. These 3D fixtures do not replace them.

Common dimensionalization: use declared box length Lref, h=cbrt(V), surface
area S, fixed initial fluid/field scales, nonzero momentum denominator
`M*c_ref+sum |p_i|`, energy denominator `sum |E_i|` and volume-weighted norms.
For dimensional rescaling, compare normalized residuals, not raw unit-dependent
epsilons. For polynomial reproduction with accepted condition estimate k,
use `max(1e-10,64*epsilon*k)` times the analytic derivative scale; report the
absolute error and k too. A large allowed tolerance near the rejection boundary
is not evidence of useful accuracy on galaxy meshes.

| ID / dependency | Exact prospective fixture family and measurements | Proposed pass/failure criteria | Per-case initial envelope |
| --- | --- | --- | --- |
| `G00` / accepted M1, new source preflight | Build one immutable 3D-capable binary; fmt, strict all-target/all-feature Clippy, locked debug/release workspace tests, schema and fixture integrity. Adapter feature build separate from dependency all-features. | All required commands pass; preserve 2D regression scope and source identities. | 4 threads, 8 GiB, 30 min; native libraries one thread. |
| `G01` / G00 | Bounded one-cell cuboid; periodic one-cell and 2x2x2; regular 4³; nonuniform Cartesian 4³ with each axis gaps repeating `[1,2,3,4]/10`; scales `1e-6,1,1e6`, translations and all coordinate permutations. Analytic bisectors/cuboid moments. | Normalized V/centroid/area/normal errors <=1e-10. Exact canonical incidence counts, correct self-image handling, no unpaired periodic face. | Each independent fixture: 1 thread, 2 GiB, 5 min. |
| `G02` / G01 | Jittered 4³/6³/8³ at .15 of spacing using a specified counter-based seed 20261122; add clustered/sliver fixtures and boundary-near points as explicit arrays. Oracle versus candidate per cell/face/image/moments. | Total volume relative error <=1e-10; normal closure / S <=1e-10; tensor/centroid normalized identities <=1e-9; oracle V/centroid/face-area difference <=1e-9. Positive finite cells, no unexplained topology differences. | Oracle <=512 cells: 1 thread, 4 GiB, 30 min. Candidate same case: 1 thread, 4 GiB, 10 min. |
| `G03` / G01 | Duplicate/periodically coincident generators, NaN/Inf/invalid widths, empty input, boundary-leaving generators, exact co-spherical cube seeds, separations 1e-4/1e-8/1e-12 of spacing and coplanar/near-coplanar stencils. | Invalid inputs return typed errors before backend; no panic/partial accepted mesh. Valid degeneracies either pass analytic geometry or explicitly return supported ambiguity error; count all rejections. No silent jitter. Smooth production fixtures may not reject. | 1 thread, 2 GiB, 5 min each. |
| `G04` / G02–03 | Reverse input order and a fixed ID-preserving shuffle; threads 1/2/4; repeat identical input; translation `(0.371,-0.219,0.443)*L`, seam crossings and multiple windings. | Canonical keys identical away from zero-area events; geometry/operator normalized difference <=1e-10. Same-input same-build serial output deterministic; report bitwise/thread results separately from toleranced gate. | 1/2/4 threads as named, 4 GiB, 10 min each. |
| `O01` / G02–04 | Synthetic full-rank linear/quadratic stencils and bounded interior cells; q equal to each of 1,x,y,z,x²/2,y²/2,z²/2,xy,xz,yz and all A component placements. Local image polynomial samples, not invalid globally affine periodic fields. | Constants vanish; affine linear fits and quadratic gradient/Hessian reproduce within condition-scaled tolerance. Reject deficient rank. Curl signs and Hessian symmetry exact to that tolerance. | 1 thread, 2 GiB, 5 min each. |
| `O02` / O01 | Periodic unit cube, A=`(sin(2pi*y)*sin(2pi*z), sin(2pi*z)*sin(2pi*x), sin(2pi*x)*sin(2pi*y))`, mean B separately `(0,0,0)` and `(.3,-.2,.4)`; N=8/16/32 regular and jitter .15. Use analytic curl/div(A), raw linear/quadratic and independent divergences. | Quadratic curl finest-three L1 order >=1.8 and N32 normalized L1 <=.1; all divergences finite, face-mean dimensional RMS decreases with refinement and signed periodic global face sum <=1e-12 normalized. Linear path is measured separately, no false second-order irregular claim. | Each resolution/mesh/mean: 2 threads, 8 GiB, 30 min; oracle only on small subset. |
| `O03` / O01 | Random fixed integer-vector inputs for C/transpose adjoint; gauge constants; analytic tricubic polynomials, all cube faces and periodic seams; root/empty-bin cases. | Relative adjoint error <=1e-12 using nonzero dot-product scale; C constant <=1e-12 scaled; shared u and first derivatives agree <=1e-12; polynomial derivative reproduction <=1e-10. | 1 thread, 2 GiB, 5 min each. |
| `M01` / G04 | Rigid translation `(2,-1,.5)`, N=4/8, dt producing >2 box lengths; bounded internal nonuniform w and periodic smooth w. Compare face formula, finite-difference volumes and centroid paths. | Rigid V/areas/centroid-offset drift <=1e-10 normalized; image/winding exact. Volume derivative finite-difference error decreases at second order away from topology events; <=1e-7 scaled at finest registered difference. | 1 thread, 4 GiB, 10 min each. |
| `M02` / M01,O03 | Prescribed periodic w=`(.05*sin(2pi*y),.05*sin(2pi*z),.05*sin(2pi*x))`, N=4/8, t=.1, dt=.01/.005/.0025; explicit five-seed co-spherical crossing embedded in a bounded 4³ fixture, frozen arrays/velocities chosen analytically before execution. Record union faces, GCL and substep sensitivity. | Shared GCL solve normalized volume residual <=1e-12; final uniform-state relative error <=1e-10 with GCL correction, budgets <=1e-10. Smooth raw local GCL/corrector corrections order >=2.8 and Euler correction order >=1.8; finest corrector `max abs(delta_S)/min adjacent V <=1e-4`. Topology fixture resolves the same event/piecewise geometry on halving dt, no missing positive-area faces or negative volume. | 1 thread, 4 GiB, 15 min each. |
| `F01` / O02–03,M02, moving-target design review | Kinematic full-vector periodic A from O02, fixed, rigid comoving and prescribed deformation; N=8/16/32; constant physical flow `(1,.5,-.25)` to t=1; analytic translated fields, periodic mean B cases. No fluid-backreaction claim. | Smooth fixed/deforming B L1 order >=1.8, finest normalized L1 <=.1. Rigid comoving discrete A/B drift <=1e-10. Mean-B drift <=1e-9 normalized; dimensional divergence RMS decreases. No nonsmooth loop order requirement. | 2 threads, 8 GiB, 2 h each. |
| `F02` / F01, accepted incremental/GCL design | Prescribed advection in a periodic cube: compact spherical potential `A=1e-3*(1-s)^4*(1,2,3)/sqrt(14)` for `s=norm(x-(.5,.5,.5))²/.2²<1`, zero outside; analytic curl `grad(1e-3*(1-s)^4) cross (1,2,3)/sqrt(14)`. Separate axial tube `Az=1e-3*max(0,.3-r_xy)` and cyclic permutations, flow `(1,.5,-.25)`, t=1, N=8/16/32; retain tube cusp/edge mask. | Smooth bump B convergence >=1.8; nonsmooth errors decrease, extrema/energy/topology recorded. Rigid comoving drift <=1e-10. These engineering fixtures do not claim P26 §6.9 reproduction. | 2 threads, 8 GiB, 2 h each. |
| `C01` / F01–02, full stage/coupling review | Uniform rho=p=1, gamma=5/3, v=`(.3,-.2,.4)`, Bmean=`(.2,.1,-.3)`, a=phi=0; prescribed deformation and topology fixture, t=.1. Oblique face two-cell exchange permutations. | All accepted rho/p positive, gas budgets <=1e-10, constant-state normalized drift <=1e-10, per-face antisymmetry exact by one-record application; stage/final geometry and projection gates pass. | 2 threads, 8 GiB, 30 min each. |
| `C02` / C01 | Oblique circular Alfvén waves defined below; travelling/standing, N=8/16/32/64, regular/jitter .15, fixed/rigid/deforming. Gamma=5/3, rho=1,p=.1, parallel B=1, transverse amplitude .1, common final t=`1/sqrt(14)`. | Finest-three B L1 order >=1.8; finest B error / .1 <=.02; budgets <=1e-10, positive states. Compare time caps separately; do not invent an M1 temporal threshold. Failure blocks long 3D blast/vortex campaigns. | N<=32: 4 threads,16 GiB,4 h; N64: 8 threads,32 GiB,12 h; calibrate before escalation. |
| `B01` / relevant completed F/C subset | Joint fluid/mesh/reference-frame boosts `(2,-1,.5)` and `(10,7,-3)` for each supported motion, transformed coordinates and conserved energy; rotations/permutations and restart pairs. | Smooth wave/state component/vector L1 with both amplitude and fixed nonzero state normalization <=1e-8; uniform mean-field comparison <=1e-9; budget <=1e-10. Rigid prescribed loop uses <=1e-10 drift; coupled nonsmooth loop boost <=.001 of fixed initial field scale. Record A only with a stated gauge transform. | Same resources as its unboosted case; every boosted case separate workflow. |
| `C03` / C02,B01 | 3D MHD blast and 3D vortex from separately frozen full-text fixtures or explicitly named engineering configurations; pressure/density/field statistics, spectra, symmetry, independent finer reference and budgets. | Full benchmark-specific error/symmetry/divergence limits must be frozen after source transcription and reference-uncertainty study, **before** execution; positivity/budget/boost/GCL gates above already apply. No pass can be declared from pictures or finite completion. | Calibration 4 threads,16 GiB,1 h; prospective N64 8 threads,32 GiB,12 h per case; finer envelope set from calibration. |
| `X01` / accepted geometry/hydro, gravity contract | Typed EntityId/centroid/mass/epoch/hash/unit handoff and kicked uniform gas; checked force-to-acceleration conversion; boundary source ledger, mixed gas-particle work and domain-size tests are coordinated with G1/G2. | Reject stale epoch/hash/time or wrong units/kind; exact ID/mass accounting, face/source budgets <=1e-10 where the force/source model permits; force/energy/angular-momentum tolerances owned by gravity contract. | Small interface case 1 thread,4 GiB,15 min; physical gravity cases separately registered. |

For C02 choose `k=(1,2,3)`, `kh=k/sqrt(14)`,
`e1=(2,-1,0)/sqrt(5)`, `e2=kh cross e1`, `K=2pi*sqrt(14)` and
`theta=2pi*(k dot x+sqrt(14)*(1-v_parallel)*t)`. Set
`T=e1*sin(theta)+e2*cos(theta)`, `B_mean=kh`, `a=.1*T/K`,
`v=v_parallel*kh+.1*T`, phi=0 and `v_parallel=0` or 1. Thus
`curl(a)=.1*T`, derived independently; the standing case uses the same final
time as the travelling case. This is a project periodic-cube fixture, not the
paper's exact rotated-box setup. Check the analytic signs/algebra independently
in its REANA fixture before evolving it. Smooth potential-bump coordinates
use nearest periodic displacements; its compact support avoids seam ambiguity.

The topology event's exact five-seed input and the 3D blast/vortex reference
packets are explicit remaining fixture-preparation tasks; neither is silently
claimed execution-ready. All other formula-defined fixture families still need
immutable serialized cases and reducers. Proposed resource envelopes are
planning caps, not measured costs or an aggregate limit. If calibration
exceeds one, revise resources prospectively while retaining the physical case
and thresholds, not by truncating its final time.

For all evolutions record stage accepted minima, actual dt/caps/rejections,
mesh and stencil failures, topology births/deaths, GCL correction sizes,
projection iterations/true residuals, HLL fallback versus intentional blend,
auxiliary roots, magnetic energy, all divergence definitions, mean B and gas
budgets. Compare boosts in equivalent physical coordinates after removing
`boost*t`; transform `p'=p+M*b` and `E'=E+b·p+.5*M*|b|²`. Compare local values
by ID only for homologous meshes; otherwise independently integrate common
physical bins/polyhedron overlaps and record coverage/reference uncertainty.
Gauge-dependent A is never the sole physical boost metric.

Each independent fixture, resolution, seed, motion, backend and base/boost
case gets its **own REANA workflow**, CPU request/limit, memory and timeout.
Submit all ready independent cases concurrently; there is **no aggregate
24-core/64-GB cap**. Numerical libraries use one internal thread unless that
job's single project Rayon pool owns parallelism. Preserve build/preflight
dependencies and reuse a checksum-verified immutable binary. Reduce complete
pairs/ladders promptly; a verified required failure blocks dependent escalation
and preserves/cancels unnecessary siblings. Missing downloads are observation
errors, not passes or physical failures. Do not use the legacy monolithic
runner unchanged. Nothing in this task submits or controls a workflow.

## 10. First implementation tasks after M1 acceptance

1. Add the new 3D ID/domain/local-chart types, typed errors and fixture format;
   keep existing 2D paths untouched. Freeze G01/G03 analytic inputs and
   independent geometric reducers, with an explicit REANA preflight plan.
2. Implement only the all-pairs clipped-polyhedron builder, oriented shared
   pairing, tetrahedron moments and validator. Execute G00–G03 on REANA;
   review analytic values and failures before adding an accelerated backend.
3. Prepare the optional exact-version ibig adapter and complete locked license
   closure/notices. Add its normal-sign and periodic-pair regressions and run
   G02–G04, including raw polygon extraction and degenerate cases. Adopt only
   if it meets the geometry contract; otherwise retain the small oracle.
4. Add full-3D QR stencils, raw/limited derivative separation, curl/adjoint and
   independent divergence diagnostics. Run O01–O03; publish conditioning and
   manufactured convergence before coupling a fluid step.
5. Add prescribed linear motion, lifted centroid paths and the shared GCL
   experiment. Freeze event arrays; run M01–M02 and review correction order,
   conservation and missed-event sensitivity. Then add tricubic auxiliary
   transport and F01/F02 without claiming coupled MHD.
6. Obtain the new moving-target/GCL numerical review, verify fixed/rigid
   reduction against the accepted M1 engineering family, implement the named
   3D integrator and run C01/C02/B01. Only then prepare long C03 and gravity
   coupling. Bounded A/gauge physics remains its own explicit prerequisite.

Completion of this document means an actionable design and source audit.
There is no accepted 3D implementation, dependency adoption, executed 3D
benchmark, nonperiodic magnetic boundary or galaxy-merger validation yet.
