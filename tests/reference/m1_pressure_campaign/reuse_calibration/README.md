# Pressure-blend N128 calibration

The two N128 jittered travelling waves complete and pass their calibration
checks on `openmhd-m1-pressure-reuse-20261110.1`, UUID
`7a615758-c141-4903-a2ea-8da3094ddd58`. The vortex remains running at this
checkpoint. **Calibration as a whole and full M1 remain unaccepted.**

The frozen source and complete preflight are retained in
[reuse_preflight](../reuse_preflight/README.md). Candidate settings are
`bulk-frame-heun-quadratic-v1 --accelerated-projection --projection-screening 1
--riemann hlld-pressure`. Both drivers explicitly reuse executable SHA256
`90d40a752e357ed6a459e828d8a48cba51eed13549229271583f89fb7384a426`.
The wave driver's final provenance confirms that digest and records no Cargo
build. All tests/evolutions run on REANA; local work is archival verification
and postprocessing only.

## Completed wave pair

Both waves use N128, jitter .15, t=1, gamma=5/3, transverse amplitude .1,
mean B=(1,0,0), f64 and dimensionless permeability one on a periodic unit
square. The base mesh is fixed; the joint boost (2,-1,0) also translates
the boosted mesh. Each case uses eight threads; the concurrent vortex uses
eight more, within the 24-core / 64-GB limit.

| Frame | Wall seconds | Relative B L1 | Minimum density | Minimum pressure | Maximum normalized budget |
| --- | ---: | ---: | ---: | ---: | ---: |
| Base | 1710.13 | .003164205891 | .9983741312 | .09994094477 | 8.74720e-15 |
| Boosted | 1894.93 | .003164205891 | .9983741312 | .09994094477 | 1.26689e-14 |

History minima and budgets include the initial, t=.25 and final outputs.
Accepted states also pass the solver's conservative/curl positivity recovery.
Both runs record 3667 accepted steps, 2695 CFL retries, zero state rejections,
74 accepted HLL fallbacks and 111 attempted fallbacks. Intentional pressure
blends are recorded separately from invalid-HLLD fallbacks.

The independent NumPy reduction of the hash-verified final CSVs gives maximum
normalized boost L1 **2.74698759e-14**, below 1e-8 under both recorded
conventions. The relative magnetic amplitude-error limit .02 and budget limit
1e-10 also pass. This is one calibration pair, not a full invariance claim.

The matching N64 magnetic relative L1 is .01134162001. Its N64→N128 order
is **1.841711** in both frames. The required finest-three N64/128/256 fit
for all eight wave families remains pending. The retained orthogonal mode
analysis verifies all six raw snapshots and closes the error decomposition:
the final base phase error is -.002721070 radians and accounts for 72.36%
of squared magnetic error. This identifies an error component, not its cause.

The Linux measurement wrapper reports **667,435,008 bytes** peak process
RSS and 1896.65 seconds for the two-wave driver. This is the largest process
RSS, not the simultaneous memory sum or a measured N256 memory requirement.
The final worker allocation awaits the vortex's completed measurement.

## Provenance and reproduction

All **16 raw artifacts** and every wave execution source/result hash verify
against the frozen export. `wave/` retains exact compressed reports,
configurations, execution sources and provenance. `reduce_pairs.py` in that
directory accepts the raw wave phase directory and recomputes the boost
comparison. `wave_checks.json` records the physical measurements and scope.
`wave_modes.json.gz` retains the six snapshot hashes, decomposition closure
and `scripts/analyze_alfven_modes.py` source hash. The original memory record
and stage log are retained alongside them.

`campaign_checkpoint.json` is a running checkpoint with completed bounded,
mean and wave-calibration phases. It is not a final workflow-success record.
The vortex, full physics/wave matrices and final review remain required;
no issue is closed by the wave pair alone.
