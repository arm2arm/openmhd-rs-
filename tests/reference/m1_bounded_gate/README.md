# Bounded screened-candidate gate (2026-11-09, issue #22)

All four short stages pass in 71.1 wall seconds including cached builds and
measurement. The 51 candidate/control evolutions complete; two additional
literal-profile planar shocks reproduce the known pressure failure. None
times out; the longest case including measurement takes 13.66 seconds.
The medium stage and full M1 matrix are not evaluated by this archive.

`gate.json` gives the configuration, checks, commands, stage durations and
source hashes. `raw.tar.gz` contains every stage manifest, run record, log,
snapshot and provenance file, including the failed literal controls and the
coarse vortex's failed diagnostics. `sha256.json` identifies the archive and
every member. The top-level `source.tar.gz` inside the raw archive is the
exact execution source: revision `3cbd1d5` plus the gate-runner fixes. Later
REANA orchestration changes are not part of these measurements.

Reproduce in a fresh checkout restored from that source archive:

```sh
python3 scripts/run_m1_bounded.py --output-dir results/fresh_bounded
python3 scripts/plot_m1_bounded.py results/fresh_bounded bounded_screened_gate.png
```

Three serial simulations at a time, 30-second per-evolution cap. Candidate:
`bulk-frame-heun-quadratic-v1 --accelerated-projection --projection-screening 1`.
Dimensionless mu0=1, f64, periodic, gamma=2 for Brio and 5/3 otherwise.
No pressure floors or energy resets. Bx follows the owner-approved mesh
amendment; coarse diagnostic failures are preserved, not promoted to passes.

See the [results report](../../../docs/M1_SHOCK_INVESTIGATION.md#bounded-m1-gate-for-the-screened-candidate-2026-11-09-issue-22).
