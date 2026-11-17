# Binary-reuse campaign: preflight passes

All eight preflight commands pass on REANA workflow
`openmhd-m1-pressure-reuse-20261110.1`, UUID
`7a615758-c141-4903-a2ea-8da3094ddd58`, started 2026-11-10 05:35:42 UTC.
The scientific campaign starts at **05:47:05 UTC**. It is still running at
this checkpoint; preflight does not establish full M1 acceptance.

| Check | Result |
| --- | --- |
| Formatting and strict all-target/all-feature Clippy | Pass |
| Debug workspace Rust tests | 154 pass |
| Locked release workspace build | Pass |
| Python discovery | 85 pass |
| M0 algebra and independent reference packet | 13 algebra tests and reference checks pass |
| Release/all-target workspace Rust tests | 163 pass |

The five new Python regressions verify hash-checked executable reuse,
rejection of missing/wrong/malformed reuse, the original standalone build
command, calibration-failure propagation and real Linux descendant-process
cancellation. The intentional failed/cancelled mocked phases in `04.log`
are successful regression tests, not failed physical runs. A retained
ResourceWarning comes from the existing shock-sensor CSV reader; discovery
still completes with all tests passing.

Snapshot SHA256:
`00d823cc61e3ebfca3c79645625e528bf45f59e0a94967f532d74cd52b56390b`.
Actual source parent: **4f491de**. The private export revision is a provenance
fixture. All 323 frozen source hashes, upload parts and workflow hash verify.
All 70 Rust/Cargo inputs are unchanged from the preceding pressure campaign.
The newly built executable has its own recorded hash; cross-workflow binary
identity is not claimed. Numerical output parity is checked separately.

`sources.tar.gz` retains 177 exact executable/configuration/plan files.
All eight logs match `execution_checkpoint.json`; runtime and snapshot
digests also verify. `verification.json` records independently extracted
test counts and verification scope; `sha256.json` covers the archive.
The running execution checkpoint is not a final workflow-success record.

All tests run on REANA. Local work only verifies and archives their outputs.
The preparation container reports 8 GiB; the execution checkpoint reports
the requested **64,000,000,000-byte** memory limit and 24 visible CPUs.
Runners limit aggregate case threads to 24. Actual concurrent calibration,
including executable reuse by both drivers, and all full physical gates
remain required. Issue #25 stays open pending that execution evidence.
