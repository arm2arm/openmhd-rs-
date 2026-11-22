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

**Author response to the [independent boundary review](BOUNDARY_MHD_DESIGN_REVIEW.md),
committed in f8220ef:** the report and its source/line identities remain
frozen. It does not approve these new bytes. The exact pressure choice is
now [perpendicular-half-riemann-gamma53-v1](WALL_RIEMANN_SPEC.md); the operator
candidate is `relative-local-quadratic-adjoint-v2`. The source inventory pins
the old subject, review, new inputs and current output. All choices remain
unimplemented and unexecuted; the final deforming self-gravitating full-3D
magnetized merger is unchanged.

| Review finding | Concrete design disposition here | What manual mathematics does not close |
| --- | --- | --- |
| 2, physical pressure | Separate W1–W5 half-Riemann solver, admissible shock/rarefaction and typed vacuum/uncertainty branches; B10–B12 use its state, not FaceFlux completion. | Independent root/jump/boost accuracy and pressure-oracle REANA evidence. |
| 3, exact observations | O1–O3 specify every real central/two-ring row/weight, constraints, baseline restoration and assembled affine maps. | Approximation and adjoint consistency of those particular maps. |
| 4, support/zero space | Target-local planes stay fixed as rows expand inside 8h; degree-3 scalar corner amendment, explicit spaces and physical-resolution rejection. | Boundary-band approximation under irregular refinement; rank alone is insufficient. |
| 5, cleaning | B9/O4 select unprojected constrained G and its negative volume adjoint, fixed masses and spectral/time-error bounds. | Gradient/divergence consistency and moving-weight stability. |
| 6, combined trace/curl | O5 states combined forcing trace and a nontrivial manufactured cancellation, exact C/Ct dependencies, kernels/active policy; no kernel projector. Old B15 is withdrawn. | CG contamination, physical-target/mean/trace/energy and bounded moving Cdot coupling. |
| 8, reflection/startup | R8 background and O6 variable-coefficient physical perturbation/reference, time windows and uncertainty; explicit hydrostatic control and bounded weak ambient launch. | Physical reflection/background stability, gravity and source evidence. |
| 7/9/10, frozen choices | One wall ALE transform and signed force/work/torque; anchored image/jet/stage semantics; registered domain/ambient and merger observables. | Executed algebra/restart and finite-domain adequacy; closed budgets do not prove isolation. |

The independent geometry fixture packet/review is unchanged and is not
reissued as a passed numerical gate. This task changes only the owned
boundary/pressure design and their inventories, never the shared or moving
stage contracts.

**Source-only follow-up to the [bounded revision review](BOUNDARY_MHD_REVISION_REVIEW.md),
committed in 59bc5c8:** that review addresses exact bed56a4 bytes, which
remain historical inputs. It supports W1–W5's reduced wall-pressure
mathematics, not numerical acceptance or these changed bytes. This revision
corrects O7 and freezes `boundary-qr-frobenius-v1` and
`reflection-unit-response-ncc-v1` before literal fixtures. No source state,
physical threshold or wall/domain gate is changed to make a result pass.

