# Scientific validation and reproducibility

Successful execution is not equivalent to a correct physical solution. All results must be compared to analytical, converged, or published reference calculations and archived with configurations and code revision.

## General-component operator/coupling packet (issue #6)

[paper-global-v2](VECTOR_POTENTIAL_REFERENCE.md) specifies the 2.5D implementation and its preregistered gates. Reproduce the 29-run packet with `python3 scripts/run_vector_potential.py`: 27 acceptance runs plus two observational nonuniform mean-field boost runs added after the AI review. The latter show a discrepancy and are recorded as a limitation, not a successful invariance test. Raw curl convergence, frozen-C1 gauge order and deforming-mesh volume/fluid error are measured separately. Three B-divergence operators, div(A), phi, positivity, normalized periodic budgets and counters accompany each run. This packet does not satisfy the full M1 matrix below.

## Physics benchmark matrix

| Benchmark | Main quantitative check | Earliest milestone |
|---|---|---|
| Hydro smooth wave and shock tubes | `L1/L2` convergence; Rankine–Hugoniot; budgets | M1 |
| Circularly polarized Alfvén wave | Expected second-order error trend with resolution | M1 |
| Brio–Wu MHD shock tube | B, density, velocity and energy profiles vs references | M1 |
| Magnetic flux-loop advection | Field topology, energy, boosted vs unboosted error | M1/M2 |
| 2D Orszag–Tang vortex | Density/magnetic slices, energy history, stability | M1 |
| 3D vortex/field advection | Structure, spectrum, stability and 3D boost | M2 |
| MHD blast wave | Shock symmetry, no negative pressure, conservation | M2 |
| Magnetorotational instability | Linear growth vs theory once physical setup is ready | M4 |
| Magnetized gravitational collapse | B amplification and flow/outflows after gravity exists | M4 |
| Local timesteps/refinement | Reference to synchronized, fixed-resolution runs | M4 |
| MPI and Rayon invariance | Match physical diagnostics vs 1-rank reference | M3 |

## Diagnostics required in every physics case

- Integrated mass, momentum and total-energy budgets, including boundary/source terms.
- Volume-weighted magnetic energy and extrema; minimum density and thermal pressure.
- Magnetic divergence with **two explicitly labeled discrete operators** (solver-associated and independent flux-based).
- Gauge residual/cleaning behavior of A and correlation with physical field metrics.
- Galilean boost comparison after appropriate coordinate transformation.
- Mesh quality, ill-conditioned least-squares stencils, near-degenerate cell counters.
- Provenance: git revision, configuration, random seed, compiler flags, ranks/threads, hardware.

## Acceptance protocol

1. Declare resolution ladder, fitted convergence range and pass thresholds before using them to judge new code.
2. Fit smooth-wave error order and report uncertainties; second-order behavior is a proposed target.
3. For boosted runs, compare in equivalent physical coordinates at matched times.
4. For periodic conserved quantities, quantify any residual non-conservation and its change with refinement.
5. MPI/Rayon comparisons should allow numerical summation-order differences; byte-identical results are not required.
6. Do not test MRI and collapse as release gates until necessary physics and boundary conditions exist.

Large snapshots may be external, but scripts, small reference fixtures, checksums and quantitative tables belong in the repository.

