# Paper-source and symmetry audit

The user requested returning to the Springel–Mayer–Pakmor formalism.
`paper-state-emf-v1` isolates the literal Eq. (69) Riemann-state product in
both endpoint stages. This profile retains the linear cell curl, original
gauge and the existing auxiliary/endpoint engineering policies. It changes
neither the default nor historical profiles. The independent face-integral
prototype was removed from the library, with its source preserved here.

The new profile's two regular short shocks complete t=.01, but both jittered
shocks fail at t=.00334288704. The matched default fails at t=.00336336379.
Both failures occur in cell 253. The literal source does **not** fix the
conservative-energy/curl pressure mismatch. Both short screens correctly
return exit status 1; full M1 acceptance and merging remain unapproved by
the numerical gates. No long REANA jobs were restarted.

The rank audit exports exact effective affine/quadratic derivative matrices
for regular/jittered nx16/32/64/256, ny4 meshes. Removing the constant gauge
leaves full numerical rank for the tested jittered normal derivatives. The
nx256 x-normal bounds imply transverse RMS below .000304977 (affine) or
.00757527 (quadratic) if maximum normal-field error is below 1e-8. This is
numerical evidence of a representation/gate conflict, not an interval proof,
an AREPO equivalence result or permission to change the gate. The paper does
not establish machine-small Bx for this project's jitter family.

See the [source audit and measurements](../../../docs/M1_SHOCK_INVESTIGATION.md#paper-source-comparison-measured-result).

## Archive contents

- `retained_source.tar.gz`: final working source, tests, scripts and context.
- `retained_source_sha256.json`: hashes of each source archive member.
- `raw.tar.gz`: both short screens with full energy traces and their exact
  source snapshots, exported derivative matrices, initial/rerun SVD reports,
  historical parity outputs, and validation logs.
- `raw/paused_face_source.tar.gz` inside the raw archive: the removed
  face-integral prototype, with its matching source hashes and two-test log.
  It had no coupled evolution and is not part of the retained library.
- `verification.json`: actual checks and remaining failures.
- `raw_sha256.json`: hashes of all raw archive files.
- `archive.json`: hashes of top-level files except itself.

The initial rank report used NumPy's BLAS matrix products, which emitted
floating-point warnings despite finite outputs. `rank_checked.json` is the
retained rerun using explicit `einsum` contractions under raise-on-warning
handling, with finite-value, gauge and backward-residual checks. The two
reports agree on ranks and bounds. Both logs are preserved.

Verification passes: 127 release Rust tests across all targets, 41 Python
tests, 13 M0 algebra checks, pinned-reference integrity, formatting and strict
all-target/all-feature Clippy. Ten historical boosted wave/loop cases retain
byte-identical physical outputs. These checks are not physical acceptance.

## Reproduction

Start with a separate checkout at the base revision recorded in
`verification.json`, then extract `retained_source.tar.gz` over it. That base
revision alone does not contain these uncommitted changes. To reproduce an
exact short-screen source version, use that screen's `source.tar.gz` from
the raw archive instead; do not mix overlays.

```sh
cargo test --release --locked -p mhd-vector-pot --test paper_source
python3 scripts/run_shock_repro.py --profile paper-state-emf-v1 --output-dir results/fresh_paper --trace-energy
python3 scripts/run_shock_repro.py --profile paper-global-v2 --output-dir results/fresh_default --trace-energy
cargo run --release --locked -p mhd-vector-pot --example symmetry-rank-probe -- results/fresh_matrices
OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 OMP_NUM_THREADS=1 python3 scripts/check_symmetry_rank.py results/fresh_matrices --output results/fresh_rank.json
```

The rank checker requires NumPy. Each shock screen uses four serial workers
with a 30-second cap per case. Use fresh output paths. The failed shock
commands are expected to return 1; run each separately if using a shell
that stops on failure. No command above submits remote work.
