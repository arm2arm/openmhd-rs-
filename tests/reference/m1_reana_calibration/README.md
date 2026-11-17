# REANA N128 calibration evidence (2026-11-10, issue #7)

**All three N128 calibration cases complete and pass their calibration checks.**
The campaign advanced to the full shock/vortex matrix, then stopped after
a [finest-column Brio boost failure](../m1_column_boost/README.md). Full M1
remains open; calibration is a precondition, not full physical acceptance.

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
translates the boosted mesh. There were eight Rayon threads per case; the
concurrent vortex used eight more, within 24 total cores and 64 GB.

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
is a measured N128 cost, not an N256 memory measurement.

## Vortex calibration

The fixed N128, jitter .15 Orszag–Tang case completes at t=.5 in **2574.25 s**
with no state rejections. Initial conditions, gamma=5/3, mean B=0, units and
periodic square are those of the unchanged M0 packet. Final raw minimum
density is .08585625 and pressure .02611223; normalized budgets stay below
5.51341e-15 at the recorded initial/final outputs.

| Registered diagnostic | Measured | Limit | Outcome |
| --- | ---: | ---: | --- |
| Mean-B drift / Bscale | .000137273745 | .001 | Pass |
| Limited-face dimensionless divergence RMS | .0361845124 | .1 | Pass |

The latter uses a shared face-normal field obtained from the arithmetic mean
of componentwise limited left/right reconstructions. Its signed face fluxes
are divided by cell volume. Per-cell dimensionless values are
`sqrt(V/pi) div(B) / (|B| + 1e-12 Bscale)`; the reported RMS is volume weighted.
This is distinct from the raw neighbour-LS and unreconstructed arithmetic-face
operators, both also retained in the diagnostics. It is not machine-zero
divergence inferred from the continuum identity.

Diagnostic reference comparisons use polygon-overlap projection onto the
registered 64² bins and the pinned Athena++ N512 reference:

| Field | Scaled bin L1 error |
| --- | ---: |
| Density | .0219337014 |
| Pressure | .0442154133 |
| Bx | .0377138106 |
| By | .0337360120 |

The [gas comparison](../../../docs/images/m1_completion/vortex_calibration_gas.png)
and [magnetic comparison](../../../docs/images/m1_completion/vortex_calibration_magnetic.png)
use identical candidate/reference color ranges and explicitly scaled error
maps. All four independently recalculated plot norms match the recorded
comparison. This jittered N128 case does not replace the regular N64/128/256
profile/refinement or the full boost/diagnostic matrix.

Vortex driver peak process RSS is **665,624,576 bytes**, wall time 2575.03 s,
CPU time 4215.41 s. The campaign therefore uses the larger wave peak and an
8× N256 estimate of 5,340,987,392 bytes per worker. With 8 GB reserved, it
selects **10 concurrent workers × two threads = 20 cores**, within the owner's
24-core / 64-GB cap. The estimate is conservative scheduling input; actual
N256 memory remains unmeasured. `campaign_checkpoint.json` records the four
completed phases and this allocation before the later stop. The historical
running label is not the authoritative workflow status.

All **24 raw artifacts** (14 wave, 10 vortex), the six result-file hashes, and every
execution source hash were verified by `archive_m1_completion.py` against
the frozen submission export. `wave/` and `vortex/` retain the original compressed reports,
execution provenance, exact source and archive checksums. Raw snapshots remain
in the named REANA workspace and in local
`results/reana_remote_m1_reporting_campaign_20261110/source/results/reana_m1-campaign/calibration_{wave,vortex}`.
`wave_modes.json.gz` retains the derived observations and analysis source hash.
The memory JSON and stage logs are original remote outputs. The original
`wave_checks.json` is a historical checkpoint before the vortex completed;
use `campaign_checkpoint.json` for the completed calibration verdicts.

Regenerate both vortex figures from the compact archive:

```sh
python3 scripts/plot_m1_vortex_calibration.py tests/reference/m1_reana_calibration/vortex docs/images/m1_completion
```

No new evolutions or unit tests ran locally. Publishing these records changes
no numerical source, thresholds or frozen inputs. The supplemental mean-report
audit subsequently passes all 68 Python tests on REANA; its original and
corrected reports are retained separately.
