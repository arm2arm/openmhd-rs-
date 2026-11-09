# Projected-rate short-shock investigation

See [the prospective contract and findings](../../../docs/M1_SHOCK_INVESTIGATION.md).
The experimental `bulk-frame-heun-projected-v1` completes all four short
shocks to t=.01 with positive pressure, conservation and boost checks passing.
The unchanged jittered Bx diagnostic still fails. This is a partial stability
improvement, **not** a passed short screen or M1 acceptance. Long jobs remain
stopped; no merge is authorized by these results.

The initial-state probe shows a volume-weighted relative magnetic-rate mismatch
of .4718 on the nx256 jittered mesh even after solving the best-fit normal
equations. That residual falls to roundoff on the regular mesh. The projected
evolution adjusts the potential rate, with conservative fluid updates and
curl-based magnetic recovery retained. No pressure floor or energy reset is used.

`raw.tar.gz` contains six initial-state probes under `probe/`, the four short
evolutions and their complete diagnostics under `short/`, ten historical-output
comparisons under `parity/`, and validation logs under `validation/`.
`raw_sha256.json` hashes every contained file. Each run's provenance records
the compiler, base revision, exact commands, selected source and binary hashes.

Use a **fresh checkout of the recorded base revision** for each source archive;
extract the selected working files over that checkout. The checkout supplies
unchanged workspace files and pinned test references. Do not extract different
source versions over one another:

- `probe_source.tar.gz`: exact selected source for the initial compatibility
  example, before adding the evolution profile.
- `evolution_source.tar.gz`: exact source used by the four-case short runner.
- `retained_source.tar.gz`: final source, adding documentation, CLI help,
  thread-invariance coverage and the plotting script. Its file hashes are in
  `retained_source_sha256.json`.
- `initial_z_frame_attempt.tar.gz` and its text record preserve the first
  draft's failed out-of-plane boost control. The corrected frame passes the
  unchanged tolerance; no benchmark thresholds changed.

Reproduce the two measurements using separate fresh result directories:

```sh
cargo run --release --locked -p mhd-vector-pot --example shock-compatibility -- results/fresh_probe
python3 scripts/run_shock_repro.py --profile bulk-frame-heun-projected-v1 --output-dir results/fresh_short
```

The short runner returns **1**, correctly reporting the failed Bx gate. Its
four evolutions complete in 2.62 seconds in the recorded execution. Full-time
stability, convergence and physical-reference agreement remain untested for
this candidate. The existing default and five historical profiles are unchanged.

`verification.json` records 117 Rust tests, 38 Python tests, 13 M0 algebra
checks, reference verification, formatting and strict Clippy. The bounded
1/4/24-thread check is bit-identical; historical snapshots/histories/summaries
also match their frozen baseline in ten cases. The hashes in all source/data
archives were independently verified.

After extracting raw data, regenerate the figure with the retained source:

```sh
python3 scripts/plot_shock_compatibility.py raw/probe raw/short --output shock.png
```

`shock_projected_rate.png` is the inspected figure. `archive.json` hashes all
top-level evidence files, including this README, except itself.
