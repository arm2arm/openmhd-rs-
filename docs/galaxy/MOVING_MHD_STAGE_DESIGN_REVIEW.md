# Independent review of the revised moving-MHD stages

2026-11-22. **Disposition: the old moving order defect is correctly identified
and removed for the stated smooth prescribed-path finite-dimensional ODE;
moving-MHD physical acceptance remains blocked by its numerical prerequisites.**
No further algebraic order blocker was identified for that limited ODE under
the assumptions below. This does not establish spatial consistency, stability,
event coverage, bounded MHD or the final state-dependent galaxy calculation.
Before dependent implementation, clarify the event packet's coverage verdict
and comparison/reference semantics in finding 6 and freeze the literal small
fixtures. Static geometry/operator slices remain separately gated after M1.

The subject is commit `66370fa9b9dfdb01e5772c2b9801463e27aa338a`:

| Reviewed file | Bytes | SHA256 |
| --- | ---: | --- |
| `MOVING_MHD_STAGE_SPEC.md` | 52213 | `021598e60991c3d04e15187d0abf3e992785bee7094f409b7947af17f5dbb4f1` |
| `moving_mhd_stage_sources.json` | 29454 | `a274d5e6dc8e0a8b9a24093d11c58e256869f959d3f676189c85b9bffd86ca74` |
| `MESH_3D_SPEC.md` | 73092 | `f7019788304ab2a9270f0b4fbe29f134d921b420d1b9683c68f2fc8d80b91190` |
| `mesh_3d_sources.json` | 29461 | `0feba37895d363673df745ac142073174a528f5a59edbda98619a1a66271b1d3` |

Line locators refer to those committed bytes. The companion
[review inventory](moving_mhd_stage_review_sources.json) pins the other
contracts, historical reviews and inspected code. In particular, boundary
context is the **committed** 50,194-byte `BOUNDARY_MHD_SPEC.md`, SHA256
`c08be57d86c4a3a8de9b8dd36a74cfc695103661f4169d64e30c021bfef4b7a0`,
and the committed independent bounded review, SHA256
`94a6ad765b33ee9347a48f2f906a33d91ed72fc5818975f102da9f69c6039085`.
Subsequent boundary revisions are outside this review. Neither historical
review is overwritten or retroactively marked approved.

Only the two new review files were authored. No numerical executable probe,
test, evolution, geometry backend, reducer, Cargo command, REANA/service
control, commit, push or delegation occurred. All calculations below are
manual algebra. Document parsing/hashing and PDF reading/render inspection
are not numerical validation. Frozen scientific source `2bdcea0` and M1
evidence are unchanged; fresh M1 acceptance remains root-owned and pending.

## Primary sources and disposition of the six earlier findings

