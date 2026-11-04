# M0: paper-to-code specification

Issue: [#1](https://github.com/arm2arm/openmhd-rs-/issues/1). Review draft, updated 2026-11-04.
**This specification is not a validation of the full method.** The [engineering profile](M0_ENGINEERING_DECISIONS.md) now supplies explicit choices for U1-U5; the [review checklist](M0_REVIEW.md) records acceptance separately from implementation. The [experimental planar reference](COUPLED_2D.md) implements a restricted subset with explicit deviations, not the complete stage algorithm specified here.

The [M0 completion checklist and decision register](M0_REVIEW.md) distinguishes completed evidence, planar-only policies and remaining general-method decisions. The [isolated gauge/cleaning audit](M0_OPERATOR_CHECKS.md) records new Rust kernels and a manufactured temporal-order finding for Eq. (90).

## Source and evidence conventions

The primary source, denoted **P**, is Springel, Mayer & Pakmor, *Divergence-free magnetohydrodynamics on a moving mesh*, [arXiv:2609.35989v1](https://arxiv.org/abs/2609.35989v1), submitted 2026-09-28. The complete [37-page PDF](https://arxiv.org/pdf/2609.35989v1) and [HTML](https://arxiv.org/html/2609.35989v1), including Appendix A, were consulted on 2026-11-03. Page numbers below are the PDF's printed, one-based pages. Prefer PDF equation labels: the HTML labels Appendix A's equations (117)-(122), while the PDF labels them (A1)-(A6).

Downloaded PDF provenance:

```text
URL:    https://arxiv.org/pdf/2609.35989v1
bytes:  14060781
SHA256: 6e12da18a86c57536fc26f2baf86d15d6db2e378e040a59bc9b82870b2dfcb84
```

The PDF was extracted and important formula pages were rendered and visually checked against the HTML: pp. 7-16 and 18 include the cleaning, reconstruction, smoothing, mean-field and integration formulas. P is distributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); this specification attributes and restates the method, and imports no AREPO source code. The repository's MIT license does not relicense the paper.

Evidence labels:

- **P:** explicitly specified in the primary text, with page/equation or numbered implementation step.
- **D:** our algebraic derivation or interpretation of P, requiring review; not a claim about unpublished AREPO implementation details.
- **E:** proposed OpenMHD-RS engineering choice or scope restriction.
- **U:** unresolved detail; must not acquire an undocumented default in implementation.

The main method and stencils below are verified against P. Verification of a transcription is distinct from independent scientific review, proof of numerical stability, or reproduction of the paper's results.

## State, notation and units

**P, pp. 2-3, Eqs. (1)-(14); p. 8, Section 4.1; p. 14, Section 5.1.** The paper uses Lorentz-Heaviside magnetic units, with magnetic pressure `|B|²/2`. In Newtonian, ideal MHD:

```text
p = (gamma - 1) rho u_thermal
e = u_thermal + |v|²/2 + |B|²/(2 rho)
U_density = (rho, rho v, rho e)
Q_cell = (m, momentum, E_total) = V U_density
s = p/rho^gamma; S_entropy = m s                 [optional]
```

Store `A_i` and the cleaning scalar `phi_i` as **point values at the geometric cell centre `c_i`**, not volume integrals and not values at generator `r_i`. The free intercept of a local fit, `Abar_i`, need not equal stored `A_i`. Distinguish these velocities:

| Symbol | Meaning |
| --- | --- |
| `v_i` | Fluid velocity |
| `u_i` | Smooth auxiliary velocity used in the gauge; not thermal energy |
| `wtilde_i` | Prescribed mesh-generator velocity |
| `w_i` | Actual average velocity of the geometric cell centre over a step |
| `what_i` | Corrected second-stage advection velocity |
| `w_face_ij` | Velocity of the moving Voronoi face |

Use `a_ij` for face area, `Sigma_i = sum_j a_ij` for total cell surface area, `x_face_ij` for face centroid and `d_face_ij = x_face_ij-c_i`. This avoids P's reuse of `S` for surface area/entropy and `f_ij` for position/displacement.

**D, dimensional audit:** `[A]=[B] length`, `[psi]=[phi]=[B] length²/time`, `[eta]=length²/time`. The Jacobian convention is `G[a][b]=partial_b A_a`, and similarly `H[a][b]=partial_b u_a`. P's `A dot grad(u)` means **`H^T A`**, whose component `b` is `sum_a A_a partial_b u_a` (p. 4, Eq. (21), footnote 3). It does not mean `H A`.

**E:** `f64`, constant gamma per benchmark, no gravity, no cosmology, serial execution and global timesteps initially. Gamma is not a universal paper constant: e.g. Alfvén/Orszag-Tang use `5/3`, Brio-Wu uses `2`. Record each configuration's length, time, density and magnetic units.

## Evolution and gauge

**P, pp. 5-7, Eqs. (35)-(42); p. 13, Eqs. (75)-(76).** For a fixed periodic mean field `B0`, the combined continuum equations to discretize are:

```text
B = B0 + curl(A)
psi = u dot A
D_w A/Dt = (v-u) cross B - H^T A
           + [(w-u) dot grad] A - eta J + grad(phi)
           + u cross B0
D_w phi/Dt = alpha c_s² div(A) - beta_clean c_s phi/r_cell
J = curl(B)
```

The mean-field term is Eq. (76); the other terms are Eq. (42). Do not omit Eq. (76) just because it is not repeated in the stage equations (80)/(86). The gauge scalar `psi=u dot A` is different from the evolved cleaning scalar `phi`. There is no separately integrated `psi` equation in this algorithm.

**P:** default cleaning coefficients `alpha=1`, `beta_clean=0.15`; `tau=r_cell/c_s` (pp. 6-7, Eq. (41)). The text calls `c_s` the local sound speed, not the fast magnetosonic speed. **E/D:** for the ideal-gas EOS interpret this as `sqrt(gamma p/rho)`; explicitly review that choice before implementation.

**P:** cleaning acts on `div(A)`, with **positive** `grad(phi)` in the A equation and positive `alpha c_s² div(A)` in the phi equation. It is not Dedner cleaning of B, and it is not Powell source-term evolution. The continuum identity `curl(grad(phi))=0` does not guarantee a zero discrete magnetic perturbation on an irregular stencil.

**D:** expanding the vector identities gives the Eulerian equation

```text
partial_t A = v cross B - grad(u dot A) + grad(phi) - eta J.
```

Here the added `u cross B0` is essential to that equality. For uniform `v=u=w`, constant `B0` and spatially constant A, `dot(A)=v cross B0`, although `dot(B)=0`. Tests with a mean field must compare physical B rather than require raw A to remain invariant under a velocity boost.

**P, p. 7:** `D_clean=alpha c_s r_cell/beta_clean`, Eq. (45), and the additional printed timestep bounds are

```text
dt < r_cell/(alpha c_s_prime)          (49)
dt < r_cell²/D_clean_prime             (50)
```

Primes in these bounds denote optionally smoothed transport coefficients, not the later RK predictor. P says smoothing these coefficients was not needed in its tests. **D:** the undamped constant-coefficient cleaning waves have speed `sqrt(alpha) c_s`. Preserve the printed Eq. (49) separately; do not silently replace it by that wave speed. **U:** the full hydro/MHD CFL factor and geometry-dependent cell-radius definition are not given here. Proposed 2D radius `sqrt(area/pi)` is **E**, not a verified paper formula. Extra explicit resistivity would need its own diffusion bound.

## Neighbour reconstruction and curl

### Default linear fit

**P, pp. 8-9, Eqs. (51)-(61).** For each component of A, use only cells sharing a Voronoi face with i, geometric-centre coordinates and face-area weights. Fit a free intercept and gradient:

```text
delta_ij = c_j - c_i                   [same periodic image]
X_ij = [1, delta_x, delta_y, delta_z]^T
M_i = sum_j a_ij X_ij X_ij^T
b_i,k = sum_j a_ij A_j,k X_ij
M_i chi_i,k = b_i,k
chi_i,k = [Abar_i,k, partial_x A_k, partial_y A_k, partial_z A_k]^T
qfull_ij = a_ij M_i^(-1) X_ij
D_ij = qfull_ij[1..4]                  [three derivative coefficients]
G_i[k][b] = sum_j D_ij[b] A_j[k]
B_i = B0 + (G[z][y]-G[y][z], G[x][z]-G[z][x], G[y][x]-G[x][y])
```

The target cell's stored value is not an extra observation in this fit. Do not substitute the usual centre-anchored fit of neighbour differences. Eq. (59)'s `qfull` has four entries; Eq. (72) requires only its three derivative entries, denoted `D` here.

**P:** compute B from **unlimited** G. Save that G for `div(A)=trace(G)` and optional current/Laplacian calculations before making a separate limited copy for A face reconstruction. Estimate gradients of B by applying the ordinary linear estimator to the reconstructed cell B values. Keep unlimited derivatives for current estimates; limit B gradients for extrapolation to faces. P does not require `div(B)` from these successive derivatives to vanish to roundoff.

**E:** solve a scaled weighted least-squares problem with a rank-revealing method, rather than form an inverse in production. Record rank/conditioning failures and reject an unusable stencil. The conditioning threshold and any stencil enlargement/fallback require a documented choice; do not insert a pseudoinverse or zero gradient silently.

### Optional quadratic fit

**P, pp. 9-10, Eqs. (62)-(67).** Use neighbours plus neighbours of neighbours, a free intercept and symmetric Hessian for each component:

```text
X = [1, dx,dy,dz, dx²/2,dy²/2,dz²/2, dx dy,dx dz,dy dz]
```

This is a 10-coefficient fit per component in 3D. P specifies inverse-distance weighting, but does not fully specify distance regularization or degeneracy handling. The Hessian gives

```text
partial_b B_a = sum_(c,d) epsilon_(a,c,d) partial_b partial_c A_d
J = grad(div(A)) - laplacian(A)
```

These compact forms restate Eqs. (66)-(67). The trace of this *particular*, unlimited Hessian-derived B Jacobian cancels algebraically. Differentiating the small-stencil cell B values is a different diagnostic. Componentwise limiting can destroy the Hessian trace cancellation. P prefers the direct-neighbour fit for B itself, because the larger stencil broadens sharp features. Neither a quadratic fit nor a Delaunay loop-integral reconstruction is the default B construction. The latter is discussed and rejected as the preferred method in Section 4.2.3, p. 10.

### Limiting and face advection

**P, pp. 9-10, 12 and 14:** limit extrapolations to avoid new extrema relative to neighbouring cell values. The precise default limiter formula and whether the target value participates in bounds are **U**; minmod is mentioned as a more dissipative alternative for the fixed-mesh flux loop (p. 20), not established as the universal default.

**P, p. 12, Eq. (71):** construct a different least-squares derivative operator `g_ij` for samples at face centres, rather than neighbour centres. With `b_i=w_adv_i-u_i`, its A-advection contribution is

```text
R_adv_i = sum_j A_up_ij (b_i dot g_ij)
A_L_ij = A_i + G_limited_i (x_face_ij-c_i)
A_R_ij = A_j + G_limited_j (x_face_ij-c_j)
A_up_ij = A_L_ij if b_i dot d_face_ij < 0 else A_R_ij
```

The sign is intentional: the differential equation is `dot(A)=+b dot grad(A)`, so transport velocity is `-b`. Each receiving cell's `b_i` controls its selection. This is not the fluid mass-flux donor rule. **U:** P says the face-centre least-squares construction is analogous to the earlier estimator, but gives no separate complete matrix/weight prescription. A free-intercept face-area-weighted fit is a candidate **E** choice, not a verified hidden stencil.

## Smooth auxiliary velocity

**P, pp. 10-12, Eq. (68), Figure 4.** P abandoned a real-space local kernel fit because of noisy derivatives. Its chosen representation is an auxiliary adaptive Cartesian mesh with a componentwise tricubic polynomial

```text
u_component(x,y,z) = sum_(a,b,c=0..3) coefficient[a,b,c] x^a y^b z^c.
```

At each cube corner the eight inputs are the value, three first derivatives, three mixed second derivatives and the mixed third derivative. Derivatives are obtained from neighbouring grid values; evaluate the polynomial's Jacobian analytically. Shared corner data produce a globally C1 representation. The required values at corners are volume-weighted velocity averages in cubes centred at those corners, of side equal to the interpolation grid spacing; these sampling cubes are staggered by half a grid spacing from interpolation elements.

Adaptive rules in P:

1. Replace selected cubes by eight daughters of half the side length.
2. Interior fine corners have all 26 fine neighbours. They receive new averaged velocities and finite-difference derivative inputs.
3. Boundary fine corners inherit both values and derivatives from the parent polynomial. Do not independently average them.
4. Refine only if the largest Voronoi cell in each daughter has volume below `epsilon_vol * V_daughter`; the default range is `epsilon_vol=0.002-0.01`, corresponding to smoothing over roughly 100-500 cells.
5. P usually also requires all eight parent corners to be internal at that level. It renews the auxiliary field on fully synchronized steps, not every local substep.

**D/E:** a tensor-product cubic Hermite basis can realize the specified polynomial constraints. Physical derivative inputs must be scaled by element side lengths when using normalized coordinates; its evaluated Jacobian must undo those factors. **U:** root-grid size, empty sampling regions, exact finite-difference formulas, cell-membership convention and a 2D reduction are not exhaustively specified in P. A uniform periodic bicubic grid for the first 2D implementation is a proposed dimensional reduction, to be recorded as such. It must preserve constants, boost covariance and continuity across periodic seams. Replacing the field with unrelated per-cell smoothed fits would depart from the selected method.

## Fluid coupling and energy

**P, p. 15, Section 5.1 steps xi/xv:** solve HLLD Riemann problems in the moving face frame, using limited primitive reconstructions. Transform momentum/energy fluxes to the lab frame, and apply a single face contribution with opposite signs to the two cells. Optional entropy is advected from the mass donor. Use the returned face solution's lab-frame velocity and B in the A update; a flux-only API is insufficient unless it also provides the required electric-field/state information.

**D:** with a face normal oriented out of cell i, a laboratory conservative flux through a face moving with velocity `w_face` is `(F(U)-U w_face^T) dot n`. In terms of a face-rest-frame flux `(f_m, f_p_prime, f_E_prime)`, Galilean transformation gives

```text
f_p_lab = f_p_prime + w_face f_m
f_E_lab = f_E_prime + w_face dot f_p_prime + |w_face|² f_m/2
delta Q_i = -dt_stage a_face f_lab
delta Q_j = +dt_stage a_face f_lab
```

These transformations follow from the conservative state transformation, not new equations quoted from P. **U:** P delegates HLLD internals and the base moving-mesh hydrodynamics to prior literature. It does not fully specify a common face-normal B prescription, HLLD degeneracies/fallbacks, positivity treatment, moving-face velocity formula or mesh regularization parameters. These are prerequisites for an implementation-ready flux module; no claim of exact AREPO equivalence is justified from the present paper alone.

**P, pp. 13-14, Eqs. (77)-(79):** optional artificial dissipation uses `eta_eff=alpha_diss v_A r_cell`, with a stated typical `alpha_diss=0.1-0.3`. P says its presented tests did not need this addition. The discrete optional term is `+eta laplacian(A)` (Eq. (73)), approximating `-eta J` when `div(A)` is small. These are not identical operators at finite `div(A)`.

Optional entropy heating is `-(gamma-1)/rho^(gamma-1) J dot dot(A)_diss`, applied only when the scalar product is negative. There is no extra total-energy increase for this heating. **E:** disable explicit physical/artificial resistivity initially, and record it as zero in every reference configuration.

**P, Section 4.7:** an optional entropy closure is used only if plasma beta is below `beta_low` at both step endpoints and the maximum Riemann Mach number over the step is below `Mach_low`. It resets total energy from entropy and logs the resulting energy adjustment. Otherwise entropy is reset from total energy. Neither threshold is numerically specified in this section. The shorter summary in step v must not erase the Mach/endpoints conditions. **E:** keep this closure disabled in the initial conservative baseline; reject invalid pressure rather than silently repair it. Later enabling it requires specified thresholds, an energy-correction ledger and validation. There is no unconditional magnetic-energy reset after every curl reconstruction in the described conservative baseline.

## Two-stage sequence

**P, pp. 14-16, Section 5.1, steps i-xvii and Eqs. (80)-(92).** This is an endpoint-geometry, Heun-type sequence. It is not a generic RK2 call that rebuilds every primitive from a provisional conservative half-state.

The complete cell A rate, with explicit derivative notation, is

```text
R_i = sum_j (a_ij/Sigma_i) [(v_face_ij-u_i) cross B_face_ij]
      - H_i^T A_i
      + sum_j A_up_ij [(w_adv_i-u_i) dot g_ij]
      + sum_j phi_j D_ij
      + eta laplacian(A_i)
      + u_i cross B0
```

The terms map to Eqs. (69), (70), (71), (72), (73), and (76), respectively. Use total B, including B0, in the Riemann problems and the first term. A rates are pointwise rates; they do not receive equal-and-opposite conservative face updates.

| P steps | Required operations and dependencies |
| --- | --- |
| i-iii | Build/reuse the old mesh; construct unlimited A gradients and B; optionally Hessians/current. Geometry and neighbour values must refer to the same time. |
| iv-vii | Retain unlimited derivatives; make limited A gradients; obtain primitives using B and total energy; compute and limit primitive gradients. Preserve the initial state for predictions. |
| viii-x | Choose global dt satisfying all bounds, prescribe generator velocities, construct/evaluate smooth u and its Jacobian at old centres. |
| xi | Solve old-face Riemann problems. Accumulate first conservative contribution weighted by dt/2, with opposite face signs. |
| xii | Compute R0 using `w_adv=wtilde`, old geometry and old face solutions. Compute `C0=alpha c_s0² div(A0)-beta_clean c_s0 phi0/r0`. |
| xiii-xiv | Move generators by full dt (82); construct endpoint geometry. Keep old values, old centres and old gradients for prediction. |
| xv | Predict primitives to the new face positions using old gradients and hydrodynamic/induction time derivatives (83)-(85); solve new-face Riemann problems and accumulate dt/2 contributions. |
| xvi | Use predicted A/phi (87)-(88), endpoint geometry, endpoint u evaluations and endpoint face solutions to compute R1 with corrected `what` (89). Evaluate C1 exactly as described below (90). |
| xvii | Apply trapezoidal A/phi update (91)-(92), retain endpoint mesh; next step starts by reconstructing B from updated A. |

**P:** the predictors and centroid correction are

```text
A_star   = A0   + dt R0
phi_star = phi0 + dt C0
w_actual = (c1_unwrapped-c0_unwrapped)/dt
what     = 2 w_actual - wtilde
A1       = A0   + dt (R0+R1)/2
phi1     = phi0 + dt (C0+C1)/2
```

**D/E:** track consistent unwrapped centroid coordinates through periodic crossings. A naive subtraction of wrapped positions can create a spurious velocity of box-size/dt; a minimum-image displacement can also fail for a large boost. Persistent generator IDs and image/winding information are needed.

**P, p. 16, Eq. (90), explicit following sentence:** second-stage cleaning uses

```text
C1 = alpha c_s0² div(A0) - beta_clean c_s0 phi_star/r1.
```

The source divergence and sound speed remain those at the **beginning** of the step; only radius and the damped scalar are updated. Do not silently replace that source by `div(A_star)` on the endpoint mesh. **U:** this frozen-source prescription needs a dedicated coupled-cleaning temporal-convergence assessment; P's use of Heun for the main scheme is not proof of second-order accuracy for every frozen coefficient/source.

**P, p. 15, Eq. (85):** moving-mesh primitive prediction is of the form

```text
q_L = q_i0 + grad(q)_i0 dot (x_face1-c_i0-v_i0 dt)
              + (D_v q/Dt)_i0 dt.
```

For a stationary mesh P also gives the equivalent Eulerian version (84). Lorentz acceleration uses the **limited** B Jacobian, not the optional unlimited current of Eq. (67). End-state B for this Riemann prediction comes from the induction equation, not from advancing an independently conserved B. Appendix A, p. 37, explicitly explains why both A and B evolution equations are listed. The precise discrete primitive B predictor also needs review: expanding the curl in Eq. (6) gives a `v div(B)` term, which vanishes for a continuum solenoidal field but not necessarily for the estimated cell derivatives. P does not spell out this expanded numerical predictor. The endpoint gradient/predicted-A face reconstruction details that P leaves implicit remain in U below.

Design pseudocode (E names; P ordering):

```text
advance_global(old):
    geom0 = old.mesh
    raw_A0 = neighbour_fit(old.A, geom0)
    B0_cells = curl(raw_A0) + mean_B
    prim0, raw_prim0 = primitives_and_gradients(old.Q, B0_cells, geom0)
    limited_A0, limited_prim0 = limit_separate_copies(raw_A0, raw_prim0)
    wtilde = prescribe_generator_velocities(prim0)
    smooth_u = build_auxiliary_field_at_synchronization(prim0)
    face0 = riemann(geom0, reconstruct(prim0, limited_prim0))
    dt = choose_global_dt(geom0, face0, smooth_u, wtilde)
    dQ0 = oriented_conservative_face_rates(face0)
    R0, C0 = first_potential_rates(old, geom0, face0, wtilde, smooth_u)
    A_star, phi_star = old.A + dt*R0, old.phi + dt*C0
    geom1 = build_mesh(old.generators + dt*wtilde)
    face1 = riemann(geom1, predict_primitives_from_initial_state(prim0))
    dQ1 = oriented_conservative_face_rates(face1)
    what = 2*unwrapped_centroid_displacement(geom0, geom1)/dt - wtilde
    R1 = endpoint_potential_rate(A_star, phi_star, geom1, face1, what, smooth_u)
    C1 = alpha*cs0²*divA0 - beta_clean*cs0*phi_star/radius(geom1)
    next.Q = old.Q + dt*(dQ0+dQ1)/2
    next.A, next.phi = old.A + dt*(R0+R1)/2, old.phi + dt*(C0+C1)/2
    next.mesh = geom1
    # Reconstruct B before the next primitive closure/diagnostic snapshot.
```

This pseudocode deliberately leaves unresolved reconstruction/flux policies as named operations; it is not executable solver code. Buffering both conservative contributions is an E choice equivalent to P's incremental accumulation provided initial data are preserved and no midpoint primitive closure is inserted. It proposes retaining the auxiliary interpolation field within a step and sampling it at the new centres; the within-step field-refresh policy should be recorded explicitly when resolving U3.

## Periodicity, dimensional reduction and later extensions

**P, pp. 12-13:** evolve periodic A for the fluctuating field and store a fixed mean B separately. Do not periodically wrap `A_const=B0 cross x/2` and then differentiate its jumps. Fit neighbour/face coordinates using consistent periodic images, with unchanged periodic A and phi values. Periodic fluxes must share orientation and geometry across paired boundaries.

P's baseline uses periodic domains, but this is not a claim that all its examples do: the MRI has cylindrical zero-gradient boundaries plus vertical periodicity (pp. 29-30); Kelvin-Helmholtz uses a doubled mirrored domain to permit periodicity (p. 25); collapse uses periodic gas boundaries and nonperiodic gravity (p. 32). **E:** general nonperiodic A/phi boundary conditions are deferred; do not invent them from the abstract.

**P, p. 4, Eq. (25); p. 22, Section 6.4:** strictly planar flow with `A=(0,0,Az)`, `v_z=0`, no fluctuating Bz and z-invariance has `D_v Az/Dt=0` for the zero-mean, nondissipative case. Its distortion and div(A) vanish, allowing the special choice `u=v`. That simplified test does not exercise the hard 3D gauge/cleaning dynamics.

**E/D:** use 2D geometry with all three vector components for a circularly polarized Alfvén wave (often called 2.5D). A single Az degree of freedom is insufficient. Drop the z column from the least-squares basis rather than attempt a singular 3D fit to coplanar points; retain

```text
B = mean_B + (partial_y Az, -partial_x Az, partial_x Ay-partial_y Ax).
```

A general three-component 2D test no longer inherits the single-Az simplifications. The paper's oblique Alfvén test is genuinely 3D; a 2D version must be labelled an adaptation.

**P, pp. 16-17, Section 5.2:** later local timesteps use a power-of-two hierarchy and the smaller neighbouring step for conservative face exchanges. A/phi rates are evaluated at each cell's own endpoints, not accumulated as conservative intercell fluxes. Predict passive neighbours' A/phi and geometry to the requested time. Double stencils require constructing neighbours of active cells as well. **E:** deferred to M4.

**P, pp. 16-17, Section 5.3:** refinement initializes A from a free-intercept fit at the new centre; derefinement drops the removed A and adjusts neighbours' A for centroid shifts with their last Jacobians. Conservative variables use volume-overlap transfers. New generators are placed at a farthest cell vertex. Active/nonadjacent eligibility rules and random selection resolve conflicts. **U:** transfer of cleaning phi is not specified. **E:** no adaptation in M1.

**P, p. 17, Eqs. (93)-(95):** an optional initial-field inversion solves `laplacian(A)=-curl(B_star)` with matched discrete gradient/divergence operators using BiCGSTAB. The scalar in Helmholtz decomposition (93) is not automatically the evolved cleaning state. **D/U:** separate the periodic mean first, fix the periodic Poisson nullspace and specify residual tolerances; unstructured discrete curl/divergence compositions do not automatically reproduce continuum identities. **E:** start from analytic periodic A and explicit mean_B instead of implementing this solve.

**P, pp. 36-37, Appendix A:** cosmological variables and (A1)-(A6) were read; they are outside M0/M1 implementation scope. They must receive a separate derivation/review before use, including their printed scale factors and pressure conventions. No cosmological factors enter this Newtonian specification.

## Equation-to-code and operator-test map

The identifiers below describe mathematical contracts; the implementation column names the present Rust bindings where available. A local point-source check does not replace a face stencil or a coupled mesh-stage test.

Previously unresolved engineering contracts in this table are completed by [paper-global-v1](M0_ENGINEERING_DECISIONS.md): the solenoidal primitive predictor, moving-face normal speed, endpoint A/phi-stencil refresh, tensor-Hermite auxiliary field in a translating frame, and explicit radius/timestep policies. Those are E choices, not newly discovered publication details. The profile takes precedence over earlier tentative E suggestions in this extraction; P transcriptions remain unchanged.

| Source in P | Contract / implementation | Reference check |
| --- | --- | --- |
| p. 3, (7)-(9), (14); p. 14, step v | [`IdealGas::recover`](../crates/mhd-core/src/lib.rs); cell integrals vs densities | Implemented: EOS round trip, invalid states and uniform coupled state |
| p. 4, (21), footnote 3; pp. 6-7, (38), (42) | [`gauge::PointSources::rate`](../crates/mhd-vector-pot/src/gauge.rs); `-H^T A` | Implemented: arbitrary-Jacobian Eulerian identity, shear and rotation; also Python algebra |
| pp. 8-9, (51)-(61) | [`Derivatives::build`](../crates/moving-mesh/src/lib.rs); free intercept, centroid differences, face weights | Implemented in 2D: affine/constant, periodic images and regular/jittered curl convergence |
| pp. 9-10, (62)-(67) | Optional `fit_hessians`; symmetric mixed derivatives | Quadratic manufactured A; label Hessian trace vs independently differentiated B |
| pp. 10-12, (68), Fig. 4 | `SmoothVelocity::sample`; returns u and analytic H | Constant/affine input, periodic seams, coarse/fine continuity, uniform-boost covariance |
| p. 12, (69); p. 15, step xi | [`mhd_planar::Simulation::rate`](../crates/mhd-planar/src/lib.rs); face states with total B | Implemented planar-only: uniform translating state, magnetic force and joint boost |
| p. 12, (70) | `gauge::PointSources::rate` distortion term | Implemented: covector shear/rotation and transpose/sign audit |
| p. 12, (71) | `mhd_planar::Simulation::rate`; separate face-centre `Derivatives` | Implemented planar stencil and scalar donor tests; general endpoint refresh remains U2 |
| p. 12, (72); p. 8, (59) | Proposed `gradient_phi`; derivative entries only | Raw gradient is accepted by point kernel; mesh phi-gradient coupling remains unimplemented |
| pp. 6-7, (41)-(42); pp. 15-16, (81), (90) | `gauge::Cleaning::begin` / `CleaningStage`; frozen initial source | Implemented isolated signs/stages and [damped-mode temporal study](M0_OPERATOR_CHECKS.md); physical curl contamination remains open |
| p. 7, (45), (49)-(50) | `gauge::Cleaning::bounds` | Implemented scaling checks; not a complete MHD timestep controller |
| p. 13, (75)-(76) | `gauge::PointSources::rate` mean-field term; planar fixed mean B | Implemented positive drift/boost and continuum identity; general mesh coupling remains open |
| p. 12, (73); p. 13, (77)-(78) | Point kernel accepts continuum `-eta J`; discrete diffusion/heating deferred | Full diffusive mode, J sign, nonnegative entropy source and energy ledger tests remain future work |
| pp. 13-14, (79), Section 4.7 | Optional `EntropyClosure` | Both beta endpoints + Mach condition; measure every total-energy reset |
| pp. 15-16, (80)-(92) | Proposed `GlobalStep`; preserve old and predicted state | Full endpoint predictor/stages remain future work; planar MOL Heun is an explicit deviation |
| p. 16, (87)-(89) | `predict_potential`, `centroid_velocity` | Mean first/second velocity equals measured centroid velocity; exact algebra fixture |
| p. 17, (93)-(95) | Deferred `InitialPotentialSolve` | Periodic analytic A, nullspace and residual; compare reconstructed field |
| pp. 16-17, Sections 5.2-5.3 | Deferred local stepping / remapping | Global vs local steps; affine A under insertion/removal; conservation |

## Discrepancies and implementation decisions

These are review findings, not author-confirmed errata. R1-R3 were checked against rendered PDF equations, so they are not solely extraction artifacts. Proposed corrected expressions are D, not silently substituted transcriptions. The U identifiers retain the original gaps in publication detail; their explicit E resolutions are in the engineering profile and have received the [separate AI review](M0_AI_REVIEW.md).

| ID | Evidence / finding | Consequence or required decision |
| --- | --- | --- |
| R1 | p. 18, (99)-(101): printed `Ay=0.1 cos(2pi x)/(2pi)+y/2`, `Az=0.1 sin(2pi x)/(2pi)-z/2` curls to `(0,-0.1 cos(2pi x),-0.1 sin(2pi x))`, not (96)-(98). The stated linear terms also give zero Bx. | For a fixture matching the stated B, derive periodic `Ay=0.1 sin(2pi x)/(2pi)`, `Az=0.1 cos(2pi x)/(2pi)` and set `mean_B=(1,0,0)`. Flag this as a corrected benchmark definition pending review. |
| R2 | p. 7, (43): the bracket adds `partial_t phi` to `beta c_s/r_cell` without phi; the text says “curl” although the scalar derivation needs divergence. In (44), the printed inertial coefficient is `r_cell/(beta c_s²)`. | Dimensional rederivation suggests a missing phi in (43) and coefficient `r_cell/(beta c_s)` in (44). Integrate the primary (41)-(42), not these explanatory formulas. |
| R3 | p. 12: prose after (69) calls the target surface sum `S_j`; (59)'s q is four-dimensional while (72) needs a gradient. Stage (80)/(86) brackets are incomplete in print. | Use target `Sigma_i`, derivative entries only, and explicit separated terms above. These are notation repairs, not new physics. |
| R4 | p. 19, Fig. 6 caption says 512 cells in [0,1] at t=0.1; p. 20 prose says dx=0.01 / 100 cells. | The plotted resolution cannot be inferred uniquely from the prose; retain both statements and use the caption only as a declared benchmark target. |
| U1 | Common face-normal B, HLLD wave-state selection/degeneracies, positivity/fallbacks, precise moving-face velocity and expanded discrete primitive B predictor are delegated or absent. | The [planar contract](COUPLED_2D.md) records common-Bn, flux/fallback and rigid-motion choices with analytic fixtures. The engineering profile specifies general face motion and the solenoidal endpoint primitive B predictor; their implementation remains M1 work. |
| U2 | Face-centre derivative g weights, default limiter formula/bounds and precise endpoint A-face reconstruction/gradient refresh are not exhaustive. | Planar face-area weights and neighbour-extrema limiting are explicit E choices. Endpoint refresh is specified in the engineering profile; implementation must pass its manufactured transport/temporal checks. |
| U3 | Auxiliary-grid root resolution, exact difference stencil, empty-bin policy, selection of averaging members, within-step refresh timing and 2D adaptation are incomplete. | The engineering profile specifies root layout, derivative jets, membership, coarsening, inheritance and a translating temporal frame, with required implementation fixtures. |
| U4 | CFL coefficient, precise radius conventions in 2D/3D, entropy thresholds, initial phi, and failure tolerances are not fully prescribed. | The engineering profile fixes these as E choices, including sound speed, old/new radius use, endpoint bounds and retry policy. |
| U5 | The end cleaning source is explicitly frozen by (90), unlike a fully reevaluated Heun source. Other predicted-field dependencies are partly implicit. | The [isolated gauge-mode audit](M0_OPERATOR_CHECKS.md) measures finest order 1.00519 for the printed prescription versus 2.00131 for a separately labelled reevaluated comparator. The AI review accepts retaining this reference prescription and reporting its limitation; any alternative needs a separately reviewed profile. This does not determine full-solver physical error order. |
| U6 | No general nonperiodic A/phi boundary operator, cleaning-scalar refinement transfer or full initial-Poisson nullspace/tolerance policy is supplied. | Defer those features and define a later review gate. |
| U7 | Data availability on p. 36 offers data on request; author datasets have not been acquired. | The [benchmark packet](M0_BENCHMARK_PACKET.md) now includes pinned independent Athena shock/vortex outputs, refinement uncertainty, analytic references and prospective candidate gates. These are not author-supplied data. |
| U8 | A separate, user-requested AI scientific review is complete. | The [report](M0_AI_REVIEW.md) identifies the reviewed commit, independent checks and scoped acceptance. Human peer review and author confirmation have not occurred. |

R2 rederivation with constant coefficients: let `kappa=beta_clean c_s/r_cell`. Equations (41)-(42), neglecting the other sources as in P's discussion, give `phi_tt+kappa phi_t=alpha c_s² laplacian(phi-psi)`. Multiplication by `1/kappa` produces the coefficient `r_cell/(beta_clean c_s)`. If coefficients vary in time, differentiating (41) gives `(phi_t+kappa phi) partial_t ln(c_s²)-phi partial_t kappa` as the additional terms. This is an algebra audit, not a full justification of P's approximations for the other sources.

## Proposed Rust boundaries and first compilable milestone

**E; design only.** Keep physics kernels independent of tessellation construction, I/O and MPI:

```rust
// Interface sketch, not compiled Rust and not a solver implementation.
type Vec3 = [f64; 3];
type Jacobian = [[f64; 3]; 3]; // [component][coordinate]
struct Conserved { mass: f64, momentum: Vec3, total_energy: f64 }
struct Potential { a: Vec3, phi: f64 }
struct MeanField(Vec3);
struct FaceSolution { mass_flux: f64, momentum_flux: Vec3,
                      energy_flux: f64, velocity_lab: Vec3, b_lab: Vec3 }
struct LocalDerivatives { raw_a: Jacobian, limited_a: Jacobian,
                          raw_b: Jacobian, limited_b: Jacobian }
trait SmoothVelocity {
    fn sample(&self, position: Vec3) -> (Vec3, Jacobian);
}
// Mesh view: stable cell IDs, generator and centroid coordinates, periodic
// images, volumes, oriented faces and stencil coefficients. No physics ownership.
// Flux kernel: primitive states + face geometry -> FaceSolution.
// Potential kernel: stage views + face solutions + u/H -> A/phi rates.
// Integrator: immutable initial state, endpoint geometry, predictions and buffers.
```

Keep `qfull` (fit intercept plus derivatives) distinct from the derivative-only vector in types. Keep generator, centroid and face velocities distinct in names and call signatures. Optional entropy, diffusion and Hessians must be explicit configuration/state extensions. Parallel layout and HDF5 dependencies are unnecessary for these serial mathematical contracts.

The workspace now contains the [Cartesian kinematic pilot](KINEMATIC_2D.md), [experimental coupled planar reference](COUPLED_2D.md), ideal-gas conversions, HLLD/HLL fluxes and periodic 2D Voronoi/LS operators. The new `mhd_vector_pot::gauge` kernels isolate general pointwise sources and the printed cleaning stages. They are not connected to either driver. The interface sketch remains incomplete: smooth auxiliary interpolation, deforming geometry and the full paper endpoint predictor are not implemented. The [independent AI review](M0_AI_REVIEW.md) accepts the M0 specification; the [acceptance record](M0_REVIEW.md) distinguishes it from later solver implementation.

## Checks and acceptance status

Run `python3 scripts/check_m0_spec.py` for small dependency-free algebra checks: covector/mean-field identity, affine least-squares moments, upwind direction, centroid correction, cleaning signs/dimensions, the R1 initialization discrepancy and the consistent Orszag-Tang normalization. These are mathematical fixtures, not time-evolved MHD tests, a proof of stability, or an independent scientific review.

The first 2D benchmark definitions, diagnostic operators and proposed gates are in [VALIDATION.md](VALIDATION.md). All implementation deviations must also enter the run configuration/provenance, including the corrected Alfvén initial condition. The workspace's format, lint and Rust tests apply to the implemented subset. Run `python3 scripts/run_m0_operators.py` for the isolated cleaning temporal-order table/provenance. None of these self-checks constitutes independent scientific review or full-method validation.

- [x] Read complete v1 source and record provenance.
- [x] Trace the main equations, published stencils and endpoint sequence.
- [x] Record ambiguities, apparent inconsistencies and proposed dimensional reduction.
- [x] Define operator fixtures and initial benchmark/diagnostic proposals.
- [x] Resolve E/U choices for the initial general profile, with explicit later-feature deferrals.
- [x] Obtain a separate, explicitly labelled AI scientific review of signs, discretizations and engineering choices.
- [x] Finalize the initial reference/configuration packet and prospective tolerances in issue #2.

Implementing and validating the full numerical method remains later-milestone work; it is not an additional requirement for closing the M0 specification itself.
