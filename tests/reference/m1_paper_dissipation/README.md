# Optional paper dissipation: rejected repair experiments

Both Eq. (77) evolution profiles were implemented and tested, then removed.
Successive raw-LS and direct quadratic-trace Laplacians with alpha=.2 reach
t=.02 at nx256, but fail the nx512 jittered shock before .000824. The nx256
successive alpha=.1/.2/.3 and quadratic alpha=.2 t=.01 screens complete all
16 evolutions, yet retain failing Bx diagnostics. All 37 recorded evolutions
finish or fail within 3.52 seconds each; no timeout or new remote job.

An independent regular-grid Fourier calculation shows that the 2D neighbour-only
inverse-distance quadratic trace has symbol
`lambda*h^2=(2/3)*(cos(2*theta)-cos(theta))`, positive for theta>2*pi/3.
Rust measurements agree within 2.39e-12; mode kx=6 on n16 has positive magnetic
energy growth. Smooth polynomial/convergence tests do not establish diffusion
stability. This rejects this use of the fit, not the paper's published results,
and does not explain the original solver's failure (which has no diffusion).

See [findings, scope and next decision](../../../docs/M1_SHOCK_INVESTIGATION.md#measured-dissipation-result-both-candidates-rejected-2026-11-09)
and the [visually inspected figure](../../../docs/images/m1_completion/paper_dissipation.png).
All original thresholds, numerical profiles and failed outcomes are preserved.
No full M1 acceptance, general invariance or merge is claimed.

## Contents

- `raw.tar.gz`: `raw/primary`, `low`, `high`, `extended` (successive trials),
  `quadratic_primary`, `quadratic_extended`, `baseline`, and `checks`.
  Each study has its exact source archive, provenance, commands, run logs,
  initial/final snapshots and measured results, including failures. Extended
  runs include accepted-step pressure, density, budget, energy and divergence.
- `raw_sha256.json`: hashes for every file in the raw archive.
- `analysis.json`: reverified run summaries, accepted histories and Fourier data.
- `retained_source.tar.gz` / `retained_source_sha256.json`: final measurement
  code, analysis/plot scripts and documentation, with the rejected profiles
  removed. Overlay on base `44cdb5618dd9fc23198fea66eca40d63271fc2b1`.
- `verification.json`: checks, baseline parity and disposition.
- `archive.json`: top-level hashes, excluding itself.

## Reproduction

After extracting raw data and retained source, run:

```sh
python3 scripts/analyze_paper_dissipation.py raw --output remeasured.json
python3 scripts/plot_paper_dissipation.py remeasured.json --output paper_dissipation.png
cargo run --release --locked -p moving-mesh --example laplacian-audit > modes.csv
```

The analyzer verifies 37 recorded evolutions and 529 source members against
study provenance, checks accepted-state histories, and independently checks
the regular-grid Fourier symbol. Plotting uses Matplotlib; it is not needed
for verification. The study source archives are authoritative for their runs.
The final source adds interpretation and does not expose the rejected solver
profiles. To reproduce either trial, use its own source archive in a separate
base checkout, then run its saved commands or its archived bounded runner
(`run_shock_repro.py` / `run_paper_dissipation.py`). Never overlay rejected
trial source on an active development checkout.

Final verification: 134 release Rust tests across all targets; 42 Python and
13 M0 tests; format, strict Clippy and pinned-reference checks pass. Six REANA
packaging tests pass after excluding this study from minimal uploads. Original
jittered nx256 initial/final CSVs are byte-identical to the earlier literal-state
paper baseline. Long REANA jobs remain stopped. Issues #19–#22 remain open.
