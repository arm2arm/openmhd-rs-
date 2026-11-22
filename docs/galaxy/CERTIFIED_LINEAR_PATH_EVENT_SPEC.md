# Candidate-owned certified events on a finite linear generator path

2026-11-22. **Source/manual-algebra proposal; unimplemented, unexecuted and unadopted.**
Profile: `certified-linear-halfspace-heun-v1` (CLH1). It is a small serial
reference, not a merger-scale kinetic mesh backend. Both `numerical_acceptance`
and `full_m1_accepted` remain false. Scientific source 2bdcea0 is unchanged.

This proposal supplies a candidate's own finite geometry certificate and a
clock which actually integrates the faces it certifies. It does not promote
the sampled controller in [stage §9](MOVING_MHD_STAGE_SPEC.md) to a certificate.
It does not adopt the separate [midpoint-frozen alternative](MIDPOINT_FROZEN_MESH_MOTION_SPEC.md),
or resolve the augmented-Heun dense-path issue in
[the state-dependent review](STATE_DEPENDENT_MOTION_DESIGN_REVIEW.md).
The caller must first supply one immutable finite linear path; a path chosen
by a future coupled motion law needs that law's separate acceptance.

**Pinned context:** Git `97183f33438e406b77680758427af7aaeda6b42e`, not later
parallel working bytes. The [source inventory](certified_linear_path_event_sources.json)
pins every context blob, complete primary, read/render locator, manual
derivation and the [closed reading/check boundary](../../results/galaxy_certified_linear_path_event_design_20261122/closed_manifest.json).
The boundary excludes itself and the two tracked outputs; the inventory
pins this note and that boundary, avoiding circular hashes. P09 means Springel
arXiv:0901.4107v3; P26 means Springel–Mayer–Pakmor arXiv:2609.35989v1.
KDS means Basch–Guibas–Hershberger's retained author-hosted manuscript.
P denotes a primary-source fact, D manual mathematics here, E proposed
engineering, U an unresolved prerequisite. CL1–CL9 below are D/E, not a
published P26/AREPO event or MHD algorithm. No external implementation is
copied or selected.

## 1. Domain, immutable inputs and three geometries

The input is `LinearPathPacketV1`: exact serialized binary64 bits for t0,
positive H, all finite r_i0 and nu_i, sorted unique typed CellIds, UnitSystem,
domain, constant wall velocity where applicable, winding/chart conventions,
operator/sampling/flux policies and a positive finite resource budget.
Interpret each finite bit pattern as its exact dyadic value, including the
recorded signed-zero bits (geometrically both zeros have value zero).
NaN/infinity, duplicate IDs, image overflow and zero/negative domain lengths
reject. No generator/source insertion or deletion occurs on this packet.

Write s=(t-t0)/H in [0,1], u_i=H*nu_i as an **exact rational product**, and

```text
r_i*(s)=r_i0+s*u_i.                                           (CL1)
```

The domain is either a fixed orthorhombic torus with positive lengths L, whose
display anchor may translate at one constant W, or an axes-aligned cuboid
with fixed lengths and walls translating at the same constant W.
No shear, rotation, changing period basis/lengths, mixed periodicity,
curved wall or nonconvex domain is covered. Bounded generators must be
strictly interior for the whole target path; their signed wall distances
are affine, so strict endpoint tests suffice. Every pair's separation from
every retained periodic image must stay nonzero. Collisions, even a
tangential isolated collision, reject, rather than assigning overlapping gas
owners. These are certified whole-interval conditions, not sampled tests.

Keep three objects separate:

1. The exact continuous target path/domain CL1. Event algebra describes this.
2. At an exact dyadic elapsed tag tau=k*H/2^ell, the E0 materialized cloud:
   `elapsed_arg=RN(tau)`,
   `r_cloud[i,a]=RN(r_i0[a]+RN(nu_i[a]*elapsed_arg))`.
   No FMA, reassociation, repeated drift or minimum-image trajectory.
   Record RN(t0+tau), RN(tau), actual wall-plane arguments/rounding and every
   coordinate bit. A translated wall uses the same two-operation recipe
   for its offset. The exact dyadic cloud and actual rounded wall planes
   define a second all-halfspace problem at that stage.
3. The backend's materialized geometry at those inputs. Its polygon,
   volume and face-key checks must agree with the independently checkable
   cloud problem, not just the continuous path prediction.

Keep exact tags as the authoritative clock. Actual floating time arguments
and `h_arg=RN(tau_b-tau_a)` accompany them; do not advance time by repeated
addition. Certify their enclosures, positive weights and accumulated
time/weight-rounding error against the existing reference uncertainty
budgets. Never silently adjust the last step to hide a clock mismatch.
A witness needs the exact tag, actual time argument and t0+elapsed_arg to
lie strictly inside its certified positive interval, as E0 requires.

Continuous lifts and image integers are checkpointed. For owner i, use
y=x-r_i*(s); a neighbor is r_j*(s)+L*n. A wrapped backend adapter must retain
the trajectory-image n; changing display winding is not a topology event.
For its cloud geometry require exact dyadic equality between the backend
wrapped coordinate plus L*winding and the authoritative cloud lift.
If a rounding/recentering operation changes that problem, reject with
`BackendCloudRecenterMismatch`; an undocumented third cloud is forbidden.
This is a representation limitation, particularly for very large lifts,
not a claim of universal binary64 acceptance. Independently rebuild the
complete point-cloud image bound at each actual stage from its actual bits,
rather than assuming the continuous-path image list encloses rounding.
Check all cloud/backend positive keys against the target at that stage;
a cloud-only or target-only positive face yields `CloudTopologyMismatch`.
No area tolerance erases the difference. Exact predicates and backend
roundoff tolerances are distinct evidence.

