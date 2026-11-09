# Coupled conservative pressure guard: bounded evidence

The [report](../../../docs/M1_CT_POSITIVITY.md) defines the prospective
algorithm and records the remaining physical failures. All 42 new controls
complete and all 17 boost pairs pass. The original CT pressure crash is
avoided without resetting energy; jittered Bx and wave-order gates remain
failed. Timestep refinement approaches the pressure boundary. This is not
M1 acceptance or a general positivity theorem.

`raw.tar.gz` contains 564 regular files (10,500,706 compressed bytes), with
member hashes in `raw_manifest.json` and archive hash in `archive.json`:

- `primary/`: 32 control commands, execution/analysis records, snapshots,
  accepted diagnostics, frozen initial rates, exact source overlay and hashes.
- `extended/`: ten additional timestep-cap and t=.04 controls with their own
  exact source overlay, prospective contract and provenance.
- `frozen/`: original CT failure repeated using the final numerical source,
  three frozen rate constructions and nine Euler probes per snapshot. The
  final numerical source is byte-identical to both retained Rust overlays.
- `pre_limiter_probe/`: the earlier frozen measurements that motivated the
  limiter, before its implementation. Every file is reproduced byte for byte
  by `frozen/`; the intermediate source was not separately snapshotted. Use
  the retained final source for the verified reproduction, not an inferred
  intermediate revision. Two frozen repetitions plus 42 controls = 44 new
  evolutions, all short.
- `baseline/` and `old_frozen/`: 54 selected historical files from the original
  [CT archive](../m1_ct_comparator/README.md), verified against its manifest.
  These are reused evidence, not new runs. All 16 wave initial/final physical
  CSVs and accepted histories are byte-identical with the limiter inactive.
- `analysis_source/`: exact final analysis/plot/runner scripts and report;
  runner changes after primary execution add the extended packet and a
  profile-provenance check, without altering the numerical code.
- `checks/`: actual Rust/Python/M0/Clippy logs and verification metadata.

The base revision is `542017e`. The retained overlays include uncommitted
source as executed; a Git patch alone is insufficient to reproduce new
files. No external AREPO/Athena implementation is imported.

Verify archive/member hashes before extraction and reject absolute paths,
`..` components and non-regular members. Extract to a fresh directory, then:

```sh
python3 scripts/run_ct_controls.py --analyze-only --output-dir /tmp/ct-positive/primary
python3 scripts/run_ct_controls.py --analyze-only --output-dir /tmp/ct-positive/extended
python3 scripts/analyze_ct_positivity.py --primary /tmp/ct-positive/primary --extended /tmp/ct-positive/extended --frozen /tmp/ct-positive/frozen --baseline /tmp/ct-positive/baseline --old-frozen /tmp/ct-positive/old_frozen --output /tmp/ct-positive/analysis.json
python3 scripts/plot_ct_positivity.py --analysis /tmp/ct-positive/analysis.json --extended /tmp/ct-positive/extended --baseline /tmp/ct-positive/baseline --output /tmp/ct-positive/plot.png
```

Analysis is standard-library only; plotting requires Matplotlib. Fresh
extraction reproduces the primary, extended and combined JSON analyses byte
for byte. The combined analysis is also published as `analysis.json` here.
Checks pass: 138 debug workspace / 146 release all-target Rust tests, 45
Python tests, 13 M0 tests, formatting, strict Clippy and pinned references.
The original solver profiles and all physical thresholds remain unchanged.
