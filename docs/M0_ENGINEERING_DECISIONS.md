# General reference algorithm: M0 engineering decisions

Profile name: **paper-global-v1**. These are explicit OpenMHD-RS engineering choices (E), supported where stated by derivations (D). Published choices (P) and their page/equation references remain in [the source specification](PAPER_IMPLEMENTATION_SPEC.md). This document completes the previously unnamed policies U1-U5 for review. It is a specification for future implementation; the existing planar driver still uses its documented method-of-lines integration.

## U1: primitive predictor, face motion and energy

Use the existing ideal-gas EOS, common arithmetic face-normal B at preserved reconstructed gas pressure, moving-face HLLD/HLL policy and lab-frame flux/EMF transform in [COUPLED_2D.md](COUPLED_2D.md). Record every fallback; it is not a positivity guarantee. Preserve conservative cell mass, momentum and total energy. No Powell source, entropy switch, pressure floor or magnetic-energy reset is enabled.

With `Gv[a,b]=partial_b v_a`, `GB[a,b]=partial_b B_a`, let `theta=trace(Gv)` and `J=curl(GB)`. At the beginning of the step, form the following material derivatives using the **limited primitive gradients**:

```text
D_v rho = -rho theta
D_v p   = -gamma p theta
D_v v   = (-grad(p) + J cross B)/rho
D_v B   = Gv B - B theta
```

The density, pressure and Lorentz terms follow the primitive equations used in P p. 15, Eq. (83); the explicit induction expansion is our choice. The full curl identity contains an additional `v div(B)`. We adopt the solenoidal form above, omitting an estimated nonzero LS divergence from this predictor. This agrees with the continuum constraint and makes the material derivative invariant under a uniform boost even when the discrete divergence residual is nonzero. Retain that residual as a diagnostic. This choice affects the Riemann **predictor**, not the conservative gas update; it is neither a claim that the LS divergence vanishes nor a Powell source added to the gas equations.

For each old cell i and each new face f, use P (85):

```text
q_face_end = q_i0 + Gq_i0 (f_end-c_i0-v_i0 dt) + dt (D_v q)_i0
```

Use old cell-centred primitives and old limited gradients throughout this prediction. New neighbours are handled by evaluating each surviving cell's own old data at the new face. Positions use the image/winding of that endpoint face relative to the persistent cell ID, not a minimum-image difference between times. In 2.5D, positions/gradients have x/y coordinates only; all v/B components remain physical. No provisional conservative-state closure supplies endpoint Riemann primitives. Final closure uses updated Q divided by endpoint volume and B reconstructed from updated A; invalid pressure rejects the attempted step.

Generator motion is explicit and linear over the step: fixed wtilde=0, prescribed rigid translation, or wtilde=v_i0 in active geometry dimensions, chosen by configuration. No mesh regularization or adaptation initially. For paired generators r_i,r_j in the same periodic image, put d=r_j-r_i, m=(r_i+r_j)/2. Assign

```text
w_face = (wtilde_i+wtilde_j)/2
       + d * [(wtilde_i-wtilde_j) dot (f-m)] / |d|².
```

**D:** differentiating the bisector identity `(f-m) dot d=0` gives this normal speed. Its chosen tangential component is an E convention. Evaluate it at both endpoint geometries with the same prescribed generator velocities. Opposite face ownership reverses the normal and conservative contribution, not the physical face velocity. Reject coincident generators and invalid meshes.

Required fixtures: affine primitive material derivatives, uniform and rotational states, predictor joint boosts with nonzero estimated div(B), differentiated-bisector normal speed, orientation reversal, and equal/opposite exchanges across a face that changes area. Full deforming-mesh temporal convergence is an M1/M2 implementation gate.

## U2: reconstruction and endpoint refresh

Adopt the existing 2D free-intercept LS operators: neighbour-centroid samples for cell gradients, face-centroid samples for Eq. (71), both weighted by face area/edge length, excluding the target observation. Scaled covariance conditioning and rejection thresholds are as recorded in the planar contract. The 3D extension must use a dimension-appropriate conditioned solve and has its own implementation gate; do not transplant the 2x2 determinant criterion to a 3x3 matrix.