Face keys, charts, orientation and self images follow mesh §§2–3:
canonical min of (i,j,n) and (j,i,-n); for i=j choose the sign with first
nonzero component positive; self n=0 is invalid. One shared polygon/rate,
two metric incidences. Distinct image faces never collapse into a pair-ID
key. Wall keys are (real CellId, physical patch ID). Images, event batches,
clock knots and witnesses allocate no source EntityId/EventId.

## 2. A finite complete plane inventory

For each periodic owner i include every potentially relevant image plane,

```text
d_ijn(s)=r_j*(s)+L*n-r_i*(s);
a_ijn(s)=2*d_ijn(s), b_ijn(s)=d_ijn(s) dot d_ijn(s);
P_i(s)={y: a_h(s) dot y <= b_h(s), all retained h}.             (CL2)
```

The six own-image planes n=±e_a give exactly |y_a|<=L_a/2. They
must be retained even in a one-cell torus. Let Rbar=(Lx+Ly+Lz)/2,
a conservative rational upper bound on this box's Euclidean radius.
For every y in this box, |y|<=Rbar. If |d|>2*Rbar, then
2*d dot y<=2*|d|*Rbar<|d|², so that image cannot cut the cell.
For q_a(s)=r_ja*(s)-r_ia*(s), let lo_a and hi_a be its exact endpoint
minimum and maximum. A necessary condition for a relevant image is

```text
ceil((-2*Rbar-hi_a)/L_a) <= n_a
                         <= floor((2*Rbar-lo_a)/L_a).          (CL3)
```

Enumerate the entire closed integer product, except i=j,n=0, plus the
mandatory six planes. Equality is retained. This bound covers arbitrarily
large **finite** nu*H/L with a finite, potentially enormous inventory; it
never assumes 27 images. A tighter rational radius bound may be used only
as a separately verified bound with the same outer-inclusion proof.
Checked integer overflow/resource exhaustion rejects, not truncates.

The selected small reference may remove planes only by the following
two fully recorded, backend-independent certificates; otherwise keep them.
This reduces trivial oversets without assuming a neighbor list.

* An own image n other than ±e_a is redundant: on the own box,
  max(2*(L*n) dot y)=sum_a |n_a|*L_a²<=sum_a n_a²*L_a².
  If any |n_a|>=2 this is strict. Otherwise equality fixes every nonzero
  coordinate to its appropriate box endpoint; with at least two nonzero
  components its contact dimension is at most1, so it is never a positive
  face. Preserve that contact/alias receipt, not a fictitious face.
* For any other image compute the symbolic piecewise-quadratic
  `g_h(s)=b_h(s)-sum_a (L_a/2)*|a_h,a(s)|`.
  Split only at exact roots of the linear a components. On each piece a
  quadratic's minimum is checked at its endpoints and, when applicable,
  its exact rational stationary point. Remove the plane only if every
  minimum is **strictly positive**, with exact certificate identities.
  Equality/uncertainty keeps it. This proves strict inactivity on the
  entire own box for the entire path, without evaluating any cell backend.

Record every raw CL3 key and its retained/pruned proof, with checked counts.
The root/minor inventory in §3 uses retained rows; the verifier also checks
each omitted-plane certificate, so its polytope still equals the complete
all-halfspace problem. Bounds/certificates are symbolic algorithms proposed
here, not evaluations performed in this task. A static neighbor list,
endpoint distance filter, sampled slack or undocumented backend candidate
set cannot replace them. More powerful moving-guard-polytope pruning or
kinetic maintenance is a separately reviewed future acceleration.

For a bounded cuboid, retain all N-1 real-neighbor planes and all six wall
planes. In owner coordinates a wall n_w dot x<=c_w0+s*H*n_w dot W becomes
`a_w=Lref*n_w, b_w=Lref*(c_w0+s*H*n_w dot W-n_w dot r_i*(s))`,
with one fixed positive rational length Lref from the domain packet.
This positive row scaling gives all a length units and b length-squared
units, as in CL2, without changing the halfspace.
Thus neighbor a has degree<=1 and b<=2; wall a is constant and b affine.
All intersections with walls, edges and corners participate in the same
inventory. Wall reflection images used by the auxiliary field are not
Voronoi competitors, exchange edges or gravitating sources.

Distinct generators and strict wall interior imply full-dimensional bounded
cells: a sufficiently small ball around each generator is feasible at each
time. Periodic own-image bounds, or the actual cuboid, make them compact.
The finite periodic competitor list gives the same cell as the infinite
periodic list: every omitted plane is strictly inactive on the own box.
These facts are assumptions checked by certificates, not inferred from
a backend reporting a positive volume.

## 3. Polynomial certificates and a completeness argument

For m plane rows h per owner, construct the following finite exact rational
polynomial inventory. A coefficient is an integer numerator/positive
denominator; serialization is decimal integer strings in ascending powers
of s. Store the exact construction keys and original sign/scale.

* Every square minor of the m-by-4 matrix [a_x,a_y,a_z,b], orders1–4,
  all row/column choices; include the normal-only minors, orders1–3.
* For every normal-plane triple T, its Cramer data and every plane slack:

```text
A_T=(a_h^T)_(h in T); Delta_T=det(A_T);
N_T=adj(A_T)*b_T;
y_T=N_T/Delta_T;
P_Tj=b_j*Delta_T-a_j dot N_T;
slack_j(y_T)=P_Tj/Delta_T.                                   (CL4)
```

* Every image separation |d|² (degree<=2), and bounded wall-clearance
  polynomials. Their roots are forbidden collision/contact events.

