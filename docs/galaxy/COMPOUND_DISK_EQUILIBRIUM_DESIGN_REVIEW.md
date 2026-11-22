# Independent review: compound disk equilibrium source proposal

2026-11-22. **Conditional source/manual-math support, with one support-claim
qualification required (finding 1).** CD1–CD4 and CD8 have the stated signs,
normalizations and dimensions. CD5–CD7 describe a useful conditional
stationary-measure/finite-library construction, not an existence proof for
a smooth positive DF. The proposed feasible-moment reference can precede
the parent's independently implemented Yurin–Springel velocity optimizer.
It does not replace that optimizer or any isolated live-galaxy gate.
No concrete obstruction to retaining the exact proposed density is
established by this review; feasibility remains unknown.

The subject **C** is commit `bbc2997`, specifically:

| Frozen subject | Bytes | SHA256 |
| --- | ---: | --- |
| `COMPOUND_DISK_EQUILIBRIUM_SOURCE_NOTE.md` | 28140 | `ccaaf3ab6b2a83573894a25be5a1e93a326a6987e1b19ec42612b85400389023` |
| `compound_disk_equilibrium_sources.json` | 25023 | `4637a216f5d843112caaabc04f21ff7c4a694a846b77f34e29203e209b6742be` |

All C line locators below refer to those bytes. C's historical context **H**
is `028876a0d7ecd13a6c71bd3fb10b88fd5948a6d6`. This review additionally pins
interface context **R** at `b8496c98c85ad7339ec461deabc012f9f08c1d90`;
it does not silently substitute R for H. Gravity, spherical/Jeans notes and
reviews, integration, bounded MHD, ISM and cooling inspected here agree
between H and R. The mesh and moving-stage specifications also agree at
those commits; they were not among C's original 24 retained context copies.
The evolving handoff differs and is status context only. Exact captures,
comparison scope and primary locators are in
[the review inventory](compound_disk_equilibrium_review_sources.json).

This is an independent **AI** source/design review, not human peer review,
a DF calculation or numerical/physical acceptance. M1 source `2bdcea0`
remains unaccepted. No scientific implementation, target import, test,
quadrature, orbit, optimizer, RNG draw, sampling, evolution, build, reducer,
workflow/service/network action, commit, push or delegation was performed.
Only the two assigned review files and ignored review reading/receipt
boundary were authored. The actual goal remains a validated, genuinely
deforming full-3D moving-Voronoi magnetized gas system with isolated gravity,
live DM/old/new stars and active published multiphase sources through a
controlled galaxy merger; a collisionless equilibrium is an intermediate.

## Primary-source scope

