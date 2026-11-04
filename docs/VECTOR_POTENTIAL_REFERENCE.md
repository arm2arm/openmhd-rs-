# Issue #6: general-component serial vector potential

This packet preregisters the implementation and operator/coupling checks for three-component A/v/B with z-invariant periodic 2D Voronoi geometry (2.5D). It implements the reviewed paper terms and endpoint sequence, with the explicit engineering choices below. It does not establish the full M1 physical benchmark matrix, 3D adaptive smoothing, local timesteps, entropy closure, resistivity, remapping, gravity or general nonperiodic boundaries.

## Prospective engineering amendment: paper-global-v2

Retain [paper-global-v1](M0_ENGINEERING_DECISIONS.md) and its historical [benchmark packet](M0_BENCHMARK_PACKET.md). Before implementation/evaluation, a separate AI design review identified that v1's fixed auxiliary-grid origin does not commute with translations when sampling boxes are rebuilt at later synchronization times. Its within-step moving sampling coordinates alone cannot repair changed bin membership on the next step.

`paper-global-v2` changes that origin rule explicitly. Initially origin=0. At synchronization n, bin cell centroids relative to origin_n and build the same 4/2/1-interval periodic bicubic field. During a trial at relative time tau, sample at `wrap(c_stage-origin_n-vbar_n*tau)`. After acceptance only, set `origin_next=wrap(origin_n+dt*vbar_n)`. Freeze origin, selected root, corner values/jets and volume-mean velocity during all retries. A boost b shifts both centroids and the persistent origin by b*t, preserving sampling membership. No fluid-frame force is introduced; only the auxiliary representation moves. This is an engineering amendment, not a new paper equation.

Membership uses half-open corner-centred boxes. To make floating-point seam ties consistent, a normalized bin coordinate within `32*epsilon*(1+abs(coordinate))` of an integer is snapped to that integer before floor/modulo. This is a declared finite-precision tie rule, not exact-predicate geometry. Test exact boundary cases and translated copies.

All other v1 terms, limiting, old-data primitive predictor, frozen cleaning C1, default coefficients, timestep limits and retry policy remain. The prospective `benchmarks/m1/packet-v2.json` preserves all previous physical benchmark thresholds and configurations, changing only the named profile/origin convention; those candidate gates are still future measurements.

## Implementation contract and source map

Use f64, mu0=1, ideal gas, conservative cell Q=(mass,momentum3,total energy), pointwise periodic A3/phi at cell centroids, and separately fixed mean B3. Initial energy uses the initial discrete curl at the prescribed pressure. Later closure never repairs energy or floors pressure.

| Term/stage | Source and discrete contract |
| --- | --- |
| Curl and div(A) | Paper pp.8-9 (51)-(61); raw neighbour-centroid free-intercept, face-length-weighted LS. B=mean_B+(Dy Az,-Dx Az,Dx Ay-Dy Ax). |
| Smooth u/H | pp.10-12 (68), Fig.4; periodic tensor Hermite bicubic reduction, shared value/dx/dy/dxy corner jets, analytic first derivatives. Full volume weights and 4→2→1 global root fallback from v1, persistent origin from v2. |
| Induction | p.12 (69); sum face_length/perimeter * (numerical_EMF_face-u_i cross B_face). Use HLL's numerical EMF when it differs from the state product. |
| Distortion | p.12 (70); -H^T A with all three components retained. |
| Advection | p.12 (71); separate face-centroid LS coefficients g, b=w_adv-u; donor is target if b dot(face-c)<0, otherwise neighbour. Limit separate A-gradient copies. Subtract target A as a constant baseline. |
| Cleaning | p.12 (72), pp.6-7 (41)-(42); +raw grad(phi) in A, alpha*cs²*div(A)-beta*cs*phi/r in phi. Default alpha=1,beta=.15, r=sqrt(V/pi), EOS sound speed. |
| Mean field | p.13 (76); +u cross mean_B in both A stages. |
| Fluid predictor/face motion | pp.15-16 (83)-(85) plus v1 U1: old limited primitive gradients and solenoidal material derivatives; moving Voronoi bisector speed, shared equal/opposite Q updates. |
| Endpoint stages | pp.15-16 (80)-(92): preserve old state; A_star/phi_star for endpoint A/phi fits; old primitive PDE predictor for endpoint Riemann states; centroid-corrected what=2*(c1_unwrapped-c0)/dt-wtilde; C1 freezes div(A0)/cs0 and uses phi_star/r1. |