A normal k-minor has degree<=k. A k-minor containing the b column has
degree<=k+1, because exactly one selected factor comes from that column.
Hence augmented 4-minors have degree<=5. In CL4,
deg Delta<=3, deg N<=4, deg P<=5. The block determinant
`det[[A_T,b_T],[a_j^T,b_j]]=P_Tj` independently checks its sign/factors.
There are no square roots from unit normals in these predicates. With the
wall scaling above Delta, N and P have length powers3,4 and5 respectively;
y=N/Delta has length units and a slack has length-squared units.
Identically zero polynomials are explicitly certified identities; they
are not omitted as “small”. A nonzero repeated root remains an event even
without a sign change.

**D, completeness on this domain, not a generic-position assumption.**
Partition [0,1] by all distinct real roots of nonzero inventory polynomials.
On each open root-free interval choose one exact rational representative.
All minor/slack signs, including persistent zeros, are constant there.
For each triple whose Delta is nonzero, CL4 gives a unique candidate vertex;
feasibility is exactly P_Tj/Delta>=0 for every j. Every vertex of a compact
full-dimensional 3D polytope has an independent active triple, so none is
missed. Two feasible bases denote the same vertex exactly when each basis'
defining planes is active at the other's vertex. Their equality relation
and all active-plane sets are therefore constant in the interval.

For a plane h, collect the distinct feasible vertices where its slack is
zero. The face is their convex hull. If nonempty, take their average:
every constraint not tight at every such vertex is strict at that average.
Consequently its affine hull is exactly the intersection of the constraints
tight at every collected vertex, and its dimension is 3 minus the rank of
those normal rows. The normal minors certify this rank. A face is present
iff this dimension is2; compactness then gives strictly positive area.
Dimension0/1 contacts are absent. Thus existence, vertex/face incidence and
positive-face presence cannot change inside a root-free interval.
This also handles permanently non-simple tensor vertices and redundant
contact planes: no random perturbation or simple-tetrahedron assumption is
needed for this **polytope** argument. It does not certify an LS map's
derivative at such a vertex.

At isolated roots classify the polytope separately with exact algebraic
signs, not interpolated signs or a chosen “before” triangulation. To check
p(alpha)=0 use its gcd with alpha's defining polynomial and an isolated-root
count; otherwise refine rational enclosures until the nonzero sign is
decided. All such refinement is subject to the declared resource limits.
A persistent zero-area contact contributes no physical face. A face
positive only at an isolated instant cannot arise here: a positive face
has relative-interior strict inequalities against noncoincident competitors,
so persists locally; ambiguous coincident supporting planes require
the alias rule below. A zero-area event itself has zero area measure in
time and never licenses division by area.

Positive-proportional duplicate plane rows may be coalesced **geometrically**
only with exact proportionality and preserved alias provenance. Persistent
non-simple vertices retain all active keys, with a deterministic independent
basis for their rational coordinates. Opposite coincident constraints
would destroy full dimension and reject. If aliases assign one positive
physical polygon to different real exchange partners or wall patches,
return `AmbiguousPhysicalFaceOwner`; do not invent a flux tie.
In the declared unweighted, distinct-owner, strictly interior domain,
duplicate physical bisectors of that kind should be excluded; checking
that exclusion is part of the validator. Persistent relations are not,
by themselves, a reason to reject required Cartesian/tensor geometry.

The exhaustive cost is O(sum_i m_i^4) low-degree predicates, with additional
O(sum_i m_i^3) Cramer data, root comparison and exact-integer bit growth.
There is no practical-cost or 69-seed runtime claim. A mandatory
`EventResourceBudget` declares positive finite maximum image rows, plane
rows, minors/slacks, coefficient/working-integer bits, isolated roots,
simultaneous-batch members, certificate bytes, stages, refinement rounds,
CPU threads, memory and wall time **before execution**. Precompute counts
and fail `EventInventoryResourceLimit` before allocating beyond them.
An independent fixture's resource allocation must be adequate or its
outcome is an unresolved failure, never a pass. Literal resource values
remain to be frozen with each prospective case; this document is not a
reservation or permission to launch. The existing <=512-real-cell scope
is retained, without an aggregate CPU/memory scheduling cap.

## 4. Exact root isolation, event identities and validation

The candidate generates its **own** `CandidateTopologyCertificateV1`.
For each nonzero polynomial clear denominators, divide integer content,
record the removed signed scale, and use a primitive positive-leading
integer representative. Retain a checked square-free factorization and
multiplicities. Isolate all real roots in [0,1], not just sign-changing ones.
A deliberately simple reference may use exact Sturm sequences:
p0=q, p1=q', p_(k+1)=-rem(p_(k-1),p_k) for square-free q.
Division identities, endpoint evaluations and signs are part of the receipt;
only positive sequence rescalings preserve its sign convention.
For non-root endpoints the zero-deleted variation difference V(l)-V(r)
counts the roots in (l,r). At a zero of an internal sequence member its
neighbors have opposite signs, so variation is unchanged; at a simple
zero of q, crossing decreases variation by one. This is the manual
root-count basis, not a new root solver implemented here.

Subdivide rational dyadic brackets deterministically, lower child first.
An exact dyadic root is stored as an exact point, with separately counted
open intervals. Endpoint roots are not lost by an open-interval convention.
Refine disjoint isolating intervals until comparisons are decided.
Use gcd/common-root certificates to merge shared roots into one simultaneous
batch; overlapping floating brackets alone cannot merge them.
Each sign cell and root point must account for every polynomial's root
count. The validator reconstructs the full inventory from the packet,
checks identities, counts and all sign cells, and rejects missing/extra/
ambiguous certificates. It must not trust an author's event count or hash
without the full construction. A hash speeds lookup, never equality.

