# Independent static 3D oracle source review

2026-11-22. Reviewed subject **`ba49c54dca152505ce42e29e60ff32013ca2fa87`**.
Disposition: **repair the integration-test trait mismatch before the coherent
all-target preflight; strengthen the arithmetic control and use the frozen
reference area in relative checks.** The small static comparator is suitable
for subsequent REANA falsification after those source corrections and root
integration. This is not a build result, a proved general-purpose geometry
kernel, numerical geometry acceptance or permission to couple moving MHD.

I authored the separate identity crate. Here its pinned `8a25ebf` declarations
are inspected only as the geometry dependency's interface; I do not independently
approve that component. Its source/execution review belongs to the separate
reviewer. The geometry implementation was authored by another worker.

M1 is accepted at `309ae41` only for its named iterative periodic,
single-process fixed/rigid 2.5D profile. Its evidence remains unchanged. The
static oracle, all 28 new selectors, gravity and the full moving-3D live
magnetized gas/DM/old/new-star merger retain independent gates.

## Numbered findings and dispositions

### 1. High — both integration-test targets require an unimplemented Display trait

**Locations:** `tests/geometry3_analytic.rs:23`,
`tests/geometry3_controls.rs:23`; dependency `galaxy-types/src/identity.rs`
at `8a25ebf`, lines 43–47 and 101–112; dependency root re-exports in `src/lib.rs`.

Both `println!` calls supply `g.id: CellId` for `{}`. The pinned dependency
implements `Display` for `EntityId`, not `CellId`; the wrapper derives include
`Debug` but not `Display`. No other dependency module supplies that trait.
This is a statically visible trait mismatch, not a newly observed compiler
failure. It prevents compiling the two integration-test targets as delivered;
it does not demonstrate a failure to compile the oracle library by itself.

**Smallest fix:** change those arguments to `g.id.entity()`, preserving the
canonical 32-hex-digit input witness and the fixed shared API. Do not change
identity constructors, weaken a test, or widen the identity API to conceal the
geometry caller error. Root workspace/lock integration is separately required.
**REANA:** the immutable all-target compilation preflight must compile both
test targets before any of their 24 cases is launched. The four library
predicate cases remain separately selected, not evidence that the integration
test targets compiled.

### 2. Medium — the carry control does not exercise overlapping multiplication rows

**Locations:** `exact.rs:113–131`, `exact.rs:230–237`; the other three direct
predicate tests at lines 210–247.

The carry test uses `a=2^32-1` and `b=2^32`. After normalization, both have
one limb: `a` is one full limb, `b` is one limb with exponent 32. This checks
a carry out of a one-by-one-limb product, but not the existing-word plus carry
accumulation at line 122 across multiple outer rows. The other direct tests
cover cancellation, signed zero/subnormals and small determinants, rather
than supplying that missing product case. This is a concrete test-coverage
gap, **not evidence that multiplication is wrong**.

There is source-level support for the loop: with base `B=2^32`, its largest
accumulator is `(B-1)^2+(B-1)+(B-1)=B^2-1`, fitting `u64`. At row `i`, tail
slot `i+q` has not been written by an earlier row, whose maximum index is
`i+q-1`. Thus the tail assignment need not add an old word. That local
argument does not formally verify the entire arithmetic implementation.

**Smallest fix:** extend the existing carry selector with a genuine multi-limb
operand, for example construct `a=2^64-1` by exact subtraction and independently
assert `a^2=2^128-2^65+1`. Include an overlapping-row carry and multi-limb
borrow/alignment identity; do not initialize the unrepresentable integer
`2^64-1` through a rounded f64 literal. The subnormal selector can also cover
negative finite decoding, not only negative zero. These can remain bounded
controls within the existing methods. **REANA:** run each strengthened
predicate method independently; retain the exact source identities and outcomes
before treating predicate accuracy as supported. None has run here.

### 3. Low — use the fixed analytic face area as the relative-error denominator

**Locations:** `geometry3_analytic.rs:62,150,180,194` and
`geometry3_controls.rs:39`; fixture JSON `/gates/positive_face_area_relative_max`.

These `close` calls use the candidate face area as `scale`. For positive
candidate `a`, reference `e` and `tau=1e-10`, the test checks
`|a-e| <= tau*a`, permitting a reference-relative error as large as
`tau/(1-tau)`. The difference is order `tau^2`; it is not a claimed material
observed error, but it is a different normalization from the frozen analytic
relative-error gate. The other dimensional J/centroid tolerances use fixed
reference scales as required, including `V_expected*Lref^2` for zero cross terms.

