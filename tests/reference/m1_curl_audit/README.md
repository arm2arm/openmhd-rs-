# Initial Brio curl reconstruction audit

See [the prospective contract and measured conclusions](../../../docs/M1_SHOCK_INVESTIGATION.md).
This is an initial-state diagnostic. It changes no production solver, initial
condition, mesh, physical tolerance or execution policy. The retained projected
candidate still passes short stability/budget/boost controls and fails Bx.

All 12 probes complete in 2.29 seconds. The registered Brio initial Az and a
smooth periodic one-dimensional control are evaluated at nx256/512/1024,
ny4, regular/jitter=.15. Jittered Brio maximum initial Bx errors are
.160355/.149907/.284451. Errors outside neighbour stencils spanning a slope
change are <=3.34e-16. The smooth field also has a transverse reconstruction
error. The regular control remains at roundoff.

Independent 70-digit Decimal normal-equation fits match the implemented
derivatives to 2.23e-16. Affine and constant controls pass; the decomposition
of Dy Az into the nonlinear residual from the local analytic affine branch
agrees to 3.89e-16. The measured error is consistent with the selected
free-intercept affine approximation; higher arithmetic precision does not
remove it. This does not prove the entire solver correct or the full-time
Bx gate impossible.

`raw.tar.gz` contains every initial cell, the worst-cell sample data for all
12 fits, summary, independent calculations, compiler/source provenance and
validation logs. `raw_sha256.json` lists every contained file. The summary,
independent fits and production-source parity record are also available
uncompressed. `source.tar.gz` contains the exact selected working files for
the run and the prospective contract, before results were appended.

Reproduce in a fresh checkout at the base revision in `provenance.json`, with
the selected source archive extracted over it. The checkout supplies unchanged
workspace files and pinned test references. From the repository root:

```sh
mkdir results/fresh_curl_audit
cargo run --release --locked -p mhd-vector-pot --example shock-curl-audit -- results/fresh_curl_audit/cells > results/fresh_curl_audit/summary.csv
python3 scripts/check_shock_curl_audit.py results/fresh_curl_audit
```

The checker uses only Python's standard library. Its 3x3 pivoted Decimal solve
is independent of the production scaled 2x2 covariance implementation. It
rejects singular/invalid samples, missing families and failed numerical
controls. The full check suite passes: 118 Rust tests, 41 Python tests, 13 M0
algebra checks, pinned reference verification, formatting and strict Clippy.

`verification.json` records the scope; `archive.json` hashes all evidence
files including this README, except itself. All data/source archive members
were checked against their recorded hashes. Long REANA jobs remain stopped;
these diagnostic results do not establish M1 acceptance or permission to merge.