Normalize owner-local face records to the full canonical key and verify
the paired owner's chart-translated polygon/active constraints and presence
components agree exactly before building the global event/clock list.
A self-image face still has two geometric incidences with opposite lifts.
Failure is a certificate mismatch, not an averaged geometry.

A root identity is (primitive square-free polynomial coefficients, real-root
index, isolating bracket); compare equivalent representations by exact
common-root predicates. `EventBatchKey` consists of PathDigest and the
sorted contributing predicate keys/multiplicities plus this equality proof.
It is a diagnostic identity, not a source EventId. Sort cells by exact root
order; ties by full predicate key. Persistent identities have a separate
record, no infinite event queue and no epsilon tie breaker.

The candidate verifier is a separately written pure certificate checker,
not the mesh backend's assertion. The independent reference/oracle is a
third implementation: separately derived plane reconstruction and root/
polytope predicates, no shared coefficient builder, production root/clip
routines or flux integrator. It may audit certificates and output errors;
its event times are never supplied to the candidate's schedule builder.

For every positive presence component (maximal connected positive-area
time interval for a full face key), retain inward/outward rational root
brackets, Wlo=t_plus_lo-t_minus_hi>0 and multiplicity/contact history.
Combine adjacent sign cells only after exact classification at their
common event verifies positive area with the same physical key.
For a macro endpoint use its exact time rather than a fictitious root.
A bracket stored in s has physical width H*(s_hi-s_lo).
Each non-point event bracket must satisfy E5:

```text
bracket_width <= min(1e-10*H, 1e-8*Wlo)                       (CL5)
```

for every adjacent positive component it bounds. Refine against the smallest
such Wlo; if it cannot be made positive/resolved within declared resources,
reject `EventRootWidthUnresolved`. Other geometry root neighborhoods
remain explicitly represented and their exchange uncertainty enclosed;
they are not dropped because the named challenge face is already isolated.
A persistent relation has exact identity evidence instead of a finite-width
root neighborhood. There is no probabilistic confidence attached to exact
rational certificates; errors in an implementation remain a separate risk.

## 5. Candidate clock and compulsory physical interior stages

The certificate's exact algebraic root times are **not** new floating
timesteps. Select an E0 dyadic clock as follows. Retain

```text
hmin=max(H*2^-20,128*eps64*max(abs(t0),H,T_unit)).
ell_max=largest ell in [0,20] with H/2^ell >= hmin.            (CL6)
```

Reject if H<hmin or the required initial levels8/9/10 cannot exist.
The finest allowed clock nodes are k*H/2^ell_max. This deliberately
declared representation can reject some perfectly valid paths.
Certificate brackets may refine beyond this clock; they need not become
physical knots. Do not create arbitrarily short steps around a root in
violation of hmin.

Before evolving states, for **every** certified positive face component
select a strict-interior clock node. Enumerate eligible k by distance from
the component's exact midpoint, ties to smaller k; compare algebraic
midpoints/brackets exactly. Require the E0 time enclosures inside that
component and exact all-halfspace positive presence in the materialized
cloud as well as the target path. Choose the first satisfying these
geometry/clock conditions. If none exists return
`PositiveFaceClockUnresolvable`, retaining the component, root brackets,
all considered node failures and coordinate bits. No area cutoff, oracle
time, parameter shift or “small contribution” exemption. Operator or
state-positivity failure at a selected node rejects the physical branch;
do not search for a node whose state happens to pass.

Let the branch at level ell initially contain all uniform dyadic nodes at
ell plus **all** these candidate-owned witness nodes, sorted/deduplicated
on the common finest grid. Levels start at8/9/10 and increase one at a time.
Every interval is integrated; no root bracket or topology gap is removed
from time. The uniform maximum gap halves with ell; witness insertions
make individual steps unequal. They do not all halve, which must be
reported honestly in temporal fits. Minimum gaps are one finest-grid
quantum>=hmin. Additional state/CFL restrictions refine the declared
uniform grid; failure at ell_max or a budget limit rejects, not accepts
the last branch. Strict stage-time/backend-key validation is repeated
when each actual state-dependent physical rate is evaluated.

An interior node becomes the old or predicted-endpoint stage of an actual
accepted microstep, with Heun weight h_arg/2>0. Thus a face absent at both
birth/death times but positive between them contributes to the accepted
physical exchange at an interior node. This is a literal accepted-stage
construction, not logging its existence. Its physical flux channel may
itself be zero; presence/positive quadrature weight and a correctly keyed
rate record, rather than an invented nonzero mass flux, are the witness.

For each positive component require a `PhysicalStageWitness`:
PathDigest, component/root IDs, exact/actual time tags and cloud bits,
full face key and orientation, actual polygon/GeometryEpoch and
operator/state/source epochs, old or P stage, branch/microstep ID,
strict-positive quadrature-weight bits and the immutable physical
fluid/induction rate-record identity. The witness points to a term
actually used in the final selected branch's corrector ledger.
An old-stage rate also used by the Euler predictor is counted only once
in the corrector's h/2 exchange. Private trajectory predictions,
reference queries, midpoint-only geometry, discarded coarse branches,
final-state queries and GCL correction records are not witnesses.
Coverage is mandatory even when every global error is tiny.

## 6. Actual Heun exchanges, closure and what is not certified

