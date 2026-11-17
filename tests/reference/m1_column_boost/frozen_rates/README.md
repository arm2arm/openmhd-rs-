# Immutable RHS decomposition for #24

REANA workflow `openmhd-m1-column-rates-20261110.1`, UUID
`658b9f65-b318-474c-a81a-71e2ef2da244`, finished at 2026-11-10 01:59:08 UTC.
Four original nx1024 regular/column base/boost cases complete in
143.11–174.09 seconds. **All 24 original scientific files and all 152
accepted-trace snapshot records remain identical.** No numerical evolution
term, timestep landing point or acceptance threshold changes.

Format, strict Clippy, **145 release/all-target Rust tests**, **70 Python tests**,
M0 algebra/reference and invalid snapshot-stride checks pass. The two new Rust
tests verify periodic face-group conservation/sum to production and uniform
rigid-state zero rates. The two Python tests cover transverse-mode selection
and cancellation of mass transport in physical acceleration.

`Simulation::frozen_rates()` reevaluates the production stage from immutable
state. Fluid exchanges are grouped by |nx| >= |ny| and its complement; on
these rectangular meshes those are exactly x-normal and y-normal faces.
All rates are per unit cell volume. Magnetic columns contain the curl of
the projected and unprojected A rates, plus the same rigid-frame FV target
used by production. These are observations, not alternative evolved states.

For each sampled four-row coefficient a, the report computes
`sum(V_column * a * a_dot) / sum(V_column * a²)`. This is an instantaneous
logarithmic growth measure on a nonlinear moving shock, **not an eigenvalue**.
Physical acceleration uses `(momentum_rate - vx * density_rate)/rho`.

Across all **77 observations** with max |vx mode| >= 1e-10, the y-normal face
contribution is negative: -100.330 to -83.335 per simulation-time unit. The
x-normal contribution varies strongly, between approximately -1341 and +1233.
Thus the measured transverse-face velocity contribution damps this mode;
the result does not support identifying that contribution as direct
anti-diffusion. The x-direction evolution and magnetic/fluid feedback need
further isolation. Comparing rates on the same state is not a counterfactual
evolution and does not prove which modification will stabilize the method.

The [inspected plot](../../../../docs/images/m1_completion/column_mode_rate_groups.png)
shows this distinction. Four compressed raw rate snapshots are retained and
hash checked; their corresponding physical snapshots are in `../accepted_trace`.
Independent NumPy DFT/acceleration reduction differs by at most 0.000339 in
relative growth units for the tiny regular modes and 1.80e-8 for columns.
The largest local sum-of-face-groups residual is 1.34e-13. Full numerical
error details are in `independent_fft.json`; this is not an independent review.

The source archive contains all 146 Python/Rust/Cargo/runtime files, verified
against the complete 298-file input manifest. Large pinned references and
documentation remain in the original immutable submission and REANA workspace.
`source_revision` is the real repository parent (`411d917`); `revision` is a
private source-export fixture. All full snapshots/rates remain on REANA.
Scientific acceptance stays false. The known boost gate is still failed.