All geometry/time displacements retain periodic winding; no minimum-image subtraction between times. Fixed/rigid geometry may reuse equivalent geometry/stencil data; deforming endpoints must rebuild and validate. Configured prescribed in-plane generator velocities and fluid-following motion are distinct from physical v_z. Invalid initial states fail; invalid trial geometry/stencils/states or endpoint CFL bounds retry from immutable old data, at most 16 trials. Record causes, HLL fallbacks and auxiliary coarsening.

## Predeclared issue #6 gates

1. Hermite polynomials with supplied analytic value/dx/dy/dxy jets reproduce tensor cubics and physical first derivatives within 1e-11 relative-plus-absolute tolerance. Periodic value/derivative seam differences <=1e-10. Test constants, all velocity components, weighted membership, half-open ties, root 4/2/1 selection, translated-origin/boost covariance and centred-difference-jet convergence separately.
2. Raw curl of three-component smooth periodic A at N8/16/32: volume-weighted vector L1/L2, regular order >1.8, jitter .15 order >.7 at each doubling. Fixed test field: A=.001*(sin(2pi*y),cos(2pi*x),sin(2pi*x)*sin(2pi*y)); report analytic versus initial discrete B separately. These thresholds reuse the existing LS gates; no irregular second-order claim.
3. Check primitive material derivatives, boost covariance with nonzero estimated div(B), moving-face bisector identity, both A-advection donor signs, all source signs/components, separate endpoint A/phi refresh, frozen C1, periodic centroid winding and opposite conservative exchanges. Ordinary algebra tolerances 1e-11.
4. Uniform rho=p=1, v=(.4,-.2,.3), A=(.1,-.05,.03), phi=0, mean_B=(.3,.2,.1), gamma=5/3; fixed and rigid mesh (.7,-.8), regular/jittered N6, through t=.05: physical states preserved and A drift=v cross mean_B to 1e-10. No requirement of raw A invariance under boosts.
5. Longitudinal gauge mode on regular N16, rho=1,p=1/gamma so cs=1, v=mean_B=0, Ax=.001*cos(2pi*x), Ay=Az=phi=0. At t=.05 compare dt caps .001/.0005/.00025 with the exact same-grid central-derivative damped mode (k_eff=sin(2pi/N)/dx); finest temporal order of A/phi in [.8,1.2], consistent with the retained frozen C1. Physical B maximum <=1e-10. For a separate jitter .15 N16 run report initial curl and cleaning-induced B changes, require finite positive gas and max(|A|,|phi|/cs)<=.002; do not pretend discrete curl(grad phi) vanishes.
6. Multi-step boost on regular/jittered N8, t=.02, mean_B=0, rho=p=1: v=(.2+.05*sin(2pi*y),-.1+.03*cos(2pi*x),.04*sin(2pi*(x+y))), A as in gate2, phi=0. Compare fixed baseline with fluid boost (2,-1,0) and matching rigid generator boost. Require rho/p/B and transformed velocities/energy to agree within 1e-9, plus identical selected auxiliary roots and origin shift modulo the box. This tests repeated auxiliary rebuilds; the mean-field boost is tested separately by gate4.
7. Prescribed nonuniform generator motion on N6, t=.04, uniform physical state rho=1,p=.01,v=0,mean_B=(.3,.2,.1),A=phi=0. Use w=(.1*sin(2pi*y),.1*cos(2pi*x)), dt caps .004/.002/.001 and report physical-state/geometric-conservation errors and every refinement order; require finest error below coarsest and all accepted states finite/positive. Do not impose machine-zero GCL on a deforming mesh. Separately test a topology-changing endpoint and rejected-trial immutability, including the auxiliary origin.
8. All evolved cases: positive finite rho/p, periodic normalized conservative budgets <=1e-10, no pressure floors/energy resets. Record three explicitly distinct B divergence operators, dimensionless diagnostics, mean-B drift, div(A)/phi, extrema, timestep/rejection/auxiliary counters and provenance. Run all required workspace checks and obtain a separate labelled AI implementation review before closure.

## Diagnostic definitions