Every microstep uses the existing S1–S14 sequence from immutable local old
state, with actual geometry rebuilt at both clock nodes on **this** nu path.
No extra remap, pressure reset, mean subtraction, endpoint projection or
different trajectory is introduced. Write X_Q=A*F_Q, X_T=A*F_T and s_f=A*w_n.
The union of actual old/P physical keys uses zero area/rate only where
a face is absent. Owners still resolve by real ID. In schematic notation:

```text
R_P=V_b-V_a-D*(h*s_a);          D*deltaS_P=R_P
E_QP=h*X_Qa-Ubar_P*deltaS_P;    Q_P=Q_a-D*E_QP
E_TP=h*X_Ta-Bbar_P*deltaS_P;    BT_P=(V_a*B_a-D*E_TP)/V_b

R_H=V_b-V_a-D*(h/2*(s_a+s_P)); D*deltaS_H=R_H
E_QH=h/2*(X_Qa+X_QP)-Ubar_H*deltaS_H
Q_b=Q_a-D*E_QH
E_TH=h/2*(X_Ta+X_TP)-Bbar_H*deltaS_H
BT_H=(V_a*B_a-D*E_TH)/V_b.                                  (CL7)
```

Here h is the recorded actual positive step argument, with its exact-tag
difference and rounding enclosure; D includes the appropriate actual key
union. Prescribed wall sweep/physical boundary terms remain fixed.
Ubar_P=(U_aL+U_aR)/2 and Ubar_H=(U_aL+U_aR+U_PL+U_PR)/4, with
U_P=Q_P/V_b. Bbar_P is the two OLD owner B values averaged;
Bbar_H is the four OLD/PREDICTED values averaged, with predictor B recovered
after its one tangent correction. There is no implicit final unknown among these four samples.
At a common knot, the preceding microstep's P and final states remain
distinct; the next microstep rebuilds its OLD rates from that final state,
never reuses a P rate with a different StateEpoch.
Graph weights, pinned-component compatibility, no self-edge correction,
full residuals and correction scaling remain exactly S13–S14.
A face missing at both ends of **one** microstep has no invented correction
edge; the schedule ensures each positive component has a different actual
old/P interior rate. If the graph cannot realize actual volume changes,
the branch rejects despite successful topology certification.

For a at moving actual centroid point samples, use the same stage C,Cdot,
volumes, support, auxiliary field/origin/gauge and raw rate r as the selected
operator tuple. Holding real samples fixed in Cdot is mandatory:

```text
lambda=diag(Vdot/V);
tB=-V^-1*D*(A*F_T)-lambda*B;
e=tB-Cdot*a-C*r;       Hproj=C^T*V*C+Dproj; L=Hproj^-1*C^T*V;
H_a*zP=h*C_a^T*V_a*e_a;             aP=a_a+h*r_a+zP;
H_P*vH=h/2*C_P^T*V_b*e_P;
a_b=a_a+h/2*(r_a+r_P)+zP/2+vH.                              (CL8)
```

These are S10–S12's once-only increments. Recover predictor/final B from
their actual C and a, not BT. No second screening of a corrected rate,
or independent final-field projection. phi, auxiliary origin o, K and
their old/P/final rebuilds follow S6–S9 and the stage table, including
run-constant Vref through subsequent gravity/source events.
For the periodic shared-face comparator B is a cell-average approximation
and a is a centroid point sample; LS point/FV-surrogate is a distinct tuple.
The schedule cannot turn one into the other.

Use S3–S5 and F5–F9 at every stage: actual volume Vdot, face covariance
term in centroid velocity, derivative of vertex/area/centroid/covariance
and weighted fit with moving centroids, lift and normalization derivatives.
Cdot holds stored real a fixed; C*adot is the separate chain-rule term.
At a materialized stage, its tangent is the analytic local linear motion
through that **actual cloud** with the same immutable nu/W, not a derivative
of the discontinuous RN operation and not a Cdot cached at the target cloud.
Record (actual CloudDigest, nu, W) as the tangent epoch; target/cloud
rounding differences and their derivative error remain part of the error
budget. Metric self-image incidences contribute before owner cancellation.
One shared flux contributes equal/opposite extensive exchanges; a
self-image owner transaction is deterministic net zero, while its
metric/chart incidences remain. The owner GCL graph is not this metric
incidence list, and metric-support samples are not exchange edges.

The face provider already returns laboratory ALE fluxes. Apply no second
-U*w_n or -B*w_n. Selected interior completion is
F_T=FaceFlux.induction+Bn_returned*Vref; returned Bn is not an unrelated
divergence diagnostic. At a wall retain the prescribed physical
half-Riemann stress, signed force/torque and lab work W dot F once,
Bn=0 and zero completed induction. Normal face speed is affine over
the polygon; no tangential centroid speed substitutes for it.

**Certification scope:** the proof in §3 certifies polytope event inventory
and the witness contract certifies actual sampling, not an MHD truncation,
energy or div(curl) theorem. A microstep may straddle a certified root.
All time is integrated by CL7–CL8, but that does not make a discontinuous
rate smooth or a missed narrow pulse accurate. Positive Jarea/Jcent
relative gates below prevent a lone very overweight witness from passing
the challenge. Even those finite fixtures do not prove universal physical
accuracy. The S17–S19 O(h³) local/O(h²) global argument survives only on its
smooth, stable fixed-spatial-ODE regions; it is not extended through roots,
rank/limiter/donor/auxiliary switches by this schedule.

