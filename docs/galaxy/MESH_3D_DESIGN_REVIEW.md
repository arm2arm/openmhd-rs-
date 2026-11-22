# Independent M2 moving-mesh design review

2026-11-22. **Disposition: revise the moving-MHD stage contract before its
implementation; allow the separately gated geometry/operator slices after
scoped M1 acceptance.** This is a source and mathematical design review of
[MESH_3D_SPEC.md](MESH_3D_SPEC.md), not an executed 3D result, M1 final-output
review or scientific acceptance. The moving, state-dependent, full-3D merger
goal remains the required endpoint. Fixed/rigid and prescribed-motion cases
are intermediate controls.

Reviewed checkout: `a06aebc295ad64276fd45ef2464c06991bb83543`. The reviewed mesh
document is 65,853 bytes, SHA256
`c419d215a6a774455dcd62f0e2cc909969875deece5a49d3d9b71cdf76183f77`.
Line locators below refer to those exact bytes, not a future author revision.
The shared contract is 12,464 bytes, SHA256
`e91984c4ec05409f5cf29861ee276f96ee0a496d0885ef1c61905d9a1434728c`.
The complete reviewed-file and primary-source inventory is
[mesh_3d_review_sources.json](mesh_3d_review_sources.json).

The inspected seven Rust files match their frozen M1 bytes at
`2bdcea0d28340e7429e10053a641f92d51fcc696`. No scientific source, benchmark,
M1 evidence, workflow or service was changed. No build, numerical test,
geometry probe, evolution or production reduction was run. Local operations
were reading, PDF-page inspection, hashing and document checks. Historical M1
gates and the conditional source review are evidence for the named periodic
2.5D fixed/rigid profile; fresh physical acceptance remains the coordinator's
separate gate.

## Source boundary and review method

