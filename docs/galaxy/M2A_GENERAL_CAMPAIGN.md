# Registered general static-geometry campaign

The original single-thread runs covered all twelve registered base inputs. Ten
meshes passed all eleven metrics, the nearly coplanar input returned a typed
metric ambiguity, and the largest jittered mesh exhausted the default predicate
budget. The calibrated build passed all eleven checks on eleven base inputs,
including the 512-cell mesh, and reproduced the nearly coplanar ambiguity.
The G04 clustered seam placement returned the same triangle-area error in
three independent workflows at one, two and four threads. This required
positive case blocks closure.
[Measured seam rejection](results/m2a_general_20261125/clustered-seam-rejection.json).
[Calibrated base results](results/m2a_general_20261125/calibrated-base-release.json) ·
[Original base results](results/m2a_general_20261125/base_results.json).
The original analytic G01 bridge, reference, comparison and
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

The workspace gate passed on November 25. The single-thread native driver
took **18.49 seconds for 64 jittered generators** and **242.20 seconds for 216**.
Quadratic scaling from 216 to 512 generators gives about 1,360 seconds.
Before launching the first 512-generator native workflow, the coordinator set
its wall limit to 3,600 seconds, with 4 GiB and the registered thread count.
Both timing measurements used the same executable as the analytic campaign.
[Timing receipts and resource decision](results/m2a_general_20261125/jitter8-resource-release.json).

### Measured base results

| Registered input | Rust and independent reference |
| --- | --- |
| Jittered 4³ and 6³ lattices | All eleven metrics passed. The Rust driver counted 19,766,864 and 273,641,682 predicate operations respectively. |
| Jittered 8³ lattice | The reference produced 512 cells, 4,063 faces and exact total volume. Rust returned `ResourceLimit("predicate operations")` after 215.25 s with empty stdout. The 3,600 s wall limit did not expire. |
| Clustered, sliver and boundary-near arrays | All eleven metrics passed for each input. |
| Separations of 1e−4, 1e−8 and 1e−12, co-spherical cube and coplanar array | All eleven metrics passed for each input. |
| Nearly coplanar array | The independent reference certified positive cells. Rust returned `UncertainMetric` for a tetrahedron volume of 1.8518558600158183e−14 against its separation bound of 1.9201955683198396e−14. G03 permits this typed outcome. |

The 512-generator run stopped on the shared 500,000,000-operation counter in
`three_d/clip.rs`. The oracle clips against the periodic image constraints
for every owner and then tests every final vertex against all its constraints.
A positive mesh remains mandatory for this G02 input. Its reference and all
native stdout, stderr, command status, workflow observations and executed
comparison packets are retained together.
[Base workflow receipts](results/m2a_general_20261125/base_workflow_receipts.tar.gz).

### Calibrated build

REANA built both the default driver and the opt-in `large-geometry-budget`
driver from revision `95d4d8d` with Rust 1.85.1. Workspace formatting, strict
Clippy, release compilation and test discovery returned zero. Discovery listed
676 tests in 114 executables. The optional build allows up to 2.5 billion
predicate operations. Its runner verifies the executable SHA-256, records the
build UUID, and pins the same executable for both runs in a reproducibility
comparison. The frozen input words and comparison limits also apply to this
build. [Build record and executable identities](results/m2a_general_20261125/predicate-budget-build.json) ·
[REANA build receipts and both executables](results/m2a_general_20261125/predicate-budget-build.tar.gz).

With the opt-in executable, the 8³ jittered mesh used 1,907,489,046
predicates and took 810.54 seconds on one declared CPU. Rust returned 512
cells and 4,063 faces. The comparison workflow verified identical topology
and all eleven metrics against the 19,935,200-byte independent reference.
The upper bounds were 2.17 × 10⁻¹⁹ for relative total-volume error,
2.09 × 10⁻¹⁶ for maximum relative cell-volume error and 3.37 × 10⁻¹³
for maximum relative face-area error.
The co-spherical cube passed all eleven metrics and reproduced its original
transcript byte for byte. [Qualification results and workflow identities](results/m2a_general_20261125/predicate-budget-qualification.json).

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
the terminal workflow UUID and packet hash. The single-thread base results
above use these frozen words.