The complete pinned texts were available and their relevant surrounding
sections were read. [P26 v1](https://arxiv.org/pdf/2609.35989v1) is 37 pages,
14,060,781 bytes, SHA256
`6e12da18a86c57536fc26f2baf86d15d6db2e378e040a59bc9b82870b2dfcb84`.
Its printed pp.6–7 Eqs.38–42, pp.8–13 Eqs.51–76 and pp.14–16 Eqs.80–92
provide the gauge, fits and published stage context. [P09 v3](https://arxiv.org/pdf/0901.4107v3)
is 67 pages, 9,354,438 bytes, SHA256
`dfe38502394b15a0b05bbb1f610b0e1533198594e33681e22a507162cc2d10f4`;
printed p.17 Eqs.32–40 provides the bisector/flux-frame context. The PDF
identifies v3, 31 October 2009, recompiled 26 November 2024; it is not the
different v2 gravity source. P26 pp.15–16 and P09 p.17 rendered equation
pages were inspected again for this review. Earlier session inspections of
P26 pp.6,9,12,13 remain context, not new runtime evidence.

S3's normal speed follows P09; its face covariance, S5, S10–S19, graph GCL,
uniform spline grid and topology controller are this project's engineering
constructions. P26's state-product EMF and frozen second-stage cleaning are
distinct from the selected numerical-EMF/reevaluated profile. No published
equation proves these amendments. No external code was copied and no
source-access gap remains for these anchors.

| Earlier finding | Disposition against the new bytes | Remaining gate |
| --- | --- | --- |
| 1, target/M1 reduction | Design ambiguity resolved by S1–S2 and run-frozen Vref; comparison is conditional. | S-FRAME on identical arrays; full-3D physical convergence separately. |
| 2, samples/double projection | Resolved explicitly by S11–S15 and the stage table. | S-INC, true residuals, immutable replay. |
| 3, centroid/time order | S3–S5 replace the defective mean-speed rationale; S16 is correct; S17–S19 give conditional ODE order. | S-CENTROID/CDOT/ORDER; state-dependent motion still unspecified. |
| 4, missed topology | Operational comparison/failure policy now exists, with an honest alias example. Not event certification. | Finding 6 clarification, independent S-EVENT reference and production coverage. |
| 5, mean/energy | Missing identities and all conversion channels are now explicit; no repair is smuggled in. | Mean, physical-target, positivity and partition gates; no claim of passing. |
| 6, raw xyz/gauge/origin | A reproducible periodic raw profile and origin law are supplied. | Full-3D static/operator/auxiliary/boost evidence; walls remain gated. |

## Numbered findings

### 1. Supported scoped target/frame contract; M1 reduction is not literal extrusion

**Locators:** stage S1–S2, lines 61–112; mesh §7.1 lines 746–761;
frozen `general.rs:853–868,1217–1242`, `mhd-core/src/lib.rs:615–635`.

With outward-left incidence D, adding `Bn*(Vref-T)` to one shared flux gives
exactly `t_full-t_compare=-(Vref-T)*D(area*Bn)/V`. The volume-conversion term
is identical and cancels in this difference. This verifies S2's sign and its
**returned-face** divergence definition. It need not equal the unlimited LS,
face-mean or limited-face diagnostic. On fixed metric, L applies to that rate
difference. A continuum div(B)=0 statement cannot remove it.

The actual frozen flux transformation yields
`F_ind,ALE=(v dot n-w dot n)*B-Bn*v` for a consistent constant state.
Under a joint boost b it changes by `-Bn*b`; adding `Bn*Vref` cancels that
change when Vref also gains b. Gas fluxes already have their laboratory ALE
transform. Subtracting `w_n*U` or `w_n*B` again is incorrect. Equal/opposite
accumulation uses one shared returned face solve, including its Bn completion.

Freezing Vref for the whole run, including gravity kicks, source transactions
and births, is a useful exact contract. The auxiliary volume mean and wall
velocity are separate quantities. Recomputing Vref after an impulse would
change the semidiscrete method and gauge without a frame transformation.

**Required scope/gate:** S15 proves the A integrator's matching-array
reduction, not automatic equality of every Q/phi/auxiliary stage. In particular
the spherical 3D cleaning radius differs from frozen `general.rs:456–459`'s
2D radius, and 3D fits/deposition differ from their 2D counterparts. A full
state comparison must inject/certify those maps too. Keep S-FRAME's `1e-12`
algebra and `1e-9` solve-normalized comparison gates; the smallest case is
injected fixed/rigid M1 arrays with nonzero returned divergence and
Vref_xy unequal to rigid velocity. A separately tessellated extrusion is a
spatial/physical comparison. No M1 evidence or guard is changed.

### 2. Supported geometric derivatives, with exact chart and differentiation obligations

**Locators:** stage S3–S5, lines 116–178; mesh §§5.1,6.1;
P09 p.17 Eqs.32–34; frozen `quadratic.rs:59–140`.

Differentiating `d dot(x-m)=0` gives
`w_n=mdot dot n+(w_L-w_R) dot(x-m)/|d|`, verifying S3 and
`gamma=(I-n*n^T)(w_L-w_R)/|d|`. Reynolds differentiation of the first moment
gives the independent identity

```text
R1: d(V*c)/dt = sum_incidence sign*A*(f*w_n(f)+M_f*gamma),
    V*cvel = sum_incidence sign*A*((f-c)*w_n(f)+M_f*gamma).
```

M_f is the area-normalized **central** surface second moment. Omitting it
would miss normal-speed variation on a rotating/nonrigid face. Both terms
have length^4/time before dividing by V, giving velocity. Right-incidence
f and c must be in the same lifted owner chart. In a one-cell periodic
translation, the two self-face lifts differ by a box length: their volume
terms cancel but R1 gives cvel=W. A zero coalesced graph column must not
erase this metric information. Closure of `sum sign*A*(f-c)*n^T=V*I`
also makes the added centroid velocity under a joint boost exactly b.

For S5 set A=Xw and residual rho=A*beta-bw. Differentiating
`A^T*rho=0` with real samples held fixed yields
`A^T*A*betadot=A^T*(bwdot-Adot*beta)-Adot^T*rho`.
The residual term is required for an overdetermined noisy/nonpolynomial fit;
it is not generally zero. QR triangular solves, differentiated column
unscaling, hdot and evaluation rows produce the derivative without forming
normal equations. Differentiating pivot choices is unnecessary when they
represent the same full-rank map; a real rank/stencil change is different.

**Required implementation detail/gate:** distinguish Cdot at fixed real-owner
samples from `d[C(t)*a(t)]/dt=Cdot*a+C*adot`; differentiating transported
samples and calling that Cdot would double count transport. Coalesce the
actual periodic baseline and repeated-image coefficients first. Include the
trajectory digest even when the geometry epoch is unchanged. Constrained
wall/nullspace derivatives are outside this formula's approval.

S-CENTROID's smallest independent geometry case needs an oblique rotating
face with nonzero M_f*gamma and a periodic one-cell rigid self-image control.
Compare rebuilt central differences at several spacings: `1e-10` affine/
rigid identities, second-order derivative decrease to the `1e-7` finest
bound. S-CDOT uses one small full-rank 3D periodic stencil, fixed sample
vectors and independent differences of the assembled C, then a separate
analytic moving-sample chain-rule check. Keep the `1e-12` constant/adjoint
checks. These remain prospective, not differentiated-backend results.

### 3. Verified S16: the withdrawn endpoint objective has a genuine order defect

**Locators:** stage §8.1 S16, lines 514–534; previous moving review findings
2–3 and 5. Dots below are total derivatives along the stated ODE/path.

Let `e=t-Cdot*a-C*r`, `f=r+L*e`, `k=Cdot*a+C*f`, and lambda=Vdot/V.
Expanding the quotient of integrated induction and actual endpoint volume
gives

```text
R2: BT_H=B0+dt*t+dt^2/2*[tdot+lambda*(k-t)]+O(dt^3).
```

The lambda term uses the derivative k of the **screened actual** field in
the endpoint face evaluation; replacing k by t would wrongly assume exact
target matching. Expanding C1 times the raw trapezoid and then L1 times
the endpoint mismatch gives the additional term, relative to Heun for f,

```text
R3: dt^2/2*[Ldot+L*Cdot*L-L*lambda*(I-C*L)]*e.
```

Thus S16 includes the volume term with the correct sign. A smooth GCL
corrector is O(dt^3) and cannot generally remove R3.

For the scalar C=1+c*t, V=1, r=t_target=0, kappa=1, a(0)=1,
`L=1/(2*C)` and `adot=-c*a/(2*C)`. The exact solution is C^(-1/2).
The old map is `1-c*dt/[2*(1+c*dt)]`, with coefficient c^2/2 at dt^2,
whereas the exact coefficient is 3*c^2/8. Their difference is
`c^2*dt^2/8+O(dt^3)`. This verifies both the counterexample and R3; it is
an algebraic matrix example, not an executed tessellated-curl experiment.

**Resolution/gate:** withdrawal is justified. Do not retain it as an
equivalent fallback after S12. The smallest future REANA S-INC algebra case
can use C(t)=1+t, V=1 and the above exact solution, comparing old and new
maps over a fixed interval with halved dt. It must expose the old defect
and new order above the solve floor. A separate changing-volume algebra
case should exercise R2; actual smooth geometry belongs to S-ORDER.

### 4. Supported conditional Heun proof; it proves the chosen ODE, not full ideal-MHD accuracy

**Locators:** S10–S15 and S17–S19, lines 341–398,400–493,536–604.

Put q_s=L_s*e_s. Exact S11 gives zP=dt*q0. The shifted corrector equation
gives `zH=dt*(q0+qstar)/2`, hence

```text
R4: astar=a0+dt*f0,
    a1=a0+dt/2*(f0+fstar).
```

The old correction half is passed through the identity; it is not screened
again. Changing L is included by evaluating L1 at the endpoint. For the
scalar example in finding 3, R4 gives
`1-c*dt/2+3*c^2*dt^2/8+O(dt^3)`, removing that defect. At dt=0 all
increment RHSs vanish; with matching geometry the correction is zero.
No endpoint target solve may be appended to this update.

The material target `t=-V^-1*D(area*F_T)-lambda*B` has units B/time.
So do Cdot*a and C*r; H has units length, and its increment RHS has
B*length^2, giving z in A units B*length. The lambda term is necessary
when turning an integral derivative into a field rate. Calling B a
centroid sample does not make this an exact finite-volume average identity.
That representation difference is a spatial-consistency obligation.

On a fixed smooth graph with bounded inverse, Euler sweep error and its
correction are O(dt^2), while the trapezoid sweep correction is O(dt^3).
S13 supplies two **old** samples to the predictor and four **old/predicted**
samples to the corrector, never Q1/V1. The O(dt^2) modification of Qstar
therefore leaves its endpoint predictor defect O(dt^2); differentiable
endpoint maps change rates by O(dt^2). Q's final GCL term is O(dt^3).
Together with R4 and ordinary Heun for phi/origin/K, this proves S19's
local O(dt^3) and conditional global O(dt^2) for S17, assuming stability/
Lipschitz bounds on the fixed spatial system. Actual cvel includes the
leading moving-point shift in S18; Cdot differentiates those same points.

The constant-state GCL sign also survives the revision: for constant
conserved density U and closed stage polyhedra, the raw Euler/trapezoid
update gives `U*(V0+D*S)`; subtracting `U*deltaS` from its shared exchange
adds `U*D*deltaS`, giving U*V1. With uniform B represented as Bmean and
constant a, consistent returned fluxes and metric closure give t=0,
C*r=Cdot*a=0 and zero projection correction. These narrow identities do
not establish nonconstant-state accuracy or general mean preservation.

This proof needs bounded sufficient time derivatives of every participating
map and a fixed active solve space, not just a fixed face count. In
particular exclude or separately control pressure-minimum/Riemann/fallback
switches and auxiliary interpolation-brick crossings: a shared Hermite
field is C1, so its Jacobian need not be differentiable across a brick.
Root/donor/limiter/ring changes are already excluded. The branch controller
is an error policy, not a replacement Taylor theorem at such events.

**Required scope/gate:** retain these smoothness qualifications explicitly in
the S-ORDER fixture metadata and show its branch history. At fixed h this is
time convergence toward the *screened spatial ODE*, including its retained
physical target mismatch. Centroid samples versus cell averages, raw EMF,
cleaning curl-gradient, Cdot and screening consistency need independent h
refinement. A relative normal residual bounds neither field error nor order;
use absolute residual times active inverse norm. The `1e-30` cutoff is a
recorded code-unit floor, not a theorem that a finite correction is zero.

Smallest physical S-ORDER: one smooth nonconstant xyz potential on a
prescribed nonrigid periodic mesh with fixed topology/branches, static
physical field first and an advected control second. Use at least four dt
halvings at fixed h, then separate h refinement. Keep predictor/final order
>=1.8 above independently identified spatial/solve floors. The temporal
reference must resolve the same S17 spatial ODE with independent integration
and bounded reference uncertainty; analytic physical-field errors separately
measure spatial/representation consistency. No new mathematical
order blocker is identified within these assumptions; none of this proves
second order for old-state-selected generator velocities or source splitting.

### 5. Raw xyz, auxiliary and stage contracts are reproducible; preserve the exact profile boundary

**Locators:** S6–S9 lines 180–339; stage table lines 476–493;
frozen `operators.rs:524–608`, `general.rs:1090–1248,1497–1583`,
`auxiliary.rs:107–174,209–317`, `pressure_blend.rs:8–54`.

S6 matches the selected M1-family choices in the dimensions actually present
there: numerical-flux EMF, unsigned surface-area averaging, `-J_u^T*a`,
limited linear donor transport, curvature=None and separate linear primitive/
B gradients. Its xyz/grad_phi_z extensions and 3D radius need their own
evidence. Neither the Hessian transport branch nor the literal returned-state
cross product is silently imported. EMFnum's normal completion still matters;
zero normal induction flux does not determine that component of A rate.

With u,v,cvel,Vref jointly boosted, `EMFnum-u cross Breturn`, cvel-u and
u-Vref are invariant; Jacobians and relative fit geometry are unchanged.
This supports the frame algebra, not discrete boost performance. K is a
separate gauge-offset variable with Kdot=Vref cross Bmean; omitting
`-J_u^T*K` is explicitly a new bulk gauge, not literal substitution into
P26. Constant K cannot contaminate C, Cdot or limits if the implementation
respects that separation. A sampled gradient gauge perturbation does not
inherit a proved discrete curl-gradient null identity.

S9 is an explicit origin ODE: deposit at o0/ostar, sample each fresh field
at local tau=0, correct o1 trapezoidally, rebuild Aux1 at o1. Advancing
ostar and also sampling it at dt would be a second translation. Tricubic
tensor basis/jet factors and root-1/2 alias summation are dimensionally
consistent; they ensure shared C1 interpolation, not exact velocity
reproduction from arbitrary deposition samples. The root policy, supported
states and empty-support rejection are now specified.

The stage table binds current geometry, state, trajectory, origin, raw fit,
pressure blend and sources. Its retry/new-tag rules avoid reusing Cdot with
another path or Auxstar at a different origin. Absent faces retain real
owner states by ID. No source/ID birth occurs inside the hydro branch;
accepted-endpoint source changes invalidate state-dependent caches.

**Required gates:** exact dense-map/transpose and C1/analytic-derivative
controls O01–O03 precede S-AUX-REPLAY; include root 4/2/1, rejected attempts,
origin winding and accepted-state restart. Preserve `1e-12` constant-K and
`1e-8` boost gates, nonzero fields and separate physical B/Q comparison.
The smallest replay case is one accepted smooth periodic step with an
intentionally rejected larger trial and reordered storage. A later bounded
provider follows the translating box chart, not S9's periodic mean drift;
this review accepts no wall operator, pressure rule or constrained Cdot.

### 6. Topology remains a numerical blocker; the new alias packet needs a sharper verdict definition

**Locators:** stage §9 lines 606–732, S20; mesh M02 line 927;
previous moving review finding 4. No event geometry was computed here.

The three branches now integrate **physical** Heun/GCL steps, compare
per-key/time-bin exchanges and states, select only the finest complete
branch and reject unresolved/minimum-interval/resource failures. This is a
substantial correction to an unspecified geometry movie. Compatibility
checks use positive non-self components before pinning and full residuals;
near-zero weights invalidate the smooth order proof. Shared gas/target
exchanges retain antisymmetry and actual tessellated volumes remain primary.

The five local points lie on the stated bipyramid. ABCD's sphere is the unit
sphere; E crosses it where
`(3*s/2-1/2)^2=2*epsilon_e-epsilon_e^2`, giving the stated roots. The DE
segment crosses the interior of ABC near the event. The nearest background
seeds are at distance sqrt(3)/8 from c, greater than R=1/20, so none is
inside the core sphere. This supports the intended local flip geometry;
the clipped physical face and all other empty-sphere predicates still need
the independent oracle.

For epsilon_e=2^-9 the radial cross-section is sqrt(1023)/512, strictly
less than 1/16. At s=3/8, |E_x|=1/16, so the dyadic levels through 3 miss
the positive face. For epsilon_e=2^-28 its time half-width is less than
`(2/3)*2^(-27/2)`, whereas the closest dyadic level-10 sample to 1/3 is
`1/(3*1024)` away. Thus all initial 256/512/1024-microstep branches can
miss it. In fact this inequality still excludes level 12; level 13 first
has an interior sample for the unshifted core. These are hand inequalities,
not evidence of a particular backend's accepted topology or controller pass.

**Required author clarification before S-EVENT implementation:** distinguish
two verdicts: (a) face/event coverage, and (b) exchange error within the fixed
global state scale. A nonzero transient contribution can be arbitrarily
small. Losing all of it can satisfy `1e-4` branch differences and `1e-3`
global reference error. The current <=10% transient condition bounds the
**reference uncertainty**, not candidate coverage/error. Therefore those
global numbers alone do not define the claimed "caught false pass" in the
deliberately aliased packet. Freeze an independent predicate/face-presence
assertion for the geometry challenge (missing DE must be reported), and a
separate noncancelling transient-DE exchange diagnostic with uncertainty.
Declare before execution whether a coverage miss itself rejects this fixture
or the claim is solely error-bounded exchange. Keep the existing global
error gates; do not rename a small global error as universal coverage.

For the analytic-exchange comparator also freeze exactly what is integrated:
e.g. surface integrals of known smooth conservative/induction ALE flux using
the affine w_n(x), rather than a reused candidate face-centre quadrature.
If isolating temporal/event error on the same spatial face rule, label that
distinct comparator and give the independent surface-quadrature uncertainty.
Otherwise spatial face quadrature can masquerade as event error. Root
isolation must resolve the event relative to its width; the stated absolute
`1e-10*DeltaT` is an upper bound, not sufficient accuracy for every required
transient-contribution uncertainty. Freeze any extra precision prospectively.

**Smallest independent REANA sequence:** 69-seed geometry-only exact/rational
predicate/root brackets first; then independently clipped polygons and
analytic exchanged fields with at least 32 interior event subdivisions and
two refinements, including epsilons, shifts and coordinate permutations.
Compare dyadic alias branches to this reference, not to themselves. Retain
`1e-12` GCL, `1e-10` uniform/budget and `1e-3` finest exchange gates and
decreasing error. A coupled case rejected for initial mean/fit/pressure does
not validate topology coverage; keep the analytic comparator independent.

The <=512-cell comparison controller is honestly described as uncertified.
Its fixture success can justify only that limited error-controlled reference
scope. A state-dependent, scalable trajectory/event policy and adversarial
coverage remain required before the merger; sampled agreement alone can
never approve arbitrary short events. Typed rejection when a comparison
fails is sound, but it does not make an unseen false acceptance fail closed.

### 7. Mean and energy are correctly exposed, not solved by the new time integrator

**Locators:** S10, S20a–S22, lines 348–373,734–818; mesh §5.2;
P26 p.16 footnote 12 and pp.13–14 energy discussion; frozen
`projected_rate.rs:337–408,471–552`, `general.rs:462–475`.

The physical rate mismatch is `(I-C*L)*e`; the normal residual measures only
the finite solve. S14's shared target conserves its periodic volume sum,
but S11–S12 do not set that target equal to the recovered field. For
`M=(1^T*V/Vtot) tensor I`, the product rule verifies S20a:

```text
R5: mu-Bmean=M*C*a,
    (mu-Bmean)dot=(Mdot*C+M*Cdot)*a+M*C*f.
```

C*constant=0 is a right-nullspace property; mean preservation needs a left
condition. If G=M*C is nonzero, there exists a with G*a nonzero (choose
a=G^T*b with G^T*b nonzero). Some initial states therefore fail the mean
gate before any time integration. The publication's mean-conservation
statement cannot establish this identity for the changed LS/screened maps.
No mean identity is silently supplied by S19. The declared rejection at
`1e-9*Bscale` is honest and must stay a prerequisite, not an assertion of
eventual success or grounds to select only specially cancelling fields.

S21's geometric, raw and projection changes telescope to
`V1*|B1|^2/2-V0*|B0|^2/2`. At fixed endpoint Q,V, changing B by projection
changes thermal energy by exactly the negative magnetic change. S22 follows
by subtracting kinetic and all three magnetic channels from total Q_E.
Origin/gauge choices affect raw rates; K itself is outside curl and has no
extra physical energy. The path split is diagnostic, not physical heating.
Q_E conservation does not establish entropy stability or small partition error.

**Required gates:** independently check C/C^T and coalesced Dproj on a small
irregular mesh before evolving; no volume factor may be applied twice.
Positive active diagonal with kappa>0 gives SPD; exact zero columns are
unobserved, while a tiny nonzero column is not a gauge pin. Keep the new
`1e-14` scaling-rejection diagnostic, absolute residual/inverse sensitivity
and source/geometry hashes. A fixed relative solve tolerance is a floor.

S-PARTITION must keep initial/stage/final mean, physical finite-target/rate
errors, independent divergences and cellwise/signed/sum-absolute conversion
histories. The smallest cases are a nonzero smooth field on changed geometry
and weak-field/beta=.01 positive-pressure controls with a separately refined
reference. Retain `1e-9` true normal, `1e-9` mean, `1e-10` budget, >=1.8
physical convergence and `1e-3` excess-conversion gates. No measured mean
subtraction, retuned Bmean, pressure/energy reset or distributed residual
may turn a failed case green. This remains a moving-physics adoption blocker.

### 8. Final-goal dependencies remain: prescribed geometry does not complete the merger

**Locators:** S17 limitations lines 586–604; stage table source rows;
mesh §§7.3,11; pinned shared contract "Mesh motion and physical boundary gate";
the unchanged independent bounded review.

The limited proof treats g(t) as prescribed. If a generator equation is
`rdot=w(Y,r)` but a step freezes w0, then
`r1=r0+dt*w0` omits `dt^2*(w_t+w_Y*F+w_r*w)/2`. This is generically an
O(dt^2) local trajectory error, independent of R4's order for the conditional
fluid ODE. Updating the generator velocity only at the next step does not
remove it. A state-dependent predictor/regularization law, differentiable
path or a separately justified order claim remains a design task. Actual
centroid velocity still has to be derived from that chosen path.

Gravity work, softened gas-centroid representation and endpoint source
transactions keep their separate ledgers/prerequisites. Run-frozen Vref
survives them. A hydro Heun proof and collisionless KDK do not make the
declared first-order gas/ISM/source split second order; newborns activate
only at their accepted endpoint, with no replayed previous kick.

The first galaxy profile's conducting slip box remains a physical choice,
not an approved discrete operator or vacuum model. Bounded U1–U4, wall
pressure/reflection, constrained Cdot and auxiliary trace compatibility,
domain/ambient controls and isolated gravity remain explicit independent
dependencies. This task neither reviews a concurrent wall amendment nor
closes any finding in the frozen bounded report.

**Implementation disposition:** after scoped M1 acceptance, proceed with
independently reviewed static M2a geometry/QR/curl/adjoint/auxiliary slices
and their frozen fixtures. Then stage the small S-FRAME/INC/CENTROID/CDOT
and clarified event-reference slices; use this review's limited algebraic
support without claiming moving physical acceptance. Moving coupling remains
conditional on S-ORDER/PARTITION/EVENT/BOOST and all preceding gates. Prepare
the augmented state-dependent trajectory and bounded/source contracts before
long gravity/ISM/merger coupling. Preserve the goal of genuinely deforming,
self-gravitating full-3D MHD with multiphase gas, DM and old/new stars.

All future executable cases run on REANA, one independent case per workflow,
with declared threads/memory/time and no aggregate cap. Retain the author's
packet envelopes and preflight/build/scientific prerequisites; failures stop
dependent escalation. No threshold is weakened and no successful numerical
gate is manufactured by this review.

Document-only checks passed: all 33 pinned source/contract/context/code
identities match, JSON parses, local links resolve, fences pair, final
newlines are present and owned files have no trailing whitespace.
`git diff --check` passed. The working boundary specification changed during
this review; only its committed `66370fa` bytes identified above were used.
Historical reviews and inspected frozen scientific files retain their hashes.