The full primary PDFs were available locally. Equation locators use printed
PDF pages and the hashed PDF's numbering. P26 is
[Springel, Mayer & Pakmor, arXiv:2609.35989v1](https://arxiv.org/pdf/2609.35989v1),
37 pages, 14,060,781 bytes, SHA256
`6e12da18a86c57536fc26f2baf86d15d6db2e378e040a59bc9b82870b2dfcb84`.
P09 is [Springel, arXiv:0901.4107v3](https://arxiv.org/pdf/0901.4107v3),
67 pages, 9,354,438 bytes, SHA256
`dfe38502394b15a0b05bbb1f610b0e1533198594e33681e22a507162cc2d10f4`.
Its first page identifies v3, 31 October 2009, with a 26 November 2024
recompilation date. It is not the v2 PDF used for some gravity citations.
The source inventory's unversioned P09 retrieval URL must not obscure this
identity. Official version landing pages were also checked.

P26 §§4.1–4.5, pp.8–13, Eqs.51–76, and §5.1, pp.14–16, Eqs.80–92 were
read against the proposed operators/stages; pages 9, 15 and 16 were visually
inspected. P09 §3.3, p.17, Eqs.32–40 was read and its equation page visually
inspected. The graph sweep, screened increment projection, uniform auxiliary
grid and full-vector target completion are engineering proposals. Neither
publication proves them. Equations below labelled R are derivations in this
review, with their assumptions stated. No external code was copied, imported
or relicensed. The candidate crate's full transitive license/feature closure
was not independently repeated here; its documented adoption gate stays open.

In the derivations let `D` denote the oriented cell-face incidence matrix
(left +1, right -1), `C` the actually implemented discrete curl, and `V` the
diagonal matrix repeating each cell volume for its three field components.
This avoids the mesh document's overloaded `B` for both incidence and field.
All numerical bounds and experiments below are **prospective**, not measured.

## Numbered findings

### 1. Blocking for M1 reduction: the proposed target changes fixed/rigid arithmetic

**Locator:** mesh §7.1, lines 668–677; frozen
`general.rs:1217–1242`, `853–868`; `projected_rate.rs:471–507`.

The frozen target adds `Bn*T`, where
`T=(w_rigid_x,w_rigid_y,Vref_z)`. Its gauge reference `Vref` is the initial
mass-weighted bulk gas velocity, which need not equal the rigid generator
velocity. The new target adds `Bn*Vref` in all three dimensions. On a
z-invariant fixed/rigid test, using the same face results and field, their
cell target-rate difference is exactly

```text
R1: t_new_i - t_M1_i = -(Vref-T) * d_face_i,
    d_face_i = sum_f sign_if*A_f*Bn_f / V_i.
```

Here `sign_if` is +1 for the outward left incidence. This is the divergence
of the returned Riemann normal field, not necessarily any output LS
divergence. It is generally nonzero. The screened rate difference is
`L[-(Vref-T)*d_face]`, with `L=(C^T V C+kappa*diag(C^T V C))^-1 C^T V`.
Thus the draft does **not** generically reduce to frozen M1. Coincidence
requires `Vref_xy=w_rigid_xy`, zero relevant face divergence, or annihilation
of this difference by L. Continuum `div(B)=0` is insufficient evidence.

**Resolution:** specify a named target-frame policy and acknowledge the
changed semidiscrete method. Retain an explicit M1-compatible reduction mode
using T for the comparison; separately review the full-vector Vref mode.
The full-3D profile may adopt Vref after its own evidence, but cannot cite M1
as arithmetic equivalence. Record both target and post-screening differences.

**REANA:** independent fixed and rigid z-invariant cases with nonuniform B,
nonzero mean B and `Vref_xy != w_rigid_xy`; compare frozen/new-compatible/new-
full-vector rates and one-step states on identical curl/fit/face-stage arrays.
For this controlled target-only comparison the compatible mode should agree to
the existing solve tolerance (report absolute and normalized differences;
prospective normalized ceiling `1e-9`). Check R1 directly to `1e-12` scaled
algebra tolerance. A genuine 3D extruded mesh can produce different LS weights;
without an operator-equivalence certificate its comparison with 2D is a
convergence/physical-error comparison, not this arithmetic identity. Then run
full-vector 3D joint boosts under B01. This
comparison supplements, and cannot rewrite, the frozen M1 evidence.

### 2. Blocking for stage implementation: name the four samples and projection inputs

**Locator:** mesh §6.2, lines 587–599; §7.1, lines 649–658; §7.2 table,
lines 685–690. Frozen `general.rs:1497–1557` projects each stage's rate and
then averages those projected rates.

"Both endpoints (four samples)" leaves the corrector's final gas state
ambiguous. Taking Q1/V1 makes the stated explicit corrector an implicit
nonlinear equation. Likewise, projecting an increment already made from
projected rates applies the screened correction twice. With kappa=1,
screening does not make the first corrected field exactly equal to target,
so the second correction generally is not zero.

**Resolution:** write these assignments explicitly for each real owner j:

```text
R2: U0_j = Q0_j/V0_j; Ustar_j = Qstar_j/V1_j
    Ubar_predictor_f = (U0_L+U0_R)/2
    Ubar_corrector_f = (U0_L+U0_R+Ustar_L+Ustar_R)/4.
```

`Qstar` includes the predictor's single GCL correction. Its `Bstar` is
recovered after the predictor's single increment projection. Use B0/Bstar
in the analogous corrector Bbar, never final B1. Both endpoints' owner
states exist by ID even when the face is absent. Boundary faces need their
explicit provider, not an invented second real owner. Write raw A-rate
inputs `r0,rstar` and integrated induction exchanges `E0,Estar` separately:
predictor `a_trial=a0+dt*r0`; corrector
`a_trial=a0+dt*(r0+rstar)/2`, with each increment projected **once**.
The corrector starts from a0/Q0 and its own integrated exchange. It does not
add another final correction to the already updated predictor.

There is a useful conditional fixed-metric reduction. Define
`P(r,t)=r+L(t-C*r)` with the same C,V,kappa and target-frame policy in both
methods. Then linearity gives

```text
R3: a_predictor = a0 + dt*P(r0,t0)
    a1 = a0 + dt/2 * [P(r0,t0)+P(rstar,tstar)].
```

The draft's endpoint solve yields R3 exactly in real arithmetic if its
trial increments are raw and its target is
`B0+dt*t0` / `B0+dt*(t0+tstar)/2`. This proves a narrow reduction, not its
moving-metric accuracy or equality after changing the target in finding 1.

**REANA:** compare rate-versus-increment versions on identical fixed metric
and frozen stage arrays; include kappa=1 and deliberately nonzero screened
mismatch. Require normalized `<=1e-9` state agreement and `<=1e-12` one-face
sample/formula checks. Include zero dt and no accidental predictor double
application. Dependent C01/F01 executions wait for these definitions.

### 3. Blocking for a second-order moving claim: averaged centroid speed is insufficient

**Locator:** mesh §6.1, lines 549–554; §7.2 endpoint/reevaluation/corrector
rows. P26 p.15 Eq.80, p.16 Eqs.87–91. Frozen `endpoint:719–725` computes the
centroid correction; the Heun path at `general.rs:1503` instead takes the
rigid branch and never exercises a deforming correction.

The geometry identity
`(wtilde+what)/2=delta_c/dt` is correct. It fixes the *mean sampling speed*,
but does not by itself make the predicted A an endpoint state to O(dt²).
For smooth deformation, `delta_c/dt-wtilde` can be O(1) as dt tends to zero
at fixed mesh. Predicting only with wtilde omits an O(dt) spatial shift.
Reevaluating derivatives, limiter donors, auxiliary jets and projection on
that shifted field needs an additional consistency argument.

A reduced Taylor example exposes the logical gap, without alleging that it
models every term of the complete scheme. For `dy/dt=c*f(y)` with constant
true speed c, use predictor `y*=y0+dt*p*f(y0)` and corrector speeds p and
`q=2*c-p`. Its second-order coefficient is
`p*(2*c-p)*f'(y0)*f(y0)/2`, while the exact coefficient is
`c*c*f'(y0)*f(y0)/2`. The difference is
`-(c-p)^2*f'(y0)*f(y0)/2`. Correct mean speed alone therefore does not prove
second order. In a spatial transport problem the analogous omitted shift
also enters endpoint derivative fits. Full projected induction may alter
this error; no cancellation proof is supplied.

**Resolution:** give separate explicit predictor and corrector centroid
transport rules, their donor geometry and the A location represented at
each stage. Derive the order for the complete engineering sequence. Options
include a consistent predictor relocation to c1 or centroid-velocity stage
estimates derived from geometric moments; each is a newly reviewed choice.
P26 Eq.89 can motivate an experiment, but does not certify this modified
reevaluated/screened scheme. Retain the moving path as conditional until
this is resolved; do not remove the M1 guard to evade it.

**REANA:** manufactured smooth three-dimensional A with nonconstant spatial
gradients on a nonrigid prescribed mesh, static physical field and separately
advected field. Freeze spatial mesh and halve dt at least four times, then
refine space separately; include a case where centroid/generator speed
difference remains finite under dt refinement. Measure point-sample A in a
fixed gauge, recovered B, endpoint predictor defect and projection changes.
Prospective temporal order `>=1.8` above the spatial/solve floor is required
for a second-order claim; otherwise register the measured lower-order method
and obtain a separate owner decision before coupling.

### 4. Blocking for moving acceptance: endpoint topology sampling needs an operational error policy

**Locator:** mesh §6.2, lines 576–586 and 600–613; M02 table line 835,
lines 855–858. P09 Eq.34 is an instantaneous identity, not a time-integrated
topology theorem.

The union of old/new faces can omit a face born and destroyed within dt.
Its physical gas/induction exchange need not be zero. A graph correction
can still exactly close volumes by routing the residual through other
edges, so GCL residual and even final uniform-state success cannot detect
the missing exchange. A displacement cap based only on cell size does not
bound distance to a co-spherical event; events can be arbitrarily close.
The draft correctly warns about this, but "limit motion and substep" does
not yet define an accept/reject algorithm or an error estimator.

**Resolution:** before accepting such steps, choose either certified event
bracketing for the linear trajectories, or a declared adaptive geometry/
flux substepping and comparison policy with a frozen tolerance. Sampling
midpoints alone is not a proof that all short-lived faces were found. If
using error-controlled substepping, state its limits and reject unresolved
events rather than claiming an event certificate. Define physical exchange
comparison, minimum substep, failure behavior and immutable retry handling.
Freeze the acknowledged missing five-seed arrays, including a transient
face absent at both endpoints, before execution.

**REANA:** event fixture plus near-event perturbations and nonconstant
advected states, compared against increasingly fine independently rebuilt
substeps. Record integrated exchanges by spacetime event, gas and B errors,
not only endpoint face keys. Retain M02's `1e-12` GCL / `1e-10` uniform-state
gates and smooth correction orders, but add a predeclared `<=1e-3` normalized
coarse-versus-resolved physical exchange target at the finest registered
production step and demonstrate decreasing error on halving. This is an
engineering target requiring fixture calibration before the run, not a
published bound or permission to skip events below a face-area floor.

### 5. Blocking for coupled moving MHD: separate projection error, mean flux and energy transfer

**Locator:** mesh §5.2, lines 489–492; §7.1, lines 655–677; §7.2 pressure
recovery rows; §9 energy/mean gates. P26 §4.1 p.8 and §4.7 pp.13–14 discuss
energy recovery; frozen `general.rs:462–475,1575–1585` follows Q plus curl.

The endpoint equation is dimensionally consistent: A has units B*length,
C has 1/length, `C^T V C` and D have length, kappa is dimensionless, and
both sides have B*length². It includes finite C/V changes through the
actual endpoint target and `C1*a_trial`; it is not simply missing Cdot.
However, solving its screened normal equations tightly does not establish
small physical induction mismatch, exact volume-mean B or correct energy
partition. If `e=B_target-B_mean-C1*a_trial`, the final field mismatch is
`e-C1*z`; the normal solve imposes
`C1^T V1*(e-C1*z)=kappa*D1*z`, not zero physical mismatch.

Even though a shared periodic target conserves `sum V*B_target`, the LS
curl need not satisfy `sum V*C*a=0`. Screening cannot enforce this missing
left-nullspace identity. A fixed B_mean parameter is not proof of a fixed
discrete volume mean. The existing diagnostic and `1e-9` prospective mean
gate are appropriate, but the contract needs an explicit response to failure.

At fixed endpoint Q/V, let Btrial and Bafter be the fields before/after the
projection. The exact magnetic/thermal bookkeeping is

```text
R4: delta_EB_projection_i = V1_i*(|Bafter_i|²-|Btrial_i|²)/2
    delta_Uthermal_projection_i = -delta_EB_projection_i.
```

Total gas Q energy remains unchanged. This is numerical energy conversion,
not an external heat source and not necessarily positive. Pressure can fail.
Similarly separate the magnetic-energy change from moving C/V at unchanged
a, raw A evolution and projection. A global `sum Q_E` budget can pass while
spurious magnetic-to-thermal transfer or mean flux error is large.

**Resolution:** publish cellwise/summed/sum-absolute R4, physical target
residual norms and mean drift in addition to the true normal-equation
residual. Reject inadmissible closures without resetting E, p or B. Keep
the target and recovered field distinct. If the mean gate fails, derive a
constraint-compatible curl/projection or explicitly revise the method and
review it; do not silently subtract the measured mean from B or change
B_mean, since either changes magnetic energy and the flux/force closure.
No exact discrete magnetic-energy identity is established by this review.

**REANA:** zero-dt fixed geometry (zero correction to scaled `1e-12`),
finite smooth geometry changes with analytic A/B, pure prescribed sampling,
and fixed/rigid limits. Use normal residual `<=1e-9` as a solver gate only;
retain physical B order `>=1.8`, mean drift `<=1e-9` and budget `<=1e-10`
from F/C gates. Add a weak-field and magnetic-pressure-dominated positive
closure pair, and a stationary/advected smooth-field test in which the
*excess* magnetic/thermal conversion versus a refined reference converges
and is `<=1e-3` of initial magnetic energy at the finest registered mesh.
Register the reference uncertainty before this added gate is executed.

### 6. Blocking for a reproducible operator: complete the raw 3D/gauge/origin formulas

**Locator:** mesh §§5.3,7.2, lines 503–513 and 685–695; reuse rows 798–801.
P26 Eqs.69–72,76,80–92 are not the selected M1 engineering rate. Frozen
`operators.rs:524–608` and `auxiliary.rs:199–207,285–317` contain material
choices absent from the 3D stage sketch.

The draft identifies Jacobian order and raw/limited separation correctly,
but does not select the actual full raw-A formula: P26 returned-state
cross product versus M1 numerical-flux EMF, face-area versus centroid-
triangle weighting, or any quadratic transport remainder. The selected M1
Heun quadratic profile uses surface-area EMF averaging and has
`MagneticFit.curvature=None`: its transport uses the limited quadratic-derived
gradient but not the donor/receiver Hessian branch at lines 582–599. That
branch belongs to other M0 profiles (`general.rs:96–116,340–365`;
`operators.rs:125–127,191–266`). Do not import it as frozen M1 behavior.
Moreover, M1 fits primitive/B gradients separately with the linear neighbour
stencil (`general.rs:1117–1125`), whereas mesh §5.2 proposes same-fit Hessian
derivatives for B. Selecting those for fluid reconstruction changes the
face states even on a fixed z-invariant mesh. The gauge and auxiliary-origin
stage rules are requested by the draft, not yet stated.

**Resolution:** supply a named raw-rate expression with full xyz contractions,
including the distortion `-J_u^T*a`, `grad(phi)`, mean source
`(u-Vref) cross B_mean`, the chosen face EMF completion, transport policy and
primitive/B gradient policy. New Hessian transport or B reconstruction may
be reviewed options, but are not inherited arithmetic of the M1 candidate.
Specify the engineering omission of `-J_u^T*gauge_offset` and why the
offset is kept separate. Pin constant Vref for the whole run, including
after source events. State `offset1=offset0+dt*(Vref cross B_mean)`.
For the existing reevaluated-origin family, a concrete unambiguous extension
is `origin*=origin0+dt*mean_u0`, build endpoint deposits there, sample that
fresh field with stage_time=0, then
`origin1=origin0+dt*(mean_u0+mean_ustar)/2` with checked wrapping. Do not both
advance the stored origin and sample it with another dt translation. A frozen
old auxiliary field sampled at dt is a different stage policy. Define root-
fallback switches and checkpoint/retry behavior in both cases.

**REANA:** tricubic analytic derivatives/C1 seams (O03), constant gauge
offsets, xyz coordinate permutations, varying auxiliary roots, restart and
rejected-step replay, followed by F01/B01. Constant offsets must not alter
B to scaled `1e-12`; raw-rate/reduction comparisons use the explicit chosen
formula and normal solver tolerance. Gauge-dependent A is compared only
after its declared transform; independently compare B and Q. Pure-gradient
gauge perturbations require a refinement study, because an arbitrary
discrete curl-gradient null identity has not been established.

### 7. Nonblocking mathematical support: shared GCL sign and constant-state closure are correct

**Locator:** mesh §3.1 moment identities, §6.1 face formula and §6.2.
P09 p.17 Eqs.32–34. This finding supports a restricted property and does not
remove findings 2–5.

Differentiating the moving bisector constraint at a point f gives the
normal component of the draft's w_f, with `d=r_R-r_L`; the sign in line 539
agrees with P09. The tangential vector is a frame choice, not a face-
centroid trajectory. With outward-left incidence the volume rate is
`D*(A*w_n)`, and positive outward fluid exchange is applied as `-D*E`.
For constant conserved density U, closed stage polyhedra imply cancellation
of all physical constant-state fluxes by `sum A*n=0`. Therefore

```text
R5: Q_H = U*(V0+D*S_H)
    E = E_H-U*delta_S
    Q1 = Q_H+D*(U*delta_S)
       = U*V1, if D*delta_S=V1-V0-D*S_H.
```

Every interior correction uses the same exchange with opposite signs;
global mass, momentum and total energy change only through boundaries/
sources up to summation error. For uniform B the analogous induction
target closes if the returned flux and Bbar use that same constant field.
This proves no nonconstant-state accuracy, positivity, entropy or exact
angular-momentum property. Geometric volumes must remain the actual rebuilt
volumes. The stated tensor and centroid moment identities are correct:
the last follows from `div(y_a*y)=4*y_a` and `int_cell y dV=0`;
`y·n` is constant per planar face, so its centroid quadrature is exact.

**Resolution/REANA:** retain these identities as independent assertions in
G01/G02/M02/C01, including an MHD uniform field and fixed wall boundary
ledger. Use stated geometry `1e-10`/`1e-9` tolerances and GCL `1e-12`,
constant-state/budget `1e-10`. Recompute raw volume/moment closure independently
of the correction solve; a corrected second RK volume is not a substitute.

### 8. Nonblocking conditional support: graph solve compatibility, conditioning and self-images

**Locator:** mesh §2.2, §3 and §6.2, especially lines 580–586.

With dimensionless positive W, `D W D^T` has one constant null mode per
connected component. Its range consists of vectors whose sum vanishes on
each component. Pinning one multiplier is sufficient only after this
compatibility check. lambda and delta_S have units volume; using area
normalized by a fixed area scale is dimensionally valid. For a periodic
self-image face the two incidences on the same real cell cancel: its graph
column is zero, so it cannot repair a nonzero volume defect. Parallel edges
between different images must remain distinct face exchanges.

**Resolution:** define components using positive-weight, non-self edges;
check component sums with a scale-aware roundoff tolerance; evaluate the
full residual including pinned rows. Never subtract a physical volume
defect's mean. A one-cell periodic mesh must have unchanged total volume
and zero compatible residual. Retain both geometric self-face incidences,
but avoid interpreting an in-place floating subtraction/addition to the
same gas owner as a bitwise-zero transaction. State a deterministic net-zero
owner update while retaining the two physical incidences for metrics.
Near vanishing W, the graph inverse can amplify a nominal O(dt³) R; temporal
orders require smooth geometry, stable connectivity/rank and bounded graph
conditioning at fixed spatial resolution. Record both raw R and delta_S,
conditioning/iteration data, not only solver residuals.

**REANA:** one-cell, tiny periodic, parallel-image, disconnected synthetic
graph and incompatible-component fixtures; require scaled residual `<=1e-12`
or a typed rejection. A self-loop cannot hide incompatibility. Sweep nearly
vanishing edge weights and mesh resolutions; keep M02 correction-size/order
gates and report their h-dependent constants. No result has been executed.

### 9. Nonblocking conditional support: fit weights, adjoint and curl nullspaces

**Locator:** mesh §§5.1–5.2, §7.1 lines 660–666. P26 pp.8–9,
Eqs.51–66. Frozen `quadratic.rs:59–140`,
`projected_rate.rs:371–405`.

The free-intercept area-weighted linear fit and ten-term symmetric quadratic
basis match the cited choices. Row scaling by sqrt(1/r) gives an objective
weight 1/r; it is not row scaling by 1/r. CPQR/SVD, thresholds and ring
expansion are engineering improvements. Polynomial rank of an observation
matrix is distinct from rank of the assembled periodic curl. Symmetric
Hessians cancel the same-fit divergence algebraically, not the independent
LS/face divergences; retaining all three diagnostics is correct.

For baseline sample b_i and sample map j(s), each derivative is
`sum_s w_is*(a_j(s)-a_b(i))`. Its transpose adds each row contribution to
j(s) and subtracts the complete contribution at b(i). Repeated periodic
images share one stored unknown. Aggregate their coefficients, including
baseline terms, **before** squaring to form diag(C^T V C). Squaring samples
separately loses cross terms; the frozen implementation explicitly coalesces
indices for this reason. A synthetic local polynomial sample per image is
valid for fit diagnostics but differs from a globally periodic field's
unknown layout.

**Resolution:** make the dot-product identity
`dot(C*a,V*b)=dot(a,C^T V*b)` explicit with no extra hidden V multiplication.
Specify all zero-column modes: with kappa>0 and every active diagonal
positive the screened matrix is SPD; a zero diagonal implies an inactive
column/zero RHS there and needs an explicit fixed-zero correction policy or
typed unsupported case. Constants, discrete gradient-like and other stencil
null modes are not ruled out by local QR rank. Kappa=0 requires a separate
compatible singular-solve/gauge policy; keep it outside the first profile.

**REANA:** O01/O03 dot-product and independent dense small-matrix comparisons,
constants, repeated image/baseline collisions and deliberately zero columns;
scaled adjoint/constant error `<=1e-12`. Verify D against the assembled
operator at `<=1e-12`, then rank/SVD diagnostics on small accepted meshes.
Do not reject all geometry merely because physical curl has gauge null modes.

### 10. Nonblocking mathematical support: ALE and joint-boost signs are consistent

**Locator:** mesh §7.1 lines 619–626 and 668–675; frozen
`mhd-core/src/lib.rs:511–521,615–635`; P09 §3.3 Eqs.35–40.

The kernel solves using v-w_f, preserves supplied gas pressure when replacing
normal B, and transforms its full flux back. In a constant state its lab ALE
induction flux is `B*(v·n-w_f·n)-v*Bn`. Subtracting `U*w_n` again would double
count mesh transport. The draft correctly prohibits this. The GCL term is
only `-Ubar*delta_S`, a correction to the integrated sweep, not another
`-dt*A*U*w_n`.

Under joint boost b of gas/mesh, `F_induction' = F_induction-b*Bn`.
For `Vref'=Vref+b`, the proposed completed flux is invariant. This is a
narrow algebraic covariance argument assuming identical transformed
geometry, reconstruction, returned face states and decisions; it is not
an executed joint-boost result. It does not remove the fixed-limit
discrepancy in finding 1. Face pressure changes, limiter roots, deposition
origin, timestep caps and roundoff still require independent comparison.

**Resolution/REANA:** retain one full-vector kernel and one shared exchange;
compare oblique normals, tangential face velocities, n reversal/owner swap,
coordinate permutations and both B01 boosts. Require per-face conservative
sign/covariance errors `<=1e-12` scaled on well-conditioned manufactured
states, and the registered coupled `1e-8`/mean `1e-9` boost gates. Transform
energy by `E'=E+b·p+M*|b|²/2`; do not compare unchanged lab energy.

### 11. Nonblocking for standalone slices, blocking for the requested merger: remaining motion/boundary dependencies

**Locator:** mesh §3.2 lines 225–242, §6.1 lines 519–525, §10;
shared integration contract "Mesh motion and physical boundary gate".

Freezing wtilde through a trial correctly gives a well-defined geometric
path. Recomputing endpoint primitive velocity for flux/auxiliary physics is
compatible only if it does not silently replace this path's generator
velocity. Choosing wtilde from the old gas velocity is not an established
second-order, state-dependent Lagrangian motion policy. Regularization,
centroid offsets, topology events and reversibility/boost behavior need
their own configured policy and study. The source explicitly leaves this
unvalidated; it must remain a dependency, not disappear after a green
prescribed-motion campaign.

The periodic-only first auxiliary field does not provide bounded MHD.
Clipping a cuboid supplies neither gas outflow nor compatible magnetic,
gauge and cleaning boundary conditions. Mesh §3.2 and the shared M2d gate
state this correctly. Isolated gravity plus periodic gas is not the final
merger convention. A B=0 hydro control can proceed through its own boundary
review but cannot substitute for the requested nonzero-field merger.

**Resolution/REANA:** register the state-dependent trajectory/regularization
law before implementing that mode, including how it uses kicked gas states,
endpoint velocity predictions and rejected trials. Add a nonuniform smooth
flow with topology changes, dt/mass refinement, boosts and restart, with
physical/geometry gates at least as strict as its prescribed controls.
Derive and independently review bounded A/B/phi/gauge/EMF conditions and
their energy/boundary ledgers under M2d before any isolated MHD galaxy.
Use domain-size/ambient-density comparisons from the gravity contract only
after that boundary path passes. No source values or accepted boundary
equations are invented here.

### 12. Nonblocking shared-interface refinement: pin the gas geometry epoch

**Locator:** shared integration contract "Identity and immutable views";
original gravity sketch at `GRAVITY_PARTICLES_SPEC.md:176` before this review.

The source hash, physical time and state revision do not visibly encode the
applicable immutable gas geometry in that API sketch. The coordinator
explicitly requires it. The narrowly authorized refinement adds
`gas_geometry_epoch: Option<GeometryEpoch>`: Some for a catalog containing
gas and None only for collisionless-only evaluation. A gas source event
still invalidates state/hash without a geometry change. The gravity source
inventory records this interface correction. No force law, integrator,
birth policy or shared file was changed.

**REANA:** the prospective X01/G1 interface fixtures must reject a stale
geometry epoch even if force storage order, time or source values match;
likewise reject a stale source revision on unchanged geometry. This is a
future typed-interface test, not an executed check in this review.

## Implementation disposition and closure requirements

1. After M1's separate scoped acceptance, proceed with independent 3D
   ID/domain/polyhedron validation and static fit/curl/adjoint modules under
   G00–G04/O01–O03. Their conditional mathematical basis is sufficiently
   concrete for small reviewed slices. Dependency adoption still requires
   the documented license/feature closure and normal/image checks.
2. Return findings 1–6 to the mesh author for an explicit named stage/target
   revision and mathematical response. Register event fixtures and transport/
   energy/mean diagnostics. Prescribed motion and the shared GCL experiment
   remain the intended next moving slices; no approval of coupled moving
   induction follows from this document.
3. Re-review the revised equations and exact file hashes before implementing
   the disputed coupled sequence. Each numerical uncertainty needs its own
   frozen REANA fixture, independent case workflow, CPU/thread/memory/timeout
   declaration and reducer. Use the spec's per-case envelopes initially;
   small algebra/interface additions can use 1 thread, 2 GiB, 5 min each.
   Finite-geometry transport/energy cases use F01/C01 envelopes. No aggregate
   cap applies. No workflows were submitted or controlled here.
4. Keep required failures as dependency stops. New numerical code and every
   executable test/evolution run only on REANA. A tight linear solve, green
   M1 profile, exact GCL identity or constant-state result cannot certify
   arbitrary moving 3D equivalence, physical boundaries or galaxy stability.
5. Preserve the final full-3D deforming, state-dependent moving-MHD goal with
   isolated gravity and active sources. The unresolved trajectory policy and
   M2d magnetic boundary are necessary next contracts, not reasons to relabel
   a fixed/rigid calculation as the completed merger.

Review limits: no runtime geometry/backend verification; no resolved dependency
build/license closure; no proof of stability, entropy, arbitrary discrete gauge
invariance, exact magnetic energy or general second order through topology
events; no assessment of fresh M1 outputs. Numerical tolerances above are
review proposals that must be registered before execution. Only the explicit
symbolic properties with stated assumptions are supported now.

Document verification performed: 23 recorded input identities matched their
bytes/hashes (the two narrowly refined gravity files checked against their
pre-refinement committed inputs); both source JSON documents parsed; local
Markdown targets, fences and whitespace passed. `git diff --check` passed.
These are document/source integrity checks, not numerical validation.
