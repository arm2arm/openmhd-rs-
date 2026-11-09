# Exact-pattern geometry controls — 2026-11-09

The production solver is unchanged from `f1c0213458d4793f868a8f6afa12c72d5773a9ef`.
These six bounded experiments reuse the exact original nx256 x ny4 generator
perturbations. Repeating the stretched pattern in taller periodic boxes still
fails near t=.00334. Compressing the same four rows by 1/2 or 1/4 completes
t=.01; repeating the latter also completes. All configurations retain failed
Bx diagnostics. No registered benchmark, gate or solver profile is changed.

Repeated effective derivative rows agree within 3.87e-14 relative L1. The
original physical CSVs reproduce the previous geometry probe byte for byte.
Compression changes topology and neighboring magnetic reconstruction: the
253/255 face disappears, and the right reconstructed By on 253/254 changes
from -.871549 to -1. Cell 253's initial pressure rate changes from -35.3551
to +3.34461 under 1/4 compression. This localizes geometric sensitivity at
the magnetic discontinuity, without isolating aspect ratio from topology or
establishing a solver fix. See the [full table and plot](../../../docs/M1_SHOCK_INVESTIGATION.md#measured-repeated-pattern-result).

All initial/endpoint face audits reproduce the production first-step Q/A
update with zero measured difference, for both regular and jittered fixtures.
The six cases, including their audits, take 3.16–11.27 seconds each with at
most three serial processes and a 30-second cap. None times out. Maximum
normalized conservation residual across the histories is 2.12e-15.

## Contents and reproduction

- `raw.tar.gz`: `raw/controls` contains all six evolutions, original failures,
  geometry/operator CSVs, face audits, hashes, provenance and exact run source;
  `raw/checks` contains verification and original development-failure logs.
- `raw_sha256.json`: SHA256 of every raw file.
- `retained_source.tar.gz` and `retained_source_sha256.json`: final source,
  analysis/plotting tools and documentation. Overlay on a separate checkout
  of the recorded base revision.
- `verification.json`: actual checks, source correspondence and limitations.
- `archive.json`: top-level hashes, excluding itself.

From the retained source:

```sh
python3 scripts/run_paper_geometry.py --pattern-controls --output-dir results/fresh_pattern
python3 scripts/analyze_paper_pattern.py results/fresh_pattern --output results/fresh_pattern/analysis.json
python3 scripts/plot_paper_pattern.py results/fresh_pattern --output pattern_controls.png
```

The runner is observational: three numerical failures are expected. Exit zero
means all configurations were recorded, face audits completed and source and
binaries stayed unchanged; inspect `runs.json`, `summary.json` and `analysis.json`
for the physical results. This is not the M1 acceptance runner.

The exact measured runner is retained in `raw/controls/source.tar.gz`. After
the runs, its summary/exit check was tightened to require successful face
audits explicitly. The measured `runs.json` already records zero audit return
codes for all six cases, independently checked by the analyzer. The recorded
summary is preserved as produced; it predates the `face_audits_complete` field.
Subsequent additions are the analysis/plotting tools, evidence packaging and
results documentation. No measured Rust source changed after the runs.

With `raw.tar.gz` extracted, analyze or replot directly:

```sh
python3 scripts/analyze_paper_pattern.py raw/controls --output analysis_reproduced.json
python3 scripts/plot_paper_pattern.py raw/controls --output pattern_controls.png
```

The figure was visually inspected with Matplotlib 3.9.4. The analyzer accounts
for duplicate periodic images and the derivative's first-sample subtraction.
An early geometry test incorrectly matched distinct periodic images by base
cell ID; matching physical displacement fixed that test. A preliminary Rust
compatibility compile error was also corrected. Their logs are retained;
neither was a solver defect or a failed scientific candidate.

Final checks pass 129 release Rust tests across all targets, 42 Python tests,
13 M0 algebra tests, formatting, strict Clippy and pinned-reference integrity.
The six REANA packaging tests were rerun after adding this evidence directory
to the minimal-upload exclusions. No long job was restarted. Full M1 acceptance
remains false; issues #19–#22 remain open.
