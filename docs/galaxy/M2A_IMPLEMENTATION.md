# First static 3D half-space oracle implementation

2026-11-22. **Code and tests written; no build, format, Clippy, test,
geometry/reference evaluation or evolution executed for this slice.** Scoped
[M1 acceptance](../../tests/reference/m1_final_acceptance/acceptance.json)
permits this implementation. It does not accept static 3D geometry, deforming
MHD, gravity, ISM or the galaxy merger. The separate
[final joint review](../M1_FINAL_OUTPUT_ARCHIVE_REVIEW.md) and actual copied
outer consistency execution are the M1 prerequisite, not 3D evidence.

This is an independently written serial comparator. No external geometry
code, dependency, search tree, meshless_voronoi adapter or licensed algorithm
implementation was imported. The only new dependency is the project-owned
`galaxy-types` path, using its shared `EntityId`/`CellId` API. Root owns the
workspace/lockfile integration. Old 2D algorithms are unchanged; `lib.rs`
adds only `pub mod three_d;`. No historical evidence or independent review
was edited. This document supplements, rather than rewrites, the historical
unimplemented/design status in [MESH_3D_SPEC.md](MESH_3D_SPEC.md).

## Implemented API and identity boundary

```rust
use galaxy_types::{CellId, EntityId};
use moving_mesh::three_d::{
    Boundary3, Domain3, Generator3, HalfSpaceOracle3, Image3,
};
// Illustrative source only, not an executed example.
let input = [Generator3 {
    id: CellId::new(EntityId::new(1, 1)),
    position: [0.25, 0.375, 0.625],
    winding: Image3::ZERO,
}];
let domain = Domain3 {
    anchor: [0.0; 3], width: [1.0; 3], boundary: Boundary3::Periodic,
};
let geometry = HalfSpaceOracle3::build(domain, &input)?;
```

`ValidatedGeometry3` has private fields and no public raw constructor or
mutable accessor. Read-only cells/faces/domain/quality expose the validated
snapshot. `cell_by_id`, `cell_ref`, `face_ref`, `cell` and `face` provide
sorted real-owner lookup and epoch-checked handles. Geometry-local indices
are u32. The process-local atomic epoch is allocated only after all checks;
different successful rebuilds get different epochs. Clones share the same
immutable identity. Epoch values are not persistent IDs or restart tokens;
a future checkpoint must rebuild/revalidate and invalidate old handles.
Thread scheduling is not promised to assign identical epoch numbers.

Cells retain the shared persistent CellId, primary-box generator and i64
winding, positive volume, centroid **offset**, volume-integrated central
second moment J, surface area, bounding radius, minimum generator/face
distance and every oriented incidence. A centroid can lie outside the
primary box; it is never wrapped or replaced by the generator. Sorting is
by full CellId; a zero identity payload is valid, duplicates are not.
Catalog construction does not allocate IDs or substitute images for real
entities. Run-wide namespace/particle uniqueness remains the shared
registry's responsibility.

`FaceKey3::Interior {lo,hi,hi_image}` stores full owner IDs and trajectory
image m. For distinct IDs the lower owner is left. A self-image uses the
sign with positive first nonzero component. Its zero image is invalid.
`Boundary {cell,patch}` distinguishes each of the six physical cuboid
patches in x_min,x_max,y_min,y_max,z_min,z_max order. One canonical shared
face stores left/right local owners, wrapped image s, area, outward-left
unit normal, left-relative centroid, positive plane distance, ordered
convex polygon and surface-average central covariance. Fan triangles are
`(0,k,k+1)` in that loop; no independent triangulation state is hidden.

Each interior record has two incidences with signs +1/-1. This includes
two entries on the same real cell for a self-image, whose coalesced exchange
incidence is zero. The two different geometric charts remain available.
Incidences retain neighbour `(CellId,m)` and the translation from the
canonical left-relative polygon to their owner's relative coordinates.
Reverse normals/loop winding follow the incidence sign. No flux is
implemented here.

For wrapped positions x and winding k, m=s+k_left-k_right. Calculation uses
i128 intermediates then checked i64 conversion, so equal extreme windings
do not fail merely because an intermediate i64 addition would overflow.
The relative displacement is `d=x_right+L*s-x_left`; cancellation of winding
terms makes this the same displacement in the continuous owner lift.
Huge reconstructed absolute lifted positions are never formed in f64.

