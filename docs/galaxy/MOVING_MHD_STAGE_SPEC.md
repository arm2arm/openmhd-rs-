# Revised moving-MHD stage contract

2026-11-22, author revision responding to findings 1–6 of the
[independent design review](MESH_3D_DESIGN_REVIEW.md). **Proposed engineering
method; unimplemented, unexecuted, not independently approved.** The review
retains its original line/hash locators and disposition. It does not approve
these new bytes. [Source identities](moving_mhd_stage_sources.json) pin both
inputs and the actual frozen M1 code inspected for this revision.

This document supersedes the ambiguous moving-stage/projection choices in
[MESH_3D_SPEC.md](MESH_3D_SPEC.md), not its geometry, signs or acceptance
gates. It withdraws the old finite-endpoint projection as the selected
second-order moving proposal. Its fixed-metric reduction remains useful.
The new proposal is `moving-covariant-heun-increment-v2`, initially with
prescribed linear generator trajectories and periodic operators. Bounded
coupling uses the root-selected `box-conducting-slip-relative-v1` only after
the [boundary operator contract](BOUNDARY_MHD_SPEC.md) resolves U1–U4
identified in its [independent review](BOUNDARY_MHD_DESIGN_REVIEW.md). No conducting-wall approval is inferred.

No numerical source changes, tests, executable probes, evolutions or workflow
controls are authorized here. M1 source `2bdcea0d28340e7429e10053a641f92d51fcc696`
remains immutable and unaccepted. The final goal remains genuinely deforming,
state-dependent full-3D MHD with isolated gravity and active sources; the
prescribed-trajectory argument below does not complete that goal.

**Follow-up to the [independent revised-stage review](MOVING_MHD_STAGE_DESIGN_REVIEW.md)
at 70ad33e:** retain its conditional Heun support only for the stated smooth
prescribed-path spatial ODE. Section 9.2 now fixes finding 6's coverage/
exchange verdicts, independent surface reference and relative root accuracy.
The separately proposed [periodic shared-face curl comparator](CURL_3D_MEAN_SPEC.md)
addresses finding 7's missing mean left-nullspace by a different operator,
not by repairing the LS result. The selected reference remains
`periodic-ls-quadratic-point-curl-v1`; no comparator adoption, event
certification, wall approval or new physical acceptance follows.
The independent report and its exact reviewed-byte locators remain frozen;
it does not approve these new bytes.

## 1. Review disposition and publication boundary

| Finding | Addressed design equations in this revision | Still-open prerequisite before coupled implementation/acceptance |
| --- | --- | --- |
| 1, target frame | Two explicit policies, run-constant Vref, exact returned-face-divergence difference (S1–S2). | Independently compare target-only arithmetic on identical M1 arrays; full 3D fits need their own evidence. |
| 2, samples/stages/projection | Old/predicted-owner four samples (S13), complete explicit stages (section 7), one correction per raw increment (S11–S12), fixed-metric R3 derivation (S15). | Independent audit of the changed covariant increment objective and REANA fixed-metric reduction. |
| 3, centroid/order | Moment-derived instantaneous centroid velocity (S3–S4), actual endpoint location, differentiated curl, explicit fixed-topology Heun proof (S17–S19) and old scheme counterexample (S16). | Consistency/conditioning of Cdot, spatial/solve floors, non-smooth switches and state-dependent trajectory law remain unvalidated. No general second-order moving claim yet. |
| 4, topology | Limited operational adaptive branch comparison, minimum interval/typed rejection, concrete transient-face inputs and independent-reference requirements (section 9). | Sampling is not an event certificate; alias/short-event and independent resolved-exchange gates must pass before extending this small reference to production. |
| 5, mean/energy | Separate target/normal residuals and three magnetic-transfer channels (section 10, S21–S22); fail closed at the unchanged mean/pressure gates. | Retained LS reference has no proved discrete mean or magnetic-energy identity. The unadopted shared-face comparator has its own F2/F9 mean algebra, not physical acceptance. A failed LS mean gate is not repaired by subtraction. |
| 6, raw 3D operator | Full xyz numerical-EMF/transport/distortion/mean/cleaning rate, curvature=None, separate linear primitive/B gradients, gauge/origin/root rules (S6–S9). | Independent full-3D limiter/auxiliary/boost/restart evidence; bounded U1–U4 remain open. |