| Revision-review finding | Disposition of this revision | Still required |
| --- | --- | --- |
| 1 | O7 uses abs(r)^3; O7a proves evenness, positivity and C2 joins manually. The review's old literal counterexamples remain unchanged history. | Independent kernel/denominator/mirror REANA controls, not executed here. |
| 2 | W1–W5 conservation/Hugoniot reduction remains unchanged and supported in its stated positive gamma=5/3, Bn=0 branch. | Independent physical-pressure references and branch coverage. |
| 3 | Root/vacuum rejection, one ALE transform, signed impulse/torque/work and nonzero normal A rate remain unchanged. | Floating enclosures, physical wall-flux and boost evidence. |
| 4 | O2a now fixes exact redundancy, QR input identities/scaling/signs/ties and the conservative Frobenius condition gate. | Independent literal matrices/oracle, U2 approximation and B-FIT evidence. |
| 5 | The negative-adjoint frozen-metric identity remains supported; it is not gradient/divergence consistency. | U1 consistency/spectrum and moving-metric evidence. |
| 6 | Combined forcing trace, actual CG/returned-divergence/mean and separate magnetic-to-thermal budgets remain mandatory. | U3 bounded forcing/projection/Cdot and physical convergence. |
| 7 | O6d fixes unit-epsilon response, peak-one aperture, amplitude windows and a fully normalized lag estimator with unresolved ties rejected. | Independently converged reference, literal packet and U4 physical reflection. |
| 8 | O7's corrected even kernel supports the all-word parity argument; anchors/endpoints/epochs/retry/coarsening rules are retained. | Numerical cancellation/jet/restart/root-change evidence. |
| 9 | Force/ambient/full-duration domain gates are unchanged; scoped a7ef086 ISM context is reconciled below. | Live gravity, sources, reference uncertainty and finite-box adequacy. |
| 10 | Current input/review/output identities are pinned separately; bed56a4 and the unretained working-copy observation are preserved. | Independent review of new bytes, M1 and all dependent implementation/REANA gates. |

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
The pressure derivation additionally uses **[TY13](https://arxiv.org/pdf/1310.2330v1)**,
Takahashi & Yamada, arXiv:1310.2330v1: p.4 Eqs.2.1–2.8
(conservation/EOS/speeds), p.5 Eqs.2.11–2.13 (Bn=0 limit),
p.6 Eqs.2.17–2.21 (mass/momentum/energy jumps). W1–W5 are
independent reductions of these laws, not that paper's solver code.
All five full texts are accessible and their actual bytes are pinned; no
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

**E, candidate `relative-local-quadratic-adjoint-v2`:** define a scalar
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

**D/E: B10 is an incident/mirror comparator only.** It does not select
physical traction. The review's admissible receding example has negative
HLL normal traction although the magnetic completion is admissible. Neither
that traction, its absolute value, a clipped maximum, nor completion pressure
defines the physical wall state. The selected boundary provider is
[perpendicular-half-riemann-gamma53-v1](WALL_RIEMANN_SPEC.md), W1–W5:
a positive perpendicular-MHD fast shock or rarefaction connecting the
one-sided incident gas to zero relative normal speed. Gamma=5/3 and Bn=0
are explicit first-slice restrictions. Its independent physical
`rho_star,p_star,Bt_star,Pi_star=p_star+Bt_star^2/2`, branch, wave bounds,
bracket and uncertainty are retained. Vacuum is a physically distinct
branch but a typed rejection in this positive-density first profile.
No HLL/HLLD completion supplies this pressure; existing solvers remain
interior solvers and optional diagnostic wall comparators.

Check the raw constrained incident Bn separately before setting the solved
wall Bn exactly zero. Its error must pass the B-FIT trace gate; constructing
a zero-flux star state cannot hide that error. The incident relative normal
speed is not zeroed: it selects compression or recession. Tangential v and
Bt/rho are invariant through this perpendicular fast wave. Supply the
physical star EMF and the following one-time laboratory ALE exchange:

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
time/weight, centroid x_f, area, W, Pi_star, physical branch/uncertainty, comparator fallback (if requested), and signed exchanges.
With `I_f=-dt_weight area Pi_star n` the impulse **to gas**, save

```text
Delta P_wall_to_gas=I_f;
Delta L_wall_to_gas=(x_f-x_ref) cross I_f;
Delta E_wall_to_gas=W dot I_f.                                (B12)
```

The support holding the wall receives the opposite impulse/torque. For
W=0 its work is zero even if net force is nonzero. A stationary wall does
not imply zero wall force. Internal face antisymmetry conserves internal
exchange but does not remove this external impulse. Cell-centroid L also has the explicit representation channel
`(c_i-x_f) cross I_f` for a monopole momentum kick at c_i rather than
x_f, in addition to centroid-motion and hydro errors. Report these
separately; this difference is not another wall force. Use the
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

### 7.1 Exact selected rows, support and spaces (O1–O3)

**E: `relative-local-quadratic-adjoint-v2`.** These are new engineering
maps, not P26's unconstrained LS operator. For target real cell i choose
origin c_i (volume centroid), h_i=V_i^(1/3), coordinates d=(x-c_i)/h_i.
Freeze its wall patch set to **only planes incident on that target cell**.
An interior target has none. The face evaluator uses its real owner's
same polynomial, same patch set and same coefficient map, evaluated at
the face point. A wall face's own plane is therefore included. Expanded
rows never add another cell's planes. Opposite-wall unioning is withdrawn.

Initial observations are the central cell and unique real cells within
two face-neighbour BFS rings, sorted by CellId; no ghost observations.
Try (rings,radius/h)=(2,4),(4,6),(6,8) in order. Include all real cells
within both bounds, at most 256; exceeding that cap is a typed
`BoundaryStencilCapacity` rejection, not order-dependent truncation.
Require target diameter/h<=8 and that no selected physical target touches
opposite parallel walls. If support/rank/conditioning fails at the last
choice, return `BoundaryResolutionUnresolved`: refine/review before a
physical run. These radii/caps are frozen proposals, not successful results.

For every included scalar sample j, including j=i,
```text
M_j = [monomials of d_j in the chosen basis];
q_j = real owner sample q_j;
w_j = 1/sqrt(1+dot(d_j,d_j));   W=diag(w_j).              (O1)
```
Thus the central weight is exactly 1. There is no 1/0 distance rule or
unstated face-area weight. A vector sample has three rows
`e_k tensor M_j`, observations q_j,k, identical weight w_j for k=x,y,z;
component-major ordering then CellId ordering is used. All repeated real
owner dependencies are coalesced before transposes/diagonals. Two-ring
observations are values, never invented derivatives.

Select total-degree monomials:
P1=(1,dx,dy,dz);
P2=P1+(dx²/2,dy²/2,dz²/2,dx*dy,dx*dz,dy*dz).
For the scalar three-wall amendment only, P3 is all 20 total-degree<=3
monomials ordered by degree then decreasing x exponent then decreasing y
exponent, scaled by the exponent factorials. P1 is a diagnostic comparator;
**production uses vector [P2]^3 and scalar P2 except scalar P3 for a target
incident on three distinct coordinate walls.** The P3 corner change is
explicit: quadratic Dirichlet scalar space there is zero, which cannot
approximate a nonzero corner cleaning field. It is not inherited from M1.

For vector A impose polynomial trace `A_t=0, div A=0` on every selected
plane, equivalent to `A_t=0, partial_n A_n=0` for planar traces.
For phi impose polynomial trace phi=0. Translate exact physical wall
locations into target-scaled coordinates before forming every coefficient
constraint; no face-centre-only collocation. Let Lc=0 be these homogeneous
constraints, Z an orthonormal basis of ker L. For a future prescribed
inhomogeneous trace Lc=g a specified lift c_g would be required; the present
state maps have c_g=0, not an unspecified fitted lift. Freeze
```text
K = Z (sqrt(W) M Z)^dagger sqrt(W);
c = c_g + K (q - M c_g).                                (O2)
```
Normalize each nonzero dimensionless constraint row to unit Euclidean norm.
O2a fixes the exact redundancy, scaling, signs, ordering and condition
criterion for the selected column-pivoted Householder QR. SVD remains an
independent spectrum diagnostic, never a runtime fallback. Require full
reduced rank and at least two surplus scalar rows (or six vector rows)
over the reduced dimension. A zero-dimensional space is an explicit
diagnostic zero map, **never a physical rank/approximation pass**.
The spatial gates below, not this rank rule, decide approximation.

The following exact spaces in coordinates with incident planes x=0,y=0,z=0
make support failures reviewable (signs/translations do not change dimensions):

| Incident planes | scalar P1/P2 dimensions | vector [P1]^3/[P2]^3 dimensions |
| --- | --- | --- |
| none | 4/10 | 12/30 |
| x=0 | 1/4 | 5/15 |
| x=y=0 | 0/1 | 2/7 |
| x=y=z=0 | 0/0 (selected P3 has 1) | 0/3 |
| all six box planes | 0/0 | 0/0: unsupported physical resolution |

At one wall scalar P2=x(a+bx+cy+dz). Vector P2 has
A_x in span{1,y,z,y²,yz,z²,x²}, A_y,A_z in x*P1.
At two walls scalar P2=a xy and
A=(y(a+by+cz), x(d+ex+fz), gxy).
At three walls selected scalar P3=a xyz and
A=(a yz,b xz,c xy). These explicit spaces are polynomial facts, not
arbitrary smooth-function accuracy. Targets spanning opposite walls are
rejected before these rules are invoked. Cross-wall thin cells must be
refined, not assigned a formally full-rank zero approximation.

With real-owner gather S_i, assemble the **full affine map**
```text
c_i = K_i S_i q + (I-K_i M_i)c_g,i;
C_i = E_curl,i K_A,i S_A,i;
G_i = E_grad,i K_phi,i S_phi,i.                           (O3)
```
The derivative evaluations include h_i^-1. With homogeneous traces the
constant term vanishes, but central/global coefficient dependencies do
not. If implementation subtracts a scalar baseline q_b,
`K q = K(q-q_b 1)+q_b K1`; for a vector baseline use the block
constant-sample embedding J: `Kq=K(q-Jb)+KJb`. K1/KJ are computed,
not assumed zero. Constant A is generally incompatible with the wall.
A data-dependent lift/baseline must be expanded into real-owner columns
before applying an adjoint or diagonal; treating it as a frozen constant
would assemble another operator.

Cell curl is curl of this owner's polynomial at c_i; raw wall B is curl
of **the same** polynomial at the wall centroid. Therefore wall Bn=0
holds algebraically along each patch, and cell/face compatibility is
explicit. No independently fitted face A or B is selected. Its two
boundary donor traces are the same owner polynomial value; no ghost
selector changes the normal induction term. No componentwise limiting of
these constrained vector coefficients is allowed: it could break the
coupled constraints. Positivity limiting of incident rho/p is separate.
Optional future A limiting would need one scalar contraction about an
admissible constrained baseline and a new reviewed approximation gate.

**U2 narrowed:** rows, weights, planes, spaces, expansion and cell/face
evaluation are now specified. Reproduction of all these admissible
polynomials, boundary-band approximation of higher-degree fields and
conditioning on irregular meshes are unexecuted; the dimension table is
not a proof of those results.

#### 7.1.1 Numerical QR policy, without changing the exact map (O2a)

**D/E: `boundary-qr-frobenius-v1`.** Dimensionless monomials, objective
weights W and O2's unique constrained weighted-LS problem are unchanged.
The following is a numerical decision profile, not a published P26 rule.

**Constraints and identities.** Coefficient columns keep the declared
scalar basis order, or x/y/z component-major copies of P2. Enumerate
constraint rows by axis x,y,z; side lower,upper; then A's tangential
components in x/y/z order (excluding the normal component), then
partial_n A_n. Scalar phi has only its value trace. For each trace use the
remaining-coordinate monomials in the order induced by its declared
coefficient basis, removing duplicate monomials on restriction. Each row
has an immutable (axis,side,trace-component-or-normal-derivative,
trace-monomial) identity. Row expansion never changes the target patch set.

Form raw polynomial coefficient rows **symbolically**, treating the stored
finite binary64 scaled wall offsets as exact dyadic inputs, with exact
factorial factors. Scan rows in that order; exact rational elimination
uses the first nonzero coefficient column as pivot, and retains the first
row that increases the exact row rank. Drop only an exactly zero row or
an exactly dependent row, recording its identity and exact dependency.
This small constraint calculation has at most30 coefficient columns;
it is distinct from a floating QR rank decision. Do not declare a tiny
nonzero pivot redundant. Normalize each retained nonzero row by its full
Euclidean norm, obtaining L_I. Unrepresentable normalization/nonfinite
coefficients or insufficient conditioning reject; they do not delete a
constraint. The input chart/offset rounding is fixed and hash-recorded;
physical trace residuals against the actual wall remain separate gates.

There is **no additional column scaling of L_I^T**. Factor
`L_I^T P_L=Q_L [R_L;0]`. With p coefficients and exact rank r, the full
Q_L defines Z=Q_L[:,r:p], dimension p by d with d=p-r. Independent-column
identities for this QR are the retained original constraint-row identities,
not their transient array positions. Empty constraints give Z=I and no
constraint condition test; d=0 retains the diagnostic-zero/physical-reject
rule. Surplus observation counts and all O1 approximation gates are unchanged.

**Reduced fit and unscaling.** Let A=sqrt(W) M Z and
`s_j=norm2(A[:,j])>0`, S=diag(s_j), Ahat=A S^-1. Null-basis column j has
identity (full-Q-completion,j) in ascending completion order. A zero or
unrepresentable s_j is a reduced-fit failure, not a removable unknown.
Use column-pivoted Householder QR
```text
Ahat P_A = Q_A [R_A;0];
y = S^-1 P_A R_A^-1 Q_A,1^T sqrt(W) (q-M c_g);
c = c_g + Z y;
K = Z S^-1 P_A R_A^-1 Q_A,1^T sqrt(W).                  (O2a)
```
Q_A,1 contains the first d columns. Full column rank makes the minimizer
unique: z=P_A^T S y is an invertible change of variables, so this solves
exactly O2, including its free intercept and real-owner baseline/lift
dependencies. Omitting S^-1, reversing the pivot incorrectly or dropping
K1/KJ changes c and hence C/G. Assemble the full real-owner K before any
adjoint or coalesced-column diagonal. The scaled condition below is not
a condition bound for the whole unscaled C/G; report the s_j range too.

**Fixed QR choices.** At each step recompute every remaining column's
tail norm in ascending row order; do not use downdated norm heuristics.
Choose the greatest computed binary64 norm; exact equality of these
deterministically rounded scores chooses the smallest original column
identity, with +0 canonicalized. The pivot permutation is then fixed for
its enclosure/audit. Use Householder beta=-sign0(x0)*norm2(x), with
sign0(0)=+1, no cancellation-prone opposite choice. A zero tail is a rank
failure. Canonicalize nonzero R diagonals positive by matching Q-column/
R-row sign changes. For null completion columns, make the largest-magnitude
entry positive, ties by original coefficient index. Retain these choices
and all pivot identities; no rank/thread-dependent alternate basis.

For **both** square triangular factors R_L and R_A require every
`rho_k=abs(R_kk)/abs(R_11)>=1e-10`, with the first leading pivot strictly
positive, and
```text
kappa_F(R)=normF(R)*normF(R^-1)<=1e8.                    (O2b)
```
Obtain R^-1 by deterministic triangular solves against unit columns in
ascending column order, backward rows, each inner sum in ascending column
order. Norms use scaled sum-of-squares accumulation: maintain a^2*b=sum x^2;
initialize (a,b)=(0,1).
For |x|>a replace (a,b) by (|x|,1+b*(a/|x|)^2), otherwise add (|x|/a)^2
to b, skipping exact zeros. Norm2 scans rows ascending, Frobenius scans
columns then rows ascending. This avoids overflow in naive square sums;
nonfinite/underflow ambiguity still rejects. Fix binary64 round-to-nearest,
ties-to-even, disabled reassociation/FMA contraction, and the same reduction
order for every partition.
It is not an order-dependent norm estimator.

Enclose the exact normalized inputs and the QR factors for the selected
permutations using outward-rounded interval elementary operations (including
sqrt), then the triangular inverse actions and both norms. This enclosure
must include normalization, orthogonal-basis and factorization roundoff,
not just rounding of an already computed condition number. Certify all
rho lower bounds and the kappa_F upper bound. Nonfinite bounds, a divisor
interval containing zero, a threshold-straddling interval or unsupported
arithmetic returns `BoundaryQRDecisionUnresolved`; no SVD, relaxed gate,
coefficient clipping or silent map change follows. Exact score ties use
the declared identity rule; uncertainty in an acceptance threshold rejects.
The immutable fit plan retains row/column identities and raw-constraint hash,
exact dependency records, Z/sign/pivot choices, all s_j, rank ratios and
condition enclosures with its geometry/state/source epochs and map hash.

**D:** normF(R)>=norm2(R) and normF(R^-1)>=norm2(R^-1), hence
kappa_F(R)>=kappa_2(R). Orthogonal factors/permutations preserve singular
values, so this is a conservative concrete condition test for L_I^T and
Ahat. For an identity block of dimension d, kappa_F=d, not1. It can reject
a matrix an SVD condition test would accept; it cannot relax the old1e8
gate. Constraint conditioning cannot be repaired by adding observation
rows. A fit failure may try only the next frozen O1 support, with the same
planes; final failure is typed rejection. Empty/zero spaces are not passes.

Before B-FIT execution freeze independent literal raw constraint rows,
admissible bases, W/M, full K/C/G and rank/condition decisions. Include
exact dependent rows and distinct tiny nonzero controls, unequal s_j,
pivot ties/signs/permutations, threshold-straddling enclosures and deficient/
zero/surplus-row cases. The independent oracle uses exact nullspaces and
high-precision weighted LS/SVD diagnostics, not production QR. No literal
matrix, QR factorization or condition test was executed in this revision;
approximation and operator consistency remain U1/U2 prerequisites.

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
magnetic wall trace comes from that same constrained A fit, with no
independent component limiter. Rho/p and primitive velocity gradients use
one-sided P1 rows/weights from O1 with independently reported positivity
limiting; neither their normal derivative nor the incident normal speed is
forced to zero. Interior primitive/B gradient policies remain the moving-stage
separately linear-fitted profile; this wall's incident B is explicitly the
owner A-polynomial curl, not a component-limited independent face B fit. The exact
conservative flux uses W1–W5 and (B11), not a centred polynomial through duplicated
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

### 8.1 Actual closure, dimensions and masses (O4)

**E/D:** for N real cells, nodal A has 3N entries in cell-major
(Ax_i,Ay_i,Az_i) ordering and phi has N. Local component-major fit rows
are reordered by the explicit S_i gather; they do not change the mass matrix. They are
samples, not coefficients of a global conforming space. C is 3N by 3N,
G is 3N by N, assembled from O3's owner maps. Ms=diag(V_i)>0,
Ma=Ms tensor I3; use the actual tessellated volumes at that stage.
The selected closure is **unprojected** G and
`D_clean=-Ms^-1 G^T Ma`, as in B9. No ker(C) projector is selected;
it could annihilate G. No assertion C*G=0 is made. Any explicit ghost
extension must first be assembled in the real-owner map
(C=R C_ext E, C^T=E^T C_ext^T R^T), including central and baseline terms.
The discrete negative-adjoint identity is exact algebra, while consistency
of both G and D_clean is an independent question.

For constant frozen c_h>0 and damping kappa_i>=0 the fixed-geometry pair is
`a_dot=G phi, phi_dot=c_h² D_clean a-kappa phi`. Its energy
`Eg=.5 a^T Ma a+.5 phi^T Ms diag(c_h^-2) phi` has derivative
`-phi^T Ms diag(kappa/c_h²) phi`. This is gauge/cleaning energy,
not physical magnetic or gas energy. The cancellation also holds for
G=0, and therefore proves no approximation. Variable frozen cell c_h is
allowed with the stated diagonal energy, but time-dependent volumes/c_h
and auxiliary transport add metric/transport terms; they require the
moving-stage analysis, not a fixed-mass energy assertion.

Screening makes the active increment objective unique, but is not a proof
that the state is in a preferred physical gauge. There is no periodic constant-A gauge pin. Measure the full singular
spectra of C, G and scaled cleaning matrix
`Kc=Ma^(1/2) G diag(c_h) Ms^(-1/2)` in the small reference slices.
Distinguish polynomial-fit rank, curl nullspace, cleaning nullspace and
physical relative harmonic kernel (ABDG); they are different objects.
A common constant scalar is not a Dirichlet gauge. Continuum curl-free
gradients of functions constant on the boundary need not belong to the
state space with div A wall trace zero; gauge transformations also have
the B7 compatibility conditions.

For projection use the exact coalesced real-owner columns:
H=C^T Ma C and D_kk=sum_i V_i |C_ik|². A structurally zero column is
fixed to zero **correction** and its RHS checked zero. Near-zero but
nonzero D_kk<1e-14 max(D) is `UnresolvedProjectionObservable`, not
discarded. Active screening is 1; active D must be finite positive.
Use the moving-stage increment projection, not the withdrawn old B15
finite-endpoint formula: integrate the RAW A rate, project each trial
increment once; corrector starts at a0 and Q0. Exact map derivatives for
bounded Cdot must include K, weights, scaled basis, planes and volumes.
The fixed/rigid M1 guard is no argument for this moving bounded derivative.

The bounded physical target uses the **box frame** T=W, not an implicit
periodic mean-field split: target induction is laboratory ALE face
induction plus returned face Bn times W; wall Bn=0 gives zero exchange.
Auxiliary/gauge velocities are v-W,u-W,w-W, B_mean=0 throughout.
This is an explicit bounded engineering frame profile. The run's Vref
metadata remains frozen, never retuned to make it coincide with W. A
comparison using identical interior faces against the moving-stage
full-Vref target includes rate difference
`-(W-Vref) * d_returned`, with the review's signed returned-face
divergence. Agreement is only expected as that divergence converges.
Root integration/review must reconcile this bounded frame specialization;
this document does not amend the owned moving/shared contracts.

A solve's true normal residual <=1e-9 (iterative residual <=1e-11,
maximum 24N iterations, dimensionless RHS threshold 1e-30 after the
registered field/volume scaling) is only a solve gate. Report separately:
target mismatch, raw evolution and Cdot change, projection change,
raw volume-mean B, wall trace, and cellwise/signed/sum-absolute
magnetic-to-thermal transfers. Q energy is unchanged by projection;
Delta Uthermal_i=-Delta EB_i, not wall work. Reject a pressure failure,
do not reset it. The mean gate is prospective
`|sum V B|/(Vbox Bref)<=1e-9`: failure blocks this candidate.
Do not subtract a measured mean or retune B_mean. Tight solves cannot
establish target/mean/trace compatibility or physical positive closure.
Retain the mesh contract's separate raw linear-LS div(B), same-fit Hessian
div(curl A) identity, raw/limited shared-face divergence and returned-face
divergence; a zero same-fit identity or cancelling global face sum is not
proof that the other operators vanish. Their existing nonzero-field gates
remain prerequisites.

