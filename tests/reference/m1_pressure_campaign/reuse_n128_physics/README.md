# Complete N128 physics checkpoint — full N256 gates still pending

`openmhd-m1-pressure-reuse-20261110.1` now has **26/30 completed physics
cases**: all 18 shocks and all eight N64/N128 vortices. All recorded
state/diagnostic gates and all **13 independently reduced boost pairs pass**.
Only the four N256 vortex cases remain. The full wave phase has not started;
this checkpoint does not accept the full physics stage or M1.

| N128 family | Base / boost wall seconds | Minimum recorded pressure | Maximum normalized mean-B drift | Maximum normalized limited-face divergence RMS | Boost max normalized L1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Regular | 2192.08 / 2440.86 | .0278234 | 5.48354e-16 | .0197279 | 1.51895e-14 |
| Planar jitter .15 | 3276.70 / 3566.52 | .0337215 | 9.41954e-5 | .0257406 | 1.40549e-14 |

The unchanged limits are 1e-3 for normalized mean-B drift, .1 for normalized
limited-face divergence, 1e-8 for boost L1 and 1e-10 for conservative budgets.
Every recorded density and pressure is positive. Maximum recorded normalized
budget magnitude across these N128 histories is 1.57707e-13.

Independent reductions of initial/final cells verify all four final budgets,
mean fields and normalized divergence RMS values. The operator values and
intermediate-history extrema are exported solver data; these reductions do
not independently reconstruct the divergence operator or rerun the evolution.

The regular N64/N128 base/boost reference comparisons are independently
reduced from raw face-plane rectangles into the registered 64 × 64 bins.
Their largest L1/L2 disagreement with production is 1.52656e-16. The two
N64/128/256 primary reference ladders explicitly remain **pending**; N128
does not replace the finest N256 gate. This uses the unchanged reducer in
[`reuse_vortex_reference`](../reuse_vortex_reference/), whose earlier
23-record self-contained archive remains intact. Its
[gas](../../../../docs/images/m1_completion/pressure_vortex_refinement_gas.png)
and [magnetic](../../../../docs/images/m1_completion/pressure_vortex_refinement_magnetic.png)
figures already show the completed N64/N128 base comparison.

## Repeated calibration and reduction precision

The N128 jittered base case uses two threads in this phase versus eight in
calibration. **All nine scientific files are byte-identical**, including
initial/final cells, histories, geometry, reference bins and summaries.
Timing and log files differ. The complete paired run records and file hashes
are retained in `calibration_parity.json.gz`. The two wall times are shared-node
observations, not a controlled scaling experiment. The inspected calibration
[gas](../../../../docs/images/m1_completion/pressure_calibration/vortex_calibration_gas.png)
and [magnetic](../../../../docs/images/m1_completion/pressure_calibration/vortex_calibration_magnetic.png)
figures therefore depict exactly the same scientific output as this full-phase
base case.

An initial postprocessing check using NumPy dot-product totals differed from
the regular-mesh recorded normalized mass budget by 2.62051e-13, exceeding
the reducer's 2e-13 agreement check. Both values were far below the unchanged
1e-10 physical gate. The reducer now uses `math.fsum` for the independent
totals and weighted averages, retaining the dot-product observations alongside
them. The compensated budgets have maximum magnitude 6.96552e-17; their
largest difference from the sequential production totals is 1.57707e-13.
No solver arithmetic, recorded result, physical gate or agreement tolerance
was changed. This is a reduction-order observation, not a physics failure.

## Evidence and reproduction

All **268 per-run raw artifacts** and **73 frozen source dependencies** verify.
The run map, manifest, initial phase provenance, paired reductions, independent
state/reference reports and calibration-parity record are retained here.
Large initial/final snapshots remain in the REANA workspace and verified local
download cache. This compact checkpoint is not a self-contained raw-data
archive. The workflow UUID is `7a615758-c141-4903-a2ea-8da3094ddd58`; input
snapshot SHA256 is
`00d823cc61e3ebfca3c79645625e528bf45f59e0a94967f532d74cd52b56390b`.
The phase provenance remains its initial checkpoint, not a final source
immutability verdict. `archive_sha256.json` covers this directory except itself.

After downloading checksum-matching raw files, from the repository root:

```sh
python3 tests/reference/m1_pressure_campaign/reuse_n128_physics/reduce_pairs.py \
  results/reana_remote_m1_pressure_reuse_20261110/source/results/reana_m1-campaign/physics
python3 tests/reference/m1_pressure_campaign/reuse_n128_physics/reduce_states.py \
  results/reana_remote_m1_pressure_reuse_20261110/source/results/reana_m1-campaign/physics
```

Both commands use this immutable 26-record run map even if the live map has
grown. To reproduce the exact primary reference checkpoint, place the
decompressed archived run map beside `provenance_checkpoint.json` and the four
regular N64/N128 base/boost raw case directories, then run the linked
`reduce_reference.py` into a fresh output directory. These are data reductions;
all test/evolution execution remains on REANA.
