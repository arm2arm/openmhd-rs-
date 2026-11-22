# Bounded ideal-MHD boundary contract for the isolated merger

Design/source audit, 2026-11-22. **Proposed, unimplemented, unexecuted and
not accepted.** This resolves a physical-profile choice for M2d and specifies
its discrete review problem; it does not close the M2d acceptance gate.
Frozen M1 source `2bdcea0` and all M1 gates/evidence are unchanged. M1 physical
acceptance remains the coordinator's prerequisite for numerical work.

The [shared integration contract](INTEGRATION_CONTRACT.md) owns units, IDs,
source ordering and the final deliverable. The [mesh contract](MESH_3D_SPEC.md)
owns geometry, motion, GCL, curl diagnostics and the moving-target proposal;
the [gravity contract](GRAVITY_PARTICLES_SPEC.md), sections 6–7 and 9, owns
isolated forces, centroid sources and source/work accounting. This document
proposes a conducting-wall **alternative to** its section 7 hydro outflow
proposal. The coordinator has now selected this wall profile for the first
bounded reference and recorded that reconciliation in both shared/gravity
contracts. The discrete prerequisites below remain open; selection is not
acceptance of an implemented boundary.

## 1. Recommendation, scope and evidence classes

**E: choose `box-conducting-slip-relative-v1` as the first bounded magnetized
reference profile.** A stationary, nonrotating, closed Cartesian cuboid
contains positive-density ambient gas and deforming three-dimensional Voronoi
cells. The wall is impermeable, free slip and perfectly conducting, with
initial and evolved normal magnetic flux zero. Use a nonzero compact-support
galactic vector potential, no independently imposed uniform mean field,
and the relative A/cleaning conditions derived below. Collisionless particles
are unbounded and all real gas/particles use isolated gravity. This is a
finite-box engineering reference to an isolated galaxy, requiring measured
wall and domain/ambient controls; it is not a vacuum boundary model.

A constant-velocity translation of the **entire box and problem** is supported
as the coordinate-equivalent boost fixture. Arbitrary moving, rotating,
accelerating or curved walls, external magnetic flux, resistive walls,
absorbing cleaning layers, vacuum matching and general outflow are deferred.
The merger still needs state-dependent, genuinely deforming 3D mesh motion,
nonzero B and the full integration/source gates. A fixed mesh is only a
boundary subproblem fixture.

Labels on equations/decisions have these meanings:

| Label | Meaning |
| --- | --- |
| P | Verified primary-source statement, with exact locator below and in [the source inventory](boundary_mhd_sources.json). |
| D | Independent derivation in this document, with assumptions stated; not attributed to AREPO. |
| E | Engineering choice or candidate discrete construction requiring independent review and REANA evidence. |
| U | Specific unresolved prerequisite; implementation/acceptance cannot assume it away. |

