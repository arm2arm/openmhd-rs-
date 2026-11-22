# Independent bounded-MHD and analytic geometry-input design review

2026-11-22. **Disposition: retain the selected finite conducting-box physical
profile; revise the discrete wall-pressure and operator contracts before
implementation.** U1–U4 remain open. The seven geometry fixtures' stated
geometric values are supported by the manual derivations below; this is
permission to use them as prospective reference inputs after harness review,
not an executed geometry gate or M2d acceptance.

Reviewed checkout `23ab6187d75859572b5a718d62e2d943b5bd74cf` selects
`box-conducting-slip-relative-v1`. The subject
[BOUNDARY_MHD_SPEC.md](BOUNDARY_MHD_SPEC.md) is 50,194 bytes, SHA256
`c08be57d86c4a3a8de9b8dd36a74cfc695103661f4169d64e30c021bfef4b7a0`.
Line numbers below identify those reviewed bytes. The geometry packet is
the design frozen in `606d8e7`; its JSON is 12,665 bytes, SHA256
`69fd92fc2009df207d076441527161825eb50ae911a2ec2a8e398d687306f288`.
Exact source, contract, fixture and code identities are recorded in
[boundary_mhd_review_sources.json](boundary_mhd_review_sources.json).

This independent review owns only these two new review files. It changes no
authored boundary/mesh/shared/gravity/fixture/ISM file, no earlier review,
scientific Rust/Cargo, script, benchmark or M1 evidence. No local or REANA
numerical probe, test, evolution, geometry backend or reducer was executed;
no workflow/service control, commit, push or delegation occurred. Hashing,
document parsing, source reading and PDF inspection are the only executable
checks. Numerical thresholds/experiments below are prospective engineering
gates, not measurements or paper values. M1 physical acceptance remains the
coordinator's pending gate; the inspected code matches frozen `2bdcea0`.

## Primary-source scope

Complete primary texts were available, with hashes rechecked against the
author's source inventory:

