# M1 serial reference implementation

The complete initial M1 case set is implemented in the general 2.5D endpoint solver and a separate prescribed-flow transport driver. Physical acceptance is still being evaluated against the unchanged [M0 benchmark packet](M0_BENCHMARK_PACKET.md); implementation availability alone does not close M1. The [completion plan](M1_COMPLETION_PLAN.md) records prospective changes, measurement corrections and required gates.

## Explicit numerical profiles

`paper-global-v2` remains the historical default. `bulk-frame-v1` changes the mean-field gauge as documented in [the wave/loop plan](M1_WAVE_LOOP_PLAN.md), storing A=a+C with a constant initial mass-mean reference velocity. Its remaining N64 standing-wave boost failure is retained in [the earlier results](M1_WAVE_LOOP_RESULTS.md).

The new `bulk-frame-hll-v1` retains the bulk-frame equations and changes only the face-state completion used by the vector-potential source. It averages the conserved state across a symmetric fan enclosing the historical HLLD outer speeds, using alpha=max(|SL|,|SR|). This continuous average supplies the completion B and velocity. The tangential EMF still comes from the actual numerical induction flux; its normal component uses the completion state. The same B is used in the face-frame-to-lab boost and in `EMF - u_aux cross B`. The finite-volume fluid and induction fluxes are bit-identical to the historical routine for identical face inputs. This is a separately named engineering convention, not a claim of an exact paper prescription.

Permanent tests cover zero/signed normal B, finite-normal-field stationary rotational waves, three-component boosts, rotations, normal reversal, nonuniform HLL fallback, cell-ID permutations and the former rectangular geometry-roundoff failure. The previously failing N64 standing-wave fixture now has vector B boost L1 4.01489e-14, compared with 3.10769e-4 under `bulk-frame-v1`. This verifies that fixture only; full spatial/temporal and physical-reference gates remain separate.

`bulk-frame-hll-quadratic-v1` is a further explicitly experimental reconstruction profile motivated by irregular-grid consistency measurements. It uses a free-intercept quadratic A fit over two neighbour rings; all other stage/source choices remain unchanged. It is being evaluated separately and is not yet an accepted replacement. Its N128 irregular-wave probe shows increased evolved error despite lower initial curl error, so it is not accepted.

`bulk-frame-hll-consistent-v1` adds positive centroid-triangle source averaging and a quadratic donor/receiver correction to pointwise advection. One limiter factor per A component scales both gradient and Hessian; the unlimited gradient still supplies the curl. The isolated passive equivalent is selected with `--consistent`. Manufactured full-rate identities, affine source moments and passive/general operator equivalence pass, but the physical wave study is still pending. These profiles are explicit experiments, with unchanged acceptance thresholds. See the [separate AI review](M1_COMPLETION_AI_REVIEW.md).

## Run on a Mac

Build from the repository root with the pinned Rust toolchain (`source "$HOME/.cargo/env"` if Cargo is not already on PATH):

```sh
cargo build --release --locked --bins

# Circularly polarized wave, periodic square, gamma=5/3
cargo run --release --locked -p openmhd --bin vector-potential -- \
  --profile bulk-frame-hll-v1 --case alfven --n 32 --jitter 0.15 \
  --parallel-velocity 1 --time 1 --checkpoint 0.25 --output results/m1_wave_example

# Brio-Wu, periodic 2 x .125 strip, gamma=2, central comparison interval [.5,1.5]
cargo run --release --locked -p openmhd --bin vector-potential -- \
  --profile bulk-frame-hll-v1 --case brio --nx 256 --ny 4 \
  --time 0.1 --output results/m1_brio_example

# Orszag-Tang, periodic unit square, gamma=5/3
cargo run --release --locked -p openmhd --bin vector-potential -- \
  --profile bulk-frame-hll-v1 --case vortex --n 64 \
  --time 0.5 --output results/m1_vortex_example

# Prescribed-flow loop: fixed Voronoi mesh; add --comoving for exact discrete transport
cargo run --release --locked -p openmhd --bin passive-voronoi -- \
  --n 64 --jitter 0.15 --output results/m1_passive_example
```

All states and geometry use f64, dimensionless units and mu0=1. The general solver uses global steps, conservative shared-face gas fluxes, strict positive density/pressure and no pressure floor or magnetic-energy reset. It writes initial/final CSVs, optional checkpoint CSVs, diagnostics/history JSON and oriented cell polygons. Failures retain the last accepted state and an explicit failed status. The passive driver evolves only scalar Az under prescribed v=(2,1), using the general face-LS upwind transport restriction and Heun steps; it does not evolve gas or cleaning.

## Full registered studies

These are substantial serial-per-run studies; `--jobs` controls concurrent independent processes. The first N256 mesh construction is expensive. Exact serialized mesh reuse avoids repeating that initialization across physics cases; every cache preserves f64 bits, ordering and its producer provenance and is validated against the requested lattice.

```sh
python3 scripts/run_m1_wave_loop.py --suite all --profile bulk-frame-hll-v1 \
  --temporal --jobs 4 --mesh-cache-dir results/m1_mesh_cache \
  --output-dir results/m1_full_wave_loop
python3 scripts/run_m1_completion.py --jobs 4 \
  --mesh-cache-dir results/m1_mesh_cache --output-dir results/m1_remaining
```

Use fresh output directories. `--analyze-only` remeasures existing evolutions only after verifying their immutable execution metadata, raw files and reference hashes; it preserves the original summary and writes separate analysis provenance. `--reuse-from` can import completed, exact-configuration runs from a stopped earlier study, preserving the original per-run execution origin and exact source ledger bytes. Unfinished or failed runs are not silently counted as completed.

The wave study reports initial curl error separately, true N-by-N spatial ladders, fixed-grid temporal refinement, joint boosts, magnetic energy, three independent divergence operators, positivity and normalized conservation budgets. The remaining study adds prescribed-flow loop errors, Brio reference averaging onto each candidate polygon before absolute differences, and vortex primitive-field projection by exact polygon overlap onto 64-by-64 comparison bins. The reference refinement differences are archived sensitivity estimates, not rigorous error bounds. Longer vortex times, full 3D, adaptive cells, MPI/Rayon and local steps remain later milestones.


## Diagnose the reconstruction experiments

The bounded probe runs only the fixed irregular travelling-wave ladder, using exact cached meshes. It is not the full acceptance packet:

```sh
python3 scripts/run_m1_quadratic_probe.py --profile bulk-frame-hll-consistent-v1 \
  --jobs 2 --mesh-cache-dir results/m1_mesh_cache --output-dir results/m1_consistent_probe
python3 scripts/plot_m1_wave_probes.py --linear-dir results/m1_completion_full \
  --quadratic-dir results/m1_quadratic_probe --consistent-dir results/m1_consistent_probe \
  --output-dir results/m1_probe_figures
```

The plotter uses only completed runs with matching snapshot hashes, marks pending cases, and reports initial and evolved errors separately. Figures show volume-weighted vector B L1 and unsmoothed cell-centroid error maps; missing results are never plotted as zero.
