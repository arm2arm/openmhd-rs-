# State-dependent motion with a midpoint-predicted linear macro path

2026-11-22. **Unimplemented engineering alternative; not adopted, reviewed or
numerically validated.** M1 acceptance remains the first implementation
prerequisite. This proposal supplies a concrete state-dependent trajectory
choice whose physical integration stages lie on one declared linear path.
It does not certify event coverage or resolve the known alias challenge of
the limited topology controller. The full deforming, magnetized,
multicomponent galaxy-merger goal and its gates remain required.

Name the alternative `midpoint-predicted-frozen-path-v1`. Preserve
[`augmented-heun-centroid-regularized-v1`](STATE_DEPENDENT_MESH_MOTION_SPEC.md)
and its [independent review](STATE_DEPENDENT_MOTION_DESIGN_REVIEW.md) as a
different proposal. In particular this alternative does not claim to
implement SM4–SM8's stage-by-stage velocity reevaluation. Exact current and
historical identities are recorded in
[the inventory](midpoint_frozen_mesh_motion_sources.json).

## 1. Source boundary and purpose

[Springel 2009 v3](https://arxiv.org/abs/0901.4107v3), printed p.16 Eq.31,
allows fluid-following generator velocities, and p.17 Eqs.32–34 relates
generator velocities to moving-face and volume rates. The retained complete
PDF and previously extracted complete equation pages were reinspected for
this note; the official version metadata was also rechecked. These pages
provide ALE context. They do not prescribe the midpoint construction below,
the existing SM1/SM2 smooth regularizer, a vector-potential tangent solve or
this project's event controller. MF1–MF5 below are engineering derivations,
not transcriptions of AREPO or a claim of AREPO equivalence.

The reviewed augmented-Heun proposal has an Euler generator predictor rP
which generally differs from its final rH and from the end of its proposed
dense physical path. A predictor-only face therefore cannot prove coverage
of that physical path. Here a private half-step predicts one velocity array
nu. All subsequently compared physical branches use nu on the same linear
macro trajectory. The half-step is not itself a physical contribution.

## 2. Private midpoint prediction and immutable path

Use the state, units, IDs, explicit curl/target/raw/auxiliary selectors,
fixed run Vref and SM1 or separately labelled SM2 velocity law of the
parent motion proposal. No IDs, particles, source births or accepted RNG
state change inside a hydro trial. Let Z=(r,Y), Y=(Q,a,phi,o,K), and let
W(t,Z) be that fixed velocity law. At accepted (t0,Z0), select a positive
macro duration H. H is not the cell length used by SM1.

First evaluate a complete old stage with W0=W(t0,Z0). Privately take one
Euler/GCL/covariant predictor of duration delta=H/2:

```text
rM=r0+delta*W0,                  gM=Geometry(rM,t0+delta),
VM=V(gM),
aM=a0+delta*rA0+zM,             H0*zM=delta*C0^T*V0*e0,
phiM=phi0+delta*chi0,
oM=o0+delta*m0,                 KM=K0+delta*Kdot.             (MF1)
```

QP/VP in the parent SM4 predictor is here QM/VM: use its actual-volume
Euler GCL construction with duration delta, old physical rates and old
owner samples. In particular

```text
SM=delta*s0,
D*deltaSM=VM-V0-D*SM,
EM_Q=delta*XQ0-UbarM*deltaSM,
QM=Q0-D*EM_Q.
```

H0, e0, centroid/volume rates, Cdot and all old raw rates in MF1 use W0.
Build the actual gM curl and positive primitives from QM/VM and aM. Then
evaluate the velocity law once at that matching state:

```text
nu=W(t0+H/2,ZM),
r_line(t0+tau)=r0+tau*nu,             0<=tau<=H.               (MF2)
```

Store the finite nu bits, not just the law's name. Validate generator and
boundary positions, graph compatibility, operators, positive closures and
all predictor solve/mean gates. Any failure rejects the macro trial; do not
replace the failed prediction by W0, alpha=0, a rigid velocity or a floor.
Discard every predictor state/cache/correction/physical exchange after nu
has been captured. Keep its provenance and failure diagnostics. It creates
no accepted flux, source, wall impulse, allocator change or event witness.

Restart the physical integration from the unchanged Z0. Recompute the old
physical stage using **nu**, including face speeds, cvel, Vdot, Cdot[nu],
target, raw rates, auxiliary maps and tangent defect. The previously
computed old stage with W0 is not reusable as this physical stage. Run the
parent [moving covariant increment method](MOVING_MHD_STAGE_SPEC.md) on
MF2 with nu fixed by real ID for the entire attempted macro interval.

Every inner old/predicted geometry is built at its actual MF2 stage time.
The inner Heun endpoint predictor and corrected gas/potential states share
the same endpoint generator geometry because this path is prescribed and
linear. There is no separate generator corrector or final Lloyd shift.
Rates and states are still reevaluated on every physical microstep; only
the generator velocity array stays fixed. Distinct per-cell nu vectors
permit genuinely deforming three-dimensional meshes. Equal velocities,
fixed grids, planar extrusion and alpha=0 remain separately labelled
controls and cannot replace the deforming tests.

The law W is independent of H; the integration rule estimates its midpoint
value using H. That is distinct from defining a regularizer proportional to
centroid displacement divided by the current step. The law generally does
not equal nu at an arbitrary inner state. Recording W there as a diagnostic
does not authorize changing the actual path or its Cdot velocity.

## 3. Conditional smooth-order derivation

On one smooth finite-dimensional branch, write the frozen-velocity ODE as

```text
G(t,Z;nu)=(nu,F(t,Z;nu)),
Zdot=A(t,Z)=G(t,Z;W(t,Z)).
```

F includes the actual conservative rates, potential tangent rates,
auxiliary/gauge/origin rates and the matching geometry derivative. Partial
derivatives G_t and G_Z below hold nu fixed. Assume the parent's positive
closure, fixed catalogue/images/stencils/ranks/raw branches, sufficiently
smooth maps and wall motion, bounded graph and projection inverses, and
exact or appropriately controlled solves. The actual-volume predictor
changes the Euler state by O(delta^2) on such a branch, so

```text
ZM=Z0+(H/2)*A0+O(H^2),
nu=W0+(H/2)*dotW0+O(H^2),
dotW0=W_t+W_Z*A0.                                            (MF3)
```

A consistent second-order inner integration of the frozen-nu ODE over H
has expansion

```text
Z1=Z0+H*G0(nu)+(H^2/2)*(G_t+G_Z*G)0(nu)+O(H^3)
  =Z0+H*A0+(H^2/2)*(G_t+G_Z*A0+G_nu*dotW0)0+O(H^3).
```

The exact augmented ODE has

```text
A_t+A_Z*A0=(G_t+G_Z*A0+G_nu*(W_t+W_Z*A0))0,                  (MF4)
```

which matches MF3. Thus the proposed macro rule has conditional local
O(H^3), global O(H^2) for that smooth spatial ODE. Its generator update is

```text
r1=r0+H*nu
  =r0+H*W0+(H^2/2)*dotW0+O(H^3).                             (MF5)
```

For the manual scalar control r'=r, r0=1, MF1 gives rM=1+H/2 and MF2 gives
r1=1+H+H^2/2. Freezing W0 instead would omit the quadratic term. This is a
symbolic control, not an executed numerical test.

For a uniform inner step eta=H/N, a bounded smooth second-order inner
method contributes O(H*eta^2)<=O(H^3). The constant must be bounded across
the registered family; an observed small branch difference is no proof of
this bound. Each physical microstep retains its actual-volume GCL
corrector, O(eta^3) only under the parent's smooth/compatible-graph
assumptions. Fixed solve tolerances, floors, topology and all other switches
invalidate an unqualified order claim. Same-ODE order also proves no
spatial MHD consistency, magnetic mean identity, positivity, divergence,
energy partition or full-step gravity/source order.

## 4. Controller boundary, coverage and retries

The existing limited `adaptive-exchange-substeps-v1` comparisons may be
investigated **within one MF2 macro path**. Freeze H, Z0, nu, path digest,
scales and time origin before constructing its three branches. Refining an
inner branch does not rerun MF1 or reevaluate nu. Geometry at a given macro
time is therefore common across branches; their Q/a/auxiliary states and
physical rates are not. Preserve the parent's real physical Heun increments,
canonical image/time-bin ledgers, GCL separation, minimum interval,
conditioning/closure gates and typed failure behavior.

If the macro interval is rejected or shortened, discard all its physical
branches and nu, restart from the accepted snapshot, and recompute MF1 for
the new H. Nu normally changes. Different macro-step refinements therefore
have different physical paths; their differences measure trajectory and
state error together. They are not quadrature convergence on a shared
geometry movie. Use persistent IDs and matching continuous lifts, retaining
position/centroid/volume errors and the selected field-sampling meaning.
Do not silently interpolate A between branch geometries or remap Q.

For each attempted macro path the exact numerical oracle target interprets
retained r0/nu/domain/time binary64 bits as dyadic rationals. Inherit E0's
exact time tags, specified rounded cloud-evaluation recipe and separate
path-versus-actual-cloud checks. E1–E5 event coverage and accepted physical
exchange witnesses may use only stages of the selected physical branch.
An MF1 face, a discarded comparison-branch face or an oracle query is not a
witness. References must distinguish exchange on the actual MF2 numerical
path from the independently resolved augmented ODE. Neither reference can
be substituted for the other.

This removes the specific ambiguity between an off-path Euler generator
predictor and the physical branch's endpoint **by defining a different
algorithm**. It does not remove short-face aliasing. The parent's epsilon
2^-28 S20 false-pass challenge, mandatory positive-face coverage, separate
noncancelling/surface/centroid-rule exchanges, reference/root uncertainty
and all absolute/relative gates remain unchanged. The limited controller
still supplies no universal event certificate and remains insufficient for
production-merger acceptance without the independent numerical evidence
and separately reviewed coverage strategy already required by the parent.

Actual nu must pass the parent moving-face CFL checks; a bound calculated
using W0 alone is insufficient. For a constant translating cuboid, require
the entire linear generator path inside the wall chart. Exact endpoint
inclusion implies segment inclusion for this convex box in its comoving
frame, but actual rounded evaluated clouds still require the boundary
checks. SM2's instantaneous continuous wall-taper property is not a proof
that this finite frozen-velocity trial stays inside. Bounded U1–U4 and all
moving-wall operators remain separate unaccepted prerequisites.

## 5. Evidence required before adoption

The independent source/manual review must first check MF1–MF5, the
discard/recompute boundary and the frozen-macro versus outer-retry semantics.
No implementation or execution is supplied here. After M1, approved static
geometry/operators, literal independent fixture review and actual preflight:

- Extend SM-LAW/SM-STAGE with a separately labelled midpoint profile: at
  least four macro-step halvings against an independent same augmented-ODE
  reference, the existing order>=1.8/state/field gates, and the parent
  history maximum generator error<=1e-5 Lmin0 and reference uncertainty
  <=1e-10 Lmin0. Retain ZM/nu, all actual paths and exposed inner/solve floors.
- Freeze predictor-only and actual-linear-path-only face controls with
  exact rounded inputs and independent event certificates. Check that
  predictor and discarded-branch entries cannot satisfy E1–E5. Then pass
  all unchanged prescribed-path S-EVENT gates and coupled macro-refinement
  gates. S20 alias/typed-rejection controls remain mandatory.
- Pass genuine nonuniform three-dimensional deformation, GCL, centroid and
  Cdot, nonzero full-vector B, all independent divergence, mean, conditioning,
  boost, budget, positivity, partition, retry and restart gates inherited
  from the parent. A proof about MF4 cannot replace any of them.
- Record the midpoint prediction as private work with a distinct epoch,
  and each physical attempt/branch with immutable nu/path identities.
  Rejected work changes no accepted counter, source or component ledger.
  Recompute the law after accepted gravity/source operations for the next
  macro prediction; newborns receive no earlier kick and Vref stays fixed.
- Complete bounded magnetic, gravity-work, multiphase/source, equilibrium,
  domain/ambient and full live merger gates. This trajectory choice supplies
  none of those results and does not change the shared endpoint split order.

Each independent ready control runs in its own REANA workflow with explicit
CPU/memory after the relevant source preflight. Local source/hash/manual
checks of this note supply no numerical validation or M1 acceptance.
