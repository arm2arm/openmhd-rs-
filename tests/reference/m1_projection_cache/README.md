# REANA projection cache and threading evidence (2026-11-10)

All 11 evolutions complete and all seven comparisons have byte-identical
scientific files. All 52 downloaded scientific-file hashes were independently
verified. This is a performance/parity packet, not full M1 acceptance.

Baseline Rust/Cargo source matches `3cbd1d5`; cached source matches `9ce5304`
across all 59 recorded files. Workflow `openmhd-m1-cache-campaign-20261110.1`,
UUID `9122c09e-93da-4bda-9f57-a534713cf4d3`, used the pinned REANA image and
Rust 1.85.1. The baseline binary came from the earlier stopped preflight.

| Case | Before evolution (s) | Cached evolution (s) | Speedup |
| --- | ---: | ---: | ---: |
| wave64_k0 | 10.519 | 9.759 | 1.078 |
| wave128_k1 | 98.163 | 91.599 | 1.072 |
| shock512 | 46.693 | 43.727 | 1.068 |
| vortex32 | 36.227 | 32.746 | 1.106 |

N128 is the **standing** wave (parallel velocity 1), jitter .15, t=.02.
The separate campaign calibration uses travelling velocity 0; do not equate
its unknown full-time cost with the standing-wave extrapolation.
The shock is nx512×ny8 at t=.02; vortex N32 at t=.5; all use fixed meshes.
Screening is 1 except the N64 wave at 0. Dimensionless mu0=1, f64, periodic;
gamma=2 for Brio and 5/3 otherwise. No floors or energy resets.

| Threads | Total wall (s) | Evolution (s) | Average CPU cores |
| ---: | ---: | ---: | ---: |
| 1 | 147.033 | 91.599 | 0.990 |
| 4 | 86.759 | 66.988 | 1.752 |
| 12 | 73.547 | 61.937 | 2.306 |
| 24 | 76.157 | 66.292 | 3.047 |

These are one-sample shared-node timings, not controlled scaling guarantees.
Independent case concurrency remains preferable for the full matrix.

`raw.tar.gz` contains all 75 raw files, including initial/final CSVs, histories,
geometry/physics where emitted, logs, timings and the report. `sha256.json`
covers every member and the source/snapshot archives. `execution_source.tar.gz`
contains the exact Rust/Cargo/Python execution sources captured in the same
frozen workspace; all 59 numerical source hashes match the benchmark report.
`execution_snapshot.json` identifies the full original upload.

**Known reporting defect:** the historical `projection_preconditioner_shift`
label is hard-coded to 1e-8 even for positive screening. The actual factor
uses the correctly recorded `projection_screening` value (1 in these cases).
The subsequent reporting correction is separate and not included here.
Original raw bytes are preserved.

Reproduce the comparison in the pinned REANA environment with
`scripts/run_projection_cache_benchmark.py`, the original baseline binary and
its recorded provenance. The parent workflow continues/cancels independently
of this completed sub-study; partial medium runs are not accepted by this packet.

Regenerate the [plot](../../../docs/images/m1_completion/projection_cache.png):

```sh
python3 scripts/plot_projection_cache.py tests/reference/m1_projection_cache/benchmark.json docs/images/m1_completion/projection_cache.png
```

Plot environment: Python 3.9, Matplotlib 3.9.4, NumPy 2.0.2; Agg backend.
