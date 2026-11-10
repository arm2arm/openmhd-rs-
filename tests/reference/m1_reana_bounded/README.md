# REANA bounded and mean-field evidence (2026-11-10)

All five bounded stages pass for
`bulk-frame-heun-quadratic-v1 --accelerated-projection --projection-screening 1`.
The medium precondition is now measured. **Full M1 acceptance remains open**:
N128 calibration and the full shock/vortex/reference, wave/loop spatial and
physical temporal matrices are still required.

Workflow `openmhd-m1-reporting-campaign-20261110.1`, UUID
`01947a14-a507-4384-a4ca-9533395d08e8`; snapshot SHA256
`b102b766bc5b8e116811924f977e923e097c7ec3cf351647fae3bd2c8c46de04`.
Numerical source matches `9e99b74`. The [preflight/reporting packet](../m1_projection_metadata/README.md)
contains the full frozen upload manifest, 135 debug Rust / 143 release Rust /
66 Python test results, M0 checks and reporting parity. The running snapshot
is unchanged by later reporting-only development.

| Bounded stage | Outcome | Wall seconds |
| --- | --- | ---: |
| Short shock | Pass | 63.41 |
| Shock mesh-symmetry controls | Pass; two known default-profile planar failures retained | 43.30 |
| Short waves | Pass | 73.18 |
| Coarse shock/vortex | Pass under its preregistered finest-quick-grid rule | 86.43 |
| N32/64 waves and loops to t=1 | 48/48 complete; all state, budget and boost checks pass | 1061.49 |

There are 99 completed evolutions and two expected `paper-global-v2` pressure
failures in the five-stage gate. The latter remain failures of that profile;
they are expected negative controls, not positive physical validation.
Short stages use three serial workers, 120-second per-case caps; medium uses
up to 24 serial workers, 1800-second per-case caps. Physical settings and
thresholds are unchanged.

The medium packet has 16 passing Alfvén boost pairs under both normalization
conventions (largest normalized L1 difference 2.51759e-12, limit 1e-8), and
eight passing loop pairs (largest B-relative L1 3.84522e-14, limit 1e-3).
Minimum density is .997511, minimum pressure .0995617, and the largest
normalized conservative-budget residual is 4.44104e-14 (limit 1e-10).
All are periodic, dimensionless mu0=1, f64, gamma=5/3, fixed/rigid meshes.

**Convergence is not yet accepted.** The eight coarse N32→N64 B-error orders
are 1.565–1.769. The preregistered >=1.8 acceptance fit uses N64/128/256, so
these coarse orders are diagnostics and cannot satisfy that gate. The N64
relative B L1 errors are .01039–.01496; the finest-grid amplitude criterion
also remains tied to its registered ladder. See the
[medium plot](../../../docs/images/m1_completion/medium_screened_gate.png).

An [orthogonal error decomposition](wave_modes/README.md) checks all 96 raw
wave snapshots against the registered L2 norms. Phase contributes 65–84% of
the N64 fixed-mesh final squared magnetic error; much of the amplitude deficit
is present at initialization. This is a measured error component, not a proven
algorithmic cause or a replacement for the full L1 convergence gate.

The subsequent mean-field suite completes all 24 runs and passes all 12 boost
pairs. Maximum transformed primitive/energy-component difference is
1.06581e-14 (limit 1e-9); maximum normalized budget residual is 2.48670e-14.
The regular/jitter .15 nonuniform states use mean B=(.3,.2,.1), t=.02, spatial
N8/16/32/64 and N16 time caps .001/.0005/.00025.

**Known report omission:** the original `mean/summary.json.gz` contains no
candidate refinement rows because its profile loop only lists historical
profiles. Individual runs and pair errors are present. Preserve these bytes.
Commit `c6cda9d` corrects the rows and requires their presence; its two added
regressions pass in the separate 68-test [REANA reporting audit](mean_reporting_audit/README.md).
Only the refinement field changes in the corrected copy. No new physical
order threshold is assigned to roundoff-sensitive boost residuals.

All **480 raw files** of the medium and mean suites were independently
hash-verified before compaction; `archive_m1_completion.py` also verified
all source and result hashes. `medium/` retains four selected raw snapshot
cases; complete raw files remain in the named REANA workspace and local
`results/reana_remote_m1_reporting_campaign_20261110`. `mean/` keeps the full
numeric reports and provenance without snapshot selections. Each subpacket
has its own archive checksums and exact execution source.

`gate.json`, `execution_sources.tar.gz`, `short_measurements.tar.gz` and
`short_members_sha256.json` retain the five-stage verdict and the four short
stages' compact reports/manifests/provenance plus stage logs. Their result,
source and binary hashes verify against the frozen packet. Short raw snapshots
remain on REANA; they were not all independently downloaded in this archive.
The historical failed coarse N16 vortex diagnostics remain in the reports.
`campaign_checkpoint.json` records only the completed bounded/mean phases;
its running status is not a claim of full campaign success.

Regenerate the plot without evolving a simulation:

```sh
python3 scripts/plot_m1_medium.py tests/reference/m1_reana_bounded/medium/summary.json.gz docs/images/m1_completion/medium_screened_gate.png
```

The original execution commands, source/binary identities, initial conditions,
EOS, boundaries, mesh motion, projection settings and raw hashes are in the
per-stage provenance and manifests. No floor, energy reset or guessed
resistivity has been used.
