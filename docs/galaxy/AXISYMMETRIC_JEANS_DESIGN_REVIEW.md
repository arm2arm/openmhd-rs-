# Independent review: axisymmetric Jeans source and taper constraints

2026-11-22. **J1/J2 and the conditional J3–J5 exclusion are supported by independent manual derivation.** The retained Y14v2 page 8 really contains the two identified equation/text discrepancies. These are source/derivation discrepancies, not an acknowledged publisher erratum or a GALIC software audit. The note correctly leaves the compound galaxy's density/stress/DF closure unselected. No DF, optimizer, disk stability, gas equilibrium, M1 or galaxy-merger acceptance follows.

Subject **J** is `3be5f4dec311ee50e020caf3a1d6e3a376972dd8`. `AXISYMMETRIC_JEANS_SOURCE_NOTE.md` is 9,032 bytes, SHA256 `859ae0b5f1253732c9a013365e100a898853d76a27eb0e43907752d00121ff10`; locators below refer to those bytes. Parent **P** is `d3d156d64e281918aaae79631ac63c1ac71a367a`, especially gravity section10 and its unchanged G-EQUIL/G-GALAXY gates. [The review inventory](axisymmetric_jeans_review_sources.json) pins both subjects, parent context, historical reviews and actual PDF/read artifacts. Observed root was `cf3d8533e329ba351ddafb5246e84d036505df10`; no later working-copy bytes replace P.

1. **Blocking model choice, not a failed implementation: the constant-b untilted shortcut cannot realize J3 under J4's edge assumptions.** J:86–140 is a valid conditional exclusion. Let `w(z)=sech^2(z/zd)`, `rho=A*T(R)*exp(-R/Rd)*w(z)`, `t=<vR*vz>=0` and `sR=b*sz` with constant b>0. Zero vertical stress at infinity gives

   ```text
   rho*sz = integral_z^infinity rho(R,z')*Phi_z(R,z') dz',
   sz = integral_z^infinity w(z')*Phi_z(R,z') dz'/w(z).
   ```

   The explicit radial density factor cancels for R inside the positive-density support. The combined potential still depends on the radial taper and all components; cancellation does not make sz independent of the physical model. At the finite positive edge Rout, assume `sz=s0(z)+O(delta)`, `s0(z)>0`, bounded `partial_R sz`, and bounded Phi_R, where delta=Rout-R. The stated smooth softened potential and bounded derivative supply this expansion if the positive edge limit exists; this review has not evaluated that limit for a target galaxy.

   With DeltaR=Rout-Rt, direct rearrangement of the transition polynomial gives

   ```text
   T=10*(delta/DeltaR)^3-15*(delta/DeltaR)^4+6*(delta/DeltaR)^5,
   partial_R log T=-3/delta+O(1),
   sphi=b*sz+R*Phi_R+R*b*partial_R sz
                       +R*b*sz*(partial_R log T-1/Rd)
        =-3*Rout*b*s0(z)/delta+O(1) -> -infinity.
   ```

   This is a negative **raw total** azimuthal second moment, hence incompatible with any nonnegative DF satisfying the stated stress and density assumptions. A rotating mean, Satoh parameter, Gaussian proposal, optimizer, seed, bin cutoff or normalization cannot repair it while those assumptions remain fixed. C2 density tapering does not bound its logarithmic derivative. J3 displays the transition and outer branches; when freezing a standalone input packet also carry P's explicit `T=1 for R<=Rt`, positive Rout>Rt and post-taper normalization. This is a completeness clarification, not an equation defect in the edge argument.

   **Required before the rotating-galaxy IC slice:** select and review a compatible density/edge/stress/tilt/streaming model in the combined softened potential. Do not clip sphi, discard outer bins, or choose a new model after seeing a failed live test. J5 does not exclude all tilted/three-integral DFs, an anisotropy vanishing at the edge, altered vertical structure, or other boundaries; neither does it prove any of those alternatives exists. The smallest later REANA negative control must test the stated edge assumptions independently and compare raw moments at a registered sequence of interior edge distances, with sign/error enclosures. It is not evidence that a particular live disk has already failed.

