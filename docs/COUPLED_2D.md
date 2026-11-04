# Experimental coupled planar MHD reference

This is an independently implemented serial 2D reference, not a reproduction of the full 2026 algorithm. It adds conservative gas dynamics, periodic Voronoi geometry and magnetic force feedback to the earlier prescribed-flow pilot. Scientific M0 review remains open. No external implementation source code or geometry dependency was imported.

The [illustrated results and Mac run guide](COUPLED_2D_RESULTS.md) includes the committed shock/vortex figures and commands to reproduce them.

## Numerical contract and explicit choices

- Rust 2024, f64, nondimensional length/density/time; Lorentz-Heaviside magnetic units, mu0=1. Ideal gas E=p/(gamma-1)+rho v²/2+B²/2. Conservative cell integrals contain mass, three momentum components and total energy. Strictly planar v_z=B_z=0, A=(0,0,Az); B=mean_B+(D_y Az,-D_x Az,0).
- `mhd-core` uses HLLD's four intermediate states and jump-condition fluxes. Primary equation reference: [Miyoshi, Minoshima & Matsumoto's CANS+ numerical-method documentation](https://www.astro.phys.s.chiba-u.ac.jp/cans/doc/riemann.html), equations (45)-(74), describing Miyoshi & Kusano (2005), [doi:10.1016/j.jcp.2005.02.017](https://doi.org/10.1016/j.jcp.2005.02.017). Equations were independently translated, without importing the source-code examples. Bounds are min(vn_L,vn_R)-max(cf_L,cf_R) and max(vn_L,vn_R)+max(cf_L,cf_R). Zero normal field requires no division by Bn. Near-singular star denominators (relative 1e-12), nonpositive star thermal pressure, invalid wave ordering or nonfinite states trigger two-wave HLL; fallback state must also be admissible. These are engineering policies, not a general positivity proof.
- Both face primitives receive the arithmetic mean of their normal magnetic fields, preserving their reconstructed gas pressure. Face energy is recomputed from those primitives; conserved cell energies are never reset. Momentum/energy fluxes are transformed from the moving-face frame as derived in [the M0 specification](PAPER_IMPLEMENTATION_SPEC.md#fluid-coupling-and-energy). The numerical induction flux supplies a consistent EMF; for HLLD it equals the intermediate-state v cross B. In an HLL fallback, its average-state product generally differs; using the flux EMF is an explicit engineering choice.
- `moving-mesh` clips each generator's self-image rectangle against all other generators in a 3x3 periodic tiling. Reciprocal faces are checked and stored once with opposite cell signs. Orientation, positive area/volume, face closure, divergence-theorem volume and total box coverage are checked. Duplicate periodic generators, nearly zero-volume cells, unmatched faces and self-image faces are errors. This O(N²) f64 reference supports small well populated meshes, not arbitrary degenerate topology or scalable 3D geometry. Edges shorter than 1e-12 of the largest box side are treated as zero-length cocircular edges.
- Curl uses face-area-weighted neighbour-centroid least squares with a free intercept, excluding the target observation, matching [Springel, Mayer & Pakmor v1](https://arxiv.org/abs/2609.35989v1), pp. 8-9, equations (51)-(61). A scaled centred 2x2 covariance solve eliminates the free intercept analytically. Reject det(C)<=1e-10 trace(C)²; report trace²/det as a condition indicator. No silent zero-gradient fallback.
- Primitive and A extrapolation use separate copies of these gradients, with a cell-anchored componentwise neighbour-extrema limiter (our choice). Unlimited A derivatives reconstruct cell B. `--first-order` disables fluid extrapolation only; it does not change the curl or A limiter.
- The planar special choice u_i=v_i is allowed by the paper's reduction (p. 4, equation 25; p. 22 section 6.4). Its distortion and div(A) vanish identically in this embedding, so phi=0 stays zero. A's rate is the face-area average of (v_face-u_i) cross B_face (equation 69), plus donor-upwind (w-u_i) dot grad(A) using a separate free-intercept face-centroid stencil (equation 71), plus u_i cross mean_B (equation 76). Face-centroid weights use face areas: an explicit resolution of the unspecified weighting in M0. This does not implement the general smooth auxiliary field, gauge cleaning or three-component A.
- Geometry may be fixed or translate rigidly at a user-specified constant w. Metrics and neighbour images stay in a translating reference frame; physical positions are wrapped only for output. Both fluid face frames and A advection use w. There is no deformation, topology change or mesh regularization. Geometry rebuilds can be tested separately, but the solver does not claim general moving-mesh integration.
- Time integration is synchronized method-of-lines Heun. Every stage re-closes pressure using that stage's reconstructed B, without independently evolving a conserved B. This is deliberately a reference integration choice and **differs from the paper's endpoint primitive PDE predictor**. dt<=CFL min(V/sum(area*max_wave_speed),1/sum(abs((w-u) dot g_face))), CFL default .3, allowed <=.4. An invalid trial stage or endpoint CFL violation halves dt, up to 16 attempts. Rejected attempts are counted separately by cause; fallback counts refer to face evaluations in accepted stages. No pressure floors, energy repairs, resistivity, Powell sources, entropy switch, local stepping or adaptation.
- Divergence diagnostics: (1) successive unlimited neighbour LS derivatives D_x B_x+D_y B_y (`div_ls_rms`); (2) oriented sum of arithmetic-average cell normal B divided by cell volume (`div_face_rms`); (3) a separately measured face sum after limited extrapolation of each cell's B to the face (`div_limited_rms`). The third was added after the first measurements, because the first two coincide algebraically on a regular Cartesian lattice; it exposes errors that their cancellation cannot. No gate was changed to hide a result. These operators do not generally cancel on irregular Voronoi cells. Also report volume-weighted mean B and its drift from the initial discrete field: an unstructured cell-centred curl does not guarantee preservation of that mean.

## Initial configurations

`orszag-tang`: periodic [0,1]²; gamma=5/3, rho=25/(36pi), p=5/(12pi), v=(-sin(2pi y),sin(2pi x),0), Az=[cos(2pi y)/(2pi)+cos(4pi x)/(4pi)]/sqrt(4pi), mean_B=0. This agrees with the paper's normalization (pp. 22-23).

`brio-wu`: periodic [0,2]x[0,1/8], gamma=2; x<1 has rho=1,p=1, x>=1 has rho=1/8,p=.1; v=0, mean_B=(.75,0). Az=-x for x<1 and x-2 otherwise, giving By=+1/-1 away from jumps. Analyse only x in [.5,1.5] through t=.1: the second periodic interface at x=0 must not be confused with an outflow boundary. Initialize energy from the **discrete** curl, so the prescribed initial gas pressure is exact while By is smoothed across the initial discontinuity. This is a periodic adaptation, not the paper's boundary treatment.

`smooth`: periodic unit square; rho=1+.1 sin(2pi x), p=1, v=(.4,-.2,0), mean_B=(.3,.2), Az=0. Exact finite-amplitude entropy/contact wave: rho(x,t)=1+.1 sin(2pi[x-(.4+boost_x)t]); pressure, velocity and B stay constant. It checks coupled closure and fluid transport, **not** convergence of magnetic waves.

`uniform`: same as smooth with rho=1. Optional deterministic generator jitter in [0,.25] cell widths produces genuine unstructured cells. It is initialized at geometric centroids. No random seed is used.

`magnetic-pressure`: an additional analytic force fixture on the unit square, gamma=5/3, rho=p=1, initial v=0, mean_B=0, Az=.02 cos(2pi x). With a=.02, k=2pi, the initial acceleration is dv_x/dt=-a² k³ sin(kx) cos(kx). A unit test at t=1e-4, nx=16,32,64 and ny=4 checks decreasing force error and finest absolute L1 error <.005. This catches a solver that transports A without applying magnetic force to the gas.

## Predeclared first acceptance gates

Declared before running the new implementation:

1. EOS round trips and rejected invalid states; identical-state ALE flux equals the analytic physical flux minus w_n U; normal reversal swaps signs; uniform joint velocity/mesh boosts obey the mass/momentum/energy transform; stationary contact and isolated rotational discontinuity fluxes agree with analytic Rankine-Hugoniot states (relative/absolute tolerance 1e-11). Degenerate HLLD paths must be finite or return a useful error.
2. Regular, jittered and periodic-crossing Voronoi meshes tile their boxes and satisfy closure/volume/reciprocity at 1e-9 geometric tolerance. Affine derivatives away from a periodic discontinuity agree within 1e-10. Smooth curl errors on regular N=8,16,32 decrease at order >=1.8; jittered derivatives must converge but no second-order claim is assumed. Coincident points must be rejected.
3. Uniform coupled states on regular/jittered meshes remain constant through t=.1 to 1e-10. Periodic budget residual <=1e-10, positive density/pressure and finite divergence diagnostics in every run.
4. Smooth entropy wave N=8,16,32 through t=.2, second-order-space mode: error must decrease at every doubling. Report observed orders; second order is a target, not a condition to conceal limiter errors.
5. Brio-Wu nx=32,64,128, ny=4, t=.1: central density and By profiles approach a separate nx=2048 **conservative-induction 1D** first-order HLLD calculation, using the same Riemann kernel but not Az/curl. Report normalized central L1 and resolution trends. Gate: finest normalized errors <.15 for density and By, and finest lower than coarsest. This is a consistency comparison, not independent Riemann-kernel validation or comparison with a published high-resolution curve.
6. Orszag-Tang N=12,24,48 through t=.1: report stability, budgets, magnetic energy, both divergences and mean B. A run finishing is only a smoke check until published/converged profile agreement and longer-time convergence are quantified. Joint boost (2,-1), mesh w=(2,-1), N=12 must match the unboosted fixed run's physical density/pressure/B in translating coordinates to 1e-9. Include a jittered N=12 smoke run.

Passing these gates is not a full M1 release gate: Alfvén convergence, magnetic smooth-wave convergence, longer vortex validation and the paper-specific integrator remain outstanding.

## Measured results, 2026-11-04

Local Apple arm64, Rust 1.85.1, release profile, one process/thread; zero external Rust dependencies. The archived [summary](../tests/reference/coupled_2d/summary.csv) and [provenance](../tests/reference/coupled_2d/provenance.json) contain complete diagnostics, commands, source hashes and toolchain/platform details. The revision records the HEAD at execution; the source hash map identifies the working-tree implementation, including uncommitted files at capture time. These historical source hashes precede later documentation edits. The implementation subsequently passed [hosted CI at da58490](https://github.com/arm2arm/openmhd-rs-/actions/runs/41792760235).

All six scripted gates passed. The 1D shock comparison shares the EOS/Riemann kernel and is **not independent validation of that kernel**. Its induction discretization and magnetic representation are separate. Analytic face-flux, contact and rotational-wave fixtures check the Riemann kernel independently.

| Case | Resolution | Error/check |
| --- | --- | --- |
| Smooth entropy wave, t=.2 | 8² / 16² / 32² | density L1 .00335999 / .000945703 / .000296921 |
| Smooth observed order | 8→16 / 16→32 | 1.829 / 1.671: decreasing, **not demonstrated second order** |
| Brio–Wu, t=.1 | nx32 / 64 / 128, ny4 | normalized density L1 .0411870 / .0244249 / .0142686 |
| Brio–Wu, t=.1 | same | normalized By L1 .0399491 / .0400119 / .0253005; small intermediate increase |
| Vortex, t=.1 | 12² / 24² / 48² | magnetic energy .0300642 / .0374080 / .0397905 |
| Vortex limited-face div(B) RMS | same | .151207 / .111336 / .0904635; independently nonzero |
| Joint vortex fluid/mesh boost | N12, (2,-1) | max density/pressure/B discrepancy 1.03e-15 |
| All scripted periodic gas budgets | all runs | max normalized residual 1.95e-14 |

All accepted states retain positive density and pressure. Brio–Wu uses 248 / 168 / 136 fallback face evaluations at nx32 / 64 / 128, respectively. The stricter rotational-wave ordering guard was added during verification; the table and archive use that final policy. Rejected attempts are tabulated by cause in the CSV; the simple halve-and-retry policy costs extra evaluations and is not an optimized timestep controller.

The jittered N12 vortex is a smoke test only: neighbour-LS div(B) RMS is .148625, arithmetic-face RMS .243876, limited-face RMS .245719, and volume-weighted mean-B drift is 1.79e-4 by t=.1. These are material unresolved unstructured-field errors. On the regular meshes, the first two operators cancel at roundoff while the limited-face operator does not. Stable execution and gas conservation do not establish a validated divergence-free unstructured method.

Reproduce and plot:

```sh
cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test --workspace --locked
python3 scripts/check_m0_spec.py
python3 scripts/run_coupled_2d.py
# Optional, requires matplotlib; the simulation/study has no Python dependencies:
python3 scripts/plot_coupled_2d.py
```

The plot script produces `results/coupled_2d/brio_comparison.png` and `vortex_density.png`. The former shows remaining shock broadening/overshoots; the latter is an early-time resolution inspection, not a published-data overlay. Validation must next quantify magnetic-wave convergence and unstructured divergence/mean-field behavior before extending to deforming meshes or the general gauge.