### 8.2 Time and consistency gates for this actual pair

**D/E:** even for kappa=0, Heun has
`|R(i sigma dt)|²=1+(sigma dt)^4/4`. Thus no strict non-growth
claim is valid. On frozen geometry sigma_max=||Kc||2 can be bounded by
sqrt(||Kc||1 ||Kc||infinity). Freeze sigma dt<=.1 and
`dt³<=4 log(1.01)/(T sigma^4)` for a pure undamped cleaning run
of duration T: the product energy-growth bound is <=1.01.
If sigma=0 this bound is vacuous and the consistency gate still applies.
For damped frozen L in the energy-scaled variables,
L is skew-adjoint minus nonnegative damping and ||exp(tL)||2<=1.
Let Lambda=sigma_bound+max(kappa); Heun's local operator difference
is <=exp(dt Lambda)(dt Lambda)^3/6. With dt Lambda<=.1 and
`dt²<=3 log(1.01)/(T exp(.1) Lambda³)`, multiplying this bound
gives energy norm-squared growth <=1.01. These conservative engineering
step bounds concern the frozen cleaning subsystem, not stability of the
full moving MHD method. They are not retrospective M1 restrictions.

Freeze N=8,16,32,64 unit-cube regular and 0.1h deterministic interior-jitter
geometry families with fixed walls and shape rejection. For each measure
both full-domain and first two h boundary bands; report face/edge/corner
bands separately. G on analytic Dirichlet phi and D on analytic relative
A must converge to the actual gradient/divergence, respectively:
global L1 orders >=1.8 for G and >=1.5 for D; boundary-band order >=1;
finest relative errors <=.1. Include
phi=sin(pi x)sin(pi y)sin(pi z) and
A=(cos(pi x)sin(pi y)sin(pi z),0,0), whose divergence is nonzero
in the interior and zero on all walls. Do not use only divergence-free A.
C*G and C applied to independently sampled analytic gradients must have
spurious-B order >=1.5 and finest error <=.01 Bref at fixed declared
phi/A scale. Report exact/near kernels and active columns at every N;
nonconvergent boundary modes are a failure even if adjoint error <=1e-12.
Also require algebraic raw wall Bn and state A_t/div-trace <=1e-10
of their scale, projection mean gate above, target convergence,
and sum-absolute projection thermal transfer <=1e-3 initial EB_ref
over the fixed-duration smooth field fixture. Use nonzero EB_ref, never
a B=0 normalization. Positive closure/nonzero-field/boost gates remain.