For a scalar q, form bounds over the target and its face neighbours. For each face extrapolation delta=Gq dot(f-c), compute the largest factor in [0,1] keeping q+factor*delta within these bounds. Use the minimum factor over the cell's faces. Apply componentwise to separate copies of primitive/A gradients, anchored at the stored cell value. Raw A gradients remain unlimited for curl and cleaning divergence.

At the second A stage, rebuild both LS geometrical stencils on the endpoint mesh. Fit **A_star** and **phi_star** on its neighbour centroids; make new limited A_star gradients and new neighbour-extrema bounds. Use these values in endpoint donor reconstructions and gradient(phi_star). Use A_star in the distortion term. Use endpoint face Riemann states from the old-data primitive predictor above for the induction term; do not replace those B states with curl(A_star). The HLL fallback uses its numerical EMF, as already documented. The stored old div(A0) and cs0 still supply cleaning C1. This resolves the ambiguous endpoint-refresh policy as E; it does not alter P's explicit frozen-source prescription.

Required fixtures: separate neighbour/face affine reproduction, constant annihilation, both donor signs, endpoint-stencil rebuild at a topology change, and time convergence with limiting disabled/enabled reported separately.

## U3: smooth auxiliary field and frame

P pp. 10-12 provides adaptive tricubic corner interpolation and volume-weighted averaging. The initial 2.5D implementation uses a **uniform periodic bicubic** reduction for each of the three velocity components. Adaptive tricubic interpolation is specified below for later 3D work; its implementation is outside M0.

Root layout is 4 intervals along each active periodic axis, anchored at the domain origin. Rectangular boxes use tensor-product cells with the corresponding axis spacings; this is an E extension of P's cubical construction. For each corner, average fluid velocities over geometric cell centroids in the half-open, periodic, corner-centred box of one interpolation-cell width on each axis. Each included Voronoi cell contributes its full volume; membership uses centroids, not volume-overlap fractions. Store membership counts and maximum included cell volume. Ties follow the half-open convention consistently across seams.

If any root sampling box is empty, rebuild the entire root with 2 intervals per axis, then 1 if needed. Never fill isolated empty corners using unrelated nearest-cell values. At a one-interval root use the global volume-weighted velocity and zero derivatives. With two intervals the centred first derivative is zero because the two periodic neighbours coincide; this is a deliberately coarse, smooth representation, not an affine-exact periodic approximation. Report the selected root and coarsening count. No requirement of 100 samples is imposed on these fallback roots.

Corner derivatives use the centred difference `D_a f=[f(x+h_a)-f(x-h_a)]/(2 h_a)`. Mixed jets use commuting tensor products `D_x D_y`, `D_x D_z`, `D_y D_z`, `D_x D_y D_z`. Values and each required mixed jet are stored once per periodic corner. The cubic Hermite value bases are `(2s³-3s²+1, -2s³+3s²)` and derivative bases `(s³-2s²+s, s³-s²)`; multiply physical derivative jets by the product of their axis spacings, and differentiate the interpolant analytically with the reciprocal spacing. Shared corner jets give C1 continuity.

For later adaptive 3D use eps_vol=.01, split all eligible leaves breadth-first with stable index ordering, and require every daughter to be nonempty with `max(V_cell) <= eps_vol V_daughter`. All parent corners must be interior at their level (periodic root corners are interior). Stop at configured max_level=12; report this cap and failures of the density criterion. Fine corners with all 26 level neighbours are interior. First assign inherited parent-polynomial values/jets to boundary corners, then independent volume-weighted values at interior corners, then obtain the interior derivative jets with the centred stencils using this completed fine-level value set. Boundary jets stay inherited. Rebuild this hierarchy at each global synchronization. Refinement of the auxiliary interpolation field is distinct from adaptation of the fluid mesh.

The within-step temporal extension is explicit: compute `vbar=sum(V_i v_i)/sum(V_i)` from initial primitives. Freeze the auxiliary polynomial in coordinates translating with vbar, sampling at

```text
xi_stage = wrap(c_stage - vbar * stage_time)
u_stage = u_initial(xi_stage)
H_stage = H_initial(xi_stage).
```

