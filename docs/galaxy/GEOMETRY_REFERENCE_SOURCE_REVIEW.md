# Independent exact rounded-input geometry reference source review

2026-11-22. Subject **`f57a6e6c60d518c25fa185e248a4cfcdc7155d3f`**.
**No blocking source defect was identified within the registered static
seven-fixture family.** The three frozen files are conditionally eligible for
immutable REANA source/import and arithmetic preflight, then each written
method and reference case in its own workflow. This is source/manual-mathematics
support, not a successful import, evaluated reference, candidate comparison,
proved arithmetic library or geometry acceptance.

I authored the adjacent Rust `HalfSpaceOracle3` and its tests. The coordinator
authored this Python reference. This review assesses reference independence and
its declared formulas/interfaces; it does **not** independently approve my
candidate or my earlier test corrections. The separate
[candidate source review](M2A_SOURCE_REVIEW.md) and
[narrow revision review](M2A_SOURCE_REVISION_REVIEW.md) remain unchanged.
M1 acceptance remains confined to its frozen periodic, single-process,
fixed/rigid 2.5D profile. Full deforming nonzero-MHD, gravity/ISM and the live
galaxy merger remain open.

## Numbered dispositions

### 1. Supported: independent construction and exact target

**Locators:** reference script R1–32, R171–289, R366–493; implementation note
“Input and transformation contract” and “Rounded oblique box cut”; fixture
README “Exact derivations”; historical boundary review findings 11–12.
Here R denotes line numbers of the frozen reference script; T denotes the
frozen test script.

The reference imports standard-library facilities only. It does not import or
call candidate clipping, homogeneous intersections, cap hulls or tetrahedron
integration. Cartesian products use exact midpoint intervals; oblique cells
use box-cut monomial inclusion-exclusion; surfaces use coarea derivatives and
explicit edge/plane intersections. These are materially different constructions
from the candidate. Exact rational arithmetic is supplied by `Fraction`; the
binary64 conversion is separately written integer code, not the candidate
decoder. Shared IDs, face conventions and original analytic expectations are
required common interfaces, not evidence of implementation dependence.

The certified mathematical target is the exact dyadic interpretation of the
**actual once-rounded coordinate/width/anchor words**, rather than an ideally
similar transform of the unrounded reference. This is the right distinction
for translated/nonuniform inputs. No target/reference arithmetic was executed
in this review. All mathematical arguments below are independent manual
derivations, not attributed AREPO/P26 algorithms or coefficients.

### 2. Supported conditionally: integer RN conversion and radical enclosures

**Locators:** R52–139; T18–74.

For positive N/D, the bit-length difference is the binary exponent or one too
large; the exact comparison at R72–74 corrects that one possible excess.
Normal conversion rounds `N/D*2^(52-e)` by quotient/remainder. R55–56 selects
the upper integer above a half and at a half only when the lower integer is
odd. R82–84 propagates a significand carry into the exponent. Below the normal
range, rounding on the fixed `2^-1074` lattice produces subnormals, zero, or
the minimum-normal word `2^52`. Negative underflow retains its sign bit;
exact rational zero is canonical positive zero. The inverse decoder uses
the correct finite normal/subnormal exponents and rejects exponent 2047.

The maximum-finite midpoint can carry to exponent 1024, which is explicitly
rejected. The written test uses the correct half-ulp offset `2^970` above
the largest finite value. These source arguments support ties-even, gradual
underflow and carry handling; they are not exhaustive executed converter
verification. A fixed finite export is never replaced by infinity.

For an irrational square root, `isqrt(floor(N*2^(2k)/D))` bounds the root
between consecutive `2^-k` rationals. Negative factors reverse the endpoints.
Rational roots are detected before interval refinement. Equal finite RN
endpoint words certify the enclosed value's rounded word by monotonicity.
Unresolved rounding at the finite precision ladder rejects export. Extreme
unrepresented inputs/enclosures can also reject; arbitrary-range success is
not promised. The exact value/enclosure, not merely its nearest word, must
remain available to a later gate reducer.

### 3. Supported: all 252 source-defined transformations retain original IDs

**Locators:** R24–32, R150–217, R496–540; T135–155; design
`/identity`, `/transform_families`; historical review finding 12.

