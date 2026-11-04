# First runnable 2D reference: prescribed magnetic transport

This pilot is a **kinematic Cartesian reference**, preceding the coupled M1 solver. It exercises periodic transport of pointwise `Az`, curl reconstruction, convergence and magnetic diagnostics. The velocity is prescribed, and the grid translates rigidly at a prescribed velocity. There is no gas update, Lorentz-force feedback, EOS evolution, Riemann solver, Voronoi topology change, general gauge cleaning, MPI or Rayon. It does not establish faithfulness of the full paper method or reproduce its MHD benchmarks.

## Mathematical and numerical scope

For strictly planar, z-invariant flow with `A=(0,0,Az)`, zero mean B, constant fluid velocity v and translating grid velocity w, the equation reduces to

```text
partial_t Az + (v-w) dot grad(Az) = 0     [in grid coordinates]
B = (partial_y Az, -partial_x Az, 0)
```

This uses the simple planar limit of the [M0 specification](PAPER_IMPLEMENTATION_SPEC.md), including paper Eq. (25), p. 4. Here `u=v` is constant, its Jacobian and `div(A)` vanish, and `phi=0`. The implementation choices below are ours, not a transcription of the paper's irregular-mesh advection stencil.

- Serial Rust 2024, `f64`, no third-party Rust dependencies.
- Unit periodic square, uniform Cartesian cell centres `(i+1/2)/nx,(j+1/2)/ny`, unit depth; spacings `dx=1/nx`, `dy=1/ny`. Nondimensional length/time and magnetic amplitude units. No random seed is needed.
- Unsplit method of lines: reconstruct Az at each Cartesian face, use the upwind state for relative velocity `c=v-w`, and difference the face transport rates. On this uniform constant-velocity grid the resulting difference operator applies to point samples of Az. Conservation of its discrete integral is a transport property of this case, not a general conservation law for vector potential.
- Piecewise linear reconstruction with either unlimited centred slopes (smooth verification case) or monotonized-central (MC) slopes (nonsmooth field loop). MC uses `minmod(2 delta_minus, (delta_minus+delta_plus)/2, 2 delta_plus)`.
- Globally synchronized explicit Heun/SSP RK2: Euler predictor, recompute the spatial rate at the predictor, average the two rates. This scalar test does not implement the paper's frozen-source cleaning substep.
- `dt <= CFL/(abs(cx)/dx+abs(cy)/dy)`, default `CFL=0.4`, shortened to the requested final time. Restrict CFL to `(0,0.5]`. A comoving grid (`c=0`) requires no numerical transport steps; only the physical sample positions translate.
- Unlimited centred curl: `Bx=(Az[i,j+1]-Az[i,j-1])/(2dy)`, `By=-(Az[i+1,j]-Az[i-1,j])/(2dx)`. This equals the free-intercept direct-neighbour least-squares gradient on this regular mesh. It does not test irregular-cell conditioning.

## Cases, diagnostics and predeclared checks

The smooth manufactured case is `Az=sin(2pi x) sin(4pi y)`, so `B=(4pi sin(2pi x) cos(4pi y),-2pi cos(2pi x) sin(4pi y),0)`. It intentionally has unequal wavenumbers, helping expose differences between divergence operators. Its exact solution is the initial profile evaluated at `x-v*t` in physical coordinates. Use unlimited slopes, `v=(2,1)`, fixed grid, `t=1`, and `N=16,32,64,128` for the archived resolution study. Before measuring results, set the smooth Az and B L1 convergence gate to **order >=1.8 for each of the two finest resolution doublings**. Tests can use a shorter ladder/time for CI.

Separately isolate temporal accuracy at fixed `N=16`, `t=0.2` and CFL `0.4,0.2,0.1`. Compare the discrete Fourier coefficient of the `(kx,ky)=(2pi,4pi)` mode to the exact method-of-lines evolution `coefficient(t)=coefficient(0)*exp(lambda*t)`. For this unlimited reconstruction, an axis contributes `Re(lambda)=-abs(c)*(1-cos(theta))²/(2h)` and `Im(lambda)=-c*(1.5 sin(theta)-0.25 sin(2theta))/h`, with `theta=k*h`; add the two axes. Require order >=1.8 on both temporal doublings, independently of spatial truncation error.

The loop uses paper Eq. (103), p. 20: `Az=(0.001/sqrt(4pi))*max(0,0.3-r)` about `(0.5,0.5)`, periodic minimum-image radius, zero mean B, and `v=(2,1)`. Use MC slopes and `t=1`. The potential is nonsmooth at its apex and outer edge; no second-order gate applies there. Check no new Az extrema (tolerance `1e-12` times the initial amplitude), the periodic discrete Az integral (relative drift <=`1e-11`), and field/energy error trends with resolution. Full MHD would also evolve the gas; this test does not make the approximation that weak but finite Lorentz forces vanish in a coupled solver.

Report:

- Absolute Az L1 error and vector B L1 error against the analytic translated profile; for the loop use the piecewise analytic B away from its measure-zero cusp/interface. Report magnetic energy relative to the initial *discretely reconstructed* energy separately from analytic error.
- Az integral drift and extrema; mean B components; magnetic energy. No mass/momentum/total-energy conservation claim is available because those variables are not evolved.
- `div_central = Dx_central(Bx)+Dy_central(By)`. For this periodic Cartesian curl, the derivative matrices commute, so this particular composition cancels to roundoff. This property does not transfer automatically to Voronoi geometry.
- `div_face_mc`: reconstruct each normal B component from both cells to its shared face using MC slopes, average those two face states, then take the oriented face sum divided by cell area. This is an independent nonlinear, consistent flux diagnostic and need not vanish. The plain arithmetic-mean face diagnostic proposed for irregular M1 meshes would collapse to the central operator on this Cartesian grid; using reconstructed faces here makes the distinction explicit.
- RMS and maximum absolute divergence for both operators, with dimensional units B/length. Do not call a nonzero independent diagnostic a violation of an exact property of a different operator.

The comoving loop must retain Az and its reconstructed B exactly on persistent grid indices (apart from physical coordinate wrapping); target normalized Az drift <=`1e-10`. Compare runs where the same constant boost is added to v and w: their relative-velocity transport is the same. This verifies only the rigid-grid kinematic equation, not full moving-mesh Galilean invariance. Include positive, negative and zero relative velocities and periodic crossings in tests.

## Usage and next implementation gates

Rust toolchains are managed with the pinned `rust-toolchain.toml`; source `~/.cargo/env` if Cargo is not already on PATH. The Rust workspace has no external dependencies.

```sh
cargo run --release -p field-loop -- --case loop --n 64 --mesh fixed
cargo run --release -p field-loop -- --case loop --n 64 --mesh comoving
cargo run --release -p field-loop -- --case smooth --n 64
python3 scripts/run_kinematic_2d.py
```

The driver prints a CSV diagnostics header/row. Add `--output path.csv` to write final point samples, analytic references and both divergence fields; the parent directory must exist. The study writes `convergence.csv`, `provenance.json` and three 64² loop snapshots under `results/kinematic_2d/` by default. The provenance records configurations, source-file hashes, the base Git commit plus dirty-worktree status, compiler/host, serial execution and diagnostic-data checksum. Use `--output-dir` to choose another destination.

Optional plots require `matplotlib==3.9.4` in your Python environment:

```sh
python3 scripts/plot_kinematic_2d.py results/kinematic_2d
```

This creates `loop_comparison.png` and `smooth_convergence.png`. Plotting is separate from the dependency-free study and is not required by CI.

## Measured pilot results, 2026-11-03

On `aarch64-apple-darwin`, rustc 1.85.1, optimized serial execution, default parameters and t=1:

| N | Smooth Az L1 | Smooth B L1 | Az order | B order | Fixed-grid loop magnetic energy / initial |
| --- | --- | --- | --- | --- | --- |
| 16 | 2.646385e-1 | 4.373731 | - | - | 0.466409 |
| 32 | 8.326119e-2 | 1.331078 | 1.6683 | 1.7163 | 0.841940 |
| 64 | 2.103468e-2 | 3.280794e-1 | 1.9849 | 2.0205 | 0.938522 |
| 128 | 5.240799e-3 | 8.058269e-2 | 2.0049 | 2.0255 | 0.969234 |

The two finest smooth doublings pass the preregistered >=1.8 gates. The coarsest doubling is outside that range. The CI test also separately passes the Fourier-reference temporal-order gate. The nonsmooth fixed-grid loop has slower B L1 convergence (measured orders 0.65-0.96), as expected for this limited transport test with a cusp and field discontinuity; it is not second-order evidence. Az stays within its initial bounds, and the largest measured normalized Az-integral drift over the loop ladder is 2.13e-16.

At N=64 the comoving loop has zero Az transport error and exactly unchanged discrete B/energy, with **zero numerical transport steps**, since relative velocity is zero. It still has nonzero error relative to the analytic B because of finite-resolution curl reconstruction. The fixed-grid loop has `max(abs(div_central))=1.73e-18`, while its independent `div_face_mc` RMS is `8.63e-5`. The latter RMS does not decrease monotonically across the nonsmooth loop ladder; differentiation near discontinuities and the nonlinear diagnostic must not be advertised as exact divergence cancellation.

Small archived [convergence data](../tests/reference/kinematic_2d/convergence.csv) and [provenance](../tests/reference/kinematic_2d/provenance.json) record this run. They are evidence, not bitwise golden outputs or author-supplied paper reference data. Full cell snapshots and plots are regenerated by the commands above.

Local verification: `cargo fmt --check`, `cargo clippy --all-targets --all-features -- -D warnings`, and `cargo test --workspace --locked` pass, with 13 Rust tests. The nine existing M0 algebra checks also pass. A GitHub Actions workflow is supplied but has not been observed running on GitHub.

The next physics milestone remains a reviewed ideal-gas conservative state/flux module, followed by periodic 2D Voronoi geometry and its reconstruction tests. Resolve the M0 face-normal B, limiter, predictor and stage-policy questions before coupling the fluid update to A. A circularly polarized Alfvén wave needs all three vector components; this single-Az pilot cannot run it.
