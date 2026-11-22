# Exact references for the registered rounded G01 problems

2026-11-22. `scripts/galaxy_geometry3_reference.py` and its15 written controls
are source for independent review. No input expansion, reference evaluation,
new test, numerical probe or candidate geometry has been executed in this
author task. M1's accepted fixed/rigid2.5D prerequisite is closed; geometry,
moving3D MHD and the complete live-component merger retain their own gates.

The script implements the missing exact-input/reference arithmetic for the
seven manually reviewed [analytic designs](fixtures/geometry3_analytic_v1.json).
It pins that unchanged design's SHA256
`69fd92fc2009df207d076441527161825eb50ae911a2ec2a8e398d687306f288`.
Its implementation is independent of the Rust candidate's clipping, homogeneous
Cramer vertices, cap hulls and tetrahedral integration. It imports only Python
standard-library integer/rational/JSON/file/CLI facilities, with no candidate
module, native extension, mesh backend, random draw or general polyhedron
integrator. The seven manual derivations in
[the fixture README](fixtures/README.md) and independent findings11–12 in
[the original fixture review](BOUNDARY_MHD_DESIGN_REVIEW.md) remain the parent
expectation map. New formulas below are explicit independent derivations,
with review and actual REANA arithmetic evidence still required.

## Input and transformation contract

The registered cross product has252 independently named cases: seven fixtures,
three exact scales, six coordinate permutations and two translations. A name is
`<fixture>__s<scale-index>__p<permutation>__t<translation-index>`. Indices0,1,2
select scales `1/1000000,1,1000000`; translation index0 is zero and1 is
`(371/1000,-219/1000,443/1000)` in the scaled, permuted domain side lengths.
Backend comparison, jitter/slivers, points-only periodic seams, storage order,
threads, repeated builds and moving geometry retain their separate cases.

For permutation p, scale s, original anchor a, width L and translation vector t,
compose the following exactly as rationals, then round each final scalar once
to nearest ties-to-even IEEE binary64:

```text
delta_j = t_j*s*L_(p_j)
a'_j = RN(s*a_(p_j)+delta_j)
L'_j = RN(s*L_(p_j))
x'_(i,j) = RN(s*x_(i,p_j)+delta_j)
```

The original namespace and x-fast counter stay attached to each generator.
Images and all geometric axes use the permuted coordinate system. Inputs store
16-digit lowercase binary64 words and32-digit namespace-first ID text. Domain
widths stay independent input words: a physical upper wall is the exact sum
of the rounded anchor and width. The script checks the additional finite,
strictly increasing rounded-upper-bound precondition of the current candidate.
Each generator must remain strictly interior to these particular fixtures.

The existing28 Rust controls use their own expression-evaluated input bytes,
including multiple rounded operations in some transformed cases. This252-case
packet defines the registered exact-composition/one-round family. Its future
outputs do not retroactively certify a different input bit array. Actual bit
logs and source/preflight identities must bind whichever problem is compared.

## Integer conversion and certified reference words

`binary64_bits` finds the exact rational's binary exponent with integer bit
length/comparison. It scales an integer quotient/remainder to53 significand
bits, rounds an exact midpoint to an even integer, and handles carry into the
next exponent. Below the normal range it rounds on the fixed `2^-1074` grid;
negative underflow preserves negative zero. An overflow to infinity rejects
the input/reference. Exact rational zero has the canonical positive-zero word.
`exact_binary64` performs the inverse finite-bit interpretation as a rational,
with either signed zero representing mathematical zero. No host float/libm
conversion supplies the independent rounded word. This is newly written
arithmetic, not a formal verification or an observed successful rounding test.

All polynomial moments and centroids are exact reduced rationals. Face areas
and normals with an irrational square root retain `factor*sqrt(radicand)`.
For positive rational `radicand=N/D`, integer arithmetic gives

```text
kroot = isqrt(floor(N*2^(2b)/D))
kroot/2^b <= sqrt(N/D) < (kroot+1)/2^b
```

Perfect rational square roots are detected first. Otherwise the factor-scaled
endpoints bound the exact algebraic value, including negative factors. Both
endpoints must round to the same finite binary64 word. The script starts with
b=256 and can refine to512,1024,2048,4096; unresolved rounding rejects export.
The exact enclosure remains in the record. It is not an uncertainty inferred
from agreement of two approximate evaluations.

A later independent reducer can decode candidate output words to rationals
and compute exact rational errors, or conservative error bounds from the
algebraic interval. A rounded reference word alone must not replace its stored
exact value/enclosure when an error is near a gate. Use fixed reference V and
Lref in the parent's moment/centroid norms and positive reference face areas
for relative errors. No normalization uses a candidate value or a tuned floor.

## Cartesian references

After rounding, each tensor input remains an exact Cartesian product, with
possibly perturbed axis spacings. Its periodic intervals are adjacent actual
axis midpoints, using the nearest translated endpoint at each seam. A single
generator's interval is `[x-L/2,x+L/2]`. Their Cartesian products give V,
centroid and `J_aa=V*h_a^2/12`, `J_ab=0`. Face rectangles give their actual
area, midpoint, outward signed unit axis and surface-average covariance
`h_tangent^2/12` on tangent diagonals. The bounded one-generator case uses
the actual physical box, independently of the generator's location.

