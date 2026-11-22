# Periodic shared-face curl and its moving mean identity

2026-11-22. **Source/design comparator only: unimplemented, unexecuted,
unadopted and awaiting independent review.** This responds to finding 7 of
[the frozen revised-stage review](MOVING_MHD_STAGE_DESIGN_REVIEW.md) at
70ad33e. Keep `periodic-ls-quadratic-point-curl-v1` as the named reference.
The new `periodic-shared-face-quadratic-curl-v1` can supply the missing
periodic **mean left-nullspace algebra**, by changing the magnetic operator
and sampling. It supplies no spatial, temporal, topology, wall or merger
acceptance. M1 scientific source 2bdcea0 and its gates remain unchanged.

**Source-only follow-up to [CURL_EVENT_DESIGN_REVIEW](CURL_EVENT_DESIGN_REVIEW.md)
at 5cdf51d, exact subject 3b9719c:** its supported F1–F9 algebra and scoped
conditional estimates are retained without equation changes. It does not
approve these new bytes or supply numerical evidence.

| Review finding | Narrow disposition here / linked normative contract | Remaining prerequisite |
| --- | --- | --- |
| 1 | Stage E0 defines exact symbolic versus serialized dyadic targets; E2a defines reducers/zero channels; section2/S10 and API metadata carry point-A/average-B sampling. | Literal bytes, converted-input roots/enclosures/references and actual geometry/field evidence. |
| 2 | Conditional prescribed-path spatial-ODE Heun scope is unchanged; no state-dependent trajectory solution is claimed. | Full motion/source/bounded/gravity/merger gates. |
| 3 | F1–F3, common H, intercept/baseline, charts/self-images and separate metric closure remain unchanged. | CF-MAP/MEAN numerical controls. |
| 4 | F4 transpose, coalesced diagonal, active/zero-column and independent-divergence rules remain unchanged. | Actual spectra, physical target/conditioning and field convergence. |
| 5 | F5–F9 derivatives/mean identities remain unchanged; S5 includes PQR scaling/weight derivatives. | Independent Cdot/transported-sample/switch controls. |
| 6 | Analytic norm sampling is explicit for both selectors, with common physical Q and no energy/pressure repair. | Spatial/temporal/partition/boost and beta=.01 evidence. |
| 7 | Mesh PQR1–PQR2 now fixes periodic column scaling and kappa1(R) decisions; no bounded Frobenius substitution. | Literal independent matrices/condition references and derivative/no-switch evidence. |
| 8 | E0/E1–E5 retain mandatory actual-stage coverage and all error/root/GCL gates; symbolic S20 roots are not numerical certificates. | Actual dyadic-input event certificates, separate surface/same-rule references and alias comparisons. |
| 9 | Deterministic jitter/coordinate/source classifications are retained; seeds are not claimed statistically independent. Historical reviewed identities remain separate. | Frozen arrays and all scientific acceptance evidence. |

