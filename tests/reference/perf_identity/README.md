# Result-preserving solver speed-ups (issue #26, 2026-11-16/17)

Requested by the owner on 2026-11-15: the code was too slow to run the N256
tests in reasonable time (the registered N256 loops of the 2026-11-13
campaign took 11.5–15.2 hours each). Branch `arm2arm/perf-solver-speedup` on
top of `32155bc`, merged into `main` at the owner's request on 2026-11-17.

**Verification at merge time.** The tests and the comparisons of sections
3.1–3.3 had passed. The six-case campaign comparisons of `c110d59` and
`e8d228b`, and the tests and historical comparison of `e8d228b`, were still
running on REANA; their results are added in a later commit.

**Scope.** Every change below keeps the floating-point operations and their
order. The physical outputs of the comparison cases are byte-identical to
those of the campaign binary. No gate, threshold, grid, default or registered
result changed, nothing is reviewed, and M1 remains unaccepted. The opt-in
`--trial-step-fraction` (section 5) is a measurement option; its default
reproduces the historical controller, and no registered case uses it.

## 1. Changes

| Commit | Change |
| --- | --- |
| `40f9848` | Validate each geometry once (`ValidMesh`) instead of at every limiter call; reject a Heun trial at its CFL bound before the A-rate projection; reuse the closure (fit and primitives) of an accepted step; share stencils across rigid translations; reuse the unlimited A gradients in the limiter; per-phase times in `timing.json`. |
| `b8a8aae` | Voronoi clipping without per-plane allocation, with cached vertex radii, one side evaluation per vertex and block copies (`Polygon`). |
| `bdcb538` | Flat stencil copy for the projection: the curl in one parallel pass per cell, its transpose as per-target term lists in the order of the serial scatter, the Jacobi diagonal cached. |
| `1901fe3` | Pressure-blend ratio taken once per cell instead of over the two-cell stencil at every face. |
| `20a09db` | Profile counters only: rejected trials by the ratio of bound to step. |
| `79302bd` | Test fix: the new pressure-ratio test asked for a 3×5 lattice, which `Mesh::lattice` rejects. |
| `a7cd1ce` | Parallel elementwise updates in the iterative (Jacobi-PCG) projection; inner products stay serial. |
| `f4487ea` | Opt-in `--trial-step-fraction S`; default 1 is the historical controller and writes nothing new. |
| `e599e91`, `c110d59`, `74b6006` | Comparison tooling (below), including a suite for the historical profiles. |
| `e8d228b` | Primitive gradients and the magnetic fit: all components fitted and limited in one parallel pass; the scalar path still runs to report any error. |

One difference is visible in counters only, from `40f9848`: a trial that
exceeds its bound *and* whose discarded projection would also have failed now
counts as a CFL rejection instead of a state rejection. The retried step is
the same. None of the comparison cases has such a trial.

Every replaced kernel stays in the code as the reference of a unit test that
compares old and new bit for bit, on one and three threads where the kernel is
parallel: `clip`, the serial curl loops, `face_weight`,
`project_serial_reference`, and the scalar gradient and limiter functions.

## 2. How it is verified

`scripts/run_perf_compare.py` (REANA study `perf-compare`, see
[docs/REANA.md](../../../docs/REANA.md)) builds the snapshot and runs six short
excerpts of the campaign configuration `bulk-frame-heun-quadratic-v1 --motion
rigid --accelerated-projection --projection-screening 1 --riemann
hlld-pressure --potential-limiter smooth-extrema`. Each case runs with the
campaign binary `7544a6ab…` (frozen source `7fef6e2`) and with the new build,
one after the other on the same node with four threads. Every physical output
(`initial.csv`, `final.csv`, `summary.json`, `history.json` and, where
written, the physics, geometry and shock-face files) must be byte-identical.
Only `timing.json` is excluded.

- The N256 baseline takes 15 minutes. It comes from `baseline.json`, which
  holds the hashes and timings that the same binary, arguments and
  configuration produced on 2026-11-16. Ratios against it are marked
  *recorded*.
- From `c110d59` the iterative projection (no `--accelerated-projection`, the
  default of the projected profiles) also runs with both binaries and must be
  byte-identical.
- `m1-fanout-preflight` on the same snapshot runs `cargo fmt --check`, Clippy
  with `-D warnings`, the debug and release workspace tests and the Python
  tests.

Timings are single observations on a shared node. Between days they vary by
about ±20 %: the unchanged factored solve of the N256 case took 35.4 s on
2026-11-16 and 28.2 s on 2026-11-17.

## 3. Results

Evolution, mesh build and total times are `timing.json` values of the
campaign binary → the new build, four threads. *Recorded* marks the N256
baseline taken from `baseline.json`.

### 3.1 Round one: `40f9848` (2026-11-16, candidate binary `a269aae0…`)

