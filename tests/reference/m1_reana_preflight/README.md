# REANA preflight, 2026-11-09

Workflow `openmhd-m1-campaign-20261109.1`, UUID
`0909f51a-f9db-4190-b545-18b9d5318210`, ran on the pinned image and Rust
1.85.1. Snapshot SHA256:
`29e467e6a0af19cc2afd59701c7132e9f813d71bdaae704bef13bdccafcd828d`.

Format, strict Clippy, 133 debug Rust tests, release build, 61 Python tests,
M0 algebra/reference checks and 141 release/all-target Rust tests passed.
The numerical campaign then failed immediately because `/usr/bin/time`
was absent; no numerical phase ran. The overall workflow remains **failed**.

`execution.json` records commands, exit codes, timings, log hashes and the
actual run-tests cgroup: 64,000,000,000 bytes, 24 visible CPUs. The separate
`runtime.json` describes the preparation job, whose memory cap is 8 GiB.
All nine command log hashes were independently verified after download.

This compact export includes logs and the complete source/upload hash map,
not the large source bundle or raw input archives. The immutable original
inputs and workspace remain in REANA and the local submission directory
`results/reana_submission_m1_campaign_20261109_v5`. They include uncommitted
orchestration changes over `3cbd1d5`; later changes in `9c14da2` (portable
memory wrapper and cache benchmark) were not executed in this preflight.
Do not attribute this preflight to the later cached-diagonal solver.
