# Softened spherical equilibrium reference: source and derivation

2026-11-22. **Source preparation, not an accepted DF, initial condition or
executed numerical gate.** This closes the missing primary-formula source
map for the Eddington option in [gravity section 10.1](GRAVITY_PARTICLES_SPEC.md).
It proposes a concrete spherical G-EQUIL-SOURCE reference. The separate
[independent AI review](EQUILIBRIUM_SAMPLING_DESIGN_REVIEW.md), committed in
`d1059b8`, conditionally supports E1-E5; the author dispositions below clarify
its controls and diagnostics without claiming numerical acceptance.
It does not replace the compound galaxy's orbit-response construction,
its disk velocity constraints, or the moving-3D gas/MHD/ISM merger goal.
M1 acceptance still precedes new numerical implementation/execution.

[Barnes 2012 v3](https://arxiv.org/pdf/1205.2729v3), p.8 section 4.2/Eq.21,
uses the underlying particle density with the softened potential in the
inversion; p.6 Eq.19 relates that potential to the smoothed enclosed mass.
[Eddington 1916](https://articles.adsabs.harvard.edu/pdf/1916MNRAS..76..572E),
printed p.580/PDF p.9, derives the Abel inversion and discusses positivity;
its footnote permits a shifted finite energy cutoff. Those equation pages
were rendered and visually inspected. The complete primary PDFs, versions,
hashes and inspection limits are recorded in
[spherical_equilibrium_sources.json](spherical_equilibrium_sources.json).
Publisher access to Barnes failed; the available v3 preprint is pinned
instead. No published simulation result is reused as project evidence.

## Numbered review dispositions

These are author corrections to findings in the pinned independent review,
not a replacement review. Historical reviewed-byte receipts remain in the
inventory, distinct from current document identities.

| Finding | Author disposition and remaining prerequisite |
| --- | --- |
| 1 | E2/E3, their attractive gradient, stable center and rationalization are unchanged; independent quadrature/precision evidence is pending. |
| 2 | E1, its post-taper normalization and the registered epsilon/taper targets are unchanged; no positive DF follows from positive density. |
| 3 | Separate controls N-T (fixed tapered density, epsilon to zero) and N-P (independently specified infinite untapered Plummer) below. Neither is the finite-positive-epsilon equilibrium reference. |
| 4 | Make the complete DF domain explicit, including typed failure above Psi(0). E4/E5 and edge/center derivations are unchanged. |
| 5 | Explicitly leave independent DF positivity/reconstruction/quadrature/interpolation/CDF budgets and literal reference tables pending. The orbit-response 1%/2% targets do not supply an inversion budget. |
| 6 | Use COM-relative K_int and W for the unchanged 2% collisionless live virial gate; retain lab energy, initial sampled P/L and free COM motion. Distinguish external all-N probes from conditional tagged N-1 sampling. |
| 7 | No identity/address/transaction amendment here; the separate sampling contract and its implementation gates remain authoritative and unexecuted. |
| 8 | No open52 or half-open SF draw-law change; determinism/equal preimage counts do not certify IID samples. |
| 9 | Physical DF/CDF inversion, enclosures and endpoint policies still require their own frozen packet; no sampler or CDF is accepted by this note. |
| 10 | Retain provenance, independent literal references, rollback/restart and staged REANA prerequisites; no hash/RNG draw or numerical execution occurred in this correction. |

## Proposed target and exact softened potential

The following formulas are independent derivations for the project's GP-2
kernel. Proposed fixture parameters are `G=M=a=1`, `epsilon/a=.05,.1`, and
a radial taper from `r_t=10a` to `R=20a`. These are engineering input choices,
not source-paper values or already accepted numerical results. Set

```text
q=(r-r_t)/(R-r_t),
tau(r)=1                         for r<=r_t,
      =1-10q^3+15q^4-6q^5         for r_t<r<R,
      =0                         for r>=R,
rho(r)=C*[3 M a^2/(4 pi (r^2+a^2)^(5/2))]*tau(r),
4 pi integral_0^R s^2 rho(s) ds=M.                             (E1)
```

C normalizes the **post-taper** mass; it must be computed independently and
retained. This rho is the particle-position mass density, not the smoothed
Poisson source density. Do not apply the taper again after sampling.

Angular integration of `-G/sqrt(|x-y|^2+epsilon^2)` gives, for r>0,

```text
s_plus=sqrt((r+s)^2+epsilon^2),
s_minus=sqrt((r-s)^2+epsilon^2), D=s_plus+s_minus,
Phi(r)=-(2 pi G/r) integral_0^R s rho(s) (s_plus-s_minus) ds
      =-8 pi G integral_0^R s^2 rho(s)/D ds.                   (E2)
```

The second form also holds at r=0 and avoids subtracting two nearly equal
square roots. In particular,

```text
Phi(0)=-4 pi G integral_0^R s^2 rho(s)/sqrt(s^2+epsilon^2) ds,
Phi'(r)=8 pi G integral_0^R s^2 rho(s) D_r/D^2 ds,
D_r=(r+s)/s_plus+(r-s)/s_minus,
Phi''(0)=4 pi G epsilon^2 integral_0^R
                          s^2 rho(s)/(s^2+epsilon^2)^(5/2) ds. (E3)
```

Phi has its isolated zero at infinity. It is not set to zero at R in the
gravity solver, and the Plummer kernel/particle domain is not truncated there.
For an additional stable derivative representation, let
`K=s_plus*s_minus`, `B=r^2-s^2+epsilon^2`. Then
`D_r=2r*(K+B)/(D*K)`; for B<0 evaluate
`K+B=4s^2 epsilon^2/(K-B)` instead of subtraction. The identity follows from
`K^2-B^2=4s^2 epsilon^2`. It establishes `Phi'(r)>0` for r>0, positive
epsilon and a nonzero positive density. At r=0 use the analytic limit;
neither `0/0` nor a numerical radial floor is an acceptable definition.

## Relative energy, inversion and endpoint behavior

Only the **DF energy reference** is shifted:
`Psi(r)=Phi(R)-Phi(r)`, `calE=Psi-v^2/2=Phi(R)-E_physical`.
For finite calE use f(calE)=0 for calE<=0. The supported bound-energy interval
is exactly
`0<calE<=Psi(0)`. The upper endpoint uses the controlled center limit below;
it is not omitted. A finite request above Psi(0) returns the typed failure
`DfEnergyOutOfDomain { requested, psi_center, model_identity }`; nonfinite
input returns `DfNonFiniteInput`. Retain the inputs and any uncertainty in
Psi(0). If uncertainty prevents classifying the request, fail as
`DfDomainUnresolved`; no extrapolation, clipping, borrowed endpoint value or
resampling is permitted. These type names are engineering interface choices.
There is no boundary reflection or deletion of
live particles at R. The stationary target's energy cutoff is distinct from
escape to infinity and does not confine a finite-N evolution artificially.

Direct isotropic velocity integration yields

```text
rho(Psi)=4 pi sqrt(2) integral_0^Psi f(calE) sqrt(Psi-calE) dcalE,
f(calE)=1/(sqrt(8) pi^2) * [rho_Psi(0)/sqrt(calE)
                + integral_0^calE rho_PsiPsi(Psi)/sqrt(calE-Psi) dPsi]. (E4)
```

The normalization in E4 follows by applying Abel inversion to the derivative
of its first line. Derivatives refer to the original rho composed with
the inverse of E2, never to the smoothed Poisson density. For E1 the edge
has `rho~C_edge Psi^3`, so `rho_Psi(0)=0`. Removing the integrable upper
endpoint singularity gives the proposed quadrature form

```text
f(calE)=sqrt(calE)/(sqrt(2) pi^2)
              * integral_0^1 rho_PsiPsi(calE*(1-u^2)) du,
f(calE)~(2 sqrt(2)/pi^2)*C_edge*calE^(3/2) at calE->0+.        (E5)
```

The asymptote follows by inserting `rho_PsiPsi=6 C_edge Psi` into E4.
Near the center, calculate derivatives in z=r^2:
`rho_Psi=rho_z/Psi_z` and
`rho_PsiPsi=(rho_zz Psi_z-rho_z Psi_zz)/Psi_z^3`.
Here `Psi_z(0)=-Phi''(0)/2` is nonzero. Using raw r derivatives there would
form cancelling quantities and a vanishing denominator. The taper joins
must be explicit quadrature breaks; C2 matching is not infinite smoothness.

Neither monotonic Psi nor positive rho proves f>=0. Negative DF values,
uncertainty that cannot resolve their sign, failed reconstruction, or a
nonmonotone sampling CDF block this fixture. Do not take abs, clamp f,
trim unfavorable energies, or renormalize away a density mismatch. A changed
taper/model must be reviewed and registered before its own execution.

## Independent numerical packet required before live sampling

The G-EQUIL-SOURCE potential/force refinement target `<1e-6` and existing
G-EQUIL-LIVE conservation/stability gates remain unchanged. Before execution,
freeze the high-precision quadrature/error controls, energy/radius grids,
near-zero normalization scales, reference hashes and sampler/RNG separately.
In particular, the gravity table's orbit-response density L1 `<1%` and moment
`<2%` targets do **not** define an Eddington inversion acceptance budget.
Independent DF sign enclosures (including unresolved sign), density and
Jeans-moment reconstruction errors, quadrature/derivative/interpolation
budgets, CDF normalization/inverse probability errors, their center/edge
scales, and literal reference tables/hashes remain **unfrozen prerequisites**.
They must be registered before the DF/CDF slice or any physical sampling;
no passing values or globally positive DF have been computed. Reference
builders must not call candidate E2/E5 kernels or share derivative/table
caches. Agreement at a few nodes or moments cannot discharge these budgets.
Each independent epsilon/resolution/reference case runs on REANA with the
contract's explicit per-case resources and build/scientific prerequisites.

The candidate radial E2/E5 path must be compared to a separately written
high-precision angular/radial GP-2 quadrature and Abel inversion, with
precision and quadrature refinement. Include r=0, r~epsilon, both taper joins,
the DF cutoff and the highest binding energies. Compare Phi' both by the
independent force integral and on a demonstrated finite-difference plateau.
Check isolated asymptotics and the two distinct Newtonian controls below.

Reconstruct rho by the velocity integral in E4. Independently compare the
radial velocity moment to
`rho(r)*sigma_r^2(r)=integral_r^R rho(s)*Phi'(s) ds`, with zero edge pressure.
The sampling laws are `p(r)=4 pi r^2 rho(r)/M` and
`p(v|r)=4 pi v^2 f(Psi-v^2/2)/rho(r)` on `0<=v<=sqrt(2Psi)`; each must
normalize independently. A nonnegative interpolant must reproduce these
integrals, not merely the tabulated f values. The separate
[sampling proposal](RANDOM_SAMPLING_SPEC.md) supplies an IC address/draw
contract, not an accepted physical CDF, RNG independence or live realization.

## Two separate Newtonian controls (finding 3)

**N-T: fixed tapered-density Newtonian limit.** First fix E1's M,a,rt,R,tau
and its independently computed post-normalization C, with rt=10a,R=20a.
C is independent of epsilon and remains greater than one. Only then take
`epsilon->0+` in the GP-2 convolution, at that unchanged density. Define
`m_T(r)=4*pi*integral_0^min(r,R) s^2*rho(s) ds`. The independently derived
Newtonian spherical reference is

```text
Phi_NT(r)=-G*[m_T(r)/r+4*pi*integral_r^R s*rho(s) ds] (0<r<R),
Phi_NT(0)=-4*pi*G*integral_0^R s*rho(s) ds,
Phi_NT(r)=-G*M/r                                  (r>=R),
Phi_NT'(r)=G*m_T(r)/r^2                           (r>0),
acceleration_NT=-Phi_NT'(r)*x/r; acceleration_NT(0)=0.
```

At epsilon=0, E2's D is `2*max(r,s)`; splitting its integral at s=r gives
these formulas with zero potential at infinity. This is also the Newtonian
spherical relation underlying Barnes p.6 Eq.(19), now with the unchanged
raw tapered density as the Newtonian source. For positive epsilon Barnes's
mass in that equation is the **smoothed** enclosed mass; the finite-epsilon
exterior field is not exactly `G*M/r^2`. Use its isolated large-r asymptote
only. N-T is not the analytic untapered Plummer potential.

**N-P: separately specified infinite untapered Newtonian Plummer control.**
Declare a different density with tau=1 everywhere, R=infinity, C=1, the same
positive M,a, and Newtonian epsilon=0. Equivalently one may take epsilon to
zero only after declaring this different, untapered infinite density.
[Dehnen v1](https://arxiv.org/pdf/astro-ph/0011568v1), p.9 section5.1 Eq.(30),
gives its density and potential (r_s=a); differentiation gives its force:

```text
rho_P(r)=3*M*a^2/[4*pi*(r^2+a^2)^(5/2)],
Phi_NP(r)=-G*M/sqrt(r^2+a^2),
Phi_NP'(r)=G*M*r/(r^2+a^2)^(3/2),
acceleration_NP=-G*M*x/(r^2+a^2)^(3/2).
```

That primary page was visually inspected; its PDF/render identities are
pinned in the inventory. No Plummer DF normalization is needed or adopted
for either potential/force control. N-P is a separately declared reference,
not an epsilon-only limit of finite E1. No taper-removal/epsilon limit
interchange or unspecified rt/R sequence is assumed. N-T's separate radial
mass/shell quadrature and N-P's analytic formula are independent controls;
neither replaces independent angular/radial GP-2 quadrature for the actual
E1 epsilon/a=.05,.1 targets. Those targets, and the registered `<1e-6`
potential/force refinement gate, are unchanged. Numerical controls, grids
and literal reference tables for these paths are still future evidence.

## Finite-N interpretation and internal diagnostics (finding 6)

The continuum reference includes the smooth density's full mass M. For
independent equal-mass positions of mass M/N, a fixed external probe whose
location is independent of the catalog sums **all N** sources: its expected
potential/acceleration is the full continuum softened convolution. A probe
at a tagged sampled particle instead excludes that particle's diagonal; only
conditional on independent equal-mass sampling do its N-1 other sources
have mean `(N-1)/N` times the full continuum field at the tagged position.
This statement concerns mass-specific potential/acceleration; multiply by
the tagged mass for force. Barnes pp.6-7 discusses probe/particle sampling
correlations. Stratified, paired or otherwise correlated catalogs require
their own measured conditional reference. SHA address determinism alone is
not IID certification. Do not change G, particle velocities or self energy
to cancel the finite-N effect; no selective seed retry is permitted.

For the closed fixed-mass collisionless catalog, use
`K_int=(1/2)*sum m*|v-P/M|^2`, computed from velocity deviations, and
`W=sum (x-X_cm) dot F`. The identity and boost derivation are in
[gravity section 9](GRAVITY_PARTICLES_SPEC.md#9-diagnostics-and-accounting-before-any-merger-claim):
`I_cm''/2=2*K_int+W`; the raw lab expression has the extra `|P|^2/M`.
Use `abs(2*K_int+W)/(2*K_int+abs(W))` for the unchanged 2% time-mean live
gate. Preserve K_lab/raw conserved energy and the **actual**, generally
nonzero initial P/L residuals. Track changes from that catalog and its free
COM path `X_cm(0)+P0*t/M`; do not repair velocities or recenter the live data.
Density/velocity bins use the explicit diagnostic centers/frames in gravity
section9; raw model-origin and COM-frame comparisons remain distinguishable.
These are diagnostic coordinate transforms, not catalog edits. The finite-N
sample is not an exactly stationary realization of E1. No closed
collisionless virial theorem is asserted for bounded active MHD gas.

This note retains the review's conditional source/design support and still
requires the full REANA reference/positivity/DF/sampling/live gates. It
establishes no stable disk, coupled gas equilibrium or merger result.