A stage exactly at an isolated topology root, or at a persistent multiple
vertex, needs an independently validated Cdot/map definition on the
actual path. For a persistent vertex, a nonsingular active triple gives
a rational derivative; every other active equation and admissible basis
must agree identically on that interval. This supports a geometry-only
derivative, not automatic differentiability of raw fits or bounded maps.
At an isolated root, differing one-sided derivatives are retained;
the first coupled reference returns `StageDerivativeUnresolved` unless
the selected separately reviewed operator supplies a consistent path
derivative. It does not evaluate at an epsilon-shifted fake geometry.
Geometry certificates for required static/tensor fixtures can still pass
their mathematical contract; a rejected coupled case is not called a
physical pass. A macro retry changing its endpoint can avoid some such
nodes, but cannot prove all paths acceptable.

A named metric-support fit can avoid an adjacency-row jump only under
its existing full-rank/smooth-weight assumptions; this proposal does not
select it silently. Raw transport/limiter/Riemann/auxiliary changes,
metric-support rank/conditioning and bounded U1–U4 remain independent
failures. No topology certificate authorizes use of an undefined stage.

## 7. Acceptance, independent exchange references and transactions

Run at least the three complete nested levels8/9/10, all from the same
immutable macro old state and **same PathPacket**, with the same compulsory
witness set. Retain all discarded branches. Compare both successive pairs
on the finer branch's exact time bins and full canonical keys. Piecewise
linear old/P rates define the physical exchange ledger over each actual
microstep; integrate absolute values by splitting component zero crossings.
For exact tag length DeltaTau and actual h_arg, the committed integral
uses h_arg/2 weights. Represent its within-bin density as
`(h_arg/DeltaTau)*[(1-theta)*X_old+theta*X_P]`,
theta=(tau-tau_a)/DeltaTau. This makes bin totals exactly match the
committed floating-weight quadrature in real arithmetic.
Retain the unscaled exact-tag rule and their difference as a separate
clock-rounding diagnostic; apply the same convention to sampled-area
quadrature. Include its bound in all exchange/relative uncertainty gates.
Neither dropping that difference nor relabeling it as a source is allowed.
No cancellation across faces, time bins or components is allowed in the
exchange error. Compare signed physical exchanges and absolute net ledgers
separately from GCL. Require the existing <=1e-4 normalized final state/B
L1 and cell maxima and <=1e-4 summed absolute exchange differences for
both pairs, plus all existing geometry, CFL, positivity, solve, mean,
partition, boundary and budget gates. In particular retain mesh M02's
normalized GCL residual<=1e-12, uniform-state drift/budgets<=1e-10,
smooth raw corrector scaling order>=2.8 and predictor order>=1.8, and
finest max|deltaS_H|/min(adjacent V)<=1e-4. The smooth scaling claim does
not extend to a root-containing step; all registered event/refinement
requirements still apply. The unchanged mesh G/O/M/F/C/B registry owns
geometry/conditioning/field/boost thresholds, not a relaxed CLH1 table.
Accept **only the finest complete**
passing branch with verified actual-stage coverage for every positive
component. No valid source transaction is committed on a discarded branch.

Preserve the separate E2/E2a/E3/E4 quantities, channel by channel:

```text
I_surf = integral_dt integral_face F(x,t) dS;
J_surf = integral_dt integral_face |F(x,t)| dS;
J_face = integral_dt |integral_face F(x,t) dS|;
J_area = integral_dt area(t);
X_cent(t)=area(t)*F(f(t),w_n(f(t)),t);
I_cent=integral X_cent dt;  J_cent=integral |X_cent| dt.        (CL9)
```

Candidate physical stage interpolation defines I_rule/J_net,rule and its
piecewise-linear sampled-area integral J_area,cand. Label J_cent,cand only
in the analytic-centroid fixture; coupled Riemann rate records are not
pointwise analytic surface fluxes. Net face stage data cannot recover
J_surf. Root-containing reducer bins use certified algebraic boundaries
with directed enclosures; they do not change the physical clock or inject
reference times into the solver.

The independent reference computes true clipped polygons and actual
surface/time exchanges, including spatially varying analytic states and
affine normal speed, with its own implementation. It also computes a
separate high-accuracy **same centroid face rule** time integral to expose
temporal aliasing apart from spatial quadrature error. It cannot reuse the
candidate root/clip/flux implementation as its independent proof.
The E3 prescribed analytic rho,p,v,A,B fields and nonzero Bmean remain
unchanged. They are an exchange-integrand experiment, not an exact coupled
MHD solution. A surface-reference spatial floor still fails the physical
comparison; same-rule success cannot waive it.

The existing finest global actual-surface exchange error <=1e-3 and
decrease under macro-time refinement remain, together with:
- Mandatory positive J_cent,mass and J_area: relative error, including
  reference uncertainty, <=1% against certified positive lower bounds.
  Their reference uncertainty <=1e-3 of those lower bounds; event-root
  contribution <=1e-4 of the same positive lower bounds. The challenge's
  actual-surface J_surf,mass must also have a certified positive lower
  bound, or its reference is unresolved.
- E5 component reference uncertainty <=1e-4 of fixed initial channel scale
  and <=10% of positive J_surf; CL5 width condition also holds.
- For a structurally zero channel require an exact zero certificate;
  otherwise no near-zero waiver. Retain absolute error+uncertainty
  <=1e-3*fixed_scale and reference uncertainty<=1e-4*fixed_scale.
  Fixed gas scales are M0, M0*c0 for momentum and E0=sum|Q_E,0|;
  induction uses Vtot*B_scale and area-time uses Vtot^(2/3)*H, all frozen
  from the packet's initial catalog as E2a specifies. The mandatory challenge
  mass/area positive channels cannot take this zero-channel exemption.
- The existing independent reference ladders32/64/128 event subdivisions,
  triangle/time orders8/12/16 and >=80-digit arithmetic, escalating160/320,
  remain prospective. These declarations are not observed error bounds.

