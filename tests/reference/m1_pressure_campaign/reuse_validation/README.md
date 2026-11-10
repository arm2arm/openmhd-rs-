# Binary-reuse campaign: bounded and mean-field gates pass

Workflow `openmhd-m1-pressure-reuse-20261110.1`, UUID
`7a615758-c141-4903-a2ea-8da3094ddd58`, passes all five bounded stages
and the complete 24-run nonzero-mean-field ladder. The N128 calibration
starts at 06:09:08 UTC on 2026-11-10 and remains running at this checkpoint.
The full physical matrices have not started. **Full M1 is not accepted.**

The candidate remains `bulk-frame-heun-quadratic-v1` with accelerated
projection, screening 1 and explicit `hlld-pressure`. Snapshot SHA256 is
`00d823cc61e3ebfca3c79645625e528bf45f59e0a94967f532d74cd52b56390b`;
the actual source parent is `4f491de`. The executable SHA256 is
`90d40a752e357ed6a459e828d8a48cba51eed13549229271583f89fb7384a426`.
Every Rust/Cargo input is unchanged from the preceding pressure campaign;
the execution correction and tests are documented in the
[new preflight archive](../reuse_preflight/README.md).

| Completed stage | Evidence | Result |
| --- | --- | --- |
| Four short stages | [471 verified raw files](../reuse_short/README.md) | 51 evolutions complete; two expected literal-paper pressure failures retained |
| Medium N32/64, t=1 | 48 evolutions, 384 verified raw files | All 16 Alfvén and eight loop boost pairs pass |
| Mean-field ladder | 24 evolutions, 168 verified raw files | All 12 boost pairs and four candidate refinement rows pass |

The complete bounded stage takes 1308.14 s, including medium 1096.51 s.
The mean ladder takes 14.87 s using the explicitly verified prebuilt binary.
All tests/evolutions run on REANA, within 24 aggregate worker cores / 64 GB.
Local work only verifies, reduces and archives returned data.

## Independent measurements and exact reproduction

The new medium and mean raw snapshots reproduce **all 288 and 120 scientific
files** from the preceding pressure campaign byte for byte. Only timing/log
files differ. Together with short-stage parity this is **773 identical
scientific files among 1023 individually downloaded, hash-verified artifacts**.
Source and binary checks are recorded separately; cross-workflow executable
byte identity is not claimed.

The archived NumPy reductions recompute all 24 medium and 12 mean-field
comparisons directly from the new final snapshots:

| Quantity | Maximum | Unchanged limit |
| --- | ---: | ---: |
| Medium Alfvén normalized boost L1 | 2.36822135e-12 | 1e-8 under both recorded conventions |
| Medium loop relative magnetic L1 | 2.63445009e-8 | .001 |
| Mean-field transformed component error | 1.04360964e-14 | 1e-9 |

The preceding [medium figure and numerical interpretation](../README.md#complete-bounded-gate-and-medium-measurements)
apply to these identical scientific files. The largest loop residual and
different accepted-step counts remain a
[recorded observation](../loop_followup/README.md), not a demonstrated cause.
The coarse N32→N64 wave orders, 1.565–1.769, do not establish the required
fine-grid convergence. Negative fitted orders for roundoff-level mean-field
boost residuals are not physical accuracy orders or new acceptance failures.

## Archived provenance

`bounded_gate.json` records all five passing stages, unchanged source/binary
and the satisfied full-matrix precondition. `bounded_sources.tar.gz`
matches its recorded archive digest; all **162 members** match both the
gate's source map and the frozen preflight snapshot.

`medium/` and `mean/` retain all exact compressed reports, run maps,
configurations and provenance, plus the **59 verified source dependencies**
of each driver. The medium archive also retains four standard snapshot
selections. The worst-loop pair's identical snapshots are preserved in the
preceding `medium/` archive. Every current raw file was verified before
compaction; full raw files also remain in this named REANA workspace and
the local `results/reana_remote_m1_pressure_reuse_20261110` download tree.

Each `reduce_pairs.py` accepts its corresponding raw phase directory and
writes `independent_pairs.json`; the report includes the reduction-source
hash and NumPy version. These commands perform no evolution or numerical
test. `verification.json` records source verification, raw counts and
cross-campaign parity. The subtree manifests and root `archive_sha256.json`
cover this archive.

`campaign_checkpoint.json` is an immutable **running** checkpoint containing
completed bounded and mean phases. It is not a final workflow-success record.
Calibration, memory-based allocation, the 30-run physics matrix, the 112-run
wave/loop/temporal matrix and final review remain required before M1 closure.