## Construction and equation map

All rows in this table are independent mathematical derivations or explicit
engineering decisions. None is an asserted AREPO/P26 implementation.
The full primary-publication map remains in the parent mesh specification;
this slice needs only Euclidean distance, convex half-spaces and simplex
integration. No new paper coefficient was inferred.

| Contract/source anchor | Implementation | Represented equation/decision |
| --- | --- | --- |
| Mesh §4.3 | `oracle.rs`: `constraints`, `bisector` | `d dot y <= (d dot d)/2`, generator-relative y; every real neighbour, all 27 wrapped shifts for periodic geometry. |
| Mesh §§2–3 | `types.rs`, `oracle.rs`: `key`, `paired` | Full IDs/images and one shared polygon; exact rational reverse-chart polygon equality before selecting canonical metrics. |
| Mesh §4.3, independent derivation here | `exact.rs`, `clip.rs` | Exact dyadic planes, homogeneous Cramer vertices; side sign `sign(n dot numerator-h*denominator)` with positive denominator. |
| Mesh §4.3 | `clip.rs`: `convex_loop`, `clip` | Exact projected orientation, cap hull, deterministic winding and starting vertex; delete only certified equal/collinear/zero-area contacts. |
| Mesh §3.1 | `moments.rs`: `integrate` | Outward signed tetrahedra, `v=det(a,b,c)/6`, first moment `v*(a+b+c)/4`. |
| Simplex integration, derivation here | `moments.rs` | For d-simplex vertices p, `average(p p^T)=[sum p_i p_i^T+(sum p_i)(sum p_i)^T]/[(d+1)(d+2)]`; d=2 for surface covariance, d=3 for volume moments. |
| Mesh §3.1 | `clip.rs`: `validate`; `moments.rs` | Exact half-space containment, two oppositely oriented uses per edge and Euler closure; floating normal/affine/centroid/divergence-volume identities. |
| Mesh §9 G01; fixture review R9/R10 | Integration tests | Independent separable intervals and oblique inclusion/exclusion references; no candidate moments/clipping used to obtain expectations. |

The simplex formula follows from barycentric integrals
`average(lambda_i^2)=2/[(d+1)(d+2)]` and
`average(lambda_i*lambda_j)=1/[(d+1)(d+2)]` for i!=j.
The implementation first obtains the centroid, then accumulates the central
second moments from shifted simplex vertices. It does not subtract two large
absolute-coordinate raw moments. Local coordinates are divided by the
largest domain width Lref; final area/V/J scale as Lref^2/Lref^3/Lref^5.
Neumaier accumulation uses canonical face, triangle and component order.
Signed negative tetrahedra are rejected rather than made positive by abs.

Periodic cells start in the exact nearest-self-image cuboid
`[-Lx/2,Lx/2] x ...` about the generator. Six starting faces are tagged real
self-image constraints. Other self shifts and all other generators' 27
shifts remain eligible, ordered by ID then lexicographic wrapped image.
The orthorhombic nearest-image argument in Mesh §4.3 supplies sufficiency;
skew, mixed-periodic, shearing, nonconvex or moving domains are not supported.
Bounded cells start in the physical cuboid, not a generator-centred box,
and clip every other real generator without images. Generators are strictly
interior in bounded domains; periodic inputs must already lie in the
half-open primary box. Wrapping or perturbing invalid input is forbidden.
Physical MHD wall states and ghost observations are deliberately absent.

Plane coefficients use the **exact dyadic interpretation of the actual
finite binary64 input bytes**, including exact subtraction, squaring and
sum, not rounded f64 plane coefficients. D is a bounded signed integer
times a power of two, implemented here with little-endian u32 limbs.
Intersection coordinates are ratios of exact 3x3 determinants, not chained
floating interpolation. Edge endpoints retain defining-plane support; an
intersection selects two shared independent supports and the cutting plane.
Singular support combinations are skipped only while searching that same
edge for an independent pair; exhaustion is a typed topology failure, not
a lower-precision fallback.