### 8.3 Combined forcing trace, not separately constrained forcing (O5)

**D:** at a fixed box-chart wall the physical rate is
```text
F = (v-W) cross B - grad((u-W) dot A);
partial_t A = F + grad(phi);
P_t(F+grad(phi))=0;
div(F+grad(phi))|wall=0  =>  Delta(phi)|wall=-div(F)|wall.   (O5)
```
Phi=0 implies tangential grad(phi)=0 at the wall. The normal induction
and normal grad(phi) are allowed; setting normal A_dot=0 would be wrong.
For a general forcing div F need not vanish there. Imposing both
div F=0 and Delta phi=0 separately would solve another problem.
The selected cell rate is the named moving-stage raw xyz rate with this
box-frame F, centroid transport and G phi, and phi_dot uses B9 damping
plus the same centroid/auxiliary transport. Evaluate the physical face
EMF from W1–W5 and the gauge derivative from the owner A and anchored
auxiliary jets. For an independent diagnostic of div F, fit unrestricted
one-sided P2 vector data with O1's weights/support, not the state A
constraints. This diagnostic is not another independently evolved F.
The state is refit in its relative space at each trial stage. That
refitting alone does **not** prove that its semidiscrete forcing/cleaning
satisfies O5 or that the constraint does not contaminate the interior.

A nontrivial forced manufactured compatibility case is fixed on stationary
geometry with v=u=w=0 and an explicitly imposed artificial A forcing
F_MMS; this is a compatibility test, not a physical MHD solution. Choose a smooth relative divergence-free A_m from B2 or the R8 background,
A=cos(t) A_m,
phi=1e-3 sin(t) x²(1-x)² y(1-y) z(1-z),
F=-sin(t) A_m-grad(phi), and scalar forcing
S_phi=partial_t phi+kappa phi.
Then partial_t A=F+grad(phi) and div A=0 exactly; Delta phi is
nonzero on x walls and is cancelled by -div F. Independently sample
the analytic F and derivatives; never define it as minus the discrete
G phi merely to force cancellation. The full and boundary-band errors,
constraint residuals, C*G contamination and physical mean are measured
against these analytic fields through a nonzero interval.
Pure-cleaning compatibility (Delta phi=0 at the wall) is a separate case.

**U1/U3 precise remaining prerequisite:** no consulted source proves
consistency of this specific cell-centred constrained G/negative-adjoint
D, its C*G defect, or moving forced trace. Do not claim a complete accepted
wall algorithm. The smallest implementation slice after M1 and this new
review is a **fixed-geometry, gravity/source-off map builder**, physical
wall pressure oracle and the algebra/manufactured cases above, including
full matrices/spectra and independently sampled forcing. It can falsify
the candidate before a coupled stepper is written. Passing it still does
not establish moving bounded Cdot/GCL or physical reflection.

## 9. Smooth auxiliary velocity, deposition and boosts

**P26/E:** a smooth auxiliary u with a finite Jacobian is the gauge input;
P26 section 4.3 motivates C1 interpolation, not this bounded construction.
The selected anchored box-chart grid has a fixed chart anchor a, widths L,
and n_aux intervals per axis, **n_aux+1 distinct nodes**
q_k=a+k L/n_aux, k=0,...,n_aux. End nodes are not periodically identified.
Real chart coordinates obey a<y_s<a+L. Allow nonzero a explicitly.
The laboratory chart origin is X0+W(t-t0); the auxiliary anchor is that
origin plus a. It is recomputed at each requested stage time, never advanced
by a mean velocity or translated a second time at sampling.

For each real sample s, positive weight is
V_s product_axis beta3((q_axis-z_axis)/h_axis), h_axis=L_axis/n_aux,
with signed r=(q-z)/h and the **even** `anchored-even-beta3-v1` kernel
```text
beta3(r)=2/3-r^2+abs(r)^3/2,          abs(r)<1;
         (2-abs(r))^3/6,             1<=abs(r)<2;
         0,                         otherwise.          (O7a)
```
The older signed r^3 literal was wrong; the unchanged revision review
retains its negative/asymmetric/discontinuous counterexamples. Frozen M1's
fractional-coordinate weights are not a proof for that signed literal.
For every axis enumerate **all** image words
```text
z = a+2*m*L+sigma*(y_s-a),   m integer, sigma in {-1,+1}.    (O7)
```
An explicit finite superset of integer bounds is
floor((q-2h-a-sigma*(y_s-a))/(2L))-1 through
ceil((q+2h-a-sigma*(y_s-a))/(2L))+1, inclusive.
Filter by the strict support |q-z|<2h using the declared floating enclosure;
an uncertain support comparison is `AuxiliaryImageBoundaryUnresolved`,
not a nondeterministic tie. A certified equality has zero beta and is
excluded. Take Cartesian products, sorted by
(CellId,mx,my,mz,sigmax,sigmay,sigmaz). This includes multiple mirror
layers when h is coarse; nearest-mirror-only enumeration is forbidden.

Image vector component k is sigma_k*(v_s-W)_k; translations by 2mL
do not change parity. All three components share the same positive unsigned
volume-kernel denominator. Retain each reflection word's multiplicity if
positions coincide, rather than deleting an odd/even partner; exact
plane samples are prohibited for real centroids but are explicit algebra
controls. Reflection words at a shared boundary cancel odd components
pairwise. Real CellIds are dependencies, never new image entities. All
physical mass, gravity and means exclude images. Reproducible reductions
use the same sorted words and accumulation algorithm, independent of rank
decomposition. Enumerating many images does not add physical samples.

**D, manual O7a disposition, not executed kernel evaluations:** put s=abs(r).
On [0,1], beta decreases from2/3 to1/6 because
beta_s=-2s+3s²/2<=0; on [1,2] it is (2-s)^3/6>=0.
It is strictly positive for |r|<2 and zero outside. Dependence on abs(r)
and r² proves evenness. At r=0 the value/first/second derivatives are
(2/3,0,-2) from both sides. At r=+1 the inner and outer triples are
(1/6,-1/2,1); at r=-1 they are (1/6,+1/2,1). At both +/-2 the triple
is (0,0,0), matching the zero branch. Thus beta is C2 (not claimed C3).
In particular the repaired beta(+/-1/2)=23/48 and beta(-3/4)=121/384;
these manual values do not rewrite the review's old-formula counterexamples.

At the lower wall the word bijection (m,sigma)->(-m,-sigma), and at the
upper wall (m,sigma)->(1-m,-sigma), sends q-z to its negative and flips
the normal velocity sign. O7a gives equal weights; other-axis factors,
positive volumes and tangential components are unchanged. Keeping every
word, including coincident multiplicities, proves normal cancellation in
exact arithmetic, including corners by commuting Cartesian bijections.
The denominator is the **unsigned** sum D(q)=sum_words V_s product beta,
never a parity-signed sum or absolute value of a signed sum. For n_aux=1
and at least one positive-volume real owner strictly inside the box, its
direct word alone has |q_axis-y_s,axis|/L_axis<1 at every corner node, so
D(q)>=V_s/216>0. This is a root-grid existence bound, not permission to
floor an underflowed denominator or pass coarsened physical cases.