The complete retained [Yurin & Springel v2](https://arxiv.org/abs/1402.1623v2)
PDF is 18 pages, 1129978 bytes, SHA256
`44d4d3e8a1b1bcfa4da8567ca99275fe1ecbc5f10f0b84bb026372853f693082`.
Its arXiv version date is 19 August 2014; the printed recompile date is
5 June 2018. These are distinct fields. Relevant complete method text and
equation pages were read, with visual inspection of printed pp.3–6,8–12.
In particular, Eqs.1–7/section2.1 define the fixed-position orbital density
response; Eqs.8–12/section2.2 define **initial-catalog** moment constraints;
section2.3 p.5 gives sequential proposal acceptance and acknowledges residual
correlations. Sections4.1–4.4 pp.9–11 give binning, orbit and proposal context;
Eqs.47/50/51 pp.11–12 give untapered density families. No final-publisher
equation identity, GALIC software audit or adoption of its numerical
parameters/code is asserted.

The complete journal [Schwarzschild 1979](https://articles.adsabs.harvard.edu/pdf/1979ApJ...232..236S)
scan is 12 pages, 1322987 bytes, SHA256
`fe975b16c93eb0f498517a5debd172c0249196c1757cf30af71990cd69df211f`.
Printed pp.236–238, sectionIIa–e, were read in full; pp.237–238/Eqs.1–2
were visually inspected. Printed pp.245–247 supply the library-extension,
nonuniqueness, finite-cell and stability limitations; p.246 was freshly
rendered and inspected. The paper's attributed Lynden-Bell axisymmetric
existence statement on p.238 is not independently verified here or adopted
as a theorem for this softened target. Its example's finite-cell success
and absence of stability tests are not project evidence. No additional
external source retrieval or dependency adoption was needed.

## Numbered findings

### 1. Medium: zero occupation outside support is not a pointwise no-excursion theorem

**C:236–242; CD5 assumptions at C:163–179.** The exact nonnegative-sum
implication is correct: `sum w_q*B_out,q=0`, with every factor nonnegative,
implies `w_q*B_out,q=0` term by term. It excludes outside **mass of the
stationary measures** and cancellation by negative occupations. The phrase
“cancellations cannot hide an excursion” is stronger if it means every
point of each generating trajectory is inside support.

By CD5's definition, `B_out=lim A_out(T)/T`, where
`A_out(T)=integral_0^T 1_out(x(t)) dt`. A finite nonzero outside episode, or
more generally `A_out(T)=o(T)`, still has B_out=0. Existence of a long-time
occupation limit does not alone assert recurrence with positive visitation
frequency for every open set visited by that generating trajectory. A
forward-limit invariant measure need not retain its generating trajectory's
transient part. This logical distinction does not assert that a particular
exceptional orbit exists in CD2, nor that the target is infeasible.

**Required narrow correction:** state the consequence as `mu_q(out)=0`
for each positive-weight measure, hence exclusion almost everywhere with
respect to that measure. Keep pointwise initial-orbit/max-excursion support
as a distinct requirement with explicit invariant-support or recurrence
assumptions and finite-window/error limits. For an invariant measure on
the closed allowed region, the measure-supported flow remains inside for
almost every sampled phase point; this is not a certificate for an
arbitrary launch whose limiting measure is being used. Retain the already
required maximum-excursion, longer-window and unresolved-support failures;
do not replace them by a small residence fraction or a finite observation
with no detected excursion. S79 pp.237–238 does not supply the missing
pointwise theorem. No mass, taper, force or acceptance threshold needs to
change for this correction.

### 2. Supported: CD1 normalization, target identity and CD2 common softened field

**C:48–100.** `Id` has length-squared units. Full azimuth contributes 2pi
and the vertical integral contributes 2zd, so CD1's `4*pi*zd*Id`
denominator gives exactly Md. In the transition,
`T_s=-30*s^2*(1-s)^2`; T and its first two derivatives match the constant
branches. Near the outer edge, T is `10*(delta/DeltaR)^3+O(delta^4)`.
Thus C2 joins do not make the logarithmic derivative finite. The spherical
1/r cusps have integrable volume mass, and the disk's exponential R factor
is not Cartesian-differentiable at the axis. Retaining those facts is
correct; softening does not redefine their raw position densities.

CD2 follows by differentiating the negative Plummer convolution:
`grad_x[-G/sqrt(s^2+e^2)]=G*(x-y)/(s^2+e^2)^(3/2)`.
Acceleration is its negative, as printed. Phi and h are specific energies
with units L^2/T^2; acceleration has L/T^2. For fixed e>0 the kernel and
its derivatives are bounded, and the finite total source mass controls
the convolution despite central density cusps and the disk tail. All
components see the same isolated field and infinity zero. The SI/code
conversion including `B0=V0*sqrt(mu0*M0/L0^3)` is dimensionally consistent.
No sum of unsoftened analytic component potentials or isolated spherical
isotropic DFs solves this combined flattened problem.

Retain the exact post-taper `.85/.12/.03` masses, `10/.2/.2 Rd` scales,
stellar 8–10 Rd and spherical 100–200 Rd tapers, infinite stellar vertical
support, and `.05 Rd` softening with `.025/.1` controls. These are project
choices, not Y14 calibration. A binned orbit-density fit must independently
regenerate CD2 within a frozen field error budget; it does not become
self-consistent merely by using a fixed target potential during fitting.

### 3. Supported: CD3/CD4 retain the J1–J5 exclusion without excluding the density

**C:104–159; H Jeans review findings1–5.** Multiplying the stationary
cylindrical CBE by vR and vz and integrating, with vanishing velocity-space
boundary terms, gives the two CD3 equations. The radial curvature terms
are `rho*(sR-sphi)/R`, and its mixed derivative is `partial_z(rho*t)`.
The complete Y14 p.8 really prints an R derivative in Eq.24 instead.
Its post-Eq.33 axis paragraph also lacks J2's fixed-z `1/z` factor. These
are source/manual-derivation discrepancies, not a publisher erratum or a
claim about GALIC implementation. At t=0 the derivative discrepancy cannot
be tested. The prior tilted/axis negative controls remain necessary.

For the local untilted alternative, let
`rho=A(z)*delta^p*(1+O(delta))`,
`sR=kappa(z)*delta+O(delta^2)` with the stated differentiated-remainder
control. Then

```text
partial_R(rho*sR)/rho=-(p+1)*kappa+O(delta),
sphi=sR+R*Phi_R+(R/rho)*partial_R(rho*sR)
     -> Rout*(Phi_R-(p+1)*kappa).
```

For p=3 this is CD4's factor 4 and its acceleration-valued kappa.
Nonnegative sR and limiting raw sphi require
`0<=kappa<=Phi_R/4` where Phi_R>=0. This is a necessary local condition,
not sufficient for the vertical equation, higher moments or a DF. Under
the separate J4 positive finite vertical limit, constant positive
`b=sR/sz` instead gives `sphi=-3*Rout*b*s0/delta+O(1)`, which cannot be a
raw second moment. Streaming cannot repair that negative control.

The flexible-stress proposal correctly abandons only an unselected
closure. It does not assert a solved global tilted model or require a
density amendment from this argument. Covariance positivity, full mixed
moments and central integrated diagnostics remain necessary. Smooth-axis
tensor limits require smoothness assumptions that a cusped density does
not provide; positive e smooths the force, not the target DF/stress. Do
not fill the origin with a finite-core DF or impose a direction-dependent
tilt formula there. No global DF sign or central regularity was computed.

### 4. Supported with the stated limits: stationarity and whole-orbit symmetries

**C:163–207.** On each exact bound orbit of the smooth static CD2
Hamiltonian, the normalized occupation limit, if it exists, obeys CD5:
the time integral of `{g,h}` is the bounded endpoint difference. On its
compact orbit closure the smooth generator is continuous/bounded, which
permits this test of a weak limit. Nonnegative finite-mass sums of those
invariant measures remain invariant. This establishes weak stationarity,
not absolute continuity, a smooth DF, completeness, stability or a finite-N
equilibrium. In particular, arbitrary phase-space histogram smoothing is
not an operation known to commute with Hamiltonian flow.

The symmetries are appropriate **measure pushforwards of entire orbits**.
Axial rotation commutes with the flow. Q reflects a meridional plane and
reverses vphi; time reversal T reverses all v and conjugates forward to
backward flow. QT therefore changes `(vR,vz)` together, retains vphi and
preserves `vR*vz`. Averaging the QT pair cancels meridional first moments
and cross moments with vphi without erasing t. Midplane reflection maps
`(z,vz)` to `(-z,-vz)`, making density/even moments even and t odd in z.
Separate local flips of vR or vz would erase t and are not justified as
whole trajectories. Finite response construction must transform the
whole track/window consistently; the invariant-measure argument alone
does not establish equality of independently truncated forward/backward
windows for an unsaturated orbit.

After these symmetries, Q pairs have equal spatial and raw even moments.
CD6's weights are nonnegative exactly when |eta|<=1, sum to w, and give
the stated angular momentum. Here `Lz_q` must be understood as **specific**
angular momentum, units L^2/T, so `w_q*Lz_q` has mass-angular-momentum units.
Their streaming changes centered azimuthal dispersion while leaving raw
sphi fixed. Equal counterrotation is not isotropy or a stability result.
Constant eta_d, its value, feasible total Lz and interior hotness remain
physical choices to freeze before production fitting; no value is supplied
by the source papers or this review.

### 5. Supported finite cone; exact infinite-tail representation and DF existence remain distinct

**C:209–250,270–299.** B is dimensionless residence probability, d and w
are masses. Positivity gives nonnegative binned reconstructed mass and the
support implication in finding1. For the complete frozen equality system
including mass rows, `Bw=d,w>=0`, a dual with `B^T*y>=0,d^T*y<0` is a valid
finite-cone contradiction: `d^T*y=w^T*(B^T*y)>=0` would be required.
Additional linear constraints must appear in that complete system, with
slack/dual sign conventions when they are inequalities. An infeasibility
claim about nonlinear kinematic/regularization constraints does not follow
from a dual of the displayed smaller equality system. Constraint scaling,
response/target uncertainty and strict dual sign enclosures must be frozen
before a numerical certificate; an optimizer message is not that certificate.

S79 p.238 explicitly separates inadequate orbit coverage from model
infeasibility and cautions about replacing continua by finite sets; p.246
again denies a mathematically safe existence inference from the numerical
model. C correctly retains these limits. A second launch set, library/time
refinement and held-out partitions are necessary challenges, not completeness
proofs. Failure of any one finite cone blocks that candidate IC, not all
continuum DFs. Conversely, success cannot establish a smooth positive DF.

There is a useful exact limitation to carry into the reference budget: each
bound E<0 orbit in this finite-mass isolated potential has bounded spatial
support. A **finite** sum of such measures therefore has some finite maximum
|z|, whereas CD1 has positive mass beyond every finite Z. Its exact tail
fraction is `1-tanh(Z/zd)`. A finite orbit library can approximate specified
tail masses/moments/forces to stated errors; it cannot equal this continuum
density everywhere. This is consistent with C's conditional finite/binned
scope, not a new proof against the target or a reason to cut its tail.
The continuum/DF limit needs suitable expanding near-escape coverage and
tail enclosures, with central/cusp and thin-orbit concentration checks.
The recommended positive-prior concentration regularizer is a selection
rule, not a source-proved smoothness or stability mechanism. Its prior,
selection and roughness/concentration acceptance criteria remain unfrozen.

### 6. Supported optimizer route and bin factors; literal reference choices are still prerequisites

**C:254–330; Y14 pp.3–5,9–11.** Full-azimuth signed-z bin volume is
`pi*(R_hi^2-R_lo^2)*(z_hi-z_lo)`. Folding both z signs doubles it, as
Y14's positive-quadrant Eq.40 does. Odd-z moments must transform rather
than be doubled as even scalars. CD1 also correctly factors into its
normalized radial marginal, `sech^2/(2zd)` vertical marginal and uniform
azimuth; integrating the latter vertical marginal gives the stated Fz.
No radial inverse, physical CDF or random draw was evaluated here.

The proposal preserves fixed positions and adjusts velocities, rather than
replacing the parent with an orbit-weighted final catalog. Deriving feasible
stationary moment targets first is an explicitly additional engineering
reference, compatible with that selected route. Y14 Eq.8 uses initial
particles in each bin and Eq.10 uses the target mass integral; its merit
does not already validate orbital moments. C correctly requires both,
full first/mixed moments, centered covariance and independent held-out
orbital responses. A Gaussian can propose velocities but is not a DF.
Convergence/stall of a weighted merit cannot compensate for a failed
component/bin, wrong support or impossible moments.

Crossing-time residence, not endpoint counts, and a force derived from
the same differentiable scalar interpolant preserve the intended
Hamiltonian interpretation. Both potential and force still need separate
comparison to CD2; their internal consistency alone does not show accuracy.
The independent integrator/convolution/derivative oracle must not share
candidate caches/kernels. Central, joins, tails, signed/near-zero moments,
streaming, sign/support, finite windows and sampling each need their own
scales/error allocations. The existing `<1e-6` field, 1% density and 2%
moment limits do not define those allocations or a DF/CDF budget.

Before numerical references/ICs, freeze actual libraries/launches, bins and
validation partitions, rotation/hotness/prior choice, precision/quadrature/
interpolation/time controls, literal independent tables, support/sign failure
policies, optimizer proposals/stopping and disk CDF/RNG/correlation policy.
These openly unchosen inputs block a production compound IC, not source
support for CD1–CD7's scoped primitives. No bins may be deleted/coarsened
after failure, nor catalogs repaired by live velocity rescaling or seed
selection. Raw initial-catalog sampling bias and correlations remain visible.

### 7. Supported CD8 signs and induction restriction; no gas solution has been selected

**C:374–401.** For scalar P and steady circular flow, radial acceleration
is `-vphi^2/R`; the radial momentum equation is therefore
`-rho*vphi^2/R=-P_R-rho*Phi_R+fB_R`, giving CD8. Its vertical equation
also has the correct sign. `fB=(curl B) cross B/mu0` has force-density
units. The displayed tension-minus-magnetic-pressure identity is algebraic;
`div[(BB-B^2*I/2)/mu0]` additionally contains `B*div B/mu0`, so its use as
the physical Maxwell-stress divergence requires div B=0 as C states.

In axisymmetry, `v cross B=R*Omega*(Bz*eR-BR*ez)`. With div B=0 its
curl's phi component is `R*(BR*Omega_R+Bz*Omega_z)`. Thus C's stationary
induction condition is correct; an arbitrary poloidal seed generally winds.
The azimuthal momentum equation also needs fB_phi=0 for the assumed
steady circular state. Those necessary conditions do not choose a field,
solve induction/force balance, or prove MHD stability.

After `.02` stellar-to-gas replacement, the new `.85/.10/.03+.02` density,
gas vertical structure, self-gravity and every collisionless response/target
must be rebuilt. Surface density alone is not a 3D gas equilibrium.
EOS/entropy/phases, nonzero field topology, ambient matching and nonnegative
vphi^2 remain physical/source inputs; abs-root repairs or pressure floors
would change the problem. Conservative volume integrals, curl-recovered B,
magnetic variance and phase-derived thermal pressure must agree. CD8 has
not supplied or accepted a gas profile or a stationary finite-phase state.

### 8. Supported bounded/source interfaces and honest time dependence

**C:403–445; H/R integration and bounded sections11.2–11.3.** The
conducting-slip box, Bn=0 relative traces, nonzero compact interior field,
no separate mean, live ambient and isolated unbounded particles agree
with the actual shared profile. A finite box/ambient need not be exactly
axisymmetric: a CD7 axisymmetric fit alone cannot certify that field.
Rebuild/audit actual departures. The note correctly retains separate
bounded U1–U4, moving Cdot/GCL/topology and state-dependent motion gates;
a compact A bump guarantees neither magnetostatic balance nor isolation.

The 128/256/384 Rd boxes, largest-box baseline ambient mass bound and
independent .1/10 pressure/density controls are retained. The cited parent
requires both the hydrostatic control and honest weak-startup treatment,
net and absolute wall impulse/torque, signal returns, common physical
times and one-fifth-reference-uncertainty limits. C's summary does not
override those stricter observables. Zero wall work or small ambient mass
does not waive immediate ambient gravity, pressure or reflection effects.

Active cooling and net locked star formation generally change gas mass,
energy and the common potential. Absent a supplied physical balance the
active isolated galaxy must be a specified time-dependent reference, not
a stationary DF certified by collisionless drift thresholds. The source-free
and B=0 controls remain intermediate; neither discharges the active,
nonzero-B merger. Finite-phase thermal energy/pressure consistency and no
duplicate eEOS/SN heating remain separate ISM requirements.

The accepted-endpoint birth summary agrees with the actual interface:
retain one nonzero-L packet per actual successful subinterval, its midpoint
and interval, then activate all packets atomically at the accepted global
endpoint without a preceding kick/drift. Net L, gross F and prompt beta*F
are distinct; delayed returns stay disabled and initial ages require
configured epochs. All before/after gravitational pairs including new-new,
gas-centroid representation changes, raw energies and signed source/
radiation/feedback/metals/angular-momentum channels must remain explicit.
Reporting an adjusted energy residual does not waive the parent's signed
representation ledger or representation-error convergence gate.

### 9. Supported unchanged parent gates and internal virial frame

**C:334–370; H/R gravity sections9–11.** No weakening of the named
G-EQUIL-SOURCE, G-EQUIL-LIVE, G-GALAXY/G4/G5 limits was identified. The
source field refinement remains `<1e-6`, orbital density L1 `<1%`, supported
moments `<2%`; inversion/compound DF and reference budgets are separately
pending. The sphere retains ten crossings, radius `<2%`, resolved profiles
`<5%`, internal time-mean virial `<2%`, raw lab energy `<1e-3` and changes
from actual initial P/L `<1e-10` fixed scales. Compound galaxies retain the
base counts/2x/4x, three seeds, half-dt, epsilon controls, ten periods at
2.2 Rd, radius `<2%`, density/rotation/dispersion/thickness `<5%`, virial
`<2%`, energy `<1e-3`, COM `<1e-6 Rd`, P/L changes `<1e-8` and the `.05`
m=1/m=2 physical-review condition. Parent algebra/time-order, direct/tree,
resource/time-ceiling and resolved-support conditions remain operative.

For fixed-mass closed collisionless particles, put `r_i=x_i-Xcm` and
`c_i=v_i-P/M`. Since `sum m_i*r_i=sum m_i*c_i=0`, differentiating
`Icm=sum m_i*r_i^2` gives

```text
Icm''/2=sum m_i*c_i^2+sum r_i dot F_i=2*Kint+W,
Klab=Kint+P^2/(2*M),
2*Klab+W=(2*Kint+W)+P^2/M.
```

C correctly uses velocity-deviation Kint with COM-relative W for its 2%
virial gate and keeps laboratory H and actual nonzero initial P/L for
conservation. For the softened kernel W is not generally U. Density and
velocity bins retain gravity section9's explicit model/COM frames and free
COM path, not hidden recentering. A closed collisionless virial theorem is
not asserted for bounded, magnetized, actively sourcing gas.

The separate source/probe distinction is also retained: an independent
external probe includes all N sources. Only for independent equal-mass
sampling does a tagged particle's self-excluded N-1 source field have
conditional mean `(N-1)/N` times the continuum field at its position.
SHA determinism does not certify IID draws; correlated/paired or optimized
catalogs require their own conditional reference, not a force/velocity fix.

Gas no-source drift/energy/domain and G5 mass/energy/radius/timing limits
are preserved together with the stricter bounded/source comparisons.
Unsupported bins remain unresolved, not removed. N, dt and epsilon changes
address different errors and must remain separate. A failed finite-cone,
source, support, live or boundary gate blocks dependent escalation; it
does not authorize an easier density, live repair or a changed acceptance
threshold. All future independent cases remain separate REANA workflows
after M1 and their immutable source/reference/preflight dependencies, with
declared per-job resources and no aggregate cap.

### 10. Source/readiness disposition and document-only evidence

**C:447–458.** The complete primaries support the limited method map;
CD1/CD2/CD4–CD8's project-specific extensions are correctly identified as
manual/engineering constructions. No source-access gap for the two
required complete primary methods was found. No AREPO/GALIC code or
calibration is imported. Finding1 needs the narrow measure/trajectory
qualification before the support statement is used as a theorem.

After scoped M1 acceptance and each applicable frozen reference/preflight,
CD1/CD2 field/normalization, source algebra/symmetry, scalar-potential/
force consistency, crossing-residence and manufactured finite-cone/dual
primitives have a defensible source basis for small independent slices.
They cannot be credited with solving the production compound target.
The open physical rotation/hotness selection and numerical reference
budgets in finding6 must be frozen before actual compound fitting/ICs.
Positive continuum DF/reconstruction, finite-library/support convergence,
stable independently evolved live galaxies, joint gas/nonzero-B/phase
construction, tracer-domain/source-duration validity, moving/bounded MHD,
gravity/source coupling and full encounter evidence remain prerequisites.
Optional later optimizer parallelization or a different regularizer is
not a demonstrated repair for any of these missing gates.

Both frozen subject identities match Git and the working files. All 45
entries closed by the author's retained receipt match bytes/hashes; all
24 pinned context copies match their exact H Git blobs. Fresh review
captures retain those files/receipt, both subject blobs, 20 R context
blobs and two additional H mesh/stage blobs. An initial comparison marked
the latter two as unmatched because they had no copy in the author's
24-file context subset; an explicit additional Git comparison establishes
that they are unchanged, rather than interpreting absence as changed
source. This check limitation/correction is retained, not hidden. The
handoff's later status bytes are separately pinned, not evidence of a
scientific pass. Document JSON/identity/link/whitespace checks and fresh
PDF source renders are recorded in the closed review receipt. No numerical
feasibility, source kernel, sampler, live equilibrium, M1 or merger result
was executed or accepted.