An exact zero side does not itself reject the cell. It adds plane support
and permits a certified edge/vertex contact without inventing a face.
Exact projected monotone hulls remove only duplicate or collinear vertices;
an exactly lower-dimensional clipped polygon is a non-face. A positive
but difficult face is never omitted by an area threshold. This distinction
is necessary for the co-spherical Cartesian controls. Independent builds
of reciprocal cells must produce exactly equal rational vertex sets after
chart translation; their floating area/centroid/normal/covariance also must
agree at the unchanged normalized1e-10 bound. Incompatible faces are not
averaged.

After canonical selection, the exported shared metrics are used to recheck
every cell's normal/affine/centroid/divergence-volume closure and centroid
containment, with both self-image charts. Surface/radius/minimum-distance
diagnostics are then derived from those exported incidences. Precursor-only
validation cannot substitute for this last check. V and J remain actual
owner-side tessellated integrals, never adjusted to force closure.

## Validation, explicit limits and uncertainty

The published object requires exact closure/containment/topology/pairing
checks plus finite positive metrics, correctly oriented triangles, positive
generator distance and the normalized1e-10 normal, affine, centroid,
divergence-volume, global-volume and bounded patch-area identities. Cell
centroid containment is checked in the computed face planes. Central J
must be finite/positive definite under the declared floating separation
check. Boundary closure covers all six actual cuboid patches. None of these
invariants proves general physical convergence or bounds every floating
output error on every admissible point set.

The exact predicate implementation itself is **new and unexecuted**, not
formally verified big-integer software. Exactness is its intended arithmetic
contract, subject to independent source review and the written arithmetic
and geometry tests. Rational-to-f64 conversion truncates each operand to
its leading53 bits before division and a binary scale; it is not claimed
correctly rounded or an interval enclosure. Overflow/underflow of a nonzero
output, unrepresentable dimensional scales, inconsistent topology, failed
identities and unresolved metric separation reject the build.

The explicit engineering separation policy rejects a positive triangle
area <=256*epsilon*R^2 or signed tetrahedron volume <=512*epsilon*R^3,
where R is the greatest generator-relative normalized vertex radius of
that triangle. This is `UncertainMetric`, never face deletion, perturbation
or a passed analytic fixture. These conservative operation-scale filters
are not rigorous propagated coordinate/error enclosures. The normalized
central-J determinant must exceed64*epsilon times its summed absolute
determinant terms, with positive leading principal minors. This is a
documented conditioning rejection, not a replacement for the1e-10 analytic
accuracy gates. A badly placed generator pivot can therefore reject even
a physically well-shaped cell; a future independently reviewed pivot/
interval improvement may enlarge the supported set, but is not silently
present. Required seven analytic cases must build and meet every original
gate; rejection/uncertainty is a failure for them.

Hard resource limits are512 generators,1024 u32 limbs per dyadic,
256 faces/cell,256 vertices/face,64 supporting planes/vertex,
4096 polygon-vertex incidences/cell,65536 retained owner-side raw vertices,
and500000000 counted side/orientation/sort/intersection predicate operations
per build. Exact pairing/limb operations are bounded by the other caps, not
claimed individually counted in the latter counter. Caps fail closed as
`ResourceLimit`; they do not imply all512-generator inputs fit a time or
memory budget. Intermediate exact arithmetic and all-pairs final checks can
be expensive. Allocator/OOM/process failure is not made recoverable by a
typed geometric error. Measure cost before enlarging any cap.

Other typed errors cover invalid domain, empty/oversized catalogs,
nonfinite/out-of-domain/wall generators, duplicate IDs/positions, bounded
winding, image overflow, singular intersections, invalid topology,
unrepresentable metrics, reciprocal-face mismatch, exhausted epochs,
stale handles and invalid local indices. The initial f64 upper-bound
representability check can reject a width lost beside an enormous anchor;
it does not redefine that width as zero or silently translate the input.
No partial geometry is returned after any failure. This slice supplies no
checkpoint payload, gradients, curl, Cdot, moving faces, GCL, raw A rate,
fluid exchange, auxiliary velocity, gravity force or gas boundary physics.

## Written independent REANA cases

Every selector below is **unexecuted**. Use the exact test name with `--exact`
and retain `--nocapture` input-bit/quality logs. Seven base fixtures use the
packet's namespace/x-fast counter convention, intervals, full J, face data
and exact counts. Their tests pass only if the builder returns geometry.
The regular tests check face covariance separately from volume J. The
oblique test checks all cross moments, the actual hexagon vertex set and
its physical wall fragments. Covariance for the oblique face does not yet
have a separately frozen independent value; no invented answer is supplied.

