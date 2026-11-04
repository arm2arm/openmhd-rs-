# M0 gauge and cleaning operator audit

This audit adds isolated mathematical kernels and manufactured tests to support M0 review. It does not implement the general gauge inside the coupled planar solver, or establish completion of issue #1. The [M0 review checklist](M0_REVIEW.md) tracks the remaining decisions and independent review.

## Scope and source

The pointwise vector-potential source uses Springel, Mayer & Pakmor [arXiv:2609.35989v1](https://arxiv.org/abs/2609.35989v1), equations (38), (41)-(42), (75)-(76), pp. 6-7 and 13. The Jacobian convention is `G[a][b]=partial_b A_a`, `H[a][b]=partial_b u_a`:

```text
D_w A = (v-u) cross B - H^T A + G (w-u)
        - eta J + grad(phi) + u cross mean_B.
```

The kernel returns the separated terms and rejects invalid inputs. It receives exact/local derivatives; the neighbour/face stencils, limiting, Riemann EMF and mesh stage predictor are separate algorithms. Its optional `-eta J` is the continuum resistive term, not the paper's optional discrete `+eta laplacian(A)` approximation. Positive `eta` is a diffusivity in nondimensional units with mu0=1.

Cleaning uses `C=alpha cs² div(A)-beta cs phi/r` (41). The staged scalar update follows equations (81), (88), (90), (92), pp. 15-16, including **old** `div(A)` and `cs` in the second rate. The old and new cell radii are separate inputs. Defaults are `alpha=1`, `beta=.15`; positive sound speed/radius and positive coefficients are required. Bounds from printed equations (49)-(50) are returned separately, with `Dclean=alpha cs r/beta`; these are not a complete MHD timestep controller.

## Predeclared checks

Declared before executing the new Rust kernels:

1. At arbitrary analytic local jets, compare the full rate with the independently expanded Eulerian identity `v cross B-grad(u dot A)+G w-eta J+grad(phi)`. Require each component to agree within `1e-12` times a nonzero reference scale. Test an asymmetric H, a shear, a rotation and a nonzero mean field to expose the transpose and background signs.
2. Under a uniform joint boost of v/u/w, the point rate changes by `boost cross mean_B`, with the fluctuating terms unchanged. For uniform `v=u=w`, a constant background field must produce that gauge drift while B remains constant.
3. For local rotation with `dot(A)=-H^T A`, Heun time integration over t=1.3 with 20/40/80 steps must have amplitude error order >=1.8. Affine shear has an exact linear solution and must match to `1e-12`. These tests isolate the local source, not the full coupled mesh integrator.
4. Check the cleaning-wave signs, damping sign, radius dependence, frozen-source stage and scaling of the two printed timestep bounds. Reject nonfinite values, nonpositive radii/sound speeds/coefficient values and negative time intervals.
5. For the exact Fourier mode `Ax=a(t) cos(kx)`, `phi=p(t) sin(kx)`, use `a'=k p`, `p'=-alpha cs² k a-kappa p`, `kappa=beta cs/r`. Set `k=2pi`, `cs=1`, `r=.1`, `alpha=1`, `beta=.15`, `(a0,p0)=(.01,.02)` and t=.5. Compare 40/80/160/320 steps with the analytic damped-oscillator matrix exponential. Report errors and orders for the paper's frozen-source step and, separately, fully reevaluated Heun as a diagnostic comparator. The frozen-source formula omits an O(dt²) term in the p update, so **first-order coupled-mode convergence is the analytic expectation**, not a reason to silently replace equation (90). Require decreasing errors and finest observed order in [.8,1.2] for the frozen-source implementation; require >=1.8 for the reevaluated comparator. Neither result alone establishes the order of the complete paper algorithm.

The Fourier fixture has zero physical curl: the longitudinal vector potential and cleaning scalar describe a gauge mode. This study measures coefficient-amplitude error; it uses analytic spatial derivatives, so it has no spatial discretization error.

## Reproduction

```sh
cargo test -p mhd-vector-pot
cargo run --release -p mhd-vector-pot --example gauge-cleaning
python3 scripts/run_m0_operators.py
```

The example prints a CSV resolution table. The Python runner uses only the standard library, builds the pinned release example with `--locked`, checks the predeclared temporal gates and writes CSV plus source/toolchain/configuration provenance under `results/m0_operators/`. Spatial derivatives are analytic, the domain is the periodic unit interval, and all quantities use nondimensional mu0=1 units. There is no mesh, gas EOS or fluid update in this isolated fixture; cs=1 is supplied directly.

## Measured result, 2026-11-04

Eight new Rust operator tests pass; the full workspace has 37 passing Rust tests, and all nine Python algebra checks pass. Format and Clippy checks also pass. The release example on Apple arm64, Rust 1.85.1, one process/thread gives:

| Steps to t=.5 | Paper frozen-source relative amplitude error | Reevaluated-Heun comparator error |
| --- | --- | --- |
| 40 | .0435027 | .00249186 |
| 80 | .0214526 | .000621019 |
| 160 | .0106503 | .000154987 |
| 320 | .00530601 | .0000387116 |
| Finest doubling order | **1.00519** | **2.00131** |

Error is `hypot(a-a_exact,p-p_exact)/hypot(a0,p0)`. The [CSV](../tests/reference/m0_operators/cleaning.csv) and [provenance](../tests/reference/m0_operators/provenance.json) archive full precision and source hashes. All predeclared gates pass: this includes the **expected first-order** result, not a second-order acceptance claim for the frozen source.

For constant radius and cs, write `C0=-q a-kappa p`, `q=alpha cs² k`. Equation (90) gives `p_next=p+dt C0-dt² kappa C0/2`. The exact Taylor series additionally contains `-dt² q k p/2` because a changes during the step. Its omission gives a local O(dt²) error and explains the observed first-order coupled-mode convergence. The comparator includes that term by reevaluating the source at predicted a; it is deliberately labelled as a different update.

This result leaves U5 open for review. It tests an analytic longitudinal gauge mode with zero physical curl, not full-solver temporal order, irregular-stencil curl contamination, stability of all modes or the paper's reported physical benchmark convergence. The new kernels are isolated under `mhd_vector_pot::gauge`; neither driver uses them yet.