The source cross product is seven distinct fixture names, three scale indices,
six distinct permutation strings and two translation indices. The name contains
each independent selection, so the registered construction defines 252 unique
identities, 36 per fixture. This is a manual source count, not execution of
`case_catalog` or a retained expanded 252-case packet.

The transform composes `s*x[p]+delta`, `s*a[p]+delta`, and `s*L[p]` in exact
rationals, with `delta_j=t_j*s*L[p_j]`, then applies one RN to each final
scalar. Width is an independent rounded input; the physical wall is the exact
sum of rounded anchor and width. The additional rounded-upper representability
guard is an explicit conservative input prerequisite, not a redefinition of
the wall. Generator checks use the actual exact sum.

Tensor generators are enumerated in original x-fast order before coordinate
permutation. IDs therefore remain attached to original points. The separate
permuted index tuples and inverse map retain this association for every axis
permutation, including the asymmetric 3×2×2 product. Bounded IDs retain their
original counters. Hex serialization is namespace first and exactly 32 lower
case digits. Face patches, vectors, both tensor indices and image triples are
constructed in the new coordinate axes.

The older **28 Rust controls are a different input family**: their expression-
rounded transformed coordinates and control namespaces cannot be relabelled as
these exact-composition inputs. Future comparisons must bind actual bit arrays
and IDs. Neither this source nor this review retroactively certifies them.

### 4. Supported: rounded periodic intervals, full keys and self-incidences

**Locators:** R366–433, R521–534; T180–192; mesh §§2.2–3.

Distance separation still applies after independent rounding of each tensor
axis. Previous/next intervals use actual rounded neighbours; at a seam they
use the last point minus actual L or first point plus actual L. A one-point
axis therefore yields `[x-L/2,x+L/2]`, regardless of anchor or generator offset.
Products yield actual V, centroid, diagonal volume-integrated J and rectangle
covariances. The bounded one-cell case uses its actual box.

Each incidence retains the full canonical owner/image key and sign. Reversing
the owner ordering negates the image; canonical shared data is emitted only
from the lower-ID owner. For self-neighbours, positive axis sign emits the
canonical face and negative sign retains the second incidence. Two-point axes
retain both the internal and seam face between the same real IDs. No image is
another persistent entity. All fixture windings here are zero; unequal
windings, points-only seam motion and G04 are not covered.

`owner_chart_centroid` is the absolute coordinate in that owner's unwrapped
box chart; `face.centroid_offset` and polygon offsets are relative to the
canonical generator. A later reader must preserve that distinction. Sorting
faces and incidences keeps both self signs, and the source checks unique
canonical keys and required aggregate positive-face/incidence counts. The
actual 252 emitted inventories remain to be observed, not inferred from this
source support.

### 5. Supported: general positive-coefficient box cuts and complements

**Locators:** R220–289, R436–448, R456–476; T76–133.

For `u_j=c_j*t_j`, upper bounds are `b_j=c_j*w_j`. Inclusion-exclusion shifts
`u=v+b_S`; expanding `(v+b_S)^alpha` gives the binomial coefficient and shifted
power at R251. The remaining simplex term is
`prod(beta_j!)*H^(d+sum beta)/(d+sum beta)!`; division by
`prod(c_j^(alpha_j+1))` restores both the monomial and Jacobian. This establishes
the formula for arbitrary **positive actual rational coefficients**, including
the unequal coefficients induced by translated/scaled rounding, rather than
assuming a symmetric `(1,1,1)` bisector. The source rejects unsupported signs.

All raw monomials through degree two are computed before centralization.
Complement moments are full-box minus cut raw moments, then
`c=M1/M0`, `J=M2-M1*M1^T/M0`. Subtracting central tensors directly would be
wrong; this source does not do so. The bisector level includes the actual
rounded anchor shift, with `c=g1-g0` and
`h=sum((g1^2-g0^2)/2-c*anchor)`. These are exact operations after input RN.

For d=2/3 and the selected degrees, zero-height terms and their first
derivatives vanish; skipping `H<=0` is compatible with the coarea calculation.
The helper's trusted callers supply rational widths/levels; this is not a
general floating-input integration API. Required positive measures reject
nonpositive results rather than replacing them or dropping a face.

### 6. Supported: coarea surface moments, new covariance and outward polygons

**Locators:** R253–254, R292–350, R444–490; T112–133, T157–178;
implementation note “Rounded oblique box cut”.