**Smallest fix:** bind `expected_area` and pass that same positive reference
value as the third argument in each listed call. Keep `tau=1e-10`, all fixture
constants, positive-face counts and rejection behavior unchanged. **REANA:**
the existing seven analytic and three oblique transformation cases then
exercise the corrected assertions; no new geometry fixture is needed for
this source correction.

### 4. Supported conditionally — exact clipping and the static periodic inventory are coherent

**Locations:** `exact.rs:22–131,163–203`; `clip.rs:36–155,171–260`;
`oracle.rs:27–93`; mesh contract §§3.1,4.3.

The decoder uses the correct normal and subnormal binary64 dyadic exponents,
normalizes either signed zero to exact zero, and preserves a separate sign.
Opposite-sign addition selects unsigned magnitude before borrowing. In-place
low-bit normalization proceeds upward, so the upper word it reads has not yet
been modified. Subject to bounded arithmetic correctness, no floating epsilon
participates in side, equality, hull or orientation predicates.

For `N*y=h`, Cramer's rule replaces a column for each coordinate numerator.
`intersection` flips numerator and denominator together when necessary,
making denominators positive. Therefore `n·numerator-h*denominator` has the
correct side sign. The projected orientation determinant also has the
Euclidean orientation sign because all three denominators are positive;
cyclic projection supplies the selected normal-component sign. Strict edge
crossings use two independent common supports plus the new plane. Singular
support pairs are skipped while searching that same edge, with exhaustion
rejected. Exact contacts add support and are not automatically faces.

The hull removes only equal/collinear points, and a strict cut requires a
positive cap. Final exact checks require supporting-plane membership,
containment in **all** original planes, two oppositely oriented uses per
edge and Euler closure. These facts are consistent with the convex clipping
construction; they are not a formal verification of arbitrary input degeneracy.

For wrapped orthorhombic inputs, write `delta_a=x_j,a-x_i,a`. In the own-image
box, `y_a` is in `[-L_a/2,L_a/2]` and `delta_a` in `(-L_a,L_a)`. A nearest
integer image for `(y_a-delta_a)/L_a` lies in `{-1,0,1}`. Euclidean squared
distance separates by coordinate, so the retained 27 images contain a nearest
image for every point in the box. Own diagonal images may make lower-dimensional
contacts; they do not create extra positive-area faces. Bounded cells instead
start from the actual six wall planes and use all other real generators.
This supports the **static orthorhombic** inventory, not a moving/skew domain
certificate. **REANA:** the four arithmetic cases and seven required fixtures
must still falsify these source arguments independently, followed by G02/G03
near-degenerate and reference comparisons. A typed rejection cannot pass a
required Cartesian case.

### 5. Supported conditionally — full keys, reciprocal charts, moments and exported checks

**Locations:** `types.rs:20–62,94–134`; `oracle.rs:35–46,133–155,160–210,256–294`;
`moments.rs:54–211`.

For `X_i=x_i+L*k_i` and `m=s+k_i-k_j`, the displacement identity is
`X_j+L*m-X_i=x_j+L*s-x_i=d`. The code uses the correct sign: right local
points translate by `+d` for exact comparison in the left chart, and the right
exported incidence stores `-d`, `-m` and sign `-1`. Checked i128 intermediates
permit equal extreme windings to cancel before conversion to i64. Distinct
owner/image keys preserve parallel seam faces. Self-images have two geometric
incidences on the same real owner; no extra real entity is created.

Reciprocal faces require the same exact rational vertex set after translation,
opposite normals, and agreement of area/centroid/covariance before selecting
the canonical left metrics. Incompatible pairs are rejected, not averaged.
The projected hull fixes winding and starting vertex deterministically.

The volume and first moment use outward signed generator-pivot tetrahedra.
For simplex vertices `p_i`, barycentric integration gives
`E[xx^T]=(sum p_i*p_i^T+(sum p_i)*(sum p_i)^T)/((d+1)*(d+2))`.
The code's denominators 12 (surface triangles) and 20 (volume tetrahedra) are
correct. It shifts vertices by the integrated centroid before central-moment
accumulation. Area, volume, covariance and integrated J restore dimensions
with `Lref^2,Lref^3,Lref^2,Lref^5`, respectively.