**E, smallest prospective B-AUX-KERNEL packet:** use anchor
a=(.3,-.2,.7), L=(1,1.5,.75), n_aux=1, one real sample at
a+(Lx/4,Ly/3,2Lz/5), V=1 and v-W=(1,2,3); separately include declared
plane/coincident-word algebra samples. Retain all support words/layers
from O7, both distinct endpoints and their edge/corner products. Check
beta, beta' and beta'' against the manual triples at0,+/-1,+/-2 and at
each knot +/-delta, delta=2^-8,2^-20,2^-40. Compare complete finite image
enumeration to an independent enlarged-word-box sum and each wall's word
bijection before imposing exact odd-node zeros. Require interval-certified
nonnegative beta and evenness/C2-reference errors<=1e-12 scaled, positive
denominator with
independently enclosed sum (relative error<=1e-12), and normal numerator
cancellation<=1e-12 times its unsigned volume-kernel speed scale.
Never normalize by the nominally zero normal numerator. Test uncertain
support/underflow/empty-input rejection; normal-odd and tangential-even
values/derivative parity remain distinct. Every knot/side/anchor/word case
is a separate future REANA workflow, 1 thread/2 GiB/5 min, after M1,
independent review, literal packet and preflight. This is not a new
executable kernel, draw or observed denominator result.

Extend nodal values by folding integer indices into [0,n_aux] using even
2*n_aux reflection, with component-normal odd parity and tangential even.
Indices 0 and n_aux remain separate physical nodes. Set a boundary value/jet exactly zero only when its **combined component
and derivative parity** is odd; a normal derivative of a normal-odd
component is even and is not zeroed. Derivative jets use
centred differences on these parity-defined nodes, composing x,y,z in
that order; differentiation reverses parity in that coordinate. Store one
shared value and the 7 first/mixed jets per corner. The tensor cubic
Hermite polynomial uses 8 corners times 8 jets (64 coefficients per
component), with analytic value/Jacobian sampling. Same shared jets ensure
C1 across auxiliary cells, and u_r,n=0 identically on each wall/edge/corner.
Tangential evenness here is an auxiliary engineering choice, not a
thermodynamic/gravity or resistive B boundary condition.

Freeze requested n_aux=4 for the first slice, and independent physical
controls 4/8/16. If any node has no certified positive denominator,
**whole-grid** coarsening halves n_aux through 1, rebuilding every node
and jet from all real owners and the complete image enumeration. The
support footprint is now the whole box, not a local galaxy patch.
A physical acceptance case requires active n_aux=requested n_aux and no
empty/coarsened node anywhere; failing this is a resolution/design failure.
Algebra/restart controls deliberately allow coarsening/root changes and
record the full branch. Root n_aux=1 failure is
`AuxiliarySupportUnresolved`; the old automatic u=W fallback is withdrawn.
The constant u=W, zero-Jacobian field remains an explicitly requested
algebra profile only, never a hidden production fallback. No discontinuous
patchwise fallback or second rolling-origin shift is allowed.

Every cache/input record includes profile/grid/root/image policy, anchor,
the O7a kernel and O2a QR-policy identities,
requested/active n_aux, geometry epoch, real state epoch, source epoch/hash,
physical time, stage name, sorted owner/map hash and chart hash. Old,
predicted endpoint and accepted final states get distinct immutable records;
a retry cannot reuse jets from a rejected predicted/final state.
Checkpoint the fixed anchor/chart, profile and root metadata; deterministic
rebuild must reproduce hashes/branch, not reset the gauge. Future controls
include nonzero anchor, >one mirror layer at n_aux=1, root 4->2->1 changes,
globally coarsened support, ID order, restart and joint boosts.
Old signed-kernel or unspecified-QR cache identities cannot be silently
reused under these profiles; a mismatch rejects the restart/cache input.

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
boundary sweeps in **each exchange-graph connected component**, not just
the global sum. Auxiliary reflected images never become exchange edges.
Reject a generator crossing or touching the outer plane;
no reflection/deletion of a generator or cell state is implicit.

The full trial sequence is owned by
[MOVING_MHD_STAGE_SPEC.md](MOVING_MHD_STAGE_SPEC.md), not a new split here.
This specialization supplies the following immutable boundary providers:

1. At g0/t0 and old real Q0,a0,phi0, rebuild target-local O1–O3 maps,
   C/Ct/G/Gt, raw wall trace and old auxiliary jets at the anchored chart.
   The wall provider returns W1–W5 physical star state/exchange and normal
   A induction once per wall face; the box wall speed is always W dot n.
2. Construct endpoint generator geometry g1/t1 **before** locating predicted
   centroid samples, using that contract's predictor relocation and
   topology/GCL policy. Rebuild endpoint maps for actual volumes/centroids.
   The predicted raw A increment is projected exactly once on g1.
   Predicted Q and phi are assigned from Q0/phi0, not a partially accepted
   final state. Recover Bpred=C1 apred and thermal state without reset;
   build fresh predicted real-owner auxiliary data at chart time t1.
3. Use OLD and PREDICTED ENDPOINT owner states (and their own geometry/
   chart epochs) for corrector samples, wall stress and source-free
   transport/cleaning rates. An absent wall face is reevaluated through
   its stable real owner/physical patch provider at that quadrature time,
   not a stale polygon or ghost EntityId. No second accepted source event
   is inserted into this MHD substep.
4. Start corrector from Q0,a0,phi0. Integrate raw rates and conservative
   wall/interior exchanges, prescribed wall sweeps and GCL once, then
   project the one corrector trial increment once. Recover final B,
   thermal state and all independent mean/trace/target diagnostics.
   Build final auxiliary data afresh at t1 from final real-owner state;
   it is not one of the four old/predicted target samples.
5. Commit only after all geometry/physical/solve/trace checks. Wall
   impulses/work/torques and source/allocator records commit atomically;
   rejected ledgers never accumulate. Retry begins from the identical
   immutable old checkpoint with a smaller registered interval, fresh
   epoch IDs and deterministic rebuilds. No IDs/random draws/source
   events are consumed by a rejected trial. An unresolved topology,
   vacuum, map/root support, pressure or projection condition returns
   its typed failure; it never switches boundary/auxiliary algorithms.

Discrete bounded Cdot and O5 compatibility remain U3, and the separate
moving-stage review may identify additional order prerequisites.
No wall design text claims those independent issues are solved.

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

Use box `[0,1]^3`, gamma=5/3, rho=p=1 unless stated, N=8/16/32/64 Cartesian
and separately frozen .1-spacing interior-jittered arrays (same counter-seed scheme
as the mesh contract), axes and component permutations. Initial budgets use
the gravity contract's fixed nonzero P/L/E scales; field errors use fixed
initial B amplitude, never a nearly zero current field. Algebra tolerances
are `max(1e-10,64 epsilon cond)` times a stated analytic scale unless the
table gives a tighter adjoint/trace gate. Report absolute errors too.