Differentiating a volume monomial in h gives
`M'_alpha=integral_face(t^alpha)dS/|c|`. Thus area is `|c|*M'_0`; centroid
and surface-average covariance are ratios cancelling the same constant.
The stored normal `(c/n2)*sqrt(n2)` equals `c/|c|`. Fixed physical-wall
fragments use the corresponding two-dimensional cut/complement and coordinate
normal; their fixed-coordinate covariance entries are zero. Dimensions are
area L², V L³, covariance L² and integrated J L⁵ even though h has dimension L².

For the base shared hexagon, centre-to-adjacent-vertex triangles have mean
squared radius `(1/2+1/2+1/4)/6=5/24`. Coordinate symmetry and fixed coordinate
sum give covariance diagonal `5/72` and off-diagonal `-5/144`. This independently
supports the new manual observation. **No parent covariance gate is added or
accepted:** a later comparator must register its tolerance explicitly before
using this quantity for acceptance.

Analytic edge/plane intersections enumerate vertices without candidate clipping
or hull construction. Exact polar sorting around the positive-measure centroid
orders these convex faces. Cyclic tangent axes fix outward coordinate-normal
orientation; a negative normal reverses the loop. For the shared face, `c_z>0`
makes xy projection nonsingular and fixes the positive orientation. Rebuilding
loops in the permuted coordinates supplies outward winding for odd permutations;
an old loop is not blindly copied. Lexicographic rotation changes no orientation.
This argument is confined to the registered convex positive-coefficient family,
not arbitrary degeneracy/topology certification.

### 7. Supported artifact semantics; execution/staging remains a prerequisite

**Locators:** R496–581; implementation note “Artifacts, controls and execution
boundary”; design `/gates`.

The unchanged design digest is checked before parsing. Its exact transformation
families, one registered name, selected fixture, aggregate counts and unique
face keys are checked. Inputs contain actual bit words/IDs, reference contains
their exact mathematical target and a digest of the serialized input buffer,
and status pins the script source. Design bytes are checked again before
successful completion. The finally block writes status and a body hash/length
manifest; numerical/validation exceptions retain `status=failed`, exception
type/message and propagate nonzero. Early CLI/output/source-read or final I/O
failure can prevent a complete envelope; no universal filesystem/process
recovery is claimed. A later runner must require actual process success,
complete status and exact allowlisted artifacts, rather than trusting a
partial `reference.json` or a `complete` status whose manifest write failed.

Reference output preserves the existing fixed V/Lref/reference-area
normalizations as declarations by copying the original gates and recording
actual Lref. This script **does not execute a candidate error reducer or any
gate comparison**. Exact values/enclosures must drive the later reducer near
a gate; a rounded reference word or candidate-dependent scale cannot replace
them. `candidate_invoked=false` and `component_accepted=false` remain explicit.
Source/runtime immutability, same-generation byte acquisition and safe closed
workflow packaging belong to the future immutable runner/output boundary;
this small fresh-directory writer is not an adversarial-storage verifier.

### 8. All 15 written controls reviewed; none executed

The following are direct methods in
`test_galaxy_geometry3_reference.GeometryReferenceArithmeticTests`, each requiring
its own workflow after actual import/preflight. Module search path/command must
resolve the sibling reference module on REANA; import success is not inferred
from source reading.

