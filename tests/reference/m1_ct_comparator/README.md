# Complete fixed/rigid CT comparator: rejected as an M1 repair

The [report](../../../docs/M1_CT_COMPARATOR.md) defines the source equations,
explicit deviations and prospective bounded screens. `analysis.json` records
30/32 completed controls, two late pressure failures, failed jittered Bx and
wave-order screens, and 11 passing complete boost pairs. `full_m1_accepted`
is false. One additional nx256 repetition records the frozen failure audit.
No long simulation or REANA job was submitted.

`raw.tar.gz` contains 340 regular files (4,786,558 compressed bytes):

- `controls/`: all 32 commands, stdout/stderr, summaries, initial/final physical
  snapshots, frozen initial energy rates, accepted-step diagnostics, analysis,
  execution records and machine/compiler provenance. Failed runs retain their
  final accepted state; no fabricated snapshot at the requested target.
- `controls/source/` and `source_manifest.json`: exact source used for these
  simulations, including the new module/CLI and preregistered contract.
  Base Git revision is `570303f`; the working-tree patch alone is not the full
  source because new files were untracked at execution. Use the saved source
  overlay and hashes. No public AREPO or Athena implementation is imported.
- `audit/`: nx256 initial and last-accepted face fluxes, geometry, field/pressure
  rates, integer topology checks, independent NumPy/SVD field recovery, and
  failed-step immutability. Its physical output matches the primary base run.
- `audit_source/`: exact diagnostic example and independent/plot/test scripts
  added after the primary packet; simulation source is unchanged.
- `checks/`: actual debug/release Rust logs and verification record.

`archive.json` hashes the compressed archive; `raw_manifest.json` hashes every
member. Verify those before extracting. Every member is a relative regular
file; reject absolute paths, `..` components and links. Extract to a fresh
directory, then, from a checkout containing this experiment:

```sh
python3 scripts/run_ct_controls.py --analyze-only --output-dir /tmp/ct-extracted/controls
python3 scripts/check_ct_audit.py /tmp/ct-extracted/audit
python3 scripts/plot_ct_controls.py /tmp/ct-extracted/controls --output /tmp/ct.png
```

The first command is standard-library only. The audit requires NumPy; the
figure requires Matplotlib. Fresh extraction/reanalysis reproduces both
JSON analyses byte for byte in the recorded environment. The archived
NumPy/SVD recovery agrees within 1.45e-15, and integer incidence is exact.

Verification: 135 debug workspace tests and 143 release all-target tests;
44 Python and 13 M0 checks; format, strict all-feature Clippy and pinned
reference integrity pass. The original solver modules are unchanged.

The Bx gate remains 1e-8, the short wave-order screen remains 1.8, and the
full M1 physical matrix remains unpassed. Do not use successful execution
or CT flux divergence alone as evidence of positivity or physical acceptance.
