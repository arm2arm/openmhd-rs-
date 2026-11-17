# Passing focused pressure-weighted HLLD/HLL comparison (#24)

REANA `openmhd-m1-pressure-blend-20261110.2`, UUID
`976c4360-a91b-4a5c-842a-01c997ff82c5`, ran 2026-11-10
04:19:24–04:31:45 UTC (741 s). Snapshot SHA256
`85cbaf2025f591ee989c59a33c4c5db5b3a212ef7fe6dd5c95feb5649760ad89`.
All 24 evolutions complete. Format, strict Clippy, **163 release/all-target
Rust tests, 80 Python tests, 13 M0 algebra tests and independent reference
checks pass**. All tests/evolutions ran on REANA, with eight two-thread cases,
16-GB job memory and 600-second case limits. The preceding test-only Clippy
failure remains in `../pressure_blend_preflight`; no simulation ran there.

The [registered candidate](../../../../docs/M1_PRESSURE_BLEND_PLAN.md) uses
`--riemann hlld-pressure` / `hlld-pressure-blend-v1`. A minimum neighbouring
gas-pressure ratio cubed weights the full HLLD/HLL fluid and induction flux
vectors. Constant pressure retains HLLD. This is our explicitly documented
MHD/Voronoi extension of a published scalar sensor, not HLLC-ADC or an AREPO
algorithm. The exponent is not tuned. No floor, reset, imposed row symmetry
or acceptance-threshold change is introduced. Numerical implementation is
committed as `144ac35`; the frozen export records actual parent `c0265ee`
and its then-uncommitted changes separately from the private export fixture.

| Measurement | HLLD control | Global HLL | Pressure blend | Unchanged gate |
| --- | ---: | ---: | ---: | ---: |
| Column shock maximum boost L1 | 5.81839e-6 | 9.58953e-14 | **6.04941e-14** | 1e-8 |
| Regular shock maximum boost L1 | 5.70035e-11 | 6.83614e-13 | **5.61954e-14** | 1e-8 |
| Regular N32 vortex normalized div B RMS | .0683461 | .385293 | **.0684606** | .1 |
| Jitter N32 vortex normalized div B RMS | .0825589 | .0592202 | **.0730138** | .1 |
| Jitter vortex normalized mean-B drift | .000606654 | .000350006 | **.000430755** | .001 |
| Column base final row-to-row vx range | .00168008 | 1.27701e-12 | **1.87642e-12** | diagnostic |

All eight candidate runs and four boost pairs pass their focused checks.
Across the eight histories, minimum density is .102394764, minimum pressure
.043215232 and maximum normalized conservative-budget residual 2.87329e-14.
Shock Bx errors remain below 1.04e-14; all seam-isolation checks pass.
Column-base finest scaled reference L1 errors are rho .00236412, pressure
.00247511, vx .00504441 and By .00332921, below .03/.04/.03/.04 respectively.
Some profile errors increase relative to HLLD; this remedy has a measured
diffusion cost. N32 vortex reference errors are diagnostics, not substitutes
for the full N64/128/256 comparison.

All **96 historical HLLD/HLL scientific files reproduce byte for byte**.
The known HLLD column boost and global-HLL regular vortex failures remain
visible. The new frozen slow-shock audit has minimum omega .108407 on the
column mesh and modifies the normal-face mass flux by up to .0112115 in
rest-frame x=[1.05,1.25]. It measures the actual final-state flux comparison,
not cumulative activation or a proof of the single instability mechanism.

All 321 frozen source files, upload hashes and 224 final output artifacts
verify. `sources.tar.gz` preserves 169 executable/configuration files and
`science.tar.gz` all 214 scientific artifacts, including raw initial/final
states and face observations. `scripts/plot_shock_sensor_probe.py` verifies
the archive and independently reduces all 12 boost pairs, all shock row
ranges and the vortex divergence norms. The stored divergence operator values
are not independently reconstructed. The [inspected plot](../../../../docs/images/m1_completion/pressure_blend_comparison.png)
and `independent_reduction.json` record that distinction.

This is a **focused pass, not full M1 acceptance**. Continue the unchanged
five-stage bounded gate, mean-field ladder, calibration, full physics and
wave/loop/temporal matrices via `m1-pressure-campaign`. Only that complete
evidence plus the final review can close M1. Original paper-profile failures
remain preserved, and no paper-level or general Galilean equivalence follows.
