# Opt-in projection screening controls (issue #21)

Bounded evidence for `--projection-screening kappa` on the quadratic projected
candidate. kappa=1 reduces the planar-jitter Brio Bx L1 error by 31-39% and
halves the nx256 t=.1 maximum (.0650 -> .0340), with unchanged short Alfven
convergence orders, boost checks and positivity. It does not make Bx exact,
is default off, and is not M1 acceptance.

See the [diagnosis and results](../../../docs/M1_SHOCK_INVESTIGATION.md#measured-bx-growth-and-opt-in-projection-screening-2026-11-09-issue-21).

- `analysis.json`: shock table, wave errors/orders, boost pairs, per-kappa verdicts.
- `raw.tar.gz` (SHA256 `a2e96e16ef06fb0cb03db44f08e4a5c5bdf2dcec25192a0df2e174c00814df7f`):
  all 44 runs with manifest, provenance (source and binary hashes, rustc,
  30-second cap), `source.tar.gz`, commands, logs, histories and snapshots.

Runs were made on revision `4dfeb19` plus the then-uncommitted screening
change; the archived `source.tar.gz` is the exact source. Binary SHA256
`a61c4064b0b891986a278be478e3182b00dba17b604346c10cf05dba93d4df8c`. f64,
periodic, mu0=1, CFL .3, one thread per case, no floors, resets or resistivity.
The kappa=3/10 failures quoted in the investigation were exploratory
unaccelerated runs and are not in this archive.

```sh
python3 scripts/run_projection_screening.py --output-dir results/fresh_screening
cd scripts && python3 -m unittest test_projection_screening
cargo test --release -p mhd-vector-pot --lib screening
```