**[P26](https://arxiv.org/pdf/2609.35989v1):** Springel, Mayer & Pakmor,
arXiv:2609.35989v1, full PDF, printed
pp. 6–7, Eqs. (38)–(42), supplies the auxiliary-gauge A equation and cleaning
signs. Printed pp. 8–13, Eqs. (51)–(76), supplies cell-centred fits, auxiliary
interpolation and the periodic mean-field discussion. It does **not** supply
the nonperiodic operator constructed here. MRI zero-gradient boundaries
(pp. 29–30) do not constitute this conducting A/phi treatment.

**[ABDG](https://dauge.pages.math.cnrs.fr/publis/ABDG_VPot.pdf):** Amrouche,
Bernardi, Dauge & Girault, author-hosted complete
43-page preprint of the 1998 vector-potential paper: PDF p. 22, Theorem 3.17,
Eqs. (3.21)–(3.22); PDF p. 23, Proposition 3.18. It establishes a potential
with zero tangential trace and zero divergence for suitable zero-normal-flux
fields, including the topology/flux qualifications. Its finite-element
results are not a proof for our cell-centred LS method.

**[S24](https://arxiv.org/pdf/2411.09352v1):** Secchi, arXiv:2411.09352v1,
printed p. 2, Eq. (1.4), distinguishes
zero-normal-field slip walls from walls threaded by magnetic field. Printed
pp. 4–6, Eqs. (2.9)–(2.10), (3.1) and the reflection argument make regularity
and compatibility assumptions explicit. This is not a theorem for a
self-gravitating cuboid with our numerical operators.

**[DC23](https://faculty.washington.edu/shumlak/WARPX/html/mhd_bc.pdf):**
Datta & Crews, author-hosted *MHD BC*, dated 2023-12-07,
p. 1, Eqs. (1)–(6), derives the zero-normal-flux conductor from electromagnetic
interface conditions and an initially unthreaded ideal conductor. Its
resistive conditions, p. 2, Eqs. (7)–(10), are **not** imposed in ideal MHD.
All four full texts are accessible and their actual bytes are pinned; no
source PDF access gap is being filled with invented equations.

## 2. Why this profile, rather than hydro-only outflow

| Property | Conducting impermeable reference, recommended E | Transmissive no-inflow proposal in gravity section 7 |
| --- | --- | --- |
| Gas mass/metals | No boundary transport; tagged ambient remains a live source. | Escaping mass/metals need signed flux and a specified exterior/source fate. |
| Magnetic field | Explicit Bn=0 and wall-frame tangential E=0; nonzero closed field in the interior. | Copying primitives or clipping inflow does not prescribe induction, external B or incoming MHD characteristics. |
| A, cleaning, gauge | Relative trace, scalar Dirichlet and compatibility derivation below. | A/phi characteristic/gauge conditions remain unresolved. |
| Gravity | No gas source disappears at the box; collisionless particles cross it freely. | Removed monopoles change gravitational potential energy; an exterior mass representation or controlled truncation is required. |
| Cost/physical limitation | Reflections and wall impulses, so domain and ambient controls are mandatory. | Potential reflections, incoming characteristics and field/gauge injection also need controls; “outflow” does not imply nonreflecting. |

**E:** do not implement general outflow as part of this first profile. Its
remaining design work is specified in section 12. A large wall box is
defensible only if the registered encounter interval and central observables
meet domain/ambient and wall-impulse limits. A box large enough to hide a
failed wall condition is not a substitute for the algebra/wave tests.

## 3. Coordinates, physical wall conditions and field topology

Let `y=x-X_box(t)`, `X_box(t)=X_box(0)+W*t`, where constant W is zero in
the production reference. The box in y coordinates is fixed; n is its
outward unit normal, and `P_t=I-n n^T`. Define `v_r=v-W`, `u_r=u-W` and
`w_r=w-W`. Physical wall speed is W, not the velocity of a nearby generator
or the tangential motion of a polygon corner. Units use the common SI-based
UnitSystem with `mu0_code=1`.

**P/D, ideal unthreaded free-slip conductor:**

```text
v_r dot n = 0;             B dot n = 0;
P_t E_r = 0;               E_r = -(v-W) cross B.                 (B1)
```

DC23 (5)–(6) and S24 (1.4) support the zero-normal-flux branch. The last
condition follows directly from the first two and ideal Ohm's law. Tangential
velocity is free; there is no no-slip condition, prescribed tangential B,
zero tangential current, or imposed normal electric field. Surface charge
and surface current may provide the conductor's field discontinuity.
Perfect conductivity alone does not erase pre-existing normal flux: the
initial unthreaded wall is an explicit assumption.

**D:** in a simply connected cuboid with connected boundary, divergence-free
B with Bn=0 has no through-boundary flux or handle flux. In fact
`integral B_i dV = integral x_i Bn dS = 0` by divergence of `x_i B`.
The volume mean of the continuum B is therefore zero. A nonzero spatially
uniform B is incompatible with Bn=0 on all six faces. Do not import the
periodic `B_mean + curl(a)` flux mode, linear periodic A jump, mean-gauge
offset, or periodic constant-A nullspace into this profile.

**E:** initialize from analytic A whose value and derivatives vanish in an
open collar of every wall. One explicit smooth, nonzero fixture is

```text
s = |y-y0|^2/R^2;
f(s) = exp(-1/(1-s)) for s<1, otherwise 0;
A = A0 f(s) e_z;           B = A0 grad(f) cross e_z.             (B2)
```

Choose the support ball strictly inside the box; the two galactic supports
are initially disjoint from the outer collar, and add their potentials.
This is an engineering initialization, not a realistic dynamo equilibrium
or a P26 galaxy fixture. A0/R sets a stated nonzero physical field scale;
its force and pressure support must be included in the gravity worker's
galaxy-equilibrium review. The fixture amplitude is fixed below. A=0 is not
a permissible magnetic substitute for the final merger. Tapering B directly
without constructing a compatible A is prohibited.

## 4. A, phi and gauge compatibility: the continuum derivation

**P26/D:** for ideal MHD, no separate mean field, and the common Jacobian
convention `H_ab=partial_b u_a`, Eq. (42) is equivalently, in the box chart,

```text
partial_t|y A = v_r cross B - grad(u_r dot A) + grad(phi),
B = curl(A),
D_w_r phi/Dt = c_h^2 div(A) - kappa phi,
c_h^2=alpha c_s^2;   kappa=beta_clean c_s/r_cell.                 (B3)
```

P26 (41)–(42) fixes the plus signs. `psi=u dot A` is an algebraic gauge
scalar, distinct from evolved phi; in the box chart its relevant form is
`psi_r=u_r dot A`. P26's alpha=1 and beta_clean=.15 can be retained as a
named baseline, but the bounded **discrete** choices below are amendments.
No new cleaning coefficients or AREPO boundary recipe are inferred.

**E/D: relative boundary choice, on each open planar patch:**

```text
P_t A=0;       phi=0;       u_r dot n=0.                         (B4)
```

Then `psi_r=0` on that patch, so both tangential scalar gradients vanish.
Both `v_r` and B are tangent, so `v_r cross B` is normal. Equation (B3)
therefore preserves `P_t A=0`. Also `Bn` is the tangential surface curl of
the tangential A trace, so Bn=0. These are trace statements, not the
assumption that every independently reconstructed cell divergence vanishes.

For a classical compatible solution, phi remains zero at the wall, and
`w_r dot n=0` at the wall. Evaluating its equation gives

```text
div(A)|wall=0;
partial_n A_n=0 on a flat patch, since div_t(A_t)=0.             (B5)
```

This is a **compatibility consequence** of homogeneous phi data, not a
second independently adjustable incoming cleaning characteristic. Together,
zero tangential A and the divergence trace are the relative mixed conditions.
Do not set all three A components to zero on each open wall, or add
`partial_n phi=0`. A_n and the normal gradient of phi are free to evolve.
ABDG (3.21)–(3.22) verifies existence/uniqueness of a Coulomb representative
under its flux qualifications. Here Coulomb divergence need not vanish in
the interior: cleaning evolves it. The theorem does not prove this evolution.

**D:** differentiating the compatibility trace gives, for a smooth solution
with `F=v_r cross B-grad(psi_r)`,

```text
Delta(phi)|wall = -div(F)|wall.                                (B6)
```

Because the tangential phi trace is zero, this specifies the compatible
normal second derivative, rather than another boundary value to impose.
It explains why imposing smooth odd reflection of phi/A for **all** forced
states is too strong. Compact-support initial fields with a constant ambient
collar satisfy the initial A/phi traces; gravity-driven hydro compatibility
must still be checked. At shocks a weak trace/flux interpretation is needed;
smooth derivative statements are not asserted across discontinuities.

**D: residual gauge transformations.** A change `A'=A+grad(chi)` preserves
continuum B. Choosing chi=0 on the connected wall preserves tangential A.
Equation (B3) requires `phi'=phi+D_u_r chi/Dt` (up to an irrelevant spatial
constant fixed to zero). This preserves phi's trace when u_r is tangent.
It is a symmetry of the *cleaned, gauge-fixed evolution* only if

```text
D_w_r(D_u_r chi/Dt)/Dt + kappa D_u_r chi/Dt - c_h^2 Delta chi=0,  (B7)
```

with its compatible initial/boundary data. The divergence trace additionally
requires `Delta chi=0` at a smooth wall. Arbitrary time-dependent gauge
resets are not symmetries of that fixed system. A harmonic residual chi
with homogeneous Dirichlet data is zero on a cuboid (a constant potential
has zero gradient). There are no relative harmonic 1-form modes for this
topology; ABDG Proposition 3.18 has I=0. Curl alone still has the infinite
gradient kernel; do not confuse it with the curl-and-divergence kernel.
Exact discrete `C G=0` has not been established for cell-centred LS.

## 5. Cleaning reflection, energy and the specific discrete review blocker

**D:** isolate constant c_h>0, fixed geometry, w_r=0 and no physical/gauge
forcing. The normal cleaning subsystem is `A_n,t=partial_n phi`,
`phi_t=c_h^2 partial_n A_n-kappa phi`. At phi=0 one incoming
characteristic is set by the outgoing one: reflected phi changes sign,
and reflected A_n has the same sign. It is a reflecting, zero-cleaning-flux
condition, not an absorbing wall. The characteristic speed is c_h.

```text
E_clean = 1/2 integral (|A|^2 + phi^2/c_h^2) dV;
dE_clean/dt = integral_wall phi A_n dS
              - integral kappa phi^2/c_h^2 dV.                  (B8)
```

The boundary term vanishes. This is a gauge-variable energy estimate, **not
physical magnetic or gas energy**. Variable coefficients, moving volume
weights and physical/advection forcing add explicit bulk terms; (B8) cannot
be advertised as their full energy law. Heun has a temporal truncation error
even for an exactly skew semidiscrete wave operator.

**E, candidate `relative-ls-adjoint-cleaning-v1`:** define a scalar
Dirichlet-fit gradient G from the constrained fits in section 7 and use
the actual negative volume adjoint for the cleaning divergence:

```text
V_s=diag(V_i); V_a=V_s tensor I3;
D_clean = -V_s^-1 G^T V_a;
A_dot_clean=G phi;
phi_dot_clean=c_h^2 D_clean A-kappa phi.                         (B9)
```

For constant c_h and a frozen stage this gives (B8), without a boundary
source, algebraically. With diagonal variable c_h^2, use the corresponding
`phi^T V_s diag(c_h^-2) phi` instantaneous norm and report time-dependent
weight contributions separately. Implement G transpose from the exact
linear map; never assemble it as an independently chosen LS divergence.
Keep `D_LS A` from the vector polynomial as an independent diagnostic.

This is a **proposed engineering amendment to the P26 divergence/gradient
pair**, not M1 adoption or paper equivalence. It is deliberately reviewable:
the map, weights and boundary constraints are specified, so its consistency
can be checked, rather than assuming that a formal Green identity holds.

**U1, precise operator blocker:** the volume adjoint of a one-sided LS
gradient is not automatically a consistent pointwise divergence on irregular
centroid samples. No proof or REANA manufactured-convergence result yet
establishes simultaneous consistency of G, D_clean and the constrained curl
near faces/edges/corners. Nor is `C G=0` guaranteed. Independent review must
either approve (B9) with the proposed convergence/contamination evidence or
replace it with a fully specified compatible pair before numerical coupling.
The alternative of using two raw LS operators has an unaccounted discrete
cleaning-energy defect and is **not** an accepted fallback. This source audit
therefore does not assert a completely accepted A/cleaning/projection path.

## 6. Wall Riemann states, ALE fluxes and ledgers

**E:** reconstruct an admissible interior face state from the current stage.
In the wall rest frame form the exterior *face* state by

```text
rho_R=rho_L; p_R=p_L; v_r,R=v_r,L-2(v_r,L dot n)n;
B_R=B_L-2(B_L dot n)n.                                        (B10)
```

Use the established common-normal-field convention: its average is exactly
zero for this pair. This is a wall-face Riemann construction, not an
assertion of even thermodynamic derivatives outside the gas. Query the
existing 3D-capable face-rest-frame solver with face velocity W and the same
named pressure/HLLD/fallback policy as the selected accepted fluid profile.
The Bn=0 degeneracy must take the solver's reviewed finite fallback, not
divide by Bn. Record all fallbacks. Zero normal mass/induction flux and
normal-only traction must first hold to the B-WALL tolerance below; a
discrepancy is a rejected boundary solve, not silently repaired interior data.

**D/E:** denote the resulting compressive normal stress by `Pi_star`
(thermal plus magnetic star pressure). Construct the boundary exchange
from that one scalar; no cell pressure reset or post-update energy fix:

```text
outward ALE flux per unit area:
F_m=0; F_metals=0; F_cold=0;
F_p=Pi_star n;
F_E=Pi_star (W dot n);
F_B,ALE=(v_n-W_n)B-B_n v=0.                                   (B11)
```

These follow from the ideal-MHD stress and energy flux with
`v_n=W_n, Bn=0`. Magnetic evolution still uses A, not an independently
committed B update. A normal electromotive value is allowed:
`v_r cross B` may be nonzero normal to the wall, while its tangential
component vanishes. Do not zero that normal A-induction source. Returned
laboratory ALE fluid fluxes already contain the rest-frame boost: do not
subtract `W_n U` a second time. Boundary Bn times the reference-frame
completion in the mesh target is zero, so its induction exchange is zero.

For each accepted time-quadrature increment, outward exchange E_f is
subtracted once from the real cell. A boundary ghost is no second cell or
gravity source. Save at least patch ID, full FaceKey, geometry/state epochs,
time/weight, centroid x_f, area, W, Pi_star, fallback, and signed exchanges.
With `I_f=-dt_weight area Pi_star n` the impulse **to gas**, save

```text
Delta P_wall_to_gas=I_f;
Delta L_wall_to_gas=(x_f-x_ref) cross I_f;
Delta E_wall_to_gas=W dot I_f.                                (B12)
```

The support holding the wall receives the opposite impulse/torque. For
W=0 its work is zero even if net force is nonzero. A stationary wall does
not imply zero wall force. Internal face antisymmetry conserves internal
exchange but does not remove this external impulse. Cell-centroid L can
also have hydro/representation errors; report them separately. Use the
same face position/quadrature for the torque ledger and the update, retaining
the gravity contract's distinction between monopole L and resolved subcell L.

**E:** physical budget residuals use signed gas+particle+source ledgers:
`P-P0-I_wall-I_other`, `L-L0-T_wall-T_other`,
`H-H0-W_wall-E_sources-Delta U_representation`, with the shared definitions
of H, scale and source signs. Retain raw histories as well. Stationary-wall
mass/metals transport is exactly zero by construction; all ambient gas
continues to gravitate at its volume centroid. Thermal recovery after a
curl/projection change uses the committed total gas energy. Record its
magnetic/thermal partition change, not a fictitious wall heating term.

## 7. Boundary reconstruction, ghost observations and corners

### 7.1 Linear maps and constrained fits

**E:** retain the mesh specification's local scaling, degree-1/degree-2
polynomial bases, weighted QR/SVD diagnostics, rank/condition rejection and
double-stencil expansion. Build fits in the box chart using real-cell
centroids; an outside observation has no EntityId. The initial stencil is
the cell and its two-ring face-neighbour BFS, sorted by CellId. Its patch
set is the union of physical planes incident on any stencil cell. If the
remaining fit is rank deficient or exceeds condition 1e8, expand one BFS
ring and recompute the patch set/constraints, up to six rings or the entire
connected component, whichever comes first; then reject if still deficient.
A patch set is sorted, axis/side keyed and epoch-owned. Face-centred fits
start from the union of the real incident-cell stencils and the face's own
patch. The plan/hash records the actual expanded rows and planes.

For vector A fit all components with coupled homogeneous constraints:
`P_t A_p(y)=0` and `div A_p(y)=0` **as polynomial traces on each relevant
plane**. For a planar patch the latter is `partial_n A_p,n=0`, since the
tangential components' polynomial trace is identically zero. For phi use
`phi_p=0` on each plane. Enforce the entire degree-1/2 trace by coefficient
equalities after translating/rotating to that plane; a single collocation at
the face centroid is insufficient. Derive a basis Z of the constraint
nullspace, solve the weighted real-data fit in that basis, and retain the
complete map `coeff=Z (M Z)^+ observations` plus derivative/trace evaluations.
Use column-pivoted Householder QR with original coefficient-index tie breaks,
scaled columns and the mesh contract's relative rank pivot1e-10; apply that
same declared rank rule to the constraint/nullspace factorization. Report
constraint and reduced-data ranks/conditions separately. Remove redundant
constraint rows deterministically. Zero-dimensional
admissible subspaces are explicit (not an ill-conditioned pseudoinverse).
Expanded stencils must have full rank for **all remaining** degrees of
freedom; otherwise reject the trial/fixture. No random jitter or unreported
regularization is permitted. All resulting maps are linear for a frozen
geometry/weight/patch set; nonlinear limiters are a separate transport step.

Degree-2 wall A constraints allow a tangential component proportional to
the square of distance from a wall. They do not impose zero normal gradient
of tangential B. Thus they avoid silently importing the resistive condition
`n cross J=0`. Near corners the admissible polynomial space is smaller;
report its dimension/rank and compare a higher-degree analytic field by
convergence rather than claiming arbitrary quadratic reproduction.

**U2:** constraints on several planes plus a free intercept are a specified
candidate, but their truncation error/conditioning and agreement between
cell and face fits are not established. The chosen rank/patch-support rules
and reproduction of every admissible polynomial must be independently
reviewed/frozen as part of the implementation design.

### 7.2 What ghosts mean, and what they must not mean

For a wall face the right A/phi trace is the same constrained trace, not an
independent Riemann potential. Optional outside samples for a fit may only
be evaluations of its **explicit linear boundary extension** and their
dependence on real observations must be included in the transpose. They
cannot add independent unknowns, duplicate mass or improve the nominal
rank as if they were independent measurements. The first implementation
uses direct constraints and real samples, avoiding those circular ghosts.

**E:** scalar rho/p/metals and the incoming interior primitive prediction
use one-sided real stencils. Do not force its incident normal velocity to
zero before the reflected Riemann solve: the solver must resolve wall
compression and its star stress. The **solved physical trace** has
`v_r,n=Bn=0`; it is distinct from that one-sided incident state. The raw
magnetic wall trace also comes from the constrained A fit, and limiting is
applied consistently to its tangential face prediction. The exact
conservative flux uses (B10), not a centred polynomial through duplicated
ghost-cell centres. A source-balanced hydro boundary is a
separate well-balancing question. For a smooth stationary flat wall,
the normal momentum equation gives

```text
partial_n(p+B^2/2)=rho g_n                                   (B13)
```

when there are no other normal body forces: tangential derivatives of vn
and Bn vanish on the wall. A finite normal isolated-gravity force generally
does not respect a mirror-symmetric extension. Reflecting rho/p as smooth
even functions would impose an additional zero gradient inconsistent with
(B13). For hydrostatic source fixtures either impose the derived analytic
normal pressure derivative in the reconstruction or use the reviewed
one-sided source discretization; the wall-face density/pressure remain the
interior trace. No density/pressure floor replaces equilibrium validation.

**D/E:** simple parities are useful only for the unforced symmetric
manufactured/cleaning fixtures and auxiliary field: relative v/u normal odd,
tangential even; A normal even, tangential odd; B normal odd, tangential
even; phi odd. As smooth whole-field extensions these also constrain higher
normal derivatives. Do not assert that they represent every ideal wall
solution with gravity. S24's reflection result explicitly uses a compatible
regularity subspace; it is not authority to omit this qualification.

### 7.3 Edges and corners

There is no independently solved finite-area edge flux. Every boundary
polygon belongs to one plane; zero-area edges/corners have no separate
conservative exchange. Impose **all** incident planar trace constraints in
the fit and boundary evaluator. Along two perpendicular walls A=0 (their
normal subspaces intersect only at zero); B and v_r may be parallel to the
edge. At a three-wall corner A=B=v_r=0 in a continuous compatible trace.
Phi is zero at every wall/edge/corner. Normal derivatives are not copied
from the last patch visited. Constraint ordering and, for symmetric auxiliary
ghosts, the diagonal Cartesian parity maps commute; diagnose their
composition explicitly. Do not claim smooth shock reflection at a corner
from this algebra. Real corner regularity and geometric slivers have their
own manufactured/convergence gate.

## 8. Raw curl, adjoint and screened moving projection

**D:** the continuous Green identities are

```text
integral b dot curl(a) = integral a dot curl(b)
                         + integral_wall (n cross a) dot b;
integral a dot grad(phi) = -integral phi div(a)
                         + integral_wall phi a_n.              (B14)
```

The first surface term vanishes with a_t=0; the second with phi=0. Bn=0
alone does not eliminate the first. These identities justify the chosen
trace spaces, not equality of two independently assembled LS matrices.

**E:** let C be the actual raw cell curl derived from section 7's constrained
vector fits, in the component/coordinate convention of the mesh contract.
Store each coefficient dependency on real cell IDs/indices, including all
free-intercept eliminations and boundary rows. C transpose is that exact
matrix transpose. If an explicit extension E and sampling R are ever used,
`C=R C_extended E` and `C^T=E^T C_extended^T R^T`; discarding ghost
contributions is incorrect. The adjoint test uses arbitrary **admissible map
inputs**, independent integer-vector data and both Euclidean and stated
volume-weighted products.

The mesh contract's endpoint correction remains a proposed moving-geometry
engineering method. In this profile replace its periodic curl by this C,
set B_mean=0, and include boundary induction exchanges (B11) in the target:

```text
M_B,target=V0 B0 - incidence(integrated F_B,ALE, with GCL terms);
B_target=M_B,target/V1;
a_trial=a0+raw_increment;
H=C1^T V_a,1 C1; D=diag(H);
(H+kappa_projection D) z=C1^T V_a,1 (B_target-C1 a_trial);
a1=a_trial+z.                                                 (B15)
```

`kappa_projection` is distinct from cleaning damping; retain the named
screening baseline 1 for this candidate. It defines a regularized objective,
not merely a preconditioner and not an exact target match. The tolerance/
true-residual/retry policy of the mesh projection must be registered and
retained: iterative relative residual <=1e-11, checked true residual <=1e-9,
and at most 24N iterations; a RHS norm <=1e-30 takes no correction, with its
absolute units/scale reported. These are engineering baseline choices,
not a universal field-error bound. No singular periodic mean pin is
transplanted. Require finite
positive D entries on all active unknowns or a reviewed explicit reduction
of unobservable modes; otherwise reject. Admissible correction **fits**
obey homogeneous traces by construction. Do not overwrite wall B after a
projection to conceal an inconsistent C. The normal Riemann field and the
independent raw-curl boundary trace are reported separately.

Constant vector A is not a generally allowed global wall gauge, and C's
nullspace/rank is not the periodic nullspace. A discrete cell-centred curl
may have additional numerical kernels. Screening does not establish gauge
invariance, absence of spurious modes or compatibility with (B9).
**U3:** no reviewed spectrum/rank, curl-gradient defect, wall-trace and
incremental-target/GCL result yet establishes that this bounded C/G/D and
screened correction work together. The potential's value can be a gauge
mode in the continuum while its discrete curl is nonzero. Keep separate
raw LS divergence, Hessian same-fit identity, shared-face mean/limited
divergence and Bn-trace diagnostics. A globally cancelling face sum does
not prove pointwise divergence or curl-gradient commutation.

## 9. Smooth auxiliary velocity, deposition and boosts

**P26/E:** a smooth auxiliary u with a finite Jacobian is the gauge input;
P26 section 4.3 supplies a C1 tricubic construction. The first bounded
candidate uses the mesh contract's uniform Cartesian tricubic slice in y,
with deterministic volume-weighted deposition of **real** gas v_r. It is
not P26's adaptive algorithm. Anchor its translating origin/grid to the
box chart, checkpoint it, and never wrap physical cells through the wall.

For a precise first slice choose `n_aux=4` intervals per axis, including
both endpoint nodes, with whole-grid fallback 4/2/1. Larger configured
powers of two halve to one; separate galaxy controls use 4/8/16. At each
Cartesian node q, deposit sample s with positive weight
`V_s product_a beta3((q_a-y_s,a)/h_a)`, where, for r=abs(argument),
`beta3=2/3-r^2+r^3/2` for r<1, `(2-r)^3/6` for 1<=r<2, otherwise zero.
This explicitly generalizes the current local cubic deposition, not an
unverified P26 coefficient. Include all reflected sample images within
that compact support: per axis `2m L_a+y_s,a` and `2m L_a-y_s,a`.
The reflected normal component changes sign, tangential components do not.
This finite-support auxiliary extension is not periodic gas geometry or
a second gravitating catalog. Divide the deposited vector by the positive
deposited scalar weight. Form first/mixed corner jets by Cartesian centred
differences of the shared nodal values and their parity-defined ghost nodes;
compose coordinate differences in fixed x,y,z order. Use those one-time
jets in the tensor-Hermite interpolant and its analytic derivatives.

**E:** extend the deposition support across a Cartesian wall using the
auxiliary symmetry `u_r,n` odd, `u_r,t` even. Reflect sample positions and
signed vector components; auxiliary ghost support carries no gas mass,
metals or gravity source. Normalize weights per component from the same
positive unsigned volume kernel; negative odd-component values do not
produce negative normalization. Real-only physical totals and diagnostic
means exclude every reflected sample. Assemble corner values and derivative
jets with the corresponding tensor parity (each normal differentiation
reverses parity); set odd trace jets exactly zero and share each boundary
jet once. The resulting Hermite interpolant has `u_r,n=0` identically on
each wall, including corners. Tangential evenness is an allowed choice for
this auxiliary field, not a required gas/B derivative condition.

Empty support requires deterministic **whole-grid** coarsening under the
registered uniform-grid policy. If even the root grid is empty, use the
analytic auxiliary field u=W with zero Jacobian for the entire box and
record that fallback; do not join independently chosen fallback fields at
cell interfaces. Do not use an arbitrary global
mean normal flow at a wall. This analytic field is also the first algebra
fixture, but it is not claimed to give adequate galaxy accuracy. Expansion
of smoothing support, grid resolution and fallback counts are convergence
inputs; force a failure if fallback occurs in the resolved galaxy/support
region of a physical acceptance case. Mixed/refined auxiliary patches are
deferred; no independently reconstructed boundary derivative jets.

**D:** under a joint boost b, `x'=x+b*t`, `v'=v+b`, `W'=W+b`,
`u'=u+b`, `w'=w+b`, while y, A, phi and B are unchanged in this zero-mean
wall-chart representation. Laboratory `psi'=psi+b dot A`; psi_r is
unchanged. Conserved momentum/energy transform by `p'=p+m b` and
`E'=E+b dot p+|b|^2 m/2`. The wall ledger transforms as
`I'=I`, `W_wall'=W_wall+b dot I`, with torque reported about the
transformed reference worldline. A lab-fixed origin for L introduces the
usual translated-origin terms and must not be compared blindly.
A stationary box in both runs is a different physical problem, not a failed
Galilean-invariance test. Isolated gravity sources and particle positions
receive the same coordinate transformation.

## 10. Motion, stages, rebuilds and restart obligations

**E:** a boundary face has one real incidence and one physical patch ID;
the normal face speed is `W dot n` at **every** stage, independent of the
nearby generators. Tangential boundary polygon changes follow the
intersection of moving internal bisectors with the plane. Integrate wall
area/centroid/stress on the same stage sequence as interior face exchanges.
Stationary wall swept volume is zero. In a boosted box individual wall
sweeps need not vanish, but their closed-box sum does. Prescribe those
sweeps; do not let the interior GCL graph correction adjust wall motion.
Its residual compatibility uses fixed physical box volume and the known
boundary sweeps. Reject a generator crossing or touching the outer plane;
no reflection/deletion of a generator or cell state is implicit.

Each accepted trial must:

1. Build/validate geometry and patch incidence at the old stage; rebuild
   constrained cell/face maps, C/C^T and G/G^T from that epoch.
2. Recover raw B, all independent divergences/traces, constrained primitive
   predictions and auxiliary jets; form interior and wall-rest Riemann
   solutions once per face and retain their signed exchanges.
3. Advance the predictor including accepted source splitting, A/phi cleaning
   pair and centroid transport; use its own Euler GCL correction.
4. Move interior generators, rebuild endpoint topology/centroids/boundary
   polygons and all boundary maps; reevaluate wall states, traces, auxiliary
   u/H and cleaned endpoint data. Old boundary neighbours/weights cannot
   survive arbitrary deformation.
5. Form the trapezoidal integrated exchanges, wall ledger and prescribed
   sweeps; apply the endpoint GCL and moving-curl correction with the same
   incidence and boundary target. Recompute B and thermal state, reject
   invalid states or failed linear/trace/geometry checks, and commit all
   gas/source/allocator/ledger data atomically. Retry leaves no impulse or
   work entry behind.

Boundary source accelerations use actual isolated gravity at the current
volume-centroid sources, with time/epoch/hash checks. Do not mirror gravity
sources, wrap particles, or treat wall supports as gravitating matter unless
a later physical model explicitly adds them. The wall constrains gas only.

Save profile/version, UnitSystem, box chart/X0/time origin/W, all patch IDs,
mesh policy/IDs, physical A/phi, auxiliary grid/origin/jets policy, cleaning
and projection profiles, source identities and accumulated patch ledgers.
Rebuild epoch-local maps on restart and verify their input hashes; do not
reset phi, A_n, gauges, ambient state or cumulative impulses. Restart parity
includes joint boosts, topology events and source retries. Removing the
current fixed/rigid Heun guard cannot supply any of these boundary or
stage obligations.

## 11. Concrete prospective REANA fixtures and gates

**E, all unimplemented/unexecuted.** These are proposed additional M2d
gates, not previously accepted M1 thresholds. No existing M1, mesh or gravity
gate is weakened. Before the corresponding numerical implementation,
independently review/freeze the operator/profile decisions **and** its
literal generator arrays, source/fixture hashes, case parameters, final
times, reference uncertainty and reducers. These tables are not yet frozen
fixture packets; that review is a prerequisite, not an implied completed
step. Each independent combination of resolution,
geometry, boost, damping, wall orientation, restart or ambient choice is
its **own** REANA workflow. Ready independent cases run concurrently, with
declared per-job resources and no aggregate cap. Native/FFI thread pools
use one thread; REANA preflight/build remains an explicit prerequisite.

Use box `[0,1]^3`, gamma=5/3, rho=p=1 unless stated, N=8/16/32 Cartesian
and separately frozen .15-spacing jittered arrays (same counter-seed scheme
as the mesh contract), axes and component permutations. Initial budgets use
the gravity contract's fixed nonzero P/L/E scales; field errors use fixed
initial B amplitude, never a nearly zero current field. Algebra tolerances
are `max(1e-10,64 epsilon cond)` times a stated analytic scale unless the
table gives a tighter adjoint/trace gate. Report absolute errors too.

| Family / prerequisite | Frozen fixture definition and measurements | Proposed acceptance criterion | Initial envelope per independent case |
| --- | --- | --- | --- |
| B-WALL / accepted M1, geometry/operators, reviewed B10–11 | One planar face, n each signed axis and one rotated local face; rho=1,p=1,B_t=(.2,.3) in local coordinates; v_r,t=(.3,-.4), v_r,n=-1,0,+1; W=0 and `(2,-1,.5)`. Additional B_t=0 and strong-field beta=.01 cases. Test raw mirrored solver and constructed flux separately, including Bn=0 fallback. | No NaN, positive star state; normalized raw mass, tangential momentum, rest-frame energy and induction flux <=1e-12; exact constructed zero mass/metals/cold/induction; traction-only momentum, lab energy=`W dot F_p` within 1e-12. Wrong epochs/units/patch speed rejected. | 1 thread,2 GiB,5 min |
| B-FIT / geometry, reviewed section 7 | At faces/edges/corners enumerate all monomials of degree <=2, restrict their vector/scalar coefficient space by the exact trace constraints, and sample every basis vector on real centroids. Also reject deliberately deficient remaining fit ranks; patch-order permutations. | Full admissible rank, condition <=mesh cap1e8, residual/rank diagnostics present; derivative and polynomial trace reproduction at vertices plus interior points within condition-scaled tolerance; no dependence on patch order <=1e-12 scaled. Never claim unconstrained quadratic reproduction. | 1 thread,4 GiB,15 min |
| B-ADJOINT / B-FIT, U1/U3 review | Exact C/C^T and G/G^T maps with fixed integer-vector data; B9 semidiscrete derivative, no evolution; compare independently assembled raw LS divergence; include one-cell/corner/irregular cases. | Relative adjoint defects <=1e-12 using nonzero product-norm scales; cleaning energy derivative plus damping <=1e-12 scaled; rank/spectrum/zero diagonal rejection matches frozen expectations. C G defect measured separately, never presumed zero. | 1 thread,4 GiB,15 min |
| B-MMS / B-FIT, B-ADJOINT | Set `A_x=a cos(pi*x)sin(pi*y)sin(pi*z)`, `A_y=2a sin(pi*x)cos(pi*y)sin(pi*z)`, `A_z=-3a sin(pi*x)sin(pi*y)cos(pi*z)`, a=1e-3. This has divA=0 and the relative traces. Phi=`1e-3 sin(pi*x)sin(pi*y)sin(pi*z)`. Test analytic curl, gradients, raw/adjoint divergences at N8/16/32 and wall/edge/corner bands separately. | Quadratic curl and G volume L1 order >=1.8, finest normalized error <=.1; D_clean manufactured L1 order >=1.5, finest <=.1; boundary bands converge >=1.0 and no O(1) corner defect. Analytic Bn/A_t/phi/divA polynomial trace <=1e-10 scaled. Face/global-flux and raw LS divergences all reported. Failure of D_clean consistency blocks candidate, not a tolerance increase. | 2 threads,8 GiB,30 min |
| B-GAUGE / B-MMS | chi=`1e-3 sin(pi*x)sin(pi*y)sin(pi*z)`; A=gradchi, phi=0, and separately add gradchi to B-MMS. Analytic curl is zero/change is zero; chi and Delta chi vanish at walls. Derivative-only cases first, then cleaning-only evolution with physical forcing off to t=1. | Raw C G or analytic-gradient sampling contamination converges >=1.5 in L1; finest spurious B / fixed `1e-3*pi^2` <=.01. Actual nonzero defects retained. Evolution may alter A/phi gauge but physical B perturbation <=.01 of that fixed scale and decreases with refinement. | 2 threads,8 GiB,1 h |
| B-CLEAN / B-MMS,Gauge | Pure cleaning box: c_h=1, kappa=0 and separately .15; v_r=u_r=w_r=0. A=grad `[1e-3 cos(omega*t) product sin(pi*y_i)]`, phi=time derivative of that scalar for kappa0, omega=sqrt(3)pi; damped scalar solves f''+kappa f'+3pi^2 f=0. Also a smooth phi packet centred (.25,.5,.5), support .1, directed normal-mode decomposition frozen before execution, reflected by x=0; compare incoming/outgoing characteristic amplitudes. | Smooth temporal order >=1.8 on fixed spatial map when temporal error isolated; spatial order of B-MMS maintained; reflection phi coefficient -1 and A_n +1 within2% finest, no artificial absorption. Undamped E_clean drift <=1% at finest and decreases with dt; damped energy agrees analytic within2%. Spurious B <=B-GAUGE bound. | 2 threads,8 GiB,1 h |
| B-UNIFORM / B-WALL, moving mesh/GCL | rho=p=1, v=W, B=A=phi=0, stationary/translated box, prescribed deformation from mesh fixture with wall-normal w_r=0. t=.1, dt=.01/.005/.0025; no sources. B=0 is only this GCL/control case. | Uniform drift <=1e-10, volume/GCL <=1e-12, M/E residual <=1e-10; wall P/L ledger residual <=1e-10 and opposite support impulse. Restart and serial ID reorder parity <=1e-10. | 2 threads,8 GiB,30 min |
| B-FIELD / B-GAUGE,CLEAN, full stage/GCL review | B2 compact potential, centre(.5,.5,.5),R=.2,A0=1e-3, u=W, v=W, prescribed deforming mesh; stationary and jointly translated box; t=.1, N8/16/32, same dt ladder. Analytic physical field is fixed in y. Then a separate coupled no-gravity evolution from identical nonzero B (not an equilibrium) with total energy initialized consistently. | Kinematic quadratic B L1 order >=1.8, finest <=.1 fixed amplitude, no wall trace violation; coupled positivity, M and ledger-corrected P/E <=1e-10. Magnetic/thermal partition changes, raw/face divergences and projection true residual reported; no hidden energy reset. | 2 threads,8 GiB,2 h |
| B-BOOST / relevant accepted B-CLEAN/UNIFORM/FIELD | For every preceding supported motion choose b=`(2,-1,.5)` and `(10,7,-3)`, transform wall/mesh/gas/particles/auxiliary chart and compare at identical y and logical dt sequence. Restart at t/2 separate case. | Smooth transformed state/B L1 <=1e-8 of fixed state/amplitude scales; uniform/GCL case <=1e-10. Wall work difference equals b dot impulse within1e-10 E_scale; all corrected budgets retain their gates. A/phi compared only under the stated wall-chart gauge. | Same as unboosted case |
| B-GRAV-WORK / accepted gravity direct/source work, B-WALL/FIELD | Analytic isothermal hydrostatic rho=rho0 exp(-Phi/c_T^2), p=c_T^2 rho in a frozen external smooth potential; include a finite normal wall gravity and B=0 first. Separate live gas/particle case with nonzero B2, wall impulse and no ISM; then separately enable frozen source transactions. | Hydrostatic profiles change <1% over registered sound-crossing time; ledger M/P/L residual <=1e-8, no-source energy residual <=5e-3 (gravity gates retained), source/representation terms satisfy gravity/ISM bounds. Explicit wall and hydro centroid torque channels; no assumed closed-system P/L. | 2 threads,16 GiB,4 h |
| B-DOMAIN / accepted isolated-galaxy/magnetized/source cases | Same galaxy profiles/resolution/support fields, boxes L=128,256,384 R_d and fixed ambient density chosen by largest box mass <=1e-4 M_pair; separate factors .1/10 in density and pressure as gravity contract. Fixed walls, nonzero fields, genuinely deforming 3D mesh, registered full encounter time. Monitor wall signal arrival, patch stress deviations and ambient accretion. | Existing central-profile domain/ambient change <1% retained; added cumulative net and absolute wall impulse/torque each <=1e-6 P_scale/L_scale after subtracting only the separately shown analytic uniform ambient traction, with raw ledgers retained. Stationary wall work <=1e-10 E_scale; wall mass/metals flux exactly0. Report fast/cleaning characteristic return times and observed reflections. Failure requires larger domain/profile revision, not claiming isolation. | 4 threads,32 GiB,12 h initial; larger envelope frozen from preceding measured calibration |

The B-DOMAIN wall criterion uses both signed and absolute integrated
**excess** traction so opposite impacts cannot cancel to a false pass.
Uniform ambient traction is `p_ambient n` times each face area/quadrature;
subtracting it is a diagnostic with a known static reference, not a
conservative-state correction. If magnetic ambient pressure is later
nonzero, revise the reference before execution; this profile initializes
unmagnetized ambient outside the compact support. The raw ambient pressure
support/energy/gravity remains in the physical state and all ledgers.

There is no uniform nonzero-B all-wall fixture: that would violate topology.
Wave/reflection MHD tests with tangential backgrounds must be local-patch
manufactured cases or a globally compatible nonuniform field. Before any
long merger, add a separately frozen linear magnetosonic wall-reflection
fixture on a compatible background, with analytic characteristic relation,
finest reflected amplitude/phase error <=2%, and spatial convergence >=1.5.
**U4:** its global field/equilibrium and reference packet are not yet
specified; neither B-CLEAN nor hydro reflection proves this coupled-MHD
wave gate. Do not start it from an incompatible uniform box B or infer its
coefficients from a periodic P26 wave map.

## 12. Outflow, integration decisions still open, and first tasks

**U5, outflow explicitly deferred:** a transmissive/no-inflow hydro boundary
is not a complete vector-potential boundary. A future profile must specify
incoming physical and cleaning characteristics, external B/normal flux and
electric field, gauge scalar/phi compatibility, edge data, its curl-adjoint
surface terms and its projection boundary target. It must conserve signed
escaping mass, momentum, cold/hot phases, metals and thermal/kinetic/magnetic
energy. It must also choose whether escaped gas remains in an exterior
gravitating representation or is truncated with an explicitly measured
before/after gravitational boundary-potential term. Removing a cell source
unnoticed, turning escaped gas into collisionless mass without a model, or
counting that potential change twice as face work is prohibited. The gravity
draft's limits of `1e-6` system mass and `1e-4` binding energy for losses
remain relevant to that deferred open-boundary branch; a closed wall does
not demonstrate that outflow branch passed them.

Resolved here: the unthreaded slip-conductor physical profile; its compatible
continuum relative A/phi traces and residual gauge; wall-frame boost;
stress/impulse/work signs; topology/mean-field restriction; and explicit
stage/ID/ghost/source obligations. Coordinator reconciliation selects this
wall profile for the first bounded reference and defers general outflow.
**Still open:** independent numerical review of U1–U3, the
globally compatible MHD reflection packet U4, and all implementation and
REANA evidence. M2d remains unaccepted. There is no full accepted bounded
A/cleaning/projection treatment or claim of AREPO equivalence in this audit.

After M1 acceptance and the design review, the smallest implementation slice
is a bounded, serial, fixed-geometry non-evolving operator/wall-flux module;
it does not require waiting for a galaxy evolution. Reviewable Rust layout
(names proposed, **no files/Cargo changes created here**):

```text
moving-mesh/src/boundary3.rs       BoxChart, WallPatchId, PatchSet, traces
moving-mesh/src/constrained3.rs    polynomial constraints, QR maps, reports
mhd-vector-pot/src/bounded_ops.rs  C/Ct, G/Gt, D_clean, weighted products
mhd-core/src/wall_flux.rs          mirrored face solve, WallExchange
mhd-vector-pot/src/bounded_step.rs stage epochs, B15 target, trial/commit
mhd-io/src/boundary_ledger.rs      patch impulses/torques/work/provenance
```

Proposed API records: `WallProfileId`, `BoxChart{origin_at_t0,t0,W,widths}`,
`WallPatch{axis,side,id}`, `BoundaryFitPlan{epoch,patch_set,map,rank,cond}`,
`BoundedOperatorPlan{epoch,source_map_hash,C,Ct,G,Gt,weights}` and
`WallExchange{epochs,key,patch,x,area,time_weight,traction,impulse,work}`.
Use the shared 128-bit typed CellId payload, never an EntityId for a ghost;
local u32 indices belong to the geometry epoch. Wall geometry and conditions
are immutable profile inputs, not closures allowed to mutate state.

1. Freeze U1/U2 constrained polynomial/adjoint choices, patch-support rule
   and exact source locators with an independent reviewer; register B-WALL,
   B-FIT and B-ADJOINT fixture packets before implementing that slice. Build
   new source only after M1 gate.
2. Implement those pure maps/flux records; reuse full-vector face-rest
   MHD primitives/solver and conditioned-fit utilities after generalization,
   not the periodic image/mean-field/constant-nullspace assumptions. Run
   each registered case on REANA under its own workflow.
3. Resolve the consistency/spectrum review with B-MMS, B-GAUGE and B-CLEAN;
   stop on U1/U3 failure. Freeze U4's full coupled reflection packet before
   any claim of a validated magnetized wall.
4. Add moving endpoint geometry/GCL/target and B-FIELD/B-BOOST with complete
   wall ledgers/restarts; only then couple isolated gravity and ISM source
   transactions and proceed to domain-controlled isolated galaxies.

No code, fixture arrays, executable probes, tests/evolutions or REANA control
were produced or run for this document. Document/source hashing and
read-only equation inspection are the only executed checks.