| Family / prerequisite | Frozen fixture definition and measurements | Proposed acceptance criterion | Initial envelope per independent case |
| --- | --- | --- | --- |
| B-WALL / M1, new wall-pressure design review and preflight | All exact W1–W5 fixtures in WALL_RIEMANN_SPEC, including receding counterexample, shock, stationary, gas-only, strong-B and vacuum thresholds; signed axes/proper rotations and joint W boosts. Compare physical oracle, raw HLL/HLLD traction and completion separately. | Physical p/rho/Pi positive in supported nonvacuum branches; independent high-precision state/jump error <=1e-10, root/boost/constructed ALE identities <=1e-12; typed vacuum/bracket/epoch failures. Negative raw HLL counterexample is expected diagnostic, never a physical pressure. | 1 thread,2 GiB,5 min |
| B-AUX-KERNEL / M1, O7a review and preflight | O7a knot/side/nonzero-anchor/all-image-word controls, unsigned denominator, n_aux=1 multiple layers, distinct endpoints and edge/corner mirror cancellation; independently enlarged image enumeration. Then requested4/8/16, root4->2->1, restart and epoch controls. | Certified nonnegative beta, even/C2-reference and unsigned-denominator errors<=1e-12; normal numerator<=1e-12 unsigned speed-weight scale; typed empty/uncertain support failures. Coarsened physical cases remain failures. | 1 thread,2 GiB,5 min for each kernel/algebra member |
| B-FIT / geometry and reviewed O1–O3/O2a | Full selected admissible P2 A/P2 phi and P3 scalar corner bases, central/two-ring constant-data/baseline restoration, one/two/three/opposite-wall targets, support 4/6/8h and deficient/zero-space controls; same owner cell/face evaluations. Add exact dependencies versus tiny nonzero rows, unequal column scales, QR signs/ties/unscaling and threshold-enclosure controls against independent literal matrices. | O2b kappa_F<=1e8 and every abs(Rkk)/abs(R11)>=1e-10 for independent constraints/scaled fit; uncertain decisions reject. All admissible basis values/derivatives/traces reproduce within condition-scaled tolerance; baseline/row/patch-order parity <=1e-12; unsupported physical zero space rejected, never passed by rank alone. | 1 thread,4 GiB,15 min |
| B-ADJOINT / B-FIT and O4 review | Independently assembled small dense real-owner maps with central/lift/baseline/optional diagnostic-extension terms, C/Ct/G/Gt, active columns and full C/G/Kc spectra; B9 derivative without evolution. | Relative adjoint and energy-derivative defects <=1e-12; zero/near-column typed failures match frozen inputs; report CG, divergence/gradient approximation and kernels separately. Exact negative adjoint is not a consistency pass. | 1 thread,4 GiB,15 min |
| B-MMS / B-FIT and B-ADJOINT | Relative A=(a cos(pi x)sin(pi y)sin(pi z),2a sin(pi x)cos(pi y)sin(pi z),-3a sin(pi x)sin(pi y)cos(pi z)), a=1e-3; phi=1e-3 product sin(pi coordinates). Add non-divergence-free O4 A and time-dependent forced O5 field, N8/16/32/64 and face/edge/corner bands. | Curl/G global L1 order>=1.8, D_clean>=1.5, finest normalized errors<=.1; band order>=1, no nonconvergent corner error; O5 analytic forced trace and raw wall traces<=1e-10 scaled. C*G contamination has its separate gauge gate. D inconsistency blocks candidate. | 2 threads,8 GiB,30 min |
| B-GAUGE / B-MMS | chi=`1e-3 sin(pi*x)sin(pi*y)sin(pi*z)`; A=gradchi, phi=0, and separately add gradchi to B-MMS. Analytic curl is zero/change is zero; chi and Delta chi vanish at walls. Derivative-only cases first, then cleaning-only evolution with physical forcing off to t=1. | Raw C G or analytic-gradient sampling contamination converges >=1.5 in L1; finest spurious B / fixed `1e-3*pi^2` <=.01. Actual nonzero defects retained. Evolution may alter A/phi gauge but physical B perturbation <=.01 of that fixed scale and decreases with refinement. | 2 threads,8 GiB,1 h |
| B-CLEAN / B-MMS,Gauge | Pure cleaning box: c_h=1, kappa=0 and separately .15; v_r=u_r=w_r=0. A=grad `[1e-3 cos(omega*t) product sin(pi*y_i)]`, phi=time derivative of that scalar for kappa0, omega=sqrt(3)pi; damped scalar solves f''+kappa f'+3pi^2 f=0. Also choose scalar chi(t0)=0, phi(t0)=1e-3*f(((x-.25)/.1)^2)*sin(pi*y)*sin(pi*z), with O6 bump f and A=grad chi; evolve chi_tt+kappa chi_t=Delta chi, phi=chi_t by an independent converged sine series (uncertainty<=.2%), reflected by x=0; compare the odd/even reflected extension. | Smooth temporal order >=1.8 on fixed spatial map when temporal error isolated; spatial order of B-MMS maintained; reflection phi coefficient -1 and A_n +1 within2% finest, no artificial absorption. O4 spectral/time-step bounds apply; undamped E_clean drift <=1% at finest and decreases with dt; damped energy agrees analytic within2%. Spurious B <=B-GAUGE bound. | 2 threads,8 GiB,1 h |
| B-UNIFORM / B-WALL, moving mesh/GCL | rho=p=1, v=W, B=A=phi=0, stationary/translated box, prescribed deformation from mesh fixture with wall-normal w_r=0. t=.1, dt=.01/.005/.0025; no sources. B=0 is only this GCL/control case. | Uniform drift <=1e-10, volume/GCL <=1e-12, M/E residual <=1e-10; wall P/L ledger residual <=1e-10 and opposite support impulse. Restart and serial ID reorder parity <=1e-10. | 2 threads,8 GiB,30 min |
| B-FIELD / B-GAUGE,CLEAN, full stage/GCL review | B2 compact potential, centre(.5,.5,.5),R=.2,A0=1e-3, u=W, v=W, prescribed deforming mesh; stationary and jointly translated box; t=.1, N8/16/32, same dt ladder. Analytic physical field is fixed in y. Then a separate coupled no-gravity evolution from identical nonzero B (not an equilibrium) with total energy initialized consistently. | Kinematic quadratic B L1 order >=1.8, finest <=.1 fixed amplitude, no wall trace violation; coupled positivity, M and ledger-corrected P/E <=1e-10. Magnetic/thermal partition changes, raw/face divergences and projection true residual reported; no hidden energy reset. | 2 threads,8 GiB,2 h |
| B-BOOST / relevant accepted B-CLEAN/UNIFORM/FIELD | For every preceding supported motion choose b=`(2,-1,.5)` and `(10,7,-3)`, transform wall/mesh/gas/particles/auxiliary chart and compare at identical y and logical dt sequence. Restart at t/2 separate case. | Smooth transformed state/B L1 <=1e-8 of fixed state/amplitude scales; uniform/GCL case <=1e-10. Wall work difference equals b dot impulse within1e-10 E_scale; all corrected budgets retain their gates. A/phi compared only under the stated wall-chart gauge. | Same as unboosted case |
| B-GRAV-WORK / accepted gravity work and B-WALL/FIELD | Exact harmonic-potential hydrostatic control in section 11.2, then separate live gas/particle/nonzero-B case and independently enabled source channels. Retain raw wall/centroid representation torque and source ledgers. | G-HYDROSTATIC: finest rho/p L1<1%, Mach<1e-2 at five sound crossings, energy residual<1e-3, momentum ledger<1e-8. Live no-source energy<5e-3 with stricter parent subcase gates retained; all source/representation bounds preserved. | 2 threads,16 GiB,4 h |
| B-DOMAIN / accepted isolated-galaxy/magnetized/source cases | Same galaxy profiles/resolution/support fields, boxes L=128,256,384 R_d and fixed ambient density chosen by largest box mass <=1e-4 M_pair; separate factors .1/10 in density and pressure as gravity contract. Fixed walls, nonzero fields, genuinely deforming 3D mesh, registered full encounter time. Monitor wall signal arrival, patch stress deviations and ambient accretion. | Existing central-profile domain/ambient change <1% retained; added cumulative net and absolute wall impulse/torque each <=1e-6 P_scale/L_scale after subtracting only the separately shown analytic uniform ambient traction, with raw ledgers retained. Stationary wall work <=1e-10 E_scale; wall mass/metals flux exactly0. Report fast/cleaning characteristic return times and observed reflections. Failure requires larger domain/profile revision, not claiming isolation. | 4 threads,32 GiB,12 h initial; larger envelope frozen from preceding measured calibration |

The B-DOMAIN wall criterion uses both signed and absolute integrated
**excess** traction so opposite impacts cannot cancel to a false pass.
Uniform ambient traction is `p_ambient n` times each face area/quadrature;
subtracting it is a diagnostic with a known static reference, not a
conservative-state correction. If magnetic ambient pressure is later
nonzero, revise the reference before execution; this profile initializes
unmagnetized ambient outside the compact support. The raw ambient pressure
support/energy/gravity remains in the physical state and all ledgers.

### 11.1 Global physical reflection reference (O6, U4 definition)

**D/E:** adopt the review's R8, not a constant-field wave:
on [0,1]^3 let a=1/(10*pi), rho0=p0=1, gamma=5/3,
```text
A0=(0,0,a sin(pi x) sin(pi y)), phi0=v_r0=u_r0=0;
B0=(a pi sin(pi x) cos(pi y),-a pi cos(pi x) sin(pi y),0);
p_eq=1+pi² A0,z²;  J0=(0,0,2pi² A0,z).                    (O6a)
```
All six wall traces hold, mean B0=0, div A0=0.
J0 cross B0=grad(p_eq) follows by differentiating A0,z; this proves a
gravity-off magnetostatic continuum equilibrium, not its discrete stability.
Initialize total energy from rho, p_eq, B0 and kinetic energy, not constant
energy. The range p_eq in [1,1.01], |B0|²<=.01 gives
cmin=sqrt(5/3), cmax=sqrt((5/3)*1.01+.01) as conservative initial
acoustic/fast bounds. This background is z-invariant; the perturbation and
mesh below are genuinely 3D and are not a replacement merger.

Specify the physical perturbation at t=0 by
```text
s=((x-.25)/.08)²+((y-.5)/.15)²+((z-.5)/.15)²;
f(s)=exp(1-1/(1-s)) for s<1, otherwise 0;
delta v_r=-epsilon*cmin*f(s)*e_x;
delta rho=delta p=delta A=delta phi=0;
epsilon=1e-4; independent half-amplitude case epsilon=5e-5. (O6b)
```
Thus delta B=0 initially but a physical compressive velocity pulse in
nonzero B creates magnetic/thermal perturbations; this is not a gauge-only
case. All perturbations vanish in an open collar of every wall, so initial
compatibility is inherited from R8. Repeat three proper cyclic coordinate
rotations of the **entire background/pulse/probe**, not a polarization
inserted into a different background. Include independently prescribed
deforming meshes after fixed-geometry background/wave gates.

The independent reference is the following *variable-coefficient*
linearized ideal-MHD initial/boundary problem, derived by linearizing
the conservation laws in P26 pp.2–3 Eqs.3,7–10,13–14 (or TY13 p.4
Eqs.2.1–2.8) about O6a. **In O6c, every delta denotes the response per
unit epsilon**, not the physical O6b amplitude. Its initial response is
delta v=-cmin*f(s)*e_x and delta rho=delta p=delta B=0; O6c contains no
epsilon factor. The actual first-order physical perturbation is epsilon
times this response (plus nonlinear O(epsilon²) in the candidate):
```text
delta rho_t = -rho0 div(delta v);
rho0 delta v_t = -grad(delta p)
                +(curl(delta B)) cross B0+J0 cross delta B;
delta p_t = -delta v dot grad(p_eq)-gamma*p_eq*div(delta v);
delta B_t = curl(delta v cross B0),    div(delta B)=0;
delta v_n=delta B_n=0 at every wall.                       (O6c)
```
Gravity, cooling, SF, feedback, explicit resistivity and all external
forcing are off. The *physical reference* has no gauge/cleaning subsystem;
the candidate's selected A/phi subsystem remains on and any magnetic
contamination counts against its error. Do not turn cleaning off merely to
match the reference. No coefficient or eigenmode of a periodic P26 wave
is imported. Tangential slip and the globally compatible reflected
extension close this particular linearized smooth problem.

