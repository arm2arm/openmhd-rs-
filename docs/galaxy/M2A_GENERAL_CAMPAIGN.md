# Registered general static-geometry campaign

This source preparation extends M2a G02–G04. It is not an executed campaign
or acceptance. The original analytic G01 bridge, reference, comparison and
candidate Rust geometry remain unchanged. The exact gate registration is
[`fixtures/m2a_general_gates_v1.json`](fixtures/m2a_general_gates_v1.json).

## Inputs and scope

The input-definition module is
[`galaxy_geometry3_general_fixtures.py`](../../scripts/galaxy_geometry3_general_fixtures.py).
Jittered 4³, 6³ and 8³ lattices use seed 20261122 and a counter-based SHA256
mapping fixed in the registration. Each axis is displaced by at most 0.15
spacing. Exact rational coordinates are rounded once to binary64 before any
candidate or independent-reference calculation. The actual serialized words
must be retained and compared, not regenerated separately by the two solvers.

Additional periodic arrays specify a 64-point Cartesian background with eight
clustered points, three 4×4 layers separated by 1e-5, and a 3³ boundary-near
array at coordinates 1e-8, 1/2 and 1−1e-8. These six G02 families require
successful positive geometry; uncertainty or resource rejection is a failure
to close G02 for that fixture.

G03 adds two-generator separations of 1e-4, 1e-8 and 1e-12, an exact
co-spherical cube, and coplanar/near-coplanar arrays. Existing Rust API tests
retain the duplicate-ID/coincident-position, invalid-domain, nonfinite,
empty/oversized, boundary-leaving and overflow checks. Every new difficult
case must retain success or the actual supported typed ambiguity/error;
generic failure, panic and missing output never become accepted rejection.

G04 fixes base, reverse-order, SHA256-ID shuffle, repeat, translated-domain,
periodic-seam and multiple-winding variants, each at 1/2/4 declared threads.
The implementation remains serial; varying the thread environment tests
reproducibility and does not claim a parallel speedup. Wrapped coordinates
and integer windings represent the same uniformly translated trajectories.
Canonical full trajectory keys must agree away from zero-area events.
Bitwise equality is reported separately from normalized agreement. Exact
contact cases retain their event/ambiguity accounting.

## Independent reference and its certificate

The new reference uses SciPy/Qhull solely to **propose** intersections of
supporting planes. Its API exposes the halfspaces forming each dual facet;
the reference does not consume the Rust mesh or its topology.
See the primary [HalfspaceIntersection documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.HalfspaceIntersection.html).
The actual remote NumPy/SciPy versions are recorded in every reference result.

All actual input coordinates are dyadic rationals. Choose a common power-of-two
denominator D and integer generator coordinates P. In owner-local integer
coordinates u, every neighbour image gives the exact constraint

$$2d\cdot u\leq d\cdot d,\qquad d=P_j+kL-P_i.$$

Self images give the initial box |u_a|≤L_a/2. A neighbour constraint is
redundant on that entire box when d·d≥Σ|d_a|L_a; its removal is certified by
this exact integer inequality. No distance heuristic or candidate neighbour
list is used.

Proposed vertices are recomputed by integer Cramer's rule and checked against
every retained halfspace. Exact active-plane sets define planar convex
polygons. Certification requires outward faces, once-per-direction paired
edges, connected surface, Euler characteristic two, connected cyclic links
at every vertex and positive origin-based tetrahedra. Each polygon lies on
an original supporting halfspace. These checks certify the closed convex
boundary rather than trusting Qhull's floating metrics. Any unresolved
proposal rejects the reference instead of exporting partial geometry.

For a tetrahedron with vertices 0,a,b,c, independently integrate

$$V=\det(a,b,c)/6,\quad
\int x\,dV=V(a+b+c)/4,$$

$$\int xx^{\mathsf T}dV=
\frac{V}{20}\left(aa^{\mathsf T}+bb^{\mathsf T}+cc^{\mathsf T}
+(a+b+c)(a+b+c)^{\mathsf T}\right).$$

Central moments follow by subtracting V times the centroid outer product.
Face moments use exact projected triangle weights. Areas use the norm of the
exact oriented area vector. Rational results and square roots receive outward
160-bit dyadic enclosures; reference uncertainty is independent of candidate
agreement and is included in every reported upper error bound.