S-EVENT literal certificates must enclose all geometry changes and uncertain
root-neighborhood contributions, not just the two symbolic DE roots.
An oracle with undefined/nonpositive reference denominators, unresolved
surface bounds or inconsistent targets yields `ReferenceUnresolved`,
never an acceptance. Coarse/fine agreement is not an exact physical error
enclosure; the prospective independent-reference gates are essential.

All standard mean/target/normal/independent-divergence diagnostics remain.
Configured mean error<=1e-9 fixed B_scale, true normal residual<=1e-9,
iterative tolerance1e-11, active-diagonal rejection and solve budgets are
unchanged. Q_E residual<=1e-10 is distinct from magnetic/thermal partition;
the finest signed and noncancelling excess transfers must retain the
existing <=1e-3 initial magnetic energy and decreasing-error gates.
Track actual V, field variance/representation term, geometry/raw/projection
S21 transfers, kinetic/thermal/magnetic budgets, boundary work and common
physical Q. Positive predictor and final closure at every selected
microstep is mandatory; no correction to p,Q_E,Bmean,a or phi is allowed
to repair a failure.

An inner refinement changes only physical step partition on immutable nu,
so its reference target is exactly the same CL1 path.
A state-dependent macro retry which recomputes nu defines a **new**
PathDigest/target, invalidates every old certificate/clock/map/witness
and needs its own reference/trajectory-error comparison. Neither MF nor
augmented-Heun geometry is interchangeable with CL1. Record the physical
old/P/final cloud hashes and never certify only a private predictor path.

Rollback restores gas/particle/source state, wall and gravity/work ledgers,
allocator and RNG state, source epochs and all accepted endpoints.
Trial certificate IDs and branch-local geometry epochs consume no physical
IDs/random draws. Sources, birth activation and source-cache invalidation
occur only at accepted full-step endpoints under the shared transaction;
formation_time and activated_at remain distinct. No inner event knot
is an extra SF/feedback/gravity source epoch. The run-frozen Vref,
SI units/common gravity kernel and signed energy/metals ledgers are retained.
This packet does not change source/gravity splitting order or prove its
coupled temporal accuracy.

## 8. Proposed interfaces and typed failure evidence

These are contracts for later Rust slices, not code adoption:

| Interface | Input -> output / invariant |
| --- | --- |
| declare_linear_path | Immutable owner bits/domain/nu/policies/budget -> full PathPacket/PathDigest; no state evolution. |
| enumerate_planes | PathPacket -> full plane/image/wall-key list plus CL3 bounds and counts. |
| certify_topology | Full plane polynomials -> root/identity/sign-cell/active-set/presence certificate; no mesh/flux queries used as proof. |
| verify_topology | Reconstruct inventory and exact identities/root counts -> ValidatedTopologyCertificate; failure retains the supplied and derived evidence. |
| make_physical_clock | Validated certificate + E0 cloud recipe -> dyadic branch knots and component-to-stage requirements; no oracle input. |
| evaluate_physical_stage | Actual state/geometry/path/clock/epochs -> shared rates, Cdot/maps/closure and immutable rate records. |
| integrate_branch | Immutable old state + clock -> CL7/CL8 state, all physical/GCL/energy ledgers and actual witnesses. |
| compare_and_commit | Three complete branches + coverage/registered gates -> finest accepted transaction or typed rejection; never partial commit. |

Certificate and witness records include full input/construction values,
not only hashes. Checked serialization versions, decimal integer strings,
positive rational denominators, binary64 bit strings, exact dyadic k/ell,
all policy/source versions and wall/image charts are mandatory.
The independent validator has no mutation/source/ID/RNG capability.

In addition to existing geometry/conditioning/positivity/boundary failures,
typed failures distinguish unsupported domain/collision,
inventory/integer/root/stage resource limits, invalid/incomplete certificate,
root-order/identity uncertainty, ambiguous physical owner,
materialized-cloud mismatch, positive-face clock failure,
stage derivative undefined, GCL component incompatibility,
topology/exchange refinement exhaustion and independent-reference uncertainty.
Each retains PathPacket, failing keys/predicates/brackets, budget use,
actual attempted clocks/cloud bits, branch states/rates/logs and precise
uncommitted status. Loss of storage/process is not claimed to manufacture
such evidence; the durable accepted checkpoint remains authoritative.

## 9. Prospective independent literal and physical gates

No arrays, seeds, roots, flux values, certificate tables or successful
outcomes were generated in this task. Freeze literal dyadic packets,
candidate/oracle source separation and all budgets before immutable
preflight. Each independent case/method runs in its own resource-declared
REANA workflow after accepted M1 and applicable reviewed static operators.
Retain S-EVENT's initial per-case geometry envelope1 thread/4GiB/1h and
physical/reference envelope4 threads/16GiB/12h, with prospective calibration
before any declared enlargement. Exact enumeration may exceed these; that
is a recorded resource failure, not permission to omit predicates or relax
a gate. Other coupled cases retain their matching parent registry envelope;
all exact inventory/bit/stage budget fields must additionally be frozen.

Under an orthogonal R, transform polar r,nu,A,v,W,Vref by R and axial
B,Bmean by det(R)*R. Reverse polygon winding under a reflection so its
cross-product area vector remains outward R*S. Transform image keys/domain
widths under the supported signed axis permutations; arbitrary rotated
period bases are not accepted by this domain profile. Exact relative
bisectors are equivariant under a common constant boost, but newly rounded
input clouds need their own certificates. No bitwise or full coupled
Galilean theorem follows from this algebra.

