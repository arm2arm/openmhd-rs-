# Compound disk equilibrium: a conditional orbit-response construction

2026-11-22. **Source/manual-math proposal; narrow author correction awaiting
root inspection.**
Keep the proposed compound density and common softened kernel; obtain its
stress and rotation targets from a nonnegative, invariant-orbit feasibility
construction before running the selected independently implemented
Yurin–Springel velocity optimizer. Neither stage is guaranteed feasible.
No DF, orbit, quadrature, sampler, test or evolution was evaluated here.
M1 source `2bdcea0` remains frozen and unaccepted. This is preparation for
the live moving-3D magnetized gas/DM/old/new-star goal, not a replacement
collisionless-only goal.

[The inventory](compound_disk_equilibrium_sources.json) pins context commit
`028876a0d7ecd13a6c71bd3fb10b88fd5948a6d6`, full primaries, inspected pages,
retained derivations and read-only checks. Historical
[Jeans source constraints](AXISYMMETRIC_JEANS_SOURCE_NOTE.md) and their
[independent review](AXISYMMETRIC_JEANS_DESIGN_REVIEW.md) remain unchanged.

## Narrow author dispositions

The [independent compound review](COMPOUND_DISK_EQUILIBRIUM_DESIGN_REVIEW.md)
examined subject `bbc299796351238c55d36b81d0fafd144b8c16a5`; its report is
26,319 bytes, SHA256
`70bae9b464d926bdb2de9236821285b8f66fd0dac30620ef4ac93e3e0ea2bbbe`.
It and its exact source/reading receipts remain historical, unchanged evidence.
The inventory retains that subject's two original identities, the review
identities and current revision input context separately from the original
`028876a` context. This correction changes no CD1–CD8 equation, parent
physical target, selected Yurin optimizer route or acceptance threshold.

1. **Review finding 1 corrected:** section4 now states zero outside
   stationary-measure mass, not a pointwise no-excursion theorem for an
   arbitrary generating launch. Invariant/recurrence assumptions, phase
   selection and initial-orbit export/max-excursion checks remain distinct;
   a finite quiet window or small residence fraction is no certificate.
2. **Review finding 5 scope recorded:** section5 now derives the finite
   bound-orbit library's inability to reproduce the exact infinite sech²
   vertical tail. Finite/binned approximation requires explicit tail mass,
   moment and force enclosures and expanding near-escape coverage in a
   continuum limit. No density truncation, parameter amendment, numerical
   value or impossibility claim about all continuum DFs follows.

## 1. What the sources support