P denotes a checked publication statement, D a derivation here, E a proposed
engineering choice, U a remaining prerequisite. Everything in the new stage
algorithm not expressly labelled P is D/E. Primary sources are the complete
hashed PDFs: [P26 v1](https://arxiv.org/pdf/2609.35989v1), printed pp.6–7,
Eqs.38–42; pp.8–13, Eqs.51–76; pp.14–16, Eqs.80–92; and
[P09 v3](https://arxiv.org/pdf/0901.4107v3), printed p.17, Eqs.32–40.
The latter's actual bytes are v3, 31 October 2009, recompiled 26 November
2024, not the different v2 gravity source. Both full texts are available;
there is no source-access gap for these anchors. Neither publication gives
our Cdot/projection, graph correction, topology controller or auxiliary-origin
algorithm. No AREPO algorithm/equivalence or unpublished coefficient is claimed.

## 2. State, targets and immutable reference frame

At accepted time t0 the real-owner state is
`Y0={Q0,a0,phi0,o0,K0}` by typed CellId. Geometry `g0` owns actual V0,
centroids c0, lifted generators, faces, fits and raw curl C0. Bmean is a
run-constant parameter and `B0=Bmean+C0 a0`. K is a separately stored
spatially constant gauge offset; it is never included in C, Cdot, limiter
differences or the distortion contraction. Full potential output is a+K.
Use the common SI-derived units with mu0_code=1. Matrices V below repeat
each real-cell volume for xyz components. D is outward-left incidence;
`Qdot=-D*(area F_Q)`. This D is not a magnetic field or a projection diagonal.

**E:** choose and checkpoint `Vref=sum_initial_gas p/sum_initial_gas m`
from the initial conservative gas catalog, or a literal configured value
under a separately recorded initialization option. Freeze it for the **entire
run**, including gravity kicks, births, recycling and loss/source events.
Only a joint change of inertial frame changes it by the same constant boost.
It is not the instantaneous gas bulk velocity, auxiliary volume mean, wall
speed or generator velocity. Its initial catalog/hash and choice are provenance.

Record `CurlOperatorId=periodic-ls-quadratic-point-curl-v1` in this
reference's geometry/state caches. The proposed shared-face option is a
separate new profile with the field-sampling/Cdot rules in
[CURL_3D_MEAN_SPEC.md](CURL_3D_MEAN_SPEC.md); changing that selector requires
new review and evidence, not reuse of old Cdot or M1 arithmetic claims.

Two named target policies use the returned numerical face Bn:

```text
bulk-full-vector-vref-v1: T_s,f=Vref  (selected new 3D policy)
m1-rigid-xy-zref-compare-v1: T=(w_rigid,x,w_rigid,y,Vref,z)
F_T,s,f=FaceFlux.induction_s,f + Bn_s,f T_s,f,
Bn_s,f=n_s,f dot FaceFlux.magnetic_s,f.                         (S1)
```

The comparison policy is supported only for the named fixed/rigid,
z-invariant comparison, with one constant rigid velocity. It is not a rule
for arbitrary 3D deformation. Boundary faces use their physical provider;
the conducting wall has Bn=0 and zero completed induction exchange.
There is one shared F_T per interior face. FaceFlux fluid/induction already
are laboratory ALE fluxes; never subtract another `U w_n` or `B w_n`.

**D, review R1:** on identical C/fit/face/state/volume arrays in the rigid
comparison, `t_s=-V_s^-1 D(area F_T,s)` satisfies

```text
t_full,i-t_M1,i=-(Vref-T) d_returned_face,i,
d_returned_face,i=sum_f D_if area_f Bn_f/V_i.                   (S2)
```

This is not necessarily the LS, face-mean or limited-face divergence in
outputs. The screened correction difference is L applied to this difference
when Cdot=Vdot=0. Record both differences and the returned-face divergence.
Equality needs the special frame/divergence/nullspace conditions in the
review. A genuine 3D extrusion generally changes weights/rows even for
z-invariant fields. Arithmetic comparison requires an **identical-operator
certificate or injected frozen 2D stage arrays with zero z derivatives**;
otherwise compare converged physical errors, not arithmetic identity.

## 3. Actual centroid velocities and differentiated curl

**P09/D:** on a fixed smooth topology, canonical face speed has the form
`w_n(x)=w_n(f)+gamma_f dot (x-f)`. For a Voronoi bisector with
`d=r_R,image-r_L`, `n=d/|d|`,

```text
w_n(f)=[(w_L+w_R)/2] dot n
         +(w_L-w_R) dot (f-(r_L+r_R,image)/2)/|d|;
gamma_f=(I-n n^T)(w_L-w_R)/|d|.
M_f=(1/area_f) integral_face (x-f)(x-f)^T dS.                   (S3)
```

The old face-normal sign is retained. For a physical translating wall,
`w_n=W_wall dot n`, gamma=0. Rebuilt face second moments, not only centroids,
are necessary: w_n varies over a nonrigid face.

**D, Reynolds moment differentiation:**

```text
Vdot_i=sum_f D_if area_f w_n(f),
cvel_i=(1/V_i) sum_f D_if area_f *
       [(f_i-c_i) w_n(f) + M_f gamma_f].                       (S4)
```

Here the sums in S4 run over **metric incidences before owner coalescing**;
f_i is lifted into the corresponding incidence's owner chart. A periodic
self-image contributes two different f_i lifts with opposite signs. Its
scalar volume contributions cancel, but its first-moment terms must not be
dropped by first forming a zero owner-incidence column. This follows by differentiating
`V_i c_i=integral_cell x dV`: the face integral of x w_n is
`area*(f w_n(f)+M_f gamma)`. Tangential polygon-centroid motion is not
inserted as a normal speed. The closure tensor implies cvel transforms by
the joint boost. S4 is an instantaneous derivative of the **actual** tessellated
centroid, not a generator/centroid finite-displacement average.

For each prescribed linear trajectory evaluate S4 at g0 and g1 using the
same frozen w_i. Endpoint locations are the rebuilt `c1`, not
`c0+dt*w_i`, and the old/predicted point values live at c0/c1 respectively.
The earlier `what=2*(c1-c0)/dt-w_i` policy is not used in this profile.

**E/D: Cdot plan.** Differentiate the actual unlimited quadratic curl map
with real-owner values held fixed. Its epoch key additionally includes
the generator-trajectory/velocity digest, wall motion and fit policy. In a
constant image/ring/QR-rank region, local coordinates have derivatives
`d_j'=cvel_j,image-cvel_i`; `h'=h Vdot/(3V)`. Quadratic objective weights
`1/|d_j|` and scaled polynomial entries are differentiable there. Let
`Xw=sqrt(Wfit) X`, `bw=sqrt(Wfit) y` for one scalar fit, coefficient beta,
and residual `rho=Xw beta-bw`. Differentiating the least-squares stationarity
equation with samples y held fixed gives

```text
(Xw^T Xw) betadot = Xw^T(bwdot-Xwdot beta)-Xwdot^T rho.         (S5)
```

Use the original QR triangular factors to apply this inverse twice, not
explicit normal-matrix formation. Differentiate physical h scaling and
the evaluation rows as well. If the factored design has additional column
normalization, differentiate those column norms and the coefficient unscaling
(or apply S5 in the unnormalized basis through equivalent scaled factors);
freezing a changing norm changes Cdot. Coalesce baseline/repeated-image coefficients
before constructing Cdot. Cdot is the partial time derivative of C, not C
applied to an already transported a. Constants satisfy Cdot*constant=0 in
the periodic algebra, which needs an independent coefficient check.
Local polynomial rank does not imply curl rank. Changes of stencil, support,
topology or true fit rank invalidate this smooth derivative; the controller
handles them as non-smooth cases. Pivot tie changes of a full-rank equivalent
factorization must not change the represented derivative.

**U-Cdot:** no numerical consistency/conditioning evidence exists for S4–S5,
including their combined cancellation with raw transport. Finite differencing
C in production is not an interchangeable unstated fallback. Its independent
REANA oracle uses central differences at several registered differences and
analytic polynomial reproduction, with truncation/roundoff floors separated.
For constrained wall fits, their actual constraint/nullspace derivative is
also required; S5 alone does not differentiate those constraints. This is
still blocked by the independent bounded-operator review.

## 4. Complete named raw periodic 3D rate

**E profile:** `raw-3d-numerical-emf-linear-donor-v1` is the sole raw
operator used by `moving-covariant-heun-increment-v2` in this revision. Its
configuration pins quadratic unlimited A/phi derivatives, smooth-extrema
A transport limiter, neighbour-extrema primitive limiter, curvature=None,
HLLD-pressure/SignalWeighted face completion, and the periodic spline/tricubic
auxiliary below. Changing any of these creates a separate recorded profile.

At stage s in geometry g_s, recover Q_s/V_s and B_s together with positive
thermal closure. Fit all xyz A and phi derivatives with the unlimited
ten-term quadratic point fit. Denote `J_a[k][b]=partial_b a_k` and
`J_u[j][k]=partial_k u_j`. Use quadratic-derived A gradients in a **separate**
limited transport copy, but no donor/receiver Hessian transport remainder:
`transport_curvature=None`. Hessians may be retained for diagnostics only.

**E, M1-family choices:** independently linear-fit all eight primitive
components `(rho,vx,vy,vz,p,Bx,By,Bz)` on the one-ring centroid stencil,
using face-area objective weights and the stored cell-average anchor for
piecewise-linear face reconstruction. Limit those gradients by the separate
neighbour-extrema fluid limiter. Do not use the derivative of quadratic A
Hessians for the Riemann B gradient. The latter remains a named same-fit
diagnostic, not this fluid reconstruction. M1's selected Heun profile also
has curvature=None and separately linear primitive/B gradients; its M0
Hessian-transport branch is different.

Each stage Riemann input is a spatial reconstruction to the **current stage
face** from the current stage state, with no extra temporal predictor:
`q_L,f=q_L+limited_grad_q_L dot(f-c_L)` and similarly in the right image.
There is no second `dt*material_derivative`, centroid offset or old-state
extrapolation hidden inside that stage. Use the existing HLLD-pressure
blend and SignalWeighted completion, with recorded fallbacks. Its 3D pressure
weight is the cube of the minimum positive pressure ratio over both owners'
incident faces (same frozen scalar algorithm, generalized adjacency).
Boundary pressure observations come from the boundary provider, not a new
real mass. Positivity failure rejects; do not replace a failed state by a floor.

The primitive limiter scales each cell/component gradient by the minimum
of 1 and its neighbour-extrema ratio for all face extrapolations, clamped
to [0,1]. For the potential's `smooth-extrema-v1` component limiter, define
`jump=a_j-a_i`, `here=jump-J_i dot(c_j-c_i)`,
`there=J_j dot(c_j-c_i)-jump`. Both negative admit
`concave=max_j min(-here,-there)`; both positive admit
`convex=max_j min(here,there)`. Set `upper=max_neighbour a-a_i+concave`,
`lower=min_neighbour a-a_i-convex`; take the minimum positive/negative
face-extrapolation ratio, clamp [0,1], and scale the raw gradient only.
This is an engineering xyz extension of the actual frozen scalar rule,
not an invented Hessian limiter. Record branch changes and raw/limited rows.

Let `d_if=f-c_i`, `b_i=cvel_i-u_i`, and let `ell_if` be the vector derivative
coefficient of the independent free-intercept, face-area-weighted **linear
face-centre** fit. Its full baseline subtraction is included in the map.
For an interior face choose donor=i when `b_i dot d_if<0`, otherwise the
other real owner in its image (including equality). Define

```text
a_up,i,f,k = a_donor,k + Jlim_a,donor[k][:] dot(f-c_donor,image),
T_i,k = sum_f (sum_b=x,y,z b_i,b ell_if,b) (a_up,i,f,k-a_i,k).
r_i,k = sum_f area_f/S_i *
          [EMFnum_f,k - (u_i cross Breturn_f)_k]
        - sum_j=x,y,z J_u[j][k] a_i,j
        + (grad_phi_i)_k + [(u_i-Vref) cross Bmean]_k + T_i,k,
S_i=sum_incident_faces area_f.                                (S6)
```

EMFnum is the numerical-flux electromotive vector returned by the same
face solve, with its reviewed normal completion. It is **not replaced** by
`v_return cross B_return`. There is no incidence sign on the vector EMF
surface average, no centroid-triangle weighting and no quadratic transport
term. The geometric cvel in b is S4, not the trajectory's generator velocity.
All xyz contractions, including gradient_phi_z, are active. Reconstruct the
donor at the same stage face/centroid; reevaluate donor decisions at g1.

For periodic phi the named reevaluated cleaning rate is

```text
chi_i=alpha c_s,i^2 div_a,i - beta_clean c_s,i phi_i/r_eff,i,
div_a=sum_k=x,y,z J_a[k][k]; c_s=sqrt(gamma p/rho);
r_eff=(3V/(4pi))^(1/3); alpha=1; beta_clean=.15.                 (S7)
```

No additional phi transport term is silently added: this is the point source
along the centroid trajectory. The source/EOS/radius convention is recorded.
Reevaluate S7 at the predicted endpoint, unlike P26 Eq.90's frozen old source.
For the bounded profile replace gradient_phi/divergence by that profile's
reviewed pair and constrained traces; do not mix its proposed negative
adjoint with the periodic LS divergence and call it accepted.

The offset and mean convention is

```text
Kdot=Vref cross Bmean; Kstar=K1=K0+dt*Kdot.                      (S8)
```

The deliberate omission of `-J_u^T K` belongs to the bulk reduced gauge;
it is not substitution of a+K into the literal P26 gauge. Keeping K outside
difference arithmetic avoids a growing constant contaminating curl/limiting.
The source `(u-Vref) cross Bmean` in S6 plus S8 gives the full mean source.
For the conducting relative wall, Bmean=0 and K=0, because arbitrary constant
offsets need not satisfy its tangential A trace. Preserve that separate gauge.

## 5. Auxiliary stages, origins and caches

**E:** periodic auxiliary deposition is the uniform tricubic generalization
of the actual M1 cubic B-spline, volume-weighted, with shared corner jets
`u,ux,uy,uz,uxy,uxz,uyz,uxyz`, analytic Hermite derivatives and a persistent
lifted origin o. Initial interval choice 4, coarsening 4/2/1; record counts,
normalizers, root and maximum contributing cell volume. Sum all aliases at
roots 1/2 before normalization. Native/outer pools do not nest. The P26
adaptive algorithm is not asserted here. Physical means use real cells only:

```text
m_s=sum_i V_s,i v_s,i / sum_i V_s,i,
Aux0=deposit(g0,Q0,a0,origin=o0); sample Aux0 with stage_time=0,
ostar=checked_wrap(o0+dt*m0),
Auxstar=deposit(g1,Qstar,astar,origin=ostar);
sample Auxstar with stage_time=0,
o1=checked_wrap(o0+dt*(m0+mstar)/2).                            (S9)
```

All origin formulas are full xyz; preserve an overflow-checked lift/winding
separately. This is an explicit origin ODE, not a second translation inside
sampling. Never advance ostar and then sample its fresh field with tau=dt.
Freezing Aux0 and sampling it at dt is a different profile, not S9. Build
Aux1 from final Q1/a1/o1 for final closure/CFL and the next accepted state;
do not treat Auxstar at ostar as Aux1 at o1.

The periodic deposition/interpolation rule is explicit (E, tensor extension
of frozen auxiliary.rs:21–95,107–127,146–174,209–268). On each axis set
`q=n*((x-o) mod L)/L`, `j=floor(q)`, `f=q-j` and deposit weights
`[(1-f)^3, 4-6*f^2+3*f^3, 1+3*f+3*f^2-3*f^3, f^3]/6`
to corners `(j-1,j,j+1,j+2) mod n`. Sum coincident aliases first. For each
corner use `w_i=(V_i/sum V)*wx*wy*wz`, deposit w_i*v_i and w_i in
sorted real-ID order, and normalize their ratio. Shared jets are periodic
centred differences of those corner values, including mixed differences:
`D_x=(shift_+x-shift_-x)/(2*h_x)`, jet indexed by subset S of xyz is
`product_{axis in S} D_axis value` (fixed x,y,z application order).
The Hermite basis for endpoint0 is `(2*s^3-3*s^2+1,s^3-2*s^2+s)`
and for endpoint1 `(-2*s^3+3*s^2,s^3-s^2)` for value/derivative slots.
Sum the eight corners and eight subset jets with product basis and the
physical factors `product_{axis in S} h_axis`; differentiate that polynomial
analytically for J_u. There are 64 coefficients per component/cube.
This defines derivatives of the interpolant; it is not a claim of exact
linear velocity reproduction by deposition on irregular cell samples.

At every build deterministically try 4/2/1 using the **same stage samples**;
empty support or nonfinite normalization at the last root is a typed failure.
There is no silent zero-velocity fallback. Root/limiter/donor switches are
recorded as non-smooth branches and enter the adaptive comparison in section
9. The smooth order argument excludes such switches; persistent failure at
the minimum interval is `AuxiliaryTransitionUnresolved`, not permission to
accept a lower-order unlogged update. Checkpoint the active/requested root
policy and origin, rebuilding jets deterministically from matching inputs.

Bounded auxiliary construction is proposed to use the separately reviewed reflected
box-chart provider: origin is the translating physical box origin at each
stage, not S9's volume-mean drift. Do **not** advance that wall chart by m_s.
It also samples with stage_time=0. Record which origin law applies; do not
reuse periodic wrap at a physical wall. Bounded root/fallback/derivative
compatibility remains subject to that contract's unresolved review.

## 6. Covariant rate residual and one-correction increment scheme

Write `lambda_s=diag(Vdot_s/V_s)` repeated for xyz. The material target rate
at the cell centroid, including volume conversion, and the raw rate defect
are defined by

```text
t_s= -V_s^-1 D_s(area_s F_T,s) - lambda_s B_s,
e_s=t_s-Cdot_s a_s-C_s r_s,
H_s=C_s^T V_s C_s+kappa_proj Dproj_s,
Dproj_s=diag(C_s^T V_s C_s); L_s=H_s^-1 C_s^T V_s,
f_a,s=r_s+L_s e_s; kappa_proj=1.                              (S10)
```

Vdot is S4's actual geometric rate. This is a new rate objective accounting
for Cdot and Vdot; it is **not** the old finite-endpoint objective. Screening
does not make `Cdot a+C f_a=t` exactly. `L` notation is mathematical; no
matrix inverse is formed. C^T V is one volume weighting, not V twice:
`dot(C a,V b)=dot(a,C^T V b)`. Coalesce repeated owners and sample baseline
terms before forming diagonal squares. Positive-diagonal active columns
give SPD with kappa_proj>0, despite physical curl gauge null modes. Exactly
zero columns have zero RHS and an explicitly fixed-zero correction; reject
an inconsistent nonzero RHS there. For this proposed reference, an active
diagonal below 1e-14 times the largest active diagonal is a typed
`ProjectionScalingRejected`, not a zero column. Record that ratio, diagonal-
scaled operator/inverse sensitivity and physical increment norms; this new
threshold is an unexecuted engineering rejection policy, not an M1 criterion.
Nonfinite scaling or an unsupported ill-conditioned active solve rejects. Kappa_proj=0 is outside this first profile.

For both solves below use the registered iterative relative residual1e-11,
recomputed true normal residual1e-9, maximum24N iterations and reported
absolute RHS scale; RHS norm<=1e-30 returns zero correction with the implied
absolute error recorded. These are solver gates, not physical field bounds.

**Predictor:** raw trial plus one increment correction at the old tangent
metric, then endpoint closure:

```text
aP_raw=a0+dt*r0;
H0 zP=dt*C0^T V0 e0; astar=aP_raw+zP.                         (S11)
```

**Corrector:** integrate RAW rates from a0 and solve once about the already
known half old correction, not about the predictor as a new initial state:

```text
aH_raw=a0+dt*(r0+rstar)/2;
H1 (zH-zP/2)=dt/2*C1^T V1 estar;
a1=aH_raw+zH.                                                 (S12)
```

Equivalently solve for `vH=zH-zP/2`, then add zP/2 once. Its objective is
`min_v ||C1 v-dt*estar/2||_V1^2/2+kappa_proj v^T Dproj1 v/2`.
The known old half correction passes through the identity, not another
screened projector. No raw r is overwritten with f_a and then projected
again. There is one solve for each trial increment; no final additional
finite-target correction. In particular, **do not apply the old endpoint
solve after S12**. This design change is essential to the order argument.

## 7. Explicit Q/target samples, stages and geometry epochs

Let a star denote the **predicted endpoint**, never an implicit final state.
Every real owner j has `U0_j=Q0_j/V0_j` and `Ustar_j=Qstar_j/V1_j` even if
the particular face is absent at one endpoint. For union-key integrated
GCL correction use

```text
UbarP_f=(U0_L+U0_R)/2;
BbarP_f=(B0_L+B0_R)/2;
UbarH_f=(U0_L+U0_R+Ustar_L+Ustar_R)/4;
BbarH_f=(B0_L+B0_R+Bstar_L+Bstar_R)/4.                          (S13)
```

These are centre real-owner values, not limited face states or Q1/V1/B1.
Absence sets a stage face's **area/exchange** to zero, not its owner's state
to zero. Resolve both owners in that stage's ID map and image chart; missing
real ID is an error. The initial profile forbids creation/removal during a
hydro trial. Periodic images share their real values. A boundary key has
one real owner: request `BoundarySamples{old,predicted}` and prescribed
sweeps/ghost exterior values from the named provider instead of inventing R.
For a conducting wall the GCL correction on the prescribed physical sweep
is zero, so these hypothetical exterior correction samples are not used.
Actual Riemann states/ledgers still come from its wall-rest provider.

For the appropriate stage/key set define `s_s=area_s w_n,s` and outward
rates `X_Q,s=area_s F_Q,s`, `X_B,s=area_s F_T,s`. Retain the mesh contract's
graph sign/compatibility and actual volumes. Euler and trapezoid exchanges:

```text
SP=dt*s0; RP=V1-V0-D*SP; solve D deltaSP=RP;
EP_Q=dt*X_Q,0-UbarP*deltaSP;
EP_B=dt*X_B,0-BbarP*deltaSP;
Qstar=Q0-D*EP_Q;
BT_P=(V0*B0-D*EP_B)/V1;

SH=dt*(s0+sstar)/2; RH=V1-V0-D*SH; solve D deltaSH=RH;
EH_Q=dt*(X_Q,0+X_Q,star)/2-UbarH*deltaSH;
EH_B=dt*(X_B,0+X_B,star)/2-BbarH*deltaSH;
Q1=Q0-D*EH_Q;
BT_H=(V0*B0-D*EH_B)/V1.                                      (S14)
```

The incidence for each solve is its actual stage-union key graph; absent
faces contribute zero rates, never arbitrary newly invented zero-area edges.
The predictor graph uses old positive-area interior edges with weights
A0/Aref plus prescribed boundary sweeps. Corrector weights are
(A0+Astar)/(2*Aref) on positive union edges. Aref is a fixed positive
initial area scale; changing it by a common factor must not change deltaS.
Each connected component of non-self positive edges must have compatible R
sum to a scale-aware roundoff tolerance before pinning a multiplier. Freeze
the proposed compatibility bound as
`abs(sum_component R)<=256*epsilon*(sum_component(V0+V1)+sum_incident abs(S))`,
with the actual Euler/trapezoid S, counting boundary/incidence magnitudes.
This is a geometry compatibility check, not the looser iterative residual
gate; full residual includes pinned rows. No mean subtraction of a volume defect.
Self-image graph columns cancel exactly; commit their net gas update as
one deterministic zero transaction while retaining both metric incidences.
Keep parallel-image edges distinct. Near-zero graph weights/poor inverse
conditioning invalidate the smooth correction-order argument and trigger
refinement/rejection, never a replaced geometric volume.

**Important changed interface:** BT_P/H remain the finite-volume induction
target and physical-mismatch diagnostics. S11–S12 do not project directly
onto them. The rate objective is S10. At constant metric the two formulations
have the narrow R3 reduction below. At changing metric, asserting that these
are the same algorithm would restore the original review error.

Every trial has the following explicit stage table. Geometry rebuild tags
are unique across attempts/branches; a rejected tag is never recycled into a
cache hit. The accepted geometry handle remains unchanged until commit.
Attempt-only epoch allocation may advance while real EntityId/source/RNG
allocators remain at the accepted snapshot. A restart invalidates transient
plans and rebuilds under new tags from the checkpointed accepted geometry.


| Object/time | Assignments and obligations |
| --- | --- |
| Snapshot t0, accepted epoch epoch0 | Copy immutable IDs/lifts, Q0/a0/phi0/o0/K0, Vref/Bmean, source/RNG/allocator state and ledgers. Construct frozen linear generator plan and trial dt. No source events inside the hydro trial. |
| Old evaluation g0/epoch0 | Build/verify C0, Cdot0, Vdot0/cvel0, all primitive/face maps and exact transposes. Recover B0 and primitives from Q0/V0. Build Aux0 at o0 and tau=0, raw r0/chi0, old face solutions/exchanges, e0 and S11 RHS. |
| Geometry endpoint t1/epoch1 | Advance the lifted generators along the declared path and rebuild actual g1 before any endpoint density/fit. Build fresh V1,c1,faces,C1,Cdot1 and cvel1 using that same plan. epoch1 is distinct even when counts match; reuse requires a metric certificate, never just size. |
| Predictor state at c1/epoch1 | Apply predictor S14 to Q0, S11 to a0; phi_star=phi0+dt*chi0, ostar from S9, Kstar from S8. Bstar=Bmean+C1 astar. BT_P is separately saved. Recover positive Qstar/V1/Bstar; reject without reset. |
| Endpoint reevaluation epoch1 | Fit/limit using astar and Qstar, build fresh Auxstar at ostar with tau=0; recompute primitives, phi source, donor decisions, EMF/pressure blend, signal bounds, raw rstar/chi_star and estar. Generator velocity remains the frozen plan, not newly selected next-step motion. |
| Corrector at c1/epoch1 | From Q0/a0 apply corrector S14 and S12; phi1=phi0+dt*(chi0+chi_star)/2; o1 from S9; K1 from S8. Recover B1=Bmean+C1 a1, save BT_H separately and all transfers/residuals. |
| Final closure/accept epoch1 | Recover final Q1/V1/B1, refresh final A/primitive fits and Aux1 at o1 for closure/CFL. Enforce all positivity, metric, mean, residual and comparison gates; no additional projection/pressure reset. Commit selected complete trial branch atomically, including ledgers. |

Any retry rebuilds every dt-dependent trajectory/geometry/operator/origin/
ledger object from the accepted snapshot. Attempt counters can advance;
accepted step/source/ID/RNG counters cannot. No projection correction, origin
translation or wall impulse survives a rejected branch. Source events then
follow the shared first-order split at the accepted endpoint, invalidate
matching force/state caches, preserve fixed Vref and do not replay a
preceding hydro increment for newborn particles. That source split is not
made second order by this hydro/MHD design.

## 8. Order argument, reduction and limitations

### 8.1 Fixed-metric R3 and the old moving defect

**D:** fixed C,V and target policy imply Cdot=Vdot=0. Put
`P(r,t)=r+L(t-Cr)`. Then zP=dt L(t0-Cr0) and
`zH=zP/2+dt L(tstar-Crstar)/2`. S11–S12 give exactly

```text
astar=a0+dt P(r0,t0);
a1=a0+dt/2 [P(r0,t0)+P(rstar,tstar)].                         (S15)
```

This is review R3 in real arithmetic, without double screening. The old
finite-endpoint solve also reduces to S15 under those assumptions and
BT=B0+the corresponding integrated t. Finite-iteration differences and RHS
absolute cutoff remain measured floors. This is an algebraic comparison
using matching arrays, not proof that a 3D geometry reproduces frozen 2.5D.

**D, why the old moving proposal is withdrawn:** let `r` be a smooth raw
rate, `lambda=Vdot/V`, `e=t-Cdot a-Cr`, `f=r+L e`, and
`k=Cdot a+C f`. Expanding the old raw-trapezoid **finite-endpoint** projection
with endpoint L1 gives, relative to Heun for f, an additional second-order
coefficient

```text
dt^2/2 * [Ldot + L Cdot L - L lambda (I-C L)] e.                (S16)
```

The quotient-volume term follows from
`BT_H=B0+dt*t0+dt^2*(tdot+lambda*(k-t))/2+O(dt^3)`;
raw trapezoid uses the predicted projected state. Smooth GCL changes its
corrector only at O(dt^3), so it cannot generally cancel S16.
For a simple changing scalar matrix C=1+t*c, V=1, r=t_target=0,
kappa_proj=1 and a0=1, the old endpoint map gives
`1-c*dt/2+c^2*dt^2/2+...`; the effective ODE gives
`(1+c*dt)^(-1/2)=1-c*dt/2+3c^2*dt^2/8+...`.
This algebraic counterexample is not an executed curl experiment, but rules
out a universal moving-metric second-order inference. It supplements the
review's centroid-speed counterexample rather than hiding it behind M1's guard.

### 8.2 Conditional smooth-topology proof for the revised sequence

**D:** fix a finite spatial mesh and a prescribed smooth linear generator
trajectory over the interval. Assume positive states/volumes, fixed image/
stencil/fit ranks and limiter/donor/root branches, bounded derivatives and
condition numbers of all maps, and exact solves for this argument. Actual
geometry g(t), C(t), centroid c(t) and cvel(t) are differentiable. Define the
nonautonomous finite-dimensional ODE

```text
Qdot= -D_g(area F_Q(g,Y));
adot= r(g,Y,cvel)+L_g [t(g,Y)-Cdot_g a-C_g r(g,Y,cvel)];
phidot=chi(g,Y); odot=m(g,Y); Kdot=Vref cross Bmean.            (S17)
```

Every quantity on the right has been defined above; r/chi are raw and g
is prescribed, not an independently integrated substitute volume. For an
exact point field at the moving centroid,

```text
a(c1,t1)=a(c0,t0)+dt*(partial_t a+cvel0 dot grad a)_0
                  +O(dt^2).                                  (S18)
```

Using w_generator instead would miss
`dt*(cvel0-w_generator) dot grad a`, possibly O(dt) at fixed h. S4/S6
include that leading shift and S5 differentiates the fit at its **moving**
centroid locations. The predictor S11 equals a0+dt*f_a,0; its endpoint
closure is at c1 with error O(dt^2), not at a generator-advected proxy point.
Q predictor's shared-sweep correction is O(dt^2), phi/origin/K predictors
have O(dt^2) or zero defect. Thus the full predicted state differs from
the exact ODE endpoint by O(dt^2). Differentiable endpoint face/donor/Aux
maps and their spatial derivatives then differ by O(dt^2) at fixed h.
All endpoint rates, including the coupled correction L1 estar, are evaluated
on this predicted state. S12 is exactly the trapezoid of f_a, not the old
endpoint map. The Q corrector's GCL term is O(dt^3) on a smooth well-conditioned
graph, so the complete update is

```text
Y1=Y0+dt F0+dt^2/2*(F_t+F_Y F)_0+O(dt^3).                    (S19)
```

This gives local O(dt^3), hence global O(dt^2) for this **finite-dimensional
smooth prescribed-path method**, under the stated stability/Lipschitz
assumptions. There is no reliance on averaging w_generator and what.
Limited donors/stencils must be recomputed at g1; freezing old ones is
another method and invalidates the argument. No independent final-field
projection is permitted after S12. S19 is offered for independent review,
not a claim of already reviewed/proven stability or physical convergence.

**U, floors and remaining scope:** at fixed h the physical error contains
raw spatial reconstruction, Cdot/commutator, centroid-point versus volume-
average, screened-target and solver errors. A raw target defect e need not
vanish at fixed h; screening retains physical mismatch. Spatial consistency
requires these defects decrease under h refinement and is not proved by
S19. Solve error is bounded by the active inverse norm times the **absolute**
normal residual; a fixed relative tolerance creates a temporal floor. Operator
finite-difference and physical exact-solution comparisons must expose that
floor, not fit orders through it. Non-smooth root/limiter/topology/rank
switches, pressure-minimum/Riemann/fallback switches, auxiliary-brick
Jacobian crossings, badly conditioned graph weights and constrained wall
maps are outside the Taylor argument. A shared Hermite field is C1; that
alone does not make its Jacobian differentiable across bricks. S-ORDER
metadata must freeze/expose all these branch histories. They have separate refinement/rejection gates.

State-dependent generator motion selected solely from old fluid velocity
and frozen through the step is not established as a second-order coupled
trajectory law. This revision does not claim otherwise. Before the final
merger, register a state-dependent predictor/regularization/trajectory policy
and extend the augmented-state argument to its generator equations and
source split. Its nonuniform deforming/boost/restart gates remain mandatory;
prescribed-path success cannot waive them or replace the requested goal.

## 9. Operational, limited topology/exchange controller

**E: `adaptive-exchange-substeps-v1`, small reference scope.** This is not
certified event bracketing. For each attempted macro interval DeltaT and
its frozen linear trajectory, privately integrate branches with uniform
`2^ell`, `2^(ell+1)` and `2^(ell+2)` physical Heun/GCL/covariant increments,
starting at ell=8. Each microstep rebuilds both actual stage geometries,
all maps, raw face exchanges and origin/cleaning states; it is not a geometry
movie with one macro physical exchange. Generate positions from the same
macro lift/time, not repeated minimum-image increments. No sources/IDs are
committed inside a branch. Record per-spacetime key integrated gas/target
exchanges, GCL correction, geometry, root and limiter decisions.

For comparison only, represent each microstep's physical face-rate ledger
by the line `X_f(t)=X_f,0+(t-t_a)*(X_f,star-X_f,0)/h` on its interval;
its integral equals that branch's trapezoid. Integrate this line over every
finer comparison bin, splitting at coarse microstep boundaries. A key absent
from the coarse endpoint union has X=0 there. Do not invent a coarse value
for a short-lived face. Keep this physical ledger separate from GCL and
source ledgers; allocate a GCL correction by its own explicitly tagged
microstep interval if a binned correction diagnostic is requested.

Freeze positive scales from the common initial catalog: `M0=sum m`,
`c0` a declared positive initial characteristic speed,
`E0=sum abs(Q_E)`, `Vtot` domain volume and `Bscale>0` the initial amplitude
scale. For gas components use `(M0,M0*c0,M0*c0,M0*c0,E0)`; integrated
induction uses `Vtot*Bscale`. Final differences require both global
sum-absolute normalized component norms and a cell maximum normalized by
that component scale times `V1_i/Vtot`. B uses volume-weighted L1 and max
normalized by Bscale. These scales are not recomputed during refinement.
For both successive branch pairs require all of:

- Componentwise final Q and volume-weighted B differences, normalized by
  predeclared fixed nonzero initial state/field scales, <=tau_top=1e-4.
- Sum-absolute differences of integrated **physical** gas and induction
  exchanges by canonical `(owners,image,physical-time-bin)` key, normalized
  by the corresponding fixed global integrated-state scales, <=1e-4.
  Use the finer branch's time bins; an absent coarse face contributes zero.
  Report physical and GCL exchange differences separately, so a volume
  repair cannot mask a missed physical transfer.
- Every branch passes actual geometry/positive closure, normal residual,
  unchanged mean, budget and component-compatibility gates. Reject any
  unsupported predicate, crossing generator or operator failure.

If both comparisons pass, select/commit only the finest complete branch.
Otherwise increment ell and repeat from the **same** immutable snapshot.
The minimum permitted interval is
`max(DeltaT*2^-20,128*epsilon*max(abs(t0),DeltaT,T_unit))`;
no comparison may require a finer interval. T_unit is the declared code
time unit, recorded before execution. Failure at this limit is typed
`TopologyExchangeUnresolved` (or the specific geometry/auxiliary error),
with all comparison histories. Reject the macro attempt; a permitted outer
dt retry restarts unchanged data. Exhaustion is a required campaign failure,
not acceptance of the last finite state. Resource exhaustion is also not a pass.
This intentionally expensive first reference is initially <=512 real cells;
scalable/event-certified alternatives require separate review.

**Limits:** endpoint union, these samples and even two small differences can
alias a shorter-lived face. This controller certifies no event-duration
lower bound and cannot justify a general claim that every positive face was
visited. Its scope must be supported by the independent resolved fixtures
below, including deliberately adversarial timing. A controller false pass
against that reference blocks adoption. No small-area cutoff deletes a
positive face. Global volume/GCL/constant-state success alone is insufficient.
Production merger event coverage remains a blocking numerical prerequisite,
not solved by the word “adaptive”.

### 9.1 Concrete transient-face fixture inputs

**D/E, not executed:** use local scale R=1/20 and centre c=(1/2,1/2,1/2)
in a unit box; r=c+R*p. Four fixed local generators are

```text
A=(1,0,0), B=(-3/5,4/5,0), C=(-3/5,-4/5,0), D=(0,0,-1).
E(s)=(3*s/2-1/2,0,1-epsilon_e), 0<=s<=1;
epsilon_e=2^-9, 2^-16 and separately 2^-28;
w_E=(3R/(2 DeltaT),0,0), all other w=0.                       (S20)
```

Use DeltaT=1 for geometry-only and .1 for the physical-exchange case.
Give A–E namespace1 counters1–5, and 64 fixed background generators
`((i+1/2)/4,(j+1/2)/4,(k+1/2)/4)`, i,j,k=0..3, counters
`100+i+4*j+16*k`. All are explicit formula-defined inputs, not generated
randomly. None of those background points is inside the core unit sphere
after rescaling. Core ABCD lies on that sphere and the DE segment crosses
the interior of ABC. The bipyramid's in-sphere sign changes when

```text
s_-=1/3-(2/3)*sqrt(2 epsilon_e-epsilon_e^2),
s_+=1/3+(2/3)*sqrt(2 epsilon_e-epsilon_e^2).
```

The expected local Delaunay DE edge/Voronoi face exists between those roots
and is absent at both endpoints. For epsilon_e=2^-9, even all dyadic samples
through level3 miss it: at the nearest such sample3/8, abs(E_x)=1/16 exceeds
the sphere cross-section radius. These are manual geometric expectations,
not observed accepted backend results. Independent exact/rational predicate
and all-pairs clipped-polyhedron reference construction must confirm the
face, its clipped polygon and event intervals before fixture acceptance.
For epsilon_e=2^-28 the half-width is smaller than the nearest-sample
distance through dyadic level10, so all three initially proposed controller
branches can miss it. This is an explicit alias/false-pass challenge, not a
claim that the controller resolves it; a candidate false pass blocks adoption.
Include epsilon_e=2^-16/2^-28, coordinate permutations and event-centre shifts
`s_c=1/3 +/- 2^-10` by replacing x with `3(s-s_c)/2` as independent cases.

Pure geometry uses the bounded cuboid. A separate periodic physical case
uses the same 69 seeds, positive rho=`1+.1*sin(2pi*x)+.07*cos(2pi*y)
+.03*sin(2pi*z)`, p=1, gamma=5/3, v=(.2,-.1,.05), phi=0,
`a=1e-3*(sin(2pi*y)sin(2pi*z),sin(2pi*z)sin(2pi*x),
sin(2pi*x)sin(2pi*y))`, Bmean=(.2,.1,-.3). Recover discrete initial B/E
under the selected maps; the unchanged mean gate can reject this profile.
For an initial geometry/exchange-only comparator prescribe these analytic
smooth fields directly at each time, translate by v*t, and integrate the
passive conservative and induction flux through the actual moving face;
this isolates lost face exchange from coupled nonlinear state error.

### 9.2 Separate event coverage, exchange and reference verdicts (E1–E5)

**E, finding 6 disposition:** keep the <=512-cell controller, tau_top=1e-4,
minimum interval and all existing global physical-exchange<=1e-3, GCL<=1e-12,
uniform/budget<=1e-10, positivity/mean/solve gates. A tiny missed transient
can pass every global exchange comparison. Thus S-EVENT has **separate
coverage and exchange verdicts**, and a coverage miss rejects this geometry
challenge regardless of its global normalized error. It is not relabelled
as successful universal event detection.

**D/E, E1 face-presence predicate:** for the canonical DE pair
(CellIds namespace1 counters4/5, zero relative image in the core), the
independent all-pairs oracle intersects its bisector with all owner/image
distance half-spaces and the declared domain. Presence means this intersection
has affine dimension 2 and strictly positive area, certified by exact/algebraic
predicates or directed high-precision enclosures; a zero-area event face is
absent. No relative-to-largest-face area cutoff is permitted. The core
in-sphere sign `(3*(s-s_c)/2)^2-2*epsilon_e+epsilon_e^2<0` predicts the
event but is not a substitute for checking all competing half-spaces.
The oracle must establish the DE interval I=(tminus,tplus), absence outside,
and positive clipped polygons at the quarter/mid/three-quarter times of I.
Those special oracle/backend geometry queries are **not injected into the
controller's physical sample schedule**.

Record every actual geometry/flux stage time and full face key in each branch.
Coverage of this single fixture event requires at least one **actual
controller stage** certified inside I with positive DE area and a corresponding
DE face-rate entry. Wrong/stale keys or only zero-area endpoint observations
do not count. Report the sampled fraction of I and maximum unsampled gap too;
one visited time is presence coverage, not an exchange-accuracy certificate.
If no such sample exists, return fixture disposition
`EventCoverageMiss{DE,event,branch,sample_times}`.
An explicitly underresolved negative-control branch must be reported rejected;
that expected rejection checks the harness, not successful controller coverage.
If the controller's branch comparison says accept while coverage is false,
this is a **false coverage acceptance and failed candidate adoption case**.
The oracle detects it in the fixture; v1 has no such independent production
event certificate. The hand level<=12 alias inequality remains a challenge,
not an executed verdict or permission to skip that case.

**D/E, E2 noncancelling transient diagnostic:** besides the signed DE exchange
I_DE,k, retain for every gas/induction component k
`Jsurf_DE,k=integral_I integral_face |F_k(x,t)| dS dt` and
`Jface_DE,k=integral_I |integral_face F_k(x,t) dS| dt`.
Also retain strictly positive geometric exposure
`Jarea_DE=integral_I area_DE(t) dt`.
These distinguish cancellation over time from cancellation over a surface.
For the separately defined centroid rule below also record
`Jcent_DE,k=integral_I |Xcent_DE,k(t)| dt`.
The candidate's piecewise-linear ledger from section 9 is integrated in
absolute value **with splits at its zero crossings**, never absolute value
of a cancelling total. Absent DE gives zero, not an interpolated hidden face.
For candidate Jarea, integrate the piecewise-linear DE area ledger at the
same actual branch stage times, with zero area for an absent face; keep
this geometry diagnostic separate from the physical exchange ledger.
The reference must certify a positive mass-component Jcent and Jsurf for the
registered packet; otherwise this packet's exchange verdict is unresolved,
while Jarea/presence remain mandatory.

A new, separately labelled transient gate requires candidate Jcent mass error
plus reference uncertainty <=1% of the certified Jcent mass lower bound.
Jarea receives the same1% relative gate. Keep the signed and componentwise
Jsurf/Jface differences visible with absolute and relative uncertainties;
global component exchange error still must be <=1e-3 and decrease with halving.
This extra relative gate prevents a tiny global scale from excusing loss of
the whole DE event; it does not relax the existing global gate.

**D/E, E3 actual surface/time reference:** the analytic-exchange case
prescribes the section 9.1 smooth rho/A fields translated by v*t, p=1,
v=(.2,-.1,.05), B=Bmean+analytic curl(A), with actual gamma-law
E=p/(gamma-1)+rho*|v|²/2+|B|²/2 and fixed Vref=v.
These are prescribed quadrature inputs; the unbalanced momentum/energy
fields are not claimed to solve a coupled MHD evolution.
At every actual polygon point x, use S3's affine w_n(x), n fixed over that
polygon and Ptot=p+|B|²/2:
```text
Fmass = rho*(v_n-w_n);
Fmom  = rho*v*(v_n-w_n)+Ptot*n-Bn*B;
Fener = (E+Ptot)*v_n-Bn*(v dot B)-w_n*E;
F_T   = (v_n-w_n)*B-Bn*v+Bn*Vref.
Iref_f = integral_time integral_polygon F(x,t) dS dt.        (E3)
```
Use independently clipped, event-resolved geometry and actual surface
integration, including varying w_n; reusing a face-centre rate as this
reference is prohibited. The geometric sweep reference is the same
surface/time integral of w_n. Independent interval surface quadrature on
polygon triangles and time quadrature split at certified event brackets
must enclose the integral. Other polygon-combinatorics changes must also
be isolated or enclosed; the two core roots are not asserted to be every
event of the full69-cell tessellation. Begin with at least32 interior event subdivisions,
refine32/64/128 and triangle/time orders8/12/16, including outer intervals;
these are reference ladders, not observed convergence. Retain per-key/time-bin
ledgers, not just net totals. Use >=80 decimal digits, with predetermined
160/320-digit escalation; unresolved predicates/enclosures at the limit are
`EventReferenceUnresolved`, never zero exchanges.

**E4, explicitly separate temporal comparator:** in
`analytic-centroid-face-rule-v1` freeze
`Xcent_f(t)=area_f(t)*F_analytic(f_centroid(t),t,w_n(f_centroid(t)))`.
The independent event-resolved oracle time-integrates **this same rule**;
the candidate analytic branch evaluates it on its own sampled geometries
and uses its ordinary trapezoid. Their difference isolates temporal/event
error for that spatial face rule. Separately report the independent
Iref_surface minus Iref_centroid difference as spatial face-quadrature error.
At fixed69-cell geometry a surface-quadrature floor may itself fail1e-3;
that requires a separately reviewed spatial rule/refinement, never waiving
the surface gate. Neither comparator is a reference for all reconstruction/Riemann errors in
the coupled case. A small same-rule error cannot waive surface-reference
uncertainty, coverage or the later physical gate.

**E5, event-relative root/uncertainty contract:** isolate both analytic roots
with positive certified width lower bound
`Wlo=tplus_lo-tminus_hi>0`. Each root bracket must have width
<=min(1e-10*DeltaT,1e-8*Wlo). Propagate those root brackets through the
polygon/time integrals rather than treating roots as exact rounded floats.
Reference uncertainty per component must be <=1e-4 of its unchanged fixed
global exchange scale and <=10% of its positive Jsurf_DE,k
(the original transient ceiling, now explicitly noncancelling); for the new1% transient verdict tighten to
<=1e-3 of the certified positive Jcent mass and Jarea lower bounds.
The root-bracket contribution alone is <=1e-4 of those lower bounds.
If quadrature/precision cannot establish them, fail the reference rather
than count missing tiny events as zero. Thus fixed absolute1e-10*DeltaT
alone is explicitly insufficient.

Freeze/independently review literal arrays, root enclosures, quadrature
implementation and reducers before implementation/execution. Run the
69-seed geometry-only predicates first, then independent clipped/exchange
references, alias controls and coupled cases separately; an initial
mean/fit/pressure rejection in a coupled case proves no event coverage.
There is no new event certificate for arbitrary production trajectories.
A v1 false acceptance against these fixtures blocks its adoption; scalable
state-dependent event/motion design remains required for the merger.

## 10. Distinct errors, mean failure and magnetic/thermal transfers

At predictor and corrector report separately:

1. True normal residual for S11 / the shifted unknown in S12, with absolute
   and relative norms, RHS, inverse/conditioning estimate and iteration count.
2. Rate defect e_s and post-screening physical rate mismatch
   `t_s-(Cdot_s a_s+C_s f_a,s)=(I-C_s L_s)e_s` (up to solve error).
3. Finite target mismatch `BT_P-Bstar` or `BT_H-B1`: volume-weighted
   component/vector L1/RMS and max, absolute and initial-amplitude normalized.
   It is not the normal residual and need not vanish at a tight solve.
4. Actual volume mean `mu_s=sum V_s B_s/sum V_s` and target mean.
   Periodic desired mean is the **configured** Bmean; bounded desired mean
   is zero. Require <=1e-9 of fixed initial B_scale at initialization and
   accepted stages/final states, retaining the existing gate. Also report
   drift from the initial measured mean, without using it to retune Bmean.

**E, fail closed:** if this mean gate fails, reject the candidate/campaign.
No subtracting a measured mean from B, changing Bmean, shifting a boundary
trace, editing Q_E or distributing a projection residual is authorized.
The matrix may lack the necessary discrete left-nullspace; this is a method
failure needing a new constraint-compatible reconstruction/projection and
independent review. Dt halving alone may expose a fixed spatial mean floor.
No unexecuted assertion that this LS-reference candidate passes the mean gate
is made. [CURL_3D_MEAN_SPEC.md](CURL_3D_MEAN_SPEC.md) derives a separately named
periodic shared-face comparator with M*C_FV=0 algebraically, including its
actual Cdot. It changes B to a cell-average reconstruction and is neither
selected here nor accepted by this review; spatial/conditioning/switching/
partition and bounded gates remain independent.

**D, exact mean compatibility condition:** let
`M_g=(1^T V_g/Vtot) tensor I_xyz` and `G_g=M_g C_g`. Then

```text
mu-Bmean=G_g a;
d/dt(mu-Bmean)=(Mdot_g C_g+M_g Cdot_g)*a+G_g*f_a.             (S20a)
```

On a constant-volume periodic domain a compatible mean-preserving method
would require `G_g*a=0` initially and the second expression to vanish along
every accepted path. Neither local polynomial reproduction nor C*constant=0
establishes `M_g*C_g=0`. S10's screened least-squares objective imposes no
S20a constraint, so no preservation theorem is claimed. Shared finite-target
exchanges do conserve their **own** volume sum (including GCL correction)
under periodic incidence, but they need not equal the screened curl field.
This pinpoints the missing constraint rather than calling a normal residual
mean preservation. The bounded relative fit needs its actual constrained
version and U3 review as well. This revision chooses fail-closed measurement,
not an unreviewed augmented solve or mean repair.

For each predictor/corrector endpoint, by real owner define the following
**diagnostic path** with the same endpoint Q and actual V1:

```text
B_G=Bmean+C1*a0;
B_R=Bmean+C1*a_raw; B_P=Bmean+C1*(a_raw+z);
Delta EB_geom= V1*|B_G|^2/2 - V0*|B0|^2/2;
Delta EB_raw = V1*(|B_R|^2-|B_G|^2)/2;
Delta EB_proj= V1*(|B_P|^2-|B_R|^2)/2;
Delta Uthermal_proj=-Delta EB_proj.                            (S21)
```

Use a_raw=aP_raw/z=zP or aH_raw/z=zH, never the predictor as the corrector
base. Geometric channel includes the change of C and V at unchanged a;
optionally split it further in the declared order V0/C0 -> V1/C0 -> V1/C1.
This split is diagnostic, not a unique physical heating attribution. Its
sum telescopes exactly to endpoint magnetic-energy change. Store **cellwise,
signed sum and sum of absolute values** for every channel. At fixed endpoint
Q/V, raw/projection magnetic changes have opposite thermal changes.
Across the physical full update the exact budget is

```text
Delta Uthermal=Delta Q_E-Delta Kinetic
               -Delta EB_geom-Delta EB_raw-Delta EB_proj.      (S22)
```

Q_E is unchanged by either projection solve. These conversions are numerical
partition changes, not wall work, radiation or feedback. Check pressure and
density after predictor and final projection and every selected microstep;
reject without resetting p, E, B, a or phi. Initial weak-field and magnetic-
pressure-dominated cases must retain nonzero B and positive closure gates.
No exact magnetic-energy/entropy law follows from gas total-energy conservation.

For each channel compare against an independently refined reference at
matching physical cells/bins with recorded coverage. Report both
`abs(sum(channel_candidate-channel_ref))` and
`sum(abs(channel_candidate-channel_ref))`; require the registered finest
excess conversion <=1e-3 initial magnetic energy with decreasing error.
Do not let cancelling thermal transfers or an O(1) spatial/solve floor
pass because total Q_E has the unchanged <=1e-10 budget residual.

## 11. Prospective independent REANA packets and next review

All cases below are **unimplemented/unexecuted**. Freeze literal arrays,
case/reference hashes, uncertainty, norms and reducers and independently
review the corresponding equations before implementation. Every independent
resolution, dt, motion, target, root, boost and restart is a separate REANA
workflow with declared resources; ready cases run concurrently, no aggregate
CPU cap. Preserve M1 acceptance, immutable preflight/build and component
dependencies. No numerical tests or workflows are started by this revision.

| Packet / prerequisite | Required measurable comparison, additional to unchanged mesh/M1 gates | Initial envelope per case |
| --- | --- | --- |
| S-FRAME / static operators | Identical frozen M1 arrays, nonuniform/mean B, fixed and rigid with Vref_xy!=w_xy. S2 algebra <=1e-12 scaled; compatible target/rate/one-step differences <=1e-9 solve-normalized; report full-vector differences. Full3D geometry is a separate convergence case. | 1 thread,2 GiB,5 min |
| S-INC / S-FRAME | Fixed-metric rate-versus-S11/S12 increment R3 with kappa1 and deliberately nonzero screened mismatch; zero dt (zero correction <=1e-12 scaled), two-cell samples including an absent face and boundary provider. No double screening; state agreement <=1e-9, sample formulas <=1e-12. | 1 thread,2 GiB,5 min |
| S-CENTROID / geometry | Differentiate actual centroid using independent rebuilt differences, including finite cvel-w_generator as dt->0; S4 exact affine/rigid tests <=1e-10 scaled, smooth derivative error decreases at second order and <=1e-7 finest. Include M_f gamma contribution and oblique xyz permutations. | 1 thread,4 GiB,15 min |
| S-CDOT / static C and S-CENTROID | Analytic polynomial samples, constant modes, differentiate C with values held fixed using independent central differences; derivative error decreases at second order to its roundoff floor, <=1e-7 scaled finest. Cdot constant and adjoint/diagonal/baseline-image coalescing checks <=1e-12 scaled. Inspect inverse constants separately. | 1 thread,4 GiB,30 min |
| S-ORDER / S-CDOT,S-INC,O03 | Smooth nonconstant 3D analytic A: static physical and separately advected fields on nonrigid prescribed meshes; g fixed spatial resolution while halving dt at least4 times (e.g .01,.005,.0025,.00125,.000625), then N8/16/32 separately. Retain a fixed gauge, predictor defect O(dt^2) order>=1.8 and final temporal order>=1.8 above spatial/solve floors; physical B spatial order>=1.8 and existing amplitude gate. Compare old endpoint v1 as a labelled control, not an accepted fallback. | 2 threads,8 GiB,2 h |
| S-EVENT / S-CENTROID and geometry | E1–E5 separate mandatory coverage and exchange verdicts; S20 eps2^-9/2^-16/2^-28, centre shifts/permutations, geometry-only and analytic exchange then full coupled cases; independent root-resolved oracle. Keep GCL<=1e-12, uniform state/budgets<=1e-10, smooth correction orders; finest physical exchange error<=1e-3 and decreasing with halving. A DE coverage miss rejects even if global error is small; Jcent mass/Jarea relative error<=1% with <=.1% reference uncertainty and event-width-relative root bounds. Deliberately underresolved false coverage acceptances and minimum-interval rejection are explicit negative controls. | geometry 1 thread,4 GiB,1 h; physical/reference 4 threads,16 GiB,12 h, calibration before enlargement |
| S-PARTITION / accepted smooth steps | Geometry-only, raw-only, projection path diagnostics S21/S22; weak B and magnetic beta=.01 with positive pressure, fixed/rigid/deforming controls. True normal residual<=1e-9 alone is insufficient; mean<=1e-9 B_scale, budgets<=1e-10, physical B order>=1.8, finest signed/sum-absolute excess transfers<=1e-3 initial EB with predeclared reference uncertainty. | 2 threads,8 GiB,2 h |
| S-AUX-REPLAY / O03 | Tricubic C1/xyz derivatives, constant K shifts, root switches4/2/1, origin winding, failed trial replay and restart; no second origin translation; constant K physical B difference<=1e-12 scaled. Pure-gradient gauge perturbations require refinement, no assumed C G=0. | 1 thread,4 GiB,30 min |
| S-BOOST / accepted relevant smooth/coupled cases | Joint gas/generator/Vref/auxiliary-origin and physical-box boosts (2,-1,.5),(10,7,-3), transform p/E and wall work. Keep field/state boost<=1e-8, mean<=1e-9, gas budgets<=1e-10 and existing loop limits. All tests retain nonzero field where relevant. | corresponding unboosted envelope |

The new independent review must disposition S4–S5's geometric derivative,
the changed S10–S12 objective and conditional S19 order argument, explicit
topology-controller scope/alias risk, and the mean/partition failure policy
against these **new hashes**. Findings1–6 are not retroactively marked
approved in the old report. Static geometry/operator slices remain separately
gated after M1; the disputed moving coupling waits for this review and its
registered prerequisites. State-dependent trajectories and bounded U1–U4
remain explicit dependencies of the final deforming magnetized merger.
