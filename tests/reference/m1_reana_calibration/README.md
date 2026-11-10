# REANA N128 calibration evidence (2026-11-10, issue #7)

**Both travelling-wave frames complete at t=1 and pass the wave-calibration
checks. The vortex calibration is still running; full M1 remains open.**
This packet is a completed wave subset, not a completed calibration campaign.

Workflow `openmhd-m1-reporting-campaign-20261110.1`, UUID
`01947a14-a507-4384-a4ca-9533395d08e8`, frozen snapshot SHA256
`b102b766bc5b8e116811924f977e923e097c7ec3cf351647fae3bd2c8c46de04`.
The [preflight packet](../m1_projection_metadata/README.md) retains the full
submission manifest. Numerical source matches `9e99b74`. The named profile is
`bulk-frame-heun-quadratic-v1 --accelerated-projection --projection-screening 1`;
this engineering comparator does not establish paper-algorithm equivalence.

Both cases use N128, deterministic jitter .15, v_parallel=0, gamma=5/3,
transverse amplitude .1, mean B=(1,0,0), f64, dimensionless mu0=1 and periodic
unit-square geometry. The base mesh is fixed. The joint boost (2,-1,0) also
translates the boosted mesh. There are eight Rayon threads per case; the
concurrent vortex uses eight more, within 24 total cores and 64 GB.

| Frame | Wall seconds | B L1 / .1 at t=1 | Minimum density | Minimum pressure | Maximum normalized budget residual |
| --- | ---: | ---: | ---: | ---: | ---: |
| Base | 1745.3674 | .0031641251423493 | .998326419247 | .0999406116933 | 4.87825e-15 |
| Boosted | 1915.2132 | .0031641251423534 | .998326419247 | .0999406116933 | 1.07617e-14 |

Minima/budget maxima above are over the recorded diagnostic history. Accepted
states also pass the solver's positive conservative/curl recovery. The largest
normalized boost L1 residual under either reported convention is
**2.69922e-14**, below the unchanged 1e-8 limit. The relative B amplitude-error
limit .02 and the 1e-10 budget limit pass. The local postprocessing record
`wave_checks.json` reproduces these checks from the original remote summary;
it does not change that summary or the running workflow.

The matching N64 medium case has relative B L1 .0113408097875. Its N64→N128
two-grid order is **1.841645**. This is useful finer-grid evidence, but the
registered fit requires N64/128/256 for all eight wave families. It is not yet
a full convergence pass. The same
[orthogonal mode analysis](../m1_reana_bounded/wave_modes/README.md) checks all
six N128 snapshots against their raw hashes and original L2 norms. At t=1,
the base phase error is -.002720975 radians, accounting for 72.36% of squared
B error. This identifies an error component, not its numerical cause.

The Linux `wait4` wrapper reports **667,623,424 bytes peak process RSS**,
1917.03 wall seconds and 6096.50 CPU seconds for the two-wave driver. RSS is
the largest individual process, not the sum of simultaneous processes. This
is a measured N128 cost; N256 resource estimates still require the larger of
the wave and vortex peaks. The full campaign reserves 8 GB and uses an 8×
N128 peak estimate per N256 worker. No N256 memory measurement is claimed.

All **14 raw wave artifacts**, the three result-file hashes, and every
execution source hash were verified by `archive_m1_completion.py` against
the frozen submission export. `wave/` retains the original compressed reports,
execution provenance, exact source and archive checksums. Raw snapshots remain
in the named REANA workspace and in local
`results/reana_remote_m1_reporting_campaign_20261110/source/results/reana_m1-campaign/calibration_wave`.
`wave_modes.json.gz` retains the derived observations and analysis source hash.
The memory JSON and stage log are original remote outputs.

No new evolutions or unit tests ran locally. Publishing these records changes
no numerical source, thresholds or frozen inputs. The supplemental mean-report
regressions still await their already-created REANA workflow after the main
compute campaign ends.