**Independent reference construction E:** use a separately written Fourier
Galerkin linear operator on the reflected period-2 cube [-1,1]^3.
Extend v and B with normal-odd/tangential-even parities, rho/p even, in all
axes; O6a and the compact pulse belong to this compatible reflection class.
S24 pp.4–6 motivates only this restricted symmetry, not arbitrary forced
walls. Background coefficients have finite trigonometric support. Assemble
exact retained convolution with those coefficients (or equivalent
dealiased products), spectral derivatives and transverse divB constraint;
never use candidate C/G/flux/maps. Initial compact pulse Fourier
coefficients require independent converged quadrature. Evolve the resulting
linear ODE by residual-controlled matrix-exponential action, tolerance
1e-12, with independent time/subspace refinement. Freeze modal cutoffs
|k_axis|<=32,48,64 (and enough padding for exact retained products);
these are reference proposals, not completed reference data.
The three cutoffs/time refinements must agree in amplitude/phase
<=.2% and field norm <=.002 of the pulse scale before comparison;
uncertainty must be <one tenth of the 2% gate. A failed reference ladder
blocks production comparison, rather than setting its uncertainty to zero.

Run to T=.45. Record plane x=.125 with the **peak-one** smooth aperture
g(y,z)=f(((y-.5)/.1)²+((z-.5)/.1)²).
There is no division by integral g or by aperture area. Observable
S(t)=integral_aperture g*(delta p+B0 dot delta B) dy dz retains its
physical surface integral. Rotate this same aperture with the entire
background/pulse/probe; do not change it with resolution or reference cutoff.
Resolve time sampling dt_diag<=.001 and refine that sampling.
Incoming window [.02,.18], reflected window [.20,.45] are fixed.
The near pulse support reaches x=0 after about .17/cmax; a probe return
travels about .17+.125, within the reflected window. These are bounding/
planning distances, not a constant-coefficient phase prediction.
Other-wall paths to this aperture are longer than .75/cmax>.45
for y/z and 1.5/cmax for x=1, so the first reflected window is localized.
The independent reference, not a guessed reflection coefficient, defines
the signal when refraction/multiple modes occur.

**E, O6d `reflection-unit-response-ncc-v1`:** for each epsilon separately,
paired perturbed/unperturbed candidate workflows supply
X_cand,1=(X_perturbed-X_background)/epsilon, including delta v/rho/p/B.
Use these responses in both field norms and
S_cand=integral g*(delta p_cand,1+B0 dot delta B_cand,1) dy dz;
S_ref uses O6c's unit response and the same analytic B0/aperture.
Reference, time/aperture-quadrature and paired-background uncertainties
are converted to that same unit-response convention. If a norm was stated
in physical pulse units, divide both its error and fixed pulse scale by
epsilon once; do not change its denominator otherwise. Retain all raw
physical states, background force/budget ledgers and actual epsilon values.
Subtraction/division is diagnostic, never a conservative-state repair.

For X=ref,cand define
```text
I_X = sqrt(integral_[.02,.18] S_X(t)^2 dt);
R_X = sqrt(integral_[.20,.45] S_X(t)^2 dt);
amplitude_ratio_X = R_X/I_X;
abs(amplitude_ratio_cand/amplitude_ratio_ref-1)<=.02.       (O6d)
```
Use enclosed ratios: including reference/quadrature/response uncertainty,
the entire candidate/reference ratio interval must lie in [.98,1.02].
The full incoming/reflected windows and2% gate are unchanged. Both incoming
and reflected reference signals must be certified nonzero, as must the
normalizing candidate signals; unresolved division is not an amplitude pass.

Phase maximizes the **signed**, normalized L2 cross-correlation over
ell in [-.02,.02], with no signal-mean subtraction:
```text
N(ell) = integral_[.22,.43] S_ref(t)*S_cand(t+ell) dt;
D_ref  = integral_[.22,.43] S_ref(t)^2 dt;
D_cand(ell) = integral_[.22,.43] S_cand(t+ell)^2 dt;
rho(ell) = N(ell)/sqrt(D_ref*D_cand(ell)).                 (O6e)
```
Both normalization integrals must be enclosed strictly positive. The
fixed interior reflected window keeps every shifted candidate sample in
[.20,.45]. Positive ell denotes a **delayed candidate**: for
S_cand(t)=S_ref(t-d), the aligned lag is ell=d, not -d.
No absolute correlation, earliest-peak tie break or post-result state
alignment is permitted.

Freeze piecewise-linear interpolation of the recorded raw S(t) on the
diagnostic times for this estimator. Integrate its products/squares exactly
piecewise, splitting at reference and shifted candidate knots; aperture
quadrature uncertainty remains separate. Partition the lag interval at
all knot-difference and shifted-window-endpoint breakpoints. Isolate all
stationary roots of 2*N'(ell)*D_cand(ell)-N(ell)*D_cand'(ell)=0 on each
polynomial piece, and include breakpoints and interval endpoints in the
global-maximum comparison. Certified interval root/value enclosures must
establish a **unique global maximum**, including isolation of its location;
not merely the largest sampled lag. Tied/flat maxima, vanishing signals,
unresolved roots/value comparisons, inadequate time interpolation or
reference uncertainty yield `ReflectionObservableUnresolved`.

Retain dt_diag<=.001 and its independent halving refinement. Bound the
combined reference, quadrature, interpolation and lag uncertainty by
<=.002*Tpacket and also the existing **strictly less than one tenth of
the phase gate**, where Tpacket=.16/cmin. The enclosing lag interval,
including uncertainty, must satisfy abs(ell)/Tpacket<=.02. Preserve the
reference .2% response/amplitude uncertainty ceiling and stricter
one-tenth-of-gate rule too; apparent sub-grid peaks are not zero-error
measurements. The epsilon/half-epsilon **unit responses** must differ
<=.2% before the linear comparison is accepted.
Otherwise this fixed packet's U4 comparison remains unresolved. A different
nonlinear reference requires separate prospective review; no changed epsilon,
rates, geometry, source switches or thresholds may manufacture a pass.

Production N=16/32/64 regular and separately frozen .1h interior-jitter
meshes, and later the same prescribed deforming families, are independent
cases. Require physical reflected amplitude/phase <=2% on finest,
field/response spatial L1 order>=1.5 and decreasing background force
imbalance with order>=1.5. Background Mach<=1e-2 through T and raw
background budget gates also apply; quantify paired-response uncertainty.
Reference cutoffs: 4 threads/16 GiB/12 h each; production/background/
half-amplitude/orientation/motion: 2 threads/8 GiB/2 h each initially.
Every cutoff, amplitude, resolution, orientation and background pair is a
separate workflow, not an aggregate allocation. Calibration can enlarge
an envelope **before** the corresponding run. No packet/reference was
executed or serialized into the shared fixture packet here.

### 11.2 Gravity startup: compatible control versus weak ambient launch

**D/E:** for the source-only hydrostatic control use y in [0,1]^3,
Phi=.5*|y-(.5,.5,.5)|², g=-grad Phi, c_T²=1,
rho=exp(-Phi), p=rho, B=A=phi=v_r=0, gamma=5/3.
Then grad p=rho*g everywhere including nonzero normal wall gravity.
Initialize gamma-law energy from that p/rho. This is an exact external-
potential hydrostatic control, not an isolated self-gravitating galaxy.
Run fixed and moving geometry for five adiabatic reference sound crossings,
T=5/sqrt(5/3), N16/32/64 and a dt ladder. Preserve the parent's stricter
G-HYDROSTATIC gates: rho/p L1<1%, Mach<1e-2, energy residual<1e-3,
momentum ledger<1e-8, errors decreasing with h/dt and no floors.
A live softened-gravity hydrostatic construction remains the parent's
separate gate; this external control does not replace it.

A uniform-p ambient collar in the live galaxy generally violates B13
because isolated g_n is nonzero. Name it a **weak startup transient**, never
a smooth equilibrium. Before evolution calculate
Tdyn=R_d/Vc(R_d), c_ambient=sqrt(gamma*p_ambient/rho_ambient),
vmax=max_real_gas |v-W| and
Tstart=min(.1*Tdyn,L/[4*(c_ambient+vmax)]) from the frozen IC;
require max_collar |g_n|*Tstart/c_ambient<=1e-3.
During [0,Tstart] measure collar normal Mach and launched relative
pressure disturbance <=1e-3 of fixed ambient scales, plus the unchanged
net/absolute excess impulse/torque gates. The collar is the outermost
two ambient initial cell layers, tagged by initial IDs; track their
successors/volume support deterministically. Uniform ambient has no
pressure-gradient repair. If this precondition or launch bound fails,
a larger domain or separately reviewed hydrostatic ambient construction
is required. All ambient gas remains a live isolated source.