The [general candidate entry point](../../reana/general_geometry_candidate.py)
checks its input against this catalog and uses the same 727,792-byte Rust
executable as the 252 G01 comparisons. It records the original stdout, stderr
and child-process result, including the Rust error variant on a typed rejection.
Two REANA launcher controls passed. The eight-cell cube returned volume
1/8 for every cell and 24 shared faces. Changing one generator word by one
unit in the last place caused input rejection before the executable started.
[Workflow identities and artifact hashes](results/m2a_recovery_20261124/export_checks.json).

To stage the 84 reference and 252 candidate workflow specifications, pass the
recorded G01 executable to the preparer and choose a fresh output directory.

```sh
python3 -B scripts/prepare_general_geometry_jobs.py /path/to/geometry.part0000 results/m2a-general-jobs
```

Preparation checks the executable, frozen literal packet and source hashes.
Each reference consumes one literal array. Each candidate receives its named
array and thread count. The complete matrix still depends on G00 and resource
calibration.

A separate small REANA control compared the actual eight-cell Rust export
with the certified independent reference. Every registered metric passed.
The control then doubled one cell's reported volume while preserving the
rest of the transcript. The reducer rejected the changed output on the
cell-volume, total-volume and affine-identity checks. The retained failure
packet contains the deliberately changed transcript and failed comparisons.
[Control metrics, workflow UUID and packet hashes](results/m2a_recovery_20261124/cube_comparison.json).

The G04 plan links **240 pairs** across the 12 base families. For each family,
the one-thread base is paired with the two- and four-thread base. At each of
the three thread counts, the base is also paired with each of the six
transformed inputs. The reducer checks both terminal workflow identities,
the frozen input words, the G01 executable hash and the native output hashes.
For an identical-input repeat it requires byte-for-byte equality of the entire
native transcript after removing the validated case label from both outputs.
This includes polygon vertices, incidence charts and diagnostic words.
Cross-thread pairs record that equality separately from the registered
normalized geometry limit. An unresolved topology change or typed rejection
still requires individual review.

The preparer can enumerate pairs before the scientific matrix runs. After
acquisition, each pair can be staged from the two capture directories
containing the observations and native outputs.

```sh
python3 -B scripts/prepare_geometry3_reproducibility.py plan g04-pairs.json
python3 -B scripts/prepare_geometry3_reproducibility.py stage cospherical_cube__repeat__t1 base-capture repeat-capture results/g04-cube-pair
```

For a candidate with a successful native export and completed independent
reference, the comparison preparer verifies the reference packet's complete
manifest, frozen sources, literal words and volume-closure certificate. It
binds both acquired workflow UUIDs to the comparison specification. The
existing reducer then evaluates the geometry on REANA.

```sh
python3 -B scripts/prepare_geometry3_comparison.py cospherical_cube__base__t1 reference-capture native-capture results/compare-cube
```

For a failed native workflow, `scripts/inspect_geometry3_rejection.py` checks
the terminal UUID, process outcome, literal input and actual Rust diagnostic.
For `UncertainMetric` it records the quantity, measured positive value and
separation bound. The six G02 families require a successful mesh. On the
difficult G03 inputs, a recorded ambiguity goes to individual scientific
review alongside the independent reference and the other transforms.

Each G04 pair also reconstructs the right incidence translation of every
periodic face from the frozen generator positions, integer windings and box
widths. In one axis the expected translation is
`x_left − x_right − (m + k_right − k_left) L`, including self-image faces.
The report records the largest component error divided by the box length,
the responsible face and axis, and the number of wrapped incidences. The
registered G04 limit of `1e-10` applies to both runs.
