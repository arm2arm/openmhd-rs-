# Paper coupling and geometry diagnostics — 2026-11-09

The retained solver is unchanged from checkpoint `e17cf9b337d2dd3a4c9228d0cbe45e85df34ec4e`.
New diagnostic examples independently assemble the stationary first step and
measure bounded geometry controls. See the [interpretation and plot](../../../docs/M1_SHOCK_INVESTIGATION.md#resumed-paper-audit-and-prospective-mixed-stencil-trial-2026-11-09).

The face audit reproduces Q/A updates bit for bit. Faces 1050 and 1051 account
for 99.4% of cell 253's initial energy loss; both use HLLD, and their state and
flux EMFs agree to roundoff. Initial dE=-42.2816 versus curl-derived dM=-6.92645
drives dp=-35.3551. The independent FV-induction diagnostic gives dM=-39.7689;
it is not used to overwrite the solver's magnetic field. Shared conservative
exchanges remain equal and opposite.

The optional mixed-stencil trial retained linear cell B and used quadratic
Hessians only for magnetic face slopes, with the original gauge, literal
Riemann-state source and paper endpoint stages. Its two new operator tests
and three uniform/boost controls pass, but both jittered short shocks fail
earlier, at t=.00295085417. Its profile and Hessian additions were removed.
Exact source and failures are preserved in `raw/hessian/source.tar.gz`.

Seven of eight bounded geometry controls complete; the original nx256 x ny4
jittered shock still fails at t=.00334288704. At nx256, ny8/16 reach t=.01
with final minimum p=.0802609/.0814819, after history minima .0141654/.0267612.
Their final Bx errors are .110146/.0821556. Geometry changes improve short
stability but do not resolve the registered Bx gate or establish physical
accuracy. Changing ny also changes topology/jitter/auxiliary samples; this
does not isolate aspect ratio alone.

## Contents and reproduction

- `raw.tar.gz`: face CSVs and a byte-identical rerun, eight geometry controls,
  four mixed-Hessian shock runs including full energy traces, source snapshots,
  provenance, original failures and verification logs.
- `raw_sha256.json`: every raw file's SHA256.
- `retained_source.tar.gz` and `retained_source_sha256.json`: final source and
  measurement tools with per-file hashes. Restore over a separate checkout
  at the recorded checkpoint; do not mix this with the rejected source.
- `verification.json`: actual checks, source correspondence and limitations.
- `archive.json`: top-level file hashes, excluding itself.

After extracting the retained source over the checkpoint:

```sh
cargo run --release --locked -p mhd-vector-pot --example paper-shock-audit -- results/fresh_faces
python3 scripts/run_paper_geometry.py --output-dir results/fresh_geometry
```

The geometry runner records numerical failures and does not award acceptance;
it returns zero only for complete recording with unchanged source/binary.
Inspect `summary.json` and `runs.json`: one failed evolution is expected.
Cases use at most three serial processes, each capped at 30 wall seconds.

To reproduce the rejected mixed-Hessian screen, instead overlay its exact
`raw/hessian/source.tar.gz` on a separate checkpoint checkout, then run:

```sh
python3 scripts/run_shock_repro.py --profile paper-hessian-v1 --output-dir results/fresh_hessian --trace-energy
```

That failed short screen correctly exits 1. The current retained CLI does
not offer the rejected profile. No gate, initial condition or registered
benchmark has been changed, and no long REANA workflow was restarted.

With `raw.tar.gz` extracted, regenerate the visually inspected figure using
Matplotlib (3.9.4 used here):

```sh
python3 scripts/plot_paper_coupling.py raw/faces raw/geometry raw/hessian --output paper_coupling_audit.png
```

Final checks: 127 release Rust tests across all targets, 41 Python tests,
formatting and strict Clippy pass. Checkpoint validation also passed 13 M0
algebra checks and pinned-reference integrity. All retained numerical Rust
files match the previous paper-audit source; only diagnostic examples are new.
Full M1 acceptance remains false. Issues #19–#22 remain open.