2. **Supported J1 and verified printed Eq.24 discrepancy.** J:19–49 uses the stationary axisymmetric cylindrical CBE. Assuming finite moments and vanishing velocity-space boundary terms, its vR moment is

   ```text
   partial_R(rho*sR)+partial_z(rho*t)
                         +rho*(sR-sphi)/R+rho*Phi_R=0.
   ```

   Specifically, integration by parts of the radial acceleration term gives `-rho*sphi/R+rho*Phi_R`, while the azimuthal velocity-coordinate term gives `+rho*sR/R`. The vz moment gives `partial_R(rho*t)+partial_z(rho*sz)+rho*t/R+rho*Phi_z=0`. Rearranging the first gives J1's final **z derivative** of rho*t. Direct inspection of the complete retained printed p.8 confirms that Y14 Eq.24 instead prints an R derivative in this last term, while Eq.23 prints the radial mixed-stress term in the vertical equation. The disagreement is not an extraction artifact and is not resolved by dimensional analysis alone: both derivatives have the same dimensions.

   The project should use the independently derived J1 and retain the source discrepancy explicitly. Here t denotes the mixed moment, not simulation time; J:47's `t=0` is an untilted stress. A control with t identically zero cannot distinguish the derivatives. A minimal later REANA manufactured tilted stress with independent R/z variation must compare both cylindrical moment residuals to independent analytic derivatives and show the deliberately transcribed Eq.24 fails its negative control. No software/source behavior of GALIC was inspected or inferred.

3. **Supported J2 covariance rotation and nonuniform origin qualification.** J:51–84 follows Y14 Eqs.26–32 away from the origin. Rotating `diag(fR*qprime,qprime)` through alpha with tan(alpha)=z/R yields the stated sR, sz and t. Division by sz gives

   ```text
   t/sz=(fR-1)*R*z/(R^2+fR*z^2),
   sR/sz=(fR*R^2+z^2)/(R^2+fR*z^2).
   ```

   For fR>0 and `(R,z)!=(0,0)` the denominator is positive. This removes the spurious tan(2*alpha) singularity at R=|z|. For fixed nonzero z and finite positive constant fR, `h_tilt/R -> (fR-1)/(fR*z)` as R->0; at z=0,R>0, h_tilt=0 and sR/sz=fR. Along z=kR, h_tilt tends `(fR-1)*k/(1+fR*k^2)`, generally dependent on the approach direction. Thus an exact central stress limit needs its own regularity/anisotropy prescription. Setting the origin angle or h arbitrarily to zero would not prove it. The isotropic fR=1 case is separately well defined, with zero mixed stress.

   The full rendered p.8 paragraph after Eq.33 prints `h/R -> (f-1)/f`. It lacks the 1/z factor required by its own Eqs.29–32; h is dimensionless and h/R has inverse-length units in physical coordinates. Nondimensional R,z still retain the functional 1/z dependence. No unprinted z=1 convention or publisher correction is assumed. For a spatially varying fR, the limit requires that function's own finite positive axis limit and regularity; the constant-fR calculation does not supply them. Later independent limit controls must separate axis-at-nonzero-z, midplane-at-nonzero-R, diagonal, isotropic and simultaneous-origin cases.

4. **Supported vertical PDE; solvability and a positive DF remain open.** Substituting `q=rho*sz` and `rho*t=h_tilt*q` into J1's vertical equation gives `q_z+partial_R(h_tilt*q)+h_tilt*q/R+rho*Phi_z=0`, matching Y14 Eq.33 after the algebraic J2 reduction. It does not fix axis/central/outer boundary conditions, prove positive q, determine every stress/streaming component, or establish existence of a nonnegative global collisionless DF. A Jeans tensor is a necessary moment constraint; positive local covariance is still not a sufficient DF theorem. The density-response optimizer cannot be credited with preserving impossible target moments by achieving only a small aggregate merit.

   The first selected tilted problem needs independently frozen boundaries, central/tail treatment, raw and centered moments, tilt, first moments, bin integrals, sign/enclosure budgets and normalization. Compare the actual radial and vertical Jeans residuals in the **combined softened** halo+bulge+disk potential; include gas/ambient contributions when that later configuration is chosen. A Newtonian analytic component superposition or the separate isotropic spherical DF cannot certify this flattened compound problem. No quadrature, DF/CDF, orbit or sampling evaluation occurred here.