**Y14:** [Yurin & Springel, arXiv:1402.1623v2](https://arxiv.org/abs/1402.1623v2),
printed pp.3–5 Eqs.1–12/section2.3, defines fixed-position velocity adjustment
against orbit-averaged density and additional velocity constraints. Its
moment merit uses the **initial** catalog, not orbit-averaged moments.
Sections4.1–4.4, pp.9–11, describe bins, orbit integration and proposals;
Eqs.47/50/51, pp.11–12, give the untapered density families. Paper examples,
orbit durations, proposal parameters and force-table construction are not
project accuracy guarantees or adopted constants.

**S79:** [Schwarzschild, ApJ232,236–247 (1979)](https://articles.adsabs.harvard.edu/pdf/1979ApJ...232..236S),
printed pp.237–238, sectionIIc–e/Eqs.1–2, supplies the nonnegative orbit
occupation formulation. It distinguishes inadequate libraries from possible
model infeasibility and cautions about finite discretization. Its p.238
attribution of a general axisymmetric existence claim to Lynden-Bell is
not independently established here and is **not** used as a theorem for
this softened, cusped, compact-radial/infinite-vertical target.

The feasibility step, support checks, stress extraction, symmetry construction
and acceptance hierarchy below are **project engineering derivations**.
They adapt these ideas to the fixed Plummer convolution; they are not a
published GALIC prescription. No external software/code/dependency is adopted.

## 2. Freeze density and field before velocity search

Retain [gravity sections10–11](GRAVITY_PARTICLES_SPEC.md#10-equilibrium-initial-conditions-and-staged-merger).
These are project proposals, not Y14 values or a Milky Way fit:

| Physical inputs | Retained target |
| --- | --- |
| Collisionless post-taper masses, `G=Rd=Mgal=1` | halo/disk/bulge `.85/.12/.03` |
| Halo scale a / bulge scale b / stellar height zd | `10/.2/.2 Rd` |
| Halo/bulge spherical taper | `100–200 Rd` |
| Stellar radial taper | `8–10 Rd`, exponential R and `sech²(z/zd)`; no hard z cut |
| Later gas configuration | `.85/.10/.03` collisionless plus `.02` gas; `Rg=1.5 Rd`, gas surface taper `8–10 Rg` |

For every component multiply the GP-7 density shape by its taper, then
renormalize its **entire** volume integral to the stated mass. With
`s=(r-rt)/(rout-rt)` (or R for the disk), use `T=1` inside rt,
`T=1-10s³+15s⁴-6s⁵` on the transition and zero outside rout.
For example, define `Id=integral_0^Rout R exp(-R/Rd) T(R) dR` and

```text
rho_d(R,z)=Md exp(-R/Rd) T(R) sech²(z/zd)/(4 pi zd Id),
2 pi integral R dR integral dz rho_d=Md.                    (CD1)
```

The second line follows from `integral sech²(z/zd) dz=2zd`.
Do not taper a sampled catalog again. Halo/bulge integrable `1/r` cusps
and the exponential disk's Cartesian radial cusp are retained, not silently
replaced by smooth cores.

All components use the **one combined** isolated field

```text
Phi_e(x)=-G sum_c integral rho_c(y)/sqrt(|x-y|²+e²) d³y,
a_e(x)=-G sum_c integral rho_c(y)(x-y)/(|x-y|²+e²)^(3/2) d³y,
Phi_e(infinity)=0; h(x,v)=|v|²/2+Phi_e(x).                 (CD2)
```

Fixed numerical softening is `e=.05 Rd`, with separate `.025/.1 Rd`
controls; it is not thickness or a pressure floor. Source density in CD2
is the particle-position density, not an additionally smoothed density.
This is softened Vlasov self-consistency, not the unsoftened component
potential sum. A spherical isotropic Eddington DF for halo or bulge alone
does not solve their problem in the flattened common field. The
[spherical E1–E5 reference](SPHERICAL_EQUILIBRIUM_SOURCE_NOTE.md) is a separate
prerequisite/control, not their compound DF.

For the collisionless target CD2 is already fixed by CD1 and the other
densities. Refine quadrature/tables; do not change density or potential to
improve a velocity merit. Reconstructed orbit densities must regenerate the
same field within a separately frozen error budget. Gas makes this a joint
field/force-balance iteration (section7).

Use [GP-1 and the shared units contract](INTEGRATION_CONTRACT.md#units-state-and-exchanged-quantities):
one SI map, `T0=L0/V0`, `Phi0=V0²`, `Gcode=GSI M0/(L0 V0²)` and
`B0=V0 sqrt(mu0_SI M0/L0³)`. G=1 requires the compatible derived V0;
cooling receives its explicit cgs adapter. Keep physical density/rotation/
population choices, dimensional conversions and numerical N/e/dt/bin/domain/
RNG choices in separate manifest fields. None is calibrated here.

## 3. Preserve the exclusion; change the unselected closure

Let `sR=<vR²>`, `sz=<vz²>`, `sphi=<vphi²>`, `t=<vR vz>`, with mean
vR=vz=0. The reviewed cylindrical CBE moments give

```text
dR(rho sR)+dz(rho t)+rho(sR-sphi)/R+rho Phi_R=0,
dz(rho sz)+(1/R)dR(R rho t)+rho Phi_z=0.                  (CD3)
```

The last mixed-stress derivative in the radial equation is **z**, unlike
retained printed Y14 Eq.24. Its printed axis paragraph after Eq.33 also
does not supply J2's nonuniform origin limit. These remain source
discrepancies, not publisher errata or a software audit.

At fixed finite z write `delta=Rout-R`; the chosen taper has
`rho=A(z) delta³[1+O(delta)]`. Under J4's positive finite `sz->s0(z)` and
bounded derivative, untilted `t=0`, constant positive `sR/sz` gives J5's
negative divergent raw sphi. Retain that exact closure as a **negative
control**, not as the optimizer's target or a Gaussian proposal covariance.

One local alternative illustrates why the density alone is not yet excluded:
if `t=0` locally and `sR=kappa(z) delta+O(delta²)` with differentiated
remainders controlled, then direct substitution into CD3 gives

```text
(1/rho) dR(rho sR)=-4 kappa(z)+O(delta),
sphi -> Rout [Phi_R(Rout,z)-4 kappa(z)].                 (CD4)
```

Here kappa has acceleration units. A necessary edge condition is
`0<=kappa(z)<=Phi_R(Rout,z)/4` where that force derivative is nonnegative;
then `sR/sz->0` if s0>0. For a density edge `delta^p` the factor is p+1.
This is a **local necessary moment asymptote**, not a global untilted model,
solved Jeans PDE or positive-DF theorem. It is not uniform as |z| grows;
allowing t changes the radial balance and requires its own derivative.

Recommendation: retain the density provisionally and drop the **unselected
constant-positive-b shortcut**, not any pinned mass/scale/taper. Let orbit
feasibility solve flexible stresses and tilt. No physical density amendment
is proved necessary by J5 or CD4. If a later verified obstruction requires
one, preserve the original as a labelled negative target and review the
smallest explicit change before new IC generation; no clipping, bad-bin
deletion, seed retry or live velocity rescaling is a repair.

For all selected moments require `sR,sz>=0`, `sR sz-t²>=0`,
`sphi-<vphi>²>=0`, plus the full covariance when other cross terms exist.
Use CD3 independently, not the printed wrong derivative or an imposed
Satoh split to manufacture positivity. At a regular Cartesian axis a smooth
axisymmetric covariance has equal transverse components and vanishing
meridional cross term; `t=O(R)` additionally requires differentiability.
Our density cusps do not justify assuming a smooth DF/stress at the origin.
Positive softening smooths the force kernel, not the raw target density;
a central DF singularity or unresolved high-binding population remains a
separate possibility, not a supplied finite-core solution.
Use Cartesian orbit states, central **integrated** masses/moments and
separate approach limits. Do not assign a tilt angle at (0,0), divide by R,
or borrow a finite-core central DF without analysis.

## 4. Nonnegative feasibility reference and rotation

For an exact bound orbit q in CD2 let `mu_q` be its normalized invariant
phase-space occupation measure, if the long-time limit exists. For a bounded
smooth test function g,

```text
integral {g,h} dmu_q
 =lim_T->infinity [g(X_q(T))-g(X_q(0))]/T=0.
F_c=sum_q w_cq mu_q, w_cq>=0, sum_q w_cq=Mc              (CD5)
```

is therefore a nonnegative **weak stationary measure**. This manual
telescoping proof assumes the limit, a time-independent field and bounded
endpoint term. It proves neither a smooth, absolutely continuous DF nor
stability. Finite-time tracks or smoothing a histogram in arbitrary
phase-space coordinates do not inherit its exact invariance. Chaotic/sticky
tracks need independent longer windows and remain unresolved if they do not
saturate; calling every orbit a function of an invented I3 is unnecessary.

Construct axisymmetric measures by averaging whole orbits under rotations
about z. In a static axisymmetric, midplane-symmetric CD2, also use exact
whole-orbit symmetries: meridional reflection Q changes `(phi,vphi)` to
`(-phi,-vphi)`; time reversal reverses all v; their composition reverses
`(vR,vz)` together while retaining vphi. Average this latter pair to remove
meridional first moments without erasing t. Equal midplane-reflected
measures make t odd in z. **Independent local vR or vz flips erase t and
are not assumed equivalent trajectories.** This qualified construction is
distinct from Y14 section4.3's proposal/merit symmetrization.

Pair the resulting prograde measures with their Q images. For each pair
with total mass w use

```text
w_plus=(1+eta_q)w/2; w_minus=(1-eta_q)w/2; |eta_q|<=1,
Lz_component=sum_q eta_q w_q |Lz_q|.                    (CD6)
```

This preserves density and raw even moments, changes streaming and keeps
weights nonnegative. Halo/bulge use equal counterrotation (zero mean
rotation), not spherical velocity isotropy. For the first disk recommend
one constant `0<eta_d<=1` across the prograde/counterrotating pairs; freeze
its value and feasible interior hotness bounds **before** production fitting.
Their values are unresolved physical inputs. Eta is constant on each invariant
measure, not an arbitrary spatial sign-flip law. A total Lz outside the
nonnegative feasible range fails. Rotation cannot change negative sphi.
Even a maximal prograde choice is not a stability theorem.

For each component and spatial bin define nonnegative residence fractions
`B_jq=integral 1_bin_j(x) dmu_q`. Solve the reference problem

```text
sum_q w_cq B_jq = d_cj = integral_bin_j rho_c d³x,
w_cq>=0, sum_q w_cq=Mc,                                 (CD7)
```

with frozen finite error enclosures, not exact equality asserted from
floating-point residuals. Add CD6 and explicitly chosen kinematic bounds;
do not insert the excluded constant-b profile. Obtain first/raw-second/mixed
moment targets by replacing the indicator with indicator times v_a or
v_a v_b in CD7 and dividing the weighted sum by the reconstructed bin mass.
Zero-mass bins impose support constraints and have no defined moment ratio.
They are **outputs to solve**, then freeze as the velocity
optimizer's target profiles, including their interpolation uncertainty.

Nonuniqueness needs a stated selection rule. Recommend minimum weight
concentration `sum w_q²/pi_q` within the hard feasible set, with positive
normalized library prior pi frozen from the declared launch quadrature.
This is an engineering regularizer, not a DF-existence or hot/stable-disk
theorem. Its prior, strength if relaxed, and any interior dispersion bounds
remain explicit pre-implementation choices. Density/positivity/support and
the individual moment bounds cannot be traded against this score. Reject
weight concentration or rough moment profiles that cannot converge under
library refinement; unconstrained smoothing is not a remedy.

For exact zero target outside each component support, write
`B_out,q=mu_q(out)`. Positivity in CD7 implies `w_q*mu_q(out)=0` term by
term: for each positive-weight measure, `mu_q(out)=0`. Thus the stationary
ensemble has zero outside mass, almost everywhere with respect to that
measure; nonnegative occupations cannot cancel positive outside
**measure mass**. This alone is not a pointwise no-excursion theorem for
an arbitrary trajectory generating the long-time limit. If its outside
residence `A_out(T)=integral_0^T 1_out(x(t)) dt` is finite or `o(T)`,
`A_out(T)/T->0` despite that residence. This logical distinction asserts
neither an actual exceptional orbit in CD2 nor target infeasibility.

Pointwise/invariant-support claims for a chosen launch need separate
invariant-support or justified recurrence/positive-visitation assumptions
and an explicit phase/launch selection policy. An invariant measure
supported on a closed allowed region gives a measure-a.e. supported-flow
statement, not a certificate for every launch whose limiting measure was
used. No wall reflects these particles. Retain the initial-orbit export,
outer-residence, maximum-excursion, longer-window and unresolved-support
checks separately. Neither a finite observation with no detected excursion
nor a small residence fraction certifies infinite-time pointwise support;
unresolved required support still blocks IC export. The disk's full
vertical tail and the cusps must not be truncated into a different target.

A failed finite library is **inconclusive about all DFs**, but blocks the
candidate IC. Distinguish negative/unresolved weights, inadequate coverage,
orbit nonconvergence, inconsistent constraints and a certified finite-cone
infeasibility. For the last, an independently checked dual y satisfying
`B^T y>=0` and `d^T y<0` contradicts CD7; include the mass/constraint rows
and numerical enclosures. It excludes only that frozen cone, not every
orbit. No solution, unresolved sign or unresolved support means no IC export.

## 5. Bins, independent responses and the selected optimizer

Use full-azimuth signed-z cylindrical annuli with boundaries including R=0,
both taper joins, an independently resolved central region and exterior/
tail bins. For `[Ri,Ri+1] x [zk,zk+1]`, volume is
`pi*(Ri+1²-Ri²)*(zk+1-zk)`; target mass is
`2pi integral R dR integral dz rho`. If folding +/-z, double both volumes
and mass and transform odd-z moments explicitly. Y14 Eq.40's factor2pi
already includes its midplane folding; do not apply it to a signed-z bin.
These diagnostic bins are not the moving gas mesh.

Use half-open intervals with an explicit final-bin endpoint rule. The axis
belongs to the central bin; the zero-density cutoff surface belongs to the
component's exterior support row. Include both vertical overflow tails and
all exterior space exactly once, with per-component support indicators.
Exact-boundary trajectories need deterministic tie handling and a separate
singular-orbit check, not double counting or a discarded residence fraction.

For the disk the exact mass fraction at `|z|>Z` is
`1-tanh(Z/zd)`; this follows from CD1. Retain it with a converged tail
force/moment enclosure. No hard z cutoff, deleted central mass or
unreported zero-target exterior bin is allowed. Central cusped integrals,
taper joins and outer tails need distinct quadrature panels/limits.

There is an exact finite-library limitation (review finding 5). In CD2,
the finite-mass isolated potential tends to zero at infinity. For a fixed
bound specific energy `E<0`, choose a finite radius beyond which
`Phi_e(x)>E`; energy conservation and nonnegative kinetic energy require
`E=|v|²/2+Phi_e(x)>=Phi_e(x)`, so that orbit cannot enter that exterior.
Each such orbit/occupation measure has bounded spatial support. A finite
sum therefore has a finite maximum `|z|=Zmax`, but CD1 has positive mass
fraction `1-tanh(Zmax/zd)>0` outside every finite Zmax. No finite sum of
these bound measures exactly equals the full continuum disk density.

CD7's finite/binned approximation must therefore carry explicit tail
**mass, moment and force** error enclosures, not a claim of exact global
reconstruction from a finite library. A continuum limit requires expanding
spatial and near-escape (`E->0-`) orbit coverage together with those tail
controls; that is necessary coverage, not a sufficient DF-existence proof.
No tail value, orbit energy grid or enclosure budget was calculated here.
The target remains the infinite vertical density with unchanged masses,
radial taper and kernel; this finite-library limitation rules out neither
all continuum DFs nor the target itself and weakens no parent gate.

Freeze bins from target mass/resolution **before** fitting; do not coarsen
failed edge bins after seeing results. Use separate training and finer/
offset validation partitions. Library launches span bound E, both Lz signs,
meridional velocity/position families and near-edge/axis/high-binding orbits;
no circular-orbit-only library. Their actual grids/prior/coverage and
normalization are still unfrozen. A second launch set must challenge
incompleteness. Occupation positivity does not certify library completeness.

Record independent time integrals of `1,vR,vz,vphi,vR²,vz²,vphi²,vR vz`
per bin, using the local cylindrical basis along the orbit. Normalize raw
integrals before forming centered dispersions; retain initial and orbital
moments separately. Response sums use positive elapsed-time weights;
crossing times, not an endpoint-only histogram, determine residence.
Compare disjoint and successively longer windows and independently refined
orbit steps. Monitor physical E and Lz as well as response convergence.
If a field table is used, derive its force from the **same differentiable
scalar potential interpolant** and check both against CD2. Independently
interpolating three force components need not define the Hamiltonian assumed
in CD5; force/potential inconsistency cannot be called orbit error alone.
An independent Cartesian integrator/field quadrature must not call candidate
orbit, interpolation, response or derivative caches. Different names sharing
those kernels are not an independent oracle. All associated error budgets,
durations, literal tables and convergence ranges must be frozen on REANA
before accepting a reference; none is supplied by this manual note.

Then implement Y14's selected route: sample fixed positions/masses from
the original densities. CD1 factors into `p(R)=R exp(-R/Rd) T(R)/Id`,
`p(z)=sech²(z/zd)/(2zd)` and uniform azimuth; symbolically
`Fz=(1+tanh(z/zd))/2`. The radial CDF and actual disk inverse/draw-purpose
law still need independent review/error budgets. Existing reviewed random
address algebra is not an accepted disk sampler. Spherical halo/bulge
position CDFs do not authorize isotropic compound velocity draws. Then
adjust velocities, one accepted proposal at a time in the first serial
reference, against density residence and the **frozen feasible** moment/
streaming targets. Recompute old/new responses deterministically. Broad
bound trial velocities may use the feasible reference as a proposal, but
a Gaussian is only a search proposal, never the final DF. No copied Y14
Gaussian/escape factor/duration/parallel batch constant is adopted.

Extend the moment audit to mixed t and full first moments; Y14 Eq.12 alone
is not our acceptance criterion. Report each component/bin, tails, support,
raw sphi and centered covariance. A merit decrease/stall is an optimization
observation; a pass requires every separate gate and the held-out orbital
audit. Seed changes, chi/regularizer adjustment or reduced sampling support
cannot conceal infeasibility. Freeze optimizer stopping/proposal/RNG and
correlation diagnostics before production; the spherical quantile sampler
does not specify this disk velocity law. Record all failures and transforms.

Finally export unchanged catalogs and run independent live gravity with
optimization disabled. The initial fixed-position catalog is not itself
an invariant measure or an exact finite-N equilibrium. Raw COM/P/L,
sampling correlations, central/tail support and the finite-N force bias
distinctions in the spherical note remain visible. Preserve original and
any explicitly allowed one-time merger assembly COM transform; never
recenter or rescale the live evolution to pass drift/stability checks.

## 6. Prospective gates and dependency order

Every row is **unexecuted**, one independent case/member per REANA workflow
after M1, source review, literal references and immutable preflight. Declare
CPU/memory, avoid nested pools; no aggregate cap. This note creates no cases.

Prospective initial resources per member: source algebra `1 CPU/2 GiB`,
compound field quadrature `1/4 GiB`, finite-cone/reference and velocity-
response cases `1/8 GiB`. Keep the parent live sphere `1/2 GiB` (validated
tree `1/4 GiB`), isolated collisionless galaxy `1/8 GiB`, gas `2/16 GiB`.
Retain parent time ceilings; calibrate bounded reference costs before larger
cases. These are declarations, not measured resource reservations or runs.

| Smallest distinct comparison | Contract/disposition |
| --- | --- |
| Manual-source fixtures | Independently differentiate CD3, the historical J1/J2 discrepancies, J5 negative control and CD4 asymptote. Test full-orbit symmetries and CD6, retaining t. No runtime result here. |
| Common-field reference | All three components, central/taper/outer probes; independent softened convolution, gradient and reconstructed field. Retain G-EQUIL-SOURCE potential/force refinement `<1e-6`; literal compound DF/field interpolation/sign budgets remain unfrozen. |
| Nonnegative feasibility | Every component in the same field; complete mass/support rows, manufactured feasible and infeasible finite cones, dual/sign uncertainty; increase orbit libraries, time windows and hold-out bins. No finite-cone success proves continuum existence. |
| Optimizer/response | Original compound target, not J5's impossible moments. Retain orbit-response density L1 `<1%` and moments `<2%` in adequately supported bins; no compensation across components or bins. Resolve normalization, near-zero/mixed-moment, DF, tail, quadrature and finite-time budgets independently before execution. |
| G-EQUIL-LIVE | Separate accepted softened sphere control: 10 crossing times, radius drift `<2%`, resolved density/moments `<5%`, internal time-mean virial residual `<2%`, raw lab energy `<1e-3`, changes from actual initial P/L `<1e-10` of fixed scales. Not compound acceptance. |
| G-GALAXY-ISOLATED / G4 | Full compound at base counts halo/disk/bulge `8192/4096/1024`, 2x/4x, three registered seeds, half dt, independent e controls; at least 10 periods at 2.2 Rd. Half-mass radius drift `<2%`, density/rotation/dispersion/thickness `<5%`, internal time-mean virial `<2%`, raw energy `<1e-3`, COM `<1e-6 Rd`, changes in initial P/L `<1e-8`; no growing m=1/m=2 above `.05` without physical review. Preserve unsupported-bin reporting and all parent controls. |
| G-GAS-GALAXY / G4 then G5 | Rebuilt gas/magnetic/source system and isolated full-duration controls before pair assembly. Retain gas no-source drift `<5%`, energy `<5e-3`, central domain/ambient sensitivity `<1%`, plus stricter bounded/source gates. G5 retains encounter/coalescence duration, H `<5e-3`, no-source M/P/L `<1e-8`, bound mass/radius agreement `<5%`, timing `<10%` and stricter bounded domain comparisons. No acceptance inferred. |

Use COM-relative `Kint` and `W=sum (x-Xcm) dot F` for the collisionless
virial gate; softening makes W different from U. Preserve raw laboratory H,
actual sampled P/L and free COM path. Parent resolved support is outside
`max(3e,2 local_cell_radius)` and at least 200 effective samples where
possible; underpopulated bins stay unresolved, not absent. Compare N at
fixed e, dt at fixed N/e, e at converged N/dt, direct versus accepted tree,
and independent domain/ambient changes. Relaxation that significantly
changes the target rejects/regenerates it, not a renamed equilibrium.

Concrete order: review CD1–CD7 and choose the still-open rotation/prior/
dispersion selection rule; freeze independent field/bin/orbit/feasibility
error packets; validate those primitives and the spherical control; solve
the compound nonnegative reference and freeze its moment profiles; implement
and independently audit Y14 optimization; pass isolated live G4; only then
assemble the intermediate collisionless encounter. A negative response
blocks escalation. This is a required intermediate, not the delivered merger.

## 7. What must change when gas, nonzero B and sources are present

Rebuild **all** collisionless orbit responses and velocity targets after the
`.02` stellar-to-gas replacement. Gas surface density is an input, not the
stellar sech² vertical solution. Supply its EOS/entropy/phase/metal profile,
ambient pressure/density and boundary-compatible field/gauge topology.
For steady axisymmetric `vR=vz=0` and scalar mixture pressure, the continuum
extension of GP9 is

```text
fB=(curl B) cross B/mu0=-grad(B²/(2mu0))+(B dot grad)B/mu0,
d_z P=-rho Phi_z+fB_z,
vphi²/R=Phi_R+(d_R P-fB_R)/rho.                           (CD8)
```

The displayed curl identity is algebraic; identifying it with the divergence
of Maxwell stress also requires div B=0, as does the intended physical model.
Require the azimuthal force/induction
conditions too: a field with fB_phi!=0 or nonstationary induction does not
give the assumed steady circular gas state. In the axisymmetric ideal
circular case `v=R*Omega*e_phi`, stationary induction additionally requires
`R*(B_R*d_R Omega+B_z*d_z Omega)=0`; an arbitrary poloidal seed can wind up.
This necessary continuum condition is not a selected field profile.
Solve CD8 jointly with gas
self-gravity, surface-density normalization, vertical tails/ambient matching
and `vphi²>=0`; an arbitrary compact A bump is boundary-compatible, not
automatically a magnetostatic disk. No square root of abs(vphi²), pressure
floor or thermal reset. Initialize conservative cell integrals by quadrature;
point A, selected cell-average B, magnetic variance, gas total energy and
phase-derived thermal pressure must obey the still-gated 3D contracts.

The first [shared bounded profile](INTEGRATION_CONTRACT.md#mesh-motion-and-physical-boundary-gate)
is finite `box-conducting-slip-relative-v1`: Bn=0, relative A/phi traces,
nonzero compact interior field and no independent mean field. Gas/ambient
remain live sources with signed wall impulse/torque/work; collisionless
particles remain unbounded under isolated gravity. No periodic-gravity or
vacuum interpretation follows. A globally finite box/ambient can spoil
exact axisymmetry; use the actual field, quantify the controlled departure
and rebuild/audit the reference, rather than certifying it with axisymmetric
CD7 alone. Discrete bounded U1–U4, moving curl/Cdot/GCL/trajectory/topology
and state-dependent motion evidence remain separate prerequisites.

Retain boxes `128/256/384 Rd`, largest-box baseline ambient mass
`<=1e-4 Mpair`, and independent `.1/10` ambient density/pressure controls.
The [bounded contract sections11.2–11.3](BOUNDARY_MHD_SPEC.md) distinguish a
hydrostatic control from a weak ambient startup transient and require full
encounter/source-duration profile, field/flux, SFR and trajectory comparisons,
net **and absolute** wall impulse/torque, reference uncertainty and signal
returns. Zero wall work/mass loss does not show isolation; low ambient mass
alone does not remove its gravity or pressure effects.

Validate source-free gas, then nonzero-B equilibrium, then the existing
`sh03-finite-phase-ira-v1` cooling/SF channels and their source ledgers.
Finite-phase pressure must agree with conserved thermal energy; an
equilibrium EOS reset is not initialization or live repair. Active cooling
and net locked star formation generally produce evolving mass/energy, so a
closed disk is not a strict stationary combined DF/source solution unless
all requisite balances are supplied. Declare the intended regulated
time-dependent isolated reference and test it; do not import collisionless
stationarity thresholds as proof of the active model. B=0 controls cannot
discharge the nonzero-B final goal. No SH03 coefficient or cooling policy
is changed by this note.

Preserve shared accepted-endpoint births: activation only at t_end after an
atomic source transaction, formation interval and midpoint population-age
estimate separate, initial stellar formation epochs explicit. Net locked
mass L is birth/current mass, gross F and prompt beta F metadata separate;
delayed return remains disabled. All species/gas use the common kernel and
unit map; gas gravity initially uses volume centroids. Retain exact signed
gas-to-star representation-energy jumps (including new-new terms), raw
mechanical/thermal/magnetic energy, radiation/feedback/metals and angular-
momentum ledgers. A new packet is not retroactively kicked through the
previous interval. A separately tested isolated **full** galaxy with these
channels precedes the actual moving-MHD gas/DM/old/new-star merger.

## 8. Disposition and source limits

The present density can remain a **conditional feasibility target**; the
constant-b shortcut cannot. CD4 demonstrates a possible local stress
scaling, not a positive global DF. CD5–CD7 give an explicit positivity/
stationarity representation and falsifiable finite reference, not an
existence guarantee. The complete numerical representation, tail/support
enclosures, prior/rotation choices, response budgets and stable live model
are still unfrozen. No parameter calibration, literal DF tables or passing
physical evidence is invented. Root inspection of this narrow corrected
inference is the next action. M1 acceptance, positive-DF/reconstruction and
independent reference gates, stable live galaxies, moving/bounded MHD,
gravity/source/domain coupling and the full-duration active magnetized
gas/DM/old/new-star merger remain unresolved/unexecuted prerequisites;
implementation and numerical execution retain their stated component and
immutable-preflight dependencies. This correction supplies no acceptance.
