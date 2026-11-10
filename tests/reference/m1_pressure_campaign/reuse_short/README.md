# Binary-reuse campaign: short-stage parity

The fresh `openmhd-m1-pressure-reuse-20261110.1` campaign passes all four
short stages: 51 completed evolutions and two expected literal-paper planar
pressure failures. All **471 raw artifacts** were downloaded and checked
against their current execution hashes. Every one of the **365 scientific
files matches the previous pressure-blend campaign byte for byte**; only
106 timing/log files differ. This is measured parity, not an inference from
unchanged Rust sources or a claim of identical executable bytes.

| Stage | Records | Result | Wall seconds, including driver/build |
| --- | ---: | --- | ---: |
| Short shock | 4 | Pass | 5.63 |
| Shock symmetry | 8 | Six complete; two literal-paper failures retained | 43.84 |
| Short waves | 21 | Pass | 75.15 |
| Quick physics | 20 | Pass | 86.23 |

The previous [scientific reductions and plot](../short/README.md) therefore
apply exactly to these scientific files, including the failed coarse N16
jittered mean-field diagnostic under the registered finest-quick-grid rule.
No failed diagnostic or literal-profile failure is relabelled as passing.
The medium, mean-field, calibration and full matrices require separate evidence.

Snapshot SHA256 is
`00d823cc61e3ebfca3c79645625e528bf45f59e0a94967f532d74cd52b56390b`.
The new binary SHA256 is
`90d40a752e357ed6a459e828d8a48cba51eed13549229271583f89fb7384a426`.
All 77 stage source dependencies match the frozen export and
[preflight manifest](../reuse_preflight/README.md). Both literal controls
retain their pressure-recovery failure in cell 253 near t=.00336336379.

To avoid storing duplicate science data, `metadata_and_runtime.tar.gz`
retains 20 new stage reports/configurations/logs plus all 106 changed
per-run timing/log files. The remaining 365 files are retained in the
hash-pinned preceding `short/measurements.tar.gz`. `raw_sha256.json` lists
all current raw artifacts; `members_sha256.json` covers the 126 new archive
members. The current run maps and gate summary digests bind the records to
this new execution. `verification.json` records the download, source and
parity checks. Reproduce the archive-only parity check from the repository:

```sh
python3 tests/reference/m1_pressure_campaign/reuse_short/verify_parity.py
```

This performs no evolution or numerical test. All tests/evolutions ran on
REANA, within 24 aggregate worker cores / 64 GB. M1 remains unaccepted.
