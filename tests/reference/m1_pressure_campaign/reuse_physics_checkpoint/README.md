# Full physics checkpoint: 22 of 30 complete

The running `openmhd-m1-pressure-reuse-20261110.1` campaign has completed
all 18 Brio–Wu cases and the four N64 Orszag–Tang cases at this checkpoint.
All 22 recorded state/diagnostic gates pass. Independent reductions of the
**22 hash-verified final CSVs** pass all 11 completed boost pairs.
The eight N128/N256 vortices are pending; **this is not a full physics or
M1 acceptance result**. The 112-case wave/loop/temporal phase has not started.

The formerly failing N1024 column-jitter shock now has maximum normalized
boost L1 **6.049405107e-14**, against the unchanged 1e-8 gate. Its two final
snapshots are retained here. The full regular N1024 pair gives 5.61954e-14;
the planar N1024 pair gives 1.11154e-14. All nine shock pairs pass. The two
N64 vortex pairs give 1.19481e-14 / 1.00143e-14 (regular/jittered).
The historical HLLD failure remains archived separately.

The physics phase starts 2026-11-10 **06:51:35 UTC**, following verified
[complete calibration](../reuse_calibration/README.md), and runs with ten
workers × two threads. The profile is `bulk-frame-heun-quadratic-v1`, with
accelerated projection, screening 1 and `hlld-pressure`. Per-case domains,
EOS, times, mesh families and boosts are retained in the exact manifest.
All 73 driver source dependencies match the frozen preflight manifest.
The recorded prebuilt/current binary digest is
`90d40a752e357ed6a459e828d8a48cba51eed13549229271583f89fb7384a426`.

`runs.json.gz` is the immutable 22-record checkpoint; `manifest.json.gz`
contains all 30 prescribed configurations. `provenance_checkpoint.json`
is the initial phase provenance, **not a final unchanged-source/result
manifest**. `physics_pair_checkpoint.json` records independent NumPy boost
reductions, geometry checks, current run-map digest and reduction-source hash.
The stage's full reference/refinement verdict is still pending. Only the
22 final files have been independently downloaded/verified for this partial
record; other per-run artifacts require the later full archive.

Recompute these same 11 pairs using the immutable archived run map and the
downloaded raw phase directory, even after additional cases have completed:

```sh
python3 tests/reference/m1_pressure_campaign/reuse_physics_checkpoint/reduce_pairs.py results/reana_remote_m1_pressure_reuse_20261110/source/results/reana_m1-campaign/physics
```

The two finest column final CSVs are retained compressed in `snapshots/`.
The other raw files remain in the named REANA workspace and local download
tree. Every loaded final CSV must match its frozen per-run digest. No new
evolution, tolerance change or full-matrix acceptance is performed locally.
