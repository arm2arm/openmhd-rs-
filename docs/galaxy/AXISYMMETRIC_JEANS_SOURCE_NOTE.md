# Axisymmetric Jeans constraints: source and taper audit

2026-11-22. **Manual source/derivation note, unreviewed and unexecuted.**
This serves the compound rotating halo/disk/bulge prerequisite of the
moving-3D magnetized live-gas/star merger. It does not implement or accept
a velocity optimizer, a positive distribution function, a stable disk or
gas equilibrium. M1 and all later physical gates remain pending.
[Exact sources and context](axisymmetric_jeans_sources.json) are retained.

The complete [Yurin & Springel 2014 v2 paper](https://arxiv.org/abs/1402.1623v2)
is available. Printed pp.3–5 Eqs.1–12 and the optimization discussion define
orbit-averaged density and velocity-moment merit functions. Printed p.6
Eqs.17–22 gives a two-integral axisymmetric closure; p.8 Eqs.23–33 gives
a tilted three-integral proposal. Printed p.12 Eq.50 gives the exponential
radial/sech-squared vertical stellar density, with no project outer taper.
Those equation pages were read and pp.6/8/12 freshly rendered and inspected.
No GALIC software or paper test parameters are adopted.

## 1. Derive the mixed-moment derivative before transcribing it

For a stationary axisymmetric collisionless distribution with zero mean
radial/vertical streaming, write `sR=<vR^2>`, `sz=<vz^2>`,
`sphi=<vphi^2>` and `t=<vR*vz>`. Integration of the cylindrical
collisionless Boltzmann equation against vR and vz gives

```text
partial_R(rho*sR)+partial_z(rho*t)
                 +rho*(sR-sphi)/R+rho*Phi_R=0,
partial_z(rho*sz)+(1/R)*partial_R(R*rho*t)+rho*Phi_z=0.

sphi=sR+(R/rho)*partial_R(rho*sR)+R*Phi_R
                                      +(R/rho)*partial_z(rho*t). (J1)
```

Boundary terms in velocity space must vanish for this moment derivation.
For example the stationary cylindrical equation used here is
`vR*f_R+vz*f_z+(vphi^2/R-Phi_R)*f_vR
 -vR*vphi*f_vphi/R-Phi_z*f_vz=0`; multiplying and integrating establishes
the coordinate derivatives and curvature terms in J1.

**Source discrepancy:** retained Y14 p.8 Eq.24 visibly prints
`(R/rho)*partial_R(rho*<vR*vz>)` as its last term. J1 requires the **z**
derivative there. Its vertical Eq.23 does have the radial derivative shown
in J1. This is a direct equation-page/moment-derivation discrepancy, not an
acknowledged publisher erratum or an audit of GALIC source behavior. A
future project implementation must use independently reviewed J1, not copy
the printed Eq.24 derivative blindly. At t=0 the distinction disappears;
an untilted-only control cannot test it. A tilted manufactured stress tensor
with independently different R and z derivatives is required on REANA.

## 2. Nonsingular algebra for the proposed ellipsoid tilt

Y14 Eqs.29–32 choose `tan(alpha)=z/R` and principal-dispersion ratio
`fR=<vRprime^2>/<vzprime^2>>0`. If `qprime=<vzprime^2>`, direct rotation
of the symmetric covariance gives

```text
sR=qprime*(fR*cos(alpha)^2+sin(alpha)^2),
sz=qprime*(fR*sin(alpha)^2+cos(alpha)^2),
t=qprime*(fR-1)*sin(alpha)*cos(alpha).

h_tilt=t/sz=(fR-1)*R*z/(R^2+fR*z^2),
sR/sz=(fR*R^2+z^2)/(R^2+fR*z^2).                            (J2)
```

For `(R,z)!=(0,0)`, J2 is an algebraically reduced form of that proposal;
it avoids the `tan(2*alpha)` singularity at R=abs(z). It is not a new
observational anisotropy prescription. If fR=1, the covariance is isotropic
in the meridional plane and t=0; if fR is a nonunit constant the orientation
at the exact origin is undefined. The central stress/DF limit requires its
own symmetry/regularity condition, not an arbitrary angle or zero assignment.

**Source discrepancy:** Y14 p.8's paragraph after Eq.33 prints
`h/R -> (f-1)/f` for R->0. At fixed nonzero z, J2 instead gives
`h_tilt/R -> (fR-1)/(fR*z)`. This is finite for each such z, but is neither
independent of z nor a uniform bounded-origin limit. The ratio h_tilt/R has
units inverse length in physical coordinates. This note does not infer an
unprinted z=1 convention. The zero-tilt case, axis at nonzero z, midplane
at nonzero R, R=abs(z), and simultaneous origin limit are separate controls.

With `q=rho*sz`, the vertical equation becomes
`partial_z q+partial_R(h_tilt*q)+h_tilt*q/R+rho*Phi_z=0`, consistent with
Y14 Eq.33 after J2 reduction. Its well-posed boundary/axis/central behavior,
positive q and complete J1 stress/streaming solution remain unverified.

## 3. A radial-only compact taper rules out a tempting simple closure

The current proposed stellar density uses a finite radial C2 taper, constant
vertical scale and positive post-taper mass normalization:

```text
rho(R,z)=A*T(R)*exp(-R/Rd)*sech(z/zd)^2,
T=1-10*s^3+15*s^4-6*s^5,    s=(R-Rt)/(Rout-Rt),
T=0 for R>=Rout,             zd>0.                            (J3)
```

This is a project modification of Y14 Eq.50. It has not been certified as
an equilibrium density in the combined softened potential. In particular,
consider the proposed **untilted** closure `t=0`, `sR=b*sz`, with a constant
`b>0`; the two-integral f(E,Lz) case is b=1. Y14 Eq.19 then yields

```text
sz(R,z)=integral_z^infinity sech(zprime/zd)^2
                    *Phi_z(R,zprime) dzprime / sech(z/zd)^2.  (J4)
```

The entire T(R)*exp(-R/Rd) factor cancels. Assume the smooth combined
potential gives a finite positive limit `sz->s0(z)>0` as R->Rout from
inside and a bounded radial derivative there. This is a condition on the
actual target potential, not an evaluated quadrature result; a gravitating
halo supplies a vertical restoring contribution. With
`delta=Rout-R`, `DeltaR=Rout-Rt`, exact polynomial rearrangement gives

```text
T=10*(delta/DeltaR)^3-15*(delta/DeltaR)^4+6*(delta/DeltaR)^5,
partial_R(log T)=-3/delta+O(1).

sphi=b*sz+R*Phi_R+(R/rho)*partial_R(rho*b*sz)
     =-3*Rout*b*s0(z)/delta+O(1) -> -infinity.                (J5)
```

Thus J3 with these conditions cannot satisfy the untilted constant-b Jeans
closure all the way to its edge: a second velocity moment cannot be
negative. No choice of Satoh streaming, Gaussian draw, seed, binning,
normalization or orbit optimizer can repair this negative **total** moment
while keeping those density/stress assumptions. Removing the outer bad
bins from a verdict or clipping sphi to zero is not a physical resolution.
The taper's C2 smoothness alone does not make its logarithmic gradient
bounded or make the assumed moment tensor admissible.

J5 does not rule out every three-integral/tilted DF or every possible disk
boundary. It rules out the stated untilted constant-b shortcut under the
explicit J4 limits. It also does not show that a varying-b prescription or
a different taper produces a positive DF. A revised density/stress/tilt
choice must be derived, independently reviewed, frozen, solved and checked
for positive moments and actual equilibrium; it cannot be selected after a
failed live evolution. The parent contract has not yet selected that disk
closure, so this note identifies a constraint on that choice, not an observed
failure of an existing numerical implementation. No target family or
registered physical threshold is changed here.

## 4. Gates before the compound-galaxy optimizer

The first rotating-galaxy implementation needs a complete compatible
density/taper, combined **softened** target potential and velocity-tensor/
streaming prescription, including outer and axis behavior. The initial
untapered analytic-paper problem is a separately labelled source control,
not the finite-taper galaxy target. Positive covariance and Jeans residuals
are necessary and do not prove a nonnegative global DF or stability.

Retain distinct radial/vertical first and second moments, azimuthal raw
second moment, streaming and centered dispersion, and the mixed moment t.
For a selected Satoh relation `mean_vphi^2=k^2*(sphi-sR)`, first establish
its denominator/sign domain and `sphi-mean_vphi^2>=0`; k cannot fix J5.
Use the physical rotation sign from the IC manifest. Independent orbit
responses and live disk profiles must check these moments and density,
not only a small aggregate merit value. All numerical references, bins,
central/tail enclosures, constraints and optimizer policies remain unfrozen.

Required future REANA cases separately cover J1's tilted derivative, J2's
axis/diagonal/isotropic limits, J3–J5's analytic negative control, proposed
revised positive moment targets, target-potential/Jeans residual convergence,
orbit-response density/moment convergence and independently evolved
multicomponent disks. Preserve the parent G-EQUIL/G-GALAXY drift, sampling,
timestep, softening, domain and stability gates; no new looser substitute.
Each ready case gets its own workflow/resources after M1 and applicable
source/fixture/preflight prerequisites. No numerical test or probe was run.

Gas rotation/vertical support with magnetic forces and active ISM sources
requires its own compatible construction. A stellar Jeans tensor is not
a gas/MHD pressure balance. Stable isolated live DM, stars and magnetized
gas plus the full encounter/source/boundary evidence remain prerequisites
to the requested merger demonstration.
