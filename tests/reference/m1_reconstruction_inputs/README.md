# Frozen reconstruction and input-field diagnostics — 2026-11-09

Production Rust is unchanged from `e362c40e67c3970994804167cd7ee8a4a1e8a3c3`.
The paper's optional primitive fit through the central value passes the new
operator tests, but worsens cell 253's initial dp from -35.3551 to -35.4438.
Zero magnetic slopes worsen it to -61.9306. No evolution profile is introduced.

Counterfactual Riemann inputs isolate the neighboring curl values. Substituting
analytic Bx at cells 254/255 leaves dp=-30.6001; substituting By alone yields
-.0320103; both components yield +5.89480. This implicates broadening of By
as the dominant contributor to the target's initial energy drain. The stored
A/Q, closure B and curl operator are never modified. The substituted inputs
are inconsistent with A and never evolved: they are diagnostic interventions,
not a candidate algorithm or a permissible initialization repair.

Independent kink-residual and normal-equation calculations reproduce initial
B for cells 253–255 on all four fixtures; maximum kink reconstruction error
is 9.39e-15. Broadening is also described by the source, so this does not show
that the published derivative formula is wrong. Robust conservative energy/curl
coupling on the original geometry remains unresolved. See the
[full interpretation, table and plot](../../../docs/M1_SHOCK_INVESTIGATION.md#measured-reconstruction-input-result).

## Contents

- `raw.tar.gz`: the first centered-fit screen (`raw/centered`, 32 frozen
  evaluations), its input-substitution follow-up (`raw/inputs`, 64), the final
  component-separated probe (`raw/split`, 80), and `raw/checks`. Every stage
  retains exact run source, provenance, cell/face/slopes CSVs and failures.
- `raw_sha256.json`: per-file hashes for all raw files.
- `retained_source.tar.gz` and `retained_source_sha256.json`: final source,
  analysis/plotting tools and documentation. Overlay on a separate base checkout.
- `verification.json`: measured checks and correspondence to unchanged production.
- `archive.json`: top-level hashes, excluding itself.

The final probe takes 5.43 seconds, serial, under a 30-second external cap.
It contains old and predicted endpoint evaluations, not time integrations.
The only post-run Rust edit rewrites the three-cell CSV-export loop as an
iterator to satisfy strict Clippy. The original lint log is preserved. The
source archive inside each run is authoritative for that run; the retained
source also contains later analysis, plotting, packaging and results documentation.
A separate retained-source one-step audit gives six byte-identical CSVs to
the prior baseline and zero measured Q/A assembly differences.

## Reproduction

From the retained source, with Rust 1.85.1:

```sh
python3 scripts/run_reconstruction_probe.py --output-dir results/fresh_reconstruction
python3 scripts/analyze_reconstruction_probe.py results/fresh_reconstruction --output results/fresh_reconstruction/analysis.json
python3 scripts/plot_reconstruction_probe.py results/fresh_reconstruction/analysis.json --output reconstruction_inputs.png
```

After extracting `raw.tar.gz`, the last two commands can instead use
`raw/split` and `raw/split/analysis.json` as inputs; give the analyzer a fresh
output filename. Matplotlib 3.9.4 generated the visually inspected figure.
No optional numerical package is needed for the independent analyzer.

Final verification passes 131 release Rust tests across all targets, 42 Python
tests, 13 M0 algebra tests, formatting, strict Clippy and pinned references.
Six packaging tests were rerun after adding this archive to minimal REANA
upload exclusions. No long job was restarted, no gate changed, and no full
M1 acceptance or merge is claimed. Issues #19–#22 remain open.