The centroid identity is appropriate: on a planar face `y·n` is constant,
so face-centroid quadrature for `y*(y·n)` is exact; the divergence theorem
gives `4*integral_cell y=0`. Normal, affine, centroid and divergence-volume
checks are repeated using the **exported single shared metrics** and both
self-image charts. V/J are not repaired to force closure. Global volume and
all six bounded patch areas have additional checks. Independent oblique
surface-covariance expectations and general error enclosures remain absent,
as the author discloses. **REANA:** retain independent all-component J/face
comparisons, both chart incidences and quality logs; internal closure alone
is not an independent accuracy reference.

### 6. Supported base-fixture coverage; full G01/G02/G04 coverage is not delivered

**Locations:** analytic test file in full; controls file in full; fixture JSON;
historical `BOUNDARY_MHD_DESIGN_REVIEW.md:547–669`, findings 11–12.

The seven base point sets, namespaces, x-fast counters, interval endpoints,
volumes, centroids, all J entries and counts match the frozen manual formulas:

| Case | Expected canonical faces / incidences | Independent expected construction |
| --- | --- | --- |
| Periodic one cell | 3 / 6 | Unit cube around generator, self images `+e_a`, J diagonal `1/12` |
| Periodic 2³ | 24 / 48 | Width `1/2` product, three neighbour IDs but six image incidences |
| Periodic nonuniform 3×2×2 | 36 / 72 | x widths `5/16,5/16,3/8`, y/z width `1/2` |
| Periodic 4³ | 192 / 384 | Width `1/4` product |
| Periodic nonuniform 4³ | 192 / 384 | Widths `1/4,3/20,1/4,7/20`; first centroid `-1/40` in its image chart |
| Bounded 2×3×4 | 6 / 6 | Actual box, V=24, centroid `(0,-1/2,-1)`, J diagonal `(8,18,32)` |
| Bounded oblique pair | 13 / 14 | Cube split at `x+y+z=3/2`, both V=`1/2`, diagonal J=`599/18432`, cross J=`-169/18432` |

The tensor expected values use separable interval formulas; the oblique
references use independently derived constants/polygons from the frozen
packet. They do not call candidate clipping or integration to obtain expected
values. Every required fixture demands a successful build with `expect` or
`unwrap`; ambiguity, resource rejection and `UncertainMetric` cannot silently
pass it. The seven names are embedded via `include_str!`/`contains`, not a JSON
fixture interpreter. Byte pinning and this manual constant comparison bind
them to the current packet; a changed JSON would require another source check.

The source inventory is **7 analytic +17 controls +4 predicate=28 new
selectors**. Controls cover selected scale/anchor transforms, all six
anisotropic cuboid permutations, input order, owner/image reciprocity,
unequal/equal-extreme windings, handles and invalid inputs. The controls use
their own namespace 23; they are not literal ID-preserving expansions of
namespace-6/7 base fixtures. They also evaluate rounded f64 expressions rather
than a correctly rounded exact composed fixture expander. The report explicitly
retains that limitation. Do not call them the complete seven-by-transform
packet, a completed odd-permutation oblique test family, jitter/sliver accuracy,
or point-only seam-motion evidence. Oblique face covariance and the complete
independent literal/reference packet remain future inputs; no tolerance or
required case may be relaxed after observing results.

### 7. Nonblocking retained limits — conversion, conditioning, resources and immutable scope

**Locations:** `exact.rs:136–159`; `moments.rs:79–94,138–151,182–209`;
`oracle.rs:96–130,219–253,315–320`; `types.rs:64–92,147–187`; author report
“Validation, explicit limits and uncertainty.”

The leading-53-bit ratio conversion is not correctly rounded or enclosing.
It can reject a mathematically representable quotient because it scales through
an unrepresentable intermediate: `1/(3*2^-1024)=2^1024/3` is within finite
binary64 range, but line 155 forms `powi(1024)` first. This is a manual
range example, not a measured kernel failure. Keep the disclosed extreme-scale
limitation; `Unrepresentable` is a conversion failure, not proof that no finite
rounded answer exists. No wrong accepted metric follows from that example.

