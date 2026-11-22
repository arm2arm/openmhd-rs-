# Independent AI review of the ISM and cooling design

2026-11-22. Separate AI reviewer, not the specification author, human peer
review, author confirmation, or numerical validation. No delegation.

**Recommendation: revise the birth/substep interface before coupled source
implementation; conditionally approve the transcribed equation kernels and
the explicitly named cooling model for subsequent gated implementation.**
The adopted atomic formulas, negative dielectronic correction, signed CMB
derivation, SH03 phase equations and integrated mass/energy/metal identities
are supported. Finding 1 is a concrete interface blocker. Findings 6, 7, 9,
10 and 13 identify prerequisites for physical use and reproducible acceptance;
they are not evidence that an unexecuted model has numerically failed.

M1 numerical source remains frozen at `2bdcea0`. This review changes neither
M1 acceptance nor its live physical campaign. The intended endpoint remains
a deforming 3D magnetized merger with live gas, dark matter and existing/new
stars, behind the M2, gravity, source, bounded MHD and isolated-galaxy gates.

## Reviewed inputs and actual work

The review checkout was `23ab6187d75859572b5a718d62e2d943b5bd74cf`;
the two specifications/source inventories originated in `c3969e1`.
The following working files were byte-identical to the review checkout:

| File | SHA256 |
| --- | --- |
| `ISM_STAR_FORMATION_SPEC.md` | `76f1938b7ed77d36351435decd5366c31b0709546edca3e900523e593a3d244c` |
| `COOLING_RATES_SPEC.md` | `35e6b0194e0ded07457bf1f5045adf3113d604f73049f05a3277459e4212773b` |
| `ism_star_formation_sources.json` | `a7dcb381fb666349b039face65960d88916c4d7e3ce03cdfb72c0af42b10b407` |
| `cooling_rates_sources.json` | `e6f9bda49b179c9227171ed58ba1972d7f39c29034afb3af34f846e426389f6c` |
| `INTEGRATION_CONTRACT.md` | `f742fb818b374b6dd2ee86400c5a3f90e6c00d64bc80e395cb87db84a4763509` |
| `GRAVITY_PARTICLES_SPEC.md` | `d2e0d3249b5bad0962a109ad17261948c47a3230fb0087eb38cf1336771da7ff` |
| `BOUNDARY_MHD_SPEC.md` | `c08be57d86c4a3a8de9b8dd36a74cfc695103661f4169d64e30c021bfef4b7a0` |

The companion [review inventory](ism_cooling_review_sources.json) records
exact primary-file hashes, locators, inspected equation images, checks and
finding dispositions. I checked all **24 unique inventoried downloaded
artifacts**, including the explicitly failed retrievals, against their
recorded lengths/hashes; all matched. The selected archive members matched
their extracted files. The archive has 14 members and no LICENSE/COPYING
member. These are integrity results only.

I inspected the equations and surrounding qualifications in the complete
downloaded final SH03, KWH, Black and Cen PDFs and FG20 arXiv v2, rather than
using their abstracts as an equation source. Exact mathematical scope is in
the findings below; this is not a rederivation of the papers' unrelated SPH,
cosmological transfer or AGN-population algorithms. Published KWH Tables 1-2,
the preprint table, Black Table 3, SH03 pp. 291-294 and 297-298, Cen's CMB
and coefficient equations, and FG20 Table D1 were visually inspected. Black
Eq. (9) was additionally rendered directly in memory from the hashed PDF.
I read the relevant shared/gravity/boundary contracts and current project
requirements. No scientific code, tests, evolution, production reducer,
workflow/service control, commit or external outreach was performed.