In 2.5D, project c and vbar onto x/y for sampling; retain all three components of the interpolated u. Keep initial vbar, corner data and the selected hierarchy through all retries of that step. A uniform boost b sends c_stage to c_stage+b*stage_time and vbar to vbar+b; xi is unchanged and u shifts by b. This ensures covariance of the auxiliary sampling. P specifies refreshes at synchronization but does not prescribe this temporal extension; it is an E choice to avoid freezing the field in an absolute laboratory frame.

Required fixtures: constant/boost preservation; exact Hermite reconstruction from supplied analytic cubic jets; analytic first derivatives; face and periodic-seam C1 continuity; parent/fine continuity; mixed-derivative scaling; empty-bin/global-coarsening behavior; and the translated-frame identity. Centred-difference jets are not exact for arbitrary cubic input data and receive separate convergence tests. Nonconstant affine reproduction is checked on an unwrapped polynomial patch, not on a discontinuous periodic affine field.

## U4-U5: cleaning, global timestep and failure policy

Set phi_initial=0, alpha=1, beta=.15, eta=0; interpret cs as `sqrt(gamma p/rho)` without auxiliary smoothing. Equivalent-area radius is `sqrt(V/pi)` in 2D and equivalent-volume radius `(3V/(4pi))^(1/3)` in 3D. These radius/EOS conventions are E. Store fixed periodic mean B separately; use Eq. (76) in both A stages.

The profile retains `C1=alpha cs0² div(A0)-beta cs0 phi_star/r1` and the printed cleaning bounds. The [measured first-order longitudinal gauge mode](M0_OPERATOR_CHECKS.md) is accepted as a documented property of this reference prescription, not treated as a failed implementation of Heun and not silently corrected. A fully reevaluated source is only a separately named comparator. Report temporal errors of physical B and gauge-dependent A/phi independently. If later physical-field accuracy fails, any revised method receives a new profile and validation gate.

Build initial u/H, prescribe wtilde, and solve the initial spatial face problems before selecting the final dt: their rates/wave speeds are needed below and are independent of dt. At the initial stage w_adv=wtilde. Initial global dt uses CFL=.3 times the minimum, over cells, of:

```text
V / sum_faces(area * maximum_Riemann_wave_speed_relative_to_face)
1 / sum_faces(abs((w_adv-u) dot g_face))
r / (alpha cs)
beta r / (alpha cs)
1 / norm_infinity(H^T)
min_neighbours(r / norm(wtilde_i-wtilde_j))
```

A zero denominator yields no restriction. Initial bounds use r0 and cs0. Predict cell-centre rho1/p1 with the same old-data formula as the face predictor, substituting f=c1, and set cs_pred1=sqrt(gamma*p_pred1/rho_pred1); invalid predicted rho/p rejects the attempt. Apply endpoint bounds using corrected w_adv=what, r1, endpoint face wave speeds/stencils and the translated initial auxiliary field. In the endpoint cleaning bounds use max(cs0,cs_pred1); after final closure also include cs_recovered1 in this maximum and recheck. This extra safety check does not change the frozen cs0 used in C1. These are explicit safety choices, not a theorem of nonlinear stability. Retry from immutable initial state with dt/2 on violated endpoint bounds, nonfinite state, invalid primitive/closure, or failed geometry/stencil construction. Allow 16 trials, then return the recorded failure; no floors, repair or silent gradient fallback. Persistent rank-deficient initial geometry fails immediately. Count each rejection by cause.

## Scope, diagnostics and review

Periodic boundaries only, global steps, fixed connectivity during each rate evaluation, persistent generator IDs and unwrapped cell paths. Full topology changes between endpoint meshes are allowed only after geometric/operator implementation gates pass. General boundary operators, entropy closure, resistive diffusion, Hessians, initial Poisson solves, local steps, fluid adaptation, gravity and cosmology remain explicit later extensions.

Use the LS, arithmetic-face and separately limited-face divergence operators already documented in the planar reference. For dimensionless divergence use `r*div(B)/(|B|+Bfloor)` with `Bfloor=1e-12*Bscale`, where Bscale is fixed by the benchmark initial field scale. Preserve volume weighting, signed and RMS/max forms, and mean-B drift. The [benchmark packet](M0_BENCHMARK_PACKET.md) fixes configurations, norms and quantitative gates before evaluating the future general implementation.

Independent review must identify the reviewed revision and disposition of each choice. An AI review is labelled as such and does not imply author confirmation, human peer review or validation of the future implementation.