The area/tetrahedron filters reject the whole build rather than dropping a
positive face. Their operation-scale bounds and normalized J determinant
separation are engineering conditioning policies, not propagated interval
error certificates. A generator near a wall can make a valid shape unsupported.
The initial rounded upper-bound guard can also conservatively reject a valid
exact dyadic domain. These are disclosed limits, not passes for required
analytic cases. No source counterexample to their seven required builds was
established here; those outcomes remain unobserved.

The generator/face/vertex/support/limb/raw-vertex/predicate caps reject rather
than alter the problem. The predicate counter does not count every limb or
pairing operation; the report says so. All-pairs work and linear hull/pairing
searches may be expensive even below 512 cells. No measured 300-second/2-GiB
feasibility, G02 cost or scalable backend claim follows. There is no source
basis to call a valid required fixture rejection a passed resource test.

Build input is immutable, partial results remain local and the epoch is
allocated only after validation. Public geometry access is read-only;
detached clones of cell/face records do not mutate the validated object.
Epoch handles reject use on another successful rebuild; cloning the immutable
geometry preserves its epoch. Epochs are process-local, not restart tokens or
MPI identities. No persistent geometry codec/cache digest, differential operator,
moving geometry, GCL, wall-MHD state or physical source API is supplied here.

### 8. Concrete implementation disposition and remaining execution

Route findings 1–3 to the author; retain the original reviewed bytes. Then root
can integrate the independently reviewed identity dependency/workspace/lock,
freeze the coherent source and perform G00 on REANA. Source inspection found
no second definite Rust type error, but it is not a syntax/type/format/Clippy
pass: one-line bodies and indexed loops still need actual formatter and strict
Clippy review. Do not claim the written 28-method catalog resolves in a test
binary until actual build/harness evidence exists.

Run each source-derived independent case in its own REANA workflow, initially
1 CPU/thread, 2 GiB, 300 seconds as declared, with no aggregate cap and required
preflight dependencies. Preserve input bits, actual source/compiler/runtime,
quality, rejection and cost evidence. Review actual outputs against independent
fixture expansion/reference arithmetic before accepting static geometry.
G01's full literal transformations and G02/G03/G04 remain separate requirements.
No new abstract review cycle or additional physical threshold is introduced.
Moving C/Cdot/GCL/events, state-dependent motion, bounded U1–U4, gravity/work,
active ISM/SF/feedback, equilibrium components and the full-duration
domain-controlled magnetized merger retain their existing prerequisites.

## Exact reading boundary and performed checks

All ten code files and the author report were read from `git show ba49c54:path`,
retained under `results/galaxy_m2a_source_review_20261122/`. The full six new
modules and both integration test files were read; the old 2D lib/manifest
changes were checked as exactly their one-line module/path-dependency additions
relative to `2bdcea0`. All 18 identities in the author report were independently
matched. Thirty full subject/context/interface byte copies are retained; the
five required project documents match the previously read `15ae7f5` context
with an empty delta. Frozen AGENTS, operative integration/mesh sections,
fixture packet/README and the historical seven-fixture derivations were read.

The closed receipt has **38 entries excluding itself**:
`results/galaxy_m2a_source_review_20261122/reading_manifest.json`, 6806 bytes,
SHA256 `c4b854cdf711d84a13d2f74f0fd4d98fd86eb61813695631cece1d14a00f88c5`.
The companion [source inventory](m2a_source_review_sources.json) pins every
reviewed input, full commit, byte count/hash, exact selector/locator, manual
receipt and read-only check. The inventory does not hash itself or this report;
their final hashes are supplied in the worker completion message.

Actual checks: Git/source-byte comparisons, JSON parsing, lexical source selector
inventory (not target test enumeration), hashes, link/whitespace checks and manual
algebra/control-flow review. One initial source-count inspection returned 1:
it included five unchanged M1 `lib.rs` tests and asserted 28 instead of finding
33. A retained diagnostic identified the scope error; the corrected new-source
inventory finds 28 and all subsequent identity/whitespace checks return 0.
This was an inspection failure, not an executed Rust test. No target import,
guard/help, cargo/rustfmt/rustc, harness listing, build, test, geometry/reference
evaluation, numerical probe, reducer, evolution, network, service or workflow ran.
No primary-paper algorithm attribution is added: the half-space, simplex and
chart arguments above are explicit manual derivations of this project's
engineering comparator, not a claim of published AREPO/P26 construction.
