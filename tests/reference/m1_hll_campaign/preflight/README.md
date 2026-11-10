# HLL campaign preflight evidence

All eight preflight commands pass on REANA workflow
`openmhd-m1-hll-campaign-20261110.1`, UUID
`f32fda39-1696-4fe2-8950-54e4ec10fd55`, started 2026-11-10 03:06:16 UTC.
The scientific campaign remains active at this archive checkpoint; these
checks do not establish full M1 acceptance.

| Check | Result |
| --- | --- |
| `cargo fmt --check` | Pass |
| Strict Clippy, all targets/features | Pass |
| Debug workspace Rust tests | 139 pass |
| Locked release workspace build | Pass |
| Python discovery, including flux-provenance regressions | 76 pass |
| M0 algebra | 13 pass |
| M0 independent reference packet | Pass |
| Release/all-target workspace Rust tests | 148 pass |

The Python log includes an intentional mocked `shock_short fail` from the
regression that verifies a failed short stage prevents medium runs. Its test
passes; it is not a physical evolution or the campaign's shock-stage result.
Raw logs retain their original whitespace and checksums.

The immutable snapshot SHA256 is
`cf55c78de31a305bb06f0059e7a347cfe5c6563bcfcf64bba023b64932a067b4`.
Its actual source parent is `8d53b79`; the private export revision in
`snapshot.json` is only a build/provenance fixture. All **307 frozen source
files** and all upload part hashes were verified before archiving. The Rust
numerical source is unchanged from the passing
[bounded HLL comparison](../../m1_column_boost/hll_comparator/README.md).
The new runner changes propagate explicit HLL and reject inconsistent flux
metadata. The default and literal-paper symmetry controls retain HLLD.

`sources.tar.gz` contains 163 exact source/configuration files, including the
prospective full-validation plan. The complete frozen file manifest is
retained in `snapshot.json`; existing independent reference data remain at
their recorded repository paths. Four working documentation files were
updated after submission; no executable or numerical source differed from
the packet at the preflight checkpoint.

Every archived check log matches the hash recorded in
`execution_checkpoint.json`. That report is an immutable **running** snapshot,
not a final workflow-success record. Runtime and snapshot identities also
verify. `sha256.json` covers the preserved input/output artifacts;
`verification.json` records the independent local hash/count reduction.
Local work only archived and checked returned evidence: all tests and
evolutions ran on REANA. The run cgroup reports 64,000,000,000 bytes and
24 visible CPUs; the runners cap aggregate case threads at 24.

The unchanged bounded, mean-field, calibration, full physics and full
wave/loop/temporal gates are recorded separately as they complete. No issue
is closed by this preflight archive.
