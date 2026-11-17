# Independent primary vortex reference reduction — partial ladder

The same frozen REANA campaign now has **23/30 completed physics cases**.
Its first N128 vortex, the regular rest-frame case, completes in 2192.08 s
and passes the state, conservation and magnetic diagnostics. This archive
independently checks the three completed primary vortex cases: regular N64
base/boost and N128 base. N128 boost and both N256 primary cases are absent
from this immutable checkpoint. **Both reference ladders remain pending.**

`reduce_reference.py` recovers rectangular bounds directly from the exported
oriented face planes, verifies their areas against the cell volumes, removes
the boost translation and computes interval intersections with the periodic
64 × 64 bins. It imports neither the production polygon clipping nor its
reference-error routines and does not use saved polygon vertices. Bin coverage
is checked before averaging. The reference is the checksum-pinned Athena++
N512 result already averaged onto those same bins in the M0 packet; this
analysis does not reconstruct the original Athena simulation.

The independently recomputed bin values differ from production by at most
**2.63678e-15**, and the normalized L1/L2 values by **2.77556e-17**.
The archive retains the nine compressed raw inputs, exact 23-run checkpoint,
initial execution provenance, independent bins, reduction and figure scripts.
Executing the reduction from this archive itself exactly reproduces the
measured values and input hashes. No simulation or unit test ran locally.

| Field | N64 base scaled L1 | N128 base scaled L1 | Registered N256 limit |
| --- | ---: | ---: | ---: |
| Density | .05625624 | .02246731 | .06 |
| Gas pressure | .11459538 | .04761318 | .10 |
| Bx | .09505831 | .04097807 | .10 |
| By | .08504542 | .03425788 | .10 |

The improvement is measured, but N128 is not the required finest grid. The
finest-grid limits are not applied to N64 or N128 as replacement gates.
The full N64/128/256 ladders, all vortex boost pairs and both mesh families'
state/divergence checks remain required. Jittered profile diagnostics are not
part of this rectangular-cell reduction.

The inspected figures compare N64, N128 and Athena on identical bins with
matched color limits, followed by the N128 normalized difference:

- [Density and gas pressure](../../../../docs/images/m1_completion/pressure_vortex_refinement_gas.png)
- [Magnetic components](../../../../docs/images/m1_completion/pressure_vortex_refinement_magnetic.png)

Workflow `openmhd-m1-pressure-reuse-20261110.1`, UUID
`7a615758-c141-4903-a2ea-8da3094ddd58`; frozen input SHA256
`00d823cc61e3ebfca3c79645625e528bf45f59e0a94967f532d74cd52b56390b`.
The named candidate is screened quadratic Heun with `hlld-pressure` and κ=1.
All 235 raw artifacts for the first 23 physics cases have been downloaded and
hash checked; all 73 phase source dependencies match the frozen source map.
The initial phase provenance is not a final unchanged-source verdict.
`archive_sha256.json` covers this archive except itself.

From the repository root, with NumPy and Matplotlib available:

```sh
python3 tests/reference/m1_pressure_campaign/reuse_vortex_reference/reduce_reference.py \
  tests/reference/m1_pressure_campaign/reuse_vortex_reference /tmp/fresh_vortex_reference
python3 tests/reference/m1_pressure_campaign/reuse_vortex_reference/plot.py \
  tests/reference/m1_pressure_campaign/reuse_vortex_reference /tmp/fresh_vortex_figures
```

This is archival postprocessing. Full physics, wave/loop/temporal validation,
the original-profile failure disposition and final M1 review remain open.