The reference requires exact summed domain volume and reciprocal periodic
face coverage. Source controls include literal cube volumes/centroids/moments,
co-spherical and coplanar cells, enclosure proofs, missing-corner rejection,
ID/order preservation, winding equivariance and parser failures. Each control
requires its own actual REANA workflow after immutable import preflight.

## Remote task entry points

[`run_geometry3_general.py`](../../scripts/run_geometry3_general.py) provides
four separate REANA task entry points:

```text
python3 -B scripts/run_geometry3_general.py fixtures --output literal-packet
python3 -B scripts/run_geometry3_general.py reference --input input.json --output reference-packet
python3 -B scripts/run_geometry3_general.py compare --input input.json --candidate candidate.txt --reference reference.json --output comparison-packet
python3 -B scripts/run_geometry3_general.py reproducibility --left-input base.json --left-candidate base.txt --right-input transformed.json --right-candidate transformed.txt --output reproducibility-packet
```

These are remote invocation examples, not results of local executions. The
fixture task freezes all **84 distinct actual input arrays** and the **252
per-thread case selections** before either geometry implementation runs. Both
implementations must consume those retained words. Each reference, candidate
and reduction retains its exact input identities and executed source hashes.

Every completed task publishes a closed file manifest and a bounded compressed
packet. The complete status is published last. Failures preserve captured
inputs and any computed failing reduction in a separately labelled failure
packet; they do not produce a successful packet. Output directories are fresh
and input reads reject symlinks and changing generations. These internal links
do not prove authoritative workflow/build/prerequisite provenance; the host
must verify those separately before using a packet as a gate result.

The registered `m2a-general` cohort now has **22 direct methods**: the original
16 mathematical/transport controls plus six literal-catalog, closure,
single-cell reference, failure-retention and input-safety controls. All remain
unexecuted until the actual immutable REANA import parent and their individual
workflows run. Their written existence does not close a numerical gate.

## Unchanged gates and dependencies

Total relative volume and Euclidean normal closure retain 1e-10 limits.
Independent volume/centroid/area/normal/moment errors and tensor/centroid
identities retain 1e-9. Reproducibility retains 1e-10 and exact canonical keys.
The normal-closure calculation uses a squared norm and a squared threshold;
it does not replace a Euclidean gate with a looser component bound.

The larger workspace regression gate must pass before the long geometry
matrix starts. Source/import capability and small arithmetic controls may be
prepared and qualified meanwhile. Initial resource envelopes remain those in
the mesh specification; resource calibration may increase declared resources
prospectively without changing fixtures, thresholds or required successes.
M2b operators and M2c moving geometry/MHD remain separate downstream work.

## Executed controls and frozen inputs

On 2026-11-24 REANA executed all 22 registered control methods. The first
collection verified 18 methods. Fresh downloads supplied three missing
output proofs. One replacement supplied the remaining method after its
original workflow stayed pending with no job. Each passing output identifies
one exact method with zero errors, failures or skips.
[Method identities and output hashes](results/m2a_recovery_20261124/general_controls.json).

The fixture workflow then froze **84 input arrays and 252 thread selections**.
The [literal packet](results/m2a_recovery_20261124/literal_packet.tar.gz)
contains the exact generator words, catalog and file manifest. The
[acquisition record](results/m2a_recovery_20261124/literal_packet.json) pins
the terminal workflow UUID and packet hash. G02–G04 still require the actual
independent references, native exports and comparisons after G00 passes.

The [general candidate entry point](../../reana/general_geometry_candidate.py)
checks its input against this catalog and uses the same 727,792-byte Rust
executable as the 252 G01 comparisons. It records the original stdout, stderr
and child-process result, including the Rust error variant on a typed rejection.
This entry point awaits its REANA execution check.

To stage the 84 reference and 252 candidate workflow specifications, pass the
recorded G01 executable to the preparer and choose a fresh output directory.

```sh
python3 -B scripts/prepare_general_geometry_jobs.py /path/to/geometry.part0000 results/m2a-general-jobs
```

Preparation checks the executable, frozen literal packet and source hashes.
Each reference consumes one literal array. Each candidate receives its named
array and thread count. The complete matrix still depends on G00 and resource
calibration.