| Exact method suffix | T lines | Independent expectation / scope |
| --- | --- | --- |
| `test_exact_binary64_words_and_finite_decoding` | 18–28 | Fixed words, minimum normal, 1/10, signed-zero decode. |
| `test_midpoint_ties_choose_even_significand_and_carry` | 30–36 | Even/odd ties, power-of-two carry and negative symmetry. |
| `test_gradual_underflow_and_minimum_normal_midpoint` | 38–45 | Subnormal lattice, zero sign and normal transition. |
| `test_largest_finite_and_infinite_rounding_boundary` | 47–56 | Exact finite maximum, midpoint overflow and nonfinite rejection. |
| `test_radical_enclosures_and_rational_roots` | 58–74 | Fixed squared irrational target plus enclosure; converter agreement is a consistency check, not a second converter. |
| `test_oblique_volume_centroid_and_all_central_moments` | 76–82 | Frozen manual V/c/all J entries. |
| `test_complement_oblique_moments_and_full_box_limit` | 84–95 | Complement and unequal-coefficient full box. |
| `test_general_diagonal_simplex_before_first_upper_bound` | 97–110 | Unequal-coefficient simplex, independent scaled-tetrahedron formula. |
| `test_coarea_hexagon_centroid_and_covariance` | 112–122 | Fixed coarea weight/centroid and new manually derived covariance. |
| `test_oblique_wall_square_triangle_and_complements` | 124–133 | Four frozen area/tangent-centroid controls. |
| `test_registered_catalog_has_all252_unique_transformations` | 135–144 | Intended exact cross-product coverage; not evaluation of its references. |
| `test_permutation_preserves_original_id_and_changes_all_domain_axes` | 146–155 | Asymmetric box axes/position and original ID. |
| `test_complete_base_oblique_reference_has_independent_face_covariance` | 157–178 | Complete base records/counts/offsets, covariance and fan orientation. |
| `test_complete_periodic_self_face_keys_retain_two_incidences` | 180–192 | Three full self keys, both signs per face. |
| `test_changed_design_is_rejected_before_reference_evaluation` | 194–200 | Changed design and malformed rational rejection. |

The unequal-coefficient direct controls cover a simplex before upper bounds
and the full-box limit, rather than a fixed independently tabulated unequal-
coefficient partial cut. The manual inclusion-exclusion derivation above
supports that branch, but numerical evidence remains absent. Full translated
reference outputs, complete image joins, polygon/covariance checks, reference
uncertainty and candidate comparisons still require independent output review.
The written suite is not exhaustive arithmetic verification or a passing
252-case catalog. No speculative extra acceptance threshold or source-repair
cycle is required by this review.

## Exact identities, checks and next action

| Frozen subject | Bytes | SHA256 |
| --- | ---: | --- |
| `scripts/galaxy_geometry3_reference.py` | 28394 | `2b9f55d5ed72a08a90c3445fcd62b7702598174e04603e7ecd0d672c387df2df` |
| `scripts/test_galaxy_geometry3_reference.py` | 11336 | `1d764a5e69a245711c3427a8786d18cb6f596ec6e08d3f02dc9ebea62d2c36e7` |
| `docs/galaxy/GEOMETRY_REFERENCE_IMPLEMENTATION.md` | 10962 | `af985d63403149f96b1ed437ace4acec0f5799ea0562dab6f801a404a6eb98d5` |

The unchanged design is 12665 bytes, SHA256
`69fd92fc2009df207d076441527161825eb50ae911a2ec2a8e398d687306f288`.
Five complete frozen byte copies and identity-only context receipts are retained
under `results/geometry_reference_source_review_20261122/`; the companion
[inventory](geometry_reference_review_sources.json) pins their scopes and
closed reading manifest. Existing historical trees are referenced by exact
identity, not duplicated or falsely described as retained copies. Neither
review output hashes itself or the other; completion pins both final hashes.

Performed only: complete subject reading, frozen Git-byte/hash comparisons,
source/JSON/lexical-method/link/whitespace inspection and manual symbolic
reasoning. The 33 recorded static checks returned 0 with no metadata errors;
the lexical method count is 15, not an observed test-harness catalog.
Required project documents were previously read and their current
delta from `0599b8e` was checked empty. One context read returned 1 because
`M2A_SOURCE_REPAIR_REVIEW.md` was a mistaken filename; the actual
`M2A_SOURCE_REVISION_REVIEW.md` was located and read completely. That failure
and correction are retained. No target import, arithmetic/reference/fixture
evaluation, test, candidate geometry, build/formatter/compiler, probe, network
or workflow action occurred. There is **no actual reference result yet**.

Proceed with a coherent immutable REANA import/arithmetic prerequisite, then
15 methods and 252 reference cases independently, prospectively 1 CPU/thread,
2 GiB, 300 seconds each with no aggregate cap. Preserve exact source/design,
commands, actual expanded bit arrays, status/manifests, resource/runtime and
terminal/download identities, including failures. Candidate comparison additionally
requires its own successful immutable compile/build prerequisite and independent
input/reference/output review. G02/G03/G04, moving geometry/GCL/events/operators,
bounded MHD, gravity/active sources and the full-duration merger retain their
existing gates. This recommendation grants no scientific/component acceptance.