5. **Supported stellar/streaming and parent distinctions.** Y14 p.6 Eqs.17–22 supplies the two-integral untilted context and Satoh-type split; p.8 supplies the tilted proposal. For the selected relation `mean_vphi^2=k^2*(sphi-sR)`, check its real-valued domain, rotation sign and `sphi-mean_vphi^2>=0` before sampling. Even k=0 cannot make negative sphi physical. Keep the raw sphi, mean streaming, centered dispersion, radial/vertical moments and mixed t separately in the reference and orbit-response/live diagnostics.

   P's gravity section10.1:790–877 recommends an independently implemented orbit-response optimizer but explicitly leaves numerical disk dispersions/streaming to a positive combined-potential Jeans/DF construction. Its radial disk taper is 8–10 Rd, normalized after tapering; neither a constant-b untilted closure nor a positive DF was selected. J accurately reports that status. The prior spherical equilibrium/sampling review and corrected spherical source note remain separately pinned, not amended by this disk argument. Their finite-taper Newtonian versus untapered controls and COM-relative live virial diagnostic remain applicable to their own cases. A stellar collisionless moment tensor also cannot initialize the gas pressure/magnetic force balance or discharge active ISM/gravity source ledgers.

6. **Source and documentary closure; precise limits.** The complete retained [Yurin & Springel 2014 v2](https://arxiv.org/abs/1402.1623v2) PDF has 18 pages, 1,129,978 bytes and SHA256 `44d4d3e8a1b1bcfa4da8567ca99275fe1ecbc5f10f0b84bb026372853f693082`. The actual strip says v2, 19 August 2014; the printed first-page recompile date is 5 June 2018. These identify different metadata fields, not a version mismatch. Complete pp.6/8/12 were freshly rendered and visually inspected; pp.1,3–6,8,11–12 surrounding text/equations were consulted. In particular p.12 Eq.50 is the untapered exponential-R/sech-squared-z disk; the project taper and J5 edge argument are engineering choices/derivations, not paper values. The Eq.50 footnote about a different older paper is not evidence of an acknowledged correction to Y14 Eq.24 or its axis paragraph. No unavailable publisher version or software audit is claimed.

   All 34 subject/context/source/render identity entries across the two author inventories match the retained bytes or their stated git commits. There was no nonzero identity-check discrepancy to omit. The ignored fresh equation texts/renders and exact read-only receipt are pinned in this review's inventory. Only document/PDF reading, rendering, parsing, safe file hashes and the manual algebra above were performed; no RNG/address/hash-draw test, numerical DF/quadrature/geometry probe, build, test, evolution, reducer, workflow/service action, commit, push or delegation occurred. The only authored repository outputs are the four assigned new review/inventory files; historical independent reviews and scientific source remain unchanged.

7. **Actionable disposition and prospective gates.** J1/J2 are suitable reviewed source formulas for a future independently specified moment kernel after M1, literal reference and immutable preflight prerequisites. J3–J5 is a supported conditional negative control, not an accepted disk target. The rotating compound IC remains model-blocked until finding 1/4's compatible closure/DF and all reference error budgets are frozen. Retain the parent potential/force refinement <1e-6, orbit-response density L1 <1% and moments <2% where supported, plus the distinct still-unfrozen DF positivity/reconstruction/CDF budgets; those moment targets do not define a DF error budget.

   Future independent REANA cases separately cover the tilted-derivative negative control, covariance/axis limits, taper edge exclusion, proposed revised positive targets, softened-potential/moment residual convergence, orbit-response density/moments and isolated live galaxies. Preserve G-EQUIL-LIVE and G-GALAXY-ISOLATED thresholds: radius drift <2%, resolved density/moment/profile drift <5%, COM-relative time-mean virial residual <2%, raw energy drift <1e-3 and the existing momentum/angular-momentum/stability controls, with sampling/dt/epsilon/domain comparisons. The gas/magnetic/ISM/merger stages retain their own bounded/domain/source gates; none has been executed or accepted here. Each independent ready case requires its own REANA workflow/resources after prerequisites, with no aggregate cap.