1. **CL-CERT:** exact static one-cell self-image torus, required uniform and
   nonuniform tensor fixtures, bounded one-cell and oblique two-generator
   cube; persistent zeros, redundant contacts, simultaneous multiple flips,
   independent vertex bases and exact face-dimension checks. Positive faces
   must survive zero-minor relations. Collision/contact and ambiguous-alias
   negatives reject with their real reason. Test omitted image layers using
   large finite travel/unequal widths; CL3 completeness cannot assume27.
2. **CL-CLOCK:** periodic crossing/full winding, self-image metric versus
   owner cancellation, joint translated cuboid wall-edge/corner cases;
   exact target versus rounded-cloud disagreement, huge-lift adapter and
   nonrepresentable positive intervals. Corrupt a polynomial/slack sign,
   multiplicity, root batch, interval, full image key, cloud bit, witness
   branch or quadrature weight; missing/fabricated/ambiguous certificates
   must fail before a physical commit. Required valid geometry rejected
   on resource/representation grounds remains a failed/unresolved case.
3. **CL-ALIAS:** the unchanged original69-seed S20 recipe at eps2^-9,
   2^-16 and2^-28, shifted centers and axis permutations. Do not substitute
   the symbolic unrounded DE roots for actual dyadic-input roots.
   Old coarse/fine aliases remain negative controls. Include an oracle-only
   visit, discarded prediction, P-only augmented-Heun geometry visit,
   and a face present only on the actual linear path; only actual accepted
   path old/P rate terms qualify. Both certified positive components and
   noncancelling mass/area requirements must reject missing coverage even
   when global errors fall below tolerance.
4. **CL-EXCHANGE:** unchanged E3 analytic nonzero-field challenge with
   independent actual surface/time and same-centroid-rule references;
   zero-channel controls, root-width/uncertainty straddles, signed and
   absolute ledgers and time refinement. A lone pulse sample must not
   escape J_area/J_cent relative gates. Include intentionally inadequate
   spatial quadrature and mismatched path/rounded-cloud references.
5. **CL-MHD:** genuine nonuniform full3D nonzero-B deforming periodic
   controls, spatial/temporal ladders, joint boosts/axial-B orientation,
   restart/rollback, Cdot at held-fixed samples, raw/limiter/support switches
   and low-beta positivity/partition cases. Retain independent mean,
   returned-face versus other divergence, actual-volume GCL and projection
   target diagnostics. Bounded cases additionally require U1–U4 and their
   real wall/auxiliary/operator prerequisites; a periodic pass supplies none.

The finite image and face-lattice arguments are manual mathematical support
for a proposed small certificate checker. Exact-arithmetic implementation,
complete literal inputs, certified roundoff/enclosures, budgets and actual
face/flux/operator results are still absent. A useful later acceleration
may maintain a kinetic subset of certificates (KDS), use certified spatial
pruning or a reviewed backend. It must prove equivalence/completeness or
return the same typed failures; a fast neighbor guess or event sample is
not a substitute. No license/dependency/build/MSRV/performance adoption
follows from these primary sources.

Independent source review must first assess CL2–CL6 completeness and the
actual-stage CL7–CL8 connection. After M1, separately eligible non-evolving
static algebra/geometry slices may proceed through their own prerequisites
without accepting moving physics. The source-only MF and state-dependent
path alternatives, topology through raw/map switches, bounded U1–U4,
gravity/work/source coupling, positive compound IC feasibility and stable
full isolated magnetized galaxy, ambient/domain controls and full-duration
active multiphase gas/DM/old/new-star merger remain required. Prescribed
linear paths, tiny reference meshes, collisionless or B=0 controls do not
replace that goal. Original metadata output review, repaired coherent
preflight/cases/output and final collector/archive/joint numerical review
still precede M1 acceptance; reported fresh science passes alone do not
set either acceptance flag.

## 10. Sources and read-only work

P09 printed p17 Eqs32–34 supplies the bisector normal-speed/volume context;
pp17–18 distinguish face-frame and laboratory fluxes. P26 printed pp8–10
Eqs51–67 supplies the point-fit/curl context and a distinct integral
alternative; pp15–16 Eqs80–92 supplies its published stage context.
None publishes CL1–CL9, the GCL engineering correction or this schedule.

The KDS manuscript, printed pp2–4, distinguishes certificate failures from
fixed-rate motion samples and separates correctness from efficient/local/
compact kinetic maintenance. We borrow that conceptual distinction,
not a 3D MHD algorithm or its implementation.
Sagraloff–Mehlhorn arXiv:1308.4088v2, printed pp1–8, defines square-free
real-root isolation/refinement and discusses exact signs/rational input;
its ANewDsc algorithm is **not selected**. The retained PDF has arXiv v2
stamp11Mar2015 but title-page date10Sep2018; both identities are recorded,
without inventing another version. CGAL6.1.1 official Algebraic Kernel
manual, Univariate Concepts/Major Types/Design Rationale, documents
polynomial+isolating-interval representation, multiplicity/common-factor
and sign-at-root concepts. Its code, algorithms and dependencies are not
adopted. Exact Sturm/remainder and polytope proofs above are the project's
explicit reference construction; an implementation still needs independent
source/literal review.

Performed complete retained-source acquisition, relevant text/page-render
inspection, immutable Git copying, manual algebra and document/hash/JSON/
link/whitespace checks only. No target import/call, test/mock, geometry/
root-isolation/flux/operator/RNG evaluation, scientific computation,
build/reducer/evolution, REANA/workflow/service action, private-config
access, commit/push or delegation occurred. The companion inventory
distinguishes full retained bytes from pages actually inspected and
records limited terminal-output truncations followed by narrower reads.
Source integrity checks are not numerical tests or acceptance evidence.