P means checked primary literature; D means derivation here; E means a new
engineering proposal. Complete pinned sources/inputs/output identity are in
[curl_3d_mean_sources.json](curl_3d_mean_sources.json). P26 v1
[pp.8–10, Eqs.51–67](https://arxiv.org/pdf/2609.35989v1) supplies point-A fits
and the reference curl; p.10 §4.2.3 discusses a **different** edge/Delaunay
integral construction; p.16 footnote12 states periodic mean conservation
without proving a left identity for our LS map. P09 v3
[p.17, Eqs.32–34](https://arxiv.org/pdf/0901.4107v3) supplies the bisector
speed/volume context. These full PDFs were retained and equation pages
inspected. F1–F9 and the metric-support comparator below are independent
mathematics/engineering, not published P26/AREPO algorithms or copied code.

## 1. One face value, charts and exact algebra

Use the existing typed IDs, actual polygon geometry, outward-left incidence
D and actual tessellated volumes from [MESH_3D_SPEC](MESH_3D_SPEC.md).
Let V3=diag(V_i) tensor I3, a=(Ax_i,Ay_i,Az_i) in cell-major order,
J=1_N tensor I3, and [S]x b=S cross b. In a canonical face's **one common
lifted chart**, define S_f=area_f*n_f pointing left to right-image,
centroid f and central covariance Sigma_f=average_face[(x-f)(x-f)^T].
P_L and P_R,image are the owners' unlimited quadratic point-sample fits,
with a free fitted intercept, the existing full-rank/conditioning policy,
and no A/B limiter.
Both topological and metric owner fits use the periodic PQR1–PQR2 numerical
policy in mesh section5.1; a bounded QR/Frobenius profile is not substituted.
Fix equal owner weights, not an unstated upwind value:

```text
Avg_f P_i = P_i(f) + (1/2) Hess(P_i):Sigma_f;
Abar_f = H_f a = (Avg_f P_L + Avg_f P_R,image)/2;
C_FV = V3^-1 (D tensor I3) blockdiag_f([S_f]x) H;
(C_FV a)_i = (1/V_i) sum_f D_if (S_f cross Abar_f).       (F1)
```

The Hessian contraction is componentwise in **physical xyz**, including
both off-diagonal entries of the symmetric tensor. Polynomial face moments
are integrated over the actual polygon, not a bounding disk or point rule.
The same H_f, S_f and Abar_f serve both incidences; independent owner face
evaluations must not be committed as two face values. The component
divergence theorem gives integral_cell curl(A)=integral_boundary n cross A;
it fixes F1's sign. For a periodic fluctuation potential,

```text
M = (1^T diag(V_i)/Vtot) tensor I3;
M C_FV = (1/Vtot)(1^T D tensor I3) blockdiag([S]x) H = 0;
sum_i V_i (Bmean+C_FV a)_i = Vtot Bmean.                 (F2)
```

This holds for **every** a, not specially cancelling initial fields. It
needs paired incidence, not measured/subtracted mean, and does not assert
the recovered field equals the conservative target. Floating evaluation
adds ordinary division/accumulation/geometry roundoff: retain normalized
and absolute identity errors and deterministic reductions; no bitwise-zero
claim for arbitrary scales. Never repair the output B or retune Bmean.

Periodic A here means the stored fluctuation a. Add configured Bmean
analytically and keep the stage's spatially constant gauge K separate from
fits, C/Cdot, distortion and limiter differences. Owner/image observations
have the same a value, without an affine magnetic-background A lift. Translate
P_R,image(x)=P_R(x-L*k) and all composed stencil centroid images consistently;
axes/components are unchanged by an image translation. Wrapping with a
checkpointed winding must not create a physical derivative jump. Face/image
keys remain distinct even for the same owner pair.

A self-image face has two metric incidences in different owner charts but
one shared H_f; its coalesced D column is zero and its curl exchange cancels
before an in-place owner update. Keep metric incidences for S4 centroid
moments: their different face lifts cannot be deleted there. Images/ghosts
are not new EntityIds. Do not extend F2 to a nonperiodic wall by dropping
the unpaired boundary term; that needs a separate trace/operator review.

## 2. Constants, field sampling, consistency and limitations

**D:** fit reproduction gives H_f J=I3. Constant-potential annihilation is
then a distinct, local metric identity:

```text
C_FV J b = V_i^-1 (sum_f D_if S_f) cross b = 0.           (F3)
```

Check sum D S=0 using actual polygons independently of F2. A left mean
identity alone does not prove F3. Restore the free intercept/baseline before
assembling H: if an owner face evaluation is implemented as
b_i+h_i(S_i a-1*b_i), with b_i=E_b a an actual owner sample, its full row is
`h_i S_i+(I-h_i 1)E_b`. This baseline term, central sample dependency and all
repeated-image columns must be included before transposes, derivatives and
diagonal squares. Constant K is excluded even when F3 is exact algebra,
since large offsets magnify finite closure errors. Do not delete the
intercept because derivative rows of the LS reference annihilate constants.

**D, conditional second-order consistency:** suppose cell diameters ~h,
V_i>=c h^3, bounded surface area/h^2 and neighbour count, uniformly bounded
scaled full-rank fit/evaluation maps, finite-radius O(h) stencils, and A
has bounded third spatial derivatives on all lifted supports. A quadratic
point fit then has O(h^3) value error throughout each face. Its exact face
average has the same error; area summation/volume division gives
`C_FV a - average_cell curl(A)=O(h^2)`. Global quadratic A is reproduced
exactly in a valid chart, since its curl is affine and its volume average
equals its value at the **volume** centroid. Cubic A gives an O(h^2) field
error in general; its analytic cell-average curl includes the actual cell
second moment. These bounds require uniform inverse constants; a nominal
rank pass/ten observations or a tiny-volume sliver is insufficient.

For the comparator, B_i is a **cell-average approximation**, while a_i
remains a centroid point sample. Use this B in the fluid's cell-average
primitive state and its separately linear-fitted/limited reconstruction;
do not treat it as a new Hessian B reconstruction or change raw transport
curvature=None silently. Point B(c_i) and average B differ by O(h^2), not
identically. Reference comparisons must integrate analytic curl over the
actual cell for C_FV, and use the centroid value for raw LS; show both
representations rather than calling their arithmetic difference an error.
Stage `SamplingContractId=a-point-b-cell-average-v1` carries this into S1/S10,
operator APIs, checkpoints, reference reducers and every stage/final norm;
the raw-LS reference uses its separately named point/FV-surrogate tuple.
S10 is the conservative cell-average Reynolds target for the **completed
numerical** face flux, not an exact point material derivative at c_i.
The raw A rate remains a centroid point rate with S4 cvel; no extra transport
term is added to the reviewed equations. Q errors compare actual extensive
cell integrals; analytic B errors use actual volume averages for this map,
while a/phi errors use centroid samples in the same declared gauge.

Resolved magnetic energy remains V_i*|B_i|^2/2. For an exact average the
unrepresented variance is
`V_i*(average |B|^2-|average B|^2)/2>=0`, generally O(V_i h^2).
Record this spatial representation term separately from S21's geometry,
raw-rate and projection transfers. Initialize common physical Q by volume
integration of the analytic total energy when comparing operators; do not
reset pressure separately to hide their representation difference. All
initial/stage/final positive-closure gates apply, including beta=.01 cases.
F2 makes the constant-mean cross term in global resolved EB vanish:
`EB=Vtot*|Bmean|^2/2+a^T C_FV^T V3 C_FV a/2`. It gives no physical energy,
entropy or small magnetic-to-thermal-transfer theorem for the stage update.

## 3. Exact transpose, active diagonal and independent divergences

With the complete real-owner H, Euclidean transpose and volume adjoint are

```text
C_FV^T = H^T blockdiag(-[S_f]x) (D^T tensor I3) V3^-1;
C_FV^T V3 b = H^T blockdiag(-[S_f]x)(D^T tensor I3)b;
Dproj_kk = sum_i V_i |(C_FV)_ik|^2.                      (F4)
```

Coalesce every real-owner image/baseline contribution to C_ik **before
squaring**; summing separate squares is another diagonal. Use the stage's
screening1, zero-column/fixed-zero-correction rule and 1e-14 active scaling
rejection, not a new gauge pin. Hproj=C^T V3 C+Dproj is SPD on positive
active columns; this does not imply C has physical rank. Store null/singular
spectra of volume-scaled C for both operators, constant modes, sampled
gradient modes, small periodic/self-image configurations and checkerboard/
other extra kernels. A one-cell torus cannot resolve a nonconstant magnetic
fluctuation merely because a zero C has a valid mean identity. Tight normal
residuals still do not prove physical target or partition accuracy.

F1 is **not** an edge-cochain curl whose divergence is a boundary-of-boundary
identity. Raw neighbouring-cell LS div(B), shared mean/limited-face
divergences, returned-face divergence and curl-gradient contamination can
all be nonzero. Retain their named diagnostics and decreasing physical
errors. The raw LS same-Hessian div(curl) identity is a reference diagnostic,
not an identity for independently reconstructed C_FV B gradients. Gauge
perturbations grad chi do not inherit an exact C_FV*G=0 assertion.

## 4. Smooth-topology Cdot with real samples held fixed

**D/E:** use the same smooth prescribed trajectory/chart and S3–S5 centroid/
fit derivatives as the stage. Hold real a_j values fixed while differentiating
the operator. With a fixed face/vertex/image label region,

```text
Cdot_FV = -Lambda C_FV
          + V3^-1 (D tensor I3)
            {blockdiag([Sdot]x) H+blockdiag([S]x) Hdot};
Lambda=diag(Vdot_i/V_i) tensor I3.                       (F5)
```

Vdot uses actual tessellated volumes/Reynolds normal speeds, not an RK volume.
For ordered polygon vertices x_l in the canonical chart,

```text
S=(1/2) sum_l x_l cross x_(l+1);
Sdot=(1/2) sum_l [xdot_l cross x_(l+1)+x_l cross xdot_(l+1)]. (F6)
```

Translate to a nearby anchor for stable sums and differentiate that anchor
too. A nondegenerate Voronoi vertex solves T x=b, with bisector rows
d=r_j,image-r_i and b=(|r_j,image|^2-|r_i|^2)/2; hence
`T xdot=bdot-Tdot x`. Retain the defining plane keys, condition checks and
other-plane residuals. An unresolved multiple vertex/rank change is not a
smooth derivative. A=|S|, Adot=n dot Sdot and ndot=(I-nn^T)Sdot/A.

For actual f/Sigma derivatives use a fixed combinatorial triangle fan of
the convex face. In triangle tau with vertices x0,x1,x2, u=x1-x0,v=x2-x0,
area q=|u cross v|/2, g=(x0+x1+x2)/3, z=x0+x1+x2,

```text
qdot=(1/2)n dot(udot cross v+u cross vdot);
R_tau=(z z^T+sum_l x_l x_l^T)/12;
A=sum q; I1=sum q*g; I2=sum q*R_tau;
f=I1/A; Sigma=I2/A-f f^T;
fdot=I1dot/A-f*Adot/A;
Sigmadot=I2dot/A-(I2/A)*Adot/A-fdot*f^T-f*fdot^T.          (F7)
```

Differentiate all products in I1/I2, including each vertex. Use stable
translated moments, positive oriented triangles and fixed vertex **keys**,
not a coordinate-sort choice that can change within the interval. Degenerate
zero-area faces are event limits, not places to divide by area. Scalar
normal speed is affine over the face as S3, not polygon-centroid tangential
speed substituted for it.

Write the owner's physical polynomial in d=x-c_i,image as
P_i=beta0_i+g_i dot d+Hess_i:(dd^T)/2. Its face average derivative at fixed
real a is

```text
d=f-c_i,image; ddot=fdot-cvel_i,image;
d(Avg P_i)/dt = beta0dot+gdot dot d+g dot ddot
               +(1/2) Hessdot:(dd^T+Sigma)
               +(Hess*d) dot ddot+(1/2)Hess:Sigmadot;
Hdot_f a = (d Avg P_L/dt+d Avg P_R,image/dt)/2.             (F8)
```

S5 differentiates the actual weighted LS map with the residual term, hdot,
row weights and column normalization/unscaling. F8 includes the new moving
face evaluation and surface covariance terms. Image integers are fixed
on this chart region; cvel_j,image includes the same lift as c_j,image.
Common boosts cancel from all relative displacements and derivatives.
Transported analytic samples are a separate chain rule
`d(C a)/dt=Cdot a+C adot`; including them inside Cdot double counts transport.
Do not cache old Cdot after geometry/trajectory/support changes.

Differentiating F2 verifies the moving compatibility identity:

```text
Mdot C_FV + M Cdot_FV = 0,    M C_FV=0.                   (F9)
```

Thus for any f_a from the existing covariant S10 ODE,
`e=t-Cdot a-C r`, `adot=r+L e`, the configured mean derivative is zero
in exact arithmetic on a constant-volume periodic domain. The target's
own conservative mean is compatible as well: sum V*t=-sum Vdot*B.
Use **this** C/Cdot, changed L and cell-average B together at every stage;
using LS Cdot or an old frozen H/S derivative breaks the equation. S11/S12
remain conditional Heun for the newly defined spatial ODE, not a proof
that this comparator approximates ideal MHD. Even after topology rebuilds,
each snapshot can satisfy F2 while B/energy jump; F9 is a smooth-region
identity, not an event jump rule. Source events still need the shared
atomic endpoint/epoch rules and run-frozen Vref/Bmean/K conventions.

## 5. Stencil jumps and a separately named metric-support comparison

Existing quadratic fits use topological double stencils and 1/|d| weights.
A new zero-area face can add a finite-weight observation/two-ring route,
changing a fit abruptly. Its direct S_f H_f term may vanish at birth, but
other positive faces' H can jump. Endpoint F2 does not bound that jump or
certify a hidden transient. Even continuous fits need bounded inverse maps
as faces become small. Keep this issue in S-EVENT/partition, not concealed
by the mean identity.

**E: `periodic-metric-quadratic-support-v1` is an additional unadopted fit
comparator**, not a change to the retained P26-style reference. For target i
set R_i=4 V_i^(1/3), include the central real sample and **all** periodic
centroid images with q=|c_j,image-c_i|^2/R_i^2<1, independent of adjacency.
Fix objective weight w=(1-q)^4 for q<1, zero otherwise; central w=1.
Enumerate complete support image bounds, including multiple self/image
layers, sorted by (CellId,image); cap4096 rows then typed rejection, never
nearest-subset truncation. Apply the same scaled P2/free intercept and
the mesh section5.1 **periodic-cpqr-kappa1-v1** PQR1–PQR2 policy: weighted
column2-norm scaling, original monomial/key ordering, complete permutation/
unscaling restoration, largest-QR-pivot relative1e-10 threshold and explicit
triangular1-norm inverse-product criterion<=1e8. This is not a spectral
condition number or the bounded QR/Frobenius profile. Failed rank/conditioning rejects; there is
no automatic radius or lower-degree fallback. The face still averages the
two owner fits as F1; no target-face adjacency enters their sample support.

The weight as a function of q is C3 across its cutoff. In a smooth geometry
with uniformly invertible weighted Gram map, treating entering rows as zero
rows gives a C3 least-squares map despite a changed stored row list. Derive
its time derivative through W/Wdot stationarity (or equivalent differentiated
QR); do not differentiate a hard nearest-neighbour selection or omit weight
derivatives. This is conditional support smoothness, not a theorem through
all geometric degeneracies. Real rank/threshold changes, geometry moments,
raw-rate donor/limiter/auxiliary switches and state-dependent generator motion
remain separate. A paired LS point-curl evaluation with this support is a
diagnostic to separate support effects from face averaging, not a silently
adopted third method.
Equivalent accepted QR sign/pivot storage branches leave the full-rank
represented map unchanged; differentiating those discrete choices does not
define Cdot. Differentiate normalization/unscaling and W through S5, including
its residual term, or use the equivalent unnormalized stationarity map.

## 6. Coordinates and reflection conventions

For an orthogonal R, A,K,v,w,u,Vref and outward S are polar vectors;
B,Bmean are axial: B'=det(R) R B. Hence
`(R S) cross(R A)=det(R) R(S cross A)` gives the correct F1 transform.
For a reflection, reverse polygon winding so its cross-product area vector
remains the **outward** R S; blindly preserving winding would produce the
wrong area orientation. Translate all owner charts/image integers and
permute widths/keys consistently. First backend mesh controls use signed
axis permutations of the orthorhombic torus; arbitrary rotated period bases
are only local algebra controls until separately supported. Orthogonal
component transformations apply to C/Cdot/transpose as well. Never compare
B as a polar vector in an odd coordinate permutation.

## 7. Small prospective REANA registry and disposition

All cases below are unimplemented/unexecuted, need M1, new independent review,
literal generator/source/reference hashes and immutable preflight **before**
implementation/execution. Each resolution/dt/support/operator/seed/boost/
restart/reference is its own workflow with declared resources, no aggregate
cap and no nested native pools. Reuse geometry G01–G04 before differential
maps. The following new gates add to existing gates; none weakens M1/M2.

Use N=8/16/32 regular and genuinely xyz-jittered periodic unit-cube grids.
Freeze a literal deterministic jitter packet with separate xyz hash tags
in [-.15/N,.15/N], three recorded seeds and no extrusion; its arrays and
hash are prerequisites, not supplied/executed here. Compare both supports
on identical geometry without selecting only favourable LS-mean fields.
Smooth fixed-path motion is the stage's nonrigid sinusoidal velocity at
the common initial generators, held fixed over the whole comparison path;
never change the path when dt changes. Certify a smooth no-switch window
independently before freezing the S-ORDER temporal packet; event controls
are separate. All branch histories remain visible. A proposed reproducible jitter definition
is the engineering mix `jitter-mix64-v1` on
seed xor i xor (j<<21) xor (k<<42) xor axis*C, axis=0/1/2,
C=0x9e3779b97f4a7c15, all arithmetic modulo2^64: add C, apply
(z xor (z>>30))*0xbf58476d1ce4e5b9, then
(z xor (z>>27))*0x94d049bb133111eb, then z xor (z>>31).
Set q=(z>>11)*2^-53 and displacement .3*(q-.5)/N per axis,
seeds1/2/3, around (i+.5,j+.5,k+.5)/N. This is an explicit engineering
packet generator definition, not executed arrays or an imported code library.
Retain every registered seed; no retrying jitter seeds until a case passes.
These are deterministic arrays, not certified statistically independent
realizations: seed xor i can permute x-index hash inputs on these grids.

| Family / measurements | Gates retained or additional proposed gate | Initial envelope per case |
| --- | --- | --- |
| CF-MAP: explicit dense H/C versus matrix-free action, transpose, coalesced diagonal, self/parallel images, baseline/intercept/K, constant geometry closure, orientation/odd permutation | Relative action/adjoint/diagonal/constant identities<=1e-12; closure as G01<=1e-12; all active/zero/near-column decisions recorded. Full singular spectra of V3^(1/2)C, not rank inferred from fit rank. | 1 thread,4 GiB,15 min |
| CF-SPACE: constant, quadratic/cubic localized polynomials and Fourier A on irregular actual cells; both operators and both support rules | C_FV vs analytic **cell-average** curl, LS vs centroid curl. Finest-three physical L1 order>=1.8, finest normalized L1<=.1; reference spatial uncertainty<=1e-5 Bscale. Nonzero independent divergences finite and RMS decreasing; shared global face sum<=1e-12. | 2 threads,8 GiB,30 min |
| CF-MEAN: all dense-map columns, generic nonzero/random integer sample arrays, Fourier and strong/weak fields, exact-volume changing snapshots | F2/F9 algebra defects<=1e-12 relative operator scale; actual configured mean<=1e-9 Bscale at initialization/every stage/final, plus raw absolute sum/roundoff bound. No mean subtraction or retuned Bmean. LS failure is evidence, not an array-selection excuse. | 1 thread,4 GiB,15 min |
| CF-CDOT: fixed real samples and separately analytic moving samples on fixed smooth topology; rigid/self-image, rotating oblique polygon moments and boosts | Independent rebuilt central differences: second-order decrease to roundoff, finest<=1e-7 scaled, oracle uncertainty<=1e-9; constant/adjoint/mean-derivative identities<=1e-12. Hold sample values fixed for operator derivative. | 1 thread,4 GiB,30 min |
| CF-TIME/BOOST/PARTITION: existing S-ORDER/FRAME/INC/AUX/BOOST/PARTITION with explicit C_FV selector, fixed h then h ladder; static/advected nonzero fields, beta=.01 positive closure, common physical Q and geometric/raw/projection channels | At least4 dt halvings, predictor/final temporal order>=1.8 above solve/spatial floors; independently resolved same spatial ODE reference uncertainty<=1e-10 fixed scale. Physical spatial order>=1.8; solve1e-11 iterative/1e-9 true, mean1e-9, gas budgets1e-10, boost1e-8 and excess signed/sum-absolute conversion<=1e-3 initial EB unchanged. No pressure/energy resets. | 2 threads,8 GiB,2 h |
| CF-SWITCH: same S-EVENT E1–E5 roots/coverage/DE noncancelling exchanges; C/H/field jumps and thermal conversion on both sides; metric-cutoff/rank changes separate | All E1–E5 and S21/S22 gates retained; measure one-sided operator jump against event distance/refinement. Mean cancellation never waives coverage, conditioning or partition. No universal event certificate asserted. | geometry1 thread,4 GiB,1 h; physical/reference4 threads,16 GiB,12 h |

For the polynomial family a nonconstant global polynomial is **not periodic**.
Local polynomial reproduction may use explicit analytic image values in an
isolated algebra chart, but that is not a torus field/mean test. Whole-mesh
quadratic/cubic tests use A=eta*P_d, d=2/3, centred at (.5,.5,.5), eta=1
for r<=.2 and eta=0 for r>=.35 with a C-infinity transition, periodically
extended. Freeze eta via b(s)=exp(-1/s) for s>0, zero otherwise,
eta=b(1-s)/(b(s)+b(1-s)), s=(r^2-.2^2)/(.35^2-.2^2), with explicit endpoint
branches. Evaluate exact polynomial reproduction only on supports wholly
inside the plateau; absent eligible supports are unresolved, not a pass.
Use all component monomials through degree3 and the existing O02 Fourier
potential/mean-field families. Independent clipped-cell volume quadrature
and face moments define their references. Never invent a polynomial image
lift to evade the periodic A/Bmean split in a physical run.

**Disposition:** the new comparator makes the intended periodic mean
invariant algebraically true, including moving metrics and screening, if
implemented exactly as F1–F9. Its accuracy, conditioning, spectrum, Cdot,
stencil-switch behaviour and energy partition remain open numerical
prerequisites. First review the map/moment/transpose/derivative design,
then after M1 implement the static map slice and independent REANA controls.
Only a later explicit decision could adopt it. State-dependent deforming
motion, bounded trace/operators, isolated gravity and active source gates
remain necessary for the full DM/old/new-star/multiphase MHD merger.
