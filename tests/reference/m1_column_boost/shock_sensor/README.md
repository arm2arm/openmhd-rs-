# Failed shock-only HLLD correction (#24)

REANA `openmhd-m1-shock-sensor-20261110.1`, UUID
`443effc9-4179-46ba-97d0-e27ca17e21c2`, completed 2026-11-10
03:47:25–04:00:01 UTC (756 s). All 24 evolutions finish. Format, strict
Clippy, 156 release/all-target Rust tests, 78 Python tests, 13 M0 algebra
tests and independent reference checks pass. Eight two-thread workers,
16-GB memory and 600-second case limits; all tests/evolutions ran on REANA.

The implementation follows the [prospective plan](../../../../docs/M1_SHOCK_SENSOR_PLAN.md):
Minoshima–Miyoshi's shock-only contact-speed correction, ordinary symmetric
intermediate pressure, fixed exponent four and an explicitly labelled Voronoi
sensor extension. This is not full LHLLD or a paper-equivalence claim.
`--riemann hlld-shock` records `hlld-shock-sensor-v1`.

| Measurement | HLLD | HLL | Shock-only HLLD | Gate |
| --- | ---: | ---: | ---: | ---: |
| Column shock maximum boost L1 | 5.81839e-6 | 9.58953e-14 | **7.50395e-6** | 1e-8 |
| Regular shock maximum boost L1 | 5.70035e-11 | 6.83614e-13 | 5.42272e-11 | 1e-8 |
| Regular N32 vortex normalized div B RMS | .0683461 | **.385293** | .0684859 | .1 |
| Jitter N32 vortex normalized div B RMS | .0825589 | .0592202 | .0888917 | .1 |
| Column base final row-to-row vx range | .00168008 | 1.27701e-12 | .00266470 | diagnostic |

All new cases pass positivity, conservative budgets and their reference/Bx/seam
or vortex mean-field/divergence checks. The column shock boost fails, so
`candidate_bounded_pass=false`. The wrapper's completed status denotes
execution only. No long validation matrix was started for this candidate.

The correction is active: in the column base slow-shock window, transverse
faces reach theta=.577591 and mass-flux changes reach 1.83661e-5; normal
faces remain near theta=1. Row differences persist. This rules out a wholly
inactive correction, not every possible cause of instability. Do not tune
the exponent against this result. The initial report's slow-shock window used
absolute x, so its boosted-window observations sample a different location.
`independent_reduction.json` corrects that observational window to
`(x-boost_x*time) mod 2`; no evolution or gate calculation is affected.

All **96 historical HLLD/HLL scientific files are byte-identical**. All 315
frozen source files, upload hashes and 224 output artifacts verify.
`sources.tar.gz` retains 164 executable/configuration files;
`science.tar.gz` retains all 214 scientific artifacts, including raw initial,
final, geometry, history and frozen face CSVs. The snapshot manifest records
the actual parent 8f48a08 and separate private source-export fixture.

`scripts/plot_shock_sensor_probe.py` verifies the archive and independently
reduces all 12 boost pairs, all final shock row ranges and vortex divergence
norms. The divergence values themselves are stored operator outputs, not a
new independent face reconstruction. [Comparison plot](../../../../docs/images/m1_completion/shock_sensor_comparison.png).
M0 remains accepted; M1/#24 remain open. The next bounded hypothesis is
the separately [registered pressure-weighted blend](../../../../docs/M1_PRESSURE_BLEND_PLAN.md).