| Case | identical | steps / CFL rejections | mesh build (s) | evolution (s) | total (s) |
| --- | --- | ---: | ---: | ---: | ---: |
| `alfven128_standing` | yes (5 files) | 163 / 162 | 25.8 → 26.8 | 58.6 → 36.9 (×1.59) | 88.3 → 67.3 (×1.31) |
| `alfven128_jitter_boost` | yes (5 files) | 169 / 142 | 12.8 → 12.5 | 83.0 → 56.2 (×1.48) | 103.1 → 76.7 (×1.34) |
| `loop128_jitter` | yes (5 files) | 147 / 0 | 12.6 → 12.6 | 48.8 → 43.9 (×1.11) | 69.5 → 63.5 (×1.10) |
| `vortex128_jitter` | yes (7 files) | 227 / 226 | 12.9 → 12.6 | 120.3 → 72.9 (×1.65) | 141.7 → 93.7 (×1.51) |
| `brio512_jitter` | yes (7 files) | 344 / 316 | 0.0 → 0.0 | 11.9 → 7.7 (×1.56) | 13.0 → 8.6 (×1.51) |
| `alfven256_standing` | yes (5 files) | 43 / 42 | 767.9 → 747.2 | 79.5 → 55.6 (×1.43) | 871.4 → 826.3 (×1.05) |

### 3.2 Round two: `e599e91` (2026-11-17, candidate binary `20407357…`)

| Case | identical | steps / CFL rejections | mesh build (s) | evolution (s) | total (s) |
| --- | --- | ---: | ---: | ---: | ---: |
| `alfven128_standing` | yes (5 files) | 163 / 162 | 28.4 → 14.6 | 58.6 → 39.7 (×1.48) | 91.1 → 58.2 (×1.57) |
| `alfven128_jitter_boost` | yes (5 files) | 169 / 142 | 13.0 → 7.7 | 80.9 → 57.7 (×1.40) | 101.2 → 73.4 (×1.38) |
| `loop128_jitter` | yes (5 files) | 147 / 0 | 12.6 → 7.5 | 47.1 → 38.7 (×1.22) | 67.6 → 53.4 (×1.27) |
| `vortex128_jitter` | yes (7 files) | 227 / 226 | 12.5 → 6.4 | 111.8 → 71.2 (×1.57) | 132.1 → 85.8 (×1.54) |
| `brio512_jitter` | yes (7 files) | 344 / 316 | 0.0 → 0.0 | 11.8 → 7.0 (×1.68) | 12.7 → 7.9 (×1.60) |
| `alfven256_standing` | yes (5 files) | 43 / 42 | 767.9 → 353.2 | 79.5 (recorded) → 45.2 (×1.76) | 871.4 → 424.3 (×2.05) |

Variant `iterative_projection` against the new build's own run:

| Case | evolution (s) | total (s) | peak RSS (MiB) | steps / CFL rejections | iterations per projection | largest difference: physical / potential |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `alfven128_standing` | 39.7 → 31.1 (×1.28) | 58.2 → 46.5 | 377 → 94 | 163/162 → 163/162 | 30 | 7.55e-15 / 1.73e-17 |
| `alfven128_jitter_boost` | 57.7 → 54.9 (×1.05) | 73.4 → 64.0 | 634 → 116 | 169/142 → 169/142 | 43 | 1.91e-14 / 1.32e-16 |
| `loop128_jitter` | 38.7 → 30.6 (×1.27) | 53.4 → 38.3 | 634 → 108 | 147/0 → 147/0 | 30 | 2.44e-15 / 1.29e-18 |
| `vortex128_jitter` | 71.2 → 55.9 (×1.27) | 85.8 → 64.1 | 636 → 121 | 227/226 → 227/226 | 31 | 2.00e-15 / 5.55e-17 |
| `brio512_jitter` | 7.0 → 13.3 (×0.52) | 7.9 → 13.9 | 108 → 108 | 344/316 → 344/316 | 34 | 8.02e-13 / 3.50e-14 |
| `alfven256_standing` | 45.2 → 35.4 (×1.28) | 424.3 → 452.7 | 1989 → 322 | 43/42 → 43/42 | 32 | 1.11e-15 / 3.47e-18 |

In the variant table the new build's factorized run is compared with its own
iterative run. The largest differences are absolute maxima over all cells of
the final ρ, p, v, B and of A, φ; the values are of order 0.1 to 1. The
iterative N256 total is larger only because its unchanged mesh build took
413 s instead of 353 s. Every CFL rejection of round two had a predictor
bound of at least 0.99 of the trial step (round one did not count margins).

### 3.3 Historical profiles: `624d1af` (2026-11-17, candidate binary `b73cf432…`)

`--suite historical`, the same Rust sources as `c110d59`. Each case runs with
its own complete arguments and no campaign options; the projected and
quadratic cases use the default exact projection (no screening) and the
quadratic one the default HLLD flux and limiter. The fluid-motion case
rebuilds the mesh at every trial, inside its evolution time; the mesh column
is the initial build only.