Use raw neighbour LS `Dx Bx+Dy By`; independent oriented face sum of arithmetic cell B; and a separately limited-face B sum. None is generally zero for an irregular discrete curl. Record volume-weighted signed mean, RMS/max and r*div(B)/(|B|+1e-12*Bscale), with Bscale fixed per initial configuration. Record mean B relative to its initial discrete volume mean. Phi cleans div(A), not div(B); report magnetic contamination from cleaning separately from gauge-mode accuracy. Conserved-budget denominators are fixed from the initial absolute integrals and initial density/velocity/energy scales, following the M0 packet.

## Evidence

Implementation, test commands, measured tables, source/compiler provenance and the separate AI review will be added after evaluating these unchanged gates. Passing this issue is an operator/coupling acceptance boundary, not completion of the larger M1 benchmark matrix.

## Running and inspecting the implementation

On the Mac, load Cargo with `source "$HOME/.cargo/env"` if it is not on PATH, then run:

```sh
cargo run --release --locked -p openmhd --bin vector-potential -- --case smooth --n 8 --jitter 0.15 --time 0.02 --output results/smooth
cargo run --release --locked -p openmhd --bin vector-potential -- --case gauge --n 16 --dt 0.0005 --time 0.05 --output results/gauge
cargo run --release --locked -p openmhd --bin vector-potential -- --case deform --n 6 --motion prescribed --dt 0.002 --time 0.04 --output results/deform
python3 scripts/run_vector_potential.py
```

The CLI accepts `--motion fixed|rigid|fluid|prescribed`, rigid `--mesh-x/--mesh-y`, three fluid `--boost-*` components, `--mean-bx/by/bz`, and `--unlimited` for the separately labelled reconstruction comparator. `--help` lists options. Prescribed motion is the specific sinusoidal generator field in gate7. The unit-square driver is a small deterministic fixture; the library accepts rectangular validated periodic meshes and user initial data. It is serial f64, gamma=5/3, mu0=1 with no external numerical dependencies. The clipping mesh builder is O(Ncells²), so it is not yet a practical large-mesh solver.

Each output directory contains `initial.csv`, `final.csv` and `summary.json`. CSV rows retain persistent cell IDs and give wrapped centroid, area, all physical/A components, phi, energy density and divergence diagnostics. JSON records fixed budget denominators, all dimensional/dimensionless divergence norms, extrema, mean-field drift, phi/div(A), accepted timestep ranges, rejection causes, HLL fallbacks and auxiliary root history/origin. The per-step geometric-conservation residual is `max_i |V1-V0-dt/2*(Vdot0+Vdot1)|/V0`, with `Vdot=sum_faces(area*w_face dot n_outward)` at both endpoint geometries; it is recorded over accepted steps. It is distinct from the accumulated physical-state error.

Implementation map: `auxiliary.rs` builds the moving bicubic field; `operators.rs` owns raw/limited fits, primitive prediction, moving bisectors and A rates; `general.rs` owns conservative exchange, immutable initial preparation, endpoint trials and acceptance; `diagnostics.rs` owns the three divergence operators. No cell insertion/removal, restart/checkpoint or conservative reference-bin projection is implemented here.

## Known limitation from additional AI-review probes

The preregistered mean-zero multi-step boosts and uniform nonzero-mean states pass their declared gates. An additional review probe of **nonuniform flow with nonzero mean B** shows transformed physical-field differences around 2e-5 at t=.01 on a rectangular jittered deforming mesh. This lies outside those original gates and must not be presented as successful general Galilean invariance. The study includes a reproducible unit-square fixed/rigid counterpart, added after review as an observation without a retroactive success threshold.

A possible mechanism is the noncommuting discrete curl/gradient response to spatially varying gauge terms following the mean-field boost drift. This is an inference, not an established diagnosis. Issue #7 must investigate it and quantify refinement/physical-field consequences before broader invariance or full-M1 claims. The registered v2 equations and acceptance thresholds have not been adjusted to hide this observation.

Counter semantics: `hll_fallbacks` counts successful HLL face results used by accepted stages; `hll_fallbacks_attempted` additionally includes successful HLL results from discarded endpoint trials and partially failed sweeps, including failed initial preparation. An internal Riemann attempt returning an error has no usable face method/result and is recorded as a state rejection instead. Initial/final diagnostics report the worst neighbour and face LS conditioning indicators (the shared dimensionless covariance metric), distinct from geometry/stencil rejection counters.
