# Issue #4: conservative states and moving-face flux validation

This packet covers the ideal-gas/finite-volume kernels in `mhd-core`, independently of the future general A/gauge integrator. The published flux and wave-speed equations are attributed in [COUPLED_2D.md](COUPLED_2D.md), including [CANS+ equations (18), (45)-(74)](https://www.astro.phys.s.chiba-u.ac.jp/cans/doc/riemann.html). No external solver source is imported into Rust.

## Pressure and energy policy

The original issue mentioned pressure floors. The reviewed [M0 engineering profile](M0_ENGINEERING_DECISIONS.md) supersedes that proposal: require finite positive density/pressure, return errors for inadmissible states, and reject/retry invalid timesteps. Do not add pressure floors or reset conserved cell total energy. Face primitives receive a common arithmetic normal B while retaining their reconstructed gas pressure; their face energies are recomputed for the Riemann problem. Cell closure uses its conserved energy and reconstructed B, so increased magnetic energy reduces available thermal energy and may reject the state.

HLLD's guarded degeneracies/nonpositive intermediate states use a counted two-wave HLL fallback. The fallback must also be finite and admissible or return an error. This is a tested policy, not a proof of positivity for arbitrary data or discretizations.

## Predeclared extension checks

Declared before evaluating the new regression tests or comparing the updated kernels with the independent profiles:

1. Preserve analytic identical-state ALE fluxes, contact and rotational waves. Extend checks to both upwind branches, coordinate rotations, magnetic reversal, induction/EMF boost transforms, and normal reversal. Use relative-plus-absolute tolerance 1e-11 for ordinary states.
2. Check common-normal-B pressure preservation and fixed-cell-energy magnetic/thermal coupling. Reject nonfinite/invalid primitive, conservative and face inputs. Exercise valid low-pressure and zero-field/degenerate cases without floors.
3. Check the fast magnetosonic speed against exact parallel/perpendicular/unmagnetized limits, including pressure scales 1e-200 and 1e200 at rho=1. Require relative error <=1e-12 for the speed when the expected result is representable. Avoid avoidable squaring overflow/underflow; unrecoverable states still return errors.
4. In the separate 1D conservative-induction driver, evolve Brio-Wu on periodic [0,2], interface x=1, gamma=2, Bx=.75, at total N=512/1024/2048 through t=.1 with first-order spatial states and synchronized Heun time integration. Use CFL .3 with endpoint rechecking and counted half-step retries; no A/curl or Voronoi geometry enters this fixture. Compare x in [.5,1.5] with the pinned independent Athena++ 8192-cell unit-domain profile from the M0 archive, averaging fine reference cells over each candidate cell interval. The reference coordinates are already shifted to [.5,1.5].
5. For each rho/p/vx/By profile report L1 and L2 normalized by the fixed unit scales in the M0 packet. Require finest L1 < .03/.04/.03/.04 respectively and lower than coarsest. These limits are reused from M0; the driver and resolution ladder are this explicitly separate kernel-validation case, not a run of `paper-global-v1`.
6. Require finite positive density/pressure in accepted stages, periodic conservative budgets <=1e-10, unchanged Bx, and integrated maximum face-relative signal travel <.45 so the second periodic interface cannot reach the analysis region. Record fallback and rejection counts. A joint fluid/grid x-boost of +2 at N512 must reproduce comoving rho/p/B to 1e-10 after transforming velocity and energy appropriately.

In this one-dimensional fixture both the cell-centred and arithmetic-face divergence of the constant Bx are identically zero; By is evolved conservatively. This says nothing about unstructured multidimensional div(curl(A)). The independent reference uses Athena's HLLD implementation and PLM reconstruction, while this driver uses our implementation and piecewise-constant spatial states. Finite-resolution errors and the reference's own refinement uncertainty must be reported separately.

## Reproduction and evidence

The gates above were committed in `a3446d1` before the extension tests and comparison were run. The M0 reference archive is unchanged. The comparison script verifies its checksum before use.

```sh
source "$HOME/.cargo/env"  # if Cargo is not already on PATH
cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
cargo build --workspace --locked
cargo test --workspace --locked
python3 scripts/check_m0_spec.py
python3 scripts/check_reference_packet.py
python3 scripts/test_core_flux_validation.py
python3 scripts/run_core_flux_validation.py
```

The final command builds the release binary and runs all three resolutions plus the N512 boost, writing CSV snapshots and `archive/summary.csv`, `archive/provenance.json` and compressed profiles under `results/core_flux/`. It needs only Python's standard library and the pinned Rust toolchain. The summary contains L1/L2, each conservative budget, minimum accepted-stage density/pressure, signal travel and counters. The [committed archive](../tests/reference/core_flux/) includes the same small artifacts; provenance identifies source hashes, compiler/platform, binary, commands and the independent reference hash.

To run one case directly:

```sh
cargo run --release -p openmhd --bin brio-reference -- 2048 0.1 shock.csv
cargo run --release -p openmhd --bin brio-reference -- 512 0.1 boosted.csv 2
```

`BOOST_X` is optional and translates both fluid and grid. CSV `x` is the wrapped laboratory coordinate; `x_comoving` identifies the original cell. Velocities and energy are laboratory quantities. The earlier three-argument invocation and original seven columns remain supported, with energy and comoving position appended.

## Measured results, 2026-11-04

Apple arm64, Rust 1.85.1, optimized release, one process/thread, `f64`, gamma=2 and mu0=1. All 13 study gates pass. Profiles are cellwise comparisons of primitives against the reference primitives averaged over each candidate cell; no interpolation across shock locations or fitted amplitude normalization is used.

| Total N on [0,2] | Density L1 | Pressure L1 | vx L1 | By L1 |
| --- | --- | --- | --- | --- |
| 512 | .0144448 | .0168537 | .0318841 | .0191657 |
| 1024 | .0100716 | .0105862 | .0201887 | .0129025 |
| 2048 | .00670338 | .00646223 | .0125515 | .00809293 |
| Finest acceptance limit | .03 | .04 | .03 | .04 |

Finest L2 values are .0224905, .0254838, .0465809 and .0333664 in the same order. Athena's separate 4096-to-8192 reference refinement changes are .000239061, .000179467, .000393430 and .000253376 in L1 on 4096 bins. These estimate reference sensitivity; they are not an exact-solution error bound. Shock broadening remains visible in the first-order spatial driver, and no second-order convergence claim is made for this case.

| Total N | Accepted steps | Endpoint-CFL rejected trials | Min rho | Min p | Max normalized budget error | Integrated signal travel |
| --- | --- | --- | --- | --- | --- | --- |
| 512 | 632 | 619 | .117356 | .0883720 | 8.34e-15 | .377510 |
| 1024 | 1280 | 1267 | .117223 | .0881203 | 2.27e-14 | .378711 |
| 2048 | 2577 | 2564 | .117132 | .0879362 | 3.45e-14 | .379388 |

No invalid-state rejection or HLL fallback occurred in these shock runs; fallback is separately exercised by the degenerate-flux unit test. Counts refer to face evaluations in accepted stages. The timestep controller checks the Euler predictor endpoint as well as the old state, then halves and retries if its CFL bound grows stricter. This deliberately simple rule causes nearly one rejection per accepted step here and is not an optimized controller. It never repairs a state or changes the conservative energy.

Periodic budgets use `abs(U_final-U_initial)/max(abs(U_initial),initial_mass)` for each of mass, three momenta, total energy and By in these nondimensional units. The largest boost discrepancy across rho/p/B, transformed velocities and energy is 1.83e-14 (energy); the rho/p/B maximum is 5.22e-15. Bx is constant by construction, so `(Bx[i+1]-Bx[i-1])/(2*dx)` and the difference of arithmetic face Bx divided by dx are both exactly zero. This fixture exercises no multidimensional divergence cancellation or gauge cleaning.

The fast-speed regression first failed in the old formula at p=1e-200: the discriminant underflowed, underestimating the sound speed by a factor sqrt(2). The replacement normalizes sound/Alfven speeds and uses the algebraically equivalent discriminant `(a²-b²)²+4*a²*bt²`, evaluated with `hypot`; tests also cover p=1e200, parallel/perpendicular fields and the unmagnetized limit. This does not promise that all conservative or flux arithmetic can represent every extreme finite input; unrepresentable states still return errors.

The full workspace passes 44 Rust tests, formatting, Clippy with warnings denied and a locked build. The 13 M0 algebra tests, independent archive checker and three new Python comparison tests pass. CI repeats these checks and the 1D independent study. The separate AI review is recorded alongside the completion evidence; it is not human peer review or author confirmation. Full M1 acceptance still requires the general A/gauge integration and its benchmark gates.