### 11.3 Domain/ambient adequacy observables, bins, time and reference

**E:** preserve L=128,256,384 R_d, common baseline ambient density such
that its mass in the **largest** box is <=1e-4 M_pair, independent .1/10
density and pressure controls, common galaxy/particle IDs/physical
resolution/softening/source model. The nominal-density constraint is a
baseline; factor-10 controls report their actual mass and gravity.
No ambient subtraction, deletion or exterior-particle cutoff.
Physical and cleaning return-time estimates use actual evolving speeds;
also compare initial/live ambient gravity because it acts immediately.
All original M/P/L/H/source/representation gates remain, with signed and
absolute excess wall impulse/torque <=1e-6 fixed P/L scales and central
profile sensitivity<1%. Opposite wall impacts cannot cancel the absolute
criterion; raw uniform pressure remains in every physical ledger.

Freeze nonzero magnetic scales EB_ref=EB_initial>0,
B_ref=sqrt(2*EB_ref/R_d³) and Phi_ref=B_ref*R_d². Use Phi_ref even
when a particular aperture's initial flux is zero.
Freeze analysis before execution as follows. Define
Td=2*pi*R_d/Vc(R_d) from the accepted common isolated-galaxy IC; save the
value/hash. Compare at t_k=k*Td/20 and every source/event snapshot,
without shifting encounter clocks to align results. Full duration is
the configured encounter plus at least five reference disk periods after
claimed coalescence (parent gravity section 10.3), including the source/
feedback interval required for the final goal. Tag each galaxy core by
the same initial most-bound 10% of old stellar mass and retain these IDs;
new stars never change a core definition. Pericenter is a local minimum
of core-COM separation, fitted by a quadratic through three adjacent
diagnostic snapshots with a refined snapshot control. Coalescence is
separation<.1 R_d continuously for Td. Event interpolation uncertainty
must be <=.002 Td; absent/noisy events are reported, not reclassified.

Use common centre = all originally tagged galaxy mass COM (gas descendants
and old/new stars tracked through immutable source provenance), with all
unbounded real collisionless mass included. Radial bin edges are
r_j=R_d*2^(j/4), j=-8,...,20; add a central enclosed r<=R_d aperture.
Reject unsupported bins: r<max(3 epsilon,2 local cell radii) or fewer
than 200 effective samples are explicitly unresolved and must be refined,
not silently omitted from a claimed resolved comparison. Use three matched
IC seeds, matched stochastic event streams and deterministic channel cases
to estimate sampling/source uncertainty. These choices need agreement
with the parent IC reducer; they do not change gravity/SF source physics.

| Observable / exact reduction | Proposed domain/ambient bound vs largest accepted reference |
| --- | --- |
| Core relative trajectory at common times; pericenter/coalescence timing | Separation RMS difference<=.02 R_d and each event-time difference<=.02 Td; these additional engineering limits are stricter than parent encounter timing<10%. |
| Bound proxy and tidal gas/old-star/new-star masses, half-mass radii | Differences<=2% of fixed initial corresponding component mass (new-star scale = initial gas mass) and <=2% of reference radius. Parent bound-mass/radius<5% remains. |
| Central and resolved radial density, pressure, temperature, rotation/thickness and phase fractions | Density/pressure/temperature central profiles<1%; other resolved profiles<=2% and phase mass differences<=.01 initial gas mass, with the parent's independent equilibrium/source bounds retained. |
| Integrated newly locked stellar mass L and separately gross formed mass F/SFR | New mass difference<=.02 initial gas mass; SFR bins of width .1 Td differ in integrated formed mass<=.02 initial gas mass per bin; additionally relative differences<=5% wherever reference formed mass>=.01 initial gas mass. These are new sensitivity limits, not acceptance of a star-formation model. |
| Nonzero magnetic energy, signed/unsigned aperture flux and helicity diagnostic | Enclosed EB and unsigned flux at common apertures differ<=2% of fixed initial EB/flux scale; signed flux absolute difference<=.02 fixed initial unsigned flux. Full-box H=integral A dot B, normalized by 2 R_d EB_initial, differs<=.02. With Bn=0 continuum H is gauge invariant; discrete gauge contamination/mean/trace must first pass. No claim of resolved field-line reconnection from helicity alone. |

For the bound proxy, use the same declared diagnostic gravitational
potential from the accepted backend, zero at infinity. Collisionless
specific proxy is .5|v-vCOM|²+Phi; gas proxy adds u+p/rho+B²/rho.
Negative gas proxy is a **Bernoulli-style tag**, not a conserved binding
energy in time-dependent MHD. Save raw values; tidal tag means r>10 R_d
with initial-galaxy provenance. Neither tag removes any source. If the
parent science analysis requires another bound/topology definition, freeze
and independently review it before execution; no post-result changes.
Flux apertures are common spheres at these fixed radii, separately
signed and unsigned, evaluated with the same independently converged
surface quadrature; helicity uses the same chart gauge and actual volumes.

Use L384 as the domain reference only after its own independent spatial
resolution ladder, half dt, tighter gravity and source/auxiliary controls
meet the parent and new gates. Compare both L128->384 and L256->384 and
each ambient control, with identical physical resolution in common
regions. Estimated reference/sampling/reducer uncertainty must be <=one
fifth of each listed bound; if not, that observable remains unresolved.
Magnetic/topology and stochastic-source uncertainty are explicit
prerequisites, not zero-valued error bars. Final reference validity and
parent science reducer agreement must be reviewed before costly execution.
A failed observable requires domain/profile/resolution revision; no
post-result relaxation and no inference of general-outflow acceptance.

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
W1–W5's manual reduced-pressure algebra is supported by the unchanged
59bc5c8 review; its implementation, floating enclosures and numerical gates
remain unexecuted. **Still open:** independent review of this O2a/O6d–e/O7a revision,
consistency/trace/spectrum/physical evidence for U1–U4, literal serialization
and review of the defined O6 reflection reference, bounded moving Cdot/frame
integration, and all implementation and REANA evidence. M2d remains
unaccepted. There is no full accepted bounded
A/cleaning/projection treatment or claim of AREPO equivalence in this audit.

**Scoped provenance reconciliation:** the input bed56a4 design and the
review's exact subject identities remain pinned separately from this output.
The old 90075-byte ISM working-copy hash is an **unretained historical
observation**, not reproducible verified input. The retained 6d8f634 record
remains historical too; current committed ISM context is a7ef086, inspected
only for gamma=5/3 mixture pressure/phase admissibility, source ordering,
dimensionally separate guard scales and unchanged parent domain/source gates.
Its entry guard is specific energy scaled by u_ref, cloud exhaustion is
mass scaled by M_ref; neither is a wall-work/cleaning-energy source. No
cooling/source calibration or coupled compatibility approval follows.

The 3b9719c [curl comparator](CURL_3D_MEAN_SPEC.md) and
[event semantics](MOVING_MHD_STAGE_SPEC.md) are current context, not new
bounded algorithms. C_FV is **periodic-only and unadopted**; shared-face
periodic mean cancellation supplies no wall trace/operator or bounded mean
proof. E1–E5 separates event coverage from exchange error but does not
certify every production event with the <=512-cell sampled controller.
Bounded moving Cdot/GCL, state-dependent motion, isolated gravity and
active sources remain required for the full nonzero-B deforming merger.

After M1 acceptance and the design review, the smallest implementation slice
is a bounded, serial, fixed-geometry non-evolving operator/wall-flux module;
it does not require waiting for a galaxy evolution. Reviewable Rust layout
(names proposed, **no files/Cargo changes created here**):

```text
moving-mesh/src/boundary3.rs       BoxChart, WallPatchId, PatchSet, traces
moving-mesh/src/constrained3.rs    polynomial constraints, QR maps, reports
mhd-vector-pot/src/bounded_ops.rs  C/Ct, G/Gt, D_clean, weighted products
mhd-core/src/wall_flux.rs          W1-W5 physical half-Riemann, WallExchange
mhd-vector-pot/src/bounded_step.rs moving-stage raw increment, trial/commit
mhd-io/src/boundary_ledger.rs      patch impulses/torques/work/provenance
```

Proposed API records: `WallProfileId`, `BoxChart{origin_at_t0,t0,W,chart_min,widths}`,
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
   MHD primitives and conditioned-fit utilities after generalization; the
   W1–W5 pressure oracle is new and has its own reviewed wave curve.
   Generalize periodic image/mean-field/constant-nullspace assumptions
   before using existing machinery at walls. Run
   each registered case on REANA under its own workflow.
3. Resolve the consistency/spectrum review with B-MMS, B-GAUGE and B-CLEAN;
   stop on U1/U3 failure. Serialize and independently freeze O6's U4 coupled
   reference before
   any claim of a validated magnetized wall.
4. Add moving endpoint geometry/GCL/target and B-FIELD/B-BOOST with complete
   wall ledgers/restarts; only then couple isolated gravity and ISM source
   transactions and proceed to domain-controlled isolated galaxies.

No code, shared fixture packet/arrays, executable probes, tests/evolutions
or REANA control were produced or run for this document. Document/source hashing and
read-only equation inspection are the only executed checks.