| Identity | Exact reviewed source and locators | Scope used |
| --- | --- | --- |
| P26 | [Springel, Mayer & Pakmor, arXiv:2609.35989v1](https://arxiv.org/pdf/2609.35989v1), 37 pages; printed pp.6–7 Eqs.38–42; pp.8–13 Eqs.51–76; pp.15–16 Eqs.80–92 | Gauge/cleaning signs and periodic reference context; not a bounded LS/adjoint recipe. |
| ABDG | [Amrouche et al., author-hosted 43-page preprint](https://dauge.pages.math.cnrs.fr/publis/ABDG_VPot.pdf), PDF p.22 Theorem 3.17 Eqs.3.21–3.22; p.23 Proposition 3.18 Eqs.3.23–3.24 | Relative Coulomb potential and topology-qualified harmonic kernel; not evolution or discrete stability. |
| S24 | [Secchi, arXiv:2411.09352v1](https://arxiv.org/pdf/2411.09352v1), 8 pages; p.2 Eq.1.4; pp.4–6 Eqs.2.9–2.10,3.1 and reflection proof | Slip/unthreaded branch and the compatibility limits of smooth reflection. The official version page identifies v1 submitted 14 November 2024; its source header is dated 15 November. v2 exists and is not silently substituted. |
| DC23 | [Datta & Crews, MHD BC](https://faculty.washington.edu/shumlak/WARPX/html/mhd_bc.pdf), 11 pages, dated 7 December 2023; p.1 Eqs.1–6; p.2 Eqs.7–10 | Initially unthreaded ideal conductor; resistive tangential-current conditions are a separate model. |

P26 p.6, ABDG p.22 and S24 p.2 equation pages were visually inspected in
this review, in addition to extracted full text and relevant surrounding
sections. The independent calculations labelled R below are manual
derivations, not sourced numerical results. No external code was copied.
Author-hosted PDFs without version identifiers are pinned by bytes/hash;
there is no full-text access gap for the cited anchors.

## Numbered findings and required disposition

### 1. Supported physical choice, with classical compatibility qualifications

**Locators:** boundary §§3–5, Eqs.B1–B8, lines 107–247; ABDG Theorem 3.17
and Proposition 3.18; S24 Eq.1.4; DC23 Eqs.5–6.

In the constant-velocity box chart, `v_r,n=Bn=0` makes
`(v_r cross B)_t=0`. With `A_t=phi=0` and `u_r,n=0`, the tangential trace of
the A equation remains zero. The normal field is the surface curl of that
tangential A trace. For a smooth solution phi's homogeneous Dirichlet trace
and tangent sampling velocity imply `div(A)|wall=0`; on a flat patch this
is `partial_n A_n=0`. Differentiation gives the stated forced compatibility
`Delta(phi)|wall=-div(v_r cross B-grad(u_r dot A))|wall`. These are
compatibility consequences, not freely selectable extra incoming data.
Do not impose both phi Dirichlet and normal-Neumann data, or require odd
smooth reflection of every forced thermodynamic/cleaning field.

For a cuboid, connected boundary and no handles remove the relative
curl-and-div harmonic modes in the cited static theorem. Curl alone still
has gradient modes. At an edge A lies in two incompatible normal subspaces,
so its continuous trace is zero; B and v_r can be along the edge. At a
three-wall corner their continuous B/v_r traces are zero too. These point
statements need smooth compatible traces; they are not shock regularity
theorems and introduce no finite-area edge flux.

For divergence-free continuum B with Bn=0,
`int B_i dV = int_wall x_i*Bn dS = 0`. The no-independent-mean-field choice
is therefore correct. The compact-support B2 potential supplies a nonzero
initial field without wall flux, but not force equilibrium. The residual
gauge law B7 follows by substituting `A'=A+grad(chi)` and
`phi'=phi+D_u_r chi/Dt`; arbitrary gauge resets are not symmetries of the
fixed cleaning system. The static theorem does not give uniqueness of a
non-Coulomb dynamical state.

**Resolution/gates:** retain this physical profile and these qualifications.
Use B-FIT/B-MMS/B-GAUGE for face/edge/corner traces and interior convergence;
retain the proposed trace `1e-10` and gauge-contamination gates. Do not call
them executed or infer a cuboid-gravity well-posedness theorem from S24's
mixed quarter-space result. Gravity startup compatibility is finding 8.

### 2. Blocking wall-flux implementation: Pi_star is not defined by the existing API

**Locators:** boundary §6 B10–B11, lines 285–305, B-WALL line 662;
frozen `mhd-core/src/lib.rs:164–179,280–329,522–535,576–635`.

The mirror construction correctly cancels Bn and normal mass flow by
symmetry. Bn=0 is handled by a collapsed rotational fan in HLLD
(`323–329`), and does not always cause fallback or division by Bn.
However, `FaceFlux` returns the conservative flux and completion v/B,
not a thermal star pressure. Its completion state can be changed *after*
selecting the conservative flux (`594–613`); it is not a general pressure
oracle. In particular the numerical normal momentum flux need not equal
positive thermal-plus-magnetic pressure of the returned HLL state.

There is a concrete symbolic counterexample already inside B-WALL. Set
wall-frame `rho=p=1`, `gamma=5/3`, normal incident velocity `a=-1`,
`v_t=(3/10,-2/5)`, `B_t=(1/5,3/10)`, Bn=0. Then

```text
R1: c_f = sqrt(539/300),  P_t=213/200,
    s_L=-(1+c_f), s_R=1+c_f, s_M=0,
    P_HLLD_star = P_t-c_f < 0.
```

The frozen HLLD rejects this nonpositive pressure (`305–306`) and falls
back to HLL. Substituting into its flux formula gives

```text
R2: n dot F_p,HLL = rho*a^2 + P_t + (1+c_f)*rho*a
                 = P_t-c_f < 0.
```

This is compatible with an admissible HLL intermediate state. With
`q=c_f/(1+c_f)`, its density is q, tangential momentum `q*v_t`, field
`q*B_t`, and its internal energy density is

```text
R3: [400*c_f^2 + 200*c_f - 213] / [200*(1+c_f)^2] > 0.
```

Thus the proposed zero mass/tangential-momentum/energy/induction and positive
state checks can all pass while the wall's purported "compressive pressure"
is negative. Conversely, the signal-weighted completion averages the mirror
states: its thermal pressure would be `4/3`, giving another stress, unrelated
to R2 and even larger than initial pressure in this receding-flow example.
These are source substitutions and inequalities, **not an executed probe**.

**Resolution:** specify the wall pressure result and its admissibility/API.
Do not silently identify `n dot FaceFlux.fluid_momentum` with a physical
star pressure, or recover it from an A completion state. A possible separate
boundary solver is the symmetric one-dimensional perpendicular-MHD wall
Riemann problem: tangential velocity and `B_t/rho` are constant across its
normal waves; solve the positive rarefaction/shock wall state with v_n=0.
For a rarefaction, use the isentropic wave integral with
`P(rho)=K*rho^gamma + |B_t,0|^2*(rho/rho0)^2/2`; for a shock also impose the
total gas-plus-transverse-field Hugoniot energy relation. Define vacuum/
no-admissible-positive-state behavior explicitly rather than flooring Pi.
This is a candidate resolution requiring its own derivation/reference,
not an already accepted replacement for M1. If instead retaining numerical
traction, name that model and review its rarefaction/error behavior; it
cannot be described as automatically positive physical star pressure.

**REANA:** freeze all signed-velocity B-WALL cases, especially this exact
receding case, plus strong-field and gas-only limits. Compare raw flux,
completion state, selected Pi and an independent wall-Riemann reference.
Keep the `1e-12` symmetry/boost gates and add Pi admissibility, stationary
`Pi=p+B_t^2/2`, shock/rarefaction accuracy and the exact R1–R3 source branch.
No coupled wall run should proceed with the pressure rule ambiguous.

### 3. Blocking U2: observation weights and bounded affine maps need completion

**Locators:** boundary §7.1 lines 357–388; mesh §5.1 lines 420–444;
frozen `projected_rate.rs:371–405` and its periodic baseline subtraction.

The boundary stencil includes the central real cell and two-ring samples.
The inherited quadratic objective uses `1/|d|` and explicitly rejects zero
displacement; that weight is undefined at the newly included central row.
The inherited linear face-area weight also does not assign a weight to a
central cell or non-face two-ring observation. The objective therefore is
not yet an exact reproducible matrix. Free intercept means a fitted unknown,
not interpolation through the central observation. Including the central
row is a separate engineering change from P26's neighbour-only fit.

For a fully specified positive row-weight matrix W, observation matrix M,
constraints `L*c=g`, particular lift c_g and nullspace Z, the correct map is

```text
R4: K = Z*(W^(1/2)*M*Z)^dagger*W^(1/2)
    c = c_g + K*(q-M*c_g).
```

It is linear for the present homogeneous traces; it is affine for prescribed
inhomogeneous data. Scalar derivative evaluations and vector curl blocks
must retain the full real-data dependency. A synthetic outside evaluation
is not an independent degree of freedom or a new rank observation.

Unlike periodic derivative rows, a bounded Dirichlet gradient generally
has `G*1 != 0`; a constant nonzero scalar data vector has to bend to zero
at the wall. Constant vector A likewise is not a permitted global gauge.
If a baseline q_b is subtracted for cancellation control, the exact identity
is `K*q = K*(q-q_b*1) + q_b*K*1`. Dropping the last term as in the periodic
constant-annihilating pattern changes the bounded operator and transpose.

**Resolution:** enumerate every row, its weight, target-centre/face
displacement, patch set, component coupling and scalar/vector data layout.
Either exclude the central row under the existing 1/r policy, or freeze a
named bounded weight (for example the prospective dimensionless
`w_j=[eta^2+|d_j/h|^2]^-1/2`, eta>0 configured) including its central value.
Define linear two-ring weights too. Do not present a new weight as a paper
value. Assemble C, G, C^T, G^T from R4, including any lift/extension offsets
and baseline restoration; distinguish Euclidean transpose from weighted
adjoint. Reuse frozen solver concepts, not its periodic coefficient formula.

**REANA:** B-FIT/B-ADJOINT need central-row, constant-data, synthetic-extension
and baseline-restoration cases, independently assembled dense small maps,
and patch-order permutations. Require the registered `1e-12` adjoint/ordering
defects and condition-scaled admissible-polynomial reproduction. Define
expected matrices before implementation; no local matrix probe was run here.

### 4. Blocking U2 production use: patch expansion can collapse the approximation space

**Locators:** boundary §7.1 lines 361–395, U2 lines 397–401; B-FIT line 663.

For homogeneous degree-d polynomials the simultaneous wall constraints have
substantial exact rank effects. On perpendicular planes through the origin,
manual coefficient counting gives:

| Incident plane set | Scalar phi space dimensions d=1 / d=2 | Vector A space dimensions d=1 / d=2 |
| --- | --- | --- |
| None | 4 / 10 | 12 / 30 |
| x=0 | 1 / 4 | 5 / 15 |
| x=y=0 | 0 / 1 | 2 / 7 |
| x=y=z=0 | 0 / 0 | 0 / 3 |
| All six cuboid planes | 0 / 0 | 0 / 0 |

For example at a degree-2 corner, A is
`(a*y*z,b*x*z,c*x*y)`. At two walls it is
`(y*(a+b*y+c*z), x*(d+e*x+f*z), g*x*y)`.
At one wall A_x has the seven basis terms
`1,y,z,y^2,y*z,z^2,x^2`, while A_y and A_z each have four terms x times an
affine polynomial. The scalar requires a product of each incident plane's
linear factor: three adjacent faces already require degree 3, and all six
require degree 6. Tangential A at all six requires degree at least 4.

Taking the union of patches incident on *any* expanded stencil cell means
adding observations can also add opposite-wall constraints and reduce the
space, eventually to zero. A zero-dimensional reduced fit is formally
full-rank with zero free unknowns; that is not successful approximation of
a nonzero state. On the one-cell box this is unavoidable at degree <=2.
On highly irregular meshes expansion can spread this defect beyond a
shrinking wall band. A small algebraic fit residual/rank report alone
does not establish convergence. The stated zero-dimensional handling is
useful diagnosis, not a general production acceptance rule.

**Resolution:** freeze the above coefficient/rank expectations. Choose a
target-local patch support with a bounded physical stencil radius as h
shrinks. A concrete candidate is to keep the target cell's incident wall
patches (plus the target boundary face) fixed while expanding real rows;
review its separate cell/face trace agreement. Do not enlarge constraints
merely to cure a data-rank failure. Reject a production stencil whose
zero space cannot approximate its required fields; reserve algebraic
zero-space fixtures for explicit expected behavior. A higher-degree/global
boundary space is another named design, not a silent rescue.

**REANA:** freeze one/two/three-wall and opposite-wall ranks, including the
one-cell box, and distinguish valid zero maps from unsupported physical
resolution. Use admissible basis reproduction plus smooth higher-degree
fields on irregular/refined boundary bands. Keep B-MMS volume and band
orders and require the affected patch support shrink with h; do not count
a shrinking-volume band as proof of pointwise corner accuracy.

### 5. U1 adjudication: formal semidiscrete energy cancellation passes; consistency is unproved

**Locators:** boundary B8–B9, lines 230–281; B14 lines 463–474; B-CLEAN.

Let `M_s=diag(V_i)`, `M_a=M_s tensor I3` and
`D_c=-M_s^-1*G^T*M_a`. For fixed positive weights, fixed c_h>0 and
homogeneous scalar traces, direct differentiation gives

```text
R5: E_c = (a^T M_a a + phi^T M_s phi/c_h^2)/2
    dE_c/dt = a^T M_a G phi + phi^T M_s D_c a
               - phi^T M_s*kappa*phi/c_h^2
             = -phi^T M_s*kappa*phi/c_h^2.
```

The sign is correct. With spatially variable but frozen positive c_h,
replace the scalar mass by `M_s*diag(c_h^-2)` and use the specified
diagonal c_h^2 multiplying D_c. The instantaneous cross terms still cancel.
Time-dependent masses/speeds add the derivatives of both norm weights;
physical/gauge/advection forcing adds its own work. Dimensions agree:
G and D_c have 1/length, phi has A*length/time. This norm has A^2*volume
units, not physical magnetic/gas energy units. Green's surface terms in B14
have the stated signs and vanish for the stated continuum traces.

This energy algebra is true for **any** G, including G=0. It proves neither
G approximates grad nor D_c approximates the intended div. A necessary
manufactured consistency check for compatible smooth p is

```text
R6: G*S_s[p] - S_a[grad p] -> 0,
    -M_s^-1*G^T*M_a*S_a[A] - S_s[div A] -> 0,
```

in the registered interior and wall/edge/corner norms; S denotes sampling.
Volume-weighted weak consistency and pointwise divergence consistency are
different claims. Conditions on local QR rank do not prove the second line.

Nor is explicit Heun energy stable for an undamped skew wave eigenmode:
for z=omega*dt, `|1+i*z-z^2/2|^2=1+z^4/4 > 1`. Its finite-time norm drift
can converge with dt, as the B-CLEAN table anticipates. A c_h/h ceiling
alone does not bound all singular values of irregular constrained G.

**Resolution:** approve only R5's frozen semidiscrete norm statement.
Keep U1 open until both R6 limits, trace/forcing compatibility and a
spectral timestep/error policy are established. A candidate alternative is
a globally compatible weak construction with scalar zero trace,
`M_a*G=K`, `M_s*D_c=-K^T`, exact/controlled moment quadrature and separately
verified reconstruction to cell values. Its spaces/masses/commuting maps
must be specified; naming an adjoint is not that construction. Do not
replace D_c by an independent raw LS divergence without accounting for
`a^T M_a G phi + phi^T M_s D_LS a`.

**REANA:** keep B-ADJOINT `1e-12`, B-MMS G/curl order >=1.8 and D_c order
>=1.5, including compatible fields with nonzero divergence and isolated
wall/edge/corner errors. B-MMS's divergence-free field alone would not
establish divergence reproduction. B-CLEAN must isolate temporal error
and show its stated norm-drift/phase/reflection convergence; report largest
small-fixture weighted G singular values and actual dt. No semidiscrete
identity is a runtime or fully discrete stability result here.

### 6. Blocking U3: relative fit traces do not establish curl-gradient or projection compatibility

**Locators:** boundary §§7–8, B15 lines 476–524; B-GAUGE/B-MMS;
frozen `projected_rate.rs:389–408,471–507`.

C has shape 3N by 3N and G has shape 3N by N for real point samples;
all matrices must include the constrained fit maps from findings 3–4.
The negative adjoint only fixes the cleaning energy exchange. It does not
give `C*G=0` or the matching relative trace of the reconstructed gradient.
For example scalar Dirichlet alone allows the local polynomial phi=x^2
at x=0, while grad(phi)=(2x,0,0) violates the vector fit's imposed
`partial_x A_x=0`. This is not compatible initial data for *unforced* pure
cleaning; it illustrates why the two independently constrained polynomial
spaces are not nested. In a forced solution B6 can permit the corresponding
nonzero Delta(phi) trace through cancellation with physical/gauge forcing.
Imposing Delta(phi)=0 for every forced state would add a false condition.

U3 therefore needs the combined operator and forcing trace closure, not
only a small random adjoint defect. Cleaning can alter physical B by
`B_dot_clean=C*G*phi` on fixed geometry. A screened correction can also
turn a numerical gradient mode into B, and a different cell/face fit can
hide a trace mismatch behind the Riemann-enforced Bn=0.

For `H=C^T M_a C`, each diagonal is a sum of squares of *assembled real
unknown coefficients*. Combine baseline/extension dependencies before
squaring. Positive active diagonal and positive screening make H+kD SPD
on that active space, even when C has gauge null modes. A zero diagonal
is a genuinely unobservable column and needs explicit fixed-zero
correction/reduction, not a borrowed periodic gauge pin. Local QR rank
does not imply global curl rank. A one-cell all-wall degree-2 map can have
C=G=0, yielding vacuous energy/trace passes and no physical resolving power.

**Resolution:** freeze global dimensions/kernels and test both analytic-
gradient sampling and actual `C*G`. Require the stated contamination
convergence, not exact commutation unless derived. A possible exact
algebraic amendment is a weighted projector Q onto ker(C),

```text
R7: Q=I-M_a^-1 C^T*(C M_a^-1 C^T)^dagger*C,
    G_tilde=Q*G, D_tilde=-M_s^-1*G_tilde^T*M_a.
```

R7 would enforce C*G_tilde=0 and retain R5 in exact arithmetic, but is
**not approved as a fix**: if the numerical kernel approximates gradients
poorly it destroys G's consistency, even reducing cleaning to zero. A
compatible weak/reconstruction design is another route. Either requires
the same R6, trace and spectrum evidence; no formal algebra may substitute
for approximation of the intended continuum operators.

The bounded B15 solve includes finite C/V change, but inherits the earlier
moving-stage blockers. Its true normal residual is not the physical field
residual: if e=Btarget-C*a_trial, then
`C^T M_a*(e-C*z)=kD*z`. Tight solution neither forces exact Btarget nor
zero discrete volume mean/independent divergence. Do not subtract a measured
mean, overwrite Bn or reset gas pressure/energy to conceal this. At fixed
Q,V the projection changes magnetic energy by
`V*(|Bafter|^2-|Btrial|^2)/2` and thermal energy by the negative of that;
record this conversion separately from wall work.

**REANA:** B-GAUGE, B-ADJOINT, B-CLEAN and frozen small spectra/zero-column
fixtures precede coupling. Retain their proposed errors, normal solve
`1e-11`/true `1e-9` and separate physical target/trace/mean diagnostics.
Use zero-dt, finite-geometry and fixed/translated box comparisons. U3
stays open; these are future experiments, not solved bounded numerics.

### 7. Supported wall/ALE ledgers, with distinct induction and torque obligations

**Locators:** boundary B11–B12, lines 307–351; §10 lines 591–601;
frozen `mhd-core/src/lib.rs:615–635`.

For a physically valid selected Pi, the stated flux is correct:
`F_m=0`, `F_p=Pi*n`, `F_E=Pi*(W dot n)`, `F_B,ALE=0`.
One face exchange is subtracted from the real cell; support receives the
opposite impulse. With `I=-dt*A*Pi*n`, gas work is W dot I. A constant
joint boost adds b dot I to wall work and transforms gas conserved energy
as stated. Stationary zero work does not imply zero force or no reflection.

The existing full-vector kernel already applies the ALE/laboratory boost.
Another subtraction of W_n*U would be wrong. A zero induction *flux*
does not mean the normal A induction *rate* is zero: `(v_r cross B)_n`
can be nonzero while its tangential electric field vanishes. B15 must use
the selected wall flux and prescribed wall sweeps once, with exactly the
same frame convention as its interior target. For this chart, all gauge,
raw A and cleaning expressions must use the relative velocities, not a
periodic bulk-reference offset silently carried over from M1.

Physical wall torque uses `(x_face-x_ref) cross I`. The angular change of a
cell-centroid monopole from the same kick uses its cell centroid; the
difference `(c_cell-x_face) cross I` is a representation/hydro torque
channel, not a second external wall impulse. A matching face ledger cannot
prove exact centroid angular-momentum conservation. Source gas/particles
and ambient remain live; no mirror gravity or deletion at the wall is
introduced.

**Resolution/REANA:** retain signed raw/adjusted P/L/E histories, real-only
mass/source accounting and normal A source. Add source/epoch/stale-patch
rejections to B-WALL/B-BOOST; require the registered `1e-12` flux and
`1e-10` boost/work identities. In moving cases compare actual wall
area/centroid quadrature with prescribed sweeps, not a generator's velocity.
Keep boundary sweeps outside the interior GCL correction's free edges.

### 8. Blocking U4 and smooth gravity startup: freeze a globally compatible background and perturbation

**Locators:** boundary B2, B6, B13; B-FIELD/B-GRAV-WORK and U4
lines 683–692; shared finite-box choice and gravity §7.

The compact nonzero A is globally compatible with the initial magnetic
traces. It is not automatically magnetostatic, so B-FIELD's coupled
non-equilibrium control launches physical waves. A constant thermodynamic
ambient collar with isolated nonzero normal gravity also fails classical
normal-momentum startup compatibility: at a stationary slip wall,
`partial_n(p+B^2/2)=rho*g_n` is required. Uniform p and B=0 there give an
initial nonzero normal acceleration. The contract acknowledges this risk;
it must not later label that initialization a smooth hydrostatic solution.
Either construct compatible pressure/density or register and bound the
resulting weak startup transient.

A concrete gravity-off **candidate background** for U4 is available without
an illegal uniform all-wall field. In the unit cube set

```text
R8: A=(0,0,a*sin(pi*x)*sin(pi*y)), phi=0, v_r=u_r=0,
    B=(a*pi*sin(pi*x)*cos(pi*y),
       -a*pi*cos(pi*x)*sin(pi*y),0),
    rho=rho0>0, p=p0+pi^2*A_z^2, p0>0.
```

This obeys all six relative A/B traces, has zero volume mean B, and
`div A=0`. Since `J_z=2*pi^2*A_z`,
`J cross B=grad(pi^2*A_z^2)=grad(p)`; hence it is an exact stationary
ideal-MHD background with gravity off and energy initialized from the EOS
and B. Its y-varying tangential field at x=0 permits a genuine local wall
wave interaction while closing globally. This is a manual equilibrium
identity, not an executed stability result or a galaxy IC. It is z-invariant
only as a deliberately simple background; the mesh can still be fully 3D.

**Resolution:** an author can use R8 or another globally specified background,
then freeze all perturbations `delta rho,delta p,delta v,delta A,delta phi`,
support/wall traces, amplitude, polarization, orientation, source switches,
arrival/reflection time and reference solution. A plane-wave formula with
constant coefficients cannot be transplanted across R8's nonuniform field.
Derive the linearized variable-coefficient initial-boundary problem or
construct a compatible manufactured solution; give an independent reference
and its uncertainty. Small-amplitude/refinement comparisons must distinguish
nonlinearity from discretization and corner effects. B-CLEAN is a gauge
wave test, not this physical magnetosonic test.

**REANA:** retain U4's reflected amplitude/phase <=2% and spatial order >=1.5
after the packet/reference is frozen. First verify background force balance
and its temporal stability; then waves and wall-parallel/corner variations.
For gravity startup, run the independent analytic hydrostatic profile with
nonzero g_n before live gravity, and measure wall launches in the galaxy
controls. U4 cannot be closed by B=0, B-CLEAN or a zero-work wall ledger.

### 9. Auxiliary symmetry is plausible; freeze its chart, stage and fallback semantics

**Locators:** boundary §9 lines 526–587; §10 lines 603–635;
frozen `auxiliary.rs:199–275,285–317`.

For Cartesian walls the component reflection matrices commute. Unsigned
positive kernel normalization and signed normal-component values produce
the stated auxiliary parity. A single shared Hermite jet per boundary node,
with all tangential derivatives of the odd normal-component trace zero,
makes u_r,n identically zero on an entire face, not just its nodes. At
corners all three relative components vanish. Tangential evenness is an
auxiliary choice; it is not permission to mirror the gravity-forced gas
pressure, B or arbitrary phi smoothly.

The image formula `2mL +/- y_s` assumes the box chart's minimum is zero.
Define that convention explicitly, or for chart minimum a use
`a+2mL +/- (y_s-a)`, with nodes `a+k*L/n_aux`. Specify the deterministic
finite image enumeration by the kernel support `|q-image|<2h` in each
axis, reflection parity, endpoint-node ownership and duplicate policy.
There are n_aux+1 real nodes per axis, not n_aux periodic nodes.

**Resolution:** anchor the grid permanently to the box chart, translating
in the laboratory with W. Do not apply M1's separate volume-mean rolling
origin and then another stage-time translation. Each old/predicted/final
auxiliary field, constrained map, source snapshot and fallback decision
needs its geometry/state/time epoch and immutable retry provenance. Define
whether whole-grid coarsening is a rejected physical-resolution event and
how the support-region criterion is evaluated; a globally coarsened field
does not have only a local fallback footprint. Pure fallback u=W is a
valid algebra control, not automatically a resolved galaxy gauge field.

**REANA:** include nonzero chart anchors, all corner reflection orderings,
images reaching more than one mirror layer at root resolution, empty
support/root changes and analytic Hermite derivatives. Retain trace/C1/
ordering `1e-12`, boost `1e-8` and restart/failed-trial parity gates.
Repeat n_aux=4/8/16 controls at fixed physical case. Earlier moving-stage
findings, including centroid predictor/order and target composition, remain
unchanged prerequisites; this boundary stage list does not resolve them.

### 10. Blocking finite-box adequacy claim: closed budgets need physical domain/ambient controls

**Locators:** boundary B-DOMAIN lines 672–681, §§1–2; gravity §7 and the
shared "Mesh motion and physical boundary gate".

The profile is a finite reflecting box, not a vacuum or outflow model.
Zero gas loss and stationary wall work follow the chosen boundary; they do
not bound a reflected disturbance, confinement of ejecta, gauge-induced B
contamination or ambient drag/accretion. Net wall force alone can cancel;
the proposed signed and absolute excess impulse/torque are useful additional
controls. Subtracting only separately recorded analytic uniform ambient
traction is a diagnostic, never a gas-state correction. Preserve raw terms.

**Resolution/gates:** retain the registered 128/256/384 R_d domain ladder,
common baseline ambient density chosen from the largest-box mass limit,
independent density/pressure factors, central-profile change <1%, excess
wall impulse/torque `<=1e-6` fixed scales and all original energy/source
budgets. Register common radial bins/times and reference uncertainty.
In addition freeze which merger outcomes must be insensitive: trajectory/
pericentre timing, bound/tidal gas and stellar mass, integrated new-star
mass/SFR, central thermodynamics and magnetic energy/topology diagnostics.
Select their acceptance bounds before execution from the parent gravity/
ISM gates or a reviewed observable-specific criterion. Central density alone
cannot establish adequacy for all requested physics.

Report observed physical and cleaning wave return times using actual
fast/cleaning speeds and flows. Lack of a hydrodynamic return within the
encounter does not exclude gravity/ambient effects: isolated gravity is
instantaneous and every ambient cell gravitates. Compare the initial ambient
force and live dynamics across boxes as well. A failure requires larger
domain or a newly reviewed physical profile; no post-result relaxation.
Do not infer acceptance of the deferred general outflow branch.

### 11. Supported analytic fixture values: all seven cases pass the manual formula review

**Locators:** fixture JSON `/tensor_expected_rule`, `/fixtures/0` through
`/fixtures/6`; fixture README "Exact derivations". No geometry backend,
reference reducer or executable rational-arithmetic test was run.

The calculations in the following subsection support the stated interval,
volume, centroid, face, incidence and volume-integrated central-J values.
No correction to those mathematical expectations was identified. This
support is restricted to the frozen inputs, with the exact image conventions
and transformations in finding 12; it is not evidence that any builder
produces them.

**Cartesian derivation (R9).** Squared Euclidean distance separates on a
Cartesian product, so each cell is the product of midpoint intervals,
including the previous/next periodic generator image. For widths h_a and
midpoints c_a,
`V=h_x*h_y*h_z`, `J_aa=V*h_a^2/12`, `J_ab=0` for a!=b. Face area is the
product of the other two widths; its centroid has one endpoint coordinate
and the other two interval midpoints. Each real cell has six incidences.
On the torus there are 3N canonical shared faces, including self-image
faces and multiple image faces between the same pair of real IDs.

| Fixture | Manual expectations supported |
| --- | --- |
| periodic_one_cell_self_images | Generator `(1/4,3/8,5/8)` is also the cell centroid; the three intervals are generator +/-1/2. V=1, diagonal J=1/12. Three canonical self-image faces with images +e_x,+e_y,+e_z have six incidences and zero net real-owner incidence. |
| periodic_cartesian_2x2x2 | Width 1/2, V=1/8, area 1/4, diagonal J=1/384. N=8 gives 24 faces, 48 incidences. Each cell has three distinct neighbour IDs but six image incidences: the internal and seam face between a pair are distinct. |
| periodic_nonuniform_3x2x2 | x intervals `[-1/16,1/4]`, `[1/4,9/16]`, `[9/16,15/16]`; widths `5/16,5/16,3/8`; centroids `3/32,13/32,3/4`. With y/z widths 1/2, V=`5/64,5/64,3/32`; Jxx=`125/196608,125/196608,9/8192`; Jyy=Jzz=`5/3072,5/3072,1/512`. N=12 gives 36 faces, 72 incidences. |
| periodic_cartesian_4x4x4 | Width 1/4, V=1/64, area 1/16, diagonal J=1/12288. N=64 gives 192 faces, 384 incidences. |
| periodic_nonuniform_4x4x4 | Cyclic generator gaps `1/10,1/5,3/10,2/5`; intervals `[-3/20,1/10]`, `[1/10,1/4]`, `[1/4,1/2]`, `[1/2,17/20]`; widths `1/4,3/20,1/4,7/20`; centroids `-1/40,7/40,3/8,27/40`. V and J follow R9 on all 64 tensor products. Jaa/V factors are respectively `1/192,3/1600,1/192,49/4800`. Faces=192, incidences=384. |
| bounded_one_cell_2x3x4 | The physical box is the cell despite the off-centre generator. V=24, centroid `(0,-1/2,-1)`, J diagonal `(8,18,32)`, cross J=0. Two x faces area12, y faces8, z faces6, with the listed signed normals and face midpoints; six boundary fragments/incidences. |
| bounded_oblique_bisector | The two generators give the bisector x+y+z=3/2. Both V=1/2; the detailed moments and oriented hexagon below agree with the packet. One shared face and twelve physical boundary fragments give fourteen incidences. |

The nonuniform 4^3 first centroid lies outside the primary box; its offset
from its generator is `-3/40`, not the minimum-image-wrapped centroid
difference. The other offsets are `1/40`. For the 3x2x2 x offsets they are
`-1/32,1/32,0`. These are the intended independent controls on centroid
charts versus generator coordinates.

**Oblique derivation (R10).** Let D be the unit cube below S=x+y+z=3/2.
Inclusion/exclusion gives
`V=((3/2)^3-3*(1/2)^3)/6=1/2` and
`int_D(3/2-S)=((3/2)^4-3*(1/2)^4)/24=13/64`.
Thus `int_D S=35/64`, `int_D x=35/192`, c_a=35/96.
Reflection x->1-x swaps the two cells, so the upper centroid is 61/96.
Writing m=35/192, the full-cube moments imply
`2*int_D x^2 + V-2m=1/3` and
`2*int_D xy + V-2m=1/4`.
Hence raw moments are 19/192 and 11/192. Subtracting
`V*c_a*c_b=1225/18432` gives J diagonal `599/18432` and cross terms
`-169/18432`, identical for both cells. Its eigenvalues are positive:
29/2048 along (1,1,1) and 1/24 in both transverse directions.

The six stored shared vertices lie on S=3/2. Consecutive sides have length
1/sqrt(2), the centroid is (1/2,1/2,1/2), and six equilateral triangles give
area 3*sqrt(3)/4. For the first three vertices, the cross product of
successive edge vectors is `(1/4,1/4,1/4)`, supporting outward winding from
counter 1 and normal `(1,1,1)/sqrt(3)`.

At a lower-cell minimum-coordinate face the removed corner triangle has
area1/8 and tangent centroid (5/6,5/6). The remaining area is 7/8 and each
tangent centroid is `(1/2-5/48)/(7/8)=19/42`. A maximum-coordinate face
is the small triangle with area1/8 and tangent centroid (1/6,1/6).
Reflection gives upper-cell 5/6 and 23/42. The lower x-normal closure is
`-7/8+1/8+(3*sqrt(3)/4)/sqrt(3)=0`; the other axes follow by symmetry.

**REANA:** an independent reference must still expand every ID/point,
evaluate exact rational/algebraic expectations, check physical polygons,
orientation, charts, all tensor entries and the full geometry identities,
and compare actual accepted backend output. Preserve all packet `1e-10`
normalized gates and exact positive-face/incidence counts. An ambiguity or
rejection is not a pass for these required analytic cases. Do not infer
nondegenerate Delaunay topology: Cartesian seeds have co-spherical contacts
whose zero-area diagonals are not extra physical Voronoi faces.

### 12. Fixture harness refinement: freeze transformation/ID semantics and independent reference separation

**Locators:** fixture JSON `/scalar_encoding`, `/identity`,
`/transform_families`, `/gates`; fixture README final paragraph.

Rational strings and `{rational:[p,q],sqrt:d}` encode every listed value
without an expression evaluator. Positive denominators and the specific
small integer radicands avoid a mathematical serialization ambiguity.
The plane string is a human-readable label, not code to evaluate. The
future expander must reject malformed values, validate namespace/counter
range, and round the exact composed input once to ties-to-even f64 while
archiving the resulting bits. Algebraic expectations use independently
controlled precision and uncertainty.

The x-fast rule `1+ix+nx*(iy+ny*iz)` is unambiguous in the base packet.
Transformed cases retain those original IDs; recomputing x-fast IDs after
an axis permutation would violate that instruction. Image triples and both
J indices must transform together; owner/image canonicalization must
retain parallel image faces. A periodic one-cell face has two incidences
on one real owner and no second gravitating entity.

**Resolution:** freeze the order of composed transformations, for example
the explicit prospective convention
`x'=s*P*x+t`, `L'=s*P*L`, `anchor'=s*P*anchor+t`,
`t=L' elementwise_multiply tau` with tau from the packet.
Record patch-axis/name remapping and retain IDs. Central moments transform
as `J'=s^5*P*J*P^T`; V as s^3 and area as s^2. An odd permutation reverses
polygon winding to keep outward normals; translating changes centroids
but not J. This is geometry-only transformation data, not an implicit
magnetic pseudovector convention for future MHD fixtures.

The stated normalized denominators have correct dimensions, including
`V_expected*Lref^2` for volume-integrated J (length^5) and a positive
fixed Lref for zero expected cross terms. Do not substitute J/V or use
an absolute unit-dependent tolerance after scales 1e-6/1e6. Keep exact
positive-face counts and certified zero-area contact handling.

**REANA:** the candidate builder consumes only domain/generators/IDs, never
the expected interval/polygon table as construction input. An independent
reference can use the manual separable/oblique formulas with exact/high-
precision arithmetic, and must not call the candidate clipping/integration
code. Archive expanded points, transformed expected data, f64 bits, coverage,
hashes and uncertainty; run each backend/scale/translation/permutation case
as its own workflow. The packet correctly leaves points-only seam shifts,
thread/permutation repeats and motion to G04/M fixtures. This review found
no expected-value correction, but it does not certify that expander or
independent REANA reference, which remain future implementation work.

## Implementation disposition and review limits

Return findings 2–6 and 8 to the boundary author before numerical operator/
wall-pressure implementation. R4 and the coefficient counts make U2 a
concrete revision task; R5 supports only formal frozen semidiscrete energy
cancellation, leaving U1 consistency and U3 kernel/trace coupling open.
R8 provides a candidate global background, not the missing U4 reflection
packet. Findings 7, 9, 10 and 12 identify additional frame/stage/domain and
harness decisions that must be frozen before their dependent cases.

After scoped M1 acceptance, a separately reviewed small fixed-geometry
map/wall-flux slice can proceed once its exact weights, pressure rule,
constraints and fixtures are fixed. All new executable cases run on REANA,
independent workflow per case with declared threads/memory/time and no
aggregate cap. Use the author's B-WALL/B-FIT/B-ADJOINT envelopes initially;
geometry cases retain 1 thread, 2 GiB, 300 s. Native numerical libraries
must not create unallocated nested pools. Preserve preflight/build and
physical prerequisites; required failures stop dependent escalation.

The earlier [moving-stage review](MESH_3D_DESIGN_REVIEW.md), frozen in
`e5a35d1`, is unchanged. Its target-frame/reduction, sample/composition,
centroid order, missed-topology, energy/mean and raw-stage blockers are
not resolved by choosing this wall. Coupled deforming MHD remains the goal;
a finite fixed-box algebra success cannot replace it or establish galaxy
isolation. No stability theorem, executed geometry/physics acceptance,
general outflow solution or fresh M1 result is asserted here.

Document-only verification passed: the inventory's 18 source/contract/code
identities match their pinned bytes, both fixture-manifest hashes match,
JSON parses, local links resolve, code fences pair and the owned files have
no trailing whitespace. `git diff --check` passed. At final verification
another worker had changed `MESH_3D_SPEC.md`; this report reviews its pinned
`23ab618` bytes, not those subsequent changes. The earlier moving-stage
findings remain frozen and require their own follow-up review.
