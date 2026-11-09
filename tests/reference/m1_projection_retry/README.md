# Bounded projection candidate and acceleration evidence

All 40 accelerated controls complete. The quadratic-curl projected candidate
keeps positive pressure through t=.02 on nx512 x ny4 jittered Brio base/boost,
finishing in 7.64/7.92 seconds. All four short N8/16/32 wave-convergence screens
pass with B/velocity orders 1.909–1.953. The linear-curl comparator still fails
two velocity screens. This is an engineering comparator, not the published
endpoint method or full M1 acceptance. Bx error .0549856 still fails 1e-8.

See [results and remaining work](../../../docs/M1_SHOCK_INVESTIGATION.md#measured-projection-retry-2026-11-09)
and the [visually inspected figure](../../../docs/images/m1_completion/projection_retry.png).
Default paper profiles, initial conditions and physical gates are preserved.
No long REANA workflow is restarted. #7/#19–#22 remain open.

## Contents and scope

`raw.tar.gz` contains **96 new evolutions plus three reused baseline records**:

- `raw/positive_primary`: four nx256 positive-Laplacian trial cases.
- `raw/positive_extended`: nine extension/dt/refinement cases. Both nx512
  trials fail at t=.00113439. This evolution profile is rejected and removed;
  only a separately tested measurement operator/probe remains in active code.
- `raw/projected_refinement`: three unchanged linear-curl projected shocks,
  including nx512 base/boost, all completing t=.02.
- `raw/controls`: 40 original Jacobi-solver wave/shock controls. 38 complete;
  both quadratic nx512 shocks time out at 30 seconds. Their accepted prefixes
  are retained; incomplete final CSV lines are excluded from measurements.
- `raw/accelerated`: the same 40 controls with cached preconditioning, all
  completing under the original cap. Each packet uses at most three serial
  cases concurrently. Completion does not imply every physical gate passed.
- `raw/baseline`: three reused literal-state paper controls from the preceding
  dissipation archive, including the original pressure failures.
- `raw/checks`: compiler/test logs, frozen positive-diffusion measurements,
  parity results and bounded-run logs, including earlier failed experiments.

Each study retains source archives, hashes, commands, binary hashes, run logs
and snapshots. `raw_sha256.json` hashes every file. `analysis.json` verifies
all 580 run-source members and records histories, errors, timings and failures.
`retained_source.tar.gz` / `retained_source_sha256.json` contain the final code,
measurement tools and documentation; overlay on base
`7bd051f98d3c089a0760a02fae21135596485c02` in a separate checkout.
`verification.json` records checks; `archive.json` hashes top-level files.

Run-source archives are authoritative for their measurements. Retained source
adds final thread checks, lint/style and analysis/documentation changes after
the runs. In particular it excludes fits of roundoff-sized initial velocity
errors, because that velocity is analytically imposed. No final spatial gate
or physical evolution changes. Failed positive-diffusion source is archived
only in its trial directories; never overlay it on active development.

## Reproduction

Extract raw data into a fresh directory, then use the retained analysis tools:

```sh
python3 scripts/analyze_projection_retry.py raw --output remeasured.json
python3 scripts/plot_projection_retry.py remeasured.json --output projection_retry.png
cargo run --release --locked -p mhd-vector-pot --example positive-dissipation-probe > frozen.csv
python3 scripts/run_projected_controls.py --accelerated-projection --output-dir results/accelerated_fresh
```

Plotting requires Matplotlib. Verification/analysis uses the Python standard
library. To reproduce historical trial runs, use their exact source archive
in a separate base checkout and the saved commands with fresh output paths.
The runner returns success for complete, source-stable execution; inspect its
reported physical screens. It always reports `full_m1_accepted=false`.

## Numerical and performance checks

The optional preconditioner factors `C^T V C + 1e-8 D` once for fixed/rigid
geometry. It solves the original **unshifted** projection equations with the
same residual tests; no pressure floor, energy reset or altered target.
The shift is not regularization of the physical objective. faer 0.22.6 is
pinned and MIT-licensed, with Rayon disabled and no internally threaded FFI.

Across 38 completed matched waves, physical differences are <=2.80e-13 and
A differences <=2.33e-10. Both shock prefixes agree through their 88 complete
rows. Matched N32 jittered waves are 10.1/10.0 times faster on this Mac; the
original fine shocks timed out, so no completed old shock runtime is claimed.
All three independent divergence histories are retained, not declared zero.

Checks: 138 release Rust tests across all targets, 43 Python tests, 13 M0
algebra checks, format, strict all-target/all-feature Clippy and pinned
references pass. Six REANA packaging tests pass after excluding this evidence
from minimal uploads. Serial and 1/2/4/24-thread states/diagnostics/counters
match bitwise. Full M1 wave/shock/vortex/loop validation remains outstanding.