The [issue #5 geometry/reconstruction packet](MESH_VALIDATION.md) records analytic cell/face fixtures, checked connectivity and conditioning, limiter bounds and regular/jittered manufactured-gradient convergence. These fixtures evolve no fluid state and establish no multidimensional div(curl) identity.

The [issue #4 conservative state/flux packet](CORE_FLUX_VALIDATION.md) records independent Athena++ Brio–Wu comparisons for the 1D conservative-induction driver, measured refinement, budgets, positive accepted stages and a joint fluid/grid boost. These scoped kernel gates do not complete the M1 vector-potential benchmark matrix.

The first implemented subset is the [Cartesian kinematic 2D reference](KINEMATIC_2D.md). Its measured convergence and rigid-grid transport checks are separate from the coupled MHD benchmark matrix above. It evolves no mass, momentum or total fluid energy; those budgets are therefore not claimed for that pilot. The newer [coupled planar reference](COUPLED_2D.md) evolves conservative gas integrals and Az on periodic Voronoi cells. Its predeclared first gates, measured results and limitations are recorded there and in `tests/reference/coupled_2d/`; it does not satisfy the full M1 matrix.

## M0 source audit and first reference configurations

The [paper specification](PAPER_IMPLEMENTATION_SPEC.md) records the consulted source: Springel, Mayer & Pakmor, [arXiv:2609.35989v1 PDF](https://arxiv.org/pdf/2609.35989v1). Page numbers below refer to that PDF. **These are definitions and proposed acceptance gates, not measured results.** The source's apparent Alfvén initialization inconsistency R1 must be reviewed before claiming a paper-matched benchmark.

The dependency-free `python3 scripts/check_m0_spec.py` checks algebra underlying the specification, including the discrepancy calculations. It does not evolve an MHD solution, build Voronoi geometry, or validate a Rust implementation.

The [isolated Rust gauge/cleaning audit](M0_OPERATOR_CHECKS.md) implements the point-source, shear/rotation, mean-field and frozen-source cleaning fixtures below. Its manufactured longitudinal-mode study measures first-order convergence for Eq. (90) and second order for a separately labelled reevaluated-Heun comparator. These are measured operator results, distinct from the proposed coupled benchmark gates in this section.

### Operator fixtures before coupled benchmarks

| Fixture | Analytic reference | Required observation |
| --- | --- | --- |
| Affine potential on regular and irregular stencils | `A=a+G x`, `B=mean_B+curl(G)` | Free-intercept fit reproduces derivatives; constant fields give zero derivatives. Test neighbour-centre and face-centre operators separately. |
| Smooth periodic potential | In 2D, `Az=sin(2pi x) sin(2pi y)`, so `B=(2pi sin(2pi x) cos(2pi y),-2pi cos(2pi x) sin(2pi y),0)` | Spatial curl convergence; unlimited vs limited gradients; both divergence diagnostics. |
| Smooth velocity representation | Constant/affine corner data; cubic-polynomial data | Exact polynomial derivative inside an element; C1 continuity at shared faces and periodic seams; adaptive boundaries inherit parent data. |
| Constant-Jacobian deformation | `dot(A)=-H^T A` with other terms isolated | Transpose/sign and temporal order, including rotation and shear. |
| Upwind A transport | `partial_t A=b dot grad(A)`, solution `A(x,t)=A_init(x+b t)` | Correct donor direction for both signs; smooth-wave convergence and no new extrema for nonsmooth data. |
| Cleaning mode with fixed coefficients | `Ax=a(t) cos(kx)`, `phi=p(t) sin(kx)`: `a'=k p`, `p'=-alpha c_s² k a-kappa p` | Damped oscillation with `kappa=beta_clean c_s/r`; distinguish the frozen-source stage prescription from fully reevaluated Heun. |
| Mean field and mesh translation | Constant B, `A(t)=A_init+t v cross mean_B` for constant `v=u=w` | B stays constant even when A changes; verify positive Eq. (76) sign. |
| Centroid correction and periodic crossing | `what=2(c1-c0)/dt-wtilde` on unwrapped coordinates | Stage-averaged advection velocity equals measured centroid velocity, including displacement exceeding half a box. |
| Conservative face exchange | One oriented face contribution applied to two cells | Equal/opposite mass, momentum and total-energy increments; changing geometry does not alter this contract. |

Use fixed deterministic meshes/seeds. Proposed algebra tolerance for f64 affine reproduction is `64*epsilon_machine*max(1,condition_estimate)*reference_scale`; record coordinate scaling and reject rank-deficient stencils. The exact-rational Python fixture has no floating-point tolerance. This is an engineering proposal, not a tolerance quoted from the paper.

### Circularly polarized Alfvén wave: adapted 2D geometry

**Paper evidence:** p. 18, Eqs. (96)-(98) give `rho=1`, `p=0.1`, `gamma=5/3`, parallel `B=1`, and transverse velocity/B amplitude `0.1`. The published oblique mesh/rotation and convergence plot are 3D, Eq. (102) and Figure 5.

**Our proposed 2D adaptation:** periodic unit square, all three velocity/B/A components, with z derivatives zero and mesh generators restricted to the xy plane. A single-Az implementation cannot run this case. At t=0 set

```text
rho=1; p=0.1; gamma=5/3; k=2pi
v=(v_parallel, 0.1 sin(k x), 0.1 cos(k x))
mean_B=(1,0,0)
A_periodic=(0, 0.1 sin(k x)/k, 0.1 cos(k x)/k)
phi=0
```

The potential above is derived to reproduce the stated field; it **replaces the inconsistent printed Eqs. (99)-(101)** (specification R1). Compare to the analytic B/velocity wave with phase `k[x+(1-v_parallel)t]`, at `t=1`, for `v_parallel=0` (travelling) and `1` (standing). Start with fixed meshes; then repeat with moving in-plane mesh motion. The out-of-plane velocity is a physical component, not a generator displacement in a nonexistent third mesh dimension.

Proposed resolution ladder: `N=32,64,128,256` in each mesh direction, with a documented deterministic irregular-mesh sequence as a second family. Measure volume-weighted transverse-B L1/L2 errors. Proposed smooth-wave gate: fit the finest three L1 values against `h=1/N`, require observed order at least `1.8`, and verify spatial/time errors separately. This is a proposed project threshold; P supplies the second-order trend, not this numerical bound.

### Weak field-loop advection

**Paper evidence:** p. 20, Eq. (103), unit periodic box, `rho=p=1`, `v=(2,1,0)`, final `t=1`, and

```text
r = distance to (0.5,0.5), using periodic coordinates
Az = (0.001/sqrt(4pi)) max(0,0.3-r)
Ax=Ay=0; mean_B=0
```

P shows hexagonal Voronoi and Cartesian comparisons at nominal `512²`. **Engineering choices:** initially `gamma=5/3`, `phi=0`, no explicit resistivity, no entropy closure, ladders `N=32,64,128,256`; exact mesh construction and counts must be recorded rather than call a hexagonal lattice `N²` without counting it.

Run an isolated prescribed-velocity transport test first, then full MHD. For transport, compare A/B to the initial *discrete* fields on translated, persistent cell IDs, and separately compare to the analytic field away from the cusp/edge. Propose normalized transport drift below `1e-10` for a rigidly translating mesh without regularization, after accounting for roundoff and periodic images. Do not impose second-order convergence on this nonsmooth potential. In full MHD the magnetic field is weak but finite; compare boosted/unboosted solutions and magnetic-energy histories, rather than assume exactly zero physical Lorentz response.

### Brio-Wu shock tube

**Paper evidence:** pp. 19-20, Figure 6/Section 6.2: at rest, `gamma=2`, `(rho,p,Bx,By)_L=(1,1,0.75,1)`, right `(0.125,0.1,0.75,-1)`. Figure 6 gives `t=0.1`, 512 cells over the plotted [0,1] interval and an independent ATHENA++ 8192-cell reference; the prose instead gives 100 cells. Retain this source disagreement (specification R4).

**Proposed periodic embedding:** box `[-1.5,2.5] x [0,0.125]`, primary interface `x=0.5`, analysis interval `[0,1]`, left/right states extending to the box edges. This introduces a second interface at the periodic seam; verify its domain of dependence cannot reach the analysis interval by `t=0.1`. Initialize continuous periodic Az by

```text
Az=-(x+1.5)          for -1.5 <= x <= 0.5
Az=x-2.5            for  0.5 <  x <  2.5
mean_B=(0.75,0,0); phi=0
```

This domain, width and potential are our construction; the paper does not give its full extended box. Initial mesh density should yield 128/256/512 cells per unit x length, with enough rows to test 2D geometry. Compare density, p, velocities, By and energy profiles against an independently produced converged reference. Do not treat the compound-wave solution as a simple exact Riemann fixture. Acquiring/checksumming the reference, defining norms near discontinuities, and setting profile tolerances remain issue #2 work. Report Bx departures and verify jump conditions without adding Powell sources.

### Orszag-Tang vortex

**Paper evidence:** pp. 21-22, Section 6.4, periodic unit square, `gamma=5/3`, `rho=gamma²/(4pi)`, `p=gamma/(4pi)`, `v=(-sin(2pi y),sin(2pi x),0)`, and stated `B=(-sin(2pi y),sin(4pi x),0)/sqrt(4pi)`. Shown output times are `0.5`, `1.0`, `2.5` at `1024²` cells.

**Equivalent form of the paper's potential matching that B:**

```text
Az = [cos(2pi y)/(2pi) + cos(4pi x)/(4pi)]/sqrt(4pi)
Ax=Ay=0; mean_B=0; phi=0
```

This equals the printed `[2 cos(2pi y)+cos(4pi x)]/(4pi)^(3/2)` potential: differentiating its numerator gives a factor of `4pi` for both B components. The algebra fixture confirms the normalization. Propose resolutions `64²,128²,256²`, diagnostics at all three reported times, pressure/density positivity, budget histories, magnetic-energy/current maps and convergence of profiles/statistics against an independent finer reference. Numeric profile thresholds remain open in issue #2. P's pictured planar run sets `u=v`; run the full smooth-u path as a separately labelled configuration. Neither planar variant establishes stability of the general 3D gauge/cleaning system.

## Explicit divergence operators and budgets

For the first reference implementation propose these distinct diagnostics, with their definitions recorded in output:

1. **Cell derivative:** `div_cell(B)_i=trace(G_B_raw_i)`, using an unlimited, free-intercept, face-area-weighted neighbour-centre fit to the reconstructed cell B values. If Hessian-derived divergence is also reported, label it separately and do not substitute its algebraic cancellation for this diagnostic.
2. **Independent face sum:** `div_face(B)_i=(1/V_i) sum_f area_f n_if dot [(B_i+B_j)/2]`, with one shared arithmetic-mean face B and outward oriented normals. In 2D use edge lengths and cell areas. This deliberately uses neither the curl coefficients nor HLLD's normal-field convention. Verify periodic face pairing. Zero *global sum* from paired faces does not imply zero local divergence.

Report signed values and volume-weighted mean/max absolute values of each, as well as normalized `r_cell*abs(div(B))/(abs(B)+B_floor)`. Fix `B_floor` from a documented initial reference scale; never tune it after seeing failures. Also record `trace(G_A_raw)` and, for general-component tests, cleaning scalar histories and physical B changes correlated with cleaning.

Define `L1(q)=sum_i V_i abs(q_i-q_ref(c_i,t))/sum_i V_i` and L2 by the corresponding weighted square mean. Use vector magnitudes or componentwise norms consistently. Boost comparisons require the same physical coordinates after removing `v_boost*t`, matched times, and explicit velocity/energy frame transforms; A is gauge-dependent, especially with a mean field.

Proposed initial periodic budget gate, with gravity/entropy resets/resistivity disabled: relative mass, momentum and total-energy residuals below `1e-10` over the test interval. Use nonzero initial scales (e.g. sum of momentum magnitudes plus `M*c_ref`), not a zero net momentum denominator. Also check per-face opposite increments to roundoff, and track any allowed energy correction as a separate signed source. Final gates, including permissible Galilean differences in full MHD, are to be preregistered in issue #2 before judging solver output.

Every coupled-MHD reference config must record the source version, R1 correction choice, gamma/units, initial phi/mean_B, exact mesh/periodic images, limiter/stencil policies, auxiliary-grid parameters, CFL/cleaning bounds, entropy/dissipation switches, resolution, output times and reference-data checksums. The configurations in this M0 proposal are not successful coupled-MHD benchmark results. Results for the separate, prescribed-velocity pilot are recorded in [KINEMATIC_2D.md](KINEMATIC_2D.md).