| Case | identical | steps / CFL rejections | mesh build (s) | evolution (s) | total (s) |
| --- | --- | ---: | ---: | ---: | ---: |
| `paper_global_alfven32_fluid` | yes (4 files) | 13 / 2 | 0.0 → 0.0 | 0.6 → 0.4 (×1.36) | 0.9 → 0.7 (×1.34) |
| `paper_global_loop64_fixed` | yes (4 files) | 75 / 0 | 0.5 → 0.4 | 1.8 → 1.0 (×1.79) | 2.6 → 1.9 (×1.35) |
| `bulk_frame_alfven64_rigid_boost` | yes (4 files) | 47 / 46 | 0.6 → 0.4 | 2.1 → 1.5 (×1.39) | 3.3 → 2.3 (×1.45) |
| `heun_alfven64_rigid_boost` | yes (4 files) | 47 / 46 | 0.6 → 0.4 | 2.5 → 1.5 (×1.67) | 3.9 → 2.4 (×1.65) |
| `spline_loop64_fixed` | yes (4 files) | 75 / 0 | 0.6 → 0.4 | 2.3 → 1.3 (×1.83) | 3.4 → 2.1 (×1.65) |
| `projected_alfven64_fixed` | yes (4 files) | 46 / 45 | 0.6 → 0.3 | 25.3 → 11.9 (×2.13) | 26.3 → 12.6 (×2.09) |
| `quadratic_defaults_alfven64` | yes (4 files) | 29 / 11 | 0.6 → 0.3 | 33.0 → 17.7 (×1.87) | 33.9 → 18.3 (×1.85) |

## 4. What is left, and why it needs a decision

With the campaign configuration, the cached-Cholesky triangular solves are
now about two thirds of the stepping time (N256: 28.2 of 45.2 s; loop N128:
26.4 of 38.7 s). A triangular solve cannot run faster without changing its
summation order. The rest of a stage is spread over the fluid rate (about
11 %), the primitive gradients (8 %), the magnetic fit (5 %), the auxiliary
field, the bound and the A rate.

The mesh build is the other large cost: 353 s for the N256 lattice on four
threads, 15 s for N128. Every generator is offered to every cell in ID order,
and before the generators of its own row arrive a cell polygon spans the whole
box, so nearly every far plane cuts it. That clip order decides the roundoff
of every vertex, so the build stays superlinear unless the order changes.

## 5. Open decisions for the owner

None of these is adopted, and each changes results. Each would need the
registered matrix again before it could replace the campaign configuration.

**(a) Iterative projection instead of the cached factorization.** The same
equations and residual tolerances, solved by Jacobi-PCG, which is the default
path of the projected profiles. Measured in all six cases: identical step,
rejection and fallback counts, final states within 2×10⁻¹⁴ (8×10⁻¹³ in the
Brio shock), 30–43 iterations per projection, and 4–6 times less memory
except in the small Brio case. On 2026-11-17 it was ×1.05–1.28 faster at N128
and N256 and two times slower for the 512×4 Brio case, whose factorization is
tiny. Section 3 gives the times after the parallel vector updates.

**(b) A trial step fraction.** In every CFL rejection of the comparison cases
the predictor bound was at least 0.99 of the trial step. The controller tries
the old state's bound, misses by less than one per cent and halves, so wave,
vortex and shock cases advance at about half their bound. The registered N256
runs had a CFL rejection in 43–72 % of their steps (for example 13,600 of
19,818 in a fixed-mesh loop); their margins were not recorded.
`--trial-step-fraction 0.95` tries 0.95 of the bound first. It changes the
step sequence, raises the time step by up to a factor of 1.9 and with it the
temporal error, which is second order. Section 3 gives the measured effect.

**(c) Mesh build order.** Clipping nearest generators first would make the
build roughly linear (seconds instead of minutes at N256). It changes every
vertex at roundoff level and therefore every result. Not implemented.

## 6. Files and reproduction

- `baseline.json`: recorded baseline of the N256 case (no commands or paths).
- `results.json`: reduction of each comparison run, keyed by date
  (`summarise.py`), with source revision, snapshot hash, image, toolchain,
  binary hashes, identity per case, timings, profile phases and the variant
  measurements.
- `summarise.py`: `python3 tests/reference/perf_identity/summarise.py --label
  <date> --outputs <downloaded outputs/> --snapshot <submission>/snapshot.json`.

To repeat a comparison: `python3 scripts/prepare_reana.py --minimal
--compact-history --output <fresh>`, `python3 scripts/add_reana_binary.py
<fresh> baseline-vector-potential <campaign binary>`, then from `<fresh>` run
`m1-fanout-preflight` (`jobs=1`) and `perf-compare` (`jobs=4`) as two
workflows, download `outputs/`, and reduce.
