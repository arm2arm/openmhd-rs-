# Quadratic-curl development evidence

The retained `bulk-frame-heun-quadratic-v1` uses a free-intercept quadratic
double-neighbour derivative for A/phi and the existing projected magnetic-rate
coupling. It is an experimental engineering comparator; the default is unchanged.
See the [prospective contracts, results and limitations](../../../docs/M1_SHOCK_INVESTIGATION.md).

All eight short t=.01 evolutions and six observational t=.02 extensions
complete. At t=.02 on the jittered nx256, ny4 shock, Bx error decreases from
.107515 for the previous projected profile to .0604426 for the retained
quadratic profile, with minimum p=.0493331 and zero state rejections.
Conservation and boost comparisons pass. The Bx gate is still 1e-8 and fails;
**neither short screen nor full M1 acceptance is claimed**. No long REANA job
was restarted, and no merge was made.

The wider fit improves initial x-only transverse accuracy and measured smooth
2D convergence order, but has larger absolute errors on the small 2D ladder,
broadens the initial shock and costs more per evolution. A second variant
using the same fit's symmetric Hessians for magnetic face slopes was measured
and removed: its t=.02 Bx error is .0701692. Its complete source and results
remain here. No pressure floor, energy reset or known-answer field overwrite
is used by either trial.

Use a separate fresh checkout at the recorded base revision for each source
archive, then extract the selected source over it. Do not mix versions:

- `quadratic_source.tar.gz`: source used by the first four-case screen.
- `hessian_source.tar.gz`: rejected Hessian variant, also used by the six
  extensions (including its unchanged projected/quadratic profiles).
- `retained_source.tar.gz`: quadratic candidate after removing Hessian,
  with added transpose/thread checks, documentation and plotting script.
- `raw.tar.gz`: all initial derivative measurements, both complete short
  screens including per-step energy traces, all six extensions, historical
  parity outputs and validation logs. Original commands, configurations,
  source/binary hashes and run status are included.

`raw_sha256.json` verifies every file in the raw archive.
`retained_source_sha256.json` verifies the retained source archive.
`verification.json` records the checks and scientific limitations.
`archive.json` hashes all top-level archive files except itself.
The base revision is scaffolding for reproducing the archived working trees;
it is not claimed to contain the uncommitted experimental changes.

Reproduce the retained initial measurement and short screen:

```sh
cargo run --release --locked -p mhd-vector-pot --example quadratic-curl-probe
python3 scripts/run_shock_repro.py --profile bulk-frame-heun-quadratic-v1 --output-dir results/fresh_quadratic --trace-energy
```

The short runner correctly exits **1** for the failed Bx gate. To reproduce
an observational extension, use the archived source/version and its exact
command in `raw/extension/runs.json`, changing only the output directory.
Each process was capped at 30 wall seconds, with at most three concurrent
processes. Timeouts would be failures, not accepted results.

Retained verification: 126 Rust tests across all targets (release), 41 Python
tests, 13 M0 algebra checks, pinned-reference verification, format and strict
Clippy pass. Ten historical boosted wave/loop cases retain byte-identical
physical CSVs, histories and summaries. A new bounded 1/4/24-thread check is
bit-identical. These checks do not establish physical benchmark acceptance.

After extracting `raw.tar.gz`, regenerate the inspected plot using:

```sh
python3 scripts/plot_shock_quadratic.py raw raw/previous_projected_short --output shock_quadratic.png
```

The `previous_projected_short` folder contains the small prior measurements
used in this figure; their original full archive remains in `m1_projected_rate`.
