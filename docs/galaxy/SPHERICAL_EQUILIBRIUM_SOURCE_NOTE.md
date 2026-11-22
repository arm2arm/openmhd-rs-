# Softened spherical equilibrium reference: source and derivation

2026-11-22. **Source preparation, not an accepted DF, initial condition or
executed numerical gate.** This closes the missing primary-formula source
map for the Eddington option in [gravity section 10.1](GRAVITY_PARTICLES_SPEC.md).
It proposes a concrete spherical G-EQUIL-SOURCE reference for independent
review. It does not replace the compound galaxy's orbit-response construction,
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
Use f(calE)=0 for calE<=0. There is no boundary reflection or deletion of
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
Each independent epsilon/resolution/reference case runs on REANA with the
contract's explicit per-case resources and build/scientific prerequisites.

The candidate radial E2/E5 path must be compared to a separately written
high-precision angular/radial GP-2 quadrature and Abel inversion, with
precision and quadrature refinement. Include r=0, r~epsilon, both taper joins,
the DF cutoff and the highest binding energies. Compare Phi' both by the
independent force integral and on a demonstrated finite-difference plateau.
Check isolated asymptotics and the epsilon->0 Plummer control only as a
separate limiting case, never as the finite-epsilon reference.

Reconstruct rho by the velocity integral in E4. Independently compare the
radial velocity moment to
`rho(r)*sigma_r^2(r)=integral_r^R rho(s)*Phi'(s) ds`, with zero edge pressure.
The sampling laws are `p(r)=4 pi r^2 rho(r)/M` and
`p(v|r)=4 pi v^2 f(Psi-v^2/2)/rho(r)` on `0<=v<=sqrt(2Psi)`; each must
normalize independently. A nonnegative interpolant must reproduce these
integrals, not merely the tabulated f values. No RNG or CDF implementation
is selected/certified by this source note.

The continuum reference includes the smooth density's full mass. A finite-N
direct catalog excludes self pairs and has sampling/relaxation effects;
it is not an exactly stationary realization of E1. For independent equal-mass
sampling the conditional mean field has the familiar (N-1)/N factor, while
stratified/paired sampling changes correlations. Retain these as measured
finite-N controls, not a hidden force/COM/energy correction. Record any IC
centering/symmetrization explicitly and never recenter the live result to
manufacture a pass. Softened virial diagnostics use `2K+sum x dot F`, not
the unsoftened `2K+U` identity.

This note remains a coordinator proposal requiring separate source/math
review and the full REANA reference/positivity/DF/sampling/live gates. It
establishes no stable disk, coupled gas equilibrium or merger result.