`--test geometry3_analytic` selectors:

- `periodic_one_cell_self_images`
- `periodic_cartesian_2x2x2`
- `periodic_nonuniform_3x2x2`
- `periodic_cartesian_4x4x4`
- `periodic_nonuniform_4x4x4`
- `bounded_one_cell_2x3x4`
- `bounded_oblique_bisector`

`--test geometry3_controls` selectors:

- `oblique_scale_one_millionth`
- `oblique_scale_one_million`
- `oblique_nonzero_anchor`
- `cuboid_permutation_xyz`
- `cuboid_permutation_xzy`
- `cuboid_permutation_yxz`
- `cuboid_permutation_yzx`
- `cuboid_permutation_zxy`
- `cuboid_permutation_zyx`
- `input_permutation_is_canonical`
- `periodic_owner_image_reciprocity_and_unequal_windings`
- `epoch_handles_reject_cross_geometry_use`
- `invalid_domains_and_empty_catalog_reject`
- `invalid_catalog_identity_finiteness_and_domain_reject`
- `image_overflow_rejects_without_partial_geometry`
- `equal_extreme_windings_do_not_overflow_intermediate_arithmetic`
- `unrepresentable_physical_moment_scale_rejects`

New library-only selectors, using `--lib`:

- `three_d::exact::tests::exact_cancellation_retains_below_binary64_ulp_terms`
- `three_d::exact::tests::dyadic_subnormal_and_signed_zero_decode_exactly`
- `three_d::exact::tests::integer_product_carry_matches_binomial_identity`
- `three_d::exact::tests::determinant_orientation_and_exact_coplanar_contact`

These are24 integration cases and4 predicate cases. Each is one independent
REANA workflow after an immutable source/build preflight: initially1CPU,
2GiB,300s and one thread, no aggregate cap. Build/format/strict Clippy and
debug/release/all-target compilation are mandatory REANA prerequisites.
`cargo fmt`, `rustfmt`, `cargo`, `rustc`, test enumeration/imports and target
entrypoints were **not invoked locally**. Formatting, lint, type checking,
actual selector resolution and runtime costs all remain unobserved. Root
must integrate galaxy-types workspace membership/lockfile before freezing
and reviewing that complete source. Do not run all new independent cases
inside one aggregate numerical workflow.

Transformation controls use the reviewed geometric transformation laws and
retain IDs: anisotropic cuboid tests distinguish all six axis permutations;
oblique tests distinguish s^2/s^3/s^5 scaling and a translated domain.
Their actual expression-evaluated binary64 inputs are the candidate problem.
They are **not** a completed correctly-rounded exact-rational composed
fixture expander or the entire seven-by-scale-by-translation-by-permutation
cross product. Independent high-precision/reference conversion and that
complete literal packet still need review and REANA evaluation. Bit logs
must be retained; expected ideal-rational formulas are compared at the
packet's normalized1e-10 gates, with conversion uncertainty assessed by
the independent later reference. No jitter/sliver oracle answer or measured
uncertainty was generated locally.

## Actual source-only checks and remaining dependency

Performed: source reading/manual equation and control-flow review, exact
shared-ID interface inspection, JSON/source-byte/hash inspections, textual
selector/delimiter/whitespace checks and owned `git diff --check`. These do
not establish Rust syntax/type correctness, executed predicate accuracy,
correctness of a fixture expansion or any numerical result. Large combined
context displays were truncated; narrower operative reads followed. One
early combined inspection returned1 because `crates/galaxy-types` had not
yet been created by its concurrent owner; later direct source inspection
found the specified API. An overlapping sed range displayed one line twice;
numbered source inspection confirmed it was not duplicated in the file.
An inert-check orchestration wrapper initially failed JavaScript parsing
because Markdown backticks were unescaped; no nested tool executed in that
call. The corrected wrapper completed the source-only checks below.
No inspection error was converted to a numerical pass.

