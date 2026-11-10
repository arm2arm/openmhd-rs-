# Uniform-state response control for #24

REANA `openmhd-m1-transverse-symbol-20261110.1`, UUID
`8e21b7ea-c053-41a6-9461-25286b170419`, finished 2026-11-10 02:24:18 UTC
(425 seconds including environment preparation and checks). The 96 no-evolution
probes each take 0.18–0.62 seconds. Format, strict Clippy, 146 release/all-target
Rust tests, 72 Python tests, M0 algebra and pinned-reference checks pass.

All 204 output artifacts and all 303 frozen input files were hash verified.
The archive includes all 96 raw coefficient CSVs, the full numerical report,
153 Rust/Python/Cargo/runtime source files, workflow/runtime records and checks.
The snapshot digest is
`6a70c0c542ae41773d9d49adc53460b9238119972a727df8a33cfe08335e373c`.
`source_revision` is the actual parent 1ced401; `revision` is a private export.

The probe uses the screened quadratic candidate with **unlimited reconstruction**
on regular [.125,.125] meshes, ny=4, nx=16/32/64 (dy/dx=4/8/16), gamma=2,
and periodic boundaries. Inputs are rho, vx, vy, p and kx*Az in both phases;
x modes are below Nyquist, y mode is zero or alternating. Central perturbations
1e-6 and 1e-7 measure amplitude dependence. The manufactured downstream state
is rho=.235, p=.512, v=[.592,-1.579,0], mean B=[.75,-.535,0]; it is deliberately
rounded, not an exact reference solution. Stationary magnetic and nonmagnetic
controls are included. Source and report specify every configuration.

**No resolved growing eigenmode is found for the screened candidate in this
sample.** The largest real eigenvalue is 4.73e-8 in a stationary neutral mode;
all moving downstream cases are damped. Maximum relative Fourier leakage is
8.23e-8; maximum relative matrix change between perturbation sizes is 3.70e-7.
The uniform reference RHS is at most 1.18e-11. Thus this test does not support
blaming the observed shock growth on a uniform-state eigenmode alone.

The diagnostic response with the projection removed has stationary short-mode
growth up to 1.12469 per time unit. It uses the same fluid response and is not
a separately evolved or accepted algorithm. The sign reversal of the quadratic
first-derivative symbol therefore remains a property to test, not a sufficient
explanation of the screened shock failure. No production correction is made.
These uniform unlimited matrices cannot establish stability of a limited,
spatially varying, time-dependent shock. M1 and #24 remain open.