Each neighbour retains the complete owner/image key. Lower-ID owners provide
canonical shared data; a self-image uses the positive image and both+/-
incidences. IDs retain the original point ordering through permutations.
Canonical face sorting and incidence signs follow the shared contract rather
than candidate array indices. Reference polygons are ordered explicitly in
cyclic coordinate tangents with outward orientation.

## Rounded oblique box cut

Translated/scaled generator rounding can perturb each component of the
bisector differently. For actual rounded g0,g1 and actual anchor a/width w,
set local t=x-a and

```text
c_j = g1_j-g0_j > 0
h = sum_j ((g1_j^2-g0_j^2)/2 - c_j*a_j)
D = {0<=t_j<=w_j, sum_j c_j*t_j<=h}.
```

The lower cell is D and the upper is its exact box complement. Let
`u_j=c_j*t_j`, `b_j=c_j*w_j`. For every subset S of violated upper bounds,
shift `u_j=v_j+b_j` for j in S, multiply by `(-1)^|S|`, and expand the
degree-at-most-two monomial by the binomial theorem. Each remaining term
uses the exact simplex integral in dimension d:

```text
integral_(v>=0,sum v<=H) product(v_j^beta_j) dv
 = product(beta_j!)*max(H,0)^(d+sum beta)/(d+sum beta)!
```

Divide by `product(c_j^(alpha_j+1))` for the original t monomial. This gives
V, first moments and all raw second moments, then exact central J. Upper-cell
raw moments subtract the lower moments from the full rectangular box before
centralization. The method is a finite formula, with no approximate quadrature,
tetrahedral integration or generic face clipping.

The coarea identity gives shared-face moments by differentiating the same
polynomials with respect to h. If M_alpha are the volume monomials, then
`integral_face t^alpha dS=|c|*M'_alpha(h)`. Area is
`sqrt(sum c_j^2)*M'_0`; centroid and surface-average covariance are the ratios
in which this constant square root cancels. The unit normal is c/|c|. Each
physical boundary fragment is the analogous two-dimensional box cut or its
complement at the fixed wall coordinate, with the physical wall normal.
Analytic edge/plane intersections enumerate the shared hexagon and wall
polygons; exact polar ordering around their independently computed centroids
supplies outward loops. No convex-hull/clipping candidate is called.

At the exact untransformed oblique case, the shared regular hexagon also has
an independent covariance expectation. Its six centre/edge triangles have
vertex radius squared1/2 and adjacent-radius dot product1/4, so the barycentric
second-moment formula gives mean squared radius `(1/2+1/2+1/4)/6=5/24`.
Symmetry and the fixed sum of coordinates imply diagonal covariance5/72 and
off-diagonal covariance-5/144. This is a new manual reference derivation,
requiring independent review and REANA confirmation; it is not an extra
silently accepted parent gate. A later reducer must explicitly register any
covariance acceptance tolerance before using those observations for acceptance.

## Artifacts, controls and execution boundary

One future invocation selects exactly one case, for example:

```text
python3 scripts/galaxy_geometry3_reference.py --design docs/galaxy/fixtures/geometry3_analytic_v1.json --case bounded_oblique_bisector__s1__pxyz__t0 --output <fresh-case-directory>
```

It writes actual `input.json`, independently derived `reference.json`, typed
`status.json` and a body `sha256.json` manifest. The reference binds the input
bytes; status binds the script source. The design is verified before and after.
Every required positive cell/face count and total incidence count must match
the original design after rounding, or reference generation fails. No required
case passes through ambiguity/rejection. Successful reference generation keeps
`candidate_invoked=false` and `component_accepted=false`.

Each of252 reference cases needs its own REANA workflow after reviewed source
and immutable source/import preflight, prospectively1CPU/2Gi/300s, with all
ready cases concurrent and no aggregate cap. Actual resource use remains
unmeasured. Safe source/input staging, authoritative terminal/download receipts,
actual artifact acquisition and independent numerical-output review remain
required; writing this source performs none of them. Candidate comparison
workflows additionally require the accepted source/build prerequisite, exact
candidate binary/source/input pins, independently frozen references and all
parent G01/G02/G04/operator/moving gates appropriate to the claimed scope.

The15 direct `GeometryReferenceArithmeticTests.test_*` methods in
`scripts/test_galaxy_geometry3_reference.py` cover exact words, ties/carry,
gradual underflow, finite overflow boundary, radical enclosures, oblique volume/
J/complement and full box, general positive-coefficient simplex moments,
coarea covariance, wall moments, all252 transformation identities, preserved
IDs/axis permutation, full base oblique polygon orientation, periodic self-face
incidences and changed-design rejection. Each method is a separate future
REANA case. They use standard-library exact arithmetic and manually derived
constants, with no candidate implementation; all remain unexecuted.
