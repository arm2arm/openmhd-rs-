# State-dependent generator motion: augmented-stage proposal

2026-11-22. **Unimplemented engineering proposal, not an adopted profile or
an acceptance result.** M1 remains frozen at `2bdcea0` and unaccepted. This
note supplies the missing state-dependent smooth-stage construction for the
full deforming three-dimensional galaxy goal. It neither changes the
prescribed-linear profile in [the moving-stage contract](MOVING_MHD_STAGE_SPEC.md)
nor resolves its topology, bounded-operator, gravity or source prerequisites.
No new numerical execution was performed. Exact source/context identities
are in [the inventory](state_dependent_mesh_motion_sources.json).

The proposal is `augmented-heun-centroid-regularized-v1`. All statements of
order below concern a smooth finite-dimensional spatial ODE, with the
specified operators and exact solves. They are manual derivations requiring
independent review and subsequent REANA evidence, not physical MHD accuracy
claims. In particular, section 6 leaves a concrete event-integration blocker.

## 1. Source boundary and state

[Springel 2009 v3](https://arxiv.org/abs/0901.4107v3), printed p.16 Eq.31,
allows generator velocities tied to cell fluid velocity. Printed p.17
Eqs.32–34 gives the bisector face speed and instantaneous volume rate.
Printed p.22 Eq.63 adds a thresholded, sound-speed-limited displacement
toward the cell centroid; that page also discusses an explicitly
timestep-dependent alternative. Its printed p.25 discussion distinguishes
fluid-following velocity from the boost-invariant corrective velocity.
These primary pages were read; pp.17/22 were freshly rendered and inspected.
They do **not** prescribe this note's smooth regularizer, magnetic signal
scale, wall taper, augmented stages, Cdot projection or event controller.
Those are proposed engineering choices and derivations here. No AREPO
equivalence is inferred.

Use the existing typed real-owner IDs, positive actual Voronoi volumes and
SI-derived code units with `mu0_code=1`. During one hydro trial no cells,
particles or source births are inserted or deleted. Let

```text
Z=(r,Q,a,phi,o,K),   g=Geometry(r,t),   B=Bmean+C_g*a.
```

`r` denotes lifted generator positions; `a` denotes potential point samples
at the actual volume centroids of g. For the shared-face selector B is a
cell-average approximation, while the retained LS selector is a point
reconstruction. Neither is silently interchanged. `Q` is the conservative
gas catalogue, not a collection of primitives at generator positions.
The named curl, raw-rate, EOS, auxiliary and projection profiles are part
of Z's configuration. Use `bulk-full-vector-vref-v1` and kappa=1. Require
an explicit curl selector; the retained LS and unadopted shared-face choices
have separate evidence, with no silent selector default or runtime switch.
`Vref` stays constant for the run. The wall-relative
profile keeps its separate `Bmean=K=0` convention.

## 2. Explicit state-dependent velocity law

For each current stage, first recover positive `rho,p,v,B` from the matching
Q, actual volume and selected curl. Use the present gamma-law thermodynamic
closure; a new EOS must separately define and validate this signal scale.
Set, in the generator's continuous cell chart,

```text
h_i=V_i^(1/3),   d_i=c_i-r_i,
c_sig,i=sqrt(gamma*p_i/rho_i + dot(B_i,B_i)/rho_i),
u_reg,i=alpha*c_sig,i*d_i/sqrt(h_i^2+dot(d_i,d_i)),
W_i=v_i+u_reg,i,                  alpha=1/4.                  (SM1)
```

This c_sig is the positive scalar square-root sum of acoustic and Alfvén
speeds, not a face-normal fast-wave eigenvalue or a replacement CFL formula.
With positive p/rho, SM1 has no norm singularity at d=0. Its corrective
speed is strictly less than alpha*c_sig. The correction is a velocity;
there is no separate Lloyd position shift, volume reset, or hidden remap.
It need not vanish for a merely approximately centroidal cell. The explicit
`alpha=0` control is a different recorded policy; production failure cannot
switch to it. SM1's alpha and smooth saturation are not P09 parameters.

For periodic geometry, c and r use the same checked lift, not unrelated
wrapped coordinates. Under a constant joint boost d, h and c_sig are
unchanged and W gains that boost. This is an algebraic property of SM1,
not proof of Galilean invariance of the whole discrete MHD step.

For the separate translating conducting cuboid with prescribed constant
wall velocity Wbox, define distances dminus/dplus from a generator to the
two current walls of coordinate axis b, and

```text
chi(q)=0                         q<=0,
       10*q^3-15*q^4+6*q^5       0<q<1,
       1                         q>=1;
theta_i,b=chi(dminus/(2*h_i))*chi(dplus/(2*h_i)),
W_i,b=Wbox_b+theta_i,b*((v_i-Wbox)_b+u_reg,i,b).               (SM2)
```

The taper is C2 at its joins and equals one away from both wall layers.
It affects mesh motion only. The physical wall Riemann solve still uses
Wbox and its actual wall-normal speed, not W_i; the wall has no gas mass
flux. Rebuild h and all taper factors at every stage. A positive generator
distance is required at every tested position. Continuous vanishing of the
normal speed at a wall does not prove an explicit trial cannot cross it;
out-of-domain predictor/final/dense positions reject the trial. This note
provides no accepted bounded Cdot, trace, reflection or wall-domain result.

SM1/SM2 contain no explicit dt. Changing the integration step therefore does
not redefine the intended generator ODE, unlike a correction proportional
to d/dt. Neither policy ensures shape/rank/conditioning or prevents all
collisions. Existing geometry rejection, topology and physical gates remain.

## 3. Acyclic stage evaluation and three distinct geometries

At any stage `(t,r,Y)` with `Y=(Q,a,phi,o,K)`, evaluate in this order:

1. Build and validate actual geometry g; build C, recover B and primitives.
2. Evaluate W from SM1 or SM2. This requires no Cdot or centroid velocity.
3. From **that** W and g obtain face normal speeds, Vdot and centroid cvel
   using S3/S4. Form `Cdot=D_r C_g[W]+partial_t C_g` holding real samples a
   fixed, with any physical-wall motion included once. The explicit partial
   term vanishes for a fixed periodic domain. It is not C applied to adot.
4. Build matching auxiliary fields and raw rates rA, chi_phi, origin and
   face fluxes. Form the rate defect and screened tangent map

```text
tB=-V^-1*D*(area*F_T)-diag(Vdot/V)*B,
e=tB-Cdot*a-C*rA,
L=(C^T*V*C+kappa*Dproj)^-1*C^T*V,
fA=rA+L*e.                                                  (SM3)
```

The existing target policy, active-column tests, no explicit matrix inverse,
iterative/true residual requirements and all diagnostics remain. The
dependence of W on Q/a/r is included by reevaluating the stage; no derivative
of W is numerically approximated in production. Cdot differentiates the
geometry along its instantaneous W, and does not include an extra Wdot
term. Such terms enter derivatives of the augmented RHS when proving order.

For one trial interval of duration h (distinct from cell lengths h_i), all sums
are by persistent real ID. Use three independently validated geometries:

```text
rP=r0+h*W0;                       gP=Geometry(rP,t0+h),
VP=V(gP),
aP=a0+h*rA0+zP,                 H0*zP=h*C0^T*V0*e0,
phiP=phi0+h*chi_phi0,
oP=o0+h*m0,                      KP=K0+h*Kdot.               (SM4)
```

`m` is the existing periodic volume-mean origin rate, not W or a mass mean;
the bounded profile instead uses the prescribed wall-chart origin. Obtain
QP with the predictor GCL correction in section 4 using VP, then recover
BP and positive primitives on gP. Evaluate **WP and all P rates** afresh
from `(gP,QP,aP,phiP,oP,KP)` by the sequence above. The old frozen W0 is
not the P-stage velocity. Then

```text
rH=r0+h*(W0+WP)/2;               gH=Geometry(rH,t0+h),
VH=V(gH),
aH_raw=a0+h*(rA0+rAP)/2,
HP*vH=h/2*CP^T*VP*eP,
aH=aH_raw+zP/2+vH,
phiH=phi0+h*(chi_phi0+chi_phiP)/2,
oH=o0+h*(m0+mP)/2,               KH=K0+h*Kdot.                (SM5)
```

Here H0/HP are the normal operators from SM3 at the old/**predicted**
geometries. The second correction uses CP, VP, CdotP[WP], rAP and eP
together. It is the P tangent solve; gH does not replace gP inside it.
After QH from section 4, recover final `BH=Bmean+CH*aH` on actual gH.
Do not run another finite-endpoint projection or thermal-pressure repair.

In general `rP!=rH`, `VP!=VH`, `CP!=CH`, and `cP!=cH`. Reusing gP as the
final geometry is not this algorithm. For the scalar manual example
`r'=r,r0=1`, SM4 gives `rP=1+h`, while SM5 gives `rH=1+h+h^2/2`;
freezing the old velocity loses the quadratic term. This is not a numerical
probe or a physical trajectory example.

Caches include unique old/P/H geometry epochs, attempt/branch and velocity
law identities, actual W digest, curl/fit/boundary policy, state/auxiliary
origin and map generations. CdotP cannot be reused with W0, and an equal
cell count proves no metric equality. Build final auxiliary/primitive maps
from gH/QH/aH/oH for closure and next-step CFL; do not use the P cache.
Retries discard every trial trajectory, correction and ledger while leaving
accepted state, source/RNG counters and EntityId allocator unchanged.

## 4. Conservative exchanges and actual-volume GCL

Use S14's equal-and-opposite graph signs and component compatibility checks.
There is still one shared interior face exchange. With `s=area*w_normal`,
and stage outward physical rates XQ and XB,

```text
SP=h*s0,                       RP=VP-V0-D*SP,
solve D*deltaSP=RP,
EP_Q=h*XQ0-UbarP*deltaSP,       QP=Q0-D*EP_Q,
EP_B=h*XB0-BbarP*deltaSP,       BT_P=(V0*B0-D*EP_B)/VP;

SH=h*(s0+sP)/2,                RH=VH-V0-D*SH,
solve D*deltaSH=RH,
EH_Q=h*(XQ0+XQP)/2-UbarH*deltaSH,
QH=Q0-D*EH_Q,
EH_B=h*(XB0+XBP)/2-BbarH*deltaSH,
BT_H=(V0*B0-D*EH_B)/VH.                                      (SM6)
```

The predictor samples use U0=Q0/V0 and B0. The four corrector owner samples
use **UP=QP/VP and BP**, not QP/VH or CH*aP. They exist for every real
owner even if a stage face is absent. Keep the S13 pair/four-sample means.
Use the old/P positive face-key union and weights in S14; a face existing
only in gH has no old/P rate or invented correction edge. Component
incompatibility or bad graph conditioning rejects; there is no volume-defect
mean subtraction. This graph choice does not solve event coverage.

BT_P and BT_H are finite-volume magnetic targets/diagnostics, not projection
destinations. For a uniform conservative state and compatible graph, SM6
exactly changes Q in proportion to the actual VP/VH, up to the declared
geometry/solve errors. That algebra follows constant-state physical flux
closure and the signed sweep correction; it does not establish nonuniform
physical accuracy. Record separate physical and GCL exchanges.

At the final accepted candidate, report the existing magnetic transfer
sequence at fixed samples: `(g0,a0)->(gH,a0)->(gH,aH_raw)->(gH,aH)`.
The intermediate gP closure is separately recorded. Conservative total Q_E
changes only by its face/source/wall ledger, so each recovered magnetic
change has the opposite thermal partition change. No mean-field adjustment,
mean subtraction or positivity floor is authorized. Both predicted and
corrected beta=.01 cases must satisfy the parent positivity gates.

## 5. Conditional augmented-state order and physical scope

On a fixed smooth branch define

```text
rdot=W(t,r,Y),
Ydot=F(t,r,Y;W(t,r,Y)),
```

where F contains SM3 and the matching conservative, cleaning and auxiliary
rates. Assume positive closure, fixed real catalogue/image/stencil/rank and
raw branches, bounded map derivatives/inverses, smooth walls, and exact
solves for the argument. For this finite-dimensional problem SM4 gives
`ZP=Z0+h*Faug,0+O(h^2)`. The predictor GCL term has size O(h^2), since
`VP-V0-h*Vdot0=O(h^2)` and its graph inverse is bounded. Consequently

```text
WP=W0+h*(W_t+W_r*W0+W_Y*F0)+O(h^2),
rH=r0+h*W0+h^2/2*(W_t+W_r*W0+W_Y*F0)+O(h^3).               (SM7)
```

For the same reason `RH=VH-V0-h*(Vdot0+VdotP)/2=O(h^3)`; the corrector
GCL perturbation is O(h^3), rather than the predictor's O(h^2). SM5 is
exactly the trapezoid of the raw-plus-tangent rates at old/P states. Thus
the complete smooth augmented step has local O(h^3), conditional global
O(h^2). No freezing of W's state dependence is used in this derivation.

This is not a proof of useful ideal-MHD spatial consistency, stable pressure,
small screened target error, rank/condition preservation, low magnetic
divergence, or successful switch/topology handling. The existing spatial,
mean, partition, independent divergence, boost, conditioning and residual
gates remain mandatory. Inexact solves and reconstructed Cdot produce
observable floors; a fitted order through a floor is not accepted evidence.

Gravity kicks and active source updates follow the shared accepted-endpoint
split. Recompute W from the actual post-kick/source state and invalidate its
cache before the next hydro trial. New stars receive no earlier kick. Vref
does not change. This does not promote the currently first-order combined
gravity/source split to second order or accept gas-gravity work accounting.

## 6. Event-path blocker and required independent evidence

One natural continuous extension of an accepted numerical generator step is

```text
r_dense(theta)=r0+h*(theta*W0+theta^2*(WP-W0)/2),  0<=theta<=1,
dr_dense/dt=W0+theta*(WP-W0).                                 (SM8)
```

It reaches rH, not rP. The face at the Euler predictor rP is therefore
generally **not** the actual dense-path face at t0+h. An arbitrarily narrow
topology event can distinguish these O(h^2)-separated geometries. Presence
at the P-stage cannot alone prove physical-path coverage. Conversely, a
dense-path oracle query is not a candidate flux contribution. SM8 is a
declared proposed continuous extension, not an event certificate or an exact
solution of the coupled generator ODE.

The existing frozen-linear macro-path controller cannot be reused by merely
renaming its trajectory object. Each refined state-dependent branch has
its own evolving W and path; it must retain those paths and distinguish
physical exchange, GCL and predictor-only face appearances. Before topology
adoption, freeze a separately reviewed path-aware quadrature/controller
which defines how an actual covered face contributes to accepted physical
exchange. No such new quadrature is selected or accepted here. An oracle
time injected into the candidate, or a coverage flag without an accepted
rate contribution, is insufficient.

Compare finite-dimensional branch Q/a/r states by persistent ID, preserving
their distinct endpoint geometries and volumes. A difference in recovered B
then includes trajectory/operator error; it is not a same-fixed-geometry
quadrature error. Retain generator/centroid/volume discrepancies alongside
the parent Q/B and canonical face/time ledgers. Independent prescribed-path
controls still isolate missed exchange from coupled-trajectory error. No
inter-branch A interpolation or conservative remap is silently introduced.

The required sequence is:

| Future case family | Distinct evidence required, after M1/review/fixture/preflight |
| --- | --- |
| SM-LAW | Exact scalar/vector controls for SM1/SM2, d=0, taper joins, weak/nonzero B, three-axis lifts, dimensions and joint boosts; alpha=0 and 1/4 are separately labelled. No independent geometry accuracy is inferred. |
| SM-STAGE | Small full-rank no-switch 3D stencil; four or more dt halvings against an independently resolved **same augmented ODE**, including rP/rH, Q, point a, selected B sampling and auxiliary origins. Order>=1.8 above exposed spatial/solve floors; generator finest error<=1e-5 of fixed initial domain length and reference uncertainty<=1e-10 of that length. Parent field/state gates also apply. |
| SM-GCL | Uniform positive full-vector MHD on an irregular genuinely deforming mesh, alpha=1/4; both VP and VH independently rebuilt. Retain GCL<=1e-12 and state/budget<=1e-10 parent gates, graph component errors and both centroid-rate identities. A rigid-only pass is insufficient. |
| SM-PATH | Literal P-only versus dense-path transient-face negative controls, then independently enclosed actual coupled trajectories, positive-area coverage and accepted exchange. Freeze rounded inputs, path/reducer meaning and uncertainty before any execution. Preserve E1–E5 and all parent absolute/relative gates. This family is design-blocked until the controller/quadrature choice above is reviewed. |
| SM-PHYSICS | Nonuniform full-3D nonzero-B wave/advection/boost/partition tests and nonlinear topology cases using actual W, including all three magnetic divergences. Retain the parent >=1.8 spatial, 1e-8 boost, 1e-10 budget and 1e-3 excess-partition gates. Same-ODE temporal evidence cannot replace them. |
| SM-BOUND/SOURCE | First bounded U1–U4 and moving-wall/operator evidence, then gravity work, active births/ISM and domain/ambient controls. Restart/retry parity includes policy, W/path/epoch and all component/source ledgers. No full merger acceptance before the existing isolated-galaxy/encounter gates. |

Each independent ready case will have its own concurrent REANA workflow,
with explicit CPU threads/memory and no aggregate resource cap. Numerical
implementation, literal fixture execution and all rows remain pending. The
entire live-DM/gas/existing/new-star magnetized multiphase merger remains the
required end state; this smooth-stage proposal is only one prerequisite.

For SM-STAGE the fixed length is the initial minimum domain side length
Lmin0. The generator error is `max_i norm2(r_i-r_ref,i)/Lmin0` on matching
continuous lifts at every registered history sample, not wrapped distances
or a mean that can hide a bad cell. The reference uncertainty uses the same
norm. Literal sample times, no-switch enclosures and independent reference
construction still require preregistration; the table is not an executed
or frozen numerical fixture packet.
