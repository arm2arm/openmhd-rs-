# Passing bounded HLL comparator for #24

REANA `openmhd-m1-hll-shock-20261110.1`, UUID
`b689d692-63c5-40cb-9026-b338872346b2`, ran 2026-11-10 02:34:02–02:43:56 UTC.
All eight evolutions complete in 131.92–172.59 seconds. Eight two-thread cases
use at most 16 worker cores; the job memory limit is 16 GB. All tests and
evolutions ran on REANA. Format, strict Clippy, **148 release/all-target Rust
tests, 72 Python tests and M0 checks pass**.

The candidate's explicit `--riemann hll` option changes only the Riemann fan
to the existing two-wave HLL formula. Common normal B, outer signal bounds,
ALE transformation, signal-weighted A-face completion, reconstruction, Heun
update and screened curl-rate projection remain unchanged. HLL has separate
flux/summary metadata; it is not counted as a failed HLLD fallback. Historical
APIs and the default remain HLLD. No floors, resets, resistivity, imposed row
symmetry or acceptance-threshold changes are introduced.

All four HLLD controls reproduce **all 24 original scientific files exactly**,
including the original column failure. The HLL trials pass every check in
this four-case comparison:

| Measurement | HLLD control | Explicit HLL | Original limit |
| --- | ---: | ---: | ---: |
| Column boost maximum normalized L1 | 5.818394374e-6 | 9.589525564e-14 | 1e-8 |
| Regular boost maximum normalized L1 | 5.700347372e-11 | 6.836139727e-13 | 1e-8 |
| Column base final row-to-row vx range | .001680084 | 1.277006278e-12 | diagnostic |
| Column boost final row-to-row vx range | .002194238 | 7.467360064e-13 | diagnostic |
| Column base rho reference L1 | .002086894 | .002768909 | .03 |
| Column base pressure reference L1 | .002438445 | .002627892 | .04 |
| Column base vx reference L1 | .004311679 | .005084955 | .03 |
| Column base By reference L1 | .002978335 | .003604428 | .04 |

Across the HLL histories, minimum density is .116296844 and minimum pressure
.086392573; maximum normalized conservative-budget residual is 2.62435e-14.
Maximum final Bx error is 4.47420e-14. All four seam checks pass.
The new independent derivative-symbol test also confirms the quadratic
stencil's short-mode sign reversal. As the preceding uniform study shows,
that property alone does not establish instability of the coupled candidate.

[Inspected comparison plot](../../../../docs/images/m1_completion/hll_shock_comparison.png)
shows the row mode staying small under HLL, together with the slow-shock
profiles. The plot reproduces byte for byte. `verify_reduction.py` independently
recomputes all four boost comparisons and final row coefficients using NumPy
and verifies 155 archived source files and 74 scientific artifacts. All 305
frozen input files and 84 downloaded output artifacts were also hash checked.
The full accepted-state snapshots remain in the REANA workspace; compact mode
histories and all eight initial/final/geometry/history/summary/log sets are
included in `science.tar.gz`. Exact runtime and build sources are retained.
The working wrapper corrects a copied "no-evolution" docstring; the archived
wrapper preserves its executed bytes. No executable difference is hidden.

This isolates a successful **bounded remedy**, not the single causal HLLD
term or full M1 acceptance. HLL changes both fluid and induction fluxes and
increases diffusion; the reference errors above show a measurable accuracy
cost. The existing smooth-wave, loop, vortex, boost and refinement gates must
all pass for this explicit configuration before adoption. [Springel et al.'s published implementation](https://arxiv.org/html/2609.35989v1#S5.SS1)
uses HLLD (§5.1); HLL is an additional engineering
departure, not a claim of paper equivalence. #24 and M1 remain open.
