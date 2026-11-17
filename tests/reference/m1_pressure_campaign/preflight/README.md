# Pressure-blend campaign preflight evidence

All eight preflight commands pass on REANA workflow
`openmhd-m1-pressure-campaign-20261110.1`, UUID
`b04502aa-c906-4efa-9333-7f2649a28757`, started 2026-11-10 04:39:05 UTC.
The scientific campaign starts at 04:51:22 UTC and remains active at this
checkpoint. These checks do not establish full M1 acceptance.

| Check | Result |
| --- | --- |
| `cargo fmt --check` | Pass |
| Strict Clippy, all targets/features | Pass |
| Debug workspace Rust tests | 154 pass |
| Locked release workspace build | Pass |
| Python discovery, including candidate configuration and campaign gates | 80 pass |
| M0 algebra | 13 pass |
| M0 independent reference packet | Pass |
| Release/all-target workspace Rust tests | 163 pass |

The Python log includes an intentional mocked `shock_short fail` from the
test that verifies a failed short stage prevents medium runs. Its test passes;
it is not a physical evolution or a result from this campaign's shock stage.
Raw logs retain their original whitespace and checksums.

The immutable snapshot SHA256 is
`de65afe4f1920ec3a6db0535f904d48112227ce1fc57324fe604b3fbaf8b5c95`.
The actual source parent is `d1127f2`; the private export revision in
`snapshot.json` is a build/provenance fixture. All **321 frozen source files**,
upload part hashes and the workflow hash verify. Every Rust source and Cargo
input is unchanged from the passing
[focused pressure-blend comparison](../../m1_column_boost/pressure_blend/README.md).
Only documentation, a plotting script and the minimal-export exclusion list
differ from that focused snapshot. The default and literal-paper controls
retain HLLD; the new candidate explicitly selects `hlld-pressure`.

`sources.tar.gz` preserves 175 exact source/configuration files, including
the prospective full-validation plan. `snapshot.json` retains the complete
frozen manifest; existing independent reference data remain at their recorded
repository paths. All eight check logs match `execution_checkpoint.json`,
and runtime/snapshot identities also verify. `sha256.json` covers the archived
artifacts; `verification.json` records the independent hash/count reduction.

The execution checkpoint is an immutable **running** snapshot, not a final
workflow-success record. All tests and evolutions ran on REANA; local work
only archived and reduced returned evidence. The run cgroup reports
64,000,000,000 bytes and 24 visible CPUs; the runners cap aggregate case threads
at 24. Bounded, mean-field, calibration, full physics and wave/loop/temporal
results are recorded separately as they complete. No issue is closed by this
preflight archive.