Next: independent source review (especially custom dyadic carry/sign,
homogeneous predicates, cap support and moment separation), coherent root
workspace integration, immutable REANA formatting/compile/source preflight,
then all28 named cases separately and independent output/reference review.
G02 jitter/slivers/clustered512-cell cost controls, the complete G01
transformation packet and G04 seam/partition controls remain pending.
Only after geometry gates pass should a separately audited accelerated
backend or3D differential operators be considered. State-dependent motion,
certified events, C/Cdot/GCL and nonzero-MHD coupling, bounded U1–U4,
gravity/active sources and the full-duration live-component merger retain
their independent prerequisites. Written code confers no3D acceptance.

Exact source/input identities below are a noncircular source-only inventory;
this document's own hash is supplied in the worker completion receipt.

### Source-byte inventory

Actual inert source checks: textual delimiter/selector/whitespace checks,
two JSON parses and exact M1 lib/manifest one-line-extension comparisons;
errors: []. No Rust parser/compiler/formatter or target import ran.

| Path | Bytes | SHA256 |
| --- | ---: | --- |
| `crates/moving-mesh/Cargo.toml` | 414 | `51fba1fcf21c1b02797c1ae6da5bd8d77753e11c5b5722c466fe9ccbdd6d9406` |
| `crates/moving-mesh/src/lib.rs` | 62358 | `11d63c9fedb1c6604c248babd7c66fdd2add8640c8be4ec620371b5ee3c14672` |
| `crates/moving-mesh/src/three_d/clip.rs` | 10491 | `450f26bf2f1b9f2f83b7b6a968554753dc1bcf907b91bec9c22251e8312492ca` |
| `crates/moving-mesh/src/three_d/exact.rs` | 10477 | `f8935875f49757cc318c796282dcbe04599e2e8b3770d99348f841b92fb90be4` |
| `crates/moving-mesh/src/three_d/mod.rs` | 429 | `2968a3118369c7bd6dbecabc88aa26459fb3ca8bcbb4508bf750e80e216d22d2` |
| `crates/moving-mesh/src/three_d/moments.rs` | 10628 | `89138a50877c7619af1f1ca0b668458908b1ebd1587637bb4e16d84881a4974a` |
| `crates/moving-mesh/src/three_d/oracle.rs` | 18323 | `c743a82c1be9cd5f28aa8ab9939f45c9db5f2d8ed023f7b2ca729bceec6db618` |
| `crates/moving-mesh/src/three_d/types.rs` | 7321 | `355c025e850f6e1716e9e282697eba4107798751c0e3d2e030fb6a973b1e2878` |
| `crates/moving-mesh/tests/geometry3_analytic.rs` | 9900 | `c7a28e5b09727e1142a5518bb33d4e23cc78827f48cd9b996d86fd9d81d87def` |
| `crates/moving-mesh/tests/geometry3_controls.rs` | 11636 | `70271bba5d920b266b106aca6cb0b38be887a8aaea4a31b1ffc3d046782f58ec` |
| `tests/reference/m1_final_acceptance/acceptance.json` | 5730 | `274b4af78a3b0a3845e8210825c3a1b573df4bdfac9a1d305f7d3a7f05d8eebb` |
| `docs/M1_FINAL_OUTPUT_ARCHIVE_REVIEW.md` | 1673 | `e8ae072c5deafbe5c96573c09c7258e3950493fdeec0a9cfd84f37ec273bb065` |
| `docs/galaxy/INTEGRATION_CONTRACT.md` | 14271 | `16b1b21791ad780510c568a93fd73a655c1fd8d66720cf9073e8e28defcbf453` |
| `docs/galaxy/MESH_3D_SPEC.md` | 79538 | `32e5ed2af3097c8106896fcb262a751ee37fe06dbf927f510e03952b5826b4ac` |
| `docs/galaxy/fixtures/README.md` | 5287 | `a5cf8069df48795ee7d7c8eaef4f0d33e19f590d2725354f99079a177a1624d7` |
| `docs/galaxy/fixtures/geometry3_analytic_v1.json` | 12665 | `69fd92fc2009df207d076441527161825eb50ae911a2ec2a8e398d687306f288` |
| `docs/galaxy/BOUNDARY_MHD_DESIGN_REVIEW.md` | 41551 | `94a6ad765b33ee9347a48f2f906a33d91ed72fc5818975f102da9f69c6039085` |
| `crates/galaxy-types/src/identity.rs` | 14951 | `b2dad224dae53dcb51f1b8729120b44e85ff3c12ebebdee8b6e61d04031bed0e` |
