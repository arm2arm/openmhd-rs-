# Issue #5: periodic 2D geometry and reconstruction

Scope: the independent serial `moving-mesh` reference, periodic rectangular boxes, f64, nondimensional lengths, at least nine generators and no self-image faces. This is O(N²) half-plane clipping using all neighbour images in a 3x3 tiling. It does not provide a dynamic fluid integrator, remapping, general 3D tessellation or exact geometric predicates. Failed geometry/stencils must return errors, never silently substitute a different mesh or zero derivative.

The existing free-intercept, face-area-weighted least-squares operators and componentwise neighbour-extrema limiter follow the engineering choices in [M0](M0_ENGINEERING_DECISIONS.md#u2-reconstruction-and-endpoint-refresh). Neighbour-centroid and face-centroid fits exclude the target as an observation. The limiter is anchored at the cell value and uses the minimum factor in [0,1] that bounds every face extrapolation by the target/face-neighbour extrema. It is applied to separate copies; raw A gradients remain unlimited for curl. This limiter is an engineering choice, not a paper-specific formula or general monotonicity proof for a full time integrator.

## Predeclared checks

These checks are declared before running the new tests/study:

1. Analytic uniform and nonuniform tensor-product periodic generator grids: exact cell widths are half the sum of adjacent generator spacings, with centroids at the midpoint of adjacent bisectors. Require relative-plus-absolute errors <=1e-10 in box-normalized volume, centroid, face length and normal. Include periodic crossings and uniform length scalings 1e-6/1/1e6.
2. Every shared face has one left and one right incidence, opposite signs, a finite positive length, unit outward normal aligned with its generator separation, and a centroid on the generator bisector. Every cell has finite positive area and a finite centroid inside its face planes. Require closed face-normal sums, the boundary volume/tensor identities and the first moment about the cell centroid, with 1e-9 scaled tolerance; total area must match the box within relative 1e-9. Reject malformed connectivity without panicking.
3. Detect invalid/nonfinite box lengths, generators, cells/faces, out-of-range indices, duplicate incidences, periodic coincident generators and rank-deficient/ill-conditioned stencils. Stencil condition indicator remains trace(C)²/det(C), with rejection at det(C)<=1e-10 trace(C)². Validate finite coefficients and reject incorrect input lengths/nonfinite values or unrepresentable gradients.
4. Neighbour-centroid and face-centroid fits reproduce affine derivatives and annihilate constants to 1e-10. Affine fixtures use local unwrapped image coordinates; a globally nonperiodic affine scalar is only evaluated away from the periodic seam. Translation and generator permutation must preserve per-cell geometry/gradients after restoring cell IDs to 1e-10 normalized error.
5. Test the limiter directly on regular/jittered cells: all face extrapolations stay within target/neighbour extrema to 1e-12 scaled tolerance; constants give zero gradients; interior affine fields retain exact gradients to 1e-10 where bounds admit the face value. Reject invalid reconstruction inputs. The planar solver must use this same checked implementation.
6. Manufacture q=sin(2pi*x)sin(2pi*y) on the periodic unit square at N=8/16/32, with jitter=0 and .15 using the existing deterministic trigonometric pattern. Record volume-weighted vector-gradient L1/L2 errors for raw and limited neighbour fits and raw face fits, each against analytic derivatives. Report every refinement order. Require every raw-neighbour error order >1.8 on regular grids and >.7 on jittered grids, matching the existing curl-test thresholds. Require finest error below coarsest for the face and limited fits; do not claim second order on irregular or limited stencils without measured support.
7. Rebuild geometry and both derivative stencils after a periodic translation and a local topology change. Re-run affine reproduction on the rebuilt local stencils. Existing coupled uniform, conservation and boost tests must continue to pass. Rebuilding alone is not a conservative fluid/A transfer.

Geometry/reconstruction fixtures evolve no physical fluid or magnetic field and therefore have no fluid energy budgets. For A_z=q, the corresponding planar curl is (D_y q,-D_x q); gradient errors equal vector-curl errors. These tests do not establish any independent unstructured div(curl(A)) identity. The existing coupled tests retain their explicitly separate divergence diagnostics.

## Reproduction and measured evidence

The gates above were committed in `333ac8a` before the new regression tests or convergence study. Reproduce with:

```sh
source "$HOME/.cargo/env"  # if Cargo is not on PATH
cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
cargo build --workspace --locked
cargo test --workspace --locked
python3 scripts/check_m0_spec.py
python3 scripts/check_reference_packet.py
python3 scripts/test_core_flux_validation.py
python3 scripts/run_mesh_validation.py
```

The study needs only Rust and Python's standard library. It builds/runs `cargo run --release --locked -p moving-mesh --example reconstruction-study` and writes `summary.csv` and `provenance.json` to `results/mesh_validation/`. The [committed archive](../tests/reference/mesh_validation/) records source hashes, compiler, configuration, all L1/L2 errors and both refinement orders. The Rust example enforces the declared convergence gates; nonzero exit prevents a successful archive record. Existing GitHub CI runs all new Rust tests and Clippy checks the example. The full study is a documented local command; no workflow changes are required.

## Geometry and API changes

The old validator accepted a NaN cell volume because comparisons against NaN returned false. A new regression test reproduced this failure before the fix. Validation now checks finite values and index/sign/incidence consistency before dereferencing connectivity. Each canonical shared face has exactly one left and one right incidence, including its periodic image, with no duplicate keys or incidences. It checks generator-normal alignment and the bisector plane as well as cell boundary identities.

For a cell with area V, set h=sqrt(V), s_f=face_length/h and d_f=(face_centroid-cell_centroid)/h in the cell's image. With outward n_f the boundary identities are:

```text
sum_f s_f n_f = 0
sum_f s_f d_f[a] n_f[b] = delta[a,b]
sum_f s_f (d_f dot n_f) d_f / 3 = 0
```

The trace of the second identity gives the volume check. The third follows by integrating div(x_i x)=3*x_i in 2D about the centroid; straight-face midpoint quadrature is exact because x dot n is constant along each face. Closure and centroid residual tolerances are 1e-9 times the scaled perimeter; tensor components use absolute tolerance 1e-9. This catches an incorrect centroid even if it remains inside every face plane. Total normalized volume must equal one within 1e-9.

`Derivatives::gradient` now returns `Result`: values must have the exact cell or face count selected during stencil construction and must be finite. It subtracts an actual sample as a constant baseline in both modes, rejects unrepresentable coefficients/results, and preserves constant annihilation. `Mesh::limit_gradients` is the single checked implementation used by the planar solver for primitive/A extrapolation and limited-field diagnostics. Low-level displacement/neighbour helpers require an incident face from a validated mesh; those preconditions are documented.

The condition indicator trace(C)²/det(C) is an indicator, not the matrix's spectral condition number. Synthetic collinear and nearly collinear sample fits explicitly fail the conditioning gate. A box of aspect ratio 1.25e10 fails geometry reciprocity before a stencil can be built: the implementation explicitly rejects this configuration. This packet does not claim general extreme-aspect-ratio or full-f64-range geometry support.

## Measured results, 2026-11-04

Apple arm64, Rust 1.85.1, release profile, one process/thread. Errors are volume-weighted norms of the vector-gradient difference against the analytic derivative, divided by total volume. Lengths and scalar amplitude are nondimensional; there is no fitted normalization.

| Jitter | Operator | N8 L1 | N16 L1 | N32 L1 | L1 orders 8→16 / 16→32 |
| --- | --- | --- | --- | --- | --- |
| 0 | raw neighbour | .427792 | .108691 | .0273029 | 1.977 / 1.993 |
| 0 | limited neighbour | 1.13490 | .212245 | .0407592 | 2.419 / 2.380 |
| 0 | raw face | .109453 | .0273304 | .00683559 | 2.002 / 1.999 |
| .15 | raw neighbour | .618989 | .193581 | .0668661 | 1.677 / 1.534 |
| .15 | limited neighbour | 1.12260 | .256910 | .0765958 | 2.128 / 1.746 |
| .15 | raw face | .167439 | .0478019 | .0169370 | 1.809 / 1.497 |

Finest L2 errors in the same order are .0284929, .112027, .00713352, .0748926, .112535 and .0193038. Every declared gate passes. The regular raw operators show approximately second-order convergence for this scalar. Jittered operators do not demonstrate second order, and the limiter's larger error near extrema remains visible; high L1 order on the regular limited fixture is not a general order guarantee.

Across these six meshes, maximum relative total-area error is 2.22e-16, maximum face-closure residual divided by perimeter is 1.74e-15, and maximum stencil condition indicator is 4.319. The analytic nonuniform-rectangle fixtures also pass at uniform length scales 1e-6, 1 and 1e6. These are geometry/reconstruction measurements, not full MHD validation.

All 51 workspace Rust tests pass, including 12 geometry/reconstruction tests and the existing planar conservation/boost checks. Formatting, Clippy with warnings denied, locked build, 13 M0 algebra checks, independent-reference archive checks and four comparison-script tests pass. A separate AI review accompanies completion. General A/gauge integration, magnetic-wave validation, dynamic fluid geometry and the remaining M1 gates are still open.