Primary texts: [SH03 final](https://articles.adsabs.harvard.edu/pdf/2003MNRAS.339..289S),
[KWH final](https://articles.adsabs.harvard.edu/pdf/1996ApJS..105...19K),
[KWH preprint](https://arxiv.org/pdf/astro-ph/9509107v1),
[Black final](https://articles.adsabs.harvard.edu/pdf/1981MNRAS.197..553B),
[Cen final](https://articles.adsabs.harvard.edu/pdf/1992ApJS...78..341C),
[FG20 v2](https://arxiv.org/pdf/1903.08657v2). The archive's selected bytes,
not an unpinned URL response, define the external input reviewed here.

## Numbered findings

### 1. Blocking interface conflict: subinterval formation versus activation

ISM [lines 530-538](ISM_STAR_FORMATION_SPEC.md#L530) plan a packet for each
source interval, retain that interval and its midpoint, but activate all
packets at the accepted full-step endpoint. Local subcycling is expressly
allowed at lines 763-766. Gravity [lines 586-594](GRAVITY_PARTICLES_SPEC.md#L586)
instead requires `formation_interval.end = activated_at`. These cannot both
hold for the first of two source subintervals committed at one global
endpoint. For `[t0,t1]` and `[t1,t2]`, the first packet has interval end `t1`
and activation `t2`; a gravity validator following line 590 rejects it.
The shared contract correctly distinguishes age estimate from activation,
but does not settle this subinterval case.

**Resolution before coupled implementation:** choose one consistent schema.
I recommend preserving each packet's actual source interval and permitting
`formation_start <= formation_time <= formation_end <= activated_at`, with
all dynamical activations at the accepted global endpoint. This preserves
the selected per-interval deterministic policy and its age metadata. An
alternative is one aggregate packet per cell/global step with explicitly
aggregated mass/metals and an interval/age estimator; it must not be silently
substituted for the stated no-merging reference. Either choice requires the
coordinator to reconcile the shared and gravity contracts. No earlier kick
or drift is added. A REANA transaction case must cover two source substeps,
branch-event subdivision, a rejected outer step and restart, verifying
intervals, ages, atomic activation, unique IDs and no consumed retry IDs.

### 2. Atomic transcription and named dielectronic correction are supported

KWH final PDF p. 6, printed p. 24, Table 1 and Eq. (23), and PDF p. 7,
printed p. 25, Table 2 are the authoritative adopted network. Comparing
each entry with cooling lines 135-176 and ISM lines 365-411 gives:

| Channel | Independently checked factor, with kelvin-valued T | Density factor |
| --- | --- | --- |
| H I excitation | `7.50e-19 exp(-118348/T)/D5` | `ne nHI` |
| He II excitation | `5.54e-17 T^(-.397) exp(-473638/T)/D5` | `ne nHeII` |
| H I ionization | `1.27e-21 sqrt(T) exp(-157809.1/T)/D5` | `ne nHI` |
| He I ionization | `9.38e-22 sqrt(T) exp(-285335.4/T)/D5` | `ne nHeI` |
| He II ionization | `4.95e-22 sqrt(T) exp(-631515/T)/D5` | `ne nHeII` |
| H II recombination | `8.70e-27 sqrt(T) T3^(-.2)/D6` | `ne nHII` |
| He II recombination | `1.55e-26 T^.3647` | `ne nHeII` |
| He III recombination | `3.48e-26 sqrt(T) T3^(-.2)/D6` | `ne nHeIII` |
| He II dielectronic | `1.24e-13 T^(-1.5) exp(-470000/T) [1+.3 exp(-94000/T)]` | `ne nHeII` |
| Free-free | `1.42e-27 gff sqrt(T)` | `ne (nHII+nHeII+4nHeIII)` |

Here `D5=1+sqrt(T/1e5)`, `D6=1+(T/1e6)^.7`, `T3=T/1e3`, and
`gff=1.1+.34 exp[-(5.5-log10(T))^2/3]`. Products are volumetric losses in
`erg cm^-3 s^-1`; the fitted constants carry the implicit kelvin powers.
No factor of electron density or ionic charge is missing or duplicated.

The seven coefficients in `cm^3 s^-1` also match KWH Table 2:
`alphaHII=8.4e-11 T^(-.5) T3^(-.2)/D6`,
`alphaHeII=1.5e-10 T^(-.6353)`,
`alphad=1.9e-3 T^(-1.5) exp(-470000/T)[1+.3 exp(-94000/T)]`,
`alphaHeIII=3.36e-10 T^(-.5) T3^(-.2)/D6`, and the three collisional
ionization factors `sqrt(T) exp(-E/T)/D5` with
`(coefficient,E)=(5.85e-11,157809.1),(2.38e-11,285335.4),
(5.68e-12,631515)`.

**C1 adjudication:** final KWH Table 1 prints a positive `470000/T`;
KWH preprint Table 1, PDF p. 13, prints the negative sign. Black final
Table 3, printed p. 557/PDF p. 5, has the negative sign in cooling;
Black Eq. (9), p. 556/PDF p. 4, and KWH Table 2 have it in recombination.
Cen Eq. (14), p. 345/PDF p. 5, also has negative dielectronic cooling.
The negative choice is independently supported. Dividing the corrected
cooling coefficient by `alphad` cancels its T dependence and gives
`(1.24e-13)/(1.9e-3)` erg per recombination, consistent with Black's
surrounding explanation in terms of He+ excitation energy. The positive
version instead introduces `exp(940000/T)` in that ratio and diverges at
low T. Approve **`kwh96-dielectronic-sign-correction-v1`**, not an invented
official erratum or a claim of literal published-table evaluation.

One additional lineage detail merits recording: Black Eq. (7), p. 556,
prints the He II recombination exponent `-.6533`; KWH Table 2, both
versions, and Cen Eq. (27b), p. 347, print `-.6353`. The contract follows
the latter unambiguously. Do not claim identical transcription of every
Black expression, or silently change this separate coefficient. Black's
metastable helium and other extra channels are deliberately excluded.
**Disposition:** equation-kernel source approval, still no evaluated-value
or accuracy evidence. Independent high-precision REANA channel fixtures
must retain all constants, powers, signs and species products separately.

### 3. Ionization closure is correct; distinguish its uniqueness from other roots

Cooling lines 179-214 reproduce KWH Eqs. (25)-(38), printed pp. 24-25,
without the unsafe `Gamma/ne` divisions. With electron trial `e>0`, define
`a=cHI e+GammaHI`, `b=alphaHII e`,
`c=cHeI e+GammaHeI`, `d=(alphaHeII+alphad)e`,
`j=cHeII e+GammaHeII`, `k=alphaHeIII e`.
The normalized weights are `H:(b,a)` and `He:(dk,ck,cj)`.
Then charge neutrality is `e=Q(e)=nH fHII+nHe(fHeII+2fHeIII)`.

For finite positive recombination coefficients and nonnegative photo rates
at fixed T, each forward/backward ratio is of the form
`c/alpha+Gamma/(alpha e)`, nonincreasing in e. The mean charge of the
two/three-state chain increases with either ionization ratio, so Q is
nonincreasing; `e-Q(e)` is strictly increasing. The positive physical
root is unique on the stated electron interval. Zero UV leaves constant
collisional ratios, hence this selected positive-electron limiting root;
the all-neutral algebraic root lost by cancellation is not that branch.
Handle exact vanished/underflowed rates through explicit limiting/log-scaled
weights, not a fake electron floor. Generic zero-rate inputs still need
separate cases; the uniqueness statement does not cover arbitrary singular
networks after coefficients have been rounded to zero.

`nH=X rhoh/mp`, `nHe=Y rhoh/(4mp)`,
`mu=rhoh/[mp(nH+nHe+ne)]` and `u=3 kB T(nH+nHe+ne)/(2 rhoh)` are
consistent with KWH's thermal convention and `P=(gamma-1)rhoh u`.
`rhoh=mh/V` is the coarse-grained hot density, not total gas density or
an unresolved filling-factor density. Ionization binding energy is not a
second evolved reservoir; adding it while retaining Table 1 ionization
losses would change the model and double count losses.

The electron uniqueness argument does **not** certify monotonicity of
the nested `u(T)` map, roots of `Lambda_net=0`, or nonlinear implicit
source roots. A sign bracket alone finds a root, not all roots or their
stability. Before physical use, specify the finite T search/ambiguity
policy, and use an independent T/energy scan plus a separate abundance
solver on REANA. Retain every detected bracket/branch; do not label
convergence of one Newton iterate proof of uniqueness. No root ambiguity
was measured here.

### 4. Signed CMB exchange, constants and unit conversions pass source/algebra review

Cen final p. 346/PDF p. 6 Eq. (17) defines u as internal energy **density**.
Substitution into that printed equation gives

```text
-(8/3) sigmaT/(me c) (ne/npart) (1-Tr/T) (aR Tr^4)
       * (3/2 npart kB T)
 = -4 sigmaT aR kB/(me c) ne Tr^4 (T-Tr).
```

Thus the proposed loss has the right normalization, sign and density power:
zero at `T=Tr` or `ne=0`, heating below Tr and cooling above. With
`Tr=T0(1+z)`, it tends to a coefficient times `ne T(1+z)^4` at high T.
The historical KWH p. 24 Eq. (24) coefficient `5.41e-36` is a comparison,
not an additional loss. Cen Eq. (18)'s diffuse-X-ray exchange is separate
and excluded. The blackbody expression
`aR=8 pi^5 kB^4/(15 h^3 c^3)` is consistent with `aR=4 sigmaSB/c`.

The six specified constants match the pinned NIST **2022** listing, and
`T0=2.72548 K` with measurement uncertainty `.00057 K` matches Fixsen v2's
abstract/combined determination. Treat kB, h and c as exact SI defining
values; mp, me, sigmaT and the fixed observational central T0 are not exact
measurements. The conversion factors `rhoCGS=1e-3 rhoSI`,
`uCGS=1e4 uSI`, `nCGS=1e-6 nSI`, `LambdaSI=.1 LambdaCGS` and
`energySI=1e-7 energyCGS` are dimensionally correct.
**Disposition:** approve this named amendment's algebra; REANA still must
compare independent SI/cgs paths, near-cancellation, both CMB signs and the
normalization difference. A pure CMB test below 1000 K does not extend the
full atomic backend's domain.

### 5. FG20 identity, normalization and interpolation are adequately distinguished

The selected 195-row, seven-column member is the **unrescaled effective
default**, not the archive's recommended `.68` variant. Exact SHA256s:

| Input | SHA256 |
| --- | --- |
| `fg20_102720_rescaled.zip` | `587a27854de50c95d79901b514d9acee421119ca41ff483eaeea84b6d695d49d` |
| `README.dat` | `df0e37f35c9b8abae618094e162b5a9ef0133be5a119cb8e2957200e05e88939` |
| `fg20_treecool_eff_default.dat` | `c6e6030be92c6965c019c53915f31661782eb2cafed058cf9672b7efefc24aaa` |
| unselected `.68` member | `4bfc5d9bd6f0541addd01256ac20b5e6bc8a7aa5fc8849b9cbdf34cb0882b313` |
| unselected thin member | `3adbff8572c5d4fcb3dd9e209d3d43028686a7cdc6f31263cfc7ac7b6b71d7d9` |

I independently checked the selected decimal axis: 0 through .970 by .005,
so its redshift domain is exactly `0 <= z <= 10^.970-1`, not `z<=10`;
all six rates are positive, minimum `1e-40`. The `.68` member has the same
195 axes and unchanged ionization columns; heating columns agree with
the stated scaling to their different decimal printing precision, not
necessarily exact bitwise multiplication of rounded default values. Its
tiny values include `6.8e-41`. The thin member has 501 rows, ends at
`q=1.0413926851582251`, and has exact zeros; it cannot use the selected
positive-only interpolation profile silently.

FG20 v2 Eqs. (7)-(8), PDF p. 4, and Eq. (27), p. 13, establish that Gamma
is per-target `s^-1`, qdot per-target `erg/s`, with the spectral integral's
`4 pi` already included. `H=sum ni qdoti` is correct: no extra ne, 4 pi,
threshold energy or division by Gamma. The README prints only `log(1+z)`;
the thin table's explicit z=10 endpoint and Appendix D p. 20/Table D1
support base ten. The z=0 row agrees with Table D1 at its printed precision;
the table's Gamma and qdot column scales are `1e-12` and `1e-24` respectively.
Coarse printed rows are not exact nodes of the .005-q member in general.

Section 3, PDF pp. 11-14, constructs effective rates to prescribe a
homogeneous-equilibrium reionization history, not a spectrum during
reionization. Thin spectral rates are a distinct model. At fixed isolated
z=0 the reference does not perform reionization. Its exact member/version,
interpolation, z and constants must be hashed into threshold calibration.
Historical SH03's modified HM96/Dave history is not recovered; FG20 is an
explicit replacement. The arXiv record verifies v2 dated 2020-01-29; the
263-byte purported final PDF is AccessDenied XML. This review does not
claim final-publication equation parity or recover missing historical bytes.

The proposed log-rate/linear-q interpolation is a reasonable named
engineering choice. It must preserve exact parsed nodes, retain tiny
positive entries, reject invalid/out-of-range z, and never log a signed net
rate. Freeze how floating-point q/z endpoint roundoff is distinguished from
real extrapolation, with adjacent-representable boundary cases. No source
establishes its interpolation error against an exact UV curve. The ISM
`ism-rates` row at line 805 must distinguish interpolation-implementation
agreement with an independent formula from physical interpolation accuracy;
there is no effective spectrum available as a direct oracle before
reionization. **Disposition:** source identity/normalization approved;
parser, interpolation and physical-use evidence pending.

### 6. External operator input can support private science, not an assumed public mirror

The downloaded author page links data for scientific use; its README gives
simulation replacement instructions. Neither is an explicit verified
downstream redistribution/relicensing grant. The original archive contains
no LICENSE/COPYING entry; the arXiv article's nonexclusive distribution
license is not a data grant, and the repository's MIT license does not
relicense this input. This is an evidence/access assessment, not a legal
determination that private use or redistribution is lawful or unlawful.

The contract's operator-supplied external-input boundary is acceptable for
design and privately controlled scientific evaluation: independently written
code accepts a user-supplied immutable table, checks its archive/member
identity and records model provenance. Private REANA execution is still
subject to operator authorization and a concrete access/retention plan;
supplying the file to a remote workflow is not automatically authorized by
this source review. No table fetcher, vendored copy, public workflow raw
input, mirror or raw artifact publication is approved here.

**Required before execution/packaging:** select a private-input path with
operator-controlled access and an explicit artifact allowlist that excludes
the table/archive and accidental copies in logs, configs or checkpoints.
Keep private exact-byte verification and public source/hash/instruction
metadata distinct. Public reproducibility remains conditional on users
independently obtaining the same external bytes and access persisting; hashes
do not guarantee future availability or confer permission. Before public
redistribution, archive a verified applicable grant or select an explicitly
licensed substitute, name the new model and redo rate/threshold calibration.
No external outreach or legal permission was invented. This finding does
not block source-only coefficient work or synthetic reference fixtures.

### 7. Accept an explicit analytic evaluation domain, not universal physical accuracy

Cooling lines 397-415 request `1e3 <= T <= 1e8 K` and positive finite hot
density. Black p. 557 explicitly qualifies his unmodified expressions by
approximately `5e3-5e5 K`; KWH p. 24 explicitly adopts Cen modifications
for proper high-T behavior above `1e5 K`. Cen pp. 345-347 supply the rate
forms, not a precision guarantee for all densities or arbitrary temperatures.
There is no source-supported universal density cutoff in these inputs.

**Disposition:** the requested interval can define the named KWH analytic
model's computational evaluation interval, provided the author explicitly
records the low-T tail as a model extension beyond Black's stated interval
and does not call `1e3-1e8` a verified physical-accuracy domain. It is not
source approval of primordial optically thin equilibrium for any positive
density, a molecular cloud, a newly shocked non-equilibrium plasma, or a
relativistic/two-temperature plasma. No numerical domain calibration has
been supplied. The fixed cold reservoir never enters the ordinary backend;
it is a coarse-grained phenomenological phase rather than a molecular rate
calculation.

Before physical one-zone/disk use, freeze actual density/T/UV bounds and
justify the optically thin, low-density and instantaneous-ionization
approximations for that fixture, or explicitly label it a test of the
approximate analytic model. Report ionization/recombination versus thermal/
dynamical timescales where physical applicability is claimed. Out-of-domain
energy/T roots must return typed failure and retain inputs; no clipping,
silent extrapolation, molecular/metal import or 1000 K floor is justified.
The above is a calibration/applicability condition, not a measured model
failure or an instruction to abandon the first-profile merger goal.

### 8. SH03 finite-phase source and pressure equations pass the algebra audit

Final SH03 pp. 291-292/PDF pp. 3-4 Eqs. (1)-(12) support the transcribed
finite phase source. Put `s=rhoc/tstar`, `d=uh-uc`,
`q=(1-f)Lambda/d`. Then

```text
rhoc_dot=-(1+A beta)s+q;
rhoh_dot=beta(1+A)s-q;
rhostar_dot=(1-beta)s;
rhoc_dot+rhoh_dot+rhostar_dot=0.
```

Adding the cold and hot phase energy equations cancels phase-transfer
terms and gives `Udot/V=-Lambda+beta s uSN-(1-beta)s uc` exactly.
Subtracting `uh*rhoh_dot` from the hot energy equation gives
`rhoh uh_dot=beta s[uSN-(A+1)(uh-uc)]-f Lambda`.
This independently verifies signs and the absence of an extra evaporative
heating/cooling term. At f=0 with frozen nonzero coefficients/masses,
`uheq=uc+uSN/(A+1)` and positive
`tau=tstar rhoh/[beta(A+1)rhoc]` give exponential relaxation. It is not an
analytic solution of the fully evolving phase-mass problem.

Final p. 293 Eqs. (13),(19) support mixture pressure
`P=(gamma-1)(rhoc uc+rhoh uh)`, using the same thermal energy recovered
from conservative total energy. Common velocity, centroid gravity source,
finite-volume phase advection and endpoint decoupled stars are declared
engineering adaptations; they are not the paper's hybrid SPH particles.
The energy equation's SN budget is already the same source that regulates
hot energy/evaporation. Adding a second prompt feedback event would be a
real error; the document expressly forbids it.

The parameter interpretations are supported: SH03 p. 291 gives typical
beta .1 (Salpeter example .106) and approximate SN energy/temperature;
p. 292 gives typical cold T about 1000 K; p. 294 gives A0 about 1000 and
fiducial t0 2.1 Gyr. The exact `beta uSN=(1-beta)epsilonSN` relation follows
Eq. (2), not an independently imposed second exact energy constraint.
Neutral uc/u4 and fully ionized uSN conversions are explicitly named choices.
The old AREPO manual supplies concepts, not current master algorithms or
numeric defaults. No AREPO equivalence is approved.

### 9. Equilibrium and threshold amendments are coherent but need actual branch calibration

SH03 p. 293 Eqs. (14)-(18) impose a constant-pressure/thermal-energy
regulation condition, not separate stationary phase masses. The quadratic
scaling gives `x=y(1-x)^2`. Its physical root and hot fraction in the
document are algebraically equivalent to Eq. (18), including the `y->0`
and large-y limits. The positive denominator
`K=beta uSN-(1-beta)uc` is required. At x=0 the relaxation time diverges;
that is absence of SN relaxation, not a finite-time division to regularize.

Photo fractions/heating and signed CMB are not generally quadratic in
rho, and even T at fixed u changes with ionization. It is correct to retain
the full `Lambda((1-x)rho,uheq)` root separately. SH03 p. 294 Eq. (23)
uses approximate hot energy `uSN/A0`, not exact `uc+uSN/(A0+1)`.
The named `published-eq23` versus `full-rate-continuity-v1` distinction
therefore matters. With declared u4,
`xth=(uh0-u4)/(uh0-uc)` makes `ueff=u4` identically, and the proposed
full-rate density equation enforces Eq. (14) using that same backend.
This is a defensible amendment, not a sourced AREPO implementation.

**Not yet established:** threshold existence/uniqueness, the stable selected
full-rate branch, the EOS slope, admissible T throughout the density range,
or continuity with the actual ordinary thermal equilibrium. A single root
residual is not those results. Before using the closure as an entry oracle,
freeze a physical density search interval, scan/retain all candidate roots,
define the branch-continuation/stability criterion and separately measure
the finite-phase dynamics near it. Compare published/full-rate thresholds
and both u4/ordinary-equilibrium continuity conventions. A nonzero onset
SFR and a jump in EOS derivative are allowed model properties; imposing
SFR continuity or global gamma_eff=4/3 would alter the model. No numerical
threshold is approved by this review.

### 10. Backward Euler and branch semantics are viable first-order design, not a guarantee

ISM lines 742-779 define a common endpoint quadrature for F, evaporation,
condensation and energy, with density-dependent A/tstar reevaluated at the
same endpoint. This produces conservative transactions if the nonlinear
solve is admissible. First-order source splitting and no extra Heun-stage
source copy are explicit. The paper's p. 297 Eq. (32) hot-mass robustness
restriction does not prove positivity of this new coupled nonlinear solve.

The sign guard `Lambda>0`, hot T guard, energy-preserving entry partition,
cloud exhaustion, and downward density exit are explicit engineering
events. Negative net loss belongs in hot heating, not positive condensation.
At a zero cloud fraction s vanishes; at zero hot mass uh and Lambda/rhoh
are undefined. The stored two-phase domain excludes a fully cold cell;
tests should distinguish rejection of that state from a legitimate
one-sided limiting RHS or creation-aware synthetic test. An implementation
must never call the backend with mh=0 merely because a generic zero-phase
test asks for it. The `uh=uc` denominator is similarly outside the two-phase
domain, not a reason to add an epsilon or clip a phase.

**Before source integration:** freeze nonlinear residual scales, finite
root-search/branch policy, event-location tolerance and zero/tiny-reservoir
absolute scales. Boundary roots, rejected outer transactions and subcycling
must preserve state/IDs exactly. A thermal equilibrium is an asymptotic
fixed point for an autonomous scalar cooling ODE; guard against a spurious
implicit jump to another root rather than forcing an artificial crossing.
The proposed dt ladders and independent high-accuracy oracle can test
first-order accuracy. These conditions do not require a positivity theorem,
nor does backward Euler alone establish one.

### 11. Gross/locked mass, metals and energy ledgers are algebraically consistent

For integrated F the selected first profile has `L=(1-beta)F`, `R=beta F`.
Adding phase updates gives `mg'=mg-L`; only L is collisionless. With
constant source-call bulk velocity, gas loses Lv and `L|v|^2/2`, exactly
the newborn momentum/kinetic energy. Its thermal loss Luc goes to the
unresolved stellar ledger, not star hydrodynamics or gas reheating.
Leaving A/B/volume and magnetic energy unchanged then gives

```text
Delta(Egas + Kstars + Estar_unresolved) + Qrad - QSN = 0.
```

Qrad is signed net loss; separate gross cooling/heating channels must also
remain observable. The flux-retention assumption changes gas mass-to-flux
ratio deliberately, and is not a protostellar magnetic-transport claim.
No gas deletion/remap is enabled by this local source contract.

SH03 p. 298 Eq. (40) defines yield per locked stellar mass; p. 308's .02
is an example/calibration, not an exact universal abundance. With
`dMg=-dL`, `dZ=y dL/Mg` integrates to the specified logarithmic Z update.
The complement `MZstar=MZold+y L-Mg' Zg'` conserves inherited plus newly
synthesized metals. For `r=L/Mg`, the packet mean is
`Zstar=Z0+y[1+(1-r)ln(1-r)/r]`, tending to `Z0+y r/2+O(r^2)`.
This supplies an independent small-L oracle and shows why direct
subtraction/division can lose precision. At L=0 no packet is created.

**Required clarification before physical enrichment use:** X=.76,Y=.24
remain an effective primordial thermal composition even when a passive
metal tracer is produced. They cannot simultaneously be interpreted as
actual H/He fractions summing to one *in addition* to Z. Do not count Z
as extra baryon/gravity mass. A bookkeeping conversion into metals is
compatible with the declared tracer approximation, but is not element-by-
element H/He conservation or a chemically consistent metal-rich EOS.
Freeze the tracer-validity range requested at ISM line 456 and its failure
policy. Renormalizing thermal X/Y by `(1-Z)` would be a different closure
requiring rate/threshold revision. This is an explicit first-profile
limitation, not an argument for adding metal cooling without sources.

### 12. Birth gravity, typed identity and deterministic-first policy are appropriate

Gravity GP-2 excludes diagonal self energy. Splitting a co-located mass m
into `m-L` gas and L stars with identical Plummer epsilon leaves external
interactions unchanged, but creates
`DeltaW=-G(m-L)L/epsilon`. Multiple packets add their mutual terms too.
Thus coincident position/equal softening does not imply zero energy jump.
The contracts correctly retain raw H and exact representation change,
distinct from SN/radiation; an adjusted residual cannot replace the raw
history. The gravity contract's cumulative `1e-4` binding-energy and
mass-refinement gate still applies. At fixed total split mass, changing
packet number changes the sum of packet-pair self-exclusion terms, so dt/
packet/softening controls are also essential for deterministic packets.

Typed CellId/ParticleId/EventId wrappers, fixed-width serialization, monotone
checkpointed allocator, sorted atomic commits, source/catalog force-cache
invalidation and accepted-endpoint activation fit the shared contracts.
New stars enter the next force evaluation and receive no past kick. Age
metadata and explicit initial formation epochs are appropriate once Finding
1 is resolved. Gas and particles retain their different box-boundary roles;
wall ghosts must not become gravity sources. Boundary impulses/work remain
separate from sources and the gravity representation jump.

Deterministic variable-mass packets provide an auditable first reference,
with real particle-count and discreteness costs. They are not SH03 Eq. (39)
at fixed resolution. The separate Bernoulli equilibrium hazard and the
finite-phase tau-leap proposal have different finite-step laws; their
expectations/variance must not be conflated. The proposed SHA-256 counter
stream specifies bytes and rollback intent, but **no RNG/sampler extension
is selected, implemented or certified by this review**. Later review must
freeze key/counter test vectors, distribution/expectation tests, seed list,
packet/dt convergence and family-wise statistical failure policy. A 2%
variance gate is a statistical choice with finite false-rejection risk,
not a conservation identity.

### 13. The prospective gates can falsify errors after a concrete packet is frozen

The existing families are useful, but are explicitly unexecuted and omit
specific one-zone initial states, dt0/final times, density brackets, oracle
accuracy scales, and actual disk ICs. This is reasonable for source design;
they cannot yet serve as a registered executable acceptance packet. Do not
report formula/hash checks as numerical evidence or reuse the production
root solver as its own oracle. Before REANA execution I recommend freezing
the following independent experiments with all model/source/input hashes:

| Experiment | Concrete independent measurements and required disposition |
| --- | --- |
| Atomic coefficients/channels | Each of 17 coefficients/channels separately at T=`1e3,5e3,1e4,1e5,5e5,1e6,1e8` within the explicitly accepted evaluation interval; independent arbitrary-precision transcription, nonunit species products and free-free charge mixtures. Preserve C1 source comparison. Relative `1e-10` plus preregistered absolute underflow scale; comparisons establish implementation of the model, not universal atomic accuracy. |
| Abundance/caloric roots | UV-zero and private selected z=0 input; proposed nH ladder `1e-8,1e-6,1e-3,1,1e2 cm^-3`, qualified as analytic-model cases until applicability is justified. Independent normalized H/He-chain or mass-action solver, all nuclear/charge residuals `<=1e-12`, u/T round trip `<=1e-10`, electron limiting roots, separate exhaustive T-bracket inspection. |
| UV parser/interpolation | All row/member hashes, decimal axis and six positive columns; exact-node and midpoint formula checks, 1-ULP endpoint neighbors, malformed/zero/negative inputs, wrong member/source identity. Compare independent log interpolation `<=1e-12`; printed rows only to their displayed precision. Raw external inputs stay private under Finding 6. |
| CMB/units/net rate | Independent SI and cgs paths `<=1e-12`, ne=0, T=Tr, both signs, high-T coefficient comparison, channel-by-channel gross cooling/heating and cancellation scaled to gross terms. Pure CMB low-T probes are separately scoped. |
| Phase algebra/ledger | Both f branches, A=0 and positive A, beta limits as synthetic algebra cases; explicit nonzero velocity/B, exact mass/momentum/thermal/kinetic/unresolved ledgers `<=1e-12` algebra or `1e-10` integrated scales; y=0 and positive-y closed-box oracle including tiny L. Invalid zero-hot/uh=uc cases have declared failures, no floors. |
| One-zone temporal | Frozen-mass hot exponential first; then full evolving phase masses with independent high-accuracy solver, both cooling/heating and phase events. Freeze at least one non-equilibrium valid state per branch, dt0 and tfin before execution, use `dt0/2^k`, k=0..4; finest error `<=1e-3`, finest-three fitted order `>=.9`, oracle error substantially below finest target and reported. |
| Threshold/entry/exit | Full finite density search, every bracket/root, approximate Eq. (23) comparison, selected continuation/stability evidence, both u4 and actual ordinary-equilibrium continuity. Amended pressure/energy jump `<=1e-8`, source residual `<=1e-12`; compress/expand across threshold and hot-T/net-sign events without repeated equilibrium resets. |
| Atomic endpoint births | Two substeps and branch subdivision at a single full endpoint, rejection/restart/thread permutation, formation interval versus activation, no prior kick, exact ID/source-cache invalidation. Independent GP-2 before/after including every new packet pair; same-step ordering identity and dt/mass/epsilon convergence. |
| Coupled layer/disk/merger | After accepted M2/G1/G2/G3/M2d inputs, independent sheet solution, three disk mass resolutions, half-dt and softening/domain/ambient controls, source-free identity, nonzero B and every named divergence operator. Freeze the actual IC/mesh/softening/orbit-time packet jointly with G4; retain the source and `DeltaW` budgets and existing `1e-4` representation bound before the final merger. |

Each independent new case has its own REANA workflow and declared resources,
with ready cases concurrent and no aggregate cap. The specified scalar
1-thread/2-GiB and shared preflight 2-thread/8-GiB allocations are sensible
starting registrations, not measured resource requirements. Coupled 4-thread/
16-GiB disk allocations need concrete IC sizing. Preserve build, physics
and independent-review dependencies; known required failures block escalation.

## Implementation disposition and remaining acceptance work

Source-only preparation of typed interfaces and pure atomic, CMB and SH03
algebra kernels is scientifically supportable after the existing M1
prerequisite permits it. Preserve the explicit C1 and engineering profile
names. Resolve Finding 1 before implementing birth validation/coupled
subcycling, and settle the root/domain/tracer/private-input details before
physical G3 use. No historical SH03 UV identity, current AREPO master
behavior, licensed public FG20 redistribution, numeric threshold/EOS,
successful one-zone solve, isolated disk or merger is certified.

The absence of metals/molecules/shielding, winds, delayed returns, radiation
transport and resolved SN blast feedback is acceptable for the declared
first reference. It limits realism and requires the stated coarse-grained
interpretation; it does not replace the actual equation/interface and
REANA gates. The full moving 3D live-merger goal remains intact.
